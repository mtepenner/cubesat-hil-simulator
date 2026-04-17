// Package comms - tests for COBS encoding/decoding and packet framing.
package comms

import (
	"bytes"
	"testing"
)

func TestCOBSEncodeEmpty(t *testing.T) {
	result := COBSEncode([]byte{})
	expected := []byte{0x01, 0x00}
	if !bytes.Equal(result, expected) {
		t.Errorf("COBSEncode(empty) = %v, want %v", result, expected)
	}
}

func TestCOBSEncodeNoZeros(t *testing.T) {
	input := []byte{0x01, 0x02, 0x03}
	encoded := COBSEncode(input)
	// Should not contain any 0x00 except the trailing delimiter
	for i, b := range encoded[:len(encoded)-1] {
		if b == 0x00 {
			t.Errorf("Unexpected zero at position %d in encoded data: %v", i, encoded)
		}
	}
	// Last byte should be 0x00
	if encoded[len(encoded)-1] != 0x00 {
		t.Errorf("Missing trailing delimiter: %v", encoded)
	}
}

func TestCOBSEncodeWithZeros(t *testing.T) {
	input := []byte{0x00, 0x01, 0x00}
	encoded := COBSEncode(input)
	// No zeros in encoded data except delimiter
	for i, b := range encoded[:len(encoded)-1] {
		if b == 0x00 {
			t.Errorf("Unexpected zero at position %d: %v", i, encoded)
		}
	}
}

func TestCOBSRoundTrip(t *testing.T) {
	testCases := [][]byte{
		{},
		{0x00},
		{0x01},
		{0x01, 0x02, 0x03},
		{0x00, 0x00, 0x00},
		{0x01, 0x00, 0x02, 0x00, 0x03},
		{0xAA, 0x55, 0x03, 0x01, 0x00, 0x02, 0x00},
	}

	for i, input := range testCases {
		encoded := COBSEncode(input)

		// Remove trailing delimiter for decode
		decoded, err := COBSDecode(encoded[:len(encoded)-1])
		if err != nil {
			t.Errorf("Case %d: COBSDecode error: %v", i, err)
			continue
		}

		if !bytes.Equal(decoded, input) {
			t.Errorf("Case %d: roundtrip failed\n  input:   %v\n  encoded: %v\n  decoded: %v",
				i, input, encoded, decoded)
		}
	}
}

func TestCOBSDecodeBadData(t *testing.T) {
	// Data containing a zero byte should error
	_, err := COBSDecode([]byte{0x03, 0x01, 0x00, 0x02})
	if err == nil {
		t.Error("Expected error for zero byte in COBS data, got nil")
	}
}

func TestBuildPacket(t *testing.T) {
	registers := map[string]uint16{
		"mag_x": 1024,
		"mag_y": 2048,
	}
	packet := BuildPacket(registers)

	// Check header
	if packet[0] != 0xAA || packet[1] != 0x55 {
		t.Errorf("Bad header: %02x %02x", packet[0], packet[1])
	}

	// Check register count
	if packet[2] != 2 {
		t.Errorf("Bad register count: %d", packet[2])
	}

	// Verify checksum
	var checksum byte
	for _, b := range packet[:len(packet)-1] {
		checksum ^= b
	}
	if checksum != packet[len(packet)-1] {
		t.Errorf("Checksum mismatch: computed %02x, got %02x", checksum, packet[len(packet)-1])
	}
}

func TestFloat32RoundTrip(t *testing.T) {
	values := []float32{0.0, 1.0, -1.0, 3.14159, 1e-6, 1e6}
	for _, v := range values {
		b := Float32ToBytes(v)
		result := BytesToFloat32(b)
		if result != v {
			t.Errorf("Float32 roundtrip failed: %f -> %v -> %f", v, b, result)
		}
	}
}
