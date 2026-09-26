# 🚀 Panduan Deployment GEMPA AI-TEWS

**Sistem Monitoring Gempa Real-time dengan AI Detection**

---

## 📋 Daftar Isi

1. [Arsitektur Sistem](#arsitektur-sistem)
2. [Prerequisites](#prerequisites)
3. [Setup User & Permissions](#setup-user--permissions)
4. [Struktur Direktori](#struktur-direktori)
5. [Konfigurasi Environment](#konfigurasi-environment)
6. [Network & Port Setup](#network--port-setup)
7. [Deployment Steps](#deployment-steps)
8. [Verifikasi & Health Check](#verifikasi--health-check)
9. [Admin User Setup](#admin-user-setup)
10. [Troubleshooting](#troubleshooting)
11. [Maintenance & Backup](#maintenance--backup)

---

## 🏗️ Arsitektur Sistem

### Stack Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Host: Ubuntu 22.04 Server (152.118.31.54)                 │
│  User: bmkg (no sudo, docker group)                         │
├─────────────────────────────────────────────────────────────┤
│  DinD Wrapper Container (gempa-dind-wrapper)                │
│  ├─ sispro-tews_network (Docker network)                    │
│  │                                                           │
│  ├─ Infrastructure Services                                 │
│  │  ├─ MongoDB :27017 (internal) → :32717 (host)           │
│  │  ├─ Redis :6379 (internal) → :36379 (host)              │
│  │  ├─ Kafka :9092 (internal) → :39092 (host)              │
│  │  └─ Zookeeper :2181 (internal) → :32181 (host)          │
│  │                                                           │
│  ├─ SISPRO-TEWS Backend Modules                            │
│  │  ├─ record_stream_module :38001 → :8001                 │
│  │  ├─ fdsn_api_module :38002 → :8002                      │
│  │  ├─ controller_module :38003 → :8003                    │
│  │  ├─ websocket_waveform :38004 → :8004                   │
│  │  ├─ websocket_general :38005 → :8005                    │
│  │  ├─ public_api_module :38007 → :8007                    │
│  │  ├─ fdsn_module (internal scheduler)                    │
│  │  ├─ archiving_module (7 replicas, 20GB each)            │
│  │  └─ seedlink_module (5 replicas, 5GB each)              │
│  │                                                           │
│  ├─ TEWS UI Frontend                                        │
│  │  └─ tews-ui-vue :38006 → :8006                          │
│  │                                                           │
│  └─ AI-TEWS Modules                                         │
│     └─ AI detection :8000                                   │
└─────────────────────────────────────────────────────────────┘
```

### Resource Requirements

| Component | CPU | RAM | Disk | Replicas |
|-----------|-----|-----|------|----------|
| archiving_module | 2 core | 20 GB | 100 GB | 7 |
| seedlink_module | 1 core | 5 GB | 50 GB | 5 |
| controller_module | 2 core | 4 GB | 10 GB | 1 |
| fdsn_api_module | 2 core | 4 GB | 10 GB | 1 |
| record_stream_module | 2 core | 4 GB | 10 GB | 1 |
| websocket_* | 1 core | 2 GB | 5 GB | 2 |
| public_api_module | 1 core | 2 GB | 5 GB | 1 |
| tews-ui-vue | 1 core | 512 MB | 2 GB | 1 |
| MongoDB | 2 core | 4 GB | 200 GB | 1 |
| Redis | 1 core | 2 GB | 10 GB | 1 |
| Kafka | 2 core | 4 GB | 100 GB | 1 |
| **TOTAL** | **~30 cores** | **~165 GB** | **~1.8 TB** | - |

---

## ✅ Prerequisites

### 1. Server Specifications

- **OS**: Ubuntu 22.04 LTS (atau kompatibel)
- **CPU**: Minimum 32 cores (64 vCPU recommended)
- **RAM**: Minimum 256 GB
- **Disk**: Minimum 2 TB (SSD recommended untuk /archive)
- **Network**: 1 Gbps uplink

### 2. Software Dependencies

| Software | Versi | Cara Install |
|----------|-------|--------------|
| Docker | 20.10+ | `apt install docker.io` |
| Docker Compose Plugin | 2.20+ | `apt install docker-compose-plugin` |
| Git | 2.34+ | `apt install git` |
| Python 3 | 3.10+ | `apt install python3 python3-pip` |
| curl / wget | latest | `apt install curl wget` |

### 3. Network & Firewall

**Port yang harus dibuka:**

| Port | Service | Source | Destination |
|------|---------|--------|-------------|
| 8000-8007 | API & Frontend | Public/Internal | Server |
| 32717 | MongoDB | Internal only | Server |
| 36379 | Redis | Internal only | Server |
| 39092 | Kafka | Internal only | Server |
| 32181 | Zookeeper | Internal only | Server |
| 22 | SSH | Admin IP only | Server |

**Firewall rules (ufw):**

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000:8007/tcp  # Services
sudo ufw enable
```

---

## 👤 Setup User & Permissions

### 1. Buat User Deployment (sebagai root/sudo user)

```bash
# Login sebagai user dengan sudo (misal: riset)
sudo su -

# Buat user bmkg
useradd -m -s /bin/bash bmkg

# Set password (gunakan password yang kuat)
passwd bmkg
# Masukkan password: [INPUT_PASSWORD]

# Buat direktori kerja
mkdir -p /home/bmkg/GEMPA
chown bmkg:bmkg /home/bmkg/GEMPA

# Buat direktori archive (untuk seismic data)
mkdir -p /mnt/archive
chown bmkg:bmkg /mnt/archive
chmod 755 /mnt/archive
```

### 2. Add User ke Docker Group

```bash
# Tambahkan bmkg ke docker group (agar bisa run docker tanpa sudo)
usermod -aG docker bmkg

# Verifikasi group membership
groups bmkg
# Output harus include: bmkg docker

# PENTING: User harus logout & login ulang agar group membership aktif
# Atau gunakan: newgrp docker
```

### 3. Setup SSH Key (Opsional, untuk Git)

```bash
# Switch ke user bmkg
su - bmkg

# Generate SSH key
ssh-keygen -t ed25519 -C "bmkg@riset-01"
# Tekan Enter untuk default location: /home/bmkg/.ssh/id_ed25519
# Masukkan passphrase (opsional)

# Copy public key untuk GitHub/GitLab
cat ~/.ssh/id_ed25519.pub
# Paste ke GitHub Settings → SSH Keys
```

### 4. Verifikasi Docker Access

```bash
# Sebagai user bmkg (tanpa sudo)
docker --version
# Expected: Docker version 20.10.8, build ...

docker compose version
# Expected: Docker Compose version v2.29.2

docker ps
# Harus berhasil tanpa permission error

# Test pull image
docker pull hello-world
docker run hello-world
# Harus berhasil
```

### 5. Setup Sudo Access (Opsional, untuk Troubleshooting)

```bash
# Sebagai root
# Tambahkan bmkg ke sudoers HANYA jika diperlukan untuk troubleshooting
# PERINGATAN: User bmkg production TIDAK perlu sudo access

# Jika benar-benar diperlukan:
usermod -aG sudo bmkg

# Atau buat limited sudo (lebih aman):
echo "bmkg ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose" | sudo tee /etc/sudoers.d/bmkg
chmod 440 /etc/sudoers.d/bmkg
```

---

## 📂 Struktur Direktori

```
/home/bmkg/GEMPA/ai-gempa-bmkg/
├── docker-compose.wrapper.yml       # DinD wrapper orchestration
├── Dockerfile.wrapper               # DinD wrapper image
├── entrypoint-wrapper.sh            # DinD startup script
├── sispro-tews/                     # Backend services
│   ├── docker-compose.yml
│   ├── .env                         # Backend config
│   ├── archiving_module/
│   ├── record_stream_module/
│   ├── controller_module/
│   ├── fdsn_module/
│   ├── api_incoming_module/
│   └── seedlink_module/
├── tews-ui-vue/                     # Frontend
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── .env                         # Frontend config
├── AI-TEWS/                         # AI detection modules
│   ├── AI_modules_alpha/
│   ├── AI_modules_beta/
│   └── AI_modules_neoalpha/
├── .envs/                           # Centralized env configs
│   ├── mongodb.env
│   ├── redis.env
│   ├── kafka.env
│   └── common.env
└── logs/                            # Application logs
    ├── sispro-tews/
    ├── frontend/
    └── ai-modules/
```

### Setup Direktori

```bash
# Sebagai user bmkg
cd /home/bmkg/GEMPA

# Clone repository
git clone https://github.com/your-org/ai-gempa-bmkg.git
cd ai-gempa-bmkg

# Buat direktori logs
mkdir -p logs/{sispro-tews,frontend,ai-modules}

# Set permissions
chmod -R 755 .
```

---

## ⚙️ Konfigurasi Environment

### 1. Backend Environment (sispro-tews/.env)

```bash
# Sebagai user bmkg
cd /home/bmkg/GEMPA/ai-gempa-bmkg/sispro-tews

# Copy dari template (jika ada)
cp .env.example .env

# Edit configuration
nano .env
```

**Isi file `.env`:**

```bash
# Kafka Configuration
kafka_host="kafka"
kafka_port="9092"

# Redis Configuration
redis_host="redis"
redis_port="6379"

# MongoDB Configuration
database_host="mongodb"
database_port="27017"
database_name="sispro-tews"

# Archive Storage
archive_location="/mnt/archive"

# Service Scaling
archive_replica_count="7"
seedlink_replica_count="5"

# MongoDB Admin Credentials (CHANGE THIS!)
MONGO_INITDB_ROOT_USERNAME="admin"
MONGO_INITDB_ROOT_PASSWORD="StrongPassword123!"

# API Keys & Secrets (CHANGE THIS!)
JWT_SECRET="your-jwt-secret-key-min-32-chars"
API_SECRET="your-api-secret-key"

# External Services (jika ada)
SEEDLINK_HOST="194.195.92.242"
SEEDLINK_PORT="9999"
```

### 2. Frontend Environment (tews-ui-vue/.env)

```bash
cd /home/bmkg/GEMPA/ai-gempa-bmkg/tews-ui-vue

# Edit frontend config
nano .env
```

**Isi file `.env`:**

```bash
# API Base URL (adjust sesuai domain/IP server)
VITE_API_BASE_URL="http://152.118.31.54:8003"

# WebSocket URLs
VITE_WS_GENERAL_URL="ws://152.118.31.54:8005"
VITE_WS_WAVEFORM_URL="ws://152.118.31.54:8004"

# Feature Flags
VITE_ENABLE_AI_DETECTION="true"
VITE_ENABLE_REALTIME_MONITORING="true"

# Map Configuration
VITE_MAP_CENTER_LAT="-2.5"
VITE_MAP_CENTER_LON="118.0"
VITE_MAP_ZOOM="5"
```

### 3. Infrastructure Environment (.envs/mongodb.env)

```bash
mkdir -p /home/bmkg/GEMPA/ai-gempa-bmkg/.envs
cd /home/bmkg/GEMPA/ai-gempa-bmkg/.envs

# MongoDB
cat > mongodb.env << 'EOF'
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=StrongPassword123!
MONGO_INITDB_DATABASE=sispro-tews
EOF

# Redis
cat > redis.env << 'EOF'
REDIS_PASSWORD=RedisSecurePass456!
REDIS_MAXMEMORY=4gb
REDIS_MAXMEMORY_POLICY=allkeys-lru
EOF

# Kafka
cat > kafka.env << 'EOF'
KAFKA_BROKER_ID=1
KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1
EOF
```

---

## 🌐 Network & Port Setup

### 1. Buat Docker Network

```bash
# Sebagai user bmkg
docker network create sispro-tews_req || true
```

### 2. Verifikasi Network

```bash
docker network ls | grep sispro-tews
# Expected: sispro-tews_req dengan driver bridge
```

### 3. Port Mapping Summary

| Internal Port | External Port | Service |
|---------------|---------------|---------|
| 38001 | 8001 | Record Stream API |
| 38002 | 8002 | FDSN API |
| 38003 | 8003 | Controller API (Main) |
| 38004 | 8004 | WebSocket Waveform |
| 38005 | 8005 | WebSocket General |
| 38006 | 8006 | Frontend UI |
| 38007 | 8007 | Public API |

---

## 🚀 Deployment Steps

### Step 1: Verifikasi Prerequisites

```bash
# Sebagai user bmkg
cd /home/bmkg/GEMPA/ai-gempa-bmkg

# Check docker
docker --version && docker compose version

# Check network
docker network inspect sispro-tews_req

# Check disk space
df -h /mnt/archive
# Harus tersedia minimal 1TB free

# Check ports availability
for port in 8000 8001 8002 8003 8004 8005 8006 8007; do
  nc -zv localhost $port 2>&1 | grep -q "Connection refused" && echo "Port $port: ✓ Available" || echo "Port $port: ✗ IN USE"
done
```

### Step 2: Build DinD Wrapper

```bash
# Build wrapper image
docker compose -f docker-compose.wrapper.yml build

# Verifikasi image
docker images | grep gempa-wrapper
```

### Step 3: Start DinD Wrapper

```bash
# Start wrapper container
docker compose -f docker-compose.wrapper.yml up -d

# Verify wrapper running
docker ps | grep gempa-dind-wrapper

# Check wrapper logs
docker logs -f gempa-dind-wrapper --tail 50
# Ctrl+C untuk stop tailing
```

### Step 4: Deploy Backend Services (Inside DinD)

```bash
# Enter DinD container
docker exec -it gempa-dind-wrapper bash

# Inside DinD container:
cd /app/sispro-tews

# Build & start services
docker compose up --build -d

# Verify services
docker ps

# Exit DinD container
exit
```

### Step 5: Deploy Frontend (Inside DinD)

```bash
# Enter DinD container
docker exec -it gempa-dind-wrapper bash

# Inside DinD container:
cd /app/tews-ui-vue

# Build & start frontend
docker compose up --build -d

# Exit DinD container
exit
```

### Step 6: Wait for Services Initialization

```bash
# Backend services need 2-5 minutes untuk full startup
# Monitor progress:
docker exec gempa-dind-wrapper docker logs sispro-tews_controller_module_1 -f --tail 100

# Tunggu sampai muncul:
# "Uvicorn running on http://0.0.0.0:8003"
# "Application startup complete"
```

---

## ✅ Verifikasi & Health Check

### 1. Check Running Containers

```bash
# List all containers inside DinD
docker exec gempa-dind-wrapper docker ps

# Expected output: 20+ containers running
# - 7x archiving_module
# - 5x seedlink_module
# - 1x controller_module
# - 1x fdsn_api_module
# - 1x record_stream_module
# - 1x websocket_general
# - 1x websocket_waveform
# - 1x public_api_module
# - 1x fdsn_module
# - 1x tews-ui-vue (frontend)
# - Infrastructure: mongodb, redis, kafka, zookeeper
```

### 2. Health Check Endpoints

```bash
# Frontend accessibility
curl -s -o /dev/null -w "%{http_code}" http://localhost:8006
# Expected: 200

# Controller API (main backend)
curl -s http://localhost:8003/api/health
# Expected: {"status":"healthy"}

# Login endpoint test
curl -X POST http://localhost:8003/api/v1/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq
# Expected: {"access_token":"...","token_type":"bearer"}

# WebSocket endpoints
wscat -c ws://localhost:8005
# Expected: Connection established

wscat -c ws://localhost:8004
# Expected: Connection established
```

### 3. Database Verification

```bash
# Check MongoDB connection
docker exec gempa-dind-wrapper docker exec sispro-tews_controller_module_1 python3 -c "
import pymongo
client = pymongo.MongoClient('mongodb://mongodb:27017/')
print('MongoDB databases:', client.list_database_names())
"
# Expected: ['admin', 'config', 'local', 'sispro-tews']

# Check Redis connection
docker exec gempa-dind-wrapper docker exec sispro-tews_controller_module_1 python3 -c "
import redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)
print('Redis PING:', r.ping())
"
# Expected: Redis PING: True
```

### 4. Log Verification

```bash
# Check for errors in controller logs
docker exec gempa-dind-wrapper docker logs sispro-tews_controller_module_1 --tail 100 | grep -iE "(error|exception|critical)"

# Jika tidak ada output → no critical errors ✓
```

---

## 👨‍💼 Admin User Setup

### 1. Verifikasi Default Admin User

```bash
# Check apakah admin user sudah ada
docker exec gempa-dind-wrapper docker exec sispro-tews_controller_module_1 python3 -c "
import pymongo
client = pymongo.MongoClient('mongodb://mongodb:27017/')
db = client['sispro-tews']
user = db.user.find_one({'username': 'admin'})
if user:
    print('✓ Admin user exists')
    print('Username:', user['username'])
    print('Role:', user.get('role', 'N/A'))
else:
    print('✗ Admin user not found')
"
```

### 2. Create Admin User (jika belum ada)

```bash
# Enter controller container
docker exec -it gempa-dind-wrapper docker exec -it sispro-tews_controller_module_1 bash

# Inside container, run Python:
python3 << 'EOF'
import pymongo
from passlib.context import CryptContext
from datetime import datetime

# Password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Connect to MongoDB
client = pymongo.MongoClient('mongodb://mongodb:27017/')
db = client['sispro-tews']

# Create admin user
admin_user = {
    "username": "admin",
    "email": "admin@bmkg.go.id",
    "hashed_password": pwd_context.hash("admin123"),  # GANTI PASSWORD INI!
    "full_name": "Administrator BMKG",
    "role": "admin",
    "is_active": True,
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}

# Insert atau update
result = db.user.update_one(
    {"username": "admin"},
    {"$set": admin_user},
    upsert=True
)

print(f"Admin user created/updated: {result.upserted_id or result.modified_count}")
EOF

# Exit container
exit
```

### 3. Create Additional Users

```bash
# Template untuk user baru
docker exec -it gempa-dind-wrapper docker exec -it sispro-tews_controller_module_1 python3 << 'EOF'
import pymongo
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
client = pymongo.MongoClient('mongodb://mongodb:27017/')
db = client['sispro-tews']

# User data
new_user = {
    "username": "operator1",
    "email": "operator1@bmkg.go.id",
    "hashed_password": pwd_context.hash("SecurePassword123!"),
    "full_name": "Operator Monitoring",
    "role": "operator",  # roles: admin, operator, viewer
    "is_active": True,
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}

result = db.user.update_one(
    {"username": new_user["username"]},
    {"$set": new_user},
    upsert=True
)

print(f"User {new_user['username']} created/updated")
EOF
```

### 4. Test Login dengan User Baru

```bash
# Test login
curl -X POST http://localhost:8003/api/v1/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"operator1","password":"SecurePassword123!"}' | jq

# Expected output:
# {
#   "access_token": "eyJ...",
#   "token_type": "bearer",
#   "user": {
#     "username": "operator1",
#     "role": "operator",
#     "full_name": "Operator Monitoring"
#   }
# }
```

---

## 🔧 Troubleshooting

### Problem 1: Port Already in Use

**Symptom:**
```
Error: bind: address already in use
```

**Solution:**
```bash
# Check port usage
netstat -tlnp | grep :8003

# Kill process using the port
sudo kill -9 <PID>

# Atau stop conflicting container
docker stop <container_name>

# Restart deployment
docker compose -f docker-compose.wrapper.yml restart
```

### Problem 2: Container Fails to Start

**Symptom:**
```
Container sispro-tews_controller_module_1 exited with code 1
```

**Solution:**
```bash
# Check logs
docker exec gempa-dind-wrapper docker logs sispro-tews_controller_module_1 --tail 100

# Common issues:
# - Missing environment variable → check .env file
# - MongoDB not ready → wait 1-2 minutes, restart container
# - Dependency missing → rebuild image

# Rebuild specific service
docker exec gempa-dind-wrapper bash -c "cd /app/sispro-tews && docker compose up -d --build controller_module"
```

### Problem 3: MongoDB Connection Failed

**Symptom:**
```
pymongo.errors.ServerSelectionTimeoutError: mongodb:27017: [Errno -2] Name or service not known
```

**Solution:**
```bash
# Check if MongoDB container running
docker exec gempa-dind-wrapper docker ps | grep mongodb

# Check network connectivity
docker exec gempa-dind-wrapper docker exec sispro-tews_controller_module_1 ping -c 3 mongodb

# Restart MongoDB
docker exec gempa-dind-wrapper docker compose -f /app/sispro-tews/docker-compose.yml restart mongodb

# Wait 30 seconds, then restart dependent services
sleep 30
docker exec gempa-dind-wrapper docker compose -f /app/sispro-tews/docker-compose.yml restart controller_module
```

### Problem 4: High Memory Usage

**Symptom:**
```
Out of memory error / System sluggish
```

**Solution:**
```bash
# Check memory usage
docker stats --no-stream

# Check disk usage
df -h
docker system df -v

# Clean unused resources
docker system prune -a --volumes -f

# Reduce replica counts in sispro-tews/.env:
# archive_replica_count="5"  # from 7
# seedlink_replica_count="3"  # from 5

# Restart with new config
docker exec gempa-dind-wrapper bash -c "cd /app/sispro-tews && docker compose up -d --scale archiving_module=5 --scale seedlink_module=3"
```

### Problem 5: Frontend 404 Errors

**Symptom:**
```
curl http://localhost:8006 → 404 Not Found
```

**Solution:**
```bash
# Check frontend container
docker exec gempa-dind-wrapper docker ps | grep tews-ui-vue

# Check nginx logs
docker exec gempa-dind-wrapper docker logs sispro-tews_fe-1 --tail 50

# Verify environment variables
docker exec gempa-dind-wrapper docker exec sispro-tews_fe-1 cat /etc/nginx/conf.d/default.conf

# Rebuild frontend
docker exec gempa-dind-wrapper bash -c "cd /app/tews-ui-vue && docker compose up -d --build"
```

---

## 🛡️ Maintenance & Backup

### 1. Regular Maintenance Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| Log rotation | Daily (cron) | `find ./logs -name "*.log" -mtime +7 -delete` |
| Docker cleanup | Weekly | `docker system prune -f` |
| Database backup | Daily | `mongodump --out /backup/$(date +%F)` |
| Health check | Hourly (cron) | `curl -f http://localhost:8003/api/health` |
| Update check | Monthly | `git pull && docker compose build` |

### 2. Database Backup

```bash
# Backup MongoDB
docker exec gempa-dind-wrapper docker exec mongodb mongodump \
  --out /backup/mongodb-$(date +%F-%H%M) \
  --gzip

# Copy backup to host
docker cp gempa-dind-wrapper:/backup/mongodb-$(date +%F-%H%M) \
  /home/bmkg/backups/mongodb/

# Backup Redis snapshot
docker exec gempa-dind-wrapper docker exec redis redis-cli SAVE
docker exec gempa-dind-wrapper docker cp redis:/data/dump.rdb \
  /backup/redis-$(date +%F).rdb

# Archive old backups (keep 30 days)
find /home/bmkg/backups -name "mongodb-*" -mtime +30 -exec rm -rf {} \;
```

### 3. Log Management

```bash
# Setup log rotation (sebagai bmkg user)
cat > /home/bmkg/logrotate-gempa.conf << 'EOF'
/home/bmkg/GEMPA/ai-gempa-bmkg/logs/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 bmkg bmkg
}
EOF

# Add to crontab
crontab -e
# Add line:
# 0 2 * * * /usr/sbin/logrotate /home/bmkg/logrotate-gempa.conf
```

### 4. Service Restart

```bash
# Restart individual service
docker exec gempa-dind-wrapper docker compose -f /app/sispro-tews/docker-compose.yml restart controller_module

# Restart all backend services
docker exec gempa-dind-wrapper docker compose -f /app/sispro-tews/docker-compose.yml restart

# Restart entire stack (downtime ~5 minutes)
docker compose -f docker-compose.wrapper.yml restart

# Full rebuild (downtime ~15 minutes)
docker compose -f docker-compose.wrapper.yml down
docker compose -f docker-compose.wrapper.yml up --build -d
```

### 5. Monitoring Script

```bash
# Create health check script
cat > /home/bmkg/GEMPA/ai-gempa-bmkg/health-check.sh << 'EOF'
#!/bin/bash
set -e

echo "=== GEMPA AI-TEWS Health Check ==="
echo "Timestamp: $(date)"
echo ""

# Check DinD wrapper
echo -n "DinD Wrapper: "
docker ps | grep -q gempa-dind-wrapper && echo "✓ Running" || echo "✗ Stopped"

# Check services inside DinD
echo -n "Backend Services: "
BACKEND_COUNT=$(docker exec gempa-dind-wrapper docker ps | grep sispro-tews | wc -l)
echo "$BACKEND_COUNT containers"

# Check endpoints
echo "API Health:"
for port in 8001 8002 8003 8004 8005 8006 8007; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port 2>/dev/null || echo "000")
  echo "  Port $port: $STATUS"
done

# Check disk usage
echo ""
echo "Disk Usage:"
df -h /mnt/archive | tail -1 | awk '{print "  Archive: " $3 "/" $2 " (" $5 " used)"}'

# Check memory
echo ""
echo "Memory Usage:"
free -h | grep Mem | awk '{print "  RAM: " $3 "/" $2 " (" int($3/$2*100) "% used)"}'
EOF

chmod +x /home/bmkg/GEMPA/ai-gempa-bmkg/health-check.sh

# Run health check
./health-check.sh
```

### 6. Disaster Recovery

```bash
# Export container configurations
docker exec gempa-dind-wrapper docker compose -f /app/sispro-tews/docker-compose.yml config > /home/bmkg/backups/sispro-tews-config.yml

# Backup .env files
tar czf /home/bmkg/backups/env-backup-$(date +%F).tar.gz \
  sispro-tews/.env \
  tews-ui-vue/.env \
  .envs/

# Full disaster recovery dari backup:
# 1. Restore code: git clone repository
# 2. Restore .env files: tar xzf env-backup-*.tar.gz
# 3. Restore database: mongorestore --drop /backup/mongodb-YYYY-MM-DD/
# 4. Deploy: docker compose -f docker-compose.wrapper.yml up -d
```

---

## 📞 Support & Contacts

### Tim Development

| Role | Contact | Responsibility |
|------|---------|----------------|
| System Admin | admin@bmkg.go.id | Infrastructure, deployment |
| Backend Lead | backend@bmkg.go.id | API, database, modules |
| Frontend Lead | frontend@bmkg.go.id | UI, dashboard |
| AI Engineer | ai@bmkg.go.id | ML models, detection |

### Escalation Path

1. **Level 1 (Operator)**: Basic troubleshooting, restart services
2. **Level 2 (System Admin)**: Server issues, network, deployment
3. **Level 3 (Development Team)**: Code bugs, feature issues
4. **Level 4 (Vendor Support)**: Infrastructure vendor issues

---

## 📝 Changelog & Updates

| Date | Version | Changes |
|------|---------|---------|
| 2026-09-26 | 1.0.0 | Initial deployment guide |

---

**End of Deployment Guide**

Untuk pertanyaan atau dukungan, hubungi tim DevOps BMKG.
