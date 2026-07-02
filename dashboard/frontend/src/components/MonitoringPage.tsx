import React, { useState, useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LineChart,
  Line,
  ReferenceLine,
} from 'recharts'
import {
  useMonitoringAccuracy,
  useMonitoringUptime,
  useMonitoringLatency,
} from '../hooks/useApiQuery'

const REGIONS = ['NSW1', 'QLD1', 'SA1', 'TAS1', 'VIC1']

const getMapeColor = (mape: number) => {
  if (mape < 5) return '#22c55e'
  if (mape < 10) return '#F4D35E'
  if (mape < 15) return '#EE6C2C'
  return '#E8402B'
}

const getAccuracyColor = (accuracy: number) => {
  if (accuracy >= 95) return '#22c55e'
  if (accuracy >= 90) return '#F4D35E'
  if (accuracy >= 85) return '#EE6C2C'
  return '#E8402B'
}

const getUptimeColor = (pct: number | null) => {
  if (pct === null) return '#3f3f46'
  if (pct >= 99.5) return '#22c55e'
  if (pct >= 98) return '#F4D35E'
  if (pct >= 95) return '#EE6C2C'
  return '#E8402B'
}

const formatLatency = (s: number) => {
  if (s < 60) return `${s.toFixed(1)}s`
  return `${(s / 60).toFixed(1)}m`
}

const sectionHeader = 'text-xs font-mono text-tactical-muted uppercase tracking-[0.2em] mb-3'

