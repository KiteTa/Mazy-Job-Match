import { useEffect, useRef, useState } from 'react'
import { getJobDate, isNew, matchPercent, tierColor, timeAgo } from '../lib/utils'
import type { Job } from '../types'

interface JobRowProps {
  job: Job
  selected: boolean
  onSelect: () => void
  onApply: () => void
  onBlacklist: (company: string) => void
}

export default function JobRow({ job, selected, onSelect, onBlacklist }: Omit<JobRowProps, 'onApply'> & { onApply?: () => void }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const pct = matchPercent(job)
  const color = tierColor(pct)
  const date = getJobDate(job)
  useEffect(() => {
    if (!menuOpen) return
    function handler(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  const locationText = job.location
    ?? (job.locations?.length ? job.locations[0] : null)
    ?? ''

  return (
    <div
      onClick={onSelect}
      className={[
        'flex items-stretch cursor-pointer group relative transition-colors duration-100',
        selected ? 'bg-row-selected' : 'hover:bg-row-hover',
      ].join(' ')}
      style={{ borderBottom: '0.5px solid #C8D9D8', minHeight: 64 }}
    >
      {/* Content */}
      <div className="flex-1 min-w-0 px-3 py-2.5">
        <p
          className="truncate text-[13px] font-medium text-[#2D2A26] leading-tight mb-0.5"
          title={job.title}
        >
          {job.title}
        </p>
        <p className="text-[11px] text-chip-text truncate mb-1.5">
          <span
            className="inline-block w-1.5 h-1.5 rounded-full mr-1.5 translate-y-[-1px]"
            style={{ background: color }}
            aria-hidden="true"
          />
          {job.company}
          {locationText ? ` · ${locationText}` : ''}
        </p>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-chip-text">{timeAgo(date)}</span>
          {isNew(date) && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
              style={{ background: '#EDF5E8', color: '#5A8A4A' }}
            >
              New
            </span>
          )}
          {job.sponsors_visa && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
              style={{ background: '#EAE6F5', color: '#6B5FA8' }}
            >
              Sponsor
            </span>
          )}
        </div>
      </div>

      {/* Context menu */}
      <div
        className="relative flex items-start pt-2.5 pr-2 opacity-0 group-hover:opacity-100 transition-opacity"
        ref={menuRef}
      >
        <button
          onClick={e => {
            e.stopPropagation()
            setMenuOpen(v => !v)
          }}
          aria-label="Job options"
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          className="w-5 h-5 flex items-center justify-center rounded text-chip-text hover:text-[#2D2A26] hover:bg-sand/60 transition-colors"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <path d="M2 2l6 6M8 2l-6 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
        </button>

        {menuOpen && (
          <div
            role="menu"
            className="dropdown-menu absolute top-7 right-0 bg-parchment border border-sand rounded-lg shadow-md z-50 py-1 min-w-[140px]"
            onClick={e => e.stopPropagation()}
          >
            <button
              role="menuitem"
              className="w-full text-left px-3 py-1.5 text-[11.5px] text-chip-text hover:bg-cream hover:text-[#2D2A26] transition-colors"
              onClick={() => {
                setMenuOpen(false)
                onBlacklist(job.company)
              }}
            >
              Hide this company
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
