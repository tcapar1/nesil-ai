"""Optional small-team gate and feature-flagged Supabase Auth."""
import hashlib, hmac, json, os
from supabase_auth import create_auth_client, SupabaseAuthError

def _setting(secrets, key, default=""):
    try: value = secrets.get(key)
    except Exception: value = None
    return value if value not in (None, "") else os.environ.get(key, default)

def configured_users(secrets):
    try: users = secrets.get("NESIL_USERS")
    except Exception: users = None
    if users is None: users = json.loads(os.environ.get("NESIL_USERS_JSON", "{}"))
    if not hasattr(users, "items"): raise ValueError("NESIL_USERS must map user names to access codes")
    result = dict(users)
    if any(not isinstance(k, str) or not isinstance(v, str) or len(v) < 16 for k, v in result.items()):
        raise ValueError("Access codes must contain at least 16 characters")
    return result

def configured_admin_emails(secrets):
    try:
        configured = secrets.get("NESIL_ADMIN_EMAILS")
    except Exception:
        configured = None
    if configured is None:
        configured = os.environ.get("NESIL_ADMIN_EMAILS", "")
    if isinstance(configured, str):
        values = configured.replace(";", ",").split(",")
    elif isinstance(configured, (list, tuple, set)):
        values = configured
    else:
        raise ValueError("NESIL_ADMIN_EMAILS must be a list of email addresses")
    return {str(value).strip().lower() for value in values if str(value).strip()}


def is_admin_email(secrets, email):
    normalized = str(email or "").strip().lower()
    return bool(normalized and normalized in configured_admin_emails(secrets))


def authenticate(users, name, code):
    expected = users.get(name)
    if not expected or not hmac.compare_digest(expected.encode(), code.encode()): return ""
    return hashlib.sha256((name + chr(0) + expected).encode()).hexdigest()

def _require_supabase_access(st):
    if st.session_state.get("supabase_access_token") and st.session_state.get("supabase_user_id"):
        return st.session_state.supabase_user_id
    client = create_auth_client(st.secrets)
    st.title("🤖 Nesil AI")
    st.caption("E-posta adresiniz ve şifrenizle güvenli giriş yapın.")
    action = st.radio("İşlem", ["Giriş yap", "Yeni hesap oluştur"], horizontal=True)
    email = st.text_input("E-posta", max_chars=254)
    password = st.text_input("Şifre", type="password", max_chars=128)
    if st.button("Devam et", use_container_width=True):
        if not email or "@" not in email or len(password) < 8:
            st.error("Geçerli e-posta ve en az 8 karakterlik şifre girin.")
        else:
            try:
                if action == "Yeni hesap oluştur":
                    result = client.sign_up(email, password)
                    if result.get("access_token") and result.get("refresh_token") and result.get("user", {}).get("id"):
                        st.session_state.supabase_access_token = result["access_token"]
                        st.session_state.supabase_refresh_token = result["refresh_token"]
                        st.session_state.supabase_user_id = result["user"]["id"]
                        st.session_state.supabase_user_email = result["user"].get("email", email).strip().lower()
                        st.rerun()
                    st.success("Hesap oluşturma isteği alındı. E-posta doğrulamasını tamamlayın, ardından giriş yapın.")
                else:
                    result = client.sign_in(email, password)
                    st.session_state.supabase_access_token = result["access_token"]
                    st.session_state.supabase_refresh_token = result["refresh_token"]
                    st.session_state.supabase_user_id = result["user"]["id"]
                    st.session_state.supabase_user_email = result["user"].get("email", email).strip().lower()
                    st.rerun()
            except SupabaseAuthError as exc: st.error(str(exc))
    st.stop()

def require_access(st, store):
    auth_backend = str(_setting(st.secrets, "NESIL_AUTH_BACKEND", "legacy")).strip().lower()
    if auth_backend == "supabase": return _require_supabase_access(st)
    if auth_backend != "legacy": raise ValueError("NESIL_AUTH_BACKEND yalnızca legacy veya supabase olabilir.")
    users = configured_users(st.secrets)
    if not users: return "public"
    active = {hashlib.sha256((name + chr(0) + code).encode()).hexdigest() for name, code in users.items()}
    if st.session_state.get("principal") in active: return st.session_state.principal
    st.title("🤖 Nesil AI")
    st.caption("Devam etmek için kurum hesabınızla giriş yapın.")
    name = st.text_input("Kullanıcı adı", max_chars=100)
    code = st.text_input("Erişim kodu", type="password", max_chars=200)
    if st.button("Giriş yap"):
        from usage_limits import UsageLimit
        try:
            store.login_attempt()
            principal = authenticate(users, name, code)
            if principal:
                st.session_state.principal = principal
                st.rerun()
            st.error("Kullanıcı adı veya erişim kodu geçersiz.")
        except UsageLimit as exc: st.error(str(exc))
    st.stop()
