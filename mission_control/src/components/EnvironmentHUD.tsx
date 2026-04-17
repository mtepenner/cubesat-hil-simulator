import React from 'react'
import { SimulationState } from '../hooks/useHILStream'

interface EnvironmentHUDProps {
  state: SimulationState | null
}

/**
 * Displays the "Truth" state from the Python simulation engine.
 * Shows orbital parameters, environment conditions, and dynamics.
 */
const EnvironmentHUD: React.FC<EnvironmentHUDProps> = ({ state }) => {
  const orbit = state?.orbit
  const env = state?.environment
  const dyn = state?.dynamics

  return (
    <div style={{
      flex: 1,
      padding: '12px',
      borderBottom: '1px solid #333',
      fontSize: '12px',
      lineHeight: 1.8,
    }}>
      <h2 style={{ color: '#00ff88', fontSize: '14px', marginBottom: 8 }}>
        ▸ SIMULATION TRUTH
      </h2>

      <Section title="ORBIT">
        <DataRow label="Altitude" value={orbit?.altitude?.toFixed(1)} unit="km" />
        <DataRow label="Latitude" value={orbit?.latitude?.toFixed(3)} unit="°" />
        <DataRow label="Longitude" value={orbit?.longitude?.toFixed(3)} unit="°" />
        <DataRow label="Velocity"
          value={orbit?.velocity_eci
            ? Math.sqrt(
                orbit.velocity_eci[0] ** 2 +
                orbit.velocity_eci[1] ** 2 +
                orbit.velocity_eci[2] ** 2
              ).toFixed(3)
            : '--'}
          unit="km/s" />
      </Section>

      <Section title="ENVIRONMENT">
        <DataRow label="Eclipse" value={
          env?.eclipse_factor !== undefined
            ? env.eclipse_factor < 0.5 ? '☀ SHADOW' : '☀ SUNLIT'
            : '--'
        } />
        <DataRow label="Solar Flux" value={env?.solar_flux_w_m2?.toFixed(1)} unit="W/m²" />
        <DataRow label="|B| Field"
          value={env?.magnetic_field_eci_nT
            ? Math.sqrt(
                env.magnetic_field_eci_nT[0] ** 2 +
                env.magnetic_field_eci_nT[1] ** 2 +
                env.magnetic_field_eci_nT[2] ** 2
              ).toFixed(0)
            : '--'}
          unit="nT" />
      </Section>

      <Section title="DYNAMICS">
        <DataRow label="Quaternion" value={
          dyn?.quaternion
            ? dyn.quaternion.map((v: number) => v.toFixed(4)).join(', ')
            : '--'
        } />
        <DataRow label="ω (rad/s)" value={
          dyn?.angular_velocity
            ? dyn.angular_velocity.map((v: number) => v.toFixed(4)).join(', ')
            : '--'
        } />
      </Section>
    </div>
  )
}

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div style={{ marginBottom: 8 }}>
    <div style={{ color: '#888', fontSize: '11px', marginBottom: 2 }}>{title}</div>
    {children}
  </div>
)

const DataRow: React.FC<{ label: string; value?: string | null; unit?: string }> = ({
  label, value, unit
}) => (
  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
    <span style={{ color: '#aaa' }}>{label}</span>
    <span>
      {value ?? '--'}
      {unit && <span style={{ color: '#666', marginLeft: 4 }}>{unit}</span>}
    </span>
  </div>
)

export default EnvironmentHUD
