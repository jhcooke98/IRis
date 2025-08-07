# Home Assistant OTA Update Integration for IR Remote Mini Devices

## Project Description

I need to create a Home Assistant integration that can automatically discover and push firmware updates to multiple IR Remote Mini devices on my network. Each device runs ESP32 firmware with OTA (Over-The-Air) update capabilities.

## Device Specifications

### Device Details:
- **Device Name**: IR Remote Mini
- **Chip**: ESP32
- **Hostname**: `IR-Remote-Mini` (may include MAC suffix for uniqueness)
- **Firmware Version**: 1.0
- **OTA Port**: 3232 (standard ESP32 OTA port)
- **OTA Password**: `ir_remote_update`

### Device APIs Available:
- **Status API**: `GET http://[DEVICE_IP]/api/status`
- **OTA Status**: `GET http://[DEVICE_IP]/api/ota/status`
- **OTA Enable**: `POST http://[DEVICE_IP]/api/ota/enable`
- **OTA Disable**: `POST http://[DEVICE_IP]/api/ota/disable`
- **Web Upload**: `POST http://[DEVICE_IP]/update` (for .bin file uploads)
- **Device Info**: Includes chip model, revision, free heap, flash size

### Device Discovery:
- Devices broadcast mDNS as `IR-Remote-Mini.local`
- Devices respond to network scanning on port 80
- Status API returns device type as "mini"
- MQTT topic pattern: `home/ir_remote_mini/[device_id]/status`

## Requirements

### 1. Device Discovery Service
Create a Home Assistant service that can:
- **Auto-discover devices** on the network using mDNS or network scanning
- **Identify IR Remote Mini devices** by checking the `/api/status` endpoint
- **Track device information**:
  - IP address
  - MAC address (from chip ID)
  - Firmware version
  - Device hostname
  - Last seen timestamp
  - OTA capability status

### 2. Firmware Management
- **Central firmware repository** in Home Assistant config directory
- **Firmware versioning** system to track available updates
- **Firmware validation** to ensure .bin files are compatible
- **Rollback capability** to previous firmware versions
- **Update scheduling** for maintenance windows

### 3. OTA Update Service
Create services for:
- **Individual device updates**: `ir_remote.update_device`
- **Bulk updates**: `ir_remote.update_all_devices`
- **Scheduled updates**: Integration with HA automation
- **Update status monitoring** with progress tracking

### 4. Home Assistant Integration Components

#### Custom Integration Structure:
```
custom_components/ir_remote_ota/
├── __init__.py
├── manifest.json
├── config_flow.py
├── const.py
├── device_scanner.py
├── ota_manager.py
├── services.yaml
├── sensor.py
└── switch.py
```

#### Entities to Create:
- **Sensor entities** for each device:
  - Firmware version
  - Device status (online/offline)
  - Free memory
  - Uptime
  - Last update time
- **Switch entities**:
  - OTA enabled/disabled per device
  - Force update trigger
- **Device entities** with device info and diagnostics

### 5. Configuration Options
```yaml
ir_remote_ota:
  scan_interval: 300  # seconds
  network_range: "192.168.1.0/24"
  firmware_path: "/config/ir_remote_firmware/"
  auto_discovery: true
  update_check_interval: 3600  # seconds
  devices:
    - ip: "192.168.1.100"
      name: "Living Room IR"
    - ip: "192.168.1.101"
      name: "Bedroom IR"
```

## Implementation Details

### Device Discovery Method:
```python
# Pseudo-code for device discovery
async def discover_devices():
    devices = []
    # Method 1: mDNS discovery
    mdns_devices = await discover_mdns("IR-Remote-Mini")
    
    # Method 2: Network scanning
    for ip in network_range:
        try:
            response = await http_get(f"http://{ip}/api/status")
            if response.get("deviceType") == "mini":
                devices.append(create_device(ip, response))
        except:
            continue
    
    return devices
```

### OTA Update Process:
1. **Pre-update checks**:
   - Verify device is online
   - Check current firmware version
   - Ensure OTA is enabled
   - Validate firmware file

2. **Update methods** (in order of preference):
   - **ESP32 OTA Protocol**: Direct binary upload via espota.py
   - **Web API Upload**: HTTP POST to `/update` endpoint
   - **MQTT Triggered**: Send update command via MQTT

