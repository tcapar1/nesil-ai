# AI Growth System – Phase 1

This branch contains the first isolated implementation plan for Kırmızı Beyaz AI's learning workflow.

## Safety boundaries
- Production Cloudflare Pages and Supabase Edge Functions are unchanged.
- No production SQL migration has been applied.
- The `main` branch remains unchanged.
- All learning candidates remain pending until an administrator reviews them.
- User feedback is private to its owner; candidate records have no client-facing RLS policies.
- Feedback is linked to an assistant message ID; raw conversation text is not copied into the learning tables.

## Phase 1 scope
1. Capture helpful / not-helpful feedback for assistant messages.
2. Optionally capture a short user-provided reason (maximum 2,000 characters).
3. Prepare a server-only learning-candidate queue.
4. Keep candidate approval separate from learning capture.
5. Do not automatically change prompts, code, model settings, or published knowledge.

## Before production rollout
- Review current RLS and grants on `nesil_messages` and `nesil_conversations`.
- Verify the logged-in user can only submit feedback for their own assistant messages.
- Add an authenticated, administrator-only review endpoint.
- Add UI feedback controls and test duplicate submissions.
- Run migration in a non-production environment first.
- Require explicit administrator approval before applying migration or deploying any function.
