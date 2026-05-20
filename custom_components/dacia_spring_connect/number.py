"""Number platform for Dacia Spring Connect — charge limit control."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DaciaSpringConnectCoordinator
from .entity import DaciaSpringConnectEntity

_LOGGER = logging.getLogger(__name__)

DEFAULT_CHARGE_LIMIT = 80
STOP_COMMAND_TIMEOUT = timedelta(minutes=10)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dacia Spring Connect charge limit number entity."""
    coordinator: DaciaSpringConnectCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([DaciaSpringConnectChargeLimit(coordinator)])


class DaciaSpringConnectChargeLimit(DaciaSpringConnectEntity, NumberEntity, RestoreEntity):
    """Number entity that caps charging at a configurable battery percentage.

    After every coordinator refresh, if the car is actively charging and the
    battery level has reached (or exceeded) the configured limit, a charge-stop
    command is issued automatically — no HA automation required.
    """

    _attr_translation_key = "charge_limit"
    _attr_native_min_value = 50
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:battery-charging-80"

    def __init__(self, coordinator: DaciaSpringConnectCoordinator) -> None:
        """Initialise the charge limit entity."""
        super().__init__(coordinator, "charge_limit")
        self._attr_native_value: float = DEFAULT_CHARGE_LIMIT
        self._stop_requested_at: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Restore previous value and register the charge-limit enforcement callback."""
        await super().async_added_to_hass()

        # Restore the last known limit across restarts.
        # Guard against "unavailable"/"unknown" — those are written when HA shuts
        # down while the coordinator is stopped, not the actual user-set value.
        if (
            (last_state := await self.async_get_last_state()) is not None
            and last_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        ):
            try:
                self._attr_native_value = float(last_state.state)
            except (ValueError, TypeError):
                pass

        # Run the check after every coordinator data refresh
        self.async_on_remove(
            self.coordinator.async_add_listener(self._async_enforce_charge_limit)
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the configured charge limit.

        If the new limit is raised above the current battery level while the
        cable is still plugged in and charging is stopped (because this
        integration previously stopped it), automatically restart charging.
        """
        old_limit = self._attr_native_value
        _LOGGER.debug(
            "Charge limit updated: %.0f%% → %.0f%%",
            old_limit,
            value,
        )
        self._attr_native_value = value
        self.async_write_ha_state()

        # If the user raises the limit above the current battery level while the
        # car is plugged in but not charging, restart charging automatically.
        data = self.coordinator.data
        if not (data and data.battery_status):
            return
        bs = data.battery_status
        cable_plugged = bs.plugStatus == 1
        currently_charging = (
            bs.chargingStatus is not None and float(bs.chargingStatus) > 0
        )
        battery_below_new_limit = (
            bs.batteryLevel is not None and bs.batteryLevel < value
        )
        limit_was_raised = value > old_limit

        if (
            limit_was_raised
            and cable_plugged
            and not currently_charging
            and battery_below_new_limit
        ):
            # Clear any pending stop-acknowledgment flag — user explicitly
            # overrode the limit, so previous stop state is no longer relevant.
            self._stop_requested_at = None
            _LOGGER.warning(
                "Charge limit raised from %.0f%% to %.0f%% "
                "while battery is at %s%% and cable is connected — restarting charging",
                old_limit,
                value,
                bs.batteryLevel,
            )
            await self.coordinator.async_charge_start()

    @callback
    def _async_enforce_charge_limit(self) -> None:
        """Stop charging if the battery has reached the configured limit.

        A timestamp flag prevents duplicate commands while the car still reports
        chargingStatus=1 due to API latency after a stop was issued.  The flag
        is cleared when the car confirms it stopped, or after STOP_COMMAND_TIMEOUT
        in case the command failed and was never acknowledged.
        """
        data = self.coordinator.data
        if not (data and data.battery_status):
            return

        bs = data.battery_status

        if self._stop_requested_at is not None:
            car_stopped = bs.chargingStatus is None or float(bs.chargingStatus) == 0
            timed_out = datetime.now(UTC) - self._stop_requested_at > STOP_COMMAND_TIMEOUT
            if car_stopped:
                _LOGGER.debug(
                    "Car confirmed charge stopped (chargingStatus=%s)",
                    bs.chargingStatus,
                )
                self._stop_requested_at = None
            elif timed_out:
                _LOGGER.warning(
                    "Charge stop command was not acknowledged within %s — retrying",
                    STOP_COMMAND_TIMEOUT,
                )
                self._stop_requested_at = None
            else:
                _LOGGER.debug(
                    "Waiting for car to acknowledge charge stop "
                    "(battery=%s%%, charging=%s, elapsed=%s)",
                    bs.batteryLevel,
                    bs.chargingStatus,
                    datetime.now(UTC) - self._stop_requested_at,
                )
                return  # still waiting for the car to acknowledge

        is_charging = (
            bs.plugStatus == 1
            and bs.chargingStatus is not None
            and float(bs.chargingStatus) > 0
        )

        if is_charging:
            _LOGGER.debug(
                "Charge limit check: battery=%s%%, limit=%s%%, chargingStatus=%s",
                bs.batteryLevel,
                self._attr_native_value,
                bs.chargingStatus,
            )

        if (
            is_charging
            and bs.batteryLevel is not None
            and bs.batteryLevel >= self._attr_native_value
        ):
            _LOGGER.warning(
                "Battery level %s%% reached charge limit %s%% — sending charge stop",
                bs.batteryLevel,
                self._attr_native_value,
            )
            self._stop_requested_at = datetime.now(UTC)
            self.hass.async_create_task(
                self.coordinator.async_charge_stop(),
                eager_start=False,
            )
