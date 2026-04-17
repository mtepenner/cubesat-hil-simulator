// Package comms provides serial communication with the flight hardware.
package comms

import (
	"fmt"
	"time"

	"go.bug.st/serial"
)

// SerialConnection wraps a serial port for UART communication.
type SerialConnection struct {
	port serial.Port
	path string
}

// NewSerialConnection opens a serial port at the given path and baud rate.
func NewSerialConnection(portPath string, baudRate int) (*SerialConnection, error) {
	mode := &serial.Mode{
		BaudRate: baudRate,
		DataBits: 8,
		Parity:   serial.NoParity,
		StopBits: serial.OneStopBit,
	}

	port, err := serial.Open(portPath, mode)
	if err != nil {
		return nil, fmt.Errorf("failed to open serial port %s: %w", portPath, err)
	}

	return &SerialConnection{
		port: port,
		path: portPath,
	}, nil
}

// Write sends raw bytes over the serial port.
func (sc *SerialConnection) Write(data []byte) error {
	n, err := sc.port.Write(data)
	if err != nil {
		return fmt.Errorf("serial write error: %w", err)
	}
	if n != len(data) {
		return fmt.Errorf("serial write incomplete: wrote %d of %d bytes", n, len(data))
	}
	return nil
}

// ReadPacket reads bytes from serial until a COBS frame delimiter (0x00) is found.
func (sc *SerialConnection) ReadPacket(timeout time.Duration) ([]byte, error) {
	if err := sc.port.SetReadTimeout(timeout); err != nil {
		return nil, fmt.Errorf("set read timeout: %w", err)
	}

	buf := make([]byte, 1)
	var packet []byte

	for {
		n, err := sc.port.Read(buf)
		if err != nil {
			return nil, fmt.Errorf("serial read error: %w", err)
		}
		if n == 0 {
			return nil, fmt.Errorf("serial read timeout")
		}

		if buf[0] == 0x00 {
			// Frame delimiter found
			return packet, nil
		}
		packet = append(packet, buf[0])

		// Safety limit
		if len(packet) > 4096 {
			return nil, fmt.Errorf("packet too large (>4096 bytes)")
		}
	}
}

// Close closes the serial port.
func (sc *SerialConnection) Close() error {
	if sc.port != nil {
		return sc.port.Close()
	}
	return nil
}

// ListPorts returns a list of available serial ports.
func ListPorts() ([]string, error) {
	ports, err := serial.GetPortsList()
	if err != nil {
		return nil, err
	}
	return ports, nil
}
