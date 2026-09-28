#!/bin/bash

set -e

export DOCKER_API_VERSION=1.41

echo "=== Starting Docker-in-Docker for GEMPA AI-TEWS ==="
echo ""

# ========================================
# Validate Seed Credentials
# ========================================
echo "[WRAPPER] Validating seed credentials..."

if [ -z "$INITIAL_ADMIN_USERNAME" ]; then
    echo "✗ ERROR: INITIAL_ADMIN_USERNAME not set"
    echo "   Please create .env.seed from .env.seed.example"
    exit 1
fi

if [ -z "$INITIAL_ADMIN_PASSWORD" ]; then
    echo "✗ ERROR: INITIAL_ADMIN_PASSWORD not set"
    echo "   Please create .env.seed from .env.seed.example"
    exit 1
fi

if [ ${#INITIAL_ADMIN_PASSWORD} -lt 8 ]; then
    echo "✗ ERROR: INITIAL_ADMIN_PASSWORD must be at least 8 characters"
    exit 1
fi

echo "[WRAPPER] ✓ Seed credentials validated"
echo ""

# ========================================
# Setup Docker-in-Docker
# ========================================
echo "[WRAPPER] Setting up Docker daemon..."

# Setup Docker daemon if not running
if ! pgrep -x "dockerd" > /dev/null; then
    echo "[WRAPPER] Starting Docker daemon..."
    dockerd > /var/log/dockerd.log 2>&1 &
    sleep 5
    echo "[WRAPPER] Docker daemon started"
fi

# Wait for Docker socket to be ready
for i in {1..15}; do
    if [ -e /var/run/docker.sock ] && [ $(stat -c '%a' /var/run/docker.sock) != "??????" ]; then
        echo "[WRAPPER] ✓ Docker socket ready"
        break
    fi
    echo "[WRAPPER] Waiting for Docker socket... ($i/15)"
    sleep 2
done

sleep 3

# ========================================
# Setup Networks & Volumes
# ========================================
echo "[WRAPPER] Creating Docker network..."

# Create Docker network if not exists
docker network inspect sispro-tews_req > /dev/null 2>&1 || \
    docker network create sispro-tews_req

# Setup volume mounts for persistent data
echo "[WRAPPER] Setting up persistent directories..."
mkdir -p /app/sispro-tews/logs
mkdir -p /app/AI-TEWS/requirements/mongodb
mkdir -p /app/AI-TEWS/requirements/redis
mkdir -p /mnt/archive

# ========================================
# Environment Configuration
# ========================================
echo "[WRAPPER] Configuring environment..."

# Setup environment variables
export SERVER_IP="${SERVER_IP:-152.118.31.54}"
export ARCHIVE_LOCATION="${ARCHIVE_LOCATION:-/mnt/archive}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export KAFKA_BROKER="${KAFKA_BROKER:-kafka:9092}"

# Set replica counts for resource optimization
export archive_replica_count=${archive_replica_count:-3}
export seedlink_replica_count=${seedlink_replica_count:-2}
export p_pick_replicas=${p_pick_replicas:-2}

# Copy .env files if not present
if [ ! -f /app/sispro-tews/.env ]; then
    echo "[WRAPPER] Setting up sispro-tews .env..."
    cp /app/.envs/sispro-tews.env /app/sispro-tews/.env 2>/dev/null || {
        # Fallback if .envs not available
        cat > /app/sispro-tews/.env << 'EOF'
kafka_host="kafka"
kafka_port="9092"
redis_host="redis"
redis_port="6379"
database_host="mongodb"
database_port="27017"
database_name="sispro-tews"
archive_location="/mnt/archive"
archive_replica_count="3"
seedlink_replica_count="2"
EOF
    }
fi

# Apply resource limits if GPU detected
echo "[WRAPPER] Checking GPU availability..."
if docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi > /dev/null 2>&1; then
    export GPU_ENABLED="true"
    export GPU_ID="0"
    echo "[WRAPPER] ✓ GPU detected and enabled"
else
    export GPU_ENABLED="false"
    echo "[WRAPPER] GPU not available (CPU mode)"
fi

echo ""
echo "[WRAPPER] ========== Starting Docker Compose Services =========="
echo ""

# ========================================
# Start Infrastructure Services
# ========================================
echo "[WRAPPER] Starting infrastructure services (Kafka, MongoDB, Redis, Zookeeper)..."

cd /app/AI-TEWS/requirements
docker-compose -f docker-compose.yml up -d

echo "[WRAPPER] Waiting for infrastructure services to be ready (60s)..."
sleep 60

# ========================================
# Start Backend Services (with Seeding)
# ========================================
echo "[WRAPPER] Starting SISPRO-TEWS backend services..."
echo "[WRAPPER] Note: Admin user will be seeded automatically"

cd /app/sispro-tews

# Export seed credentials for docker-compose
export INITIAL_ADMIN_USERNAME="${INITIAL_ADMIN_USERNAME}"
export INITIAL_ADMIN_PASSWORD="${INITIAL_ADMIN_PASSWORD}"
export INITIAL_ADMIN_EMAIL="${INITIAL_ADMIN_EMAIL}"
export INITIAL_ADMIN_FULLNAME="${INITIAL_ADMIN_FULLNAME}"
export INITIAL_ADMIN_REGION="${INITIAL_ADMIN_REGION}"
export MONGO_HOST="${MONGO_HOST:-mongodb}"
export MONGO_PORT="${MONGO_PORT:-27017}"
export MONGO_DB_NAME="${MONGO_DB_NAME:-sispro-tews}"
export MONGO_CONNECT_RETRIES="${MONGO_CONNECT_RETRIES:-10}"
export MONGO_CONNECT_RETRY_DELAY="${MONGO_CONNECT_RETRY_DELAY:-3}"

# Start services (environment vars will be passed to containers)
docker-compose -f docker-compose.yml up -d --no-deps --remove-orphans

echo "[WRAPPER] Waiting for backend services to be ready (60s)..."
sleep 60

# ========================================
# Start AI Modules
# ========================================
echo "[WRAPPER] Starting AI modules..."

cd /app/AI-TEWS/AI_modules_simple_ai
docker-compose -f docker-compose.yml up -d

echo "[WRAPPER] Waiting for AI modules to be ready (30s)..."
sleep 30

# ========================================
# Start Frontend
# ========================================
echo "[WRAPPER] Starting frontend..."

cd /app/tews-ui-vue
docker-compose -f docker-compose.yml up -d

echo "[WRAPPER] Waiting for frontend to be ready (30s)..."
sleep 30

# ========================================
# Health Check
# ========================================
echo ""
echo "[WRAPPER] ========== Deployment Status =========="
echo ""

docker ps

echo ""
echo "[WRAPPER] Performing health checks..."
echo ""

# Check backend API
CONTROLLER_STATUS=$(docker exec -it sispro-tews_controller_module_1 curl -s http://localhost:8003/api/health 2>/dev/null | grep -q "healthy" && echo "✓" || echo "✗")
echo "[WRAPPER] Controller API: $CONTROLLER_STATUS"

# Check MongoDB
MONGO_STATUS=$(docker exec -it requirements_mongodb_1 mongo localhost:27017 --eval 'db.adminCommand("ping")' 2>/dev/null | grep -q "ok" && echo "✓" || echo "✗")
echo "[WRAPPER] MongoDB: $MONGO_STATUS"

# Check admin user seeding
ADMIN_STATUS=$(docker exec -it requirements_mongodb_1 mongo sispro-tews --eval 'db.user.findOne({username: "'"${INITIAL_ADMIN_USERNAME}"'"})' 2>/dev/null | grep -q "ObjectId" && echo "✓" || echo "✗")
echo "[WRAPPER] Admin user seeded: $ADMIN_STATUS"

echo ""
echo "[WRAPPER] ========== Deployment Complete =========="
echo ""
echo "[WRAPPER] Access points:"
echo "[WRAPPER]   Frontend: http://localhost:8006"
echo "[WRAPPER]   Controller API: http://localhost:8003"
echo "[WRAPPER]   MongoDB: localhost:32717"
echo ""
echo "[WRAPPER] Login credentials:"
echo "[WRAPPER]   Username: ${INITIAL_ADMIN_USERNAME}"
echo "[WRAPPER]   Password: (from .env.seed)"
echo "[WRAPPER]   ⚠️  Change password after first login!"
echo ""

# Keep container running
tail -f /dev/null
