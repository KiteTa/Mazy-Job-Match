"""Keyword filter for security clearance and citizenship requirements (pre-Gemini)."""

import re

_REJECT_RE = re.compile(
    r'\btop[\s-]?secret\b'
    r'|\bts[/\s]sci\b'
    r'|\bsecurity\s+clearance\b'
    r'|\bclearance\s+required\b'
    r'|\bactive\s+clearance\b'
    r'|\bmust\s+be\s+(a\s+)?(us|u\.s\.)\s+citizen'
    r'|\b(us|u\.s\.)\s+citizen(ship)?\s+required'
    r'|\bamerican\s+citizen'
    r'|\bonly\s+(us|u\.s\.)\s+citizens?\b',
    re.IGNORECASE,
)


def passes_security(job: dict) -> bool:
    """Return False if description or title contains clearance/citizenship keywords."""
    text = ' '.join(filter(None, [
        job.get('title', ''),
        job.get('description_text') or '',
    ]))
    return not _REJECT_RE.search(text)
