# NESİL AI Security and Backup Runbook

This runbook is for the free-tier production project. It deliberately separates verified safeguards from operational tasks that require dashboard access.

## Current verified safeguards

- Supabase project is healthy and the `nesil-chat` Edge Function is active.
- Chat requests are limited to 64 KiB before JSON parsing.
- Chat requests require a valid Supabase user session; the function checks conversation ownership.
- Conversations, messages, memory, document metadata and Storage object policies are scoped to `auth.uid()`.
- The `nesil-user-files` bucket is private and has a 10 MiB per-object limit.
- Client roles do not have TRUNCATE, TRIGGER or REFERENCES privileges on NESİL application tables.
- Service-only quota tables have RLS enabled and no client-facing policies.
- CI has passed Windows, Linux, local Supabase integration and browser static checks on the recorded production commit.

## Backup procedure (manual dashboard step)

A live database backup has NOT been verified by this repository. Do not describe the project as backed up until a downloadable backup has been created and its timestamp and size recorded.

1. Open the Supabase dashboard for the production project.
2. Open Database / Backups (the exact menu may vary by dashboard version and plan).
3. Check whether the current plan provides automatic backups or point-in-time recovery. Do not upgrade a paid plan without owner approval.
4. Before a risky migration, create/download a database dump if the plan and dashboard allow it. Store it privately; never commit dumps, credentials, or user data to GitHub.
5. Record backup timestamp, file size, project reference, and storage location in a private operational log.
6. A database dump does not automatically include Storage object bytes. Preserve the private Storage bucket separately using an authenticated export/download process.
7. Never test restore against production. Restore into a separate disposable project or local Supabase instance, then verify schema, row counts, RLS policies, and Storage object availability.
8. If no free backup/export capability is available, state that clearly and keep the current production data untouched.

## Safe release procedure

1. Work on a feature branch, not directly on `main`.
2. Run GitHub Actions: Windows tests, Linux tests, local Supabase integration, and Pages static checks.
3. Review the migration diff and ensure it contains no destructive statements.
4. Merge only after successful checks and human review.
5. Confirm the production project remains healthy and verify the deployed Edge Function version.
6. Do not claim a Cloudflare Pages deployment unless the Cloudflare deployment status is independently confirmed.

## Remaining owner-only dashboard checks

- Enable leaked-password protection only if the current Supabase plan supports it; the Free plan UI reports Pro is required.
- Review Auth email confirmation, redirect allowlist, SMTP and rate limits in the Supabase dashboard.
- Confirm Cloudflare Pages production deployment and custom-domain settings in the Cloudflare dashboard.
- Keep all service-role and provider keys in server-side secrets only. Never paste them into chat or browser code.

## Incident response

- Do not delete user records or Storage objects as a first response.
- Pause risky releases, preserve logs, rotate only confirmed exposed secrets, and assess impact.
- Restore only after identifying the correct backup and testing it outside production.
