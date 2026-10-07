# Analisis Mendalam Codebase GEMPA AI-TEWS

**Waktu Analisis:** 26 September 2026  
**Direktori Kerja:** `D:\Projects\GEMPA\ai-gempa-bmkg`  
**Status:** 440 file termodifikasi, branch main

---

## 1. PETA ARSITEKTUR & STRUKTUR CODEBASE

### 1.1 Ringkasan Komponen Utama

Sistem GEMPA AI-TEWS terdiri dari 4 komponen utama:

```
┌─────────────────────────────────────────────────────────────────┐
│                    tews-ui-vue (Frontend)                       │
│  Vue 3 + Vite | Socket.IO | D3 + Leaflet | Port 38006:8004     │
└────────────────────────────┬────────────────────────────────────┘
                             │ (WebSocket + REST)
┌────────────────────────────┴────────────────────────────────────┐
│                    sispro-tews (Backend APIs)                    │
│  FastAPI + Uvicorn | Port: 38001-38007 | 7 modul utama        │
└────────────────────────────┬────────────────────────────────────┘
                             │ (Kafka + Redis)
┌────────────────────────────┴────────────────────────────────────┐
│                    AI-TEWS (ML Inference)                        │
│  TensorFlow 2.10 | Kafka Consumer | AI_modules_simple_ai       │
└────────────────────────────┬────────────────────────────────────┘
                             │ (MongoDB + Redis)
┌────────────────────────────┴────────────────────────────────────┐
│              Data Layer (MongoDB + Redis + Archive)              │
│  Seismic data, event metadata, waveforms, cache                │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Rincian Setiap Komponen

#### **A. tews-ui-vue (Frontend Web Application)**

**Lokasi:** `./tews-ui-vue/`  
**Teknologi:** Vue 3, TypeScript, Vite, TailwindCSS + DaisyUI  
**Port:** 38006 (eksternal) → 8004 (internal, nginx)

**Fungsi:**
- Visualisasi real-time gempa dan data seismik
- Dashboard monitoring station, event, phase detection
- Integrasi peta (Leaflet, D3 untuk grafik)
- Koneksi WebSocket ke controller_module untuk live data
- REST API calls ke backend services

**Dependencies Utama:**
```json
- Vue 3.4.31, Vue Router 4.4.0
- Pinia 2.1.7 (state management)
- Socket.IO-Client 4.7.5 (real-time)
- Axios 1.7.2 (HTTP client)
- D3 7.9.0 (data visualization)
- Leaflet 1.9.4 (mapping)
- TanStack Vue Query 5.51.1 (data fetching)
- date-fns 3.6.0, lodash 4.17.21
```

**Build Process:**
```bash
npm run build  # Output: dist/ folder
# nginx serves /app/dist ke /usr/share/nginx/html
```

**Nginx Config** (`tews-ui-vue/nginx.conf`):
- Listens on port 8004
- SPA fallback: semua route → index.html
- Gzip compression enabled
- Worker processes: 4

#### **B. sispro-tews (Backend - Seismic Data Processing)**

**Lokasi:** `./sispro-tews/`  
**Teknologi:** Python 3, FastAPI, Uvicorn, ObsPy, MongoDB driver  
**Network:** External Docker network `sispro-tews_req`  
**Port Mapping:**

| Modul | Port Internal | Port Eksternal | Fungsi |
|-------|---------------|-----------------|--------|
| api_incoming_module | 8007 | 38007 | Public API untuk incoming events |
| record_stream_module | 8001 | 38001 | Streaming seismic records |
| fdsn_api_module | 8002 | 38002 | FDSN-WS API endpoint |
| controller_module | 8003 | 38003 | Main controller API + orchestration |
| websocket_waveform | 8004 | 38004 | WebSocket waveform data stream |
| websocket_general | 8005 | 38005 | WebSocket general updates |
| archiving_module | - | - | Background archiving service (no public port) |
| fdsn_module | - | - | FDSN scheduler (background) |
| seedlink_module | - | - | SeedLink protocol consumer (background) |

**Modul Detail:**

**1. api_incoming_module**
- Entry point untuk data eksternal (HTTP POST)
- FastAPI app di `api_incoming_module.py`
- Wrapper: `app_incoming_module.py` → uvicorn server (32 workers, port 8007)
- Menerima: earthquake data, station info, picks, associations

**2. record_stream_module**
- Streaming real-time seismic waveforms
- Port 8001, volume mount ke archive location
- Consumer data dari seedlink atau external sources

**3. controller_module**
- Orchesterasi seluruh sistem
- Main controller API (FastAPI, port 8003)
- WebSocket untuk client connections
- 3 variants:
  - `controller_web_socket_redis.py` - Main WebSocket handler (backup & replicas)
  - `controller_web_socket.py` - Alt implementation
  - `controller_api_app.py` - API endpoint wrapper

**3a. websocket_general** (Dockerfile_general)
- Port 8005
- Broadcast general updates (station status, etc.)

**3b. websocket_waveform** (Dockerfile_waveform)
- Port 8004
- Dedicated waveform streaming (high-frequency data)
- Nginx proxy (`sispro-tews/nginx/nginx.conf`) routes WebSocket ↔ waveform service

**4. fdsn_module + fdsn_api_module**
- FDSN-WS (Federated Digital Seismic Network) compliant
- `fdsn_api.py` - FDSN REST API
- `fdsn_scheduler.py` - Background scheduler untuk query remote stations
- Volume mount: archive location (read seismic data)
- Port 8002 public, scheduler runs internal

**5. archiving_module**
- Background daemon, no public port
- Replicates: 7 instances (load-balanced archiving)
- Memory limit: 20 GB per instance
- Fungsi: persist seismic data to MongoDB/disk, cleanup old data
- Volume: `${archive_location}` (seismic archive directory)
- Docker socket mount: orchestrate sibling containers if needed

**6. seedlink_module**
- SeedLink protocol consumer
- Replicates: 5 instances
- Memory limit: 5 GB per instance
- Connects to remote SeedLink servers, streams waveform data
- Docker socket mount: dynamic container orchestration

#### **C. AI-TEWS (Artificial Intelligence Modules)**

**Lokasi:** `./AI-TEWS/`  
**Teknologi:** Python 3, TensorFlow 2.10, Kafka, Redis, MongoDB  
**Versi Aktif:** `AI_modules_simple_ai` (per README.md)

**Struktur Directory:**
```
AI-TEWS/
├── AI_modules_alpha/          (experimental, v1)
├── AI_modules_beta/           (experimental, v2)
├── AI_modules_neoalpha/       (experimental, v3)
├── AI_modules_simple_ai/      (RECOMMENDED - production ready)
├── AI_modules_template/       (development template)
├── requirements/              (shared dependencies: Kafka, Redis, MongoDB setup)
├── archive/                   (waveform data cache)
└── dump.rdb                   (Redis persistence snapshot)
```

**AI_modules_simple_ai Components:**

**1. p-pick_module** (P-wave Phase Picker)
- **Teknologi:** TensorFlow 2.10 (neural network model)
- **Memory:** 5 GB per instance, 5 replicas
- **Service** (`p-pick_module/service/`):
  - Flask/Gunicorn server (port 8000 internal)
  - Model inference engine
  - Requirements: tensorflow==2.10, keras, numpy, scipy
  
- **Nginx Load Balancer** (`p-pick_module/nginx/`):
  - Distributes requests to 5 service replicas
  - Nginx config: load balancing upstream
  
- **Consumer** (`p-pick_module/consumer/`):
  - Kafka consumer: listens to "event" topic
  - Posts waveform data to p-pick service via HTTP
  - Publishes results back to Kafka

- **Ports:**
  - Service: 8000 (internal, no external exposure - behind nginx)
  - Nginx: configurable via `${nginx_port}` in .env (default: 80)

**2. association_module**
- Event-phase association algorithm
- PyOcto/custom algorithm
- Consumes picks from Kafka, publishes associated events

**3. phase-arrival_module**
- Phase arrival time prediction
- Velocity models, travel time calculations

**4. locmag_module**
- Location and magnitude estimation
- Hypocenter determination using triangulation
- Magnitude calculation from amplitude

**Requirements File** (`AI-TEWS/AI_modules_simple_ai/p-pick_module/service/requirements.txt`):
```
kafka_python==2.0.2
obspy==1.4.0
pymongo==4.6.2
python-dotenv==1.0.1
redis==3.5.3
tensorflow==2.10
pandas==1.4.4
tqdm==4.66.4
flask
gunicorn
```

**Docker Compose** (`AI-TEWS/AI_modules_simple_ai/docker-compose.yml`):
- Services: p-pick_service, p-pick_nginx, p-pick_consumer, association_module, phase-arrival_module, locmag_module
- Environment: CUDA_VISIBLE_DEVICES=-1 (CPU-only; set to 0 for GPU if available)
- Dependencies: .env file for Kafka, Redis hosts

#### **D. Infrastructure & Data Layer**

**1. MongoDB**
- Container: Managed via sispro-tews network
- Port: 27017 (internal), 27018 (external, per memory)
- Data: `./data/` folder (WiredTiger database files)
- Collections:
  - `stations` - Network/station metadata
  - `events` - Earthquake events (origin, magnitude, etc.)
  - `picks` - Phase picks (P, S arrivals)
  - `associations` - Event-phase associations
  - `waveforms` - Seismic waveform snippets
  - `metadata` - Catalog metadata

**2. Redis**
- Role: Cache layer, session store, Kafka offset tracking
- Port: 6379 (internal)
- Persistence: `AI-TEWS/dump.rdb` (RDB snapshot)
- Data structure: Strings (cache), Hashes (state), Lists (queues)

**3. Kafka**
- Message broker for inter-service communication
- Topics: `event`, `pick`, `association`, `waveform`
- Ports: configurable (internal)
- Used by: AI modules (consumers), archiving (producers), controller (bidirectional)

**4. Archive Storage**
- Volume mount: `${archive_location}` (local filesystem)
- Stores: Raw seismic waveforms (miniSEED format)
- Size: ~1-2 TB typical (depends on station count & retention)

**5. Data Files**
- `./data.zip` - MongoDB backup (compressed, ~1.8 MB)
- `./data/` - Expanded MongoDB data (WiredTiger storage engine)
- `AI-TEWS/dump.rdb` - Redis persistence (RDB format, ~1 KB)

---

### 1.3 Data Flow (Alur Data Sistem)

```
1. INCOMING DATA STREAM
   ├─ External SeedLink Servers
   │  └─→ seedlink_module (5x) ─→ Kafka topic: "waveform"
   ├─ HTTP POST (api_incoming_module:38007)
   │  └─→ FastAPI ─→ Validate ─→ MongoDB + Kafka: "event"
   └─ FDSN-WS Query (client calls fdsn_api_module:38002)
      └─→ Query MongoDB, return FDSN-format response

