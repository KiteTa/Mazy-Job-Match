"""Blacklist filter — reject jobs from blacklisted companies."""

import re


def _norm(s: str) -> str:
    return re.sub(r'\s+', ' ', s.lower().strip())


def passes_blacklist(job: dict, blacklist: list) -> bool:
    """Return False if job's company matches any blacklisted company name."""
    company = _norm(job.get('company') or '')
    blocked = {_norm(entry['company']) for entry in blacklist}
    return company not in blocked
