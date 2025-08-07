# IRis IR Remote Home Assistant Integration Guide

## Overview

This guide walks you through setting up the custom Home Assistant integration for your IRis IR Remote devices. The integration provides full control over your devices, including sending IR commands, monitoring status, and accessing the web interface directly from Home Assistant.

### Hybrid Communication: HTTP + MQTT

The integration automatically detects your device's capabilities and sets up the optimal communication method:

- **HTTP REST API**: Used for device control (sending commands, configuration)
- **MQTT (Auto-detected)**: Used for real-time updates when available

**Benefits of the hybrid approach:**
- **Instant updates**: Button presses appear immediately via MQTT (no 10-second delay)
- **Reliable control**: Commands sent via HTTP for guaranteed delivery
- **Automatic fallback**: Works with HTTP-only if MQTT is not configured
- **Best of both worlds**: Real-time responsiveness with reliable control

## Quick Start

### 1. Install the Integration

#### Automatic Installation (Recommended)

**For Linux/macOS:**
```bash
./install.sh /path/to/homeassistant/config
```

**For Windows:**
```powershell
.\install.ps1 -HomeAssistantConfigPath "C:\path\to\homeassistant\config"
```

#### Manual Installation

1. Copy the `iris_ir_remote` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. The integration will appear in the integrations list

### 2. Add Your Device

1. Go to **Configuration** → **Integrations**
2. Click **Add Integration**
3. Search for **IRis IR Remote Integration**
4. Enter your device information:
   - **Host**: IP address of your IRis device (e.g., `192.168.1.100`)
   - **Port**: Usually `80`
   - **Name**: Friendly name (optional)

### 3. Configure Communication Method (Automatic)

The integration automatically detects your device's capabilities:

**If your device has MQTT enabled:**
- ✅ **Real-time updates** via MQTT (instant button press detection)
- ✅ **Reliable control** via HTTP (send commands, configuration)
- ✅ **Reduced polling** (30-second intervals instead of 10)
- ✅ **Best responsiveness** (updates appear within milliseconds)

**If your device only has HTTP:**
- ✅ **Standard polling** every 10 seconds (configurable to 2-5 seconds)
- ✅ **Full functionality** via HTTP REST API
- ⚠️ **Slight delay** for status updates (polling interval)

### 4. Configure Update Settings (Optional)

After adding the device, you can adjust the update frequency:
1. Click **Configure** on your IRis device in the integrations list
2. Adjust **Update interval**:
   - **With MQTT**: Default 30 seconds (since real-time updates come via MQTT)
   - **HTTP only**: Default 10 seconds (recommended: 2-10 seconds for responsiveness)
   - Lower values = more responsive updates but higher network traffic

### 5. Start Using Your Device

Once added, you'll see:
- **Remote entities** for each learned remote
- **HTTP sensors** for device status (polling-based)
- **MQTT sensors** for real-time updates (if device supports MQTT)
- **Binary sensors** for connectivity
- **Services** for device control

### Real-time vs Polling Entities

**MQTT Real-time Entities** (if available):
- `sensor.iris_mqtt_button_[ip]` - Instant button press notifications
- `sensor.iris_mqtt_status_[ip]` - Real-time device status changes

**HTTP Polling Entities** (always available):
- `sensor.iris_last_button_[ip]` - Last button (updated every scan interval)
- `sensor.iris_uptime_[ip]` - Device uptime
- `sensor.iris_button_count_[ip]` - Number of learned buttons
- `sensor.iris_free_heap_[ip]` - Available memory

## Detailed Features

### Device Management

#### Multiple Device Support
- Add as many IRis devices as you want
- Each device appears as a separate integration instance
- Devices are identified by IP address and port

#### Web UI Integration
- Direct access to device web interface
- Configuration URL in device info
- Service to open web UI from automations

### Remote Control

#### Main Remote Entity
- Controls the entire device
- Turn on/off for learning mode
- Send commands using `remote.send_command`

#### Individual Remote Entities
- One entity per learned remote protocol
- Each has its own available commands
- Easy to organize by device type (TV, Stereo, etc.)

### Monitoring & Status

#### Real-time Status
- Last button pressed
- Device uptime
- Button count
- Memory usage
- Connection status