2. AI INFERENCE PIPELINE
   ├─ P-pick Service (5x replicas)
   │  ├─ Consumer reads Kafka: "waveform"
   │  ├─ POST to p-pick_nginx (load-balanced)
   │  ├─ Model inference (TensorFlow GPU/CPU)
   │  └─ Publish Kafka: "pick"
   ├─ Association Module
   │  ├─ Consumes: "pick"
   │  └─ Publishes: "association"
   ├─ Phase-Arrival Module
   │  └─ Refines picks with travel time
   └─ LocMag Module
      └─ Calculates hypocenter, magnitude

3. ARCHIVING & PERSISTENCE
   ├─ Archiving Module (7x) reads Kafka: "waveform"
   │  ├─ Write to MongoDB (events, picks, associations)
   │  ├─ Write to filesystem archive (miniSEED)
   │  └─ Update Redis cache
   └─ FDSN Module periodically syncs remote stations

4. REAL-TIME FRONTEND UPDATES
   ├─ Controller Module (orchestrator)
   │  ├─ Polls MongoDB for new events
   │  ├─ Aggregates system status
   │  └─ WebSocket broadcast (socket.io)
   ├─ websocket_general:38005 ─→ Browser (general updates)
   ├─ websocket_waveform:38004 ─→ Browser (waveform plot data)
   └─ Frontend: Vue app consumes via socket.io-client

