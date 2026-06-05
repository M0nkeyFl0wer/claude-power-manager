# Usage Examples

Practical examples for using Claude Code Power Manager in real-world scenarios.

## Quick Start

### 1. Install and Setup
```bash
mkdir /home/claude-power-manager
cd /home/claude-power-manager
./install.sh
```

### 2. Check Current Status
```bash
claude-ctl status
```

### 3. Start the Daemon
```bash
# Option A: Run in foreground (see all actions)
./claude-power-daemon.py

# Option B: Run as systemd service
sudo systemctl start claude-power-manager
journalctl -u claude-power-manager -f
```

## Common Workflows

### Development Workflow

**Scenario**: Working on multiple projects, want to run tests and builds in background while coding.

```bash
# High priority: Current work
claude-ctl create "claude-code --task implement-feature" --priority high --dir ~/project-a

# Normal priority: Code review
claude-ctl create "claude-code --task review-pr" --priority normal --dir ~/project-b

# Low priority: Run test suite
claude-ctl create "npm test" --priority low --dir ~/project-c

# Background: Documentation generation
claude-ctl create "npm run docs" --priority background --dir ~/project-a

# Check what's running
claude-ctl list
```

### Thermal Emergency

**Scenario**: System temperature is critical, need to protect hardware.

```bash
# Check thermal state
claude-ctl thermal

# If critical, daemon will automatically:
# 1. Pause low-priority sessions
# 2. Stop spawning new instances
# 3. Wait for temperature to drop

# Monitor in real-time
watch -n 5 'claude-ctl status'

# Manual intervention if needed
claude-ctl list --status running
claude-ctl pause session-id-1
claude-ctl pause session-id-2
```

### Battery Conservation

**Scenario**: Working on battery, want to maximize battery life.

```bash
# Daemon automatically switches to battery profile
# But you can verify:
claude-ctl status

# Or force battery mode
sudo systemctl stop claude-power-manager
./claude-power-daemon.py --profile battery

# This limits to 2 instances max, 60% CPU, 4GB RAM
```

### Performance Mode for Urgent Work

**Scenario**: Plugged in, need maximum performance for urgent deadline.

```bash
# Start daemon in performance mode
./claude-power-daemon.py --profile performance

# Create high-priority sessions
claude-ctl create "urgent-build" --priority critical
claude-ctl create "urgent-tests" --priority high
claude-ctl create "urgent-deploy" --priority high

# Monitor resources
watch -n 2 'claude-ctl status'
```

### Long-Running Background Tasks

**Scenario**: Have multiple long-running tasks that can run overnight.

```bash
# Create all tasks with background priority
claude-ctl create "npm run build:prod" --priority background --dir ~/app1
claude-ctl create "npm run build:prod" --priority background --dir ~/app2
claude-ctl create "npm run build:prod" --priority background --dir ~/app3
claude-ctl create "python train_model.py" --priority background --dir ~/ml-project

# They'll run when system is idle
# Check queue
claude-ctl list --status queued

# Let daemon run overnight
sudo systemctl start claude-power-manager
```

### Session Management

**Scenario**: Managing multiple active sessions, need to pause/resume/stop them.

```bash
# List all sessions
claude-ctl list

# Pause a session temporarily
claude-ctl pause claude-1735678901234

# Resume it later
claude-ctl resume claude-1735678901234

# Stop completed or failed sessions
claude-ctl stop claude-1735678900123

# Force kill a stuck session
claude-ctl stop claude-1735678899012 --force

# Clean up all old sessions
claude-ctl cleanup
```

## Monitoring Examples

### Real-Time Temperature Monitoring
```bash
# Watch thermal state
watch -n 5 'claude-ctl thermal'

# Or continuous monitoring
while true; do
    clear
    claude-ctl thermal
    sleep 5
done
```

### Session Dashboard
```bash
# Watch session status
watch -n 5 'claude-ctl list'

# Or combined view
watch -n 5 'claude-ctl status && echo && claude-ctl list'
```

### Log Monitoring
```bash
# Tail daemon log
tail -f logs/power-daemon.log

# Follow systemd journal
journalctl -u claude-power-manager -f

# Search for thermal events
grep "THERMAL" logs/power-daemon.log

# Search for actions taken
grep "ACTION" logs/power-daemon.log
```

## Integration Examples

### Integration with CI/CD
```bash
#!/bin/bash
# ci-runner.sh - Run CI tests with power management

# Create high-priority CI job
SESSION_ID=$(claude-ctl create "npm run ci" --priority high | grep -oP 'claude-\d+')

# Wait for completion
while [ "$(claude-ctl list | grep $SESSION_ID | awk '{print $2}')" = "running" ]; do
    sleep 10
done

# Check if passed
if [ "$(claude-ctl list | grep $SESSION_ID | awk '{print $2}')" = "completed" ]; then
    echo "CI passed"
    exit 0
else
    echo "CI failed"
    exit 1
fi
```

