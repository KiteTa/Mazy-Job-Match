"""Entry point for the daily job-search pipeline."""

import argparse
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

# Load .env for local development (optional, non-fatal if dotenv not installed)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def run_pipeline(dry_run: bool = False, max_jobs: int = 60) -> None:
    import config
    from scrapers.github_scraper import fetch_github_jobs
    from scrapers.linkedin_scraper import fetch_linkedin_jobs
    from filters.dedup import is_seen, mark_seen, cleanup, canonical_id
    from filters.expiry import passes_expiry
    from filters.industries import passes_industries
    from filters.location import passes_location
    from filters.seniority import passes_seniority
    from filters.tech_stack import passes_tech_stack
    from filters.blacklist import passes_blacklist
    from filters.visa import passes_visa
    from enrichment.jd_fetcher import fetch_jd
    from enrichment.keyword_extractor import extract_keywords
    from ranking.priority import assign_priority, sort_jobs
    from output.writer import init_data_dir, write_history, update_latest, load_seen, save_seen

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    init_data_dir()

    seen = load_seen()
    cleanup(seen, days=config.DEDUP_WINDOW_DAYS)

    logger.info('Fetching GitHub jobs…')
    gh_jobs = fetch_github_jobs()
    logger.info('GitHub: %d raw listings', len(gh_jobs))

    logger.info('Fetching LinkedIn jobs (max %d per URL)…', max_jobs)
    li_jobs = fetch_linkedin_jobs(max_jobs=max_jobs)
    logger.info('LinkedIn: %d raw listings', len(li_jobs))

    all_raw = gh_jobs + li_jobs
    total_scraped = len(all_raw)
    logger.info('Total scraped: %d', total_scraped)

    passed: list[dict] = []

    for job in all_raw:
        # 1. Active / visible (GitHub fields)
        if not job.get('active', True) or not job.get('is_visible', True):
            continue
        # 2. Repost (LinkedIn)
        if job.get('reposted_job'):
            continue
        # 3. Expiry (LinkedIn)
        if not passes_expiry(job):
            continue
        # 4. Date: already filtered in scrapers
        # 5. Dedup
        if is_seen(job, seen):
            continue
        # 6. Industries (LinkedIn)
        if not passes_industries(job):
            continue
        # 7. Location
        if not passes_location(job):
            continue
        # 8. Seniority L1 + L2 (L3 re-runs after Gemini)
        if not passes_seniority(job):
            continue
        # 9. Tech stack
        if not passes_tech_stack(job):
            continue
        # 10. Blacklist
        if not passes_blacklist(job, config.BLACKLIST):
            continue

        # 11. JD enrichment (GitHub: fetch apply URL; LinkedIn: already has descriptionText)
        if job['source'] == 'github' and job.get('apply_url'):
            jd = fetch_jd(job['apply_url'])
            job['description_text'] = jd
            job['has_jd'] = bool(jd)
            job['no_jd'] = not bool(jd)

        # 12. Gemini keyword extraction
        jd_text = (job.get('description_text') or '').strip()
        if jd_text:
            job['keywords'] = extract_keywords(jd_text)

        # 13. Visa filter (needs Gemini output)
        if not passes_visa(job):
            continue

        # 8b. Seniority L3 re-check (now yoe_required may be populated)
        if not passes_seniority(job):
            continue

        mark_seen(job, seen)
        passed.append(job)

    # 14. Priority scoring + sort
    for job in passed:
        assign_priority(job)
    sorted_jobs = sort_jobs(passed)

    by_tier: dict[str, int] = {}
    for job in sorted_jobs:
        t = str(job.get('priority_tier', 4))
        by_tier[t] = by_tier.get(t, 0) + 1

    stats = {
        'total_scraped': total_scraped,
        'after_filters': len(sorted_jobs),
        'by_tier': by_tier,
    }
    logger.info('Done: %d → %d jobs | tiers %s', total_scraped, len(sorted_jobs), by_tier)

    if dry_run:
        preview = {'stats': stats, 'jobs': sorted_jobs[:3]}
        print(json.dumps(preview, indent=2, default=str))
        return

    write_history(today, stats, sorted_jobs)
    update_latest(today)
    save_seen(seen)
    _sync_data_to_site()

    logger.info('Output written for %s', today)


def _sync_data_to_site() -> None:
    """Copy data/ → site/data/ so GitHub Pages (source=/site) can serve the JSON."""
    import shutil
    repo = Path(__file__).parent
    src = repo / 'data'
    dst = repo / 'site' / 'data'
    dst.mkdir(parents=True, exist_ok=True)
    (dst / 'history').mkdir(exist_ok=True)
    for f in src.glob('*.json'):
        shutil.copy2(f, dst / f.name)
    for f in (src / 'history').glob('*.json'):
        shutil.copy2(f, dst / 'history' / f.name)


def main() -> None:
    parser = argparse.ArgumentParser(description='Mazy Job Match daily pipeline')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print summary without writing files')
    parser.add_argument('--max-jobs', type=int, default=60,
                        help='Max LinkedIn jobs per search URL (default: 60)')
    args = parser.parse_args()
    run_pipeline(dry_run=args.dry_run, max_jobs=args.max_jobs)


if __name__ == '__main__':
    main()
