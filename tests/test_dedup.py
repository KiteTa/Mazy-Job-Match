import hashlib
from datetime import datetime, timedelta, timezone

from filters.dedup import (
    canonical_id,
    cleanup,
    composite_key,
    is_seen,
    mark_seen,
    normalize,
)

# ── helpers ────────────────────────────────────────────────────────────────────

def _li(id='4321375715', company='Epic', title='Software Developer'):
    return {'source': 'linkedin', 'id': id, 'company': company, 'title': title}

def _gh(url='https://example.com/job/123', company='Epic', title='Software Developer'):
    return {'source': 'github', 'url': url, 'company': company, 'title': title}

def _empty_seen():
    return {'by_id': {}, 'by_company_title': {}}

def _iso_ago(days: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def _inject_seen(seen, job, days_ago: int):
    """Directly insert an entry with a backdated timestamp."""
    cid = canonical_id(job)
    ck = composite_key(job)
    date_str = _iso_ago(days_ago)
    seen['by_id'][cid] = {'company': job['company'], 'title': job['title'], 'date_seen': date_str}
    seen['by_company_title'][ck] = {'canonical_id': cid, 'date_seen': date_str}


# ── canonical_id ───────────────────────────────────────────────────────────────

def test_canonical_id_linkedin():
    assert canonical_id(_li(id='4321375715')) == 'linkedin:4321375715'

def test_canonical_id_github():
    url = 'https://example.com/job/123'
    expected = 'github:' + hashlib.sha1(url.encode()).hexdigest()[:12]
    result = canonical_id(_gh(url=url))
    assert result == expected
    assert result.startswith('github:')
    assert len(result) == len('github:') + 12


# ── normalize ─────────────────────────────────────────────────────────────────

def test_normalize_basic():
    assert normalize('Software Engineer, New Grad') == 'software engineer new grad'

def test_normalize_dash():
    assert normalize('Software Engineer - New Grad') == 'software engineer new grad'

def test_normalize_comma_equals_dash():
    assert normalize('Software Engineer, New Grad') == normalize('Software Engineer - New Grad')

def test_normalize_preserves_year():
    assert normalize('Software Engineer (New Grad 2026)') == 'software engineer new grad 2026'


# ── mark_seen writes both indices ─────────────────────────────────────────────

def test_mark_seen_writes_both_indices():
    seen = _empty_seen()
    job = _li()
    mark_seen(job, seen)
    assert canonical_id(job) in seen['by_id']
    assert composite_key(job) in seen['by_company_title']


# ── dedup hit by canonical_id ─────────────────────────────────────────────────

def test_dedup_hit_by_canonical_id():
    seen = _empty_seen()
    job = _li(id='4321375715')
    mark_seen(job, seen)
    assert is_seen(job, seen)

    # Same job object a second time → still seen
    job2 = _li(id='4321375715')
    assert is_seen(job2, seen)


# ── dedup hit by company+title cross-source ───────────────────────────────────

def test_dedup_hit_by_company_title_cross_source():
    seen = _empty_seen()
    li_job = _li(company='Stripe', title='Software Engineer')
    gh_job = _gh(url='https://stripe.com/careers/1', company='Stripe', title='Software Engineer')

    mark_seen(li_job, seen)

    # GitHub job has a different canonical_id …
    assert canonical_id(gh_job) not in seen['by_id']
    # … but matches via normalized company+title
    assert is_seen(gh_job, seen)


# ── dedup miss ────────────────────────────────────────────────────────────────

def test_dedup_miss():
    seen = _empty_seen()
    job1 = _li(id='111', company='Google', title='SWE I')
    job2 = _li(id='222', company='Meta',   title='SWE I')

    assert not is_seen(job1, seen)
    assert not is_seen(job2, seen)

    mark_seen(job1, seen)
    mark_seen(job2, seen)

    assert is_seen(job1, seen)
    assert is_seen(job2, seen)


# ── 14-day cleanup ────────────────────────────────────────────────────────────

def test_cleanup_removes_15d_entry():
    seen = _empty_seen()
    job = _li(id='old1', company='OldCo', title='OldJob')
    _inject_seen(seen, job, days_ago=15)

    cleanup(seen, days=14)

    assert canonical_id(job) not in seen['by_id']
    assert composite_key(job) not in seen['by_company_title']

def test_cleanup_keeps_13d_entry():
    seen = _empty_seen()
    job = _li(id='recent1', company='RecentCo', title='RecentJob')
    _inject_seen(seen, job, days_ago=13)

    cleanup(seen, days=14)

    assert canonical_id(job) in seen['by_id']
    assert composite_key(job) in seen['by_company_title']
