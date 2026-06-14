import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { LOCATION_OPTIONS } from '../constants'
import type { Filters } from '../types'
import Dropdown from './Dropdown'
import FilterPanel from './FilterPanel'

interface FilterBarProps {
  filters: Filters
  onChange: (f: Filters) => void
  totalCount: number
}

export default function FilterBar({ filters, onChange, totalCount }: FilterBarProps) {
  const [panelOpen, setPanelOpen] = useState(false)
  const filterRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setPanelOpen(false)
      }
    }
    function keyHandler(e: KeyboardEvent) {
      if (e.key === 'Escape') setPanelOpen(false)
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('keydown', keyHandler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('keydown', keyHandler)
    }
  }, [])

  function set<K extends keyof Filters>(key: K, value: Filters[K]) {
    onChange({ ...filters, [key]: value })
  }

  function handleLocationChange(selected: string[]) {
    const hadUs = filters.locations.includes('us')
    const hasUs = selected.includes('us')
    if (hasUs && !hadUs) {
      onChange({ ...filters, locations: ['us'] })
    } else if (!hasUs && hadUs) {
      onChange({ ...filters, locations: selected.filter(x => x !== 'us') })
    } else if (hasUs && hadUs && selected.some(x => x !== 'us')) {
      onChange({ ...filters, locations: selected.filter(x => x !== 'us') })
    } else {
      onChange({ ...filters, locations: selected })
    }
  }

  const subFilterCount =
    filters.workTypes.length + filters.jobTypes.length + (filters.sponsorOnly ? 1 : 0)
  const filterActive = subFilterCount > 0

  const anyActive =
    filters.locations.length > 0 ||
    filters.companyType !== 'all' ||
    filters.past24h ||
    filterActive

  function clearAll() {
    onChange({
      ...filters,
      locations: [],
      companyType: 'all',
      workTypes: [],
      jobTypes: [],
      past24h: false,
      sponsorOnly: false,
    })
    setPanelOpen(false)
  }

  return (
    <div
      className="flex items-center gap-2 px-4 py-2 shrink-0 flex-wrap"
      style={{ background: '#F7F7F7', borderBottom: '0.5px solid #E2E2E2' }}
    >
      <Dropdown
        label="Location"
        options={LOCATION_OPTIONS}
        selected={filters.locations}
        onChange={handleLocationChange}
        multi
      />

      <Dropdown
        label="Company"
        options={[
          { value: 'faang', label: 'FAANG' },
          { value: 'other', label: 'Other' },
        ]}
        selected={filters.companyType === 'all' ? [] : [filters.companyType]}
        onChange={v => set('companyType', (v[0] as Filters['companyType']) ?? 'all')}
      />

      <ToggleChip active={filters.past24h} onClick={() => onChange({ ...filters, past24h: !filters.past24h })}>
        Past 24h
      </ToggleChip>

      {/* Filter panel trigger */}
      <div ref={filterRef} className="relative">
        <ToggleChip active={filterActive || panelOpen} onClick={() => setPanelOpen(v => !v)}>
          Filter{filterActive ? ` · ${subFilterCount}` : ''}
        </ToggleChip>
        {panelOpen && <FilterPanel filters={filters} onChange={onChange} />}
      </div>

      <span className="ml-auto flex items-center gap-3">
        {anyActive && (
          <button
            onClick={clearAll}
            className="text-[11px] text-chip-text hover:text-chip-on-text transition-colors"
          >
            Reset
          </button>
        )}
        <span className="text-[11px] text-chip-text">{totalCount} jobs</span>
      </span>
    </div>
  )
}

function ToggleChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={[
        'px-2.5 py-1 rounded-full text-[11.5px] border transition-colors',
        active
          ? 'bg-chip-on border-chip-on-border text-chip-on-text'
          : 'bg-chip border-chip-border text-chip-text hover:bg-chip-on',
      ].join(' ')}
      style={{ borderWidth: '0.5px' }}
    >
      {children}
    </button>
  )
}
