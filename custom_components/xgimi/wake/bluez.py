"""Local BlueZ BLE advertising wake backend."""

# This module intentionally does not enable postponed annotations. dbus-fast
# uses string return annotations such as "s" and "a{qv}" as D-Bus signatures.

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Protocol, Self, cast
from uuid import uuid4

from dbus_fast import Message, Variant
from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType, MessageType, PropertyAccess
from dbus_fast.errors import DBusError
from dbus_fast.service import ServiceInterface, dbus_property, method

from ..const import (
    BLUETOOTH_ADAPTER_AUTO,
    MAX_MANUFACTURER_PAYLOAD_LENGTH,
    WAKE_BACKEND_LOCAL,
    XGIMI_APPEARANCE,
    XGIMI_LOCAL_NAME,
    XGIMI_MANUFACTURER_ID,
    XGIMI_SERVICE_UUID,
)
from .exceptions import (
    AdapterRemovedError,
    AdvertisementRegistrationError,
    AdvertisingUnsupportedError,
    BlueZUnavailableError,
    ConfiguredAdapterMissingError,
    DBusConnectionLostError,
    DBusUnavailableError,
    InsufficientBluetoothPermissionsError,
    InvalidAdvertisementDataError,
    NoAdvertisingInstanceError,
    NoLocalAdapterError,
    WakeBackendClosedError,
    WakeBackendError,
)

_LOGGER = logging.getLogger(__name__)

BLUEZ_SERVICE = "org.bluez"
BLUEZ_ROOT_PATH = "/"
OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"
ADAPTER_INTERFACE = "org.bluez.Adapter1"
ADVERTISING_MANAGER_INTERFACE = "org.bluez.LEAdvertisingManager1"
ADVERTISEMENT_INTERFACE = "org.bluez.LEAdvertisement1"

DBUS_ERROR_SERVICE_UNKNOWN = "org.freedesktop.DBus.Error.ServiceUnknown"
DBUS_ERROR_NAME_HAS_NO_OWNER = "org.freedesktop.DBus.Error.NameHasNoOwner"
DBUS_ERROR_NO_REPLY = "org.freedesktop.DBus.Error.NoReply"

BLUEZ_ERROR_INVALID_ARGUMENTS = "org.bluez.Error.InvalidArguments"
BLUEZ_ERROR_ALREADY_EXISTS = "org.bluez.Error.AlreadyExists"
BLUEZ_ERROR_INVALID_LENGTH = "org.bluez.Error.InvalidLength"
BLUEZ_ERROR_NOT_PERMITTED = "org.bluez.Error.NotPermitted"
BLUEZ_ERROR_DOES_NOT_EXIST = "org.bluez.Error.DoesNotExist"


class _MessageBusLike(Protocol):
    """Subset of the dbus-fast MessageBus used by the backend."""

    connected: bool

    async def connect(self) -> Self:
        """Connect to D-Bus."""

    async def call(self, message: Message) -> Message | None:
        """Call a D-Bus method."""

    def export(self, path: str, interface: ServiceInterface) -> None:
        """Export a service interface."""

    def unexport(
        self, path: str, interface: ServiceInterface | str | None = None
    ) -> None:
        """Unexport a service interface."""

    def disconnect(self) -> None:
        """Disconnect from D-Bus."""

    async def wait_for_disconnect(self) -> None:
        """Wait until the bus disconnects."""


BusFactory = Callable[[], _MessageBusLike]


@dataclass(frozen=True, slots=True)
class BlueZAdapter:
    """A local BlueZ adapter capable of BLE advertising."""

    path: str
    name: str
    address: str | None
    supported_instances: int | None
    active_instances: int | None

    @property
    def has_free_instance(self) -> bool:
        """Return whether the adapter has an advertising slot available."""
        if self.supported_instances is None:
            return True
        active = self.active_instances or 0
        return self.supported_instances > active

    @property
    def display_name(self) -> str:
        """Return a user-facing adapter label."""
        details = f" ({self.address})" if self.address else ""
        return f"{self.name}{details} — {self.path}"


