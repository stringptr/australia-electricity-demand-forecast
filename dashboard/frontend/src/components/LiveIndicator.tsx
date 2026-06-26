import React from 'react'

interface LiveIndicatorProps {
  connected: boolean
}

const LiveIndicator: React.FC<LiveIndicatorProps> = ({ connected }) => {
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <span className={`relative flex h-2 w-2 ${connected ? '' : 'opacity-50'}`}>
          <span className={`animate-ping absolute inline-flex h-full w-full opacity-75 ${connected ? 'bg-green-500' : 'bg-red-600'}`} />
          <span className={`relative inline-flex h-2 w-2 ${connected ? 'bg-green-500' : 'bg-red-600'}`} />
        </span>
        <span className={`text-[10px] font-mono font-bold uppercase tracking-[0.2em] ${connected ? 'text-green-500' : 'text-red-600'}`}>
          {connected ? 'Live' : 'Offline'}
        </span>
      </div>
      <div className="w-px h-3 bg-grid" />
      <div className="text-[10px] font-mono text-tactical-muted uppercase tracking-wider">
        {new Date().toLocaleString('en-AU', {
          timeZone: 'Australia/Sydney',
          weekday: 'short',
          day: 'numeric',
          month: 'short',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })}
      </div>
    </div>
  )
}

export default LiveIndicator
