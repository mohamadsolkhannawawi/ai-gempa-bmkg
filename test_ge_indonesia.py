#!/usr/bin/env python3
"""
Stasiun Indonesia (GE+IA network) aktif di SeedLink
Method: FDSN metadata + SeedLink real-time intersection
"""
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy.clients.fdsn import Client
import xml.etree.ElementTree as ET

print("Fetching FDSN metadata...")
fdsn = Client("GFZ")
inv = fdsn.get_stations(
    network="GE,IA",              # GE = GEOFON, IA = BMKG Indonesia
    channel="BH?",
    minlatitude=-11, maxlatitude=6,
    minlongitude=95, maxlongitude=141,
    level="station",
)
indo = {(net.code, sta.code) for net in inv for sta in net}
print(f"Stasiun Indonesia (FDSN): {len(indo)}")

print("\nFetching SeedLink live availability...")
client = EasySeedLinkClient("geofon.gfz.de:18000")
root = ET.fromstring(client.get_info("STREAMS"))

live = {
    (s.get("network"), s.get("name"))
    for s in root.iter("station")
    if any(st.get("seedname", "").startswith("BH") for st in s.iter("stream"))
}
print(f"Stasiun live di SeedLink (all networks): {len(live)}")

# Intersection: stasiun Indonesia + aktif di SeedLink
hasil = sorted(indo & live)
print(f"\n{'='*60}")
print(f"Stasiun Indonesia aktif di SeedLink: {len(hasil)}")
print(f"{'='*60}\n")

for net, sta in hasil:
    print(f"{net}.{sta}")
