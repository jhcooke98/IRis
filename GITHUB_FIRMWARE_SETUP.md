# GitHub Firmware Source Setup Guide

This guide explains how to configure the IR Remote OTA integration to use GitHub as a firmware source, enabling centralized firmware management and automatic updates.

## Benefits of GitHub Firmware Source

- **Centralized Management**: Single source of truth for all firmware versions
- **Version Control**: Full git history of firmware changes
- **Automatic Detection**: Integration automatically detects new firmware releases
- **Team Collaboration**: Multiple developers can contribute firmware updates
- **Backup & Recovery**: GitHub serves as reliable firmware backup
- **CI/CD Integration**: Automatic building and deployment via GitHub Actions

## Setup Requirements

### 1. GitHub Repository Structure

Your repository should have firmware files organized in a dedicated directory:

```
your-repo/
├── firmware/                    # Firmware directory (configurable)
│   ├── ir_remote_v1.0.0.bin    # Firmware files with version naming
│   ├── ir_remote_v1.1.0.bin
│   ├── ir_remote_v2.0.0.bin
│   └── latest.bin              # Optional symlink to latest version
├── arduino_project/            # Your Arduino source code
├── .github/                    # GitHub Actions workflows
│   └── workflows/
│       └── firmware-release.yml
└── README.md
```

### 2. Firmware File Naming Convention

Firmware files must follow this naming pattern for version detection:
```
ir_remote_v<MAJOR>.<MINOR>.<PATCH>.bin
```

Examples:
- ✅ `ir_remote_v1.0.0.bin`
- ✅ `ir_remote_v2.1.5.bin` 
- ✅ `firmware_v1.2.3.bin`
- ❌ `firmware.bin` (no version)
- ❌ `ir_remote_1.0.0.bin` (missing 'v')

## Configuration Steps

### 1. Configure Home Assistant Integration

1. **Add Integration**: Go to Settings → Integrations → Add Integration → "IR Remote OTA"

2. **Select GitHub Source**:
   - **Firmware Source Type**: Select "GitHub"
   - **GitHub Repository**: Enter in format `owner/repo` (e.g., `jhcooke98/IRis`)
   - **Firmware Path**: Path to firmware directory in repo (default: `firmware`)
   - **Auto Download**: Enable to automatically download firmware files
   - **GitHub Token**: Optional, only needed for private repositories

3. **Other Settings**:
   - Configure device discovery and update intervals as needed
   - Set OTA password to match your devices

### 2. GitHub Personal Access Token (Optional)

Only required for private repositories:

1. **Generate Token**:
   - Go to GitHub → Settings → Developer settings → Personal access tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo` (for private repos) or `public_repo` (for public repos)
   - Copy the generated token

2. **Add to Integration**:
   - Paste the token in the "GitHub Token" field during setup
   - Or update via Integration Options

### 3. Test Configuration

1. **Verify Repository Access**:
   ```yaml
   # Test service call to check GitHub connection
   service: ir_remote_ota.sync_github_firmware
   ```

2. **Check Logs**: Look for successful firmware detection in Home Assistant logs

3. **Monitor Entities**: 
   - `sensor.ir_remote_latest_firmware` should show the latest version
   - `sensor.ir_remote_updates_available` should show devices needing updates

## Workflow Integration

### Automatic Firmware Building (Recommended)

Use the provided GitHub Actions workflow to automatically build and release firmware:

1. **Copy Workflow**: Place `.github/workflows/firmware-release.yml` in your repository

2. **Configure Workflow**:
   - Triggers on changes to Arduino code
   - Builds firmware using Arduino CLI
   - Commits built firmware to repository
   - Creates GitHub releases
   - Notifies Home Assistant (optional)

3. **Manual Releases**:
   - Go to GitHub → Actions → "Build and Release IR Remote Firmware"
   - Click "Run workflow"
   - Enter version number
   - Workflow builds and releases automatically

### Manual Firmware Deployment

For manual deployment without GitHub Actions:

1. **Build Firmware Locally**:
   ```bash
   ./build_firmware.sh  # Use provided build script
   ```

2. **Commit to Repository**:
   ```bash
   git add firmware/ir_remote_v1.2.3.bin
   git commit -m "Release firmware v1.2.3"
   git push
   ```

3. **Sync in Home Assistant**:
   ```yaml
   service: ir_remote_ota.sync_github_firmware
   ```

## Advanced Configuration

### Multiple Repository Support

You can use different repositories for different device types by creating multiple integration instances:

```yaml
# Integration 1: Main IR Remotes
github_repo: "jhcooke98/IRis"
github_path: "firmware"

