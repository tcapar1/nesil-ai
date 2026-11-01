import { createClient } from "npm:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
};
function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: corsHeaders });
}
Deno.serve(async (request: Request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (request.method !== "GET") return json({ error: "Method not allowed" }, 405);
  const authorization = request.headers.get("Authorization") || "";
  const token = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
  if (!token) return json({ error: "Unauthorized" }, 401);
  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") || Deno.env.get("SUPABASE_PUBLISHABLE_KEY") || "";
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!supabaseUrl || !anonKey || !serviceRoleKey) {
    console.error("nesil-admin missing required server configuration");
    return json({ error: "Admin service is not configured" }, 503);
  }
  // Verify the bearer token with Supabase Auth; never trust an email supplied by the browser.
  const authClient = createClient(supabaseUrl, anonKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const { data: authData, error: authError } = await authClient.auth.getUser(token);
  if (authError || !authData.user?.email) return json({ error: "Unauthorized" }, 401);
  const configuredAdmins = (Deno.env.get("NESIL_ADMIN_EMAILS") || "tuncaycapar1@gmail.com")
    .split(/[;,]/).map((value) => value.trim().toLowerCase()).filter(Boolean);
  const verifiedEmail = authData.user.email.trim().toLowerCase();
  if (!configuredAdmins.includes(verifiedEmail)) return json({ error: "Forbidden" }, 403);
  const admin = createClient(supabaseUrl, serviceRoleKey, { auth: { persistSession: false, autoRefreshToken: false } });
  try {
    const [conversations, messages, documents] = await Promise.all([
      admin.from("nesil_conversations").select("*", { count: "exact", head: true }),
      admin.from("nesil_messages").select("*", { count: "exact", head: true }),
      admin.from("nesil_documents").select("*", { count: "exact", head: true }),
    ]);
    for (const result of [conversations, messages, documents]) if (result.error) throw new Error("Admin aggregate query failed");
    const users = [];
    let page = 1;
    const perPage = 100;
    while (page <= 10) {
      const { data, error } = await admin.auth.admin.listUsers({ page, perPage });
      if (error) throw new Error("Admin user listing failed");
      users.push(...(data.users || []).map((user) => ({
        email: user.email || "", created_at: user.created_at || null,
        last_sign_in_at: user.last_sign_in_at || null, email_confirmed_at: user.email_confirmed_at || null,
        banned_until: user.banned_until || null,
      })));
      if (!data.users || data.users.length < perPage) break;
      page += 1;
    }
    return json({
      is_admin: true,
      metrics: { users: users.length, conversations: conversations.count || 0, messages: messages.count || 0, documents: documents.count || 0 },
      users, users_truncated: users.length >= perPage * 10,
    });
  } catch (error) {
    console.error("nesil-admin request failed:", error instanceof Error ? error.message : "unknown");
    return json({ error: "Admin data could not be loaded" }, 500);
  }
});
