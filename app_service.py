"""Usage enforcement around every UI model call, including source reviews."""
import logging
import os
from model_client import ModelResult, build_messages, wants_research, InputBudgetError
from usage_limits import UsageLimit


def call_with_limits(provider, store, subject, prompt, mode, history, context, web_enabled, *, api_key, note):
    if not api_key:
        return provider(prompt, mode, history, context, web_enabled, api_key=api_key, note=note)
    try:
        messages = build_messages(prompt, mode, history, context, note)
        estimate = sum(len(m["content"].encode("utf-8")) + 32 for m in messages) + 1200
        if wants_research(prompt, web_enabled):
            estimate += 1000
        reservation = store.reserve(subject, estimate,
            daily_requests=min(1000, int(os.environ.get("NESIL_DAILY_REQUESTS", "500"))),
            daily_tokens=min(200000, int(os.environ.get("NESIL_DAILY_TOKENS", "150000"))),
            user_requests=int(os.environ.get("NESIL_USER_DAILY_REQUESTS", "100")))
    except (UsageLimit, InputBudgetError) as exc:
        return ModelResult(str(exc))
    except Exception:
        logging.getLogger("nesil.usage").error("usage_reservation_failed")
        return ModelResult("Kullanım sınırı kaydına erişilemiyor. Yönetici ayarları kontrol etmeli; model isteği gönderilmedi.")
    result = provider(prompt, mode, history, context, web_enabled, api_key=api_key, note=note)
    try:
        store.finish(reservation, (result.usage or {}).get("total_tokens", 0), result.retry_after)
    except Exception:
        logging.getLogger("nesil.usage").error("usage_reconciliation_failed")
    return result
