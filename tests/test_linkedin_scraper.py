"""Phase 5 — LinkedIn scraper tests."""

import pytest
from unittest.mock import MagicMock, patch

from scrapers.linkedin_scraper import _normalise, _trigger_run, fetch_linkedin_jobs

SAMPLE_ITEM = {
    'id': '4321375715',
    'title': 'Software Developer (Entry Level)',
    'companyName': 'Epic',
    'seniorityLevel': 'Entry level',
    'industries': 'Software Development',
    'country': 'US',
    'location': 'Verona, WI',
    'link': 'https://www.linkedin.com/jobs/view/4321375715',
    'applyUrl': 'https://epic.avature.net/apply',
    'descriptionText': 'Join our team and build great things.',
    'postedAt': '2026-05-11T18:23:28.000Z',
    'expireAt': 9_999_999_999_000,
    'applicantsCount': '57',
    'repostedJob': False,
    'employmentType': 'Full-time',
    'workplaceTypes': ['On-site'],
    'workRemoteAllowed': False,
    'companyLogo': 'https://media.licdn.com/logo.jpg',
    'companyAddress': {'city': 'Verona', 'region': 'WI', 'country': 'US'},
    'companyDescription': 'Epic is a healthcare software company.',
    'companyEmployeesCount': 17246,
    'salary': None,
}


def _make_client(items=None, run_id='run_abc', dataset_id='ds_xyz', fail=False):
    client = MagicMock()
    if fail:
        client.actor.return_value.start.side_effect = Exception('Invalid token')
        return client
    client.actor.return_value.start.return_value = {
        'id': run_id,
        'defaultDatasetId': dataset_id,
        'status': 'RUNNING',
    }
    client.run.return_value.wait_for_finish.return_value = {
        'id': run_id,
        'defaultDatasetId': dataset_id,
        'status': 'SUCCEEDED',
    }
    client.dataset.return_value.iterate_items.return_value = iter(items or [])
    return client


# ── trigger ───────────────────────────────────────────────────────────────────

def test_trigger_returns_run_id():
    client = _make_client()
    run = _trigger_run(client, 'https://linkedin.com/jobs/search', max_jobs=10)
    assert run['id'] == 'run_abc'
    client.actor.return_value.start.assert_called_once()


# ── poll + collect ────────────────────────────────────────────────────────────

def test_collect_returns_normalised_jobs():
    client = _make_client(items=[SAMPLE_ITEM])
    with patch('scrapers.linkedin_scraper.ApifyClient', return_value=client):
        jobs = fetch_linkedin_jobs(token='fake', search_urls=['https://linkedin.com/test'], max_jobs=5)
    assert len(jobs) == 1
    assert jobs[0]['id'] == '4321375715'


# ── parse all fields ──────────────────────────────────────────────────────────

def test_normalise_all_fields():
    job = _normalise(SAMPLE_ITEM)
    assert job['source'] == 'linkedin'
    assert job['id'] == '4321375715'
    assert job['title'] == 'Software Developer (Entry Level)'
    assert job['company'] == 'Epic'
    assert job['seniority_level'] == 'Entry level'
    assert job['industries'] == 'Software Development'
    assert job['country'] == 'US'
    assert job['location'] == 'Verona, WI'
    assert job['apply_url'] == 'https://epic.avature.net/apply'
    assert job['linkedin_url'] == 'https://www.linkedin.com/jobs/view/4321375715'
    assert job['description_text'] == 'Join our team and build great things.'
    assert job['posted_at'] == '2026-05-11T18:23:28.000Z'
    assert job['expire_at'] == 9_999_999_999_000
    assert job['applicants_count'] == '57'
    assert job['employment_type'] == 'Full-time'
    assert job['workplace_types'] == ['On-site']
    assert job['work_remote_allowed'] is False
    assert job['company_logo'] == 'https://media.licdn.com/logo.jpg'
    assert job['company_description'] == 'Epic is a healthcare software company.'
    assert job['company_employees_count'] == 17246
    assert job['has_jd'] is True


def test_normalise_apply_url_fallback_to_link():
    item = dict(SAMPLE_ITEM, applyUrl=None)
    job = _normalise(item)
    assert job['apply_url'] == SAMPLE_ITEM['link']


def test_normalise_no_id_returns_none():
    item = dict(SAMPLE_ITEM, id=None)
    assert _normalise(item) is None


# ── repost filter ─────────────────────────────────────────────────────────────

def test_repost_filtered_out():
    reposted = dict(SAMPLE_ITEM, repostedJob=True)
    client = _make_client(items=[reposted])
    with patch('scrapers.linkedin_scraper.ApifyClient', return_value=client):
        jobs = fetch_linkedin_jobs(token='fake', search_urls=['https://linkedin.com/test'])
    assert len(jobs) == 0


# ── multiple URLs merged ──────────────────────────────────────────────────────

def test_multiple_urls_results_merged():
    item1 = dict(SAMPLE_ITEM, id='111')
    item2 = dict(SAMPLE_ITEM, id='222')

    call_count = [0]

    def side_effect():
        idx = call_count[0]
        call_count[0] += 1
        return iter([item1] if idx == 0 else [item2])

    client = _make_client()
    client.dataset.return_value.iterate_items.side_effect = lambda: side_effect()

    with patch('scrapers.linkedin_scraper.ApifyClient', return_value=client):
        jobs = fetch_linkedin_jobs(token='fake', search_urls=['https://url1', 'https://url2'])

    assert len(jobs) == 2
    assert {j['id'] for j in jobs} == {'111', '222'}


# ── API error ─────────────────────────────────────────────────────────────────

def test_api_error_raises_exception():
    client = _make_client(fail=True)
    with patch('scrapers.linkedin_scraper.ApifyClient', return_value=client):
        with pytest.raises(Exception):
            fetch_linkedin_jobs(token='bad', search_urls=['https://linkedin.com/test'])