#### Connectivity Monitoring
- WiFi connection status
- MQTT connection status
- Automatic reconnection detection

### Services Available

#### Core Services
- `send_button`: Send specific IR commands
- `start_learning`: Begin learning new buttons
- `stop_learning`: Stop learning mode
- `restart_device`: Restart the device
- `open_web_ui`: Access device web interface

## Configuration Examples

### Basic Device Control

```yaml
# Send a single command
service: remote.send_command
target:
  entity_id: remote.sony_tv_192_168_1_100
data:
  command: "POWER"

# Send multiple commands
service: remote.send_command
target:
  entity_id: remote.sony_tv_192_168_1_100
data:
  command: ["POWER", "VOL_UP", "CH_UP"]
```

### Learning Mode Control

```yaml
# Start learning mode
service: remote.turn_on
target:
  entity_id: remote.iris_ir_remote_192_168_1_100

# Stop learning mode
service: remote.turn_off
target:
  entity_id: remote.iris_ir_remote_192_168_1_100
```

### Device Management

```yaml
# Restart device
service: iris_ir_remote.restart_device
target:
  entity_id: remote.iris_ir_remote_192_168_1_100

# Open web UI
service: iris_ir_remote.open_web_ui
target:
  entity_id: remote.iris_ir_remote_192_168_1_100
```

## Automation Examples

### Smart Learning Mode

```yaml
automation:
  - alias: "Smart IR Learning"
    trigger:
      - platform: state
        entity_id: input_boolean.learn_ir_button
        to: "on"
    action:
      - service: iris_ir_remote.start_learning
        target:
          entity_id: remote.iris_ir_remote_192_168_1_100
      - wait_for_trigger:
          - platform: state
            entity_id: sensor.iris_last_button_192_168_1_100
        timeout: "00:05:00"
      - service: iris_ir_remote.stop_learning
        target:
          entity_id: remote.iris_ir_remote_192_168_1_100
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.learn_ir_button
```

### Device Connectivity Monitoring

```yaml
automation:
  - alias: "IR Device Status Monitor"
    trigger:
      - platform: state
        entity_id: binary_sensor.iris_wifi_connected_192_168_1_100
        to: "off"
        for: "00:02:00"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "IR Device Offline"
          message: "IRis device {{ trigger.entity_id }} has gone offline"
          data:
            actions:
              - action: "RESTART_IR_DEVICE"
                title: "Restart Device"
```

### Button Press Logger (MQTT Real-time)

```yaml
automation:
  - alias: "Log IR Button Presses (Real-time)"
    trigger:
      - platform: state
        entity_id: sensor.iris_mqtt_button_192_168_1_100  # MQTT sensor for instant updates
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state not in ['unknown', 'unavailable'] }}"
    action:
      - service: logbook.log
        data:
          name: "IR Remote (Real-time)"
          message: "Button '{{ trigger.to_state.state }}' pressed ({{ trigger.to_state.attributes.protocol }})"
          entity_id: "{{ trigger.entity_id }}"
```

### Button Press Logger (HTTP Polling Fallback)

```yaml
automation:
  - alias: "Log IR Button Presses (Polling)"
    trigger:
      - platform: state
        entity_id: sensor.iris_last_button_192_168_1_100  # HTTP polling sensor
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state != 'None' }}"
    action:
      - service: logbook.log
        data:
          name: "IR Remote (Polling)"
          message: "Button '{{ trigger.to_state.state }}' pressed on {{ trigger.to_state.attributes.friendly_name }}"
          entity_id: "{{ trigger.entity_id }}"
```

## Lovelace Dashboard Examples

### Device Status Card

```yaml
type: entities
title: IRis IR Remote Status
entities:
  - entity: remote.iris_ir_remote_192_168_1_100
    name: Main Remote
    icon: mdi:remote
  - entity: sensor.iris_last_button_192_168_1_100
    name: Last Button
    icon: mdi:gesture-tap-button
  - entity: sensor.iris_uptime_192_168_1_100
    name: Uptime
    icon: mdi:clock-outline
  - entity: sensor.iris_button_count_192_168_1_100
    name: Learned Buttons
    icon: mdi:counter
  - entity: binary_sensor.iris_wifi_connected_192_168_1_100
    name: WiFi
    icon: mdi:wifi
  - entity: binary_sensor.iris_mqtt_connected_192_168_1_100
    name: MQTT
    icon: mdi:server-network
```

