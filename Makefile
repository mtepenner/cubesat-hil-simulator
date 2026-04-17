.PHONY: help sim bridge dashboard test flash-firmware clean

SERIAL_PORT ?= /dev/ttyUSB0
BAUD_RATE ?= 115200

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Docker ---
up: ## Start all services with Docker Compose
	docker-compose up --build -d

down: ## Stop all services
	docker-compose down

logs: ## Tail logs from all services
	docker-compose logs -f

# --- Simulation Engine ---
sim: ## Run the simulation engine locally
	cd simulation_engine && uvicorn app.main:app --reload --port 8000

sim-test: ## Run physics unit tests
	cd simulation_engine && python -m pytest tests/ -v

# --- Hardware Bridge ---
bridge: ## Run the hardware bridge daemon locally
	cd hardware_bridge && go run ./cmd/daemon/ --mock

bridge-test: ## Run Go unit tests
	cd hardware_bridge && go test ./... -v

# --- Firmware ---
flash-firmware: ## Compile and flash firmware to MCU
	cd firmware && pio run --target upload --upload-port $(SERIAL_PORT)

build-firmware: ## Compile firmware without flashing
	cd firmware && pio run

monitor: ## Open serial monitor to the MCU
	cd firmware && pio device monitor --baud $(BAUD_RATE) --port $(SERIAL_PORT)

# --- Mission Control ---
dashboard: ## Run the React dashboard locally (dev mode)
	cd mission_control && npm run dev

dashboard-build: ## Build the React dashboard for production
	cd mission_control && npm run build

# --- Testing ---
test: sim-test bridge-test ## Run all tests
	@echo "All tests passed!"

# --- Cleanup ---
clean: ## Remove build artifacts
	cd firmware && pio run --target clean 2>/dev/null || true
	cd mission_control && rm -rf dist node_modules 2>/dev/null || true
	docker-compose down --rmi local 2>/dev/null || true
