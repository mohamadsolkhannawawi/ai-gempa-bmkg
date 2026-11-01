# Panduan Lengkap Manajemen Storage, Keamanan .env, dan Operasional AI-GEMPA-BMKG
## Dokumentasi Arsitektur, Pemulihan Insiden, dan Pemeliharaan Sistem (Server riset-01)

Dokumentasi ini merangkum seluruh investigasi teknis, pemecahan masalah krisis penyimpanan (storage exhaustion 1.7 TB), mekanisme otomatisasi akun admin (*auto-sync self-healing*), standardisasi keamanan file environment (`.env`), serta panduan operasional harian pada sistem **AI-GEMPA-BMKG**.

---

## 1. Spesifikasi Server & Arsitektur Lingkungan

### 1.1 Spesifikasi Server Target
- **Host / Node:** `bmkg@riset-01` (`152.118.31.54`)
- **CPU:** 16 Cores @ 3.0 GHz
- **RAM:** 64 GB
- **Penyimpanan:** 1.8 TB SSD NVMe (`/dev/sda2` di partisi root `/`)
- **GPU:** NVIDIA GPU Compute Support (CUDA 11.8)
- **Akses Pengguna:** User `bmkg` (anggota grup `docker`, tanpa hak akses `sudo`)

### 1.2 Arsitektur Docker-in-Docker (DinD) & Pemetaan Port
Sistem berjalan di dalam wrapper Docker-in-Docker (`gempa-dind-wrapper`) untuk mengisolasi lingkungan multi-tenant dan dependency AI:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            HOST: bmkg@riset-01                              │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    CONTAINER: gempa-dind-wrapper                      │  │
│  │                                                                       │  │
│  │  [Network: sispro-tews_req]                                           │  │
│  │                                                                       │  │
│  │  1. Infrastructure (AI-TEWS/requirements):                            │  │
│  │     - requirements_mongodb_1     ──> 127.0.0.1:27017 / localhost:32717│  │
│  │     - requirements_redis_1       ──> 127.0.0.1:6379  / localhost:36379│  │
│  │     - requirements_kafka_1       ──> 127.0.0.1:9092  / localhost:39092│  │
│  │     - requirements_zookeeper_1   ──> 127.0.0.1:2181  / localhost:32181│  │
│  │                                                                       │  │
│  │  2. SISPRO-TEWS Backend:                                              │  │
│  │     - sispro-tews_controller_module_1 ──> Port Host: 38003 (Int: 8003) │  │
│  │     - archiving_module                ──> Menyimpan ke /mnt/archive   │  │
│  │     - seedlink_module                 ──> Internal bridge             │  │
│  │                                                                       │  │
│  │  3. Frontend:                                                         │  │
│  │     - sispro-tews_fe-1 (Vue 3)        ──> Port Host: 38006 (Int: 8004) │  │
│  │                                                                       │  │
│  │  4. AI Modules (AI-TEWS/AI_modules_simple_ai):                        │  │
│  │     - p-pick_module, association_module, locmag_module                │  │
│  │     - phase-arrival_module (Log limited: 50MB max)                    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Investigasi Krisis Storage 100% (1,7 TB) & Solusi Pembersihan

### 2.1 Kronologi & Gejala Masalah
Pada pemeriksaan awal sistem, kapasitas penyimpanan root `/dev/sda2` menunjukkan **100% Use** (0 byte available dari 1.8 TB):
```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda2       1,8T  1,8T     0 100% /
```
Dampaknya:
- Layanan MongoDB *crash* / *exit* karena tidak dapat menulis ke file journal disk.
- Layanan Docker gagal membuat layer kontainer baru (`no space left on device`).
- API Controller tidak dapat melakukan verifikasi login.

### 2.2 Investigasi & Penemuan Penyebab Akar (*Root Cause*)
Dengan menggunakan kontainer helper Docker berhak istimewa (`--privileged`):
```bash
docker run --rm --privileged -v /:/host mongo:4.4 bash -c "
  find /host/var/lib/docker/containers/ -name '*-json.log' -exec ls -lh {} + | sort -k5 -hr | head -n 5
"
```
**Temuan Fatal:**
Sebuah file log JSON kontainer milik `ai_modules_simple_ai_phase-arrival_module_1` di:
`/var/lib/docker/containers/793c416bebbb.../793c416bebbb...-json.log` membengkak hingga **1.720 Gigabyte (1,72 TERABYTE)**.

### 2.3 Mengapa Pembersihan Biasa & Cron Sebelumnya Gagal?
1. File log kontainer berada di bawah direktori host `/var/lib/docker/containers/` yang memiliki izin akses `0700` milik `root:root`.
2. Pengguna `bmkg` tidak memiliki akses `sudo`, sehingga script cron harian biasa tidak dapat mengakses atau memotong file log tersebut (*Permission Denied*).

