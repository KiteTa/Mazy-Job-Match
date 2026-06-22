# Supabase Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the local JSON-based pipeline outputs with Supabase so the backend upserts scraped jobs after filtering and the frontend reads directly from the database.

**Architecture:** The Python pipeline calls `upsert_jobs()` and `insert_pipeline_run()` from a new `output/supabase_writer.py` module, replacing file-based dedup (`filters/dedup.py`) and output (`output/writer.py`). The React frontend queries `supabase.from('jobs')` directly, replacing `fetch('/jobs_latest.json')`. Conflict detection (dedup) moves to the DB via `ON CONFLICT (source, id) DO UPDATE`.

**Tech Stack:** Python `supabase>=2.0` (backend), `@supabase/supabase-js` (frontend), Vite env vars, python-dotenv.

## Global Constraints

- Supabase Python client: `supabase>=2.0`
- Frontend JS client: `@supabase/supabase-js` (latest)
- Backend env vars: `SUPABASE_URL`, `SUPABASE_KEY` (service role key) — loaded from `.env` via python-dotenv
- Frontend env vars: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` — Vite injects at build time
- No Row Level Security (out of scope)
- No Gemini enrichment wiring (out of scope; columns exist in schema as nullable)
- `data/` directory cleanup deferred until pipeline confirmed working
- Root `.gitignore` already covers both `.env` and `site/.env` via the `.env` pattern

---

## File Map

**Create:**
- `output/supabase_writer.py` — `upsert_jobs()` and `insert_pipeline_run()`
- `tests/test_supabase_writer.py` — unit tests with mocked client
- `site/src/lib/supabase.ts` — Supabase JS client singleton

**Modify:**
- `scrapers/greenhouse_scraper.py:44` — `_CUTOFF_DAYS = 7` → `2`
- `scrapers/ashby_scraper.py:37` — `_CUTOFF_DAYS = 7` → `2`
- `requirements.txt` — add `supabase>=2.0`
- `main.py` — remove file-based state; call supabase_writer
- `site/src/types.ts` — remove `JobsData`; add `enriched_at`
- `site/src/App.tsx` — replace fetch with Supabase query; `JobsData | null` → `Job[] | null`
- `tests/test_pipeline_verbose.py` — remove dedup imports and column
- `site/package.json` — `@supabase/supabase-js` added via `npm install`

**Delete:**
- `output/writer.py`
- `filters/dedup.py`
- `tests/test_writer.py`
- `tests/test_dedup.py`

---

### Task 1: Provision Supabase tables and create env files

This is a manual setup task — nothing to commit.

**Files:**
- SQL run in Supabase dashboard (no file)
- Create: `.env` (backend, git-ignored)
- Create: `site/.env` (frontend, git-ignored)

- [ ] **Step 1: Create tables in the Supabase SQL editor**

Open Supabase dashboard → SQL Editor and run:

```sql
CREATE TABLE jobs (
  pk               bigserial PRIMARY KEY,
  id               text NOT NULL,
  source           text NOT NULL,
  title            text NOT NULL,
  company          text NOT NULL,
  locations        text[] NOT NULL DEFAULT '{}',
  is_remote        boolean,
  work_type        text,
  job_type         text,
  department       text,
  url              text,
  apply_url        text,
  description_text text,
  description_html text,
  published_at     timestamptz,
  active           boolean DEFAULT true,
  required_skills  text[],
  tools_and_tech   text[],
  sponsors_visa    boolean,
  salary_min       integer,
  salary_max       integer,
  seniority        text,
  yoe_required     text,
  enriched_at      timestamptz,
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now(),
  UNIQUE (source, id)
);

CREATE INDEX ON jobs (published_at DESC);
CREATE INDEX ON jobs (company);
CREATE INDEX ON jobs (active);
CREATE INDEX ON jobs USING GIN (locations);

