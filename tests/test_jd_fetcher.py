"""Phase 6 — JD fetcher tests."""

import requests as req
import pytest
from unittest.mock import MagicMock, patch

from enrichment.jd_fetcher import fetch_jd

_LONG_HTML = '<html><body>' + '<p>Job description sentence. ' * 100 + '</p></body></html>'
_SHORT_HTML = '<html><body><p>Please log in.</p></body></html>'


def _resp(status=200, text=''):
    r = MagicMock()
    r.status_code = status
    r.text = text
    return r


def test_plain_html_returns_text_over_200():
    with patch('enrichment.jd_fetcher.requests.get', return_value=_resp(text=_LONG_HTML)):
        result = fetch_jd('https://example.com/job')
    assert result is not None
    assert len(result) > 200


def test_404_returns_none():
    with patch('enrichment.jd_fetcher.requests.get', return_value=_resp(status=404)):
        result = fetch_jd('https://example.com/missing')
    assert result is None


def test_auth_wall_short_page_returns_none():
    with patch('enrichment.jd_fetcher.requests.get', return_value=_resp(text=_SHORT_HTML)):
        result = fetch_jd('https://example.com/login')
    assert result is None


def test_timeout_returns_none():
    with patch('enrichment.jd_fetcher.requests.get', side_effect=req.exceptions.Timeout):
        result = fetch_jd('https://slow.example.com/job')
    assert result is None


def test_non_200_returns_none():
    with patch('enrichment.jd_fetcher.requests.get', return_value=_resp(status=403)):
        result = fetch_jd('https://example.com/forbidden')
    assert result is None


def test_connection_error_returns_none():
    with patch('enrichment.jd_fetcher.requests.get', side_effect=req.exceptions.ConnectionError):
        result = fetch_jd('https://unreachable.example.com/job')
    assert result is None
