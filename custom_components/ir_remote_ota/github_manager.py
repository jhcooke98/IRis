"""GitHub firmware manager for IR Remote OTA integration."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant

from .const import (
    GITHUB_API_BASE,
    GITHUB_RAW_BASE,
    GITHUB_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class GitHubFirmwareManager:
    """Manages firmware from GitHub repositories."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        repo: str,
        path: str = "firmware",
        token: str | None = None,
    ) -> None:
        """Initialize GitHub firmware manager."""
        self.hass = hass
        self.session = session
        self.repo = repo
        self.path = path.strip("/")
        self.token = token
        self._cache: dict[str, Any] = {}
        self._last_check: datetime | None = None
        self._cache_ttl = timedelta(minutes=5)

    @property
    def headers(self) -> dict[str, str]:
        """Get headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "HomeAssistant-IRRemoteOTA/1.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def get_firmware_files(self) -> list[dict[str, Any]]:
        """Get list of firmware files from GitHub repository."""
        try:
            # Check cache first
            if (
                self._last_check
                and datetime.now() - self._last_check < self._cache_ttl
                and "files" in self._cache
            ):
                return self._cache["files"]

            url = f"{GITHUB_API_BASE}/repos/{self.repo}/contents/{self.path}"
            _LOGGER.debug("Fetching firmware files from: %s", url)

            async with asyncio.timeout(GITHUB_TIMEOUT):
                async with self.session.get(url, headers=self.headers) as response:
                    if response.status == 404:
                        _LOGGER.warning(
                            "Firmware path not found in repository: %s/%s",
                            self.repo,
                            self.path,
                        )
                        return []

                    if response.status != 200:
                        _LOGGER.error(
                            "Failed to fetch firmware files: HTTP %d", response.status
                        )
                        return []

                    data = await response.json()

                    # Filter for .bin files only
                    firmware_files = []
                    for item in data:
                        if (
                            item.get("type") == "file"
                            and item.get("name", "").endswith(".bin")
                        ):
                            firmware_files.append(
                                {
                                    "name": item["name"],
                                    "download_url": item["download_url"],
                                    "sha": item["sha"],
                                    "size": item["size"],
                                }
                            )

                    # Cache results
                    self._cache["files"] = firmware_files
                    self._last_check = datetime.now()

                    _LOGGER.debug("Found %d firmware files", len(firmware_files))
                    return firmware_files

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout fetching firmware files from GitHub")
        except Exception as err:
            _LOGGER.error("Error fetching firmware files from GitHub: %s", err)

        return []

    async def get_firmware_versions(self) -> dict[str, str]:
        """Get firmware versions from GitHub repository."""
        files = await self.get_firmware_files()
        versions = {}

        for file_info in files:
            filename = file_info["name"]
            # Extract version from filename (e.g., "ir_remote_v1.2.3.bin")
            match = re.search(r"v?(\d+\.\d+\.\d+)", filename)
            if match:
                version = match.group(1)
                versions[version] = filename

        return versions

    async def get_latest_version(self) -> str | None:
        """Get the latest firmware version."""
        versions = await self.get_firmware_versions()
        if not versions:
            return None

        # Sort versions
        sorted_versions = sorted(
            versions.keys(), key=lambda v: [int(x) for x in v.split(".")]
        )
        return sorted_versions[-1] if sorted_versions else None

    async def download_firmware(
        self, filename: str, local_path: str
    ) -> bool:
        """Download firmware file to local storage."""
        try:
            files = await self.get_firmware_files()
            file_info = next(
                (f for f in files if f["name"] == filename), None
            )

            if not file_info:
                _LOGGER.error("Firmware file not found: %s", filename)
                return False

            download_url = file_info["download_url"]
            _LOGGER.info("Downloading firmware: %s", filename)

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            async with asyncio.timeout(GITHUB_TIMEOUT * 3):  # Longer timeout for downloads
                async with self.session.get(download_url) as response:
                    if response.status != 200:
                        _LOGGER.error(
                            "Failed to download firmware: HTTP %d", response.status
                        )
                        return False

                    # Write file
                    with open(local_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)

            # Verify file size
            if os.path.getsize(local_path) != file_info["size"]:
                _LOGGER.error("Downloaded file size mismatch")
                os.remove(local_path)
                return False

            _LOGGER.info("Successfully downloaded firmware: %s", local_path)
            return True

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout downloading firmware: %s", filename)
        except Exception as err:
            _LOGGER.error("Error downloading firmware %s: %s", filename, err)

        return False

    async def sync_firmware_directory(
        self, local_dir: str, auto_download: bool = True
    ) -> dict[str, str]:
        """Sync GitHub firmware with local directory."""
        try:
            # Get available firmware files
            files = await self.get_firmware_files()
            local_versions = {}

            # Create local directory if it doesn't exist
            os.makedirs(local_dir, exist_ok=True)

            for file_info in files:
                filename = file_info["name"]
                local_path = os.path.join(local_dir, filename)

                # Extract version
                match = re.search(r"v?(\d+\.\d+\.\d+)", filename)
                if not match:
                    continue

                version = match.group(1)

                # Check if file exists locally
                if os.path.exists(local_path):
                    # Verify file size
                    if os.path.getsize(local_path) == file_info["size"]:
                        local_versions[version] = local_path
                        continue
                    else:
                        _LOGGER.warning("Local file size mismatch: %s", filename)

                # Download if auto_download is enabled
                if auto_download:
                    if await self.download_firmware(filename, local_path):
                        local_versions[version] = local_path
                else:
                    _LOGGER.info("Firmware available for download: %s", filename)

            return local_versions

        except Exception as err:
            _LOGGER.error("Error syncing firmware directory: %s", err)
            return {}

    async def check_repository_access(self) -> bool:
        """Check if repository is accessible."""
        try:
            url = f"{GITHUB_API_BASE}/repos/{self.repo}"
            async with asyncio.timeout(GITHUB_TIMEOUT):
                async with self.session.get(url, headers=self.headers) as response:
                    return response.status == 200
        except Exception:
            return False

    async def get_repository_info(self) -> dict[str, Any]:
        """Get repository information."""
        try:
            url = f"{GITHUB_API_BASE}/repos/{self.repo}"
            async with asyncio.timeout(GITHUB_TIMEOUT):
                async with self.session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as err:
            _LOGGER.error("Error getting repository info: %s", err)

        return {}

    def invalidate_cache(self) -> None:
        """Invalidate the firmware cache."""
        self._cache.clear()
        self._last_check = None
