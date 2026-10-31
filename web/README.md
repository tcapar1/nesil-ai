# nesilai Web (Cloudflare Pages)

This is a separate static web client. It does not replace the existing Streamlit app or Worker.

## Current scope
- Responsive Turkish interface.
- Supabase email/password sign-in, sign-up and password reset.
- User-owned conversation list and message persistence through Supabase RLS.
- Chat UI scaffold. AI generation remains disabled until the existing Worker API is reviewed and a secure chat endpoint is connected.
- Documents and memory screens are intentionally placeholders until their existing storage/data methods are wired and tested.

## Configure
1. Copy the project Supabase URL and **publishable** API key into `config.js`.
2. Never place a Supabase secret/service-role key or model provider key in this folder.
3. The current production Supabase project must already have the migrations applied. Do not run migrations from this folder.

## Cloudflare Pages
Connect this repository and select branch `feature/pages-web-20261101`.
- Framework preset: None
- Build command: leave empty
- Build output directory: `web`
- Root directory: leave empty

Deploy only to the generated `*.pages.dev` preview. Do not bind a custom domain or change the existing Worker routes until tests pass.
