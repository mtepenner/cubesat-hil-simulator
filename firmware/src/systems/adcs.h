#ifndef ADCS_H
#define ADCS_H

#include <stdint.h>
#include "../../drivers/simulated_sensors.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * ADCS operating modes.
 */
typedef enum {
    ADCS_MODE_DETUMBLE = 0,   // B-dot controller for initial detumbling
    ADCS_MODE_SUNPOINT,        // Point solar panels at the sun
    ADCS_MODE_NADIR,           // Point camera at Earth
    ADCS_MODE_SAFE             // Minimum power attitude hold
} ADCSMode;

/**
 * ADCS state structure.
 */
typedef struct {
    // Estimated attitude quaternion [w, x, y, z]
    float quaternion[4];

    // Estimated angular velocity (rad/s) in body frame
    float angular_velocity[3];

    // Magnetometer reading (nT) in body frame
    float mag_field[3];

    // Control torque output (N·m)
    float control_torque[3];

    // Current operating mode
    ADCSMode mode;

    // Tumble rate magnitude (rad/s)
    float tumble_rate;

    // Sun vector in body frame (unit vector, valid when not eclipsed)
    float sun_vector[3];

    // Is the satellite in eclipse?
    uint8_t in_eclipse;
} ADCSState;

/**
 * Initialize the ADCS subsystem.
 */
void adcs_init(ADCSState* state);

/**
 * Update ADCS with new sensor data and compute control output.
 */
void adcs_update(ADCSState* state, const SensorData* sensors);

#ifdef __cplusplus
}
#endif

#endif // ADCS_H
