import os
from datetime import datetime, timezone

from supabase import create_client, Client

_client_instance: Client | None = None


def _client() -> Client:
    global _client_instance
    if _client_instance is None:
        _client_instance = create_client(
            os.environ['SUPABASE_URL'],
            os.environ['SUPABASE_KEY'],
        )
    return _client_instance


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
    _client().table('jobs').upsert(records, on_conflict='company,title').execute()


def insert_pipeline_run(run_date: str, stats: dict, breakdown: dict) -> str:
    result = _client().table('pipeline_runs').insert({
        'run_date':         run_date,
        'run_timestamp':    datetime.now(timezone.utc).isoformat(),
        'total_scraped':    stats.get('total_scraped', 0),
        'after_filters':    stats.get('after_filters', 0),
        'filter_breakdown': breakdown,
    }).execute()
    return result.data[0]['id']
