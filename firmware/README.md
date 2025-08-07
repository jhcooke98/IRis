# IR Remote Firmware Directory

This directory contains firmware files for IR Remote Mini devices managed by the Home Assistant OTA integration.

## Firmware Naming Convention

Firmware files should be named using the following pattern:
```
ir_remote_v<version>.bin
```

Examples:
- `ir_remote_v1.0.0.bin`
- `ir_remote_v1.2.3.bin`
- `ir_remote_v2.0.0.bin`

## Version Format

Use semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible functionality additions
- **PATCH**: Backward-compatible bug fixes

## Directory Structure

```
firmware/
├── README.md              # This file
├── ir_remote_v1.0.0.bin   # Example firmware file
├── ir_remote_v1.1.0.bin   # Example firmware file
└── latest -> ir_remote_v1.1.0.bin  # Symlink to latest version (optional)
```

## Integration Behavior

The Home Assistant integration will:

1. **Scan this directory** for `.bin` files every hour (configurable)
2. **Extract version numbers** from filenames
3. **Determine the latest version** by comparing version numbers
4. **Compare with device versions** to detect available updates
5. **Notify** when updates are available
6. **Perform OTA updates** when requested

## Adding New Firmware

To add new firmware:

1. **Compile your Arduino firmware** to a `.bin` file
2. **Name the file** using the version convention above
3. **Copy the file** to this directory
4. **Verify the integration detects** the new version (check sensor states)
5. **Test the update** on a single device before bulk updates

## Firmware Validation

The integration performs basic validation:
- File must have `.bin` extension
- Filename must contain a valid version number
- File must be readable and non-empty

**Note**: The integration does NOT validate firmware compatibility with devices. Ensure you're uploading correct firmware for your ESP32 devices.

## Automatic Updates

You can configure automations to:
- **Auto-update devices** during maintenance windows
- **Notify** when new firmware is detected
- **Update specific devices** based on conditions

See the integration documentation for automation examples.

## Backup and Rollback

While the integration doesn't automatically backup firmware, you should:
- **Keep previous versions** in this directory for rollback capability
- **Test new firmware** thoroughly before deployment
- **Have a recovery plan** if updates fail

## Security Notes

- **Secure this directory** appropriately (file permissions)
- **Validate firmware sources** before deployment
- **Use HTTPS** for firmware downloads if fetching remotely
- **Consider firmware signing** for production environments
