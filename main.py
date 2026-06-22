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


def _drop_detail(stage: str, job: dict) -> str:
    if stage == 'location':
        locs = job.get('locations') or []
        return ', '.join(locs) or '(no locations)'
    if stage == 'active':
        return f"active={job.get('active')} is_visible={job.get('is_visible')}"
    if stage == 'seniority_tech':
        if not passes_seniority(job):
            level = job.get('seniority_level') or job.get('seniority') or ''
            return f"seniority: {level or 'inferred from title'}"
        return 'tech stack'
    if stage == 'security':
        return 'security/defense role'
    if stage == 'blacklist':
        return 'blacklisted company'
    return ''


def run_filters(jobs: list[dict]) -> tuple[list[dict], dict]:
    stages = [
        ('active',         filter_active),
        ('blacklist',      filter_blacklist),
        ('security',       filter_security),
        ('location',       filter_location),
        ('seniority_tech', filter_seniority_tech),
    ]

    remaining = jobs
    breakdown: dict = {}

    for stage_name, filter_fn in stages:
        passed = filter_fn(remaining)
        passed_set = {id(j) for j in passed}
        for j in remaining:
            if id(j) not in passed_set:
                detail = _drop_detail(stage_name, j)
                logger.info(
                    'dropped [%s] %s / %s — %s',
                    stage_name, j.get('company', '?'), j.get('title', '?'), detail,
                )
        breakdown[f'after_{stage_name}'] = len(passed)
        remaining = passed

    return remaining, breakdown


# ── pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline(sources: list[str] | None = None, dry_run: bool = False) -> None:
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    raw = scrape(sources)
    passed, breakdown = run_filters(raw)

    stats = {'total_scraped': len(raw), 'after_filters': len(passed)}
    logger.info('done: %d → %d jobs', len(raw), len(passed))

    if dry_run:
        print(json.dumps({'stats': stats, 'breakdown': breakdown, 'jobs': passed[:5]}, indent=2, default=str))
        return

    upsert_jobs(passed)
    insert_pipeline_run(today, stats, breakdown)
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
