"""Industries filter — reject Staffing and Recruiting (Phase 4)."""


def passes_industries(job: dict) -> bool:
    """LinkedIn only. Reject exact match on 'Staffing and Recruiting'."""
    if job.get("source", "linkedin") != "linkedin":
        return True
    return job.get("industries", "") != "Staffing and Recruiting"
