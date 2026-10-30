"""Create an unsent plain-text .eml file. No accounts or network access."""
import re
from email.message import EmailMessage
from email.policy import SMTP

MAX_BODY = 30000


def build_draft(recipient, subject, body):
    if any(ord(c) < 32 or ord(c) == 127 for c in recipient + subject):
        raise ValueError("Alıcı ve konu tek satır olmalı; kontrol karakterleri içeremez.")
    recipient, subject = recipient.strip(), subject.strip()
    if not subject or len(subject) > 200:
        raise ValueError("Konu 1–200 karakter olmalı.")
    if not body.strip() or len(body) > MAX_BODY or "\x00" in body:
        raise ValueError("İleti metni boş olamaz; en fazla 30.000 karakter olabilir.")
    if recipient:
        if len(recipient) > 254 or recipient.count("@") != 1:
            raise ValueError("Tek bir geçerli e-posta adresi yazın veya alıcıyı boş bırakın.")
        local, domain = recipient.rsplit("@", 1)
        valid_local = re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+", local)
        valid_domain = re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+", domain)
        if not valid_local or not valid_domain or len(local) > 64 or local.startswith(".") or local.endswith(".") or ".." in local:
            raise ValueError("Alıcı için tek bir standart e-posta adresi kullanın; görünen ad ve çoklu alıcı desteklenmiyor.")
    message = EmailMessage(policy=SMTP)
    message["X-Unsent"] = "1"
    if recipient:
        message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body, subtype="plain", charset="utf-8")
    return message.as_bytes()
