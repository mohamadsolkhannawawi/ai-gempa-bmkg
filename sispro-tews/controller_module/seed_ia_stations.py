#!/usr/bin/env python3
"""
Seed 204 Indonesia seismic stations (network IA) from CSV into MongoDB.
Uses GEOFON public SeedLink server instead of internal BMKG server.
"""
import csv
import ast
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection (compose uses database_host/port/name)
MONGO_HOST = os.getenv("database_host", "mongodb")
MONGO_PORT = os.getenv("database_port", "27017")
db_name = os.getenv("database_name", "sispro-tews")
client = MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")
db = client[db_name]
stations_collection = db['station']

CSV_PATH = "./data/station.csv"
GEOFON_SERVER = "geofon.gfz-potsdam.de:18000"

def parse_channel_string(channel_str):
    """Convert Python list string to actual list."""
    try:
        return ast.literal_eval(channel_str)
    except:
        return []

def import_stations():
    """Import all IA stations from CSV, replacing internal server with GEOFON."""
    count_inserted = 0
    count_updated = 0
    count_error = 0
    
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                try:
                    # Parse data
                    code = row.get('code', '').strip()
                    name = row.get('name', '').strip()
                    network = row.get('network', '').strip()
                    channels = parse_channel_string(row.get('channel', '[]'))
                    longitude = float(row.get('longitude', 0)) if row.get('longitude') else None
                    latitude = float(row.get('latitude', 0)) if row.get('latitude') else None
                    elevation = float(row.get('elevation', 0)) if row.get('elevation') else None
                    location = row.get('location', '').strip() or None
                    
                    if not code or not network:
                        count_error += 1
                        continue
                    
                    # Build document
                    station_doc = {
                        'code': code,
                        'name': name,
                        'network': network,
                        'channel': channels,
                        'longitude': longitude,
                        'latitude': latitude,
                        'elevation': elevation,
                        'location': location,
                        'server_seedlink': GEOFON_SERVER,  # GEOFON public
                        'server_fdsn': 'GFZ'
                    }
                    
                    # Upsert (update if exists, insert if new)
                    result = stations_collection.update_one(
                        {'code': code, 'network': network},
                        {'$set': station_doc},
                        upsert=True
                    )
                    
                    if result.upserted_id:
                        count_inserted += 1
                    elif result.modified_count > 0:
                        count_updated += 1
                    
                    if (count_inserted + count_updated) % 50 == 0:
                        print(f"Progress: {count_inserted + count_updated} processed...")
                
                except Exception as e:
                    print(f"Error processing station: {e}")
                    count_error += 1
        
        print(f"\n✓ Import complete!")
        print(f"  Inserted: {count_inserted}")
        print(f"  Updated: {count_updated}")
        print(f"  Errors: {count_error}")
        print(f"  Total: {count_inserted + count_updated}")
        
        # Verify
        total = stations_collection.count_documents({'network': 'IA'})
        print(f"  MongoDB IA stations: {total}")
        
        return count_inserted + count_updated
    
    except Exception as e:
        print(f"Fatal error: {e}")
        return 0

if __name__ == '__main__':
    import_stations()
