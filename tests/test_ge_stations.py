#!/usr/bin/env python3
"""
Test GE network station count via get_info("STREAMS") XML parsing
Source: Claude approach - no streaming, just XML parse
"""
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
import xml.etree.ElementTree as ET
import signal
import sys

SERVER = "geofon.gfz.de:18000"

def signal_handler(sig, frame):
    print("\nInterrupted.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

print(f"Connecting to {SERVER}...")
client = EasySeedLinkClient(SERVER)
print("Capabilities:", client.capabilities)

print("\nFetching STREAMS info...")
xml = client.get_info("STREAMS")
print(f"STREAMS XML length: {len(xml)} chars")
print("\nFirst 1000 chars:")
print(xml[:1000])
print("...")

root = ET.fromstring(xml)

# Semua stasiun jaringan GE
stasiun = {s.get("name") for s in root.iter("station") if s.get("network") == "GE"}
print(f"\n{'='*60}")
print(f"Jumlah stasiun GE: {len(stasiun)}")
print(f"Stasiun: {sorted(stasiun)}")

# Hanya yang punya channel BH?
bh = {s.get("name") for s in root.iter("station") if s.get("network") == "GE"
      and any(st.get("seedname", "").startswith("BH") for st in s.iter("stream"))}
print(f"\nJumlah stasiun GE dengan BH?: {len(bh)}")
print(f"Stasiun BH: {sorted(bh)}")
print(f"{'='*60}")
