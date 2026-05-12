"""Expiry filter — reject LinkedIn jobs where expireAt < now (Phase 4)."""

import time


def passes_expiry(job: dict) -> bool:
    """LinkedIn only. Reject if expireAt (ms) is in the past."""
    if job.get("source", "linkedin") != "linkedin":
        return True
    expire_at = job.get("expire_at")
    if expire_at is None:
        return True
    return int(expire_at) >= _now_ms()


def _now_ms() -> int:
    return int(time.time() * 1000)
