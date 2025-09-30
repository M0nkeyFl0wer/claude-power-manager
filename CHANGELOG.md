# Changelog

All notable changes to Claude Code Power Manager will be documented in this file.

## [1.0.0] - 2025-09-30

### Initial Release

#### Added
- Thermal monitoring system with multi-sensor support
  - Real-time CPU temperature monitoring
  - CPU frequency and load tracking
  - Throttling detection
  - Multiple thermal sensor support (coretemp, hwmon, thermal_zones)

- Session management system
  - Priority-based queue (Critical, High, Normal, Low, Background)
  - Process lifecycle management (create, start, stop, pause, resume)
  - Resource tracking (CPU%, memory MB)
  - Idle session detection and cleanup
  - State persistence across daemon restarts

- Power profile system
  - Battery mode (conservative)
  - Plugged mode (balanced)
  - Performance mode (aggressive)
  - Automatic profile switching based on AC adapter state

- Safety features
  - Emergency stop at critical temperatures
  - Automatic session pausing under thermal stress
  - Minimum free memory enforcement
  - Process group isolation
  - Graceful shutdown handling

- CLI management tool (`claude-ctl`)
  - System status dashboard
  - Session list and filtering
  - Session creation with priorities
  - Session control (stop, pause, resume)
  - Thermal monitoring view
  - Cleanup utilities

- Daemon (`claude-power-daemon.py`)
  - Continuous thermal monitoring
  - Automatic session queue processing
  - Action logging and reporting
  - Signal handling for clean shutdown

- System integration
  - Systemd service support
  - Installation scripts
  - Configuration management (YAML)
  - Comprehensive logging

- Documentation
  - Complete README with examples
  - Configuration guide
  - Troubleshooting section
  - Security best practices

- Security features
  - Secrets separation from main config
  - Comprehensive .gitignore
  - No external dependencies by default
  - User-level operation (no root required)

### Design Decisions
- **Not Over-Throttling**: System only intervenes when thermal or resource limits are actually reached
- **Action Reporting**: All throttling and scaling decisions are logged and reported
- **Thermal-First Design**: Temperature monitoring is primary constraint
- **Priority Queue**: Fair scheduling based on task priority
- **State Persistence**: Sessions survive daemon restarts
- **Safe Defaults**: Conservative thresholds that protect hardware

### Tested On
- Dell Inspiron 7472
- Intel Core i5-8250U (4 cores, 8 threads)
- 8GB RAM
- Pop!_OS 22.04 LTS
- Linux kernel 6.12.10

### Known Limitations
- CPU governor changes require root access (manual setup)
- Desktop notifications not yet implemented
- Web dashboard planned for future release
- Email notifications require manual configuration

## [Unreleased]

### Planned Features
- Web-based monitoring dashboard
- Desktop notifications integration
- Prometheus metrics export
- Advanced alerting (email, webhooks)
- Machine learning for thermal prediction
- Integration with system76-power daemon
- GPU monitoring support
- Per-session resource limits
- Session priorities auto-adjustment
- Historical metrics and reporting