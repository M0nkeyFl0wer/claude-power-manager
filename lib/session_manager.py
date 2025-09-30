#!/usr/bin/env python3
"""
Claude Code Session Manager
Manages multiple Claude Code instances with priority queuing and resource limits
"""

import os
import signal
import subprocess
import time
import json
import logging
import psutil
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import IntEnum
from queue import PriorityQueue
from datetime import datetime


class Priority(IntEnum):
    """Priority levels for Claude Code sessions"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class ClaudeSession:
    """Represents a Claude Code session"""
    session_id: str
    pid: Optional[int]
    priority: Priority
    command: str
    working_dir: str
    status: str  # 'queued', 'running', 'completed', 'failed', 'paused'
    created_at: float
    started_at: Optional[float]
    completed_at: Optional[float]
    cpu_usage: float
    memory_mb: float
    last_activity: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['priority'] = int(self.priority)
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'ClaudeSession':
        """Create from dictionary"""
        data['priority'] = Priority(data['priority'])
        return cls(**data)


class SessionManager:
    """Manage Claude Code sessions with priority queuing"""

    def __init__(self, config: Dict, thermal_monitor):
        self.config = config
        self.thermal_monitor = thermal_monitor
        self.logger = logging.getLogger('SessionManager')

        # Session storage
        self.sessions: Dict[str, ClaudeSession] = {}
        self.queue = PriorityQueue()

        # Limits
        self.max_memory_mb = config.get('max_memory_mb', 6000)  # 6GB for 8GB system
        self.max_cpu_percent = config.get('max_cpu_percent', 80)
        self.idle_timeout = config.get('idle_timeout', 3600)  # 1 hour

        # State file
        self.state_file = Path(config.get('state_file', '/tmp/claude-power-manager-state.json'))

        # Load existing sessions
        self._load_state()

    def _load_state(self):
        """Load session state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    for session_data in data.get('sessions', []):
                        session = ClaudeSession.from_dict(session_data)
                        self.sessions[session.session_id] = session
                        # Re-queue pending sessions
                        if session.status == 'queued':
                            self.queue.put((session.priority, session.session_id))
                self.logger.info(f"Loaded {len(self.sessions)} sessions from state file")
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.error(f"Error loading state: {e}")

    def _save_state(self):
        """Save session state to disk"""
        try:
            data = {
                'sessions': [s.to_dict() for s in self.sessions.values()],
                'timestamp': time.time()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            self.logger.error(f"Error saving state: {e}")

    def create_session(self, command: str, working_dir: str, priority: Priority = Priority.NORMAL,
                      metadata: Optional[Dict] = None) -> str:
        """Create a new Claude Code session"""
        session_id = f"claude-{int(time.time() * 1000)}"

        session = ClaudeSession(
            session_id=session_id,
            pid=None,
            priority=priority,
            command=command,
            working_dir=working_dir,
            status='queued',
            created_at=time.time(),
            started_at=None,
            completed_at=None,
            cpu_usage=0.0,
            memory_mb=0.0,
            last_activity=time.time(),
            metadata=metadata or {}
        )

        self.sessions[session_id] = session
        self.queue.put((priority, session_id))
        self._save_state()

        self.logger.info(f"Created session {session_id} with priority {priority.name}")
        return session_id

    def start_session(self, session_id: str) -> bool:
        """Start a queued session"""
        if session_id not in self.sessions:
            self.logger.error(f"Session {session_id} not found")
            return False

        session = self.sessions[session_id]

        if session.status != 'queued':
            self.logger.warning(f"Session {session_id} is not queued (status: {session.status})")
            return False

        # Check if we can spawn new instance
        if not self.thermal_monitor.can_spawn_instance():
            self.logger.info(f"Cannot start session {session_id}: thermal constraints")
            return False

        if not self._check_resource_limits():
            self.logger.info(f"Cannot start session {session_id}: resource limits reached")
            return False

        # Start the process
        try:
            env = os.environ.copy()
            env.update(session.metadata.get('env', {}))

            process = subprocess.Popen(
                session.command,
                shell=True,
                cwd=session.working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )

            session.pid = process.pid
            session.status = 'running'
            session.started_at = time.time()
            session.last_activity = time.time()

            self._save_state()
            self.logger.info(f"Started session {session_id} (PID: {process.pid})")
            return True

        except Exception as e:
            self.logger.error(f"Error starting session {session_id}: {e}")
            session.status = 'failed'
            self._save_state()
            return False

    def stop_session(self, session_id: str, force: bool = False) -> bool:
        """Stop a running session"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        if session.status != 'running' or session.pid is None:
            return False

        try:
            if force:
                os.killpg(os.getpgid(session.pid), signal.SIGKILL)
            else:
                os.killpg(os.getpgid(session.pid), signal.SIGTERM)

            session.status = 'completed'
            session.completed_at = time.time()
            self._save_state()

            self.logger.info(f"Stopped session {session_id}")
            return True

        except (ProcessLookupError, PermissionError) as e:
            self.logger.error(f"Error stopping session {session_id}: {e}")
            return False

    def pause_session(self, session_id: str) -> bool:
        """Pause a running session"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        if session.status != 'running' or session.pid is None:
            return False

        try:
            os.killpg(os.getpgid(session.pid), signal.SIGSTOP)
            session.status = 'paused'
            self._save_state()
            self.logger.info(f"Paused session {session_id}")
            return True
        except (ProcessLookupError, PermissionError) as e:
            self.logger.error(f"Error pausing session {session_id}: {e}")
            return False

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        if session.status != 'paused' or session.pid is None:
            return False

        try:
            os.killpg(os.getpgid(session.pid), signal.SIGCONT)
            session.status = 'running'
            session.last_activity = time.time()
            self._save_state()
            self.logger.info(f"Resumed session {session_id}")
            return True
        except (ProcessLookupError, PermissionError) as e:
            self.logger.error(f"Error resuming session {session_id}: {e}")
            return False

    def update_session_stats(self, session_id: str):
        """Update resource usage stats for a session"""
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]

        if session.status != 'running' or session.pid is None:
            return

        try:
            process = psutil.Process(session.pid)

            # Get CPU and memory usage
            session.cpu_usage = process.cpu_percent(interval=0.1)
            session.memory_mb = process.memory_info().rss / (1024 * 1024)

            # Check if process is still running
            if not process.is_running():
                session.status = 'completed'
                session.completed_at = time.time()

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            session.status = 'completed'
            session.completed_at = time.time()

    def _check_resource_limits(self) -> bool:
        """Check if we're within resource limits"""
        total_memory = 0
        total_cpu = 0

        for session in self.sessions.values():
            if session.status == 'running':
                self.update_session_stats(session.session_id)
                total_memory += session.memory_mb
                total_cpu += session.cpu_usage

        if total_memory > self.max_memory_mb:
            self.logger.warning(f"Memory limit reached: {total_memory:.0f}MB / {self.max_memory_mb}MB")
            return False

        if total_cpu > self.max_cpu_percent:
            self.logger.warning(f"CPU limit reached: {total_cpu:.0f}% / {self.max_cpu_percent}%")
            return False

        return True

    def cleanup_idle_sessions(self):
        """Clean up idle or completed sessions"""
        now = time.time()
        to_cleanup = []

        for session_id, session in self.sessions.items():
            # Clean up completed sessions older than 1 hour
            if session.status in ['completed', 'failed']:
                if session.completed_at and (now - session.completed_at) > 3600:
                    to_cleanup.append(session_id)

            # Clean up idle running sessions
            elif session.status == 'running':
                self.update_session_stats(session_id)
                if (now - session.last_activity) > self.idle_timeout:
                    self.logger.info(f"Session {session_id} idle for {now - session.last_activity:.0f}s, stopping")
                    self.stop_session(session_id)
                    to_cleanup.append(session_id)

        for session_id in to_cleanup:
            del self.sessions[session_id]

        if to_cleanup:
            self._save_state()
            self.logger.info(f"Cleaned up {len(to_cleanup)} sessions")

    def get_running_sessions(self) -> List[ClaudeSession]:
        """Get all running sessions"""
        return [s for s in self.sessions.values() if s.status == 'running']

    def get_queued_sessions(self) -> List[ClaudeSession]:
        """Get all queued sessions"""
        return [s for s in self.sessions.values() if s.status == 'queued']

    def get_session_stats(self) -> Dict:
        """Get overall session statistics"""
        stats = {
            'total': len(self.sessions),
            'running': len([s for s in self.sessions.values() if s.status == 'running']),
            'queued': len([s for s in self.sessions.values() if s.status == 'queued']),
            'paused': len([s for s in self.sessions.values() if s.status == 'paused']),
            'completed': len([s for s in self.sessions.values() if s.status == 'completed']),
            'failed': len([s for s in self.sessions.values() if s.status == 'failed']),
            'total_cpu': sum(s.cpu_usage for s in self.sessions.values() if s.status == 'running'),
            'total_memory_mb': sum(s.memory_mb for s in self.sessions.values() if s.status == 'running')
        }
        return stats

    def process_queue(self):
        """Process queued sessions based on thermal and resource state"""
        max_instances = self.thermal_monitor.get_max_instances()
        running_count = len(self.get_running_sessions())

        while running_count < max_instances and not self.queue.empty():
            priority, session_id = self.queue.get()

            if session_id in self.sessions and self.sessions[session_id].status == 'queued':
                if self.start_session(session_id):
                    running_count += 1
                else:
                    # Re-queue if start failed
                    self.queue.put((priority, session_id))
                    break