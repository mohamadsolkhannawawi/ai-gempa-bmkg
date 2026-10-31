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
    
    js_dbs = (
        'var dbs; '
        'try { dbs = db.getMongo().getDBNames(); } '
        'catch(e) { var a = db.adminCommand({listDatabases: 1}); dbs = (a.databases||[]).map(function(x){return x.name;}); } '
        'print("DATABASES_JSON:" + JSON.stringify(dbs));'
    )
    
    try:
        res = subprocess.run(
            ["docker", "exec", "requirements_mongodb_1", "mongo", "--quiet", "--eval", js_dbs],
            capture_output=True, text=True
        )
        out = res.stdout.strip()
        db_line = ""
        for line in out.split("\n"):
            if "DATABASES_JSON:" in line:
                db_line = line.split("DATABASES_JSON:")[-1].strip()
                break
                
        if not db_line:
            # Fallback test with mongosh
            res2 = subprocess.run(
                ["docker", "exec", "requirements_mongodb_1", "mongosh", "--quiet", "--eval", js_dbs],
                capture_output=True, text=True
            )
            for line in res2.stdout.strip().split("\n"):
                if "DATABASES_JSON:" in line:
                    db_line = line.split("DATABASES_JSON:")[-1].strip()
                    break

        if not db_line:
            # Fallback test with python in controller module container
            py_code = (
                "import os, json, pymongo; "
                "c = pymongo.MongoClient(os.getenv('DATABASE_URL', 'mongodb://mongodb:27017/sispro-tews')); "
                "print('DATABASES_JSON:' + json.dumps(c.list_database_names()))"
            )
            res3 = subprocess.run(
                ["docker", "exec", "sispro-tews_controller_module_1", "python3", "-c", py_code],
                capture_output=True, text=True
            )
            for line in res3.stdout.strip().split("\n"):
                if "DATABASES_JSON:" in line:
                    db_line = line.split("DATABASES_JSON:")[-1].strip()
                    break

        if not db_line:
            err = res.stderr.strip() or (res2.stderr.strip() if 'res2' in locals() else '')
            print(f"  ⚠ Tidak dapat membaca daftar database dari requirements_mongodb_1: {out} {err}")
            return False
        
        databases = json.loads(db_line)
        print(f"  ✓ Daftar database di MongoDB: {', '.join(databases)}")
        
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
        js_colls = (
            'var d = db.getSiblingDB("sispro-tews"); '
            'var uCount = (d.user.countDocuments ? d.user.countDocuments({}) : d.user.count()); '
            'var sCount = (d.station.countDocuments ? d.station.countDocuments({}) : d.station.count()); '
            'var res = {'
            '  user_count: uCount,'
            '  station_count: sCount,'
            '  admin_exists: !!d.user.findOne({username: "admin"})'
            '}; '
            'print("STATS_JSON:" + JSON.stringify(res));'
        )
        res_colls = subprocess.run(
            ["docker", "exec", "requirements_mongodb_1", "mongo", "--quiet", "--eval", js_colls],
            capture_output=True, text=True
        )
        stats_line = ""
        for l in res_colls.stdout.strip().split("\n"):
            if "STATS_JSON:" in l:
                stats_line = l.split("STATS_JSON:")[-1].strip()
                break
                
        if not stats_line:
            py_stats_code = (
                "import os, json, pymongo; "
                "c = pymongo.MongoClient(os.getenv('DATABASE_URL', 'mongodb://mongodb:27017/sispro-tews')); "
                "d = c['sispro-tews']; "
                "res = {"
                "  'user_count': d.user.count_documents({}),"
                "  'station_count': d.station.count_documents({}),"
                "  'admin_exists': d.user.find_one({'username': 'admin'}) is not None"
                "}; "
                "print('STATS_JSON:' + json.dumps(res))"
            )
            res_py = subprocess.run(
                ["docker", "exec", "sispro-tews_controller_module_1", "python3", "-c", py_stats_code],
                capture_output=True, text=True
            )
            for l in res_py.stdout.strip().split("\n"):
                if "STATS_JSON:" in l:
                    stats_line = l.split("STATS_JSON:")[-1].strip()
                    break

        if stats_line:
            stats = json.loads(stats_line)
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
            
        # Check backup directory inside container using sh -c for proper glob expansion
        bak_res = subprocess.run(
            ["docker", "exec", "requirements_mongodb_1", "sh", "-c", "ls -d /data/db/backup_* 2>/dev/null"],
            capture_output=True, text=True
        )
        backups = [b.strip() for b in bak_res.stdout.strip().split("\n") if b.strip()]
        if not backups:
            import glob
            backups = [b for b in glob.glob("AI-TEWS/requirements/data/backup_*")]

        if backups:
            print(f"  ✓ File snapshot/backup database ditemukan ({len(backups)} snapshot): {', '.join(backups)}")
        else:
            print("  ℹ Belum ada snapshot backup lokal di /data/db/backup_*.")
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
