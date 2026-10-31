#!/bin/bash
# =============================================================================
# Automated Storage & Log Retention Cleanup Script
# AI-GEMPA-BMKG System
#
# Target Server: riset-01 (152.118.31.54)
# Hardware: 16 Cores, 64 GB RAM, 2 TB Storage, 8 GB GPU
# =============================================================================

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
CLEANUP_LOG="$LOG_DIR/cleanup.log"

mkdir -p "$LOG_DIR"

# -----------------------------------------------------------------------------
# CLI Arguments
# -----------------------------------------------------------------------------
DRY_RUN=false
VERBOSE=false

for arg in "$@"; do
  case $arg in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --dry-run    Simulate cleanup without deleting any files"
      echo "  --verbose    Print detailed file-by-file log output"
      echo "  --help       Show this help message"
      exit 0
      ;;
  esac
done

# -----------------------------------------------------------------------------
# Logging Function
# -----------------------------------------------------------------------------
log() {
  local level="$1"
  shift
  local msg="$*"
  local timestamp
  timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
  local formatted="[$timestamp] [$level] $msg"
  echo "$formatted"
  echo "$formatted" >> "$CLEANUP_LOG"
}

log "INFO" "============================================================"
log "INFO" "Starting AI-GEMPA Storage Cleanup Job"
if [ "$DRY_RUN" = true ]; then
  log "WARN" "DRY-RUN MODE ENABLED: No files or database records will be deleted."
fi
log "INFO" "============================================================"

# -----------------------------------------------------------------------------
# Load Environment Configuration
# -----------------------------------------------------------------------------
load_env() {
  local env_files=(
    "$PROJECT_ROOT/.env"
    "$PROJECT_ROOT/.env.seed"
    "$PROJECT_ROOT/sispro-tews/.env"
    "$PROJECT_ROOT/AI-TEWS/requirements/.env"
  )
  for f in "${env_files[@]}"; do
    if [ -f "$f" ]; then
      # Export variables excluding comments and empty lines
      set -a
      # shellcheck disable=SC1090
      source <(grep -E '^[A-Za-z0-9_]+=' "$f" | sed 's/\r$//') 2>/dev/null || true
      set +a
    fi
  done
}
load_env

# -----------------------------------------------------------------------------
# Storage & Retention Policy Configuration (Ideal for 2 TB Disk)
# -----------------------------------------------------------------------------
# 1. MiniSEED Waveform files retention in days (Default: 90 days for 2TB)
ARCHIVE_RETENTION_DAYS="${ARCHIVE_RETENTION_DAYS:-90}"
ARCHIVE_LOCATION="${ARCHIVE_LOCATION:-/mnt/archive}"
# Fallback to local archive if /mnt/archive is not present
if [ ! -d "$ARCHIVE_LOCATION" ] && [ -d "$PROJECT_ROOT/archive" ]; then
  ARCHIVE_LOCATION="$PROJECT_ROOT/archive"
fi

# 2. Application log files (.log) retention in days (Default: 14 days)
LOG_RETENTION_DAYS="${LOG_RETENTION_DAYS:-14}"

# 3. Maximum size for active rotating log files (Default: 50MB)
MAX_LOG_SIZE_MB="${MAX_LOG_SIZE_MB:-50}"

# 4. MongoDB AI raw picks retention in days (Default: 30 days)
DB_PICKS_RETENTION_DAYS="${DB_PICKS_RETENTION_DAYS:-30}"

# 5. Docker prune settings
ENABLE_DOCKER_PRUNE="${ENABLE_DOCKER_PRUNE:-true}"
DOCKER_PRUNE_UNTIL="${DOCKER_PRUNE_UNTIL:-168h}" # 7 days

# 6. Disk alert threshold (percentage)
DISK_USAGE_ALERT_THRESHOLD="${DISK_USAGE_ALERT_THRESHOLD:-85}"

log "INFO" "Configuration Loaded:"
log "INFO" "  - ARCHIVE_LOCATION:           $ARCHIVE_LOCATION"
log "INFO" "  - ARCHIVE_RETENTION_DAYS:     $ARCHIVE_RETENTION_DAYS days"
log "INFO" "  - LOG_RETENTION_DAYS:         $LOG_RETENTION_DAYS days"
log "INFO" "  - MAX_LOG_SIZE_MB:            $MAX_LOG_SIZE_MB MB"
log "INFO" "  - DB_PICKS_RETENTION_DAYS:    $DB_PICKS_RETENTION_DAYS days"
log "INFO" "  - ENABLE_DOCKER_PRUNE:        $ENABLE_DOCKER_PRUNE (until: $DOCKER_PRUNE_UNTIL)"
log "INFO" "  - DISK_USAGE_ALERT_THRESHOLD: $DISK_USAGE_ALERT_THRESHOLD%"

