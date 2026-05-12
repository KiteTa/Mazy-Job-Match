"""Visa sponsorship filter — uses Gemini visa_status field (Phase 8)."""

_REJECT_STATUSES = frozenset({
    'requires_us_citizenship',
    'requires_clearance',
    'no_sponsorship',
})


def passes_visa(job: dict) -> bool:
    """Return False if the job's visa_status indicates sponsorship is unavailable."""
    keywords = job.get('keywords') or {}
    status = keywords.get('visa_status', 'not_mentioned')
    return status not in _REJECT_STATUSES
