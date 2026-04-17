// Package main is the entry point for the CubeSat HIL Hardware Bridge daemon.
// It connects to the Python simulation engine via WebSocket and to the
// physical flight hardware via UART serial port.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
	"github.com/mtepenner/cubesat-hil-simulator/hardware_bridge/internal/comms"
	"github.com/mtepenner/cubesat-hil-simulator/hardware_bridge/internal/translator"
)

// SimState represents the simulation state received from the Python engine.
type SimState struct {
	SimTime     float64                `json:"sim_time"`
	Orbit       map[string]interface{} `json:"orbit"`
	Environment map[string]interface{} `json:"environment"`
	Dynamics    map[string]interface{} `json:"dynamics"`
}

func main() {
	wsURL := flag.String("ws", getEnv("SIM_WS_URL", "ws://localhost:8000/api/sim/ws"), "Simulation WebSocket URL")
	serialPort := flag.String("serial", getEnv("SERIAL_PORT", ""), "Serial port path (e.g., /dev/ttyUSB0, COM3)")
	baudRate := flag.Int("baud", 115200, "Serial baud rate")
	mockMode := flag.Bool("mock", false, "Run in mock mode without hardware")
	flag.Parse()

	log.Println("CubeSat HIL Hardware Bridge starting...")
	log.Printf("  WebSocket URL: %s", *wsURL)
	log.Printf("  Serial Port:   %s", *serialPort)
	log.Printf("  Mock Mode:     %v", *mockMode)

	// Set up signal handling for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Connect to simulation engine WebSocket
	log.Println("Connecting to simulation engine...")
	wsConn, _, err := websocket.DefaultDialer.Dial(*wsURL, nil)
	if err != nil {
		log.Printf("Warning: Could not connect to simulation engine: %v", err)
		log.Println("Running in offline mode. Will retry connection...")
		runOfflineLoop(sigChan)
		return
	}
	defer wsConn.Close()
	log.Println("Connected to simulation engine.")

	// Open serial port (or use mock)
	var serialConn *comms.SerialConnection
	if !*mockMode && *serialPort != "" {
		log.Printf("Opening serial port %s at %d baud...", *serialPort, *baudRate)
		serialConn, err = comms.NewSerialConnection(*serialPort, *baudRate)
		if err != nil {
			log.Fatalf("Failed to open serial port: %v", err)
		}
		defer serialConn.Close()
		log.Println("Serial port opened.")
	} else {
		log.Println("Running without hardware (mock mode).")
	}

	mapper := translator.NewStateMapper()

	// Main bridge loop
	log.Println("Bridge loop started.")
	for {
		select {
		case sig := <-sigChan:
			log.Printf("Received signal %v, shutting down...", sig)
			return
		default:
		}

		// Read simulation state from WebSocket
		_, message, err := wsConn.ReadMessage()
		if err != nil {
			log.Printf("WebSocket read error: %v", err)
			break
		}

		var simState SimState
		if err := json.Unmarshal(message, &simState); err != nil {
			log.Printf("JSON unmarshal error: %v", err)
			continue
		}

		// Translate simulation state to hardware register values
		registers := mapper.MapToRegisters(simState.Environment)

		// COBS-encode and send to hardware
		packet := comms.BuildPacket(registers)
		encoded := comms.COBSEncode(packet)

		if serialConn != nil {
			if err := serialConn.Write(encoded); err != nil {
				log.Printf("Serial write error: %v", err)
				continue
			}

			// Read telemetry response from hardware
			response, err := serialConn.ReadPacket(time.Second)
			if err != nil {
				log.Printf("Serial read error: %v", err)
				continue
			}

			decoded, err := comms.COBSDecode(response)
			if err != nil {
				log.Printf("COBS decode error: %v", err)
				continue
			}

			// Forward telemetry back to simulation via WebSocket
			telemetry := mapper.ParseTelemetry(decoded)
			telJSON, _ := json.Marshal(telemetry)
			if err := wsConn.WriteMessage(websocket.TextMessage, telJSON); err != nil {
				log.Printf("WebSocket write error: %v", err)
				break
			}
		} else {
			// Mock mode: generate synthetic telemetry
			mockTelemetry := mapper.GenerateMockTelemetry(simState.Environment)
			telJSON, _ := json.Marshal(mockTelemetry)
			if err := wsConn.WriteMessage(websocket.TextMessage, telJSON); err != nil {
				log.Printf("WebSocket write error: %v", err)
				break
			}
		}
	}
}

func runOfflineLoop(sigChan chan os.Signal) {
	log.Println("Running in offline mode. Press Ctrl+C to exit.")
	<-sigChan
	log.Println("Shutting down.")
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}

func init() {
	// Suppress unused import warning for fmt
	_ = fmt.Sprintf
}
