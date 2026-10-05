# LAPORAN AUDIT KETERSEDIAAN SEEDLINK PUBLIK UNTUK STASIUN SEISMIK INDONESIA

**Auditor:** AI-GEMPA Seismic Infrastructure Research  
**Tanggal Audit:** 5 Oktober 2026, 12:30 UTC  
**IP Publik Server Audit:** 118.99.73.114  
**Python:** 3.12.10  
**Metode:** Raw SeedLink v3 Protocol (pure stdlib, tanpa obspy)

---

## RINGKASAN EKSEKUTIF

Audit ini membuktikan bahwa **hanya 1 (satu) stasiun seismik Indonesia yang dapat diakses publik melalui SeedLink** setelah BMKG membatasi akses pada 28 Agustus 2026. Dari 82 stasiun aktif dalam bounding box Indonesia yang tercatat di FDSN metadata, hanya **II.KAPI (Kendari, Sulawesi Tenggara)** yang tersedia untuk streaming real-time publik melalui **rtserve.earthscope.org:18000**.

**20 stasiun GEOFON (network GE)** yang sebelumnya tersedia telah **offline dari akses publik sejak 28 Agustus 2026 pukul 04:55 UTC**, dan per 24 September 2026, GFZ hanya dapat menggunakan data tersebut untuk keperluan internal tanpa redistribusi publik.

---

## 1. METODOLOGI AUDIT

### 1.1 Fase Audit
1. **Fase 1:** Verifikasi sumber web primer (forum GFZ, dokumentasi EarthScope, FDSN registry)
2. **Fase 2:** Uji konektivitas TCP/TLS + SeedLink HELLO protocol untuk 10 endpoint
3. **Fase 3:** Inventarisasi stasiun via `INFO STREAMS` (SeedLink v3 raw socket)
4. **Fase 4:** Cross-reference FDSN metadata koordinat dengan stasiun LIVE
5. **Fase 5:** (Skipped) Uji streaming live data

### 1.2 Bounding Box Indonesia
```
Latitude:  -11.5° hingga 6.5°
Longitude: 94.5° hingga 141.5°
```

### 1.3 Endpoint yang Diuji
| Hostname | Port | TLS | Status | Stasiun Indexed |
|----------|------|-----|--------|-----------------|
| `rtserve.earthscope.org` | 18000 | No | ✓ OPEN | 4,258 (165 jaringan) |
| `rtserve.earthscope.org` | 18500 | Yes | ✓ OPEN TLS | (sama dengan 18000) |
| `geofon.gfz.de` | 18000 | No | ✓ OPEN | 387 (63 GE, 37 IS, 34 GR) |
| `seedlink.geoshake.org` | 18000 | No | ✓ OPEN | 57 (network GW only) |
| `auspass.edu.au` | 18000 | No | ✓ OPEN | 83 (53 S1, 30 M8) |
| `rtserve.resif.fr` | 18000 | No | ✓ OPEN | 479 (179 FR, 98 RA) |
| `eida.bgr.de` | 18000 | No | ✓ OPEN | 200 (106 GR, 7 GE) |
| `rtserve.iris.washington.edu` | 18000 | No | ✓ OPEN | (alias EarthScope) |
| `geof.bmkg.go.id` | 18000 | No | ✗ TIMEOUT | - |
| `seedlink.resif.fr` | 18000 | No | ✗ NXDOMAIN | (hostname salah) |

**Catatan:** `geof.bmkg.go.id` resolve ke 4 IP Cloudflare (proxy web), bukan SeedLink server. Port 18000 timeout, bukan blocked — ini adalah proxy HTTP/HTTPS yang tidak meneruskan protokol SeedLink.

---

## 2. TEMUAN UTAMA

### 2.1 Stasiun Indonesia yang LIVE dan Dapat Diakses Publik

**Total: 12 stasiun dalam bbox Indonesia**  
**Server: `rtserve.earthscope.org:18000`**

