"""Phase 2 — seniority filter tests."""

import pytest
from filters.seniority import passes_seniority


def job(title="Software Engineer", seniority_level=None, yoe="not specified"):
    j = {"title": title}
    if seniority_level is not None:
        j["seniority_level"] = seniority_level
    if yoe != "not specified":
        j["keywords"] = {"yoe_required": yoe}
    return j


# ── Layer 1 ──────────────────────────────────────────────────────────────────

def test_l1_entry_level():
    assert passes_seniority(job(seniority_level="Entry level")) is True

def test_l1_associate():
    assert passes_seniority(job(seniority_level="Associate")) is True

def test_l1_mid_senior():
    assert passes_seniority(job(seniority_level="Mid-Senior level")) is False

def test_l1_director():
    assert passes_seniority(job(seniority_level="Director")) is False

def test_l1_executive():
    assert passes_seniority(job(seniority_level="Executive")) is False

def test_l1_internship():
    assert passes_seniority(job(seniority_level="Internship")) is False

# ── Layer 1 fall-through → Layer 2 ───────────────────────────────────────────

def test_l1_na_falls_to_l2_senior_reject():
    assert passes_seniority(job(title="Senior Software Engineer", seniority_level="Not Applicable")) is False

def test_l1_missing_falls_to_l2():
    assert passes_seniority(job(title="Software Engineer, New Grad 2026")) is True

# ── Layer 2 ──────────────────────────────────────────────────────────────────

def test_l2_senior_reject():
    assert passes_seniority(job(title="Senior Software Engineer")) is False

def test_l2_sr_dot_reject():
    assert passes_seniority(job(title="Sr. Software Engineer")) is False

def test_l2_staff_reject():
    assert passes_seniority(job(title="Staff Engineer")) is False

def test_l2_principal_reject():
    assert passes_seniority(job(title="Principal Engineer")) is False

def test_l2_l6_reject():
    assert passes_seniority(job(title="L6 Software Engineer")) is False

def test_l2_roman_iii_reject():
    assert passes_seniority(job(title="Software Engineer III")) is False

def test_l2_new_grad_pass():
    assert passes_seniority(job(title="Software Engineer, New Grad 2026")) is True

def test_l2_junior_pass():
    assert passes_seniority(job(title="Junior Software Engineer")) is True

def test_l2_sde_i_pass():
    assert passes_seniority(job(title="SDE I — Backend")) is True

def test_l2_sde_ii_pass():
    assert passes_seniority(job(title="SDE II")) is True

def test_l2_l3_pass():
    assert passes_seniority(job(title="L3 Software Engineer")) is True

def test_l2_l4_pass():
    assert passes_seniority(job(title="L4 Software Engineer")) is True

def test_l2_entry_level_title_pass():
    assert passes_seniority(job(title="Entry Level Software Engineer")) is True

def test_l2_unclear_falls_to_l3():
    # plain title with no signals → L3 → "not specified" → PASS
    assert passes_seniority(job(title="Software Engineer")) is True

# ── Layer 3 ──────────────────────────────────────────────────────────────────

def test_l3_0_2_yoe_pass():
    assert passes_seniority(job(yoe="0-2 years")) is True

def test_l3_1_year_pass():
    assert passes_seniority(job(yoe="1 year")) is True

def test_l3_5_plus_yoe_reject():
    assert passes_seniority(job(yoe="5+ years")) is False

def test_l3_3_years_reject():
    assert passes_seniority(job(yoe="3 years")) is False

def test_l3_not_specified_pass():
    assert passes_seniority(job(yoe="not specified")) is True

def test_l3_missing_keywords_pass():
    # no keywords dict at all
    assert passes_seniority({"title": "Software Engineer"}) is True
