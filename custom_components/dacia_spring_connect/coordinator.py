"""Data update coordinator for Dacia Spring Connect."""
from __future__ import annotations

import logging
import ssl
from datetime import timedelta
from typing import Any

import aiohttp

try:
    import certifi
    _SSL_CONTEXT: ssl.SSLContext = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # pragma: no cover
    _SSL_CONTEXT = ssl.create_default_context()


def create_renault_session() -> aiohttp.ClientSession:
    """Create a dedicated aiohttp session with certifi SSL for the Renault API."""
    connector = aiohttp.TCPConnector(ssl=_SSL_CONTEXT)
    return aiohttp.ClientSession(connector=connector)
from renault_api.renault_account import RenaultAccount
from renault_api.renault_client import RenaultClient
from renault_api.renault_vehicle import RenaultVehicle

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

_AUTH_STATUSES = frozenset({401, 403})


class DaciaSpringConnectData:
    """Container for data fetched from the Renault API."""

    def __init__(self) -> None:
        """Initialise the data container."""
        self.battery_status: Any = None
        self.hvac_status: Any = None
        self.location: Any = None
        self.charge_mode: Any = None
        self.cockpit: Any = None
        self.hvac_settings: Any = None


class DaciaSpringConnectCoordinator(DataUpdateCoordinator[DaciaSpringConnectData]):
    """Coordinator to manage fetching data from the Renault API."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        locale: str,
        account_id: str,
        vin: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        websession: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        if websession is None:
            self._websession = create_renault_session()
            self._owns_session = True
        else:
            self._websession = websession
            self._owns_session = False
        self._username = username
        self._password = password
        self._locale = locale
        self._account_id = account_id
        self._vin = vin
        self._client: RenaultClient | None = None
        self.vehicle: RenaultVehicle | None = None

    async def _async_setup(self) -> None:
        """Authenticate and initialise vehicle object."""
        self._client = RenaultClient(
            websession=self._websession,
            locale=self._locale,
        )
        await self._client.session.login(self._username, self._password)
        account: RenaultAccount = await self._client.get_api_account(self._account_id)
        self.vehicle = await account.get_api_vehicle(self._vin)

    async def _async_reauthenticate(self) -> None:
        """Re-authenticate to refresh an expired session token."""
        if self._client is None:
            await self._async_setup()
            return
        await self._client.session.login(self._username, self._password)

    async def _async_fetch_all_data(
        self, previous: DaciaSpringConnectData | None = None
    ) -> DaciaSpringConnectData:
        """Fetch every vehicle endpoint; propagates auth errors, keeps last value on transient failures."""
        data = DaciaSpringConnectData()
        # Pre-populate with the previous values so a transient failure on one
        # endpoint doesn't wipe out its last-known state.
        if previous is not None:
            data.battery_status = previous.battery_status
            data.hvac_status = previous.hvac_status
            data.location = previous.location
            data.charge_mode = previous.charge_mode
            data.cockpit = previous.cockpit
            data.hvac_settings = previous.hvac_settings

        endpoints: list[tuple[str, Any, str]] = [
            ("battery_status", self.vehicle.get_battery_status, "battery status"),
            ("hvac_status", self.vehicle.get_hvac_status, "HVAC status"),
            ("location", self.vehicle.get_location, "location"),
            ("charge_mode", self.vehicle.get_charge_mode, "charge mode"),
            ("cockpit", self.vehicle.get_cockpit, "cockpit"),
            ("hvac_settings", self.vehicle.get_hvac_settings, "HVAC settings"),
        ]
        for attr, getter, label in endpoints:
            try:
                setattr(data, attr, await getter())
            except aiohttp.ClientResponseError as err:
                if err.status in _AUTH_STATUSES:
                    raise  # propagate to trigger reauthentication
                _LOGGER.warning(
                    "Transient error fetching %s (HTTP %s), keeping last known value",
                    label, err.status,
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Could not fetch %s: %s", label, err)
        return data

    async def _async_update_data(self) -> DaciaSpringConnectData:
        """Fetch all vehicle data, refreshing the token automatically on auth failure."""
        if self.vehicle is None:
            try:
                await self._async_setup()
            except aiohttp.ClientResponseError as err:
                if err.status in _AUTH_STATUSES:
                    raise ConfigEntryAuthFailed(
                        "Invalid Renault credentials"
                    ) from err
                raise UpdateFailed(str(err)) from err

        try:
            return await self._async_fetch_all_data(self.data)
        except aiohttp.ClientResponseError as err:
            if err.status not in _AUTH_STATUSES:
                raise UpdateFailed(str(err)) from err
            _LOGGER.debug("Auth error (%s), attempting token refresh", err.status)
            try:
                await self._async_reauthenticate()
                return await self._async_fetch_all_data(self.data)
            except aiohttp.ClientResponseError as reauth_err:
                if reauth_err.status in _AUTH_STATUSES:
                    raise ConfigEntryAuthFailed(
                        "Renault account credentials are no longer valid. Please re-authenticate."
                    ) from reauth_err
                raise UpdateFailed(str(reauth_err)) from reauth_err
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    async def async_close_session(self) -> None:
        """Close the aiohttp session if it was created by this coordinator."""
        if self._owns_session and not self._websession.closed:
            await self._websession.close()

    async def async_set_hvac(self, action: str, temperature: float | None = None) -> None:
        """Send HVAC command to the vehicle."""
        if action == "start":
            if temperature is None:
                temperature = 21.0
            await self.vehicle.set_ac_start(temperature)
        elif action == "stop":
            await self.vehicle.set_ac_stop()
        await self.async_request_refresh()

    async def async_set_charge_mode(self, charge_mode: str) -> None:
        """Set the vehicle charge mode."""
        await self.vehicle.set_charge_mode(charge_mode)
        await self.async_request_refresh()

    async def async_charge_start(self) -> None:
        """Start vehicle charging."""
        await self.vehicle.set_charge_start()
        await self.async_request_refresh()

    async def async_charge_stop(self) -> None:
        """Stop vehicle charging."""
        await self.vehicle.set_charge_stop()
        await self.async_request_refresh()

    async def async_refresh_location(self) -> None:
        """Request a fresh GPS location from the vehicle."""
        await self.vehicle.refresh_location()
        await self.async_request_refresh()
