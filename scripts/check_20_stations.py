#!/usr/bin/env python3
"""
check_20_stations.py
Audit ketersediaan 20 stasiun SeedLink (EarthScope / IRIS) dan status pipeline trace GEMPA.
Dapat dijalankan langsung dengan:
  python3 scripts/check_20_stations.py
"""
import os
import sys
import csv
import ast
import time
import socket
import subprocess

def readline_sock(sock, timeout=5):
    sock.settimeout(timeout)
    buf = b""
    while not buf.endswith(b"\n"):
        try:
            c = sock.recv(1)
            if not c:
                break
            buf += c
        except socket.timeout:
            break
        except Exception:
            break
    return buf.decode("utf-8", "replace").strip()

def test_seedlink_station(host, port, network, code, channels, timeout=8):
    """Test single station on SeedLink server"""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.sendall(b"HELLO\r")
        banner1 = readline_sock(s, timeout)
        banner2 = readline_sock(s, timeout)
        
        # Test STATION
        s.sendall(f"STATION {code} {network}\r".encode())
        res_sta = readline_sock(s, timeout)
        if res_sta != "OK":
            s.close()
            return False, f"STATION rejected ({res_sta})", []
            
        # Test channels
        valid_channels = []
        for ch in channels:
            # e.g. BHZ or HHZ
            sel = ch[-3:]
            s.sendall(f"SELECT {sel}\r".encode())
            res_ch = readline_sock(s, timeout)
            if res_ch == "OK":
                valid_channels.append(sel)
                
        s.close()
        return True, "OK", valid_channels
    except Exception as e:
        return False, f"Connection error: {e}", []

def test_live_packet(host, port, network, code, channel="BHZ", wait_sec=8):
    """Test receiving at least 1 live data packet from the station"""
    try:
        s = socket.create_connection((host, port), timeout=5)
        s.sendall(b"HELLO\r")
        readline_sock(s, 2)
        readline_sock(s, 2)
        
        s.sendall(f"STATION {code} {network}\r".encode())
        readline_sock(s, 2)
        
        s.sendall(f"SELECT {channel}\r".encode())
        readline_sock(s, 2)
        
        s.sendall(b"DATA\r")
        res_data = readline_sock(s, 2)
        if res_data != "OK":
            s.close()
            return False, f"DATA rejected: {res_data}"
            
        s.settimeout(1.0)
        t_start = time.time()
        received_bytes = 0
        while time.time() - t_start < wait_sec:
            try:
                chunk = s.recv(520)
                if chunk and len(chunk) >= 8 and chunk[:2] == b"SL":
                    received_bytes += len(chunk)
                    s.close()
                    return True, f"Live packet received ({len(chunk)} bytes)"
            except socket.timeout:
                continue
            except Exception:
                break
        s.close()
        return False, f"Idle (no packet in {wait_sec}s)"
    except Exception as e:
        return False, f"Error: {e}"

