"""Base entity for Dacia Spring Connect."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DaciaSpringConnectCoordinator


class DaciaSpringConnectEntity(CoordinatorEntity[DaciaSpringConnectCoordinator]):
    """Base entity class for Dacia Spring Connect."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DaciaSpringConnectCoordinator, unique_id_suffix: str) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        vin = coordinator._vin
        self._attr_unique_id = f"{vin}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            manufacturer="Dacia",
            model="Spring",
            name=f"Dacia Spring Connect {vin[-4:]}",
        )
