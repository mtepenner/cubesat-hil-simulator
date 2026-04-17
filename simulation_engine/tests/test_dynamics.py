"""Unit tests for the rigid body dynamics model."""

import numpy as np
import pytest
from app.models.dynamics import (
    DynamicsModel,
    normalize_quaternion,
    quaternion_multiply,
    quaternion_conjugate,
    rotate_vector_by_quaternion,
)


class TestQuaternionOperations:
    """Tests for basic quaternion math."""

    def test_normalize_unit_quaternion(self):
        """Normalizing an already-unit quaternion should return it unchanged."""
        q = np.array([1.0, 0.0, 0.0, 0.0])
        result = normalize_quaternion(q)
        np.testing.assert_array_almost_equal(result, q)

    def test_normalize_non_unit_quaternion(self):
        """Normalized quaternion should have unit norm."""
        q = np.array([2.0, 1.0, 1.0, 1.0])
        result = normalize_quaternion(q)
        assert abs(np.linalg.norm(result) - 1.0) < 1e-10

    def test_identity_quaternion_multiply(self):
        """Multiplying by identity should return the same quaternion."""
        identity = np.array([1.0, 0.0, 0.0, 0.0])
        q = normalize_quaternion(np.array([0.5, 0.5, 0.5, 0.5]))
        result = quaternion_multiply(identity, q)
        np.testing.assert_array_almost_equal(result, q)

    def test_quaternion_multiply_conjugate_gives_identity(self):
        """q * q_conjugate should give the identity quaternion."""
        q = normalize_quaternion(np.array([1.0, 2.0, 3.0, 4.0]))
        q_conj = quaternion_conjugate(q)
        result = quaternion_multiply(q, q_conj)
        np.testing.assert_array_almost_equal(result, [1, 0, 0, 0], decimal=10)

    def test_rotate_vector_identity(self):
        """Rotating by identity quaternion should not change the vector."""
        v = np.array([1.0, 2.0, 3.0])
        q_id = np.array([1.0, 0.0, 0.0, 0.0])
        result = rotate_vector_by_quaternion(v, q_id)
        np.testing.assert_array_almost_equal(result, v)

    def test_rotate_90_degrees_around_z(self):
        """Rotating [1, 0, 0] by 90° around Z should give [0, 1, 0]."""
        angle = np.pi / 2
        q = np.array([np.cos(angle / 2), 0, 0, np.sin(angle / 2)])
        v = np.array([1.0, 0.0, 0.0])
        result = rotate_vector_by_quaternion(v, q)
        np.testing.assert_array_almost_equal(result, [0, 1, 0], decimal=10)

    def test_rotate_preserves_magnitude(self):
        """Rotation should preserve vector magnitude."""
        q = normalize_quaternion(np.array([0.7, 0.3, 0.5, 0.1]))
        v = np.array([3.0, 4.0, 5.0])
        result = rotate_vector_by_quaternion(v, q)
        assert abs(np.linalg.norm(result) - np.linalg.norm(v)) < 1e-10


class TestDynamicsModel:
    """Tests for the rigid body dynamics integration."""

    @pytest.fixture
    def model(self):
        return DynamicsModel()

    def test_initial_state_is_identity(self, model):
        """Initial quaternion should be identity, angular velocity zero."""
        q = model.get_quaternion()
        w = model.get_angular_velocity()
        np.testing.assert_array_almost_equal(q, [1, 0, 0, 0])
        np.testing.assert_array_almost_equal(w, [0, 0, 0])

    def test_zero_torque_preserves_zero_state(self, model):
        """With no angular velocity and no torque, state should not change."""
        model.step(1.0)
        q = model.get_quaternion()
        w = model.get_angular_velocity()
        np.testing.assert_array_almost_equal(q, [1, 0, 0, 0], decimal=8)
        np.testing.assert_array_almost_equal(w, [0, 0, 0], decimal=8)

    def test_constant_spin_no_torque(self, model):
        """Constant spin with no torque should preserve angular velocity (spherical inertia)."""
        initial_omega = np.array([0.0, 0.0, 0.1])  # 0.1 rad/s around z
        model.set_state([1, 0, 0, 0], initial_omega)

        model.step(1.0)

        omega = model.get_angular_velocity()
        # For spherical inertia, angular velocity should be constant
        np.testing.assert_array_almost_equal(omega, initial_omega, decimal=6)

    def test_torque_changes_angular_velocity(self, model):
        """Applying torque should change angular velocity."""
        torque = np.array([0.001, 0.0, 0.0])  # Small torque around x
        model.step(1.0, torque=torque)

        omega = model.get_angular_velocity()
        assert omega[0] > 0, "Torque around x should increase omega_x"

    def test_quaternion_remains_normalized(self, model):
        """Quaternion should remain normalized after integration."""
        model.set_state([1, 0, 0, 0], [0.1, 0.2, 0.05])

        for _ in range(100):
            model.step(0.1)

        q = model.get_quaternion()
        norm = np.linalg.norm(q)
        assert abs(norm - 1.0) < 1e-6, f"Quaternion norm {norm} drifted from 1.0"

    def test_angular_momentum_conservation(self, model):
        """Without torque, angular momentum should be conserved."""
        model.set_state([1, 0, 0, 0], [0.1, 0.0, 0.05])
        L_initial = np.linalg.norm(model.get_angular_momentum())

        for _ in range(50):
            model.step(0.1)

        L_final = np.linalg.norm(model.get_angular_momentum())
        assert abs(L_initial - L_final) / (L_initial + 1e-20) < 1e-4, \
            f"Angular momentum changed from {L_initial} to {L_final}"

    def test_rotational_energy_conservation(self, model):
        """Without torque, rotational energy should be conserved."""
        model.set_state([1, 0, 0, 0], [0.1, 0.2, 0.05])
        E_initial = model.get_rotational_energy()

        for _ in range(50):
            model.step(0.1)

        E_final = model.get_rotational_energy()
        assert abs(E_initial - E_final) / (E_initial + 1e-20) < 1e-4, \
            f"Energy changed from {E_initial} to {E_final}"

    def test_custom_inertia_tensor(self):
        """Test with non-spherical inertia tensor."""
        inertia = np.diag([0.002, 0.003, 0.004])
        model = DynamicsModel(inertia=inertia)

        model.set_state([1, 0, 0, 0], [0.1, 0.0, 0.0])
        model.step(1.0)

        q = model.get_quaternion()
        assert np.linalg.norm(q) > 0.99

    def test_step_returns_dict(self, model):
        """Step should return a dict with quaternion and angular_velocity."""
        result = model.step(1.0)
        assert "quaternion" in result
        assert "angular_velocity" in result
        assert len(result["quaternion"]) == 4
        assert len(result["angular_velocity"]) == 3

    def test_rotation_accumulates(self, model):
        """Quaternion should change when spinning."""
        model.set_state([1, 0, 0, 0], [0.0, 0.0, 1.0])  # 1 rad/s around z

        model.step(1.0)
        q = model.get_quaternion()

        # After 1 second at 1 rad/s, quaternion should have changed significantly
        assert q[0] < 0.95, "Quaternion should have rotated away from identity"
