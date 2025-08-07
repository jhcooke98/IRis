#!/bin/bash
# Build and Deploy Script for IR Remote Mini Firmware
# This script compiles the Arduino firmware and copies it to the firmware directory

set -e  # Exit on any error

# Configuration
ARDUINO_CLI_PATH="arduino-cli"  # Path to arduino-cli binary
BOARD="esp32:esp32:esp32"       # ESP32 board specification
SKETCH_DIR="./arduino_project"   # Path to your Arduino sketch directory
FIRMWARE_DIR="./firmware"       # Firmware output directory
VERSION_FILE="version.txt"      # File containing current version

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if arduino-cli is installed
check_arduino_cli() {
    if ! command -v $ARDUINO_CLI_PATH &> /dev/null; then
        log_error "arduino-cli not found. Please install it first."
        log_info "Download from: https://arduino.github.io/arduino-cli/latest/installation/"
        exit 1
    fi
    log_success "arduino-cli found"
}

# Check if sketch directory exists
check_sketch_dir() {
    if [ ! -d "$SKETCH_DIR" ]; then
        log_error "Sketch directory not found: $SKETCH_DIR"
        log_info "Please update SKETCH_DIR in this script to point to your Arduino project"
        exit 1
    fi
    log_success "Sketch directory found: $SKETCH_DIR"
}

# Get current version from file or ask user
get_version() {
    if [ -f "$VERSION_FILE" ]; then
        CURRENT_VERSION=$(cat "$VERSION_FILE")
        log_info "Current version: $CURRENT_VERSION"
        
        # Suggest next version
        IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
        MAJOR=${VERSION_PARTS[0]}
        MINOR=${VERSION_PARTS[1]}
        PATCH=${VERSION_PARTS[2]}
        
        SUGGESTED_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
        
        echo -n "Enter new version [$SUGGESTED_VERSION]: "
        read NEW_VERSION
        
        if [ -z "$NEW_VERSION" ]; then
            NEW_VERSION=$SUGGESTED_VERSION
        fi
    else
        echo -n "Enter firmware version (e.g., 1.0.0): "
        read NEW_VERSION
    fi
    
    # Validate version format
    if [[ ! $NEW_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "Invalid version format. Use MAJOR.MINOR.PATCH (e.g., 1.0.0)"
        exit 1
    fi
    
    log_info "Building version: $NEW_VERSION"
}

# Update version in Arduino code
update_version_in_code() {
    local version_header="$SKETCH_DIR/version.h"
    
    # Create or update version.h file
    cat > "$version_header" << EOF
#ifndef VERSION_H
#define VERSION_H

#define FIRMWARE_VERSION "$NEW_VERSION"

#endif
EOF
    
    log_success "Updated version.h with version $NEW_VERSION"
}

# Compile the firmware
compile_firmware() {
    log_info "Compiling firmware..."
    
    # Find the main sketch file
    SKETCH_FILE=$(find "$SKETCH_DIR" -name "*.ino" | head -1)
    if [ -z "$SKETCH_FILE" ]; then
        log_error "No .ino file found in $SKETCH_DIR"
        exit 1
    fi
    
    log_info "Compiling sketch: $SKETCH_FILE"
    
    # Compile the sketch
    $ARDUINO_CLI_PATH compile --fqbn $BOARD "$SKETCH_FILE" --output-dir "$SKETCH_DIR/build"
    
    if [ $? -eq 0 ]; then
        log_success "Compilation successful"
    else
        log_error "Compilation failed"
        exit 1
    fi
}

# Copy firmware to repository
deploy_firmware() {
    log_info "Deploying firmware to repository..."
    
    # Find the compiled binary
    BINARY_FILE=$(find "$SKETCH_DIR/build" -name "*.bin" | head -1)
    if [ -z "$BINARY_FILE" ]; then
        log_error "No .bin file found in build directory"
        exit 1
    fi
    
    # Create firmware directory if it doesn't exist
    mkdir -p "$FIRMWARE_DIR"
    
    # Copy firmware with version name
    FIRMWARE_FILENAME="ir_remote_v${NEW_VERSION}.bin"
    FIRMWARE_PATH="$FIRMWARE_DIR/$FIRMWARE_FILENAME"
    
    cp "$BINARY_FILE" "$FIRMWARE_PATH"
    
    if [ $? -eq 0 ]; then
        log_success "Firmware deployed: $FIRMWARE_PATH"
        
        # Update version file
        echo "$NEW_VERSION" > "$VERSION_FILE"
        
        # Calculate file size
        FILE_SIZE=$(stat -c%s "$FIRMWARE_PATH" 2>/dev/null || stat -f%z "$FIRMWARE_PATH" 2>/dev/null)
        log_info "Firmware size: $FILE_SIZE bytes"
        
        # Create symlink to latest (optional)
        if command -v ln &> /dev/null; then
            cd "$FIRMWARE_DIR"
            ln -sf "$FIRMWARE_FILENAME" "latest.bin"
            cd - > /dev/null
            log_info "Created symlink: latest.bin -> $FIRMWARE_FILENAME"
        fi
    else
        log_error "Failed to deploy firmware"
        exit 1
    fi
}

# Git operations (optional)
git_commit() {
    if [ -d ".git" ]; then
        read -p "Commit changes to git? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git add "$FIRMWARE_PATH" "$VERSION_FILE"
            git commit -m "Release firmware v$NEW_VERSION"
            log_success "Changes committed to git"
            
            # Optionally create tag
            read -p "Create git tag v$NEW_VERSION? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git tag "v$NEW_VERSION"
                log_success "Created git tag v$NEW_VERSION"
            fi
        fi
    fi
}

# Cleanup build files
cleanup() {
    if [ -d "$SKETCH_DIR/build" ]; then
        read -p "Clean build directory? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$SKETCH_DIR/build"
            log_success "Build directory cleaned"
        fi
    fi
}

# Display summary
show_summary() {
    echo
    log_success "Build and deployment complete!"
    echo "=========================="
    echo "Version: $NEW_VERSION"
    echo "Firmware: $FIRMWARE_PATH"
    echo "Size: $FILE_SIZE bytes"
    echo
    echo "Next steps:"
    echo "1. Test the firmware on a single device"
    echo "2. Use Home Assistant integration to deploy updates"
    echo "3. Monitor device status after update"
    echo
}

# Main execution
main() {
    log_info "IR Remote Mini Firmware Build Script"
    echo "====================================="
    
    check_arduino_cli
    check_sketch_dir
    get_version
    update_version_in_code
    compile_firmware
    deploy_firmware
    git_commit
    cleanup
    show_summary
}

# Show help
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "IR Remote Mini Firmware Build Script"
    echo
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --help, -h     Show this help message"
    echo "  --version      Show current version"
    echo
    echo "Configuration:"
    echo "  Edit the variables at the top of this script to match your setup:"
    echo "  - ARDUINO_CLI_PATH: Path to arduino-cli binary"
    echo "  - BOARD: ESP32 board specification"
    echo "  - SKETCH_DIR: Path to your Arduino sketch directory"
    echo "  - FIRMWARE_DIR: Firmware output directory"
    echo
    echo "Prerequisites:"
    echo "  1. Install arduino-cli"
    echo "  2. Install ESP32 board package"
    echo "  3. Set up your Arduino sketch with proper structure"
    echo
    exit 0
fi

# Show version
if [ "$1" = "--version" ]; then
    if [ -f "$VERSION_FILE" ]; then
        echo "Current version: $(cat $VERSION_FILE)"
    else
        echo "No version file found"
    fi
    exit 0
fi

# Run main function
main
