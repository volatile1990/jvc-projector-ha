"""Data update coordinator for the jvc_projector integration."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any, override

from jvcprojector import (
    JvcProjector,
    JvcProjectorAuthError,
    JvcProjectorCommandError,
    JvcProjectorError,
    JvcProjectorTimeoutError,
    command as cmd,
)
from jvcprojector.error import JvcProjectorReadWriteTimeoutError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_MODEL, NAME

if TYPE_CHECKING:
    from jvcprojector import Command


_LOGGER = logging.getLogger(__name__)

INTERVAL_SLOW = timedelta(seconds=10)
INTERVAL_FAST = timedelta(seconds=5)

CORE_COMMANDS: tuple[type[Command], ...] = (
    cmd.Power,
    cmd.Signal,
    cmd.Input,
    cmd.LightTime,
)

TRANSLATIONS = str.maketrans({"+": "p", "%": "p", ":": "x"})

TIMEOUT_RETRIES = 12
TIMEOUT_SLEEP = 1

TRANSIENT_ERRORS = (
    JvcProjectorTimeoutError,
    JvcProjectorError,
    OSError,
    TimeoutError,
    asyncio.TimeoutError,
)

FALLBACK_OPTIONS: dict[str, tuple[str, ...]] = {
    cmd.Power.name: (
        cmd.Power.STANDBY,
        cmd.Power.ON,
        cmd.Power.COOLING,
        cmd.Power.WARMING,
        cmd.Power.ERROR,
    ),
    cmd.Input.name: (cmd.Input.HDMI1, cmd.Input.HDMI2),
    cmd.Signal.name: (cmd.Signal.NONE, cmd.Signal.SIGNAL),
    cmd.ColorDepth.name: ("8-bit", "10-bit", "12-bit"),
    cmd.ColorSpace.name: (
        "rgb",
        "yuv",
        "xv-color",
        "ycbcr-420",
        "ycbcr-422",
        "ycbcr-444",
    ),
    cmd.Hdr.name: ("none", "sdr", "hdr", "hdr10+", "hybrid-log", "smpte-st-2084"),
    cmd.HdrProcessing.name: (
        "static",
        "frame-by-frame",
        "scene-by-scene",
        "hdr10+",
    ),
    cmd.PictureMode.name: (
        "frame-adapt-hdr",
        "frame-adapt-hdr2",
        "frame-adapt-hdr3",
        "hdr1",
        "hdr2",
        "hdr10",
        "hdr10-ll",
        "last-setting",
        "pana-pq",
        "user-4",
        "user-5",
        "user-6",
    ),
    cmd.InstallationMode.name: (
        "memory-1",
        "memory-2",
        "memory-3",
        "memory-4",
        "memory-5",
        "memory-6",
        "memory-7",
        "memory-8",
        "memory-9",
        "memory-10",
    ),
    cmd.LightPower.name: ("low", "mid", "normal", "high"),
    cmd.DynamicControl.name: (
        "off",
        "low",
        "balanced",
        "high",
        "mode-1",
        "mode-2",
        "mode-3",
    ),
    cmd.ClearMotionDrive.name: ("off", "low", "high", "inverse-telecine"),
    cmd.Anamorphic.name: ("off", "a", "b", "c", "d"),
}

type JVCConfigEntry = ConfigEntry[JvcProjectorDataUpdateCoordinator]


class JvcProjectorCommunicationError(HomeAssistantError):
    """Raised when communication with the projector fails."""


class JvcProjectorDataUpdateCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Data update coordinator for the JVC Projector integration."""

    config_entry: JVCConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: JVCConfigEntry, device: JvcProjector
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=NAME,
            update_interval=INTERVAL_SLOW,
        )

        self.device: JvcProjector = device

        if TYPE_CHECKING:
            assert config_entry.unique_id is not None
        self.unique_id = config_entry.unique_id

        self.model: str | None = config_entry.data.get(CONF_MODEL)
        self.capabilities: dict[str, Any] = {}
        self.capabilities_known = False
        self._initialized = False

        self.state: dict[type[Command], str] = {}

    async def async_setup_from_cache(self) -> None:
        """Initialize command metadata from the cached model without network I/O."""
        if not self.model:
            return

        try:
            await self.device.connect(model=self.model)
        except JvcProjectorError as err:
            _LOGGER.debug(
                "Failed to initialize cached JVC model %s: %s", self.model, err
            )
            return

        self._initialized = True
        self._refresh_capabilities()

    @override
    async def _async_update_data(self) -> dict[str, Any]:
        """Update state with the current value of a command."""
        try:
            await self._async_ensure_initialized()
        except JvcProjectorAuthError as err:
            await self.async_disconnect()
            raise ConfigEntryAuthFailed("Password authentication failed") from err
        except TRANSIENT_ERRORS as err:
            await self.async_disconnect()
            self.update_interval = INTERVAL_SLOW
            raise UpdateFailed(
                f"Unable to connect to projector at {self.device.host}: {err}"
            ) from err

        commands: set[type[Command]] = set(self.async_contexts())
        commands = commands.difference(CORE_COMMANDS)
        commands = {command for command in commands if self.supports(command)}

        last_timeout: JvcProjectorReadWriteTimeoutError | None = None

        for _ in range(TIMEOUT_RETRIES):
            try:
                new_state = await self._get_device_state(commands)
                break
            except JvcProjectorReadWriteTimeoutError as err:
                # Read/write timeouts are expected when the projector loses
                # signal or briefly ignores commands during mode changes.
                last_timeout = err
                await asyncio.sleep(TIMEOUT_SLEEP)
            except JvcProjectorAuthError as err:
                await self.async_disconnect()
                raise ConfigEntryAuthFailed("Password authentication failed") from err
            except TRANSIENT_ERRORS as err:
                self.update_interval = INTERVAL_SLOW
                raise UpdateFailed(
                    f"Unable to update projector state at {self.device.host}: {err}"
                ) from err
        else:
            self.update_interval = INTERVAL_SLOW
            raise UpdateFailed(str(last_timeout)) from last_timeout

        # Clear state on signal loss
        if (
            new_state.get(cmd.Signal) == cmd.Signal.NONE
            and self.state.get(cmd.Signal) != cmd.Signal.NONE
        ):
            self.state = {k: v for k, v in self.state.items() if k in CORE_COMMANDS}

        # Update state with new values
        for k, v in new_state.items():
            self.state[k] = v

        if self.state[cmd.Power] != cmd.Power.STANDBY:
            self.update_interval = INTERVAL_FAST
        else:
            self.update_interval = INTERVAL_SLOW

        return {k.name: v for k, v in self.state.items()}

    async def async_disconnect(self) -> None:
        """Disconnect from the projector and reset runtime initialization."""
        try:
            await self.device.disconnect()
        except TRANSIENT_ERRORS as err:
            _LOGGER.debug("Error disconnecting from JVC projector: %s", err)
        finally:
            self._initialized = False

    async def _get_device_state(
        self, commands: set[type[Command]]
    ) -> dict[type[Command], str]:
        """Get the current state of the device."""
        new_state: dict[type[Command], str] = {}
        deferred_commands: list[type[Command]] = []

        power = await self._update_command_state(cmd.Power, new_state)

        if power == cmd.Power.ON:
            signal = await self._update_command_state(cmd.Signal, new_state)
            await self._update_command_state(cmd.Input, new_state)
            await self._update_command_state(cmd.LightTime, new_state)

            if signal == cmd.Signal.SIGNAL:
                for command in commands:
                    if command.depends:
                        # Command has dependencies so defer until below
                        deferred_commands.append(command)
                    else:
                        await self._update_command_state(command, new_state)

                # Deferred commands should have had dependencies met above
                for command in deferred_commands:
                    depend_command, depend_values = next(iter(command.depends.items()))
                    value: str | None = None
                    if depend_command in new_state:
                        value = new_state[depend_command]
                    elif depend_command in self.state:
                        value = self.state[depend_command]
                    if value and value in depend_values:
                        await self._update_command_state(command, new_state)

        elif self.state.get(cmd.Signal) != cmd.Signal.NONE:
            new_state[cmd.Signal] = cmd.Signal.NONE

        return new_state

    async def _update_command_state(
        self, command: type[Command], new_state: dict[type[Command], str]
    ) -> str | None:
        """Update state with the current value of a command."""
        try:
            value = await self.device.get(command)
        except JvcProjectorCommandError as err:
            _LOGGER.warning("Command %s failed: %s", command.name, err)
            cached = self.state.get(command)
            if command is cmd.Power and cached is None:
                raise UpdateFailed(
                    f"Failed to fetch {command.name} and no cached value is available"
                ) from err
            return cached

        if value != self.state.get(command):
            new_state[command] = value

        return value

    async def async_set(
        self,
        command: type[Command],
        value: str,
        *,
        refresh: bool = True,
    ) -> None:
        """Set a projector command with connection recovery handling."""
        await self._async_run_device_command(
            f"setting {command.name}",
            self.device.set,
            command,
            value,
            required_command=command,
        )

        if refresh:
            await self.async_request_refresh()

    async def async_remote(self, value: str) -> None:
        """Send a remote command with connection recovery handling."""
        await self._async_run_device_command(
            f"sending remote command {value}",
            self.device.remote,
            value,
            required_command=cmd.Remote,
        )

    async def _async_run_device_command(
        self,
        action: str,
        command: Callable[..., Awaitable[Any]],
        *args: Any,
        required_command: type[Command] | None = None,
    ) -> None:
        """Run a device command and mark the coordinator unavailable on failure."""
        try:
            await self._async_ensure_initialized()
            if required_command is not None and not self.supports(required_command):
                raise HomeAssistantError(
                    f"JVC projector does not support {required_command.name}"
                )
            await command(*args)
        except JvcProjectorCommandError as err:
            raise HomeAssistantError(
                f"JVC projector command failed while {action}"
            ) from err
        except JvcProjectorAuthError as err:
            await self.async_disconnect()
            self.mark_unavailable(err)
            self.config_entry.async_start_reauth_if_available(self.hass)
            raise HomeAssistantError(
                "JVC projector authentication failed; reauthentication required"
            ) from err
        except TRANSIENT_ERRORS as err:
            self.mark_unavailable(err)
            raise JvcProjectorCommunicationError(
                f"JVC projector is unavailable while {action}"
            ) from err

    async def _async_ensure_initialized(self) -> None:
        """Initialize the JVC command set before sending commands."""
        if self._initialized:
            return

        await self.device.connect(model=self.model)
        self._initialized = True

        try:
            self.model = self.device.model
        except JvcProjectorError:
            self.model = None

        self._refresh_capabilities()
        self._store_model()

    def _refresh_capabilities(self) -> None:
        """Refresh command capabilities from the initialized projector model."""
        try:
            self.capabilities = self.device.capabilities()
        except JvcProjectorError as err:
            _LOGGER.debug("Failed to load JVC projector capabilities: %s", err)
            return

        self.capabilities_known = True

    def _store_model(self) -> None:
        """Persist the detected model so later HA starts can work offline."""
        if not self.model or self.config_entry.data.get(CONF_MODEL) == self.model:
            return

        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={**self.config_entry.data, CONF_MODEL: self.model},
        )

    def mark_unavailable(self, err: BaseException | None = None) -> None:
        """Mark entities unavailable immediately after a command failure."""
        if err is not None:
            self.last_exception = err
        if self.last_update_success:
            self.last_update_success = False
            self.async_update_listeners()
        self.update_interval = INTERVAL_SLOW

    def get_options_map(
        self, command: str, *, snake_case: bool = False
    ) -> dict[str, str]:
        """Get the available options for a command."""
        values: list[str]
        if capabilities := self.capabilities.get(command):
            if TYPE_CHECKING:
                assert isinstance(capabilities, dict)
                assert isinstance(capabilities.get("parameter", {}), dict)
                assert isinstance(
                    capabilities.get("parameter", {}).get("read", {}), dict
                )

            values = list(capabilities.get("parameter", {}).get("read", {}).values())
        elif self.capabilities_known:
            values = []
        else:
            values = list(FALLBACK_OPTIONS.get(command, ()))

        options = {v: v.translate(TRANSLATIONS) for v in values}
        if snake_case:
            return {k: v.replace("-", "_") for k, v in options.items()}
        return options

    def supports(self, command: type[Command]) -> bool:
        """Check if the device supports a command."""
        if self.capabilities_known:
            return command.name in self.capabilities
        return True
