"""The IR Remote OTA integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UPDATE_CHECK_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONF_UPDATE_CHECK_INTERVAL,
)
from .coordinator import IRRemoteOTACoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IR Remote OTA from a config entry."""
    _LOGGER.debug("Setting up IR Remote OTA integration")

    # Get configuration
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    update_check_interval = entry.options.get(
        CONF_UPDATE_CHECK_INTERVAL, DEFAULT_UPDATE_CHECK_INTERVAL
    )

    # Create coordinator
    session = async_get_clientsession(hass)
    coordinator = IRRemoteOTACoordinator(hass, session, entry)

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass, coordinator)

    # Set up periodic updates
    async def _async_update_devices(_):
        """Update device discovery."""
        await coordinator.async_discover_devices()

    async def _async_check_updates(_):
        """Check for firmware updates."""
        await coordinator.async_check_firmware_updates()

    # Schedule device discovery
    async_track_time_interval(
        hass, _async_update_devices, timedelta(seconds=scan_interval)
    )

    # Schedule update checks
    async_track_time_interval(
        hass, _async_check_updates, timedelta(seconds=update_check_interval)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading IR Remote OTA integration")

    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    return unload_ok


async def _async_register_services(
    hass: HomeAssistant, coordinator: IRRemoteOTACoordinator
) -> None:
    """Register services for the integration."""
    from .services import async_register_services

    await async_register_services(hass, coordinator)
