"""Constants for the XGIMI integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "xgimi"
NAME: Final = "XGIMI Projector Remote"
VERSION: Final = "1.1.3"
MANUFACTURER: Final = "XGIMI"
DEVICE_MODEL: Final = "Projector"

CONF_WAKE_BACKEND: Final = "wake_backend"
CONF_WAKE_BUTTON: Final = "wake_button"
CONF_BLUETOOTH_ADAPTER: Final = "bluetooth_adapter"
CONF_ADVERTISEMENT_DURATION: Final = "advertisement_duration"
CONF_BLE_INCREMENT: Final = "ble_increment"
CONF_DEBUG_LOGGING: Final = "debug_logging"
CONF_ALIVE_PORT: Final = "alive_port"
CONF_SCAN_INTERVAL: Final = "scan_interval"
WAKE_BUTTON_DOMAINS: Final = ("button", "input_button")

WAKE_BACKEND_LOCAL: Final = "local"
WAKE_BACKEND_ESP32: Final = "esp32"
WAKE_BACKENDS: Final = (
    WAKE_BACKEND_LOCAL,
    WAKE_BACKEND_ESP32,
)

DEFAULT_WAKE_BACKEND: Final = WAKE_BACKEND_LOCAL
DEFAULT_ADVERTISEMENT_DURATION: Final = 4.0
DEFAULT_BLE_INCREMENT: Final = False
DEFAULT_DEBUG_LOGGING: Final = False
DEFAULT_ALIVE_PORT: Final = 554
MIN_SCAN_INTERVAL: Final = 5
DEFAULT_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 600
MIN_ADVERTISEMENT_DURATION: Final = 1.0
MAX_ADVERTISEMENT_DURATION: Final = 10.0

XGIMI_LOCAL_NAME: Final = "Bluetooth 4.0 RC"
XGIMI_SERVICE_UUID: Final = "00001812-0000-1000-8000-00805f9b34fb"
XGIMI_MANUFACTURER_ID: Final = 0x0046
XGIMI_APPEARANCE: Final = 961
MAX_MANUFACTURER_PAYLOAD_LENGTH: Final = 16

COMMAND_POWER_ON: Final = "poweron"
COMMAND_POWER_OFF: Final = "poweroff"

WAKE_RESULT_SUCCESS: Final = "success"

REPAIR_DBUS_UNAVAILABLE: Final = "dbus_unavailable"
REPAIR_BLUEZ_UNAVAILABLE: Final = "bluez_unavailable"
REPAIR_NO_LOCAL_ADAPTER: Final = "no_local_adapter"
REPAIR_CONFIGURED_ADAPTER_MISSING: Final = "configured_adapter_missing"
REPAIR_WAKE_BACKEND_FAILURE: Final = "wake_backend_failure"

REPAIR_KEYS: Final = (
    REPAIR_DBUS_UNAVAILABLE,
    REPAIR_BLUEZ_UNAVAILABLE,
    REPAIR_NO_LOCAL_ADAPTER,
    REPAIR_CONFIGURED_ADAPTER_MISSING,
    REPAIR_WAKE_BACKEND_FAILURE,
)
