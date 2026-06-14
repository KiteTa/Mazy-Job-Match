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

_CUTOFF_DAYS = 7


def scrape_ashby(companies: list[dict]) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=_CUTOFF_DAYS)
    results = []

    for company in companies:
        name = company['name']
        token = company['token']
        url = f'https://api.ashbyhq.com/posting-api/job-board/{token}'
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning('Ashby request failed for %s: %s', name, exc)
            continue

        for posting in resp.json().get('jobs', []):
            title = posting.get('title', '')
            if not _SWE_RE.search(title):
                continue
            if _TITLE_BLACKLIST_RE.search(title):
                continue

            location = posting.get('location', '') or ''
            country = (posting.get('address') or {}).get('postalAddress', {}).get('addressCountry', '')
            is_remote = posting.get('isRemote', False)
            if country.lower() != 'united states' and not is_remote:
                continue

            published_raw = posting.get('publishedAt', '')
            try:
                published = datetime.fromisoformat(published_raw.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue
            if published < cutoff:
                continue

            apply_url = posting.get('jobUrl', '')
            location_tag = 'Remote' if is_remote else 'United States'
            results.append({
                'id': posting.get('id', ''),
                'title': title,
                'company': name,
                'location': location,
                'locations': [location_tag],
                'url': apply_url,
                'apply_url': apply_url,
                'description_text': posting.get('descriptionPlain', '') or posting.get('description', ''),
                'published_at': published_raw,
                'source': 'ashby',
            })

    logger.info('Ashby: %d jobs after filters', len(results))
    return results
