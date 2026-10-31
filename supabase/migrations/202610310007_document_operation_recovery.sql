-- Transactional ledger for recoverable, user-scoped Storage/catalog operations.
-- This migration is for controlled staging validation; it has not been applied
-- to the production Supabase project.
create table if not exists public.nesil_document_operations (
  operation_id uuid not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  operation_kind text not null check (operation_kind in ('upload','delete')),
  state text not null default 'pending' check (state in ('pending','completed')),
  object_path text not null,
  file_name text not null check (char_length(file_name) between 1 and 180),
  file_size bigint not null check (file_size between 1 and 10485760),
  content_type text not null,
  sha256 text,
  document_id uuid references public.nesil_documents(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, operation_id),
  check (sha256 is null or sha256 ~ '^[0-9a-f]{64}$')
);
create index if not exists nesil_document_operations_pending_idx
  on public.nesil_document_operations(user_id, created_at) where state='pending';
alter table public.nesil_document_operations enable row level security;
drop policy if exists nesil_document_operations_select_own on public.nesil_document_operations;
create policy nesil_document_operations_select_own on public.nesil_document_operations
  for select to authenticated using (user_id=(select auth.uid()));
revoke all on public.nesil_document_operations from public, anon, authenticated;
grant select on public.nesil_document_operations to authenticated;

create or replace function public.nesil_begin_document_upload(
  p_operation_id text, p_object_path text, p_file_name text,
  p_file_size bigint, p_content_type text, p_sha256 text
) returns jsonb language plpgsql security definer
set search_path=pg_catalog,public as $$
declare v_uid uuid := auth.uid(); v_id uuid;
begin
  if v_uid is null or p_operation_id is null or p_operation_id !~ '^[0-9a-f]{32}$'
     or p_object_path is null or split_part(p_object_path,'/',1) <> v_uid::text
     or p_object_path like '%..%' or p_file_size not between 1 and 10485760
     or p_file_name is null or char_length(p_file_name) not between 1 and 180
     or p_sha256 is null or p_sha256 !~ '^[0-9a-f]{64}$' then
    raise exception using errcode='42501',message='NESIL_INVALID_DOCUMENT_OPERATION';
  end if;
  insert into public.nesil_document_operations(operation_id,user_id,operation_kind,object_path,file_name,file_size,content_type,sha256)
  values(p_operation_id::uuid,v_uid,'upload',p_object_path,p_file_name,p_file_size,left(coalesce(p_content_type,'application/octet-stream'),120),p_sha256)
  on conflict(user_id,operation_id) do update set updated_at=clock_timestamp()
    where nesil_document_operations.operation_kind='upload'
      and nesil_document_operations.object_path=excluded.object_path
      and nesil_document_operations.sha256=excluded.sha256
      and nesil_document_operations.file_size=excluded.file_size;
  select operation_id into v_id from public.nesil_document_operations
    where user_id=v_uid and operation_id=p_operation_id::uuid;
  if v_id is null then raise exception using errcode='P0001',message='NESIL_OPERATION_CONFLICT'; end if;
  return jsonb_build_object('operation_id',v_id,'state',(select state from public.nesil_document_operations where user_id=v_uid and operation_id=v_id));
end $$;

