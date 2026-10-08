#!/bin/bash
# Deploy AI modules with Docker-in-Docker fixes
# Run this on server: bmkg@riset-01:~/GEMPA/ai-gempa-bmkg

set -e

echo "=========================================="
echo "  AI Modules Deployment Script"
echo "  Docker-in-Docker Optimized"
echo "=========================================="

WRAPPER="gempa-dind-wrapper"

# Step 1: Pull latest code
echo ""
echo "[1/7] Pulling latest code from GitHub..."
git pull origin main

# Step 2: Stop and clean old AI containers
echo ""
echo "[2/7] Stopping old AI containers..."
docker exec $WRAPPER bash -c "
  export DOCKER_API_VERSION=1.41
  cd /app/AI-TEWS/AI_modules_simple_ai
  docker-compose down --remove-orphans 2>/dev/null || true
  echo 'Removing old images...'
  docker rmi -f p-pick_service:latest p-pick_consumer:latest p-pick_nginx:latest \
    ai_modules_simple_ai_association_module:latest \
    ai_modules_simple_ai_locmag_module:latest \
    ai_modules_simple_ai_phase-arrival_module:latest 2>/dev/null || true
"

# Step 3: Clean build cache to force fresh build
echo ""
echo "[3/7] Cleaning Docker build cache..."
docker exec $WRAPPER bash -c "
  export DOCKER_API_VERSION=1.41
  docker system prune -f --volumes 2>/dev/null || true
"

# Step 4: Ensure shared network exists
echo ""
echo "[4/7] Ensuring shared network exists..."
docker exec $WRAPPER bash -c "
  export DOCKER_API_VERSION=1.41
  docker network inspect sispro-tews_req >/dev/null 2>&1 || \
    docker network create --driver bridge sispro-tews_req
  echo 'Networks:'
  docker network ls | grep sispro-tews
"

# Step 5: Build and start AI modules
echo ""
echo "[5/7] Building and starting AI modules (this may take 10-20 minutes)..."
docker exec $WRAPPER bash -c "
  export DOCKER_API_VERSION=1.41
  cd /app/AI-TEWS/AI_modules_simple_ai
  docker-compose up -d --build
"

# Step 6: Wait for services to stabilize
echo ""
echo "[6/7] Waiting 30 seconds for services to stabilize..."
sleep 30

# Step 7: Verify deployment
echo ""
echo "[7/7] Verifying deployment..."
docker exec $WRAPPER bash -c "
  export DOCKER_API_VERSION=1.41
  echo '--- AI Container Status ---'
  docker ps -a --filter name=ai_modules --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
  
  echo ''
  echo '--- Kafka Topics ---'
  docker exec requirements_kafka_1 kafka-topics.sh --list --bootstrap-server kafka:9092 2>/dev/null || echo 'Kafka not ready yet'
  
  echo ''
  echo '--- MongoDB Events ---'
  docker exec requirements_mongodb_1 mongo --quiet ai-gempa --eval 'db.events.countDocuments({})' 2>/dev/null || echo 'MongoDB not ready'
"

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Run ./verify-ai-pipeline.sh to check full pipeline"
echo "  2. Run ./inspect-ai-errors.sh if any service is still crashing"
echo "  3. Check frontend at http://152.118.31.54:38006/eq-view"
echo ""
echo "Note: First build may take 10-20 minutes due to TensorFlow installation."
echo "      Subsequent builds will be faster with Docker layer caching."
