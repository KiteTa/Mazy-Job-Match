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
from filters.dedup import canonical_id, composite_key
from filters.location import passes_location
from filters.seniority import passes_seniority
from filters.tech_stack import passes_tech_stack, _REJECT_SIGNALS
from filters.blacklist import passes_blacklist
from output.writer import load_seen

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


def check_dedup(job: dict, seen: dict) -> tuple[bool, str]:
    cid = canonical_id(job)
    if cid in seen['by_id']:
        days = (_utc_now() - _parse_date(seen['by_id'][cid]['date_seen'])).days
        return False, f'seen {days}d ago'
    ck = composite_key(job)
    if ck in seen['by_company_title']:
        days = (_utc_now() - _parse_date(seen['by_company_title'][ck]['date_seen'])).days
        return False, f'title+co {days}d ago'
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
    # Find the configured name for this token, fall back to title-cased token
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
    'dedup':     16,
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
        _trunc('DEDUP',     W['dedup']),
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
            _trunc(job.get('title', ''),    W['title']),
            _trunc(job.get('company', ''),  W['company']),
            _trunc(', '.join(job.get('locations', [])), W['location']),
            _age(job.get('published_at', '')).ljust(W['published']),
            _cell(*r['active'],    W['active']),
            _cell(*r['dedup'],     W['dedup']),
            _cell(*r['location'],  W['loc']),
            _cell(*r['seniority'], W['seniority']),
            _cell(*r['blacklist'], W['blacklist']),
            'PASS' if r['final'] else 'FAIL',
        ])
        print(row)


def print_summary(results: list[dict]) -> None:
    def after(key: str) -> int:
        return sum(1 for r in results if r[key][0])

    # cumulative counts (each stage only counts jobs that passed all prior stages)
    n_active    = sum(1 for r in results if r['active'][0])
    n_dedup     = sum(1 for r in results if r['active'][0] and r['dedup'][0])
    n_location  = sum(1 for r in results if r['active'][0] and r['dedup'][0] and r['location'][0])
    n_seniority = sum(1 for r in results if r['active'][0] and r['dedup'][0] and r['location'][0] and r['seniority'][0])
    n_final     = sum(1 for r in results if r['final'])

    print()
    print(f'Total raw:     {len(results)}')
    print(
        f'After filters: '
        f'active={n_active}  '
        f'dedup={n_dedup}  '
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

    seen = load_seen()

    results = []
    for job in jobs:
        r_active = check_active(job)
        r_dedup  = check_dedup(job, seen)    if r_active[0] else (False, 'skipped')
        r_loc    = check_location(job)       if r_dedup[0]  else (False, 'skipped')
        r_sen    = check_seniority_tech(job) if r_loc[0]    else (False, 'skipped')
        r_bl     = check_blacklist(job)      if r_sen[0]    else (False, 'skipped')
        final    = r_active[0] and r_dedup[0] and r_loc[0] and r_sen[0] and r_bl[0]
        results.append({
            'job':       job,
            'active':    r_active,
            'dedup':     r_dedup,
            'location':  r_loc,
            'seniority': r_sen,
            'blacklist': r_bl,
            'final':     final,
        })

    print_table(results)
    print_summary(results)


if __name__ == '__main__':
    main()
