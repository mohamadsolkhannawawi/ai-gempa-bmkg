#!/bin/bash
# Inspect crash logs for all AI modules
# Usage: ./inspect-ai-errors.sh

set -e

WRAPPER="gempa-dind-wrapper"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${YELLOW}[$1]${NC} $2"; }

log "1" "p-pick_service_1 (last 30 lines)"
docker exec $WRAPPER sh -c 'docker logs --tail=30 ai_modules_simple_ai_p-pick_service_1' 2>&1 | tail -30
echo
log "2" "p-pick_service_2 (last 30 lines)"
docker exec $WRAPPER sh -c 'docker logs --tail=30 ai_modules_simple_ai_p-pick_service_2' 2>&1 | tail -30
echo
log "3" "p-pick_service_3 (last 30 lines)"
docker exec $WRAPPER sh -c 'docker logs --tail=30 ai_modules_simple_ai_p-pick_service_3' 2>&1 | tail -30
echo
log "4" "p-pick_nginx (last 20 lines)"
docker exec $WRAPPER sh -c 'docker logs --tail=20 ai_modules_simple_ai_p-pick_nginx_1' 2>&1 | tail -20
echo
log "5" "p-pick_consumer (last 20 lines)"
docker exec $WRAPPER sh -c 'docker logs --tail=20 ai_modules_simple_ai_p-pick_consumer_1' 2>&1 | tail -20
echo
log "6" "All docker ps filter by ai_modules"
docker exec $WRAPPER sh -c 'docker ps -a --filter name=ai_modules --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
echo
log "7" "Docker images built"
docker exec $WRAPPER sh -c 'docker images | grep -E "ai_modules|p-pick|association|locmag|phase-arrival"'
