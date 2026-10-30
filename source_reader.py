"""Opt-in, bounded HTTPS reads from a limited primary-source allowlist.

Page retrieval is not claim verification. Never forward extracted instructions
to the model or execute them. No provider keys, cookies, proxies or redirects.
"""
import http.client
import ipaddress
import re
import socket
import ssl
import time
import os
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

from research import public_url

MAX_BYTES = 512 * 1024
SOCKET_TIMEOUT = 3
READ_BUDGET = 5
PRIMARY_HOSTS = frozenset({"who.int", "www.who.int", "un.org", "www.un.org",
    "oecd.org", "www.oecd.org", "worldbank.org", "www.worldbank.org",
    "imf.org", "www.imf.org", "ec.europa.eu", "ecb.europa.eu", "www.ecb.europa.eu",
    "docs.python.org", "docs.streamlit.io", "console.groq.com"})


class SourceError(Exception):
    pass


def allowed_target(url):
    clean = public_url(url)
    if not clean:
        raise SourceError("blocked_url")
    parsed = urlsplit(clean)
    host = parsed.hostname.rstrip(".").lower()
    if parsed.scheme != "https" or parsed.port not in (None, 443):
        raise SourceError("https_only")
    extra_hosts = {h.strip().lower() for h in os.environ.get("NESIL_SOURCE_HOSTS", "").split(",") if h.strip()}
    if host not in PRIMARY_HOSTS and host not in extra_hosts and not host.endswith(".gov.tr"):
        raise SourceError("not_allowed")
    # HTTP request targets must be ASCII; encode unicode URLs at their source.
    target = (parsed.path or "/") + ("?" + parsed.query if parsed.query else "")
    if not target.isascii():
        raise SourceError("blocked_url")
    return clean, host, target