class _DBusCallError(Exception):
    """Internal sanitized D-Bus method-call error."""

    def __init__(self, error_name: str) -> None:
        super().__init__(error_name)
        self.error_name = error_name


class XgimiAdvertisement(ServiceInterface):
    """Exported org.bluez.LEAdvertisement1 object."""

    def __init__(self, manufacturer_payload: bytes, released: asyncio.Event) -> None:
        """Initialize the XGIMI BLE advertisement."""
        super().__init__(ADVERTISEMENT_INTERFACE)
        self._manufacturer_payload = manufacturer_payload
        self._released = released

    @dbus_property(access=PropertyAccess.READ, name="Type")
    def advertisement_type(self) -> "s":  # noqa: F821
        """Return the BlueZ advertisement type."""
        return "peripheral"

    @dbus_property(access=PropertyAccess.READ, name="LocalName")
    def local_name(self) -> "s":  # noqa: F821
        """Return the advertised local name."""
        return XGIMI_LOCAL_NAME

    @dbus_property(access=PropertyAccess.READ, name="ServiceUUIDs")
    def service_uuids(self) -> "as":  # noqa: F722
        """Return advertised service UUIDs."""
        return [XGIMI_SERVICE_UUID]

    @dbus_property(access=PropertyAccess.READ, name="ManufacturerData")
    def manufacturer_data(self) -> "a{qv}":  # noqa: F722
        """Return manufacturer identifier and payload separately."""
        return {XGIMI_MANUFACTURER_ID: Variant("ay", self._manufacturer_payload)}

    @dbus_property(access=PropertyAccess.READ, name="Appearance")
    def appearance(self) -> "q":  # noqa: F821
        """Return the Bluetooth appearance."""
        return XGIMI_APPEARANCE

    @method(name="Release")
    def release(self) -> None:
        """Handle BlueZ releasing the advertisement."""
        self._released.set()


def _default_bus_factory() -> _MessageBusLike:
    """Create a system D-Bus connection."""
    return cast(_MessageBusLike, MessageBus(bus_type=BusType.SYSTEM))


def _variant_value(value: Any) -> Any:
    """Unwrap a D-Bus Variant."""
    return value.value if isinstance(value, Variant) else value


def _optional_int(properties: dict[str, Any], key: str) -> int | None:
    """Read an optional integer D-Bus property."""
    value = properties.get(key)
    if value is None:
        return None
    unwrapped = _variant_value(value)
    return int(unwrapped) if isinstance(unwrapped, int | float) else None


def _optional_str(properties: dict[str, Any], key: str) -> str | None:
    """Read an optional string D-Bus property."""
    value = properties.get(key)
    if value is None:
        return None
    unwrapped = _variant_value(value)
    return unwrapped if isinstance(unwrapped, str) else None


async def _async_connect_system_bus(bus_factory: BusFactory) -> _MessageBusLike:
    """Connect to system D-Bus and translate transport errors."""
    bus: _MessageBusLike | None = None
    try:
        bus = bus_factory()
        return await bus.connect()
    except asyncio.CancelledError:
        if bus is not None:
            with suppress(Exception):
                bus.disconnect()
        raise
    except (OSError, DBusError, RuntimeError) as err:
        if bus is not None:
            with suppress(Exception):
                bus.disconnect()
        raise DBusUnavailableError from err
    except Exception as err:
        if bus is not None:
            with suppress(Exception):
                bus.disconnect()
        raise DBusUnavailableError from err


async def _async_call(
    bus: _MessageBusLike,
    message: Message,
) -> Message:
    """Perform a low-level D-Bus call without retaining an error body."""
    try:
        reply = await bus.call(message)
    except (OSError, EOFError, BrokenPipeError, DBusError) as err:
        raise DBusConnectionLostError from err
    except Exception as err:
        raise DBusConnectionLostError from err

    if reply is None:
        raise DBusConnectionLostError
    if reply.message_type == MessageType.ERROR:
        raise _DBusCallError(reply.error_name or "unknown")
    return reply