const AccuracySection: React.FC = () => {
  const [selectedRegion, setSelectedRegion] = useState<string>('NSW1')
  const { data, isLoading } = useMonitoringAccuracy()

  const chartData = useMemo(() => {
    if (!data?.regions) return []
    const items = data.regions[selectedRegion] || []
    return items.map(item => ({
      horizon: `h+${item.horizon}`,
      mape: item.mape,
      accuracy: 100 - item.mape,
    }))
  }, [data, selectedRegion])

  const overallMape = useMemo(() => {
    if (!data?.regions) return null
    const items = data.regions[selectedRegion] || []
    if (items.length === 0) return null
    return items.reduce((sum, i) => sum + i.mape, 0) / items.length
  }, [data, selectedRegion])

  if (isLoading) {
    return (
      <div className="bg-panel/90 border border-grid p-5">
        <div className={sectionHeader}>Model Accuracy</div>
        <div className="text-tactical-muted font-mono text-xs">Loading accuracy data...</div>
      </div>
    )
  }

  return (
    <div className="bg-panel/90 border border-grid p-5">
      <div className="flex items-center justify-between mb-4">
        <div className={sectionHeader}>Model Accuracy (MAPE)</div>
        <div className="flex gap-1">
          {REGIONS.map(r => (
            <button
              key={r}
              onClick={() => setSelectedRegion(r)}
              className={`px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider transition-colors border ${
                selectedRegion === r
                  ? 'text-accent-yorange border-accent-yorange'
                  : 'text-tactical-muted border-transparent hover:text-tactical-text hover:border-grid'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {overallMape !== null && (
        <div className="flex items-center gap-3 mb-4">
          <span className="text-[10px] font-mono text-tactical-muted uppercase tracking-wider">Avg MAPE:</span>
          <span className="text-sm font-mono font-bold" style={{ color: getMapeColor(overallMape) }}>
            {overallMape.toFixed(2)}%
          </span>
          <span className="text-[10px] font-mono text-tactical-muted">({(100 - overallMape).toFixed(1)}% accuracy)</span>
        </div>
      )}

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 5, bottom: 20, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#252529" />
            <XAxis
              dataKey="horizon"
              stroke="#52525b"
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              angle={-45}
              textAnchor="end"
              interval={2}
            />
            <YAxis
              stroke="#52525b"
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              tickFormatter={(v) => `${v}%`}
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
              formatter={(value: any, name: string) => [`${Number(value).toFixed(2)}%`, 'MAPE']}
              labelFormatter={(label: string) => `Horizon: ${label}`}
            />
            <Bar dataKey="mape">
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getMapeColor(entry.mape)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

const UptimeSection: React.FC = () => {
  const { data, isLoading } = useMonitoringUptime()

  if (isLoading) {
    return (
      <div className="bg-panel/90 border border-grid p-5">
        <div className={sectionHeader}>Service Uptime</div>
        <div className="text-tactical-muted font-mono text-xs">Loading uptime data...</div>
      </div>
    )
  }

  const services = data?.services || []

  return (
    <div className="bg-panel/90 border border-grid p-5">
      <div className={sectionHeader}>Service Uptime</div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {services.map(svc => (
          <div key={svc.name} className="bg-void/60 border border-grid p-3">
            <div className="flex items-center gap-2 mb-2">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: svc.status === 'up' ? '#22c55e' : '#E8402B' }}
              />
              <span className="text-[10px] font-mono text-tactical-muted uppercase tracking-wider">{svc.name}</span>
            </div>
            <div className="mb-1">
              <span className="text-sm font-mono font-bold text-tactical-text">24h: </span>
              <span className="text-sm font-mono font-bold" style={{ color: getUptimeColor(svc.uptime_24h) }}>
                {svc.uptime_24h !== null ? `${svc.uptime_24h}%` : '—'}
              </span>
            </div>
            <div>
              <span className="text-[11px] font-mono text-tactical-muted">7d: </span>
              <span className="text-[11px] font-mono" style={{ color: getUptimeColor(svc.uptime_7d) }}>
                {svc.uptime_7d !== null ? `${svc.uptime_7d}%` : '—'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const LatencySection: React.FC = () => {
  const { data, isLoading } = useMonitoringLatency()

  const trendData = useMemo(() => {
    if (!data?.trend) return []
    return data.trend.map(t => ({
      time: new Date(t.time * 1000).toLocaleTimeString('en-AU', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }),
      latency: t.value,
    }))
  }, [data])

  const latency = data?.latest || 0
  const thresholdWarning = data?.threshold_warning || 60
  const thresholdCritical = data?.threshold_critical || 300

  let latencyStatus = 'ok'
  let latencyColor = '#22c55e'
  if (latency >= thresholdCritical) {
    latencyStatus = 'critical'
    latencyColor = '#E8402B'
  } else if (latency >= thresholdWarning) {
    latencyStatus = 'warning'
    latencyColor = '#EE6C2C'
  }

  if (isLoading) {
    return (
      <div className="bg-panel/90 border border-grid p-5">
        <div className={sectionHeader}>Pipeline Latency</div>
        <div className="text-tactical-muted font-mono text-xs">Loading latency data...</div>
      </div>
    )
  }

  return (
    <div className="bg-panel/90 border border-grid p-5">
      <div className="flex items-center justify-between mb-4">
        <div className={sectionHeader}>Pipeline Latency (Poller &rarr; Silver)</div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: latencyColor }} />
          <span className="text-[10px] font-mono uppercase tracking-wider" style={{ color: latencyColor }}>
            {latencyStatus}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <div>
          <div className="text-[10px] font-mono text-tactical-muted uppercase tracking-wider mb-1">Current</div>
          <div className="text-2xl font-mono font-bold" style={{ color: latencyColor }}>
            {formatLatency(latency)}
          </div>
        </div>
        <div className="w-px h-8 bg-grid" />
        <div>
          <div className="text-[10px] font-mono text-tactical-muted uppercase tracking-wider mb-1">Warning</div>
          <div className="text-sm font-mono text-tactical-muted">{formatLatency(thresholdWarning)}</div>
        </div>
        <div>
          <div className="text-[10px] font-mono text-tactical-muted uppercase tracking-wider mb-1">Critical</div>
          <div className="text-sm font-mono text-tactical-muted">{formatLatency(thresholdCritical)}</div>
        </div>
      </div>

      <div className="h-36">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={trendData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#252529" />
            <XAxis
              dataKey="time"
              stroke="#52525b"
              tick={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
              interval="preserveStartEnd"
            />
            <YAxis
              stroke="#52525b"
              tick={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
              tickFormatter={(v) => `${v}s`}
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
              formatter={(value: any) => [`${Number(value).toFixed(1)}s`, 'Latency']}
              labelFormatter={(label: string) => `Time: ${label}`}
            />
            <ReferenceLine y={thresholdWarning} stroke="#EE6C2C" strokeDasharray="5 5" />
            <ReferenceLine y={thresholdCritical} stroke="#E8402B" strokeDasharray="5 5" />
            <Line
              type="monotone"
              dataKey="latency"
              stroke="#F2A541"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

const MonitoringPage: React.FC = () => {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-6 pb-4 border-b border-grid">
        <h2 className="text-sm font-mono font-bold tracking-[0.15em] text-tactical-text uppercase">
          System Monitoring
        </h2>
        <p className="text-[10px] font-mono text-tactical-muted mt-1">
          Model accuracy, service uptime, and pipeline latency
        </p>
      </div>

      <div className="space-y-6">
        <UptimeSection />
        <AccuracySection />
        <LatencySection />
      </div>
    </div>
  )
}

export default MonitoringPage
