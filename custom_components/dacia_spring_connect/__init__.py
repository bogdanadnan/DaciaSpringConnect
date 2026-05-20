"""The Dacia Spring Connect integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_ACCOUNT_ID, CONF_LOCALE, CONF_SCAN_INTERVAL, CONF_VIN, DATA_COORDINATOR, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import DaciaSpringConnectCoordinator

_LOGGER = logging.getLogger(__name__)

# Renault rotated their Gigya API keys on 2026-05-20. renault-api==0.5.9 ships
# the fix, but HA may downgrade to 0.5.8 when the official Renault integration
# (which still pins 0.5.8 in HA ≤2026.5.3) is also enabled.  This patch applies
# the correct keys in-memory at import time so auth works regardless.
_GIGYA_EU_KEY = "3_VgdkgtIRH3AdHvJm-cjV2ug2EFE0lxt0IJzMC4MFqZjFpn_GYFXVdNZ19L7wZX0N"
_EU_LOCALES = frozenset({
    "bg_BG", "cs_CZ", "da_DK", "de_DE", "de_CH", "en_GB", "en_IE",
    "es_ES", "fi_FI", "fr_FR", "fr_BE", "fr_CH", "hr_HR", "hu_HU",
    "it_IT", "it_CH", "nl_NL", "nl_BE", "no_NO", "pl_PL", "pt_PT",
    "ro_RO", "ru_RU", "sk_SK", "sl_SI", "sv_SE",
})


def _patch_gigya_keys() -> None:
    try:
        import renault_api.const as _rc  # noqa: PLC0415
    except ImportError:
        return
    patched = [
        locale
        for locale in _EU_LOCALES
        if (entry := _rc.AVAILABLE_LOCALES.get(locale))
        and entry.get("gigya-api-key") != _GIGYA_EU_KEY
        and entry.update({"gigya-api-key": _GIGYA_EU_KEY}) is None  # side-effect
    ]
    if patched:
        _LOGGER.warning(
            "Patched stale Gigya API keys for %d locale(s): %s. "
            "renault-api<0.5.9 was installed (official Renault integration pins 0.5.8). "
            "Disable the official Renault integration or update HA to 2026.5.4+ to fix permanently.",
            len(patched),
            ", ".join(sorted(patched)),
        )


_patch_gigya_keys()

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.DEVICE_TRACKER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dacia Spring Connect from a config entry."""
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = DaciaSpringConnectCoordinator(
        hass=hass,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        locale=entry.data[CONF_LOCALE],
        account_id=entry.data[CONF_ACCOUNT_ID],
        vin=entry.data[CONF_VIN],
        scan_interval=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the entry whenever options are changed (e.g. scan interval)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        await entry_data[DATA_COORDINATOR].async_close_session()
    return unload_ok
