# AI-GEMPA-BMKG CODEBASE DOCUMENTATION

## Overview

AI-GEMPA-BMKG is a seismic monitoring system combining real-time SeedLink waveform streaming, AI-powered phase detection (PhaseNet), event association, and location/magnitude calculation. Built with Docker-in-Docker architecture for nested container orchestration.

**Core Capabilities:**
- Real-time waveform ingestion from SeedLink servers (rtserve.earthscope.org:18000)
- AI-driven P/S wave phase picking using PhaseNet
- Event association and clustering
- Automatic location and magnitude calculation
- Web-based monitoring dashboard with WebSocket real-time updates
- RESTful API for configuration and data management

---

## Architecture

### High-Level Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  Docker-in-Docker Wrapper (gempa-dind-wrapper)                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Inner Docker Compose (sispro-tews/docker-compose.yml)   │  │
│  │                                                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │  SeedLink    │  │  Controller  │  │  Frontend    │   │  │
│  │  │  Module      │  │  Module      │  │  (Vue)       │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  │                                                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │  WebSocket   │  │  P-Pick      │  │  Association │   │  │
│  │  │  Module      │  │  Module (AI) │  │  Module (AI) │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  │                                                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │  LocMag      │  │  Kafka       │  │  MongoDB     │   │  │
│  │  │  Module (AI) │  │  Cluster     │  │  Redis       │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Docker Structure

#### 1. Wrapper Layer (`docker-compose.wrapper.yml`)

**Container:** `gempa-dind-wrapper`
- **Image:** `docker:27.4.0-dind`
- **Purpose:** Host Docker-in-Docker daemon for nested orchestration
- **Privileged:** Yes (required for DinD)
- **Entry Point:** `entrypoint-wrapper.sh`

**Key Responsibilities:**
- Start Docker daemon inside container
- Validate admin seed credentials from `.env.seed`
- Create Docker network `sispro-tews_req`
- Execute inner compose: `docker-compose -f /app/sispro-tews/docker-compose.yml up -d`
- Mount volumes for persistence:
  - `./sispro-tews:/app/sispro-tews`
  - `./AI-TEWS:/app/AI-TEWS`
  - `./tews-ui-vue:/app/tews-ui-vue`
  - `/mnt/archive:/mnt/archive` (waveform archive)

**Environment:**
- `DOCKER_API_VERSION=1.41`
- `COMPOSE_HTTP_TIMEOUT=300`
- Credentials from `.env.seed`: `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_PASSWORD`, etc.

#### 2. Inner Layer (`sispro-tews/docker-compose.yml`)

Orchestrates all application services inside DinD wrapper. Services share network `sispro-tews_req`.

**Services:**
- `seedlink_module` - SeedLink subscription and Kafka producer
- `controller_module` - FastAPI backend + MongoDB interface
- `frontend_module` - Vue dashboard (tews-ui-vue)
- `websocket_module` - Socket.IO real-time server
- `p_pick_module` - AI phase detection (PhaseNet)
- `association_module` - Event association
- `locmag_module` - Location/magnitude calculation
- `kafka` - Message broker
- `mongodb` - Event catalog database
- `redis` - Caching layer

---

## Data Flow

### Pipeline Overview

```
SeedLink Servers (rtserve.earthscope.org:18000)
    ↓
[seedlink_module] → Kafka: waveform_seedlink
    ↓
[p_pick_module] → Kafka: pick_topic
    ↓
[association_module] → Kafka: cluster_topic + arrival_pick_topic
    ↓
[locmag_module] → Kafka: event_topic
    ↓
[controller_module] → MongoDB: sispro-tews.events
    ↓
[websocket_module] ← Kafka topics → Socket.IO → Frontend
```

### Kafka Topics

| Topic | Producer | Consumer | Payload |
|-------|----------|----------|---------|
| `waveform_seedlink` | seedlink_module | p_pick_module | Raw waveform traces (MSEED) |
| `pick_topic` | p_pick_module | association_module | Phase picks (P/S, probability, timestamp) |
| `cluster_topic` | association_module | locmag_module | Event clusters |
| `arrival_pick_topic` | association_module | locmag_module | Arrival time picks |
| `event_topic` | locmag_module | controller_module | Located events (lat/lon/depth/mag) |

### Data Persistence

