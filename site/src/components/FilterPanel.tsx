import type { ReactNode } from 'react'
import type { Filters } from '../types'

interface FilterPanelProps {
  filters: Filters
  onChange: (f: Filters) => void
}

const WORK_TYPES = ['Onsite', 'Remote', 'Hybrid']
const JOB_TYPES  = ['Full-time', 'Part-time', 'Contract']

export default function FilterPanel({ filters, onChange }: FilterPanelProps) {
  function toggleList(key: 'workTypes' | 'jobTypes', val: string) {
    const cur = filters[key]
    const next = cur.includes(val) ? cur.filter(x => x !== val) : [...cur, val]
    onChange({ ...filters, [key]: next })
  }

  const hasAny =
    filters.workTypes.length > 0 || filters.jobTypes.length > 0 || filters.sponsorOnly

  function clearAll() {
    onChange({ ...filters, workTypes: [], jobTypes: [], sponsorOnly: false })
  }

  return (
    <div
      className="dropdown-menu absolute top-full left-0 mt-1 bg-parchment border border-sand rounded-xl shadow-lg z-50"
      style={{ minWidth: 296, padding: '14px 16px 12px' }}
    >
      <Row label="Work type">
        {WORK_TYPES.map(opt => (
          <Pill
            key={opt}
            active={filters.workTypes.includes(opt.toLowerCase())}
            onClick={() => toggleList('workTypes', opt.toLowerCase())}
          >
            {opt}
          </Pill>
        ))}
      </Row>

      <div className="my-3" style={{ height: '0.5px', background: '#E2E2E2' }} />

      <Row label="Job type">
        {JOB_TYPES.map(opt => (
          <Pill
            key={opt}
            active={filters.jobTypes.includes(opt.toLowerCase())}
            onClick={() => toggleList('jobTypes', opt.toLowerCase())}
          >
            {opt}
          </Pill>
        ))}
      </Row>

      <div className="my-3" style={{ height: '0.5px', background: '#E2E2E2' }} />

      <Row label="Visa">
        <Pill
          active={filters.sponsorOnly}
          onClick={() => onChange({ ...filters, sponsorOnly: !filters.sponsorOnly })}
        >
          Sponsor only
        </Pill>
      </Row>

      {hasAny && (
        <div className="mt-3 pt-3 flex justify-end" style={{ borderTop: '0.5px solid #E2E2E2' }}>
          <button
            onClick={clearAll}
            className="text-[11px] text-chip-text hover:text-chip-on-text transition-colors"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  )
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] text-chip-text w-14 shrink-0">{label}</span>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </div>
  )
}

function Pill({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={[
        'px-3 py-1 rounded-full text-[11px] border transition-colors duration-150',
        active
          ? 'bg-level-fill border-level-fill text-white'
          : 'bg-parchment border-sand text-chip-text hover:border-chip-on-border hover:text-chip-on-text',
      ].join(' ')}
      style={{ borderWidth: '1px' }}
    >
      {children}
    </button>
  )
}
