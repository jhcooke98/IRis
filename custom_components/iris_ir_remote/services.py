"""Services for IRis IR Remote integration."""
import asyncio
import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import verify_domain_control

from .const import DOMAIN
from .coordinator import IRisDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_BUTTON = "send_button"
SERVICE_START_LEARNING = "start_learning"
SERVICE_STOP_LEARNING = "stop_learning"
SERVICE_RESTART_DEVICE = "restart_device"
SERVICE_OPEN_WEB_UI = "open_web_ui"

SERVICE_SEND_BUTTON_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("button"): cv.string,
    }
)

SERVICE_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
    }
)


async def _delayed_refresh(coordinator: IRisDataUpdateCoordinator, delay: int) -> None:
    """Refresh coordinator after a delay (for device restarts)."""
    await asyncio.sleep(delay)
    await coordinator.async_request_refresh()


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for IRis IR Remote integration."""

    async def async_send_button(call: ServiceCall) -> None:
        """Send a button command to the device."""
        entity_id = call.data["entity_id"]
        button = call.data["button"]
        
        coordinator = _get_coordinator_from_entity_id(hass, entity_id)
        if coordinator:
            success = await coordinator.send_button_command(button)
            if success:
                _LOGGER.info("Sent button command '%s' to %s", button, coordinator.host)
                # Force immediate refresh after sending command
                await coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to send button command '%s' to %s", button, coordinator.host)

    async def async_start_learning(call: ServiceCall) -> None:
        """Start learning mode on the device."""
        entity_id = call.data["entity_id"]
        
        coordinator = _get_coordinator_from_entity_id(hass, entity_id)
        if coordinator:
            success = await coordinator.start_learning_mode()
            if success:
                _LOGGER.info("Started learning mode on %s", coordinator.host)
                # Force immediate refresh after state change
                await coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to start learning mode on %s", coordinator.host)

    async def async_stop_learning(call: ServiceCall) -> None:
        """Stop learning mode on the device."""
        entity_id = call.data["entity_id"]
        
        coordinator = _get_coordinator_from_entity_id(hass, entity_id)
        if coordinator:
            success = await coordinator.stop_learning_mode()
            if success:
                _LOGGER.info("Stopped learning mode on %s", coordinator.host)
                # Force immediate refresh after state change
                await coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to stop learning mode on %s", coordinator.host)

    async def async_restart_device(call: ServiceCall) -> None:
        """Restart the device."""
        entity_id = call.data["entity_id"]
        
        coordinator = _get_coordinator_from_entity_id(hass, entity_id)
        if coordinator:
            success = await coordinator.restart_device()
            if success:
                _LOGGER.info("Restarted device %s", coordinator.host)
                # Give device time to restart, then refresh
                hass.async_create_task(_delayed_refresh(coordinator, 10))
            else:
                _LOGGER.error("Failed to restart device %s", coordinator.host)

    async def async_open_web_ui(call: ServiceCall) -> None:
        """Open the device's web UI."""
        entity_id = call.data["entity_id"]
        
        coordinator = _get_coordinator_from_entity_id(hass, entity_id)
        if coordinator:
            _LOGGER.info("Web UI for %s is available at: %s", coordinator.host, coordinator.base_url)
            # In a real implementation, you might want to create a persistent notification
            # or emit an event that the frontend can use to open a new tab
            hass.bus.async_fire(
                "iris_ir_remote_web_ui_request",
                {"url": coordinator.base_url, "host": coordinator.host}
            )

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_BUTTON,
        async_send_button,
        schema=SERVICE_SEND_BUTTON_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_LEARNING,
        async_start_learning,
        schema=SERVICE_DEVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_LEARNING,
        async_stop_learning,
        schema=SERVICE_DEVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTART_DEVICE,
        async_restart_device,
        schema=SERVICE_DEVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_OPEN_WEB_UI,
        async_open_web_ui,
        schema=SERVICE_DEVICE_SCHEMA,
    )


def _get_coordinator_from_entity_id(hass: HomeAssistant, entity_id: str) -> IRisDataUpdateCoordinator | None:
    """Get coordinator from entity ID."""
    # Try to extract the coordinator from entity registry
    entity_registry = hass.helpers.entity_registry.async_get(hass)
    entity_entry = entity_registry.async_get(entity_id)
    
    if not entity_entry:
        _LOGGER.error("Entity %s not found", entity_id)
        return None
    
    config_entry_id = entity_entry.config_entry_id
    if config_entry_id and config_entry_id in hass.data.get(DOMAIN, {}):
        return hass.data[DOMAIN][config_entry_id]
    
    # Fallback: try to find coordinator by searching all entries
    _LOGGER.debug("Trying fallback coordinator lookup for entity %s", entity_id)
    for coordinator in hass.data.get(DOMAIN, {}).values():
        if isinstance(coordinator, IRisDataUpdateCoordinator):
            # Check if this entity belongs to this coordinator
            entity_unique_id = entity_entry.unique_id
            if entity_unique_id and f"{coordinator.host}_{coordinator.port}" in entity_unique_id:
                _LOGGER.debug("Found coordinator via fallback method")
                return coordinator
    
    _LOGGER.error("Coordinator not found for entity %s", entity_id)
    return None


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services for IRis IR Remote integration."""
    hass.services.async_remove(DOMAIN, SERVICE_SEND_BUTTON)
    hass.services.async_remove(DOMAIN, SERVICE_START_LEARNING)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_LEARNING)
    hass.services.async_remove(DOMAIN, SERVICE_RESTART_DEVICE)
    hass.services.async_remove(DOMAIN, SERVICE_OPEN_WEB_UI)
