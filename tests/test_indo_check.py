#!/usr/bin/env python3
"""
Status stasiun Indonesia di SeedLink: FDSN vs live
"""
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy.clients.fdsn import Client
import xml.etree.ElementTree as ET

SERVER = "geofon.gfz.de:18000"

print("1. Fetch FDSN metadata (25 stasiun Indonesia)...")
fdsn = Client("GFZ")
inv = fdsn.get_stations(
    network="GE",
    channel="BH?",
    minlatitude=-11, maxlatitude=6,
    minlongitude=95, maxlongitude=141,
    level="station",
)
fdsn_indo = {sta.code for net in inv for sta in net}
print(f"   FDSN Indonesia: {len(fdsn_indo)} stasiun")
print(f"   {sorted(fdsn_indo)}\n")

print("2. Fetch SeedLink live streams...")
client = EasySeedLinkClient(SERVER)
root = ET.fromstring(client.get_info("STREAMS"))

# All stations di SeedLink dengan any channel
seedlink_all = {
    s.get("name"): {st.get("seedname") for st in s.iter("stream")}
    for s in root.iter("station")
    if s.get("network") == "GE"
}
print(f"   SeedLink GE: {len(seedlink_all)} stasiun live\n")

print("3. Status setiap stasiun Indonesia:")
print(f"{'='*60}")
print(f"{'Stasiun':<10} | {'Status':<15} | {'Channel':<20}")
print(f"{'-'*60}")

active = 0
for sta in sorted(fdsn_indo):
    if sta in seedlink_all:
        channels = sorted(seedlink_all[sta])
        status = "AKTIF"
        active += 1
        print(f"{sta:<10} | {status:<15} | {channels}")
    else:
        status = "OFFLINE"
        print(f"{sta:<10} | {status:<15} | -")

print(f"{'='*60}")
print(f"Ringkasan: {active}/{len(fdsn_indo)} stasiun Indonesia aktif di SeedLink")
print(f"{'='*60}")

if active == 0:
    print("\nKesimpulan:")
    print("Semua 25 stasiun Indonesia OFFLINE di geofon.gfz.de:18000")
    print("Data Indonesia real-time ada di server internal BMKG:")
    print("  172.19.3.87:18000 (204 stasiun IA)")
