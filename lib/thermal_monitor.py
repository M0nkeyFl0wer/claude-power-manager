#!/usr/bin/env python3
"""
Thermal Monitoring Module for Claude Code Power Manager
Monitors CPU temperature, frequency, and system thermals
"""

import os
import re
import time
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class ThermalState:
    """Represents current thermal state of the system"""
    cpu_temp: float
    cpu_freq: float
    load_avg: tuple
    throttled: bool
    timestamp: float


class ThermalMonitor:
    """Monitor and manage system thermal state"""

    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger('ThermalMonitor')

        # Thermal thresholds
        self.temp_critical = config.get('temp_critical', 85)
        self.temp_high = config.get('temp_high', 80)
        self.temp_normal = config.get('temp_normal', 70)
        self.temp_cool = config.get('temp_cool', 60)

        # Thermal zones to monitor
        self.thermal_zones = self._discover_thermal_zones()

    def _discover_thermal_zones(self) -> List[Path]:
        """Discover available thermal zones"""
        zones = []
        thermal_path = Path('/sys/class/thermal')

        if not thermal_path.exists():
            self.logger.warning("Thermal sysfs not available")
            return zones

        for zone_dir in thermal_path.glob('thermal_zone*'):
            type_file = zone_dir / 'type'
            if type_file.exists():
                zone_type = type_file.read_text().strip()
                # Focus on CPU thermal zones
                if any(keyword in zone_type.lower() for keyword in ['cpu', 'x86', 'coretemp', 'pkg']):
                    zones.append(zone_dir)
                    self.logger.info(f"Found thermal zone: {zone_type} at {zone_dir}")

        return zones

    def get_cpu_temperature(self) -> float:
        """Get current CPU temperature in Celsius"""
        temps = []

        # Method 1: Read from thermal zones
        for zone in self.thermal_zones:
            temp_file = zone / 'temp'
            if temp_file.exists():
                try:
                    temp_millidegrees = int(temp_file.read_text().strip())
                    temp_celsius = temp_millidegrees / 1000.0
                    temps.append(temp_celsius)
                except (ValueError, IOError) as e:
                    self.logger.debug(f"Error reading {temp_file}: {e}")

        # Method 2: Try coretemp (Intel)
        if not temps:
            coretemp_pattern = Path('/sys/devices/platform')
            for coretemp_dir in coretemp_pattern.glob('coretemp.*'):
                for temp_input in coretemp_dir.glob('hwmon/hwmon*/temp*_input'):
                    try:
                        temp_millidegrees = int(temp_input.read_text().strip())
                        temp_celsius = temp_millidegrees / 1000.0
                        temps.append(temp_celsius)
                    except (ValueError, IOError):
                        pass

        # Method 3: Try sensors via /sys/class/hwmon
        if not temps:
            hwmon_path = Path('/sys/class/hwmon')
            if hwmon_path.exists():
                for hwmon_dir in hwmon_path.iterdir():
                    name_file = hwmon_dir / 'name'
                    if name_file.exists():
                        name = name_file.read_text().strip()
                        if name in ['coretemp', 'k10temp', 'zenpower']:
                            for temp_input in hwmon_dir.glob('temp*_input'):
                                try:
                                    temp_millidegrees = int(temp_input.read_text().strip())
                                    temp_celsius = temp_millidegrees / 1000.0
                                    temps.append(temp_celsius)
                                except (ValueError, IOError):
                                    pass

        if temps:
            # Return the maximum temperature
            return max(temps)
        else:
            self.logger.warning("Could not read CPU temperature, using safe default")
            return 75.0  # Safe default assumption

    def get_cpu_frequency(self) -> float:
        """Get current CPU frequency in MHz"""
        try:
            freq_path = Path('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq')
            if freq_path.exists():
                freq_khz = int(freq_path.read_text().strip())
                return freq_khz / 1000.0  # Convert to MHz
        except (ValueError, IOError) as e:
            self.logger.debug(f"Error reading CPU frequency: {e}")

        # Fallback: try cpuinfo
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('cpu MHz'):
                        freq = float(line.split(':')[1].strip())
                        return freq
        except (IOError, ValueError, IndexError):
            pass

        return 0.0

    def get_load_average(self) -> tuple:
        """Get system load average (1, 5, 15 minutes)"""
        return os.getloadavg()

    def is_throttled(self) -> bool:
        """Check if CPU is currently throttled"""
        temp = self.get_cpu_temperature()
        freq = self.get_cpu_frequency()

        # Check temperature-based throttling
        if temp >= self.temp_high:
            return True

        # Check frequency-based throttling (if freq is significantly below max)
        try:
            max_freq_path = Path('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq')
            if max_freq_path.exists():
                max_freq_khz = int(max_freq_path.read_text().strip())
                max_freq_mhz = max_freq_khz / 1000.0

                # If current frequency is less than 70% of max, consider throttled
                if freq > 0 and freq < (max_freq_mhz * 0.7):
                    return True
        except (ValueError, IOError):
            pass

        return False

    def get_thermal_state(self) -> ThermalState:
        """Get current thermal state snapshot"""
        return ThermalState(
            cpu_temp=self.get_cpu_temperature(),
            cpu_freq=self.get_cpu_frequency(),
            load_avg=self.get_load_average(),
            throttled=self.is_throttled(),
            timestamp=time.time()
        )

    def get_thermal_level(self) -> str:
        """Get current thermal level: cool, normal, high, critical"""
        temp = self.get_cpu_temperature()

        if temp >= self.temp_critical:
            return 'critical'
        elif temp >= self.temp_high:
            return 'high'
        elif temp >= self.temp_normal:
            return 'normal'
        else:
            return 'cool'

    def can_spawn_instance(self) -> bool:
        """Determine if it's safe to spawn a new Claude Code instance"""
        state = self.get_thermal_state()

        # Don't spawn if temperature is too high
        if state.cpu_temp >= self.temp_high:
            self.logger.info(f"Temperature too high ({state.cpu_temp}°C) to spawn new instance")
            return False

        # Don't spawn if system is already heavily loaded
        load_1min = state.load_avg[0]
        cpu_count = os.cpu_count() or 4
        if load_1min > (cpu_count * 0.8):
            self.logger.info(f"Load too high ({load_1min}) to spawn new instance")
            return False

        # Don't spawn if CPU is throttled
        if state.throttled:
            self.logger.info("CPU throttled, not spawning new instance")
            return False

        return True

    def get_max_instances(self) -> int:
        """Calculate maximum recommended Claude Code instances based on thermal state"""
        level = self.get_thermal_level()
        load_1min = self.get_load_average()[0]
        cpu_count = os.cpu_count() or 4

        # Base calculation on thermal level
        if level == 'critical':
            max_instances = 1
        elif level == 'high':
            max_instances = 2
        elif level == 'normal':
            max_instances = min(3, cpu_count // 2)
        else:  # cool
            max_instances = min(4, cpu_count - 1)

        # Adjust based on current load
        available_cores = cpu_count - int(load_1min)
        if available_cores < max_instances:
            max_instances = max(1, available_cores)

        return max_instances

    def set_cpu_governor(self, governor: str) -> bool:
        """Set CPU frequency governor (requires root)"""
        governors = ['performance', 'powersave', 'ondemand', 'conservative', 'schedutil']

        if governor not in governors:
            self.logger.error(f"Invalid governor: {governor}")
            return False

        success = True
        cpu_count = os.cpu_count() or 4

        for cpu_id in range(cpu_count):
            governor_path = f'/sys/devices/system/cpu/cpu{cpu_id}/cpufreq/scaling_governor'
            try:
                with open(governor_path, 'w') as f:
                    f.write(governor)
                self.logger.info(f"Set CPU{cpu_id} governor to {governor}")
            except (IOError, PermissionError) as e:
                self.logger.warning(f"Failed to set governor for CPU{cpu_id}: {e}")
                success = False

        return success

    def get_cooling_recommendation(self) -> str:
        """Get recommendation for cooling/performance adjustment"""
        level = self.get_thermal_level()

        recommendations = {
            'critical': 'Reduce workload immediately. Consider pausing Claude Code instances.',
            'high': 'Thermal throttling may occur. Limit concurrent instances.',
            'normal': 'Operating normally. Monitor temperature trends.',
            'cool': 'Optimal conditions. Can run multiple instances safely.'
        }

        return recommendations[level]