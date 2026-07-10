"""Remote platform for the jvc_projector integration."""

import asyncio
from collections.abc import Iterable
import logging
from typing import Any, override

from jvcprojector import command as cmd

from homeassistant.components.remote import RemoteEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JVCConfigEntry
from .entity import JvcProjectorEntity

COMMANDS: list[str] = [
    cmd.Remote.MENU,
    cmd.Remote.UP,
    cmd.Remote.DOWN,
    cmd.Remote.LEFT,
    cmd.Remote.RIGHT,
    cmd.Remote.OK,
    cmd.Remote.BACK,
    cmd.Remote.MPC,
    cmd.Remote.HIDE,
    cmd.Remote.INFO,
    cmd.Remote.INPUT,
    cmd.Remote.CMD,
    cmd.Remote.ADVANCED_MENU,
    cmd.Remote.PICTURE_MODE,
    cmd.Remote.COLOR_PROFILE,
    cmd.Remote.LENS_CONTROL,
    cmd.Remote.SETTING_MEMORY,
    cmd.Remote.GAMMA_SETTINGS,
    cmd.Remote.HDMI1,
    cmd.Remote.HDMI2,
    cmd.Remote.MODE_1,
    cmd.Remote.MODE_2,
    cmd.Remote.MODE_3,
    cmd.Remote.MODE_4,
    cmd.Remote.MODE_5,
    cmd.Remote.MODE_6,
    cmd.Remote.MODE_7,
    cmd.Remote.MODE_8,
    cmd.Remote.MODE_9,
    cmd.Remote.MODE_10,
    cmd.Remote.GAMMA,
    cmd.Remote.NATURAL,
    cmd.Remote.CINEMA,
    cmd.Remote.COLOR_TEMP,
    cmd.Remote.ANAMORPHIC,
    cmd.Remote.LENS_APERTURE,
    cmd.Remote.V3D_FORMAT,
]

RENAMED_COMMANDS: dict[str, str] = {
    "anamo": cmd.Remote.ANAMORPHIC,
    "lens_ap": cmd.Remote.LENS_APERTURE,
    "hdmi1": cmd.Remote.HDMI1,
    "hdmi2": cmd.Remote.HDMI2,
}

ON_STATUS = (cmd.Power.ON, cmd.Power.WARMING)
OFF_STATUS = (cmd.Power.STANDBY, cmd.Power.COOLING)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JVCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the JVC Projector platform from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([JvcProjectorRemote(coordinator)], True)


class JvcProjectorRemote(JvcProjectorEntity, RemoteEntity):
    """Representation of a JVC Projector device."""

    _attr_name = None

    @property
    def _power_status(self) -> str | None:
        """Return the last known detailed power status."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(cmd.Power.name)

    @property
    @override
    def is_on(self) -> bool | None:
        """Return True if the entity is on."""
        if (power_status := self._power_status) is None:
            return None
        return power_status in ON_STATUS

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        if self._power_status in ON_STATUS:
            return

        await self.coordinator.async_set(
            cmd.Power,
            cmd.Power.ON,
            refresh=False,
            optimistic_value=cmd.Power.WARMING,
        )
        await asyncio.sleep(1)
        await self.coordinator.async_refresh()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        if self._power_status in OFF_STATUS:
            return

        await self.coordinator.async_set(
            cmd.Power,
            cmd.Power.OFF,
            refresh=False,
            optimistic_value=cmd.Power.COOLING,
        )
        await asyncio.sleep(1)
        await self.coordinator.async_refresh()

    @override
    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send a remote command to the device."""
        for send_command in command:
            # Legacy name replace
            if send_command in RENAMED_COMMANDS:
                send_command = RENAMED_COMMANDS[send_command]

            # Legacy name fixup
            if "_" in send_command:
                send_command = send_command.replace("_", "-")

            if send_command not in COMMANDS:
                raise HomeAssistantError(f"{send_command} is not a known command")

            _LOGGER.debug("Sending command '%s'", send_command)
            await self.coordinator.async_remote(send_command)
