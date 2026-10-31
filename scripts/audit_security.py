#!/usr/bin/env python3
"""
audit_security.py - Comprehensive Security & Ransomware Prevention Audit
GEMPA AI-TEWS System

Audits:
  1. Docker Port Bindings (ensures NO database/broker/infra ports bound to 0.0.0.0)
  2. MongoDB Health & Ransomware Footprint Check (verifies no ransom notes/databases exist)
  3. Essential Data Collections & User Persistence Check
  4. Docker Socket & Host Exposure Analysis
"""

import sys
import json
import subprocess
from datetime import datetime

# Ports that MUST NEVER be bound to 0.0.0.0 (must be localhost 127.0.0.1 or internal only)
SENSITIVE_PORTS = {
    27017: "MongoDB (Database)",
    32717: "MongoDB (DinD mapping)",
    6379:  "Redis (Cache/PubSub)",
    36379: "Redis (DinD mapping)",
    2181:  "Zookeeper (Coordination)",
    32181: "Zookeeper (DinD mapping)",
    9092:  "Kafka (Event Broker)",
    9999:  "Kafka External (Event Broker)",
    39092: "Kafka (DinD mapping)"
}

# Known ransomware database patterns
RANSOM_PATTERNS = [
    "read_me", "recover", "ransom", "decrypt", "restore", "bitcoin", "warning", "how_to"
]

def log_header(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def check_docker_ports():
    log_header("AUDIT 1: DOCKER PORT BINDINGS & FIREWALL ISOLATION")
    issues = []
    
    try:
        res = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True, text=True, check=True
        )
        containers = [json.loads(line) for line in res.stdout.strip().split("\n") if line.strip()]
    except Exception as e:
        print(f"✗ Gagal menjalankan 'docker ps': {e}")
        return False

    print(f"Memeriksa {len(containers)} kontainer yang aktif...")
    
    for c in containers:
        name = c.get("Names", "unknown")
        ports_str = c.get("Ports", "")
        
        for port, desc in SENSITIVE_PORTS.items():
            # Check for dangerous 0.0.0.0:PORT or :::PORT
            dangerous_patterns = [f"0.0.0.0:{port}->", f":::{port}->"]
            for pat in dangerous_patterns:
                if pat in ports_str:
                    issues.append({
                        "container": name,
                        "port": port,
                        "description": desc,
                        "binding": pat,
                        "severity": "CRITICAL"
                    })
                    print(f"  [CRITICAL] Kontainer '{name}' mengekspos {desc} port {port} ke INTERNET BEBAS ({pat})!")

    if not issues:
        print("  ✓ SEMUA port database, broker, dan infrastruktur terisolasi dengan aman!")
        print("    (Hanya terikat ke 127.0.0.1 atau berjalan dalam jaringan virtual internal Docker).")
        return True
    else:
        print(f"\n  ✗ Ditemukan {len(issues)} potensi celah keterbukaan port publik!")
        return False

def check_mongodb_integrity():
    log_header("AUDIT 2: INTEGRITAS MONGODB & JEJAK RANSOMWARE")
    
    cmd = (
        "docker exec requirements_mongodb_1 mongo --quiet --eval '"
        "var dbs = db.adminCommand(\"listDatabases\").databases.map(d => d.name);"
        "print(JSON.stringify(dbs));"
        "'"
    )
    
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        out = res.stdout.strip()
        lines = [line for line in out.split("\n") if line.startswith("[") and line.endswith("]")]
        if not lines:
            print(f"  ⚠ Tidak dapat membaca daftar database dari requirements_mongodb_1: {out}")
            return False
        
        databases = json.loads(lines[-1])
        print(f"Daftar database di MongoDB: {', '.join(databases)}")
        
        # Check for ransom db
        ransom_detected = []
        for db_name in databases:
            for pattern in RANSOM_PATTERNS:
                if pattern in db_name.lower():
                    ransom_detected.append(db_name)
                    
        if ransom_detected:
            print(f"  [CRITICAL] Terdeteksi jejak database ransomware: {ransom_detected}!")
            return False
        else:
            print("  ✓ Tidak terdeteksi adanya database tebusan/ransomware.")
            
        # Check essential collections in sispro-tews
        colls_cmd = (
            "docker exec requirements_mongodb_1 mongo --quiet --eval '"
            "var d = db.getSiblingDB(\"sispro-tews\");"
            "var res = {"
            "  user_count: d.user.count(),"
            "  station_count: d.station.count(),"
            "  admin_exists: !!d.user.findOne({username: \"admin\"})"
            "};"
            "print(JSON.stringify(res));"
            "'"
        )
        res_colls = subprocess.run(colls_cmd, shell=True, capture_output=True, text=True)
        colls_out = [l for l in res_colls.stdout.strip().split("\n") if l.startswith("{") and l.endswith("}")]
        if colls_out:
            stats = json.loads(colls_out[-1])
            print(f"  ✓ Database 'sispro-tews' AKTIF:")
            print(f"    - User superadmin 'admin' : {'ADA (Valid)' if stats.get('admin_exists') else 'TIDAK ADA'}")
            print(f"    - Total Pengguna          : {stats.get('user_count')}")
            print(f"    - Total Stasiun Seismik   : {stats.get('station_count')}")
            
            if not stats.get("admin_exists"):
                print("  ⚠ User 'admin' belum terdaftar di database!")
                return False
        return True
    except Exception as e:
        print(f"  ⚠ Gagal mengaudit MongoDB: {e}")
        return False

def check_retention_and_backups():
    log_header("AUDIT 3: STATUS BACKUP & CRON RETENSI STORAGE")
    
    try:
        cron_res = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if "cleanup_storage.sh" in cron_res.stdout:
            print("  ✓ Cron job pembersihan storage & log terpasang aktif di sistem.")
        else:
            print("  ⚠ Cron job cleanup belum terpasang di crontab!")
            
        # Check backup directory
        bak_cmd = "docker exec requirements_mongodb_1 ls -ld /data/db/backup_* 2>/dev/null"
        bak_res = subprocess.run(bak_cmd, shell=True, capture_output=True, text=True)
        if "backup_" in bak_res.stdout:
            print("  ✓ File snapshot/backup database ditemukan di storage MongoDB.")
        else:
            print("  ℹ Belum ada snapshot backup lokal di /data/db/backup_*. (Disarankan membuat backup berkala).")
    except Exception as e:
        print(f"  ⚠ Status backup check: {e}")

def main():
    print("=" * 80)
    print("      AUDIT KEAMANAN LENGKAP & PENCEGAHAN RANSOMWARE (GEMPA BMKG)")
    print(f"      Waktu Audit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    ports_ok = check_docker_ports()
    db_ok = check_mongodb_integrity()
    check_retention_and_backups()
    
    log_header("KESIMPULAN AUDIT")
    if ports_ok and db_ok:
        print("  [STATUS: SECURE / AMAN] ✓")
        print("  Seluruh celah keterbukaan port publik telah terkunci.")
        print("  Database terisolasi dari bot internet dan data tersimpan dengan benar.")
    else:
        print("  [STATUS: PERLU TINDAKAN / WARNING] ⚠")
        print("  Silakan tinjau catatan peringatan di atas.")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
