"""Unit tests for the environment model (eclipse, solar flux, magnetic field)."""

import numpy as np
import pytest
from app.models.environment import EnvironmentModel, sun_position_eci, EARTH_RADIUS_KM, AU_KM


@pytest.fixture
def env_model():
    return EnvironmentModel()


class TestSunPosition:
    """Tests for the analytical Sun position model."""

    def test_sun_distance_approximately_1_au(self):
        """Sun should be approximately 1 AU from Earth."""
        # J2000.0 epoch
        sun_pos = sun_position_eci(2451545.0)
        dist = np.linalg.norm(sun_pos)
        # Should be within 3% of 1 AU (Earth's orbit is slightly elliptical)
        assert 0.97 * AU_KM < dist < 1.03 * AU_KM

    def test_sun_position_is_3d(self):
        """Sun position should be a 3D vector."""
        sun_pos = sun_position_eci(2451545.0)
        assert sun_pos.shape == (3,)

    def test_sun_position_changes_over_year(self):
        """Sun's position should change significantly over 6 months."""
        pos_jan = sun_position_eci(2460310.5)  # ~Jan 2024
        pos_jul = sun_position_eci(2460310.5 + 182.5)  # ~Jul 2024
        diff = np.linalg.norm(pos_jan - pos_jul)
        # Should be roughly 2 AU apart (opposite sides of orbit)
        assert diff > 1.5 * AU_KM


class TestEclipseDetection:
    """Tests for eclipse factor computation."""

    def test_sunlit_satellite(self, env_model):
        """A satellite on the sun-side of Earth should be in sunlight."""
        # Place satellite between Earth and Sun
        sun_pos = sun_position_eci(2451545.0)
        sun_dir = sun_pos / np.linalg.norm(sun_pos)
        sat_pos = sun_dir * (EARTH_RADIUS_KM + 400)  # 400 km altitude, sun-side

        result = env_model.compute(sat_pos, 2451545.0)
        assert result["eclipse_factor"] == 1.0

    def test_eclipsed_satellite(self, env_model):
        """A satellite directly behind Earth should be in eclipse."""
        sun_pos = sun_position_eci(2451545.0)
        sun_dir = sun_pos / np.linalg.norm(sun_pos)
        # Place satellite on the opposite side of Earth from the Sun
        sat_pos = -sun_dir * (EARTH_RADIUS_KM + 400)

        result = env_model.compute(sat_pos, 2451545.0)
        assert result["eclipse_factor"] < 0.5  # Should be in shadow

    def test_eclipse_factor_range(self, env_model):
        """Eclipse factor must be between 0 and 1."""
        sat_pos = np.array([EARTH_RADIUS_KM + 400, 0, 0])
        result = env_model.compute(sat_pos, 2451545.0)
        assert 0.0 <= result["eclipse_factor"] <= 1.0


class TestSolarFlux:
    """Tests for solar flux computation."""

    def test_solar_flux_in_sunlight(self, env_model):
        """Solar flux in sunlight should be approximately 1361 W/m²."""
        sun_pos = sun_position_eci(2451545.0)
        sun_dir = sun_pos / np.linalg.norm(sun_pos)
        sat_pos = sun_dir * (EARTH_RADIUS_KM + 400)

        result = env_model.compute(sat_pos, 2451545.0)
        # Should be close to solar constant (within 5%)
        assert 1290 < result["solar_flux_w_m2"] < 1430

    def test_solar_flux_in_eclipse(self, env_model):
        """Solar flux in eclipse should be near zero."""
        sun_pos = sun_position_eci(2451545.0)
        sun_dir = sun_pos / np.linalg.norm(sun_pos)
        sat_pos = -sun_dir * (EARTH_RADIUS_KM + 400)

        result = env_model.compute(sat_pos, 2451545.0)
        assert result["solar_flux_w_m2"] < 700  # Should be reduced

    def test_solar_flux_positive(self, env_model):
        """Solar flux should never be negative."""
        sat_pos = np.array([0, EARTH_RADIUS_KM + 400, 0])
        result = env_model.compute(sat_pos, 2451545.0)
        assert result["solar_flux_w_m2"] >= 0


class TestMagneticField:
    """Tests for the dipole magnetic field model."""

    def test_magnetic_field_strength_at_leo(self, env_model):
        """Magnetic field at LEO should be ~20,000-50,000 nT."""
        sat_pos = np.array([EARTH_RADIUS_KM + 400, 0, 0])
        result = env_model.compute(sat_pos, 2451545.0)
        B = np.linalg.norm(result["magnetic_field_eci_nT"])
        assert 10000 < B < 60000, f"B-field {B} nT out of expected range"

    def test_magnetic_field_is_3d(self, env_model):
        """Magnetic field should be a 3D vector."""
        sat_pos = np.array([EARTH_RADIUS_KM + 400, 0, 0])
        result = env_model.compute(sat_pos, 2451545.0)
        assert len(result["magnetic_field_eci_nT"]) == 3

    def test_field_decreases_with_altitude(self, env_model):
        """Magnetic field should decrease with altitude (r^-3 dipole)."""
        pos_low = np.array([EARTH_RADIUS_KM + 400, 0, 0])
        pos_high = np.array([EARTH_RADIUS_KM + 2000, 0, 0])

        result_low = env_model.compute(pos_low, 2451545.0)
        result_high = env_model.compute(pos_high, 2451545.0)

        B_low = np.linalg.norm(result_low["magnetic_field_eci_nT"])
        B_high = np.linalg.norm(result_high["magnetic_field_eci_nT"])

        assert B_low > B_high, "Field should be stronger at lower altitude"

    def test_field_stronger_at_poles(self, env_model):
        """Dipole field should be stronger at poles than equator."""
        # Equatorial position
        pos_eq = np.array([EARTH_RADIUS_KM + 400, 0, 0])
        # Polar position (along Z-axis)
        pos_pole = np.array([0, 0, EARTH_RADIUS_KM + 400])

        result_eq = env_model.compute(pos_eq, 2451545.0)
        result_pole = env_model.compute(pos_pole, 2451545.0)

        B_eq = np.linalg.norm(result_eq["magnetic_field_eci_nT"])
        B_pole = np.linalg.norm(result_pole["magnetic_field_eci_nT"])

        assert B_pole > B_eq, "Polar field should be stronger than equatorial"
