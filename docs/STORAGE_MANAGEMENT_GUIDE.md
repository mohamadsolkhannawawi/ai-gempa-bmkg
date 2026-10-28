# Panduan Manajemen Penyimpanan & Pembersihan Data Otomatis (Storage Retention & Cleanup)
## AI-GEMPA-BMKG — Server riset-01

**Spesifikasi Server Target:**
- **Host:** `bmkg@riset-01` (152.118.31.54)
- **CPU:** 16 Cores 3.0 GHz
- **RAM:** 64 GB
- **Storage:** 2 TB (NVMe/SSD)
- **GPU Memory:** 8 GB

---

## 1. Analisis Sistem Penyimpanan Data Saat Ini

Saat aplikasi AI-GEMPA-BMKG dideploy di `riset-01`, terdapat 5 jenis data yang disimpan dan diakumulasikan ke disk:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ALIRAN & TITIK PENYIMPANAN DATA                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. WAVEFORM SEISMIC (MiniSEED):                                             │
│    SeedLink Stream ──> Redis ──> archiving_module ──> /mnt/archive/*.mseed │
│    [PERTUMBUHAN CEPAT: ~3-6 GB/hari, tidak pernah dihapus otomatis]         │
│                                                                             │
│ 2. DOCKER CONTAINER LOGS:                                                   │
│    20+ Kontainer stdout/stderr ──> /var/lib/docker/containers/*-json.log    │
│    [PENYEBAB UTAMA 100%: Default docker tanpa limit ukuran log (bisa 100GB)]│
│                                                                             │
│ 3. APPLICATION LOGS:                                                        │
│    seedlink.log, archiving.log, logs_controller_YYYY-MM-DD.log, dockerd.log│
│    [PERTUMBUHAN HARIAN: File log teks di ./logs/ yang terus membesar]       │
│                                                                             │
│ 4. DOCKER BUILD & OVERLAY CACHE:                                            │
│    docker-compose build ──> /var/lib/docker/overlay2/ + buildkit cache       │
│    [PERTUMBUHAN INTERMITTENT: Dangling layers dari proses rebuild/restart]  │
│                                                                             │
│ 5. DATABASE MONGODB (sispro-tews):                                          │
│    picks (AI detections), events (katalog gempa) ──> ./data/db              │
│    [PERTUMBUHAN SEDANG: Ratusan ribu picks per minggu]                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Mengapa Storage di `riset-01` Mencapai 100%?
1. **Docker Container Log Explosion**: Docker default menggunakan driver `json-file` tanpa batas `max-size`. Ketika ada 20+ kontainer aktif (Kafka, Redis, SeedLink, Archiving replicas, P-Pick AI, dll.) yang melakukan logging ribuan baris per menit, file `*-json.log` dapat memakan puluhan hingga ratusan gigabytes.
2. **MiniSEED Archive Menumpuk Tanpa Batas**: `archiving_module` terus menulis file `.mseed` ke `/mnt/archive` setiap hari tanpa ada skrip penghapusan data lama (retention policy).
3. **Log Aplikasi Tidak Di-rotate**: File seperti `archiving.log` dan `seedlink.log` terus di-append dan di-`tail -f`.
4. **Dangling Docker Layers**: Cache build image Docker tidak pernah dibersihkan via `docker system prune`.

---

## 2. Tindakan Darurat (Emergency Recovery) Saat Server 100% Penuh

Jika server saat ini masih dalam kondisi **Disk 100%** (seperti pada monitoring dashboard HPC), jalankan perintah darurat berikut langsung di terminal server `bmkg@riset-01` untuk membebaskan puluhan GB ruang dalam hitungan detik:

### Langkah A: Truncate Docker Container Logs yang Bengkak (Instan Bebas 10–100 GB)
```bash
# Periksa ukuran log container yang memakan disk
sudo du -sh /var/lib/docker/containers/*/*-json.log 2>/dev/null | sort -h | tail -10

# Langsung kosongkan (truncate) semua log container tanpa perlu restart container:
sudo sh -c 'for log in /var/lib/docker/containers/*/*-json.log; do cat /dev/null > "$log"; done'
```

### Langkah B: Prune Docker Build Cache & Dangling Images
```bash
# Hapus image menggantung dan cache build yang tidak digunakan
docker system prune -f

