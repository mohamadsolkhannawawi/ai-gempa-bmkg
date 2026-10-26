# Server Deployment Test - AI-GEMPA-BMKG
## Branch: main (PHASE 0-8 architecture refactor)

**Server:** riset-01 (bmkg@152.118.31.54)  
**Deployment:** Docker-in-Docker wrapper  
**User:** bmkg (no sudo, docker group)

---

## Prerequisites Check

```bash
# Verify Docker version
docker --version
# Expected: Docker version 20.10.8+

docker compose version
# Expected: Docker Compose version v2.29.2+

# Verify docker group
groups
# Expected: bmkg docker

# Check running containers (geomecca shouldn't conflict)
docker ps
# geomecca uses: 8006, 4002, 27018
# ai-gempa uses: 38006, 38003, 27017 (different ports)
```

---

## Deployment Steps

### 1. Pull Latest Code

```bash
cd ~/GEMPA/ai-gempa-bmkg
git pull origin main

# Verify branch
git branch --show-current
# Expected: main

# Check last commit
git log -1 --oneline
# Expected: 03700ec merge(main): PHASE 0-8 architecture refactor complete
```

### 2. Setup Admin Credentials (First-Time Only)

```bash
# Copy template if not exists
if [ ! -f .env.seed ]; then
  cp .env.seed.example .env.seed
  nano .env.seed
  # Edit password, lalu save
fi

# Verify .env.seed
cat .env.seed | grep INITIAL_ADMIN
# Expected:
# INITIAL_ADMIN_USERNAME=admin
# INITIAL_ADMIN_PASSWORD=***
# INITIAL_ADMIN_EMAIL=admin@bmkg.go.id

# Set secure permissions
chmod 600 .env.seed
```

### 3. Build & Deploy DinD Wrapper

```bash
# Build wrapper image
docker compose -f docker-compose.wrapper.yml build

# Start wrapper (this starts ALL inner services)
docker compose -f docker-compose.wrapper.yml up -d

# Wait 2-3 minutes for full startup
echo "Waiting for services to initialize..."
sleep 180
```

### 4. Verify Wrapper Container

```bash
# Check wrapper running
docker ps | grep gempa-dind-wrapper
# Expected: STATUS = Up X minutes

# Check wrapper logs
docker logs gempa-dind-wrapper --tail 50
# Look for: "Docker daemon started"
```

### 5. Verify Inner Services

```bash
# List all inner containers
docker exec -it gempa-dind-wrapper docker ps

# Expected containers (20+):
# - requirements_mongodb_1
# - requirements_redis_1
# - requirements_kafka_1
# - requirements_zookeeper_1
# - sispro-tews_archiving_module_1..7 (7 replicas)
# - sispro-tews_seedlink_module_1..5 (5 replicas)
# - sispro-tews_controller_module_1
# - sispro-tews_fdsn_api_module_1
# - sispro-tews_record_stream_module_1
# - sispro-tews_websocket_general_1
# - sispro-tews_websocket_waveform_1
# - sispro-tews_public_api_module_1
# - tews-ui-vue_fe_1

# Count running containers
docker exec -it gempa-dind-wrapper docker ps --format '{{.Names}}' | wc -l
# Expected: 20+ containers
```

### 6. Health Check Endpoints

```bash
# Controller API (main backend)
curl -s http://localhost:38003/health
# Expected: {"status":"healthy"} or 200 OK

# Frontend UI
curl -s -o /dev/null -w "%{http_code}" http://localhost:38006
# Expected: 200

# MongoDB connection (inside wrapper)
docker exec -it gempa-dind-wrapper docker exec requirements_mongodb_1 \
  mongosh --quiet --eval "db.adminCommand('ping')"
# Expected: { ok: 1 }

# Redis connection
docker exec -it gempa-dind-wrapper docker exec requirements_redis_1 \
  redis-cli ping
# Expected: PONG
```

### 7. Verify Admin User (Auto-Seeded)