5. CLIENT QUERIES
   ├─ HTTP GET /api/events?bbox=... (controller_module:38003)
   ├─ HTTP GET /fdsnws/event/1/query? (fdsn_api_module:38002)
   ├─ HTTP POST /api/event (api_incoming_module:38007)
   └─ WebSocket: /socket.io/ (controller + websocket modules)
```

### 1.4 Komunikasi Inter-Service

| Source | Destination | Protocol | Data | Port |
|--------|-------------|----------|------|------|
| seedlink_module | Kafka | Kafka | Waveform | 9092 |
| p-pick_service | Kafka | Kafka | Picks | 9092 |
| archiving_module | MongoDB | TCP | Event metadata | 27017 |
| controller_module | Redis | TCP | Cache/state | 6379 |
| websocket_* | Frontend | WebSocket | Live data | 8004, 8005 |
| Browser | controller_module | HTTP REST | Queries | 38003 |
| Browser | fdsn_api_module | HTTP FDSN | FDSN queries | 38002 |
| External | api_incoming_module | HTTP REST | New events | 38007 |

### 1.5 Network & Volumes

**Docker Network:** `sispro-tews_req` (external, pre-created)
- All sispro-tews services + AI services connected
- Cross-service hostname resolution: `service_name:port`

**Volumes:**
- `${archive_location}` - Seismic archive (host path, mounted R/W)
- `/var/run/docker.sock` - Docker socket (archiving_module, seedlink_module)
  - Purpose: Orchestrate sibling containers (scaling, cleanup)

**Environment Variables (.env):**
- `archive_location` - Host path for archive storage
- `archive_replica_count` - Archiving module replicas (default 7)
- `seedlink_replica_count` - SeedLink module replicas (default 5)
- `kafka_host`, `kafka_port` - Kafka broker
- `redis_host`, `redis_port` - Redis connection
- `database_host`, `database_port` - MongoDB connection
- `nginx_port` - Nginx port (AI modules)

---

## 2. PANDUAN MENJALANKAN KODE LOKAL (LOCAL DEVELOPMENT)

### 2.1 Prasyarat (Prerequisites)

**Software yang wajib diinstal:**

```bash
# Windows Git Bash / MSYS2
git --version             # >= 2.40
docker --version          # >= 20.10 (Docker Desktop on Windows)
docker-compose --version  # >= v2.20 (via Docker Desktop)

# Python & Node.js
python --version          # >= 3.9 (for sispro-tews)
node --version            # >= 18.0 (for tews-ui-vue)
npm --version             # >= 9.0

# Optional GPU support
nvidia-smi                # If using GPU for TensorFlow
```

**Docker requirements:**
- Enable WSL 2 backend (Windows)
- Allocate ≥ 8 GB RAM to Docker Desktop
- Enable Docker socket access (for archiving_module, seedlink_module)

### 2.2 Setup Environment Variables

**Step 1: Create .env file for sispro-tews**

```bash
cd sispro-tews
cat > .env << 'EOF'
# Database
DATABASE_HOST=mongodb
DATABASE_PORT=27017
database_port=27017

# Cache
REDIS_HOST=redis
REDIS_PORT=6379
redis_host=redis
redis_port=6379

# Message Queue
KAFKA_HOST=kafka
KAFKA_PORT=9092
kafka_host=kafka
kafka_port=9092

# Archive storage (local)
archive_location=/archive
archive_replica_count=2    # Reduced for local dev (default 7)

# SeedLink
seedlink_replica_count=1   # Reduced for local dev (default 5)
EOF
```

**Step 2: Create .env file for AI-TEWS**

```bash
cd ../AI-TEWS/AI_modules_simple_ai
cat > .env << 'EOF'
# Kafka
kafka_host=kafka
kafka_port=9092

# Redis
redis_host=redis
redis_port=6379

# MongoDB
MONGODB_HOST=mongodb
MONGODB_PORT=27017

# Nginx (p-pick load balancer)
nginx_port=80