**MongoDB (`sispro-tews` database):**
- `events` - Earthquake events (origin time, location, magnitude)
- `picks` - Phase picks (station, phase, time, probability)
- `stations` - Station metadata (network, station, lat/lon/elevation)
- `user` - Admin users (username, password_hash, role)
- `module` - Configuration key-value store

**Redis:**
- Real-time event cache for WebSocket distribution
- Session storage

**Filesystem:**
- `/mnt/archive` - Long-term waveform archive (MSEED format)
- `sispro-tews/seedlink_module/data/` - Station configs
- `sispro-tews/seedlink_module/logs/` - Module logs

---

## Module Details

### 1. SeedLink Module

**Location:** `sispro-tews/seedlink_module/`

**Purpose:** Subscribe to SeedLink servers, stream waveforms to Kafka

**Key Files:**
- `seedlink_scheduler.py` - Main scheduler
- `seedlink_scheduler_app.py` - Application entry point
- `start_seedlink.sh` - Startup script (kills existing, starts scheduler)
- `entrypoint.sh` - Container entry (sets cron env, starts cron, tails log)
- `data/station_public20.csv` - Station subscription list (20 stations)

**Docker:**
- **Image:** `python:3.8-slim`
- **Env vars:** `OPENBLAS_NUM_THREADS=1`, `MPLBACKEND=Agg` (thread safety)
- **Dependencies:** `requirement.txt` (obspy, kafka-python, numpy<1.24, matplotlib<3.7)

**Station Config Format (`station_public20.csv`):**
```
network,station,location,channel,latitude,longitude,elevation
II,KAPI,00,BHZ,-5.88,119.34,150.0
PS,JAY,00,HHZ,-2.51,140.70,161.0
```

**SeedLink Server:**
- Host: `rtserve.earthscope.org`
- Port: `18000`
- Protocol: SeedLink v3

**Output:** Kafka `waveform_seedlink` topic (JSON with MSEED base64 payload)

---

### 2. Controller Module

**Location:** `sispro-tews/controller_module/`

**Purpose:** FastAPI backend for UI, MongoDB CRUD, configuration management, admin seeding

**Key Files:**
- `app.py` - Main FastAPI application
- `controller_api.py` - API endpoint definitions
- `seed_admin_user.py` - Admin user seeding script
- `entrypoint.sh` - Container entry (runs seed, starts FastAPI)
- `routes/config_routes.py` - Config API routes
- `services/config_service.py` - Config business logic
- `repositories/config_repository.py` - Config MongoDB CRUD

**Docker:**
- **Image:** `python:3.10-slim`
- **Health Check:** MongoDB ping every 30s
- **Entry:** `/app/entrypoint.sh` (seed admin → start uvicorn)

**API Endpoints:**

**Authentication:**
- `POST /api/v1/auth/login` - JWT token generation
- Token format: `eyJ...` (HS256, 24h expiry)

**Configuration Management:**
- `POST /api/v1/config/create` - Create config entry
- `GET /api/v1/config/getbyname?name={name}` - Get config by name
- `GET /api/v1/config/getall` - List all configs
- `POST /api/v1/config/update` - Update config by ID

**Config Data Model:**
```json
{
  "_id": "ObjectId",
  "name": "string",
  "config": "any (JSON value)",
  "type": "string (e.g., 'system', 'module', 'ai')"
}
```

**Admin Seeding:**
- Reads `.env.seed` for `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_PASSWORD`, etc.
- Hashes password with `pbkdf2_sha256` (passlib)
- Inserts/updates user in `sispro-tews.user` collection
- Role: `superadmin`
- Idempotent: updates if user exists

**Environment Variables (`.env`):**
- `database_host` - MongoDB host (default: `mongodb`)
- `database_port` - MongoDB port (default: `27017`)
- `database_name` - Database name (default: `sispro-tews`)
- `ssh_host`, `ssh_port`, `ssh_username`, `ssh_password` - SSH tunnel config (optional)

---

### 3. Frontend Module (tews-ui-vue)

**Location:** `tews-ui-vue/`

**Purpose:** Web-based seismic monitoring dashboard

**Tech Stack:**
- **Framework:** Vue 3 + TypeScript
- **Build:** Vite
- **UI:** Tailwind CSS
- **Real-time:** Socket.IO client
- **Deployment:** Nginx (production)

