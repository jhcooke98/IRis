## IRis IR Remote Integration

Integrate your IRis IR Remote devices with Home Assistant for complete smart home control.

### Features

- **Device Discovery**: Add devices by IP address with automatic validation
- **Multiple Device Support**: Manage multiple IRis IR Remote devices from one integration
- **MQTT Real-time Updates**: Real-time button press detection when MQTT is enabled
- **Individual Button Entities**: Each Arduino button gets its own binary sensor for precise automations
- **Remote Control**: Send IR commands through Home Assistant
- **Status Monitoring**: Monitor device status, connectivity, and learned buttons
- **Web UI Access**: Direct access to device web interfaces
- **Learning Mode**: Start/stop learning mode remotely

### Quick Setup

1. Install via HACS
2. Restart Home Assistant
3. Go to Configuration → Integrations → Add Integration
4. Search for "IRis IR Remote Integration"
5. Enter your device IP address

### What you get

**Entities per device:**
- Remote control entities (main + individual learned remotes)
- Real-time button sensors (with MQTT)
- Status sensors (uptime, button count, connectivity)
- Binary sensors (WiFi, MQTT, learning mode status)
- Individual button entities for precise automations

**Services:**
- Send button commands
- Start/stop learning mode
- Restart device
- Open web interface

Perfect for IR automation, multi-room control, and integration with existing smart home setups.
