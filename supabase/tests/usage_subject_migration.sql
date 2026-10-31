begin;
select plan(4);

create temporary table nesil_subject_fixture(subject_hash text not null);
insert into nesil_subject_fixture values
  ('global'),
  ('00000000-0000-4000-8000-000000000001'),
  ('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');
update nesil_subject_fixture
set subject_hash=case when subject_hash='global' or subject_hash ~ '^[0-9a-f]{64}$' then subject_hash
                      else encode(digest(subject_hash,'sha256'),'hex') end
where subject_hash <> 'global' and subject_hash !~ '^[0-9a-f]{64}$';

select is((select subject_hash from nesil_subject_fixture where subject_hash='global'),'global',
          'global aggregate key remains unchanged');
select is((select subject_hash from nesil_subject_fixture where subject_hash=encode(digest('00000000-0000-4000-8000-000000000001','sha256'),'hex')),
          encode(digest('00000000-0000-4000-8000-000000000001','sha256'),'hex'),
          'raw Auth UUID is converted to SHA-256');
select is((select subject_hash from nesil_subject_fixture where subject_hash='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'),
          'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
          'existing legacy SHA-256 subject is not hashed again');

create temporary table nesil_usage_fixture(usage_day date, subject_hash text, requests integer, tokens bigint);
insert into nesil_usage_fixture values
  (date '2026-10-31','00000000-0000-4000-8000-000000000001',2,100),
  (date '2026-10-31',encode(digest('00000000-0000-4000-8000-000000000001','sha256'),'hex'),3,200);
create temporary table nesil_usage_fixture_hashed on commit drop as
select usage_day,
       case when subject_hash='global' or subject_hash ~ '^[0-9a-f]{64}$' then subject_hash
            else encode(digest(subject_hash,'sha256'),'hex') end as subject_hash,
       sum(requests)::integer as requests, sum(tokens)::bigint as tokens
from nesil_usage_fixture
group by usage_day,
         case when subject_hash='global' or subject_hash ~ '^[0-9a-f]{64}$' then subject_hash
              else encode(digest(subject_hash,'sha256'),'hex') end;
select is((select requests from nesil_usage_fixture_hashed),5,
          'colliding raw and hashed identities aggregate without losing request counts');

select * from finish();
rollback;
