#!/bin/bash

set -e

echo "=== Starting Docker-in-Docker for GEMPA AI-TEWS ==="

# Setup Docker daemon if not running
if ! pgrep -x "dockerd" > /dev/null; then
    echo "Starting Docker daemon..."
    dockerd > /var/log/dockerd.log 2>&1 &
    sleep 5
    echo "Docker daemon started"
fi

# Wait for Docker to be ready
for i in {1..10}; do
    docker info > /dev/null 2>&1 && break
    echo "Waiting for Docker... ($i/10)"
    sleep 2
done

# Create Docker network if not exists
docker network inspect sispro-tews_req > /dev/null 2>&1 || \
    docker network create sispro-tews_req

# Setup volume mounts for persistent data
mkdir -p /app/sispro-tews/logs
mkdir -p /app/AI-TEWS/requirements/mongodb
mkdir -p /app/AI-TEWS/requirements/redis
mkdir -p /mnt/archive

# Copy .env files if not present
if [ ! -f /app/sispro-tews/.env ]; then
    cp /app/.env.sispro /app/sispro-tews/.env
fi

# Setup environment
export SERVER_IP="152.118.31.54"
export ARCHIVE_LOCATION="/mnt/archive"
export CUDA_VISIBLE_DEVICES="0"
export KAFKA_BROKER="kafka:9092"

# Set replica counts for resource optimization
export archive_replica_count=3
export seedlink_replica_count=2
export p_pick_replicas=2

# Apply resource limits if GPU detected
if docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi > /dev/null 2>&1; then
    export GPU_ENABLED="true"
    export GPU_ID="0"
fi

echo "=== Starting Docker Compose services ==="

# Change to project directory
cd /app

# Start infrastructure first (Kafka, MongoDB, Redis, Zookeeper)
cd /app/AI-TEWS/requirements
docker-compose -f docker-compose.yml up -d

echo "Waiting for infrastructure services (60s)..."
sleep 60

# Start sispro-tews backend services
cd /app/sispro-tews
docker-compose -f docker-compose.yml up -d --no-deps --remove-orphans

# Start AI modules
cd /app/AI-TEWS/AI_modules_simple_ai
docker-compose -f docker-compose.yml up -d

# Start frontend
cd /app/tews-ui-vue
docker-compose -f docker-compose.yml up -d

echo "=== All services started ==="
docker ps

# Keep container running
tail -f /dev/null