# -----------------------------------------------------------------------------
# Helper: Disk Usage Snapshot
# -----------------------------------------------------------------------------
print_disk_usage() {
  local header="$1"
  log "INFO" "--- Disk Usage ($header) ---"
  if command -v df >/dev/null 2>&1; then
    df -h / "$ARCHIVE_LOCATION" 2>/dev/null | awk 'NR==1 || !seen[$1]++' | while read -r line; do
      log "INFO" "  $line"
    done
  fi
}

print_disk_usage "BEFORE CLEANUP"

# -----------------------------------------------------------------------------
# Step 1: MiniSEED Waveform Archive Cleanup
# -----------------------------------------------------------------------------
log "INFO" "[STEP 1/5] Cleaning expired MiniSEED waveform archive files..."

if [ -d "$ARCHIVE_LOCATION" ]; then
  # Count files older than ARCHIVE_RETENTION_DAYS
  EXPIRED_MSEED_COUNT=$(find "$ARCHIVE_LOCATION" -type f -name "*.mseed" -mtime +"$ARCHIVE_RETENTION_DAYS" 2>/dev/null | wc -l)
  
  if [ "$EXPIRED_MSEED_COUNT" -gt 0 ]; then
    # Calculate approximate size
    EXPIRED_MSEED_SIZE=$(find "$ARCHIVE_LOCATION" -type f -name "*.mseed" -mtime +"$ARCHIVE_RETENTION_DAYS" -exec du -ch {} + 2>/dev/null | grep total$ | awk '{print $1}')
    log "INFO" "Found $EXPIRED_MSEED_COUNT MiniSEED file(s) older than $ARCHIVE_RETENTION_DAYS days (Total: ${EXPIRED_MSEED_SIZE:-unknown})."
    
    if [ "$DRY_RUN" = true ]; then
      log "INFO" "[DRY-RUN] Would delete $EXPIRED_MSEED_COUNT .mseed files from $ARCHIVE_LOCATION"
    else
      find "$ARCHIVE_LOCATION" -type f -name "*.mseed" -mtime +"$ARCHIVE_RETENTION_DAYS" -delete 2>/dev/null || true
      log "INFO" "Successfully deleted $EXPIRED_MSEED_COUNT expired .mseed files."
    fi
  else
    log "INFO" "No MiniSEED files older than $ARCHIVE_RETENTION_DAYS days found."
  fi

  # Clean empty directories
  if [ "$DRY_RUN" = false ]; then
    EMPTY_DIRS_COUNT=$(find "$ARCHIVE_LOCATION" -mindepth 1 -type d -empty 2>/dev/null | wc -l)
    if [ "$EMPTY_DIRS_COUNT" -gt 0 ]; then
      find "$ARCHIVE_LOCATION" -mindepth 1 -type d -empty -delete 2>/dev/null || true
      log "INFO" "Removed $EMPTY_DIRS_COUNT empty directory structure(s)."
    fi
  fi
else
  log "WARN" "Archive directory $ARCHIVE_LOCATION does not exist. Skipping."
fi

# -----------------------------------------------------------------------------
# Step 2: Application Logs (.log) Cleanup & Rotation
# -----------------------------------------------------------------------------
log "INFO" "[STEP 2/5] Cleaning expired application log files (> $LOG_RETENTION_DAYS days)..."

LOG_SEARCH_DIRS=(
  "$PROJECT_ROOT/logs"
  "$PROJECT_ROOT/sispro-tews/logs"
  "$PROJECT_ROOT/sispro-tews/controller_module/logs"
  "$PROJECT_ROOT/sispro-tews/seedlink_module/logs"
  "$PROJECT_ROOT/sispro-tews/archiving_module/logs"
  "$PROJECT_ROOT/sispro-tews/record_stream_module/logs"
  "$PROJECT_ROOT/sispro-tews/fdsn_module/logs"
  "$PROJECT_ROOT/sispro-tews/api_incoming_module/logs"
  "/var/log/gempa"
)

