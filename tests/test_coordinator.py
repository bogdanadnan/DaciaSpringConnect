"""Tests for the Dacia Spring Connect coordinator."""
from __future__ import annotations

import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.dacia_spring_connect.coordinator import DaciaSpringConnectCoordinator

from .conftest import MOCK_ACCOUNT_ID, MOCK_LOCALE, MOCK_PASSWORD, MOCK_USERNAME, MOCK_VIN


@pytest.fixture
def coordinator(hass):
    """Create a bare coordinator without touching the Renault API."""
    session = MagicMock(spec=aiohttp.ClientSession)
    return DaciaSpringConnectCoordinator(
        hass=hass,
        websession=session,
        username=MOCK_USERNAME,
        password=MOCK_PASSWORD,
        locale=MOCK_LOCALE,
        account_id=MOCK_ACCOUNT_ID,
        vin=MOCK_VIN,
    )


async def test_coordinator_setup(coordinator, mock_renault_client, mock_vehicle):
    """Test that _async_setup authenticates and stores the vehicle."""
    await coordinator._async_setup()

    mock_renault_client.return_value.session.login.assert_awaited_once_with(
        MOCK_USERNAME, MOCK_PASSWORD
    )
    assert coordinator.vehicle is mock_vehicle


async def test_coordinator_update(coordinator, mock_vehicle):
    """Test that _async_update_data populates all DaciaSpringConnectData fields."""
    coordinator.vehicle = mock_vehicle

    data = await coordinator._async_update_data()

    assert data.battery_status.batteryLevel == 75
    assert data.battery_status.batteryAutonomy == 180
    assert data.hvac_status.hvacStatus == "off"
    assert data.location.gpsLatitude == 48.8566
    assert data.cockpit.totalMileage == 12500.0


async def test_coordinator_token_refresh_on_401(coordinator, mock_vehicle):
    """Test that a 401 response triggers token refresh and retries."""
    coordinator.vehicle = mock_vehicle

    # First call raises 401, second call (after re-auth) succeeds
    auth_error = aiohttp.ClientResponseError(request_info=MagicMock(), history=())
    auth_error.status = 401
    mock_vehicle.get_battery_status.side_effect = [auth_error, mock_vehicle.get_battery_status.return_value]

    with patch.object(coordinator, "_async_reauthenticate", new=AsyncMock()) as mock_reauth:
        # Remove side_effect after first call so the retry fetch works
        async def reset_side_effect():
            mock_vehicle.get_battery_status.side_effect = None

        mock_reauth.side_effect = reset_side_effect
        data = await coordinator._async_update_data()

    mock_reauth.assert_awaited_once()
    assert data is not None


async def test_coordinator_raises_auth_failed_on_persistent_401(coordinator, mock_vehicle):
    """Test that persistent 401 after re-auth raises ConfigEntryAuthFailed."""
    coordinator.vehicle = mock_vehicle

    auth_error = aiohttp.ClientResponseError(request_info=MagicMock(), history=())
    auth_error.status = 401
    mock_vehicle.get_battery_status.side_effect = auth_error

    with patch.object(coordinator, "_async_reauthenticate", new=AsyncMock()):
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()
