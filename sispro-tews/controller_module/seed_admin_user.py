#!/usr/bin/env python3
"""
Seed admin user from environment variables
Credentials loaded from env, not hardcoded in file
"""
import pymongo
import os
import sys
import time
from passlib.hash import pbkdf2_sha256
from dotenv import load_dotenv

# Load from multiple potential locations (.env, /app/.env, ../.env, /app/sispro-tews/.env)
for _env_candidate in [".env", "/app/.env", "../.env", "/app/sispro-tews/.env"]:
    if os.path.isfile(_env_candidate):
        load_dotenv(_env_candidate, override=True)
        break
else:
    load_dotenv(override=True)

# MongoDB connection from env
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
DB_NAME = os.getenv("MONGO_DB_NAME", "sispro-tews")
MAX_RETRIES = int(os.getenv("MONGO_CONNECT_RETRIES", 10))
RETRY_DELAY = int(os.getenv("MONGO_CONNECT_RETRY_DELAY", 3))

def get_env_clean(key: str) -> str:
    """Read env var and strip accidental surrounding quotes without hardcoding credentials"""
    val = os.getenv(key)
    if val is not None:
        val = val.strip('"\'')
        if not val:
            val = None
    return val

# Admin credentials loaded strictly from environment variables (.env), never hardcoded
ADMIN_USERNAME = get_env_clean("INITIAL_ADMIN_USERNAME")
ADMIN_PASSWORD = get_env_clean("INITIAL_ADMIN_PASSWORD")
ADMIN_EMAIL = get_env_clean("INITIAL_ADMIN_EMAIL")
ADMIN_FULLNAME = get_env_clean("INITIAL_ADMIN_FULLNAME")
ADMIN_REGION = get_env_clean("INITIAL_ADMIN_REGION")

def validate_env_vars():
    """Validate required environment variables strictly from env"""
    missing = []
    if not ADMIN_USERNAME:
        missing.append("INITIAL_ADMIN_USERNAME")
    if not ADMIN_PASSWORD:
        missing.append("INITIAL_ADMIN_PASSWORD")
    if not ADMIN_EMAIL:
        missing.append("INITIAL_ADMIN_EMAIL")
    if not ADMIN_FULLNAME:
        missing.append("INITIAL_ADMIN_FULLNAME")
    if not ADMIN_REGION:
        missing.append("INITIAL_ADMIN_REGION")

    if missing:
        print(f"✗ ERROR: Missing required environment variable(s): {', '.join(missing)}", file=sys.stderr)
        print("  Please define them in your .env or container environment.", file=sys.stderr)
        sys.exit(1)

    if len(ADMIN_PASSWORD) < 8:
        print("✗ ERROR: INITIAL_ADMIN_PASSWORD must be at least 8 characters", file=sys.stderr)
        sys.exit(1)

def wait_for_mongodb():
    """Wait for MongoDB to be ready with retries"""
    print(f"[SEED] Waiting for MongoDB at {MONGO_HOST}:{MONGO_PORT}...")
    
    for attempt in range(MAX_RETRIES):
        try:
            client = pymongo.MongoClient(
                f"mongodb://{MONGO_HOST}:{MONGO_PORT}/",
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            client.admin.command('ping')
            print(f"[SEED] MongoDB ready (attempt {attempt + 1}/{MAX_RETRIES})")
            client.close()
            return True
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"[SEED] MongoDB not ready: {str(e)}. Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"✗ Failed to connect to MongoDB after {MAX_RETRIES} attempts", file=sys.stderr)
                return False
    return False

def seed_admin():
    """Create or ensure initial admin user exists and has valid password"""
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")
        db = client[DB_NAME]
        user_collection = db["user"]
        
        # Hash password using pbkdf2_sha256
        hashed_password = pbkdf2_sha256.hash(ADMIN_PASSWORD)
        
        # Check if admin already exists
        FORCE_RESET = os.getenv("FORCE_SEED_ADMIN", "false").lower() == "true"
        existing = user_collection.find_one({"username": ADMIN_USERNAME})
        if existing:
            if FORCE_RESET:
                result = user_collection.update_one(
                    {"username": ADMIN_USERNAME},
                    {"$set": {
                        "password": hashed_password,
                        "role": "superadmin",
                        "is_active": True
                    }}
                )
                print(f"[SEED] ✓ User '{ADMIN_USERNAME}' credentials verified/updated via seed.")
            else:
                print(f"[SEED] ✓ User '{ADMIN_USERNAME}' already exists in database. Preserving existing password.")
            client.close()
            return True
        
        # Create admin user document
        user_data = {
            "username": ADMIN_USERNAME,
            "email": ADMIN_EMAIL,
            "password": hashed_password,
            "full_name": ADMIN_FULLNAME,
            "region": ADMIN_REGION,
            "role": "superadmin",
            "is_active": True,
            "modules": [],
            "stations": [],
            "disable_stations": []
        }
        
        # Insert admin user
        result = user_collection.insert_one(user_data)
        
        print(f"[SEED] ✓ Admin user created successfully")
        print(f"[SEED]   ID: {result.inserted_id}")
        print(f"[SEED]   Username: {ADMIN_USERNAME}")
        print(f"[SEED]   Email: {ADMIN_EMAIL}")
        print(f"[SEED]   Role: superadmin")
        print(f"[SEED]   Region: {ADMIN_REGION}")
        
        # Log security notice (no password in logs)
        print(f"[SEED] ⚠️  Remember to change admin password after first login")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"✗ Error seeding admin user: {str(e)}", file=sys.stderr)
        return False

if __name__ == "__main__":
    print("[SEED] ========== GEMPA Admin User Seed ==========")
    print(f"[SEED] MongoDB: {MONGO_HOST}:{MONGO_PORT}")
    print(f"[SEED] Database: {DB_NAME}")
    print("[SEED]")
    
    # Validate env vars
    validate_env_vars()
    
    # Wait for MongoDB
    if not wait_for_mongodb():
        sys.exit(1)
    
    # Seed admin user
    print("[SEED]")
    if seed_admin():
        print("[SEED] ✓ Seeding completed successfully")
        sys.exit(0)
    else:
        print("[SEED] ✗ Seeding failed", file=sys.stderr)
        sys.exit(1)
