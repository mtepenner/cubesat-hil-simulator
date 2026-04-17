import React, { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface Spacecraft3DProps {
  quaternion: number[]
}

/**
 * Three.js render showing the CubeSat's physical rotation
 * based on the attitude quaternion from hardware telemetry.
 */
const Spacecraft3D: React.FC<Spacecraft3DProps> = ({ quaternion }) => {
  const meshRef = useRef<THREE.Group>(null)

  useFrame(() => {
    if (meshRef.current && quaternion.length === 4) {
      const [w, x, y, z] = quaternion
      meshRef.current.quaternion.set(x, y, z, w)
    }
  })

  return (
    <group ref={meshRef}>
      {/* CubeSat body (1U = 10cm cube) */}
      <mesh>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color="#336699" wireframe={false} />
      </mesh>

      {/* Solar panels */}
      <mesh position={[0, 0, 0.55]}>
        <planeGeometry args={[0.9, 0.9]} />
        <meshStandardMaterial color="#1a3366" side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, 0, -0.55]}>
        <planeGeometry args={[0.9, 0.9]} />
        <meshStandardMaterial color="#1a3366" side={THREE.DoubleSide} />
      </mesh>

      {/* Body axes */}
      {/* X-axis: Red */}
      <arrowHelper args={[
        new THREE.Vector3(1, 0, 0),
        new THREE.Vector3(0, 0, 0),
        1.5, 0xff0000, 0.2, 0.1
      ]} />
      {/* Y-axis: Green */}
      <arrowHelper args={[
        new THREE.Vector3(0, 1, 0),
        new THREE.Vector3(0, 0, 0),
        1.5, 0x00ff00, 0.2, 0.1
      ]} />
      {/* Z-axis: Blue */}
      <arrowHelper args={[
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(0, 0, 0),
        1.5, 0x0088ff, 0.2, 0.1
      ]} />

      {/* Antenna */}
      <mesh position={[0, 0.7, 0]}>
        <cylinderGeometry args={[0.02, 0.02, 0.4]} />
        <meshStandardMaterial color="#aaaaaa" />
      </mesh>
    </group>
  )
}

export default Spacecraft3D
