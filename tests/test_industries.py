"""Phase 4 — industries filter tests."""

from filters.industries import passes_industries


def li(industries):
    return {"source": "linkedin", "industries": industries}


def test_staffing_reject():
    assert passes_industries(li("Staffing and Recruiting")) is False

def test_software_pass():
    assert passes_industries(li("Software Development")) is True

def test_human_resources_pass():
    assert passes_industries(li("Human Resources")) is True

def test_empty_industries_pass():
    assert passes_industries(li("")) is True

def test_partial_match_not_rejected():
    # must be exact — partial strings should pass
    assert passes_industries(li("Staffing")) is True

def test_github_source_always_pass():
    assert passes_industries({"source": "github", "industries": "Staffing and Recruiting"}) is True