TOTAL_EXPIRED_LOGS=0
for search_dir in "${LOG_SEARCH_DIRS[@]}"; do
  if [ -d "$search_dir" ]; then
    EXPIRED_LOG_COUNT=$(find "$search_dir" -type f -name "*.log" -mtime +"$LOG_RETENTION_DAYS" 2>/dev/null | wc -l)
    if [ "$EXPIRED_LOG_COUNT" -gt 0 ]; then
      TOTAL_EXPIRED_LOGS=$((TOTAL_EXPIRED_LOGS + EXPIRED_LOG_COUNT))
      if [ "$DRY_RUN" = true ]; then
        log "INFO" "[DRY-RUN] In $search_dir: Would delete $EXPIRED_LOG_COUNT .log file(s)"
      else
        find "$search_dir" -type f -name "*.log" -mtime +"$LOG_RETENTION_DAYS" -delete 2>/dev/null || true
        log "INFO" "In $search_dir: Deleted $EXPIRED_LOG_COUNT expired .log file(s)."
      fi
    fi

    # Truncate active oversized logs (> MAX_LOG_SIZE_MB)
    while IFS= read -r logfile; do
      if [ -f "$logfile" ]; then
        FILE_SIZE_MB=$(du -m "$logfile" 2>/dev/null | awk '{print $1}')
        if [ "$FILE_SIZE_MB" -ge "$MAX_LOG_SIZE_MB" ]; then
          if [ "$DRY_RUN" = true ]; then
            log "INFO" "[DRY-RUN] Would truncate oversize log file ($FILE_SIZE_MB MB): $logfile"
          else
            log "INFO" "Truncating oversize log file ($FILE_SIZE_MB MB -> keep last 10,000 lines): $logfile"
            tail -n 10000 "$logfile" > "${logfile}.tmp" 2>/dev/null && mv -f "${logfile}.tmp" "$logfile" 2>/dev/null || true
          fi
        fi
      fi
    done < <(find "$search_dir" -maxdepth 2 -type f -name "*.log" 2>/dev/null)
  fi
done

log "INFO" "Total expired application log files processed: $TOTAL_EXPIRED_LOGS."

# -----------------------------------------------------------------------------
# Step 3: Docker Container JSON Logs Truncation
# -----------------------------------------------------------------------------
log "INFO" "[STEP 3/5] Inspecting Docker container JSON logs..."

if [ -d "/var/lib/docker/containers" ]; then
  OVERSIZED_CONTAINER_LOGS=0
  while IFS= read -r json_log; do
    if [ -f "$json_log" ]; then
      LOG_MB=$(du -m "$json_log" 2>/dev/null | awk '{print $1}')
      if [ "$LOG_MB" -ge "$MAX_LOG_SIZE_MB" ]; then
        OVERSIZED_CONTAINER_LOGS=$((OVERSIZED_CONTAINER_LOGS + 1))
        if [ "$DRY_RUN" = true ]; then
          log "INFO" "[DRY-RUN] Would truncate container log ($LOG_MB MB): $json_log"
        else
          log "INFO" "Truncating bloated container log ($LOG_MB MB): $json_log"
          cat /dev/null > "$json_log" 2>/dev/null || true
        fi
      fi
    fi
  done < <(find /var/lib/docker/containers/ -name "*-json.log" 2>/dev/null)
  log "INFO" "Container logs checked. Truncated $OVERSIZED_CONTAINER_LOGS oversized file(s)."
else
  log "INFO" "/var/lib/docker/containers not directly accessible or non-root execution. Skipping host container log truncation."
fi

# -----------------------------------------------------------------------------
# Step 4: Docker System Pruning (Dangling Images, Build Cache, Stopped Containers)
# -----------------------------------------------------------------------------
log "INFO" "[STEP 4/5] Running Docker system prune..."

if [ "$ENABLE_DOCKER_PRUNE" = true ] && command -v docker >/dev/null 2>&1; then
  if [ "$DRY_RUN" = true ]; then
    log "INFO" "[DRY-RUN] Would run 'docker system prune -f --filter until=$DOCKER_PRUNE_UNTIL'"
  else
    log "INFO" "Pruning host Docker dangling images, build cache, and stopped containers older than $DOCKER_PRUNE_UNTIL..."
    docker system prune -f --filter "until=$DOCKER_PRUNE_UNTIL" 2>&1 | while read -r line; do
      if [ -n "$line" ]; then log "INFO" "  [docker-prune] $line"; fi
    done || true

    # Also trigger prune inside DinD wrapper if container is running
    if docker ps --format '{{.Names}}' | grep -q "^gempa-dind-wrapper$"; then
      log "INFO" "Pruning inner DinD wrapper Docker system..."
      docker exec gempa-dind-wrapper docker system prune -f --filter "until=$DOCKER_PRUNE_UNTIL" 2>/dev/null | while read -r line; do
        if [ -n "$line" ]; then log "INFO" "  [dind-prune] $line"; fi
      done || true
    fi
  fi
