"""3-layer seniority filter (Phase 2)."""

import re

_L1_PASS = {"entry level", "associate"}
_L1_REJECT = {"mid-senior level", "director", "executive", "internship"}

_L2_REJECT = re.compile(
    r'\b(senior|staff|principal|lead|manager|director|'
    r'head of|vp|distinguished|'
    r'iii|iv|v|'
    r'l5|l6|l7|e5|e6|e7)\b'
    r'|\bsr\.',
    re.IGNORECASE,
)
_L2_PASS = re.compile(
    r'\b(junior|jr\.|new grad|new graduate|entry.?level|associate|'
    r'\bi\b|\bii\b|'
    r'l3|l4|e3|e4|sde i|sde ii|swe i|'
    r'early career|rotational|university grad|campus hire)\b',
    re.IGNORECASE,
)


def passes_seniority(job: dict) -> bool:
    """Return True if job passes the 3-layer seniority filter."""
    # Layer 1 — LinkedIn seniorityLevel
    level = (job.get("seniority_level") or "").strip().lower()
    if level in _L1_PASS:
        return True
    if level in _L1_REJECT:
        return False

    # Layer 2 — title keyword
    title = job.get("title") or ""
    if _L2_REJECT.search(title):
        return False
    if _L2_PASS.search(title):
        return True

    # Layer 3 — Gemini yoe_required
    yoe = (job.get("keywords") or {}).get("yoe_required") or "not specified"
    return _yoe_passes(yoe)


def _yoe_passes(yoe: str) -> bool:
    """Parse yoe string; reject if min YOE >= 3."""
    yoe = yoe.lower().strip()
    if yoe in ("not specified", "", "n/a"):
        return True
    nums = [int(n) for n in re.findall(r'\d+', yoe)]
    if not nums:
        return True
    return min(nums) < 3
