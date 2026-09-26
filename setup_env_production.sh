#!/bin/bash

# Setup .env files untuk production deployment di riset-01
# Run: bash setup_env_production.sh

echo "============================================"
echo "GEMPA AI-TEWS Production .env Setup"
echo "Server: riset-01 (152.118.31.54)"
echo "============================================"
echo ""

# Default values
DEFAULT_KAFKA_PORT=9092
DEFAULT_KAFKA_EXTERNAL_PORT=29092
DEFAULT_REDIS_PORT=6379
DEFAULT_DATABASE_PORT=27017
DEFAULT_ARCHIVE_LOCATION=/mnt/archive
DEFAULT_ARCHIVE_REPLICAS=3
DEFAULT_SEEDLINK_REPLICAS=2
DEFAULT_NGINX_PORT=80
DEFAULT_SERVER_IP=152.118.31.54
DEFAULT_KAFKA_EXTERNAL_HOST=152.118.31.54

# Input dengan default
read -p "Kafka port [default: $DEFAULT_KAFKA_PORT]: " KAFKA_PORT
KAFKA_PORT=${KAFKA_PORT:-$DEFAULT_KAFKA_PORT}

read -p "Kafka external port [default: $DEFAULT_KAFKA_EXTERNAL_PORT]: " KAFKA_EXTERNAL_PORT
KAFKA_EXTERNAL_PORT=${KAFKA_EXTERNAL_PORT:-$DEFAULT_KAFKA_EXTERNAL_PORT}

read -p "Kafka external host [default: $DEFAULT_KAFKA_EXTERNAL_HOST]: " KAFKA_EXTERNAL_HOST
KAFKA_EXTERNAL_HOST=${KAFKA_EXTERNAL_HOST:-$DEFAULT_KAFKA_EXTERNAL_HOST}

read -p "Redis port [default: $DEFAULT_REDIS_PORT]: " REDIS_PORT
REDIS_PORT=${REDIS_PORT:-$DEFAULT_REDIS_PORT}

read -p "MongoDB port [default: $DEFAULT_DATABASE_PORT]: " DATABASE_PORT
DATABASE_PORT=${DATABASE_PORT:-$DEFAULT_DATABASE_PORT}

read -p "Archive location [default: $DEFAULT_ARCHIVE_LOCATION]: " ARCHIVE_LOCATION
ARCHIVE_LOCATION=${ARCHIVE_LOCATION:-$DEFAULT_ARCHIVE_LOCATION}

read -p "Archive replica count (reduce if low resource) [default: $DEFAULT_ARCHIVE_REPLICAS]: " ARCHIVE_REPLICAS
ARCHIVE_REPLICAS=${ARCHIVE_REPLICAS:-$DEFAULT_ARCHIVE_REPLICAS}

read -p "SeedLink replica count [default: $DEFAULT_SEEDLINK_REPLICAS]: " SEEDLINK_REPLICAS
SEEDLINK_REPLICAS=${SEEDLINK_REPLICAS:-$DEFAULT_SEEDLINK_REPLICAS}

read -p "Nginx port [default: $DEFAULT_NGINX_PORT]: " NGINX_PORT
NGINX_PORT=${NGINX_PORT:-$DEFAULT_NGINX_PORT}

read -p "Server IP address [default: $DEFAULT_SERVER_IP]: " SERVER_IP
SERVER_IP=${SERVER_IP:-$DEFAULT_SERVER_IP}

read -p "GPU enabled? (y/n) [default: y]: " GPU_ENABLED
GPU_ENABLED=${GPU_ENABLED:-y}

if [[ "$GPU_ENABLED" == "y" ]]; then
    read -p "GPU device ID (0-based, e.g. 0) [default: 0]: " GPU_ID
    GPU_ID=${GPU_ID:-0}
    CUDA_VISIBLE_DEVICES=$GPU_ID
else
    CUDA_VISIBLE_DEVICES=-1
fi

echo ""
echo "============================================"
echo "Creating .env files..."
echo "============================================"
echo ""

# 1. AI-TEWS/requirements/.env
echo "1. Creating AI-TEWS/requirements/.env"
cat > "AI-TEWS/requirements/.env" << EOF
kafka_host="kafka"
kafka_port="$KAFKA_PORT"
kafka_external_port="$KAFKA_EXTERNAL_PORT"
kafka_external_host="$KAFKA_EXTERNAL_HOST"
redis_host="redis"
redis_port="$REDIS_PORT"
regional="bmkg_riset01"
ssh_host="$SERVER_IP"
ssh_port="22"
ssh_username="bmkg"
database_host="mongodb"
database_port="$DATABASE_PORT"
database_name="sispro-tews"
database_root_username="admin"
database_root_password="admin123"
database_data_path="./data"
EOF
echo "   ✓ Created"

# 2. sispro-tews/.env
echo "2. Creating sispro-tews/.env"
cat > "sispro-tews/.env" << EOF
# Database
DATABASE_HOST=mongodb
DATABASE_PORT=$DATABASE_PORT
database_host=mongodb
database_port=$DATABASE_PORT
database_name=sispro-tews

# Cache
REDIS_HOST=redis
REDIS_PORT=$REDIS_PORT
redis_host=redis
redis_port=$REDIS_PORT

