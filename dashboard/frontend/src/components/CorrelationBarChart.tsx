import React from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts'
import type { CorrelationResult } from '../types'

interface CorrelationBarChartProps {
  data: CorrelationResult[]
}

const getBarColor = (r: number | null) => {
  if (r === null) return '#3f3f46'
  const abs = Math.abs(r)
  if (abs > 0.7) return '#E8402B'
  if (abs > 0.4) return '#F2A541'
  if (abs > 0.2) return '#F4D35E'
  return '#52525b'
}

const CorrelationBarChart: React.FC<CorrelationBarChartProps> = ({ data }) => {
  const chartData = data.map(d => ({
    label: d.variable_label.split('(')[0].trim(),
    r: d.r,
    display: d.r !== null ? d.r.toFixed(3) : '—',
  }))

  return (
    <div className="bg-void/40 border border-grid p-3">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#252529" />
          <XAxis
            dataKey="label"
            stroke="#52525b"
            tick={{ fontSize: 8, fontFamily: 'JetBrains Mono, monospace' }}
            interval={0}
          />
          <YAxis
            stroke="#52525b"
            tick={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
            domain={[-1, 1]}
            tickFormatter={(v: number) => v.toFixed(1)}
          />
          <ReferenceLine y={0} stroke="#52525b" strokeDasharray="3 3" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#141418',
              border: '1px solid #252529',
              fontSize: '11px',
              fontFamily: 'JetBrains Mono, monospace',
            }}
            labelStyle={{ color: '#52525b' }}
            itemStyle={{ color: '#e4e4e7' }}
            formatter={(_: any, __: string, props: any) => [`r = ${props.payload.r?.toFixed(4) || '—'}`, '']}
          />
          <Bar dataKey="r">
            {chartData.map((entry, i) => (
              <Cell key={i} fill={getBarColor(entry.r)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default CorrelationBarChart