**Key Files:**
- `src/` - Vue components
- `vite.config.ts` - Vite configuration
- `docker-compose.yml` - Development compose
- `Dockerfile` - Multi-stage build (Vite → Nginx)
- `nginx.conf` - Production server config

**Features:**
- Real-time event map (Leaflet/Mapbox)
- Event list with filters (magnitude, depth, time)
- Station status monitoring
- Waveform plots
- Admin configuration panel

**WebSocket Connection:**
- Endpoint: `ws://controller_module:8000/socket.io/`
- Events: `kafka_message` (receives events from Kafka topics)

**Docker:**
- **Dev:** `node:18` + Vite dev server (port 5173)
- **Prod:** Multi-stage (build → `nginx:alpine`, port 80)

---

### 4. WebSocket Module

**Location:** `sispro-tews/controller_module/app.py` (Socket.IO integrated)

**Purpose:** Real-time event streaming to frontend via WebSocket

**Implementation:**
- **Library:** `python-socketio` + FastAPI ASGI
- **CORS:** Allow all origins (`cors_allowed_origins='*'`)
- **Mode:** Async ASGI

**Flow:**
1. Client connects → Socket.IO handshake
2. Background task starts: `kafka_listener()`
3. Kafka consumer polls `event_topic` (or configurable topics)
4. On message → decode JSON → emit `kafka_message` event to all clients
5. Frontend receives and updates UI

**Kafka Consumer Config:**
```python
kafka_consumer = KafkaConsumer(
    'event_topic',  # or environment variable
    bootstrap_servers=['kafka:9092'],
    auto_offset_reset='latest',
    enable_auto_commit=True,
    group_id='websocket-group'
)
```

**Socket.IO Events:**
- `connect(sid)` - Client connected, start Kafka listener
- `disconnect(sid)` - Client disconnected
- `kafka_message(data)` - Emit event data to client

---

### 5. P-Pick Module (AI)

**Location:** `AI-TEWS/AI_modules_simple_ai/p-pick_module/`

**Purpose:** AI-powered P/S wave phase detection using PhaseNet

**Structure:**
- `service/p_pick_consumer.py` - Kafka consumer entry point
- `consumer/` - PhaseNet inference logic
- `nginx/` - Optional reverse proxy
- `Dockerfile` - Python 3.10 slim

**Algorithm:** PhaseNet (Zhu & Beroza, 2019)
- Deep learning model for seismic phase picking
- Inputs: 3-component waveforms (Z, N, E)
- Outputs: P-wave probability, S-wave probability, phase arrival times

**Kafka Integration:**
- **Input:** `waveform_seedlink` topic (MSEED traces)
- **Output:** `pick_topic` (phase picks with probabilities)

**Docker:**
- **Image:** `python:3.10-slim`
- **Env:** `OPENBLAS_NUM_THREADS=1`, `MPLBACKEND=Agg`
- **Dependencies:** `requirements.txt` (torch, obspy, numpy, scipy)

**Pick Format:**
```json
{
  "network": "II",
  "station": "KAPI",
  "channel": "BHZ",
  "p_arrival": "2026-10-09T15:23:45.123Z",
  "p_probability": 0.95,
  "s_arrival": "2026-10-09T15:23:52.456Z",
  "s_probability": 0.87
}
```

---

### 6. Association Module (AI)

**Location:** `AI-TEWS/AI_modules_simple_ai/association_module/`

**Purpose:** Associate phase picks into seismic events using clustering

**Key Files:**
- `association_consumer.py` - Main consumer
- `Dockerfile` - Python 3.10 slim

**Algorithm:**
- Time-space clustering (DBSCAN or custom)
- Groups picks from multiple stations into event candidates
- Filters spurious picks based on consistency

**Kafka Integration:**
- **Input:** `pick_topic` (phase picks from p-pick module)
- **Output:**
  - `cluster_topic` - Event clusters for location
  - `arrival_pick_topic` - Arrival picks for each event

**Docker:**
- **Image:** `python:3.10-slim`
- **Env:** `OPENBLAS_NUM_THREADS=1`, `MPLBACKEND=Agg`
- **CMD:** `python3 -u association_consumer.py`

