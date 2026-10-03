#!/usr/bin/env python3
"""
Cek stasiun Indonesia di SeedLink tanpa filter channel
"""
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
import xml.etree.ElementTree as ET

SERVER = "geofon.gfz.de:18000"
kode_indo = {"BBJI", "BKB", "BKNI", "BNDI", "CISI", "FAKI", "GENI", "GSI", "JAGI", "LHMI",
             "LUWI", "MMRI", "MNAI", "PLAI", "PMBI", "PMBT", "SANI", "SAUI", "SMRI", "SOEI",
             "TNTI", "TOLI", "TOLI2", "UGM", "YOGI"}

print(f"Connecting to {SERVER}...")
client = EasySeedLinkClient(SERVER)
root = ET.fromstring(client.get_info("STREAMS"))

ketemu = {}
for s in root.iter("station"):
    if s.get("name") in kode_indo:
        ketemu[(s.get("network"), s.get("name"))] = sorted(
            {st.get("seedname") for st in s.iter("stream")}
        )

print(f"\n{'='*60}")
print(f"Stasiun Indonesia ada di SeedLink: {len(ketemu)} / {len(kode_indo)}")
print(f"{'='*60}")

if ketemu:
    for (net, sta), channels in sorted(ketemu.items()):
        print(f"{net}.{sta:10} -> channels: {channels}")
else:
    print("Tidak ada stasiun Indonesia di server ini")
    
print(f"\n{'='*60}")
print("Kesimpulan:")
print("1. Ada stasiun → gunakan channel lain (HH?, SH?) bukan BH?")
print("2. Tidak ada → server GEOFON tidak menyediakan data real-time")
print("   Gunakan server internal BMKG 172.19.3.87:18000 (204 IA stations)")
print(f"{'='*60}")
