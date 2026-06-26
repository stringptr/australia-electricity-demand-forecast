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
} from 'recharts'

interface AccuracyChartProps {
  data: Array<{
    horizon: string
    mape: number | null
    accuracy: number | null
  }>
}

const AccuracyChart: React.FC<AccuracyChartProps> = ({ data }) => {
  const getColor = (accuracy: number | null) => {
    if (accuracy === null) return '#3f3f46'
    if (accuracy >= 95) return '#22c55e'
    if (accuracy >= 90) return '#F4D35E'
    if (accuracy >= 85) return '#EE6C2C'
    return '#E8402B'
  }

  return (
    <div className="w-full h-48 bg-void/40 border border-grid p-3">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 5, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#252529" />
          <XAxis
            dataKey="horizon"
            stroke="#52525b"
            tick={{ fontSize: 8, fontFamily: 'JetBrains Mono, monospace' }}
            angle={-45}
            textAnchor="end"
            interval={2}
          />
          <YAxis
            stroke="#52525b"
            tick={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#141418',
              border: '1px solid #252529',
              fontSize: '11px',
              fontFamily: 'JetBrains Mono, monospace',
            }}
            labelStyle={{ color: '#52525b', fontFamily: 'JetBrains Mono, monospace' }}
            itemStyle={{ color: '#e4e4e7', fontFamily: 'JetBrains Mono, monospace' }}
            formatter={(value: any) => [`${Number(value).toFixed(1)}% accuracy`, '']}
            labelFormatter={(label: string) => `Horizon: ${label}`}
          />
          <Bar dataKey="accuracy">
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColor(entry.accuracy)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default AccuracyChart
