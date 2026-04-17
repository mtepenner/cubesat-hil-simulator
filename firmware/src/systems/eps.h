#ifndef EPS_H
#define EPS_H

#include <stdint.h>
#include "../../drivers/simulated_sensors.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * EPS power modes.
 */
typedef enum {
    EPS_MODE_NOMINAL = 0,  // Normal operations
    EPS_MODE_LOW_POWER,    // Reduced operations (non-essential systems off)
    EPS_MODE_CRITICAL,     // Emergency — only essential systems
    EPS_MODE_SAFE          // Pre-deployment safe mode
} EPSMode;

/**
 * EPS state structure.
 */
typedef struct {
    // Battery state
    float battery_voltage;        // Volts
    float battery_current;        // Amps (positive = charging)
    float battery_charge_pct;     // Percentage (0-100)
    float battery_temperature;    // Celsius

    // Solar panel state
    float solar_power;            // Watts generated
    uint8_t panels_illuminated;   // Number of illuminated panels

    // Power management
    EPSMode mode;
    float power_budget;           // Available power (W)
    float power_consumed;         // Current consumption (W)

    // Flags
    uint8_t heater_enabled;
    uint8_t payload_enabled;
} EPSState;

/**
 * Initialize the EPS subsystem.
 */
void eps_init(EPSState* state);

/**
 * Update EPS with new sensor data.
 */
void eps_update(EPSState* state, const SensorData* sensors);

#ifdef __cplusplus
}
#endif

#endif // EPS_H
