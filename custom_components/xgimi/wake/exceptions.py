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
        "The configured local Bluetooth adapter is missing. Select another "
        "advertising-capable adapter in the integration options."
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


class WakeButtonServiceError(WakeBackendError):
    """Home Assistant could not press the configured wake button."""

    error_code = "wake_button_service_failed"
    default_message = "Home Assistant could not press the configured wake button."
