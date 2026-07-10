"""Diagnostics support for the jvc_projector integration."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .coordinator import JVCConfigEntry

TO_REDACT = (CONF_HOST, CONF_PASSWORD)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: JVCConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator = entry.runtime_data
    last_exception = coordinator.last_exception

    return {
        "config_entry": async_redact_data(entry.data, TO_REDACT),
        "coordinator": {
            "model": coordinator.model,
            "capabilities_known": coordinator.capabilities_known,
            "supported_commands": sorted(coordinator.capabilities),
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                type(last_exception).__name__ if last_exception is not None else None
            ),
            "update_interval_seconds": coordinator.update_interval.total_seconds(),
            "data": coordinator.data,
        },
    }
