# Job Search Agent — Design Document v3.1

**Sprint 1 (Static Website Edition)**
Updated: 2026-05-11

---

## 1. Overview & Goals

A Python pipeline that runs daily via GitHub Actions. It scrapes new grad software engineering jobs from LinkedIn (via Apify) and the SimplifyJobs GitHub list, filters and ranks them, extracts JD keywords and visa-sponsorship signals using Gemini Flash, and publishes a static website on GitHub Pages with the results.

**Sprint 1 deliverable:** a public website (hosted on GitHub Pages) showing today's filtered jobs with client-side JS for filtering/sorting, plus 14 days of history.

**What this is NOT (Sprint 2+):**

- No AI scoring/ranking — keyword extraction only
- No web-based feedback loop — blacklist managed via `config.py` + push
- No email digest — Sprint 2
- No specific company targeting — Sprint 2
- No cloud DB / backend — JSON files in repo

---

## 2. Tech Stack

| Component             | Tool                                            | Notes                                   |
| --------------------- | ----------------------------------------------- | --------------------------------------- |
| Language              | Python 3.11+                                    | Pipeline + scrapers                     |
| LinkedIn scraping     | Apify `curious_coder/linkedin-jobs-scraper`     | $1 per 1k results                       |
| GitHub job list       | SimplifyJobs/New-Grad-Positions `listings.json` | Structured JSON                         |
| JD keyword extraction | Gemini 2.5 Flash (or Flash-Lite)                | Free tier sufficient                    |
| Data storage          | JSON files in repo                              | No DB; commit/diff friendly             |
| Scheduler             | GitHub Actions cron                             | Daily 18:00 UTC (11 AM PDT / 10 AM PST) |
| Hosting               | GitHub Pages (public repo)                      | Free; auto-deploy on push               |
| Frontend              | Static HTML + vanilla JS                        | Client-side filter/sort                 |
| Secrets               | GitHub Actions secrets                          | `APIFY_TOKEN`, `GEMINI_API_KEY`         |

---

## 3. Architecture Overview

```
GitHub Actions (daily 18:00 UTC = 11 AM PDT)
    |
    v
Python pipeline (main.py)
    |- scrapers/      LinkedIn (Apify) + GitHub (listings.json)
    |- filters/       active, repost, expiry, date, dedup, location,
    |                  seniority, tech-stack, industries, blacklist
    |- enrichment/    JD fetch (GH) + Gemini extraction
    |                  (returns keywords + visa_status)
    |- filters/visa.py  apply visa filter using Gemini output
    |- ranking/       priority tier + keyword coverage + sort keys
    `- output/        generate JSON + static site assets
    |
    v
Write to data/:
    data/history/YYYY-MM-DD.json
    data/jobs_latest.json
    data/seen_jobs.json
    data/blacklist.json
    |
    v
