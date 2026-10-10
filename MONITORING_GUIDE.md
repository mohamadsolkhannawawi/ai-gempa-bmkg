# Monitoring & Troubleshooting Guide: AI-GEMPA

Panduan lengkap untuk monitoring, troubleshooting, dan maintenance sistem AI-GEMPA di server riset-01.

**Target User**: Operator/Admin yang perlu monitoring sistem tanpa bantuan developer.

---

## Quick Reference

| Task | Command |
|---|---|
| Status semua services | [1.1 Check Services Status](#11-check-services-status) |
| Logs realtime | [2.2 Follow Logs Realtime](#22-follow-logs-realtime) |
| Check seeding complete | [3.1 Verify Admin User](#31-verify-admin-user) |
| Check waveforms streaming | [4.1 Check Station Streaming](#41-check-station-streaming) |
| Restart service | [7.1 Restart Single Service](#71-restart-single-service) |
| Full system restart | [7.2 Full System Restart](#72-full-system-restart) |

---

## 1. Health Checks

### 1.1 Check Services Status

**Cek wrapper container running:**
```bash
cd ~/GEMPA/ai-gempa-bmkg
docker-compose -f docker-compose.wrapper.yml ps
```

**Expected output:**
```
        Name                Command        State   Ports
--------------------------------------------------------
gempa-dind-wrapper   /entrypoint-wrapp...   Up
```

**Cek semua internal services:**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose ps
"
```

**Expected output:** Semua service `State: Up`
```
           Name                         State
------------------------------------------------
requirements_kafka_1                    Up
requirements_mongodb_1                  Up
requirements_redis_1                    Up
requirements_zookeeper_1                Up
sispro-tews_association_module_1        Up
sispro-tews_controller_module_1         Up
sispro-tews_frontend_1                  Up
sispro-tews_locmag_module_1             Up
sispro-tews_p-pick_service_1            Up
sispro-tews_seedlink_module_1           Up
sispro-tews_websocket_module_1          Up
```

---

### 1.2 Quick Health Check (One Command)

```bash
docker exec -it gempa-dind-wrapper bash -c '
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
echo "=== SERVICES STATUS ==="
docker-compose ps --filter "status=running" | grep -E "Up|Name"
echo ""
echo "=== ADMIN USER ==="
docker-compose exec -T mongodb mongo --quiet sispro-tews --eval "print(\"Admin exists: \" + (db.user.countDocuments({username:\"admin\"}) > 0 ? \"YES\" : \"NO\"))"
echo ""
echo "=== STATIONS IN DB ==="
docker-compose exec -T mongodb mongo --quiet sispro-tews --eval "print(\"Total stations: \" + db.station.countDocuments({}))"
echo ""
echo "=== REDIS KEYS (waveforms) ==="
docker exec requirements_redis_1 redis-cli DBSIZE
echo ""
echo "=== DISK USAGE ==="
df -h /var/lib/docker | tail -1
'
```

**Expected output:**
- Services: Semua `Up`
- Admin exists: `YES`
- Total stations: `20`
- Redis DBSIZE: `> 0` (ada waveform keys)
- Disk usage: `< 80%`

---

### 1.3 API Health Check

```bash
# Check controller API (port 4002)
curl -s http://localhost:4002/api/v2/health | jq .

# Check frontend (port 8006)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8006
```

**Expected:**
- API: `{"status": "healthy"}` atau HTTP 200
- Frontend: HTTP 200

---

## 2. Log Monitoring

### 2.1 View Recent Logs

**Wrapper logs (last 100 lines):**
```bash
docker-compose -f docker-compose.wrapper.yml logs --tail=100 gempa-dind-wrapper
```

**Controller logs (main API):**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --tail=100 controller_module
"
```

**SeedLink logs (waveform ingestion):**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --tail=100 seedlink_module
"
```

**P-Pick logs (AI inference):**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --tail=100 p-pick_service
"
```

---

### 2.2 Follow Logs Realtime

**Single service (Ctrl+C to exit):**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs -f controller_module
"
```

**Multiple services:**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs -f controller_module seedlink_module p-pick_service
"
```

**All services (verbose):**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs -f
"
```

---

### 2.3 Search Logs for Errors

**Find errors in controller:**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --tail=500 controller_module | grep -i -E 'error|exception|traceback|failed'
"
```

**Find errors in all services:**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --tail=1000 | grep -i -E 'error|exception|traceback|failed' | head -20
"
```

**Check for crashes (service restarts):**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose ps -a | grep -E 'Restarting|Exit'
"
```

---

## 3. Seeding & Initialization Checks

### 3.1 Verify Admin User

```bash
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval '
db.user.findOne({username: "admin"})
'
```

**Expected output:**
```json
{
  "_id": ObjectId("..."),
  "username": "admin",
  "password": "pbkdf2_sha256$...",
  "role": "admin",
  "created_at": "..."
}
```

**If null:** Seeding failed. Check `.env.seed` exists and restart controller.

---

### 3.2 Verify Stations Loaded

```bash
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval '
print("Total stations: " + db.station.countDocuments({}));
print("Public stations: " + db.station.countDocuments({server_seedlink: "rtserve.earthscope.org:18000"}));
db.station.find({}, {code:1, network:1, name:1, _id:0}).limit(5).forEach(printjson);
'
```

**Expected:**
- Total: 20
- Public: 20 (all from rtserve.earthscope.org)
- Sample: AU.ARMA, II.KAPI, IU.DAV, etc.

---

### 3.3 Check Seeding Logs

```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs controller_module | grep -E 'seed|admin|user created'
"
```

**Expected:** `Admin user seeded successfully` or similar message.

---

## 4. Waveform Streaming Checks

### 4.1 Check Station Streaming

**See which stations sending data:**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --tail=200 seedlink_module | grep 'Received trace' | awk '{print \$NF}' | sort -u
"
```

**Expected:** List of station codes (JAY, KAPK, KAPI, DAV, etc.)

**Count traces received (last 100 lines):**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --tail=100 seedlink_module | grep -c 'Received trace'
"
```

**Expected:** > 10 traces in recent logs (active streaming).

---

### 4.2 Check Redis Waveform Keys

```bash
# Total keys (should grow over time)
docker exec requirements_redis_1 redis-cli DBSIZE

# Sample keys (station + channel)
docker exec requirements_redis_1 redis-cli KEYS '*' | head -10

# Keys for specific station (e.g., AU.ARMA)
docker exec requirements_redis_1 redis-cli KEYS 'AU.ARMA*'
```

**Expected:**
- DBSIZE: > 100 (varies with active stations/channels)
- Sample keys: `AU.ARMA.00.BHZ`, `II.KAPI..BHN`, etc.

---

### 4.3 Check SeedLink Subscriptions

```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --tail=500 seedlink_module | grep -E 'Subscribing|first pulling station'
"
```

**Expected:** Lines showing station subscription attempts.

---

## 5. Database Queries

### 5.1 MongoDB Shell Access

```bash
docker exec -it requirements_mongodb_1 mongo sispro-tews
```

**Useful queries inside shell:**
```javascript
// Count collections
db.user.countDocuments({})
db.station.countDocuments({})
db.pick.countDocuments({})
db.event.countDocuments({})

// Find recent picks (if any)
db.pick.find().sort({created_at: -1}).limit(3).pretty()

// Find events (earthquakes detected)
db.event.find().sort({origin_time: -1}).limit(5).pretty()

// Check station by code
db.station.findOne({code: "ARMA"})

// Exit shell
exit
```

---

### 5.2 One-Line MongoDB Queries

**Count documents:**
```bash
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval '
print("Users: " + db.user.countDocuments({}));
print("Stations: " + db.station.countDocuments({}));
print("Picks: " + db.pick.countDocuments({}));
print("Events: " + db.event.countDocuments({}));
'
```

**Recent picks:**
```bash
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval '
db.pick.find().sort({created_at: -1}).limit(5).forEach(printjson)
'
```

**Recent events:**
```bash
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval '
db.event.find().sort({origin_time: -1}).limit(5).forEach(printjson)
'
```

---

### 5.3 Check Redis Data

**All keys:**
```bash
docker exec requirements_redis_1 redis-cli KEYS '*' | wc -l
```

**Sample key content (waveform):**
```bash
docker exec requirements_redis_1 redis-cli --scan --pattern 'AU.ARMA*' | head -1 | xargs -I {} docker exec requirements_redis_1 redis-cli GET {}
```

**TTL check (keys should have expiry):**
```bash
docker exec requirements_redis_1 redis-cli --scan --pattern 'AU.ARMA*' | head -1 | xargs -I {} docker exec requirements_redis_1 redis-cli TTL {}
```

**Expected TTL:** 300-3600 seconds (keys auto-expire).

---

## 6. Performance Monitoring

### 6.1 Container Resource Usage

```bash
# All containers CPU/Memory
docker stats --no-stream

# Inside wrapper (internal containers)
docker exec -it gempa-dind-wrapper docker stats --no-stream
```

**Watch out for:**
- CPU > 200% sustained (over-utilized)
- Memory > 80% (risk of OOM kill)

---

### 6.2 Disk Usage

```bash
# Docker disk usage
docker system df

# Inside wrapper
docker exec -it gempa-dind-wrapper df -h

# Check MongoDB data size
docker exec requirements_mongodb_1 du -sh /data/db
```

**Cleanup if disk > 80%:**
```bash
docker system prune -a --volumes
```

---

### 6.3 Network Connectivity

**Check SeedLink server reachable:**
```bash
docker exec -it gempa-dind-wrapper bash -c "
timeout 5 bash -c '</dev/tcp/rtserve.earthscope.org/18000' && echo 'SeedLink OK' || echo 'SeedLink FAIL'
"
```

**Check MongoDB reachable:**
```bash
docker exec requirements_redis_1 redis-cli PING
```

**Expected:** `PONG`

---

## 7. Service Management

### 7.1 Restart Single Service

**Example: Restart controller:**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose restart controller_module
"
```

**Example: Restart seedlink (clear cache + restart):**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
rm -f seedlink_module/data/station.csv
docker-compose restart seedlink_module
"
```

---

### 7.2 Full System Restart

**Restart wrapper (graceful, preserves data):**
```bash
cd ~/GEMPA/ai-gempa-bmkg
docker-compose -f docker-compose.wrapper.yml restart
```

**Full rebuild (nuclear option, USE WITH CAUTION):**
```bash
cd ~/GEMPA/ai-gempa-bmkg
docker-compose -f docker-compose.wrapper.yml down
docker-compose -f docker-compose.wrapper.yml up -d --build --no-cache
```

**WARNING:** `down` without `-v` preserves MongoDB data. Add `-v` only if you want to **DELETE ALL DATA**.

---

### 7.3 Stop & Start Services

**Stop all:**
```bash
cd ~/GEMPA/ai-gempa-bmkg
docker-compose -f docker-compose.wrapper.yml stop
```

**Start all:**
```bash
cd ~/GEMPA/ai-gempa-bmkg
docker-compose -f docker-compose.wrapper.yml start
```

**Stop single service (inside wrapper):**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose stop controller_module
"
```

---

## 8. Troubleshooting Common Issues

### 8.1 Admin User Missing

**Symptoms:** Cannot login with admin/Bmkg2026.

**Diagnosis:**
```bash
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval 'db.user.findOne({username:"admin"})'
```

**If null, fix:**
1. Check `.env.seed` exists in `sispro-tews/controller_module/`:
```bash
docker exec -it gempa-dind-wrapper bash -c "
cd /app/sispro-tews/controller_module
ls -la .env.seed
"
```

2. If missing, create and restart:
```bash
docker exec -it gempa-dind-wrapper bash -c "
cd /app/sispro-tews/controller_module
cat > .env.seed <<EOF
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=Bmkg2026
EOF
"

docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose restart controller_module
"
```

3. Verify:
```bash
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval 'db.user.findOne({username:"admin"})'
```

---

### 8.2 No Waveforms Streaming

**Symptoms:** Redis DBSIZE = 0, no "Received trace" in logs.

**Diagnosis:**
```bash
# Check seedlink logs for errors
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --tail=100 seedlink_module | grep -i error
"

# Check SeedLink connectivity
docker exec -it gempa-dind-wrapper bash -c "
timeout 5 bash -c '</dev/tcp/rtserve.earthscope.org/18000' && echo 'SeedLink OK' || echo 'SeedLink FAIL'
"
```

**Fix:**
1. Delete stale cache:
```bash
docker exec -it gempa-dind-wrapper bash -c "
cd /app/sispro-tews/seedlink_module/data
rm -f station.csv
"
```

2. Restart seedlink:
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose restart seedlink_module
"
```

3. Wait 30s, verify:
```bash
docker exec requirements_redis_1 redis-cli DBSIZE
```

---

### 8.3 Service Keeps Restarting

**Symptoms:** `docker-compose ps` shows `Restarting` status.

**Diagnosis:**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --tail=50 <service_name> | grep -i -E 'error|traceback|exit'
"
```

**Common causes:**
- **OOM kill**: Memory limit exceeded → increase in docker-compose.yml
- **Port conflict**: Another process using port → check `netstat -tulpn`
- **Config error**: Missing env var → check service logs
- **Database unavailable**: MongoDB/Redis not ready → wait or restart

---

### 8.4 Frontend Not Loading (port 8006)

**Diagnosis:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8006
```

**If not 200:**
1. Check frontend container running:
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose ps frontend
"
```

2. Check logs:
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --tail=50 frontend
"
```

3. Restart:
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose restart frontend
"
```

---

### 8.5 High CPU / Memory Usage

**Diagnosis:**
```bash
docker exec -it gempa-dind-wrapper docker stats --no-stream | grep -E 'p-pick|association|locmag'
```

**Fix:**
- **P-Pick high CPU**: Reduce `MAX_WORKERS` in `p-pick_service/.env`
- **Association high memory**: Reduce batch size in config
- **General high load**: Scale down non-essential services

---

### 8.6 MongoDB Connection Refused

**Symptoms:** Controller logs show "Connection refused" to MongoDB.

**Diagnosis:**
```bash
docker exec requirements_mongodb_1 mongod --version
docker exec requirements_redis_1 redis-cli PING
```

**Fix:**
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose restart mongodb redis
"
```

Wait 10s for MongoDB to start, then restart controller.

---

## 9. Maintenance Tasks

### 9.1 Update Station List

1. Edit CSV on local machine:
```bash
# On local (Windows)
cd D:\Projects\GEMPA\ai-gempa-bmkg
notepad sispro-tews\seedlink_module\data\station_public20.csv
```

2. Commit + push:
```bash
git add sispro-tews/seedlink_module/data/station_public20.csv
git commit -m "feat(stations): update station list"
git push origin main
```

3. Pull on server:
```bash
cd ~/GEMPA/ai-gempa-bmkg
git pull origin main
```

4. MongoDB direct update (faster than rebuild):
```bash
# Delete old station
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval '
db.station.deleteOne({code: "OLDCODE", network: "XX"})
'

# Insert new station
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval '
db.station.insertOne({
  code: "NEWCODE",
  network: "XX",
  channel: ["BHE", "BHN", "BHZ"],
  elevation: 0.0,
  latitude: -6.0,
  location: "",
  longitude: 106.0,
  name: "XX.NEWCODE (Location)",
  server_fdsn: "IRIS",
  server_seedlink: "rtserve.earthscope.org:18000"
})
'
```

5. Restart seedlink:
```bash
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
rm -f seedlink_module/data/station.csv
docker-compose restart seedlink_module
"
```

---

### 9.2 Backup Database

```bash
# Create backup directory
mkdir -p ~/backups/$(date +%Y%m%d)

# Backup MongoDB (all collections)
docker exec requirements_mongodb_1 mongodump --db sispro-tews --archive=/tmp/backup.archive

# Copy backup out of container
docker cp requirements_mongodb_1:/tmp/backup.archive ~/backups/$(date +%Y%m%d)/sispro-tews-$(date +%Y%m%d-%H%M%S).archive
```

**Restore:**
```bash
docker cp ~/backups/20261010/sispro-tews-20261010-120000.archive requirements_mongodb_1:/tmp/restore.archive
docker exec requirements_mongodb_1 mongorestore --db sispro-tews --archive=/tmp/restore.archive
```

---

### 9.3 Clean Up Old Data

**Delete old picks (older than 30 days):**
```bash
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval '
var cutoff = new Date();
cutoff.setDate(cutoff.getDate() - 30);
db.pick.deleteMany({created_at: {$lt: cutoff.toISOString()}})
'
```

**Delete old events (older than 90 days):**
```bash
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval '
var cutoff = new Date();
cutoff.setDate(cutoff.getDate() - 90);
db.event.deleteMany({origin_time: {$lt: cutoff.toISOString()}})
'
```

---

### 9.4 Update Docker Images

```bash
cd ~/GEMPA/ai-gempa-bmkg
git pull origin main
docker-compose -f docker-compose.wrapper.yml pull
docker-compose -f docker-compose.wrapper.yml up -d --build
```

---

## 10. Emergency Procedures

### 10.1 System Not Responding

```bash
# Force stop all
cd ~/GEMPA/ai-gempa-bmkg
docker-compose -f docker-compose.wrapper.yml kill

# Remove containers (preserves data)
docker-compose -f docker-compose.wrapper.yml down

# Restart fresh
docker-compose -f docker-compose.wrapper.yml up -d
```

---

### 10.2 Data Corruption (MongoDB)

**Backup first**, then:
```bash
docker exec requirements_mongodb_1 mongod --repair
docker exec -it gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose restart mongodb
"
```

---

### 10.3 Disk Full

```bash
# Check disk usage
df -h

# Clean Docker cache
docker system prune -a --volumes

# Inside wrapper
docker exec -it gempa-dind-wrapper docker system prune -a
```

---

## 11. Automated Monitoring Script

Save as `~/monitor.sh`:

```bash
#!/bin/bash
# AI-GEMPA Automated Health Monitor

cd ~/GEMPA/ai-gempa-bmkg

echo "=== $(date) ==="
echo ""

# Wrapper status
echo "1. Wrapper Status:"
docker-compose -f docker-compose.wrapper.yml ps | grep gempa-dind-wrapper
echo ""

# Internal services
echo "2. Internal Services:"
docker exec gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose ps --filter 'status=running' | wc -l
" 2>/dev/null | xargs -I {} echo "  Running services: {}"
echo ""

# Database
echo "3. Database Status:"
docker exec requirements_mongodb_1 mongo --quiet sispro-tews --eval '
print("  Admin: " + (db.user.countDocuments({username:"admin"}) > 0 ? "OK" : "MISSING"));
print("  Stations: " + db.station.countDocuments({}));
print("  Picks: " + db.pick.countDocuments({}));
print("  Events: " + db.event.countDocuments({}));
' 2>/dev/null
echo ""

# Waveforms
echo "4. Waveform Streaming:"
docker exec requirements_redis_1 redis-cli DBSIZE 2>/dev/null | xargs -I {} echo "  Redis keys: {}"
echo ""

# Errors (last 10 min)
echo "5. Recent Errors:"
docker exec gempa-dind-wrapper bash -c "
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose logs --since 10m 2>/dev/null | grep -i -c error
" | xargs -I {} echo "  Error count: {}"
echo ""

# Disk
echo "6. Disk Usage:"
df -h /var/lib/docker | tail -1 | awk '{print "  Docker partition: " $5 " used"}'
echo ""

echo "=== End Report ==="
```

**Run periodically:**
```bash
chmod +x ~/monitor.sh
watch -n 60 ~/monitor.sh   # Every 60 seconds
```

---

## 12. Log Rotation

**Prevent logs from filling disk:**

Edit `/etc/docker/daemon.json` (requires sudo):
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker daemon:
```bash
sudo systemctl restart docker
```

---

## 13. Contact & Escalation

**Before escalating:**
1. Run [1.2 Quick Health Check](#12-quick-health-check-one-command)
2. Capture error logs: [2.3 Search Logs for Errors](#23-search-logs-for-errors)
3. Note symptoms + what changed recently

**Include in escalation:**
- Output dari Quick Health Check
- Last 100 lines dari error logs
- What you tried
- Timeline (when issue started)

---

## Appendix A: Port Reference

| Port | Service | Access |
|---|---|---|
| 4002 | Controller API | http://localhost:4002 |
| 8006 | Frontend UI | http://localhost:8006 |
| 8001 | WebSocket | ws://localhost:8001 |
| 27017 | MongoDB (internal) | - |
| 6379 | Redis (internal) | - |
| 9092 | Kafka (internal) | - |

---

## Appendix B: File Locations

| Item | Path (inside wrapper) |
|---|---|
| Station CSV | `/app/sispro-tews/seedlink_module/data/station_public20.csv` |
| Controller config | `/app/sispro-tews/controller_module/.env` |
| Seed env | `/app/sispro-tews/controller_module/.env.seed` |
| Docker compose | `/app/sispro-tews/docker-compose.yml` |
| MongoDB data | `/data/db` (inside mongodb container) |

---

**END OF MONITORING GUIDE**

Simpan dokumen ini dan gunakan sebagai referensi mandiri untuk monitoring sistem AI-GEMPA.