# TensorFlow (CPU-only for local dev)
CUDA_VISIBLE_DEVICES=-1
TF_CPP_MIN_LOG_LEVEL=2
EOF
```

**Step 3: Create .env file for tews-ui-vue** (optional, for frontend dev)

```bash
cd ../../tews-ui-vue
cat > .env.local << 'EOF'
VITE_API_BASE_URL=http://localhost:38003
VITE_SOCKET_IO_URL=http://localhost:38005
VITE_FDSN_API_URL=http://localhost:38002
EOF
```

### 2.3 Option A: Local Development (Fastest - No Docker)

**Recommended for frontend-only or debugging specific module.**

#### **A1. Backend Setup (sispro-tews + AI-TEWS)**

```bash
# 1. Install Python dependencies for sispro-tews
cd sispro-tews
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt   # If exists, or:
pip install fastapi uvicorn pymongo redis kafka-python obspy python-dotenv gunicorn

# 2. Start required services (Kafka, Redis, MongoDB) in Docker
# Option: Use standalone containers
docker run -d --name mongodb -p 27017:27017 mongo:7.0
docker run -d --name redis -p 6379:6379 redis:7-alpine
docker run -d --name kafka -p 9092:9092 \
  -e KAFKA_BROKER_ID=1 \
  -e KAFKA_ZOOKEEPER_CONNECT=localhost:2181 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092 \
  confluentinc/cp-kafka:7.5.0

# 3. Run controller_module (main backend API)
cd controller_module
python controller_api_app.py      # Starts on http://localhost:8003

# 4. In another terminal, run API incoming module
cd ../api_incoming_module
python app_incoming_module.py     # Starts on http://localhost:8007

# 5. (Optional) Run AI modules
cd ../../AI-TEWS/AI_modules_simple_ai/p-pick_module/service
python -m flask run --port 8000  # Or gunicorn
```

**Verification:**
```bash
curl http://localhost:8003/health  # Should return 200
curl http://localhost:8007/health  # Should return 200
```

#### **A2. Frontend Setup (tews-ui-vue)**

```bash
cd tews-ui-vue
npm install
npm run dev                  # Starts on http://localhost:5173

# Or build for production
npm run build
npm run preview
```

**Access:** http://localhost:5173

---

### 2.4 Option B: Full Docker Deployment (Recommended - Mirrors Production)

**Preserves all inter-service networking, volumes, replicas.**

#### **B1. Create shared Docker network**

```bash
docker network create sispro-tews_req
```

#### **B2. Prepare archive directory** (for volume mount)

```bash
mkdir -p /path/to/archive
chmod 777 /path/to/archive
```

#### **B3. Start infrastructure services** (Kafka, Redis, MongoDB)

```bash
cd AI-TEWS/requirements
docker-compose up -d
# Services: kafka, zookeeper, redis, mongodb
# Wait 10 sec for services to be ready

# Verify
docker-compose ps
docker logs kafka  # Check broker is ready
```

#### **B4. Start sispro-tews services**

```bash
cd ../../sispro-tews
# Edit .env: set archive_location, replica counts

docker-compose up -d
# Services: archiving_module, record_stream_module, controller_module, 
#           websocket_general, websocket_waveform, fdsn_module, fdsn_api_module, 
#           public_api_module, seedlink_module

# Verify
docker-compose ps
docker-compose logs controller_module -f
```

**Ports available (localhost):**
- 38001: record_stream_module
- 38002: fdsn_api_module
- 38003: controller_module
- 38004: websocket_waveform
- 38005: websocket_general
- 38006: frontend (when running)
- 38007: api_incoming_module

#### **B5. Start AI modules**

```bash
cd ../AI-TEWS/AI_modules_simple_ai
# Edit .env: set Kafka/Redis/MongoDB hosts to docker service names

docker-compose up -d
# Services: p-pick_service, p-pick_nginx, p-pick_consumer, 
#           association_module, phase-arrival_module, locmag_module

# Verify
docker-compose ps
docker-compose logs p-pick_service -f
```

#### **B6. Start frontend** (optional)

```bash
cd ../../tews-ui-vue
docker-compose up -d
# Service: app (nginx)
# Port: 38006

# Or run locally with npm
npm install && npm run dev
```

#### **B7. Test the full stack**

```bash
# 1. Check controller API
curl http://localhost:38003/events

# 2. Post test event
curl -X POST http://localhost:38007/event \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": -7.5,
    "longitude": 110.5,
    "depth": 50.0,
    "magnitude": 5.5,
    "origin_time": "2026-09-26T01:15:00Z"
  }'

# 3. Access frontend
# Browser: http://localhost:38006 (Docker) or http://localhost:5173 (npm dev)

# 4. WebSocket test
wscat -c ws://localhost:38005/socket.io/?EIO=4&transport=websocket
```

### 2.5 Stopping Local Environment

```bash
# Stop all containers
cd sispro-tews && docker-compose down
cd ../AI-TEWS/AI_modules_simple_ai && docker-compose down
cd ../requirements && docker-compose down

# Or stop and remove volumes (clean slate)
docker-compose down -v

