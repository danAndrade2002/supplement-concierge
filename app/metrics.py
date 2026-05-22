import functools
import logging
import time

from prometheus_client import Histogram

logger = logging.getLogger(__name__)

bot_stage_latency = Histogram(
    "bot_stage_latency_seconds",
    "Processing latency broken down by stage",
    ["stage"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 60.0),
)


def track_latency(stage: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed_ms = round((time.perf_counter() - t0) * 1000)
                bot_stage_latency.labels(stage=stage).observe(elapsed_ms / 1000)
                logger.info("%s completed in %dms", stage, elapsed_ms, extra={"stage": stage, "latency_ms": elapsed_ms})
        return wrapper
    return decorator
