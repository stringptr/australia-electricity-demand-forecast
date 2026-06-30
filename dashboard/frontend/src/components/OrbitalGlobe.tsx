import React, { useEffect, useRef } from 'react'

const OrbitalGlobe: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationId: number
    let rotation = 0

    const draw = () => {
      rotation += 0.005

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const cx = canvas.width / 2
      const cy = canvas.height / 2
      const radius = Math.min(cx, cy) * 0.4

      ctx.beginPath()
      ctx.arc(cx, cy, radius, 0, Math.PI * 2)
      ctx.strokeStyle = '#252529'
      ctx.lineWidth = 1
      ctx.stroke()

      ctx.beginPath()
      ctx.ellipse(cx, cy, radius, radius * 0.3, rotation, 0, Math.PI * 2)
      ctx.strokeStyle = '#252529'
      ctx.lineWidth = 1
      ctx.stroke()

      ctx.beginPath()
      ctx.ellipse(cx, cy, radius, radius * 0.3, rotation + Math.PI / 3, 0, Math.PI * 2)
      ctx.strokeStyle = '#252529'
      ctx.lineWidth = 1
      ctx.stroke()

      ctx.beginPath()
      ctx.ellipse(cx, cy, radius, radius * 0.3, rotation + Math.PI * 2 / 3, 0, Math.PI * 2)
      ctx.strokeStyle = '#252529'
      ctx.lineWidth = 1
      ctx.stroke()

      const dotAngle = rotation
      const dotX = cx + radius * Math.cos(dotAngle)
      const dotY = cy + radius * 0.3 * Math.sin(dotAngle)

      ctx.beginPath()
      ctx.arc(dotX, dotY, 3, 0, Math.PI * 2)
      ctx.fillStyle = '#E8402B'
      ctx.fill()

      animationId = requestAnimationFrame(draw)
    }

    draw()

    return () => cancelAnimationFrame(animationId)
  }, [])

  return (
    <canvas
      ref={canvasRef}
      width={300}
      height={300}
      className="absolute bottom-4 left-4 z-0 opacity-30 pointer-events-none"
    />
  )
}

export default OrbitalGlobe