CREATE TABLE pipeline_runs (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_date       date NOT NULL,
  run_timestamp  timestamptz NOT NULL,
  total_scraped  integer,
  after_filters  integer
);
```

Expected: both tables created with no errors.

- [ ] **Step 2: Create `.env` (backend)**

Create `.env` at the project root (already in `.gitignore`):

```
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_KEY=<service-role-key>
```

Get both values from Supabase dashboard → Project Settings → API → Project URL and `service_role` key.

- [ ] **Step 3: Create `site/.env` (frontend)**

Create `site/.env` (covered by root `.gitignore`'s `.env` rule):

```
VITE_SUPABASE_URL=https://<your-project>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-public-key>
```

Get `VITE_SUPABASE_ANON_KEY` from Supabase dashboard → Project Settings → API → `anon public` key.

---

### Task 2: Update scraper cutoff and create `output/supabase_writer.py`

**Files:**
- Modify: `scrapers/greenhouse_scraper.py:44`
- Modify: `scrapers/ashby_scraper.py:37`
- Modify: `requirements.txt`
- Create: `output/supabase_writer.py`
- Create: `tests/test_supabase_writer.py`

**Interfaces:**
- Produces: `upsert_jobs(jobs: list[dict]) -> None`, `insert_pipeline_run(run_date: str, stats: dict) -> None` — imported by `main.py` in Task 3

- [ ] **Step 1: Write the failing tests**

Create `tests/test_supabase_writer.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from output.supabase_writer import insert_pipeline_run, upsert_jobs


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://test.supabase.co')
    monkeypatch.setenv('SUPABASE_KEY', 'test-key')


def _job(**overrides):
    base = {
        'id': 'abc123',
        'source': 'greenhouse',
        'title': 'Software Engineer',
        'company': 'Acme',
        'locations': ['San Francisco, CA'],
        'url': 'https://example.com/job/1',
        'apply_url': 'https://example.com/apply/1',
        'description_text': 'Some description',
        'published_at': '2026-06-16T10:00:00Z',
        'active': True,
    }
    return {**base, **overrides}


@patch('output.supabase_writer.create_client')
def test_upsert_jobs_builds_records(mock_create):
    mock_client = MagicMock()
    mock_create.return_value = mock_client

    upsert_jobs([_job(), _job(id='def456', company='Beta')])

    mock_client.table.assert_called_once_with('jobs')
    call_args = mock_client.table.return_value.upsert.call_args
    records = call_args[0][0]
    assert len(records) == 2
    assert records[0]['id'] == 'abc123'
    assert records[1]['id'] == 'def456'
    assert call_args[1]['on_conflict'] == 'source,id'


@patch('output.supabase_writer.create_client')
def test_upsert_jobs_noop_when_empty(mock_create):
    upsert_jobs([])
    mock_create.assert_not_called()


@patch('output.supabase_writer.create_client')
def test_upsert_jobs_defaults_locations_to_empty_list(mock_create):
    mock_client = MagicMock()
    mock_create.return_value = mock_client

    upsert_jobs([_job(locations=None)])

    records = mock_client.table.return_value.upsert.call_args[0][0]
    assert records[0]['locations'] == []


@patch('output.supabase_writer.create_client')
def test_insert_pipeline_run_sends_correct_row(mock_create):
    mock_client = MagicMock()
    mock_create.return_value = mock_client

    insert_pipeline_run('2026-06-16', {'total_scraped': 50, 'after_filters': 12})

    mock_client.table.assert_called_once_with('pipeline_runs')
    row = mock_client.table.return_value.insert.call_args[0][0]
    assert row['run_date'] == '2026-06-16'
    assert row['total_scraped'] == 50
    assert row['after_filters'] == 12
    assert 'run_timestamp' in row
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/test_supabase_writer.py -v`
Expected: `ModuleNotFoundError: No module named 'output.supabase_writer'`

- [ ] **Step 3: Add `supabase` to `requirements.txt`**

In `requirements.txt`, add after the `requests>=2.31` line:

```
supabase>=2.0
```

Install: `pip install "supabase>=2.0"`

- [ ] **Step 4: Change `_CUTOFF_DAYS` in both scrapers**

In `scrapers/greenhouse_scraper.py`, change line 44:
```python
_CUTOFF_DAYS = 2
```

In `scrapers/ashby_scraper.py`, change line 37:
```python
_CUTOFF_DAYS = 2
```

- [ ] **Step 5: Create `output/supabase_writer.py`**

```python
import os
from datetime import datetime, timezone

from supabase import create_client, Client


