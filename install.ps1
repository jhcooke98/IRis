# IRis IR Remote Integration Installation Script for Windows
# This script helps install the custom integration to Home Assistant

param(
    [Parameter(Mandatory=$true)]
    [string]$HomeAssistantConfigPath
)

# Function to write colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

$CustomComponentsDir = Join-Path $HomeAssistantConfigPath "custom_components"
$IntegrationDir = Join-Path $CustomComponentsDir "iris_ir_remote"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceDir = Join-Path $ScriptDir "iris_ir_remote"

Write-Status "Installing IRis IR Remote Integration..."
Write-Status "Home Assistant config directory: $HomeAssistantConfigPath"
Write-Status "Source directory: $SourceDir"

# Verify Home Assistant config directory exists
if (-not (Test-Path $HomeAssistantConfigPath)) {
    Write-Error "Home Assistant config directory not found: $HomeAssistantConfigPath"
    exit 1
}

# Verify source directory exists
if (-not (Test-Path $SourceDir)) {
    Write-Error "Source directory not found: $SourceDir"
    Write-Error "Make sure you're running this script from the correct location"
    exit 1
}

# Create custom_components directory if it doesn't exist
if (-not (Test-Path $CustomComponentsDir)) {
    Write-Status "Creating custom_components directory..."
    New-Item -ItemType Directory -Path $CustomComponentsDir -Force | Out-Null
}

# Remove existing installation if it exists
if (Test-Path $IntegrationDir) {
    Write-Warning "Existing installation found. Removing..."
    Remove-Item -Path $IntegrationDir -Recurse -Force
}

# Copy the integration files
Write-Status "Copying integration files..."
Copy-Item -Path $SourceDir -Destination $IntegrationDir -Recurse -Force

# Verify installation
Write-Status "Verifying installation..."
$RequiredFiles = @(
    "__init__.py",
    "manifest.json",
    "config_flow.py",
    "const.py",
    "coordinator.py",
    "remote.py",
    "sensor.py",
    "binary_sensor.py",
    "services.py",
    "services.yaml",
    "strings.json"
)

$MissingFiles = @()
foreach ($file in $RequiredFiles) {
    $filePath = Join-Path $IntegrationDir $file
    if (-not (Test-Path $filePath)) {
        $MissingFiles += $file
    }
}

if ($MissingFiles.Count -eq 0) {
    Write-Success "Installation completed successfully!"
    Write-Status "Integration installed to: $IntegrationDir"
    Write-Host ""
    Write-Status "Next steps:"
    Write-Host "1. Restart Home Assistant"
    Write-Host "2. Go to Configuration → Integrations"
    Write-Host "3. Click 'Add Integration'"
    Write-Host "4. Search for 'IRis IR Remote Integration'"
    Write-Host "5. Enter your device IP address and port"
    Write-Host ""
    Write-Warning "Remember to restart Home Assistant for the integration to be recognized!"
} else {
    Write-Error "Installation incomplete. Missing files:"
    foreach ($file in $MissingFiles) {
        Write-Error "  - $file"
    }
    exit 1
}

# Usage example
Write-Host ""
Write-Host "Example usage:" -ForegroundColor Cyan
Write-Host "  .\install.ps1 -HomeAssistantConfigPath 'C:\Users\YourUser\.homeassistant'" -ForegroundColor Cyan
