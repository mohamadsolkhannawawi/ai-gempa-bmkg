# SeedLink Audit Scripts & Station Configuration

Skrip Python untuk audit infrastruktur SeedLink Indonesia. Semua script standalone, hanya butuh stdlib Python 3.11+.

## Current Station Configuration

**Active Deployment:** 20 seismic stations dari `rtserve.earthscope.org:18000` (IRIS EarthScope - single endpoint)

**Station List** (sispro-tews/seedlink_module/data/station_public20.csv):
- PS.JAY (Indonesia)
- MS.KAPK, MS.BESC, MS.UBIN, MS.NTU (Singapore)
- II.KAPI (Indonesia)
- IU.DAV (Philippines)
- AU.XMI, AU.DRS, AU.DPH, AU.KDU, AU.MTN, AU.COEN, AU.DERBY, AU.ARMA (Australia)
- TM.SKLT, TM.SRIT, TM.SURA (Thailand)
- S1.AUNHS (Australia)
- IN.PBA (India)

**Coverage:** Indonesia + SE Asia + Australia + India region. All channels BH*/HH* (broadband seismic).

**Data Flow:** SeedLink → seedlink_module → Kafka `waveform_seedlink` → p-pick_module → association → locmag → MongoDB events

---

## Core Scripts

### seedlink_audit.py
Audit 5-fase lengkap: connectivity → inventory → live streaming → metadata.

**Usage:**
```bash
python seedlink_audit.py --skip-web --geocode --live-seconds 90 \
  --live "rtserve.earthscope.org:18000|II|KAPI|BH?,EN?" \
  --live "rtserve.earthscope.org:18000|PS|JAY|BH?,LH?"
```

**Output:** `~/seedlink_audit/YYYYMMDD_HHMMSS/` (XML, JSON, logs, mseed)

**Phases:**
1. TCP connectivity (HELLO handshake)
2. INFO STREAMS (inventory parsing)
3. Live latency check (umur_data calculation)
4. FDSN metadata query (coordinates, channels)
5. Streaming test (mseed recording)

---

### indonesia_experiments.py
Eksperimen E1-E6 untuk validasi klaim audit.

**Usage:**
```bash
# E1: FDSN datacenter discovery
python indonesia_experiments.py e1 --geocode

# E2: Station bbox Indonesia
python indonesia_experiments.py e2 --geocode

# E3: WebSocket endpoint test
python indonesia_experiments.py e3

# E4: Archive HTTP test (GE pre/post 28Aug)
python indonesia_experiments.py e4

# E5: BMKG catalog polling
python indonesia_experiments.py e5

# E6: GitHub repo scan (SeedLink clients)
python indonesia_experiments.py e6

# Run all
python indonesia_experiments.py e1 e2 e3 e4 e5 e6 --geocode
```

**Output:** `~/seedlink_audit/exp_YYYYMMDD_HHMMSS/experiments_results.json`

---

### seedlink_audit_kedua.py
SeedLink v3 raw socket implementation (no obspy dependency).

**Usage:**
```bash
python seedlink_audit_kedua.py
```

**Catatan:** Alternatif untuk seedlink_audit.py, digunakan jika obspy error `'<' float vs None`.

---

### explore_indonesia_stations.py
FDSN bounding box query + reverse geocoding untuk discovery stasiun Indonesia.

**Usage:**
```bash
python explore_indonesia_stations.py --bbox -11.5,6.5,94.5,141.5 --geocode
```

**Output:** List stasiun (network, code, lat, lon, country, channels)

---

## Dependencies

**Required:** Python 3.11+ (stdlib only)

**Optional:**
- `obspy` (untuk seedlink_audit.py Phase 5 streaming)
- `requests` (untuk HTTP experiments E4-E6)
- Internet connection (FDSN API, reverse geocoding)

**Install optional:**
```bash
pip install obspy requests
```

---

## Quick Start

**1. Audit KAPI + JAY:**
```bash
python scripts/seedlink_audit.py --skip-web --geocode --live-seconds 90 \
  --live "rtserve.earthscope.org:18000|II|KAPI|BH?,EN?" \
  --live "rtserve.earthscope.org:18000|PS|JAY|BH?,LH?"
```

**2. Run experiments:**
```bash
python scripts/indonesia_experiments.py e1 e2 e4 e5 e6 --geocode
```

**3. Organize results:**
```bash
mkdir -p audit-evidence/$(date +%Y%m%d)/{L1_earthscope,E1_datacenters,E2_stations,E4_E5_archive,E6_github}
cp -r ~/seedlink_audit/$(date +%Y%m%d)_*/* audit-evidence/$(date +%Y%m%d)/
```

---

## Output Structure

```
~/seedlink_audit/
├── 20261007_011921/          # L1 results
│   ├── audit.log
│   ├── info_streams_*.xml
│   ├── phase2_connectivity.json
│   └── *.mseed (if streaming succeeds)
└── exp_20261007_012911/      # E1-E6 results
    ├── audit.log
    └── experiments_results.json
```

---

## Troubleshooting

**Error: `'<' not supported between float and NoneType`**
→ Use `seedlink_audit_kedua.py` (raw socket, no obspy)

**Error: `TIMEOUT` on Phase 5**
→ Reduce `--live-seconds` (default 120 → try 60-90)

**Error: `0 stations in bbox`**
→ Verify FDSN API reachable: `curl https://service.earthscope.org/fdsnws/station/1/query?minlatitude=-11.5`

**Error: `DNS NXDOMAIN`**
→ Check hostname typos (e.g., `seedlink.resif.fr` → `rtserve.resif.fr`)

---

## Related

- **Audit Reports:** `../docs/SEEDLINK_AUDIT_*.md`
- **Evidence:** `../audit-evidence/YYYYMMDD/`
- **Tests:** `../tests/test_*.py`
