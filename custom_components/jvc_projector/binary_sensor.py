"""Binary Sensor platform for JVC Projector integration."""

from typing import override

from jvcprojector import command as cmd

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JVCConfigEntry, JvcProjectorDataUpdateCoordinator
from .entity import JvcProjectorEntity

ON_STATUS = (cmd.Power.ON, cmd.Power.WARMING)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JVCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the JVC Projector platform from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        [JvcBinarySensor(coordinator), JvcSignalBinarySensor(coordinator)]
    )


class JvcBinarySensor(JvcProjectorEntity, BinarySensorEntity):
    """The entity class for JVC Projector Binary Sensor."""

    _attr_device_class = BinarySensorDeviceClass.POWER
    _attr_translation_key = "power"

    def __init__(
        self,
        coordinator: JvcProjectorDataUpdateCoordinator,
    ) -> None:
        """Initialize the JVC Projector sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_power"

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if the JVC Projector is on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(cmd.Power.name) in ON_STATUS


class JvcSignalBinarySensor(JvcProjectorEntity, BinarySensorEntity):
    """Represent whether the projector currently receives an input signal."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "signal"

    def __init__(
        self,
        coordinator: JvcProjectorDataUpdateCoordinator,
    ) -> None:
        """Initialize the JVC Projector signal sensor."""
        super().__init__(coordinator, cmd.Signal)
        self._attr_unique_id = f"{coordinator.unique_id}_signal"

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true when the projector reports an input signal."""
        if self.coordinator.data is None:
            return None
        if (signal := self.coordinator.data.get(cmd.Signal.name)) is None:
            return None
        return signal == cmd.Signal.SIGNAL