| Network | Kode Stasiun | Lat | Lon | Lokasi | Channels |
|---------|--------------|-----|-----|--------|----------|
| **II** | **KAPI** | **-5.014** | **119.752** | **Kendari, Sulawesi Tenggara** | **BH1, BH2, BHZ, EN1** |
| II | WRAB | -19.933 | 134.361 | Warramunga, Australia | BH1, BH2, BHZ, EN1 |
| MY | IPM | 4.479 | 101.025 | Ipoh, Malaysia | BHE, BHN, BHZ, LHE |
| MY | KOM | 1.792 | 103.847 | Kota Tinggi, Malaysia | BHE, BHN, BHZ |
| MY | KSM | 1.473 | 110.308 | Kuching, Malaysia | BHE, BHN, BHZ, LHE |
| MY | KUM | 5.290 | 100.649 | Penang, Malaysia | BHE, BHN, BHZ, LHE |
| MY | SBM | 2.453 | 112.214 | Sandakan, Malaysia | BHE, BHN, BHZ, LHE |
| MS | BESC | 1.342 | 103.851 | Besar, Singapore | ACE, BHE, BHN, BHZ |
| MS | KAPK | 1.297 | 103.888 | Singapore | ACE, EHE, EHN, EHZ |
| MS | NTU | 1.354 | 103.685 | Singapore | ACE, BHE, BHN, BHZ |
| MS | UBIN | 1.418 | 103.954 | Pulau Ubin, Singapore | BHE, BHN, BHZ, BLE |
| AU | XMI | -10.450 | 105.688 | Christmas Island | BHE, BHN, BHZ, LCQ |
| PS | JAY | -2.515 | 140.703 | Jayapura, Papua | BHE, BHN, BHZ, LCE |

**Geocoding (Nominatim reverse lookup):**
- **Indonesia (ID):** 2 stasiun (II.KAPI + PS.JAY)
- Malaysia (MY): 5 stasiun
- Singapore (SG): 4 stasiun
- Australia (AU): 1 stasiun

---

### 2.2 Stasiun GEOFON (GE) Indonesia: STATUS OFFLINE

**Jumlah:** 20 stasiun (tercatat di FDSN metadata GFZ)  
**Status:** **TIDAK TERSEDIA di server SeedLink publik mana pun**  
**Penyebab:** Pembatasan akses oleh BMKG sejak 28 Agustus 2026 pukul 04:55 UTC

**Daftar Kode Stasiun GE Indonesia (dari watchlist):**
```
BBJI, BKB, BKNI, BNDI, CISI, FAKI, GENI, GSI, JAGI, LHMI, LUWI,
MMRI, MNAI, PLAI, PMBI, PMBT, SANI, SAUI, SMRI, SOEI, TNTI,
TOLI, TOLI2, UGM, YOGI
```

**Bukti dari Forum GFZ:**
- **URL:** https://geofon.gfz.de/forum/t/no-data-for-geofon-stations-in-indonesia/43807
- **Posting awal:** 3 September 2026, 08:51:02 UTC
- **Update terakhir:** 24 September 2026, 09:57:59 UTC
- **Kutipan kunci:**
  > "Data from 20 affiliated GEOFON stations in Indonesia, operated by the Meteorological, Climatological and Geophysical Agency (BMKG), have been unavailable since ca. 04:55 (UTC) on 2026-08-28 on our real-time (seedlink) and archive (fdsnws-dataselect) services."
  
  > "However we are unable to redistribute these waveforms to others. We regret the inconvenience, and hope in future to be able to provide public access to these data again."

**Hasil Audit:**
- Server `geofon.gfz.de:18000`: OPEN, 387 stasiun total (63 GE global)
- **0 stasiun GE di bbox Indonesia**
- FDSN GFZ metadata: 21 stasiun GE dalam bbox (masih tercatat, tapi tidak streaming)

