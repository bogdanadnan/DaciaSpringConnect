"""Select platform for Dacia Spring Connect (charge mode)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DaciaSpringConnectCoordinator
from .entity import DaciaSpringConnectEntity

CHARGE_MODES = ["always", "always_charging", "schedule_mode"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dacia Spring Connect charge mode selector."""
    coordinator: DaciaSpringConnectCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    # Skip entity if this model doesn't support the charge-mode endpoint
    if coordinator.data and coordinator.data.charge_mode is None:
        return
    async_add_entities([DaciaSpringConnectChargeMode(coordinator)])


class DaciaSpringConnectChargeMode(DaciaSpringConnectEntity, SelectEntity):
    """Select entity for Dacia Spring Connect charge mode."""

    _attr_translation_key = "charge_mode"
    _attr_options = CHARGE_MODES

    def __init__(self, coordinator: DaciaSpringConnectCoordinator) -> None:
        """Initialise the select entity."""
        super().__init__(coordinator, "charge_mode")

    @property
    def current_option(self) -> str | None:
        """Return the current charge mode."""
        data = self.coordinator.data
        if data and data.charge_mode and data.charge_mode.chargeMode:
            mode = str(data.charge_mode.chargeMode).lower()
            return mode if mode in CHARGE_MODES else None
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the charge mode."""
        await self.coordinator.async_set_charge_mode(option)
