"""Atomic, host-wide usage accounting. Never stores questions or documents."""
import os
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager


class UsageLimit(Exception):
    pass


class UsageStore:
    def __init__(self, path=None):
        self.path = str(path or os.environ.get("NESIL_USAGE_DB", ".nesil-ai/usage.sqlite3"))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS usage(day TEXT, subject TEXT, requests INTEGER, tokens INTEGER, PRIMARY KEY(day, subject))")
            db.execute("CREATE TABLE IF NOT EXISTS cooldown(subject TEXT PRIMARY KEY, until REAL)")
            db.execute("CREATE TABLE IF NOT EXISTS minute_usage(at REAL, tokens INTEGER)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, subject, estimated_tokens, daily_requests=500, daily_tokens=150_000,
                user_requests=100, now=None, minute_requests=20, minute_tokens=7500):
        now = time.time() if now is None else now
        day = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cooldown = db.execute("SELECT until FROM cooldown WHERE subject='global'").fetchone()
            if cooldown and cooldown[0] > now:
                raise UsageLimit(f"Sağlayıcı bekleme süresi devam ediyor. Yaklaşık {int(cooldown[0] - now) + 1} saniye sonra deneyin.")
            db.execute("DELETE FROM minute_usage WHERE at<=?", (now - 60,))
            count, tokens = db.execute("SELECT count(*),coalesce(sum(tokens),0) FROM minute_usage").fetchone()
            if estimated_tokens > minute_tokens:
                raise UsageLimit("Bu istek ücretsiz dakika kotası için çok büyük. Soruyu veya sohbet notunu kısaltın, dosya bağlamını azaltın.")
            if count >= minute_requests or tokens + estimated_tokens > minute_tokens:
                raise UsageLimit("Ortak ücretsiz dakika kotası doldu. Yaklaşık bir dakika sonra yeniden deneyin; sorunuz korunuyor.")
            for key, cap in (("global", daily_requests), ("user:" + subject, user_requests)):
                row = db.execute("SELECT requests,tokens FROM usage WHERE day=? AND subject=?", (day, key)).fetchone() or (0, 0)
                if row[0] >= cap or (key == "global" and row[1] + estimated_tokens > daily_tokens):
                    raise UsageLimit("Günlük kullanım sınırına ulaşıldı. Sınırlar UTC gün başlangıcında yenilenir; yönetici sınırları değiştirebilir.")
            for key in ("global", "user:" + subject):
                db.execute("INSERT INTO usage VALUES(?,?,1,?) ON CONFLICT(day,subject) DO UPDATE SET requests=requests+1,tokens=tokens+excluded.tokens", (day, key, estimated_tokens))
            db.execute("INSERT INTO minute_usage VALUES(?,?)", (now, estimated_tokens))
            db.execute("DELETE FROM usage WHERE day < date(?, '-7 days')", (day,))
        return day, subject, estimated_tokens

    def finish(self, reservation, actual_tokens=0, retry_after=0):
        day, subject, reserved = reservation
        # Keep the reservation for failures/absent usage: they may still cost tokens.
        actual = actual_tokens if isinstance(actual_tokens, int) and actual_tokens > 0 else reserved
        with self.connect() as db:
            for key in ("global", "user:" + subject):
                db.execute("UPDATE usage SET tokens=tokens+? WHERE day=? AND subject=?", (actual - reserved, day, key))
            if retry_after:
                db.execute("INSERT INTO cooldown VALUES('global',?) ON CONFLICT(subject) DO UPDATE SET until=max(until,excluded.until)", (time.time() + retry_after,))

    def login_attempt(self, now=None):
        """Host-wide login throttle survives browser/session resets."""
        now = time.time() if now is None else now
        bucket = "login:" + str(int(now // 300))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT requests FROM usage WHERE day=? AND subject='login'", (bucket,)).fetchone()
            if count and count[0] >= 20:
                raise UsageLimit("Çok fazla giriş denemesi. Beş dakika sonra yeniden deneyin.")
            db.execute("INSERT INTO usage VALUES(?,'login',1,0) ON CONFLICT(day,subject) DO UPDATE SET requests=requests+1", (bucket,))
            db.execute("DELETE FROM usage WHERE subject='login' AND day<>?", (bucket,))
