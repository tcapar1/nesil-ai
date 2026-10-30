"""Optional small-team access gate; credentials stay in server secrets."""
import hashlib
import hmac
import json
import os


def configured_users(secrets):
    try:
        users = secrets.get("NESIL_USERS")
    except Exception:
        users = None
    if users is None:
        users = json.loads(os.environ.get("NESIL_USERS_JSON", "{}"))
    if not hasattr(users, "items"):
        raise ValueError("NESIL_USERS must map user names to access codes")
    result = dict(users)
    if any(not isinstance(k, str) or not isinstance(v, str) or len(v) < 16 for k, v in result.items()):
        raise ValueError("Access codes must contain at least 16 characters")
    return result


def authenticate(users, name, code):
    expected = users.get(name)
    if not expected or not hmac.compare_digest(expected.encode(), code.encode()):
        return ""
    return hashlib.sha256((name + "\0" + expected).encode()).hexdigest()


def require_access(st, store):
    users = configured_users(st.secrets)
    if not users:
        return "public"
    active = {hashlib.sha256((name + "\0" + code).encode()).hexdigest() for name, code in users.items()}
    if st.session_state.get("principal") in active:
        return st.session_state.principal
    st.title("🤖 Nesil AI")
    st.caption("Devam etmek için kurum hesabınızla giriş yapın.")
    with st.form("access"):
        name = st.text_input("Kullanıcı adı", max_chars=100)
        code = st.text_input("Erişim kodu", type="password", max_chars=200)
        submit = st.form_submit_button("Giriş yap")
    if submit:
        from usage_limits import UsageLimit
        try:
            store.login_attempt()
            principal = authenticate(users, name, code)
            if principal:
                st.session_state.principal = principal
                st.rerun()
            st.error("Kullanıcı adı veya erişim kodu geçersiz.")
        except UsageLimit as exc:
            st.error(str(exc))
    st.stop()