3. **Progress monitoring**:
   - Track upload progress
   - Monitor device reboot
   - Verify new firmware version
   - Handle update failures

### Service Definitions:
```yaml
# services.yaml
update_device:
  name: Update IR Remote Device
  description: Update firmware on a specific IR Remote device
  fields:
    device_id:
      name: Device ID
      description: The device identifier
      required: true
      selector:
        device:
          integration: ir_remote_ota
    firmware_file:
      name: Firmware File
      description: Path to firmware .bin file
      required: true
      selector:
        text:

update_all_devices:
  name: Update All IR Remote Devices
  description: Update firmware on all discovered devices
  fields:
    firmware_file:
      name: Firmware File
      description: Path to firmware .bin file
      required: true
    exclude_devices:
      name: Exclude Devices
      description: List of device IDs to exclude
      selector:
        device:
          integration: ir_remote_ota
          multiple: true
```

### Automation Examples:
```yaml
# Example automation for scheduled updates
automation:
  - alias: "IR Remote Firmware Update Check"
    trigger:
      - platform: time
        at: "02:00:00"  # 2 AM daily check
    condition:
      - condition: template
        value_template: "{{ states('sensor.ir_remote_firmware_available') != 'unknown' }}"
    action:
      - service: ir_remote_ota.update_all_devices
        data:
          firmware_file: "{{ states('sensor.ir_remote_latest_firmware') }}"

  # Notification for failed updates
  - alias: "IR Remote Update Failed"
    trigger:
      - platform: state
        entity_id: sensor.ir_remote_update_status
        to: "failed"
    action:
      - service: notify.mobile_app
        data:
          title: "IR Remote Update Failed"
          message: "Device {{ trigger.to_state.attributes.device_name }} failed to update"
```

### Dashboard Cards:
```yaml
# Lovelace card configuration
type: entities
title: IR Remote Devices
entities:
  - entity: sensor.living_room_ir_firmware
    name: "Living Room - Firmware"
  - entity: sensor.living_room_ir_status
    name: "Living Room - Status"
  - entity: switch.living_room_ir_ota
    name: "Living Room - OTA Enabled"
  - entity: sensor.bedroom_ir_firmware
    name: "Bedroom - Firmware"
  - entity: sensor.bedroom_ir_status
    name: "Bedroom - Status"
  - entity: switch.bedroom_ir_ota
    name: "Bedroom - OTA Enabled"

type: button
tap_action:
  action: call-service
  service: ir_remote_ota.update_all_devices
  service_data:
    firmware_file: "/config/ir_remote_firmware/latest.bin"
name: "Update All IR Remotes"
icon: mdi:upload
```

## Error Handling Requirements

### Network Issues:
- Retry logic for failed connections
- Timeout handling for slow networks
- Graceful degradation when devices are offline

### Update Failures:
- Automatic rollback on failed updates
- Backup of current firmware before update
- Recovery mode detection and handling

### Monitoring:
- Update success/failure rates
- Device health monitoring
- Firmware version compliance tracking

## Security Considerations

### Authentication:
- Store OTA passwords securely in HA secrets
- Support for device-specific authentication
- Optional certificate-based authentication

### Network Security:
- Validate firmware signatures
- Secure firmware storage
- Network isolation options for update process

## Expected Integration Behavior

### Installation:
1. User installs custom integration via HACS or manual installation
2. Integration auto-discovers IR Remote devices on network
3. Creates device entities and sensors automatically
4. Provides services for manual and automated updates

### Daily Operation:
1. Monitors devices continuously
2. Checks for firmware updates
3. Provides status dashboard
4. Enables scheduled maintenance windows
5. Sends notifications for important events

### Update Process:
1. User uploads new firmware to HA firmware directory
2. Integration validates firmware compatibility
3. User triggers update via service call or automation
4. Integration handles OTA update process
5. Monitors progress and reports status
6. Verifies successful update completion

## File Structure for Implementation

Please create the complete Home Assistant custom integration with:
- Device discovery and monitoring
- OTA update management
- Configuration flow for setup
- Services for manual and automated updates
- Sensor entities for device status
- Switch entities for OTA control
- Error handling and logging
- Documentation and examples

The integration should be production-ready with proper error handling, logging, and user-friendly configuration options.
