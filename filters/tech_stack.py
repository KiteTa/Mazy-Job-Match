"""Tech-stack filter — drop pure embedded/hardware jobs (Phase 3)."""

import re

_ALWAYS_PASS = re.compile(
    r'\b(python|javascript|typescript|go|golang|rust|java|kotlin|swift|'
    r'web|backend|api|cloud|aws|gcp|azure|mobile|ios|android|'
    r'ml|machine learning|ai|data|distributed)\b',
    re.IGNORECASE,
)

_REJECT_SIGNALS = re.compile(
    r'\b(embedded|firmware|fpga|vhdl|verilog|rtl|bare.?metal|'
    r'hardware engineer|electrical engineer|circuit design|pcb|'
    r'mechanical engineer|civil engineer|chemical engineer)\b',
    re.IGNORECASE,
)


def passes_tech_stack(job: dict) -> bool:
    """Return False only if the job is purely in a rejected stack with no safe signals."""
    title = job.get("title") or ""
    description = job.get("description_text") or ""
    jd_snippet = description[:500] if description else ""
    text = f"{title} {jd_snippet}"

    if not _REJECT_SIGNALS.search(text):
        return True
    if _ALWAYS_PASS.search(text):
        return True
    return False
