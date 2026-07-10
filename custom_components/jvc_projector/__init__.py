"""The jvc_projector integration."""

from jvcprojector import JvcProjector

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_registry import RegistryEntry, async_migrate_entries

from .const import NAME
from .coordinator import JVCConfigEntry, JvcProjectorDataUpdateCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.REMOTE,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: JVCConfigEntry) -> bool:
    """Set up integration from a config entry."""
    device = JvcProjector(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        password=entry.data.get(CONF_PASSWORD),
    )

    coordinator = JvcProjectorDataUpdateCoordinator(hass, entry, device)
    await coordinator.async_setup_from_cache()

    entry.runtime_data = coordinator

    async def disconnect(event: Event) -> None:
        await coordinator.async_disconnect()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, disconnect)
    )

    await async_migrate_entities(hass, entry, coordinator)

    # A hard powered-off projector is a recoverable runtime state, not a setup
    # failure. Start unavailable and recover through normal polling.
    coordinator.mark_unavailable()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_create_background_task(
        hass,
        coordinator.async_refresh(),
        name=f"{NAME} initial refresh",
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: JVCConfigEntry) -> bool:
    """Unload config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_disconnect()
    return unload_ok


async def async_migrate_entities(
    hass: HomeAssistant,
    config_entry: JVCConfigEntry,
    coordinator: JvcProjectorDataUpdateCoordinator,
) -> None:
    """Migrate old entities as needed."""

    @callback
    def _update_entry(entry: RegistryEntry) -> dict[str, str] | None:
        """Fix unique_id of power binary_sensor entry."""
        if entry.domain == Platform.BINARY_SENSOR and ":" not in entry.unique_id:
            if entry.unique_id.endswith("_power"):
                return {"new_unique_id": f"{coordinator.unique_id}_power"}
        return None

    await async_migrate_entries(hass, config_entry.entry_id, _update_entry)
