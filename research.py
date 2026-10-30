"""Local source ledger. Extracting a citation never verifies its contents."""
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit


def public_url(value):
    """Accept ordinary public HTTPS/HTTP links, without fetching any URL."""
    if not isinstance(value, str) or len(value) > 2048:
        return ""
    if any(ord(c) < 33 for c in value) or "\\" in value:
        return ""
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if parsed.scheme not in ("https", "http") or not host or parsed.username or parsed.password:
            return ""
        if parsed.port not in (None, 80, 443):
            return ""
        host = host.rstrip(".").lower()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".test", ".invalid")):
            return ""
        try:
            if not ipaddress.ip_address(host).is_global:
                return ""
        except ValueError:
            if "." not in host or not re.fullmatch(r"[a-z0-9.-]+", host):
                return ""
            if all(c in "0123456789." for c in host):
                return ""
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
    except ValueError:
        return ""


def research_record(text, requested, recorded_at):
    """Record only what is known. Dates and verification are never inferred."""
    record = {"requested": bool(requested), "status": "not_requested",
              "recorded_at": recorded_at, "sources": []}
    if not requested:
        return record
    text = text[:100000]
    sources, seen = [], set()
    # Markdown titles come from the model too; they are not verified page titles.
    candidates = re.findall(r"\[([^\]\n]{1,300})\]\((https?://[^\s<>]+)\)", text)
    candidates += [("Bağlantı", match.rstrip(".,;:!?)]}"))
                   for match in re.findall(r"https?://[^\s<>]+", text)]
    for title, raw in candidates:
        url = public_url(raw)
        if not url or url in seen:
            continue
        seen.add(url)
        sources.append({"title": title, "url": url, "verified": False,
                        "published_at": None, "data_period": None, "accessed_at": None})
        if len(sources) == 12:
            break
    record["sources"] = sources
    record["status"] = "links_reported" if sources else "no_sources"
    return record


def research_caption(record):
    if not record or not record.get("requested"):
        return "Canlı internet araştırması yapılmadı."
    if record.get("status") == "no_sources":
        return "Araştırma istendi; yanıtta kaynak bağlantısı bulunamadı. Güncel bilgi doğrulanmış sayılmamalı."
    return "Araştırma istendi; aşağıdaki bağlantılar yanıttan çıkarıldı. Sayfa içerikleri bağımsız doğrulanmadı."
