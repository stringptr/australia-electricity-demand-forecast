import React from 'react'

const REGIONS = [
  { id: 'NSW1', name: 'New South Wales' },
  { id: 'QLD1', name: 'Queensland' },
  { id: 'SA1', name: 'South Australia' },
  { id: 'TAS1', name: 'Tasmania' },
  { id: 'VIC1', name: 'Victoria' },
]

interface RegionCheckboxesProps {
  selected: string[]
  onChange: (ids: string[]) => void
}

const RegionCheckboxes: React.FC<RegionCheckboxesProps> = ({ selected, onChange }) => {
  const toggle = (id: string) => {
    if (selected.includes(id)) {
      onChange(selected.filter(s => s !== id))
    } else {
      onChange([...selected, id])
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-4">
      <span className="text-[10px] font-mono text-tactical-muted uppercase tracking-[0.2em]">Regions</span>
      {REGIONS.map(r => (
        <label
          key={r.id}
          className="flex items-center gap-2 cursor-pointer group"
        >
          <input
            type="checkbox"
            checked={selected.includes(r.id)}
            onChange={() => toggle(r.id)}
            className="w-4 h-4 bg-void border border-grid checked:bg-accent-redorange focus:outline-none focus:border-accent-yorange"
          />
          <span className="text-xs font-mono text-tactical-text group-hover:text-accent-yorange transition-colors">
            {r.id}
            <span className="text-tactical-muted ml-1 hidden sm:inline">{r.name}</span>
          </span>
        </label>
      ))}
    </div>
  )
}

export default RegionCheckboxes
