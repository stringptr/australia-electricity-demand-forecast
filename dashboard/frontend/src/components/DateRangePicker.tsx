import React from 'react'

interface DateRangePickerProps {
  startDate: string
  endDate: string
  onStartChange: (d: string) => void
  onEndChange: (d: string) => void
}

const DateRangePicker: React.FC<DateRangePickerProps> = ({
  startDate, endDate, onStartChange, onEndChange,
}) => {
  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        <label className="text-[10px] font-mono text-tactical-muted uppercase tracking-[0.15em]">Start</label>
        <input
          type="date"
          value={startDate}
          onChange={e => onStartChange(e.target.value)}
          className="bg-void border border-grid px-2 py-1 text-xs font-mono text-tactical-text focus:outline-none focus:border-accent-yorange"
        />
      </div>
      <div className="flex items-center gap-2">
        <label className="text-[10px] font-mono text-tactical-muted uppercase tracking-[0.15em]">End</label>
        <input
          type="date"
          value={endDate}
          onChange={e => onEndChange(e.target.value)}
          className="bg-void border border-grid px-2 py-1 text-xs font-mono text-tactical-text focus:outline-none focus:border-accent-yorange"
        />
      </div>
    </div>
  )
}

export default DateRangePicker
