"""Sensor entities for IR Remote OTA integration."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IRRemoteOTACoordinator, DeviceInfo

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: IRRemoteOTACoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Add sensors for each device
    for device_id, device in coordinator.devices.items():
        entities.extend([
            IRRemoteFirmwareVersionSensor(coordinator, device_id),
            IRRemoteStatusSensor(coordinator, device_id),
            IRRemoteFreeMemorySensor(coordinator, device_id),
            IRRemoteUptimeSensor(coordinator, device_id),
            IRRemoteUpdateStateSensor(coordinator, device_id),
        ])

    # Add global sensors
    entities.extend([
        IRRemoteDeviceCountSensor(coordinator),
        IRRemoteLatestFirmwareSensor(coordinator),
        IRRemoteUpdatesAvailableSensor(coordinator),
    ])

    async_add_entities(entities)


class IRRemoteBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for IR Remote devices."""

    def __init__(self, coordinator: IRRemoteOTACoordinator, device_id: str) -> None:
        """Initialize sensor."""
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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device = self.coordinator.devices.get(self.device_id)
        return super().available and device is not None and device.is_online


class IRRemoteFirmwareVersionSensor(IRRemoteBaseSensor):
    """Firmware version sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator, device_id: str) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, device_id)
        self._attr_name = "Firmware Version"
        self._attr_unique_id = f"{device_id}_firmware_version"
        self._attr_icon = "mdi:chip"

    @property
    def native_value(self) -> str | None:
        """Return firmware version."""
        device = self.coordinator.devices.get(self.device_id)
        return device.firmware_version if device else None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        device = self.coordinator.devices.get(self.device_id)
        if not device:
            return {}

        return {
            "available_update": device.available_update,
            "has_update": device.available_update is not None,
        }


class IRRemoteStatusSensor(IRRemoteBaseSensor):
    """Device status sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator, device_id: str) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, device_id)
        self._attr_name = "Status"
        self._attr_unique_id = f"{device_id}_status"
        self._attr_icon = "mdi:wifi"

    @property
    def native_value(self) -> str:
        """Return device status."""
        device = self.coordinator.devices.get(self.device_id)
        if not device:
            return "unknown"

        return "online" if device.is_online else "offline"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        device = self.coordinator.devices.get(self.device_id)
        if not device:
            return {}

        return {
            "ip_address": device.ip,
            "mac_address": device.mac_address,
            "hostname": device.hostname,
            "last_seen": device.last_seen.isoformat(),
            "ota_enabled": device.ota_enabled,
        }


class IRRemoteFreeMemorySensor(IRRemoteBaseSensor):
    """Free memory sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator, device_id: str) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, device_id)
        self._attr_name = "Free Memory"
        self._attr_unique_id = f"{device_id}_free_memory"
        self._attr_native_unit_of_measurement = "bytes"
        self._attr_device_class = SensorDeviceClass.DATA_SIZE
        self._attr_icon = "mdi:memory"

    @property
    def native_value(self) -> int | None:
        """Return free memory."""
        device = self.coordinator.devices.get(self.device_id)
        return device.free_heap if device else None


class IRRemoteUptimeSensor(IRRemoteBaseSensor):
    """Uptime sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator, device_id: str) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, device_id)
        self._attr_name = "Uptime"
        self._attr_unique_id = f"{device_id}_uptime"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> datetime | None:
        """Return uptime timestamp."""
        device = self.coordinator.devices.get(self.device_id)
        return device.last_seen if device else None


class IRRemoteUpdateStateSensor(IRRemoteBaseSensor):
    """Update state sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator, device_id: str) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, device_id)
        self._attr_name = "Update State"
        self._attr_unique_id = f"{device_id}_update_state"
        self._attr_icon = "mdi:update"

    @property
    def native_value(self) -> str | None:
        """Return update state."""
        device = self.coordinator.devices.get(self.device_id)
        return device.update_state if device else None


class IRRemoteGlobalSensor(CoordinatorEntity, SensorEntity):
    """Base global sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, "coordinator")},
            "name": "IR Remote OTA Coordinator",
            "manufacturer": "IRis",
            "model": "OTA Manager",
            "sw_version": "1.0.0",
        }


class IRRemoteDeviceCountSensor(IRRemoteGlobalSensor):
    """Device count sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self._attr_name = "Device Count"
        self._attr_unique_id = "ir_remote_device_count"
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self) -> int:
        """Return device count."""
        return len(self.coordinator.devices)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        online_count = sum(1 for device in self.coordinator.devices.values() if device.is_online)
        return {
            "online_devices": online_count,
            "offline_devices": len(self.coordinator.devices) - online_count,
        }


class IRRemoteLatestFirmwareSensor(IRRemoteGlobalSensor):
    """Latest firmware sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self._attr_name = "Latest Firmware"
        self._attr_unique_id = "ir_remote_latest_firmware"
        self._attr_icon = "mdi:package-down"

    @property
    def native_value(self) -> str | None:
        """Return latest firmware version."""
        return self.coordinator.firmware_versions.get("latest")


class IRRemoteUpdatesAvailableSensor(IRRemoteGlobalSensor):
    """Updates available sensor."""

    def __init__(self, coordinator: IRRemoteOTACoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self._attr_name = "Updates Available"
        self._attr_unique_id = "ir_remote_updates_available"
        self._attr_icon = "mdi:download"

    @property
    def native_value(self) -> int:
        """Return number of devices with updates available."""
        return sum(
            1 for device in self.coordinator.devices.values()
            if device.available_update is not None
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        devices_with_updates = [
            device.name for device in self.coordinator.devices.values()
            if device.available_update is not None
        ]
        return {
            "devices_with_updates": devices_with_updates,
        }
