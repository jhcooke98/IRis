"""Constants for the IR Remote OTA integration."""
from __future__ import annotations

from typing import Final

# Domain
DOMAIN: Final = "ir_remote_ota"

# Default values
DEFAULT_SCAN_INTERVAL: Final = 300  # 5 minutes
DEFAULT_UPDATE_CHECK_INTERVAL: Final = 3600  # 1 hour
DEFAULT_NETWORK_RANGE: Final = "192.168.1.0/24"
DEFAULT_OTA_PORT: Final = 3232
DEFAULT_OTA_PASSWORD: Final = "ir_remote_update"
DEFAULT_FIRMWARE_PATH: Final = "/config/ir_remote_firmware/"

# Configuration keys
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_NETWORK_RANGE: Final = "network_range"
CONF_FIRMWARE_PATH: Final = "firmware_path"
CONF_AUTO_DISCOVERY: Final = "auto_discovery"
CONF_UPDATE_CHECK_INTERVAL: Final = "update_check_interval"
CONF_DEVICES: Final = "devices"
CONF_OTA_PASSWORD: Final = "ota_password"
CONF_FIRMWARE_SOURCE_TYPE: Final = "firmware_source_type"
CONF_GITHUB_REPO: Final = "github_repo"
CONF_GITHUB_PATH: Final = "github_path"
CONF_GITHUB_TOKEN: Final = "github_token"
CONF_AUTO_DOWNLOAD: Final = "auto_download"

# Device attributes
ATTR_DEVICE_TYPE: Final = "deviceType"
ATTR_FIRMWARE_VERSION: Final = "firmware_version"
ATTR_MAC_ADDRESS: Final = "mac_address"
ATTR_HOSTNAME: Final = "hostname"
ATTR_FREE_HEAP: Final = "free_heap"
ATTR_FLASH_SIZE: Final = "flash_size"
ATTR_CHIP_MODEL: Final = "chip_model"
ATTR_LAST_SEEN: Final = "last_seen"
ATTR_OTA_ENABLED: Final = "ota_enabled"

# Services
SERVICE_UPDATE_DEVICE: Final = "update_device"
SERVICE_UPDATE_ALL_DEVICES: Final = "update_all_devices"
SERVICE_CHECK_UPDATES: Final = "check_updates"
SERVICE_ENABLE_OTA: Final = "enable_ota"
SERVICE_DISABLE_OTA: Final = "disable_ota"
SERVICE_SYNC_GITHUB: Final = "sync_github_firmware"

# Service parameters
ATTR_DEVICE_ID: Final = "device_id"
ATTR_FIRMWARE_FILE: Final = "firmware_file"
ATTR_EXCLUDE_DEVICES: Final = "exclude_devices"
ATTR_FORCE_UPDATE: Final = "force_update"

# API endpoints
API_STATUS: Final = "/api/status"
API_OTA_STATUS: Final = "/api/ota/status"
API_OTA_ENABLE: Final = "/api/ota/enable"
API_OTA_DISABLE: Final = "/api/ota/disable"
API_UPDATE: Final = "/update"

# Device discovery
MDNS_TYPE: Final = "_http._tcp.local."
DEVICE_TYPE_MINI: Final = "mini"
DEVICE_NAME_PREFIX: Final = "IR-Remote-Mini"

# Update states
UPDATE_STATE_IDLE: Final = "idle"
UPDATE_STATE_CHECKING: Final = "checking"
UPDATE_STATE_DOWNLOADING: Final = "downloading"
UPDATE_STATE_INSTALLING: Final = "installing"
UPDATE_STATE_SUCCESS: Final = "success"
UPDATE_STATE_FAILED: Final = "failed"

# Notification IDs
NOTIFICATION_UPDATE_AVAILABLE: Final = "ir_remote_update_available"
NOTIFICATION_UPDATE_FAILED: Final = "ir_remote_update_failed"
NOTIFICATION_UPDATE_SUCCESS: Final = "ir_remote_update_success"

# Timeouts
DEVICE_TIMEOUT: Final = 10  # seconds
UPDATE_TIMEOUT: Final = 300  # 5 minutes
DISCOVERY_TIMEOUT: Final = 30  # seconds
GITHUB_TIMEOUT: Final = 30  # seconds

# Firmware source types
FIRMWARE_SOURCE_LOCAL: Final = "local"
FIRMWARE_SOURCE_GITHUB: Final = "github"

# GitHub API
GITHUB_API_BASE: Final = "https://api.github.com"
GITHUB_RAW_BASE: Final = "https://raw.githubusercontent.com"