def _client() -> Client:
    return create_client(
        os.environ['SUPABASE_URL'],
        os.environ['SUPABASE_KEY'],
    )


def _to_record(job: dict) -> dict:
    return {
        'id':               job['id'],
        'source':           job['source'],
        'title':            job['title'],
        'company':          job['company'],
        'locations':        job.get('locations') or [],
        'is_remote':        job.get('is_remote'),
        'work_type':        job.get('work_type'),
        'job_type':         job.get('job_type'),
        'department':       job.get('department'),
        'url':              job.get('url'),
        'apply_url':        job.get('apply_url'),
        'description_text': job.get('description_text'),
        'description_html': job.get('description_html'),
        'published_at':     job.get('published_at'),
        'active':           job.get('active', True),
    }


def upsert_jobs(jobs: list[dict]) -> None:
    if not jobs:
        return
    records = [_to_record(j) for j in jobs]
    _client().table('jobs').upsert(records, on_conflict='source,id').execute()


def insert_pipeline_run(run_date: str, stats: dict) -> None:
    _client().table('pipeline_runs').insert({
        'run_date':      run_date,
        'run_timestamp': datetime.now(timezone.utc).isoformat(),
        'total_scraped': stats.get('total_scraped', 0),
        'after_filters': stats.get('after_filters', 0),
    }).execute()
```

- [ ] **Step 6: Run tests to confirm they pass**

Run: `pytest tests/test_supabase_writer.py -v`
Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add scrapers/greenhouse_scraper.py scrapers/ashby_scraper.py requirements.txt output/supabase_writer.py tests/test_supabase_writer.py
git commit -m "feat: add supabase writer and reduce scraper cutoff to 2 days"
```

---

### Task 3: Rewrite `main.py` to call Supabase writer

**Files:**
- Modify: `main.py`

**Interfaces:**
- Consumes: `upsert_jobs(jobs: list[dict]) -> None`, `insert_pipeline_run(run_date: str, stats: dict) -> None` from `output.supabase_writer`

- [ ] **Step 1: Replace the full contents of `main.py`**

```python
"""Entry point for the daily job-search pipeline."""

import argparse
import json
import logging
from datetime import datetime, timezone

import config
from scrapers.greenhouse_scraper import fetch_greenhouse_jobs
from scrapers.ashby_scraper import scrape_ashby
from filters.location import passes_location
from filters.seniority import passes_seniority
from filters.tech_stack import passes_tech_stack
from filters.blacklist import passes_blacklist, build_blocked_set
from filters.security import passes_security
from output.supabase_writer import upsert_jobs, insert_pipeline_run

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ── scrapers ──────────────────────────────────────────────────────────────────

ALL_SOURCES = ('greenhouse', 'ashby')


def scrape(sources: list[str] | None = None) -> list[dict]:
    """Fetch raw jobs. Pass sources=['ashby'] to target a single source."""
    active = set(sources or ALL_SOURCES)
    jobs: list[dict] = []

    if 'greenhouse' in active:
        batch = fetch_greenhouse_jobs(config.TARGET_COMPANIES.get('greenhouse', []))
        logger.info('greenhouse: %d raw', len(batch))
        jobs += batch

    if 'ashby' in active:
        batch = scrape_ashby(config.TARGET_COMPANIES.get('ashby', []))
        logger.info('ashby: %d raw', len(batch))
        jobs += batch

    logger.info('total scraped: %d', len(jobs))
    return jobs


# ── filter stages ─────────────────────────────────────────────────────────────

def filter_active(jobs: list[dict]) -> list[dict]:
    out = [j for j in jobs if j.get('active', True) and j.get('is_visible', True)]
    logger.info('active:          %d → %d', len(jobs), len(out))
    return out


def filter_location(jobs: list[dict]) -> list[dict]:
    out = [j for j in jobs if passes_location(j)]
    logger.info('location:        %d → %d', len(jobs), len(out))
    return out


def filter_seniority_tech(jobs: list[dict]) -> list[dict]:
    out = [j for j in jobs if passes_seniority(j) and passes_tech_stack(j)]
    logger.info('seniority+tech:  %d → %d', len(jobs), len(out))
    return out


def filter_blacklist(jobs: list[dict]) -> list[dict]:
    blocked = build_blocked_set(config.BLACKLIST)
    out = [j for j in jobs if passes_blacklist(j, blocked)]
    logger.info('blacklist:       %d → %d', len(jobs), len(out))
    return out


def filter_security(jobs: list[dict]) -> list[dict]:
    out = [j for j in jobs if passes_security(j)]
    logger.info('security:        %d → %d', len(jobs), len(out))
    return out


def run_filters(jobs: list[dict]) -> list[dict]:
    jobs = filter_active(jobs)
    jobs = filter_blacklist(jobs)
    jobs = filter_security(jobs)
    jobs = filter_location(jobs)
    jobs = filter_seniority_tech(jobs)
    return jobs


# ── pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline(sources: list[str] | None = None, dry_run: bool = False) -> None:
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    raw = scrape(sources)
    passed = run_filters(raw)

    stats = {'total_scraped': len(raw), 'after_filters': len(passed)}
    logger.info('done: %d → %d jobs', len(raw), len(passed))

    if dry_run:
        print(json.dumps({'stats': stats, 'jobs': passed[:5]}, indent=2, default=str))
        return

    upsert_jobs(passed)
    insert_pipeline_run(today, stats)
    logger.info('output written for %s', today)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description='Mazy Job Match daily pipeline')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print summary without writing files')
    parser.add_argument('--source', nargs='+', choices=list(ALL_SOURCES),
                        metavar='SOURCE',
                        help=f'Limit to specific sources: {", ".join(ALL_SOURCES)}')
    args = parser.parse_args()
    run_pipeline(sources=args.source, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Verify dry-run works without DB credentials**

Run: `python main.py --dry-run --source greenhouse`
Expected: JSON output with `stats` and up to 5 jobs printed; no errors about missing `SUPABASE_URL`

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: remove file-based pipeline state, write to Supabase"
```