def resolve_public(host, resolver=None):
    answers = (resolver or socket.getaddrinfo)(host, 443, type=socket.SOCK_STREAM)
    candidates = []
    for family, _, _, _, address in answers:
        if family not in (socket.AF_INET, socket.AF_INET6):
            raise SourceError("blocked_address")
        ip = ipaddress.ip_address(address[0])
        # Be conservative across supported Python versions' IP classifications.
        if not ip.is_global or ip.is_multicast or ip.is_reserved:
            raise SourceError("blocked_address")
        if ip.version == 4 and (ip in ipaddress.ip_network("192.0.0.0/24") or ip in ipaddress.ip_network("192.88.99.0/24")):
            raise SourceError("blocked_address")
        if ip.version == 6 and (ip not in ipaddress.ip_network("2000::/3") or ip.sixtofour or ip.teredo):
            raise SourceError("blocked_address")
        if (family == socket.AF_INET) != (ip.version == 4):
            raise SourceError("blocked_address")
        candidates.append((family, str(ip)))
    if not candidates:
        raise SourceError("dns_failed")
    # All answers must be public; connect to a validated numeric address once.
    return sorted(candidates, key=lambda item: item[0] != socket.AF_INET)[0]


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, address):
        context = ssl.create_default_context()
        context.set_alpn_protocols(["http/1.1"])
        super().__init__(host, 443, timeout=SOCKET_TIMEOUT, context=context)
        self.address = address

    def connect(self):
        family, ip = self.address
        raw = socket.socket(family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        raw.settimeout(self.timeout)
        try:
            raw.connect((ip, 443) if family == socket.AF_INET else (ip, 443, 0, 0))
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def read_page(host, address, target):
    connection = PinnedHTTPSConnection(host, address)
    response = None
    try:
        connection.request("GET", target, headers={"User-Agent": "NesilAI-SourceCheck/1.0",
            "Accept": "text/html,application/xhtml+xml,text/plain", "Accept-Encoding": "identity"})
        response = connection.getresponse()
        if 300 <= response.status < 400:
            raise SourceError("redirect_blocked")
        if response.status != 200:
            raise SourceError("http_error")
        media = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
        if media not in ("text/html", "application/xhtml+xml", "text/plain"):
            raise SourceError("unsupported_type")
        if response.getheader("Content-Encoding", "identity").lower() not in ("", "identity"):
            raise SourceError("unsupported_encoding")
        length = response.getheader("Content-Length")
        if length is not None and (not length.isdigit() or int(length) > MAX_BYTES):
            raise SourceError("too_large")
        chunks, size = [], 0
        deadline = time.monotonic() + READ_BUDGET
        while True:
            if time.monotonic() >= deadline:
                raise SourceError("timeout")
            chunk = response.read1(min(16384, MAX_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > MAX_BYTES:
                raise SourceError("too_large")
        return b"".join(chunks), response.getheader("Content-Type", ""), media
    finally:
        if response is not None:
            response.close()
        connection.close()


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.in_title = False
        self.title = []
        self.text = []
        self.text_chars = 0
        self.dates = set()
        self.periods = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style", "noscript", "template"):
            self.skip += 1
        if self.skip:
            return
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            value = (attrs.get("content") or "").strip()
            if key in ("article:published_time", "datepublished", "dc.date.issued", "dcterms.issued"):
                self.add_date(value)
            if key in ("temporalcoverage", "dc.coverage.temporal", "dcterms.temporal") and value:
                self.periods.add(value[:120])
        if tag == "time" and "pubdate" in attrs:
            self.add_date(attrs.get("datetime") or "")

    def add_date(self, value):
        if len(value) > 40 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ][0-9:.+Z-]+)?", value):
            return
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            self.dates.add(value)
        except ValueError:
            pass

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template") and self.skip:
            self.skip -= 1
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.skip:
            return
        text = " ".join(data.split())
        if text and self.in_title and sum(map(len, self.title)) < 500:
            self.title.append(text[:500])
        elif text and self.text_chars < 12000:
            text = text[:12000 - self.text_chars]
            self.text.append(text)
            self.text_chars += len(text)


def check_source(url, *, resolver=None, transport=None, question=""):
    result = {"content_status": "failed", "verified": False, "accessed_at": None,
              "published_at": None, "data_period": None, "source_title": None,
              "excerpt": "", "date_conflict": False, "retrieved_url": None}
    try:
        clean, host, target = allowed_target(url)
        address = resolve_public(host, resolver)
        raw, content_type, media = (transport or read_page)(host, address, target)
        if media not in ("text/html", "application/xhtml+xml", "text/plain"):
            raise SourceError("unsupported_type")
        if len(raw) > MAX_BYTES:
            raise SourceError("too_large")
        charset_match = re.search(r"charset\s*=\s*[\"']?([A-Za-z0-9_-]+)", content_type, re.I)
        charset = charset_match.group(1) if charset_match else "utf-8"
        if charset.lower() not in ("utf-8", "utf8", "iso-8859-9", "windows-1254", "iso-8859-1", "windows-1252", "us-ascii"):
            raise SourceError("unsupported_encoding")
        text = raw.decode(charset, errors="strict")
        if media == "text/plain":
            excerpt = text[:1200].strip()
        else:
            parser = PageParser()
            parser.feed(text)
            body = " ".join(parser.text)
            from file_reader import document_chunks, search_terms, normalize
            terms = search_terms(question)
            blocks = document_chunks(body)
            excerpt = max(blocks, key=lambda b: sum(t in normalize(b) for t in terms), default="")[:1200] if terms else body[:1200]
            result["source_title"] = " ".join(parser.title)[:500] or None
            if len(parser.dates) == 1:
                result["published_at"] = next(iter(parser.dates))
            result["date_conflict"] = len(parser.dates) > 1
            if len(parser.periods) == 1:
                result["data_period"] = next(iter(parser.periods))
        if not excerpt:
            raise SourceError("no_text")
        result.update(content_status="retrieved", accessed_at=datetime.now(timezone.utc).isoformat(),
                      excerpt=excerpt, retrieved_url=clean)
    except SourceError as exc:
        result["content_status"] = str(exc)
    except (TimeoutError, socket.timeout):
        result["content_status"] = "timeout"
    except Exception:
        result["content_status"] = "unavailable"
    if result["content_status"] != "retrieved":
        result.update(published_at=None, data_period=None, source_title=None, date_conflict=False)
    return result


STATUS_LABELS = {
    "retrieved": "Sayfadan metin alındı; yanıttaki iddialar doğrulanmadı.",
    "not_allowed": "Bu alan adı kaynak kontrol listesinde değil.",
    "blocked_url": "Bağlantı kaynak kontrolü için uygun değil.",
    "https_only": "Kaynak kontrolü yalnızca standart HTTPS bağlantılarını destekler.",
    "blocked_address": "Adres güvenlik kontrolünden geçmedi.",
    "redirect_blocked": "Sayfa yönlendirme döndürdü; yönlendirme izlenmedi.",
    "too_large": "Sayfa boyut sınırını aşıyor.",
    "unsupported_type": "Bu içerik türü desteklenmiyor; HTML veya düz metin gerekir.",
    "unsupported_encoding": "Sayfanın kodlaması veya sıkıştırması desteklenmiyor.",
    "http_error": "Kaynak sayfası başarılı yanıt vermedi.",
    "no_text": "Sayfadan okunabilir metin alınamadı.",
    "timeout": "Kaynak sayfası zamanında yanıt vermedi.",
    "dns_failed": "Kaynak adresi çözümlenemedi.",
    "unavailable": "Kaynağa erişilemedi; içerik doğrulanmadı.",
    "not_checked": "Bu kaynak henüz kontrol edilmedi.",
}