async def _async_get_managed_objects(
    bus: _MessageBusLike,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Query BlueZ through org.freedesktop.DBus.ObjectManager."""
    try:
        reply = await _async_call(
            bus,
            Message(
                destination=BLUEZ_SERVICE,
                path=BLUEZ_ROOT_PATH,
                interface=OBJECT_MANAGER_INTERFACE,
                member="GetManagedObjects",
            ),
        )
    except _DBusCallError as err:
        if err.error_name in (
            DBUS_ERROR_SERVICE_UNKNOWN,
            DBUS_ERROR_NAME_HAS_NO_OWNER,
        ):
            raise BlueZUnavailableError from err
        if err.error_name == DBUS_ERROR_NO_REPLY:
            raise DBusConnectionLostError from err
        raise BlueZUnavailableError from err

    if not reply.body or not isinstance(reply.body[0], dict):
        raise BlueZUnavailableError
    return cast(dict[str, dict[str, dict[str, Any]]], reply.body[0])


def _all_adapters(
    managed_objects: dict[str, dict[str, dict[str, Any]]],
) -> list[BlueZAdapter]:
    """Return adapters that expose LEAdvertisingManager1."""
    adapters: list[BlueZAdapter] = []
    for path in sorted(managed_objects):
        interfaces = managed_objects[path]
        manager_properties = interfaces.get(ADVERTISING_MANAGER_INTERFACE)
        if manager_properties is None or ADAPTER_INTERFACE not in interfaces:
            continue
        adapter_properties = interfaces[ADAPTER_INTERFACE]
        name = (
            _optional_str(adapter_properties, "Alias")
            or _optional_str(adapter_properties, "Name")
            or path.rsplit("/", 1)[-1]
        )
        adapters.append(
            BlueZAdapter(
                path=path,
                name=name,
                address=_optional_str(adapter_properties, "Address"),
                supported_instances=_optional_int(
                    manager_properties, "SupportedInstances"
                ),
                active_instances=_optional_int(manager_properties, "ActiveInstances"),
            )
        )
    return adapters


def _select_adapter(
    managed_objects: dict[str, dict[str, dict[str, Any]]],
    requested_path: str,
) -> BlueZAdapter:
    """Select an advertising-capable adapter."""
    local_adapter_paths = {
        path
        for path, interfaces in managed_objects.items()
        if ADAPTER_INTERFACE in interfaces
    }
    capable_adapters = _all_adapters(managed_objects)

    if requested_path != BLUETOOTH_ADAPTER_AUTO:
        matching = next(
            (adapter for adapter in capable_adapters if adapter.path == requested_path),
            None,
        )
        if matching is not None:
            if not matching.has_free_instance:
                raise NoAdvertisingInstanceError
            return matching
        if requested_path in local_adapter_paths:
            raise AdvertisingUnsupportedError
        raise ConfiguredAdapterMissingError

    if not local_adapter_paths and not capable_adapters:
        raise NoLocalAdapterError
    if not capable_adapters:
        raise AdvertisingUnsupportedError

    for adapter in capable_adapters:
        if adapter.has_free_instance:
            return adapter
    raise NoAdvertisingInstanceError


async def async_discover_bluez_adapters(
    bus_factory: BusFactory = _default_bus_factory,
) -> list[BlueZAdapter]:
    """Return all local adapters exposing LEAdvertisingManager1."""
    bus = await _async_connect_system_bus(bus_factory)
    try:
        return _all_adapters(await _async_get_managed_objects(bus))
    finally:
        bus.disconnect()


class BlueZWakeBackend:
    """Wake a projector using a local BlueZ advertising adapter."""

    backend_type = WAKE_BACKEND_LOCAL

    def __init__(
        self,
        token: str,
        *,
        adapter_path: str = BLUETOOTH_ADAPTER_AUTO,
        duration: float = 4.0,
        bus_factory: BusFactory = _default_bus_factory,
    ) -> None:
        """Initialize the BlueZ backend."""
        self._token = token
        self.adapter_path = adapter_path
        self.duration = duration
        self._bus_factory = bus_factory
        self._lock = asyncio.Lock()
        self._close_event = asyncio.Event()
        self._closed = False
        self._bus: _MessageBusLike | None = None
        self._advertisement: XgimiAdvertisement | None = None
        self._advertisement_path: str | None = None
        self._registered = False

        self._dbus_available = False
        self._bluez_available = False
        self._selected_adapter: BlueZAdapter | None = None
        self._advertising_supported = False

    def _manufacturer_payload(self) -> bytes:
        """Decode and validate the token without exposing it."""
        try:
            payload = bytes.fromhex(self._token)
        except (TypeError, ValueError) as err:
            raise InvalidAdvertisementDataError from err
        if not payload or len(payload) > MAX_MANUFACTURER_PAYLOAD_LENGTH:
            raise InvalidAdvertisementDataError
        return payload

    async def _async_connect_and_select(
        self,
    ) -> tuple[_MessageBusLike, BlueZAdapter]:
        """Connect to BlueZ and select an adapter."""
        self._dbus_available = False
        self._bluez_available = False
        self._selected_adapter = None
        self._advertising_supported = False

        bus = await _async_connect_system_bus(self._bus_factory)
        self._dbus_available = True
        try:
            managed_objects = await _async_get_managed_objects(bus)
            self._bluez_available = True
            capable_adapters = _all_adapters(managed_objects)
            self._advertising_supported = bool(capable_adapters)
            if capable_adapters:
                if self.adapter_path == BLUETOOTH_ADAPTER_AUTO:
                    self._selected_adapter = capable_adapters[0]
                else:
                    self._selected_adapter = next(
                        (
                            adapter
                            for adapter in capable_adapters
                            if adapter.path == self.adapter_path
                        ),
                        None,
                    )
            adapter = _select_adapter(managed_objects, self.adapter_path)
        except BaseException:
            with suppress(Exception):
                bus.disconnect()
            raise

        self._selected_adapter = adapter
        return bus, adapter

    async def async_probe(self) -> None:
        """Verify local BlueZ advertising capability."""
        if self._closed:
            raise WakeBackendClosedError
        self._manufacturer_payload()
        bus, _ = await self._async_connect_and_select()
        bus.disconnect()

    async def _async_register(
        self,
        bus: _MessageBusLike,
        adapter: BlueZAdapter,
        advertisement_path: str,
    ) -> None:
        """Register the exported advertisement."""
        try:
            await _async_call(
                bus,
                Message(
                    destination=BLUEZ_SERVICE,
                    path=adapter.path,
                    interface=ADVERTISING_MANAGER_INTERFACE,
                    member="RegisterAdvertisement",
                    signature="oa{sv}",
                    body=[advertisement_path, {}],
                ),
            )
        except _DBusCallError as err:
            if err.error_name in (
                BLUEZ_ERROR_INVALID_ARGUMENTS,
                BLUEZ_ERROR_INVALID_LENGTH,
            ):
                raise InvalidAdvertisementDataError from err
            if err.error_name == BLUEZ_ERROR_NOT_PERMITTED:
                raise InsufficientBluetoothPermissionsError from err
            if err.error_name == BLUEZ_ERROR_DOES_NOT_EXIST:
                raise AdapterRemovedError from err
            if err.error_name == BLUEZ_ERROR_ALREADY_EXISTS:
                raise AdvertisementRegistrationError from err
            raise AdvertisementRegistrationError from err

    async def _async_wait_while_advertising(
        self,
        bus: _MessageBusLike,
        released: asyncio.Event,
    ) -> None:
        """Wait for the duration, shutdown, adapter release, or bus loss."""
        duration_task = asyncio.create_task(asyncio.sleep(self.duration))
        close_task = asyncio.create_task(self._close_event.wait())
        release_task = asyncio.create_task(released.wait())
        disconnect_task: asyncio.Task[Any] | None = None
        if hasattr(bus, "wait_for_disconnect"):
            disconnect_task = asyncio.create_task(bus.wait_for_disconnect())

        tasks = {duration_task, close_task, release_task}
        if disconnect_task is not None:
            tasks.add(disconnect_task)
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            if duration_task in done:
                return
            if close_task in done:
                raise WakeBackendClosedError
            if release_task in done:
                raise AdapterRemovedError
            if disconnect_task is not None and disconnect_task in done:
                with suppress(Exception):
                    disconnect_task.result()
                self._dbus_available = False
                raise DBusConnectionLostError
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _async_cleanup(
        self,
        bus: _MessageBusLike,
        adapter_path: str,
        advertisement_path: str,
        advertisement: XgimiAdvertisement,
        registered: bool,
    ) -> None:
        """Unregister, unexport, and disconnect without hiding the main error."""
        if registered and bus.connected:
            try:
                await _async_call(
                    bus,
                    Message(
                        destination=BLUEZ_SERVICE,
                        path=adapter_path,
                        interface=ADVERTISING_MANAGER_INTERFACE,
                        member="UnregisterAdvertisement",
                        signature="o",
                        body=[advertisement_path],
                    ),
                )
            except Exception as err:
                _LOGGER.debug(
                    "Could not unregister XGIMI BLE advertisement: %s",
                    getattr(err, "error_name", type(err).__name__),
                )
        try:
            bus.unexport(advertisement_path, advertisement)
        except Exception as err:
            _LOGGER.debug(
                "Could not unexport XGIMI BLE advertisement: %s",
                type(err).__name__,
            )
        bus.disconnect()

    async def async_wake(self) -> None:
        """Advertise the XGIMI wake packet for the configured duration."""
        async with self._lock:
            if self._closed:
                raise WakeBackendClosedError

            payload = self._manufacturer_payload()
            bus, adapter = await self._async_connect_and_select()
            released = asyncio.Event()
            advertisement = XgimiAdvertisement(payload, released)
            advertisement_path = f"/org/homeassistant/xgimi/advertisement_{uuid4().hex}"
            registered = False
            self._bus = bus
            self._advertisement = advertisement
            self._advertisement_path = advertisement_path
            try:
                bus.export(advertisement_path, advertisement)
                await self._async_register(bus, adapter, advertisement_path)
                registered = True
                self._registered = True
                await self._async_wait_while_advertising(bus, released)

                if not bus.connected:
                    raise DBusConnectionLostError
                managed_objects = await _async_get_managed_objects(bus)
                if (
                    adapter.path not in managed_objects
                    or ADVERTISING_MANAGER_INTERFACE
                    not in managed_objects[adapter.path]
                ):
                    self._advertising_supported = False
                    raise AdapterRemovedError
            except DBusConnectionLostError:
                self._dbus_available = False
                raise
            except BlueZUnavailableError:
                self._bluez_available = False
                raise
            except WakeBackendError:
                raise
            except _DBusCallError as err:
                if err.error_name == BLUEZ_ERROR_DOES_NOT_EXIST:
                    raise AdapterRemovedError from err
                raise AdvertisementRegistrationError from err
            except asyncio.CancelledError:
                raise
            except Exception as err:
                raise AdvertisementRegistrationError from err
            finally:
                await self._async_cleanup(
                    bus,
                    adapter.path,
                    advertisement_path,
                    advertisement,
                    registered,
                )
                self._bus = None
                self._advertisement = None
                self._advertisement_path = None
                self._registered = False

    async def async_close(self) -> None:
        """Stop any active advertisement and close the backend."""
        if self._closed:
            return
        self._closed = True
        self._close_event.set()
        async with self._lock:
            # The wake operation performs cleanup before releasing this lock.
            return

    def diagnostics(self) -> dict[str, Any]:
        """Return cached, non-sensitive BlueZ diagnostics."""
        adapter = self._selected_adapter
        return {
            "dbus_available": self._dbus_available,
            "bluez_available": self._bluez_available,
            "selected_adapter": adapter.path if adapter else None,
            "advertising_supported": self._advertising_supported,
            "supported_instances": (
                adapter.supported_instances if adapter is not None else None
            ),
            "active_instances": (
                adapter.active_instances if adapter is not None else None
            ),
        }
