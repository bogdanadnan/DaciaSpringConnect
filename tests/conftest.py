"""Shared test fixtures for Dacia Spring Connect integration tests."""
from __future__ import annotations

import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.dacia_spring_connect.const import (
    CONF_ACCOUNT_ID,
    CONF_LOCALE,
    CONF_VIN,
    DATA_COORDINATOR,
    DOMAIN,
)

# ---------------------------------------------------------------------------
# Register the PHCC plugin so all HA fixtures (hass, etc.) are available
# ---------------------------------------------------------------------------
pytest_plugins = "pytest_homeassistant_custom_component"

# Project root (contains custom_components/)
_PROJECT_ROOT = str(pathlib.Path(__file__).parent.parent)


# ---------------------------------------------------------------------------
# Tell HA where to find custom components and enable loading them
# ---------------------------------------------------------------------------

@pytest.fixture
def hass_config_dir():
    """Point HA's config directory at the project root so it finds custom_components."""
    return _PROJECT_ROOT


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Automatically enable custom integration discovery for every test."""
    return


# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------
MOCK_USERNAME = "test@example.com"
MOCK_PASSWORD = "secret"
MOCK_LOCALE = "fr_FR"
MOCK_ACCOUNT_ID = "acc_123"
MOCK_VIN = "VF1AAAAAAA0000001"


# ---------------------------------------------------------------------------
# API response helpers
# ---------------------------------------------------------------------------

def _make_battery_status() -> MagicMock:
    m = MagicMock()
    m.batteryLevel = 75
    m.batteryAutonomy = 180
    m.batteryAvailableEnergy = 18.5
    m.chargingInstantaneousPower = 3700
    m.chargingRemainingTime = 65
    m.plugStatus = 1
    m.chargingStatus = MagicMock()
    m.chargingStatus.name = "CHARGE_IN_PROGRESS"
    return m


def _make_hvac_status() -> MagicMock:
    m = MagicMock()
    m.hvacStatus = "off"
    m.externalTemperature = 18.5
    return m


def _make_location() -> MagicMock:
    m = MagicMock()
    m.gpsLatitude = 48.8566
    m.gpsLongitude = 2.3522
    return m


def _make_charge_mode() -> MagicMock:
    m = MagicMock()
    m.chargeMode = "always"
    return m


def _make_cockpit() -> MagicMock:
    m = MagicMock()
    m.totalMileage = 12500.0
    return m


def _make_hvac_settings() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_vehicle() -> AsyncMock:
    """Return a mocked RenaultVehicle with realistic responses."""
    vehicle = AsyncMock()
    vehicle.get_battery_status = AsyncMock(return_value=_make_battery_status())
    vehicle.get_hvac_status = AsyncMock(return_value=_make_hvac_status())
    vehicle.get_location = AsyncMock(return_value=_make_location())
    vehicle.get_charge_mode = AsyncMock(return_value=_make_charge_mode())
    vehicle.get_cockpit = AsyncMock(return_value=_make_cockpit())
    vehicle.get_hvac_settings = AsyncMock(return_value=_make_hvac_settings())
    vehicle.set_ac_start = AsyncMock()
    vehicle.set_ac_stop = AsyncMock()
    vehicle.set_charge_mode = AsyncMock()
    vehicle.set_charge_start = AsyncMock()
    vehicle.set_charge_stop = AsyncMock()
    vehicle.refresh_location = AsyncMock()
    return vehicle


@pytest.fixture
def mock_renault_client(mock_vehicle: AsyncMock):
    """Patch RenaultClient in the coordinator module."""
    with patch(
        "custom_components.dacia_spring_connect.coordinator.RenaultClient", autospec=True
    ) as mock_cls:
        client = mock_cls.return_value
        client.session.login = AsyncMock()
        account = AsyncMock()
        account.get_api_vehicle = AsyncMock(return_value=mock_vehicle)
        client.get_api_account = AsyncMock(return_value=account)
        yield mock_cls


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return an unconfigured MockConfigEntry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_VIN,
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_LOCALE: MOCK_LOCALE,
            CONF_ACCOUNT_ID: MOCK_ACCOUNT_ID,
            CONF_VIN: MOCK_VIN,
        },
    )


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_renault_client,
) -> MockConfigEntry:
    """Add the config entry to hass and fully set up the integration."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
