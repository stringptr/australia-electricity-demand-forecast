import React from 'react'

interface GradientLegendProps {
  gradientMax: number
}

const GradientLegend: React.FC<GradientLegendProps> = ({ gradientMax }) => {
  return (
    <div className="absolute bottom-0 left-0 right-0 h-12 bg-panel/95 border-t border-grid z-10 flex items-center px-6 gap-4">
      <span className="text-[10px] text-tactical-muted uppercase tracking-[0.15em] font-mono whitespace-nowrap">Demand Intensity</span>

      <div className="flex-1 flex flex-col gap-1">
        {/* Gradient Bar */}
        <div
          className="h-2 w-full"
          style={{
            background: 'linear-gradient(to right, #F4D35E, #F2A541, #EE6C2C, #E8402B, #C62828)',
          }}
        />
        {/* Labels */}
        <div className="flex justify-between text-[9px] font-mono text-tactical-muted uppercase tracking-wider">
          <span>0 MW</span>
          <span>~{(gradientMax * 0.25 / 1000).toFixed(0)}k</span>
          <span>~{(gradientMax * 0.5 / 1000).toFixed(0)}k</span>
          <span>~{(gradientMax * 0.75 / 1000).toFixed(0)}k</span>
          <span>{(gradientMax / 1000).toFixed(0)}k+</span>
        </div>
      </div>
    </div>
  )
}

export default GradientLegend
