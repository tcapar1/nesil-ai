-- One-time transition from raw application principals to stable SHA-256
-- subjects. Aggregate counts/tokens and event history are retained; only
-- identifiers change. Apply in the same controlled release as the code change.
do $$
begin
  create temporary table nesil_usage_daily_hashed on commit drop as
  select usage_day,
         case when subject_hash='global' then 'global'
              else encode(digest(subject_hash,'sha256'),'hex') end as subject_hash,
         sum(requests)::integer as requests,
         sum(tokens)::bigint as tokens
  from public.nesil_usage_daily
  group by usage_day,
           case when subject_hash='global' then 'global'
                else encode(digest(subject_hash,'sha256'),'hex') end;

  delete from public.nesil_usage_daily;
  insert into public.nesil_usage_daily(usage_day,subject_hash,requests,tokens)
  select usage_day,subject_hash,requests,tokens from nesil_usage_daily_hashed;
end $$;

update public.nesil_usage_events
set subject_hash=encode(digest(subject_hash,'sha256'),'hex')
where subject_hash <> 'global';
