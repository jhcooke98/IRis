"""Data update coordinator for IRis IR Remote."""
import logging
from datetime import timedelta
import aiohttp
import async_timeout
import json

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components import mqtt

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    API_STATUS,
    API_BUTTONS,
)

_LOGGER = logging.getLogger(__name__)


class IRisDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from IRis IR Remote device."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.base_url = f"http://{self.host}:{self.port}"
        self._last_button_state = None
        self._last_learning_state = None
        
        # MQTT configuration
        self._mqtt_enabled = False
        self._mqtt_config = {}
        self._mqtt_subscriptions = []
        self._device_mqtt_config = None
        
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.host}_{self.port}",
            update_interval=timedelta(seconds=scan_interval),
            always_update=True,  # Force updates even if data hasn't changed
        )

    async def async_setup(self):
        """Set up the coordinator and check for MQTT capability."""
        await self._check_mqtt_capability()
        if self._mqtt_enabled:
            await self._setup_mqtt_subscriptions()

    async def _check_mqtt_capability(self):
        """Check if the device has MQTT enabled and get its configuration."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                # Try to get MQTT config from device
                url = f"{self.base_url}/api/mqtt/config"
                
                async with async_timeout.timeout(5):
                    async with session.get(url) as response:
                        if response.status == 200:
                            mqtt_data = await response.json()
                            
                            # Check if MQTT is enabled and configured
                            if (mqtt_data.get("enabled", False) and 
                                mqtt_data.get("server") and 
                                mqtt_data.get("topic_button") and
                                mqtt_data.get("topic_status")):
                                
                                self._mqtt_enabled = True
                                self._device_mqtt_config = mqtt_data
                                
                                _LOGGER.info(
                                    "Device %s has MQTT enabled - topics: button=%s, status=%s",
                                    self.host,
                                    mqtt_data.get("topic_button"),
                                    mqtt_data.get("topic_status")
                                )
                                
                                # Reduce polling interval since we'll get real-time updates via MQTT
                                self.update_interval = timedelta(seconds=30)  # Less frequent polling
                                
                                return
                            
        except Exception as err:
            _LOGGER.debug("MQTT check failed for %s: %s", self.host, err)
            
        # MQTT not available - keep normal polling
        _LOGGER.debug("Device %s does not have MQTT enabled - using HTTP polling only", self.host)

    async def _setup_mqtt_subscriptions(self):
        """Set up MQTT subscriptions for real-time updates."""
        if not self._mqtt_enabled or not self._device_mqtt_config:
            return
            
        try:
            # Check if Home Assistant has MQTT integration available
            if "mqtt" not in self.hass.config.components:
                _LOGGER.warning("MQTT integration not available in Home Assistant")
                self._mqtt_enabled = False
                return
                
            button_topic = self._device_mqtt_config["topic_button"]
            status_topic = self._device_mqtt_config["topic_status"]
            
            # Subscribe to button press messages for instant updates
            self._mqtt_subscriptions.append(
                await mqtt.async_subscribe(
                    self.hass,
                    button_topic,
                    self._handle_mqtt_button_message,
                    qos=1
                )
            )
            
            # Subscribe to status messages for device state updates
            self._mqtt_subscriptions.append(
                await mqtt.async_subscribe(
                    self.hass,
                    status_topic,
                    self._handle_mqtt_status_message,
                    qos=1
                )
            )
            
            _LOGGER.info(
                "MQTT subscriptions established for device %s: %s, %s",
                self.host, button_topic, status_topic
            )
            
        except Exception as err:
            _LOGGER.error("Failed to setup MQTT subscriptions for %s: %s", self.host, err)
            self._mqtt_enabled = False

    @callback
    def _handle_mqtt_button_message(self, message):
        """Handle MQTT button press messages for instant updates."""
        try:
            payload = json.loads(message.payload)
            button_name = payload.get("button")
            protocol = payload.get("protocol")
            
            if button_name:
                _LOGGER.debug("MQTT button press received: %s (%s)", button_name, protocol)
                
                # Update our cached data immediately
                if self.data and "status" in self.data:
                    self.data["status"]["lastButton"] = button_name
                    self.data["status"]["lastTime"] = payload.get("timestamp", "")
                    
                    # Trigger immediate entity state updates
                    self.async_update_listeners()
                    
        except (json.JSONDecodeError, Exception) as err:
            _LOGGER.debug("Failed to parse MQTT button message: %s", err)

    @callback
    def _handle_mqtt_status_message(self, message):
        """Handle MQTT status messages for device state updates."""
        try:
            # Handle both simple "online"/"offline" and JSON status messages
            if message.payload in ("online", "offline"):
                # Simple status message
                is_online = message.payload == "online"
                if self.data and "status" in self.data:
                    self.data["status"]["wifiConnected"] = is_online
                    self.async_update_listeners()
            else:
                # Try to parse as JSON status update
                payload = json.loads(message.payload)
                if self.data and "status" in self.data:
                    # Update relevant status fields
                    self.data["status"].update(payload)
                    self.async_update_listeners()
                    
        except (json.JSONDecodeError, Exception) as err:
            _LOGGER.debug("Failed to parse MQTT status message: %s", err)

    async def async_unload(self):
        """Unload the coordinator and clean up MQTT subscriptions."""
        for unsubscribe in self._mqtt_subscriptions:
            unsubscribe()
        self._mqtt_subscriptions.clear()

    @property
    def has_mqtt_support(self) -> bool:
        """Return True if device has MQTT support enabled."""
        return self._mqtt_enabled

    @property
    def mqtt_button_topic(self) -> str:
        """Return MQTT button topic if available."""
        if self._device_mqtt_config:
            return self._device_mqtt_config.get("topic_button", "")
        return ""

    @property
    def mqtt_status_topic(self) -> str:
        """Return MQTT status topic if available."""
        if self._device_mqtt_config:
            return self._device_mqtt_config.get("topic_status", "")
        return ""

    def get_available_buttons(self) -> list:
        """Return list of available button names from the device."""
        buttons = []
        if self.data and "buttons" in self.data:
            buttons_data = self.data["buttons"]
            if "remotes" in buttons_data:
                for protocol, remote_data in buttons_data["remotes"].items():
                    if "buttons" in remote_data:
                        for button in remote_data["buttons"]:
                            button_name = button.get("name", "")
                            if button_name:
                                buttons.append(button_name)
        return buttons

    async def _async_update_data(self):
        """Fetch data from IRis device."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            ) as session:
                # Get status data
                status_data = await self._fetch_json(session, API_STATUS)
                
                # Get buttons data
                buttons_data = await self._fetch_json(session, API_BUTTONS)
                
                # Track state changes for faster updates
                current_button = status_data.get("lastButton")
                current_learning = status_data.get("learningMode", False)
                
                # If button state changed, trigger immediate update
                if (self._last_button_state != current_button or 
                    self._last_learning_state != current_learning):
                    _LOGGER.debug(
                        "State change detected - Button: %s->%s, Learning: %s->%s", 
                        self._last_button_state, current_button,
                        self._last_learning_state, current_learning
                    )
                    self._last_button_state = current_button
                    self._last_learning_state = current_learning
                
                data = {
                    "status": status_data,
                    "buttons": buttons_data,
                    "host": self.host,
                    "port": self.port,
                    "base_url": self.base_url,
                    "last_update": self.hass.loop.time(),
                }
                
                _LOGGER.debug("Updated data for %s: %s", self.host, data["status"])
                return data
                
        except Exception as err:
            _LOGGER.error("Error communicating with IRis device %s: %s", self.host, err)
            raise UpdateFailed(f"Error communicating with IRis device: {err}")

    async def _fetch_json(self, session: aiohttp.ClientSession, endpoint: str):
        """Fetch JSON data from an endpoint."""
        url = f"{self.base_url}{endpoint}"
        try:
            async with async_timeout.timeout(10):
                async with session.get(url) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"HTTP {response.status} for {url}")
                    return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching {url}: {err}")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching {url}: {err}")

    async def send_button_command(self, button_name: str) -> bool:
        """Send a button command to the device."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                url = f"{self.base_url}/api/test"
                params = {"button": button_name}
                
                async with async_timeout.timeout(8):
                    async with session.get(url, params=params) as response:
                        success = response.status == 200
                        if success:
                            _LOGGER.debug("Successfully sent button command: %s", button_name)
                            # Force immediate refresh after sending command
                            await self.async_request_refresh()
                        return success
                        
        except Exception as err:
            _LOGGER.error("Error sending button command %s: %s", button_name, err)
            return False

    async def start_learning_mode(self) -> bool:
        """Start learning mode on the device."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                url = f"{self.base_url}/api/learn/start"
                
                async with async_timeout.timeout(8):
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            success = data.get("status") == "success"
                            if success:
                                _LOGGER.debug("Learning mode started successfully")
                                # Force immediate refresh after state change
                                await self.async_request_refresh()
                            return success
                        return False
                        
        except Exception as err:
            _LOGGER.error("Error starting learning mode: %s", err)
            return False

    async def stop_learning_mode(self) -> bool:
        """Stop learning mode on the device."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                url = f"{self.base_url}/api/learn/stop"
                
                async with async_timeout.timeout(8):
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            success = data.get("status") == "success"
                            if success:
                                _LOGGER.debug("Learning mode stopped successfully")
                                # Force immediate refresh after state change
                                await self.async_request_refresh()
                            return success
                        return False
                        
        except Exception as err:
            _LOGGER.error("Error stopping learning mode: %s", err)
            return False

    async def restart_device(self) -> bool:
        """Restart the device."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            ) as session:
                url = f"{self.base_url}/api/restart"
                
                async with async_timeout.timeout(10):
                    async with session.post(url) as response:
                        success = response.status == 200
                        if success:
                            _LOGGER.info("Device restart command sent to %s", self.host)
                        return success
                        
        except Exception as err:
            _LOGGER.error("Error restarting device: %s", err)
            return False

    async def force_update(self) -> None:
        """Force an immediate update of the data."""
        _LOGGER.debug("Forcing update for device %s", self.host)
        await self.async_request_refresh()

    @property
    def device_info(self):
        """Return device information."""
        status = self.data.get("status", {}) if self.data else {}
        
        return {
            "identifiers": {(DOMAIN, f"{self.host}:{self.port}")},
            "name": f"IRis IR Remote ({self.host})",
            "manufacturer": "IRis",
            "model": "IR Remote Mini",
            "sw_version": "1.0",
            "configuration_url": self.base_url,
        }
