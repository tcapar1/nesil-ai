-- Move elevated document-operation routines out of the exposed public API schema.
-- Public RPC names remain stable for the browser client, but execute as invoker wrappers.
create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

alter function public.nesil_begin_document_upload(text,text,text,bigint,text,text) set schema private;
alter function public.nesil_finish_document_upload(text) set schema private;
alter function public.nesil_begin_document_delete(text,uuid) set schema private;
alter function public.nesil_finish_document_delete(text) set schema private;

grant execute on function private.nesil_begin_document_upload(text,text,text,bigint,text,text) to authenticated;
grant execute on function private.nesil_finish_document_upload(text) to authenticated;
grant execute on function private.nesil_begin_document_delete(text,uuid) to authenticated;
grant execute on function private.nesil_finish_document_delete(text) to authenticated;

create or replace function public.nesil_begin_document_upload(
 p_operation_id text,p_object_path text,p_file_name text,p_file_size bigint,p_content_type text,p_sha256 text
) returns jsonb language sql security invoker
set search_path=pg_catalog,public,private
as $$ select private.nesil_begin_document_upload(p_operation_id,p_object_path,p_file_name,p_file_size,p_content_type,p_sha256) $$;

create or replace function public.nesil_finish_document_upload(p_operation_id text)
returns jsonb language sql security invoker
set search_path=pg_catalog,public,private
as $$ select private.nesil_finish_document_upload(p_operation_id) $$;

create or replace function public.nesil_begin_document_delete(p_operation_id text,p_document_id uuid)
returns jsonb language sql security invoker
set search_path=pg_catalog,public,private
as $$ select private.nesil_begin_document_delete(p_operation_id,p_document_id) $$;

create or replace function public.nesil_finish_document_delete(p_operation_id text)
returns jsonb language sql security invoker
set search_path=pg_catalog,public,private
as $$ select private.nesil_finish_document_delete(p_operation_id) $$;

revoke all on function public.nesil_begin_document_upload(text,text,text,bigint,text,text) from public,anon;
revoke all on function public.nesil_finish_document_upload(text) from public,anon;
revoke all on function public.nesil_begin_document_delete(text,uuid) from public,anon;
revoke all on function public.nesil_finish_document_delete(text) from public,anon;
grant execute on function public.nesil_begin_document_upload(text,text,text,bigint,text,text) to authenticated;
grant execute on function public.nesil_finish_document_upload(text) to authenticated;
grant execute on function public.nesil_begin_document_delete(text,uuid) to authenticated;
grant execute on function public.nesil_finish_document_delete(text) to authenticated;
