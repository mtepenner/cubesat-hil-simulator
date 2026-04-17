"""Orbital model using Skyfield SGP4/TLE propagation."""

import numpy as np
from skyfield.api import load, EarthSatellite

# Default TLE: ISS as a representative LEO CubeSat orbit
DEFAULT_NAME = "CUBESAT-HIL"
DEFAULT_TLE_LINE1 = "1 25544U 98067A   24001.00000000  .00016717  00000-0  10270-3 0  9002"
DEFAULT_TLE_LINE2 = "2 25544  51.6400 208.9163 0006703  30.1579 330.0032 15.49560532999999"

# Earth radius in km
EARTH_RADIUS_KM = 6371.0


class OrbitalModel:
    """SGP4-based orbital propagator using Skyfield."""

    def __init__(self, tle_line1: str = None, tle_line2: str = None, name: str = None):
        self.ts = load.timescale(builtin=True)
        self.name = name or DEFAULT_NAME
        line1 = tle_line1 or DEFAULT_TLE_LINE1
        line2 = tle_line2 or DEFAULT_TLE_LINE2
        self.satellite = EarthSatellite(line1, line2, self.name, self.ts)

    def propagate(self, year: int, month: int, day: int,
                  hour: int = 0, minute: int = 0, second: float = 0.0) -> dict:
        """Propagate orbit to a given UTC time.

        Returns dict with:
            position_eci: [x, y, z] in km (Earth-Centered Inertial)
            velocity_eci: [vx, vy, vz] in km/s
            latitude: degrees
            longitude: degrees
            altitude: km above Earth surface
            julian_date: Julian date of the propagation time
        """
        t = self.ts.utc(year, month, day, hour, minute, second)
        geocentric = self.satellite.at(t)

        position_km = geocentric.position.km
        velocity_km_s = geocentric.velocity.km_per_s

        subpoint = geocentric.subpoint()
        latitude = subpoint.latitude.degrees
        longitude = subpoint.longitude.degrees
        altitude = subpoint.elevation.km

        return {
            "position_eci": np.array(position_km),
            "velocity_eci": np.array(velocity_km_s),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "altitude": float(altitude),
            "julian_date": t.tt,
        }

    def propagate_jd(self, jd: float) -> dict:
        """Propagate orbit to a given Julian date."""
        t = self.ts.tt_jd(jd)
        geocentric = self.satellite.at(t)

        position_km = geocentric.position.km
        velocity_km_s = geocentric.velocity.km_per_s

        subpoint = geocentric.subpoint()

        return {
            "position_eci": np.array(position_km),
            "velocity_eci": np.array(velocity_km_s),
            "latitude": float(subpoint.latitude.degrees),
            "longitude": float(subpoint.longitude.degrees),
            "altitude": float(subpoint.elevation.km),
            "julian_date": jd,
        }

    def get_orbital_period(self) -> float:
        """Return approximate orbital period in seconds from TLE mean motion."""
        # Mean motion is in revolutions per day
        mean_motion_rev_per_day = self.satellite.model.no_kozai / (2.0 * np.pi) * 1440.0
        if mean_motion_rev_per_day <= 0:
            return 0.0
        return 86400.0 / mean_motion_rev_per_day
