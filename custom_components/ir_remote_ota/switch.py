"""Switch entities for IR Remote OTA integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IRRemoteOTACoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    coordinator: IRRemoteOTACoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Add OTA switch for each device
    for device_id, device in coordinator.devices.items():
        entities.append(IRRemoteOTASwitch(coordinator, device_id))

    async_add_entities(entities)


class IRRemoteOTASwitch(CoordinatorEntity, SwitchEntity):
    """OTA enable/disable switch."""

    def __init__(self, coordinator: IRRemoteOTACoordinator, device_id: str) -> None:
        """Initialize switch."""
        super().__init__(coordinator)
        self.device_id = device_id
        self._attr_has_entity_name = True
        self._attr_name = "OTA Enabled"
        self._attr_unique_id = f"{device_id}_ota_enabled"
        self._attr_icon = "mdi:upload"

    @property
    def device_info(self):
        """Return device info."""
        device = self.coordinator.devices.get(self.device_id)
        if not device:
            return None

        return {
            "identifiers": {(DOMAIN, device.unique_id)},
            "name": device.name,
            "manufacturer": "IRis",
            "model": "IR Remote Mini",
            "sw_version": device.firmware_version,
            "via_device": (DOMAIN, "coordinator"),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device = self.coordinator.devices.get(self.device_id)
        return super().available and device is not None and device.is_online

    @property
    def is_on(self) -> bool:
        """Return if OTA is enabled."""
        device = self.coordinator.devices.get(self.device_id)
        return device.ota_enabled if device else False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable OTA."""
        await self.coordinator.async_enable_ota(self.device_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable OTA."""
        await self.coordinator.async_disable_ota(self.device_id)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        device = self.coordinator.devices.get(self.device_id)
        if not device:
            return {}

        return {
            "device_ip": device.ip,
            "update_state": device.update_state,
            "available_update": device.available_update,
        }
