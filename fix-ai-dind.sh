#!/bin/bash
# Fix AI modules for Docker-in-Docker environment
# Issues: 1) Thread creation limit, 2) ROCm/GPU not available, 3) Huge image size

set -e

WRAPPER="gempa-dind-wrapper"

echo "=== CHECKING DOCKER WRAPPER ULIMITS ==="
docker exec $WRAPPER sh -c 'ulimit -a' 2>/dev/null || echo "Cannot check ulimit"

echo ""
echo "=== CHECKING DOCKER WRAPPER SYSCTL ==="
docker exec $WRAPPER sh -c 'sysctl kernel.threads-max 2>/dev/null || echo "No sysctl access"'

echo ""
echo "=== CHECKING P-PICK SERVICE STARTUP ERROR (first boot) ==="
docker exec $WRAPPER sh -c 'docker logs --tail=50 ai_modules_simple_ai_p-pick_service_1 2>&1 | grep -v "gunicorn" | head -30'

echo ""
echo "=== CHECKING P-PICK CONSUMER STARTUP ERROR ==="
docker exec $WRAPPER sh -c 'docker logs --tail=30 ai_modules_simple_ai_p-pick_consumer_1 2>&1 | head -30'

echo ""
echo "=== AI MODULES STATUS ==="
docker exec $WRAPPER sh -c 'docker ps -a --filter name=ai_modules --format "table {{.Names}}\t{{.Status}}"'
