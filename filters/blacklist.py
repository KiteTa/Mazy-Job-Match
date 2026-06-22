"""Blacklist filter — reject jobs from blacklisted companies."""

import re


def _norm(s: str) -> str:
    return re.sub(r'\s+', ' ', s.lower().strip())


def build_blocked_set(blacklist: list) -> frozenset:
    return frozenset(_norm(entry['company']) for entry in blacklist)


def passes_blacklist(job: dict, blocked: frozenset) -> bool:
    """Return False if job's company matches any blacklisted company name."""
    return _norm(job.get('company') or '') not in blocked
