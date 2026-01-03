import asyncudp
import asyncio
from bluez_peripheral.util import get_message_bus
from bluez_peripheral.advert import Advertisement
from time import time
import logging

_LOGGER = logging.getLogger(__name__)


class XgimiApi:
    def __init__(self, ip, command_port, advance_port, alive_port, manufacturer_data, mac_address="", hass=None) -> None:
        self.ip = ip
        self.command_port = command_port  # 16735
        self.advance_port = advance_port  # 16750
        self.alive_port = alive_port  # 554
        self.manufacturer_data = manufacturer_data
        self.mac_address = mac_address.upper() if mac_address else ""
        self.hass = hass
        self._is_on = False
        self.last_on = time()
        self.last_off = time()
        self._bluetooth_callback = None

        # Register for Bluetooth advertisements if MAC address is provided and hass is available
        if self.mac_address and self.hass:
            self._register_bluetooth_callback()

        self._command_dict = {
            "ok": "KEYPRESSES:49",
            "play": "KEYPRESSES:49",
            "pause": "KEYPRESSES:49",
            "power": "KEYPRESSES:116",
            "back": "KEYPRESSES:48",
            "home": "KEYPRESSES:35",
            "menu": "KEYPRESSES:139",
            "right": "KEYPRESSES:37",
            "left": "KEYPRESSES:50",
            "up": "KEYPRESSES:36",
            "down": "KEYPRESSES:38",
            "volumedown": "KEYPRESSES:114",
            "volumeup": "KEYPRESSES:115",
            "poweroff": "KEYPRESSES:30",
            "volumemute": "KEYPRESSES:113",
            "autofocus": "KEYPRESSES:2099",
            "autofocus_new": "KEYPRESSES:2103",
            "manual_focus_left": "KEYPRESSES:2097",
            "manual_focus_right": "KEYPRESSES:2098",
            "motor_left_overstep": "KEYPRESSES:2095",
            "motor_left_start": "KEYPRESSES:2092",
            "motor_right_overstep": "KEYPRESSES:2096",
            "motor_right_start": "KEYPRESSES:2093",
            "motor_stop": "KEYPRESSES:2101",
            "shortcut_setting": "KEYPRESSES:2094",
            "choose_source": "KEYPRESSES:2102",
            "hibernate": "KEYPRESSES:2106",
            "xmusic": "KEYPRESSES:2108",
        }
        self._advance_command = str({"action": 20000, "controlCmd": {"data": "command_holder",
                                    "delayTime": 0, "mode": 5, "time": 0, "type": 0}, "msgid": "2"})

    def _register_bluetooth_callback(self):
        """Register callback for Bluetooth advertisements."""
        try:
            from homeassistant.components.bluetooth import async_register_callback
            from homeassistant.components.bluetooth.match import BluetoothCallbackMatcher

            def _bluetooth_callback(service_info, _change):
                """Handle Bluetooth advertisement.
                
                Args:
                    service_info: Bluetooth service information
                    _change: Bluetooth change type (unused but required by callback signature)
                """
                # Check if this is our remote
                if service_info.address.upper() != self.mac_address:
                    return

                # Check for manufacturer data with ID 70 (0x0046)
                if service_info.manufacturer_data and 70 in service_info.manufacturer_data:
                    new_token = service_info.manufacturer_data[70].hex()
                    # Normalize both tokens to lowercase for comparison
                    if new_token.lower() != self.manufacturer_data.lower():
                        _LOGGER.info(
                            "Detected BLE token rotation for %s. Updating token from %s to %s",
                            self.mac_address,
                            self.manufacturer_data,
                            new_token
                        )
                        self.manufacturer_data = new_token

            # Register the callback (async_register_callback is safe to call from sync context)
            self._bluetooth_callback = async_register_callback(
                self.hass,
                _bluetooth_callback,
                BluetoothCallbackMatcher(address=self.mac_address),
                None,
            )
            _LOGGER.info("Registered Bluetooth callback for MAC address: %s", self.mac_address)
        except ImportError:
            _LOGGER.warning("Bluetooth integration not available. Token rotation monitoring disabled.")
        except Exception as e:
            _LOGGER.error("Failed to register Bluetooth callback: %s", e)

    @property
    def is_on(self) -> bool:
        """Return true if the device is on."""
        return self._is_on

    async def async_fetch_data(self):
        if time() - self.last_on < 30:
            self._is_on = True
        elif time() - self.last_off < 30:
            self._is_on = False
        else:
            alive = await self.async_check_alive()
            self._is_on = alive

    async def async_check_alive(self):
        try:
            _, writer = await asyncio.open_connection(
                self.ip, self.alive_port)
            writer.close()
            await writer.wait_closed()
            return True
        except ConnectionRefusedError:
            return False
        except Exception:
            return False

    async def async_ble_power_on(self, manufacturer_data: str, company_id: int = 0x0046, service_uuid: str = "1812"):
        bus = await get_message_bus()
        advert = Advertisement(
            localName="Bluetooth 4.0 RC",
            serviceUUIDs=[service_uuid],
            manufacturerData={company_id: bytes.fromhex(manufacturer_data)},
            timeout=1,
            duration=1000,
            appearance=961,
        )
        await advert.register(bus)

    async def async_robust_ble_power_on(self, manufacturer_data: str, company_id: int = 0x0046, service_uuid: str = "1812"):
        for i in range(10):
            await self.async_ble_power_on(manufacturer_data, company_id, service_uuid)
            await asyncio.sleep(1)

    async def async_send_command(self, command) -> None:
        """Send a command to a device."""
        if command in self._command_dict:
            if command == "poweroff":
                self._is_on = False
                self.last_off = time()
            msg = self._command_dict[command]
            remote_addr = (self.ip, self.command_port)
            sock = await asyncudp.create_socket(remote_addr=remote_addr)
            sock.sendto(msg.encode("utf-8"))
            sock.close()
        elif command == "poweron":
            self._is_on = True
            self.last_on = time()
            await self.async_robust_ble_power_on(self.manufacturer_data)
        else:
            msg = self._advance_command.replace("command_holder", command)
            remote_addr = (self.ip, self.advance_port)
            sock = await asyncudp.create_socket(remote_addr=remote_addr)
            sock.sendto(msg.encode("utf-8"))
            sock.close()
