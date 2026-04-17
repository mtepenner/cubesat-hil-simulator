#ifndef SIMULATED_SENSORS_H
#define SIMULATED_SENSORS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Sensor data structure received from the Go hardware bridge.
 * In a real CubeSat, these would come from physical I2C/SPI sensors.
 */
typedef struct {
    // Magnetometer (nT) — from Go bridge via UART
    float mag_x;
    float mag_y;
    float mag_z;

    // Sun sensor — raw ADC value and computed unit vector
    float sun_x;
    float sun_y;
    float sun_z;
    uint16_t sun_sensor_raw;

    // Eclipse indicator
    uint8_t eclipse;

    // Battery ADC reading (0-4095)
    uint16_t battery_adc;

    // Temperature sensor (Celsius)
    float temperature;

    // Data valid flag
    uint8_t valid;
} SensorData;

/**
 * Initialize the simulated sensor interface (UART2).
 */
void simulated_sensors_init(void);

/**
 * Read the latest sensor data from the Go hardware bridge.
 * This replaces physical I2C/SPI sensor reads in HIL mode.
 */
void simulated_sensors_read(SensorData* data);

#ifdef __cplusplus
}
#endif

#endif // SIMULATED_SENSORS_H
