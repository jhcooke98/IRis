# IR Remote OTA Integration

This Home Assistant custom integration provides Over-The-Air (OTA) firmware update capabilities for IR Remote Mini devices.

## Features

- **Automatic device discovery** via mDNS and network scanning
- **Firmware version management** with automatic update detection
- **OTA updates** via ESP32 standard protocols
- **Bulk update capabilities** for multiple devices
- **Update notifications** and progress tracking
- **Device monitoring** with health status sensors

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the "+" button
4. Search for "IR Remote OTA"
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/ir_remote_ota` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration → Integrations
4. Click "+" and search for "IR Remote OTA"

## Configuration

### Initial Setup

1. **Add Integration**: Go to Configuration → Integrations → Add Integration → "IR Remote OTA"
2. **Configure Settings**:
   - **Scan Interval**: How often to scan for devices (default: 300 seconds)
   - **Network Range**: CIDR notation for device discovery (default: 192.168.1.0/24)
   - **Firmware Source**: Choose between "Local" or "GitHub"
   - **Local Settings** (if using local source):
     - **Firmware Path**: Directory containing firmware files (default: /config/ir_remote_firmware/)
   - **GitHub Settings** (if using GitHub source):
     - **GitHub Repository**: Repository in owner/repo format
     - **Firmware Path**: Path in repository to firmware files
     - **GitHub Token**: Personal access token for private repos (optional)
     - **Auto Download**: Automatically download firmware files
   - **Auto Discovery**: Enable mDNS discovery (default: true)
   - **Update Check Interval**: How often to check for firmware updates (default: 3600 seconds)
   - **OTA Password**: Password for OTA updates (default: ir_remote_update)

### Firmware Directory Setup

#### Option 1: Local Firmware Directory

1. **Create Directory**: Create the firmware directory in your Home Assistant config
   ```bash
   mkdir /config/ir_remote_firmware
   ```

2. **Add Firmware Files**: Copy your compiled `.bin` files using the naming convention:
   ```
   ir_remote_v1.0.0.bin
   ir_remote_v1.1.0.bin
   ir_remote_v2.0.0.bin
   ```

3. **Permissions**: Ensure Home Assistant can read the directory and files

#### Option 2: GitHub Repository (New!)

You can now configure the integration to pull firmware directly from a GitHub repository:

1. **Configure Integration**: Set firmware source to "GitHub"
2. **Repository Settings**:
   - **GitHub Repository**: `owner/repo` format (e.g., `jhcooke98/IRis`)
   - **Firmware Path**: Path in repo to firmware files (default: `firmware`)
   - **GitHub Token**: Optional, for private repositories
   - **Auto Download**: Automatically download new firmware files

3. **Repository Structure**: Your GitHub repository should have firmware files in the specified path:
   ```
   your-repo/
   ├── firmware/
   │   ├── ir_remote_v1.0.0.bin
   │   ├── ir_remote_v1.1.0.bin
   │   └── ir_remote_v2.0.0.bin
   └── other-files...
   ```

**Benefits of GitHub Source:**
- **Centralized Management**: Single source of truth for firmware
- **Version Control**: Track firmware changes with git history
- **Automatic Updates**: Integration automatically detects new releases
- **Team Collaboration**: Multiple developers can push firmware updates
- **Backup**: GitHub serves as firmware backup

**Example Configuration:**
```yaml
# In integration options
firmware_source_type: github
github_repo: "jhcooke98/IRis"
github_path: "firmware"
auto_download: true
```

## Entities Created

### Per Device

**Sensors:**
- `sensor.{device_name}_firmware_version` - Current firmware version
- `sensor.{device_name}_status` - Online/offline status
- `sensor.{device_name}_free_memory` - Available memory in bytes
- `sensor.{device_name}_uptime` - Device uptime timestamp
- `sensor.{device_name}_update_state` - Current update state

**Binary Sensors:**
- `binary_sensor.{device_name}_connectivity` - Device connectivity status
- `binary_sensor.{device_name}_update_available` - Update available indicator
- `binary_sensor.{device_name}_updating` - Currently updating indicator

**Switches:**
- `switch.{device_name}_ota_enabled` - Enable/disable OTA for device

### Global

**Sensors:**
- `sensor.ir_remote_device_count` - Total number of discovered devices
- `sensor.ir_remote_latest_firmware` - Latest available firmware version
- `sensor.ir_remote_updates_available` - Number of devices with updates available

## Services

### `ir_remote_ota.update_device`

Update a specific device.

**Parameters:**
- `device_id` (required): Device MAC address (without colons)
- `firmware_file` (optional): Specific firmware file path
- `force_update` (optional): Force update even if versions match

**Example:**
```yaml
service: ir_remote_ota.update_device
data:
  device_id: "a1b2c3d4e5f6"
  firmware_file: "/config/ir_remote_firmware/ir_remote_v2.0.0.bin"
```

### `ir_remote_ota.update_all_devices`

Update all devices with available updates.

**Parameters:**
- `firmware_file` (optional): Specific firmware file path
- `exclude_devices` (optional): List of device IDs to exclude
- `force_update` (optional): Force update even if versions match

**Example:**
```yaml
service: ir_remote_ota.update_all_devices
data:
  exclude_devices: ["a1b2c3d4e5f6"]
