#!/bin/bash
# Claude Code Power Manager - Installation Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "Claude Code Power Manager - Installation"
echo "======================================================================"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "  Found Python $PYTHON_VERSION"

# Check required Python packages
echo ""
echo "Checking required Python packages..."

REQUIRED_PACKAGES=("psutil" "PyYAML")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import ${package,,}" 2>/dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo "  Missing packages: ${MISSING_PACKAGES[*]}"
    echo ""
    read -p "Install missing packages? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing packages..."
        pip3 install --user "${MISSING_PACKAGES[@]}"
    else
        echo "Installation aborted. Please install required packages manually:"
        echo "  pip3 install --user ${MISSING_PACKAGES[*]}"
        exit 1
    fi
else
    echo "  ✓ All required packages found"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p logs state
echo "  ✓ Created logs/ and state/ directories"

# Setup configuration
echo ""
echo "Setting up configuration..."

if [ ! -f "config/secrets.yaml" ]; then
    echo "  Creating secrets.yaml from example..."
    cp config/secrets.yaml.example config/secrets.yaml
    echo "  ✓ Created config/secrets.yaml (edit this file to add credentials)"
else
    echo "  ✓ config/secrets.yaml already exists"
fi

# Test installation
echo ""
echo "Testing installation..."

if python3 claude-power-daemon.py --help &>/dev/null; then
    echo "  ✓ Daemon script works"
else
    echo "  ✗ Error: Daemon script failed"
    exit 1
fi

if python3 claude-ctl --help &>/dev/null; then
    echo "  ✓ CLI tool works"
else
    echo "  ✗ Error: CLI tool failed"
    exit 1
fi

# Create symlinks
echo ""
echo "Creating command symlinks..."

INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

ln -sf "$SCRIPT_DIR/claude-ctl" "$INSTALL_DIR/claude-ctl"
echo "  ✓ Created symlink: $INSTALL_DIR/claude-ctl"

# Check if .local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "⚠️  Warning: $HOME/.local/bin is not in your PATH"
    echo "   Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Offer to install systemd service
echo ""
read -p "Install as systemd service? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    bash scripts/install-systemd.sh
fi

# Summary
echo ""
echo "======================================================================"
echo "Installation Complete!"
echo "======================================================================"
echo ""
echo "Quick Start:"
echo ""
echo "  1. Check system status:"
echo "     claude-ctl status"
echo ""
echo "  2. Monitor thermal state:"
echo "     claude-ctl thermal"
echo ""
echo "  3. Start daemon manually:"
echo "     ./claude-power-daemon.py"
echo ""
echo "  4. Or if you installed systemd service:"
echo "     sudo systemctl start claude-power-manager"
echo "     journalctl -u claude-power-manager -f"
echo ""
echo "Documentation: README.md"
echo "Configuration: config/default.yaml"
echo "Secrets: config/secrets.yaml"
echo ""