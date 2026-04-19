// Package comms provides framing logic for serial communication.
// Implements Consistent Overhead Byte Stuffing (COBS) encoding to ensure
// packet integrity over UART connections.
package comms

import (
	"encoding/binary"
	"errors"
	"math"
)

// COBSEncode encodes data using Consistent Overhead Byte Stuffing.
// The encoded data will not contain any zero bytes, allowing 0x00 to be
// used as a packet delimiter. A trailing 0x00 delimiter is appended.
func COBSEncode(data []byte) []byte {
	if len(data) == 0 {
		return []byte{0x01, 0x00}
	}

	encoded := make([]byte, 0, len(data)+len(data)/254+2)

	// Process input in blocks separated by zero bytes
	idx := 0
	lastWasZero := false
	for idx < len(data) {
		// Find the next zero byte (or end of data)
		blockStart := idx
		blockEnd := idx
		for blockEnd < len(data) && data[blockEnd] != 0x00 && (blockEnd-blockStart) < 254 {
			blockEnd++
		}

		blockLen := blockEnd - blockStart

		if blockEnd < len(data) && data[blockEnd] == 0x00 {
			// Zero byte found; overhead byte = distance to next zero + 1
			encoded = append(encoded, byte(blockLen+1))
			encoded = append(encoded, data[blockStart:blockEnd]...)
			idx = blockEnd + 1
			lastWasZero = true
		} else if blockLen == 254 {
			// Block reached max length (254 non-zero bytes)
			encoded = append(encoded, 0xFF)
			encoded = append(encoded, data[blockStart:blockEnd]...)
			idx = blockEnd
			lastWasZero = false
		} else {
			// End of data
			encoded = append(encoded, byte(blockLen+1))
			encoded = append(encoded, data[blockStart:blockEnd]...)
			idx = blockEnd
			lastWasZero = false
		}
	}

	// If data ended with a zero, emit overhead byte for the empty trailing group
	if lastWasZero {
		encoded = append(encoded, 0x01)
	}

	// Append frame delimiter
	encoded = append(encoded, 0x00)
	return encoded
}

// COBSDecode decodes COBS-encoded data.
// The input should NOT include the trailing 0x00 delimiter.
func COBSDecode(encoded []byte) ([]byte, error) {
	if len(encoded) == 0 {
		return []byte{}, nil
	}

	decoded := make([]byte, 0, len(encoded))
	idx := 0

	for idx < len(encoded) {
		code := encoded[idx]
		idx++

		if code == 0x00 {
			return nil, errors.New("unexpected zero byte in COBS data")
		}

		blockLen := int(code) - 1
		if idx+blockLen > len(encoded) {
			return nil, errors.New("COBS decode error: unexpected end of data")
		}

		// Copy the non-zero data block
		decoded = append(decoded, encoded[idx:idx+blockLen]...)
		idx += blockLen

		// If code < 0xFF, append a zero (implicit zero in original data)
		// unless this is the last block
		if code < 0xFF && idx < len(encoded) {
			decoded = append(decoded, 0x00)
		}
	}

	return decoded, nil
}

// BuildPacket creates a binary packet from ADC register values.
// Format: [header(2)] [num_registers(1)] [register_data(2*N)] [checksum(1)]
func BuildPacket(registers map[string]uint16) []byte {
	// Sort keys for deterministic ordering
	keys := make([]string, 0, len(registers))
	for k := range registers {
		keys = append(keys, k)
	}

	numRegs := len(keys)
	// Header (0xAA 0x55) + count + data + checksum
	packet := make([]byte, 0, 3+numRegs*2+1)
	packet = append(packet, 0xAA, 0x55)
	packet = append(packet, byte(numRegs))

	for _, key := range keys {
		val := registers[key]
		buf := make([]byte, 2)
		binary.BigEndian.PutUint16(buf, val)
		packet = append(packet, buf...)
	}

	// Simple XOR checksum
	var checksum byte
	for _, b := range packet {
		checksum ^= b
	}
	packet = append(packet, checksum)

	return packet
}

// Float32ToBytes converts a float32 to a 4-byte big-endian representation.
func Float32ToBytes(f float32) []byte {
	bits := math.Float32bits(f)
	buf := make([]byte, 4)
	binary.BigEndian.PutUint32(buf, bits)
	return buf
}

// BytesToFloat32 converts 4 big-endian bytes to a float32.
func BytesToFloat32(b []byte) float32 {
	if len(b) < 4 {
		return 0.0
	}
	bits := binary.BigEndian.Uint32(b)
	return math.Float32frombits(bits)
}
