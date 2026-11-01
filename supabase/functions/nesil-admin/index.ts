import { createClient } from "npm:@supabase/supabase-js@2";

const ALLOWED_ORIGINS = new Set([
  "https://kirmizibeyazai.pages.dev",
  "https://kirmizibeyaz-ai.pages.dev",
  "https://nesilai.pages.dev",
  "http://localhost:8788",
  "http://127.0.0.1:8788",
]);
function isAllowedOrigin(origin: string) {
  if (ALLOWED_ORIGINS.has(origin)) return true;
  try {
    const url = new URL(origin);
    return url.protocol === "https:" && url.port === "" &&
      /^[a-z0-9-]+\.(nesilai|kirmizibeyaz-ai|kirmizibeyazai)\.pages\.dev$/.test(url.hostname);
  } catch { return false; }
}
function json(body: unknown, status = 200, origin = "") {
  const headers = new Headers({
    "Access-Control-Allow-Headers": "authorization, apikey, content-type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "Vary": "Origin",
  });
  if (isAllowedOrigin(origin)) headers.set("Access-Control-Allow-Origin", origin);
  return new Response(JSON.stringify(body), { status, headers });
}
Deno.serve(async (request: Request) => {
  const origin = request.headers.get("origin") ?? "";
  if (request.method === "OPTIONS") {
    if (origin && !isAllowedOrigin(origin)) return new Response(null, { status: 403 });
    return new Response(null, { status: 204, headers: {
      "Access-Control-Allow-Origin": origin || "https://kirmizibeyazai.pages.dev",
      "Access-Control-Allow-Headers": "authorization, apikey, content-type",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Vary": "Origin",
      "Cache-Control": "no-store",
    }});
  }
  if (origin && !isAllowedOrigin(origin)) return json({ error: "Origin not allowed" }, 403, origin);
  if (!["GET", "POST"].includes(request.method)) return json({ error: "Method not allowed" }, 405, origin);
  const authorization = request.headers.get("Authorization") || "";
  const token = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
  if (!token) return json({ error: "Unauthorized" }, 401, origin);
  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") || Deno.env.get("SUPABASE_PUBLISHABLE_KEY") || "";
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!supabaseUrl || !anonKey || !serviceRoleKey) return json({ error: "Admin service is not configured" }, 503, origin);
  const authClient = createClient(supabaseUrl, anonKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const { data: authData, error: authError } = await authClient.auth.getUser(token);
  if (authError || !authData.user?.email) return json({ error: "Unauthorized" }, 401, origin);
  const configuredAdmins = (Deno.env.get("NESIL_ADMIN_EMAILS") || "tuncaycapar1@gmail.com").split(/[;,]/).map((v) => v.trim().toLowerCase()).filter(Boolean);
  if (!configuredAdmins.includes(authData.user.email.trim().toLowerCase())) return json({ error: "Forbidden" }, 403, origin);
  const admin = createClient(supabaseUrl, serviceRoleKey, { auth: { persistSession: false, autoRefreshToken: false } });
  let stage = "request";
  try {
    if (request.method === "POST") {
      stage = "post_action";
      const body = await request.json();
      if (body.action === "review_candidate") {
        const id = String(body.id || "");
        const status = body.status;
        if (!/^[0-9a-f-]{36}$/i.test(id) || !["approved", "rejected"].includes(status)) return json({ error: "Invalid review request" }, 400, origin);
        const { data, error } = await admin.from("ai_learning_candidates").update({
          status, reviewed_by: authData.user.id, reviewed_at: new Date().toISOString(),
        }).eq("id", id).eq("status", "pending").select("id,status").maybeSingle();
        if (error) throw error;
        if (!data) return json({ error: "Candidate not found or already reviewed" }, 409, origin);
        return json({ ok: true, candidate: data }, 200, origin);
      }
      if (body.action === "create_candidate") {
        const candidateText = String(body.candidate_text || "").trim();
        const category = String(body.category || "general").trim().slice(0, 80) || "general";
        if (candidateText.length < 1 || candidateText.length > 4000) return json({ error: "Candidate text must be 1–4000 characters" }, 400, origin);
        const { data, error } = await admin.from("ai_learning_candidates").insert({
          candidate_text: candidateText, category, status: "pending",
        }).select("id,status,candidate_text,category,created_at").single();
        if (error) throw error;
        return json({ ok: true, candidate: data }, 201, origin);
      }
      return json({ error: "Unknown action" }, 400, origin);
    }
    stage = "overview_queries";
    const [conversations, messages, documents, feedback, candidates] = await Promise.all([
      admin.from("nesil_conversations").select("*", { count: "exact", head: true }),
      admin.from("nesil_messages").select("*", { count: "exact", head: true }),
      admin.from("nesil_documents").select("*", { count: "exact", head: true }),
      admin.from("ai_feedback").select("id,rating,reason,created_at,conversation_id,message_id").order("created_at", { ascending: false }).limit(100),
      admin.from("ai_learning_candidates").select("id,candidate_text,category,status,created_at,reviewed_at").order("created_at", { ascending: false }).limit(100),
    ]);
    for (const result of [conversations, messages, documents, feedback, candidates]) if (result.error) throw result.error;
    stage = "list_users";
    const users = [];
    let page = 1;
    while (page <= 10) {
      const { data, error } = await admin.auth.admin.listUsers({ page, perPage: 100 });
      if (error) throw error;
      users.push(...(data.users || []).map((user) => ({
        email: user.email || "", created_at: user.created_at || null,
        last_sign_in_at: user.last_sign_in_at || null, email_confirmed_at: user.email_confirmed_at || null,
        banned_until: user.banned_until || null,
      })));
      if (!data.users || data.users.length < 100) break;
      page++;
    }
    return json({
      is_admin: true,
      metrics: { users: users.length, conversations: conversations.count || 0, messages: messages.count || 0, documents: documents.count || 0,
        feedback: feedback.data?.length || 0, candidates: candidates.data?.filter((c) => c.status === "pending").length || 0 },
      users, users_truncated: users.length >= 1000,
      feedback: feedback.data || [], candidates: candidates.data || [],
    }, 200, origin);
  } catch (error) {
    const detail = error instanceof Error ? { name: error.name, message: error.message, stack: error.stack } : error;
    console.error("nesil-admin request failed", JSON.stringify({ stage, detail }));
    return json({ error: "Admin data could not be loaded" }, 500, origin);
  }
});