**Cluster Format:**
```json
{
  "cluster_id": "evt_20261009_152345",
  "origin_time_estimate": "2026-10-09T15:23:45.000Z",
  "pick_count": 8,
  "stations": ["II.KAPI", "PS.JAY", "..."]
}
```

---

### 7. LocMag Module (AI)

**Location:** `AI-TEWS/AI_modules_simple_ai/locmag_module/`

**Purpose:** Calculate event location (lat/lon/depth) and magnitude

**Key Files:**
- `locmag_consumer.py` - Main consumer
- `Dockerfile` - Python 3.10 slim

**Algorithms:**
- **Location:** Geiger's method or NonLinLoc (iterative hypocenter inversion)
- **Magnitude:** Local magnitude (ML) or moment magnitude (Mw)

**Kafka Integration:**
- **Input:**
  - `cluster_topic` - Event clusters from association
  - `arrival_pick_topic` - Phase arrival times
- **Output:** `event_topic` (located events with magnitude)

**Docker:**
- **Image:** `python:3.10-slim`
- **Env:** `OPENBLAS_NUM_THREADS=1`, `MPLBACKEND=Agg`
- **CMD:** `python3 -u locmag_consumer.py`

**Event Format:**
```json
{
  "event_id": "evt_20261009_152345",
  "origin_time": "2026-10-09T15:23:45.123Z",
  "latitude": -5.92,
  "longitude": 119.41,
  "depth_km": 15.3,
  "magnitude": 4.2,
  "magnitude_type": "ML",
  "rms_residual": 0.18,
  "azimuthal_gap": 95.0,
  "used_stations": 8
}
```

---

## Configuration System

### Architecture

**Storage:** MongoDB collection `sispro-tews.module`

**Access:** RESTful API via controller_module

**Authentication:** JWT bearer tokens (24h expiry, HS256)

### Data Model

```javascript
{
  _id: ObjectId("..."),
  name: "string",        // Config key (unique identifier)
  config: <any>,         // Config value (JSON: string, number, object, array)
  type: "string"         // Category: "system", "module", "ai", "ui"
}
```

### API Reference

#### Create Configuration

```http
POST /api/v1/config/create
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "name": "ai.ppick.threshold",
  "config_value": 0.85,
  "type_data": "ai"
}
```

**Response:**
```json
{
  "success": true,
  "message": "config create successfully",
  "data": null
}
```

#### Get Configuration by Name

```http
GET /api/v1/config/getbyname?name=ai.ppick.threshold
Authorization: Bearer {jwt_token}
```

**Response:**
```json
{
  "success": true,
  "message": "get config success",
  "data": {
    "_id": "671c8a5f...",
    "name": "ai.ppick.threshold",
    "config": 0.85,
    "type": "ai"
  }
}
```

#### Get All Configurations

```http
GET /api/v1/config/getall
Authorization: Bearer {jwt_token}
```

**Response:**
```json
{
  "success": true,
  "message": "get all config success",
  "data": [
    {
      "_id": "671c8a5f...",
      "name": "ai.ppick.threshold",
      "config": 0.85,
      "type": "ai"
    },
    {
      "_id": "671c8b12...",
      "name": "seedlink.retry_interval",
      "config": 30,
      "type": "module"
    }
  ]
}
```

#### Update Configuration

```http
POST /api/v1/config/update
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "config_id": "671c8a5f...",
  "name": "ai.ppick.threshold",
  "config_value": 0.90,
  "type_data": "ai"
}
```

**Response:**
```json
{
  "success": true,
  "message": "config update successfully",
  "data": null
}
```

### Configuration Categories (Type)

| Type | Purpose | Example Keys |
|------|---------|--------------|
| `system` | Infrastructure settings | `kafka.bootstrap_servers`, `mongodb.connection_string` |
| `module` | Module-specific config | `seedlink.retry_interval`, `controller.log_level` |
| `ai` | AI model parameters | `ppick.threshold`, `association.dbscan_eps` |
| `ui` | Frontend display settings | `map.default_zoom`, `event_list.page_size` |

### Suggested Configuration Keys for Business System

**SeedLink Module:**
- `seedlink.servers` - List of SeedLink servers (array of `{host, port}`)
- `seedlink.station_list` - Path to station CSV or inline JSON array
- `seedlink.retry_interval` - Retry delay on connection failure (seconds)
- `seedlink.buffer_size` - Kafka producer batch size

