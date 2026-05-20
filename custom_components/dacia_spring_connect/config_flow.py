"""Config flow for Dacia Spring Connect integration."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol
from renault_api.renault_client import RenaultClient

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCOUNT_ID,
    CONF_LOCALE,
    CONF_SCAN_INTERVAL,
    CONF_VIN,
    DEFAULT_LOCALE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_LOCALE, default=DEFAULT_LOCALE): str,
    }
)


class DaciaSpringConnectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dacia Spring Connect."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise config flow."""
        self._username: str = ""
        self._password: str = ""
        self._locale: str = DEFAULT_LOCALE
        self._accounts: list[dict[str, str]] = []
        self._account_id: str = ""
        self._vehicles: list[dict[str, str]] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DaciaSpringConnectOptionsFlowHandler:
        """Return the options flow handler."""
        return DaciaSpringConnectOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: credential entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._locale = user_input.get(CONF_LOCALE, DEFAULT_LOCALE)

            try:
                websession = async_get_clientsession(self.hass)
                client = RenaultClient(websession=websession, locale=self._locale)
                await client.session.login(self._username, self._password)
                person = await client.get_person()
                self._accounts = [
                    {"id": acc.accountId, "type": acc.accountType}
                    for acc in (person.accounts or [])
                    if acc.accountId
                ]
                if not self._accounts:
                    errors["base"] = "no_accounts"
                else:
                    return await self.async_step_account()
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_account(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle account selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._account_id = user_input[CONF_ACCOUNT_ID]
            try:
                websession = async_get_clientsession(self.hass)
                client = RenaultClient(websession=websession, locale=self._locale)
                await client.session.login(self._username, self._password)
                account = await client.get_api_account(self._account_id)
                vehicles_response = await account.get_vehicles()
                self._vehicles = [
                    {"vin": v.vin, "label": f"{v.vin}"}
                    for v in (vehicles_response.vehicleLinks or [])
                    if v.vin
                ]
                if not self._vehicles:
                    errors["base"] = "no_vehicles"
                else:
                    return await self.async_step_vehicle()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error fetching vehicles")
                errors["base"] = "unknown"

        account_options = {
            acc["id"]: f"{acc['id']} ({acc['type']})"
            for acc in self._accounts
        }
        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(
                {vol.Required(CONF_ACCOUNT_ID): vol.In(account_options)}
            ),
            errors=errors,
        )

    async def async_step_vehicle(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle vehicle selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            vin = user_input[CONF_VIN]
            await self.async_set_unique_id(vin)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Dacia Spring Connect ({vin})",
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_LOCALE: self._locale,
                    CONF_ACCOUNT_ID: self._account_id,
                    CONF_VIN: vin,
                },
            )

        vehicle_options = {v["vin"]: v["label"] for v in self._vehicles}
        return self.async_show_form(
            step_id="vehicle",
            data_schema=vol.Schema(
                {vol.Required(CONF_VIN): vol.In(vehicle_options)}
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Initiate re-authentication when credentials become invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-authentication with new credentials."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                websession = async_get_clientsession(self.hass)
                client = RenaultClient(
                    websession=websession,
                    locale=reauth_entry.data[CONF_LOCALE],
                )
                await client.session.login(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    reason="reauth_successful",
                )
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during re-authentication")
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=reauth_entry.data[CONF_USERNAME]): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )


class DaciaSpringConnectOptionsFlowHandler(OptionsFlow):
    """Handle options for Dacia Spring Connect (scan interval)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)
                    ),
                }
            ),
        )
