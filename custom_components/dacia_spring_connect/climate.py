"""Climate platform for Dacia Spring Connect (HVAC pre-conditioning)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DaciaSpringConnectCoordinator
from .entity import DaciaSpringConnectEntity

DEFAULT_HVAC_TEMP = 21.0
MIN_TEMP = 16.0
MAX_TEMP = 26.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dacia Spring Connect climate entity."""
    coordinator: DaciaSpringConnectCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([DaciaSpringConnectClimate(coordinator)])


class DaciaSpringConnectClimate(DaciaSpringConnectEntity, ClimateEntity):
    """Climate entity for Dacia Spring Connect pre-conditioning."""

    _attr_translation_key = "hvac"
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = 1.0

    def __init__(self, coordinator: DaciaSpringConnectCoordinator) -> None:
        """Initialise the climate entity."""
        super().__init__(coordinator, "hvac")
        self._target_temperature = DEFAULT_HVAC_TEMP

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        data = self.coordinator.data
        if data and data.hvac_status and data.hvac_status.hvacStatus == "on":
            return HVACMode.HEAT_COOL
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action."""
        if self.hvac_mode == HVACMode.HEAT_COOL:
            return HVACAction.HEATING
        return HVACAction.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return current exterior temperature."""
        data = self.coordinator.data
        if data and data.hvac_status:
            return data.hvac_status.externalTemperature
        return None

    @property
    def target_temperature(self) -> float:
        """Return target temperature for pre-conditioning."""
        return self._target_temperature

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.HEAT_COOL:
            await self.coordinator.async_set_hvac("start", self._target_temperature)
        else:
            await self.coordinator.async_set_hvac("stop")

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._target_temperature = temperature
            if self.hvac_mode == HVACMode.HEAT_COOL:
                await self.coordinator.async_set_hvac("start", temperature)

    async def async_turn_on(self) -> None:
        """Turn on pre-conditioning."""
        await self.coordinator.async_set_hvac("start", self._target_temperature)

    async def async_turn_off(self) -> None:
        """Turn off pre-conditioning."""
        await self.coordinator.async_set_hvac("stop")
