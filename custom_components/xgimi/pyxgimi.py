import asyncudp
import asyncio


class XgimiApi:
    def __init__(self, ip, command_port, advance_port, alive_port) -> None:
        self.ip = ip
        self.command_port = command_port  # 16735
        self.advance_port = advance_port  # 16750
        self.alive_port = alive_port  # 554
        self._is_on = False

        self._command_dict = {
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
        }
        self._advance_command = str({"action": 20000, "controlCmd": {"data": "command_holder", "delayTime": 0, "mode": 5, "time": 0, "type": 0}, "msgid": "2"})

    @property
    def is_on(self) -> bool:
        """Return true if the device is on."""
        return self._is_on

    async def async_fetch_data(self):
        try:
            _, writer = await asyncio.open_connection(
                self.ip, self.alive_port)
            writer.close()
            await writer.wait_closed()
            self._is_on = True
        except ConnectionRefusedError:
            self._is_on = False
        except Exception:
            self._is_on = False

    async def async_send_command(self, command) -> None:
        """Send a command to a device."""
        if command in self._command_dict:
            msg = self._command_dict[command]
            remote_addr = (self.ip, self.command_port)
        else:
            msg = self._advance_command.replace("command_holder", command)
            remote_addr = (self.ip, self.advance_port)
        sock = await asyncudp.create_socket(remote_addr=remote_addr)
        sock.sendto(msg.encode("utf-8"))
        sock.close()
