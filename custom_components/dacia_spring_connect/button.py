"""Button platform for Dacia Spring Connect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DaciaSpringConnectCoordinator
from .entity import DaciaSpringConnectEntity


@dataclass(frozen=True, kw_only=True)
class DaciaSpringConnectButtonDescription(ButtonEntityDescription):
    """Describes a Dacia Spring Connect button."""

    press_fn: Any = None


BUTTON_DESCRIPTIONS: tuple[DaciaSpringConnectButtonDescription, ...] = (
    DaciaSpringConnectButtonDescription(
        key="charge_start",
        translation_key="charge_start",
        press_fn=lambda coordinator: coordinator.async_charge_start(),
    ),
    DaciaSpringConnectButtonDescription(
        key="charge_stop",
        translation_key="charge_stop",
        press_fn=lambda coordinator: coordinator.async_charge_stop(),
    ),
    DaciaSpringConnectButtonDescription(
        key="refresh_location",
        translation_key="refresh_location",
        press_fn=lambda coordinator: coordinator.async_refresh_location(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dacia Spring Connect buttons."""
    coordinator: DaciaSpringConnectCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        DaciaSpringConnectButton(coordinator, description)
        for description in BUTTON_DESCRIPTIONS
    )


class DaciaSpringConnectButton(DaciaSpringConnectEntity, ButtonEntity):
    """Button entity for Dacia Spring Connect actions."""

    entity_description: DaciaSpringConnectButtonDescription

    def __init__(
        self,
        coordinator: DaciaSpringConnectCoordinator,
        description: DaciaSpringConnectButtonDescription,
    ) -> None:
        """Initialise the button."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Execute the button action."""
        await self.entity_description.press_fn(self.coordinator)
