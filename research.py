"""Local source ledger. Extracting a citation never verifies its contents."""
import ipaddress
import json
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
    if any(source.get("content_status") == "retrieved" for source in record.get("sources", [])):
        return "Bazı kaynak sayfalarından metin alındı. Yanıttaki iddiaların doğruluğu ve verinin en güncel olduğu ayrıca doğrulanmadı."
    return "Araştırma istendi; aşağıdaki bağlantılar yanıttan veya sağlayıcı kaydından alındı. Sayfa içerikleri bağımsız doğrulanmadı."


def enrich_sources(record, executed_tools, annotations):
    """Consume explicit URL metadata only. Never guess citation IDs from array order.

    Groq responses may omit tool metadata. Unknown schemas leave citations unresolved.
    Provider snippets are recorded as evidence, never as independently verified facts.
    """
    by_url = {s["url"]: s for s in record["sources"]}
    remaining = 500

    def walk(node, depth=0):
        nonlocal remaining
        if remaining <= 0 or depth > 8:
            return
        remaining -= 1
        if isinstance(node, str):
            if len(node) <= 100000:
                try:
                    walk(json.loads(node), depth + 1)
                except (ValueError, TypeError):
                    pass
            return
        if isinstance(node, list):
            for item in node[:100]:
                walk(item, depth + 1)
        elif isinstance(node, dict):
            url = public_url(node.get("url") or node.get("uri"))
            if url and (url in by_url or len(by_url) < 12):
                source = by_url.setdefault(url, {"title": str(node.get("title") or "Kaynak")[:300], "url": url,
                    "verified": False, "published_at": None, "data_period": None, "accessed_at": None})
                source["origin"] = "provider_metadata"
                for key in ("citation_id", "reference_id", "id"):
                    value = node.get(key)
                    if isinstance(value, (str, int)) and re.fullmatch(r"[\w-]{1,80}", str(value)):
                        source.setdefault("citation_ids", [])
                        if str(value) not in source["citation_ids"]:
                            source["citation_ids"].append(str(value))
                excerpt = node.get("snippet") or node.get("text")
                if isinstance(excerpt, str):
                    source["provider_excerpt"] = excerpt[:2000]
            for value in node.values():
                if isinstance(value, (list, dict, str)):
                    walk(value, depth + 1)
    walk(executed_tools)
    walk(annotations)
    record["sources"] = list(by_url.values())
    record["status"] = "links_reported" if by_url else "no_sources"
    record["tool_metadata_present"] = bool(executed_tools)


def render_citations(answer, record):
    mapping = {}
    for source in record["sources"]:
        for citation_id in source.get("citation_ids", []):
            # Ambiguous IDs must not point to an arbitrary source.
            mapping[citation_id] = source["url"] if citation_id not in mapping else None
    unresolved = 0

    def replace(match):
        nonlocal unresolved
        url = mapping.get(match.group(1))
        if url:
            return f"[Kaynak]({url})"
        unresolved += 1
        return " (kaynak bağlantısı eşleştirilemedi)"
    answer = re.sub(r"[【〖]([^†】〗]+)†[^】〗]*[】〗]", replace, answer)
    record["unresolved_citations"] = unresolved
    return answer
