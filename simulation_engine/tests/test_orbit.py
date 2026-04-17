"""Unit tests for the orbital propagation model."""

import numpy as np
import pytest
from app.models.orbit import OrbitalModel, EARTH_RADIUS_KM


@pytest.fixture
def orbit_model():
    return OrbitalModel()


class TestOrbitalPropagation:
    """Tests for SGP4 orbit propagation."""

    def test_position_magnitude_is_leo(self, orbit_model):
        """LEO position should be ~6500-7200 km from Earth center."""
        state = orbit_model.propagate(2024, 1, 1, 0, 0, 0)
        r = np.linalg.norm(state["position_eci"])
        assert 6400 < r < 7200, f"Position magnitude {r} km out of LEO range"

    def test_velocity_magnitude_is_leo(self, orbit_model):
        """LEO velocity should be ~7.0-8.0 km/s."""
        state = orbit_model.propagate(2024, 1, 1, 0, 0, 0)
        v = np.linalg.norm(state["velocity_eci"])
        assert 7.0 < v < 8.0, f"Velocity magnitude {v} km/s out of LEO range"

    def test_altitude_is_positive(self, orbit_model):
        """Altitude must be positive (above Earth surface)."""
        state = orbit_model.propagate(2024, 1, 1, 12, 0, 0)
        assert state["altitude"] > 0, f"Altitude {state['altitude']} km is not positive"

    def test_latitude_range(self, orbit_model):
        """Latitude must be within [-90, 90] degrees."""
        state = orbit_model.propagate(2024, 1, 1, 6, 30, 0)
        assert -90 <= state["latitude"] <= 90

    def test_longitude_range(self, orbit_model):
        """Longitude must be within [-180, 360] degrees."""
        state = orbit_model.propagate(2024, 1, 1, 6, 30, 0)
        assert -180 <= state["longitude"] <= 360

    def test_altitude_consistent_with_position(self, orbit_model):
        """Altitude should equal |position| - Earth radius, approximately."""
        state = orbit_model.propagate(2024, 1, 1, 0, 0, 0)
        r = np.linalg.norm(state["position_eci"])
        expected_alt = r - EARTH_RADIUS_KM
        # Allow some tolerance due to Earth oblateness
        assert abs(state["altitude"] - expected_alt) < 30

    def test_propagation_changes_over_time(self, orbit_model):
        """Position should change between two different times."""
        state1 = orbit_model.propagate(2024, 1, 1, 0, 0, 0)
        state2 = orbit_model.propagate(2024, 1, 1, 0, 10, 0)
        pos_diff = np.linalg.norm(
            np.array(state1["position_eci"]) - np.array(state2["position_eci"])
        )
        assert pos_diff > 100, "Position should change significantly over 10 minutes"

    def test_julian_date_returned(self, orbit_model):
        """Julian date should be returned and be reasonable."""
        state = orbit_model.propagate(2024, 1, 1, 0, 0, 0)
        # J2000 is 2451545.0, 2024 should be roughly J2000 + 24*365.25 = ~2460310
        assert 2460000 < state["julian_date"] < 2460500

    def test_propagate_jd(self, orbit_model):
        """Test propagation by Julian date directly."""
        state = orbit_model.propagate_jd(2460310.5)
        r = np.linalg.norm(state["position_eci"])
        assert 6400 < r < 7200

    def test_position_is_3d_vector(self, orbit_model):
        """Position and velocity should be 3D vectors."""
        state = orbit_model.propagate(2024, 1, 1, 0, 0, 0)
        assert len(state["position_eci"]) == 3
        assert len(state["velocity_eci"]) == 3

    def test_custom_tle(self):
        """Test with custom TLE lines."""
        line1 = "1 25544U 98067A   24001.00000000  .00016717  00000-0  10270-3 0  9002"
        line2 = "2 25544  51.6400 208.9163 0006703  30.1579 330.0032 15.49560532999999"
        model = OrbitalModel(tle_line1=line1, tle_line2=line2, name="TEST-SAT")
        state = model.propagate(2024, 1, 1, 0, 0, 0)
        assert state["altitude"] > 0

    def test_orbital_period(self, orbit_model):
        """Orbital period for LEO should be ~90-100 minutes (~5400-6000 seconds)."""
        period = orbit_model.get_orbital_period()
        assert 5000 < period < 6500, f"Period {period}s out of expected LEO range"
