#!/usr/bin/env python3
"""
Test konektivitas ke SeedLink internal BMKG 172.19.3.87:18000
"""
import socket
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
import xml.etree.ElementTree as ET

SERVER = "172.19.3.87:18000"

print(f"Testing konektivitas ke {SERVER}...")
print("=" * 60)

# Test 1: TCP socket
print("\n1. TCP socket test...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    result = sock.connect_ex(("172.19.3.87", 18000))
    sock.close()
    
    if result == 0:
        print(f"   ✓ Port 18000 TERBUKA")
    else:
        print(f"   ✗ Port 18000 TERTUTUP (error code: {result})")
except Exception as e:
    print(f"   ✗ GAGAL: {type(e).__name__}: {e}")

# Test 2: SeedLink client
print("\n2. SeedLink client test...")
try:
    client = EasySeedLinkClient(SERVER)
    print(f"   ✓ Client berhasil dibuat")
    
    # Get capabilities
    caps = client.capabilities
    print(f"   ✓ Capabilities: {caps}")
    
    # Get STREAMS info
    print("\n3. Fetching STREAMS info...")
    root = ET.fromstring(client.get_info("STREAMS"))
    
    stations = {(s.get("network"), s.get("name")) for s in root.iter("station")}
    ia_stations = {k for k in stations if k[0] == "IA"}
    
    print(f"   ✓ Total stasiun: {len(stations)}")
    print(f"   ✓ Stasiun IA: {len(ia_stations)}")
    
    if ia_stations:
        print(f"\n   Sample 10 stasiun IA:")
        for net, sta in sorted(ia_stations)[:10]:
            print(f"     {net}.{sta}")
    
    print("\n" + "=" * 60)
    print("STATUS: SERVER REACHABLE ✓")
    print("=" * 60)
    
except Exception as e:
    print(f"   ✗ GAGAL: {type(e).__name__}: {e}")
    print("\n" + "=" * 60)
    print("STATUS: SERVER NOT REACHABLE ✗")
    print("=" * 60)
    print("\nKemungkinan penyebab:")
    print("- Server down/mati")
    print("- Firewall memblokir dari riset-01")
    print("- Service SeedLink tidak berjalan")
    print("- IP/port salah")
