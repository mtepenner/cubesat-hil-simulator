"""Environmental models: Eclipse, Solar Flux, Magnetic Field (IGRF dipole)."""

import numpy as np

# Constants
EARTH_RADIUS_KM = 6371.0
SUN_RADIUS_KM = 696340.0
AU_KM = 149597870.7
SOLAR_CONSTANT_W_M2 = 1361.0  # W/m^2 at 1 AU
EARTH_DIPOLE_MOMENT = 7.94e22  # A·m² (IGRF approximate)
MU_0 = 4.0 * np.pi * 1e-7  # Permeability of free space


def sun_position_eci(julian_date: float) -> np.ndarray:
    """Compute approximate Sun position in ECI coordinates (km).

    Uses the low-precision solar position algorithm from the Astronomical Almanac.
    Accuracy ~1 degree, sufficient for eclipse and flux calculations.
    """
    # Julian centuries from J2000.0
    T = (julian_date - 2451545.0) / 36525.0

    # Mean longitude (degrees)
    L0 = (280.46646 + 36000.76983 * T + 0.0003032 * T ** 2) % 360.0

    # Mean anomaly (degrees)
    M = (357.52911 + 35999.05029 * T - 0.0001537 * T ** 2) % 360.0
    M_rad = np.radians(M)

    # Equation of center (degrees)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T ** 2) * np.sin(M_rad)
         + (0.019993 - 0.000101 * T) * np.sin(2.0 * M_rad)
         + 0.000289 * np.sin(3.0 * M_rad))

    # Sun's true longitude (radians)
    sun_lon = np.radians((L0 + C) % 360.0)

    # Obliquity of ecliptic (radians)
    epsilon = np.radians(23.439291 - 0.0130042 * T)

    # Eccentricity of Earth's orbit
    e = 0.016708634 - 0.000042037 * T - 0.0000001267 * T ** 2

    # Distance from Earth to Sun (AU -> km)
    R_au = (1.000001018 * (1.0 - e ** 2)) / (1.0 + e * np.cos(M_rad))
    R_km = R_au * AU_KM

    # Sun position in ECI (equatorial coordinates)
    x = R_km * np.cos(sun_lon)
    y = R_km * np.sin(sun_lon) * np.cos(epsilon)
    z = R_km * np.sin(sun_lon) * np.sin(epsilon)

    return np.array([x, y, z])


