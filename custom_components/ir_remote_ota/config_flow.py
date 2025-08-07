"""Config flow for IR Remote OTA integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_NETWORK_RANGE,
    DEFAULT_FIRMWARE_PATH,
    DEFAULT_UPDATE_CHECK_INTERVAL,
    DEFAULT_OTA_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_NETWORK_RANGE,
    CONF_FIRMWARE_PATH,
    CONF_AUTO_DISCOVERY,
    CONF_UPDATE_CHECK_INTERVAL,
    CONF_OTA_PASSWORD,
    CONF_FIRMWARE_SOURCE_TYPE,
    CONF_GITHUB_REPO,
    CONF_GITHUB_PATH,
    CONF_GITHUB_TOKEN,
    CONF_AUTO_DOWNLOAD,
    FIRMWARE_SOURCE_LOCAL,
    FIRMWARE_SOURCE_GITHUB,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=60, max=3600)
        ),
        vol.Optional(CONF_NETWORK_RANGE, default=DEFAULT_NETWORK_RANGE): str,
        vol.Optional(
            CONF_FIRMWARE_SOURCE_TYPE, default=FIRMWARE_SOURCE_LOCAL
        ): vol.In([FIRMWARE_SOURCE_LOCAL, FIRMWARE_SOURCE_GITHUB]),
        vol.Optional(CONF_FIRMWARE_PATH, default=DEFAULT_FIRMWARE_PATH): str,
        vol.Optional(CONF_GITHUB_REPO, default=""): str,
        vol.Optional(CONF_GITHUB_PATH, default="firmware"): str,
        vol.Optional(CONF_GITHUB_TOKEN, default=""): str,
        vol.Optional(CONF_AUTO_DOWNLOAD, default=True): bool,
        vol.Optional(CONF_AUTO_DISCOVERY, default=True): bool,
        vol.Optional(
            CONF_UPDATE_CHECK_INTERVAL, default=DEFAULT_UPDATE_CHECK_INTERVAL
        ): vol.All(vol.Coerce(int), vol.Range(min=300, max=86400)),
        vol.Optional(CONF_OTA_PASSWORD, default=DEFAULT_OTA_PASSWORD): str,
    }
)


class IRRemoteOTAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IR Remote OTA."""

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

        # Validate firmware configuration
        firmware_source = user_input[CONF_FIRMWARE_SOURCE_TYPE]
        
        if firmware_source == FIRMWARE_SOURCE_LOCAL:
            firmware_path = user_input[CONF_FIRMWARE_PATH]
            if not firmware_path.startswith("/"):
                errors[CONF_FIRMWARE_PATH] = "invalid_path"
        
        elif firmware_source == FIRMWARE_SOURCE_GITHUB:
            github_repo = user_input[CONF_GITHUB_REPO]
            if not github_repo or "/" not in github_repo:
                errors[CONF_GITHUB_REPO] = "invalid_repo"

        if errors:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )

        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title="IR Remote OTA", data=user_input)

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> IRRemoteOTAOptionsFlow:
        """Create the options flow."""
        return IRRemoteOTAOptionsFlow(config_entry)


class IRRemoteOTAOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for IR Remote OTA."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                vol.Optional(
                    CONF_NETWORK_RANGE,
                    default=self.config_entry.options.get(
                        CONF_NETWORK_RANGE, DEFAULT_NETWORK_RANGE
                    ),
                ): str,
                vol.Optional(
                    CONF_FIRMWARE_SOURCE_TYPE,
                    default=self.config_entry.options.get(
                        CONF_FIRMWARE_SOURCE_TYPE, FIRMWARE_SOURCE_LOCAL
                    ),
                ): vol.In([FIRMWARE_SOURCE_LOCAL, FIRMWARE_SOURCE_GITHUB]),
                vol.Optional(
                    CONF_FIRMWARE_PATH,
                    default=self.config_entry.options.get(
                        CONF_FIRMWARE_PATH, DEFAULT_FIRMWARE_PATH
                    ),
                ): str,
                vol.Optional(
                    CONF_GITHUB_REPO,
                    default=self.config_entry.options.get(CONF_GITHUB_REPO, ""),
                ): str,
                vol.Optional(
                    CONF_GITHUB_PATH,
                    default=self.config_entry.options.get(CONF_GITHUB_PATH, "firmware"),
                ): str,
                vol.Optional(
                    CONF_GITHUB_TOKEN,
                    default=self.config_entry.options.get(CONF_GITHUB_TOKEN, ""),
                ): str,
                vol.Optional(
                    CONF_AUTO_DOWNLOAD,
                    default=self.config_entry.options.get(CONF_AUTO_DOWNLOAD, True),
                ): bool,
                vol.Optional(
                    CONF_AUTO_DISCOVERY,
                    default=self.config_entry.options.get(CONF_AUTO_DISCOVERY, True),
                ): bool,
                vol.Optional(
                    CONF_UPDATE_CHECK_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_CHECK_INTERVAL, DEFAULT_UPDATE_CHECK_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=300, max=86400)),
                vol.Optional(
                    CONF_OTA_PASSWORD,
                    default=self.config_entry.options.get(
                        CONF_OTA_PASSWORD, DEFAULT_OTA_PASSWORD
                    ),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
