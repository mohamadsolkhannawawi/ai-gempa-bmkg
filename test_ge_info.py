#!/usr/bin/env python3
"""
Query GE network streams dari geofon.gfz-potsdam.de:18000
"""
from obspy.clients.seedlink import Client
import sys

SERVER = "geofon.gfz-potsdam.de"
PORT = 18000

print(f"Connecting to {SERVER}:{PORT}...")
client = Client(SERVER, PORT, timeout=30)

print("\nFetching INFO STREAMS...")
streams = client.get_info('STREAMS')
print(f"STREAMS response type: {type(streams)}")
print(f"STREAMS:\n{streams}\n")

print("="*60)
print("Fetching INFO STATIONS...")
stations = client.get_info('STATIONS')
print(f"STATIONS response type: {type(stations)}")
print(f"STATIONS:\n{stations}\n")

print("="*60)
print("Fetching INFO ID...")
info_id = client.get_info('ID')
print(f"ID: {info_id}\n")

print("="*60)
print("Fetching INFO CAPABILITIES...")
caps = client.get_info('CAPABILITIES')
print(f"CAPABILITIES: {caps}\n")
