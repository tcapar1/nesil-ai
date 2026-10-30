-- Nesil AI Supabase foundation
-- Apply in Supabase SQL Editor. All application data is private; service-role access only.
create extension if not exists pgcrypto;

create table if not exists public.nesil_usage_daily (
  usage_day date not null,
  subject_hash text not null,
  requests integer not null default 0 check (requests >= 0),
  tokens bigint not null default 0 check (tokens >= 0),
  primary key (usage_day, subject_hash)
);

create table if not exists public.nesil_usage_events (
  request_id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  usage_day date not null,
  subject_hash text not null,
  estimated_tokens integer not null check (estimated_tokens >= 0),
  actual_tokens integer,
  finished_at timestamptz
);
create index if not exists nesil_usage_events_created_at_idx
  on public.nesil_usage_events (created_at);

create table if not exists public.nesil_usage_cooldowns (
  subject_hash text primary key,
  until_at timestamptz not null
);

create table if not exists public.nesil_login_buckets (
  bucket_start timestamptz primary key,
  attempts integer not null default 0 check (attempts >= 0)
);

-- Future persistent, user-owned conversation and memory storage.
create table if not exists public.nesil_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.nesil_conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'Yeni sohbet',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists nesil_conversations_owner_updated_idx
  on public.nesil_conversations(user_id, updated_at desc);
create table if not exists public.nesil_messages (
  id bigint generated always as identity primary key,
  conversation_id uuid not null references public.nesil_conversations(id) on delete cascade,
  role text not null check (role in ('user','assistant')),
  content text not null,
  created_at timestamptz not null default now()
);
create index if not exists nesil_messages_conversation_created_idx
  on public.nesil_messages(conversation_id, created_at);
create table if not exists public.nesil_memory_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  memory_text text not null check (char_length(memory_text) <= 4000),
  category text not null default 'general',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists nesil_memory_items_owner_idx
  on public.nesil_memory_items(user_id, updated_at desc);

alter table public.nesil_usage_daily enable row level security;
alter table public.nesil_usage_events enable row level security;
alter table public.nesil_usage_cooldowns enable row level security;
alter table public.nesil_login_buckets enable row level security;
alter table public.nesil_profiles enable row level security;
alter table public.nesil_conversations enable row level security;
alter table public.nesil_messages enable row level security;
alter table public.nesil_memory_items enable row level security;

-- No client-facing policies are intentionally created. The backend service role
-- bypasses RLS; browser clients must never receive the service-role key.

create or replace function public.nesil_reserve_usage(
  p_subject_hash text,
  p_estimated_tokens integer,
  p_daily_requests integer default 500,
  p_daily_tokens integer default 150000,
  p_user_requests integer default 100,
  p_minute_requests integer default 20,
  p_minute_tokens integer default 7500
) returns jsonb
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
  v_now timestamptz := clock_timestamp();
  v_day date := (v_now at time zone 'utc')::date;
  v_count integer;
  v_tokens bigint;
  v_global_requests integer;
  v_global_tokens bigint;
  v_user_requests integer;
  v_request_id uuid := gen_random_uuid();
  v_cooldown timestamptz;
