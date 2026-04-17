"""Simulation clock for synchronizing the HIL loop."""

import time
from enum import Enum


class SimState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class SimulationClock:
    """Manages the simulation time and stepping."""

    def __init__(self, time_scale: float = 1.0, dt: float = 0.1):
        """
        Args:
            time_scale: Ratio of sim time to wall time (1.0 = real-time).
            dt: Default simulation time step in seconds.
        """
        self.time_scale = time_scale
        self.dt = dt
        self.sim_time = 0.0  # Elapsed simulation time in seconds
        self.state = SimState.STOPPED
        self._wall_start = None

    def start(self):
        """Start or resume the simulation clock."""
        self.state = SimState.RUNNING
        self._wall_start = time.monotonic()

    def pause(self):
        """Pause the simulation clock."""
        self.state = SimState.PAUSED

    def stop(self):
        """Stop and reset the simulation clock."""
        self.state = SimState.STOPPED
        self.sim_time = 0.0
        self._wall_start = None

    def step(self, dt: float = None) -> float:
        """Advance simulation by one time step.

        Args:
            dt: Override time step. Uses default if None.

        Returns:
            The new simulation time.
        """
        step_dt = dt if dt is not None else self.dt
        self.sim_time += step_dt
        return self.sim_time

    def get_status(self) -> dict:
        return {
            "state": self.state.value,
            "sim_time": self.sim_time,
            "time_scale": self.time_scale,
            "dt": self.dt,
        }
