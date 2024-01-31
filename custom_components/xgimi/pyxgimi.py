import asyncudp
import asyncio
from bluez_peripheral.util import get_message_bus
from bluez_peripheral.advert import Advertisement
from time import time


class XgimiApi:
    def __init__(self, ip, command_port, advance_port, alive_port, manufacturer_data) -> None:
        self.ip = ip
        self.command_port = command_port  # 16735
        self.advance_port = advance_port  # 16750
        self.alive_port = alive_port  # 554
        self.manufacturer_data = manufacturer_data
        self._is_on = False
        self.last_on = time()
        self.last_off = time()

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
