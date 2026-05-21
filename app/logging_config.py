import json
import logging
from datetime import datetime, timezone
from typing import Any

# Compute stdlib LogRecord keys once so we can strip them from extra= kwargs
_STDLIB_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        # Promote any extra= kwargs (e.g. phone_number, event, stage) into the top-level JSON.
        for key, value in record.__dict__.items():
            if key not in _STDLIB_ATTRS and not key.startswith("_"):
                entry[key] = value
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
