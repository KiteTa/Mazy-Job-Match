import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_DATA_DIR = _REPO_ROOT / 'data'


def _data(base) -> Path:
    return Path(base) if base is not None else _DEFAULT_DATA_DIR


def init_data_dir(base=None) -> None:
    d = _data(base)
    (d / 'history').mkdir(parents=True, exist_ok=True)

    seen_path = d / 'seen_jobs.json'
    if not seen_path.exists():
        seen_path.write_text(json.dumps({'by_id': {}, 'by_company_title': {}}, indent=2))

    bl_path = d / 'blacklist.json'
    if not bl_path.exists():
        bl_path.write_text(json.dumps({'companies': []}, indent=2))

    latest_path = d / 'jobs_latest.json'
    if not latest_path.exists():
        latest_path.write_text(json.dumps({}, indent=2))


def write_history(date: str, stats: dict, jobs: list, base=None) -> Path:
    d = _data(base)
    (d / 'history').mkdir(parents=True, exist_ok=True)
    payload = {
        'date': date,
        'run_timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'stats': stats,
        'jobs': jobs,
    }
    path = d / 'history' / f'{date}.json'
    path.write_text(json.dumps(payload, indent=2))
    return path


def update_latest(date: str, base=None) -> None:
    d = _data(base)
    shutil.copy2(d / 'history' / f'{date}.json', d / 'jobs_latest.json')


def load_seen(base=None) -> dict:
    path = _data(base) / 'seen_jobs.json'
    if not path.exists():
        return {'by_id': {}, 'by_company_title': {}}
    return json.loads(path.read_text())


def save_seen(seen: dict, base=None) -> None:
    (_data(base) / 'seen_jobs.json').write_text(json.dumps(seen, indent=2))