### 2.4 Solusi Pemulihan Instan (Tanpa Sudo)
Pembersihan dilakukan dengan memanfaatkan socket Docker (`docker` group) menggunakan helper kontainer bervolume root:
```bash
docker run --rm --privileged -v /:/host mongo:4.4 bash -c "
  truncate -s 0 /host/var/lib/docker/containers/793c416bebbb.../*-json.log
  find /host/var/lib/docker/containers/ -name '*-json.log' -size +50M -exec truncate -s 0 {} +
"
docker system prune -f
docker volume prune -f
```

**Hasil Pemulihan:**
Ruang penyimpanan seketika pulih dari 100% penuh menjadi **10% terpakai (1,6 TB Free)**:
```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda2       1,8T  171G  1,6T  10% /
```

---

## 3. Pencegahan Permanen (Rotasi Log & Retensi Storage)

Agar masalah 1,7 TB tidak pernah terulang kembali, sistem telah diperkuat dengan 3 lapisan proteksi permanen:

### Lapisan 1: Pembatasan Logging Docker di Seluruh Compose File
Setiap service di `docker-compose.wrapper.yml` dan `AI_modules_simple_ai/docker-compose.yml` telah dipasangi konfigurasi rotasi log ketat:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "3"
```
*Ukuran log per kontainer tidak akan pernah dapat melebihi 150 MB (3 file x 50 MB).*

### Lapisan 2: Skrip Pembersihan Cerdas (`scripts/cleanup_storage.sh`)
Skrip [scripts/cleanup_storage.sh](file:///d:/Projects/GEMPA/ai-gempa-bmkg/scripts/cleanup_storage.sh) telah disempurnakan dengan kemampuan:
1. Memotong file log aplikasi yang melebihi batas 50 MB.
2. Menghapus arsip waveform MiniSEED yang berumur lebih dari 90 hari di `/mnt/archive`.
3. Menghapus raw picks di MongoDB yang lebih lama dari 30 hari.
4. **Fallback Pembersihan Root Tanpa Sudo:** Jika mendeteksi log kontainer host membengkak dan user tidak memiliki sudo, skrip otomatis memanggil kontainer helper Docker untuk me-truncate file log.

### Lapisan 3: Penjadwalan Cron Otomatis
Pembersihan dijadwalkan otomatis setiap pukul 02:00 dini hari:
```bash
0 2 * * * /home/bmkg/GEMPA/ai-gempa-bmkg/scripts/cleanup_storage.sh >> /home/bmkg/GEMPA/ai-gempa-bmkg/logs/cleanup.log 2>&1
```

---

## 4. Manajemen Akun Admin & Mekanisme Auto-Sync (Self-Healing)

### 4.1 Mengapa Sebelumnya Perlu Seed Berulang-ulang atau Login Gagal?
1. **Pemeriksaan User Statis (Bukan Hash Password):**
   Script `seed_admin_user.py` lama hanya mengecek `user_collection.find_one({"username": "admin"})`. Jika user `admin` sudah ada di MongoDB, script mencetak `"Preserving existing password"` dan **tidak memperbarui password**. Saat pengguna mengubah password di `.env` menjadi `Bmkg2026`, password di MongoDB tidak berubah, sehingga login gagal dan pengguna mengira seed-nya hilang.
2. **Ketergantungan Pembacaan `.env`:**
   Script berhenti membaca file konfigurasi (`break`) pada `/app/.env` lama di container yang belum memiliki variabel `INITIAL_ADMIN_PASSWORD`.

### 4.2 Arsitektur Baru: Smart Auto-Sync Saat Booting
Pada script [sispro-tews/controller_module/seed_admin_user.py](file:///d:/Projects/GEMPA/ai-gempa-bmkg/sispro-tews/controller_module/seed_admin_user.py), alur dibuat **idempoten dan self-healing**:

```
                  ┌─────────────────────────────────────┐
                  │ Container controller_module Booting │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ Baca kredensial dari .env aktif     │
                  │ (INITIAL_ADMIN_PASSWORD=Bmkg2026)   │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                       User 'admin' sudah ada di DB?
                                     │
                    ┌────────────────┴────────────────┐
                    │ TIDAK                           │ YA
                    ▼                                 ▼
         ┌─────────────────────┐       ┌───────────────────────────────┐
         │ Insert Admin User   │       │ Verifikasi kecocokan hash:    │
         │ baru ke MongoDB     │       │ pbkdf2_sha256.verify()        │
         └─────────────────────┘       └──────────────┬────────────────┘
                                                      │
                                      ┌───────────────┴───────────────┐
                                      │ COCOK                         │ BERBEDA
                                      ▼                               ▼
                           ┌─────────────────────┐       ┌─────────────────────────┐
                           │ Pertahankan password│       │ Update hash password    │
                           │ tetap aktif         │       │ otomatis di MongoDB     │
                           └─────────────────────┘       └─────────────────────────┘
