# Claude Code Power Manager

**Intelligent thermal management and session orchestration for running multiple Claude Code instances efficiently on resource-constrained systems.**

Designed specifically for the Dell Inspiron 7472 (i5-8250U, 8GB RAM, Pop!_OS 22.04) but works on any Linux system.

## 🎯 Features

### Thermal Management
- ✅ Real-time CPU temperature monitoring from multiple thermal sensors
- ✅ Automatic thermal level detection (cool, normal, high, critical)
- ✅ Thermal-aware instance spawning (won't start new instances if temp > 80°C)
- ✅ Automatic session pausing when thermal limits approached
- ✅ CPU frequency and load monitoring
- ✅ Throttling detection and response

### Session Management
- ✅ Priority-based queue system (Critical, High, Normal, Low, Background)
- ✅ Automatic resource pooling and limits (CPU/memory)
- ✅ Session persistence across daemon restarts
- ✅ Idle session detection and cleanup
- ✅ Process group management for clean termination
- ✅ Real-time resource usage tracking per session

### Power Profiles
- ✅ **Battery Mode**: Conservative (max 2 instances, 60% CPU, 4GB RAM)
- ✅ **Plugged Mode**: Balanced (max 3 instances, 80% CPU, 6GB RAM)
- ✅ **Performance Mode**: Aggressive (max 4 instances, 90% CPU, 6.5GB RAM)
- ✅ Automatic profile switching based on AC adapter state

### Safety Features
- ✅ Emergency stop at critical temperatures
- ✅ Graceful degradation under thermal stress
- ✅ Minimum free memory enforcement
- ✅ Process group isolation
- ✅ Signal handling for clean shutdown

### Monitoring & Reporting
- ✅ Comprehensive action logging (all throttling decisions reported)
- ✅ Console output for important events
- ✅ Thermal state change notifications
- ✅ Session statistics and resource usage
- ✅ CLI dashboard for real-time monitoring

## 📦 Installation

### Prerequisites
- Python 3.7+
- Linux with sysfs thermal support
- pip3 (for dependencies)

### Quick Install

```bash
cd /home/monkeyflower/claude-power-manager
./install.sh
```

The installer will:
1. Check Python version and dependencies
2. Install missing packages (psutil, PyYAML)
3. Create necessary directories
4. Setup configuration files
5. Create command symlinks
6. Optionally install systemd service

### Manual Installation

```bash
# Install dependencies
pip3 install --user -r requirements.txt

# Create directories
mkdir -p logs state

# Copy secrets template
cp config/secrets.yaml.example config/secrets.yaml

# Make scripts executable
chmod +x claude-power-daemon.py claude-ctl install.sh
```

## 🚀 Usage

### Starting the Daemon

#### Option 1: Manual Start
```bash
# Start in foreground with console output
./claude-power-daemon.py

# Start with specific profile
./claude-power-daemon.py --profile performance

# Start with verbose logging
./claude-power-daemon.py --verbose
```

#### Option 2: Systemd Service
```bash
# Install service
./scripts/install-systemd.sh

# Start service
sudo systemctl start claude-power-manager

# Enable on boot
sudo systemctl enable claude-power-manager

# View logs
journalctl -u claude-power-manager -f
```

### CLI Management

#### Check System Status
```bash
claude-ctl status
```

Output includes:
- CPU temperature and thermal level
- CPU frequency and load average
- Session statistics (running, queued, paused, completed)
- Resource usage (CPU%, Memory MB)
- Recommendations and max instances

#### List Sessions
```bash
# List all sessions
claude-ctl list

# Filter by status
claude-ctl list --status running
claude-ctl list --status queued
```

#### Create New Session
```bash
# Create normal priority session
claude-ctl create "claude-code --task build-project"

# Create high priority session
claude-ctl create "urgent-task" --priority high

# Create with specific directory
claude-ctl create "test-suite" --dir /path/to/project --priority low
```

Priority levels:
- `critical`: Emergency tasks, run immediately
- `high`: Important tasks, preferred over normal
- `normal`: Default priority
- `low`: Background tasks, run when resources available
- `background`: Lowest priority, run only when system idle

#### Manage Sessions
```bash
# Pause a running session
claude-ctl pause session-id

# Resume a paused session
claude-ctl resume session-id

# Stop a session gracefully
claude-ctl stop session-id

# Force kill a session
claude-ctl stop session-id --force

# Clean up completed/idle sessions
claude-ctl cleanup
```

#### Monitor Thermal State
```bash
claude-ctl thermal
```

## ⚙️ Configuration

### Main Configuration: `config/default.yaml`

**Safe to commit to git** - contains no secrets.

Key settings:

```yaml
thermal:
  temp_critical: 85    # Emergency stop temperature
  temp_high: 80        # Start throttling
  temp_normal: 70      # Normal operation
  temp_cool: 60        # Optimal conditions

sessions:
  max_memory_mb: 6000     # Total memory limit
  max_cpu_percent: 80     # Total CPU limit
  idle_timeout: 3600      # Kill idle sessions after 1 hour
  max_concurrent: 4       # Max simultaneous sessions

logging:
  report_actions: true         # Log all throttling decisions
  report_to_console: true      # Print important actions
  report_thermal_changes: true # Report thermal state changes
```

### Secrets Configuration: `config/secrets.yaml`

**NEVER commit to git** - in .gitignore by default.

Copy from `secrets.yaml.example` and add your credentials:

```yaml
email:
  enabled: false
  smtp_host: "smtp.gmail.com"
  smtp_password: "your-app-specific-password"

webhooks:
  slack_webhook: "https://hooks.slack.com/..."
```

## 📊 Action Reporting

The system reports all important actions to help you stay aware:

```
[ACTION] Claude Power Manager daemon started
[INFO] Monitoring thermal state every 10s
[INFO] Current profile: plugged
[THERMAL] HIGH: Limiting concurrent instances
[ACTION] Paused session claude-1234567890 due to critical temperature
[THERMAL] NORMAL: Temperature stabilized
[ACTION] Resumed session claude-1234567890
[ACTION] Power profile changed to: battery
```

## 🔧 How It Works

### Thermal-Aware Scheduling

1. **Daemon monitors** CPU temperature every 10 seconds
2. **Thermal level determined** based on configured thresholds
3. **Actions taken** based on level:
   - **Critical (>85°C)**: Pause all non-critical sessions
   - **High (>80°C)**: Don't spawn new instances, limit concurrent sessions
   - **Normal (>70°C)**: Standard operation
   - **Cool (<60°C)**: Can run maximum instances safely

### Priority Queue System

1. Sessions created with priority (0=Critical → 4=Background)
2. Queued in priority order
3. Daemon processes queue based on:
   - Current thermal state
   - Available resources (CPU/memory)
   - Maximum instances allowed
4. Higher priority sessions started first

### Resource Limits

- **Per-session monitoring**: CPU% and Memory MB tracked
- **Global limits enforced**: Sum of all sessions must stay within limits
- **Automatic cleanup**: Idle sessions terminated after timeout
- **Graceful degradation**: Low-priority sessions paused under stress

### Power Profile Auto-Switching

Daemon detects AC adapter state and automatically switches profiles:
- **On battery** → Conservative settings (2 instances, 60% CPU)
- **Plugged in** → Balanced settings (3 instances, 80% CPU)
- **Manual override** available via CLI

## 🛡️ Safety Mechanisms

1. **Emergency Stop**: Automatically stops sessions if temperature reaches critical
2. **Throttle Detection**: Monitors CPU frequency to detect hardware throttling
3. **Memory Protection**: Maintains minimum free memory (500MB default)
4. **Process Groups**: Uses process groups for clean termination of all child processes
5. **State Persistence**: Session state saved to disk, survives daemon restarts
6. **Signal Handling**: Graceful shutdown on SIGTERM/SIGINT

## 📈 Monitoring Examples

### Basic Status Check
```bash
$ claude-ctl status

======================================================================
Claude Code Power Manager - System Status
======================================================================

📊 Thermal Status
  Temperature:     67.3°C
  Level:           NORMAL
  CPU Frequency:   2400 MHz
  Load Average:    2.45, 2.10, 1.85
  Throttled:       No

🔧 Session Statistics
  Total Sessions:  5
  Running:         2
  Queued:          1
  Paused:          0
  Completed:       2
  Failed:          0

💻 Resource Usage
  Total CPU:       45.2%
  Total Memory:    3842 MB

💡 Recommendations
  Can spawn new:   Yes
  Max instances:   3
  Advice:          Operating normally. Monitor temperature trends.
```

### Session List
```bash
$ claude-ctl list

====================================================================================================================
Session ID           Status       Priority     CPU%     Mem(MB)    Age             Command
====================================================================================================================
claude-1735678901234 running      NORMAL       23.4     1856       5m32s           claude-code --task build
claude-1735678900123 running      HIGH         21.8     1986       8m15s           claude-code --task test
claude-1735678899012 queued       LOW          0.0      0          2m10s           long-background-task
```

## 🔒 Security & Privacy

- **No secrets in default config**: All sensitive data in separate `secrets.yaml`
- **Comprehensive .gitignore**: Prevents accidental commit of credentials
- **Local-only by default**: No external connections without explicit configuration
- **Process isolation**: Each session runs in own process group
- **User-level service**: Runs as your user, not root (CPU governor requires manual setup)

## 🐛 Troubleshooting

### Daemon won't start
```bash
# Check logs
tail -f logs/power-daemon.log

# Test configuration
python3 claude-power-daemon.py --help

# Check dependencies
pip3 list | grep -E 'psutil|PyYAML'
```

### Temperature not detected
```bash
# Check thermal zones
ls /sys/class/thermal/

# Check hwmon sensors
ls /sys/class/hwmon/

# Manual check
cat /sys/class/thermal/thermal_zone*/temp
```

### Sessions not starting
```bash
# Check thermal state
claude-ctl thermal

# Check resource limits
claude-ctl status

# View detailed logs
tail -f logs/power-daemon.log
```

### High memory usage
```bash
# Check session stats
claude-ctl list

# Clean up old sessions
claude-ctl cleanup

# Adjust limits in config/default.yaml
vim config/default.yaml  # Reduce max_memory_mb
```

## 🔄 Uninstallation

```bash
# Stop and disable systemd service
./scripts/uninstall-systemd.sh

# Remove symlink
rm ~/.local/bin/claude-ctl

# Remove project directory
cd ~
rm -rf claude-power-manager
```

## 📝 Logging

Logs are stored in `logs/power-daemon.log`:

- **INFO**: Normal operations, state changes
- **WARNING**: Thermal warnings, resource constraints
- **ERROR**: Failures, exceptions
- **DEBUG**: Detailed information (use `--verbose` flag)

View logs:
```bash
# Tail daemon log
tail -f logs/power-daemon.log

# View systemd journal
journalctl -u claude-power-manager -f

# View specific time range
journalctl -u claude-power-manager --since "1 hour ago"
```

## 🚀 Advanced Usage

### Custom Priority Workflow
```bash
# High priority: urgent fixes
claude-ctl create "claude-code --task fix-critical-bug" --priority high

# Normal priority: regular development
claude-ctl create "claude-code --task implement-feature" --priority normal

# Low priority: tests and builds
claude-ctl create "npm run test" --priority low

# Background: documentation
claude-ctl create "generate-docs" --priority background
```

### Performance Mode for Short Bursts
```bash
# Start daemon in performance mode
./claude-power-daemon.py --profile performance

# Or via config
vim config/default.yaml  # Set default profile
```

### Monitoring in Real-Time
```bash
# Watch status updates
watch -n 5 'claude-ctl status'

# Monitor thermal changes
while true; do claude-ctl thermal; sleep 10; done
```

## 🤝 Contributing

This project is designed to be portable and reusable. To adapt for your system:

1. Adjust thermal thresholds in `config/default.yaml`
2. Modify resource limits based on your hardware
3. Customize power profiles for your use case
4. Update paths in systemd service file

## 📄 License

MIT License - Feel free to use, modify, and distribute.

## 🙏 Acknowledgments

Built for the Dell Inspiron 7472 but designed to work on any Linux system with thermal sensors.

Tested on Pop!_OS 22.04 with Intel i5-8250U and 8GB RAM.

---

**Note**: This system is designed NOT to over-throttle Claude Code sessions. It only intervenes when thermal or resource limits are actually reached, maximizing your productivity while protecting your hardware.