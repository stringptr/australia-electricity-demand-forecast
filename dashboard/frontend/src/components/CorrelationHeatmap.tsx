import React, { useState } from 'react'
import type { CorrelationResult } from '../types'

interface CorrelationHeatmapProps {
  data: CorrelationResult[]
}

const ITEMS = [
  { key: 'temperature_2m', label: 'Temp' },
  { key: 'relative_humidity_2m', label: 'Humidity' },
  { key: 'precipitation', label: 'Precip' },
  { key: 'cloud_cover', label: 'Cloud' },
  { key: 'wind_speed_10m', label: 'Wind' },
  { key: 'shortwave_radiation', label: 'Solar' },
]

function getHeatColor(r: number | null): string {
  if (r === null) return '#3f3f46'
  const abs = Math.abs(r)
  if (abs < 0.05) return '#3f3f46'
  if (r > 0) {
    if (abs > 0.7) return '#E8402B'
    if (abs > 0.4) return '#F2A541'
    if (abs > 0.2) return '#F4D35E'
    return '#52525b'
  }
  if (abs > 0.7) return '#1e3a5f'
  if (abs > 0.4) return '#2563eb'
  if (abs > 0.2) return '#93c5fd'
  return '#52525b'
}

function getStrength(r: number | null): string {
  if (r === null) return '—'
  const abs = Math.abs(r)
  if (abs > 0.7) return 'strong'
  if (abs > 0.4) return 'moderate'
  if (abs > 0.2) return 'weak'
  return 'negligible'
}

const CorrelationHeatmap: React.FC<CorrelationHeatmapProps> = ({ data }) => {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; label: string; r: number | null } | null>(null)

  if (!data || data.length === 0) return null

  const lookup = new Map(data.map(d => [d.variable, d]))

  return (
    <div className="bg-void/40 border border-grid p-3 relative">
      <div className="grid grid-cols-6 gap-1">
        {ITEMS.map(item => {
          const entry = lookup.get(item.key)
          const r = entry?.r ?? null
          const color = getHeatColor(r)
          const strength = getStrength(r)

          return (
            <div
              key={item.key}
              className="flex flex-col items-center justify-center p-3 cursor-default transition-opacity hover:opacity-80"
              style={{ backgroundColor: r !== null ? `${color}22` : 'transparent' }}
              onMouseEnter={(e) => {
                const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
                setTooltip({ x: rect.left + rect.width / 2, y: rect.top - 8, label: entry?.variable_label || item.key, r })
              }}
              onMouseLeave={() => setTooltip(null)}
            >
              <div className="text-[10px] font-mono text-tactical-muted uppercase tracking-wider mb-1.5">
                {item.label}
              </div>
              <div
                className="w-full h-6 flex items-center justify-center rounded mb-1"
                style={{ backgroundColor: color }}
              >
                <span className="text-[11px] font-mono font-bold text-white mix-blend-difference">
                  {r !== null ? (r >= 0 ? '+' : '') + r.toFixed(2) : '—'}
                </span>
              </div>
              <div className="text-[9px] font-mono text-tactical-muted uppercase tracking-wider">
                {strength}
              </div>
            </div>
          )
        })}
      </div>

      {tooltip && (
        <div
          className="fixed z-50 px-3 py-2 pointer-events-none"
          style={{ left: tooltip.x, top: tooltip.y, transform: 'translate(-50%, -100%)' }}
        >
          <div className="bg-panel border border-grid px-3 py-2 shadow-lg">
            <div className="text-[11px] font-mono text-tactical-text whitespace-nowrap">{tooltip.label}</div>
            <div className="text-[10px] font-mono text-tactical-muted">
              r = {tooltip.r !== null ? tooltip.r.toFixed(4) : '—'}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CorrelationHeatmap
