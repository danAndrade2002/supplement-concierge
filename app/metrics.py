import functools

from prometheus_client import Histogram

bot_stage_latency = Histogram(
    "bot_stage_latency_seconds",
    "Processing latency broken down by stage",
    ["stage"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 60.0),
)


def track_latency(stage: str):
    """Decorator that records the wall-clock duration of an async function into bot_stage_latency."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with bot_stage_latency.labels(stage=stage).time():
                return await func(*args, **kwargs)
        return wrapper
    return decorator
