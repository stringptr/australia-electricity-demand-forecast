import { useState, useEffect } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './lib/queryClient'
import { useWebSocket } from './hooks/useWebSocket'
import { useLatestDemand, useGlobalMetrics, useInvalidateQueries } from './hooks/useApiQuery'
import { WSMessage } from './types'
import VoltaicMap from './components/VoltaicMap'
import RegionSidebar from './components/RegionSidebar'
import GradientLegend from './components/GradientLegend'
import LiveIndicator from './components/LiveIndicator'
import OrbitalGlobe from './components/OrbitalGlobe'
import InsightPage from './components/InsightPage'

type Page = 'map' | 'insight'

function App() {
  const [page, setPage] = useState<Page>('map')
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [latestDemand, setLatestDemand] = useState<Record<string, number>>({})
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null)
  const [hoveredDemand, setHoveredDemand] = useState(0)

  const { data: latestDemandData } = useLatestDemand()
  const { data: metricsData } = useGlobalMetrics()
  const { invalidateDemand, invalidatePredictions } = useInvalidateQueries()

  const gradientMax = metricsData?.gradient_max || 20000

  useEffect(() => {
    if (latestDemandData?.regions) {
      const initial: Record<string, number> = {}
      latestDemandData.regions.forEach((r: any) => {
        initial[r.region_id] = r.demand_mw
      })
      setLatestDemand(initial)
    }
  }, [latestDemandData])

  const handleWSMessage = (msg: WSMessage) => {
    if (msg.type === 'demand_update' && msg.demand_mw !== undefined) {
      setLatestDemand(prev => ({
        ...prev,
        [msg.region_id]: msg.demand_mw!,
      }))
      invalidateDemand()
    } else if (msg.type === 'prediction_update') {
      invalidatePredictions()
    }
  }

  const { connected } = useWebSocket(handleWSMessage)

  const handleSelectRegion = (id: string | null) => {
    setSelectedRegion(id)
  }

  const handleHoverRegion = (id: string | null, demand: number) => {
    setHoveredRegion(id)
    setHoveredDemand(demand)
  }

  const selectedRegionDemand = selectedRegion ? latestDemand[selectedRegion] || 0 : 0

  return (
    <div className="w-screen h-screen bg-void text-tactical-text overflow-hidden relative flex flex-col">
      <header className="h-12 bg-panel/90 border-b border-grid flex items-center justify-between px-6 z-30">
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-tactical-muted tracking-[0.2em] uppercase font-mono hidden sm:inline">Real-Time Grid Intelligence</span>
          <div className="w-px h-4 bg-grid hidden sm:block" />
          <h1 className="text-base font-mono font-bold tracking-[0.15em] text-tactical-text uppercase">
            VOLTAIC<span className="text-accent-red">::</span>COMMAND
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <nav className="flex items-center gap-1">
            <button
              onClick={() => setPage('map')}
              className={`px-3 py-1 text-[10px] font-mono uppercase tracking-[0.2em] transition-colors border ${page === 'map'
                ? 'text-accent-yorange border-accent-yorange'
                : 'text-tactical-muted border-transparent hover:text-tactical-text hover:border-grid'
                }`}
            >
              Map
            </button>
            <button
              onClick={() => setPage('insight')}
              className={`px-3 py-1 text-[10px] font-mono uppercase tracking-[0.2em] transition-colors border ${page === 'insight'
                ? 'text-accent-yorange border-accent-yorange'
                : 'text-tactical-muted border-transparent hover:text-tactical-text hover:border-grid'
                }`}
            >
              Insight
            </button>
          </nav>
          <LiveIndicator connected={connected} />
        </div>
      </header>

      <main className="flex-1 relative">
        {page === 'map' ? (
          <>
            <OrbitalGlobe />
            <VoltaicMap
              latestDemand={latestDemand}
              gradientMax={gradientMax}
              selectedRegion={selectedRegion}
              onSelectRegion={handleSelectRegion}
              onHoverRegion={handleHoverRegion}
            />
            {selectedRegion && (
              <RegionSidebar
                regionId={selectedRegion}
                latestDemand={selectedRegionDemand}
                gradientMax={gradientMax}
                onClose={() => handleSelectRegion(null)}
              />
            )}
            <GradientLegend gradientMax={gradientMax} />
            {hoveredRegion && !selectedRegion && (
              <div className="absolute top-4 right-4 bg-panel/95 border border-grid z-20 px-4 py-3">
                <div className="text-[10px] text-tactical-muted uppercase tracking-wider font-mono">{hoveredRegion}</div>
                <div className="text-lg font-mono font-bold text-tactical-text">{hoveredDemand.toLocaleString()} <span className="text-sm font-normal text-tactical-muted">MW</span></div>
              </div>
            )}
          </>
        ) : (
          <InsightPage />
        )}
      </main>
    </div>
  )
}

function Root() {
  return (
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  )
}

export default Root
