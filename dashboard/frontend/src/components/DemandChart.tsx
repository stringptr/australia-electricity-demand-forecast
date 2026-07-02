import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'

interface DemandChartProps {
  data: Array<{
    time: string
    actual: number | null
    predicted: number | null
  }>
}

const DemandChart: React.FC<DemandChartProps> = ({ data }) => {
  const formatTime = (timeStr: string) => {
    const d = new Date(timeStr)
    return `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
  }

  // Find boundary between history and prediction
  const boundaryIndex = data.findIndex((d) => d.predicted !== null && d.actual === null)
  const boundaryTime = boundaryIndex >= 0 ? data[boundaryIndex]?.time : null

  return (
    <div className="w-full h-64 bg-void/40 border border-grid p-3">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#252529" />
          <XAxis
            dataKey="time"
            tickFormatter={formatTime}
            stroke="#52525b"
            tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
            interval="preserveStartEnd"
          />
          <YAxis
            stroke="#52525b"
            tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#141418',
              border: '1px solid #252529',
              fontSize: '12px',
              fontFamily: 'JetBrains Mono, monospace',
            }}
            labelStyle={{ color: '#52525b', fontFamily: 'JetBrains Mono, monospace' }}
            itemStyle={{ color: '#e4e4e7', fontFamily: 'JetBrains Mono, monospace' }}
            formatter={(value: any, name: string) => [
              `${Number(value).toLocaleString()} MW`,
              name === 'actual' ? 'Real Demand' : 'Predicted',
            ]}
            labelFormatter={(label: string) => new Date(label).toLocaleString('en-AU')}
          />
          {boundaryTime && (
            <ReferenceLine
              x={boundaryTime}
              stroke="#F2A541"
              strokeDasharray="5 5"
              label={{ value: 'NOW', fill: '#F2A541', fontSize: 11, fontFamily: 'JetBrains Mono, monospace', position: 'top' }}
            />
          )}
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#F2A541"
            strokeWidth={2}
            dot={false}
            connectNulls
            name="actual"
          />
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="#E8402B"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
            connectNulls
            name="predicted"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default DemandChart
