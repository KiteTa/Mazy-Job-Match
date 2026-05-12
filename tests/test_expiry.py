"""Phase 4 — expiry filter tests."""

import time
from filters.expiry import passes_expiry


def now_ms():
    return int(time.time() * 1000)


def li(expire_at):
    return {"source": "linkedin", "expire_at": expire_at}


def test_expired_reject():
    past = now_ms() - 86_400_000  # 1 day ago
    assert passes_expiry(li(past)) is False

def test_future_pass():
    future = now_ms() + 30 * 86_400_000  # 30 days out
    assert passes_expiry(li(future)) is True

def test_missing_expire_at_pass():
    assert passes_expiry({"source": "linkedin"}) is True

def test_none_expire_at_pass():
    assert passes_expiry(li(None)) is True

def test_github_source_always_pass():
    past = now_ms() - 86_400_000
    assert passes_expiry({"source": "github", "expire_at": past}) is True
