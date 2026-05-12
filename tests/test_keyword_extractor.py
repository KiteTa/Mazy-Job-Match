"""Phase 7 — Gemini keyword extractor tests."""

import json
import pytest
from unittest.mock import MagicMock, patch

from enrichment.keyword_extractor import extract_keywords

_KW = {
    'required_skills': ['Python', 'SQL'],
    'preferred_skills': ['TypeScript'],
    'tools_and_tech': ['Django', 'Postgres'],
    'domain': 'backend',
    'seniority_signal': 'entry-level',
    'yoe_required': '0-2 years',
    'visa_status': 'not_mentioned',
}


def _mock_client(text):
    client = MagicMock()
    resp = MagicMock()
    resp.text = text
    client.models.generate_content.return_value = resp
    return client


def _patch(client):
    return patch('enrichment.keyword_extractor.genai.Client', return_value=client)


# ── happy path ────────────────────────────────────────────────────────────────

def test_valid_jd_returns_dict():
    with _patch(_mock_client(json.dumps(_KW))):
        result = extract_keywords('We need a Python developer.', api_key='fake')
    assert result == _KW


def test_required_skills_is_list():
    with _patch(_mock_client(json.dumps(_KW))):
        result = extract_keywords('Some JD text.', api_key='fake')
    assert isinstance(result['required_skills'], list)


def test_markdown_fenced_json_parsed():
    fenced = '```json\n' + json.dumps(_KW) + '\n```'
    with _patch(_mock_client(fenced)):
        result = extract_keywords('Some JD.', api_key='fake')
    assert result == _KW


# ── seniority ─────────────────────────────────────────────────────────────────

def test_seniority_entry_level():
    kw = dict(_KW, seniority_signal='entry-level', yoe_required='0-2 years')
    with _patch(_mock_client(json.dumps(kw))):
        result = extract_keywords('0-2 years of experience required', api_key='fake')
    assert result['seniority_signal'] == 'entry-level'


# ── visa_status values ────────────────────────────────────────────────────────

def test_visa_no_sponsorship():
    kw = dict(_KW, visa_status='no_sponsorship')
    with _patch(_mock_client(json.dumps(kw))):
        result = extract_keywords('No visa sponsorship available.', api_key='fake')
    assert result['visa_status'] == 'no_sponsorship'


def test_visa_tn_only():
    kw = dict(_KW, visa_status='no_sponsorship')
    with _patch(_mock_client(json.dumps(kw))):
        result = extract_keywords('TN status only, no H1B.', api_key='fake')
    assert result['visa_status'] == 'no_sponsorship'


def test_visa_us_citizenship():
    kw = dict(_KW, visa_status='requires_us_citizenship')
    with _patch(_mock_client(json.dumps(kw))):
        result = extract_keywords('US citizens only.', api_key='fake')
    assert result['visa_status'] == 'requires_us_citizenship'


def test_visa_clearance():
    kw = dict(_KW, visa_status='requires_clearance')
    with _patch(_mock_client(json.dumps(kw))):
        result = extract_keywords('Security clearance required.', api_key='fake')
    assert result['visa_status'] == 'requires_clearance'


def test_visa_sponsorship_available():
    kw = dict(_KW, visa_status='sponsorship_available')
    with _patch(_mock_client(json.dumps(kw))):
        result = extract_keywords('We sponsor visas for qualified candidates.', api_key='fake')
    assert result['visa_status'] == 'sponsorship_available'


def test_visa_vague_authorized_is_not_mentioned():
    kw = dict(_KW, visa_status='not_mentioned')
    with _patch(_mock_client(json.dumps(kw))):
        result = extract_keywords('Must be authorized to work in the US.', api_key='fake')
    assert result['visa_status'] == 'not_mentioned'


def test_visa_silent_is_not_mentioned():
    kw = dict(_KW, visa_status='not_mentioned')
    with _patch(_mock_client(json.dumps(kw))):
        result = extract_keywords('We build great software.', api_key='fake')
    assert result['visa_status'] == 'not_mentioned'


# ── error handling ────────────────────────────────────────────────────────────

def test_api_error_returns_none():
    client = MagicMock()
    client.models.generate_content.side_effect = Exception('API error')
    with _patch(client):
        result = extract_keywords('Some JD.', api_key='fake')
    assert result is None


def test_malformed_json_returns_none():
    with _patch(_mock_client('not valid json {{{')):
        result = extract_keywords('Some JD.', api_key='fake')
    assert result is None


def test_empty_jd_returns_none_without_api_call():
    client = MagicMock()
    with _patch(client):
        result = extract_keywords('', api_key='fake')
    client.models.generate_content.assert_not_called()
    assert result is None


def test_whitespace_only_jd_returns_none():
    client = MagicMock()
    with _patch(client):
        result = extract_keywords('   \n  ', api_key='fake')
    assert result is None
