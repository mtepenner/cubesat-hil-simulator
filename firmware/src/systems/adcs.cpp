/**
 * Attitude Determination & Control System (ADCS)
 *
 * Implements:
 *   - B-dot detumbling controller (uses magnetometer derivative)
 *   - Simple sun-pointing mode
 *   - Nadir pointing mode (placeholder)
 *
 * The B-dot controller is the primary detumbling algorithm:
 *   m_cmd = -k * dB/dt
 * where m_cmd is the magnetic dipole moment command and dB/dt is the
 * time derivative of the magnetic field in the body frame.
 */

#include "adcs.h"
#include <math.h>
#include <string.h>

// B-dot gain (A·m² / (nT/s)) — tuned for a 1U CubeSat
#define BDOT_GAIN 1.0e-6f

// Tumble threshold for mode switching (rad/s)
#define DETUMBLE_THRESHOLD 0.02f

// Control loop dt (seconds) — matches task period
#define ADCS_DT 0.1f

// Previous magnetic field for B-dot computation
static float prev_mag[3] = {0.0f, 0.0f, 0.0f};
static uint8_t first_update = 1;

void adcs_init(ADCSState* state) {
    memset(state, 0, sizeof(ADCSState));
    state->quaternion[0] = 1.0f;  // Identity quaternion
    state->mode = ADCS_MODE_DETUMBLE;
    first_update = 1;
}

/**
 * B-dot detumbling controller.
 * Computes control magnetic dipole proportional to -dB/dt.
 */
static void bdot_controller(ADCSState* state) {
    if (first_update) {
        // Can't compute derivative on first sample
        prev_mag[0] = state->mag_field[0];
        prev_mag[1] = state->mag_field[1];
        prev_mag[2] = state->mag_field[2];
        first_update = 0;
        return;
    }

    // Compute dB/dt
    float dBdt[3];
    for (int i = 0; i < 3; i++) {
        dBdt[i] = (state->mag_field[i] - prev_mag[i]) / ADCS_DT;
    }

    // B-dot control law: torque proportional to -dB/dt cross B
    // Simplified: magnetic moment m = -k * dB/dt
    for (int i = 0; i < 3; i++) {
        state->control_torque[i] = -BDOT_GAIN * dBdt[i];
    }

    // Save current reading for next iteration
    prev_mag[0] = state->mag_field[0];
    prev_mag[1] = state->mag_field[1];
    prev_mag[2] = state->mag_field[2];
}

/**
 * Simple sun-pointing controller.
 * Generates torque to align +Z body axis with sun vector.
 */
static void sunpoint_controller(ADCSState* state) {
    if (state->in_eclipse) {
        // Can't sun-point in eclipse, hold attitude
        state->control_torque[0] = 0.0f;
        state->control_torque[1] = 0.0f;
        state->control_torque[2] = 0.0f;
        return;
    }

    // Target: align body +Z with sun vector
    // Error = sun_vector × [0, 0, 1] (cross product gives rotation axis)
    float sun_mag = sqrtf(state->sun_vector[0] * state->sun_vector[0] +
                          state->sun_vector[1] * state->sun_vector[1] +
                          state->sun_vector[2] * state->sun_vector[2]);

    if (sun_mag < 0.01f) return;

    // Normalize sun vector
    float sx = state->sun_vector[0] / sun_mag;
    float sy = state->sun_vector[1] / sun_mag;
    float sz = state->sun_vector[2] / sun_mag;

    // Proportional control: torque = K_p * (sun × z_body)
    float Kp = 1.0e-5f;
    state->control_torque[0] = Kp * (-sy);  // Cross product: sun × [0,0,1]
    state->control_torque[1] = Kp * (sx);
    state->control_torque[2] = 0.0f;        // No torque around pointing axis
}

void adcs_update(ADCSState* state, const SensorData* sensors) {
    // Update sensor readings
    state->mag_field[0] = sensors->mag_x;
    state->mag_field[1] = sensors->mag_y;
    state->mag_field[2] = sensors->mag_z;
    state->in_eclipse = sensors->eclipse;

    // Compute tumble rate from angular velocity magnitude
    state->tumble_rate = sqrtf(
        state->angular_velocity[0] * state->angular_velocity[0] +
        state->angular_velocity[1] * state->angular_velocity[1] +
        state->angular_velocity[2] * state->angular_velocity[2]
    );

    // Compute sun vector from sensor
    state->sun_vector[0] = sensors->sun_x;
    state->sun_vector[1] = sensors->sun_y;
    state->sun_vector[2] = sensors->sun_z;

    // Mode logic
    switch (state->mode) {
        case ADCS_MODE_DETUMBLE:
            bdot_controller(state);
            // Switch to sun-pointing when tumble rate is low enough
            if (state->tumble_rate < DETUMBLE_THRESHOLD && !first_update) {
                state->mode = ADCS_MODE_SUNPOINT;
            }
            break;

        case ADCS_MODE_SUNPOINT:
            sunpoint_controller(state);
            // Fall back to detumble if tumbling again
            if (state->tumble_rate > DETUMBLE_THRESHOLD * 2.0f) {
                state->mode = ADCS_MODE_DETUMBLE;
            }
            break;

        case ADCS_MODE_NADIR:
            // Placeholder — similar to sun-pointing but targets nadir
            state->control_torque[0] = 0.0f;
            state->control_torque[1] = 0.0f;
            state->control_torque[2] = 0.0f;
            break;

        case ADCS_MODE_SAFE:
            // Zero torque — minimize power consumption
            state->control_torque[0] = 0.0f;
            state->control_torque[1] = 0.0f;
            state->control_torque[2] = 0.0f;
            break;
    }
}
