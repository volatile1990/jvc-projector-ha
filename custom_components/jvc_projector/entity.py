"""Base Entity for the jvc_projector integration."""

from jvcprojector import Command, JvcProjector

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, NAME
from .coordinator import JvcProjectorDataUpdateCoordinator


class JvcProjectorEntity(CoordinatorEntity[JvcProjectorDataUpdateCoordinator]):
    """Defines a base JVC Projector entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JvcProjectorDataUpdateCoordinator,
        command: type[Command] | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, command)

        self.command = command
        self._device_unique_id = coordinator.unique_id
        self._attr_unique_id = self._device_unique_id

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return super().available and (
            self.command is None or self.coordinator.supports(self.command)
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        # The config entry unique id is the device's formatted MAC address (set
        # from the projector's MAC in the config flow), so it doubles as the
        # network MAC connection.
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_unique_id)},
            connections={(CONNECTION_NETWORK_MAC, self._device_unique_id)},
            name=NAME,
            model=self.coordinator.model,
            manufacturer=MANUFACTURER,
        )

    @property
    def device(self) -> JvcProjector:
        """Return the device representing the projector."""
        return self.coordinator.device
