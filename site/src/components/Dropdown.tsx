import { useEffect, useRef, useState } from 'react'

interface Option {
  value: string
  label: string
}

interface DropdownProps {
  label: string
  options: Option[]
  selected: string[]
  onChange: (selected: string[]) => void
  multi?: boolean
  clearable?: boolean
}

export default function Dropdown({
  label,
  options,
  selected,
  onChange,
  multi = false,
  clearable = true,
}: DropdownProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [])

  function toggle(value: string) {
    if (multi) {
      onChange(
        selected.includes(value)
          ? selected.filter(s => s !== value)
          : [...selected, value]
      )
    } else {
      if (selected[0] === value) {
        if (clearable) onChange([])
      } else {
        onChange([value])
        setOpen(false)
      }
    }
  }

  const isActive = selected.length > 0

  // Multi-select with 2+ items: show compact "Label · N" instead of truncated list
  const displayLabel =
    selected.length === 0
      ? label
      : multi && selected.length > 1
        ? `${label} · ${selected.length}`
        : options.filter(o => selected.includes(o.value)).map(o => o.label).join(', ')

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className={[
          'flex items-center gap-1 px-2.5 py-1 rounded-full text-[11.5px] border transition-colors',
          isActive
            ? 'bg-chip-on border-chip-on-border text-chip-on-text'
            : 'bg-chip border-chip-border text-chip-text hover:bg-chip-on',
        ].join(' ')}
        style={{ borderWidth: '0.5px' }}
      >
        <span className="max-w-[120px] truncate">{displayLabel}</span>
        <svg
          width="8"
          height="5"
          viewBox="0 0 8 5"
          fill="none"
          className={[
            'shrink-0 opacity-50 transition-transform duration-150',
            open ? 'rotate-180' : '',
          ].join(' ')}
        >
          <path d="M1 1l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        </svg>
      </button>

      {open && (
        <div
          role="listbox"
          className="dropdown-menu absolute top-full left-0 mt-1 bg-parchment border border-sand rounded-lg shadow-md z-50 min-w-[130px] py-1"
        >
          {options.map(opt => {
            const checked = selected.includes(opt.value)
            return (
              <button
                key={opt.value}
                role="option"
                aria-selected={checked}
                onClick={() => toggle(opt.value)}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-left text-[11.5px] hover:bg-cream transition-colors"
              >
                {multi && (
                  <span
                    className={[
                      'w-3 h-3 rounded border shrink-0 flex items-center justify-center',
                      checked ? 'bg-level-fill border-level-fill' : 'border-chip-border',
                    ].join(' ')}
                  >
                    {checked && (
                      <svg width="7" height="5" viewBox="0 0 7 5" fill="none">
                        <path d="M1 2.5l1.5 1.5L6 1" stroke="white" strokeWidth="1.2" strokeLinecap="round" />
                      </svg>
                    )}
                  </span>
                )}
                <span className={checked ? 'text-chip-on-text font-medium' : 'text-chip-text'}>
                  {opt.label}
                </span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