begin
  if p_subject_hash is null or length(p_subject_hash) > 128
     or p_estimated_tokens < 0 or p_estimated_tokens > p_minute_tokens then
    raise exception using errcode = 'P0001', message = 'NESIL_INVALID_RESERVATION';
  end if;

  select until_at into v_cooldown from public.nesil_usage_cooldowns
    where subject_hash = 'global';
  if v_cooldown is not null and v_cooldown > v_now then
    raise exception using errcode = 'P0001', message = 'NESIL_PROVIDER_COOLDOWN';
  end if;

  select count(*), coalesce(sum(estimated_tokens),0)
    into v_count, v_tokens
    from public.nesil_usage_events
    where created_at > v_now - interval '60 seconds';
  if v_count >= p_minute_requests or v_tokens + p_estimated_tokens > p_minute_tokens then
    raise exception using errcode = 'P0001', message = 'NESIL_MINUTE_LIMIT';
  end if;

  insert into public.nesil_usage_daily(usage_day, subject_hash, requests, tokens)
    values(v_day, 'global', 0, 0)
    on conflict (usage_day, subject_hash) do nothing;
  insert into public.nesil_usage_daily(usage_day, subject_hash, requests, tokens)
    values(v_day, p_subject_hash, 0, 0)
    on conflict (usage_day, subject_hash) do nothing;

  select requests, tokens into v_global_requests, v_global_tokens
    from public.nesil_usage_daily where usage_day=v_day and subject_hash='global' for update;
  select requests into v_user_requests
    from public.nesil_usage_daily where usage_day=v_day and subject_hash=p_subject_hash for update;

  if v_global_requests >= p_daily_requests or v_global_tokens + p_estimated_tokens > p_daily_tokens
     or v_user_requests >= p_user_requests then
    raise exception using errcode = 'P0001', message = 'NESIL_DAILY_LIMIT';
  end if;

  update public.nesil_usage_daily set requests=requests+1, tokens=tokens+p_estimated_tokens
    where usage_day=v_day and subject_hash='global';
  update public.nesil_usage_daily set requests=requests+1, tokens=tokens+p_estimated_tokens
    where usage_day=v_day and subject_hash=p_subject_hash;

  insert into public.nesil_usage_events(request_id, usage_day, subject_hash, estimated_tokens)
    values(v_request_id, v_day, p_subject_hash, p_estimated_tokens);

  return jsonb_build_object('request_id',v_request_id,'day',v_day,'subject_hash',p_subject_hash,
                            'reserved_tokens',p_estimated_tokens);
end;
$$;

create or replace function public.nesil_finish_usage(
  p_request_id uuid,
  p_actual_tokens integer default 0,
  p_retry_after integer default 0
) returns void
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
  v_event public.nesil_usage_events%rowtype;
  v_actual integer;
begin
  select * into v_event from public.nesil_usage_events where request_id=p_request_id for update;
  if not found or v_event.finished_at is not null then return; end if;
  v_actual := case when p_actual_tokens > 0 then least(p_actual_tokens, 1000000)
                   else v_event.estimated_tokens end;
  update public.nesil_usage_events set actual_tokens=v_actual, finished_at=clock_timestamp()
    where request_id=p_request_id;
  update public.nesil_usage_daily set tokens=greatest(0,tokens + v_actual - v_event.estimated_tokens)
    where usage_day=v_event.usage_day and subject_hash in ('global',v_event.subject_hash);
  if p_retry_after > 0 then
    insert into public.nesil_usage_cooldowns(subject_hash,until_at)
      values('global',clock_timestamp()+make_interval(secs=>least(p_retry_after,86400)))
      on conflict(subject_hash) do update set until_at=greatest(public.nesil_usage_cooldowns.until_at,excluded.until_at);
  end if;
end;
$$;

create or replace function public.nesil_login_attempt()
returns void
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
  v_bucket timestamptz := date_trunc('minute',clock_timestamp()) - make_interval(mins => (extract(minute from clock_timestamp())::integer % 5));
  v_attempts integer;
begin
  insert into public.nesil_login_buckets(bucket_start,attempts) values(v_bucket,0)
    on conflict(bucket_start) do nothing;
  select attempts into v_attempts from public.nesil_login_buckets where bucket_start=v_bucket for update;
  if v_attempts >= 20 then
    raise exception using errcode='P0001', message='NESIL_LOGIN_LIMIT';
  end if;
  update public.nesil_login_buckets set attempts=attempts+1 where bucket_start=v_bucket;
  delete from public.nesil_login_buckets where bucket_start < clock_timestamp()-interval '1 day';
end;
$$;

revoke all on function public.nesil_reserve_usage(text,integer,integer,integer,integer,integer,integer) from public, anon, authenticated;
revoke all on function public.nesil_finish_usage(uuid,integer,integer) from public, anon, authenticated;
revoke all on function public.nesil_login_attempt() from public, anon, authenticated;
grant execute on function public.nesil_reserve_usage(text,integer,integer,integer,integer,integer,integer) to service_role;
grant execute on function public.nesil_finish_usage(uuid,integer,integer) to service_role;
grant execute on function public.nesil_login_attempt() to service_role;
