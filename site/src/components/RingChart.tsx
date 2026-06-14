const R = 21
const STROKE = 4
const C = 2 * Math.PI * R

interface RingChartProps {
  pct: number
  color: string
}

export default function RingChart({ pct, color }: RingChartProps) {
  const dash = (pct / 100) * C
  return (
    <div className="relative" style={{ width: 52, height: 52 }}>
      <svg
        width={52}
        height={52}
        style={{ transform: 'rotate(-90deg)', display: 'block' }}
      >
        <circle cx={26} cy={26} r={R} fill="none" stroke="#E0E0E0" strokeWidth={STROKE} />
        <circle
          cx={26}
          cy={26}
          r={R}
          fill="none"
          stroke={color}
          strokeWidth={STROKE}
          strokeDasharray={`${dash} ${C}`}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-[11px] font-bold leading-none" style={{ color }}>
          {pct}%
        </span>
        <span className="text-[9px] leading-none mt-0.5 text-gray-400">match</span>
      </div>
    </div>
  )
}