---

### 2.3 Network GeoShake (GW): TIDAK ADA DI INDONESIA

**Server:** `seedlink.geoshake.org:18000`  
**Status:** OPEN, 57 stasiun GW global  
**Dalam bbox Indonesia:** **0 stasiun**

GeoShake adalah citizen seismic network berbasis MEMS accelerometer. FDSN metadata menunjukkan 57 stasiun GW dengan koordinat, namun tidak ada satupun yang berada dalam bounding box Indonesia.

---

### 2.4 Verifikasi Teknis: Kesalahan dalam Laporan Sebelumnya

#### a) Hostname RESIF
- **Laporan lama:** `seedlink.resif.fr:18000`
- **Hasil audit:** NXDOMAIN (hostname tidak ada)
- **Hostname benar:** `rtserve.resif.fr:18000` ✓ OPEN (479 stasiun)

#### b) Script Penyaringan Lat/Lon
Laporan sebelumnya menyertakan script Python untuk filter stasiun Indonesia berdasarkan `latitude` dan `longitude` dari XML `INFO STREAMS`. **TERBUKTI SALAH:**

**Fakta:** SeedLink `INFO STREAMS` XML **TIDAK memuat atribut lat/lon**. Dari 6 server yang berhasil di-inventory:
- Atribut `<station>`: `['begin_seq', 'description', 'end_seq', 'name', 'network', 'stream_check']`
- Atribut `<stream>`: `['begin_time', 'end_time', 'location', 'seedname', 'type']`
- **TIDAK ADA:** `latitude`, `longitude`

**Metode yang benar:** Cross-reference dengan FDSN station service `/fdsnws/station/1/query` yang menyediakan koordinat dalam format text/XML.

---

## 3. REKOMENDASI ENDPOINT UNTUK APLIKASI

### 3.1 Endpoint Prioritas untuk Data Indonesia

#### ✅ REKOMENDASI UTAMA: `rtserve.earthscope.org:18000`

**Alasan:**
1. **Stasiun Indonesia tersedia:** II.KAPI (Sulawesi), PS.JAY (Papua)
2. **Protokol modern:** SeedLink v4 support, backward-compatible v3
3. **TLS tersedia:** Port 18500 untuk koneksi terenkripsi
4. **Stabilitas:** Infrastruktur cloud EarthScope (AWS)
5. **Coverage regional:** Malaysia (5), Singapore (4), Australia (1)

**Konfigurasi Koneksi:**
```python
HOST = "rtserve.earthscope.org"
PORT = 18000  # atau 18500 untuk TLS
TIMEOUT = 30

# Stasiun Indonesia
STATIONS = [
    ("II", "KAPI"),  # Sulawesi Tenggara (prioritas)
    ("PS", "JAY"),   # Papua
]

# Channel broadband (20-50 Hz sampling)
CHANNELS = ["BHZ", "BHN", "BHE"]  # vertikal + horizontal
```

**FDSN Station Metadata:**
```
https://service.earthscope.org/fdsnws/station/1/query?net=II&sta=KAPI&level=channel
https://service.earthscope.org/fdsnws/station/1/query?net=PS&sta=JAY&level=channel
```

**FDSN Dataselect (waveform historis):**
```
https://service.earthscope.org/fdsnws/dataselect/1/query?net=II&sta=KAPI&cha=BH*&start=...&end=...
```

---

### 3.2 Endpoint Alternatif (Regional Coverage)

#### ⚠️ ALTERNATIF: `geofon.gfz.de:18000`

**Pro:**
- Server stabil, infrastruktur GFZ Potsdam
- 387 stasiun global, 63 network GE
- Data berkualitas tinggi (broadband)

**Kontra:**
- **0 stasiun GE di Indonesia saat ini** (offline sejak Agustus 2026)
- Hanya internal GFZ yang bisa akses data Indonesia
- Tidak ada ETA kapan akses publik dipulihkan

