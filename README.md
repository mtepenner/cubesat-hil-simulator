# 🛰️ CubeSat HIL Simulator

A comprehensive Hardware-in-the-Loop (HIL) simulation platform designed for CubeSat development and testing. This system bridges the gap between simulated orbital physics and physical flight hardware, allowing developers to test real C/C++ firmware against a high-fidelity Python environment model, all orchestrated through a low-latency Go daemon and visualized in a React dashboard.

## 📑 Table of Contents
- [Features](#-features)
- [Architecture](#-architecture)
- [Technologies Used](#-technologies-used)
- [Installation](#-installation)
- [Usage](#-usage)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Features
* **High-Fidelity Physics Engine:** A Python and FastAPI backend that calculates precise orbital positions using Skyfield (SGP4/TLEs), alongside environmental factors like eclipses, solar flux, and a geomagnetic dipole field model.
* **Low-Latency Hardware Bridge:** A Go daemon that seamlessly translates simulated state data into raw ADC register values, communicating with the physical USB/TTY ports via raw byte-level UART. 
* **Flight-Ready Firmware:** FreeRTOS-based C/C++ firmware featuring critical subsystems like Attitude Determination & Control (ADCS) and Electrical Power Systems (EPS). It interfaces with the Go bridge via simulated sensor drivers.
* **Interactive Mission Control:** A React and TypeScript dashboard equipped with a Three.js 3D render of the spacecraft. It actively compares the "Truth" state from the Python simulation against the "Believed" state reported by the physical telemetry.
* **Packet Integrity:** Implements framing logic (e.g., COBS encoding) to ensure absolute packet integrity over serial connections.

## 🏗️ Architecture
The simulator is divided into four highly specialized subsystems:
1. **Simulation Engine (Python):** The source of "Truth" running the simulation clock, rigid body dynamics, and environmental models.
2. **Hardware Bridge (Go):** The high-speed translator and I/O daemon that connects the Python environment to the physical hardware.
3. **Firmware (C/C++):** The actual flight computer code running on the physical microcontroller.
4. **Mission Control (React):** The frontend UI that syncs both the simulation and hardware data streams for real-time visualization.

## 🛠️ Technologies Used
* **Simulation:** Python, FastAPI, Skyfield, NumPy, SciPy
* **Bridge & Comms:** Go (Golang), WebSockets, UART, COBS encoding
* **Firmware:** C/C++, FreeRTOS, PlatformIO
* **Frontend UI:** React, TypeScript, Three.js
* **Deployment & CI/CD:** Docker, Docker Compose, GitHub Actions

## 💻 Installation

### Prerequisites
* Docker and Docker Compose installed.
* Go 1.21+ (for building the hardware bridge locally).
* PlatformIO installed (for compiling and flashing firmware).
* An ESP32 development board connected via USB (for HIL mode; mock mode works without hardware).

### Setup Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/mtepenner/cubesat-hil-simulator.git
   cd cubesat-hil-simulator
   ```
2. Flash the firmware to your microcontroller using the provided Makefile:
   ```bash
   make flash-firmware
   ```
3. Boot up the Python simulation, Go bridge, and React UI locally using Docker Compose:
   ```bash
   docker-compose up --build -d
   ```
4. Or run individual components locally:
   ```bash
   make sim          # Start the simulation engine on port 8000
   make bridge       # Start the Go bridge in mock mode
   make dashboard    # Start the React dashboard on port 3000
   make test         # Run all unit tests
   ```

## 🎮 Usage
Once the hardware is connected and the cluster is running:
1. Open your browser and navigate to the Mission Control dashboard (typically `http://localhost:3000`).
2. Use the **Spacecraft3D** component to watch the physical rotation of the satellite based entirely on the hardware's telemetry.
3. Compare the **Environment HUD** (the exact physics truth) directly against the **Hardware State** to verify that your firmware's ADCS logic is responding accurately to the simulated sensor inputs.
4. Utilize the API endpoints to start, pause, or step through the simulation loop.

## 🤝 Contributing
Contributions are highly encouraged! Please ensure any modifications to orbital models pass the automated physics unit tests. Firmware updates must compile successfully via the PlatformIO CLI in the GitHub Actions pipeline.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/NewSensorModel`)
3. Commit your Changes (`git commit -m 'Add sun sensor simulation'`)
4. Push to the Branch (`git push origin feature/NewSensorModel`)
5. Open a Pull Request

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.