### Remote Control Grid

```yaml
type: grid
title: TV Remote Control
columns: 3
cards:
  - type: button
    name: Power
    icon: mdi:power
    tap_action:
      action: call-service
      service: iris_ir_remote.send_button
      target:
        entity_id: remote.sony_tv_192_168_1_100
      service_data:
        button: "POWER"
  
  - type: button
    name: Vol +
    icon: mdi:volume-plus
    tap_action:
      action: call-service
      service: iris_ir_remote.send_button
      target:
        entity_id: remote.sony_tv_192_168_1_100
      service_data:
        button: "VOL_UP"
  
  - type: button
    name: Vol -
    icon: mdi:volume-minus
    tap_action:
      action: call-service
      service: iris_ir_remote.send_button
      target:
        entity_id: remote.sony_tv_192_168_1_100
      service_data:
        button: "VOL_DOWN"
  
  - type: button
    name: Ch +
    icon: mdi:chevron-up
    tap_action:
      action: call-service
      service: iris_ir_remote.send_button
      target:
        entity_id: remote.sony_tv_192_168_1_100
      service_data:
        button: "CH_UP"
  
  - type: button
    name: Mute
    icon: mdi:volume-off
    tap_action:
      action: call-service
      service: iris_ir_remote.send_button
      target:
        entity_id: remote.sony_tv_192_168_1_100
      service_data:
        button: "MUTE"
  
  - type: button
    name: Ch -
    icon: mdi:chevron-down
    tap_action:
      action: call-service
      service: iris_ir_remote.send_button
      target:
        entity_id: remote.sony_tv_192_168_1_100
      service_data:
        button: "CH_DOWN"
```

### Learning Mode Card

```yaml
type: vertical-stack
title: IR Learning Center
cards:
  - type: entities
    entities:
      - entity: binary_sensor.iris_learning_mode_192_168_1_100
        name: Learning Mode Status
      - entity: sensor.iris_last_button_192_168_1_100
        name: Last Captured
  
  - type: horizontal-stack
    cards:
      - type: button
        name: Start Learning
        icon: mdi:school
        tap_action:
          action: call-service
          service: iris_ir_remote.start_learning
          target:
            entity_id: remote.iris_ir_remote_192_168_1_100
      
      - type: button
        name: Stop Learning
        icon: mdi:stop
        tap_action:
          action: call-service
          service: iris_ir_remote.stop_learning
          target:
            entity_id: remote.iris_ir_remote_192_168_1_100
      
      - type: button
        name: Open Web UI
        icon: mdi:web
        tap_action:
          action: call-service
          service: iris_ir_remote.open_web_ui
          target:
            entity_id: remote.iris_ir_remote_192_168_1_100
```

## Advanced Configuration

### Multiple Devices Setup

```yaml
# Example for managing multiple IR devices
input_select:
  ir_device_selector:
    name: "Select IR Device"
    options:
      - "Living Room (192.168.1.100)"
      - "Bedroom (192.168.1.101)"
      - "Kitchen (192.168.1.102)"

automation:
  - alias: "Send Command to Selected Device"
    trigger:
      - platform: state
        entity_id: input_select.ir_button_selector
    action:
      - service: iris_ir_remote.send_button
        target:
          entity_id: >
            {% if states('input_select.ir_device_selector') == 'Living Room (192.168.1.100)' %}
              remote.iris_ir_remote_192_168_1_100
            {% elif states('input_select.ir_device_selector') == 'Bedroom (192.168.1.101)' %}
              remote.iris_ir_remote_192_168_1_101
            {% else %}
              remote.iris_ir_remote_192_168_1_102
            {% endif %}
        data:
          button: "{{ trigger.to_state.state }}"
```

### Custom Button Mapping

```yaml
# Map Home Assistant media player controls to IR commands
automation:
  - alias: "Media Player to IR - Power"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        attribute: state
        to: "on"
    action:
      - service: iris_ir_remote.send_button
        target:
          entity_id: remote.sony_tv_192_168_1_100
        data:
          button: "POWER"

  - alias: "Media Player to IR - Volume"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        attribute: volume_level
    action:
      - service: iris_ir_remote.send_button
        target:
          entity_id: remote.sony_tv_192_168_1_100
        data:
          button: >
            {% if trigger.to_state.attributes.volume_level > trigger.from_state.attributes.volume_level %}
              VOL_UP
            {% else %}
              VOL_DOWN
            {% endif %}
```

