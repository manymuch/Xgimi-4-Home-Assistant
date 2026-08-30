"""Asynchronous UDP client for XGIMI projectors."""

from __future__ import annotations

import asyncio
from time import time
from typing import Final

import asyncudp

from .const import COMMAND_POWER_OFF, COMMAND_POWER_ON

COMMAND_PORT: Final = 16735
ADVANCED_COMMAND_PORT: Final = 16750
REACHABILITY_PORT: Final = 554
REACHABILITY_TIMEOUT: Final = 2.0


class XgimiApi:
    """Handle projector reachability and UDP commands only."""

    def __init__(
        self,
        ip: str,
        command_port: int = COMMAND_PORT,
        advance_port: int = ADVANCED_COMMAND_PORT,
        alive_port: int = REACHABILITY_PORT,
    ) -> None:
        """Initialize the projector API."""
        self.ip = ip
        self.command_port = command_port
        self.advance_port = advance_port
        self.alive_port = alive_port
        self._is_on = False
        # Start with no grace window so the first poll reflects the real
        # projector state after a restart or a config-entry reload instead of
        # reporting a stale "on" for the first 30 seconds.
        self.last_on = 0
        self.last_off = 0
        self._projector_reachable: bool | None = None

        self._command_dict: dict[str, str] = {
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
            COMMAND_POWER_OFF: "KEYPRESSES:30",
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
        self._advance_command = str(
            {
                "action": 20000,
                "controlCmd": {
                    "data": "command_holder",
                    "delayTime": 0,
                    "mode": 5,
                    "time": 0,
                    "type": 0,
                },
                "msgid": "2",
            }
        )

    @property
    def is_on(self) -> bool:
        """Return whether the projector is considered on."""
        return self._is_on

    @property
    def supported_commands(self) -> tuple[str, ...]:
        """Return the command names accepted by the remote."""
        return (COMMAND_POWER_ON, *self._command_dict)

    @property
    def projector_reachable(self) -> bool | None:
        """Return the result of the most recent reachability check."""
        return self._projector_reachable

    def mark_wake_successful(self) -> None:
        """Optimistically mark the projector on after wake succeeds."""
        self._is_on = True
        self.last_on = time()

    async def async_fetch_data(self) -> None:
        """Refresh projector state."""
        if time() - self.last_on < 30:
            self._is_on = True
        elif time() - self.last_off < 30:
            self._is_on = False
        else:
            self._is_on = await self.async_check_alive()

    async def async_check_alive(self) -> bool:
        """Check projector reachability over its control-side TCP port."""
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.alive_port),
                timeout=REACHABILITY_TIMEOUT,
            )
            writer.close()
            await writer.wait_closed()
            self._projector_reachable = True
        except Exception:
            self._projector_reachable = False
        return self._projector_reachable

    async def async_send_command(self, command: str) -> None:
        """Send a non-wake command to the projector over UDP."""
        if command == COMMAND_POWER_ON:
            raise ValueError("poweron must be handled by a wake backend")

        if command in self._command_dict:
            if command == COMMAND_POWER_OFF:
                self._is_on = False
                self.last_off = time()
            message = self._command_dict[command]
            remote_address = (self.ip, self.command_port)
        else:
            message = self._advance_command.replace("command_holder", command)
            remote_address = (self.ip, self.advance_port)

        socket = await asyncudp.create_socket(remote_addr=remote_address)
        try:
            socket.sendto(message.encode())
        finally:
            socket.close()