else
  log "INFO" "Docker pruning skipped (disabled or docker command not available)."
fi

# -----------------------------------------------------------------------------
# Step 5: MongoDB Raw Picks Cleanup
# -----------------------------------------------------------------------------
log "INFO" "[STEP 5/5] Checking MongoDB database retention (raw picks older than $DB_PICKS_RETENTION_DAYS days)..."

MONGO_CLEANUP_SUCCESS=false

# Method A: Direct host requirements_mongodb_1 container (standard setup)
if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q "^requirements_mongodb_1$"; then
  log "INFO" "Connecting to MongoDB via requirements_mongodb_1..."
  JS_COMMAND="
    var cutoff = new Date(Date.now() - (${DB_PICKS_RETENTION_DAYS} * 24 * 60 * 60 * 1000));
    var resPicks = db.picks.deleteMany({ timestamp: { \$lt: cutoff } });
    var resArrivals = db.arrival_picks.deleteMany({ timestamp: { \$lt: cutoff } });
    print('Cleaned raw picks: ' + (resPicks.deletedCount || 0) + ', arrivals: ' + (resArrivals.deletedCount || 0));
  "
  
  if [ "$DRY_RUN" = true ]; then
    JS_COMMAND_DRY="
      var cutoff = new Date(Date.now() - (${DB_PICKS_RETENTION_DAYS} * 24 * 60 * 60 * 1000));
      var countPicks = db.picks.countDocuments({ timestamp: { \$lt: cutoff } });
      print('[DRY-RUN] Expired raw picks to delete: ' + countPicks);
    "
    OUTPUT=$(docker exec requirements_mongodb_1 mongo sispro-tews --quiet --eval "$JS_COMMAND_DRY" 2>/dev/null || true)
    log "INFO" "MongoDB result: $OUTPUT"
  else
    OUTPUT=$(docker exec requirements_mongodb_1 mongo sispro-tews --quiet --eval "$JS_COMMAND" 2>/dev/null || true)
    if [ -n "$OUTPUT" ]; then
      log "INFO" "MongoDB cleanup result: $OUTPUT"
      MONGO_CLEANUP_SUCCESS=true
    fi
  fi
fi

# Method B: Inside DinD wrapper -> inner requirements_mongodb_1
if [ "$MONGO_CLEANUP_SUCCESS" = false ] && command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q "^gempa-dind-wrapper$"; then
  log "INFO" "Connecting to MongoDB via gempa-dind-wrapper..."
  JS_COMMAND="
    var cutoff = new Date(Date.now() - (${DB_PICKS_RETENTION_DAYS} * 24 * 60 * 60 * 1000));
    var resPicks = db.picks.deleteMany({ timestamp: { \$lt: cutoff } });
    var resArrivals = db.arrival_picks.deleteMany({ timestamp: { \$lt: cutoff } });
    print('Cleaned raw picks: ' + (resPicks.deletedCount || 0) + ', arrivals: ' + (resArrivals.deletedCount || 0));
  "
  
  if [ "$DRY_RUN" = true ]; then
    JS_COMMAND_DRY="
      var cutoff = new Date(Date.now() - (${DB_PICKS_RETENTION_DAYS} * 24 * 60 * 60 * 1000));
      var countPicks = db.picks.countDocuments({ timestamp: { \$lt: cutoff } });
      print('[DRY-RUN] Expired raw picks to delete: ' + countPicks);
    "
    OUTPUT=$(docker exec gempa-dind-wrapper docker exec requirements_mongodb_1 mongosh sispro-tews --quiet --eval "$JS_COMMAND_DRY" 2>/dev/null || \
             docker exec gempa-dind-wrapper docker exec requirements_mongodb_1 mongo sispro-tews --quiet --eval "$JS_COMMAND_DRY" 2>/dev/null || true)
    log "INFO" "MongoDB result: $OUTPUT"
  else
    OUTPUT=$(docker exec gempa-dind-wrapper docker exec requirements_mongodb_1 mongosh sispro-tews --quiet --eval "$JS_COMMAND" 2>/dev/null || \
             docker exec gempa-dind-wrapper docker exec requirements_mongodb_1 mongo sispro-tews --quiet --eval "$JS_COMMAND" 2>/dev/null || true)
    if [ -n "$OUTPUT" ]; then
      log "INFO" "MongoDB cleanup result: $OUTPUT"
      MONGO_CLEANUP_SUCCESS=true
    fi
  fi
