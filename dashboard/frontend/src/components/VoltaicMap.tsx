import React, { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { australiaStates, regionMeta } from '../lib/geojson'
import { getDemandColorExpression, interpolateColor } from '../lib/colors'

interface VoltaicMapProps {
  latestDemand: Record<string, number>
  gradientMax: number
  selectedRegion: string | null
  onSelectRegion: (id: string | null) => void
  onHoverRegion: (id: string | null, demand: number) => void
}

const VoltaicMap: React.FC<VoltaicMapProps> = ({
  latestDemand,
  gradientMax,
  onSelectRegion,
  onHoverRegion,
}) => {
  const mapContainer = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })

  useEffect(() => {
    if (!mapContainer.current) return

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap',
          },
        },
        layers: [
          {
            id: 'osm',
            type: 'raster',
            source: 'osm',
            paint: {
              'raster-opacity': 0.15,
              'raster-brightness-min': 0,
              'raster-brightness-max': 0.25,
            },
          },
        ],
      },
      center: [134, -28],
      zoom: 4,
      pitch: 0,
      bearing: 0,
    })

    mapRef.current = map

    map.on('load', () => {
      // Add Australia states source
      map.addSource('australia-states', {
        type: 'geojson',
        data: australiaStates as any,
      })

      // Fill layer
      map.addLayer({
        id: 'states-fill',
        type: 'fill',
        source: 'australia-states',
        paint: {
          'fill-color': getDemandColorExpression(gradientMax) as any,
          'fill-opacity': 0.75,
        },
      })

      // Border layer - wireframe tactical
      map.addLayer({
        id: 'states-border',
        type: 'line',
        source: 'australia-states',
        paint: {
          'line-color': '#52525b',
          'line-width': 1,
        },
      })

      // Hover highlight
      map.addLayer({
        id: 'states-hover',
        type: 'line',
        source: 'australia-states',
        paint: {
          'line-color': '#e4e4e7',
          'line-width': 2,
        },
        filter: ['==', ['get', 'id'], ''],
      })

      // Update demand data
      updateDemandData(map, latestDemand)
    })

    // Click handler
    map.on('click', 'states-fill', (e) => {
      const feature = e.features?.[0]
      if (feature) {
        const id = feature.properties?.id as string
        onSelectRegion(id)
        const meta = regionMeta[id]
        if (meta) {
          map.flyTo({ center: meta.center as [number, number], zoom: meta.zoom, duration: 1000 })
        }
      }
    })

    // Hover handlers
    map.on('mousemove', 'states-fill', (e) => {
      const feature = e.features?.[0]
      if (feature) {
        const id = feature.properties?.id as string
        setHoveredRegion(id)
        setMousePos({ x: e.point.x, y: e.point.y })
        onHoverRegion(id, latestDemand[id] || 0)
        map.setFilter('states-hover', ['==', ['get', 'id'], id])
        map.getCanvas().style.cursor = 'pointer'
      }
    })

    map.on('mouseleave', 'states-fill', () => {
      setHoveredRegion(null)
      onHoverRegion(null, 0)
      map.setFilter('states-hover', ['==', ['get', 'id'], ''])
      map.getCanvas().style.cursor = ''
    })

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Update colors when gradientMax changes
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (map.getLayer('states-fill')) {
      map.setPaintProperty('states-fill', 'fill-color', getDemandColorExpression(gradientMax) as any)
    }
    updateDemandData(map, latestDemand)
  }, [gradientMax, latestDemand])

  const updateDemandData = (map: maplibregl.Map, demand: Record<string, number>) => {
    const source = map.getSource('australia-states') as maplibregl.GeoJSONSource
    if (!source) return

    const updated = {
      ...australiaStates,
      features: australiaStates.features.map(f => ({
        ...f,
        properties: {
          ...f.properties,
          demand_mw: demand[f.properties.id] || 0,
        },
      })),
    }
    source.setData(updated as any)
  }

  const hoveredDemand = hoveredRegion ? latestDemand[hoveredRegion] || 0 : 0
  const tooltipColor = interpolateColor(hoveredDemand, 0, gradientMax || 20000)

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Hover Tooltip */}
      {hoveredRegion && (
        <div
          className="absolute pointer-events-none z-10 px-4 py-3 border border-grid shadow-2xl"
          style={{
            left: mousePos.x + 15,
            top: mousePos.y + 15,
            backgroundColor: '#141418',
            color: '#e4e4e7',
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2" style={{ backgroundColor: tooltipColor }} />
            <div className="font-mono text-xs uppercase tracking-wider text-tactical-muted">{regionMeta[hoveredRegion]?.name} ({hoveredRegion})</div>
          </div>
          <div className="text-[10px] text-tactical-muted font-mono">
            {new Date().toLocaleString('en-AU', { timeZone: 'Australia/Sydney' })}
          </div>
          <div className="mt-2 text-sm font-mono font-bold" style={{ color: tooltipColor }}>
            {hoveredDemand.toLocaleString()} MW
          </div>
        </div>
      )}
    </div>
  )
}

export default React.memo(VoltaicMap)
