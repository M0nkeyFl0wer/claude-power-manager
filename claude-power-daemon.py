#!/usr/bin/env python3
"""
Claude Code Power Management Daemon
Main daemon that monitors thermal state and manages Claude Code instances
"""

import sys
import os
import time
import signal
import logging
import argparse
import yaml
from pathlib import Path
from typing import Dict, Optional

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))

from thermal_monitor import ThermalMonitor
from session_manager import SessionManager, Priority


class PowerDaemon:
    """Main power management daemon"""

    def __init__(self, config_path: str):
        self.running = False
        self.config = self._load_config(config_path)

        # Setup logging
        self._setup_logging()

        # Initialize components
        self.thermal_monitor = ThermalMonitor(self.config.get('thermal', {}))
        self.session_manager = SessionManager(
            self.config.get('sessions', {}),
            self.thermal_monitor
        )

        # Current power profile
        self.current_profile = 'plugged'
        self._apply_profile(self.current_profile)

        self.logger.info("Claude Code Power Manager initialized")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Try to load secrets (optional)
            secrets_path = Path(config_path).parent / 'secrets.yaml'
            if secrets_path.exists():
                with open(secrets_path, 'r') as f:
                    secrets = yaml.safe_load(f)
                    # Merge secrets into config (secrets override)
                    config.update(secrets)

            return config
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(1)

    def _setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config.get('logging', {})
        log_dir = Path(log_config.get('log_dir', 'logs'))
        log_dir.mkdir(parents=True, exist_ok=True)

        log_level = getattr(logging, log_config.get('log_level', 'INFO'))

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'power-daemon.log'),
                logging.StreamHandler(sys.stdout) if log_config.get('report_to_console', True) else logging.NullHandler()
            ]
        )

        self.logger = logging.getLogger('PowerDaemon')

    def _apply_profile(self, profile_name: str):
        """Apply a power profile"""
        if profile_name not in self.config.get('profiles', {}):
            self.logger.error(f"Unknown profile: {profile_name}")
            return

        profile = self.config['profiles'][profile_name]
        self.current_profile = profile_name

        # Update session manager limits
        self.session_manager.max_memory_mb = profile.get('max_memory_mb', 6000)
        self.session_manager.max_cpu_percent = profile.get('max_cpu_percent', 80)

        # Update thermal thresholds
        thermal_config = self.config.get('thermal', {})
        self.thermal_monitor.temp_high = profile.get('temp_high', thermal_config.get('temp_high', 80))

        # CPU governor (requires root, log recommendation)
        cpu_governor = profile.get('cpu_governor')
        if cpu_governor and self.config.get('system', {}).get('enable_cpu_governor', False):
            if os.geteuid() == 0:
                self.thermal_monitor.set_cpu_governor(cpu_governor)
            else:
                self.logger.info(f"Recommended CPU governor: {cpu_governor} (requires root)")

        self.logger.info(f"Applied power profile: {profile_name}")
        if self.config.get('logging', {}).get('report_actions', True):
            print(f"[ACTION] Power profile changed to: {profile_name}")

    def _detect_power_state(self) -> str:
        """Detect if system is on battery or plugged in"""
        try:
            # Check AC adapter status
            power_supply_path = Path('/sys/class/power_supply')
            if power_supply_path.exists():
                for adapter in power_supply_path.glob('AC*/online'):
                    online = adapter.read_text().strip()
                    if online == '1':
                        return 'plugged'
                return 'battery'
        except Exception as e:
            self.logger.debug(f"Error detecting power state: {e}")

        return 'plugged'  # Default assumption

    def _check_thermal_action(self, previous_level: str, current_level: str):
        """Take action based on thermal level changes"""
        if previous_level == current_level:
            return

        report_thermal = self.config.get('logging', {}).get('report_thermal_changes', True)

        if current_level == 'critical':
            self.logger.warning("CRITICAL TEMPERATURE REACHED")
            if report_thermal:
                print(f"[THERMAL] CRITICAL: Pausing low-priority sessions")

            # Pause low-priority sessions
            if self.config.get('safety', {}).get('enable_auto_pause', True):
                for session in self.session_manager.get_running_sessions():
                    if session.priority >= Priority.NORMAL:
                        self.session_manager.pause_session(session.session_id)
                        print(f"[ACTION] Paused session {session.session_id} due to critical temperature")

        elif current_level == 'high':
            if report_thermal:
                print(f"[THERMAL] HIGH: Limiting concurrent instances")
            self.logger.warning("High temperature - limiting instances")

        elif current_level == 'normal' and previous_level == 'high':
            if report_thermal:
                print(f"[THERMAL] NORMAL: Temperature stabilized")
            self.logger.info("Temperature returned to normal")

            # Resume paused sessions if safe
            for session in self.session_manager.sessions.values():
                if session.status == 'paused':
                    self.session_manager.resume_session(session.session_id)
                    print(f"[ACTION] Resumed session {session.session_id}")

    def run(self):
        """Main daemon loop"""
        self.running = True
        self.logger.info("Power daemon starting")

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        check_interval = self.config.get('thermal', {}).get('check_interval', 10)
        previous_thermal_level = 'normal'

        print("[ACTION] Claude Power Manager daemon started")
        print(f"[INFO] Monitoring thermal state every {check_interval}s")
        print(f"[INFO] Current profile: {self.current_profile}")

        while self.running:
            try:
                # Update thermal state
                thermal_state = self.thermal_monitor.get_thermal_state()
                current_level = self.thermal_monitor.get_thermal_level()

                # Check for thermal level changes
                self._check_thermal_action(previous_thermal_level, current_level)
                previous_thermal_level = current_level

                # Check and update power state
                power_state = self._detect_power_state()
                expected_profile = 'battery' if power_state == 'battery' else 'plugged'
                if expected_profile != self.current_profile and expected_profile in self.config.get('profiles', {}):
                    self._apply_profile(expected_profile)

                # Update session statistics
                for session in self.session_manager.get_running_sessions():
                    self.session_manager.update_session_stats(session.session_id)

                # Process queued sessions
                self.session_manager.process_queue()

                # Cleanup idle sessions
                self.session_manager.cleanup_idle_sessions()

                # Log status
                stats = self.session_manager.get_session_stats()
                self.logger.debug(
                    f"Thermal: {thermal_state.cpu_temp:.1f}°C ({current_level}) | "
                    f"Sessions: {stats['running']} running, {stats['queued']} queued | "
                    f"Resources: {stats['total_cpu']:.0f}% CPU, {stats['total_memory_mb']:.0f}MB RAM"
                )

                # Sleep
                time.sleep(check_interval)

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(check_interval)

        self.logger.info("Power daemon stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down")
        print(f"\n[ACTION] Daemon shutting down gracefully")
        self.running = False

    def stop(self):
        """Stop the daemon"""
        self.running = False


def main():
    parser = argparse.ArgumentParser(description='Claude Code Power Management Daemon')
    parser.add_argument('-c', '--config', default='config/default.yaml',
                       help='Path to configuration file')
    parser.add_argument('--profile', choices=['battery', 'plugged', 'performance'],
                       help='Override power profile')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    # Resolve config path
    config_path = Path(__file__).parent / args.config
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    # Create and run daemon
    daemon = PowerDaemon(str(config_path))

    # Override profile if specified
    if args.profile:
        daemon._apply_profile(args.profile)

    try:
        daemon.run()
    except KeyboardInterrupt:
        print("\n[ACTION] Interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()