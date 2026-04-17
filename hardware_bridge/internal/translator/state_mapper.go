// Package translator maps simulation floating-point state values to raw ADC
// register values for the hardware, and parses telemetry responses.
package translator

import (
	"encoding/binary"
	"math"
)

// ADC configuration constants
const (
	ADCResolution = 4096   // 12-bit ADC
	ADCVRef       = 3.3    // Reference voltage
	MagScale      = 0.001  // Magnetometer scale: nT per LSB (adjustable)
	TempOffset    = 273.15 // Kelvin offset
)

// StateMapper translates between simulation state and hardware register values.
type StateMapper struct {
	MagXScale float64
	MagYScale float64
	MagZScale float64
	SunScale  float64
}

// NewStateMapper creates a new state mapper with default scaling factors.
func NewStateMapper() *StateMapper {
	return &StateMapper{
		MagXScale: 0.1, // nT per ADC count
		MagYScale: 0.1,
		MagZScale: 0.1,
		SunScale:  1.0, // W/m² per ADC count
	}
}

// MapToRegisters converts environment model outputs to 12-bit ADC register values.
func (sm *StateMapper) MapToRegisters(environment map[string]interface{}) map[string]uint16 {
	registers := make(map[string]uint16)

	// Magnetic field -> magnetometer ADC values
	if magField, ok := environment["magnetic_field_eci_nT"]; ok {
		if magArr, ok := magField.([]interface{}); ok && len(magArr) >= 3 {
			registers["mag_x"] = sm.floatToADC(toFloat64(magArr[0]), sm.MagXScale)
			registers["mag_y"] = sm.floatToADC(toFloat64(magArr[1]), sm.MagYScale)
			registers["mag_z"] = sm.floatToADC(toFloat64(magArr[2]), sm.MagZScale)
		}
	}

	// Solar flux -> sun sensor ADC value
	if flux, ok := environment["solar_flux_w_m2"]; ok {
		registers["sun_sensor"] = sm.floatToADC(toFloat64(flux), sm.SunScale)
	}

	// Eclipse factor -> binary eclipse indicator
	if eclipse, ok := environment["eclipse_factor"]; ok {
		if toFloat64(eclipse) < 0.5 {
			registers["eclipse"] = 1 // In eclipse
		} else {
			registers["eclipse"] = 0 // In sunlight
		}
	}

	return registers
}

// floatToADC converts a floating-point value to a 12-bit ADC register value.
// Values are centered at mid-scale (2048) and clamped to [0, 4095].
func (sm *StateMapper) floatToADC(value, scale float64) uint16 {
	midScale := float64(ADCResolution) / 2.0
	adcValue := midScale + (value / scale)

	// Clamp to valid ADC range
	if adcValue < 0 {
		adcValue = 0
	}
	if adcValue > float64(ADCResolution-1) {
		adcValue = float64(ADCResolution - 1)
	}

	return uint16(math.Round(adcValue))
}

// ParseTelemetry decodes a telemetry packet from the hardware.
// Packet format: [type(1)] [timestamp(4)] [data(N)] [status(1)]
func (sm *StateMapper) ParseTelemetry(data []byte) map[string]interface{} {
	result := make(map[string]interface{})

	if len(data) < 6 {
		result["error"] = "packet too short"
		result["raw_length"] = len(data)
		return result
	}

	result["packet_type"] = data[0]
	result["timestamp_ms"] = binary.BigEndian.Uint32(data[1:5])

	// Parse based on packet type
	switch data[0] {
	case 0x01: // ADCS telemetry
		if len(data) >= 17 {
			result["subsystem"] = "adcs"
			result["quat_w"] = bytesToFloat32(data[5:9])
			result["quat_x"] = bytesToFloat32(data[9:13])
			result["quat_y"] = bytesToFloat32(data[13:17])
		}
	case 0x02: // EPS telemetry
		if len(data) >= 11 {
			result["subsystem"] = "eps"
			result["battery_voltage"] = bytesToFloat32(data[5:9])
			result["power_mode"] = data[9]
			result["charge_percent"] = data[10]
		}
	default:
		result["subsystem"] = "unknown"
		result["raw_data"] = data[5:]
	}

	result["status"] = data[len(data)-1]
	return result
}

// GenerateMockTelemetry creates synthetic telemetry for mock mode.
func (sm *StateMapper) GenerateMockTelemetry(environment map[string]interface{}) map[string]interface{} {
	return map[string]interface{}{
		"source":          "mock",
		"subsystem":       "adcs",
		"quat_w":          1.0,
		"quat_x":          0.0,
		"quat_y":          0.0,
		"quat_z":          0.0,
		"battery_voltage": 3.7,
		"power_mode":      0,
		"charge_percent":  85,
	}
}

// Helper to convert interface{} to float64
func toFloat64(v interface{}) float64 {
	switch val := v.(type) {
	case float64:
		return val
	case float32:
		return float64(val)
	case int:
		return float64(val)
	case int64:
		return float64(val)
	default:
		return 0.0
	}
}

func bytesToFloat32(b []byte) float64 {
	if len(b) < 4 {
		return 0.0
	}
	bits := binary.BigEndian.Uint32(b)
	return float64(math.Float32frombits(bits))
}
