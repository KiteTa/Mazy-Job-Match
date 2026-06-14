import { getLevelInfo } from '../lib/utils'

interface HeaderProps {
  newTodayCount: number
  applyCount: number
}

export default function Header({ newTodayCount, applyCount }: HeaderProps) {
  const { level, current, threshold } = getLevelInfo(applyCount)
  const fillPct = threshold > 0 ? Math.min(current / threshold, 1) : 0

  return (
    <header
      className="flex items-center justify-between px-4 shrink-0"
      style={{ height: 44, background: '#A8D8D0', borderBottom: '0.5px solid #8ECAC0' }}
    >
      {/* Left */}
      <div className="flex items-center gap-3 text-[12px] text-[#1E3A36]">
        <span className="font-serif text-[18px] tracking-tight">MazyJobs</span>
        <Divider />
        <span>
          <span className="font-semibold">{newTodayCount}</span> new today
        </span>
        <Divider />
        <span>
          <span className="font-semibold">{applyCount}</span> applied
        </span>
      </div>

      {/* Right */}
      <div className="flex items-center gap-2">
        <span
          className="text-[#1E3A36] text-[11px] font-semibold px-1.5 py-0.5 rounded"
          style={{ background: 'rgba(255,255,255,0.5)', borderRadius: 4 }}
        >
          Lv {level}
        </span>

        <div
          className="rounded-full overflow-hidden"
          style={{ width: 96, height: 7, background: 'rgba(255,255,255,0.35)' }}
          title={`${current} / ${threshold} applications to next level`}
        >
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${fillPct * 100}%`, background: '#1E3A36' }}
          />
        </div>

        <span className="text-[11px] text-[#1E3A36]/60">
          {current}/{threshold}
        </span>
      </div>
    </header>
  )
}

function Divider() {
  return <span className="opacity-30 select-none">|</span>
}