## Troubleshooting

### Understanding Communication Methods

#### MQTT Real-time Updates (Preferred)
If your device has MQTT configured, you'll get:
- **Instant button press detection** (within milliseconds)
- **Real-time learning mode status** 
- **Immediate device status changes**
- **Reduced network traffic** (less frequent HTTP polling)

To enable MQTT on your device:
1. Open the device web interface (http://device-ip)
2. Go to **Settings** → **MQTT Configuration**
3. Enter your Home Assistant MQTT broker details:
   - **Server**: Home Assistant IP address
   - **Port**: 1883 (default)
   - **Username/Password**: Your MQTT credentials
4. Save and restart the device

#### HTTP Polling Fallback
If MQTT is not available, the integration uses HTTP polling:
- **Status updates** every 10 seconds (configurable)
- **All functionality available** but with polling delays
- **More network traffic** due to frequent requests

### Automatic Updates Not Working

If entities don't update automatically after sending commands:

**For MQTT-enabled devices:**
1. **Check MQTT sensors**: Look for `sensor.iris_mqtt_button_*` entities
2. **Verify MQTT connection**: Check device web UI → Settings → MQTT status
3. **Home Assistant MQTT**: Ensure MQTT integration is configured in HA

**For HTTP-only devices:**
1. **Check Update Interval**: Go to Configuration → Integrations → IRis Device → Configure
   - Set update interval to 2-5 seconds for more responsive updates
   - Default is 10 seconds, but you can go lower for instant feedback

2. **Force Manual Update**: Use developer tools to force refresh:
   ```yaml
   service: homeassistant.update_entity
   target:
     entity_id: remote.iris_ir_remote_192_168_1_100
   ```

3. **Enable Debug Logging**: Add to configuration.yaml:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.iris_ir_remote: debug
   ```

4. **Check Device Connectivity**: Verify device responds to direct HTTP calls:
   ```bash
   curl http://192.168.1.100/api/status
   ```

### Common Issues

#### Device Not Discovered
- Check IP address and port
- Verify device is powered and connected to WiFi
- Test with curl: `curl http://192.168.1.100/api/status`

#### Entities Not Appearing
- Restart Home Assistant after installation
- Check logs for errors: Configuration → Logs
- Verify integration is properly installed

#### Commands Not Working
- Ensure button names match exactly (case-sensitive)
- Check if device is in learning mode
- Verify network connectivity

#### Web UI Not Opening
- Check if browser allows popups
- Verify device web interface is accessible
- Try opening URL manually

### Debugging

#### Enable Debug Logging

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.iris_ir_remote: debug
```

#### Check Device Status

```yaml
# Template sensor to monitor all device status
sensor:
  - platform: template
    sensors:
      ir_device_debug:
        friendly_name: "IR Device Debug Info"
        value_template: >
          {{ states('sensor.iris_last_button_192_168_1_100') }}
        attribute_templates:
          full_status: >
            {{ state_attr('remote.iris_ir_remote_192_168_1_100', 'extra_state_attributes') }}
```

## Best Practices

### Security
- Use dedicated VLAN for IoT devices
- Regular firmware updates
- Monitor device access logs

### Performance
- Adjust scan interval based on needs
- Use automation conditions to prevent spam
- Monitor Home Assistant performance impact

### Organization
- Use consistent naming conventions
- Group related entities in Lovelace
- Document your button mappings

### Maintenance
- Regular device restarts if needed
- Monitor connectivity status
- Keep integration updated

## Support & Development

### Getting Help
- Check the logs first
- Test device API endpoints manually
- Document specific error messages

### Contributing
- Report bugs with detailed logs
- Suggest feature improvements
- Share automation examples

### Future Enhancements
- HACS integration
- Device discovery via mDNS
- Bulk device configuration
- Integration with Home Assistant media players

This integration provides a solid foundation for controlling your IRis IR Remote devices from Home Assistant. The modular design allows for easy extension and customization based on your specific needs.
