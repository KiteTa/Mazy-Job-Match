# Supabase Integration Design

Date: 2026-06-16

## Summary

Replace the local JSON-based pipeline outputs with Supabase. Backend upserts scraped jobs into Supabase after filtering; frontend reads directly from Supabase. All file-based state (seen_jobs, history, jobs_latest.json) is removed.

---

## Database Schema

### `jobs`

Single table — enrichment fields merged in as nullable columns, populated later by Gemini.

```sql
CREATE TABLE jobs (
  pk               bigserial PRIMARY KEY,
  id               text NOT NULL,
  source           text NOT NULL,          -- ashby | greenhouse
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
  -- enrichment (Gemini, nullable until enriched)
  required_skills  text[],
  tools_and_tech   text[],
  sponsors_visa    boolean,
  salary_min       integer,
  salary_max       integer,
  seniority        text,
  yoe_required     text,
  enriched_at      timestamptz,
  -- metadata
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now(),
  UNIQUE (source, id)
);

CREATE INDEX ON jobs (published_at DESC);
CREATE INDEX ON jobs (company);
CREATE INDEX ON jobs (active);
CREATE INDEX ON jobs USING GIN (locations);
```

### `pipeline_runs`

Records each pipeline execution for observability.

```sql
CREATE TABLE pipeline_runs (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_date       date NOT NULL,
  run_timestamp  timestamptz NOT NULL,
  total_scraped  integer,
  after_filters  integer
);
```

Tables removed: `job_enrichment` (merged into `jobs`), `seen_jobs` (replaced by DB upsert).

---

## Backend Changes

### Scrapers

- `_CUTOFF_DAYS = 2` in both `greenhouse_scraper.py` and `ashby_scraper.py` (was 7). Provides a 1-day retry buffer if a pipeline run fails.

### New: `output/supabase_writer.py`

Two functions:
- `upsert_jobs(jobs: list[dict]) -> None` — bulk upsert using `ON CONFLICT (source, id) DO UPDATE`. Updates all fields except `created_at`. Uses Supabase Python client.
- `insert_pipeline_run(run_date: str, stats: dict) -> None` — inserts a row into `pipeline_runs`.

### Updated: `main.py`

- Remove: `load_seen`, `save_seen`, `mark_seen`, `cleanup`, `_sync_data_to_site`, `init_data_dir`, `write_history`, `update_latest`
- Add: call `upsert_jobs(passed)` and `insert_pipeline_run(today, stats)` after filtering

### Deleted

- `output/writer.py` — no longer needed
- `filters/dedup.py` — replaced by DB upsert dedup

### Environment Variables (backend)

File: `.env` (added to `.gitignore`)

```
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<service-role-key>
```

Service role key is used for backend writes (bypasses Row Level Security).

---

## Frontend Changes

### New: `site/src/lib/supabase.ts`

Initializes Supabase JS client using `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.

### Updated: `site/src/App.tsx`

Replace `fetch('/jobs_latest.json')` with:

```ts
supabase
  .from('jobs')
  .select('*')
  .eq('active', true)
  .order('published_at', { ascending: false })
```

All jobs are shown sorted by `published_at` DESC (not filtered to 24h — scraper has 2-day buffer, so showing all lets users see jobs from a missed run).

### Updated: `site/src/types.ts`

`Job` type updated to match new schema (add enrichment fields as optional).

### Environment Variables (frontend)

File: `site/.env` (added to `.gitignore`)

```
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-key>
```

Anon key is read-only, safe to ship in the browser bundle.

---

## Data Flow

```
scrapers (Greenhouse, Ashby)
  → pipeline filters (active, blacklist, security, location, seniority+tech)
  → supabase_writer.upsert_jobs()         [jobs table, ON CONFLICT DO UPDATE]
  → supabase_writer.insert_pipeline_run() [pipeline_runs table]

frontend (React)
  → supabase.from('jobs').select('*')
  → renders JobList / DetailPane
```

---

## Out of Scope

- Gemini enrichment wiring (enrichment columns exist in schema, populated in a later sprint)
- Row Level Security configuration (single-user app, deferred)
- `data/` directory cleanup (can delete after confirming pipeline works)