---

### Task 4: Delete old files and clean up tests

**Files:**
- Delete: `output/writer.py`
- Delete: `filters/dedup.py`
- Delete: `tests/test_writer.py`
- Delete: `tests/test_dedup.py`
- Modify: `tests/test_pipeline_verbose.py`

- [ ] **Step 1: Stage the four deletions**

```bash
git rm output/writer.py filters/dedup.py tests/test_writer.py tests/test_dedup.py
```

Expected: 4 files staged for deletion.

- [ ] **Step 2: Replace `tests/test_pipeline_verbose.py`**

```python
"""Verbose per-job filter trace.

Usage:
    python tests/test_pipeline_verbose.py --source ashby --company notion
    python tests/test_pipeline_verbose.py --source greenhouse --company anthropic
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from filters.location import passes_location
from filters.seniority import passes_seniority
from filters.tech_stack import passes_tech_stack, _REJECT_SIGNALS
from filters.blacklist import passes_blacklist

_L2_REJECT = re.compile(
    r'\b(senior|staff|principal|lead|manager|director|'
    r'head of|vp|distinguished|iii|iv|v|l5|l6|l7|e5|e6|e7)\b|\bsr\.',
    re.IGNORECASE,
)


# ── reason-annotating checkers ────────────────────────────────────────────────

def check_active(job: dict) -> tuple[bool, str]:
    if not job.get('active', True):
        return False, 'inactive'
    if not job.get('is_visible', True):
        return False, 'not visible'
    return True, 'PASS'


def check_location(job: dict) -> tuple[bool, str]:
    if passes_location(job):
        return True, 'PASS'
    locs = job.get('locations') or []
    snippet = ', '.join(str(l) for l in locs[:2]) or '(none)'
    return False, f'no US: {snippet}'


def check_seniority_tech(job: dict) -> tuple[bool, str]:
    if not passes_seniority(job):
        level = (job.get('seniority_level') or '').strip()
        if level:
            return False, f'level:{level}'
        m = _L2_REJECT.search(job.get('title') or '')
        if m:
            return False, f"title:'{m.group()}'"
        return False, 'yoe too high'
    if not passes_tech_stack(job):
        text = (job.get('title') or '') + ' ' + (job.get('description_text') or '')[:200]
        m = _REJECT_SIGNALS.search(text)
        signal = m.group() if m else '?'
        return False, f'hw signal:{signal}'
    return True, 'PASS'


def check_blacklist(job: dict) -> tuple[bool, str]:
    if passes_blacklist(job, config.BLACKLIST):
        return True, 'PASS'
    return False, f"co:{job.get('company', '?')}"


# ── scrapers ──────────────────────────────────────────────────────────────────

def do_scrape(source: str, token: str) -> list[dict]:
    companies = [{'name': token.title(), 'token': token}]
    for entry in config.TARGET_COMPANIES.get(source, []):
        if entry['token'] == token:
            companies = [entry]
            break

    if source == 'greenhouse':
        from scrapers.greenhouse_scraper import fetch_greenhouse_jobs
        return fetch_greenhouse_jobs(companies)
    if source == 'ashby':
        from scrapers.ashby_scraper import scrape_ashby
        return scrape_ashby(companies)
    print(f'Unknown source: {source}', file=sys.stderr)
    sys.exit(1)


# ── table rendering ───────────────────────────────────────────────────────────

W = {
    'title':     34,
    'company':   11,
    'location':  22,
    'published':  8,
    'active':     8,
    'loc':       18,
    'seniority': 20,
    'blacklist': 14,
    'final':      5,
}
SEP = ' | '


def _trunc(s: str, n: int) -> str:
    s = str(s or '')
    return (s[:n - 1] + '>') if len(s) > n else s.ljust(n)


def _age(raw: str) -> str:
    try:
        days = (_utc_now() - _parse_date(raw)).days
        return f'{days}d ago'
    except Exception:
        return (raw or '?')[:8]


def _cell(passed: bool, reason: str, width: int) -> str:
    if reason == 'skipped':
        return '-'.ljust(width)
    return _trunc('PASS' if passed else f'FAIL:{reason}', width)


def print_table(results: list[dict]) -> None:
    headers = [
        _trunc('TITLE',     W['title']),
        _trunc('COMPANY',   W['company']),
        _trunc('LOCATION',  W['location']),
        _trunc('PUBLISHED', W['published']),
        _trunc('ACTIVE',    W['active']),
        _trunc('LOCATION',  W['loc']),
        _trunc('SENIORITY', W['seniority']),
        _trunc('BLACKLIST', W['blacklist']),
        'FINAL',
    ]
    hdr = SEP.join(headers)
    print(hdr)
    print('-' * len(hdr))

    for r in results:
        job = r['job']
        row = SEP.join([
            _trunc(job.get('title', ''),                      W['title']),
            _trunc(job.get('company', ''),                    W['company']),
            _trunc(', '.join(job.get('locations', [])),       W['location']),
            _age(job.get('published_at', '')).ljust(W['published']),
            _cell(*r['active'],    W['active']),
            _cell(*r['location'],  W['loc']),
            _cell(*r['seniority'], W['seniority']),
            _cell(*r['blacklist'], W['blacklist']),
            'PASS' if r['final'] else 'FAIL',
        ])
        print(row)


def print_summary(results: list[dict]) -> None:
    n_active    = sum(1 for r in results if r['active'][0])
    n_location  = sum(1 for r in results if r['active'][0] and r['location'][0])
    n_seniority = sum(1 for r in results if r['active'][0] and r['location'][0] and r['seniority'][0])
    n_final     = sum(1 for r in results if r['final'])

    print()
    print(f'Total raw:     {len(results)}')
    print(
        f'After filters: '
        f'active={n_active}  '
        f'location={n_location}  '
        f'seniority={n_seniority}  '
        f'blacklist={n_final}'
    )
    print(f'Final passed:  {n_final}')


# ── helpers ───────────────────────────────────────────────────────────────────

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_date(s: str) -> datetime:
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description='Verbose per-job filter trace')
    parser.add_argument('--source',  required=True, choices=['greenhouse', 'ashby'])
    parser.add_argument('--company', required=True, help='Company token, e.g. notion')
    args = parser.parse_args()

    print(f'\nScraping {args.source}/{args.company}…')
    jobs = do_scrape(args.source, args.company)
    print(f'Scraper returned {len(jobs)} jobs (already filtered by title/location/date)\n')

    results = []
    for job in jobs:
        r_active = check_active(job)
        r_loc    = check_location(job)       if r_active[0] else (False, 'skipped')
        r_sen    = check_seniority_tech(job) if r_loc[0]    else (False, 'skipped')
        r_bl     = check_blacklist(job)      if r_sen[0]    else (False, 'skipped')
        final    = r_active[0] and r_loc[0] and r_sen[0] and r_bl[0]
        results.append({
            'job':       job,
            'active':    r_active,
            'location':  r_loc,
            'seniority': r_sen,
            'blacklist': r_bl,
            'final':     final,
        })

    print_table(results)
    print_summary(results)


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Run pytest to confirm no remaining import errors**

Run: `pytest tests/test_supabase_writer.py tests/test_seniority.py tests/test_tech_stack.py tests/test_location.py tests/test_priority.py -v`
Expected: all collected tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_pipeline_verbose.py
git commit -m "chore: delete file-based writer and dedup, update verbose tracer"
```

