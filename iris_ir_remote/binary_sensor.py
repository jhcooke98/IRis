"""Binary sensor platform for IRis IR Remote integration."""
import logging
import json
from typing import Any
from datetime import datetime

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components import mqtt

from .const import DOMAIN
from .coordinator import IRisDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

BINARY_SENSOR_DESCRIPTIONS = [
    BinarySensorEntityDescription(
        key="wifi_connected",
        name="WiFi Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:wifi",
    ),
    BinarySensorEntityDescription(
        key="mqtt_connected",
        name="MQTT Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:server-network",
    ),
    BinarySensorEntityDescription(
        key="learning_mode",
        name="Learning Mode",
        icon="mdi:school",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IRis IR Remote binary sensor entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Add standard binary sensors
    for description in BINARY_SENSOR_DESCRIPTIONS:
        entities.append(IRisBinarySensor(coordinator, description))
    
    # Add individual button entities if MQTT is supported
    if coordinator.has_mqtt_support:
        # Get available buttons from the coordinator
        available_buttons = coordinator.get_available_buttons()
        
        for button_name in available_buttons:
            entities.append(IRisButtonEntity(coordinator, config_entry, button_name))
            _LOGGER.debug("Added button entity for: %s", button_name)
        
        _LOGGER.info(
            "Device %s has MQTT support - added %d button entities: %s",
            coordinator.host,
            len(available_buttons),
            ", ".join(available_buttons)
        )
    else:
        _LOGGER.debug("Device %s uses HTTP polling only - no button entities added", coordinator.host)
    
    async_add_entities(entities)


class IRisBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an IRis IR Remote binary sensor."""

    def __init__(
        self,
        coordinator: IRisDataUpdateCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_{description.key}"
        self._attr_name = f"IRis {description.name} ({coordinator.host})"

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return False
            
        status = self.coordinator.data.get("status", {})
        
        key = self.entity_description.key
        
        if key == "wifi_connected":
            return status.get("wifiConnected", False)
        elif key == "mqtt_connected":
            return status.get("mqttConnected", False)
        elif key == "learning_mode":
            return status.get("learningMode", False)
        
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
            
        status = self.coordinator.data.get("status", {})
        
        # Add context-specific attributes based on sensor type
        if self.entity_description.key == "mqtt_connected":
            return {
                "mqtt_enabled": status.get("mqttEnabled", False),
                "mqtt_failed_attempts": status.get("mqttFailedAttempts", 0),
                "mqtt_given_up": status.get("mqttGivenUp", False),
            }
        
        return {}


class IRisButtonEntity(BinarySensorEntity):
    """Individual binary sensor for each button with momentary press detection."""

    def __init__(self, coordinator, entry, button_name):
        """Initialize the button entity."""
        self._coordinator = coordinator
        self._entry = entry
        self._button_name = button_name
        self._attr_name = f"IRis {button_name} Button {coordinator.host}"
        self._attr_unique_id = f"iris_button_{button_name.lower()}_{coordinator.host}_{coordinator.port}"
        self._attr_icon = "mdi:circle"
        self._attr_device_class = None
        self._button_subscription = None
        self._status_subscription = None
        self._is_on = False
        self._last_trigger_time = None
        self._off_timer = None
        self._device_available = True

    async def async_added_to_hass(self):
        """Subscribe to MQTT topics when entity is added."""
        if self._coordinator.has_mqtt_support:
            # Subscribe to button topic for press events
            button_topic = self._coordinator.mqtt_button_topic
            self._button_subscription = await mqtt.async_subscribe(
                self.hass, button_topic, self._handle_button_message, qos=1
            )
            
            # Subscribe to status topic for availability
            status_topic = self._coordinator.mqtt_status_topic
            self._status_subscription = await mqtt.async_subscribe(
                self.hass, status_topic, self._handle_status_message, qos=1
            )
            
            _LOGGER.debug("Button entity %s subscribed to: %s and %s", 
                         self._button_name, button_topic, status_topic)

    async def async_will_remove_from_hass(self):
        """Unsubscribe from MQTT topics when entity is removed."""
        if self._button_subscription:
            self._button_subscription()
        if self._status_subscription:
            self._status_subscription()
        if self._off_timer:
            self._off_timer()

    @callback
    def _handle_button_message(self, message):
        """Handle MQTT button press message."""
        try:
            data = json.loads(message.payload)
            button_name = data.get("button", "")
            
            # Check if this message is for our button
            if button_name == self._button_name:
                # Turn on the binary sensor
                self._is_on = True
                self._last_trigger_time = datetime.now().isoformat()
                
                self.async_write_ha_state()
                
                # Schedule turning off after 2 seconds (like the example)
                if self._off_timer:
                    self._off_timer()
                
                self._off_timer = self.hass.loop.call_later(
                    2.0, self._turn_off
                )
                
                _LOGGER.debug(
                    "Button %s triggered - turning on for 2 seconds",
                    self._button_name
                )
                
        except (json.JSONDecodeError, Exception) as err:
            _LOGGER.debug("Failed to parse MQTT button message: %s", err)

    @callback
    def _handle_status_message(self, message):
        """Handle MQTT status message for availability."""
        try:
            # Handle both simple status and JSON status messages
            if message.payload in ("online", "offline"):
                self._device_available = message.payload == "online"
                self.async_write_ha_state()
            else:
                # Try to parse as JSON status update - if it parses, device is online
                json.loads(message.payload)
                self._device_available = True
                self.async_write_ha_state()
                
        except (json.JSONDecodeError, Exception):
            # If we can't parse the status, assume device is offline
            self._device_available = False
            self.async_write_ha_state()

    @callback
    def _turn_off(self):
        """Turn off the binary sensor."""
        self._is_on = False
        self._off_timer = None
        self.async_write_ha_state()
        _LOGGER.debug("Button %s turned off after delay", self._button_name)

    @property
    def device_info(self):
        """Return device information."""
        return self._coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (self._coordinator.has_mqtt_support and 
                self._button_subscription is not None and 
                self._device_available)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {
            "button_name": self._button_name,
            "device_available": self._device_available,
        }
        if self._last_trigger_time:
            attrs["last_triggered"] = self._last_trigger_time
        return attrs