**AI P-Pick Module:**
- `ai.ppick.model_path` - PhaseNet model checkpoint path
- `ai.ppick.p_threshold` - P-wave detection threshold (0.0-1.0)
- `ai.ppick.s_threshold` - S-wave detection threshold (0.0-1.0)
- `ai.ppick.batch_size` - Inference batch size
- `ai.ppick.window_length` - Waveform window length (seconds)

**Association Module:**
- `ai.association.algorithm` - Algorithm name (`dbscan`, `growclust`)
- `ai.association.time_threshold` - Max time gap for clustering (seconds)
- `ai.association.distance_threshold` - Max distance for clustering (km)
- `ai.association.min_picks` - Minimum picks to form event

**LocMag Module:**
- `ai.locmag.algorithm` - Location algorithm (`geiger`, `nonlinloc`)
- `ai.locmag.velocity_model` - Path to velocity model file
- `ai.locmag.magnitude_relation` - Magnitude relation formula
- `ai.locmag.max_iterations` - Max iterations for location inversion

**WebSocket Module:**
- `websocket.topics` - Kafka topics to stream (array)
- `websocket.emit_interval` - Min interval between emits (ms)
- `websocket.max_clients` - Max concurrent connections

**UI Module:**
- `ui.map.provider` - Map tile provider (`openstreetmap`, `mapbox`)
- `ui.map.center` - Default map center `[lat, lon]`
- `ui.map.zoom` - Default zoom level
- `ui.event_filter.default_magnitude_min` - Default min magnitude filter
- `ui.event_filter.default_time_window` - Default time window (hours)

### Implementation Notes

**Service Layer (`config_service.py`):**
- Enforces authentication via JWT dependency injection
- Validates config data types before repository call
- Returns standardized response format: `{success, message, data}`

**Repository Layer (`config_repository.py`):**
- Pure MongoDB CRUD operations
- No business logic
- Returns raw MongoDB results or error messages

**Security:**
- JWT secret: `3e8a3f31aab886f8793176988f8298c9265f84b8388c9fef93635b08951f379b` (change in production)
- Algorithm: HS256
- Token expiry: 24 hours
- Password hashing: bcrypt (via passlib)

---

## Directory Structure

```
ai-gempa-bmkg/
├── docker-compose.wrapper.yml      # DinD wrapper orchestration
├── entrypoint-wrapper.sh           # Wrapper startup script
├── .env.seed                       # Admin seed credentials (gitignored)
├── README.md                       # Project overview
├── DEPLOY.md                       # Deployment guide
├── CODEBASE.md                     # This file
│
├── sispro-tews/                    # Inner compose application root
│   ├── docker-compose.yml          # Inner service orchestration
│   ├── .env                        # Inner compose environment
│   │
│   ├── seedlink_module/            # SeedLink subscription module
│   │   ├── Dockerfile
│   │   ├── entrypoint.sh
│   │   ├── start_seedlink.sh
│   │   ├── seedlink_scheduler.py
│   │   ├── seedlink_scheduler_app.py
│   │   ├── requirement.txt
│   │   ├── data/
│   │   │   └── station_public20.csv
│   │   └── logs/
│   │
│   ├── controller_module/          # FastAPI backend
│   │   ├── Dockerfile
│   │   ├── entrypoint.sh
│   │   ├── app.py
│   │   ├── controller_api.py
│   │   ├── seed_admin_user.py
│   │   ├── requirement.txt
│   │   ├── .env
│   │   ├── routes/
│   │   │   └── config_routes.py
│   │   ├── services/
│   │   │   └── config_service.py
│   │   ├── repositories/
│   │   │   └── config_repository.py
│   │   └── configuration/
│   │       └── database.py
│   │
│   └── [other modules: api_incoming, archiving, fdsn, flush, etc.]
│
├── tews-ui-vue/                    # Frontend dashboard
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── nginx.conf
│   ├── vite.config.ts
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   └── main.ts
│   └── public/
│
├── AI-TEWS/                        # AI modules root
│   ├── AI_modules_simple_ai/       # Production AI pipeline
│   │   ├── p-pick_module/
│   │   │   ├── Dockerfile
│   │   │   ├── requirements.txt
│   │   │   ├── service/
│   │   │   │   └── p_pick_consumer.py
│   │   │   └── consumer/
│   │   │
│   │   ├── association_module/
│   │   │   ├── Dockerfile
│   │   │   ├── requirements.txt
│   │   │   └── association_consumer.py
│   │   │
│   │   └── locmag_module/
│   │       ├── Dockerfile
│   │       ├── requirements.txt
│   │       └── locmag_consumer.py
│   │
│   ├── AI_modules_alpha/           # Experimental pipeline (alpha)
│   ├── AI_modules_beta/            # Experimental pipeline (beta)
│   ├── AI_modules_neoalpha/        # Experimental pipeline (neoalpha)
│   └── requirements/               # Infrastructure services
│       ├── kafka/
│       ├── mongodb/
│       ├── redis/
│       └── flush_module/
│
└── docs/                           # Documentation
    ├── SEEDLINK_AUDIT_20261005.md
    └── [other audit/guide docs]
```