```bash
# Check admin user exists
docker exec -it gempa-dind-wrapper docker exec requirements_mongodb_1 \
  mongosh sispro-tews --quiet --eval 'db.user.findOne({username: "admin"})'

# Expected output (JSON):
# {
#   _id: ObjectId('...'),
#   username: 'admin',
#   email: 'admin@bmkg.go.id',
#   hashed_password: '$pbkdf2-sha256$...',
#   role: 'superadmin',
#   is_active: true,
#   ...
# }
```

### 8. Test Login API

```bash
# Test admin login
curl -X POST http://localhost:38003/api/v1/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"YOUR_PASSWORD_FROM_ENV_SEED"}' | jq

# Expected:
# {
#   "access_token": "eyJ...",
#   "token_type": "bearer",
#   "user": {
#     "username": "admin",
#     "role": "superadmin"
#   }
# }
```

### 9. Test Frontend Access

```bash
# Open browser or curl
curl -I http://152.118.31.54:38006

# Expected headers:
# HTTP/1.1 200 OK
# Content-Type: text/html
```

---

## Post-Deployment Verification

### Check Logs

```bash
# Controller logs
docker exec -it gempa-dind-wrapper docker logs sispro-tews_controller_module_1 --tail 100

# Frontend logs
docker exec -it gempa-dind-wrapper docker logs tews-ui-vue_fe_1 --tail 50

# MongoDB logs
docker exec -it gempa-dind-wrapper docker logs requirements_mongodb_1 --tail 50

# Look for errors (should be clean):
docker exec -it gempa-dind-wrapper docker logs sispro-tews_controller_module_1 2>&1 | grep -iE "error|exception|critical"
```

### Resource Usage

```bash
# Wrapper container stats
docker stats gempa-dind-wrapper --no-stream

# Expected:
# CPU: < 50%
# MEM: 10-20 GB (depends on replicas)

# Disk usage
df -h /mnt/archive
# Ensure sufficient free space (> 500 GB recommended)

# Inner containers stats
docker exec -it gempa-dind-wrapper docker stats --no-stream
```

### Network Connectivity

```bash
# Verify inner network
docker exec -it gempa-dind-wrapper docker network ls | grep sispro-tews

# Ping MongoDB from controller
docker exec -it gempa-dind-wrapper docker exec sispro-tews_controller_module_1 \
  ping -c 3 mongodb

# Ping Redis from controller
docker exec -it gempa-dind-wrapper docker exec sispro-tews_controller_module_1 \
  ping -c 3 redis
```

---

## Troubleshooting

### Problem: Wrapper Fails to Start

```bash
# Check logs
docker logs gempa-dind-wrapper --tail 200

# Common causes:
# - Port conflict: check geomecca ports
# - Volume permission: check /mnt/archive ownership
# - Docker daemon issue: restart host Docker

# Restart wrapper
docker compose -f docker-compose.wrapper.yml restart
```

### Problem: Inner Services Not Starting

```bash
# Enter wrapper
docker exec -it gempa-dind-wrapper bash

# Inside wrapper, check failed containers
docker ps -a | grep -E "Exited|Restarting"

# Check specific service logs
docker logs requirements_mongodb_1 --tail 100
docker logs sispro-tews_controller_module_1 --tail 100

# Restart specific service
cd /app/sispro-tews
docker compose restart controller_module
```

### Problem: Admin User Missing

```bash
# Re-run seed script
docker exec -it gempa-dind-wrapper docker exec \
  -e INITIAL_ADMIN_USERNAME=admin \
  -e INITIAL_ADMIN_PASSWORD=Bmkg2026 \
  -e INITIAL_ADMIN_EMAIL=admin@bmkg.go.id \
  -e INITIAL_ADMIN_FULLNAME="Administrator BMKG" \
  -e MONGO_HOST=mongodb \
  -e MONGO_PORT=27017 \
  -e MONGO_DB_NAME=sispro-tews \
  requirements_controller_module_1 \
  python3 /app/seed_admin_user.py

# Verify creation
docker exec -it gempa-dind-wrapper docker exec requirements_mongodb_1 \
  mongosh sispro-tews --quiet --eval 'db.user.findOne({username: "admin"})'
```

### Problem: Port Conflict with Geomecca

