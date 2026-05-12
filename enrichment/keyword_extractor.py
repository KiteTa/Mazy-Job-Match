"""Calls Gemini Flash to extract keywords and visa_status from JDs (Phase 7)."""

import json
import logging
import os
import re

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_MODEL = 'gemini-2.5-flash'

_SYSTEM = (
    'You are a job description analyzer. Extract structured info from '
    'JDs. Return ONLY valid JSON, no other text.'
)

_PROMPT_TEMPLATE = '''\
Extract from this JD and return JSON with these fields:
  - required_skills:   array of strings (must-have)
  - preferred_skills:  array of strings (nice-to-have)
  - tools_and_tech:    array (specific tools/frameworks/langs)
  - domain:            'backend'|'frontend'|'ML/AI'|'mobile'|'data'|'fullstack'|'devops'
  - seniority_signal:  'entry-level'|'mid-level'|'senior'|'unclear'
  - yoe_required:      string (years or 'not specified')
  - visa_status:       'requires_us_citizenship'|'requires_clearance'|'no_sponsorship'|'sponsorship_available'|'not_mentioned'

Rules for visa_status:
  'requires_us_citizenship' — JD requires US citizen / green card / permanent resident
  'requires_clearance' — security clearance is required
  'no_sponsorship' — JD explicitly says no visa sponsorship, OR accepts only TN status, OR similar explicit exclusion
  'sponsorship_available' — JD explicitly offers sponsorship
  'not_mentioned' — everything else, including vague 'must be authorized to work in the US'

JD: {jd_text}'''


def extract_keywords(jd_text: str, api_key: str | None = None) -> dict | None:
    """Call Gemini to extract keywords + visa_status from JD text.

    Returns a dict with 7 fields, or None on error/empty input.
    """
    if not jd_text or not jd_text.strip():
        return None

    key = api_key or os.environ.get('GEMINI_API_KEY')
    if not key:
        logger.error('GEMINI_API_KEY not set')
        return None

    client = genai.Client(api_key=key)
    prompt = _PROMPT_TEMPLATE.format(jd_text=jd_text)

    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM,
                    temperature=0,
                ),
            )
            parsed = _parse_json(response.text)
            if parsed is not None:
                return parsed
        except Exception as exc:
            logger.warning('Gemini attempt %d failed: %s', attempt + 1, exc)

    return None


def _parse_json(text: str) -> dict | None:
    cleaned = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned.strip(), flags=re.MULTILINE)
    try:
        data = json.loads(cleaned.strip())
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        logger.warning('Gemini returned invalid JSON: %s', text[:200])
    return None
