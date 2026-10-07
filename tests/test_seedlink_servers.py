#!/usr/bin/env python3
"""
Test server SeedLink publik untuk data Indonesia
"""
import socket
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
import xml.etree.ElementTree as ET

socket.setdefaulttimeout(15)

KANDIDAT = [
    "rtserve.iris.washington.edu:18000",
    "rtserve.earthscope.org:18000",
    "geofon.gfz.de:18000",
    "geof.bmkg.go.id:18000",
    "rtserver.ipgp.fr:18000",
    "eida.orfeus-eu.org:18000",
]

GE_INDO = {"BBJI","BKB","BKNI","BNDI","CISI","FAKI","GENI","GSI","JAGI","LHMI","LUWI",
           "MMRI","MNAI","PLAI","PMBI","PMBT","SANI","SAUI","SMRI","SOEI","TNTI",
           "TOLI","TOLI2","UGM","YOGI"}

print("Testing SeedLink servers untuk data Indonesia...\n")

for server in KANDIDAT:
    print("=" * 60)
    print(f"Server: {server}")
    print("-" * 60)
    
    try:
        c = EasySeedLinkClient(server)
        root = ET.fromstring(c.get_info("STREAMS"))
    except Exception as e:
        print(f"  GAGAL: {type(e).__name__}: {e}\n")
        continue

    semua = {(s.get("network"), s.get("name")): sorted({st.get("seedname") for st in s.iter("stream")})
             for s in root.iter("station")}
    
    ia = {k: v for k, v in semua.items() if k[0] == "IA"}
    ge = {k: v for k, v in semua.items() if k[0] == "GE" and k[1] in GE_INDO}
    global_indo = {k: v for k, v in semua.items() if k in {("II","KAPI"), ("G","PSI"), ("II","WRAB")}}

    print(f"  Total stasiun     : {len(semua)}")
    print(f"  IA (BMKG)         : {len(ia)}")
    print(f"  GE Indonesia      : {len(ge)}")
    print(f"  Global (II/G/etc) : {len(global_indo)}")
    
    if ia:
        print("\n  Stasiun IA (sample 10):")
        for k, v in sorted(ia.items())[:10]:
            print(f"    {k[0]}.{k[1]:<10} -> {v}")
    
    if ge:
        print("\n  Stasiun GE Indonesia (sample 5):")
        for k, v in sorted(ge.items())[:5]:
            print(f"    {k[0]}.{k[1]:<10} -> {v}")
    
    if global_indo:
        print("\n  Stasiun global di Indonesia:")
        for k, v in sorted(global_indo.items()):
            print(f"    {k[0]}.{k[1]:<10} -> {v}")
    
    print()

print("=" * 60)
print("Kesimpulan:")
print("- Server dengan IA > 0: SeedLink publik BMKG real-time")
print("- Semua IA = 0: gunakan FDSN dataselect atau akses internal BMKG")
print("=" * 60)