---

## Deployment

### Prerequisites

- Docker Engine 27.4.0+ with Docker-in-Docker support
- Docker Compose 2.x
- Minimum 8GB RAM, 4 CPU cores
- 100GB storage for waveform archive

### Initial Setup

1. **Clone repository:**
   ```bash
   git clone <repo-url>
   cd ai-gempa-bmkg
   ```

2. **Configure admin credentials:**
   ```bash
   cp .env.seed.example .env.seed
   # Edit .env.seed with strong password
   ```

3. **Start wrapper (launches all services):**
   ```bash
   docker-compose -f docker-compose.wrapper.yml up -d
   ```

4. **Verify deployment:**
   ```bash
   docker exec -it gempa-dind-wrapper docker ps
   # Should show ~15 containers running
   ```

5. **Access frontend:**
   - URL: `http://<server-ip>:8006`
   - Login: Use credentials from `.env.seed`

### Configuration Files

**`.env.seed` (admin seeding):**
```env
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=Bmkg2026
INITIAL_ADMIN_EMAIL=admin@bmkg.go.id
INITIAL_ADMIN_FULLNAME=Administrator BMKG
INITIAL_ADMIN_REGION=Indonesia
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_DB_NAME=sispro-tews
```

**`sispro-tews/.env` (inner compose):**
```env
database_host=mongodb
database_port=27017
database_name=sispro-tews
kafka_host=kafka
kafka_port=9092
redis_host=redis
redis_port=6379
```

**Module-specific `.env` files:**
- `sispro-tews/seedlink_module/.env`
- `sispro-tews/controller_module/.env`
- `AI-TEWS/AI_modules_simple_ai/p-pick_module/.env`
- etc.

### Health Checks

**MongoDB:**
```bash
docker exec -it gempa-dind-wrapper docker exec mongodb mongosh --eval "db.adminCommand('ping')"
```

**Kafka:**
```bash
docker exec -it gempa-dind-wrapper docker exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092
```

**Controller API:**
```bash
curl http://localhost:8000/api/v1/health
```

**Frontend:**
```bash
curl http://localhost:8006
```

---

## Development

### Adding New Configuration Keys

1. **Define key in documentation** (e.g., `ai.newmodule.threshold`)

2. **Create via API:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/config/create \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "ai.newmodule.threshold",
       "config_value": 0.8,
       "type_data": "ai"
     }'
   ```

3. **Read in module code:**
   ```python
   import requests
   
   resp = requests.get(
       "http://controller_module:8000/api/v1/config/getbyname",
       params={"name": "ai.newmodule.threshold"},
       headers={"Authorization": f"Bearer {token}"}
   )
   config_value = resp.json()["data"]["config"]
   ```

### Module Development Workflow

1. **Create module directory:**
   ```bash
   mkdir -p sispro-tews/new_module
   cd sispro-tews/new_module
   ```

2. **Add Dockerfile:**
   ```dockerfile
   FROM python:3.10-slim
   WORKDIR /app
   ENV OPENBLAS_NUM_THREADS=1
   ENV MPLBACKEND=Agg
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["python3", "-u", "main.py"]
   ```

3. **Add to `docker-compose.yml`:**
   ```yaml
   new_module:
     build: ./new_module
     container_name: new_module
     networks:
       - sispro-tews_req
     depends_on:
       - kafka
       - mongodb
     restart: unless-stopped
   ```

4. **Test locally:**
   ```bash
   docker exec -it gempa-dind-wrapper docker-compose -f /app/sispro-tews/docker-compose.yml restart new_module
   docker exec -it gempa-dind-wrapper docker logs -f new_module
   ```

---

## Troubleshooting

### Common Issues

**1. Docker daemon not starting inside wrapper:**
```bash
docker exec -it gempa-dind-wrapper ps aux | grep dockerd
docker exec -it gempa-dind-wrapper cat /var/log/dockerd.log
```

**2. MongoDB connection refused:**
- Check network: `docker exec -it gempa-dind-wrapper docker network inspect sispro-tews_req`
- Verify MongoDB running: `docker exec -it gempa-dind-wrapper docker ps | grep mongodb`

**3. Kafka topic not found:**
```bash
docker exec -it gempa-dind-wrapper docker exec kafka kafka-topics.sh \
  --create --topic waveform_seedlink \
  --bootstrap-server localhost:9092 \
  --partitions 3 --replication-factor 1
