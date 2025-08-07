"""Services for IR Remote OTA integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_UPDATE_DEVICE,
    SERVICE_UPDATE_ALL_DEVICES,
    SERVICE_CHECK_UPDATES,
    SERVICE_ENABLE_OTA,
    SERVICE_DISABLE_OTA,
    SERVICE_SYNC_GITHUB,
    ATTR_DEVICE_ID,
    ATTR_FIRMWARE_FILE,
    ATTR_EXCLUDE_DEVICES,
    ATTR_FORCE_UPDATE,
)
from .coordinator import IRRemoteOTACoordinator

_LOGGER = logging.getLogger(__name__)

UPDATE_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_FIRMWARE_FILE): cv.string,
        vol.Optional(ATTR_FORCE_UPDATE, default=False): cv.boolean,
    }
)

UPDATE_ALL_DEVICES_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_FIRMWARE_FILE): cv.string,
        vol.Optional(ATTR_EXCLUDE_DEVICES, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_FORCE_UPDATE, default=False): cv.boolean,
    }
)

ENABLE_OTA_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
    }
)

DISABLE_OTA_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
    }
)


async def async_register_services(
    hass: HomeAssistant, coordinator: IRRemoteOTACoordinator
) -> None:
    """Register services for the integration."""

    async def async_update_device(call: ServiceCall) -> None:
        """Update a specific device."""
        device_id = call.data[ATTR_DEVICE_ID]
        firmware_file = call.data.get(ATTR_FIRMWARE_FILE)
        
        _LOGGER.info("Service call: Update device %s", device_id)
        
        success = await coordinator.async_update_device(device_id, firmware_file)
        
        if success:
            _LOGGER.info("Successfully started update for device %s", device_id)
        else:
            _LOGGER.error("Failed to start update for device %s", device_id)

    async def async_update_all_devices(call: ServiceCall) -> None:
        """Update all devices."""
        firmware_file = call.data.get(ATTR_FIRMWARE_FILE)
        exclude_devices = call.data.get(ATTR_EXCLUDE_DEVICES, [])
        
        _LOGGER.info("Service call: Update all devices")
        
        results = await coordinator.async_update_all_devices(firmware_file, exclude_devices)
        
        success_count = sum(1 for result in results.values() if result)
        total_count = len(results)
        
        _LOGGER.info(
            "Update all devices completed: %d/%d successful", success_count, total_count
        )

    async def async_check_updates(call: ServiceCall) -> None:
        """Check for firmware updates."""
        _LOGGER.info("Service call: Check for updates")
        
        await coordinator.async_check_firmware_updates()
        await coordinator.async_request_refresh()

    async def async_enable_ota(call: ServiceCall) -> None:
        """Enable OTA for a device."""
        device_id = call.data[ATTR_DEVICE_ID]
        
        _LOGGER.info("Service call: Enable OTA for device %s", device_id)
        
        success = await coordinator.async_enable_ota(device_id)
        
        if success:
            _LOGGER.info("Successfully enabled OTA for device %s", device_id)
        else:
            _LOGGER.error("Failed to enable OTA for device %s", device_id)

    async def async_disable_ota(call: ServiceCall) -> None:
        """Disable OTA for a device."""
        device_id = call.data[ATTR_DEVICE_ID]
        
        _LOGGER.info("Service call: Disable OTA for device %s", device_id)
        
        success = await coordinator.async_disable_ota(device_id)
        
        if success:
            _LOGGER.info("Successfully disabled OTA for device %s", device_id)
        else:
            _LOGGER.error("Failed to disable OTA for device %s", device_id)

    async def async_sync_github_firmware(call: ServiceCall) -> None:
        """Sync firmware from GitHub repository."""
        _LOGGER.info("Service call: Sync GitHub firmware")
        
        if coordinator.github_manager:
            try:
                # Invalidate cache to force fresh check
                coordinator.github_manager.invalidate_cache()
                
                # Sync firmware
                await coordinator.async_check_firmware_updates()
                await coordinator.async_request_refresh()
                
                _LOGGER.info("Successfully synced firmware from GitHub")
            except Exception as err:
                _LOGGER.error("Failed to sync GitHub firmware: %s", err)
        else:
            _LOGGER.warning("GitHub manager not configured")

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_DEVICE,
        async_update_device,
        schema=UPDATE_DEVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_ALL_DEVICES,
        async_update_all_devices,
        schema=UPDATE_ALL_DEVICES_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_UPDATES,
        async_check_updates,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE_OTA,
        async_enable_ota,
        schema=ENABLE_OTA_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DISABLE_OTA,
        async_disable_ota,
        schema=DISABLE_OTA_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_GITHUB,
        async_sync_github_firmware,
    )