git commit + push to main -> GitHub Pages auto-deploys site/
```

---

## 4. Data Sources

### 4a. SimplifyJobs GitHub List

URL: https://github.com/SimplifyJobs/New-Grad-Positions

```
https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json
```

**Fields used:**

| Field          | Type             | Use                                                     |
| -------------- | ---------------- | ------------------------------------------------------- |
| `company_name` | string           | Blacklist + priority tier                               |
| `title`        | string           | Seniority filter + display + dedup composite key        |
| `date_posted`  | unix timestamp   | Date filter (within 48h)                                |
| `url`          | string           | Apply link as-is + source of github canonical_id (sha1) |
| `is_visible`   | boolean          | Skip if false                                           |
| `active`       | boolean          | Skip if false                                           |
| `locations`    | array of strings | US/Remote filter                                        |

**JD extraction for GitHub jobs:**

- Fetch apply URL, extract JD text from HTML
- Apply link used as-is (Simplify shortlink or direct company URL)
- If fetch fails (auth wall, JS-rendered, empty) → `no_jd=true`, displayed in Tier 4

### 4b. LinkedIn via Apify

Actor: `curious_coder/linkedin-jobs-scraper` (ID: `hKByXkMQaC5Qt9UMN`). $1 per 1k results. Free $5/mo credit.

**Input:** pre-built LinkedIn search URLs in `config.LINKEDIN_SEARCH_URLS` (built once via linkedin.com/jobs with Past 24h, Entry+Associate, United States filters).

```python
LINKEDIN_SEARCH_URLS = [
    'https://www.linkedin.com/jobs/search/?keywords=Software+Engineer&location=United+States&f_TPR=r86400&f_E=1%2C2',
    'https://www.linkedin.com/jobs/search/?keywords=SDE&location=United+States&f_TPR=r86400&f_E=1%2C2',
    'https://www.linkedin.com/jobs/search/?keywords=Backend+Developer&location=United+States&f_TPR=r86400&f_E=1%2C2',
    'https://www.linkedin.com/jobs/search/?keywords=Full+Stack+Developer&location=United+States&f_TPR=r86400&f_E=1%2C2',
]
```

**Apify API call:**

```
POST https://api.apify.com/v2/acts/hKByXkMQaC5Qt9UMN/runs?token=$APIFY_TOKEN
{
  "startUrls": [{ "url": "<each URL>" }],
  "maxJobs": 100,
  "scrapeCompany": true
}
```

**Output fields (mapped from real Apify response):**

| Field                   | Type          | Sample / Use                                          |
| ----------------------- | ------------- | ----------------------------------------------------- |
| `id`                    | string        | `'4321375715'` — **DEDUP PRIMARY KEY** (canonical_id) |
| `title`                 | string        | `'Software Developer (Entry Level)'` — raw            |
| `companyName`           | string        | `'Epic'` — blacklist + priority                       |
| `seniorityLevel`        | string        | `'Entry level'` — Layer 1 seniority filter            |
| `industries`            | string        | `'Software Development'` — filter Staffing            |
| `country`               | string        | `'US'` — filter must == `'US'`                        |
| `location`              | string        | Display only                                          |
| `link`                  | string        | LinkedIn page URL — fallback for apply                |
| `applyUrl`              | string        | Real apply URL — **PREFERRED**                        |
| `descriptionText`       | string        | Already cleaned, used directly (no fetch)             |
| `postedAt`              | ISO timestamp | 48h date filter                                       |
| `expireAt`              | unix ms       | Filter: reject if `expireAt < now`                    |
| `applicantsCount`       | string        | Store + display + sort within tier ASC                |
| `repostedJob`           | boolean       | Filter: drop if true                                  |
| `employmentType`        | string        | Store, not filtered                                   |
| `workplaceTypes`        | array         | Store, not filtered                                   |
| `workRemoteAllowed`     | boolean       | Store, not filtered                                   |
| `companyLogo`           | URL           | Store + display on card                               |
| `companyAddress`        | object        | Store (street/city/region/postal/country)             |
| `companyDescription`    | string        | Store + expandable on card                            |
| `companyEmployeesCount` | number        | Store (Sprint 2 filter)                               |
| `salary`                | string        | Store (Sprint 2 display)                              |

**Fields explicitly NOT used:**

- `jobFunction` — too generic, unreliable
- `standardizedTitle` — using raw title only
- `trackingId` / `refId` — per-scrape tokens, not stable

**Rules:**

- **Apply link rule:** `applyUrl` preferred; fallback to `link` (LinkedIn page) for Easy Apply.
- **Repost filter:** drop where `repostedJob == true` (before other processing).
- **Expiry filter:** drop where `expireAt < now_ms()`.

---

## 5. Filter Pipeline (in order)

Each job passes through these filters sequentially. Filtered jobs are logged but not displayed.

| #   | Filter            | Logic                                                                                   |
| --- | ----------------- | --------------------------------------------------------------------------------------- |
| 1   | Active/visible    | Skip if `is_visible=false` / `active=false` (GitHub)                                    |
| 2   | Repost            | LinkedIn: skip if `repostedJob == true`                                                 |
| 3   | Expiry            | LinkedIn: skip if `expireAt < now` (UTC ms)                                             |
| 4   | Date              | Skip if `posted_at` older than 48h                                                      |
| 5   | Dedup             | `canonical_id` in `seen.by_id` OR `norm(company+title)` in `seen.by_company_title`      |
| 6   | Industries        | LinkedIn: skip if `industries == 'Staffing and Recruiting'`                             |
| 7   | Location/Country  | LinkedIn: `country == 'US'`. GitHub: US city/state or Remote                            |
| 8   | Seniority         | 3-layer logic — Section 6                                                               |
| 9   | Tech stack        | Reject pure embedded/hardware — Section 7                                               |
| 10  | Blacklist         | Skip if company in blacklist                                                            |
| 11  | JD enrichment     | LinkedIn: `descriptionText`. GitHub: fetch apply URL                                    |
| 12  | Gemini extraction | Keywords + `visa_status` (1 call per job-with-JD)                                       |
| 13  | Visa filter       | Reject `visa_status` in `{requires_us_citizenship, requires_clearance, no_sponsorship}` |
| 14  | Priority scoring  | Assign tier + coverage % + sort keys                                                    |

---

## 6. Seniority Filter (3-Layer)

### Layer 1 — LinkedIn `seniorityLevel` (most reliable)

- `'Entry level'` or `'Associate'` → **PASS**
- `'Mid-Senior level'`, `'Director'`, `'Executive'` → **REJECT**
- `'Internship'` → **REJECT** (we want new grad full-time)
- Not present or `'Not Applicable'` → fall through to L2

### Layer 2 — Title keyword matching (GitHub + LinkedIn without `seniorityLevel`)

**REJECT** if title contains:

- Senior, Sr., Staff, Principal, Lead, Manager, Director, Head of, VP, Distinguished
- III, IV, V (Roman numerals 3+)
- L5, L6, L7, E5, E6, E7

**PASS** if title contains:

- Junior, Jr., New Grad, New Graduate, Entry Level, Entry-Level, Associate
- I, II (Roman numerals 1-2)
- L3, L4, E3, E4, SDE I, SDE II, SWE I
- Early Career, Rotational, University Grad, Campus Hire

**UNCLEAR** → fall through to L3

### Layer 3 — Gemini YOE (in keyword extraction output)

- 0-2 YOE → **PASS**
- 3+ YOE → **REJECT**
- not specified → **PASS** (default)

---

## 7. Tech Stack Filter

Goal: drop jobs PURELY in stacks you don't work in. Lenient — C++ with web is fine.

**REJECT** if title OR JD contains ONLY:

- Embedded systems, firmware, FPGA, VHDL, Verilog, RTL, bare metal
- Hardware engineer, electrical engineer, circuit design, PCB
- Purely mechanical, civil, chemical engineering

**ALWAYS PASS** (never reject):

- Mentions of Python, JavaScript, TypeScript, Go, Rust, Java, Kotlin, Swift
- Web, backend, API, cloud, AWS, GCP, Azure, mobile, iOS, Android
- ML, AI, data, distributed systems

**Implementation:** keyword check on title + `descriptionText` (LinkedIn) or title + first 500 chars (GitHub fetched JD). No LLM call.

---

## 8. Industries, Country, Expiry Filters

**Industries (LinkedIn only):**

- REJECT if `industries == 'Staffing and Recruiting'` (exact match)
- Other industries like `'Human Resources'` — not filtered in Sprint 1

**Country (LinkedIn only):**

- REJECT if `country != 'US'`

**Expiry (LinkedIn only):**

- REJECT if `expireAt < current_utc_timestamp_ms`

---

## 9. Visa Sponsorship Filter

User requires visa sponsorship. JDs that exclude sponsorship are rejected.

Runs AFTER Gemini extraction. `visa_status` comes from the JD via Gemini prompt (Section 11).

| `visa_status`             | Meaning                                                   | Pipeline action              |
| ------------------------- | --------------------------------------------------------- | ---------------------------- |
| `requires_us_citizenship` | JD says US citizen / green card / permanent resident only | **REJECT**                   |
| `requires_clearance`      | Security clearance required (implies US citizen)          | **REJECT**                   |
| `no_sponsorship`          | Explicitly says no sponsorship (incl. TN-only)            | **REJECT**                   |
| `sponsorship_available`   | Explicitly offers sponsorship                             | **PASS** (highlight on card) |
| `not_mentioned`           | No statement, or vague "must be authorized to work"       | **PASS**                     |

**Edge cases:**

- TN-only (NAFTA, Canadian/Mexican citizens only) → `no_sponsorship` (since user is not Canadian/Mexican)
- "Must be authorized to work in the US" alone = `not_mentioned` (PASS) — covers OPT/H1B-transfer
- Only EXPLICIT exclusion statements reject

---

## 10. Priority Scoring

Each job gets a tier. Within tier, sort by `applicantsCount` ASC (fewer applicants = earlier = better odds).

| Tier | Label              | Criteria                                            |
| ---- | ------------------ | --------------------------------------------------- |
| 1    | 🔥 Top Pick        | Big Tech / well-known company AND has full JD       |
| 2    | ⭐ Good Match      | Has full JD AND 2+ preferred stack keywords matched |
| 3    | 📋 Check It Out    | Has full JD, passes filters, no special signals     |
| 4    | 🔗 No JD Available | Passes filters but JD could not be extracted        |

**Sort order within tier:**

- Primary: `applicantsCount` ASC (missing = treat as 0, top)
- Secondary: `keyword_coverage` DESC
- Tertiary: `posted_at` DESC (newest first)

**Big Tech / well-known list (`config.py`, expandable):**

Google, Meta, Apple, Amazon, Microsoft, Netflix, Stripe, Airbnb, Uber, Lyft, Salesforce, Adobe, Oracle, Intel, Nvidia, Qualcomm, LinkedIn, Twitter/X, Snap, Coinbase, Robinhood, Palantir, Databricks, OpenAI, Anthropic, Figma, Notion, Canva, Atlassian, Shopify, Spotify, Block, Square, PayPal, Twilio, Cloudflare, Datadog, MongoDB, Snowflake

**Tech stack alignment for Tier 2:**

- Preferred stack in `config.py`
- JD's `tools_and_tech` contains 2+ preferred → Tier 2 (if not already Tier 1)
- Default: `[Python, TypeScript, JavaScript, React, Node, FastAPI, ML, LLM, cloud, AWS, distributed]`

---

## 11. Gemini Keyword Extraction

One Gemini Flash call per job-with-JD. Model: `gemini-2.5-flash` (Flash-Lite acceptable).

**Prompt:**

```
System: You are a job description analyzer. Extract structured info from
        JDs. Return ONLY valid JSON, no other text.

