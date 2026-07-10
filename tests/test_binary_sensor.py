"""Tests for JVC Projector binary sensors."""

from types import SimpleNamespace

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from jvcprojector import command as cmd
import pytest

from custom_components.jvc_projector.binary_sensor import (
    JvcBinarySensor,
    JvcSignalBinarySensor,
)


def test_power_sensor_has_device_class() -> None:
    """Identify the power binary sensor to Home Assistant."""
    entity = object.__new__(JvcBinarySensor)

    assert entity.device_class is BinarySensorDeviceClass.POWER


@pytest.mark.parametrize(
    ("signal", "expected"),
    ((cmd.Signal.SIGNAL, True), (cmd.Signal.NONE, False), (None, None)),
)
def test_signal_sensor(signal: str | None, expected: bool | None) -> None:
    """Expose the already-polled input-signal state."""
    entity = object.__new__(JvcSignalBinarySensor)
    entity.coordinator = SimpleNamespace(data={cmd.Signal.name: signal})

    assert entity.is_on is expected
