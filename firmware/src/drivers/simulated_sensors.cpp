/**
 * Simulated Sensor Driver
 *
 * Reads sensor data from the Go hardware bridge via UART instead of
 * physical I2C/SPI sensors. This is the key abstraction that enables
 * Hardware-in-the-Loop testing.
 *
 * Data is received as COBS-encoded packets over UART2:
 *   [header: 0xAA 0x55]
 *   [num_registers: 1B]
 *   [register pairs: 2B each, big-endian]
 *   [checksum: 1B XOR]
 *
 * Register mapping (from Go bridge):
 *   0: mag_x (ADC centered at 2048)
 *   1: mag_y
 *   2: mag_z
 *   3: sun_sensor
 *   4: eclipse (0 or 1)
 */

#include "simulated_sensors.h"
#include <Arduino.h>
#include <string.h>

// UART2 pins for HIL communication
#define HIL_RX_PIN 16
#define HIL_TX_PIN 17
#define HIL_BAUD   115200

#define HIL_SERIAL Serial2

// Receive buffer
#define RX_BUF_SIZE 256
static uint8_t rx_buffer[RX_BUF_SIZE];
static uint16_t rx_idx = 0;

// Latest decoded sensor data
static SensorData latest_data;
static SemaphoreHandle_t dataMutex = NULL;

/**
 * COBS decode in-place. Returns decoded length, or 0 on error.
 */
static uint16_t cobs_decode(const uint8_t* input, uint16_t length,
                            uint8_t* output) {
    uint16_t read_idx = 0;
    uint16_t write_idx = 0;

    while (read_idx < length) {
        uint8_t code = input[read_idx];
        if (code == 0) return 0;  // Error
        read_idx++;

        uint8_t block_len = code - 1;
        if (read_idx + block_len > length) return 0;  // Error

        for (uint8_t i = 0; i < block_len; i++) {
            output[write_idx++] = input[read_idx++];
        }

        if (code < 0xFF && read_idx < length) {
            output[write_idx++] = 0x00;
        }
    }

    return write_idx;
}

/**
 * Parse a decoded packet into sensor data.
 */
static void parse_packet(const uint8_t* data, uint16_t length) {
    // Minimum: header(2) + count(1) + checksum(1) = 4
    if (length < 4) return;
    if (data[0] != 0xAA || data[1] != 0x55) return;

    // Verify checksum
    uint8_t checksum = 0;
    for (uint16_t i = 0; i < length - 1; i++) {
        checksum ^= data[i];
    }
    if (checksum != data[length - 1]) return;

    uint8_t num_regs = data[2];
    if (length < (uint16_t)(3 + num_regs * 2 + 1)) return;

    // Read registers
    uint16_t regs[16];
    for (uint8_t i = 0; i < num_regs && i < 16; i++) {
        uint16_t offset = 3 + i * 2;
        regs[i] = ((uint16_t)data[offset] << 8) | data[offset + 1];
    }

    // Map registers to sensor data
    if (xSemaphoreTake(dataMutex, pdMS_TO_TICKS(5)) == pdTRUE) {
        if (num_regs > 0) latest_data.mag_x = ((float)regs[0] - 2048.0f) * 0.1f;
        if (num_regs > 1) latest_data.mag_y = ((float)regs[1] - 2048.0f) * 0.1f;
        if (num_regs > 2) latest_data.mag_z = ((float)regs[2] - 2048.0f) * 0.1f;
        if (num_regs > 3) latest_data.sun_sensor_raw = regs[3];
        if (num_regs > 4) latest_data.eclipse = regs[4] ? 1 : 0;

        // Derive sun vector from sun sensor (simplified)
        if (!latest_data.eclipse) {
            latest_data.sun_x = 0.0f;
            latest_data.sun_y = 0.0f;
            latest_data.sun_z = 1.0f;
        } else {
            latest_data.sun_x = 0.0f;
            latest_data.sun_y = 0.0f;
            latest_data.sun_z = 0.0f;
        }

        // Default battery ADC (nominal)
        latest_data.battery_adc = 3400;  // ~3.5V
        latest_data.temperature = 20.0f;
        latest_data.valid = 1;

        xSemaphoreGive(dataMutex);
    }
}

void simulated_sensors_init(void) {
    HIL_SERIAL.begin(HIL_BAUD, SERIAL_8N1, HIL_RX_PIN, HIL_TX_PIN);
    memset(&latest_data, 0, sizeof(latest_data));
    latest_data.battery_adc = 3400;
    latest_data.temperature = 20.0f;

    dataMutex = xSemaphoreCreateMutex();
    rx_idx = 0;
}

void simulated_sensors_read(SensorData* data) {
    // Check for incoming COBS-framed packets
    while (HIL_SERIAL.available()) {
        uint8_t byte = HIL_SERIAL.read();

        if (byte == 0x00) {
            // Frame delimiter — decode packet
            if (rx_idx > 0) {
                uint8_t decoded[RX_BUF_SIZE];
                uint16_t decoded_len = cobs_decode(rx_buffer, rx_idx, decoded);
                if (decoded_len > 0) {
                    parse_packet(decoded, decoded_len);
                }
            }
            rx_idx = 0;
        } else {
            if (rx_idx < RX_BUF_SIZE) {
                rx_buffer[rx_idx++] = byte;
            } else {
                rx_idx = 0;  // Buffer overflow — reset
            }
        }
    }

    // Copy latest data
    if (dataMutex != NULL && xSemaphoreTake(dataMutex, pdMS_TO_TICKS(5)) == pdTRUE) {
        memcpy(data, &latest_data, sizeof(SensorData));
        xSemaphoreGive(dataMutex);
    } else {
        memset(data, 0, sizeof(SensorData));
    }
}
