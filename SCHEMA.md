# Supabase Schema Design

## Field mapping

| Schema column | Ashby | Greenhouse | GitHub |
|---|---|---|---|
| `source` | `"ashby"` | `"greenhouse"` | `"github"` |
| `title` | `title` | `title` | `title` |
| `company` | config `name` | config `name` | `company_name` |
| `locations[]` | `[location] + secondaryLocations[].location` | `offices[].name` | `locations[]` |
| `is_remote` | `isRemote` | derived: `work_type == "Remote"` | `work_remote_allowed` |
| `work_type` | `workplaceType` | `metadata[name="Location Type"].value` | — |
| `job_type` | `employmentType` | — | `employment_type` |
| `department` | `department` | `departments[0].name` | — |
| `url` | `jobUrl` | `absolute_url` | `url` |
| `apply_url` | `applyUrl` | `absolute_url` | `url` |
| `description_text` | `descriptionPlain` | `content` (HTML, AI can handle) | — |
| `description_html` | `null` | `content` | — |
| `published_at` | `publishedAt` | `first_published` | `date_posted` (unix → iso) |
| `active` | `isListed` | `null` | `active` |

## Tables

### `jobs`

```sql
CREATE TABLE jobs (
  pk                  bigserial PRIMARY KEY,
  id                  text NOT NULL,            -- raw source job ID (Ashby UUID / Greenhouse integer / GitHub URL)
  source              text NOT NULL,            -- ashby | greenhouse | github
  title               text NOT NULL,
  company             text NOT NULL,
  locations           text[] NOT NULL DEFAULT '{}',
  is_remote           boolean,
  work_type           text,                     -- Remote | Hybrid | OnSite
  job_type            text,                     -- FullTime | Internship | Contract
  department          text,
  url                 text,
  apply_url           text,
  description_text    text,
  description_html    text,
  published_at        timestamptz,
  active              boolean DEFAULT true,
  created_at          timestamptz DEFAULT now(),
  updated_at          timestamptz DEFAULT now(),
  UNIQUE (source, id)
);

CREATE INDEX ON jobs (published_at DESC);
CREATE INDEX ON jobs (company);
CREATE INDEX ON jobs (active);
CREATE INDEX ON jobs USING GIN (locations);
```

### `job_enrichment`

One-to-one with `jobs`. Populated by Gemini after scraping.

```sql
CREATE TABLE job_enrichment (
  job_pk          bigint PRIMARY KEY REFERENCES jobs(pk) ON DELETE CASCADE,
  required_skills text[],
  tools_and_tech  text[],
  sponsors_visa   boolean,
  salary_min      integer,
  salary_max      integer,
  seniority       text,                         -- new-grad | junior | mid | senior
  yoe_required    text,                         -- e.g. "0-2"
  applicant_count integer,
  enriched_at     timestamptz
);

CREATE INDEX ON job_enrichment (sponsors_visa);
CREATE INDEX ON job_enrichment USING GIN (required_skills);
```

### `seen_jobs`

Replaces `data/seen_jobs.json`.

```sql
CREATE TABLE seen_jobs (
  canonical_id    text PRIMARY KEY,             -- {source}:{sha1(url)[:12]}
  composite_key   text UNIQUE NOT NULL,         -- {company}::{title} normalized
  company         text,
  title           text,
  date_seen       timestamptz NOT NULL
);

CREATE INDEX ON seen_jobs (composite_key);
CREATE INDEX ON seen_jobs (date_seen);          -- for 14-day cleanup
```

### `pipeline_runs`

Replaces `data/history/{date}.json`.

```sql
CREATE TABLE pipeline_runs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_date        date NOT NULL,
  run_timestamp   timestamptz NOT NULL,
  total_scraped   integer,
  after_filters   integer
);
```

## Notes

- `location` (single string) is dropped in favor of `locations[]` across all scrapers.
- `description_html` is null for Ashby (only plain text available) and GitHub (no JD fetched).
- `seen_jobs` may stay as a JSON file for now to avoid per-job round-trip latency; migrate to Supabase once batch upsert is implemented.
- localStorage (`blacklist`, `applied_ids`) stays client-side — no auth layer yet.
