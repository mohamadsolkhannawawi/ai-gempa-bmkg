#!/usr/bin/env python3
"""
Filter GE stations di Indonesia dari STREAMS XML
"""
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
import xml.etree.ElementTree as ET

SERVER = "geofon.gfz.de:18000"

print(f"Connecting to {SERVER}...")
client = EasySeedLinkClient(SERVER)

print("Fetching STREAMS info...")
xml = client.get_info("STREAMS")
root = ET.fromstring(xml)

print("\nFetching STATIONS info (with coordinates)...")
stations_xml = client.get_info("STATIONS")
stations_root = ET.fromstring(stations_xml)

# Parse station coordinates from STATIONS
ge_coords = {}
for station in stations_root.iter("station"):
    if station.get("network") == "GE":
        name = station.get("name")
        lat = float(station.get("latitude", "0"))
        lon = float(station.get("longitude", "0"))
        desc = station.get("description", "")
        ge_coords[name] = {"lat": lat, "lon": lon, "desc": desc}

# Indonesia bounding box (approximate)
# Latitude: -11 to 6
# Longitude: 95 to 141
indonesia_stations = []
for name, info in ge_coords.items():
    lat, lon = info["lat"], info["lon"]
    if -11 <= lat <= 6 and 95 <= lon <= 141:
        indonesia_stations.append((name, lat, lon, info["desc"]))

print(f"\n{'='*60}")
print(f"Total GE stations: {len(ge_coords)}")
print(f"GE stations in Indonesia region: {len(indonesia_stations)}")
print(f"{'='*60}\n")

for name, lat, lon, desc in sorted(indonesia_stations):
    print(f"{name:10} | {lat:7.3f}, {lon:8.3f} | {desc}")
