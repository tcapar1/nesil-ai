-- Add conversation organization flags to existing installations.
-- Safe additive migration; does not delete or rewrite conversation data.
alter table public.nesil_conversations
  add column if not exists is_pinned boolean not null default false,
  add column if not exists is_archived boolean not null default false;

create index if not exists nesil_conversations_owner_pinned_updated_idx
  on public.nesil_conversations(user_id, is_pinned desc, updated_at desc)
  where is_archived = false;
