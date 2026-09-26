# GEMPA AI-TEWS - Docker-in-Docker Wrapper Deployment

## Konsep
Single container yang menjalankan semua services GEMPA AI-TEWS di dalamnya menggunakan Docker-in-Docker (DinD).

## Struktur
```
gempa-dind-wrapper (1 container)
  ├── dockerd (Docker daemon inside)
  └── docker-compose orchestrate:
      ├── Infrastructure: kafka, zookeeper, mongodb, redis, flusher
      ├── Sispro-TEWS: 9 modules (archiving, seedlink, record_stream, dll)
      ├── AI-TEWS: 7 AI modules (TensorFlow + Kafka consumer)
      └── Frontend: Vue.js UI (nginx)
```

## Prerequisites (Server riset-01)
- Docker 20.10+
- NVIDIA Driver 580.178.04 (sudah ada)
- GPU: 2x GTX 1080 (sudah detect)
- Storage: /mnt/archive (2TB)

## Deploy Steps

### 1. Prepare .env files
```bash
cd ~/GEMPA/ai-gempa-bmkg
mkdir -p .envs
cp sispro-tews/.env .envs/sispro-tews.env
cp AI-TEWS/requirements/.env .envs/requirements.env
cp AI-TEWS/AI_modules_simple_ai/.env .envs/ai_modules.env
```

### 2. Build wrapper image
```bash
cd ~/GEMPA/ai-gempa-bmkg
docker build -f Dockerfile.wrapper -t gempa-wrapper:latest .
```

### 3. Run wrapper container
```bash
docker-compose -f docker-compose.wrapper.yml up -d
```

### 4. Check status
```bash
# Container wrapper status
docker ps | grep gempa-dind-wrapper

# Inner services status (exec into wrapper)
docker exec -it gempa-dind-wrapper docker ps

# Logs wrapper
docker logs -f gempa-dind-wrapper

# Logs inner service (contoh: archiving_module)
docker exec -it gempa-dind-wrapper docker logs sispro-tews_archiving_module_1
```

### 5. Verify deployment
```bash
# Health check controller
curl http://localhost:38003/health

# Frontend access
curl http://localhost:38006

# AI modules health
curl http://localhost:8000/health
```

## Management

### Start/Stop wrapper
```bash
docker-compose -f docker-compose.wrapper.yml start
docker-compose -f docker-compose.wrapper.yml stop
docker-compose -f docker-compose.wrapper.yml restart
```

### Access inner Docker
```bash
docker exec -it gempa-dind-wrapper bash
# Inside container:
docker ps
docker logs <service_name>
docker-compose -f /app/sispro-tews/docker-compose.yml restart <service>
```

### Update code & rebuild
```bash
cd ~/GEMPA/ai-gempa-bmkg
git pull origin main

# Rebuild wrapper
docker-compose -f docker-compose.wrapper.yml build

# Recreate with new code
docker-compose -f docker-compose.wrapper.yml up -d --force-recreate
```

### GPU verification (inside wrapper)
```bash
docker exec -it gempa-dind-wrapper nvidia-smi
```

## Troubleshooting

### Wrapper tidak start
```bash
docker logs gempa-dind-wrapper
```

### Inner services tidak jalan
```bash
docker exec -it gempa-dind-wrapper docker ps -a
docker exec -it gempa-dind-wrapper docker logs <failed_service>
```

### GPU tidak detect di inner containers
```bash
# Check NVIDIA runtime
docker exec -it gempa-dind-wrapper docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Port conflict (geomecca sudah pakai 8006/4002/27018)
Edit `docker-compose.wrapper.yml`, ganti port mapping:
```yaml
ports:
  - "38006:38006"  # frontend via nginx instead of 8006
  - "27017:27017"  # mongodb different from geomecca:27018
```

### Seedlink build error (apt bookworm issue)
Sudah di-skip di entrypoint-wrapper.sh. Jika perlu aktifkan:
1. Fix `sispro-tews/seedlink_module/Dockerfile` (hapus cron/nano)
2. Uncomment seedlink di entrypoint-wrapper.sh baris 55
3. Rebuild: `docker-compose -f docker-compose.wrapper.yml up -d --build`

## Architecture Notes

**Keuntungan DinD approach:**
- User bmkg hanya manage 1 container
- Inner services tetap isolated (modularity terjaga)
- Maintain docker-compose structure existing
- Bisa sudo/privileged di dalam container wrapper, host tetap restricted

**Trade-offs:**
- Nested Docker overhead ~5-10% resource
- Logs butuh `docker exec` untuk akses inner services
- Backup lebih complex (volumes + inner containers)

**Ports exposed:**
- 38001-38007: Sispro-TEWS APIs
- 8000-8007: AI-TEWS modules
- 27017, 6379, 9092, 2181: Infrastructure

**Volumes:**
- /mnt/archive: Mounted dari host (data archiving)
- gempa-docker-data: Docker daemon data (inner images/containers)
- gempa-logs: Centralized logs
- ./sispro-tews, ./AI-TEWS, ./tews-ui-vue: Code bind-mount (dev mode)

## Production Notes

Untuk production final:
1. COPY code ke image (bukan bind-mount) — edit Dockerfile.wrapper
2. Reduce log verbosity — edit entrypoint-wrapper.sh
3. Setup logrotate untuk gempa-logs volume
4. Monitor resource: `docker stats gempa-dind-wrapper`
