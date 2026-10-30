-- Supabase Auth ownership policies for Nesil AI private user data.
-- Apply AFTER 202610310001_initial_schema.sql in the Supabase SQL Editor.
-- Does not alter or expose the service-role usage RPCs.

alter table public.nesil_profiles enable row level security;
alter table public.nesil_conversations enable row level security;
alter table public.nesil_messages enable row level security;
alter table public.nesil_memory_items enable row level security;

-- Remove any earlier policies with these names before recreating them.
drop policy if exists nesil_profiles_select_own on public.nesil_profiles;
drop policy if exists nesil_profiles_insert_own on public.nesil_profiles;
drop policy if exists nesil_profiles_update_own on public.nesil_profiles;
drop policy if exists nesil_conversations_select_own on public.nesil_conversations;
drop policy if exists nesil_conversations_insert_own on public.nesil_conversations;
drop policy if exists nesil_conversations_update_own on public.nesil_conversations;
drop policy if exists nesil_conversations_delete_own on public.nesil_conversations;
drop policy if exists nesil_messages_select_own on public.nesil_messages;
drop policy if exists nesil_messages_insert_own on public.nesil_messages;
drop policy if exists nesil_messages_update_own on public.nesil_messages;
drop policy if exists nesil_messages_delete_own on public.nesil_messages;
drop policy if exists nesil_memory_select_own on public.nesil_memory_items;
drop policy if exists nesil_memory_insert_own on public.nesil_memory_items;
drop policy if exists nesil_memory_update_own on public.nesil_memory_items;
drop policy if exists nesil_memory_delete_own on public.nesil_memory_items;

create policy nesil_profiles_select_own on public.nesil_profiles
  for select to authenticated using (user_id = (select auth.uid()));
create policy nesil_profiles_insert_own on public.nesil_profiles
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy nesil_profiles_update_own on public.nesil_profiles
  for update to authenticated using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy nesil_conversations_select_own on public.nesil_conversations
  for select to authenticated using (user_id = (select auth.uid()));
create policy nesil_conversations_insert_own on public.nesil_conversations
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy nesil_conversations_update_own on public.nesil_conversations
  for update to authenticated using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy nesil_conversations_delete_own on public.nesil_conversations
  for delete to authenticated using (user_id = (select auth.uid()));

-- A message is visible/mutable only when its parent conversation belongs to this user.
create policy nesil_messages_select_own on public.nesil_messages
  for select to authenticated using (
    exists (select 1 from public.nesil_conversations c
            where c.id = conversation_id and c.user_id = (select auth.uid()))
  );
create policy nesil_messages_insert_own on public.nesil_messages
  for insert to authenticated with check (
    exists (select 1 from public.nesil_conversations c
            where c.id = conversation_id and c.user_id = (select auth.uid()))
  );
create policy nesil_messages_update_own on public.nesil_messages
  for update to authenticated using (
    exists (select 1 from public.nesil_conversations c
            where c.id = conversation_id and c.user_id = (select auth.uid()))
  ) with check (
    exists (select 1 from public.nesil_conversations c
            where c.id = conversation_id and c.user_id = (select auth.uid()))
  );
create policy nesil_messages_delete_own on public.nesil_messages
  for delete to authenticated using (
    exists (select 1 from public.nesil_conversations c
            where c.id = conversation_id and c.user_id = (select auth.uid()))
  );

create policy nesil_memory_select_own on public.nesil_memory_items
  for select to authenticated using (user_id = (select auth.uid()));
create policy nesil_memory_insert_own on public.nesil_memory_items
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy nesil_memory_update_own on public.nesil_memory_items
  for update to authenticated using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy nesil_memory_delete_own on public.nesil_memory_items
  for delete to authenticated using (user_id = (select auth.uid()));

-- Remove implicit client grants before granting minimum authenticated access.
revoke all on public.nesil_profiles from public, anon;
revoke all on public.nesil_conversations from public, anon;
revoke all on public.nesil_messages from public, anon;
revoke all on public.nesil_memory_items from public, anon;

-- Grant only the table operations required by authenticated sessions.
grant select, insert, update on public.nesil_profiles to authenticated;
grant select, insert, update, delete on public.nesil_conversations to authenticated;
grant select, insert, update, delete on public.nesil_messages to authenticated;
grant select, insert, update, delete on public.nesil_memory_items to authenticated;

-- Profiles are created automatically for newly registered Auth users.
create or replace function public.nesil_handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
begin
  insert into public.nesil_profiles(user_id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'display_name', ''))
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists nesil_on_auth_user_created on auth.users;
create trigger nesil_on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.nesil_handle_new_auth_user();

revoke all on function public.nesil_handle_new_auth_user() from public, anon, authenticated;
