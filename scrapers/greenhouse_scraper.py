import logging
import re
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

_SWE_RE = re.compile(
    r'software\s+engineer'
    r'|software\s+developer'
    r'|\bswe\b'
    r'|back.?end'
    r'|front.?end'
    r'|full.?stack'
    r'|platform\s+engineer'
    r'|infrastructure\s+engineer'
    r'|ml\s+engineer'
    r'|machine\s+learning\s+engineer'
    r'|ai\s+engineer'
    r'|data\s+engineer'
    r'|systems?\s+engineer'
    r'|application\s+engineer'
    r'|\bdeveloper\b'
    r'|\bengineer\b'
    r'|new\s+grad'
    r'|(ai|ml|llm)\s+(engineer|developer)',
    re.IGNORECASE,
)

_TITLE_BLACKLIST_RE = re.compile(
    r'\b(sales|solutions|support|customer|field'
    r'|technical\s+support|implementation|integration|test|qa)\b',
    re.IGNORECASE,
)
_US_RE = re.compile(
    r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|'
    r'MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|'
    r'TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b'
    r'|united\s+states|remote',
    re.IGNORECASE,
)

_CUTOFF_DAYS = 7


def fetch_greenhouse_jobs(companies: list[dict]) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=_CUTOFF_DAYS)
    results = []

    for company in companies:
        name = company['name']
        token = company['token']
        url = f'https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true'
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning('Greenhouse request failed for %s: %s', name, exc)
            continue

        for job in resp.json().get('jobs', []):
            title = job.get('title', '')
            if not _SWE_RE.search(title):
                continue
            if _TITLE_BLACKLIST_RE.search(title):
                continue

            location = (job.get('location') or {}).get('name', '')
            if not _US_RE.search(location):
                continue

            updated_raw = job.get('updated_at', '')
            try:
                updated = datetime.fromisoformat(updated_raw.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue
            if updated < cutoff:
                continue

            apply_url = job.get('absolute_url', '')
            results.append({
                'id': str(job.get('id', '')),
                'title': title,
                'company': name,
                'location': location,
                'locations': [location],
                'url': apply_url,
                'apply_url': apply_url,
                'description_text': job.get('content', ''),
                'published_at': updated_raw,
                'source': 'greenhouse',
            })

    logger.info('Greenhouse: %d jobs after filters', len(results))
    return results