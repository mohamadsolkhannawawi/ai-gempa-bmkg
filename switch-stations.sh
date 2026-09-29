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
echo "[1/5] Updating sispro-tews/.env..."
sed -i.bak "s/^STATION_CSV=.*/STATION_CSV=$CSV/" sispro-tews/.env
echo "      ✓ STATION_CSV=$CSV"

# Update .env inside running wrapper (root dir)
echo "[2/5] Updating wrapper /app/sispro-tews/.env..."
docker exec gempa-dind-wrapper bash -c "
  cd /app/sispro-tews
  sed -i.bak 's/^STATION_CSV=.*/STATION_CSV=$CSV/' .env
" 2>/dev/null || echo "      ⚠ Wrapper not running"

# Update controller_module/.env in wrapper
echo "[3/5] Updating wrapper /app/sispro-tews/controller_module/.env..."
docker exec gempa-dind-wrapper bash -c "
  cd /app/sispro-tews/controller_module
  sed -i.bak 's/^STATION_CSV=.*/STATION_CSV=$CSV/' .env
  docker-compose restart controller_module
  sleep 15
" 2>/dev/null || echo "      ⚠ Wrapper not running"

# Verify seed
echo "[4/5] Verifying station seed..."
docker exec gempa-dind-wrapper docker exec requirements_mongodb_1 mongo sispro-tews --quiet --eval "db.station.count()" 2>/dev/null || echo "      (wrapper offline)"

echo "[5/5] Restarting seedlink replicas..."
docker exec gempa-dind-wrapper bash -c "
  cd /app/sispro-tews
  docker-compose up -d seedlink_module
  sleep 10
" 2>/dev/null || echo "      (wrapper offline)"

echo ""
echo "✓ Switched to $DESC"
echo ""
echo "Status:"
echo "  Root .env: $(grep -o \"STATION_CSV=$CSV\" sispro-tews/.env && echo '✓' || echo '✗')"
echo "  Controller .env: $(docker exec gempa-dind-wrapper cat /app/sispro-tews/controller_module/.env 2>/dev/null | grep -c \"STATION_CSV=$CSV\" 2>/dev/null && echo '✓' || echo '✗')"
echo ""
echo "Monitor progress (check wrapper logs):"
echo "  tail -f <(docker logs gempa-dind-wrapper 2>&1 | grep -iE 'seed|station|trace')"
echo ""
echo "Verify when complete:"
echo "  - Wrapper: docker logs gempa-dind-wrapper 2>&1 | tail -5"
echo "  - Stations: docker exec gempa-dind-wrapper sh -c 'docker exec requirements_mongodb_1 mongo sispro-tews --quiet --eval \"db.station.count()\"'"
echo "  - Server: curl -s http://localhost:38003/api/v1/station/getall | grep -o '\"server_seedlink\":\"[^\"]*\"' | head -1"