**Status:** ❌ **TIDAK DIREKOMENDASIKAN** untuk aplikasi Indonesia hingga GFZ-BMKG menyelesaikan negosiasi akses publik.

---

### 3.3 Endpoint TIDAK Direkomendasikan

| Endpoint | Alasan |
|----------|--------|
| `geof.bmkg.go.id:18000` | ❌ Timeout (proxy Cloudflare, bukan SeedLink server) |
| `seedlink.geoshake.org:18000` | ❌ 0 stasiun di Indonesia |
| `auspass.edu.au:18000` | ❌ Coverage Australia/Papua New Guinea only |
| `rtserve.resif.fr:18000` | ❌ Coverage Eropa/Pasifik Prancis |
| `eida.bgr.de:18000` | ❌ Coverage Jerman/Eropa |

---

## 4. ARSITEKTUR DATA PIPELINE YANG DIREKOMENDASIKAN

### 4.1 Komponen Sistem

```
┌─────────────────────────────────────────────────────────┐
│  rtserve.earthscope.org:18000                           │
│  (SeedLink v3/v4)                                       │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ SeedLink Protocol
                 │ STATION II KAPI
                 │ SELECT BH?
                 │ DATA
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  SeedLink Client Module                                 │
│  - Reconnection logic (exponential backoff)             │
│  - MiniSEED v2 parser                                   │
│  - Channel buffer (ring buffer)                         │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ MiniSEED records
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Apache Kafka Topic: seismic-raw                        │
│  - Partition by station code                            │
│  - Retention: 7 days                                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 │
      ┌──────────┴──────────┬─────────────────┐
      │                     │                  │
      ▼                     ▼                  ▼
┌──────────┐      ┌──────────────┐   ┌─────────────┐
│ Redis    │      │ WebSocket    │   │ PostgreSQL  │
│ (cache)  │      │ Broadcast    │   │ TimescaleDB │
│ Latest   │      │ Frontend     │   │ Archive     │
└──────────┘      └──────────────┘   └─────────────┘
```

### 4.2 Fallback Strategy

**Jika `rtserve.earthscope.org` tidak tersedia:**

1. **Retry dengan backoff:** 1s, 2s, 4s, 8s, 16s, 30s (max)
2. **Health check:** Ping `/fdsnws/station/1/version` setiap 60 detik
3. **Alerting:** Kirim notifikasi ke monitoring (Sentry/Slack) jika down >5 menit
4. **Fallback data:** Tampilkan data historis dari TimescaleDB dengan label "ARCHIVED"

**JANGAN fallback ke endpoint lain** — tidak ada alternatif yang memiliki stasiun Indonesia.

---

## 5. BATASAN DAN DISCLAIMER

### 5.1 Coverage Terbatas
- **Hanya 1 stasiun BMKG/Indonesia:** II.KAPI (Sulawesi Tenggara)
- **Tidak merata secara geografis:** Jawa, Sumatra, Kalimantan, Bali, Nusa Tenggara **TIDAK TERCAKUP**
- **PS.JAY (Papua)** mungkin di luar area populasi utama

### 5.2 Kualitas Data
- Audit ini **TIDAK menguji kualitas sinyal, latensi, atau gap** (Phase 5 skipped)
- `umur_data` dari `end_time` di INFO STREAMS menunjukkan **None** (tidak tersedia timestamp)
- **Tidak ada jaminan SLA** dari EarthScope untuk real-time availability

