#!/bin/bash

# IRis IR Remote Integration Installation Script
# This script helps install the custom integration to Home Assistant

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Home Assistant directory is provided
if [ -z "$1" ]; then
    print_error "Usage: $0 <path-to-home-assistant-config>"
    print_error "Example: $0 /home/homeassistant/.homeassistant"
    exit 1
fi

HA_CONFIG_DIR="$1"
CUSTOM_COMPONENTS_DIR="$HA_CONFIG_DIR/custom_components"
INTEGRATION_DIR="$CUSTOM_COMPONENTS_DIR/iris_ir_remote"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/iris_ir_remote"

print_status "Installing IRis IR Remote Integration..."
print_status "Home Assistant config directory: $HA_CONFIG_DIR"
print_status "Source directory: $SOURCE_DIR"

# Verify Home Assistant config directory exists
if [ ! -d "$HA_CONFIG_DIR" ]; then
    print_error "Home Assistant config directory not found: $HA_CONFIG_DIR"
    exit 1
fi

# Verify source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    print_error "Source directory not found: $SOURCE_DIR"
    print_error "Make sure you're running this script from the correct location"
    exit 1
fi

# Create custom_components directory if it doesn't exist
if [ ! -d "$CUSTOM_COMPONENTS_DIR" ]; then
    print_status "Creating custom_components directory..."
    mkdir -p "$CUSTOM_COMPONENTS_DIR"
fi

# Remove existing installation if it exists
if [ -d "$INTEGRATION_DIR" ]; then
    print_warning "Existing installation found. Removing..."
    rm -rf "$INTEGRATION_DIR"
fi

# Copy the integration files
print_status "Copying integration files..."
cp -r "$SOURCE_DIR" "$INTEGRATION_DIR"

# Verify installation
print_status "Verifying installation..."
REQUIRED_FILES=(
    "__init__.py"
    "manifest.json"
    "config_flow.py"
    "const.py"
    "coordinator.py"
    "remote.py"
    "sensor.py"
    "binary_sensor.py"
    "services.py"
    "services.yaml"
    "strings.json"
)

MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$INTEGRATION_DIR/$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
    print_success "Installation completed successfully!"
    print_status "Integration installed to: $INTEGRATION_DIR"
    echo
    print_status "Next steps:"
    echo "1. Restart Home Assistant"
    echo "2. Go to Configuration → Integrations"
    echo "3. Click 'Add Integration'"
    echo "4. Search for 'IRis IR Remote Integration'"
    echo "5. Enter your device IP address and port"
    echo
    print_warning "Remember to restart Home Assistant for the integration to be recognized!"
else
    print_error "Installation incomplete. Missing files:"
    for file in "${MISSING_FILES[@]}"; do
        print_error "  - $file"
    done
    exit 1
fi
