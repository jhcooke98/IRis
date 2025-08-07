"""MQTT sensor support for IRis IR Remote integration."""
import logging
import json
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components import mqtt

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MQTT sensors for IRis IR Remote devices."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Only create MQTT sensors if device has MQTT support
    if coordinator.has_mqtt_support:
        entities.extend([
            IRisMQTTButtonSensor(coordinator, entry),
            IRisMQTTStatusSensor(coordinator, entry),
        ])
        
        _LOGGER.info(
            "Added %d MQTT sensors for device %s with real-time updates",
            len(entities), coordinator.host
        )
    
    if entities:
        async_add_entities(entities, update_before_add=True)


class IRisMQTTButtonSensor(SensorEntity):
    """MQTT sensor for real-time button press events."""

    def __init__(self, coordinator, entry):
        """Initialize the MQTT button sensor."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_name = f"IRis Last Button {coordinator.host}"
        self._attr_unique_id = f"iris_last_button_{coordinator.host}_{coordinator.port}"
        self._attr_icon = "mdi:gesture-tap-button"
        self._attr_device_class = None
        self._subscription = None
        self._last_button_data = {}

    async def async_added_to_hass(self):
        """Subscribe to MQTT topic when entity is added."""
        if self._coordinator.has_mqtt_support:
            topic = self._coordinator.mqtt_button_topic
            self._subscription = await mqtt.async_subscribe(
                self.hass, topic, self._handle_message, qos=1
            )
            _LOGGER.debug("MQTT button sensor subscribed to: %s", topic)

    async def async_will_remove_from_hass(self):
        """Unsubscribe from MQTT topic when entity is removed."""
        if self._subscription:
            self._subscription()

    @callback
    def _handle_message(self, message):
        """Handle MQTT button press message."""
        try:
            data = json.loads(message.payload)
            button_name = data.get("button", "unknown")
            protocol = data.get("protocol", "unknown")
            timestamp = data.get("timestamp", 0)
            
            # Update sensor state
            self._attr_native_value = button_name
            self._last_button_data = data
            
            # Add useful attributes
            self._attr_extra_state_attributes = {
                "protocol": protocol,
                "command": data.get("command", ""),
                "address": data.get("address", ""),
                "timestamp": timestamp,
                "uptime": data.get("uptime", 0),
                "device": data.get("device", ""),
                "last_updated": datetime.now().isoformat(),
                "source": "mqtt_realtime",
            }
            
            self.async_write_ha_state()
            
            _LOGGER.debug(
                "MQTT button update: %s (%s) at %s",
                button_name, protocol, timestamp
            )
            
        except (json.JSONDecodeError, Exception) as err:
            _LOGGER.debug("Failed to parse MQTT button message: %s", err)

    @property
    def device_info(self):
        """Return device information."""
        return self._coordinator.device_info

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.has_mqtt_support and self._subscription is not None


class IRisMQTTStatusSensor(SensorEntity):
    """MQTT sensor for real-time device status."""

    def __init__(self, coordinator, entry):
        """Initialize the MQTT status sensor."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_name = f"IRis MQTT Status {coordinator.host}"
        self._attr_unique_id = f"iris_mqtt_status_{coordinator.host}_{coordinator.port}"
        self._attr_icon = "mdi:server-network"
        self._attr_device_class = None
        self._subscription = None
        self._last_status_data = {}

    async def async_added_to_hass(self):
        """Subscribe to MQTT topic when entity is added."""
        if self._coordinator.has_mqtt_support:
            topic = self._coordinator.mqtt_status_topic
            self._subscription = await mqtt.async_subscribe(
                self.hass, topic, self._handle_message, qos=1
            )
            _LOGGER.debug("MQTT status sensor subscribed to: %s", topic)

    async def async_will_remove_from_hass(self):
        """Unsubscribe from MQTT topic when entity is removed."""
        if self._subscription:
            self._subscription()

    @callback
    def _handle_message(self, message):
        """Handle MQTT status message."""
        try:
            # Handle both simple status and JSON status messages
            if message.payload in ("online", "offline"):
                # Simple online/offline status
                self._attr_native_value = message.payload
                self._attr_extra_state_attributes = {
                    "connection_status": message.payload,
                    "last_updated": datetime.now().isoformat(),
                    "source": "mqtt_realtime",
                }
            else:
                # Try to parse as JSON status update
                data = json.loads(message.payload)
                
                # Use a meaningful status value
                status_text = "online"
                if "learningMode" in data:
                    status_text = "learning" if data["learningMode"] else "ready"
                
                self._attr_native_value = status_text
                self._last_status_data = data
                
                # Add all status data as attributes
                self._attr_extra_state_attributes = {
                    **data,
                    "last_updated": datetime.now().isoformat(),
                    "source": "mqtt_realtime",
                }
            
            self.async_write_ha_state()
            
            _LOGGER.debug("MQTT status update: %s", self._attr_native_value)
            
        except (json.JSONDecodeError, Exception) as err:
            _LOGGER.debug("Failed to parse MQTT status message: %s", err)

    @property
    def device_info(self):
        """Return device information."""
        return self._coordinator.device_info

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.has_mqtt_support and self._subscription is not None