# Integration 2: Beta Testing
github_repo: "jhcooke98/IRis-Beta" 
github_path: "beta-firmware"
```

### Branch-Specific Firmware

Use different branches for different firmware channels:

```yaml
# Production firmware
github_repo: "jhcooke98/IRis"
github_path: "firmware"

# Development firmware  
github_repo: "jhcooke98/IRis"
github_path: "dev-firmware"
```

### Private Repository Security

For enhanced security with private repositories:

1. **Create Deploy Key**: Instead of personal access token
2. **Limit Token Scope**: Use minimal required permissions
3. **Use Organization Secrets**: For team repositories
4. **Regular Token Rotation**: Update tokens periodically

## Monitoring and Automation

### Update Notifications

Create automations to notify when new firmware is available:

```yaml
automation:
  - alias: "New Firmware Available from GitHub"
    trigger:
      - platform: state
        entity_id: sensor.ir_remote_latest_firmware
    condition:
      - condition: template
        value_template: "{{ trigger.from_state.state != trigger.to_state.state }}"
    action:
      - service: notify.mobile_app
        data:
          title: "New IR Remote Firmware Available"
          message: >
            Version {{ trigger.to_state.state }} is now available from GitHub.
            Current devices will be updated automatically.
```

### Automatic Deployment

Set up automatic deployment during maintenance windows:

```yaml
automation:
  - alias: "Auto Deploy GitHub Firmware"
    trigger:
      - platform: time
        at: "03:00:00"  # 3 AM maintenance window
    condition:
      - condition: template
        value_template: "{{ states('sensor.ir_remote_updates_available') | int > 0 }}"
      - condition: time
        weekday: [sun]  # Sunday only
    action:
      - service: ir_remote_ota.sync_github_firmware
      - delay: "00:02:00"
      - service: ir_remote_ota.update_all_devices
```

## Troubleshooting

### Common Issues

1. **Repository Not Found**:
   - Verify repository name format: `owner/repo`
   - Check repository is public or token has access
   - Ensure firmware path exists in repository

2. **No Firmware Detected**:
   - Verify firmware files follow naming convention
   - Check files are in specified directory path
   - Ensure files have `.bin` extension

3. **Download Failures**:
   - Check network connectivity from Home Assistant
   - Verify GitHub API rate limits
   - Ensure local directory is writable

4. **Token Issues**:
   - Verify token has correct scopes
   - Check token hasn't expired
   - Test token with GitHub API manually

### Debug Steps

1. **Check Integration Logs**:
   ```yaml
   logger:
     logs:
       custom_components.ir_remote_ota: debug
   ```

2. **Test GitHub API Access**:
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" \
        https://api.github.com/repos/owner/repo/contents/firmware
   ```

3. **Verify Repository Structure**:
   - Browse repository on GitHub web interface
   - Confirm firmware files are present and named correctly

## Best Practices

### Security
- Use minimal token permissions
- Regularly rotate access tokens
- Consider using deploy keys for production
- Store tokens securely in Home Assistant secrets

### Versioning
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Tag releases in git for version tracking
- Maintain changelog for firmware updates
- Test firmware before releasing

### Reliability
- Keep backup of firmware files
- Test integration configuration in development
- Monitor Home Assistant logs for errors
- Set up alerting for failed updates

### Performance
- Enable auto-download only if needed
- Set appropriate cache intervals
- Use GitHub releases for large files
- Monitor GitHub API rate limits

## Example Repository

See the main IRis repository for a complete example:
- Repository: [jhcooke98/IRis](https://github.com/jhcooke98/IRis)
- Firmware Directory: `/firmware/`
- GitHub Actions: `.github/workflows/firmware-release.yml`
- Documentation: Complete setup and usage guides
