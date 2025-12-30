# ZeroDB Local - Example Scripts

This directory contains executable shell scripts that demonstrate common workflows with ZeroDB Local.

## Available Scripts

### 1. first-sync.sh

**Purpose:** Demonstrates the first synchronization workflow with ZeroDB Cloud.

**What it does:**
- Checks CLI installation and service health
- Verifies cloud API key configuration
- Shows how to plan sync operations (preview changes)
- Demonstrates executing sync with confirmation
- Verifies sync status after completion

**Usage:**
```bash
cd /path/to/zerodb-local
bash docs/examples/first-sync.sh
```

**Prerequisites:**
- ZeroDB Local services running
- Cloud API key configured in `.env.local` (optional)

**Time:** ~5 minutes

---

### 2. daily-workflow.sh

**Purpose:** Simulates a complete daily development workflow.

**What it does:**
- **Morning (9 AM):** Start services, check health, view projects
- **Midday (12 PM):** Pull latest changes from cloud
- **Afternoon (2 PM):** Simulate development work
- **Evening (5 PM):** Push changes to cloud
- **Night (6 PM):** Create backup and stop services

**Usage:**
```bash
cd /path/to/zerodb-local
bash docs/examples/daily-workflow.sh
```

**Prerequisites:**
- ZeroDB CLI installed
- Cloud API key configured (optional)

**Time:** ~10 minutes (interactive)

**Automation:**
```bash
# Add to crontab for automated daily workflow
0 9 * * * cd /path/to/zerodb-local && zerodb local up
0 18 * * * cd /path/to/zerodb-local && zerodb sync apply --auto-approve && zerodb local down
```

---

### 3. backup-restore.sh

**Purpose:** Demonstrates backup and restore operations for disaster recovery.

**What it does:**
- Creates comprehensive backups of:
  - PostgreSQL database (SQL dump)
  - Qdrant vector collections (tar.gz)
  - MinIO object storage (tar.gz)
- Generates backup manifest with metadata
- Demonstrates full restore procedure
- Shows backup management and cleanup

**Usage:**
```bash
cd /path/to/zerodb-local
bash docs/examples/backup-restore.sh
```

**Prerequisites:**
- ZeroDB Local services running
- Write permissions to `./backups/` directory

**Time:** ~5 minutes (backup), ~10 minutes (restore)

**Output:**
```
./backups/
├── zerodb_backup_20251229_120000.sql
├── zerodb_backup_20251229_120000_qdrant.tar.gz
├── zerodb_backup_20251229_120000_minio.tar.gz
└── zerodb_backup_20251229_120000_manifest.txt
```

---

## Quick Reference

### Running All Examples in Sequence

```bash
# Run all examples to learn the complete workflow
cd /path/to/zerodb-local

# 1. First sync
bash docs/examples/first-sync.sh

# 2. Daily workflow
bash docs/examples/daily-workflow.sh

# 3. Backup and restore
bash docs/examples/backup-restore.sh
```

### Making Scripts Executable

If scripts are not executable:

```bash
chmod +x docs/examples/*.sh
```

### Customizing Scripts

All scripts are well-commented and can be customized for your needs:

1. Copy script to your own directory
2. Modify variables at the top
3. Add your custom logic
4. Run your version

Example:
```bash
cp docs/examples/daily-workflow.sh my-custom-workflow.sh
nano my-custom-workflow.sh  # Edit as needed
bash my-custom-workflow.sh
```

---

## Common Use Cases

### Use Case 1: First-Time Setup
```bash
# 1. Install and start
cd cli && pip install -e . && cd ..
zerodb local init
zerodb local up

# 2. Learn sync workflow
bash docs/examples/first-sync.sh
```

### Use Case 2: Regular Development
```bash
# Use daily workflow script every day
bash docs/examples/daily-workflow.sh

# Or automate it with cron
crontab -e
# Add: 0 9 * * * cd /path/to/zerodb-local && zerodb local up
```

### Use Case 3: Before Major Changes
```bash
# 1. Create backup
bash docs/examples/backup-restore.sh

# 2. Make your changes
# ... development work ...

# 3. If something breaks, restore
bash docs/examples/backup-restore.sh
# Select 'y' when prompted to restore
```

### Use Case 4: Team Onboarding
```bash
# New team members can run all examples
cd /path/to/zerodb-local
for script in docs/examples/*.sh; do
    bash "$script"
done
```

---

## Troubleshooting

### Script Fails with "Command not found"

**Solution:**
```bash
# Ensure CLI is installed
cd cli
pip install -e .
zerodb --version
```

### Script Fails with "Services not running"

**Solution:**
```bash
# Start services first
zerodb local up
sleep 30  # Wait for services to be ready
```

### Backup Script Fails

**Solution:**
```bash
# Check Docker services
docker ps | grep zerodb

# Check disk space
df -h

# Create backup directory
mkdir -p ./backups
chmod 755 ./backups
```

### Permission Denied

**Solution:**
```bash
# Make scripts executable
chmod +x docs/examples/*.sh

# Run with bash explicitly
bash docs/examples/first-sync.sh
```

---

## Best Practices

### 1. Review Before Running
- Read script contents before execution
- Understand what each step does
- Check prerequisites

### 2. Test in Safe Environment
- Run examples in development first
- Don't test restore on production data
- Create backups before experimenting

### 3. Customize for Your Needs
- Copy scripts and modify them
- Add your own validation steps
- Integrate with your CI/CD pipeline

### 4. Automate Common Tasks
- Use cron for scheduled operations
- Add to deployment scripts
- Integrate with monitoring tools

---

## Integration Examples

### CI/CD Pipeline

```bash
# .github/workflows/deploy.yml
- name: Backup before deployment
  run: bash docs/examples/backup-restore.sh

- name: Deploy changes
  run: # your deployment commands

- name: Sync to cloud
  run: zerodb sync apply --auto-approve
```

### Monitoring Integration

```bash
# Add to backup script:
if [ $? -eq 0 ]; then
    curl -X POST https://your-monitoring.com/alert \
        -d "status=success&message=Backup completed"
else
    curl -X POST https://your-monitoring.com/alert \
        -d "status=failure&message=Backup failed"
fi
```

### Slack Notifications

```bash
# Add to daily workflow:
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
curl -X POST $SLACK_WEBHOOK \
    -H 'Content-Type: application/json' \
    -d '{"text":"ZeroDB daily sync completed successfully!"}'
```

---

## Additional Resources

- **CLI Documentation:** `docs/cli/`
- **Quick Start Guide:** `docs/QUICK_START.md`
- **Troubleshooting:** `docs/TROUBLESHOOTING.md`
- **Sync Architecture:** `docs/SYNC_ARCHITECTURE_DIAGRAM.md`

---

**Updated:** 2025-12-29
**Version:** 1.0
