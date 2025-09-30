#!/bin/bash
# Uninstall Claude Power Manager systemd service

set -e

echo "Uninstalling Claude Power Manager systemd service..."

# Check if running as root or with sudo
if [ "$EUID" -eq 0 ]; then
    echo "Error: Do not run this script as root. It will use sudo when needed."
    exit 1
fi

# Stop service if running
echo "Stopping service..."
sudo systemctl stop claude-power-manager.service 2>/dev/null || true

# Disable service
echo "Disabling service..."
sudo systemctl disable claude-power-manager.service 2>/dev/null || true

# Remove service file
echo "Removing service file..."
sudo rm -f /etc/systemd/system/claude-power-manager.service

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo ""
echo "✓ Service uninstalled successfully!"