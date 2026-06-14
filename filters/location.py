"""Location / country filter (Phase 4)."""

import re

_US_STATE_ABBR = re.compile(
    r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|'
    r'MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|'
    r'TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b'
)

_US_COUNTRY_WORDS = re.compile(
    r'\b(united states|usa|u\.s\.a|u\.s\.|america|us)\b', re.IGNORECASE
)

_REMOTE_WORDS = re.compile(r'\bremote\b', re.IGNORECASE)


def passes_location(job: dict) -> bool:
    locations = job.get("locations") or []
    return any(_is_us_or_remote(loc) for loc in locations)


def _is_us_or_remote(loc: str) -> bool:
    if _REMOTE_WORDS.search(loc):
        return True
    if _US_COUNTRY_WORDS.search(loc):
        return True
    if _US_STATE_ABBR.search(loc):
        return True
    return False