create or replace function public.nesil_finish_document_upload(p_operation_id text)
returns jsonb language plpgsql security definer
set search_path=pg_catalog,public as $$
declare v_uid uuid := auth.uid(); v_op public.nesil_document_operations%rowtype; v_doc uuid;
begin
  if v_uid is null then raise exception using errcode='42501',message='NESIL_AUTH_REQUIRED'; end if;
  select * into v_op from public.nesil_document_operations
    where user_id=v_uid and operation_id=p_operation_id::uuid and operation_kind='upload' for update;
  if not found then raise exception using errcode='P0002',message='NESIL_OPERATION_NOT_FOUND'; end if;
  insert into public.nesil_documents(user_id,object_path,file_name,file_size,content_type)
  values(v_uid,v_op.object_path,v_op.file_name,v_op.file_size,v_op.content_type)
  on conflict(object_path) do update set file_name=excluded.file_name,file_size=excluded.file_size,content_type=excluded.content_type,updated_at=clock_timestamp()
    where nesil_documents.user_id=v_uid
  returning id into v_doc;
  if v_doc is null then raise exception using errcode='42501',message='NESIL_DOCUMENT_NOT_OWNED'; end if;
  update public.nesil_document_operations set state='completed',document_id=v_doc,updated_at=clock_timestamp()
    where user_id=v_uid and operation_id=v_op.operation_id;
  return jsonb_build_object('document_id',v_doc,'state','completed');
end $$;

create or replace function public.nesil_begin_document_delete(p_operation_id text,p_document_id uuid)
returns jsonb language plpgsql security definer
set search_path=pg_catalog,public as $$
declare v_uid uuid := auth.uid(); v_doc public.nesil_documents%rowtype;
begin
  if v_uid is null or p_operation_id is null or p_operation_id !~ '^[0-9a-f]{32}$' then
    raise exception using errcode='42501',message='NESIL_INVALID_DOCUMENT_OPERATION';
  end if;
  select * into v_doc from public.nesil_documents where id=p_document_id and user_id=v_uid for update;
  if not found then raise exception using errcode='P0002',message='NESIL_DOCUMENT_NOT_FOUND'; end if;
  insert into public.nesil_document_operations(operation_id,user_id,operation_kind,object_path,file_name,file_size,content_type,document_id)
  values(p_operation_id::uuid,v_uid,'delete',v_doc.object_path,v_doc.file_name,v_doc.file_size,v_doc.content_type,v_doc.id)
  on conflict(user_id,operation_id) do update set updated_at=clock_timestamp()
    where nesil_document_operations.operation_kind='delete' and nesil_document_operations.object_path=excluded.object_path;
  if not exists(select 1 from public.nesil_document_operations where user_id=v_uid and operation_id=p_operation_id::uuid
                and operation_kind='delete' and object_path=v_doc.object_path and document_id=v_doc.id) then
    raise exception using errcode='P0001',message='NESIL_OPERATION_CONFLICT';
  end if;
  return jsonb_build_object('operation_id',p_operation_id,'state','pending');
end $$;

create or replace function public.nesil_finish_document_delete(p_operation_id text)
returns jsonb language plpgsql security definer
set search_path=pg_catalog,public as $$
declare v_uid uuid := auth.uid(); v_op public.nesil_document_operations%rowtype;
begin
  if v_uid is null then raise exception using errcode='42501',message='NESIL_AUTH_REQUIRED'; end if;
  select * into v_op from public.nesil_document_operations
    where user_id=v_uid and operation_id=p_operation_id::uuid and operation_kind='delete' for update;
  if not found then raise exception using errcode='P0002',message='NESIL_OPERATION_NOT_FOUND'; end if;
  delete from public.nesil_documents where user_id=v_uid and object_path=v_op.object_path;
  update public.nesil_document_operations set state='completed',updated_at=clock_timestamp()
    where user_id=v_uid and operation_id=v_op.operation_id;
  return jsonb_build_object('state','completed');
end $$;

revoke all on function public.nesil_begin_document_upload(text,text,text,bigint,text,text) from public,anon;
revoke all on function public.nesil_finish_document_upload(text) from public,anon;
revoke all on function public.nesil_begin_document_delete(text,uuid) from public,anon;
revoke all on function public.nesil_finish_document_delete(text) from public,anon;
grant execute on function public.nesil_begin_document_upload(text,text,text,bigint,text,text) to authenticated;
grant execute on function public.nesil_finish_document_upload(text) to authenticated;
grant execute on function public.nesil_begin_document_delete(text,uuid) to authenticated;
grant execute on function public.nesil_finish_document_delete(text) to authenticated;
