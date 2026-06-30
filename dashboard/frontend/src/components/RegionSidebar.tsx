import React, { useState } from 'react'
import { useDemandHistory, usePredictions, useAccuracy } from '../hooks/useApiQuery'
import { regionMeta } from '../lib/geojson'
import { interpolateColor } from '../lib/colors'
import DemandChart from './DemandChart'
import AccuracyChart from './AccuracyChart'

interface RegionSidebarProps {
  regionId: string
  latestDemand: number
  gradientMax: number
  onClose: () => void
}

const RegionSidebar: React.FC<RegionSidebarProps> = ({ regionId, latestDemand, gradientMax, onClose }) => {
  const [selectedHorizon, setSelectedHorizon] = useState(1)

  const { data: historyData } = useDemandHistory(regionId, 24)
  const { data: predictionData } = usePredictions(regionId)
  const { data: accuracyData } = useAccuracy(regionId)

  const regionName = regionMeta[regionId]?.name || regionId

  const predictedDemand = predictionData?.predictions?.[selectedHorizon - 1] || null

  const selectedMape = accuracyData?.accuracy?.find((a: any) => a.horizon === selectedHorizon)?.mape || null
  const accuracyPercent = selectedMape !== null ? (100 - selectedMape).toFixed(1) : null

  const chartData = (() => {
    const history = historyData?.data || []
    const predictions = predictionData?.predictions || []
    const createdAt = predictionData?.created_at ? new Date(predictionData.created_at) : null

    const data: Array<{ time: string; actual: number | null; predicted: number | null }> = []

    history.forEach((pt: any) => {
      data.push({
        time: pt.time,
        actual: pt.demand_mw,
        predicted: null,
      })
    })

    if (createdAt && predictions.length > 0) {
      predictions.forEach((pred: number, idx: number) => {
        const predTime = new Date(createdAt.getTime() + (idx + 1) * 3600000)
        data.push({
          time: predTime.toISOString(),
          actual: null,
          predicted: pred,
        })
      })
    }

    return data
  })()

  const accuracyChartData = (accuracyData?.accuracy || []).map((a: any) => ({
    horizon: `h+${a.horizon}`,
    mape: a.mape,
    accuracy: a.mape !== null ? 100 - a.mape : null,
  }))

  const demandColor = interpolateColor(latestDemand, 0, gradientMax || 20000)

  return (
    <div className="absolute left-0 top-0 h-full w-[420px] bg-panel/95 border-r border-grid z-20 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-grid">
        <div>
          <div className="text-[10px] font-mono text-tactical-muted uppercase tracking-[0.15em] mb-1">Region Target</div>
          <h2 className="text-base font-mono font-bold tracking-wider text-tactical-text uppercase">{regionName}</h2>
          <p className="text-[10px] font-mono text-tactical-muted mt-1">
            {new Date().toLocaleString('en-AU', { timeZone: 'Australia/Sydney', dateStyle: 'medium', timeStyle: 'short' })}
          </p>
        </div>
        <button
          onClick={onClose}
          className="w-8 h-8 flex items-center justify-center border border-grid hover:border-tactical-muted text-tactical-muted hover:text-tactical-text transition-colors"
        >
          <span className="font-mono text-xs">×</span>
        </button>
      </div>

      <div className="p-4 grid grid-cols-2 gap-2">
        <div className="bg-void/60 border border-grid p-3">
          <div className="text-[10px] font-mono text-tactical-muted uppercase tracking-[0.15em] mb-1">Real Demand</div>
          <div className="text-xl font-mono font-bold text-tactical-text">{latestDemand.toLocaleString()} <span className="text-xs font-normal text-tactical-muted">MW</span></div>
        </div>

        <div className="bg-void/60 border border-grid p-3">
          <div className="text-[10px] font-mono text-tactical-muted uppercase tracking-[0.15em] mb-1">Predicted (h+{selectedHorizon})</div>
          <div className="text-xl font-mono font-bold text-tactical-text">
            {predictedDemand !== null ? predictedDemand.toLocaleString() : '—'} <span className="text-xs font-normal text-tactical-muted">MW</span>
          </div>
        </div>

        <div className="bg-void/60 border border-grid p-3 col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[10px] font-mono text-tactical-muted uppercase tracking-[0.15em] mb-1">Accuracy</div>
              <div className="text-xl font-mono font-bold" style={{ color: demandColor }}>
                {accuracyPercent !== null ? `${accuracyPercent}%` : '—'}
              </div>
            </div>
            <div>
              <label className="text-[10px] font-mono text-tactical-muted uppercase tracking-[0.15em] block mb-1">Horizon</label>
              <select
                value={selectedHorizon}
                onChange={(e) => setSelectedHorizon(Number(e.target.value))}
                className="bg-void border border-grid px-2 py-1 text-xs font-mono text-tactical-text focus:outline-none focus:border-accent-yorange"
              >
                {Array.from({ length: 24 }, (_, i) => (
                  <option key={i + 1} value={i + 1}>h+{i + 1}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 px-4 min-h-0 overflow-auto">
        <div className="mb-4">
          <div className="text-[10px] font-mono text-tactical-muted uppercase tracking-[0.15em] mb-2">Demand Forecast (48h)</div>
          <DemandChart data={chartData} />
        </div>

        <div className="mb-4">
          <div className="text-[10px] font-mono text-tactical-muted uppercase tracking-[0.15em] mb-2">Prediction Accuracy per Horizon</div>
          <AccuracyChart data={accuracyChartData} />
        </div>
      </div>
    </div>
  )
}

export default RegionSidebar
