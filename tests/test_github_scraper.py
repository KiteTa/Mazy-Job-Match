"""Phase 5 — GitHub scraper tests."""

import time
from unittest.mock import patch

from scrapers.github_scraper import fetch_github_jobs, _normalise

_NOW = int(time.time())

SAMPLE = {
    'company_name': 'Acme Corp',
    'title': 'Software Engineer, New Grad',
    'date_posted': _NOW - 3600,  # 1 hour ago
    'url': 'https://acme.com/jobs/swe',
    'is_visible': True,
    'active': True,
    'locations': ['New York, NY', 'Remote'],
}


# ── fetch filters ─────────────────────────────────────────────────────────────

def test_fetch_returns_list_of_dicts():
    with patch('scrapers.github_scraper._fetch_listings', return_value=[SAMPLE]):
        jobs = fetch_github_jobs()
    assert isinstance(jobs, list)
    assert len(jobs) == 1
    assert isinstance(jobs[0], dict)


def test_fetch_filters_old_by_date():
    old = dict(SAMPLE, company_name='Old Co', date_posted=_NOW - 50 * 3600)
    new = dict(SAMPLE, company_name='New Co', date_posted=_NOW - 10 * 3600)
    with patch('scrapers.github_scraper._fetch_listings', return_value=[old, new]):
        jobs = fetch_github_jobs(max_age_hours=48)
    assert len(jobs) == 1
    assert jobs[0]['company'] == 'New Co'


def test_fetch_skips_inactive():
    inactive = dict(SAMPLE, company_name='Inactive Co', active=False)
    active = dict(SAMPLE, company_name='Active Co', active=True)
    with patch('scrapers.github_scraper._fetch_listings', return_value=[inactive, active]):
        jobs = fetch_github_jobs()
    companies = [j['company'] for j in jobs]
    assert 'Inactive Co' not in companies
    assert 'Active Co' in companies


def test_fetch_skips_invisible():
    hidden = dict(SAMPLE, company_name='Hidden Co', is_visible=False)
    visible = dict(SAMPLE, company_name='Visible Co', is_visible=True)
    with patch('scrapers.github_scraper._fetch_listings', return_value=[hidden, visible]):
        jobs = fetch_github_jobs()
    companies = [j['company'] for j in jobs]
    assert 'Hidden Co' not in companies
    assert 'Visible Co' in companies


def test_fetch_skips_missing_url():
    no_url = {
        'company_name': 'No URL', 'title': 'SWE',
        'is_visible': True, 'active': True, 'locations': [],
        'date_posted': _NOW - 3600,
    }
    with_url = dict(SAMPLE, company_name='Has URL')
    with patch('scrapers.github_scraper._fetch_listings', return_value=[no_url, with_url]):
        jobs = fetch_github_jobs()
    companies = [j['company'] for j in jobs]
    assert 'No URL' not in companies
    assert 'Has URL' in companies


# ── normalise ─────────────────────────────────────────────────────────────────

def test_normalise_source_is_github():
    assert _normalise(SAMPLE)['source'] == 'github'


def test_normalise_fields_mapped():
    job = _normalise(SAMPLE)
    assert job['company'] == 'Acme Corp'
    assert job['title'] == 'Software Engineer, New Grad'
    assert job['apply_url'] == SAMPLE['url']
    assert job['locations'] == SAMPLE['locations']
    assert job['posted_at'] is not None
    assert job['has_jd'] is False
    assert job['keywords'] is None


def test_normalise_no_date_posted():
    item = {k: v for k, v in SAMPLE.items() if k != 'date_posted'}
    job = _normalise(item)
    assert job['posted_at'] is None
