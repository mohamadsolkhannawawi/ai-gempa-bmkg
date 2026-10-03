#!/usr/bin/env python3
"""
Test GE network stations dari geofon.gfz-potsdam.de:18000
Jalankan di server dengan: python3 test_ge_stations.py
"""
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
import signal
import sys

SERVER = "geofon.gfz-potsdam.de:18000"
stations = set()
packet_count = 0

class GEStationClient(EasySeedLinkClient):
    def on_data(self, trace):
        global packet_count, stations
        packet_count += 1
        station = f"{trace.stats.network}.{trace.stats.station}"
        if trace.stats.network == "GE":
            stations.add(trace.stats.station)
            print(f"[{packet_count}] {station}.{trace.stats.location}.{trace.stats.channel} - Total GE stations: {len(stations)}")
    
    def on_seedlink_error(self):
        print("SeedLink error!")
        self.conn.disconnect()

def signal_handler(sig, frame):
    print(f"\n{'='*60}")
    print(f"Received {packet_count} packets")
    print(f"Total GE stations found: {len(stations)}")
    print(f"Station codes: {sorted(stations)}")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

print(f"Connecting to {SERVER}...")
client = GEStationClient(SERVER)

print("\nServer capabilities:", client.capabilities)
print(f"{'='*60}")

# Subscribe to GE network, all stations, BH channels (broadband high-gain)
client.select_stream("GE", "*", "BH?")

print("Listening for GE network streams... (Press Ctrl+C to stop)")
print(f"{'='*60}\n")

try:
    client.run()
except KeyboardInterrupt:
    signal_handler(None, None)
