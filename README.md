# AI-GEMPA BMKG: SeedLink Infrastructure Audit

Audit infrastruktur SeedLink untuk akses data waveform seismik Indonesia. Dokumentasi lengkap sumber data real-time stasiun seismik pasca-restriksi BMKG 28 Agustus 2026.

## Project Structure

```
ai-gempa-bmkg/
├── scripts/              # Audit scripts (seedlink_audit.py, indonesia_experiments.py)
├── tests/                # Unit tests untuk SeedLink connectivity
├── docs/                 # Audit reports & documentation
├── audit-evidence/       # Versioned execution results (20261007, 20261015, ...)
├── archive/              # Old logs & deprecated evidence folders
├── sispro-tews/          # AI-TEWS pipeline (SeedLink → Kafka → Redis → WebSocket)
└── README.md             # This file
```

## Quick Start

### 1. Run Full Audit (L1 + E1-E6)

```bash
# L1: KAPI + JAY inventory & streaming
python scripts/seedlink_audit.py --skip-web --geocode --live-seconds 90 \
  --live "rtserve.earthscope.org:18000|II|KAPI|BH?,EN?" \
  --live "rtserve.earthscope.org:18000|PS|JAY|BH?,LH?"

# E1-E6: Experiments
python scripts/indonesia_experiments.py e1 e2 e3 e4 e5 e6 --geocode

# Organize results
mkdir -p audit-evidence/$(date +%Y%m%d)/{L1_earthscope,E1_datacenters,E2_stations,E4_E5_archive,E6_github}
cp -r ~/seedlink_audit/$(date +%Y%m%d)_*/* audit-evidence/$(date +%Y%m%d)/
```

### 2. Read Latest Audit Report

```bash
cat docs/SEEDLINK_AUDIT_20261005.md
# or
cat audit-evidence/20261007/SEEDLINK_AUDIT_20261007.md
```

## Key Findings

**Stasiun Indonesia LIVE (Public Access):**
- **II.KAPI** (Kappang, Sulawesi): `-5.88°, 119.34°`, 100 Hz, latency 18.8s
- **PS.JAY** (Jayapura, Papua): `-2.51°, 140.70°`, 100 Hz, latency 145s

**Endpoint:** `rtserve.earthscope.org:18000` (or `:18500` TLS)

**Stasiun Offline:**
- 20 stasiun GE (GEOFON/BMKG) offline sejak 28 Agustus 2026
- Arsip pra-28Agu masih accessible (HTTP 200) untuk training

**3-Layer Data Infrastructure:**
1. **Event Catalog:** `earthquake.bmkg.go.id/catalog/api17/` (60s polling)
2. **Waveform Stream:** `rtserve.earthscope.org:18000` (real-time)
3. **Station Metadata:** FDSN `service.earthscope.org/fdsnws/station/1/` (daily sync)

## Dependencies

**Core:** Python 3.11+ (stdlib only)

**Optional:**
```bash
pip install obspy requests
```

## Documentation

- **Audit Reports:** `docs/SEEDLINK_AUDIT_*.md`
- **Scripts Guide:** `scripts/README.md`
- **Evidence Index:** `audit-evidence/README.md`
- **Deployment:** `docs/DEPLOYMENT_GUIDE.md`

## Usage Scenarios

### Scenario 1: Validasi AI Detection vs BMKG Catalog
```bash
# Poll catalog setiap 60s
curl "https://earthquake.bmkg.go.id/catalog/api17/?limit=100&offset=0" > bmkg_events.json

# Compare dengan AI picks: timestamp ±30s window
# Log false positives, missed events, magnitude bias
```

### Scenario 2: Auto-discovery Stasiun Baru
```bash
# Daily cron: FDSN bbox Indonesia
curl "https://service.earthscope.org/fdsnws/station/1/query?minlatitude=-11.5&maxlatitude=6.5&minlongitude=94.5&maxlongitude=141.5&level=station" > stations.xml

# Diff dengan station_indonesia.csv
# Alert jika koordinat berubah >1 km atau stasiun baru muncul
```

### Scenario 3: Backup Arsip GE (Pre-28Aug)
```bash
# Download GE.BKB historical 2016-2026-08-27
for date in $(seq 2016 2026); do
  curl "https://service.geofon.gfz-potsdam.de/fdsnws/dataselect/1/query?network=GE&station=BKB&starttime=${date}-01-01&endtime=${date}-12-31" > GE_BKB_${date}.mseed
done

# Use untuk PhaseNet training offline
```

## Roadmap

**Phase 1 (Week 1):** Configure KAPI+JAY dual-station, start BMKG catalog polling  
**Phase 2 (Month 1):** FDSN daily sync, A/B test EarthScope vs BMKG WebSocket  
**Phase 3 (Month 3):** AI validation loop, PhaseNet tuning, fallback logic  

## Risk Mitigation

| Risiko | Severity | Mitigasi |
|---|---|---|
| EarthScope outage | HIGH | Fallback BMKG WebSocket |
| BMKG policy shift | MEDIUM | Monitor announcements, pre-download backup |
| GEOFON arsip removal | MEDIUM | Backup 100 GB GE data dalam 6 bulan |
| Latency >5 min | MEDIUM | Dual-feed validation |

## Contributing

**Monthly Audit Schedule:**  
7 Oktober, 7 November, 7 Desember (setiap tanggal 7).

**Workflow:**
1. Run `seedlink_audit.py` + `indonesia_experiments.py`
2. Organize ke `audit-evidence/YYYYMMDD/`
3. Update `docs/SEEDLINK_AUDIT_YYYYMMDD.md`
4. Commit + push

## License

Internal BMKG research project.

## Contact

**Auditor:** AI-GEMPA Seismic Infrastructure Team  
**Last Audit:** 2026-10-07 UTC  
**Next Audit:** 2026-11-07 (planned)
