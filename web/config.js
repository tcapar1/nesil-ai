// Public browser configuration only. The publishable key is designed for browser use.
// Never place a Supabase secret/service-role key or model provider key here.
export const SUPABASE_URL = "https://zwdrqhqpbuvpqteuklbg.supabase.co";
export const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_lK_aFCtsASkAi0b1KsfUpw_aiugJPG8";
// Authenticated Supabase Edge Function; provider keys remain server-side.
export const AI_API_URL = SUPABASE_URL + "/functions/v1/nesil-chat";
