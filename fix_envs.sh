#!/bin/bash

echo "Fixing .env files for Docker compose..."

# Backup existing files
cp AI-TEWS/AI_modules_simple_ai/.env AI-TEWS/AI_modules_simple_ai/.env.backup
cp AI-TEWS/requirements/.env AI-TEWS/requirements/.env.backup

# Create fixed requirements/.env
cat > AI-TEWS/requirements/.env << 'EOF'
# For flushers
kafka_host="kafka"
kafka_port="9092"

# To bind to kafka
kafka_internal_port="9092"
kafka_external_host="10.68.11.21"
kafka_external_port="9999"

# Redis
redis_host="redis"
redis_port="6379"

# MongoDB
database_host="mongodb"
database_port="27017"
database_name="sispro-tews"
database_data_path="./data"
EOF

# Create fixed AI_modules_simple_ai/.env
cat > AI-TEWS/AI_modules_simple_ai/.env << 'EOF'
# Main env filled with all similar env variables
kafka_host="kafka"
kafka_port="9092"
regional="user_bmkg"

database_host="mongodb"
database_port="27017"
database_name="sispro-tews"

redis_host="redis"
redis_port="6379"

nginx_host="localhost"
nginx_port="80"

waveform_topic="waveform_seedlink"
arrival_waveform_topic="arrival_waveform"
pick_topic="pick"
cluster_topic="cluster"
arrival_pick_topic="arrival_pick"
event_topic="event"
EOF

# Fix ai_modules/.env
if [ -f AI-TEWS/AI_modules_simple_ai/ai_modules/.env ]; then
    cp AI-TEWS/AI_modules_simple_ai/ai_modules/.env AI-TEWS/AI_modules_simple_ai/ai_modules/.env.backup
    sed -i 's/kafka_host=".*"/kafka_host="kafka"/' AI-TEWS/AI_modules_simple_ai/ai_modules/.env
    sed -i 's/kafka_port=".*"/kafka_port="9092"/' AI-TEWS/AI_modules_simple_ai/ai_modules/.env
    sed -i 's/redis_host=".*"/redis_host="redis"/' AI-TEWS/AI_modules_simple_ai/ai_modules/.env
    sed -i 's/redis_port=".*"/redis_port="6379"/' AI-TEWS/AI_modules_simple_ai/ai_modules/.env
fi

echo "Fixed .env files:"
echo "=== requirements/.env ==="
cat AI-TEWS/requirements/.env
echo ""
echo "=== AI_modules_simple_ai/.env ==="
head -20 AI-TEWS/AI_modules_simple_ai/.env
echo ""
echo "Backups saved as .env.backup"