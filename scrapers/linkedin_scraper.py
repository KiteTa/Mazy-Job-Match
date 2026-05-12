"""Triggers Apify LinkedIn scraper and retrieves results."""

import logging
import os

from apify_client import ApifyClient

from config import LINKEDIN_SEARCH_URLS

_ACTOR_ID = 'hKByXkMQaC5Qt9UMN'

logger = logging.getLogger(__name__)


def fetch_linkedin_jobs(
    token: str | None = None,
    search_urls: list | None = None,
    max_jobs: int = 60,
) -> list:
    """Run Apify LinkedIn scraper for each search URL and return normalised jobs."""
    token = token or os.environ['APIFY_TOKEN']
    search_urls = search_urls or LINKEDIN_SEARCH_URLS
    client = ApifyClient(token)
    all_jobs: list[dict] = []

    for url in search_urls:
        logger.info('Scraping LinkedIn: %s', url)
        run_info = _trigger_run(client, url, max_jobs)
        items = _collect_results(client, run_info['id'])
        for item in items:
            if item.get('repostedJob'):
                continue
            job = _normalise(item)
            if job:
                all_jobs.append(job)

    return all_jobs


def _trigger_run(client: ApifyClient, url: str, max_jobs: int) -> dict:
    run = client.actor(_ACTOR_ID).start(
        run_input={
            'urls': [url],
            'maxJobs': max_jobs,
            'scrapeCompany': True,
        }
    )
    if run is None:
        raise RuntimeError(f'Apify actor start returned None for URL: {url}')
    return run


def _collect_results(client: ApifyClient, run_id: str) -> list:
    run_client = client.run(run_id)
    finished = run_client.wait_for_finish()
    status = (finished or {}).get('status', 'UNKNOWN')
    if status != 'SUCCEEDED':
        raise RuntimeError(f'Apify run {run_id} ended with status: {status}')
    dataset_id = finished['defaultDatasetId']
    return list(client.dataset(dataset_id).iterate_items())


def _normalise(item: dict) -> dict | None:
    job_id = item.get('id')
    if not job_id:
        return None
    return {
        'source': 'linkedin',
        'id': str(job_id),
        'url': None,
        'title': item.get('title') or '',
        'company': item.get('companyName') or '',
        'seniority_level': item.get('seniorityLevel'),
        'industries': item.get('industries'),
        'country': item.get('country'),
        'location': item.get('location'),
        'posted_at': item.get('postedAt'),
        'expire_at': item.get('expireAt'),
        'apply_url': item.get('applyUrl') or item.get('link'),
        'linkedin_url': item.get('link'),
        'description_text': item.get('descriptionText'),
        'applicants_count': item.get('applicantsCount'),
        'reposted_job': item.get('repostedJob', False),
        'employment_type': item.get('employmentType'),
        'workplace_types': item.get('workplaceTypes') or [],
        'work_remote_allowed': item.get('workRemoteAllowed'),
        'company_logo': item.get('companyLogo'),
        'company_address': item.get('companyAddress'),
        'company_description': item.get('companyDescription'),
        'company_employees_count': item.get('companyEmployeesCount'),
        'salary': item.get('salary'),
        'has_jd': bool(item.get('descriptionText')),
        'no_jd': not bool(item.get('descriptionText')),
        'keywords': None,
        'active': True,
        'is_visible': True,
    }