```

### `ir_remote_ota.check_updates`

Manually check for firmware updates.

**Example:**
```yaml
service: ir_remote_ota.check_updates
```

### `ir_remote_ota.enable_ota` / `ir_remote_ota.disable_ota`

Enable or disable OTA for a specific device.

**Parameters:**
- `device_id` (required): Device MAC address

**Example:**
```yaml
service: ir_remote_ota.enable_ota
data:
  device_id: "a1b2c3d4e5f6"
```

### `ir_remote_ota.sync_github_firmware`

Manually sync firmware from GitHub repository (only available when using GitHub source).

**Example:**
```yaml
service: ir_remote_ota.sync_github_firmware
```

## Automation Examples

### Automatic Update Check

```yaml
automation:
  - alias: "IR Remote Daily Update Check"
    trigger:
      - platform: time
        at: "02:00:00"  # 2 AM daily
    action:
      - service: ir_remote_ota.check_updates

  - alias: "IR Remote Update Notification"
    trigger:
      - platform: state
        entity_id: sensor.ir_remote_updates_available
        to: 
        from: "0"
    condition:
      - condition: template
        value_template: "{{ states('sensor.ir_remote_updates_available') | int > 0 }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "IR Remote Updates Available"
          message: >
            {{ states('sensor.ir_remote_updates_available') }} device(s) have firmware updates available.
```

### Scheduled Maintenance Updates

```yaml
automation:
  - alias: "IR Remote Maintenance Updates"
    trigger:
      - platform: time
        at: "03:00:00"  # 3 AM Sunday
      - platform: template
        value_template: "{{ now().weekday() == 6 }}"  # Sunday
    condition:
      - condition: template
        value_template: "{{ states('sensor.ir_remote_updates_available') | int > 0 }}"
    action:
      - service: ir_remote_ota.update_all_devices
      - delay: "00:05:00"  # Wait 5 minutes
      - service: notify.mobile_app_your_phone
        data:
          title: "IR Remote Maintenance Complete"
          message: "Weekly firmware updates completed."
```

### Update Failure Notification

```yaml
automation:
  - alias: "IR Remote Update Failed"
    trigger:
      - platform: state
        entity_id: 
          - sensor.living_room_ir_update_state
          - sensor.bedroom_ir_update_state
        to: "failed"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "IR Remote Update Failed"
          message: >
            Device {{ trigger.to_state.attributes.friendly_name }} 
            failed to update firmware.
```

## Dashboard Configuration

### Device Overview Card

```yaml
type: entities
title: IR Remote Devices
entities:
  - entity: sensor.ir_remote_device_count
    name: "Total Devices"
  - entity: sensor.ir_remote_latest_firmware
    name: "Latest Firmware"
  - entity: sensor.ir_remote_updates_available
    name: "Updates Available"
  - type: divider
  - entity: sensor.living_room_ir_firmware_version
    name: "Living Room - Firmware"
  - entity: binary_sensor.living_room_ir_connectivity
    name: "Living Room - Online"
  - entity: switch.living_room_ir_ota_enabled
    name: "Living Room - OTA"
```

### Update Actions Card

```yaml
type: horizontal-stack
cards:
  - type: button
    name: "Check Updates"
    icon: mdi:refresh
    tap_action:
      action: call-service
      service: ir_remote_ota.check_updates
  
  - type: button
    name: "Update All"
    icon: mdi:upload
    tap_action:
      action: call-service
      service: ir_remote_ota.update_all_devices
    hold_action:
      action: more-info
```

### Device Status Cards

```yaml
type: grid
columns: 2
cards:
  - type: entity
    entity: sensor.living_room_ir_firmware_version
    name: "Living Room IR"
    icon: mdi:remote
    state_color: true
    
  - type: entity
    entity: sensor.bedroom_ir_firmware_version
    name: "Bedroom IR"
    icon: mdi:remote
    state_color: true
```

## Troubleshooting

### Device Not Discovered

1. **Check Network Range**: Ensure the configured network range includes your devices
2. **Verify mDNS**: Confirm devices are broadcasting mDNS with correct service name
3. **Check Firewall**: Ensure Home Assistant can access device ports (80, 3232)
4. **Manual Configuration**: Add device IPs manually in integration options

### Update Failures

1. **Check OTA Status**: Ensure OTA is enabled on the device
2. **Verify Firmware**: Confirm firmware file is valid and compatible
3. **Network Issues**: Check for network connectivity during update
4. **Device Memory**: Ensure device has sufficient free memory for update

### Integration Errors

1. **Check Logs**: Review Home Assistant logs for error details
2. **Restart Integration**: Try reloading the integration
3. **Firmware Directory**: Verify firmware directory exists and is readable
4. **Dependencies**: Ensure all required Python packages are installed

## Development

### Adding Device Support

To add support for new device types:

1. Update `DEVICE_TYPE_*` constants in `const.py`
2. Modify device detection logic in `coordinator.py`
3. Add device-specific API endpoints if needed
4. Update documentation

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Issues**: Report bugs and feature requests on GitHub
- **Community**: Join the Home Assistant community forums
- **Documentation**: Check the GitHub wiki for additional documentation
