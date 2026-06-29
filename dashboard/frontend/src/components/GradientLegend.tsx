import React from 'react'

interface GradientLegendProps {
  gradientMax: number
}

const GradientLegend: React.FC<GradientLegendProps> = ({ gradientMax }) => {
  return (
    <div className="absolute bottom-4 right-4 z-10 bg-panel/95 border border-grid px-3 py-2 flex flex-col gap-1 min-w-[180px]">
      <span className="text-[9px] text-tactical-muted uppercase tracking-[0.15em] font-mono">Demand Intensity</span>

      <div
        className="h-1.5 w-full"
        style={{
          background: 'linear-gradient(to right, #F4D35E, #F2A541, #EE6C2C, #E8402B, #C62828)',
        }}
      />
      <div className="flex justify-between text-[8px] font-mono text-tactical-muted uppercase tracking-wider">
        <span>0</span>
        <span>~{(gradientMax * 0.25 / 1000).toFixed(0)}k</span>
        <span>~{(gradientMax * 0.5 / 1000).toFixed(0)}k</span>
        <span>~{(gradientMax * 0.75 / 1000).toFixed(0)}k</span>
        <span>{(gradientMax / 1000).toFixed(0)}k+</span>
      </div>
    </div>
  )
}

export default GradientLegend