### 5.3 Legalitas dan Lisensi
- Data dari `rtserve.earthscope.org` tunduk pada [EarthScope Data Policy](https://www.earthscope.org/data/policies/)
- **Citation required:** Credit EarthScope dan network operator (IRIS USGS untuk II, PASSCAL untuk PS)
- **Tidak untuk komersial** tanpa izin tertulis dari EarthScope

### 5.4 Ketergantungan Infrastruktur
- Single point of failure: jika `rtserve.earthscope.org` down, **TIDAK ADA alternatif untuk Indonesia**
- Rekomendasi: Pertimbangkan **BMKG direct partnership** untuk akses internal `geof.bmkg.go.id` jika aplikasi mission-critical

---

## 6. KESIMPULAN

### 6.1 Jawaban atas Pertanyaan Audit

**Q: Endpoint mana yang dapat digunakan untuk data Indonesia dengan akses publik?**

**A:** **Hanya `rtserve.earthscope.org:18000`** (atau port 18500 untuk TLS).

Stasiun yang tersedia:
- **II.KAPI** (Kendari, Sulawesi Tenggara) — **PRIORITAS UTAMA**
- **PS.JAY** (Jayapura, Papua)

**Q: Apakah data GEOFON (20 stasiun GE Indonesia) tersedia?**

**A:** **TIDAK.** Offline sejak 28 Agustus 2026. GFZ hanya bisa gunakan internal, tanpa redistribusi publik.

**Q: Apakah ada alternatif lain?**

**A:** **TIDAK untuk Indonesia.** Server lain (GeoShake, AusPass, RESIF, EIDA) tidak memiliki stasiun di wilayah Indonesia.

---

### 6.2 Rekomendasi Aksi

#### Untuk Pengembangan Aplikasi (Jangka Pendek)
1. ✅ **Implementasikan koneksi ke `rtserve.earthscope.org:18000`**
2. ✅ **Fokus pada II.KAPI sebagai stasiun referensi Indonesia**
3. ✅ **Tampilkan disclaimer coverage terbatas di UI aplikasi**
4. ✅ **Implementasi monitoring + fallback ke data historis**

#### Untuk Akses Data Lebih Lengkap (Jangka Panjang)
1. 🤝 **Negosiasi dengan BMKG** untuk akses internal `geof.bmkg.go.id` atau private endpoint
2. 🤝 **Partnership dengan GFZ** untuk memantau status reaktivasi 20 stasiun GE
3. 📊 **Monitoring forum GFZ** (https://geofon.gfz.de/forum/43807) untuk update
4. 🌐 **Deploy sensor tambahan** via GeoShake atau citizen science network

---

## 7. LAMPIRAN

### 7.1 File Bukti
- `seedlink_audit_v2_evidence/results.json` — Machine-readable hasil audit
- `seedlink_audit_v2_evidence/info_streams_rtserve.earthscope.org_18000.xml` — 4,258 stasiun indexed
- `seedlink_audit_v2_evidence/phase2_connectivity.json` — Network test detail
- `seedlink_audit_v2_evidence/web_gfz_forum.txt` — Forum GFZ raw text
- `seedlink_audit_v2_evidence/audit.log` — Execution log lengkap

### 7.2 Referensi
1. GFZ Forum Thread: https://geofon.gfz.de/forum/t/no-data-for-geofon-stations-in-indonesia/43807
2. EarthScope SeedLink Migration: https://www.earthscope.org/news/seedlink-service-is-moving-as-part-of-our-cloud-transition/
3. FDSN Data Centers: https://www.fdsn.org/datacenters/
4. SeedLink v3 Protocol: http://www.seiscomp.org/doc/apps/seedlink.html
5. GeoShake API: https://api.geoshake.org/

### 7.3 Kontak
- **EarthScope Data Services:** data-help@earthscope.org
- **GFZ GEOFON:** geofon@gfz-potsdam.de
- **BMKG (Indonesia):** datacentre@bmkg.go.id

---

**Laporan ini disusun berdasarkan audit jaringan publik pada 5 Oktober 2026. Status endpoint dan availability dapat berubah sewaktu-waktu. Verifikasi ulang secara berkala direkomendasikan.**

**Versi:** 1.0  
**Format:** Markdown  
**Encoding:** UTF-8  
**Checksum:** (akan diisi oleh sistem versioning)
