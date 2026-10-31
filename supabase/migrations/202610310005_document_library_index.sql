-- Searchable metadata index for private documents. Object bytes remain in private Storage.
create table if not exists public.nesil_documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  object_path text not null unique,
  file_name text not null check (char_length(file_name) between 1 and 180),
  folder_name text not null default 'Genel' check (char_length(folder_name) <= 80),
  tags text[] not null default '{}',
  file_size bigint not null default 0 check (file_size >= 0),
  content_type text not null default 'application/octet-stream',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists nesil_documents_owner_created_idx
  on public.nesil_documents(user_id, created_at desc);
create index if not exists nesil_documents_owner_folder_idx
  on public.nesil_documents(user_id, folder_name);
create index if not exists nesil_documents_name_search_idx
  on public.nesil_documents using gin (to_tsvector('simple', file_name));

alter table public.nesil_documents enable row level security;
drop policy if exists nesil_documents_select_own on public.nesil_documents;
drop policy if exists nesil_documents_insert_own on public.nesil_documents;
drop policy if exists nesil_documents_update_own on public.nesil_documents;
drop policy if exists nesil_documents_delete_own on public.nesil_documents;
create policy nesil_documents_select_own on public.nesil_documents
  for select to authenticated using (user_id = (select auth.uid()));
create policy nesil_documents_insert_own on public.nesil_documents
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy nesil_documents_update_own on public.nesil_documents
  for update to authenticated using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy nesil_documents_delete_own on public.nesil_documents
  for delete to authenticated using (user_id = (select auth.uid()));
revoke all on public.nesil_documents from public, anon;
grant select, insert, update, delete on public.nesil_documents to authenticated;
