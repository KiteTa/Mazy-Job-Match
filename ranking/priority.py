"""Priority tier assignment and sort-key computation (Phase 9)."""

from functools import cmp_to_key

import config


def assign_priority(job: dict) -> dict:
    """Add priority_tier, keyword_coverage, matched/unmatched_stack_keywords to job in place."""
    keywords = job.get('keywords') or {}
    tools = {t.lower() for t in (keywords.get('tools_and_tech') or [])}
    stack = [s.lower() for s in config.PREFERRED_STACK]

    matched = [s for s in stack if s in tools]
    unmatched = [s for s in stack if s not in tools]
    coverage = len(matched) / len(stack) if stack else 0.0

    has_jd = job.get('has_jd', False)
    company = (job.get('company') or '').strip().lower()
    is_big_tech = any(name.lower() == company for name in config.BIG_TECH_COMPANIES)

    if has_jd and is_big_tech:
        tier = 1
    elif has_jd and len(matched) >= 2:
        tier = 2
    elif has_jd:
        tier = 3
    else:
        tier = 4

    job['priority_tier'] = tier
    job['keyword_coverage'] = round(coverage, 4)
    job['matched_stack_keywords'] = matched
    job['unmatched_stack_keywords'] = unmatched
    return job


def sort_jobs(jobs: list) -> list:
    """Sort by: tier ASC → applicants ASC (None=0) → coverage DESC → posted_at DESC."""
    return sorted(jobs, key=cmp_to_key(_compare))


def _compare(a: dict, b: dict) -> int:
    # tier ASC
    if a['priority_tier'] != b['priority_tier']:
        return a['priority_tier'] - b['priority_tier']
    # applicants ASC (None treated as 0, sorted to front)
    a_app = _parse_applicants(a.get('applicants_count'))
    b_app = _parse_applicants(b.get('applicants_count'))
    if a_app != b_app:
        return a_app - b_app
    # coverage DESC
    a_cov = a.get('keyword_coverage', 0.0)
    b_cov = b.get('keyword_coverage', 0.0)
    if a_cov != b_cov:
        return -1 if a_cov > b_cov else 1
    # posted_at DESC (ISO string, lexicographic order works)
    a_p = a.get('posted_at') or ''
    b_p = b.get('posted_at') or ''
    return -1 if a_p > b_p else (1 if a_p < b_p else 0)


def _parse_applicants(val) -> int:
    if val is None:
        return 0
    if isinstance(val, int):
        return val
    try:
        return int(str(val).replace(',', '').strip().split()[0])
    except (ValueError, IndexError):
        return 0