class EnvironmentModel:
    """Computes environmental conditions at a spacecraft's orbital position."""

    def compute(self, position_eci_km: np.ndarray, julian_date: float) -> dict:
        """Compute all environmental parameters.

        Args:
            position_eci_km: Spacecraft position in ECI frame [x, y, z] in km.
            julian_date: Julian date for Sun position calculation.

        Returns:
            Dictionary with eclipse_factor, solar_flux_w_m2, and magnetic_field_eci_nT.
        """
        sun_pos = sun_position_eci(julian_date)
        eclipse_factor = self._eclipse_factor(position_eci_km, sun_pos)
        solar_flux = self._solar_flux(position_eci_km, sun_pos, eclipse_factor)
        mag_field = self._magnetic_field_dipole(position_eci_km, julian_date)

        return {
            "eclipse_factor": eclipse_factor,
            "solar_flux_w_m2": solar_flux,
            "magnetic_field_eci_nT": mag_field.tolist(),
        }

    @staticmethod
    def _eclipse_factor(sat_pos: np.ndarray, sun_pos: np.ndarray) -> float:
        """Compute eclipse factor using cylindrical shadow model.

        Returns:
            1.0 = full sunlight
            0.0 = full eclipse (umbra)
            Between 0 and 1 = penumbra
        """
        # Vector from satellite to sun
        sat_to_sun = sun_pos - sat_pos

        # Project satellite position onto the Earth-Sun line
        sun_dir = sun_pos / np.linalg.norm(sun_pos)

        # Satellite's distance along the sun direction
        proj = np.dot(sat_pos, sun_dir)

        if proj > 0:
            # Satellite is on the sun-side of Earth — in sunlight
            return 1.0

        # Satellite is behind Earth relative to the Sun
        # Perpendicular distance from the Earth-Sun line
        perp_dist = np.linalg.norm(sat_pos - proj * sun_dir)

        # Angular radii from satellite perspective
        sat_dist = np.linalg.norm(sat_pos)
        sun_dist = np.linalg.norm(sun_pos)

        # Apparent angular radius of Earth from the satellite
        if sat_dist <= EARTH_RADIUS_KM:
            return 0.0  # Inside Earth (shouldn't happen, but handle gracefully)

        earth_angular_radius = np.arcsin(EARTH_RADIUS_KM / sat_dist)

        # Angle between satellite position and Earth-Sun line
        if perp_dist < 1e-10:
            angle_from_axis = 0.0
        else:
            angle_from_axis = np.arctan2(perp_dist, abs(proj))

        # Umbra cone half-angle (simplified)
        umbra_half_angle = np.arcsin(
            (SUN_RADIUS_KM - EARTH_RADIUS_KM) / sun_dist
        )
        shadow_cone_angle = earth_angular_radius - umbra_half_angle

        # Penumbra cone half-angle
        penumbra_half_angle = np.arcsin(
            (SUN_RADIUS_KM + EARTH_RADIUS_KM) / sun_dist
        )
        penumbra_cone_angle = earth_angular_radius + penumbra_half_angle

        if angle_from_axis < shadow_cone_angle:
            return 0.0  # Full umbra
        elif angle_from_axis < penumbra_cone_angle:
            # Linear interpolation through penumbra
            frac = (angle_from_axis - shadow_cone_angle) / (
                penumbra_cone_angle - shadow_cone_angle
            )
            return min(1.0, max(0.0, frac))
        else:
            return 1.0  # Full sunlight

    @staticmethod
    def _solar_flux(sat_pos: np.ndarray, sun_pos: np.ndarray,
                    eclipse_factor: float) -> float:
        """Compute solar flux at satellite position in W/m^2."""
        # Distance from satellite to sun in AU
        sat_to_sun = sun_pos - sat_pos
        dist_km = np.linalg.norm(sat_to_sun)
        dist_au = dist_km / AU_KM

        # Inverse square law
        flux = SOLAR_CONSTANT_W_M2 / (dist_au ** 2)
        return flux * eclipse_factor

    @staticmethod
    def _magnetic_field_dipole(position_eci_km: np.ndarray,
                               julian_date: float) -> np.ndarray:
        """Compute Earth's magnetic field using a centered dipole model.

        Returns magnetic field vector in ECI frame, in nanotesla (nT).

        The dipole is aligned with Earth's rotation axis (simplified IGRF).
        B0 at equator surface ~ 30,000 nT.
        """
        B0_nT = 30000.0  # Equatorial surface field strength in nT

        r_km = np.linalg.norm(position_eci_km)
        if r_km < 1.0:
            return np.array([0.0, 0.0, 0.0])

        r_ratio = EARTH_RADIUS_KM / r_km

        # Position in spherical-ish coordinates
        # For a dipole aligned with Z-axis:
        x, y, z = position_eci_km
        r = r_km

        # Colatitude (angle from Z-axis)
        cos_theta = z / r
        sin_theta = np.sqrt(x ** 2 + y ** 2) / r if r > 0 else 0.0

        # Dipole field in spherical coordinates
        B_r = -2.0 * B0_nT * (r_ratio ** 3) * cos_theta
        B_theta = -B0_nT * (r_ratio ** 3) * sin_theta

        # Convert spherical to Cartesian (ECI)
        if sin_theta > 1e-10:
            rho = np.sqrt(x ** 2 + y ** 2)
            cos_phi = x / rho
            sin_phi = y / rho
        else:
            cos_phi = 1.0
            sin_phi = 0.0

        # Unit vectors
        r_hat = position_eci_km / r
        theta_hat = np.array([
            cos_theta * cos_phi,
            cos_theta * sin_phi,
            -sin_theta,
        ])

        B_eci = B_r * r_hat + B_theta * theta_hat
        return B_eci