---

### Task 5: Frontend Supabase integration

**Files:**
- Create: `site/src/lib/supabase.ts`
- Modify: `site/src/types.ts`
- Modify: `site/src/App.tsx`
- Modify: `site/package.json` (via `npm install`)

**Interfaces:**
- Consumes: `supabase` singleton from `./lib/supabase`
- Produces: `Job[]` from `.from('jobs').select('*').eq('active', true).order('published_at', {ascending: false})`

- [ ] **Step 1: Install `@supabase/supabase-js`**

```bash
cd site && npm install @supabase/supabase-js
```

Expected: `@supabase/supabase-js` appears in `site/package.json` dependencies.

- [ ] **Step 2: Create `site/src/lib/supabase.ts`**

```ts
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL as string,
  import.meta.env.VITE_SUPABASE_ANON_KEY as string,
)
```

- [ ] **Step 3: Replace `site/src/types.ts`**

```ts
export interface Job {
  source: string
  id: string | null
  title: string
  company: string
  locations: string[]
  is_remote?: boolean | null
  work_type?: string | null
  job_type?: string | null
  department?: string | null
  url: string | null
  apply_url: string | null
  description_text: string | null
  description_html?: string | null
  published_at: string | null
  active?: boolean | null
  // enrichment (nullable until Gemini populates)
  required_skills?: string[]
  tools_and_tech?: string[]
  sponsors_visa?: boolean | null
  salary_min?: number | null
  salary_max?: number | null
  seniority?: string | null
  yoe_required?: string | null
  enriched_at?: string | null
  // legacy fields kept for utils.ts fallbacks
  posted_at?: string | null
  salary?: string | null
  location?: string | null
  country?: string | null
  employment_type?: string | null
  applicant_count?: number | null
  applicants_count?: string | null
}

export type SortOption = 'latest' | 'match' | 'competition'

export interface Filters {
  locations: string[]
  companyType: 'all' | 'faang' | 'other'
  workTypes: string[]
  jobTypes: string[]
  past24h: boolean
  sponsorOnly: boolean
  sort: SortOption
}
```

