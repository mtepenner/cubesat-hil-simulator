package translator

import (
	"testing"
)

func TestNewStateMapper(t *testing.T) {
	sm := NewStateMapper()
	if sm == nil {
		t.Fatal("NewStateMapper returned nil")
	}
	if sm.MagXScale != 0.1 {
		t.Errorf("MagXScale = %f, want 0.1", sm.MagXScale)
	}
}

func TestMapToRegisters(t *testing.T) {
	sm := NewStateMapper()
	env := map[string]interface{}{
		"magnetic_field_eci_nT": []interface{}{100.0, -50.0, 200.0},
		"solar_flux_w_m2":       1361.0,
		"eclipse_factor":        1.0,
	}

	registers := sm.MapToRegisters(env)

	// Check that registers were created
	if _, ok := registers["mag_x"]; !ok {
		t.Error("Missing mag_x register")
	}
	if _, ok := registers["mag_y"]; !ok {
		t.Error("Missing mag_y register")
	}
	if _, ok := registers["mag_z"]; !ok {
		t.Error("Missing mag_z register")
	}
	if _, ok := registers["sun_sensor"]; !ok {
		t.Error("Missing sun_sensor register")
	}

	// Eclipse should be 0 (in sunlight)
	if registers["eclipse"] != 0 {
		t.Errorf("eclipse = %d, want 0 (sunlight)", registers["eclipse"])
	}
}

func TestMapToRegistersEclipse(t *testing.T) {
	sm := NewStateMapper()
	env := map[string]interface{}{
		"eclipse_factor": 0.0,
	}

	registers := sm.MapToRegisters(env)

	// Eclipse should be 1 (in shadow)
	if registers["eclipse"] != 1 {
		t.Errorf("eclipse = %d, want 1 (shadow)", registers["eclipse"])
	}
}

func TestFloatToADCClamping(t *testing.T) {
	sm := NewStateMapper()

	// Very large positive value should clamp to max
	result := sm.floatToADC(1e10, 1.0)
	if result != 4095 {
		t.Errorf("Large positive clamped to %d, want 4095", result)
	}

	// Very large negative value should clamp to 0
	result = sm.floatToADC(-1e10, 1.0)
	if result != 0 {
		t.Errorf("Large negative clamped to %d, want 0", result)
	}
}

func TestParseTelemetryShortPacket(t *testing.T) {
	sm := NewStateMapper()
	result := sm.ParseTelemetry([]byte{0x01, 0x02})
	if _, ok := result["error"]; !ok {
		t.Error("Expected error for short packet")
	}
}

func TestGenerateMockTelemetry(t *testing.T) {
	sm := NewStateMapper()
	env := map[string]interface{}{}
	mock := sm.GenerateMockTelemetry(env)

	if mock["source"] != "mock" {
		t.Errorf("source = %v, want 'mock'", mock["source"])
	}
	if mock["subsystem"] != "adcs" {
		t.Errorf("subsystem = %v, want 'adcs'", mock["subsystem"])
	}
}

func TestToFloat64(t *testing.T) {
	cases := []struct {
		input    interface{}
		expected float64
	}{
		{1.0, 1.0},
		{float32(2.5), 2.5},
		{42, 42.0},
		{int64(100), 100.0},
		{"not a number", 0.0},
	}

	for _, tc := range cases {
		result := toFloat64(tc.input)
		if result != tc.expected {
			t.Errorf("toFloat64(%v) = %f, want %f", tc.input, result, tc.expected)
		}
	}
}
