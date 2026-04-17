import React from 'react'
import { HardwareTelemetry } from '../hooks/useHILStream'

interface HardwareStateProps {
  state: HardwareTelemetry | null
}

const MODE_LABELS: Record<number, string> = {
  0: 'DETUMBLE',
  1: 'SUNPOINT',
  2: 'NADIR',
  3: 'SAFE',
}

const EPS_MODE_LABELS: Record<number, string> = {
  0: 'NOMINAL',
  1: 'LOW POWER',
  2: 'CRITICAL',
  3: 'SAFE',
}

/**
 * Displays the "Believed" state reported by the physical hardware.
 * This is the firmware's view of the world, which may differ from truth.
 */
const HardwareState: React.FC<HardwareStateProps> = ({ state }) => {
  return (
    <div style={{
      flex: 1,
      padding: '12px',
      fontSize: '12px',
      lineHeight: 1.8,
    }}>
      <h2 style={{ color: '#ffaa00', fontSize: '14px', marginBottom: 8 }}>
        ▸ HARDWARE TELEMETRY
      </h2>

      {!state ? (
        <div style={{ color: '#666' }}>Awaiting hardware data...</div>
      ) : (
        <>
          <Section title="ADCS">
            <DataRow label="Mode"
              value={MODE_LABELS[state.adcs_mode ?? -1] ?? 'UNKNOWN'}
              color={state.adcs_mode === 0 ? '#ffaa00' : '#00ff88'} />
            <DataRow label="Quaternion" value={
              state.quat_w !== undefined
                ? `${state.quat_w.toFixed(4)}, ${state.quat_x?.toFixed(4)}, ${state.quat_y?.toFixed(4)}, ${state.quat_z?.toFixed(4)}`
                : '--'
            } />
            <DataRow label="Tumble Rate"
              value={state.tumble_rate?.toFixed(4)}
              unit="rad/s" />
          </Section>

          <Section title="EPS">
            <DataRow label="Power Mode"
              value={EPS_MODE_LABELS[state.power_mode ?? -1] ?? 'UNKNOWN'}
              color={
                state.power_mode === 2 ? '#ff4444' :
                state.power_mode === 1 ? '#ffaa00' : '#00ff88'
              } />
            <DataRow label="Battery"
              value={state.battery_voltage?.toFixed(2)}
              unit="V" />
            <DataRow label="Charge"
              value={state.charge_percent?.toFixed(0)}
              unit="%" />
            <DataRow label="Heater"
              value={state.heater_enabled ? 'ON' : 'OFF'}
              color={state.heater_enabled ? '#ffaa00' : '#666'} />
            <DataRow label="Payload"
              value={state.payload_enabled ? 'ON' : 'OFF'}
              color={state.payload_enabled ? '#00ff88' : '#666'} />
          </Section>

          <Section title="STATUS">
            <DataRow label="Source" value={state.source ?? 'hardware'} />
            <DataRow label="Timestamp"
              value={state.timestamp_ms ? `${state.timestamp_ms}ms` : '--'} />
          </Section>
        </>
      )}
    </div>
  )
}

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div style={{ marginBottom: 8 }}>
    <div style={{ color: '#888', fontSize: '11px', marginBottom: 2 }}>{title}</div>
    {children}
  </div>
)

const DataRow: React.FC<{
  label: string
  value?: string | number | null
  unit?: string
  color?: string
}> = ({ label, value, unit, color }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
    <span style={{ color: '#aaa' }}>{label}</span>
    <span style={{ color: color ?? '#00ff88' }}>
      {value ?? '--'}
      {unit && <span style={{ color: '#666', marginLeft: 4 }}>{unit}</span>}
    </span>
  </div>
)

export default HardwareState
