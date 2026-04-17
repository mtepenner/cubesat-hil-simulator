import { useState, useEffect, useRef, useCallback } from 'react'

export interface OrbitState {
  position_eci: number[]
  velocity_eci: number[]
  latitude: number
  longitude: number
  altitude: number
}

export interface EnvironmentState {
  eclipse_factor: number
  solar_flux_w_m2: number
  magnetic_field_eci_nT: number[]
}

export interface DynamicsState {
  quaternion: number[]
  angular_velocity: number[]
  angular_momentum?: number[]
  rotational_energy?: number
}

export interface SimulationState {
  sim_time: number
  orbit: OrbitState
  environment: EnvironmentState
  dynamics: DynamicsState
}

export interface HardwareTelemetry {
  source: string
  subsystem: string
  quat_w?: number
  quat_x?: number
  quat_y?: number
  quat_z?: number
  adcs_mode?: number
  tumble_rate?: number
  battery_voltage?: number
  charge_percent?: number
  power_mode?: number
  heater_enabled?: boolean
  payload_enabled?: boolean
  timestamp_ms?: number
}

interface UseHILStreamResult {
  simState: SimulationState | null
  hwState: HardwareTelemetry | null
  connected: boolean
  error: string | null
  sendCommand: (command: string, payload?: Record<string, unknown>) => void
}

/**
 * Hook that synchronizes both the simulation and hardware data streams
 * via a WebSocket connection to the Python simulation engine.
 */
export function useHILStream(wsUrl?: string): UseHILStreamResult {
  const [simState, setSimState] = useState<SimulationState | null>(null)
  const [hwState, setHwState] = useState<HardwareTelemetry | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()

  const url = wsUrl ?? `ws://${window.location.hostname}:8000/api/sim/ws`

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setError(null)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          // Determine if this is sim state or hardware telemetry
          if (data.orbit && data.environment) {
            setSimState(data as SimulationState)
          } else if (data.subsystem || data.source === 'mock') {
            setHwState(data as HardwareTelemetry)
          }
        } catch {
          // Ignore malformed messages
        }
      }

      ws.onclose = () => {
        setConnected(false)
        wsRef.current = null
        // Auto-reconnect after 3 seconds
        reconnectTimer.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => {
        setError('WebSocket connection failed')
        ws.close()
      }
    } catch {
      setError('Failed to create WebSocket')
      reconnectTimer.current = setTimeout(connect, 3000)
    }
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendCommand = useCallback((command: string, payload?: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command, ...payload }))
    } else {
      // Fallback to REST API
      fetch(`/api/sim/${command}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload ?? {}),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.orbit) setSimState(data)
        })
        .catch(() => {})
    }
  }, [])

  return { simState, hwState, connected, error, sendCommand }
}
