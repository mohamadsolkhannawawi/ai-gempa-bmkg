#!/bin/bash
# Switch between GEOFON (public) and IA (internal BMKG) stations
# Usage: ./switch-stations.sh [geofon|ia]

set -e

MODE="${1:-}"

if [ -z "$MODE" ]; then
    echo "Usage: $0 [geofon|ia]"
    echo ""
    echo "  geofon - Switch to GEOFON (156 public broadband stations)"
    echo "  ia     - Switch to internal BMKG IA (203 stations, 172.19.3.87:18000)"
    exit 1
fi

case "$MODE" in
    geofon)
        CSV="station_geofon.csv"
        DESC="GEOFON (156 public broadband)"
        ;;
    ia)
        CSV="station.csv"
        DESC="Internal BMKG IA (203 stations)"
        ;;
    *)
        echo "Invalid mode: $MODE"
        echo "Use: geofon or ia"
        exit 1
        ;;
esac

echo "=== Switching to $DESC ==="
echo ""

# Update .env in wrapper (for next wrapper rebuild)
echo "[1/4] Updating sispro-tews/.env..."
sed -i.bak "s/^STATION_CSV=.*/STATION_CSV=$CSV/" sispro-tews/.env
echo "      ✓ STATION_CSV=$CSV"

# Update .env inside running wrapper
echo "[2/4] Restarting controller_module..."
docker exec gempa-dind-wrapper bash -c "
  cd /app/sispro-tews
  sed -i.bak 's/^STATION_CSV=.*/STATION_CSV=$CSV/' .env
  docker-compose restart controller_module
  sleep 15
" 2>/dev/null || echo "      ⚠ Wrapper not running, will apply on next build"

# Verify seed
echo "[3/4] Verifying station seed..."
docker exec gempa-dind-wrapper docker exec requirements_mongodb_1 mongo sispro-tews --quiet --eval "db.station.count()" 2>/dev/null || echo "      (wrapper offline)"

echo "[4/4] Restarting seedlink replicas..."
docker exec gempa-dind-wrapper bash -c "
  cd /app/sispro-tews
  docker-compose up -d seedlink_module
  sleep 10
" 2>/dev/null || echo "      (wrapper offline)"

echo ""
echo "✓ Switched to $DESC"
echo ""
echo "Status:"
echo "  .env updated: $(grep -o "STATION_CSV=$CSV" sispro-tews/.env && echo '✓' || echo '✗')"
echo ""
echo "Monitor progress (check wrapper logs):"
echo "  tail -f <(docker logs gempa-dind-wrapper 2>&1 | grep -iE 'seed|station|trace')"
echo ""
echo "Verify when complete:"
echo "  - Wrapper: docker logs gempa-dind-wrapper 2>&1 | tail -5"
echo "  - Stations: docker exec gempa-dind-wrapper sh -c 'docker exec requirements_mongodb_1 mongo sispro-tews --quiet --eval \"db.station.count()\"'"
echo "  - Seedlink: docker exec gempa-dind-wrapper sh -c 'docker logs sispro-tews_seedlink_module_1' | grep -c 'Received trace'"
