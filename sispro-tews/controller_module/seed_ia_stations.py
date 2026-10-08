#!/usr/bin/env python3
"""
Seed seismic stations from CSV into MongoDB.

CSV source selected via STATION_CSV env var:
  - unset / "station.csv"          -> internal BMKG IA stations (data/station.csv)
  - "station_geofon.csv"           -> GEOFON public broadband stations
  - "station_public20.csv"         -> audit 2026-10-08 (20 publik SeedLink, 6 negara)

Both CSVs share the same schema; switch is a one-line env change so the
internal BMKG stations can be re-enabled later without touching the file.
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

# CSV source: default to internal BMKG IA stations
CSV_NAME = os.getenv("STATION_CSV", "station.csv")
CSV_PATH = f"./data/{CSV_NAME}"


def parse_channel_string(channel_str):
    """Convert Python list string to actual list."""
    try:
        return ast.literal_eval(channel_str)
    except Exception:
        return []


def import_stations():
    """Import stations from CSV (idempotent upsert by code+network)."""
    count_inserted = 0
    count_updated = 0
    count_error = 0

    if not os.path.isfile(CSV_PATH):
        print(f"✗ CSV not found: {CSV_PATH}")
        return 0

    print(f"Seeding stations from: {CSV_PATH}")

    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=',')
            csv_reader_rows = list(reader)
            for row in csv_reader_rows:
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
                    server_seedlink = row.get('server_seedlink', '').strip()
                    server_fdsn = row.get('server_fdsn', '').strip()

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
                        'server_seedlink': server_seedlink,
                        'server_fdsn': server_fdsn
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

        # Full sync: remove stations not present in this CSV (CSV = source of truth,
        # so switching STATION_CSV swaps the whole station set, e.g. GEOFON <-> internal BMKG).
        csv_codes = {(r.get('code', '').strip(), r.get('network', '').strip()) for r in csv_reader_rows}
        existing = list(stations_collection.find({}, {'code': 1, 'network': 1}))
        removed = 0
        for doc in existing:
            if (doc.get('code'), doc.get('network')) not in csv_codes:
                stations_collection.delete_one({'_id': doc['_id']})
                removed += 1
        print(f"  Removed (not in CSV): {removed}")

        # Verify (count all stations, not just IA)
        total = stations_collection.count_documents({})
        print(f"  MongoDB stations total: {total}")

        return count_inserted + count_updated

    except Exception as e:
        print(f"Fatal error: {e}")
        return 0


if __name__ == '__main__':
    import_stations()
