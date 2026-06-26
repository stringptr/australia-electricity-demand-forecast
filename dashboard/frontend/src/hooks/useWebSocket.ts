import { useEffect, useRef, useCallback, useState } from 'react'
import { WSMessage } from '../types'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/live'

export function useWebSocket(onMessage: (msg: WSMessage) => void) {
  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const reconnectTimeoutRef = useRef<number>(1000)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onMessageRef = useRef(onMessage)
  
  onMessageRef.current = onMessage
  
  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws
      
      ws.onopen = () => {
        setConnected(true)
        reconnectTimeoutRef.current = 1000
      }
      
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WSMessage
          onMessageRef.current(msg)
        } catch {
          // ignore parse errors
        }
      }
      
      ws.onclose = () => {
        setConnected(false)
        wsRef.current = null
        // Exponential backoff
        reconnectTimeoutRef.current = Math.min(reconnectTimeoutRef.current * 2, 30000)
        reconnectTimerRef.current = setTimeout(connect, reconnectTimeoutRef.current)
      }
      
      ws.onerror = () => {
        ws.close()
      }
    } catch {
      reconnectTimerRef.current = setTimeout(connect, reconnectTimeoutRef.current)
    }
  }, [])
  
  useEffect(() => {
    connect()
    
    // Ping every 30s
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping')
      }
    }, 30000)
    
    return () => {
      clearInterval(pingInterval)
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [connect])
  
  return { connected }
}