# Remove network
docker network rm sispro-tews_req
```

### 2.6 Common Issues & Troubleshooting

| Masalah | Penyebab | Solusi |
|--------|---------|--------|
| Connection refused localhost:38003 | Service not started | Check `docker-compose logs controller_module` |
| "sispro-tews_req network not found" | Network doesn't exist | Run `docker network create sispro-tews_req` |
| Kafka broker not ready | Slow startup | Wait 15 sec after `docker-compose up` |
| p-pick service crashes (CUDA) | GPU not available | Set `CUDA_VISIBLE_DEVICES=-1` in .env (CPU mode) |
| MongoDB port already in use | Another instance running | Change port in .env or `docker stop <container>` |
| Archive volume permission denied | Permission issue on host | Run `chmod 777 /path/to/archive` |
| WebSocket connection timeout | Firewall/CORS issue | Check nginx config, CORS headers in controller |

---

## 3. PANDUAN DEPLOYMENT DI SERVER UBUNTU (riset-01)

### 3.1 Target Spesifikasi Server

```
Hostname/User: bmkg@riset-01
IP Address: 152.118.31.54
CPU: 16 cores @ 3.0 GHz
RAM: 64 GB
Storage: 2 TB
GPU: 8 GB VRAM (NVIDIA)
OS: Ubuntu 22.04 LTS
Docker: 20.10.8 (installed)
Docker Compose: v2.29.2 (plugin + standalone)
```

### 3.2 Fase 1: Persiapan Server Ubuntu

#### **3.2.1 SSH Access & Basic Setup**

```bash
# 1. SSH ke server
ssh bmkg@152.118.31.54

# 2. Update sistem
sudo apt update && sudo apt upgrade -y

# 3. Verify Docker
docker --version
docker-compose --version

# 4. Verify GPU (jika tersedia)
nvidia-smi
# Output: Should show GPU memory (8 GB)
```

#### **3.2.2 Install NVIDIA Container Toolkit (GPU Support)**

```bash
# 1. Install NVIDIA Docker runtime
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-docker2

# 2. Restart Docker daemon
sudo systemctl restart docker

# 3. Test GPU in Docker
docker run --rm --gpus all nvidia/cuda:11.8.0-runtime-ubuntu22.04 nvidia-smi
# Should output GPU info
```

#### **3.2.3 Setup Directory Structure & Permissions**

```bash
# 1. Create working directory
sudo mkdir -p /opt/gempa-ai-tews
sudo chown -R bmkg:bmkg /opt/gempa-ai-tews
cd /opt/gempa-ai-tews

# 2. Create archive storage (large volume for seismic data)
sudo mkdir -p /mnt/archive
sudo chown -R bmkg:bmkg /mnt/archive
sudo chmod 777 /mnt/archive
# Size recommendation: 1-2 TB (adjust capacity_planning based on data retention)

# 3. Create persistent volumes for databases
mkdir -p data/{mongodb,redis}
mkdir -p logs/{sispro-tews,ai-tews}
```

#### **3.2.4 Create Docker Network**

```bash
docker network create sispro-tews_req
```

### 3.3 Fase 2: Clone & Setup Codebase

```bash
# 1. Clone repository
cd /opt/gempa-ai-tews
git clone https://github.com/your-repo/ai-gempa-bmkg.git .
git checkout main

# 2. Extract data (MongoDB backup)
unzip -o data.zip -d ./

# 3. Update .env files for production
cat > sispro-tews/.env << 'EOF'
# Database (using docker internal network)
DATABASE_HOST=mongodb
DATABASE_PORT=27017
database_port=27017

# Cache
REDIS_HOST=redis
REDIS_PORT=6379
redis_host=redis
redis_port=6379

# Message Queue
KAFKA_HOST=kafka
KAFKA_PORT=9092
kafka_host=kafka
kafka_port=9092

# Archive storage (LARGE partition)
archive_location=/mnt/archive
archive_replica_count=7        # Match 7 archiving instances

# SeedLink
seedlink_replica_count=5       # Match 5 seedlink instances

# Server IP (for external access)
SERVER_IP=152.118.31.54
CORS_ORIGIN=http://152.118.31.54:8006,http://localhost:8006
EOF

cat > AI-TEWS/AI_modules_simple_ai/.env << 'EOF'
# Kafka
kafka_host=kafka
kafka_port=9092

# Redis
redis_host=redis
redis_port=6379

# MongoDB
MONGODB_HOST=mongodb
MONGODB_PORT=27017

# Nginx (p-pick load balancer)
nginx_port=80

# TensorFlow with GPU
CUDA_VISIBLE_DEVICES=0        # GPU device ID (0-3 for multi-GPU)
TF_CPP_MIN_LOG_LEVEL=1
TF_FORCE_GPU_ALLOW_GROWTH=true # Allow dynamic GPU memory growth
EOF
```

### 3.4 Fase 3: Docker Compose Configuration untuk Production

#### **3.4.1 Infrastructure Services** (`AI-TEWS/requirements/docker-compose.yml`)

Verifikasi compose file includes:
```yaml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    ports: ["2181:2181"]
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    networks: [sispro-tews_network]

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on: [zookeeper]
    ports: ["9092:9092"]
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    networks: [sispro-tews_network]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: ["redis_data:/data"]
    command: redis-server --appendonly yes
    networks: [sispro-tews_network]

  mongodb:
    image: mongo:7.0
    ports: ["27017:27017"]
    volumes: ["mongodb_data:/data/db"]
    environment:
      MONGO_INITDB_DATABASE: gempa
    networks: [sispro-tews_network]

volumes:
  redis_data:
  mongodb_data:

networks:
  sispro-tews_network:
    name: sispro-tews_req
    external: true
```

#### **3.4.2 Start Infrastructure Services**

```bash
cd AI-TEWS/requirements
docker-compose up -d

# Wait for services to stabilize (~15 seconds)
sleep 15

