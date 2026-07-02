import React, { useMemo } from 'react'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface ScatterPlotProps {
  data: Array<Record<string, any>>
  xKey: string
  yKey: string
  xLabel: string
  yLabel: string
  color?: string
}

const COLORS = ['#F2A541', '#E8402B', '#22c55e', '#3b82f6', '#a855f7']

const ScatterPlot: React.FC<ScatterPlotProps> = ({
  data, xKey, yKey, xLabel, yLabel, color = '#F2A541',
}) => {
  const chartData = useMemo(
    () => data.map(d => ({ x: d[xKey], y: d[yKey] })),
    [data, xKey, yKey]
  )

  return (
    <div className="bg-void/40 border border-grid p-3">
      <ResponsiveContainer width="100%" height={220}>
        <ScatterChart margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#252529" />
          <XAxis
            dataKey="x"
            stroke="#52525b"
            tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
            label={{ value: xLabel, fill: '#52525b', fontSize: 11, fontFamily: 'JetBrains Mono, monospace', position: 'bottom', offset: -2 }}
          />
          <YAxis
            dataKey="y"
            stroke="#52525b"
            tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
            tickFormatter={(v: number) => `${(v / 1000).toFixed(1)}k`}
            label={{ value: 'Demand (MW)', fill: '#52525b', fontSize: 11, fontFamily: 'JetBrains Mono, monospace', angle: -90, position: 'insideLeft', offset: 0 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#141418',
              border: '1px solid #252529',
              fontSize: '12px',
              fontFamily: 'JetBrains Mono, monospace',
            }}
            labelStyle={{ color: '#52525b' }}
            itemStyle={{ color: '#e4e4e7' }}
            formatter={(value: any, name: string) => {
              if (name === 'y') return [`${Number(value).toLocaleString()} MW`, 'Demand']
              if (name === 'x') return [Number(value).toFixed(1), xLabel]
              return [value, name]
            }}
            labelFormatter={() => ''}
          />
          <Scatter
            data={chartData}
            fill={color}
            opacity={0.6}
            r={3}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

export default ScatterPlot
