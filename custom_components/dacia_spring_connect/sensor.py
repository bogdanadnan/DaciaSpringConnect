"""Sensor platform for Dacia Spring Connect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DaciaSpringConnectCoordinator, DaciaSpringConnectData
from .entity import DaciaSpringConnectEntity


@dataclass(frozen=True, kw_only=True)
class DaciaSpringConnecteSensorDescription(SensorEntityDescription):
    """Describes a Dacia Spring Connect sensor."""

    value_fn: Any = None


SENSOR_DESCRIPTIONS: tuple[DaciaSpringConnecteSensorDescription, ...] = (
    DaciaSpringConnecteSensorDescription(
        key="battery_level",
        translation_key="battery_level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: (
            data.battery_status.batteryLevel
            if data.battery_status
            else None
        ),
    ),
    DaciaSpringConnecteSensorDescription(
        key="battery_autonomy",
        translation_key="battery_autonomy",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        value_fn=lambda data: (
            data.battery_status.batteryAutonomy
            if data.battery_status
            else None
        ),
    ),
    DaciaSpringConnecteSensorDescription(
        key="charging_remaining_time",
        translation_key="charging_remaining_time",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="min",
        value_fn=lambda data: (
            data.battery_status.chargingRemainingTime
            if data.battery_status
            else None
        ),
    ),
    DaciaSpringConnecteSensorDescription(
        key="charge_status",
        translation_key="charge_status",
        device_class=SensorDeviceClass.ENUM,
        options=["not_in_charge", "waiting_for_a_planned_charge", "charge_ended",
                 "waiting_for_current_charge", "energy_flap_opened", "charge_in_progress",
                 "charge_error", "unavailable"],
        value_fn=lambda data: (
            cs.name.lower()
            if data.battery_status and (cs := data.battery_status.get_charging_status()) is not None
            else None
        ),
    ),
    DaciaSpringConnecteSensorDescription(
        key="mileage",
        translation_key="mileage",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        value_fn=lambda data: (
            data.cockpit.totalMileage
            if data.cockpit
            else None
        ),
    ),
    DaciaSpringConnecteSensorDescription(
        key="external_temperature",
        translation_key="external_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: (
            data.hvac_status.externalTemperature
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
    """Set up Dacia Spring Connect sensors."""
    coordinator: DaciaSpringConnectCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        DaciaSpringConnecteSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class DaciaSpringConnecteSensor(DaciaSpringConnectEntity, SensorEntity):
    """Represents a Dacia Spring Connect sensor."""

    entity_description: DaciaSpringConnecteSensorDescription

    def __init__(
        self,
        coordinator: DaciaSpringConnectCoordinator,
        description: DaciaSpringConnecteSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
