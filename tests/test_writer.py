import json
from pathlib import Path

import pytest

from output.writer import init_data_dir, load_seen, save_seen, update_latest, write_history


# ── init_data_dir ─────────────────────────────────────────────────────────────

def test_init_creates_history_dir(tmp_path):
    init_data_dir(tmp_path)
    assert (tmp_path / 'history').is_dir()

def test_init_creates_seen_jobs_empty_schema(tmp_path):
    init_data_dir(tmp_path)
    seen = json.loads((tmp_path / 'seen_jobs.json').read_text())
    assert seen == {'by_id': {}, 'by_company_title': {}}

def test_init_creates_blacklist_empty_schema(tmp_path):
    init_data_dir(tmp_path)
    bl = json.loads((tmp_path / 'blacklist.json').read_text())
    assert bl == {'companies': []}

def test_init_creates_jobs_latest_empty(tmp_path):
    init_data_dir(tmp_path)
    latest = json.loads((tmp_path / 'jobs_latest.json').read_text())
    assert latest == {}

def test_init_is_idempotent(tmp_path):
    init_data_dir(tmp_path)
    init_data_dir(tmp_path)  # second call must not raise or overwrite existing data
    assert (tmp_path / 'seen_jobs.json').exists()


# ── write_history ─────────────────────────────────────────────────────────────

def test_write_history_creates_correct_path(tmp_path):
    init_data_dir(tmp_path)
    path = write_history('2026-05-11', {}, [], base=tmp_path)
    assert path == tmp_path / 'history' / '2026-05-11.json'
    assert path.exists()

def test_write_history_valid_json(tmp_path):
    init_data_dir(tmp_path)
    stats = {'total_scraped': 10, 'after_filters': 2, 'by_tier': {'1': 1, '2': 1}}
    jobs = [{'canonical_id': 'linkedin:123', 'title': 'SWE', 'company': 'Google'}]
    write_history('2026-05-11', stats, jobs, base=tmp_path)

    data = json.loads((tmp_path / 'history' / '2026-05-11.json').read_text())
    assert data['date'] == '2026-05-11'
    assert data['stats'] == stats
    assert data['jobs'] == jobs
    assert 'run_timestamp' in data


# ── update_latest mirrors today ───────────────────────────────────────────────

def test_jobs_latest_mirrors_today(tmp_path):
    init_data_dir(tmp_path)
    date = '2026-05-11'
    stats = {'total_scraped': 5, 'after_filters': 1, 'by_tier': {}}
    jobs = [{'canonical_id': 'linkedin:999', 'title': 'Backend SWE', 'company': 'Stripe'}]

    write_history(date, stats, jobs, base=tmp_path)
    update_latest(date, base=tmp_path)

    history = json.loads((tmp_path / 'history' / f'{date}.json').read_text())
    latest = json.loads((tmp_path / 'jobs_latest.json').read_text())
    assert history == latest


# ── load_seen / save_seen round-trip ─────────────────────────────────────────

def test_load_seen_returns_empty_when_missing(tmp_path):
    seen = load_seen(base=tmp_path)
    assert seen == {'by_id': {}, 'by_company_title': {}}

def test_save_and_load_seen_round_trip(tmp_path):
    init_data_dir(tmp_path)
    payload = {
        'by_id': {'linkedin:1': {'company': 'Co', 'title': 'SWE', 'date_seen': '2026-05-11T18:00:00Z'}},
        'by_company_title': {'co::swe': {'canonical_id': 'linkedin:1', 'date_seen': '2026-05-11T18:00:00Z'}},
    }
    save_seen(payload, base=tmp_path)
    assert load_seen(base=tmp_path) == payload
