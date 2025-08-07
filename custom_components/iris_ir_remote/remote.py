"""Remote platform for IRis IR Remote integration."""
import logging
from typing import Any, Iterable, Optional

from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IRisDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IRis IR Remote remote entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Create the main remote entity
    entities.append(IRisRemote(coordinator))
    
    # Create individual remote entities for each learned remote
    if coordinator.data and "buttons" in coordinator.data:
        remotes_data = coordinator.data["buttons"].get("remotes", {})
        for protocol, remote_info in remotes_data.items():
            entities.append(IRisIndividualRemote(coordinator, protocol, remote_info))
    
    async_add_entities(entities)


class IRisRemote(CoordinatorEntity, RemoteEntity):
    """Representation of the main IRis IR Remote device."""

    def __init__(self, coordinator: IRisDataUpdateCoordinator) -> None:
        """Initialize the remote."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_main_remote"
        self._attr_name = f"IRis IR Remote ({coordinator.host})"
        
    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("status", {}).get("wifiConnected", False)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
            
        status = self.coordinator.data.get("status", {})
        buttons = self.coordinator.data.get("buttons", {})
        
        return {
            "last_button": status.get("lastButton", "None"),
            "last_time": status.get("lastTime", "Never"),
            "uptime": status.get("uptime", "0s"),
            "button_count": status.get("buttonCount", "0 / 100"),
            "wifi_connected": status.get("wifiConnected", False),
            "mqtt_connected": status.get("mqttConnected", False),
            "mqtt_enabled": status.get("mqttEnabled", False),
            "ip_address": status.get("ipAddress", "Unknown"),
            "free_heap": status.get("freeHeap", 0),
            "available_remotes": list(buttons.get("remotes", {}).keys()) if buttons else [],
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the remote on (start learning mode)."""
        success = await self.coordinator.start_learning_mode()
        if success:
            # Force immediate update to reflect the state change
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the remote off (stop learning mode)."""
        success = await self.coordinator.stop_learning_mode()
        if success:
            # Force immediate update to reflect the state change
            await self.coordinator.async_request_refresh()

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send commands to the remote."""
        for cmd in command:
            success = await self.coordinator.send_button_command(cmd)
            if not success:
                _LOGGER.warning("Failed to send command: %s", cmd)
        
        # Force immediate update after sending commands
        await self.coordinator.async_request_refresh()


class IRisIndividualRemote(CoordinatorEntity, RemoteEntity):
    """Representation of an individual learned remote."""

    def __init__(
        self, 
        coordinator: IRisDataUpdateCoordinator, 
        protocol: str, 
        remote_info: dict
    ) -> None:
        """Initialize the individual remote."""
        super().__init__(coordinator)
        self._protocol = protocol
        self._remote_info = remote_info
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_remote_{protocol}"
        self._attr_name = f"{remote_info.get('friendlyName', protocol)} ({coordinator.host})"
        
    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("status", {}).get("wifiConnected", False)

    @property
    def available_commands(self) -> list[str]:
        """Return the list of available commands for this remote."""
        if not self.coordinator.data:
            return []
            
        remotes_data = self.coordinator.data.get("buttons", {}).get("remotes", {})
        remote_data = remotes_data.get(self._protocol, {})
        buttons = remote_data.get("buttons", [])
        
        return [button.get("name", "") for button in buttons if button.get("name")]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attributes = {
            "protocol": self._protocol,
            "friendly_name": self._remote_info.get("friendlyName", self._protocol),
            "available_commands": self.available_commands,
            "button_count": len(self.available_commands),
        }
        
        # Add button details
        if self.coordinator.data:
            remotes_data = self.coordinator.data.get("buttons", {}).get("remotes", {})
            remote_data = remotes_data.get(self._protocol, {})
            buttons = remote_data.get("buttons", [])
            
            button_details = {}
            for button in buttons:
                name = button.get("name")
                if name:
                    # Convert command and address to integers, handling both int and string inputs
                    try:
                        command = button.get('command', 0)
                        if isinstance(command, str):
                            # Handle hex strings like "0x1A" or decimal strings like "26"
                            command = int(command, 0) if command.startswith('0x') else int(command)
                        else:
                            command = int(command)
                    except (ValueError, TypeError):
                        command = 0
                    
                    try:
                        address = button.get('address', 0)
                        if isinstance(address, str):
                            # Handle hex strings like "0x1A" or decimal strings like "26"
                            address = int(address, 0) if address.startswith('0x') else int(address)
                        else:
                            address = int(address)
                    except (ValueError, TypeError):
                        address = 0
                    
                    button_details[name] = {
                        "command": f"0x{command:02X}",
                        "address": f"0x{address:02X}",
                    }
            
            attributes["button_details"] = button_details
        
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the remote on (enable this remote's commands)."""
        # For individual remotes, turning on doesn't have a specific action
        # But we can force a refresh to ensure current state is displayed
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the remote off (disable this remote's commands)."""
        # For individual remotes, turning off doesn't have a specific action
        # But we can force a refresh to ensure current state is displayed
        await self.coordinator.async_request_refresh()

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send commands to this specific remote."""
        available_commands = self.available_commands
        
        for cmd in command:
            if cmd not in available_commands:
                _LOGGER.warning("Command '%s' not available for remote '%s'", cmd, self._protocol)
                continue
                
            success = await self.coordinator.send_button_command(cmd)
            if not success:
                _LOGGER.warning("Failed to send command: %s", cmd)
        
        # Force immediate update after sending commands
        await self.coordinator.async_request_refresh()