# Message Queue
KAFKA_HOST=kafka
KAFKA_PORT=$KAFKA_PORT
kafka_host=kafka
kafka_port=$KAFKA_PORT

# Archive storage
archive_location=$ARCHIVE_LOCATION
archive_replica_count=$ARCHIVE_REPLICAS

# SeedLink
seedlink_replica_count=$SEEDLINK_REPLICAS

# Server configuration
SERVER_IP=$SERVER_IP
CORS_ORIGIN=http://$SERVER_IP:38006,http://localhost:38006
ALLOWED_HOSTS=$SERVER_IP,localhost
EOF
echo "   ✓ Created"

# 3. AI-TEWS/AI_modules_simple_ai/.env
echo "3. Creating AI-TEWS/AI_modules_simple_ai/.env"
cat > "AI-TEWS/AI_modules_simple_ai/.env" << EOF
# Kafka
kafka_host=kafka
kafka_port=$KAFKA_PORT

# Redis
redis_host=redis
redis_port=$REDIS_PORT

# MongoDB
mongodb_host=mongodb
mongodb_port=$DATABASE_PORT
MONGODB_HOST=mongodb
MONGODB_PORT=$DATABASE_PORT

# Nginx (p-pick load balancer)
nginx_port=$NGINX_PORT

# TensorFlow GPU configuration
CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES
TF_CPP_MIN_LOG_LEVEL=1
TF_FORCE_GPU_ALLOW_GROWTH=true

# General
regional=bmkg_riset01
EOF
echo "   ✓ Created"

# 4. tews-ui-vue/.env.production
echo "4. Creating tews-ui-vue/.env.production"
cat > "tews-ui-vue/.env.production" << EOF
VITE_API_BASE_URL=http://$SERVER_IP:38003
VITE_SOCKET_IO_URL=http://$SERVER_IP:38005
VITE_FDSN_API_URL=http://$SERVER_IP:38002
VITE_WAVEFORM_URL=http://$SERVER_IP:38004
EOF
echo "   ✓ Created"

echo ""
echo "============================================"
echo "Summary of Configuration"
echo "============================================"
echo ""
echo "Kafka:"
echo "  - Internal host: kafka"
echo "  - Internal port: $KAFKA_PORT"
echo "  - External host: $KAFKA_EXTERNAL_HOST"
echo "  - External port: $KAFKA_EXTERNAL_PORT"
echo ""
echo "Redis:"
echo "  - Host: redis"
echo "  - Port: $REDIS_PORT"
echo ""
echo "MongoDB:"
echo "  - Host: mongodb"
echo "  - Port: $DATABASE_PORT"
echo ""
echo "Archive Storage:"
echo "  - Location: $ARCHIVE_LOCATION"
echo "  - Archiving replicas: $ARCHIVE_REPLICAS"
echo "  - SeedLink replicas: $SEEDLINK_REPLICAS"
echo ""
echo "AI-TEWS:"
echo "  - Nginx port: $NGINX_PORT"
echo "  - GPU enabled: $([[ $CUDA_VISIBLE_DEVICES == "-1" ]] && echo "NO (CPU only)" || echo "YES (GPU $CUDA_VISIBLE_DEVICES)")"
echo ""
echo "Server:"
echo "  - IP: $SERVER_IP"
echo "  - Frontend: http://$SERVER_IP:38006"
echo "  - API: http://$SERVER_IP:38003"
echo "  - FDSN: http://$SERVER_IP:38002"
echo ""
echo "============================================"
echo "Next Steps:"
echo "============================================"
echo ""
echo "1. Prepare archive directory on server:"
echo "   ssh bmkg@$SERVER_IP"
echo "   sudo mkdir -p $ARCHIVE_LOCATION"
echo "   sudo chown -R bmkg:bmkg $ARCHIVE_LOCATION"
echo "   sudo chmod 777 $ARCHIVE_LOCATION"
echo ""
echo "2. Copy .env files to server (or upload via git):"
echo "   scp sispro-tews/.env bmkg@$SERVER_IP:/opt/gempa-ai-tews/sispro-tews/"
echo "   scp AI-TEWS/requirements/.env bmkg@$SERVER_IP:/opt/gempa-ai-tews/AI-TEWS/requirements/"
echo "   scp AI-TEWS/AI_modules_simple_ai/.env bmkg@$SERVER_IP:/opt/gempa-ai-tews/AI-TEWS/AI_modules_simple_ai/"
echo ""
echo "3. Create Docker network on server:"
echo "   docker network create sispro-tews_req"
echo ""
echo "4. Deploy services (run on server):"
echo "   cd /opt/gempa-ai-tews"
echo "   docker-compose -f AI-TEWS/requirements/docker-compose.yml up -d"
echo "   sleep 30"
echo "   docker-compose -f sispro-tews/docker-compose.yml up -d"
echo "   docker-compose -f AI-TEWS/AI_modules_simple_ai/docker-compose.yml up -d"
echo "   docker-compose -f tews-ui-vue/docker-compose.yml up -d"
echo ""
echo "5. Verify deployment:"
echo "   curl http://localhost:38003/health"
echo "   docker-compose ps"
echo ""
echo "✓ Setup complete!"
EOF
