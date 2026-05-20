"""Binary sensor platform for Dacia Spring Connect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DaciaSpringConnectCoordinator
from .entity import DaciaSpringConnectEntity


@dataclass(frozen=True, kw_only=True)
class DaciaSpringConnectBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a Dacia Spring Connect binary sensor."""

    value_fn: Any = None


BINARY_SENSOR_DESCRIPTIONS: tuple[DaciaSpringConnectBinarySensorDescription, ...] = (
    DaciaSpringConnectBinarySensorDescription(
        key="plugged_in",
        translation_key="plugged_in",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=lambda data: (
            data.battery_status.plugStatus == 1
            if data.battery_status
            else None
        ),
    ),
    DaciaSpringConnectBinarySensorDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda data: (
            data.battery_status.chargingStatus is not None
            and str(data.battery_status.chargingStatus.name).lower() == "charge_in_progress"
            if data.battery_status
            else None
        ),
    ),
    DaciaSpringConnectBinarySensorDescription(
        key="hvac_active",
        translation_key="hvac_active",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: (
            data.hvac_status.hvacStatus == "on"
            if data.hvac_status
            else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dacia Spring Connect binary sensors."""
    coordinator: DaciaSpringConnectCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        DaciaSpringConnectBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class DaciaSpringConnectBinarySensor(DaciaSpringConnectEntity, BinarySensorEntity):
    """Represents a Dacia Spring Connect binary sensor."""

    entity_description: DaciaSpringConnectBinarySensorDescription

    def __init__(
        self,
        coordinator: DaciaSpringConnectCoordinator,
        description: DaciaSpringConnectBinarySensorDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the sensor state."""
        return self.entity_description.value_fn(self.coordinator.data)
