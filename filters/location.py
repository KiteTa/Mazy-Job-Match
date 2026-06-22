"""Location / country filter (Phase 4)."""

import re

_US_STATE_ABBR = re.compile(
    r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|'
    r'MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|'
    r'TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b'
)

_US_STATE_NAMES = re.compile(
    r'\b(alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|'
    r'florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|'
    r'maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|'
    r'nebraska|nevada|new\s+hampshire|new\s+jersey|new\s+mexico|new\s+york|'
    r'north\s+carolina|north\s+dakota|ohio|oklahoma|oregon|pennsylvania|'
    r'rhode\s+island|south\s+carolina|south\s+dakota|tennessee|texas|utah|vermont|'
    r'west\s+virginia|virginia|washington|wisconsin|wyoming|district\s+of\s+columbia)\b',
    re.IGNORECASE,
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
    if _US_STATE_NAMES.search(loc):
        return True
    return False
