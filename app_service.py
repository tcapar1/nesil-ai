"""Usage enforcement around every UI model call, including source reviews."""
import logging
import os
from model_client import ModelResult, build_messages, wants_research, InputBudgetError
from usage_limits import UsageLimit


def call_with_limits(provider, store, subject, prompt, mode, history, context, web_enabled, *, api_key, note, model=None):
    provider_options = {"api_key": api_key, "note": note}
    if model is not None:
        provider_options["model"] = model
    if not api_key:
        return provider(prompt, mode, history, context, web_enabled, **provider_options)
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
    except Exception as exc:
        # Keep exception messages out of logs because HTTP libraries can include
        # URLs, request details, or credentials in them.
        logging.getLogger("nesil.usage").error(
            "usage_reservation_failed error_type=%s", type(exc).__name__
        )
        return ModelResult("Kullanım sınırı kaydına erişilemiyor. Yönetici ayarları kontrol etmeli; model isteği gönderilmedi.")
    result = None
    try:
        result = provider(prompt, mode, history, context, web_enabled, **provider_options)
        return result
    except Exception as exc:
        # Provider transports should normally return a ModelResult, but an
        # unexpected exception must not strand the quota reservation. Do not
        # log exception text: HTTP clients can include request details.
        logging.getLogger("nesil.provider").error(
            "provider_unhandled_error error_type=%s", type(exc).__name__
        )
        return ModelResult("Model bağlantısı beklenmedik bir hatayla kesildi. Sorunuz korunuyor; yeniden deneyebilirsiniz.")
    finally:
        try:
            usage = (result.usage or {}).get("total_tokens", 0) if result is not None else 0
            retry_after = result.retry_after if result is not None else 0
            store.finish(reservation, usage, retry_after)
        except Exception:
            logging.getLogger("nesil.usage").error("usage_reconciliation_failed")
