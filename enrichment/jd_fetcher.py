"""Fetches and extracts JD text from GitHub job apply URLs (Phase 6)."""

import logging

import requests
from bs4 import BeautifulSoup

from config import JD_FETCH_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
}
_MIN_TEXT_LENGTH = 200


def fetch_jd(url: str) -> str | None:
    """Fetch JD text from a URL. Returns None on error, auth wall, or empty page."""
    try:
        resp = requests.get(url, timeout=JD_FETCH_TIMEOUT_SECONDS, headers=_HEADERS)
    except requests.exceptions.Timeout:
        logger.warning('JD fetch timeout: %s', url)
        return None
    except requests.exceptions.RequestException as exc:
        logger.warning('JD fetch error: %s — %s', url, exc)
        return None

    if resp.status_code == 404:
        logger.warning('JD fetch 404: %s', url)
        return None
    if resp.status_code != 200:
        logger.warning('JD fetch non-200 (%d): %s', resp.status_code, url)
        return None

    text = _extract_text(resp.text)
    if len(text) < _MIN_TEXT_LENGTH:
        return None
    return text


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, 'lxml')
    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)
