-- Kırmızı Beyaz AI growth system - phase 1
-- Prepared on an isolated feature branch. NOT applied to production.
create table if not exists public.ai_feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  conversation_id uuid not null references public.nesil_conversations(id) on delete cascade,
  message_id bigint not null references public.nesil_messages(id) on delete cascade,
  rating text not null check (rating in ('helpful', 'not_helpful')),
  reason text null check (reason is null or char_length(reason) <= 2000),
  created_at timestamptz not null default now(),
  constraint ai_feedback_one_per_user_message unique (user_id, message_id)
);

create index if not exists ai_feedback_created_at_idx
  on public.ai_feedback (created_at desc);
create index if not exists ai_feedback_rating_created_at_idx
  on public.ai_feedback (rating, created_at desc);

alter table public.ai_feedback enable row level security;

-- A signed-in user can only create and read feedback belonging to them.
create policy "Users can read own AI feedback"
  on public.ai_feedback for select to authenticated
  using (auth.uid() = user_id);

create policy "Users can submit own AI feedback"
  on public.ai_feedback for insert to authenticated
  with check (
    auth.uid() = user_id
    and exists (
      select 1
      from public.nesil_messages m
      join public.nesil_conversations c on c.id = m.conversation_id
      where m.id = ai_feedback.message_id
        and m.conversation_id = ai_feedback.conversation_id
        and c.user_id = auth.uid()
        and m.role = 'assistant'
    )
  );

-- Candidate records are written/reviewed by trusted server-side functions only.
create table if not exists public.ai_learning_candidates (
  id uuid primary key default gen_random_uuid(),
  source_feedback_id uuid null references public.ai_feedback(id) on delete set null,
  candidate_text text not null check (char_length(candidate_text) between 1 and 4000),
  category text not null default 'general' check (char_length(category) <= 80),
  source_url text null check (source_url is null or char_length(source_url) <= 2000),
  evidence_summary text null check (evidence_summary is null or char_length(evidence_summary) <= 4000),
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  reviewed_by uuid null references auth.users(id) on delete set null,
  reviewed_at timestamptz null,
  created_at timestamptz not null default now(),
  constraint ai_learning_review_state check (
    (status = 'pending' and reviewed_at is null)
    or (status in ('approved', 'rejected') and reviewed_at is not null)
  )
);

create index if not exists ai_learning_candidates_status_created_idx
  on public.ai_learning_candidates (status, created_at desc);

alter table public.ai_learning_candidates enable row level security;
-- Intentionally no client policies: only trusted Edge Functions using service role can access candidates.
