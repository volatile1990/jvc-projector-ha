"""Tests for JVC Projector diagnostics."""

from datetime import timedelta
from types import SimpleNamespace

from homeassistant.components.diagnostics import REDACTED
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
import pytest

from custom_components.jvc_projector.diagnostics import (
    async_get_config_entry_diagnostics,
)

pytestmark = pytest.mark.asyncio


async def test_diagnostics_redact_connection_details() -> None:
    """Do not expose the projector address or password in diagnostics."""
    coordinator = SimpleNamespace(
        model="NZ7",
        capabilities_known=True,
        capabilities={"Power": {}, "Signal": {}},
        last_update_success=False,
        last_exception=TimeoutError(),
        update_interval=timedelta(seconds=10),
        data={"Power": "standby"},
    )
    entry = SimpleNamespace(
        data={
            CONF_HOST: "projector.example",
            CONF_PORT: 20554,
            CONF_PASSWORD: "secret",
        },
        runtime_data=coordinator,
    )

    result = await async_get_config_entry_diagnostics(None, entry)

    assert result["config_entry"][CONF_HOST] == REDACTED
    assert result["config_entry"][CONF_PASSWORD] == REDACTED
    assert result["config_entry"][CONF_PORT] == 20554
    assert result["coordinator"]["last_exception"] == "TimeoutError"
    assert result["coordinator"]["data"] == {"Power": "standby"}