```

**Keuntungan bagi Pengguna:**
- **Zero Manual Seeding:** Anda tidak perlu lagi menjalankan command `python seed_admin_user.py` secara manual di dalam container.
- **Kredensial Terjamin:** Jika Anda ingin mengganti password admin, cukup ubah nilai `INITIAL_ADMIN_PASSWORD` di `.env`, lalu restart `controller_module`. Password di database akan langsung tersinkronisasi.

---

## 5. Standardisasi Keamanan `.env` & Aturan Git

### 5.1 Masalah Pelacakan File `.env` di Git
Sebelumnya, file `.env` di berbagai subfolder (`sispro-tews/controller_module/.env`, `sispro-tews/.env`, dll.) pernah di-commit ke Git oleh pengembang terdahulu. Akibatnya, setiap kali ada perubahan konfigurasi lokal di server, perintah `git pull` selalu memicu error:
```text
error: Your local changes to the following files would be overwritten by merge:
        sispro-tews/controller_module/.env
```

### 5.2 Standar Baru yang Diterapkan
1. **`.gitignore` Rekursif Global:**
   Di file root [.gitignore](file:///d:/Projects/GEMPA/ai-gempa-bmkg/.gitignore):
   ```gitignore
   **/.env
   **/.env.*
   **/.env copy
   **/.envs/*.env
   !**/.env.example
   !**/.env.*.example
   ```
2. **Untracked dari Git Index:**
   Seluruh file `.env` telah dilepas dari pelacakan Git menggunakan `git rm --cached` tanpa menghapus file fisiknya di disk.
3. **Template Resmi `.env.example`:**
   Disediakan template [sispro-tews/controller_module/.env.example](file:///d:/Projects/GEMPA/ai-gempa-bmkg/sispro-tews/controller_module/.env.example) dan [sispro-tews/.env.example](file:///d:/Projects/GEMPA/ai-gempa-bmkg/sispro-tews/.env.example) sebagai contoh konfigurasi tanpa membocorkan kredensial rahasia.

---

## 6. Cheatsheet Perintah Operasional Lengkap

### 6.1 Memeriksa Status Kesehatan Server & Container
```bash
# Cek sisa kapasitas penyimpanan server
df -h /

# Cek container yang sedang aktif di dalam wrapper DinD
docker exec -i gempa-dind-wrapper docker ps

# Cek log 25 baris terakhir controller_module
docker exec -i gempa-dind-wrapper docker logs sispro-tews_controller_module_1 --tail 25

# Cek log database MongoDB
docker exec -i gempa-dind-wrapper docker logs requirements_mongodb_1 --tail 25
```

### 6.2 Menyalakan Ulang Layanan (Jika Server Restart / Service Mati)
```bash
# 1. Pastikan layanan Infrastructure (MongoDB, Redis, Kafka) menyala
docker exec -i gempa-dind-wrapper bash -c "cd /app/AI-TEWS/requirements && docker-compose up -d"

# 2. Restart Controller Backend (otomatis auto-seed admin)
docker exec -i gempa-dind-wrapper bash -c "cd /app/sispro-tews && docker-compose restart controller_module"

# 3. Pastikan AI Modules menyala
docker exec -i gempa-dind-wrapper bash -c "cd /app/AI-TEWS/AI_modules_simple_ai && docker-compose up -d"

# 4. Pastikan Frontend UI menyala
docker exec -i gempa-dind-wrapper bash -c "cd /app/tews-ui-vue && docker-compose up -d"
```

### 6.3 Verifikasi Login
- **Via Terminal (cURL):**
  ```bash
  curl -i -X POST http://localhost:38003/api/v1/user/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"Bmkg2026"}'
  ```
- **Via Web Browser:**
  - **URL:** [http://152.118.31.54:38006/login](http://152.118.31.54:38006/login)
  - **Username:** `admin`
  - **Password:** `Bmkg2026`
  - **Halaman Konfigurasi Pipeline AI:** [http://152.118.31.54:38006/config/pipeline](http://152.118.31.54:38006/config/pipeline)

### 6.4 Aturan Emas Pemeliharaan:
- **Jangan gunakan `-v` saat mematikan container:**  
  Gunakan `docker-compose down` atau `docker-compose restart`. Jangan gunakan `docker-compose down -v` agar volume data MongoDB dan waveform tidak terhapus.
- **Tarik update Git dengan aman:**  
  Karena file `.env` sudah diabaikan Git, Anda bisa menjalankan `git pull origin main` kapan saja tanpa khawatir terjadi konflik konfigurasi.
