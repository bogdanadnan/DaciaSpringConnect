"""Tests for sensor, binary_sensor, select, button, device_tracker, and number entities."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.dacia_spring_connect.const import DATA_COORDINATOR, DOMAIN

from .conftest import MOCK_VIN


# ---------------------------------------------------------------------------
# Sensor
# ---------------------------------------------------------------------------

async def test_battery_level_sensor(hass: HomeAssistant, setup_integration):
    """Battery level sensor should reflect the mocked API value."""
    state = hass.states.get(f"sensor.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_battery_level")
    assert state is not None
    assert state.state == "75"


async def test_battery_autonomy_sensor(hass: HomeAssistant, setup_integration):
    state = hass.states.get(f"sensor.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_battery_autonomy")
    assert state is not None
    assert state.state == "180"


async def test_mileage_sensor(hass: HomeAssistant, setup_integration):
    state = hass.states.get(f"sensor.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_mileage")
    assert state is not None
    assert float(state.state) == pytest.approx(12500.0)


async def test_charge_status_sensor(hass: HomeAssistant, setup_integration):
    """Charge status should be the lower-cased enum name."""
    state = hass.states.get(f"sensor.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_charge_status")
    assert state is not None
    assert state.state == "charge_in_progress"


async def test_external_temperature_sensor(hass: HomeAssistant, setup_integration):
    """External temperature sensor should reflect hvac_status.externalTemperature."""
    state = hass.states.get(f"sensor.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_exterior_temperature")
    assert state is not None
    # externalTemperature is None in the default mock → sensor reports unknown
    assert state.state == "unknown"


# ---------------------------------------------------------------------------
# Binary sensor
# ---------------------------------------------------------------------------

async def test_plugged_in_binary_sensor(hass: HomeAssistant, setup_integration):
    """plugStatus == 1 should mean plugged in (on)."""
    state = hass.states.get(f"binary_sensor.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_plugged_in")
    assert state is not None
    assert state.state == "on"


async def test_charging_binary_sensor(hass: HomeAssistant, setup_integration):
    """CHARGE_IN_PROGRESS status should make charging sensor 'on'."""
    state = hass.states.get(f"binary_sensor.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_charging")
    assert state is not None
    assert state.state == "on"


async def test_hvac_active_binary_sensor(hass: HomeAssistant, setup_integration):
    """hvacStatus == 'off' should make hvac_active sensor 'off'."""
    state = hass.states.get(f"binary_sensor.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_pre_conditioning_active")
    assert state is not None
    assert state.state == "off"


# ---------------------------------------------------------------------------
# Select
# ---------------------------------------------------------------------------

async def test_charge_mode_select(hass: HomeAssistant, setup_integration):
    state = hass.states.get(f"select.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_charge_mode")
    assert state is not None
    assert state.state == "always"


async def test_charge_mode_select_change(hass: HomeAssistant, setup_integration, mock_vehicle):
    """Selecting a new charge mode should call set_charge_mode on the vehicle."""
    await hass.services.async_call(
        "select",
        "select_option",
        {
            "entity_id": f"select.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_charge_mode",
            "option": "schedule_mode",
        },
        blocking=True,
    )
    mock_vehicle.set_charge_mode.assert_awaited_once_with("schedule_mode")


# ---------------------------------------------------------------------------
# Button
# ---------------------------------------------------------------------------

async def test_hvac_start_button(hass: HomeAssistant, setup_integration, mock_vehicle):
    """Pressing the pre-conditioning button should call set_ac_start."""
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": f"button.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_start_pre_conditioning"},
        blocking=True,
    )
    mock_vehicle.set_ac_start.assert_awaited_once()

async def test_charge_start_button(hass: HomeAssistant, setup_integration, mock_vehicle):
    """Pressing the charge start button should call set_charge_start."""
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": f"button.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_start_charging"},
        blocking=True,
    )
    mock_vehicle.set_charge_start.assert_awaited_once()


async def test_charge_stop_button(hass: HomeAssistant, setup_integration, mock_vehicle):
    """Pressing the charge stop button should call set_charge_stop."""
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": f"button.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_stop_charging"},
        blocking=True,
    )
    mock_vehicle.set_charge_stop.assert_awaited_once()


async def test_refresh_location_button(hass: HomeAssistant, setup_integration, mock_vehicle):
    """Pressing the refresh location button should call refresh_location."""
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": f"button.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_refresh_location"},
        blocking=True,
    )
    mock_vehicle.refresh_location.assert_awaited_once()


# ---------------------------------------------------------------------------
# Number — charge limit
# ---------------------------------------------------------------------------

async def test_charge_limit_default(hass: HomeAssistant, setup_integration):
    """Charge limit entity should default to 80%."""
    state = hass.states.get(f"number.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_charge_limit")
    assert state is not None
    assert float(state.state) == pytest.approx(80.0)


async def test_charge_limit_set(hass: HomeAssistant, setup_integration):
    """Setting the charge limit via service call should update the entity state."""
    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": f"number.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_charge_limit",
            "value": 70,
        },
        blocking=True,
    )
    state = hass.states.get(f"number.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_charge_limit")
    assert float(state.state) == pytest.approx(70.0)


async def test_charge_limit_enforces_stop(
    hass: HomeAssistant, setup_integration, mock_vehicle
):
    """When battery level reaches the limit, charging should stop exactly once."""
    entry_id = setup_integration.entry_id
    coordinator = hass.data[DOMAIN][entry_id][DATA_COORDINATOR]

    battery_mock = mock_vehicle.get_battery_status.return_value
    battery_mock.batteryLevel = 85  # above default limit of 80

    # First refresh — enforcement fires and issues one stop command
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert mock_vehicle.set_charge_stop.await_count == 1

    # Second refresh — car still reports chargingStatus as active (high latency)
    # The flag should prevent a second stop command
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert mock_vehicle.set_charge_stop.await_count == 1  # still only one call


async def test_charge_limit_re_arms_after_car_stops(
    hass: HomeAssistant, setup_integration, mock_vehicle
):
    """Flag clears when car confirms chargingStatus=0, re-arming enforcement."""
    entry_id = setup_integration.entry_id
    coordinator = hass.data[DOMAIN][entry_id][DATA_COORDINATOR]

    battery_mock = mock_vehicle.get_battery_status.return_value
    battery_mock.batteryLevel = 85

    # Stop issued
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert mock_vehicle.set_charge_stop.await_count == 1

    # Car confirms it stopped (chargingStatus = 0)
    battery_mock.chargingStatus = 0.0
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    # Flag cleared but car is now not charging → no new stop
    assert mock_vehicle.set_charge_stop.await_count == 1

    # User restarts charging manually
    battery_mock.chargingStatus = 1.0
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    # Enforcement re-armed and fires again
    assert mock_vehicle.set_charge_stop.await_count == 2


async def test_charge_limit_re_arms_after_car_reports_error_status(
    hass: HomeAssistant, setup_integration, mock_vehicle
):
    """chargingStatus=-1.0 (charge error) counts as stopped; flag clears immediately."""
    entry_id = setup_integration.entry_id
    coordinator = hass.data[DOMAIN][entry_id][DATA_COORDINATOR]

    battery_mock = mock_vehicle.get_battery_status.return_value
    battery_mock.batteryLevel = 85

    # Stop issued
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert mock_vehicle.set_charge_stop.await_count == 1

    # Car reports chargingStatus=-1.0 (charge error) rather than 0
    battery_mock.chargingStatus = -1.0
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    # Flag should clear — -1 counts as stopped, no retry
    assert mock_vehicle.set_charge_stop.await_count == 1

    # User restarts charging manually
    battery_mock.chargingStatus = 1.0
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert mock_vehicle.set_charge_stop.await_count == 2


async def test_charge_limit_does_not_stop_below_limit(
    hass: HomeAssistant, setup_integration, mock_vehicle
):
    """Charging should not be stopped when battery is below the limit."""
    entry_id = setup_integration.entry_id
    coordinator = hass.data[DOMAIN][entry_id][DATA_COORDINATOR]

    # batteryLevel=75 < default limit 80 → no stop
    mock_vehicle.get_battery_status.return_value.batteryLevel = 75

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    mock_vehicle.set_charge_stop.assert_not_awaited()


async def test_charge_limit_retries_after_timeout(
    hass: HomeAssistant, setup_integration, mock_vehicle
):
    """If the stop command was never acknowledged, retry after STOP_COMMAND_TIMEOUT."""
    entry_id = setup_integration.entry_id
    coordinator = hass.data[DOMAIN][entry_id][DATA_COORDINATOR]

    battery_mock = mock_vehicle.get_battery_status.return_value
    battery_mock.batteryLevel = 85

    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    t_expired = datetime(2026, 1, 1, 12, 11, 0, tzinfo=UTC)  # 11 min > 10 min timeout

    with patch("custom_components.dacia_spring_connect.number.datetime") as mock_dt:
        # First refresh at T=0: stop command issued, timestamp recorded
        mock_dt.now.return_value = t0
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert mock_vehicle.set_charge_stop.await_count == 1

        # Car still reports chargingStatus=1 (hasn't responded yet) at T+11min
        mock_dt.now.return_value = t_expired
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        # Timeout expired → warning logged → stop retried
        assert mock_vehicle.set_charge_stop.await_count == 2


async def test_charge_limit_raise_restarts_charging(
    hass: HomeAssistant, setup_integration, mock_vehicle
):
    """Raising the limit while the car is stopped-at-limit restarts charging automatically."""
    entry_id = setup_integration.entry_id
    coordinator = hass.data[DOMAIN][entry_id][DATA_COORDINATOR]

    battery_mock = mock_vehicle.get_battery_status.return_value
    battery_mock.batteryLevel = 80  # at the default 80% limit
    battery_mock.plugStatus = 1
    battery_mock.chargingStatus = 1.0

    # First refresh: 80 >= 80 limit → stop issued
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert mock_vehicle.set_charge_stop.await_count == 1

    # Car confirms it stopped
    battery_mock.chargingStatus = 0.0
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # User raises limit to 90 — battery (80) is now below new limit while cable
    # is connected and car is stopped → integration should restart charging
    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": f"number.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_charge_limit",
            "value": 90,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    mock_vehicle.set_charge_start.assert_awaited_once()


async def test_charge_limit_raise_no_restart_when_already_charging(
    hass: HomeAssistant, setup_integration, mock_vehicle
):
    """Raising the limit while the car is already charging should NOT send a start command."""
    battery_mock = mock_vehicle.get_battery_status.return_value
    battery_mock.batteryLevel = 70
    battery_mock.plugStatus = 1
    battery_mock.chargingStatus = 1.0  # already charging

    # Limit raised from 80 to 90 — car is already charging, no start needed
    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": f"number.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_charge_limit",
            "value": 90,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    mock_vehicle.set_charge_start.assert_not_awaited()


async def test_charge_limit_raise_no_restart_when_unplugged(
    hass: HomeAssistant, setup_integration, mock_vehicle
):
    """Raising the limit while the cable is unplugged should NOT send a start command."""
    battery_mock = mock_vehicle.get_battery_status.return_value
    battery_mock.batteryLevel = 70
    battery_mock.plugStatus = 0  # unplugged
    battery_mock.chargingStatus = 0.0

    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": f"number.dacia_spring_connect_{MOCK_VIN[-4:].lower()}_charge_limit",
            "value": 90,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    mock_vehicle.set_charge_start.assert_not_awaited()
