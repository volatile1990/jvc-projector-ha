"""Tests for JVC Projector power actions."""

from unittest.mock import AsyncMock, MagicMock, patch

from jvcprojector import command as cmd
import pytest

from custom_components.jvc_projector.remote import JvcProjectorRemote

pytestmark = pytest.mark.asyncio


def create_remote(power_status: str | None) -> tuple[JvcProjectorRemote, MagicMock]:
    """Create a remote backed by a minimal mocked coordinator."""
    coordinator = MagicMock()
    coordinator.data = None if power_status is None else {cmd.Power.name: power_status}
    coordinator.async_set = AsyncMock()
    coordinator.async_refresh = AsyncMock()

    remote = object.__new__(JvcProjectorRemote)
    remote.coordinator = coordinator
    return remote, coordinator


@pytest.mark.parametrize("power_status", (cmd.Power.STANDBY, cmd.Power.COOLING))
async def test_turn_off_is_idempotent(power_status: str) -> None:
    """Do not contact a projector that is already off or cooling down."""
    remote, coordinator = create_remote(power_status)

    with patch(
        "custom_components.jvc_projector.remote.asyncio.sleep", new=AsyncMock()
    ) as sleep:
        await remote.async_turn_off()

    coordinator.async_set.assert_not_awaited()
    coordinator.async_refresh.assert_not_awaited()
    sleep.assert_not_awaited()


@pytest.mark.parametrize(
    "power_status", (cmd.Power.ON, cmd.Power.WARMING, cmd.Power.ERROR, None)
)
async def test_turn_off_sends_for_non_off_states(power_status: str | None) -> None:
    """Send power off when the state is on, unknown, or erroneous."""
    remote, coordinator = create_remote(power_status)

    with patch("custom_components.jvc_projector.remote.asyncio.sleep", new=AsyncMock()):
        await remote.async_turn_off()

    coordinator.async_set.assert_awaited_once_with(
        cmd.Power,
        cmd.Power.OFF,
        refresh=False,
        optimistic_value=cmd.Power.COOLING,
    )
    coordinator.async_refresh.assert_awaited_once_with()


async def test_second_turn_off_after_ack_is_idempotent() -> None:
    """Do not send a second off command while the first one is taking effect."""
    remote, coordinator = create_remote(cmd.Power.ON)

    async def set_power(command, value, **kwargs) -> None:
        coordinator.data[command.name] = kwargs["optimistic_value"]

    coordinator.async_set.side_effect = set_power

    with patch(
        "custom_components.jvc_projector.remote.asyncio.sleep", new=AsyncMock()
    ) as sleep:
        await remote.async_turn_off()
        await remote.async_turn_off()

    coordinator.async_set.assert_awaited_once()
    coordinator.async_refresh.assert_awaited_once()
    sleep.assert_awaited_once_with(1)


@pytest.mark.parametrize("power_status", (cmd.Power.ON, cmd.Power.WARMING))
async def test_turn_on_is_idempotent(power_status: str) -> None:
    """Do not send power on when the projector is on or warming up."""
    remote, coordinator = create_remote(power_status)

    with patch(
        "custom_components.jvc_projector.remote.asyncio.sleep", new=AsyncMock()
    ) as sleep:
        await remote.async_turn_on()

    coordinator.async_set.assert_not_awaited()
    coordinator.async_refresh.assert_not_awaited()
    sleep.assert_not_awaited()