# Verify all services running
docker-compose ps
docker-compose logs | grep -E "(ready|started|listening)"
```

### 3.5 Fase 4: Deploy sispro-tews Services

#### **3.5.1 Build & Deploy**

```bash
cd sispro-tews

# Build images
docker-compose build

# Start services (detached)
docker-compose up -d

# Monitor startup
docker-compose logs -f --tail=50

# Verify all services healthy
docker-compose ps
# Should show 8 services: all "Up"

# Wait for API to be ready (~30 seconds)
sleep 30
curl -s http://localhost:38003/health || echo "Not yet ready"
```

#### **3.5.2 Configure Resource Limits** (sispro-tews/docker-compose.yml)

Optimize for 16 cores / 64 GB RAM:

```yaml
services:
  archiving_module:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 20G
      replicas: 7  # 7 * 2 CPU = 14 CPUs utilized

  seedlink_module:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 5G
      replicas: 5  # 5 * 1 CPU = 5 CPUs utilized

  controller_module:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 4G

  fdsn_module, fdsn_api_module, record_stream_module:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 2G
```

**Summary resource allocation:**
- Archiving: 14 CPUs, 140 GB RAM (7x20GB)
- SeedLink: 5 CPUs, 25 GB RAM (5x5GB)
- Others: 2 CPUs, 12 GB RAM
- **Total: 21 CPUs, 177 GB RAM** (headroom for system, Kafka, Redis, MongoDB)

Adjust replicas if needed based on load:
```bash
# Scale archiving down if needed
docker-compose up -d --scale archiving_module=3
```

### 3.6 Fase 5: Deploy AI-TEWS Services (GPU-Enabled)

#### **3.6.1 Build AI Images**

```bash
cd AI-TEWS/AI_modules_simple_ai

# Build with GPU support
DOCKER_BUILDKIT=1 docker-compose build --no-cache

# For p-pick service (TensorFlow + GPU):
# Dockerfile should use NVIDIA CUDA base image:
#   FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04 AS base
#   RUN pip install tensorflow==2.10
```

#### **3.6.2 Deploy AI Services**

```bash
docker-compose up -d

# Verify GPU is detected by TensorFlow
docker-compose logs p-pick_service | grep -i "gpu\|cuda\|device"
# Expected: "Num GPUs available: 1" or similar

# Monitor p-pick service startup (model loading can take 30-60 sec)
docker-compose logs -f p-pick_service
```

#### **3.6.3 GPU Resource Configuration**

Update `docker-compose.yml`:

```yaml
services:
  p-pick_service:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1              # Use 1 GPU (out of available 1)
              capabilities: [gpu]
        limits:
          memory: 10G
          cpus: '4.0'

  association_module:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'

  locmag_module, phase-arrival_module:
    deploy:
      resources:
        limits:
          memory: 3G
          cpus: '1.0'
```

**GPU Memory Optimization:**
```bash
# In .env:
TF_FORCE_GPU_ALLOW_GROWTH=true   # Prevent full GPU allocation upfront
TF_GPU_MEMORY_FRACTION=0.8        # Allocate 80% of 8GB = 6.4 GB
```

### 3.7 Fase 6: Frontend Deployment (tews-ui-vue)

#### **3.7.1 Build & Deploy**

```bash
cd tews-ui-vue

# Build production SPA
npm install
npm run build                    # Output: dist/ folder

# Deploy via Docker
docker-compose up -d
# Service: app (nginx on port 38006)

# Or deploy to reverse proxy (Nginx on host)
```

#### **3.7.2 Nginx Reverse Proxy (Host-level, Optional)**

For external access via domain/SSL:

```bash
sudo cat > /etc/nginx/sites-available/gempa-ui << 'EOF'
upstream gempa_frontend {
    server localhost:38006;
}

upstream gempa_api {
    server localhost:38003;
}

upstream gempa_ws {
    server localhost:38005;
}

