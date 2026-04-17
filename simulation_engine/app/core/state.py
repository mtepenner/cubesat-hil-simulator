"""Simulation state manager — integrates all models into a unified state."""

import numpy as np
from datetime import datetime, timezone

from ..models.orbit import OrbitalModel
from ..models.environment import EnvironmentModel
from ..models.dynamics import DynamicsModel
from .clock import SimulationClock, SimState

# J2000.0 epoch in Julian date
J2000_JD = 2451545.0


class SimulationState:
    """Central state manager for the HIL simulation."""

    def __init__(self):
        self.clock = SimulationClock(dt=1.0)  # 1-second default step
        self.orbit = OrbitalModel()
        self.environment = EnvironmentModel()
        self.dynamics = DynamicsModel()

        # Start epoch: 2024-01-01 00:00:00 UTC
        self.epoch_year = 2024
        self.epoch_month = 1
        self.epoch_day = 1

        self._last_state = None
        self._compute_state()

    def _compute_state(self) -> dict:
        """Compute full simulation state at current sim time."""
        # Convert sim_time offset to calendar date
        total_seconds = self.clock.sim_time
        days = total_seconds / 86400.0
        hours = (total_seconds % 86400) / 3600.0
        minutes = (total_seconds % 3600) / 60.0
        seconds = total_seconds % 60

        # Use fractional day approach
        day_offset = int(total_seconds // 86400)
        sec_of_day = total_seconds % 86400

        hour = int(sec_of_day // 3600)
        minute = int((sec_of_day % 3600) // 60)
        second = sec_of_day % 60

        # Simple date offset (works for short simulations)
        day = self.epoch_day + day_offset
        month = self.epoch_month
        year = self.epoch_year

        # Propagate orbit
        orbit_state = self.orbit.propagate(year, month, day, hour, minute, second)

        # Compute environment
        env_state = self.environment.compute(
            orbit_state["position_eci"],
            orbit_state["julian_date"]
        )

        # Get dynamics state
        dynamics_state = {
            "quaternion": self.dynamics.get_quaternion().tolist(),
            "angular_velocity": self.dynamics.get_angular_velocity().tolist(),
            "angular_momentum": self.dynamics.get_angular_momentum().tolist(),
            "rotational_energy": self.dynamics.get_rotational_energy(),
        }

        self._last_state = {
            "sim_time": self.clock.sim_time,
            "clock": self.clock.get_status(),
            "orbit": {
                "position_eci": orbit_state["position_eci"].tolist(),
                "velocity_eci": orbit_state["velocity_eci"].tolist(),
                "latitude": orbit_state["latitude"],
                "longitude": orbit_state["longitude"],
                "altitude": orbit_state["altitude"],
            },
            "environment": env_state,
            "dynamics": dynamics_state,
        }
        return self._last_state

    def step(self, torque: list = None) -> dict:
        """Advance simulation by one time step."""
        dt = self.clock.dt
        self.clock.step()

        torque_vec = np.array(torque) if torque else None
        self.dynamics.step(dt, torque_vec)

        return self._compute_state()

    def start(self):
        self.clock.start()

    def pause(self):
        self.clock.pause()

    def stop(self):
        self.clock.stop()
        self.dynamics.set_state([1, 0, 0, 0], [0, 0, 0])
        self._compute_state()

    def get_state(self) -> dict:
        if self._last_state is None:
            self._compute_state()
        return self._last_state