# (Opsional jika masih butuh space banyak, hapus semua image yang sedang tidak aktif):
docker image prune -af
```

### Langkah C: Bersihkan File Log Aplikasi yang Menumpuk
```bash
cd ~/GEMPA/ai-gempa-bmkg
# Truncate log aktif
> sispro-tews/archiving_module/logs/archiving.log 2>/dev/null || true
> sispro-tews/seedlink_module/logs/seedlink.log 2>/dev/null || true
```

### Langkah D: Cek Ulang Penggunaan Disk
```bash
df -h /
```
*Disk usage seharusnya langsung turun di bawah 60–70%.*

---

## 3. Desain Waktu Retensi Ideal untuk Spesifikasi 2 TB

Dengan spesifikasi server: **16 Cores CPU, 64 GB RAM, dan 2 TB Storage**:

| Komponen Data | Estimasi Pertumbuhan | Waktu Retensi Ideal | Alokasi Ruang Maksimal |
|---|---|---|---|
| **Waveform MiniSEED** (`/mnt/archive`) | ~3 - 5 GB / hari (50-100 stasiun) | **90 Hari (3 Bulan)** | **~350 - 500 GB** |
| **Application & Service Logs** | ~50 MB / hari (dengan limit 50m) | **14 Hari (2 Minggu)** | **~5 - 10 GB** |
| **MongoDB Raw Phase Picks** | ~100 MB / hari | **30 Hari (1 Bulan)** | **~5 - 10 GB** |
| **MongoDB Catalog Events** | ~100 KB / hari | **Permanen (Simpan Terus)** | **< 1 GB** |
| **Docker System & Images** | Fixed base images + cache | **Prune berkala (7 hari)** | **~50 - 80 GB** |
| **Free Buffer Keamanan OS & GPU** | - | - | **> 1.2 TB (Aman)** |

> [!NOTE]
> **Mengapa 90 Hari untuk Waveform?**
> Data seismik 90 hari (3 bulan) adalah standar operasional seismologi yang sangat ideal untuk validasi ulang gempa susulan (*aftershocks*) maupun kalibrasi parameter AI. 90 hari hanya mengonsumsi ~25% dari total disk 2 TB, menyisakan margin keselamatan sebesar 75% sehingga server tidak akan pernah mengalami crash *disk full*.
> Jika riset membutuhkan data lebih panjang, Anda dapat mengubahnya ke **180 hari (6 bulan)** via file `.env`.

---

## 4. Konfigurasi Variabel Lingkungan (`.env`)

Semua parameter lama penyimpanan dapat diubah dengan sangat mudah melalui file `.env` di root repository atau `.env.seed`.

Tambahkan atau sesuaikan baris berikut di `.env`:

```env
# =============================================================================
# STORAGE & RETENTION MANAGEMENT (riset-01: 2 TB Storage)
# =============================================================================

# Lokasi direktori arsip waveform MiniSEED
ARCHIVE_LOCATION=/mnt/archive

# Lama penyimpanan arsip MiniSEED dalam hari (Default: 90 hari)
ARCHIVE_RETENTION_DAYS=90

# Lama penyimpanan file log aplikasi dalam hari (Default: 14 hari)
LOG_RETENTION_DAYS=14

# Lama penyimpanan raw phase picks AI di database MongoDB dalam hari (Default: 30 hari)
DB_PICKS_RETENTION_DAYS=30

# Ukuran maksimum per file log aktif sebelum di-truncate (dalam MB)
MAX_LOG_SIZE_MB=50

# Otomatis membersihkan image dan build cache docker yang tidak terpakai
ENABLE_DOCKER_PRUNE=true
DOCKER_PRUNE_UNTIL=168h

# Batas ambang persentase disk untuk memicu peringatan darurat
DISK_USAGE_ALERT_THRESHOLD=85
```

---

## 5. Menjalankan Skrip Pembersihan Otomatis

Telah disediakan dua script utama pada folder `scripts/`:
1. `scripts/cleanup_storage.sh`: Skrip cerdas yang membaca file `.env` dan mengeksekusi pembersihan.
2. `scripts/setup_cleanup_cron.sh`: Script installer untuk mengaktifkan jadwal cron job harian.

### A. Uji Coba Pembersihan (Simulasi Tanpa Menghapus Data)
Sebelum menghapus, Anda bisa menjalankan simulasi *dry-run*:
```bash
cd ~/GEMPA/ai-gempa-bmkg
bash scripts/cleanup_storage.sh --dry-run
```

### B. Menjalankan Pembersihan Secara Langsung
```bash
bash scripts/cleanup_storage.sh
```

---

## 6. Pemasangan Cron Job Harian

Pemasangan cron job dilakukan otomatis dengan satu perintah:

```bash
cd ~/GEMPA/ai-gempa-bmkg
bash scripts/setup_cleanup_cron.sh --install
```

Secara default, cron job akan dijadwalkan berjalan setiap hari pada jam **02:00 Pagi (WIB)**:
```cron
0 2 * * * /bin/bash /home/bmkg/GEMPA/ai-gempa-bmkg/scripts/cleanup_storage.sh >> /home/bmkg/GEMPA/ai-gempa-bmkg/logs/cleanup.log 2>&1 # AI-GEMPA-BMKG-STORAGE-CLEANUP
```

### Memeriksa Status Cron Job:
```bash
bash scripts/setup_cleanup_cron.sh --status
```

### Menghapus Cron Job:
```bash
bash scripts/setup_cleanup_cron.sh --remove
```

### Memantau Log Hasil Eksekusi Pembersihan:
```bash
tail -f ~/GEMPA/ai-gempa-bmkg/logs/cleanup.log
```

---

## 7. Mencegah Docker Container Logs Membengkak Kembali

Kami telah mengintegrasikan konfigurasi pembatasan ukuran log Docker ke:
1. `docker-compose.wrapper.yml`:
   ```yaml
   logging:
     driver: "json-file"
     options:
       max-size: "50m"
       max-file: "3"
   ```
2. `entrypoint-wrapper.sh`: Otomatis membuat `/etc/docker/daemon.json` di dalam wrapper Docker-in-Docker dengan konfigurasi `max-size: 50m` dan `max-file: 3`.

**Rekomendasi Host Docker (`riset-01`):**
Agar Docker di tingkat OS host juga memiliki batas ukuran log yang sama, pastikan file `/etc/docker/daemon.json` di host riset-01 berisi:
```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
EOF
sudo systemctl reload docker
```
