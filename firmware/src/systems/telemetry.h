#ifndef TELEMETRY_H
#define TELEMETRY_H

#include "adcs.h"
#include "eps.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Telemetry packet types.
 */
#define TLM_TYPE_ADCS  0x01
#define TLM_TYPE_EPS   0x02
#define TLM_TYPE_FULL  0x03

/**
 * Maximum telemetry packet size.
 */
#define TLM_MAX_PACKET_SIZE 128

/**
 * Initialize the telemetry subsystem.
 */
void telemetry_init(void);

/**
 * Build and send a telemetry packet containing ADCS and EPS state.
 * Data is COBS-encoded and sent over UART to the Go bridge.
 */
void telemetry_send(const ADCSState* adcs, const EPSState* eps);

#ifdef __cplusplus
}
#endif

#endif // TELEMETRY_H
