/**
 * CubeSat HIL Firmware - Main Entry Point
 *
 * FreeRTOS-based firmware for the CubeSat flight computer.
 * Runs three main tasks:
 *   1. ADCS Task  - Attitude Determination & Control
 *   2. EPS Task   - Electrical Power System monitoring
 *   3. Telemetry Task - Packages and transmits system state
 *
 * In HIL mode, sensor data comes from the Go hardware bridge
 * via UART instead of physical I2C/SPI sensors.
 */

#include <Arduino.h>
#include "systems/adcs.h"
#include "systems/eps.h"
#include "systems/telemetry.h"
#include "drivers/simulated_sensors.h"

// FreeRTOS task handles
TaskHandle_t adcsTaskHandle = NULL;
TaskHandle_t epsTaskHandle = NULL;
TaskHandle_t telemetryTaskHandle = NULL;

// Task stack sizes (words)
#define ADCS_STACK_SIZE      4096
#define EPS_STACK_SIZE       2048
#define TELEMETRY_STACK_SIZE 4096

// Task priorities (higher = more important)
#define ADCS_PRIORITY      3
#define EPS_PRIORITY       2
#define TELEMETRY_PRIORITY 1

// Shared state protected by mutex
SemaphoreHandle_t stateMutex;
ADCSState adcsState;
EPSState epsState;

/**
 * ADCS Task: Reads sensor data, runs control law, outputs actuator commands.
 * Runs at 10 Hz (100ms period).
 */
void adcsTask(void* parameter) {
    TickType_t lastWakeTime = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(100);

    adcs_init(&adcsState);

    for (;;) {
        // Read simulated sensors from the Go bridge
        SensorData sensors;
        simulated_sensors_read(&sensors);

        // Run ADCS algorithm
        if (xSemaphoreTake(stateMutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            adcs_update(&adcsState, &sensors);
            xSemaphoreGive(stateMutex);
        }

        vTaskDelayUntil(&lastWakeTime, period);
    }
}

/**
 * EPS Task: Monitors battery state, manages power modes.
 * Runs at 1 Hz (1000ms period).
 */
void epsTask(void* parameter) {
    TickType_t lastWakeTime = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(1000);

    eps_init(&epsState);

    for (;;) {
        SensorData sensors;
        simulated_sensors_read(&sensors);

        if (xSemaphoreTake(stateMutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            eps_update(&epsState, &sensors);
            xSemaphoreGive(stateMutex);
        }

        vTaskDelayUntil(&lastWakeTime, period);
    }
}

/**
 * Telemetry Task: Packages system state and sends to the Go bridge.
 * Runs at 2 Hz (500ms period).
 */
void telemetryTask(void* parameter) {
    TickType_t lastWakeTime = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(500);

    telemetry_init();

    for (;;) {
        if (xSemaphoreTake(stateMutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            telemetry_send(&adcsState, &epsState);
            xSemaphoreGive(stateMutex);
        }

        vTaskDelayUntil(&lastWakeTime, period);
    }
}

void setup() {
    Serial.begin(115200);
    Serial.println("CubeSat HIL Firmware v1.0 starting...");

    // Initialize the HIL serial connection (UART2 for hardware bridge)
    simulated_sensors_init();

    // Create mutex for shared state
    stateMutex = xSemaphoreCreateMutex();
    if (stateMutex == NULL) {
        Serial.println("ERROR: Failed to create state mutex!");
        while (1) { delay(1000); }
    }

    // Create FreeRTOS tasks
    xTaskCreatePinnedToCore(adcsTask, "ADCS", ADCS_STACK_SIZE,
                            NULL, ADCS_PRIORITY, &adcsTaskHandle, 1);
    xTaskCreatePinnedToCore(epsTask, "EPS", EPS_STACK_SIZE,
                            NULL, EPS_PRIORITY, &epsTaskHandle, 1);
    xTaskCreatePinnedToCore(telemetryTask, "TLM", TELEMETRY_STACK_SIZE,
                            NULL, TELEMETRY_PRIORITY, &telemetryTaskHandle, 0);

    Serial.println("All tasks started. HIL loop active.");
}

void loop() {
    // Main loop is idle — FreeRTOS tasks handle everything
    vTaskDelay(pdMS_TO_TICKS(1000));
}