User:   Extract from this JD and return JSON with these fields:
          - required_skills:   array of strings (must-have)
          - preferred_skills:  array of strings (nice-to-have)
          - tools_and_tech:    array (specific tools/frameworks/langs)
          - domain:            'backend'|'frontend'|'ML/AI'|'mobile'|
                               'data'|'fullstack'|'devops'
          - seniority_signal:  'entry-level'|'mid-level'|'senior'|'unclear'
          - yoe_required:      string (years or 'not specified')
          - visa_status:       'requires_us_citizenship'|'requires_clearance'|
                               'no_sponsorship'|'sponsorship_available'|
                               'not_mentioned'

        Rules for visa_status:
          'requires_us_citizenship' — JD requires US citizen / green card /
             permanent resident
          'requires_clearance' — security clearance is required
          'no_sponsorship' — JD explicitly says no visa sponsorship, OR
             accepts only TN status, OR similar explicit exclusion
          'sponsorship_available' — JD explicitly offers sponsorship
          'not_mentioned' — everything else, including vague
             'must be authorized to work in the US' (no further restriction)

        JD: {job_description_text}
```

**Usage of fields:**

- `tools_and_tech` → Tier 2 detection + matched/unmatched stack lists
- `yoe_required` + `seniority_signal` → Layer 3 seniority
- `visa_status` → Section 9 visa filter (3 REJECT, 2 PASS)
- `required_skills`, `preferred_skills` → display on card
- `domain` → website filter facet

---

## 12. Data Storage (JSON Files)

All state in versioned JSON under `data/`. No SQLite.

```
data/
├── history/
│   ├── 2026-04-28.json    (oldest, rotates out at 14d)
│   ├── ...
│   └── 2026-05-11.json    (today)
├── jobs_latest.json        (copy of today's history)
├── seen_jobs.json          (dedup, 14-day window)
└── blacklist.json          (mirror of config.BLACKLIST)
```

### 12a. Canonical Job ID

Each job gets a `canonical_id` used as the identity key everywhere:

- LinkedIn: `f"linkedin:{job['id']}"` → e.g. `'linkedin:4321375715'`
- GitHub: `f"github:{sha1(job['url'])[:12]}"` → e.g. `'github:a3f9c2b1e8d4'`

Rationale: LinkedIn `id` is stable across scrapes (URL query params change). GitHub has no stable ID, hash the URL. Uniform format simplifies adding new sources later.

### 12b. Title/Company Normalization (for cross-source dedup)

Within a single source (LinkedIn), `canonical_id` catches all repeats. Cross-source repeats (same job appearing on both LinkedIn and GitHub) are caught by a secondary index on normalized `company+title`.

```python
import re

def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[^\w\s]', ' ', s)   # punctuation -> space
    s = re.sub(r'\s+', ' ', s).strip()  # collapse whitespace
    return s

def composite_key(job) -> str:
    return f"{normalize(job.company)}::{normalize(job.title)}"
```

**Examples:**

- `'Software Engineer, New Grad'` → `'software engineer new grad'`
- `'Software Engineer - New Grad'` → `'software engineer new grad'` (matches above)
- `'Software Engineer (New Grad 2026)'` → `'software engineer new grad 2026'` (year preserved, intentionally)
- `'Stripe, Inc.'` → `'stripe inc'`

**Limitation:** `'Stripe'` and `'Stripe, Inc.'` still differ. Acceptable in Sprint 1 — revisit after production data.

### 12c. `history/YYYY-MM-DD.json`

```json
{
  "date": "2026-05-11",
  "run_timestamp": "2026-05-11T18:00:00Z",
  "stats": {
    "total_scraped": 247,
    "after_filters": 32,
    "by_tier": { "1": 4, "2": 11, "3": 12, "4": 5 }
  },
  "jobs": [
    {
      "canonical_id": "linkedin:4321375715",
      "source": "linkedin",
      "title": "Software Developer (Entry Level)",
      "company": "Epic",
      "company_logo": "https://media.licdn.com/.../company-logo.jpg",
      "company_address": {
        "street": "1979 Milky Way",
        "city": "Verona",
        "region": "WI",
        "postal_code": "53593",
        "country": "US"
      },
      "company_description": "Join us in our mission...",
      "company_employees_count": 17246,
      "location": "Sheboygan, WI",
      "country": "US",
      "posted_at": "2026-05-11T18:23:28.000Z",
      "expire_at": 1784775029000,
      "apply_url": "https://epic.avature.net/...",
      "linkedin_url": "https://www.linkedin.com/jobs/view/...",
      "description_text": "...",
      "seniority_level": "Entry level",
      "industries": "Software Development",
      "employment_type": "Full-time",
      "workplace_types": ["On-site"],
      "work_remote_allowed": false,
      "applicants_count": 57,
      "salary": null,
      "keywords": {
        "required_skills": ["JavaScript", "TypeScript", "C#"],
        "preferred_skills": ["machine learning"],
        "tools_and_tech": ["JS", "TS", "C#"],
        "domain": "fullstack",
        "seniority_signal": "entry-level",
        "yoe_required": "not specified",
        "visa_status": "no_sponsorship"
      },
      "priority_tier": 2,
      "keyword_coverage": 0.18,
      "matched_stack_keywords": ["TypeScript", "JavaScript"],
      "unmatched_stack_keywords": ["Python", "React", "..."],
      "has_jd": true
    }
  ]
}
```

> Note: the Epic sample above would actually be REJECTED in Phase 13 because `visa_status='no_sponsorship'`. Shown here only to illustrate the schema.

### 12d. `seen_jobs.json` (dedup index)

```json
{
  "by_id": {
    "linkedin:4321375715": {
      "company": "Epic",
      "title": "Software Developer (Entry Level)",
      "date_seen": "2026-05-11T18:00:00Z"
    },
    "github:a3f9c2b1e8d4": { "...": "..." }
  },
  "by_company_title": {
    "epic::software developer entry level": {
      "canonical_id": "linkedin:4321375715",
      "date_seen": "2026-05-11T18:00:00Z"
    }
  }
}
```

**Dedup logic:**

```python
def is_seen(job, seen) -> bool:
    return (canonical_id(job) in seen['by_id']
            or composite_key(job) in seen['by_company_title'])

def mark_seen(job, seen):
    cid = canonical_id(job)
    ck  = composite_key(job)
    now = utc_now_iso()
    seen['by_id'][cid] = {
        'company': job.company,
        'title': job.title,
        'date_seen': now,
    }
    seen['by_company_title'][ck] = {
        'canonical_id': cid,
        'date_seen': now,
    }

def cleanup(seen, days=14):
    cutoff = utc_now() - timedelta(days=days)
    for idx in ('by_id', 'by_company_title'):
        seen[idx] = {k: v for k, v in seen[idx].items()
                     if parse(v['date_seen']) >= cutoff}
```

### 12e. `blacklist.json`

```json
{
  "companies": [
    { "company": "Infosys", "reason": "staffing", "date_added": "2026-05-10" },
    {
      "company": "TechStaffing",
      "reason": "scam-pattern",
      "date_added": "2026-05-10"
    }
  ]
}
```

Source of truth: `config.BLACKLIST`. Regenerated each run for frontend display. Sprint 2 makes it editable from the web UI.

---

## 13. Website (Frontend)

Static site at `username.github.io/job-agent`.

```
site/
├── index.html              Main view — today's jobs
├── history.html            Date picker for past 14 days
├── styles.css
└── app.js                  Fetches data/*.json, renders, filter/sort
```

**Header section:**

- Last updated: `<run_timestamp>`
- Stats: 247 scraped → 32 after filters → tiers (4/11/12/5)
- Current preferred stack (chips)
- Blacklist count + expand

**Per-job card:**

- Tier badge (🔥/⭐/📋/🔗)
- Company logo (left) + Company name + Title
- Location + Source (LinkedIn / GitHub)
- Posted timestamp + `applicantsCount` ("57 applicants")
- Apply button (`applyUrl` preferred, `link` fallback)
- Domain + seniority signal + `visa_status` chip (if `sponsorship_available`)
- `required_skills`, `preferred_skills`, `tools_and_tech` as chips
- Keyword coverage: "X% match (N/M of your stack)" with ✅/❌ per keyword
- Expand/collapse: company description + full JD

**Default sort:**

- Group by tier (1 → 4)
- Within tier: `applicantsCount` ASC → coverage DESC → `posted_at` DESC

**JS interactions (client-side, no backend):**

- Sort by: default | coverage % | posted time | company A-Z | applicants
- Filter: tier, source, domain, has_jd, visa sponsorship offered
- Search: text match on title + company
- Expand/collapse full JD per card

**History view:**

- Date picker for last 14 available days
- Loads `data/history/<date>.json` on select

---

## 14. GitHub Actions Workflow

Daily cron 18:00 UTC = 11 AM PDT / 10 AM PST. Manual switch needed at DST boundary.

```yaml
# .github/workflows/daily.yml
name: Daily job scrape
on:
  schedule:
    - cron: '0 18 * * *' # 11 AM PDT / 10 AM PST
  workflow_dispatch:

permissions:
  contents: write

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - name: Run pipeline
        env:
          APIFY_TOKEN: ${{ secrets.APIFY_TOKEN }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python main.py
      - name: Commit data updates
        run: |
          git config user.name 'github-actions[bot]'
          git config user.email '...@users.noreply.github.com'
          git add data/
          git diff --staged --quiet || git commit -m 'Daily update'
          git push
```

**Secrets to add:**

- `APIFY_TOKEN`
- `GEMINI_API_KEY`

**GitHub Pages setup:**

- Settings → Pages → Source: "Deploy from a branch"
- Branch: `main`, folder: `/site`
- `data/` accessible at `/data/*` via relative path from `site/app.js`

---

## 15. Project File Structure

```
job-agent/
├── main.py
├── config.py                     stack, locations, tier-1, BLACKLIST
├── requirements.txt
├── .env.example
├── .gitignore
│
├── .github/workflows/daily.yml
│
├── scrapers/
│   ├── github_scraper.py
│   └── linkedin_scraper.py
│
├── filters/
│   ├── dedup.py                  canonical_id, normalize, seen index
│   ├── seniority.py              3-layer logic
│   ├── tech_stack.py
│   ├── location.py
│   ├── industries.py
│   ├── expiry.py                 expireAt < now
│   ├── visa.py                   uses Gemini visa_status
│   └── blacklist.py
│
├── enrichment/
│   ├── jd_fetcher.py             GitHub only
│   └── keyword_extractor.py      Gemini Flash; returns keywords + visa_status
│
├── ranking/
│   └── priority.py               tier + coverage + sort keys
│
├── output/
│   └── writer.py                 history/, jobs_latest, seen, blacklist
│
├── data/
│   ├── history/
│   ├── jobs_latest.json
│   ├── seen_jobs.json
│   └── blacklist.json
│
├── site/
│   ├── index.html
│   ├── history.html
│   ├── styles.css
│   └── app.js
│
└── tests/
    ├── test_dedup.py             canonical_id, normalize, is_seen, cleanup
    ├── test_seniority.py
    ├── test_tech_stack.py
    ├── test_location.py
    ├── test_industries.py
    ├── test_expiry.py
    ├── test_visa.py
    ├── test_github_scraper.py
    ├── test_linkedin_scraper.py
    ├── test_keyword_extractor.py
    ├── test_priority.py
    └── test_writer.py
```

---

## 16. Build Order & Test Cases

Build phases sequentially. Each phase has mandatory passing tests.

### Phase 1 — Storage Layer + Dedup

| Test                                        | Input                                        | Expected                                  |
| ------------------------------------------- | -------------------------------------------- | ----------------------------------------- |
| Init empty `data/`                          | No existing files                            | All JSON files created with empty schemas |
| `canonical_id` LinkedIn                     | `job.id='4321375715', source='linkedin'`     | `'linkedin:4321375715'`                   |
| `canonical_id` GitHub                       | `url='https://...'`                          | `'github:<12-char hash>'`                 |
| `normalize` basic                           | `'Software Engineer, New Grad'`              | `'software engineer new grad'`            |
| `normalize` dash variant                    | `'Software Engineer - New Grad'`             | `'software engineer new grad'` (== above) |
| `normalize` preserves year                  | `'Software Engineer (New Grad 2026)'`        | `'software engineer new grad 2026'`       |
| Write history file                          | Day's job list                               | `data/history/YYYY-MM-DD.json` valid      |
| `jobs_latest` mirrors today                 | After write                                  | Content == today's history                |
| Dedup write both indices                    | New job                                      | `by_id` AND `by_company_title` updated    |
| Dedup hit by `canonical_id`                 | Same LinkedIn job twice                      | Second `is_seen=True`                     |
| Dedup hit by `company+title` (cross-source) | Different `canonical_id`, same composite key | `is_seen=True`                            |
| Dedup miss                                  | Both new                                     | `is_seen=False`, both indices written     |
| 14d cleanup removes 15d entry               | 15d-old                                      | Removed from both indices                 |
| 14d cleanup keeps 13d entry                 | 13d-old                                      | Still present                             |

### Phase 2 — Seniority

| Test              | Input                                      | Expected      |
| ----------------- | ------------------------------------------ | ------------- |
| L1 Entry level    | `seniorityLevel='Entry level'`             | PASS          |
| L1 Mid-Senior     | `seniorityLevel='Mid-Senior level'`        | REJECT        |
| L1 Internship     | `seniorityLevel='Internship'`              | REJECT        |
| L1 NA → L2 senior | `'Not Applicable'` + `title='Senior...'`   | REJECT via L2 |
| L2 Senior         | `title='Senior Software Engineer'`         | REJECT        |
| L2 New Grad       | `title='Software Engineer, New Grad 2026'` | PASS          |
| L2 SDE I          | `title='SDE I — Backend'`                  | PASS          |
| L2 L6             | `title='L6 Software Engineer'`             | REJECT        |
| L2 Unclear        | `title='Software Engineer'`                |
| UNCLEAR (defer)   |
| L3 0-2 YOE        | `yoe_required='0-2 years'`                 | PASS          |
| L3 5+ YOE         | `yoe_required='5+ years'`                  | REJECT        |
| L3 not specified  | `yoe_required='not specified'`             | PASS          |

### Phase 3 — Tech Stack

| Test          | Input                               | Expected |
| ------------- | ----------------------------------- | -------- |
| Pure embedded | `title='Embedded', jd='FPGA, VHDL'` | REJECT   |
| Pure hardware | `title='Hardware', jd='PCB design'` | REJECT   |
| C++ + web     | `jd='C++, Python, REST, AWS'`       | PASS     |
| Python only   | `jd='Python, Django, Postgres'`     | PASS     |
| ML            | `jd='ML, PyTorch'`                  | PASS     |
| No JD         | `jd=None`                           | PASS     |

### Phase 4 — Location, Industries, Expiry

| Test                | Input                                  | Expected |
| ------------------- | -------------------------------------- | -------- |
| country US          | `country='US'`                         | PASS     |
| country CA          | `country='CA'`                         | REJECT   |
| industries staffing | `industries='Staffing and Recruiting'` | REJECT   |
| industries software | `industries='Software Development'`    | PASS     |
| GH US city          | `locations=['New York, NY']`           | PASS     |
| GH Remote           | `locations=['Remote']`                 | PASS     |
| GH Canada only      | `locations=['Toronto, ON']`            | REJECT   |
| GH mixed US+non-US  | `locations=['Toronto', 'NYC']`         | PASS     |
| `expireAt` past     | `expireAt=now-1d`                      | REJECT   |
| `expireAt` future   | `expireAt=now+30d`                     | PASS     |
| `expireAt` missing  | no field                               | PASS     |

### Phase 5 — Scrapers

**GitHub:**

| Test                  | Scenario           | Expected                |
| --------------------- | ------------------ | ----------------------- |
| Fetch `listings.json` | Live GET           | Valid JSON array        |
| Parse fields          | Sample listing     | Dict with required keys |
| 48h filter            | Mix old/new        | Only ≤48h returned      |
| Skip inactive         | `active=false`     | Filtered                |
| Skip hidden           | `is_visible=false` | Filtered                |
| Missing url           | No url field       | Skipped gracefully      |

**LinkedIn (Apify):**

| Test                 | Scenario           | Expected                        |
| -------------------- | ------------------ | ------------------------------- |
| Run trigger          | Valid token + URLs | Run started, returns `runId`    |
| Poll completion      | Running run        | SUCCEEDED + dataset             |
| Parse all fields     | Sample (Epic-like) | All Section 4b fields extracted |
| Repost filter        | `repostedJob=true` | Filtered out                    |
| Multiple URLs merged | 4 search URLs      | Results combined                |
| API error            | Invalid token      | Clear exception                 |

### Phase 6 — JD Fetcher (GitHub only)

| Test            | Scenario       | Expected             |
| --------------- | -------------- | -------------------- |
| Plain HTML page | Public URL     | Text >200 chars      |
| 404             | Bad URL        | None, warning logged |
| Auth wall       | Login required | None, `no_jd=True`   |
| Timeout         | Slow URL       | None after 10s       |

### Phase 7 — Gemini Keyword Extractor

| Test                       | Scenario                        | Expected                                   |
| -------------------------- | ------------------------------- | ------------------------------------------ |
| Valid JD → JSON            | Real JD                         | Dict with all 7 fields incl. `visa_status` |
| `required_skills` is list  | Any JD                          | list of strings                            |
| Seniority entry            | `'0-2 years'` in JD             | `seniority_signal='entry-level'`           |
| visa no_sponsorship        | `'no visa sponsorship'` in JD   | `'no_sponsorship'`                         |
| visa TN-only               | `'TN status only'` in JD        | `'no_sponsorship'`                         |
| visa citizenship           | `'US citizens only'`            | `'requires_us_citizenship'`                |
| visa clearance             | `'security clearance required'` | `'requires_clearance'`                     |
| visa sponsorship_available | `'we sponsor visas'`            | `'sponsorship_available'`                  |
| visa vague "authorized"    | `'must be authorized to work'`  | `'not_mentioned'`                          |
| visa silent                | No statement                    | `'not_mentioned'`                          |
| API error                  | Invalid key                     | None, pipeline continues                   |
| Malformed JSON             | Bad output                      | Retry then None                            |
| Empty JD                   | `jd_text=''`                    | None without API call                      |

### Phase 8 — Visa Filter

| Test                      | Input                                   | Expected       |
| ------------------------- | --------------------------------------- | -------------- |
| `requires_us_citizenship` | `visa_status='requires_us_citizenship'` | REJECT         |
| `requires_clearance`      | `visa_status='requires_clearance'`      | REJECT         |
| `no_sponsorship`          | `visa_status='no_sponsorship'`          | REJECT         |
| `sponsorship_available`   | `visa_status='sponsorship_available'`   | PASS           |
| `not_mentioned`           | `visa_status='not_mentioned'`           | PASS           |
| missing `visa_status`     | no field                                | PASS (default) |

### Phase 9 — Priority + Sort

| Test                        | Scenario                        | Expected              |
| --------------------------- | ------------------------------- | --------------------- |
| Tier 1                      | `company='Google', has_jd=True` | 1                     |
| Tier 2                      | Unknown, 3/5 stack match        | 2                     |
| Tier 3                      | Unknown, 1/5 match              | 3                     |
| Tier 4                      | `has_jd=False`                  | 4                     |
| Coverage 4/6                | Stack=6, JD has 4               | 0.667                 |
| Coverage 0                  | JD has none                     | 0.0                   |
| Sort applicants ASC in tier | `[a=50, a=10, a=200]`           | `[10, 50, 200]`       |
| Coverage tiebreak           | Same applicants, diff coverage  | Higher coverage first |
| `posted_at` tiebreak        | Same applicants + coverage      | Newer first           |

### Phase 10 — Website Output

| Test                           | Scenario              | Expected                             |
| ------------------------------ | --------------------- | ------------------------------------ |
| Write history                  | Job list              | `data/history/YYYY-MM-DD.json` valid |
| `jobs_latest`                  | After write           | == today's history                   |
| `index.html` exists            | Sprint 1              | Static HTML present                  |
| `app.js` fetches `jobs_latest` | Open page             | Cards render                         |
| Card shows logo                | Job has `companyLogo` | `img` tag with URL                   |
| Card shows applicants          | Job has count         | `'57 applicants'` rendered           |
| Filter by tier                 | Click "Tier 1"        | Only Tier 1 visible                  |
| Filter visa sponsored          | Click filter          | Only `sponsorship_available`         |
| Sort by coverage               | Click sort            | Reordered                            |
| History page                   | Pick date             | `data/history/<date>.json` loaded    |

### Phase 11 — Integration / E2E

| Test                | Scenario               | Expected            |
| ------------------- | ---------------------- | ------------------- |
| Pipeline dry-run    | `main.py --dry-run`    | Prints, no commits  |
| Dedup across runs   | Run twice same day     | Second 0 new        |
| Blacklist respected | Add `'Google'`, run    | No Google in output |
| Visa reject flows   | JD with no sponsorship | Filtered, logged    |
| Expiry reject       | Inject expired         | Filtered, logged    |
| 14d cleanup         | Inject 15d-old         | Cleaned             |
| Actions trigger     | `workflow_dispatch`    | Completes, commits  |
| Pages serves        | Visit URL              | Page + data render  |

---

## 17. Instructions for Claude Code

- Read entire document before any code.
- Create directory structure (Section 15) as empty files first.
- Build ONE phase at a time (Section 16).
- After each phase: write all tests, run them, fix all failures before next phase.
- Do NOT start next phase until current phase tests all pass.
- Ask for `.env` values (`APIFY_TOKEN`, `GEMINI_API_KEY`) before Phase 5.
- Sprint 2 items (Section 18) are OUT OF SCOPE.

---

## 18. Sprint 2 — Out of Scope

- Email digest subscription
- Specific company targeting
- Web-based feedback (Blacklist button)
- `companyEmployeesCount` filter
- Application tracking
- Staffing auto-detection beyond exact match
- Resume PDF upload + keyword comparison
- Cloud DB migration
- Custom domain

---

## Changelog

**v3 → v3.1 (this update):**

- LinkedIn output fields documented from a real Apify response sample (Epic job)
- Dedup primary key changed from URL to `canonical_id` (`'linkedin:{id}'` or `'github:{sha1}'`)
- Cross-source dedup uses `normalize(company+title)`: lowercase + strip + remove punctuation + collapse whitespace
- Added expiry filter (`expireAt < now` → REJECT) as Step 3
- Added visa sponsorship filter — Gemini extracts `visa_status`; 3 values reject, 2 pass
- Gemini prompt extended with `visa_status` field + classification rules (TN-only → `no_sponsorship`; vague "must be authorized" → `not_mentioned`)
- Added storage of: `companyLogo`, `companyAddress`, `companyDescription`, `applicantsCount`, `workplaceTypes`
- Removed: `standardizedTitle` (using raw title only)
- Sort within tier: `applicantsCount` ASC → coverage DESC → `posted_at` DESC
- Website card adds: company logo, `applicantsCount`, visa chip; filter facet for `sponsorship_available`
- Test cases added for visa filter, expiry filter, normalize function, `canonical_id`, cross-source dedup

**v2 → v3 (previous):**

- Output: email digest → static GitHub Pages website
- LLM: Claude → Gemini Flash
- Storage: SQLite → JSON files
- Dedup window: 48h → 14 days
- Schedule: TBD → daily 18:00 UTC
- Deployment: local cron → GitHub Actions
- Feedback loop deferred to Sprint 2
