import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface TimeSeriesOverlayProps {
  data: Array<Record<string, any>>
  varKey: string
  varLabel: string
  varColor?: string
}

const TimeSeriesOverlay: React.FC<TimeSeriesOverlayProps> = ({
  data, varKey, varLabel, varColor = '#22c55e',
}) => {
  const formatDate = (d: string) => {
    const dt = new Date(d)
    return dt.toLocaleDateString('en-AU', { month: 'short', day: 'numeric' })
  }

  const demandKey = data.length > 0 ? ('demand_mw_avg' in data[0] ? 'demand_mw_avg' : 'demand_mw') : 'demand_mw'

  return (
    <div className="bg-void/40 border border-grid p-3">
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#252529" />
          <XAxis
            dataKey={data.length > 0 && 'date' in data[0] ? 'date' : 'time'}
            tickFormatter={formatDate}
            stroke="#52525b"
            tick={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
            interval="preserveStartEnd"
          />
          <YAxis
            yAxisId="demand"
            stroke="#F2A541"
            tick={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
            tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
            label={{ value: 'Demand (MW)', fill: '#F2A541', fontSize: 9, fontFamily: 'JetBrains Mono, monospace', angle: -90, position: 'insideLeft', offset: 0 }}
          />
          <YAxis
            yAxisId="var"
            orientation="right"
            stroke={varColor}
            tick={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
            label={{ value: varLabel, fill: varColor, fontSize: 9, fontFamily: 'JetBrains Mono, monospace', angle: 90, position: 'insideRight', offset: 0 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#141418',
              border: '1px solid #252529',
              fontSize: '11px',
              fontFamily: 'JetBrains Mono, monospace',
            }}
            labelStyle={{ color: '#52525b' }}
            itemStyle={{ color: '#e4e4e7' }}
            formatter={(value: any, name: string) => {
              if (name === demandKey) return [`${Number(value).toLocaleString()} MW`, 'Demand']
              return [`${Number(value).toFixed(1)}`, varLabel]
            }}
            labelFormatter={(label: string) => new Date(label).toLocaleString('en-AU')}
          />
          <Line
            yAxisId="demand"
            type="monotone"
            dataKey={demandKey}
            stroke="#F2A541"
            strokeWidth={2}
            dot={false}
            name={demandKey}
          />
          <Line
            yAxisId="var"
            type="monotone"
            dataKey={varKey}
            stroke={varColor}
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
            name={varKey}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default TimeSeriesOverlay