server {
    listen 80;
    server_name gempa.bmkg.go.id;              # Or your domain
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name gempa.bmkg.go.id;

    ssl_certificate /etc/letsencrypt/live/gempa.bmkg.go.id/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gempa.bmkg.go.id/privkey.pem;

    # Frontend SPA
    location / {
        proxy_pass http://gempa_frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://gempa_api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # FDSN API
    location /fdsnws/ {
        proxy_pass http://gempa_api/fdsnws/;
    }

    # WebSocket
    location /socket.io/ {
        proxy_pass http://gempa_ws/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/gempa-ui /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 3.8 Fase 7: Systemd Services (Auto-start & Daemon Management)

#### **3.8.1 Create Systemd Service File**

```bash
sudo cat > /etc/systemd/system/gempa-ai-tews.service << 'EOF'
[Unit]
Description=GEMPA AI-TEWS System
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=bmkg
WorkingDirectory=/opt/gempa-ai-tews

# Start all services
ExecStart=/bin/bash -c 'cd AI-TEWS/requirements && docker-compose up -d && \
                         cd ../../sispro-tews && docker-compose up -d && \
                         cd ../AI-TEWS/AI_modules_simple_ai && docker-compose up -d && \
                         cd ../../tews-ui-vue && docker-compose up -d'

# Stop all services
ExecStop=/bin/bash -c 'cd tews-ui-vue && docker-compose down && \
                        cd ../AI-TEWS/AI_modules_simple_ai && docker-compose down && \
                        cd ../../sispro-tews && docker-compose down && \
                        cd ../AI-TEWS/requirements && docker-compose down'

# Restart policy
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable gempa-ai-tews
```

#### **3.8.2 Start the Service**

```bash
# Start
sudo systemctl start gempa-ai-tews

# Check status
sudo systemctl status gempa-ai-tews

# View logs
sudo journalctl -u gempa-ai-tews -f -n 100
```

### 3.9 Fase 8: Monitoring & Logging

#### **3.9.1 View Logs for Each Service**

```bash
# sispro-tews services
cd /opt/gempa-ai-tews/sispro-tews
docker-compose logs controller_module -f --tail 50
docker-compose logs archiving_module -f --tail 50

# AI-TEWS services
cd ../AI-TEWS/AI_modules_simple_ai
docker-compose logs p-pick_service -f --tail 50

# Infrastructure
cd ../requirements
docker-compose logs kafka -f --tail 50
```

#### **3.9.2 Health Check Script**

```bash
cat > /opt/gempa-ai-tews/healthcheck.sh << 'EOF'
#!/bin/bash

echo "=== GEMPA AI-TEWS Health Check ==="
echo "Time: $(date)"
echo ""

# Check Docker containers
echo "--- Docker Containers ---"
docker ps --filter "label=com.docker.compose.project" \
          --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check services availability
echo ""
echo "--- Service Availability ---"
echo -n "Controller API (38003): "
curl -s -m 2 http://localhost:38003/health > /dev/null && echo "OK" || echo "FAIL"

echo -n "FDSN API (38002): "
curl -s -m 2 http://localhost:38002/health > /dev/null && echo "OK" || echo "FAIL"

echo -n "API Incoming (38007): "
curl -s -m 2 http://localhost:38007/health > /dev/null && echo "OK" || echo "FAIL"

echo -n "WebSocket General (38005): "
timeout 2 bash -c '</dev/tcp/localhost/38005' 2>/dev/null && echo "OK" || echo "FAIL"

echo -n "Frontend (38006): "
curl -s -m 2 http://localhost:38006 > /dev/null && echo "OK" || echo "FAIL"

# Check database
echo ""
echo "--- Database Status ---"
docker exec $(docker ps -f "name=mongodb" -q) mongo --eval "db.adminCommand('ping')" 2>/dev/null | grep -q "ok" && echo "MongoDB: OK" || echo "MongoDB: FAIL"

# Check Kafka
echo ""
echo "--- Message Queue Status ---"
docker exec $(docker ps -f "name=kafka" -q) kafka-broker-api-versions --bootstrap-server localhost:9092 2>/dev/null | grep -q "ApiVersion" && echo "Kafka: OK" || echo "Kafka: FAIL"

# Check Redis
echo -n "Redis: "
docker exec $(docker ps -f "name=redis" -q) redis-cli ping 2>/dev/null | grep -q "PONG" && echo "OK" || echo "FAIL"

# Resource usage
echo ""
echo "--- Resource Usage ---"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
EOF

chmod +x /opt/gempa-ai-tews/healthcheck.sh

# Run health check
/opt/gempa-ai-tews/healthcheck.sh
```

#### **3.9.3 Setup Log Rotation** (logrotate)

```bash
sudo cat > /etc/logrotate.d/gempa-ai-tews << 'EOF'
/opt/gempa-ai-tews/logs/**/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    postrotate
        docker exec $(docker ps -f "name=sispro-tews" -q) kill -HUP 1 > /dev/null 2>&1 || true
    endscript
}
EOF
```

### 3.10 Fase 9: Konfigurasi Jaringan & CORS

#### **3.10.1 Update CORS Headers** (sispro-tews/.env)

```bash
# Add to sispro-tews/.env:
CORS_ORIGIN=http://152.118.31.54:38006,http://gempa.bmkg.go.id,http://localhost:5173
ALLOWED_HOSTS=152.118.31.54,gempa.bmkg.go.id,localhost
```

#### **3.10.2 Update Controller API CORS** (sispro-tews/controller_module/controller_api.py)

```python
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

origins = os.getenv("CORS_ORIGIN", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### **3.10.3 Firewall Configuration**

```bash
# Allow inbound traffic on public ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (reverse proxy)
sudo ufw allow 443/tcp     # HTTPS

# Allow internal ports (for monitoring only, not public)
# sudo ufw allow 38001/tcp
# sudo ufw allow 38002/tcp
# sudo ufw allow 38003/tcp
# sudo ufw allow 38006/tcp

sudo ufw reload
sudo ufw status
```

### 3.11 Fase 10: Backup & Data Persistence

#### **3.11.1 MongoDB Backup Script**

```bash
cat > /opt/gempa-ai-tews/backup_mongodb.sh << 'EOF'
#!/bin/bash

BACKUP_DIR=/mnt/archive/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE=$BACKUP_DIR/mongodb_$TIMESTAMP.tar.gz

mkdir -p $BACKUP_DIR

# Dump MongoDB
docker exec $(docker ps -f "name=mongodb" -q) \
    mongodump --archive=/tmp/mongodb_dump.archive

# Compress and save
docker cp $(docker ps -f "name=mongodb" -q):/tmp/mongodb_dump.archive - | \
    gzip > $BACKUP_FILE

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "mongodb_*.tar.gz" -mtime +7 -delete

echo "Backup saved: $BACKUP_FILE"
EOF

chmod +x /opt/gempa-ai-tews/backup_mongodb.sh

# Schedule daily backup
echo "0 2 * * * /opt/gempa-ai-tews/backup_mongodb.sh" | crontab -
```

#### **3.11.2 Archive Storage Monitoring**

```bash
# Monitor disk usage
df -h /mnt/archive

# Setup alert if > 80% full
USAGE=$(df /mnt/archive | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $USAGE -gt 80 ]; then
    echo "WARNING: Archive storage at ${USAGE}%" | mail -s "GEMPA Storage Alert" ops@bmkg.go.id
fi
```

### 3.12 Performance Tuning & Optimization

#### **3.12.1 CPU & Memory Allocation Summary**

| Service | CPU | Memory | Replicas | Total CPU | Total Memory |
|---------|-----|--------|----------|-----------|--------------|
| archiving_module | 2.0 | 20 GB | 7 | 14 | 140 GB |
| seedlink_module | 1.0 | 5 GB | 5 | 5 | 25 GB |
| controller_module | 1.0 | 4 GB | 1 | 1 | 4 GB |
| websocket_general | 0.5 | 2 GB | 1 | 0.5 | 2 GB |
| websocket_waveform | 0.5 | 2 GB | 1 | 0.5 | 2 GB |
| record_stream_module | 0.5 | 2 GB | 1 | 0.5 | 2 GB |
| fdsn_module + fdsn_api | 1.0 | 4 GB | 2 | 2 | 8 GB |
| api_incoming_module | 0.5 | 2 GB | 1 | 0.5 | 2 GB |
| **p-pick_service** | 4.0 | 10 GB | 5 | 20 | 50 GB |
| **p-pick_nginx** | 0.5 | 1 GB | 1 | 0.5 | 1 GB |
| association_module | 2.0 | 4 GB | 1 | 2 | 4 GB |
| locmag_module | 1.0 | 3 GB | 1 | 1 | 3 GB |
| **Kafka + Zookeeper** | 1.0 | 2 GB | 1 | 1 | 2 GB |
| **Redis** | 0.5 | 2 GB | 1 | 0.5 | 2 GB |
| **MongoDB** | 2.0 | 8 GB | 1 | 2 | 8 GB |
| **TOTAL** | - | - | - | **51 CPUs** | **259 GB** |

**System has 16 CPUs / 64 GB RAM:**
- Reduce replicas if needed (archiving: 3-5, seedlink: 2-3)
- Or disable/defer optional services (fdsn_module can run on-demand)

#### **3.12.2 Tune Kafka for High Throughput**

```bash
# In docker-compose for Kafka:
environment:
  KAFKA_LOG_RETENTION_HOURS: 168        # 7 days
  KAFKA_LOG_SEGMENT_BYTES: 1073741824   # 1 GB
  KAFKA_NUM_NETWORK_THREADS: 8
  KAFKA_NUM_IO_THREADS: 8
  KAFKA_NUM_REPLICA_FETCHERS: 4
```

#### **3.12.3 MongoDB Indexing for Query Performance**

```bash
# Connect to MongoDB and create indexes
docker exec -it $(docker ps -f "name=mongodb" -q) mongo

# In mongo shell:
db.events.createIndex({ "origin_time": -1 })
db.events.createIndex({ "latitude": 1, "longitude": 1 })
db.picks.createIndex({ "event_id": 1, "phase": 1 })
db.associations.createIndex({ "event_id": 1 })
```

### 3.13 Pre-Launch Checklist

```bash
# Run before going to production:

☐ 1. Verify all services running
     docker-compose ps | grep "Up"

☐ 2. Test API endpoints
     curl http://localhost:38003/events
     curl http://localhost:38002/fdsnws/event/1/query?limit=1

☐ 3. Test WebSocket connection
     wscat -c ws://localhost:38005/socket.io

☐ 4. Verify GPU detection
     docker exec <p-pick-container> python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"

☐ 5. Check disk space
     df -h /mnt/archive  # Should have >50% free

☐ 6. Verify database backups
     ls -lh /mnt/archive/backups/

☐ 7. Load test (basic)
     for i in {1..100}; do curl -s http://localhost:38003/events > /dev/null; done

☐ 8. Monitor logs for errors
     docker-compose logs --tail 100 | grep -i "error\|fail\|exception"

☐ 9. Verify systemd service
     systemctl status gempa-ai-tews

☐ 10. Test frontend access
      curl http://152.118.31.54:38006
```

---

## RINGKASAN DEPLOYMENT

**Local Development (Windows):**
```bash
Option A (No Docker): pip install + npm install + local Kafka/Redis/MongoDB
Option B (Full Docker): docker network create + docker-compose up for each module
```

**Production (Ubuntu 22.04 riset-01):**
```bash
1. Install NVIDIA toolkit + GPU drivers
2. Create /mnt/archive (2TB partition)
3. Clone repo + update .env (paths, replicas, GPU settings)
4. docker-compose up -d for: requirements → sispro-tews → AI-TEWS → tews-ui-vue
5. Systemd service + monitoring + backups
6. Nginx reverse proxy (optional, for domain/SSL)
7. Firewall + CORS configuration
```

**Key Optimization for riset-01 (16C/64GB/8GB GPU):**
- Archiving replicas: 7 (utilizes 14 CPUs, 140 GB)
- Seedlink replicas: 5 (utilizes 5 CPUs, 25 GB)
- P-pick with GPU: 1 instance + 5 replicas (load-balanced via nginx)
- Archive storage: /mnt/archive (2 TB)
- TensorFlow GPU: CUDA 11.8, TF 2.10, dynamic GPU memory growth

---

**Document Generated:** 2026-09-26 UTC+7  
**Prepared For:** BMKG Riset-01 Deployment Team
