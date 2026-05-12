"""Phase 9 — priority scoring tests."""

import config
from ranking.priority import assign_priority, sort_jobs

_STACK_LEN = len(config.PREFERRED_STACK)


def _job(company='Unknown', has_jd=True, tools=None, applicants=None,
         posted='2026-05-11T00:00:00Z'):
    return {
        'company': company,
        'has_jd': has_jd,
        'applicants_count': applicants,
        'posted_at': posted,
        'keywords': {'tools_and_tech': tools or []},
    }


def _sorted_job(tier, applicants=None, coverage=0.5, posted='2026-05-11T00:00:00Z'):
    return {
        'priority_tier': tier,
        'keyword_coverage': coverage,
        'applicants_count': applicants,
        'posted_at': posted,
    }


# ── tier assignment ───────────────────────────────────────────────────────────

def test_tier_1_big_tech_with_jd():
    j = assign_priority(_job(company='Google', has_jd=True, tools=['Python', 'TypeScript']))
    assert j['priority_tier'] == 1

def test_tier_1_case_insensitive_company():
    j = assign_priority(_job(company='google', has_jd=True, tools=['Python']))
    assert j['priority_tier'] == 1

def test_tier_2_two_or_more_stack_matches():
    j = assign_priority(_job(has_jd=True, tools=['python', 'typescript', 'react']))
    assert j['priority_tier'] == 2

def test_tier_3_has_jd_no_stack_match():
    j = assign_priority(_job(has_jd=True, tools=['Java', 'C++', 'Scala']))
    assert j['priority_tier'] == 3

def test_tier_3_has_jd_one_match():
    j = assign_priority(_job(has_jd=True, tools=['python']))
    assert j['priority_tier'] == 3

def test_tier_4_no_jd_big_tech():
    j = assign_priority(_job(company='Google', has_jd=False))
    assert j['priority_tier'] == 4

def test_tier_4_no_jd_unknown():
    j = assign_priority(_job(has_jd=False))
    assert j['priority_tier'] == 4


# ── coverage ──────────────────────────────────────────────────────────────────

def test_coverage_four_matches():
    j = assign_priority(_job(tools=['python', 'typescript', 'react', 'node']))
    assert abs(j['keyword_coverage'] - 4 / _STACK_LEN) < 0.001

def test_coverage_zero_no_matches():
    j = assign_priority(_job(tools=['Java', 'C++', 'Cobol']))
    assert j['keyword_coverage'] == 0.0

def test_coverage_fields_present():
    j = assign_priority(_job(tools=['python']))
    assert 'keyword_coverage' in j
    assert 'matched_stack_keywords' in j
    assert 'unmatched_stack_keywords' in j

def test_matched_and_unmatched_correct():
    j = assign_priority(_job(tools=['python']))
    assert 'python' in j['matched_stack_keywords']
    assert 'python' not in j['unmatched_stack_keywords']


# ── sort ──────────────────────────────────────────────────────────────────────

def test_sort_by_tier_ascending():
    jobs = [
        _sorted_job(tier=3),
        _sorted_job(tier=1),
        _sorted_job(tier=2),
    ]
    result = sort_jobs(jobs)
    assert [j['priority_tier'] for j in result] == [1, 2, 3]

def test_sort_applicants_asc_within_tier():
    jobs = [
        _sorted_job(tier=2, applicants='50'),
        _sorted_job(tier=2, applicants='10'),
        _sorted_job(tier=2, applicants='200'),
    ]
    result = sort_jobs(jobs)
    assert [int(j['applicants_count']) for j in result] == [10, 50, 200]

def test_sort_none_applicants_first():
    jobs = [
        _sorted_job(tier=2, applicants='100'),
        _sorted_job(tier=2, applicants=None),
    ]
    result = sort_jobs(jobs)
    assert result[0]['applicants_count'] is None

def test_sort_coverage_tiebreak_desc():
    jobs = [
        _sorted_job(tier=2, applicants=10, coverage=0.2),
        _sorted_job(tier=2, applicants=10, coverage=0.8),
    ]
    result = sort_jobs(jobs)
    assert result[0]['keyword_coverage'] == 0.8

def test_sort_posted_at_tiebreak_newest_first():
    jobs = [
        _sorted_job(tier=2, applicants=10, coverage=0.5, posted='2026-05-10T00:00:00Z'),
        _sorted_job(tier=2, applicants=10, coverage=0.5, posted='2026-05-11T00:00:00Z'),
    ]
    result = sort_jobs(jobs)
    assert result[0]['posted_at'] == '2026-05-11T00:00:00Z'
