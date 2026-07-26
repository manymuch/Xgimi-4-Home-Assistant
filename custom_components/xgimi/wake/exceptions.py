"""Wake backend exceptions."""

from __future__ import annotations


class WakeBackendError(Exception):
    """Base wake backend error."""

    error_code = "wake_backend_error"
    default_message = "The configured projector wake backend is unavailable."

    def __init__(self, message: str | None = None) -> None:
        """Initialize the error without including sensitive wake data."""
        super().__init__(message or self.default_message)


class WakeBackendClosedError(WakeBackendError):
    """The backend has been closed."""

    error_code = "wake_backend_closed"
    default_message = "The projector wake backend is shutting down."


class DBusUnavailableError(WakeBackendError):
    """System D-Bus is unavailable."""

    error_code = "dbus_unavailable"
    default_message = (
        "System D-Bus is unavailable. For Home Assistant Container, mount "
        "/run/dbus:/run/dbus:ro from the Docker host."
    )


class DBusConnectionLostError(WakeBackendError):
    """The system D-Bus connection was lost."""

    error_code = "dbus_connection_lost"
    default_message = "The system D-Bus connection was lost during BLE advertising."


class BlueZUnavailableError(WakeBackendError):
    """BlueZ is unavailable."""

    error_code = "bluez_unavailable"
    default_message = (
        "The host BlueZ service is unavailable. Make sure bluetoothd is running "
        "on the Home Assistant host."
    )


class NoLocalAdapterError(WakeBackendError):
    """No local Bluetooth adapter exists."""

    error_code = "no_local_adapter"
    default_message = (
        "No local Bluetooth adapter was found. Check Settings → Devices & "
        "services → Bluetooth."
    )


class ConfiguredAdapterMissingError(WakeBackendError):
    """The configured local adapter is missing."""

    error_code = "configured_adapter_missing"
    default_message = (
        "The configured local Bluetooth adapter is missing. Select Automatic "
        "or another advertising-capable adapter."
    )


class AdvertisingUnsupportedError(WakeBackendError):
    """The adapter cannot advertise."""

    error_code = "advertising_unsupported"
    default_message = (
        "No local Bluetooth adapter with BLE advertising support was found. "
        "Check Settings → Devices & services → Bluetooth."
    )


class NoAdvertisingInstanceError(WakeBackendError):
    """No advertising instance is available."""

    error_code = "no_advertising_instance"
    default_message = "The Bluetooth adapter has no free BLE advertising instances."


class InvalidAdvertisementDataError(WakeBackendError):
    """Advertisement data is invalid."""

    error_code = "invalid_advertisement_data"
    default_message = (
        "The XGIMI BLE token is invalid or too long for the advertisement."
    )


class AdvertisementRegistrationError(WakeBackendError):
    """BlueZ rejected the advertisement."""

    error_code = "advertisement_registration_failed"
    default_message = "BlueZ rejected the XGIMI BLE advertisement."


class InsufficientBluetoothPermissionsError(AdvertisementRegistrationError):
    """The process lacks permissions to advertise."""

    error_code = "insufficient_bluetooth_permissions"
    default_message = (
        "BlueZ denied BLE advertising. For Home Assistant Container, add "
        "NET_ADMIN and NET_RAW capabilities and use the host BlueZ service."
    )


class AdapterRemovedError(WakeBackendError):
    """The selected adapter was removed during advertising."""

    error_code = "adapter_removed"
    default_message = "The selected Bluetooth adapter was removed during advertising."


class ESP32WakeEntityMissingError(WakeBackendError):
    """The configured ESP32 wake entity is missing."""

    error_code = "esp32_entity_missing"
    default_message = (
        "The selected ESPHome wake button is missing. Check the ESP32 device "
        "and the integration options."
    )


class ESP32WakeEntityUnavailableError(WakeBackendError):
    """The configured ESP32 wake entity is unavailable."""

    error_code = "esp32_entity_unavailable"
    default_message = (
        "The selected ESPHome wake button is unavailable. Check the ESP32 "
        "device, Wi-Fi connection, and ESPHome integration."
    )


class ESP32WakeEntityDomainError(WakeBackendError):
    """The configured entity is not a supported domain."""

    error_code = "esp32_entity_unsupported_domain"
    default_message = "The ESP32 wake entity must be a button entity."


class ESP32WakeServiceError(WakeBackendError):
    """Home Assistant could not press the ESP32 wake button."""

    error_code = "esp32_service_call_failed"
    default_message = "Home Assistant could not press the ESPHome wake button."


class NoWakeBackendAvailableError(WakeBackendError):
    """Neither local nor ESP32 wake is available."""

    error_code = "no_wake_backend_available"
    default_message = (
        "No wake backend is available. Configure an ESPHome wake button or "
        "connect a local Bluetooth adapter that supports BLE advertising."
    )

    def __init__(self, cause: WakeBackendError | None = None) -> None:
        """Initialize the error and retain a safe underlying cause."""
        super().__init__()
        self.cause = cause
