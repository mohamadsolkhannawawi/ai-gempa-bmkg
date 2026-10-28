#!/bin/bash
# =============================================================================
# Automated Storage Cleanup Cron Installer
# AI-GEMPA-BMKG System
#
# Server: riset-01 (152.118.31.54)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLEANUP_SCRIPT="$PROJECT_ROOT/scripts/cleanup_storage.sh"
LOG_DIR="$PROJECT_ROOT/logs"
CRON_LOG="$LOG_DIR/cleanup.log"

CRON_SCHEDULE="${CRON_SCHEDULE:-0 2 * * *}" # Default: 02:00 AM daily
CRON_TAG="# AI-GEMPA-BMKG-STORAGE-CLEANUP"
CRON_JOB="$CRON_SCHEDULE /bin/bash $CLEANUP_SCRIPT >> $CRON_LOG 2>&1 $CRON_TAG"

mkdir -p "$LOG_DIR"
chmod +x "$CLEANUP_SCRIPT"

show_help() {
  echo "AI-GEMPA Storage Cleanup Cron Manager"
  echo ""
  echo "Usage: $0 [OPTION]"
  echo ""
  echo "Options:"
  echo "  --install        Install or update the daily cleanup cron job (Default)"
  echo "  --status         Show current crontab status for cleanup job"
  echo "  --remove         Remove the cleanup cron job from crontab"
  echo "  --run-now        Execute the cleanup script immediately"
  echo "  --dry-run        Execute the cleanup script in dry-run mode (no deletion)"
  echo "  --help, -h       Show this help message"
  echo ""
  echo "Environment variables:"
  echo "  CRON_SCHEDULE    Custom cron expression (Current: '$CRON_SCHEDULE')"
  echo ""
}

check_status() {
  echo "=== Current Cleanup Cron Status ==="
  if crontab -l 2>/dev/null | grep -q "$CRON_TAG"; then
    echo "✓ Active cron job found:"
    crontab -l | grep "$CRON_TAG"
  else
    echo "✗ No AI-GEMPA cleanup cron job found in crontab."
  fi
  echo ""
  echo "Last cleanup log (tail 15 lines):"
  if [ -f "$CRON_LOG" ]; then
    tail -n 15 "$CRON_LOG"
  else
    echo "  (No cleanup log file exists yet at $CRON_LOG)"
  fi
}

install_cron() {
  echo "=== Installing AI-GEMPA Storage Cleanup Cron Job ==="
  echo "Project Root:   $PROJECT_ROOT"
  echo "Script Path:    $CLEANUP_SCRIPT"
  echo "Log Path:       $CRON_LOG"
  echo "Schedule:       $CRON_SCHEDULE (02:00 AM daily)"
  echo ""

  # Ensure cleanup script is executable
  chmod +x "$CLEANUP_SCRIPT"

  # Remove existing job with our tag if present
  CURRENT_CRON=$(crontab -l 2>/dev/null | grep -v "$CRON_TAG" || true)

  # Append new job
  if [ -z "$CURRENT_CRON" ]; then
    echo "$CRON_JOB" | crontab -
  else
    printf "%s\n%s\n" "$CURRENT_CRON" "$CRON_JOB" | crontab -
  fi

  echo "✓ Successfully installed cron job into current user's crontab:"
  crontab -l | grep "$CRON_TAG"
  echo ""
  echo "To view logs anytime: tail -f $CRON_LOG"
}

remove_cron() {
  echo "=== Removing AI-GEMPA Storage Cleanup Cron Job ==="
  if crontab -l 2>/dev/null | grep -q "$CRON_TAG"; then
    crontab -l | grep -v "$CRON_TAG" | crontab -
    echo "✓ Removed cleanup cron job from crontab."
  else
    echo "No cleanup cron job was found in crontab."
  fi
}

# -----------------------------------------------------------------------------
# Main CLI Controller
# -----------------------------------------------------------------------------
case "${1:-}" in
  --status)
    check_status
    ;;
  --remove)
    remove_cron
    ;;
  --run-now)
    echo "Executing cleanup script now..."
    /bin/bash "$CLEANUP_SCRIPT"
    ;;
  --dry-run)
    echo "Executing cleanup script in simulation (dry-run) mode..."
    /bin/bash "$CLEANUP_SCRIPT" --dry-run
    ;;
  --help|-h)
    show_help
    ;;
  --install|"")
    install_cron
    ;;
  *)
    echo "Unknown option: $1"
    show_help
    exit 1
    ;;
esac
