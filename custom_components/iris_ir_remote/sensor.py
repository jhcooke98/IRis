"""Sensor platform for IRis IR Remote integration."""
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfInformation

from .const import DOMAIN
from .coordinator import IRisDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(
        key="last_button",
        name="Last Button Fallback",
        icon="mdi:gesture-tap-button",
    ),
    SensorEntityDescription(
        key="uptime",
        name="Uptime",
        icon="mdi:clock-outline",
    ),
    SensorEntityDescription(
        key="button_count",
        name="Button Count",
        icon="mdi:counter",
    ),
    SensorEntityDescription(
        key="ip_address",
        name="IP Address",
        icon="mdi:ip-network",
    ),
    SensorEntityDescription(
        key="free_heap",
        name="Free Memory",
        icon="mdi:memory",
        unit_of_measurement=UnitOfInformation.BYTES,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IRis IR Remote sensor entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Add HTTP polling sensors
    for description in SENSOR_DESCRIPTIONS:
        entities.append(IRisSensor(coordinator, description))
    
    # Add MQTT real-time sensors if device supports MQTT
    if coordinator.has_mqtt_support:
        from .mqtt_sensor import IRisMQTTButtonSensor, IRisMQTTStatusSensor
        
        entities.extend([
            IRisMQTTButtonSensor(coordinator, config_entry),
            IRisMQTTStatusSensor(coordinator, config_entry),
        ])
        
        _LOGGER.info(
            "Device %s has MQTT support - added real-time sensors (topics: %s, %s)",
            coordinator.host,
            coordinator.mqtt_button_topic,
            coordinator.mqtt_status_topic
        )
    else:
        _LOGGER.debug("Device %s uses HTTP polling only - no MQTT sensors added", coordinator.host)
    
    async_add_entities(entities)


class IRisSensor(CoordinatorEntity, SensorEntity):
    """Representation of an IRis IR Remote sensor."""

    def __init__(
        self,
        coordinator: IRisDataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_{description.key}"
        self._attr_name = f"IRis {description.name} ({coordinator.host})"

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
            
        status = self.coordinator.data.get("status", {})
        
        key = self.entity_description.key
        
        if key == "last_button":
            return status.get("lastButton", "None")
        elif key == "uptime":
            return status.get("uptime", "0s")
        elif key == "button_count":
            return status.get("buttonCount", "0 / 100")
        elif key == "ip_address":
            return status.get("ipAddress", "Unknown")
        elif key == "free_heap":
            return status.get("freeHeap", 0)
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
            
        status = self.coordinator.data.get("status", {})
        
        # Add context-specific attributes based on sensor type
        if self.entity_description.key == "last_button":
            return {
                "last_time": status.get("lastTime", "Never"),
            }
        elif self.entity_description.key == "button_count":
            buttons_data = self.coordinator.data.get("buttons", {})
            remotes = buttons_data.get("remotes", {})
            return {
                "total_remotes": len(remotes),
                "remote_protocols": list(remotes.keys()),
            }
        
        return {}
