"""Fetches new-grad listings from SimplifyJobs/New-Grad-Positions."""

import datetime
import logging
import time

import requests

from config import DATE_FILTER_HOURS

_LISTINGS_URL = (
    'https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions'
    '/dev/.github/scripts/listings.json'
)

logger = logging.getLogger(__name__)


def fetch_github_jobs(max_age_hours: int = DATE_FILTER_HOURS) -> list:
    """Fetch and normalise new-grad listings from SimplifyJobs GitHub repo."""
    raw = _fetch_listings()
    cutoff = time.time() - max_age_hours * 3600
    jobs = []
    for item in raw:
        if not item.get('active', True):
            continue
        if not item.get('is_visible', True):
            continue
        url = item.get('url')
        if not url:
            logger.warning('GitHub listing missing url, skipping: %s', item.get('company_name'))
            continue
        posted = item.get('date_posted')
        if posted is not None and float(posted) < cutoff:
            continue
        jobs.append(_normalise(item))
    return jobs


def _fetch_listings() -> list:
    resp = requests.get(_LISTINGS_URL, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _normalise(item: dict) -> dict:
    posted_ts = item.get('date_posted')
    posted_iso = _ts_to_iso(float(posted_ts)) if posted_ts is not None else None
    url = item['url']
    return {
        'source': 'github',
        'id': None,
        'url': url,
        'company': item.get('company_name') or '',
        'title': item.get('title') or '',
        'posted_at': posted_iso,
        'locations': item.get('locations') or [],
        'active': item.get('active', True),
        'is_visible': item.get('is_visible', True),
        'description_text': None,
        'has_jd': False,
        'no_jd': False,
        'keywords': None,
        'apply_url': url,
        'linkedin_url': None,
        'seniority_level': None,
        'industries': None,
        'employment_type': None,
        'workplace_types': [],
        'work_remote_allowed': None,
        'applicants_count': None,
        'salary': None,
        'expire_at': None,
        'country': None,
        'company_logo': None,
        'company_address': None,
        'company_description': None,
        'company_employees_count': None,
    }


def _ts_to_iso(ts: float) -> str:
    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
