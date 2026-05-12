import hashlib
import re
from datetime import datetime, timedelta, timezone


def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def canonical_id(job: dict) -> str:
    if job['source'] == 'linkedin':
        return f"linkedin:{job['id']}"
    h = hashlib.sha1(job['url'].encode()).hexdigest()[:12]
    return f"github:{h}"


def composite_key(job: dict) -> str:
    return f"{normalize(job['company'])}::{normalize(job['title'])}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().strftime('%Y-%m-%dT%H:%M:%SZ')


def _parse_date(s: str) -> datetime:
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def is_seen(job: dict, seen: dict) -> bool:
    return (
        canonical_id(job) in seen['by_id']
        or composite_key(job) in seen['by_company_title']
    )


def mark_seen(job: dict, seen: dict) -> None:
    cid = canonical_id(job)
    ck = composite_key(job)
    now = _utc_now_iso()
    seen['by_id'][cid] = {
        'company': job['company'],
        'title': job['title'],
        'date_seen': now,
    }
    seen['by_company_title'][ck] = {
        'canonical_id': cid,
        'date_seen': now,
    }


def cleanup(seen: dict, days: int = 14) -> None:
    cutoff = _utc_now() - timedelta(days=days)
    for idx in ('by_id', 'by_company_title'):
        seen[idx] = {
            k: v for k, v in seen[idx].items()
            if _parse_date(v['date_seen']) >= cutoff
        }
