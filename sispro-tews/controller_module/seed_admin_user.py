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

# MongoDB connection from env
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
DB_NAME = os.getenv("MONGO_DB_NAME", "sispro-tews")
MAX_RETRIES = int(os.getenv("MONGO_CONNECT_RETRIES", 10))
RETRY_DELAY = int(os.getenv("MONGO_CONNECT_RETRY_DELAY", 3))

# Admin credentials from env (production must set these)
ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD")
ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", f"{ADMIN_USERNAME}@bmkg.go.id")
ADMIN_FULLNAME = os.getenv("INITIAL_ADMIN_FULLNAME", "Administrator BMKG")
ADMIN_REGION = os.getenv("INITIAL_ADMIN_REGION", "Indonesia")

def validate_env_vars():
    """Validate required environment variables"""
    if not ADMIN_USERNAME:
        print("✗ ERROR: INITIAL_ADMIN_USERNAME env var not set", file=sys.stderr)
        sys.exit(1)
    if not ADMIN_PASSWORD:
        print("✗ ERROR: INITIAL_ADMIN_PASSWORD env var not set", file=sys.stderr)
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
    """Create initial admin user"""
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")
        db = client[DB_NAME]
        user_collection = db["user"]
        
        # Hash password using pbkdf2_sha256
        hashed_password = pbkdf2_sha256.hash(ADMIN_PASSWORD)
        
        # Check if admin already exists
        existing = user_collection.find_one({"username": ADMIN_USERNAME})
        if existing:
            # Update password if user exists
            result = user_collection.update_one(
                {"username": ADMIN_USERNAME},
                {"$set": {"password": hashed_password}}
            )
            print(f"[SEED] ✓ User '{ADMIN_USERNAME}' password updated.")
            print(f"[SEED]   Updated: {result.modified_count} document(s)")
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
