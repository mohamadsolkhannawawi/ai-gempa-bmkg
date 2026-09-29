#!/bin/bash
# Entrypoint for controller_module container
# Runs seed first, then starts the application
set -e

echo "[CONTROLLER] ========== Controller Module Entrypoint =========="
echo "[CONTROLLER] Starting SISPRO-TEWS Controller Module"
echo "[CONTROLLER]"

# Health check: wait for MongoDB
echo "[CONTROLLER] Verifying MongoDB connectivity..."
python3 << 'EOF'
import os
import sys
import time
import pymongo

mongo_host = os.getenv("MONGO_HOST", "mongodb")
mongo_port = int(os.getenv("MONGO_PORT", 27017))
max_retries = int(os.getenv("MONGO_CONNECT_RETRIES", 10))
retry_delay = int(os.getenv("MONGO_CONNECT_RETRY_DELAY", 3))

for attempt in range(max_retries):
    try:
        client = pymongo.MongoClient(
            f"mongodb://{mongo_host}:{mongo_port}/",
            serverSelectionTimeoutMS=5000
        )
        client.admin.command('ping')
        print(f"[CONTROLLER] ✓ MongoDB is ready")
        client.close()
        sys.exit(0)
    except Exception as e:
        if attempt < max_retries - 1:
            print(f"[CONTROLLER] MongoDB not ready (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
            time.sleep(retry_delay)
        else:
            print(f"[CONTROLLER] ✗ MongoDB not available after {max_retries} attempts")
            sys.exit(1)
EOF

# Run seed script
echo "[CONTROLLER]"
echo "[CONTROLLER] Running admin user seed..."
python3 /app/seed_admin_user.py

# Check seed exit code
if [ $? -ne 0 ]; then
    echo "[CONTROLLER] ✗ Seed failed, but continuing (may already exist)"
fi

# Run IA stations seed (idempotent upsert)
echo "[CONTROLLER]"
echo "[CONTROLLER] Running IA stations seed..."
python3 /app/seed_ia_stations.py

echo "[CONTROLLER]"
echo "[CONTROLLER]"
echo "[CONTROLLER] Starting Uvicorn server..."
echo "[CONTROLLER] =========================================="
echo "[CONTROLLER]"

exec python3 controller_api_app.py
