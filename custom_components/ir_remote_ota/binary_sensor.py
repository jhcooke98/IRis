"""Binary sensor entities for IR Remote OTA integration."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, UPDATE_STATE_IDLE
from .coordinator import IRRemoteOTACoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator: IRRemoteOTACoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Add binary sensors for each device
    for device_id, device in coordinator.devices.items():
        entities.extend([
            IRRemoteConnectivitySensor(coordinator, device_id),
            IRRemoteUpdateAvailableSensor(coordinator, device_id),
            IRRemoteUpdatingSensor(coordinator, device_id),
        ])

    async_add_entities(entities)


class IRRemoteBaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base binary sensor for IR Remote devices."""

    def __init__(self, coordinator: IRRemoteOTACoordinator, device_id: str) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator)
        self.device_id = device_id
        self._attr_has_entity_name = True

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


class IRRemoteConnectivitySensor(IRRemoteBaseBinarySensor):
    """Device connectivity binary sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator, device_id: str) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator, device_id)
        self._attr_name = "Connectivity"
        self._attr_unique_id = f"{device_id}_connectivity"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool:
        """Return if device is connected."""
        device = self.coordinator.devices.get(self.device_id)
        return device.is_online if device else False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device = self.coordinator.devices.get(self.device_id)
        return super().available and device is not None


class IRRemoteUpdateAvailableSensor(IRRemoteBaseBinarySensor):
    """Update available binary sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator, device_id: str) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator, device_id)
        self._attr_name = "Update Available"
        self._attr_unique_id = f"{device_id}_update_available"
        self._attr_device_class = BinarySensorDeviceClass.UPDATE
        self._attr_icon = "mdi:package-down"

    @property
    def is_on(self) -> bool:
        """Return if update is available."""
        device = self.coordinator.devices.get(self.device_id)
        return device.available_update is not None if device else False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device = self.coordinator.devices.get(self.device_id)
        return super().available and device is not None and device.is_online

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        device = self.coordinator.devices.get(self.device_id)
        if not device:
            return {}

        return {
            "current_version": device.firmware_version,
            "available_version": device.available_update,
        }


class IRRemoteUpdatingSensor(IRRemoteBaseBinarySensor):
    """Device updating binary sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator, device_id: str) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator, device_id)
        self._attr_name = "Updating"
        self._attr_unique_id = f"{device_id}_updating"
        self._attr_icon = "mdi:update"

    @property
    def is_on(self) -> bool:
        """Return if device is updating."""
        device = self.coordinator.devices.get(self.device_id)
        return device.update_state != UPDATE_STATE_IDLE if device else False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device = self.coordinator.devices.get(self.device_id)
        return super().available and device is not None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        device = self.coordinator.devices.get(self.device_id)
        if not device:
            return {}

        return {
            "update_state": device.update_state,
        }
