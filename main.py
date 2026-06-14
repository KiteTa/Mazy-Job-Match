"""Entry point for the daily job-search pipeline."""

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import config
from scrapers.github_scraper import fetch_github_jobs
from scrapers.greenhouse_scraper import fetch_greenhouse_jobs
from scrapers.ashby_scraper import scrape_ashby
from filters.dedup import is_seen, mark_seen, cleanup
from filters.location import passes_location
from filters.seniority import passes_seniority
from filters.tech_stack import passes_tech_stack
from filters.blacklist import passes_blacklist
from output.writer import init_data_dir, write_history, update_latest, load_seen, save_seen

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

ALL_SOURCES = ('github', 'greenhouse', 'ashby')


def scrape(sources: list[str] | None = None) -> list[dict]:
    """Fetch raw jobs. Pass sources=['ashby'] to target a single source."""
    active = set(sources or ALL_SOURCES)
    jobs: list[dict] = []

    if 'github' in active:
        batch = fetch_github_jobs()
        logger.info('github: %d raw', len(batch))
        jobs += batch

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


def filter_dedup(jobs: list[dict], seen: dict) -> list[dict]:
    out = [j for j in jobs if not is_seen(j, seen)]
    logger.info('dedup:           %d → %d', len(jobs), len(out))
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
    out = [j for j in jobs if passes_blacklist(j, config.BLACKLIST)]
    logger.info('blacklist:       %d → %d', len(jobs), len(out))
    return out


def run_filters(jobs: list[dict], seen: dict) -> list[dict]:
    jobs = filter_active(jobs)
    jobs = filter_dedup(jobs, seen)
    jobs = filter_location(jobs)
    jobs = filter_seniority_tech(jobs)
    jobs = filter_blacklist(jobs)
    return jobs


# ── pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline(sources: list[str] | None = None, dry_run: bool = False) -> None:
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    init_data_dir()

    seen = load_seen()
    cleanup(seen, days=config.DEDUP_WINDOW_DAYS)

    raw = scrape(sources)
    passed = run_filters(raw, seen)

    for job in passed:
        mark_seen(job, seen)

    # TODO: re-enable priority scoring once filter evaluation is complete
    # from ranking.priority import assign_priority, sort_jobs
    # for job in passed: assign_priority(job)
    # passed = sort_jobs(passed)

    stats = {'total_scraped': len(raw), 'after_filters': len(passed)}
    logger.info('done: %d → %d jobs', len(raw), len(passed))

    if dry_run:
        print(json.dumps({'stats': stats, 'jobs': passed[:5]}, indent=2, default=str))
        return

    write_history(today, stats, passed)
    update_latest(today)
    save_seen(seen)
    _sync_data_to_site()
    logger.info('output written for %s', today)


def _sync_data_to_site() -> None:
    import shutil
    repo = Path(__file__).parent
    src, dst = repo / 'data', repo / 'site' / 'data'
    dst.mkdir(parents=True, exist_ok=True)
    (dst / 'history').mkdir(exist_ok=True)
    for f in src.glob('*.json'):
        shutil.copy2(f, dst / f.name)
    for f in (src / 'history').glob('*.json'):
        shutil.copy2(f, dst / 'history' / f.name)


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
