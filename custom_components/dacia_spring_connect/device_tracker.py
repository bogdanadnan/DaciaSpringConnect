"""Device tracker platform for Dacia Spring Connect."""
from __future__ import annotations

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DaciaSpringConnectCoordinator
from .entity import DaciaSpringConnectEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dacia Spring Connect device tracker."""
    coordinator: DaciaSpringConnectCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([DaciaSpringConnectTracker(coordinator)])


class DaciaSpringConnectTracker(DaciaSpringConnectEntity, TrackerEntity):
    """Device tracker for Dacia Spring Connect GPS location."""

    _attr_translation_key = "location"
    _attr_force_update = False

    def __init__(self, coordinator: DaciaSpringConnectCoordinator) -> None:
        """Initialise the tracker."""
        super().__init__(coordinator, "location")

    @property
    def latitude(self) -> float | None:
        """Return vehicle latitude."""
        data = self.coordinator.data
        if data and data.location and data.location.gpsLatitude is not None:
            return float(data.location.gpsLatitude)
        return None

    @property
    def longitude(self) -> float | None:
        """Return vehicle longitude."""
        data = self.coordinator.data
        if data and data.location and data.location.gpsLongitude is not None:
            return float(data.location.gpsLongitude)
        return None

    @property
    def source_type(self) -> str:
        """Return source type."""
        from homeassistant.components.device_tracker import SourceType
        return SourceType.GPS
