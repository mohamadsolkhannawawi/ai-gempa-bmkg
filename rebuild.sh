#!/bin/bash
# Rebuild & restart services inside the gempa-dind-wrapper container.
# Usage: ./rebuild.sh [service] [service ...]
#   ./rebuild.sh                  # rebuild all (controller + frontend)
#   ./rebuild.sh controller       # controller_module only
#   ./rebuild.sh frontend         # frontend (tews-ui-vue) only
#   ./rebuild.sh seedlink         # seedlink_module only
#   ./rebuild.sh wrapper          # rebuild wrapper (down + up --no-cache)
#   ./rebuild.sh controller frontend   # multiple at once
set -e

WRAP="gempa-dind-wrapper"
export DOCKER_API_VERSION=1.41

if [ -z "$1" ]; then
    TARGETS="controller frontend"
else
    TARGETS="$@"
fi

for T in $TARGETS; do
    case "$T" in
        wrapper)
            echo "=== Rebuilding gempa-dind-wrapper (full down+up) ==="
            docker-compose -f docker-compose.wrapper.yml down
            docker-compose -f docker-compose.wrapper.yml up -d --build --no-cache
            echo "Waiting 60s for wrapper startup..."
            sleep 60
            ;;
        controller)
            echo "=== Rebuilding controller_module ==="
            docker exec $WRAP bash -c "cd /app/sispro-tews && docker-compose up -d --build controller_module"
            ;;
        frontend)
            echo "=== Rebuilding frontend (tews-ui-vue) ==="
            docker exec $WRAP bash -c "cd /app/tews-ui-vue && docker-compose up -d --build"
            ;;
        seedlink)
            echo "=== Rebuilding seedlink_module ==="
            docker exec $WRAP bash -c "cd /app/sispro-tews && docker-compose up -d --build seedlink_module"
            ;;
        websocket)
            echo "=== Rebuilding websocket_waveform ==="
            docker exec $WRAP bash -c "cd /app/sispro-tews && docker-compose up -d --build websocket_waveform"
            ;;
        *)
            echo "Unknown service: $T"
            echo "Available: wrapper controller frontend seedlink websocket"
            exit 1
            ;;
    esac
done

echo ""
echo "✓ Rebuild complete"
