import React, { useState, useMemo } from 'react'
import { useInsightData, useCorrelation } from '../hooks/useApiQuery'
import RegionCheckboxes from './RegionCheckboxes'
import DateRangePicker from './DateRangePicker'
import ScatterPlot from './ScatterPlot'
import CorrelationHeatmap from './CorrelationHeatmap'
import TimeSeriesOverlay from './TimeSeriesOverlay'

const WEATHER_VARS = [
  { key: 'temperature_2m_avg', label: 'Temperature (°C)', color: '#E8402B' },
  { key: 'relative_humidity_avg', label: 'Humidity (%)', color: '#3b82f6' },
  { key: 'precipitation_sum', label: 'Precipitation (mm)', color: '#22c55e' },
  { key: 'cloud_cover_avg', label: 'Cloud Cover (%)', color: '#a855f7' },
  { key: 'wind_speed_10m_avg', label: 'Wind Speed (km/h)', color: '#F4D35E' },
  { key: 'shortwave_radiation_avg', label: 'Solar Rad (W/m²)', color: '#F2A541' },
]

const TWO_MONTHS_AGO = new Date()
TWO_MONTHS_AGO.setMonth(TWO_MONTHS_AGO.getMonth() - 2)
const TODAY = new Date()

const fmtDate = (d: Date) => d.toISOString().split('T')[0]

const InsightPage: React.FC = () => {
  const [selectedRegions, setSelectedRegions] = useState<string[]>(['NSW1', 'QLD1', 'VIC1'])
  const [startDate, setStartDate] = useState(fmtDate(TWO_MONTHS_AGO))
  const [endDate, setEndDate] = useState(fmtDate(TODAY))

  const { data: insightData, isLoading: dataLoading } = useInsightData(selectedRegions, startDate, endDate, 'daily')
  const { data: correlationData, isLoading: corrLoading } = useCorrelation(selectedRegions, startDate, endDate)

  const scatterData = insightData?.data || []
  const coefficients = correlationData?.coefficients || []

  const timeSeriesData = useMemo(() => {
    if (scatterData.length === 0) return []
    const dateKey = 'date' in scatterData[0] ? 'date' : 'time'

    const byDate = new Map<string, Record<string, number[]>>()
    for (const row of scatterData) {
      const d = row[dateKey]
      if (!d) continue
      if (!byDate.has(d)) byDate.set(d, { demand_mw_avg: [] })
      const g = byDate.get(d)!
      if (row.demand_mw_avg != null) g.demand_mw_avg.push(row.demand_mw_avg)
      for (const wv of WEATHER_VARS) {
        const v = row[wv.key]
        if (v != null) {
          if (!g[wv.key]) g[wv.key] = []
          g[wv.key].push(v)
        }
      }
    }

    const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length
    return [...byDate.entries()]
      .map(([d, g]) => {
        const entry: Record<string, any> = { [dateKey]: d }
        entry.demand_mw_avg = mean(g.demand_mw_avg)
        for (const wv of WEATHER_VARS) entry[wv.key] = g[wv.key] ? mean(g[wv.key]) : null
        return entry
      })
      .sort((a, b) => (a[dateKey] as string).localeCompare(b[dateKey] as string))
  }, [scatterData])

  const demandKey = 'demand_mw_avg'
  const selectedVar = WEATHER_VARS[0]

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="flex flex-wrap items-center gap-6 mb-6 pb-4 border-b border-grid">
        <RegionCheckboxes selected={selectedRegions} onChange={setSelectedRegions} />
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartChange={setStartDate}
          onEndChange={setEndDate}
        />
      </div>

      {dataLoading || corrLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-tactical-muted font-mono text-xs tracking-[0.2em] uppercase">Loading insight data ...</div>
        </div>
      ) : scatterData.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-tactical-muted font-mono text-xs tracking-[0.2em] uppercase">No data for selected filters. Run the gold pipeline first.</div>
        </div>
      ) : (
        <>
          <div className="mb-6">
            <div className="text-xs font-mono text-tactical-muted uppercase tracking-[0.2em] mb-2">
              Correlation Coefficients (Pearson's r)
            </div>
            <CorrelationHeatmap data={coefficients} />
          </div>

          <div className="mb-6">
            <div className="text-xs font-mono text-tactical-muted uppercase tracking-[0.2em] mb-2">
              Weather vs Demand — Scatter Plots
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {WEATHER_VARS.map(wv => (
                <div key={wv.key}>
                  <div className="text-[11px] font-mono text-tactical-muted mb-1 tracking-wider">{wv.label}</div>
                  <ScatterPlot
                    data={scatterData}
                    xKey={wv.key}
                    yKey={demandKey}
                    xLabel={wv.label}
                    yLabel="Demand (MW)"
                    color={wv.color}
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="mb-6">
            <div className="text-xs font-mono text-tactical-muted uppercase tracking-[0.2em] mb-2">
              Time Series: Demand + {selectedVar.label}
            </div>
            <TimeSeriesOverlay
              data={timeSeriesData}
              varKey={selectedVar.key}
              varLabel={selectedVar.label}
              varColor={selectedVar.color}
            />
          </div>

          <div className="border-t border-grid pt-4">
            <div className="text-xs font-mono text-tactical-muted uppercase tracking-[0.2em] mb-2">Summary</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {coefficients.map(c => (
                <div key={c.variable} className="bg-void/60 border border-grid p-3">
                  <div className="text-[11px] font-mono text-tactical-muted uppercase tracking-wider mb-1">{c.variable_label.split('(')[0].trim()}</div>
                  <div className="text-sm font-mono font-bold text-tactical-text">
                    r = {c.r !== null ? c.r.toFixed(3) : '—'}
                  </div>
                  <div className="text-[11px] font-mono text-tactical-muted">n = {c.n.toLocaleString()}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default InsightPage
