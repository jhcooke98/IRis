"""Coordinator for IR Remote OTA integration."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from zeroconf.asyncio import AsyncZeroconf

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components import persistent_notification

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_NETWORK_RANGE,
    CONF_FIRMWARE_PATH,
    CONF_AUTO_DISCOVERY,
    CONF_OTA_PASSWORD,
    CONF_FIRMWARE_SOURCE_TYPE,
    CONF_GITHUB_REPO,
    CONF_GITHUB_PATH,
    CONF_GITHUB_TOKEN,
    CONF_AUTO_DOWNLOAD,
    API_STATUS,
    API_OTA_STATUS,
    API_OTA_ENABLE,
    API_OTA_DISABLE,
    API_UPDATE,
    DEVICE_TYPE_MINI,
    DEVICE_NAME_PREFIX,
    MDNS_TYPE,
    DEVICE_TIMEOUT,
    UPDATE_TIMEOUT,
    ATTR_DEVICE_TYPE,
    ATTR_FIRMWARE_VERSION,
    ATTR_MAC_ADDRESS,
    ATTR_HOSTNAME,
    ATTR_FREE_HEAP,
    ATTR_FLASH_SIZE,
    ATTR_CHIP_MODEL,
    ATTR_LAST_SEEN,
    ATTR_OTA_ENABLED,
    UPDATE_STATE_IDLE,
    UPDATE_STATE_CHECKING,
    UPDATE_STATE_DOWNLOADING,
    UPDATE_STATE_INSTALLING,
    UPDATE_STATE_SUCCESS,
    UPDATE_STATE_FAILED,
    NOTIFICATION_UPDATE_AVAILABLE,
    NOTIFICATION_UPDATE_FAILED,
    NOTIFICATION_UPDATE_SUCCESS,
    FIRMWARE_SOURCE_LOCAL,
    FIRMWARE_SOURCE_GITHUB,
)
from .github_manager import GitHubFirmwareManager

_LOGGER = logging.getLogger(__name__)


class DeviceInfo:
    """Device information class."""

    def __init__(self, ip: str, data: dict[str, Any]) -> None:
        """Initialize device info."""
        self.ip = ip
        self.mac_address = data.get("mac", "").replace(":", "").lower()
        self.hostname = data.get("hostname", f"IR-Remote-Mini-{self.mac_address[-6:]}")
        self.firmware_version = data.get("version", "unknown")
        self.device_type = data.get(ATTR_DEVICE_TYPE, "unknown")
        self.free_heap = data.get("freeHeap", 0)
        self.flash_size = data.get("flashSize", 0)
        self.chip_model = data.get("chipModel", "unknown")
        self.last_seen = datetime.now()
        self.ota_enabled = False
        self.update_state = UPDATE_STATE_IDLE
        self.available_update = None

    @property
    def unique_id(self) -> str:
        """Return unique ID for the device."""
        return self.mac_address

    @property
    def name(self) -> str:
        """Return device name."""
        return self.hostname

    @property
    def is_online(self) -> bool:
        """Check if device is online."""
        return (datetime.now() - self.last_seen) < timedelta(minutes=10)

    def update_from_status(self, data: dict[str, Any]) -> None:
        """Update device info from status data."""
        self.firmware_version = data.get("version", self.firmware_version)
        self.free_heap = data.get("freeHeap", self.free_heap)
        self.flash_size = data.get("flashSize", self.flash_size)
        self.chip_model = data.get("chipModel", self.chip_model)
        self.last_seen = datetime.now()


class IRRemoteOTACoordinator(DataUpdateCoordinator):
    """Coordinator for IR Remote OTA integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        entry: ConfigEntry,
    ) -> None:
        """Initialize coordinator."""
        self.hass = hass
        self.session = session
        self.entry = entry
        self.devices: dict[str, DeviceInfo] = {}
        self.firmware_versions: dict[str, str] = {}
        self._discovery_running = False
        self.github_manager: GitHubFirmwareManager | None = None

        # Initialize GitHub manager if using GitHub source
        firmware_source = entry.options.get(CONF_FIRMWARE_SOURCE_TYPE, FIRMWARE_SOURCE_LOCAL)
        if firmware_source == FIRMWARE_SOURCE_GITHUB:
            github_repo = entry.options.get(CONF_GITHUB_REPO)
            github_path = entry.options.get(CONF_GITHUB_PATH, "firmware")
            github_token = entry.options.get(CONF_GITHUB_TOKEN)
            
            if github_repo:
                self.github_manager = GitHubFirmwareManager(
                    hass, session, github_repo, github_path, github_token
                )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        await self.async_update_device_status()
        await self.async_check_firmware_updates()
        return {
            "devices": {uid: device for uid, device in self.devices.items()},
            "firmware_versions": self.firmware_versions,
        }

    async def async_discover_devices(self) -> None:
        """Discover IR Remote devices on the network."""
        if self._discovery_running:
            return

        self._discovery_running = True
        _LOGGER.debug("Starting device discovery")

        try:
            # Auto discovery via mDNS
            if self.entry.options.get(CONF_AUTO_DISCOVERY, True):
                await self._discover_mdns_devices()

            # Network scanning
            network_range = self.entry.options.get(CONF_NETWORK_RANGE, "192.168.1.0/24")
            await self._scan_network_range(network_range)

        except Exception as err:
            _LOGGER.error("Error during device discovery: %s", err)
        finally:
            self._discovery_running = False

    async def _discover_mdns_devices(self) -> None:
        """Discover devices using mDNS."""
        _LOGGER.debug("Discovering devices via mDNS")

        try:
            aiozc = AsyncZeroconf()
            zc = aiozc.zeroconf

            class IRRemoteListener(ServiceListener):
                def __init__(self, coordinator):
                    self.coordinator = coordinator

                def remove_service(self, zc, type_, name):
                    pass

                def add_service(self, zc, type_, name):
                    info = zc.get_service_info(type_, name)
                    if info and DEVICE_NAME_PREFIX.lower() in name.lower():
                        ip = str(ipaddress.IPv4Address(info.addresses[0]))
                        asyncio.create_task(self.coordinator._check_device(ip))

                def update_service(self, zc, type_, name):
                    self.add_service(zc, type_, name)

            listener = IRRemoteListener(self)
            browser = ServiceBrowser(zc, MDNS_TYPE, listener)

            # Let it run for a few seconds
            await asyncio.sleep(5)

            browser.cancel()
            await aiozc.async_close()

        except Exception as err:
            _LOGGER.warning("mDNS discovery failed: %s", err)

    async def _scan_network_range(self, network_range: str) -> None:
        """Scan network range for devices."""
        _LOGGER.debug("Scanning network range: %s", network_range)

        try:
            network = ipaddress.IPv4Network(network_range, strict=False)
            tasks = []

            for ip in network.hosts():
                tasks.append(self._check_device(str(ip)))
                
                # Limit concurrent connections
                if len(tasks) >= 20:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks = []

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as err:
            _LOGGER.error("Network scanning failed: %s", err)

    async def _check_device(self, ip: str) -> None:
        """Check if IP is an IR Remote device."""
        try:
            async with asyncio.timeout(DEVICE_TIMEOUT):
                async with self.session.get(
                    f"http://{ip}{API_STATUS}", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get(ATTR_DEVICE_TYPE) == DEVICE_TYPE_MINI:
                            await self._add_or_update_device(ip, data)

        except Exception:
            # Device not responding or not an IR Remote
            pass

    async def _add_or_update_device(self, ip: str, data: dict[str, Any]) -> None:
        """Add or update device."""
        mac_address = data.get("mac", "").replace(":", "").lower()
        
        if mac_address in self.devices:
            # Update existing device
            device = self.devices[mac_address]
            device.ip = ip  # IP might have changed
            device.update_from_status(data)
        else:
            # Add new device
            device = DeviceInfo(ip, data)
            self.devices[mac_address] = device
            _LOGGER.info("Discovered new IR Remote device: %s (%s)", device.name, ip)

        # Check OTA status
        await self._update_device_ota_status(device)

    async def _update_device_ota_status(self, device: DeviceInfo) -> None:
        """Update device OTA status."""
        try:
            async with asyncio.timeout(DEVICE_TIMEOUT):
                async with self.session.get(
                    f"http://{device.ip}{API_OTA_STATUS}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        device.ota_enabled = data.get("enabled", False)
        except Exception:
            # OTA status not available
            device.ota_enabled = False

    async def async_update_device_status(self) -> None:
        """Update status for all known devices."""
        tasks = []
        for device in self.devices.values():
            tasks.append(self._update_single_device_status(device))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _update_single_device_status(self, device: DeviceInfo) -> None:
        """Update status for a single device."""
        try:
            async with asyncio.timeout(DEVICE_TIMEOUT):
                async with self.session.get(
                    f"http://{device.ip}{API_STATUS}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        device.update_from_status(data)
                        await self._update_device_ota_status(device)
        except Exception:
            # Device offline
            pass

    async def async_check_firmware_updates(self) -> None:
        """Check for available firmware updates."""
        firmware_source = self.entry.options.get(CONF_FIRMWARE_SOURCE_TYPE, FIRMWARE_SOURCE_LOCAL)
        
        if firmware_source == FIRMWARE_SOURCE_GITHUB and self.github_manager:
            await self._check_github_firmware_updates()
        else:
            await self._check_local_firmware_updates()

    async def _check_github_firmware_updates(self) -> None:
        """Check for firmware updates from GitHub repository."""
        try:
            auto_download = self.entry.options.get(CONF_AUTO_DOWNLOAD, True)
            firmware_path = self.entry.options.get(CONF_FIRMWARE_PATH, "/config/ir_remote_firmware/")
            
            # Sync firmware from GitHub
            if auto_download:
                local_versions = await self.github_manager.sync_firmware_directory(firmware_path)
                self.firmware_versions.update(local_versions)
            
            # Get latest version from GitHub
            latest_version = await self.github_manager.get_latest_version()
            if latest_version:
                self.firmware_versions["latest"] = latest_version

            # Check each device for updates
            await self._compare_device_versions(latest_version)

        except Exception as err:
            _LOGGER.error("Error checking GitHub firmware updates: %s", err)

    async def _check_local_firmware_updates(self) -> None:
        """Check for firmware updates from local directory."""
        firmware_path = self.entry.options.get(CONF_FIRMWARE_PATH, "/config/ir_remote_firmware/")
        
        try:
            # Scan firmware directory
            if not os.path.exists(firmware_path):
                _LOGGER.warning("Firmware directory does not exist: %s", firmware_path)
                return

            firmware_files = []
            for file in os.listdir(firmware_path):
                if file.endswith(".bin"):
                    firmware_files.append(file)

            if not firmware_files:
                _LOGGER.debug("No firmware files found in %s", firmware_path)
                return

            # Find latest firmware version
            latest_version = self._get_latest_firmware_version(firmware_files)
            self.firmware_versions["latest"] = latest_version

            # Check each device for updates
            await self._compare_device_versions(latest_version)

        except Exception as err:
            _LOGGER.error("Error checking local firmware updates: %s", err)

    async def _compare_device_versions(self, latest_version: str | None) -> None:
        """Compare device versions with latest firmware."""
        if not latest_version:
            return

        updates_available = []
        for device in self.devices.values():
            if device.is_online and self._compare_versions(latest_version, device.firmware_version) > 0:
                device.available_update = latest_version
                updates_available.append(device)
            else:
                device.available_update = None

        # Notify if updates are available
        if updates_available:
            await self._notify_updates_available(updates_available)

    def _get_latest_firmware_version(self, firmware_files: list[str]) -> str:
        """Get the latest firmware version from filename."""
        # Extract version from filename (e.g., "ir_remote_v1.2.3.bin")
        versions = []
        for file in firmware_files:
            match = re.search(r"v?(\d+\.\d+\.\d+)", file)
            if match:
                versions.append(match.group(1))

        if not versions:
            return "unknown"

        # Sort versions
        versions.sort(key=lambda v: [int(x) for x in v.split(".")])
        return versions[-1]

    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal."""
        try:
            v1_parts = [int(x) for x in version1.split(".")]
            v2_parts = [int(x) for x in version2.split(".")]
            
            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 > v2:
                    return 1
                elif v1 < v2:
                    return -1
            return 0
        except (ValueError, AttributeError):
            return 0

    async def _notify_updates_available(self, devices: list[DeviceInfo]) -> None:
        """Notify about available updates."""
        device_names = [device.name for device in devices]
        message = f"Firmware updates available for: {', '.join(device_names)}"
        
        persistent_notification.async_create(
            self.hass,
            message,
            "IR Remote Firmware Updates Available",
            NOTIFICATION_UPDATE_AVAILABLE,
        )

    async def async_enable_ota(self, device_id: str) -> bool:
        """Enable OTA for a device."""
        device = self.devices.get(device_id)
        if not device:
            return False

        try:
            async with asyncio.timeout(DEVICE_TIMEOUT):
                async with self.session.post(
                    f"http://{device.ip}{API_OTA_ENABLE}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        device.ota_enabled = True
                        return True
        except Exception as err:
            _LOGGER.error("Failed to enable OTA for %s: %s", device.name, err)

        return False

    async def async_disable_ota(self, device_id: str) -> bool:
        """Disable OTA for a device."""
        device = self.devices.get(device_id)
        if not device:
            return False

        try:
            async with asyncio.timeout(DEVICE_TIMEOUT):
                async with self.session.post(
                    f"http://{device.ip}{API_OTA_DISABLE}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        device.ota_enabled = False
                        return True
        except Exception as err:
            _LOGGER.error("Failed to disable OTA for %s: %s", device.name, err)

        return False

    async def async_update_device(self, device_id: str, firmware_file: str | None = None) -> bool:
        """Update a specific device."""
        device = self.devices.get(device_id)
        if not device:
            _LOGGER.error("Device not found: %s", device_id)
            return False

        if not device.is_online:
            _LOGGER.error("Device offline: %s", device.name)
            return False

        firmware_source = self.entry.options.get(CONF_FIRMWARE_SOURCE_TYPE, FIRMWARE_SOURCE_LOCAL)
        firmware_path = self.entry.options.get(CONF_FIRMWARE_PATH, "/config/ir_remote_firmware/")
        
        if not firmware_file:
            # Use latest firmware
            latest_version = self.firmware_versions.get("latest")
            if not latest_version:
                _LOGGER.error("No firmware version available")
                return False
            
            # Find firmware file for latest version
            if firmware_source == FIRMWARE_SOURCE_GITHUB and self.github_manager:
                # Download from GitHub if needed
                auto_download = self.entry.options.get(CONF_AUTO_DOWNLOAD, True)
                if auto_download:
                    github_versions = await self.github_manager.get_firmware_versions()
                    if latest_version in github_versions:
                        filename = github_versions[latest_version]
                        firmware_file = os.path.join(firmware_path, filename)
                        
                        if not os.path.exists(firmware_file):
                            _LOGGER.info("Downloading firmware for update: %s", filename)
                            if not await self.github_manager.download_firmware(filename, firmware_file):
                                _LOGGER.error("Failed to download firmware: %s", filename)
                                return False
            
            if not firmware_file:
                # Search local directory
                for file in os.listdir(firmware_path):
                    if latest_version in file and file.endswith(".bin"):
                        firmware_file = os.path.join(firmware_path, file)
                        break
            
            if not firmware_file or not os.path.exists(firmware_file):
                _LOGGER.error("Firmware file not found for version %s", latest_version)
                return False
        
        if not os.path.exists(firmware_file):
            _LOGGER.error("Firmware file does not exist: %s", firmware_file)
            return False

        return await self._perform_ota_update(device, firmware_file)

    async def _perform_ota_update(self, device: DeviceInfo, firmware_file: str) -> bool:
        """Perform OTA update on device."""
        _LOGGER.info("Starting OTA update for %s with %s", device.name, firmware_file)
        
        device.update_state = UPDATE_STATE_CHECKING
        
        try:
            # Enable OTA if not already enabled
            if not device.ota_enabled:
                if not await self.async_enable_ota(device.unique_id):
                    device.update_state = UPDATE_STATE_FAILED
                    return False

            device.update_state = UPDATE_STATE_DOWNLOADING

            # Read firmware file
            with open(firmware_file, "rb") as f:
                firmware_data = f.read()

            device.update_state = UPDATE_STATE_INSTALLING

            # Upload firmware via web interface
            data = aiohttp.FormData()
            data.add_field("file", firmware_data, filename="firmware.bin")

            async with asyncio.timeout(UPDATE_TIMEOUT):
                async with self.session.post(
                    f"http://{device.ip}{API_UPDATE}",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=UPDATE_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        device.update_state = UPDATE_STATE_SUCCESS
                        
                        # Wait for device to reboot and update info
                        await asyncio.sleep(10)
                        await self._update_single_device_status(device)
                        
                        # Clear available update
                        device.available_update = None
                        
                        # Notify success
                        persistent_notification.async_create(
                            self.hass,
                            f"Successfully updated {device.name}",
                            "IR Remote Update Success",
                            f"{NOTIFICATION_UPDATE_SUCCESS}_{device.unique_id}",
                        )
                        
                        _LOGGER.info("Successfully updated %s", device.name)
                        return True
                    else:
                        device.update_state = UPDATE_STATE_FAILED
                        raise Exception(f"Update failed with status {response.status}")

        except Exception as err:
            device.update_state = UPDATE_STATE_FAILED
            error_msg = f"Failed to update {device.name}: {err}"
            _LOGGER.error(error_msg)
            
            # Notify failure
            persistent_notification.async_create(
                self.hass,
                error_msg,
                "IR Remote Update Failed",
                f"{NOTIFICATION_UPDATE_FAILED}_{device.unique_id}",
            )
            
            return False

    async def async_update_all_devices(
        self, firmware_file: str | None = None, exclude_devices: list[str] | None = None
    ) -> dict[str, bool]:
        """Update all devices."""
        exclude_devices = exclude_devices or []
        results = {}
        
        for device_id, device in self.devices.items():
            if device_id in exclude_devices:
                continue
                
            if device.available_update or firmware_file:
                result = await self.async_update_device(device_id, firmware_file)
                results[device_id] = result
                
                # Small delay between updates
                await asyncio.sleep(2)
        
        return results

    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        _LOGGER.debug("Shutting down IR Remote OTA coordinator")
