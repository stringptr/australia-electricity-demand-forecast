import React from 'react'

const OrbitalGlobe: React.FC = () => {
  return (
    <div className="absolute inset-0 pointer-events-none flex items-center justify-center z-0 overflow-hidden">
      <svg
        viewBox="0 0 600 600"
        className="w-[90vh] h-[90vh] max-w-[800px] max-h-[800px] opacity-[0.08]"
        style={{ animation: 'globeRotate 120s linear infinite' }}
      >
        <defs>
          <clipPath id="globeClip">
            <circle cx="300" cy="300" r="250" />
          </clipPath>
        </defs>

        {/* Globe outline */}
        <circle
          cx="300"
          cy="300"
          r="250"
          fill="none"
          stroke="#52525b"
          strokeWidth="1"
        />

        {/* Latitude lines */}
        {[80, 160, 240, 300, 360, 440, 520].map((cy, i) => (
          <ellipse
            key={`lat-${i}`}
            cx="300"
            cy={cy}
            rx={Math.sqrt(250 * 250 - (cy - 300) * (cy - 300))}
            ry={Math.sqrt(250 * 250 - (cy - 300) * (cy - 300)) * 0.25}
            fill="none"
            stroke="#52525b"
            strokeWidth="0.5"
            clipPath="url(#globeClip)"
          />
        ))}

        {/* Longitude lines */}
        {Array.from({ length: 12 }, (_, i) => {
          const angle = (i * 30 * Math.PI) / 180
          return (
            <ellipse
              key={`lon-${i}`}
              cx="300"
              cy="300"
              rx={250 * Math.abs(Math.cos(angle)) || 0.5}
              ry="250"
              fill="none"
              stroke="#52525b"
              strokeWidth="0.5"
              clipPath="url(#globeClip)"
              style={{
                transform: `rotate(${i * 30}deg)`,
                transformOrigin: '300px 300px',
              }}
            />
          )
        })}

        {/* Dashed orbital arc 1 */}
        <ellipse
          cx="300"
          cy="300"
          rx="350"
          ry="100"
          fill="none"
          stroke="#52525b"
          strokeWidth="0.5"
          strokeDasharray="8 6"
          style={{
            transform: 'rotate(-20deg)',
            transformOrigin: '300px 300px',
          }}
        />

        {/* Dashed orbital arc 2 */}
        <ellipse
          cx="300"
          cy="300"
          rx="320"
          ry="120"
          fill="none"
          stroke="#52525b"
          strokeWidth="0.5"
          strokeDasharray="4 8"
          style={{
            transform: 'rotate(35deg)',
            transformOrigin: '300px 300px',
          }}
        />

        {/* Inner dashed ring */}
        <circle
          cx="300"
          cy="300"
          r="270"
          fill="none"
          stroke="#52525b"
          strokeWidth="0.5"
          strokeDasharray="3 6"
        />
      </svg>

      <style>{`
        @keyframes globeRotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

export default React.memo(OrbitalGlobe)
