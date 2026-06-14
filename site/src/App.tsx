import { useEffect, useMemo, useState } from 'react'
import { DEFAULT_FILTERS } from './constants'
import { applyFilters, getJobDate, isNew, jobKey } from './lib/utils'
import { addAppliedId, addToBlacklist, getAppliedIds, getApplyCount, getBlacklist, saveApplyCount } from './lib/storage'
import type { Filters, Job, JobsData } from './types'
import DetailPane from './components/DetailPane'
import FilterBar from './components/FilterBar'
import Header from './components/Header'
import JobList from './components/JobList'

const CUTOFF_MS = 48 * 3600 * 1000

export default function App() {
  const [jobsData, setJobsData] = useState<JobsData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [applyCount, setApplyCount] = useState<number>(() => getApplyCount())
  const [blacklist, setBlacklist] = useState<Set<string>>(() => getBlacklist())
  const [hiddenIds, setHiddenIds] = useState<Set<string>>(() => getAppliedIds())

  useEffect(() => {
    fetch('/jobs_latest.json')
      .then(r => r.json())
      .then((d: JobsData) => setJobsData(d))
      .catch(err => setError(String(err)))
  }, [])

  const visibleJobs = useMemo<Job[]>(() => {
    if (!jobsData) return []
    const cutoff = Date.now() - CUTOFF_MS
    return jobsData.jobs.filter(job => {
      const date = getJobDate(job)
      if (date && new Date(date).getTime() < cutoff) return false
      if (blacklist.has(job.company)) return false
      if (hiddenIds.has(jobKey(job))) return false
      return true
    })
  }, [jobsData, blacklist, hiddenIds])

  const filteredJobs = useMemo(() => applyFilters(visibleJobs, filters), [visibleJobs, filters])

  const newTodayCount = useMemo(
    () => visibleJobs.filter(j => isNew(getJobDate(j))).length,
    [visibleJobs]
  )

  const selectedJob = useMemo(
    () => filteredJobs.find(j => jobKey(j) === selectedId) ?? null,
    [filteredJobs, selectedId]
  )

  // j/k and arrow key navigation
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault()
        setSelectedId(prev => {
          const idx = filteredJobs.findIndex(j => jobKey(j) === prev)
          const next = filteredJobs[idx + 1]
          return next ? jobKey(next) : prev
        })
      }
      if (e.key === 'ArrowUp' || e.key === 'k') {
        e.preventDefault()
        setSelectedId(prev => {
          const idx = filteredJobs.findIndex(j => jobKey(j) === prev)
          const prev2 = filteredJobs[idx - 1]
          return prev2 ? jobKey(prev2) : prev
        })
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [filteredJobs])

  function handleApply(job: Job) {
    const key = jobKey(job)
    addAppliedId(key)
    setHiddenIds(prev => { const s = new Set(prev); s.add(key); return s })

    const next = applyCount + 1
    saveApplyCount(next)
    setApplyCount(next)

    if (selectedId === key) {
      const idx = filteredJobs.findIndex(j => jobKey(j) === key)
      const nextJob = filteredJobs[idx + 1] ?? filteredJobs[idx - 1] ?? null
      setSelectedId(nextJob ? jobKey(nextJob) : null)
    }
  }

  function handleBlacklist(company: string) {
    addToBlacklist(company)
    setBlacklist(prev => { const s = new Set(prev); s.add(company); return s })
    if (selectedJob?.company === company) setSelectedId(null)
  }

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-cream">
        <p className="text-[13px] text-red-500">Failed to load jobs: {error}</p>
      </div>
    )
  }

  if (!jobsData) {
    return (
      <div className="h-screen flex flex-col overflow-hidden bg-cream">
        <div style={{ height: 44, background: '#A8D8D0', borderBottom: '0.5px solid #8ECAC0' }} />
        <div className="flex flex-1 overflow-hidden">
          <div className="shrink-0 overflow-y-auto bg-cream" style={{ width: 260, borderRight: '0.5px solid #C8D9D8' }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="px-3 py-2.5 skeleton" style={{ borderBottom: '0.5px solid #C8D9D8', minHeight: 64 }}>
                <div className="h-3 rounded mb-1.5" style={{ width: `${60 + (i % 3) * 15}%`, background: '#C8D9D8' }} />
                <div className="h-2.5 rounded mb-2" style={{ width: '45%', background: '#DFF0EE' }} />
                <div className="h-2 rounded" style={{ width: '30%', background: '#DFF0EE' }} />
              </div>
            ))}
          </div>
          <div className="flex-1 flex items-center justify-center bg-parchment">
            <p className="text-[13px] text-chip-text">Loading jobs…</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-cream">
      <Header newTodayCount={newTodayCount} applyCount={applyCount} />

      <FilterBar
        filters={filters}
        onChange={setFilters}
        totalCount={filteredJobs.length}
      />

      <div className="flex flex-1 overflow-hidden">
        <JobList
          jobs={filteredJobs}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onApply={handleApply}
          onBlacklist={handleBlacklist}
          sort={filters.sort}
          onSortChange={s => setFilters(f => ({ ...f, sort: s }))}
        />

        <DetailPane job={selectedJob} onApply={handleApply} />
      </div>
    </div>
  )
}