- [ ] **Step 4: Replace `site/src/App.tsx`**

```tsx
import { useEffect, useMemo, useState } from 'react'
import { DEFAULT_FILTERS } from './constants'
import { applyFilters, getJobDate, isNew, jobKey } from './lib/utils'
import { addAppliedId, addToBlacklist, getAppliedIds, getApplyCount, getBlacklist, saveApplyCount } from './lib/storage'
import { supabase } from './lib/supabase'
import type { Filters, Job } from './types'
import DetailPane from './components/DetailPane'
import FilterBar from './components/FilterBar'
import Header from './components/Header'
import JobList from './components/JobList'

export default function App() {
  const [jobs, setJobs] = useState<Job[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [applyCount, setApplyCount] = useState<number>(() => getApplyCount())
  const [blacklist, setBlacklist] = useState<Set<string>>(() => getBlacklist())
  const [hiddenIds, setHiddenIds] = useState<Set<string>>(() => getAppliedIds())

  useEffect(() => {
    supabase
      .from('jobs')
      .select('*')
      .eq('active', true)
      .order('published_at', { ascending: false })
      .then(({ data, error }) => {
        if (error) setError(error.message)
        else setJobs((data as Job[]) ?? [])
      })
  }, [])

  const visibleJobs = useMemo<Job[]>(() => {
    if (!jobs) return []
    return jobs.filter(job => {
      if (blacklist.has(job.company)) return false
      if (hiddenIds.has(jobKey(job))) return false
      return true
    })
  }, [jobs, blacklist, hiddenIds])

  const filteredJobs = useMemo(() => applyFilters(visibleJobs, filters), [visibleJobs, filters])

  const newTodayCount = useMemo(
    () => visibleJobs.filter(j => isNew(getJobDate(j))).length,
    [visibleJobs]
  )

  const selectedJob = useMemo(
    () => filteredJobs.find(j => jobKey(j) === selectedId) ?? null,
    [filteredJobs, selectedId]
  )

  // j/k and arrow key navigation
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault()
        setSelectedId(prev => {
          const idx = filteredJobs.findIndex(j => jobKey(j) === prev)
          const next = filteredJobs[idx + 1]
          return next ? jobKey(next) : prev
        })
      }
      if (e.key === 'ArrowUp' || e.key === 'k') {
        e.preventDefault()
        setSelectedId(prev => {
          const idx = filteredJobs.findIndex(j => jobKey(j) === prev)
          const prev2 = filteredJobs[idx - 1]
          return prev2 ? jobKey(prev2) : prev
        })
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [filteredJobs])

  function handleApply(job: Job) {
    const key = jobKey(job)
    addAppliedId(key)
    setHiddenIds(prev => { const s = new Set(prev); s.add(key); return s })

    const next = applyCount + 1
    saveApplyCount(next)
    setApplyCount(next)

    if (selectedId === key) {
      const idx = filteredJobs.findIndex(j => jobKey(j) === key)
      const nextJob = filteredJobs[idx + 1] ?? filteredJobs[idx - 1] ?? null
      setSelectedId(nextJob ? jobKey(nextJob) : null)
    }
  }

  function handleBlacklist(company: string) {
    addToBlacklist(company)
    setBlacklist(prev => { const s = new Set(prev); s.add(company); return s })
    if (selectedJob?.company === company) setSelectedId(null)
  }

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-cream">
        <p className="text-[13px] text-red-500">Failed to load jobs: {error}</p>
      </div>
    )
  }

  if (!jobs) {
    return (
      <div className="h-screen flex flex-col overflow-hidden bg-cream">
        <div style={{ height: 44, background: '#A8D8D0', borderBottom: '0.5px solid #8ECAC0' }} />
        <div className="flex flex-1 overflow-hidden">
          <div className="shrink-0 overflow-y-auto bg-cream" style={{ width: 260, borderRight: '0.5px solid #E2E2E2' }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="px-3 py-2.5 skeleton" style={{ borderBottom: '0.5px solid #E2E2E2', minHeight: 64 }}>
                <div className="h-3 rounded mb-1.5" style={{ width: `${60 + (i % 3) * 15}%`, background: '#E0E0E0' }} />
                <div className="h-2.5 rounded mb-2" style={{ width: '45%', background: '#EEEEEE' }} />
                <div className="h-2 rounded" style={{ width: '30%', background: '#EEEEEE' }} />
              </div>
            ))}
          </div>
          <div className="flex-1 flex items-center justify-center bg-parchment">
            <p className="text-[13px] text-chip-text">Loading jobs…</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-cream">
      <Header newTodayCount={newTodayCount} applyCount={applyCount} />

      <FilterBar
        filters={filters}
        onChange={setFilters}
        totalCount={filteredJobs.length}
      />

      <div className="flex flex-1 overflow-hidden">
        <JobList
          jobs={filteredJobs}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onApply={handleApply}
          onBlacklist={handleBlacklist}
          sort={filters.sort}
          onSortChange={s => setFilters(f => ({ ...f, sort: s }))}
        />

        <DetailPane job={selectedJob} onApply={handleApply} />
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Run TypeScript build to confirm no type errors**

```bash
cd site && npm run build
```

Expected: build succeeds with 0 TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add site/src/lib/supabase.ts site/src/types.ts site/src/App.tsx site/package.json site/package-lock.json
git commit -m "feat: replace JSON fetch with Supabase client in frontend"
```
