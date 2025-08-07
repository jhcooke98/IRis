"""Config flow for IRis IR Remote integration."""
import logging
import aiohttp
import async_timeout
import voluptuous as vol
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    API_STATUS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data[CONF_HOST]
    port = data[CONF_PORT]
    
    url = f"http://{host}:{port}{API_STATUS}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(10):
                async with session.get(url) as response:
                    if response.status != 200:
                        raise CannotConnect(f"HTTP {response.status}")
                    
                    data_response = await response.json()
                    
                    # Verify this is actually an IRis device
                    if "uptime" not in data_response:
                        raise InvalidDevice("Device does not appear to be an IRis IR Remote")
                    
                    # Extract device info for identification
                    device_info = {
                        "title": f"IRis IR Remote ({host})",
                        "host": host,
                        "port": port,
                        "ip_address": data_response.get("ipAddress", host),
                        "uptime": data_response.get("uptime", "Unknown"),
                        "button_count": data_response.get("buttonCount", "0 / 100"),
                    }
                    
                    return device_info
                    
    except aiohttp.ClientError as err:
        _LOGGER.error("Error connecting to %s:%s - %s", host, port, err)
        raise CannotConnect(f"Cannot connect to device: {err}")
    except Exception as err:
        _LOGGER.error("Unexpected error connecting to %s:%s - %s", host, port, err)
        raise CannotConnect(f"Unexpected error: {err}")


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IRis IR Remote."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidDevice:
            errors["base"] = "invalid_device"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # Check if this device is already configured
            await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=info["title"],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for IRis IR Remote."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, 10  # Changed from DEFAULT_SCAN_INTERVAL to 10 for faster updates
                        ),
                    ): cv.positive_int,
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidDevice(HomeAssistantError):
    """Error to indicate the device is not a valid IRis IR Remote."""
