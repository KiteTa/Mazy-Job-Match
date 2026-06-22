import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { DEFAULT_FILTERS } from './constants'
import { applyFilters, getJobDate, isNew, jobKey } from './lib/utils'
import { addAppliedId, addToBlacklist, getAppliedIds, getApplyCount, getBlacklist, saveApplyCount } from './lib/storage'
import { supabase } from './lib/supabase'
import type { Filters, Job } from './types'
import DetailPane from './components/DetailPane'
import FilterBar from './components/FilterBar'
import Header from './components/Header'
import JobList from './components/JobList'

export default function App() {
  const [jobs, setJobs] = useState<Job[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [applyCount, setApplyCount] = useState<number>(() => getApplyCount())
  const [blacklist, setBlacklist] = useState<Set<string>>(() => getBlacklist())
  const [hiddenIds, setHiddenIds] = useState<Set<string>>(() => getAppliedIds())
  const [listWidth, setListWidth] = useState(260)
  const isDragging = useRef(false)
  const dragStart = useRef({ x: 0, width: 0 })

  const startResize = useCallback((e: React.MouseEvent) => {
    isDragging.current = true
    dragStart.current = { x: e.clientX, width: listWidth }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [listWidth])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isDragging.current) return
      const newW = Math.max(180, Math.min(480, dragStart.current.width + e.clientX - dragStart.current.x))
      setListWidth(newW)
    }
    const onUp = () => {
      isDragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [])

  useEffect(() => {
    supabase
      .from('jobs')
      .select('*')
      .eq('active', true)
      .order('published_at', { ascending: false })
      .then(({ data, error }) => {
        if (error) setError(error.message)
        else setJobs((data as Job[]) ?? [])
      })
  }, [])

  const visibleJobs = useMemo<Job[]>(() => {
    if (!jobs) return []
    return jobs.filter(job => {
      if (blacklist.has(job.company)) return false
      if (hiddenIds.has(jobKey(job))) return false
      return true
    })
  }, [jobs, blacklist, hiddenIds])

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

  if (!jobs) {
    return (
      <div className="h-screen flex flex-col overflow-hidden bg-cream">
        <div style={{ height: 44, background: '#A8D8D0', borderBottom: '0.5px solid #8ECAC0' }} />
        <div className="flex flex-1 overflow-hidden">
          <div className="shrink-0 overflow-y-auto bg-cream" style={{ width: listWidth, borderRight: '0.5px solid #E2E2E2' }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="px-3 py-2.5 skeleton" style={{ borderBottom: '0.5px solid #E2E2E2', minHeight: 64 }}>
                <div className="h-3 rounded mb-1.5" style={{ width: `${60 + (i % 3) * 15}%`, background: '#E0E0E0' }} />
                <div className="h-2.5 rounded mb-2" style={{ width: '45%', background: '#EEEEEE' }} />
                <div className="h-2 rounded" style={{ width: '30%', background: '#EEEEEE' }} />
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
        <div style={{ width: listWidth, flexShrink: 0 }}>
          <JobList
            jobs={filteredJobs}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onApply={handleApply}
            onBlacklist={handleBlacklist}
            sort={filters.sort}
            onSortChange={s => setFilters(f => ({ ...f, sort: s }))}
          />
        </div>

        <div className="resize-handle" onMouseDown={startResize} />

        <DetailPane job={selectedJob} onApply={handleApply} />
      </div>
    </div>
  )
}
