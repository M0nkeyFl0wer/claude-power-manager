#!/bin/bash
# Install Claude Power Manager as systemd service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$PROJECT_DIR/systemd/claude-power-manager.service"

echo "Installing Claude Power Manager systemd service..."

# Check if running as root or with sudo
if [ "$EUID" -eq 0 ]; then
    echo "Error: Do not run this script as root. It will use sudo when needed."
    exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found: $SERVICE_FILE"
    exit 1
fi

# Copy service file to systemd directory
echo "Copying service file to /etc/systemd/system/..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/claude-power-manager.service

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service
echo "Enabling service to start on boot..."
sudo systemctl enable claude-power-manager.service

echo ""
echo "✓ Service installed successfully!"
echo ""
echo "Usage:"
echo "  sudo systemctl start claude-power-manager    # Start the service"
echo "  sudo systemctl stop claude-power-manager     # Stop the service"
echo "  sudo systemctl status claude-power-manager   # Check status"
echo "  sudo systemctl restart claude-power-manager  # Restart the service"
echo "  journalctl -u claude-power-manager -f        # View logs"
echo ""
echo "To start the service now, run:"
echo "  sudo systemctl start claude-power-manager"