"""Tests for JVC Projector sensors."""

from types import SimpleNamespace

from jvcprojector import command as cmd

from custom_components.jvc_projector.sensor import JvcProjectorSensorEntity, SENSORS


def test_light_time_is_numeric() -> None:
    """Expose light-source hours as a numeric duration value."""
    entity = object.__new__(JvcProjectorSensorEntity)
    entity.coordinator = SimpleNamespace(data={cmd.LightTime.name: "1234"})
    entity.command = cmd.LightTime
    entity.entity_description = next(
        description for description in SENSORS if description.command is cmd.LightTime
    )

    assert entity.native_value == 1234
