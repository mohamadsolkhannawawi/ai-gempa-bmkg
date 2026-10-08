#!/bin/bash
# Verify AI pipeline is working end-to-end.
# Usage: ./verify-ai-pipeline.sh

set -e

WRAPPER="gempa-dind-wrapper"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${YELLOW}[$1]${NC} $2"; }
ok() { echo -e "${GREEN}[$1]${NC} $2"; }
err() { echo -e "${RED}[$1]${NC} $2"; }

log "STEP 1" "Check AI services running"
docker exec $WRAPPER sh -c 'docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "ai_modules_simple_ai_(phase-arrival|association|locmag|p-pick)"' || {
  err "FAIL" "AI services not running"
  exit 1
}

log "STEP 2" "Check Kafka topics"
docker exec $WRAPPER sh -c 'docker exec requirements_kafka_1 kafka-topics.sh --list --bootstrap-server localhost:9092 2>/dev/null | sort' || {
  err "FAIL" "Cannot list Kafka topics"
  exit 1
}

log "STEP 3" "Check phase-arrival consumer logs (last 20 lines)"
docker exec $WRAPPER sh -c 'docker logs --tail=20 ai_modules_simple_ai_phase-arrival_module_1 2>&1' || true

log "STEP 4" "Check association consumer logs (last 20 lines)"
docker exec $WRAPPER sh -c 'docker logs --tail=20 ai_modules_simple_ai_association_module_1 2>&1' || true

log "STEP 5" "Check locmag consumer logs (last 20 lines)"
docker exec $WRAPPER sh -c 'docker logs --tail=20 ai_modules_simple_ai_locmag_module_1 2>&1' || true

log "STEP 6" "Count messages in Kafka topics"
for TOPIC in waveform phase-arrival association event; do
  COUNT=$(docker exec $WRAPPER sh -c "docker exec requirements_kafka_1 kafka-run-class.sh kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic $TOPIC 2>/dev/null | tail -1" 2>/dev/null | awk -F':' '{print $3}')
  if [ -n "$COUNT" ] && [ "$COUNT" != "" ]; then
    ok "KAFKA" "Topic '$TOPIC': $COUNT messages"
  else
    log "KAFKA" "Topic '$TOPIC': not found or empty"
  fi
done

log "STEP 7" "Check MongoDB events collection"
docker exec $WRAPPER sh -c 'docker exec requirements_mongodb_1 mongosh --quiet --eval "db = db.getSiblingDB(\"ai-gempa\"); print(\"events count:\", db.events.countDocuments({})); print(\"latest event:\", JSON.stringify(db.events.find().sort({created_at:-1}).limit(1).toArray()[0] || \"none\"))"' 2>&1 | head -20 || log "MONGO" "Could not query MongoDB"

log "STEP 8" "Check Redis for seedlink data"
docker exec $WRAPPER sh -c 'docker exec requirements_redis_1 redis-cli DBSIZE' 2>&1 || log "REDIS" "Could not query Redis"

ok "DONE" "Verification complete. Review logs above for any errors."
