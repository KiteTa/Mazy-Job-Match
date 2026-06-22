import { useEffect, useRef, useState } from 'react'
import { SORT_OPTIONS } from '../constants'
import { jobKey } from '../lib/utils'
import type { Job, SortOption } from '../types'
import JobRow from './JobRow'

interface JobListProps {
  jobs: Job[]
  selectedId: string | null
  onSelect: (id: string) => void
  onApply: (job: Job) => void
  onBlacklist: (company: string) => void
  sort: SortOption
  onSortChange: (s: SortOption) => void
}

export default function JobList({
  jobs,
  selectedId,
  onSelect,
  onApply,
  onBlacklist,
  sort,
  onSortChange,
}: JobListProps) {
  return (
    <div
      className="flex flex-col bg-cream h-full"
      style={{ width: '100%' }}
    >
      {/* Sort header */}
      <div
        className="flex items-center justify-end px-2 py-1 shrink-0"
        style={{ borderBottom: '0.5px solid #E2E2E2', minHeight: 30 }}
      >
        <SortButton sort={sort} onChange={onSortChange} />
      </div>

      {/* List body */}
      {jobs.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-1.5 text-center px-6">
          <p className="text-[13px] text-[#2D2A26]">No matches</p>
          <p className="text-[11px] text-chip-text leading-relaxed">
            Clear a filter or broaden your location.
          </p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {jobs.map(job => (
            <JobRow
              key={jobKey(job)}
              job={job}
              selected={jobKey(job) === selectedId}
              onSelect={() => onSelect(jobKey(job))}
              onApply={() => onApply(job)}
              onBlacklist={onBlacklist}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function SortButton({ sort, onChange }: { sort: SortOption; onChange: (s: SortOption) => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    function keyHandler(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('keydown', keyHandler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('keydown', keyHandler)
    }
  }, [])

  const label = SORT_OPTIONS.find(o => o.value === sort)?.label ?? 'Latest'

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        title={`Sort: ${label}`}
        className="flex items-center gap-1 px-1.5 py-0.5 rounded text-chip-text hover:text-chip-on-text hover:bg-chip-on transition-colors"
      >
        <SortIcon />
        <span className="text-[10.5px]">{label}</span>
      </button>

      {open && (
        <div className="dropdown-menu absolute top-full right-0 mt-1 bg-parchment border border-sand rounded-lg shadow-md z-50 py-1 min-w-[130px]">
          {SORT_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => { onChange(opt.value as SortOption); setOpen(false) }}
              className={[
                'w-full text-left px-3 py-1.5 text-[11.5px] hover:bg-cream transition-colors',
                sort === opt.value ? 'text-chip-on-text font-medium' : 'text-chip-text',
              ].join(' ')}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function SortIcon() {
  return (
    <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
      <path d="M1 2h10M1 5h7M1 8h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}
