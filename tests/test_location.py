"""Phase 4 — location filter tests."""

from filters.location import passes_location


def li(country):
    return {"source": "linkedin", "country": country}


def gh(locations):
    return {"source": "github", "locations": locations}


# LinkedIn
def test_linkedin_us_pass():
    assert passes_location(li("US")) is True

def test_linkedin_ca_reject():
    assert passes_location(li("CA")) is False

def test_linkedin_empty_reject():
    assert passes_location(li("")) is False

# GitHub — remote
def test_github_remote_pass():
    assert passes_location(gh(["Remote"])) is True

def test_github_remote_case_insensitive():
    assert passes_location(gh(["remote"])) is True

# GitHub — US cities
def test_github_us_city_pass():
    assert passes_location(gh(["New York, NY"])) is True

def test_github_us_state_only_pass():
    assert passes_location(gh(["Austin, TX"])) is True

def test_github_canada_only_reject():
    assert passes_location(gh(["Toronto, ON"])) is False

def test_github_mixed_us_and_non_us_pass():
    assert passes_location(gh(["Toronto, ON", "New York, NY"])) is True

def test_github_united_states_string_pass():
    assert passes_location(gh(["United States"])) is True

def test_github_empty_locations_reject():
    assert passes_location(gh([])) is False

def test_github_no_locations_key_reject():
    assert passes_location({"source": "github"}) is False
