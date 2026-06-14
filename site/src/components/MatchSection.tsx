import { PREFERRED_STACK } from '../constants'
import { matchPercent, tierColor } from '../lib/utils'
import type { Job } from '../types'

interface MatchSectionProps {
  job: Job
}

export default function MatchSection({ job }: MatchSectionProps) {
  const pct = matchPercent(job)
  const color = tierColor(pct)
  const required = job.required_skills ?? []

  const matched = required.filter(s =>
    PREFERRED_STACK.some(p => p.toLowerCase() === s.toLowerCase())
  )
  const missing = required.filter(s =>
    !PREFERRED_STACK.some(p => p.toLowerCase() === s.toLowerCase())
  )

  return (
    <div className="rounded-lg p-4 bg-match-bg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[12px] font-medium text-chip-on-text">Stack match</span>
        <span className="text-[12px] font-semibold" style={{ color }}>{pct}%</span>
      </div>

      <div className="rounded-full overflow-hidden mb-3" style={{ height: 3, background: '#E0E0E0' }}>
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>

      {required.length === 0 ? (
        <p className="text-[11px] text-chip-text italic">No skills data available</p>
      ) : (
        <div className="flex flex-wrap gap-1">
          {matched.map(s => (
            <span
              key={s}
              className="text-[11px] px-2 py-0.5 rounded-full"
              style={{ background: '#EDF5E8', color: '#5A8A4A' }}
            >
              {s}
            </span>
          ))}
          {missing.map(s => (
            <span
              key={s}
              className="text-[11px] px-2 py-0.5 rounded-full"
              style={{
                border: '1px dashed #C4C4C4',
                color: '#909090',
                background: 'transparent',
              }}
            >
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
