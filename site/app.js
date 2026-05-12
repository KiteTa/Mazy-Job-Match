/* Mazy Job Match — client-side filter/sort logic */

const DATA_URL = 'data/jobs_latest.json';

const TIER_BADGES = {
  1: '🔥 Top Pick',
  2: '⭐ Good Match',
  3: '📋 Check It Out',
  4: '🔗 No JD',
};

let ALL_JOBS = [];

// ── boot ────────────────────────────────────────────────────────────────────

async function init() {
  try {
    const resp = await fetch(DATA_URL);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    renderHeader(data);
    ALL_JOBS = data.jobs || [];
    renderFiltered();
  } catch (err) {
    document.getElementById('job-list').innerHTML =
      `<p class="empty">Could not load jobs: ${err.message}</p>`;
  }
}

// ── header ───────────────────────────────────────────────────────────────────

function renderHeader(data) {
  const s = data.stats || {};
  const ts = data.run_timestamp
    ? data.run_timestamp.replace('T', ' ').replace('Z', ' UTC')
    : '';
  document.getElementById('stats').textContent =
    `Updated: ${ts} · ${s.total_scraped || 0} scraped → ${s.after_filters || 0} shown` +
    (s.by_tier ? ` (${Object.entries(s.by_tier).map(([k,v])=>`T${k}:${v}`).join(' ')})` : '');

  const stackEl = document.getElementById('stack-chips');
  // PREFERRED_STACK baked in from config
  const stack = ['Python','TypeScript','JavaScript','React','Node','FastAPI','ML','LLM','cloud','AWS','distributed'];
  stackEl.innerHTML = stack.map(t => `<span class="chip">${t}</span>`).join('');
}

// ── filter + sort ─────────────────────────────────────────────────────────────

function renderFiltered() {
  const q = document.getElementById('search').value.trim().toLowerCase();
  const tiers = new Set(
    [...document.querySelectorAll('.tier-filter:checked')].map(el => Number(el.value))
  );
  const srcs = new Set(
    [...document.querySelectorAll('.src-filter:checked')].map(el => el.value)
  );
  const domain = document.getElementById('domain-filter').value;
  const jdOnly = document.getElementById('jd-filter').checked;
  const visaOnly = document.getElementById('visa-filter').checked;
  const sortBy = document.getElementById('sort-select').value;

  let jobs = ALL_JOBS.filter(j => {
    if (!tiers.has(j.priority_tier)) return false;
    if (!srcs.has(j.source)) return false;
    if (domain && (j.keywords?.domain || '') !== domain) return false;
    if (jdOnly && !j.has_jd) return false;
    if (visaOnly && j.keywords?.visa_status !== 'sponsorship_available') return false;
    if (q && !`${j.title} ${j.company}`.toLowerCase().includes(q)) return false;
    return true;
  });

  if (sortBy !== 'default') {
    jobs = [...jobs].sort((a, b) => {
      if (sortBy === 'coverage') return (b.keyword_coverage || 0) - (a.keyword_coverage || 0);
      if (sortBy === 'posted') return (b.posted_at || '') > (a.posted_at || '') ? 1 : -1;
      if (sortBy === 'company') return (a.company || '').localeCompare(b.company || '');
      if (sortBy === 'applicants') return parseApplicants(a.applicants_count) - parseApplicants(b.applicants_count);
      return 0;
    });
  }

  renderJobs(jobs);
}

function parseApplicants(val) {
  if (val == null) return 0;
  const n = parseInt(String(val).replace(/,/g, ''));
  return isNaN(n) ? 0 : n;
}

// ── render jobs ───────────────────────────────────────────────────────────────

function renderJobs(jobs) {
  const list = document.getElementById('job-list');
  if (!jobs.length) {
    list.innerHTML = '<p class="empty">No jobs match your filters.</p>';
    return;
  }
  list.innerHTML = jobs.map(jobCard).join('');
  list.querySelectorAll('.toggle-jd').forEach(btn => {
    btn.addEventListener('click', () => {
      const jd = btn.closest('.job-card').querySelector('.jd-text');
      if (jd) {
        jd.hidden = !jd.hidden;
        btn.textContent = jd.hidden ? 'Show JD' : 'Hide JD';
      }
    });
  });
}

function jobCard(job) {
  const badge = TIER_BADGES[job.priority_tier] || '';
  const kw = job.keywords || {};

  const logo = job.company_logo
    ? `<img class="logo" src="${job.company_logo}" alt="" onerror="this.style.display='none'">`
    : '<div class="logo-placeholder"></div>';

  const skills = [
    ...(kw.required_skills || []).map(s => `<span class="chip">${s}</span>`),
    ...(kw.preferred_skills || []).map(s => `<span class="chip" style="opacity:.7">${s}</span>`),
  ].slice(0, 10).join('');

  const visaChip = kw.visa_status === 'sponsorship_available'
    ? '<span class="chip visa">Visa Sponsor</span>'
    : '';

  const domainChip = kw.domain ? `<span class="chip">${kw.domain}</span>` : '';

  const coverage = job.keyword_coverage != null
    ? `<span class="chip coverage">${Math.round(job.keyword_coverage * 100)}% stack match</span>`
    : '';

  const loc = job.location || (job.locations || []).join(', ') || '';
  const meta = [
    job.source,
    loc,
    job.posted_at ? 'Posted ' + job.posted_at.slice(0, 10) : '',
    job.applicants_count ? job.applicants_count + ' applicants' : '',
  ].filter(Boolean).join(' · ');

  const applyBtn = job.apply_url
    ? `<a href="${job.apply_url}" target="_blank" rel="noopener" class="btn-apply">Apply</a>`
    : '';

  const jdSection = job.description_text
    ? `<button class="toggle-jd">Show JD</button>
       <p class="jd-text" hidden>${escHtml(job.description_text.slice(0, 3000))}${job.description_text.length > 3000 ? '…' : ''}</p>`
    : '';

  return `<div class="job-card tier-${job.priority_tier}">
  <div class="card-top">
    ${logo}
    <div class="card-main">
      <div class="tier-badge">${badge}</div>
      <div class="job-title">${escHtml(job.title)}</div>
      <div class="job-company">${escHtml(job.company)}</div>
      <div class="job-meta">${escHtml(meta)}</div>
      <div class="chips-row">${visaChip}${domainChip}${skills}${coverage}</div>
    </div>
    <div class="card-actions">${applyBtn}</div>
  </div>
  ${jdSection}
</div>`;
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── event listeners ───────────────────────────────────────────────────────────

document.getElementById('search').addEventListener('input', renderFiltered);
document.querySelectorAll('.tier-filter, .src-filter').forEach(el =>
  el.addEventListener('change', renderFiltered)
);
document.getElementById('domain-filter').addEventListener('change', renderFiltered);
document.getElementById('jd-filter').addEventListener('change', renderFiltered);
document.getElementById('visa-filter').addEventListener('change', renderFiltered);
document.getElementById('sort-select').addEventListener('change', renderFiltered);

init();
