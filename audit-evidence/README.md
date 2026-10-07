# Audit Evidence Repository

Struktur bukti eksekusi audit SeedLink infrastruktur Indonesia. Setiap folder timestamp = satu eksekusi lengkap.

## Struktur Folder

```
audit-evidence/
└── 20261007/                          # Audit date: 7 Oktober 2026
    ├── SEEDLINK_AUDIT_20261007.md     # Laporan lengkap 490 baris
    ├── L1_earthscope/                 # Phase 1-5: KAPI + JAY inventory & streaming
    ├── E1_datacenters/                # Experiment 1: FDSN datacenter discovery
    ├── E2_stations/                   # Experiment 2: Station bbox Indonesia
    ├── E4_E5_archive/                 # Experiment 4-5: GE archive + BMKG catalog
    └── E6_github/                     # Experiment 6: GitHub repo scan
```

## Eksekusi 20261007

**Tanggal:** 2026-10-07 01:19-01:29 UTC  
**Python:** 3.11.16  
**Host:** Windows 11, Git Bash MSYS  

### L1_earthscope (8.2 MB)
- `audit.log`: Execution log fase 1-5
- `info_streams_*.xml`: SeedLink INFO STREAMS output (6 servers)
- `phase2_connectivity.json`: TCP connectivity test results

**Command:**
```bash
python seedlink_audit.py --skip-web --geocode --live-seconds 90 \
  --live "rtserve.earthscope.org:18000|II|KAPI|BH?,EN?" \
  --live "rtserve.earthscope.org:18000|PS|JAY|BH?,LH?"
```

**Hasil:**
- II.KAPI: lat -5.88, lon 119.34, umur_data 18.8s → LIVE
- PS.JAY: lat -2.51, lon 140.70, umur_data 145s → LIVE
- Phase 5 streaming timeout 90s (mseed tidak tersimpan)

### E1_datacenters (9.0 MB)
- FDSN datacenter registry query
- Temuan: 6 datacenters (EarthScope, IRIS, GEOFON, RESIF, BGR, AusPass)

**Command:**
```bash
python indonesia_experiments.py e1 --geocode
```

### E2_stations (182 KB)
- Station inventory bbox Indonesia (-11.5° to 6.5°, 94.5° to 141.5°)
- Temuan: 2 stasiun Indonesia (II.KAPI, PS.JAY), 0 network IA

**Command:**
```bash
python indonesia_experiments.py e2 --geocode
```

### E4_E5_archive (28 KB)
- `experiments_results.json`: E4 (GE archive HTTP test) + E5 (BMKG catalog polling)

**E4 Hasil:**
- GE.BKB pra-28Aug: HTTP 200
- GE.BKB pasca-28Aug: HTTP 403
- JAY latency: 145s

**E5 Hasil:**
- Katalog BMKG: max-age 60s
- Polling recommendation: 30-60s

**Command:**
```bash
python indonesia_experiments.py e4 e5
```

### E6_github (28 KB)
- `experiments_results.json`: GitHub repo scan untuk SeedLink clients
- `audit.log`: Execution log

**Temuan:**
- Rust client: `seedlink-rs`
- WebSocket endpoint: `inatews.bmkg.go.id`
- FDSN docs: `docs.fdsn.org`, `ds.iris.edu`

**Command:**
```bash
python indonesia_experiments.py e6
```

## Navigasi Cepat

| Item | Path |
|---|---|
| **Laporan Lengkap** | `20261007/SEEDLINK_AUDIT_20261007.md` |
| **Stasiun KAPI/JAY XML** | `20261007/L1_earthscope/info_streams_rtserve.earthscope.org_18000.xml` |
| **E1-E6 JSON Results** | `20261007/E{1,2,4,6}_*/experiments_results.json` |
| **Execution Logs** | `20261007/*/audit.log` |

## Regenerate Audit

```bash
# L1: Inventory + streaming test
python seedlink_audit.py --skip-web --geocode --live-seconds 90 \
  --live "rtserve.earthscope.org:18000|II|KAPI|BH?,EN?" \
  --live "rtserve.earthscope.org:18000|PS|JAY|BH?,LH?"

# L2: Experiments
python indonesia_experiments.py e1 e2 e3 --geocode
python indonesia_experiments.py e4 e5
python indonesia_experiments.py e6

# Move results
mkdir -p audit-evidence/$(date +%Y%m%d)/{L1_earthscope,E1_datacenters,E2_stations,E4_E5_archive,E6_github}
cp -r ~/seedlink_audit/$(date +%Y%m%d)_*/* audit-evidence/$(date +%Y%m%d)/
```

## Changelog

- **20261007:** Initial audit with 3-layer endpoint guide (Event/Waveform/Metadata)
- **Next:** 20261020 (planned monthly refresh)