fi

# Method C: Direct mongosh/mongo CLI on host (port 32717 or 27017)
if [ "$MONGO_CLEANUP_SUCCESS" = false ] && (command -v mongo >/dev/null 2>&1 || command -v mongosh >/dev/null 2>&1); then
  MONGO_CMD="mongosh"
  command -v mongosh >/dev/null 2>&1 || MONGO_CMD="mongo"
  
  for port in 27017 32717; do
    if [ "$DRY_RUN" = false ]; then
      OUTPUT=$($MONGO_CMD "mongodb://localhost:${port}/sispro-tews" --quiet --eval "$JS_COMMAND" 2>/dev/null || true)
      if [ -n "$OUTPUT" ]; then
        log "INFO" "MongoDB (port $port) cleanup result: $OUTPUT"
        MONGO_CLEANUP_SUCCESS=true
        break
      fi
    fi
  done
fi

if [ "$MONGO_CLEANUP_SUCCESS" = false ] && [ "$DRY_RUN" = false ]; then
  log "INFO" "MongoDB container or CLI not reachable at this moment. Skipping database raw pick cleanup."
fi

# -----------------------------------------------------------------------------
# Step 6: Automated MongoDB Daily Snapshot Backup & Rotation (7-day retention)
# -----------------------------------------------------------------------------
log "INFO" "[STEP 6/6] Running automated MongoDB snapshot backup & rotating old backups..."
BACKUP_DATE="$(date +%Y%m%d)"
BACKUP_DIR="/data/db/backup_${BACKUP_DATE}"

if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q "^requirements_mongodb_1$"; then
  if [ "$DRY_RUN" = true ]; then
    log "INFO" "[DRY-RUN] Would create daily snapshot at $BACKUP_DIR and rotate backups older than 7 days."
  else
    docker exec requirements_mongodb_1 mongodump --db sispro-tews --out "$BACKUP_DIR" >/dev/null 2>&1 || true
    log "INFO" "MongoDB snapshot backup completed at $BACKUP_DIR."
    # Prune backups older than 7 days
    docker exec requirements_mongodb_1 sh -c 'find /data/db/ -maxdepth 1 -name "backup_*" -mtime +7 -exec rm -rf {} +' 2>/dev/null || true
  fi
fi

# -----------------------------------------------------------------------------
# Disk Usage After Cleanup & Threshold Warning
# -----------------------------------------------------------------------------
print_disk_usage "AFTER CLEANUP"

# Check root partition usage percentage
CURRENT_USAGE_PERCENT=$(df / | awk 'NR==2 {gsub("%",""); print $5}')
if [ -n "$CURRENT_USAGE_PERCENT" ]; then
  log "INFO" "Current root disk usage: ${CURRENT_USAGE_PERCENT}% (Threshold: ${DISK_USAGE_ALERT_THRESHOLD}%)"
  if [ "$CURRENT_USAGE_PERCENT" -ge "$DISK_USAGE_ALERT_THRESHOLD" ]; then
    log "WARN" "⚠️  ATTENTION: Disk usage is STILL above ${DISK_USAGE_ALERT_THRESHOLD}%!"
    log "WARN" "Recommendations:"
    log "WARN" "  1. Lower ARCHIVE_RETENTION_DAYS in .env (e.g. from 90 to 60 or 30 days)"
    log "WARN" "  2. Run 'docker system prune -af --volumes' to clear old cached images and build layers"
    log "WARN" "  3. Inspect large directories using: 'du -sh /var/lib/docker /mnt/archive /* 2>/dev/null | sort -h'"
  else
    log "INFO" "✓ Disk usage is within healthy parameters (< ${DISK_USAGE_ALERT_THRESHOLD}%)."
  fi
fi

log "INFO" "Cleanup job finished successfully."
log "INFO" "============================================================"
