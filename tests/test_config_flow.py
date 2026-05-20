"""Tests for the Dacia Spring Connect config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.dacia_spring_connect.const import (
    CONF_ACCOUNT_ID,
    CONF_LOCALE,
    CONF_SCAN_INTERVAL,
    CONF_VIN,
    DEFAULT_LOCALE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

from .conftest import MOCK_ACCOUNT_ID, MOCK_PASSWORD, MOCK_USERNAME, MOCK_VIN


@pytest.fixture(autouse=True)
def mock_create_session():
    """Prevent create_renault_session from opening real sockets during tests."""
    fake_session = MagicMock()
    fake_session.closed = False
    fake_session.close = AsyncMock()
    with patch(
        "custom_components.dacia_spring_connect.config_flow.create_renault_session",
        return_value=fake_session,
    ), patch(
        "custom_components.dacia_spring_connect.coordinator.create_renault_session",
        return_value=fake_session,
    ):
        yield fake_session


def _mock_person():
    person = MagicMock()
    account = MagicMock()
    account.accountId = MOCK_ACCOUNT_ID
    account.accountType = "MYRENAULT"
    person.accounts = [account]
    return person


def _mock_vehicles():
    response = MagicMock()
    vehicle = MagicMock()
    vehicle.vin = MOCK_VIN
    response.vehicleLinks = [vehicle]
    return response


@pytest.fixture
def mock_config_flow_client():
    """Patch RenaultClient inside config_flow and coordinator for the full flow.

    Also patches coordinator.RenaultClient so the entry-setup task that HA
    schedules after async_create_entry completes doesn't open real sockets.
    """
    mock_coord_client = MagicMock()
    mock_coord_client.session.login = AsyncMock()
    mock_coord_account = AsyncMock()
    mock_coord_account.get_api_vehicle = AsyncMock(return_value=AsyncMock())
    mock_coord_client.get_api_account = AsyncMock(return_value=mock_coord_account)
    with patch(
        "custom_components.dacia_spring_connect.coordinator.RenaultClient",
        return_value=mock_coord_client,
    ), patch(
        "custom_components.dacia_spring_connect.config_flow.RenaultClient", autospec=True
    ) as mock_cls:
        client = mock_cls.return_value
        client.session.login = AsyncMock()
        client.get_person = AsyncMock(return_value=_mock_person())
        account = AsyncMock()
        account.get_vehicles = AsyncMock(return_value=_mock_vehicles())
        client.get_api_account = AsyncMock(return_value=account)
        yield mock_cls


async def test_full_config_flow(hass: HomeAssistant, mock_config_flow_client):
    """Test a complete successful config flow creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD, CONF_LOCALE: DEFAULT_LOCALE},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "account"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ACCOUNT_ID: MOCK_ACCOUNT_ID}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "vehicle"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_VIN: MOCK_VIN}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Dacia Spring Connect ({MOCK_VIN})"
    assert result["data"][CONF_VIN] == MOCK_VIN
    assert result["data"][CONF_USERNAME] == MOCK_USERNAME


async def test_config_flow_bad_credentials(hass: HomeAssistant):
    """Test that a connection error at login shows 'cannot_connect'."""
    import aiohttp

    with patch(
        "custom_components.dacia_spring_connect.config_flow.RenaultClient", autospec=True
    ) as mock_cls:
        mock_cls.return_value.session.login.side_effect = aiohttp.ClientError()
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: "wrong", CONF_LOCALE: DEFAULT_LOCALE},
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_options_flow(hass: HomeAssistant, setup_integration):
    """Test that the options flow saves a custom scan interval."""
    entry = setup_integration

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 120}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SCAN_INTERVAL] == 120