```bash
# Verify geomecca ports
docker ps | grep geomecca
# geomecca: 8006, 4002, 27018

# ai-gempa should use DIFFERENT ports:
# - 38006 (frontend, not 8006)
# - 38003 (controller, not 4002)
# - 27017 (mongodb, not 27018)

# If conflict, edit docker-compose.wrapper.yml port mappings
```

### Problem: MongoDB Connection Timeout

```bash
# Check MongoDB running inside wrapper
docker exec -it gempa-dind-wrapper docker ps | grep mongodb

# Restart MongoDB
docker exec -it gempa-dind-wrapper bash
cd /app/sispro-tews
docker compose restart mongodb

# Wait 30 seconds, then restart controller
sleep 30
docker compose restart controller_module
```

---

## Restart Procedures

### Restart Single Service

```bash
# Enter wrapper
docker exec -it gempa-dind-wrapper bash

# Restart specific service
cd /app/sispro-tews
docker compose restart controller_module

# Verify
docker ps | grep controller_module
```

### Restart All Inner Services

```bash
# Enter wrapper
docker exec -it gempa-dind-wrapper bash

# Restart backend
cd /app/sispro-tews
docker compose restart

# Restart frontend
cd /app/tews-ui-vue
docker compose restart

# Exit wrapper
exit
```

### Restart Wrapper (Full Stack)

```bash
# Graceful restart
docker compose -f docker-compose.wrapper.yml restart

# Wait 3-5 minutes for full startup
sleep 300

# Verify
docker ps | grep gempa-dind-wrapper
docker exec -it gempa-dind-wrapper docker ps
```

### Rebuild & Redeploy

```bash
# Stop wrapper
docker compose -f docker-compose.wrapper.yml down

# Pull latest code
git pull origin main

# Rebuild
docker compose -f docker-compose.wrapper.yml build --no-cache

# Start fresh
docker compose -f docker-compose.wrapper.yml up -d

# Wait for initialization
sleep 180

# Verify
docker exec -it gempa-dind-wrapper docker ps
```

---

## Maintenance Commands

### Update Code (No Downtime)

```bash
cd ~/GEMPA/ai-gempa-bmkg
git pull origin main

# Rebuild wrapper with new code
docker compose -f docker-compose.wrapper.yml build

# Recreate wrapper (inner services auto-restart)
docker compose -f docker-compose.wrapper.yml up -d --force-recreate
```

### Backup MongoDB

```bash
# Backup database
docker exec -it gempa-dind-wrapper docker exec requirements_mongodb_1 \
  mongodump --out /backup/mongodb-$(date +%F-%H%M) --gzip

# Copy to host
docker cp gempa-dind-wrapper:/backup/mongodb-$(date +%F-%H%M) \
  ~/backups/mongodb/
```

### Clean Docker Resources

```bash
# Inside wrapper
docker exec -it gempa-dind-wrapper docker system prune -f

# Host Docker cleanup
docker system prune -f
```

---

## Success Criteria

- [ ] Wrapper container running: `docker ps | grep gempa-dind-wrapper`
- [ ] 20+ inner containers running: `docker exec -it gempa-dind-wrapper docker ps`
- [ ] Frontend accessible: `curl http://localhost:38006` → 200
- [ ] Controller healthy: `curl http://localhost:38003/health` → healthy
- [ ] Admin user exists: `db.user.findOne({username: "admin"})` → found
- [ ] Login works: `curl POST /api/v1/user/login` → access_token
- [ ] No critical errors: `docker logs ... | grep -iE "error|critical"` → clean
- [ ] MongoDB ping: `db.adminCommand('ping')` → ok: 1
- [ ] Redis ping: `redis-cli ping` → PONG

---

## Next Steps

1. **Configure monitoring:** Setup Prometheus + Grafana for metrics
2. **Setup backup cron:** Daily MongoDB backup + log rotation
3. **SSL/TLS:** Add reverse proxy (Nginx/Caddy) for HTTPS
4. **Firewall:** Restrict port access to internal network only
5. **Documentation:** Update server runbook with production configs

---

**Deployment Date:** 2026-10-26  
**Version:** v2.0.0 (PHASE 0-8 complete)  
**Contact:** DevOps BMKG
