"""Diagnostics support for Dacia Spring Connect."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DaciaSpringConnectCoordinator


def _safe_serialize(obj: Any) -> Any:
    """Recursively convert an API model object to a plain dict, masking nothing."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, "__dict__"):
        return {k: _safe_serialize(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    return repr(obj)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: DaciaSpringConnectCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    data = coordinator.data

    return {
        "entry": {
            "vin": coordinator._vin,
            "locale": coordinator._locale,
            "account_id": coordinator._account_id,
            "scan_interval_seconds": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": repr(coordinator.last_exception)
            if coordinator.last_exception
            else None,
        },
        "data": {
            "battery_status": _safe_serialize(data.battery_status) if data else None,
            "hvac_status": _safe_serialize(data.hvac_status) if data else None,
            "location": _safe_serialize(data.location) if data else None,
            "charge_mode": _safe_serialize(data.charge_mode) if data else None,
            "cockpit": _safe_serialize(data.cockpit) if data else None,
            "hvac_settings": _safe_serialize(data.hvac_settings) if data else None,
        },
    }
