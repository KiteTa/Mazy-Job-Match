"""Phase 8 — visa filter tests."""

from filters.visa import passes_visa


def _job(visa_status):
    return {'keywords': {'visa_status': visa_status}}


def test_requires_us_citizenship_reject():
    assert passes_visa(_job('requires_us_citizenship')) is False

def test_requires_clearance_reject():
    assert passes_visa(_job('requires_clearance')) is False

def test_no_sponsorship_reject():
    assert passes_visa(_job('no_sponsorship')) is False

def test_sponsorship_available_pass():
    assert passes_visa(_job('sponsorship_available')) is True

def test_not_mentioned_pass():
    assert passes_visa(_job('not_mentioned')) is True

def test_missing_visa_status_defaults_to_pass():
    assert passes_visa({'keywords': {}}) is True

def test_missing_keywords_defaults_to_pass():
    assert passes_visa({}) is True