```

**4. Admin login fails:**
- Verify seed script ran: `docker exec -it gempa-dind-wrapper docker logs controller_module | grep "Admin user"`
- Check MongoDB: `docker exec -it gempa-dind-wrapper docker exec mongodb mongosh sispro-tews --eval "db.user.findOne()"`

**5. Frontend can't connect to WebSocket:**
- Check controller module logs: `docker exec -it gempa-dind-wrapper docker logs controller_module`
- Verify Socket.IO endpoint: `curl http://localhost:8000/socket.io/?EIO=4&transport=polling`

**6. SeedLink module not receiving data:**
- Check logs: `docker exec -it gempa-dind-wrapper docker logs seedlink_module`
- Verify SeedLink server: `telnet rtserve.earthscope.org 18000`
- Check station config: `docker exec -it gempa-dind-wrapper docker exec seedlink_module cat /app/data/station_public20.csv`

---

## Technical Notes

### Thread Safety (DinD Environment)

All Python modules disable OpenBLAS threading to prevent `pthread_create` failures in nested containers:

```dockerfile
ENV OPENBLAS_NUM_THREADS=1
ENV MPLBACKEND=Agg
```

Without these, NumPy/Matplotlib operations fail with:
```
pthread_create: Resource temporarily unavailable
```

### Dependency Pinning

**Critical version constraints:**
- `numpy<1.24` (compatibility with ObsPy in Python 3.8)
- `matplotlib<3.7` (thread safety in non-interactive mode)

Remove `--preload` from Gunicorn/Uvicorn (causes worker hangs in DinD).

### Network Architecture

Single Docker network `sispro-tews_req` for all inner services. DNS resolution:
- `mongodb` → MongoDB container
- `kafka:9092` → Kafka broker
- `redis:6379` → Redis cache
- `controller_module:8000` → FastAPI backend

### Process Limits

Set `pids_limit: -1` for AI modules to prevent fork exhaustion during batch inference.

---

## References

### External Data Sources

1. **SeedLink Waveforms:**
   - Server: `rtserve.earthscope.org:18000`
   - Coverage: Global seismic network (IRIS/FDSN)

2. **Event Catalog:**
   - API: `earthquake.bmkg.go.id/catalog/api17/`
   - Polling: Every 60 seconds

3. **Station Metadata:**
   - FDSN: `service.earthscope.org/fdsnws/station/1/`
   - Sync: Daily

### Key Technologies

- **PhaseNet:** Zhu, W., & Beroza, G. C. (2019). PhaseNet: A deep-neural-network-based seismic arrival-time picking method. Geophysical Journal International.
- **ObsPy:** Seismological data processing library (Python)
- **FastAPI:** Modern async web framework
- **Socket.IO:** Real-time bidirectional communication
- **Kafka:** Distributed streaming platform
- **MongoDB:** Document database for event catalog

---

## Version History

- **v1.0** (2026-10-09): Initial production deployment
- Station count: 20 (public EarthScope stations)
- AI pipeline: simple_ai variant
- Deployment: Docker-in-Docker wrapper architecture

---

## Contact & Support

**BMKG AI-GEMPA Team**
- Email: admin@bmkg.go.id
- Documentation: See `README.md`, `DEPLOY.md`
- Issues: Check `docs/SEEDLINK_AUDIT_*.md` for known issues
