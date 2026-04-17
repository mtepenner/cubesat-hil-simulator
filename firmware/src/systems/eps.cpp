/**
 * Electrical Power System (EPS)
 *
 * Manages the CubeSat's power budget:
 *   - Monitors battery voltage, current, and temperature
 *   - Estimates state of charge
 *   - Manages power modes based on energy availability
 *   - Controls heaters and payload power
 *
 * Power mode transitions:
 *   NOMINAL -> LOW_POWER:  Battery < 30%
 *   LOW_POWER -> CRITICAL: Battery < 15%
 *   CRITICAL -> LOW_POWER: Battery > 20%
 *   LOW_POWER -> NOMINAL:  Battery > 40%
 */

#include "eps.h"
#include <string.h>

// Battery thresholds (percentage)
#define BATTERY_NOMINAL_THRESHOLD    40.0f
#define BATTERY_LOW_POWER_THRESHOLD  30.0f
#define BATTERY_CRITICAL_THRESHOLD   15.0f
#define BATTERY_RECOVERY_THRESHOLD   20.0f

// Temperature thresholds (Celsius)
#define TEMP_HEATER_ON   -10.0f
#define TEMP_HEATER_OFF   0.0f

// Nominal battery voltage range
#define BATTERY_FULL_VOLTAGE    4.2f
#define BATTERY_EMPTY_VOLTAGE   3.0f

// Solar panel efficiency model
#define SOLAR_PANEL_AREA       0.01f  // m² per panel (1U face)
#define SOLAR_CELL_EFFICIENCY  0.28f  // 28% triple-junction cells
#define NUM_SOLAR_PANELS       6      // 6 faces of a 1U cube

void eps_init(EPSState* state) {
    memset(state, 0, sizeof(EPSState));
    state->battery_voltage = 3.7f;
    state->battery_charge_pct = 70.0f;
    state->battery_temperature = 20.0f;
    state->mode = EPS_MODE_NOMINAL;
    state->heater_enabled = 0;
    state->payload_enabled = 1;
    state->power_budget = 2.0f;  // 2W initial budget
}

/**
 * Estimate battery charge percentage from voltage.
 * Uses a simple linear model between empty and full voltage.
 */
static float estimate_charge(float voltage) {
    if (voltage >= BATTERY_FULL_VOLTAGE) return 100.0f;
    if (voltage <= BATTERY_EMPTY_VOLTAGE) return 0.0f;
    return ((voltage - BATTERY_EMPTY_VOLTAGE) /
            (BATTERY_FULL_VOLTAGE - BATTERY_EMPTY_VOLTAGE)) * 100.0f;
}

/**
 * Calculate solar power generation based on flux and eclipse state.
 */
static float calculate_solar_power(const SensorData* sensors) {
    if (sensors->eclipse) {
        return 0.0f;
    }
    // Solar power = flux * area * efficiency * illumination_factor
    float flux = sensors->sun_sensor_raw * 1.0f;  // Approximation from ADC
    // Simplified: assume ~30% average panel illumination
    float illumination_factor = 0.3f;
    return flux * SOLAR_PANEL_AREA * NUM_SOLAR_PANELS *
           SOLAR_CELL_EFFICIENCY * illumination_factor;
}

/**
 * Update power mode based on battery state.
 */
static void update_power_mode(EPSState* state) {
    switch (state->mode) {
        case EPS_MODE_NOMINAL:
            if (state->battery_charge_pct < BATTERY_LOW_POWER_THRESHOLD) {
                state->mode = EPS_MODE_LOW_POWER;
                state->payload_enabled = 0;
            }
            break;

        case EPS_MODE_LOW_POWER:
            if (state->battery_charge_pct < BATTERY_CRITICAL_THRESHOLD) {
                state->mode = EPS_MODE_CRITICAL;
                state->payload_enabled = 0;
            } else if (state->battery_charge_pct > BATTERY_NOMINAL_THRESHOLD) {
                state->mode = EPS_MODE_NOMINAL;
                state->payload_enabled = 1;
            }
            break;

        case EPS_MODE_CRITICAL:
            if (state->battery_charge_pct > BATTERY_RECOVERY_THRESHOLD) {
                state->mode = EPS_MODE_LOW_POWER;
            }
            break;

        case EPS_MODE_SAFE:
            // Only exit safe mode via ground command
            break;
    }
}

void eps_update(EPSState* state, const SensorData* sensors) {
    // Update battery voltage from ADC reading
    // ADC maps 0-4095 -> 0-BATTERY_FULL_VOLTAGE
    state->battery_voltage = (sensors->battery_adc / 4095.0f) * BATTERY_FULL_VOLTAGE;
    state->battery_charge_pct = estimate_charge(state->battery_voltage);

    // Update temperature
    state->battery_temperature = sensors->temperature;

    // Calculate solar power generation
    state->solar_power = calculate_solar_power(sensors);

    // Thermal management
    if (state->battery_temperature < TEMP_HEATER_ON) {
        state->heater_enabled = 1;
    } else if (state->battery_temperature > TEMP_HEATER_OFF) {
        state->heater_enabled = 0;
    }

    // Estimate power budget
    float base_consumption = 0.5f;  // 500mW baseline
    float adcs_consumption = 0.3f;  // ADCS always on
    float heater_consumption = state->heater_enabled ? 0.5f : 0.0f;
    float payload_consumption = state->payload_enabled ? 1.0f : 0.0f;

    state->power_consumed = base_consumption + adcs_consumption +
                           heater_consumption + payload_consumption;
    state->power_budget = state->solar_power - state->power_consumed;

    // Battery current (positive = charging)
    state->battery_current = state->power_budget / state->battery_voltage;

    // Count illuminated panels (simplified)
    state->panels_illuminated = sensors->eclipse ? 0 : 3;  // ~3 panels see sun

    // Update power mode
    update_power_mode(state);
}
