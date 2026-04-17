import React, { useState, useCallback } from 'react'
import { Canvas } from '@react-three/fiber'
import Spacecraft3D from './components/Spacecraft3D'
import EnvironmentHUD from './components/EnvironmentHUD'
import HardwareState from './components/HardwareState'
import { useHILStream, SimulationState } from './hooks/useHILStream'

const App: React.FC = () => {
  const { simState, hwState, connected, error, sendCommand } = useHILStream()
  const [simRunning, setSimRunning] = useState(false)

  const handleStart = useCallback(() => {
    sendCommand('start')
    setSimRunning(true)
  }, [sendCommand])

  const handlePause = useCallback(() => {
    sendCommand('pause')
    setSimRunning(false)
  }, [sendCommand])

  const handleStop = useCallback(() => {
    sendCommand('stop')
    setSimRunning(false)
  }, [sendCommand])

  const handleStep = useCallback(() => {
    sendCommand('step')
  }, [sendCommand])

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header Bar */}
      <header style={{
        padding: '8px 16px',
        background: '#111133',
        borderBottom: '1px solid #00ff88',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <h1 style={{ fontSize: '16px', color: '#00ff88' }}>
          🛰️ CubeSat HIL Mission Control
        </h1>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{
            width: 10, height: 10, borderRadius: '50%',
            background: connected ? '#00ff88' : '#ff4444',
            display: 'inline-block',
          }} />
          <span style={{ fontSize: '12px' }}>
            {connected ? 'CONNECTED' : error || 'DISCONNECTED'}
          </span>
          <span style={{ fontSize: '12px', color: '#888', marginLeft: 16 }}>
            T+ {simState?.sim_time?.toFixed(1) ?? '0.0'}s
          </span>
        </div>
      </header>

      {/* Control Bar */}
      <div style={{
        padding: '6px 16px',
        background: '#0d0d22',
        borderBottom: '1px solid #333',
        display: 'flex',
        gap: '8px',
      }}>
        {['START', 'PAUSE', 'STOP', 'STEP'].map((label) => (
          <button
            key={label}
            onClick={
              label === 'START' ? handleStart :
              label === 'PAUSE' ? handlePause :
              label === 'STOP' ? handleStop : handleStep
            }
            style={{
              padding: '4px 16px',
              background: label === 'STOP' ? '#441111' : '#112211',
              border: `1px solid ${label === 'STOP' ? '#ff4444' : '#00ff88'}`,
              color: label === 'STOP' ? '#ff4444' : '#00ff88',
              cursor: 'pointer',
              fontFamily: 'Courier New',
              fontSize: '12px',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* 3D Viewport */}
        <div style={{ flex: 2, position: 'relative' }}>
          <Canvas camera={{ position: [3, 3, 3], fov: 50 }}>
            <ambientLight intensity={0.3} />
            <directionalLight position={[5, 5, 5]} intensity={1} />
            <Spacecraft3D quaternion={simState?.dynamics?.quaternion ?? [1, 0, 0, 0]} />
            <gridHelper args={[10, 10, '#223322', '#112211']} />
          </Canvas>
        </div>

        {/* Side Panels */}
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          borderLeft: '1px solid #333', overflow: 'auto',
          minWidth: 320, maxWidth: 400,
        }}>
          <EnvironmentHUD state={simState} />
          <HardwareState state={hwState} />
        </div>
      </div>
    </div>
  )
}

export default App
