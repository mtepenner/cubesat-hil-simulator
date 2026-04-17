/**
 * Telemetry System
 *
 * Packages ADCS and EPS state into byte arrays for transmission
 * to the Go hardware bridge. Uses COBS encoding for packet framing.
 *
 * Packet format:
 *   [type: 1 byte]
 *   [timestamp_ms: 4 bytes, big-endian]
 *   [payload: variable]
 *   [status: 1 byte]
 *
 * ADCS payload (type 0x01):
 *   [quat_w: 4B float] [quat_x: 4B float] [quat_y: 4B float] [quat_z: 4B float]
 *   [omega_x: 4B float] [omega_y: 4B float] [omega_z: 4B float]
 *   [mode: 1B]
 *
 * EPS payload (type 0x02):
 *   [battery_v: 4B float] [battery_pct: 1B] [solar_power: 4B float]
 *   [power_mode: 1B] [heater: 1B] [payload: 1B]
 */

#include "telemetry.h"
#include <Arduino.h>
#include <string.h>

// UART2 for HIL communication (same as simulated_sensors)
#define HIL_SERIAL Serial2

static uint8_t tx_buffer[TLM_MAX_PACKET_SIZE];
static uint8_t cobs_buffer[TLM_MAX_PACKET_SIZE + 16];

/**
 * COBS encode a buffer. Returns the encoded length.
 */
static uint16_t cobs_encode(const uint8_t* input, uint16_t length,
                            uint8_t* output) {
    uint16_t read_idx = 0;
    uint16_t write_idx = 1;
    uint16_t code_idx = 0;
    uint8_t code = 1;

    while (read_idx < length) {
        if (input[read_idx] == 0x00) {
            output[code_idx] = code;
            code_idx = write_idx;
            write_idx++;
            code = 1;
            read_idx++;
        } else {
            output[write_idx] = input[read_idx];
            write_idx++;
            read_idx++;
            code++;
            if (code == 0xFF) {
                output[code_idx] = code;
                code_idx = write_idx;
                write_idx++;
                code = 1;
            }
        }
    }
    output[code_idx] = code;

    return write_idx;
}

/**
 * Write a float32 to a buffer in big-endian format.
 */
static void write_float(uint8_t* buf, float value) {
    union {
        float f;
        uint8_t b[4];
    } conv;
    conv.f = value;
    // Big-endian
    buf[0] = conv.b[3];
    buf[1] = conv.b[2];
    buf[2] = conv.b[1];
    buf[3] = conv.b[0];
}

/**
 * Write a uint32 to a buffer in big-endian format.
 */
static void write_uint32(uint8_t* buf, uint32_t value) {
    buf[0] = (value >> 24) & 0xFF;
    buf[1] = (value >> 16) & 0xFF;
    buf[2] = (value >> 8) & 0xFF;
    buf[3] = value & 0xFF;
}

void telemetry_init(void) {
    memset(tx_buffer, 0, sizeof(tx_buffer));
    memset(cobs_buffer, 0, sizeof(cobs_buffer));
}

void telemetry_send(const ADCSState* adcs, const EPSState* eps) {
    uint16_t offset = 0;
    uint32_t timestamp = millis();

    // === ADCS Telemetry Packet ===
    tx_buffer[offset++] = TLM_TYPE_ADCS;
    write_uint32(&tx_buffer[offset], timestamp);
    offset += 4;

    // Quaternion
    write_float(&tx_buffer[offset], adcs->quaternion[0]); offset += 4;
    write_float(&tx_buffer[offset], adcs->quaternion[1]); offset += 4;
    write_float(&tx_buffer[offset], adcs->quaternion[2]); offset += 4;
    write_float(&tx_buffer[offset], adcs->quaternion[3]); offset += 4;

    // Angular velocity
    write_float(&tx_buffer[offset], adcs->angular_velocity[0]); offset += 4;
    write_float(&tx_buffer[offset], adcs->angular_velocity[1]); offset += 4;
    write_float(&tx_buffer[offset], adcs->angular_velocity[2]); offset += 4;

    // Control torque
    write_float(&tx_buffer[offset], adcs->control_torque[0]); offset += 4;
    write_float(&tx_buffer[offset], adcs->control_torque[1]); offset += 4;
    write_float(&tx_buffer[offset], adcs->control_torque[2]); offset += 4;

    // Mode and tumble rate
    tx_buffer[offset++] = (uint8_t)adcs->mode;
    write_float(&tx_buffer[offset], adcs->tumble_rate); offset += 4;

    // Status byte (0x00 = OK)
    tx_buffer[offset++] = 0x00;

    // COBS encode and send
    uint16_t encoded_len = cobs_encode(tx_buffer, offset, cobs_buffer);
    cobs_buffer[encoded_len] = 0x00;  // Frame delimiter
    HIL_SERIAL.write(cobs_buffer, encoded_len + 1);

    // === EPS Telemetry Packet ===
    offset = 0;
    tx_buffer[offset++] = TLM_TYPE_EPS;
    write_uint32(&tx_buffer[offset], timestamp);
    offset += 4;

    write_float(&tx_buffer[offset], eps->battery_voltage); offset += 4;
    tx_buffer[offset++] = (uint8_t)eps->battery_charge_pct;
    write_float(&tx_buffer[offset], eps->solar_power); offset += 4;
    tx_buffer[offset++] = (uint8_t)eps->mode;
    tx_buffer[offset++] = eps->heater_enabled;
    tx_buffer[offset++] = eps->payload_enabled;
    write_float(&tx_buffer[offset], eps->power_consumed); offset += 4;

    // Status byte
    tx_buffer[offset++] = 0x00;

    // COBS encode and send
    encoded_len = cobs_encode(tx_buffer, offset, cobs_buffer);
    cobs_buffer[encoded_len] = 0x00;
    HIL_SERIAL.write(cobs_buffer, encoded_len + 1);
}
