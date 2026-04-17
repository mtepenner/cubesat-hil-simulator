"""Rigid body dynamics model using quaternion kinematics."""

import numpy as np
from scipy.integrate import solve_ivp


def normalize_quaternion(q: np.ndarray) -> np.ndarray:
    """Normalize a quaternion [w, x, y, z]."""
    norm = np.linalg.norm(q)
    if norm < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0])
    return q / norm


def quaternion_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Multiply two quaternions [w, x, y, z]."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ])


def quaternion_conjugate(q: np.ndarray) -> np.ndarray:
    """Return the conjugate of quaternion [w, x, y, z]."""
    return np.array([q[0], -q[1], -q[2], -q[3]])


def rotate_vector_by_quaternion(v: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Rotate a 3D vector by a quaternion."""
    v_quat = np.array([0.0, v[0], v[1], v[2]])
    q_conj = quaternion_conjugate(q)
    rotated = quaternion_multiply(quaternion_multiply(q, v_quat), q_conj)
    return rotated[1:]


class DynamicsModel:
    """Rigid body rotational dynamics for a CubeSat.

    Uses quaternion kinematics and Euler's rotation equations.

    State vector: [q_w, q_x, q_y, q_z, omega_x, omega_y, omega_z]
    where q is the attitude quaternion and omega is the angular velocity
    in the body frame (rad/s).
    """

    def __init__(self, inertia: np.ndarray = None):
        """Initialize with the spacecraft's moment of inertia tensor.

        Args:
            inertia: 3x3 inertia tensor (kg·m²). Defaults to a 1U CubeSat.
        """
        if inertia is None:
            # Approximate 1U CubeSat (1kg, 10cm cube) inertia
            self.inertia = np.diag([0.00167, 0.00167, 0.00167])
        else:
            self.inertia = np.array(inertia)

        self.inertia_inv = np.linalg.inv(self.inertia)

        # State: [qw, qx, qy, qz, wx, wy, wz]
        self.state = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    def get_quaternion(self) -> np.ndarray:
        """Return current attitude quaternion [w, x, y, z]."""
        return self.state[:4].copy()

    def get_angular_velocity(self) -> np.ndarray:
        """Return current angular velocity in body frame [wx, wy, wz] rad/s."""
        return self.state[4:7].copy()

    def set_state(self, quaternion: np.ndarray, angular_velocity: np.ndarray):
        """Set the dynamics state."""
        q = normalize_quaternion(np.array(quaternion))
        self.state = np.concatenate([q, np.array(angular_velocity)])

    def _derivatives(self, t: float, state: np.ndarray,
                     torque: np.ndarray) -> np.ndarray:
        """Compute state derivatives for the rigid body equations of motion.

        Quaternion kinematics: dq/dt = 0.5 * Omega(omega) * q
        Euler's equations: I * d_omega/dt = torque - omega × (I * omega)
        """
        q = state[:4]
        omega = state[4:7]

        # Quaternion kinematics
        # dq/dt = 0.5 * q * [0, omega]
        omega_quat = np.array([0.0, omega[0], omega[1], omega[2]])
        dq_dt = 0.5 * quaternion_multiply(q, omega_quat)

        # Euler's rotation equations
        I_omega = self.inertia @ omega
        cross = np.cross(omega, I_omega)
        d_omega_dt = self.inertia_inv @ (torque - cross)

        return np.concatenate([dq_dt, d_omega_dt])

    def step(self, dt: float, torque: np.ndarray = None) -> dict:
        """Advance dynamics by dt seconds.

        Args:
            dt: Time step in seconds.
            torque: External torque vector in body frame [Tx, Ty, Tz] in N·m.

        Returns:
            Dictionary with updated quaternion and angular_velocity.
        """
        if torque is None:
            torque = np.array([0.0, 0.0, 0.0])
        else:
            torque = np.array(torque)

        result = solve_ivp(
            fun=lambda t, y: self._derivatives(t, y, torque),
            t_span=(0, dt),
            y0=self.state,
            method="RK45",
            rtol=1e-9,
            atol=1e-12,
        )

        self.state = result.y[:, -1]
        # Re-normalize quaternion
        self.state[:4] = normalize_quaternion(self.state[:4])

        return {
            "quaternion": self.state[:4].tolist(),
            "angular_velocity": self.state[4:7].tolist(),
        }

    def get_angular_momentum(self) -> np.ndarray:
        """Return angular momentum in body frame (kg·m²/s)."""
        return self.inertia @ self.get_angular_velocity()

    def get_rotational_energy(self) -> float:
        """Return rotational kinetic energy (J)."""
        omega = self.get_angular_velocity()
        return 0.5 * np.dot(omega, self.inertia @ omega)