def main():
    print("=" * 95)
    print("   AUDIT STATUS 20 STASIUN SEEDLINK (EARTHSCOPE / IRIS) & PIPELINE TRACE GEMPA")
    print("=" * 95)
    
    # Locate station CSV
    base_dirs = [
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        os.getcwd(),
        "/home/bmkg/GEMPA/ai-gempa-bmkg"
    ]
    target_csv = None
    for b in base_dirs:
        candidate = os.path.join(b, "sispro-tews", "seedlink_module", "data", "station_public20.csv")
        if os.path.isfile(candidate):
            target_csv = candidate
            break
            
    if not target_csv:
        print("✗ File station_public20.csv tidak ditemukan!")
        sys.exit(1)
        
    print(f"File Konfigurasi : {target_csv}")
    
    stations = []
    with open(target_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ch_list = []
            try:
                ch_list = ast.literal_eval(r.get("channel", "[]"))
            except Exception:
                ch_list = ["BHZ"]
            stations.append({
                "code": r["code"].strip(),
                "network": r["network"].strip(),
                "name": r.get("name", "").strip(),
                "server": r.get("server_seedlink", "rtserve.earthscope.org:18000").strip(),
                "channels": ch_list
            })
            
    print(f"Total Stasiun    : {len(stations)} stasiun")
    print(f"SeedLink Server  : rtserve.earthscope.org:18000 (EarthScope US)")
    print("-" * 95)
    
    # 1. Test SeedLink Server TCP & HELLO
    print("\n[FASE 1] Menguji Konektivitas Server SeedLink (rtserve.earthscope.org:18000)...")
    try:
        s = socket.create_connection(("rtserve.earthscope.org", 18000), timeout=6)
        s.sendall(b"HELLO\r")
        b1 = readline_sock(s, 5)
        b2 = readline_sock(s, 5)
        s.close()
        print(f"  ✓ Terhubung! Banner: {b1} | {b2}")
    except Exception as e:
        print(f"  ✗ Gagal menghubungi rtserve.earthscope.org:18000: {e}")
        print("    (Periksa koneksi internet server atau firewall port 18000)")
        sys.exit(1)
        
    # 2. Test each station
    print("\n[FASE 2] Menguji Respons Masing-masing dari 20 Stasiun...")
    print(f"{'No':<3} {'Net.Sta':<14} {'Negara / Lokasi':<28} {'Server Respons':<16} {'Kanal Aktif'}")
    print("-" * 95)
    
    active_count = 0
    for idx, st in enumerate(stations, 1):
        net_sta = f"{st['network']}.{st['code']}"
        country = st['name'].split('(')[-1].replace(')', '') if '(' in st['name'] else st['name']
        country = country.split(',')[0].strip()
        
        host, _, port = st["server"].partition(":")
        port = int(port) if port else 18000
        
        ok, msg, valid_chans = test_seedlink_station(host, port, st["network"], st["code"], st["channels"])
        
        if ok:
            active_count += 1
            status_text = "✓ AKTIF (OK)"
            chan_str = ", ".join(valid_chans[:4])
            if len(valid_chans) > 4:
                chan_str += f" (+{len(valid_chans)-4})"
        else:
            status_text = f"✗ {msg}"
            chan_str = "-"
            
        print(f"{idx:<3} {net_sta:<14} {country[:26]:<28} {status_text:<16} {chan_str}")
        
    print("-" * 95)
    print(f"Hasil Stasiun: {active_count}/{len(stations)} stasiun aktif dan merespons perintah STATION & SELECT.")
    
    # 3. Test Live Packet Sample on Top Stations
    print("\n[FASE 3] Uji Coba Penerimaan Paket Live Stream (Sample Stasiun Indonesia & Tetangga)...")
    sample_tests = [("II", "KAPI", "BHZ"), ("PS", "JAY", "BHZ"), ("MS", "NTU", "BHZ")]
    for net, sta, ch in sample_tests:
        ok, res_str = test_live_packet("rtserve.earthscope.org", 18000, net, sta, ch, wait_sec=6)
        icon = "✓" if ok else "⚠"
        print(f"  {icon} {net}.{sta} ({ch}): {res_str}")
        
    # 4. Check Local GEMPA Pipeline
    print("\n[FASE 4] Memeriksa Komponen Pipeline Trace Lokal (Docker Containers)...")
    try:
        res = subprocess.run(["docker", "ps", "--format", "{{.Names}} | {{.Status}}"], capture_output=True, text=True)
        lines = res.stdout.strip().split("\n")
        
        target_services = ["seedlink_module", "websocket_waveform", "kafka", "redis"]
        for svc in target_services:
            matched = [line for line in lines if svc in line]
            if matched:
                for m in matched:
                    print(f"  ✓ Container: {m}")
            else:
                print(f"  ✗ Container TIDAK BERJALAN: {svc}")
    except Exception as e:
        print(f"  (Gagal memeriksa Docker ps: {e})")
        
    print("\n" + "=" * 95)

if __name__ == "__main__":
    main()
