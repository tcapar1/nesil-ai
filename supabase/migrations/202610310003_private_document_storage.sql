-- Private document bucket for Nesil AI.
-- Apply only after comparing with the live project's current Storage schema.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'nesil-user-files',
  'nesil-user-files',
  false,
  10485760,
  array[
    'text/plain', 'text/markdown', 'application/json', 'text/x-python', 'text/csv', 'application/pdf',
    'application/vnd.ms-excel.sheet.macroEnabled.12',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'image/png', 'image/jpeg', 'image/tiff', 'image/bmp',
    'application/vnd.ms-excel'
  ]
)
on conflict (id) do update set
  public = false,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname='storage' and tablename='objects' and policyname='nesil_user_files_select_own') then
    create policy nesil_user_files_select_own on storage.objects
      for select to authenticated
      using (bucket_id = 'nesil-user-files' and (storage.foldername(name))[1] = auth.uid()::text);
  end if;
  if not exists (select 1 from pg_policies where schemaname='storage' and tablename='objects' and policyname='nesil_user_files_insert_own') then
    create policy nesil_user_files_insert_own on storage.objects
      for insert to authenticated
      with check (bucket_id = 'nesil-user-files' and (storage.foldername(name))[1] = auth.uid()::text);
  end if;
  if not exists (select 1 from pg_policies where schemaname='storage' and tablename='objects' and policyname='nesil_user_files_delete_own') then
    create policy nesil_user_files_delete_own on storage.objects
      for delete to authenticated
      using (bucket_id = 'nesil-user-files' and (storage.foldername(name))[1] = auth.uid()::text);
  end if;
end $$;
