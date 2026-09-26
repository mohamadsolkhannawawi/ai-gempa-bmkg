#!/usr/bin/env python3
"""
Seed default admin user for TEWS application
"""
import pymongo
from passlib.hash import pbkdf2_sha256
import sys

# MongoDB connection
MONGO_HOST = "mongodb"
MONGO_PORT = 27017
DB_NAME = "sispro-tews"

# Default admin credentials
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"
DEFAULT_REGION = "Indonesia"

def seed_admin():
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")
        db = client[DB_NAME]
        user_collection = db["user"]
        
        # Check if admin already exists
        existing = user_collection.find_one({"username": DEFAULT_USERNAME})
        if existing:
            print(f"✓ User '{DEFAULT_USERNAME}' already exists. Skipping seed.")
            return
        
        # Hash password
        hashed_password = pbkdf2_sha256.hash(DEFAULT_PASSWORD)
        
        # Insert admin user
        user_data = {
            "username": DEFAULT_USERNAME,
            "password": hashed_password,
            "region": DEFAULT_REGION,
            "role": "superadmin",
            "modules": [],
            "stations": [],
            "disable_stations": []
        }
        
        result = user_collection.insert_one(user_data)
        print(f"✓ Created admin user successfully")
        print(f"  Username: {DEFAULT_USERNAME}")
        print(f"  Password: {DEFAULT_PASSWORD}")
        print(f"  Role: superadmin")
        print(f"  ID: {result.inserted_id}")
        
    except Exception as e:
        print(f"✗ Error seeding admin user: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    seed_admin()