### Cron Job Integration
```bash
# Add to crontab
# Run cleanup every hour
0 * * * * /home/monkeyflower/.local/bin/claude-ctl cleanup

# Check thermal state every 5 minutes
*/5 * * * * /home/monkeyflower/.local/bin/claude-ctl thermal >> /tmp/thermal-log.txt

# Daily report
0 9 * * * /home/monkeyflower/.local/bin/claude-ctl status | mail -s "Daily Power Manager Status" user@example.com
```

### Script Integration
```bash
#!/bin/bash
# smart-deploy.sh - Deploy with thermal awareness

# Check if we can deploy
if claude-ctl status | grep "Can spawn new:   Yes" > /dev/null; then
    echo "System ready for deployment"
    claude-ctl create "npm run deploy:prod" --priority high
else
    echo "System too hot, waiting..."
    # Wait for temperature to drop
    while ! claude-ctl status | grep "Can spawn new:   Yes" > /dev/null; do
        sleep 30
    done
    claude-ctl create "npm run deploy:prod" --priority high
fi
```

## Troubleshooting Examples

### Debug Why Session Won't Start
```bash
# Check system status
claude-ctl status

# Check thermal state
claude-ctl thermal

# Check session queue
claude-ctl list --status queued

# Check daemon logs
tail -n 50 logs/power-daemon.log | grep -A 5 "Cannot start"

# If temperature is high, wait for it to drop
watch -n 10 'claude-ctl thermal'
```

### Clean Up Stuck Sessions
```bash
# List all sessions
claude-ctl list

# Find stuck/zombie sessions
ps aux | grep claude

# Force stop them
claude-ctl stop session-id --force

# Or kill manually
pkill -9 -f claude-code

# Clean up state
claude-ctl cleanup
```

### Reset Everything
```bash
# Stop daemon
sudo systemctl stop claude-power-manager

# Clear state
rm -f /tmp/claude-power-manager-state.json

# Clear logs
rm -f logs/*.log

# Restart
sudo systemctl start claude-power-manager
```

## Advanced Examples

### Custom Priority Workflow
```bash
#!/bin/bash
# priority-workflow.sh - Implement custom priority logic

# Critical: Security fixes
claude-ctl create "security-scan" --priority critical

# High: Bug fixes
for bug in bug-{1..3}; do
    claude-ctl create "fix-${bug}" --priority high
done

# Normal: Features
for feature in feature-{1..5}; do
    claude-ctl create "implement-${feature}" --priority normal
done

# Low: Tests
claude-ctl create "run-all-tests" --priority low

# Background: Docs
claude-ctl create "generate-docs" --priority background

# Monitor progress
watch -n 10 'claude-ctl list'
```

### Thermal-Based Workload Adaptation
```bash
#!/bin/bash
# adaptive-workload.sh - Adjust workload based on temperature

while true; do
    TEMP=$(claude-ctl thermal | grep "Temperature:" | awk '{print $2}' | cut -d'°' -f1)
    LEVEL=$(claude-ctl thermal | grep "Level:" | awk '{print $2}')

    if [ "$LEVEL" = "COOL" ]; then
        echo "Temperature cool, starting heavy workload"
        claude-ctl create "heavy-task" --priority normal
    elif [ "$LEVEL" = "HIGH" ]; then
        echo "Temperature high, starting light workload only"
        claude-ctl create "light-task" --priority low
    fi

    sleep 300  # Check every 5 minutes
done
```

### Multi-Project Build Queue
```bash
#!/bin/bash
# build-all-projects.sh - Build multiple projects with power management

PROJECTS=(
    "~/project1:high"
    "~/project2:normal"
    "~/project3:normal"
    "~/project4:low"
    "~/project5:low"
)

for project_spec in "${PROJECTS[@]}"; do
    IFS=: read -r project priority <<< "$project_spec"
    echo "Queueing build for $project (priority: $priority)"
    claude-ctl create "npm run build" --dir "$project" --priority "$priority"
done

echo "All builds queued. Monitor with:"
echo "  claude-ctl list"
echo "  watch -n 5 'claude-ctl status'"
```

## Tips and Best Practices

1. **Start with normal priority** - Only use high/critical for truly urgent tasks
2. **Monitor temperature trends** - Use `watch -n 5 'claude-ctl thermal'` during heavy workloads
3. **Clean up regularly** - Run `claude-ctl cleanup` daily to remove old sessions
4. **Use background priority** - For truly non-urgent tasks that can run anytime
5. **Check before large jobs** - Run `claude-ctl status` before starting heavy workloads
6. **Let daemon handle it** - Trust the automatic scheduling, only intervene when needed
7. **Use systemd for production** - More reliable than manual daemon start
8. **Monitor logs** - Check `logs/power-daemon.log` for trends and issues

## Performance Tuning

### For More Aggressive Performance
Edit `config/default.yaml`:
```yaml
thermal:
  temp_high: 82        # Allow higher temps (from 80)

sessions:
  max_cpu_percent: 90  # Use more CPU (from 80)
  max_concurrent: 5    # More instances (from 4)
```

### For More Conservative Operation
Edit `config/default.yaml`:
```yaml
thermal:
  temp_high: 75        # Be more conservative (from 80)

sessions:
  max_cpu_percent: 70  # Use less CPU (from 80)
  max_concurrent: 2    # Fewer instances (from 4)
```
