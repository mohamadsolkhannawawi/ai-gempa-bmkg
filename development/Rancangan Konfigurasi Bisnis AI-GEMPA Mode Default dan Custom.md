# Rancangan Konfigurasi Bisnis AI-GEMPA: Mode Default dan Custom

*Draf v0.1 · 10 Oktober 2026 · Dasar telaah: CODEBASE.md v1.0 (2026-10-09). Angka paket, kuota, dan estimasi waktu bertanda (A) adalah asumsi awal yang perlu Anda konfirmasi.*

## 1. Ringkasan Eksekutif

**Masalah.** Konfigurasi saat ini berupa tabel kunci-nilai datar (koleksi `module` dengan `name`, `config`, `type`) dan CRUD sederhana. Tahapan pipeline (SeedLink → P-Pick → Asosiasi → LocMag) terpasang tetap. Belum ada konsep pelanggan, paket, versi konfigurasi, maupun pilihan model.

**Ide inti.** Ganti “kumpulan kunci” menjadi **Pipeline Profile**: dokumen deklaratif yang menyatakan (1) tahap mana yang aktif, (2) provider (model atau algoritma) apa yang dipakai tiap tahap, (3) parameternya, dan (4) ke mana keluaran dikirim. Ada dua mode:

- **Default**: memakai preset sistem (`default@1`) apa adanya, tanpa override. Pemiliknya platform.
- **Custom**: pengguna menyusun profil sendiri dari katalog tahap dan provider, termasuk hanya sebagian tahap (misalnya hanya P-Pick).

**Tiga prinsip rancangan.**

1. *Berbasis artifact.* Tahap terhubung lewat jenis data (waveform, pick, cluster, arrival, event), bukan lewat nama modul. Karena itu sebuah tahap boleh dilewati selama kebutuhan datanya terpenuhi.
2. *Katalog provider.* Setiap model atau algoritma terdaftar lewat manifest (versi, status, parameter, sumber daya, lisensi). Menambah model berarti menambah plugin, bukan mengubah inti.
3. *Validasi dan kompilasi sebelum aktif.* Profil tidak pernah diaktifkan sebelum lolos validasi struktur, skema parameter, dependensi data, dan aturan paket. Yang dijalankan runtime adalah hasil kompilasi (routing topic dan `rev`).

**Strategi.** Bertahap (strangler). Fase 1 hanya menambah “config sebagai data” tanpa mengubah perilaku runtime, sehingga risikonya rendah dan sistem yang berjalan sekarang tidak terganggu.

**Yang sudah ada.** Inti domain (katalog, profil, validator, compiler, proyeksi ke kunci lama) sudah dibuat sebagai prototipe dan lolos 15 tes otomatis (folder `bizconfig_proto/`). Bagian 8 menjelaskan cara memasangnya.

**Keputusan yang perlu Anda ambil** (rinci di Bagian 10): model tenant (satu deployment per pelanggan atau multi-tenant), pelanggan sasaran, kebijakan paket, dan isi modul `alpha`, `beta`, `neoalpha`.

## 2. Pemahaman Sistem Saat Ini

### 2.1 Arsitektur ringkas (dari CODEBASE.md)

| Tahap | Modul | Masuk | Keluar |
| --- | --- | --- | --- |
| Ingest | seedlink\_module | SeedLink (rtserve.earthscope.org:18000) | `waveform_seedlink` |
| P-Pick | p\_pick\_module (PhaseNet) | `waveform_seedlink` | `pick_topic` |
| Asosiasi | association\_module | `pick_topic` | `cluster_topic`, `arrival_pick_topic` |
| Lokasi dan magnitudo | locmag\_module | cluster dan arrival | `event_topic` |
| Persistensi dan API | controller\_module (FastAPI, MongoDB) | `event_topic` | REST, Socket.IO |
| UI | tews-ui-vue | REST, WebSocket | dashboard |

Infrastruktur: Kafka, MongoDB, Redis, dibungkus Docker-in-Docker. Ada juga varian modul AI `simple_ai` (produksi), `alpha`, `beta`, `neoalpha`, serta modul pendukung (`archiving`, `fdsn`, `flush`, `api_incoming`).

### 2.2 Hal yang menguntungkan

- Setiap tahap sudah punya topic masuk dan keluar yang jelas, sehingga komposisi berbasis artifact mudah dibuat.
- Penyimpanan config, REST, dan JWT sudah ada dan bisa dikembangkan, bukan dibangun dari nol.
- Varian `alpha`, `beta`, `neoalpha` kemungkinan bisa menjadi provider alternatif (isinya perlu Anda konfirmasi).

### 2.3 Kesenjangan terhadap kebutuhan bisnis

| Kebutuhan | Kondisi sekarang |
| --- | --- |
| Memilih tahap aktif | Tidak ada; semua kontainer berjalan |
| Memilih model per tahap | Satu implementasi per tahap; model tertanam |
| Banyak pelanggan | Tidak ada workspace; peran hanya `superadmin` |
| Versi dan rollback | Tidak ada; update menimpa nilai |
| Audit perubahan | Tidak ada |
| Validasi | Hanya tipe dasar, tanpa skema per parameter |
| Penerapan tanpa restart | Tidak jelas; modul membaca lewat REST dengan JWT 24 jam |

### 2.4 Temuan yang sebaiknya dibereskan lebih dulu

| # | Tingkat | Temuan | Tindakan |
| --- | --- | --- | --- |
| 1 | Tinggi | JWT secret dan password admin contoh (`Bmkg2026`) tertulis di dokumentasi | Rotasi secret, pindah ke secret store, hapus dari dokumen, wajib ganti password awal |
| 2 | Tinggi | CORS `*` dan tidak ada RBAC selain `superadmin` | Whitelist origin dan RBAC (Bagian 6) |
| 3 | Sedang | Config API tanpa hapus, versi, dan audit; modul membaca dengan JWT pengguna 24 jam | Service token per modul, config berversi, hot reload |
| 4 | Sedang | Dokumen menyebut `websocket_module` terpisah, padahal Socket.IO ada di `controller_module/app.py`; frontend memakai `ws://controller_module:8000`, nama DNS internal Docker yang tidak bisa dijangkau browser | Pastikan lewat nginx atau URL publik; putuskan apakah WebSocket dipisah |
| 5 | Sedang | Hash password disebut `pbkdf2_sha256` sekaligus bcrypt | Konsistenkan satu skema |
| 6 | Sedang | CSV stasiun contoh: koordinat `II.KAPI` (-5.88, 119.34) berbeda dari angka di laporan audit sebelumnya (-5.014, 119.752; laporan itu pun belum terverifikasi), dan kanal `PS.JAY` (`HHZ`) belum terbukti | Koordinat dan kanal diambil dari FDSN lalu divalidasi dengan INFO SeedLink; daftar stasiun dihasilkan, bukan diketik |
| 7 | Sedang | Referensi `earthquake.bmkg.go.id/catalog/api17/` (polling 60 detik) belum pernah terverifikasi | Jangan jadikan dependensi sebelum diuji; kandidat yang perlu diuji: `data.bmkg.go.id/DataMKG/TEWS/` |
| 8 | Sedang | SeedLink module memakai Python 3.8 (sudah EOL) dengan pin numpy<1.24; ObsPy 1.5.1 gagal connect pada `EasySeedLinkClient` | Pin ObsPy di bawah 1.5, atau pakai klien SeedLink v3 ringan seperti di `seedlink_audit.py` |
| 9 | Rendah-sedang | Docker-in-Docker privileged; topic Kafka dibuat manual | Cukup untuk dev dan demo; siapkan jalur ke Compose atau K8s dan provisioning topic otomatis |

## 3. Konsep Inti: Pipeline Profile

### 3.1 Artifact, tahap, provider, dan sink

```
  Sumber                 Tahap (provider dipilih)        Artifact
  SeedLink / FDSN   ->   ingest                     ->   waveform
  push / replay          p_pick                     ->   pick
                         association                 ->   cluster + arrival
                         locmag                     ->   event

  Sink (memilih artifact yang dikonsumsi): ws_ui | webhook | kafka_export | archive
```

| Tahap | Membutuhkan | Menghasilkan | Provider awal |
| --- | --- | --- | --- |
| ingest | (sumber luar) | waveform | seedlink\_v3, fdsn\_poll, push\_api, file\_replay |
| p\_pick | waveform | pick | phasenet, sta\_lta, eqtransformer |
| association | pick | cluster, arrival | dbscan\_simple, gamma, pyocto |
| locmag | cluster, arrival | event | geiger (+ ML atau mb), nonlinloc |

Sink: `ws_ui` dan `archive` sudah ada; `webhook` dan `kafka_export` baru.

### 3.2 Dua mode

| Aspek | Default | Custom |
| --- | --- | --- |
| Pemilik | Platform (`default@N`, tidak bisa diubah) | Workspace |
| Tahap | Seluruhnya aktif sesuai preset | Pengguna memilih; tahap yang tidak ditulis dianggap nonaktif |
| Provider dan parameter | Dari preset; tanpa override | Dipilih dari katalog sesuai paket; divalidasi skema |
| Pembaruan | Mengikuti kebijakan upgrade preset | Tidak ikut upgrade; ada peringatan bila provider deprecated |
| Ketersediaan | Semua paket | Pro ke atas (A) |
| Pintasan | “Mulai dari default lalu ubah” | “Reset ke default” kapan saja |

Catatan: stasiun, sumber data, dan tujuan sink (misalnya URL webhook) adalah data workspace, bukan bagian dari “aturan pipeline default”. Mode default tetap boleh punya stasiun sendiri.

### 3.3 Aturan komposisi

1. Tahap boleh dilewati selama setiap artifact yang dibutuhkan tersedia dari tahap hulu yang aktif atau dari input eksternal (`external_inputs`).
2. Minimal satu sumber (ingest atau input eksternal) dan satu sink harus aktif.
3. Sink memilih artifact yang dikonsumsi, dan artifact itu harus tersedia di pipeline.
4. Keluaran yang tidak dipakai siapa pun menghasilkan peringatan (boros sumber daya), bukan galat.
5. Tahap nonaktif tidak boleh menjalankan inferensi.

### 3.4 Kasus penggunaan yang harus didukung

| Kasus | Tahap aktif | Sink | Catatan |
| --- | --- | --- | --- |
| A. Pipeline penuh | ingest, p\_pick, association, locmag | ws\_ui, archive | Mode default |
| B. Hanya P-Pick (layanan pick) | ingest, p\_pick | webhook atau kafka\_export (artifact `pick`) | Tanpa asosiasi dan lokasi |
| C. Bawa pick sendiri | association, locmag + input eksternal `pick` | ws\_ui atau webhook | Pelanggan punya picker sendiri |
| D. Hanya arsip dan replay | ingest | archive | Tanpa AI |
| E. Bandingkan model | p\_pick dengan dua provider paralel | ws\_ui | Shadow pipeline, fase lanjut |

## 4. Arsitektur Target

### 4.1 Control plane dan data plane

```
┌────────────────────────── CONTROL PLANE ───────────────────────────┐
│ UI Admin (Vue)                                                      │
│    │ REST v2 (JWT)                                                  │
│ Config API (perluasan controller_module)                            │
│  ├─ Catalog Service    : tahap, provider, skema parameter           │
│  ├─ Profile Service    : draft, revisi, aktivasi, rollback          │
│  ├─ Validator/Compiler : inti domain (tanpa I/O)                    │
│  ├─ Entitlement        : paket dan kuota                            │
│  └─ Audit + Metering                                                │
│ MongoDB: workspaces, profiles, catalog, plans, audit, usage         │
│    │ keadaan yang diinginkan                                        │
│ Orchestrator (reconciler) ── config_events (Kafka, compacted) ──┐   │
└─────────────────────────────────────────────────────────────────┼───┘
┌─────────────────────────── DATA PLANE ─────────────────────────┼───┐
│ Stage runtime (memakai stage_sdk) ◄─────────────────────────────┘   │
│  ingest → p_pick → association → locmag → sink                      │
│  Antar tahap lewat Kafka, satu topic per artifact                   │
│  Model Registry (/models + checksum) · Redis · MongoDB              │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Komponen

| Komponen | Tanggung jawab | Status |
| --- | --- | --- |
| Catalog Service | Menyajikan tahap, provider, status, skema parameter dari manifest | Baru |
| Profile Service | Draft, revisi immutable, pointer aktif, last-known-good | Baru (di `controller_module`) |
| Validator/Compiler | Validasi dan kompilasi profil; fungsi murni tanpa I/O | Prototipe tersedia |
| Entitlement | Aturan paket dan kuota, ditegakkan di backend | Baru |
| Orchestrator | Membandingkan keadaan diinginkan vs nyata, menerbitkan snapshot | Baru (`orchestrator_module`) |
| Stage SDK | Paket Python bersama: klien config, hot reload, envelope, metrik, health | Baru (`stage_sdk`) |
| Model Registry | Bobot model berversi dengan checksum dan model card | Baru |
| Audit dan Metering | Jejak perubahan dan catatan pemakaian | Baru |
| Modul tahap | Dibungkus SDK; logika model dipindah menjadi provider | Ada, direfaktor |

### 4.3 Cara kerja aplikasi: alur aktivasi profil

1. Pengguna memilih mode dan menyusun profil di wizard; draft tersimpan.
2. UI memanggil `POST /api/v2/profiles/{id}/validate`; validator mengembalikan daftar isu (galat dan peringatan).
3. Opsional: uji-coba memakai rekaman replay; hasilnya jumlah pick dan event serta latensi.
4. `POST .../activate`: Entitlement memeriksa paket, Compiler menghasilkan rencana (topic, consumer group, parameter terisi) dan `rev`; revisi disimpan immutable.
5. Orchestrator membandingkan revisi baru dengan keadaan nyata (heartbeat tiap tahap).
6. Orchestrator menerbitkan snapshot ke `config_events` (topic compacted, key `{workspace}.{stage}`).
7. Stage runtime menerima snapshot, memuat provider baru di latar belakang, lalu menukarnya secara atomik di antara dua jendela data. Bila `enabled=false`, consumer di-pause.
8. Tahap melapor `applied(rev)`. Bila gagal atau tidak sehat dalam batas waktu, sistem rollback ke last-known-good dan mengirim alert.
9. Setiap pesan keluaran membawa `profile_rev` dan `provider` sebagai jejak audit.

### 4.4 Cara menonaktifkan tahap di runtime

| Opsi | Cara | Kelebihan | Kekurangan |
| --- | --- | --- | --- |
| A (awal) | Semua kontainer tetap jalan; tahap nonaktif mem-pause consumer | Perubahan paling kecil, cocok dengan compose sekarang | RAM tetap terpakai saat idle |
| B | Orchestrator start/stop kontainer lewat Docker API | Hemat sumber daya | Rumit di DinD privileged, menambah titik gagal |
| C | Kubernetes dengan autoscaling berbasis lag Kafka | Skala produk besar | Biaya migrasi tinggi |

Rekomendasi: Opsi A pada Fase 2 dan 3, Opsi B atau C pada Fase 5.

### 4.5 Tenancy

Workspace adalah unit konfigurasi, stasiun, dan data. Pada fase awal hanya ada workspace `default` yang memakai nama topic lama (kompatibel). Workspace lain memakai topic `{ws}.{artifact}` dan consumer group `{ws}.{stage}`. Semua pesan membawa `workspace_id` sejak awal, sehingga migrasi ke multi-tenant tidak butuh perubahan kontrak. Dua model penjualan: (a) satu deployment per pelanggan (sederhana, isolasi kuat), (b) multi-tenant dengan pekerja tahap yang berbagi (hemat biaya, rumit). Rekomendasi: mulai dari (a) dengan skema yang sudah siap untuk (b).

### 4.6 Observability

Setiap metrik tahap diberi label `workspace`, `stage`, `provider`, `profile_rev`: latensi per tahap, laju pick, rasio lolos asosiasi, lag consumer, galat model. Dengan begitu dampak memilih provider dapat diukur langsung. Data yang sama bisa dipakai sebagai bahan eksperimen observability di skripsi Anda.

## 5. Model Data dan Katalog Provider

### 5.1 Koleksi MongoDB

| Koleksi | Isi | Catatan |
| --- | --- | --- |
| `workspaces` | id, nama, paket, status | Stasiun dan sumber data merujuk ke sini |
| `profiles` | Satu dokumen per revisi (immutable): `workspace_id`, `profile_id`, `rev`, `mode`, isi, `created_by`, `note` | Revisi tidak pernah diubah |
| `profile_pointers` | `active_rev`, `last_known_good_rev`, `draft_rev` per workspace | Aktivasi = memindah pointer |
| `catalog_providers` | Hasil impor manifest provider | Dibaca Catalog Service |
| `plans` | Definisi paket dan kuota | Dikelola `platform_admin` |
| `audit_log` | Siapa, apa, kapan, diff, alasan | Append-only |
| `usage_events` | Catatan pemakaian untuk metering | Per workspace, tahap, provider |
| `stations` | Koleksi yang sudah ada | Tambah `workspace_id`, `source_id`, `terms` (ketentuan penggunaan) |
| `module` | Koleksi config lama | Tetap ada; diisi proyeksi dari profil aktif selama masa transisi |

### 5.2 Contoh profil custom (hanya P-Pick)

Ditulis dalam YAML agar mudah dibaca; API menerima JSON yang setara.

```yaml
mode: custom
name: Layanan P-Pick untuk pelanggan Acme
preset: default@1          # titik awal saja; tahap yang tidak ditulis = nonaktif
stages:
  ingest:
    provider: seedlink_v3
    params: {retry_interval: 30}
  p_pick:
    provider: phasenet
    params: {weights: original, p_threshold: 0.4, batch_size: 32}
sinks:
  webhook:
    params:
      url: https://api.acme.example/hooks/picks
      artifacts: [pick]
external_inputs: []
```

Hasil kompilasi: tahap aktif hanya `ingest` dan `p_pick`; webhook mengonsumsi `pick_topic`; consumer `association` dan `locmag` di-pause; `rev` dihitung dari isi hasil kompilasi sehingga profil yang sama selalu menghasilkan `rev` yang sama.

### 5.3 Contoh manifest provider

```yaml
id: sta_lta
stage: p_pick
version: 1.0.0
status: stable             # experimental | beta | stable | deprecated
min_plan: basic
entrypoint: providers.sta_lta:StaLtaPicker
resources: {cpu: 0.5, mem_mb: 256, gpu: none}
license: {code: <isi>, weights: none}
model_card: docs/model_cards/sta_lta.md
params:
  sta: {type: number, default: 0.5, min: 0.05, max: 5, unit: s}
  lta: {type: number, default: 10,  min: 2,    max: 60, unit: s}
  on:  {type: number, default: 3.5, min: 1.5,  max: 10}
  off: {type: number, default: 1.5, min: 0.5,  max: 5}
```

### 5.4 Provider dan model yang perlu disiapkan

Semua nama di bawah adalah kandidat. Verifikasi ketersediaan bobot, lisensi, dan kecocokan dengan data Anda sebelum dipakai secara komersial.

| Tahap | Provider | Status awal | Kebutuhan | Catatan |
| --- | --- | --- | --- | --- |
| ingest | seedlink\_v3 | stable (ada) | Klien SeedLink | Pin versi klien; klien ringan tanpa ObsPy sebagai opsi |
| ingest | fdsn\_poll | beta | CPU | Cadangan bila SeedLink tidak tersedia; latensi lebih tinggi |
| ingest | push\_api | stable | Token, batas laju | Untuk stasiun milik pelanggan (HTTP atau WebSocket ke Kafka) |
| ingest | file\_replay | stable | miniSEED, kecepatan putar | Demo, uji regresi, dry-run profil |
| p\_pick | phasenet | stable (ada) | Bobot pretrained (mis. dari SeisBench: original, instance, stead) | GPU opsional; ambang dikalibrasi per wilayah |
| p\_pick | sta\_lta | stable | CPU | Baseline dan fallback; murah tetapi banyak positif palsu |
| p\_pick | eqtransformer | beta | GPU disarankan | Deteksi sekaligus picking |
| association | dbscan\_simple | stable (ada) | CPU | Parameter waktu dan jarak bergantung geometri jaringan |
| association | gamma | beta | CPU, model kecepatan | Kandidat: GaMMA (Zhu dkk., 2022) |
| association | pyocto | experimental | CPU | Kandidat untuk dievaluasi |
| locmag | geiger + ML | stable (ada) | Model kecepatan 1D (IASP91, AK135) | ML butuh respons instrumen dan kalibrasi atenuasi regional |
| locmag | nonlinloc | beta | Grid travel-time besar | Akurasi lebih baik, memori besar; cek lisensi |
| locmag | slot magnitudo (mb, Mwp) | rencana | - | Pisahkan menjadi slot sendiri pada Fase 3 atau lebih |
| sink | ws\_ui, archive | stable (ada) | - | - |
| sink | webhook | baru | Retry, tanda tangan HMAC, DLQ | Untuk integrasi pelanggan |
| sink | kafka\_export | baru | Topic dan ACL per workspace | Untuk pelanggan teknis |
| sink | notifier, CAP/QuakeML | fase lanjut | - | Telegram, email, WhatsApp; format standar untuk interoperabilitas |

### 5.5 Evaluasi dan promosi provider

Setiap provider wajib punya **model card**: data latih, wilayah yang cocok, batas kemampuan, versi dan hash bobot, tanggal, dan hasil evaluasi. Evaluasi memakai kumpulan event historis yang diputar ulang (replay) dengan katalog pembanding independen (misalnya USGS, EMSC, GFZ; katalog BMKG bila aksesnya ada).

| Aspek | Metrik |
| --- | --- |
| Pick | Precision, recall, residual waktu terhadap pick referensi |
| Asosiasi | Recall event, jumlah event palsu per hari |
| Lokasi | Galat episentrum (km) dan kedalaman |
| Magnitudo | Residual terhadap katalog |
| Operasional | Latensi p50 dan p95, CPU/GPU/RAM, stabilitas 24 jam |

Promosi status: experimental → beta → stable berdasarkan ambang yang disepakati bersama tim seismologi. Angka ambang belum ditetapkan di dokumen ini.

## 6. Aturan Bisnis

### 6.1 Daftar aturan

| ID | Aturan | Penegakan |
| --- | --- | --- |
| BR-01 | Setiap workspace punya tepat satu profil aktif, bermode default atau custom | Pointer aktif tunggal, unique index |
| BR-02 | Mode default memakai preset sistem tanpa override; override ditolak (kode V010) | Validator |
| BR-03 | Preset `default@N` immutable; perubahan = versi baru. Workspace default mengikuti kebijakan upgrade (manual, atau otomatis untuk versi minor stable) | Catalog Service |
| BR-04 | Mode custom hanya untuk paket yang mengizinkan (A: Pro ke atas) | Backend (V009), bukan hanya UI |
| BR-05 | Profil custom harus lolos validasi: skema parameter, dependensi artifact, minimal satu sumber dan satu sink | Validator |
| BR-06 | Provider experimental hanya Enterprise dan diberi tanda di UI dan metadata keluaran; beta untuk Pro ke atas; deprecated tidak bisa dipilih untuk profil baru | Entitlement |
| BR-07 | Setiap perubahan membuat revisi baru; rollback kapan saja; riwayat tidak dapat dihapus | Profile Service, audit |
| BR-08 | Aktivasi profil produksi hanya oleh `workspace_admin`; Enterprise dapat mewajibkan persetujuan dua orang | RBAC |
| BR-09 | Bila aktivasi gagal atau tahap tidak sehat setelah batas waktu, sistem kembali ke last-known-good | Orchestrator |
| BR-10 | Kuota paket (stasiun, profil, laju pesan, retensi arsip) ditegakkan saat menyimpan dan saat berjalan | Entitlement, metering |
| BR-11 | Data, stasiun, dan profil terisolasi per workspace; lintas workspace hanya `platform_admin` | RBAC, filter query |
| BR-12 | Setiap sumber data punya catatan ketentuan penggunaan; sink yang meredistribusi data tidak boleh dipakai pada sumber yang melarang redistribusi | Validator (aturan baru V014, belum ada di prototipe) |
| BR-13 | Keluaran otomatis diberi label bukan peringatan resmi; notifikasi publik hanya untuk workspace yang lolos verifikasi organisasi | Policy engine |
| BR-14 | Setiap keluaran mencatat `profile_rev`, versi provider, dan hash bobot agar dapat direproduksi | Stage SDK |
| BR-15 | Reset ke default tidak menghapus riwayat custom; custom lama dapat dipulihkan | Profile Service |

### 6.2 Paket (contoh, A)

| Aspek | Basic | Pro | Enterprise |
| --- | --- | --- | --- |
| Mode | Default saja | Default dan custom | Default dan custom |
| Status provider | stable | stable dan beta | stable, beta, experimental |
| Stasiun | 20 | 100 | 1000 |
| Profil custom | - | 5 | Tidak dibatasi |
| Sink | ws\_ui, archive | Ditambah webhook, kafka\_export | Ditambah notifier, CAP/QuakeML |
| Persetujuan dua orang | - | - | Opsional |
| Dukungan | Komunitas | Email | Kontrak SLA |

Angka di atas contoh dari prototipe. Tentukan nilai sebenarnya dari biaya GPU dan infrastruktur serta strategi harga Anda.

### 6.3 Kepatuhan dan risiko hukum (perlu ditinjau konsultan hukum)

- **Ketentuan data sumber.** Contoh nyata dari pekerjaan sebelumnya: GFZ menyatakan tidak dapat meredistribusi waveform stasiun GEOFON-BMKG sejak 24 September 2026 (forum GFZ). Pipeline yang menerima data dari sumber berpembatasan tidak boleh otomatis menyiarkan ulang waveform. BR-12 menjawab hal ini.
- **Otoritas peringatan.** Peringatan gempa dan tsunami resmi di Indonesia adalah kewenangan BMKG (tinjau dasar hukumnya, misalnya UU No. 31 Tahun 2009, bersama konsultan hukum). Posisikan produk sebagai alat pemantauan dan analisis dengan disclaimer, kecuali ada kerja sama resmi.
- **Lisensi model dan pustaka.** Bobot pretrained dan perangkat lunak seperti NonLinLoc punya ketentuan masing-masing; audit sebelum komersialisasi.
- **Data pelanggan.** Enkripsi saat simpan dan kirim, cadangan, dan kebijakan retensi.

## 7. Spesifikasi Kebutuhan Perangkat Lunak (SRS)

### 7.1 Tujuan dan lingkup

Bagian ini menetapkan kebutuhan sistem Konfigurasi Bisnis AI-GEMPA: katalog, profil pipeline (default dan custom), validasi, aktivasi, penerapan ke runtime, paket dan kuota, serta audit. Di luar lingkup: pelatihan model baru, penagihan (billing), dan perubahan algoritma inti tiap tahap.

### 7.2 Peran pengguna

| Peran | Hak |
| --- | --- |
| platform\_admin | Mengelola katalog, preset, paket, dan semua workspace |
| workspace\_admin | Mengelola profil, stasiun, sink, pengguna workspace; mengaktifkan profil |
| operator | Mengubah draft, uji-coba, melihat status; tidak mengaktifkan produksi |
| viewer | Melihat dashboard dan konfigurasi |
| service | Akun mesin untuk modul (membaca snapshot, menulis heartbeat) |

### 7.3 Istilah

**Workspace**: unit pelanggan. **Profil**: dokumen konfigurasi pipeline. **Revisi**: versi profil yang immutable. **Preset**: profil milik sistem. **Provider**: implementasi model atau algoritma pada satu tahap. **Artifact**: jenis data antar tahap. **Sink**: tujuan keluaran. **rev**: hash isi hasil kompilasi. **LKG**: last-known-good, revisi terakhir yang terbukti sehat.

### 7.4 Asumsi dan batasan

- Kafka tetap sebagai bus pesan, MongoDB sebagai penyimpanan, Python untuk modul AI, Vue untuk UI.
- Modul tahap dapat dimodifikasi untuk memakai `stage_sdk`.
- Kunci config lama tetap harus bisa dibaca selama masa transisi.
- Latensi data bergantung pada sumber SeedLink publik dan tidak dijamin.

### 7.5 Kebutuhan fungsional

Prioritas: M = harus, S = sebaiknya, C = bisa.

| ID | Kebutuhan | Prio | Fase |
| --- | --- | --- | --- |
| FR-01 | Sistem menyediakan katalog tahap dan provider (nama, versi, status, parameter, sumber daya, lisensi) melalui API | M | 1 |
| FR-02 | Pengguna memilih mode default atau custom per workspace | M | 1 |
| FR-03 | Mode default memakai preset sistem tanpa override dan menampilkan ringkasan preset | M | 1 |
| FR-04 | Mode custom: mengaktifkan atau menonaktifkan tahap ingest, p\_pick, association, locmag dan sink | M | 2 |
| FR-05 | Mode custom: memilih provider dan parameter per tahap sesuai skema | M | 2 |
| FR-06 | Profil divalidasi (kode V001-V013, W001-W003) saat disimpan sebagai draft dan sebelum aktivasi | M | 1 |
| FR-07 | Sistem menghitung rencana routing (topic, consumer group, parameter terisi) dan `rev` | M | 1 |
| FR-08 | Profil berversi dan immutable per revisi; aktivasi memindah pointer; rollback satu langkah | M | 1 |
| FR-09 | Aktivasi diterapkan ke runtime tanpa downtime penuh (hot reload) atau restart terkontrol; status applied, pending, failed terlihat | M | 2 |
| FR-10 | Kegagalan penerapan memicu rollback otomatis ke LKG dan alert | S | 2 |
| FR-11 | Tahap nonaktif tidak mengonsumsi pesan dan tidak menjalankan inferensi (consumer di-pause) | M | 2 |
| FR-12 | Pesan keluaran memuat `workspace_id`, `profile_rev`, dan `provider` | M | 2 |
| FR-13 | Input eksternal untuk artifact `pick` dan `waveform` lewat API terautentikasi | S | 3 |
| FR-14 | Sink ws\_ui dan archive tetap berfungsi; webhook dan kafka\_export baru, dengan retry, backoff, DLQ | M | 3 |
| FR-15 | Uji-coba (dry-run) profil memakai replay sebelum aktivasi; hasil: jumlah pick dan event, latensi | S | 3 |
| FR-16 | Kunci config lama tetap tersedia lewat proyeksi (getbyname, getall) selama transisi | M | 1 |
| FR-17 | Wizard UI: pilih mode, pilih tahap dan provider, isi parameter (form dari skema), validasi langsung, pratinjau grafik, aktivasi | M | 2 |
| FR-18 | Audit log append-only: siapa, apa, kapan, diff, alasan | M | 1 |
| FR-19 | RBAC: platform\_admin, workspace\_admin, operator, viewer, service; persetujuan dua orang opsional untuk Enterprise | M | 4 |
| FR-20 | Entitlement (mode custom, status provider, jumlah stasiun, jumlah profil) divalidasi di backend | M | 4 |
| FR-21 | Metering pemakaian per workspace, tahap, provider (stasiun-jam, pesan, inferensi) | S | 4 |
| FR-22 | Manajemen stasiun per workspace; metadata dari FDSN divalidasi dengan INFO SeedLink (kanal, umur data) | S | 3 |
| FR-23 | Preset berversi `default@N` dengan kebijakan upgrade; perubahan preset tidak mengubah profil custom | S | 2 |
| FR-24 | Pengguna dapat memulai custom dari default dan mereset ke default | M | 2 |
| FR-25 | Provider baru didaftarkan lewat manifest tanpa mengubah kode inti | S | 3 |

### 7.6 Kebutuhan non-fungsional

| ID | Kebutuhan | Target (A) |
| --- | --- | --- |
| NFR-01 | Performa validasi | p95 < 200 ms untuk profil dengan sampai 20 entri |
| NFR-02 | Waktu dari aktivasi sampai status applied | < 60 detik (hot reload) |
| NFR-03 | Overhead lapisan config terhadap throughput pipeline | < 5 persen |
| NFR-04 | Ketahanan: control plane mati tidak menghentikan data plane; modul memakai snapshot terakhir yang tersimpan lokal | Wajib |
| NFR-05 | Keamanan: secret di secret store, token berumur pendek dengan refresh, service token per modul, CORS whitelist, KDF untuk password, rate limiting | Wajib |
| NFR-06 | Observability: metrik per stage, provider, rev; log terstruktur; trace id di envelope; health dan readiness | Wajib |
| NFR-07 | Keandalan pesan: at-least-once dengan kunci idempotensi, DLQ, backpressure | Wajib |
| NFR-08 | Skalabilitas: menambah stasiun atau workspace tanpa mengubah kode; target awal 100 stasiun, 3 komponen | Sebaiknya |
| NFR-09 | Portabilitas: berjalan di Compose; jalur ke K8s; tidak bergantung DinD privileged di produksi | Sebaiknya |
| NFR-10 | Maintainability: inti domain tanpa framework; cakupan tes validator dan compiler minimal 80 persen; uji kontrak untuk skema pesan | Wajib |
| NFR-11 | Kompatibilitas: modul baru Python 3.10 atau lebih baru; versi library kritis (ObsPy) dipin | Wajib |
| NFR-12 | Reproduksibilitas: `profile_rev` + versi provider + hash bobot cukup untuk mengulang hasil | Wajib |

### 7.7 Kriteria penerimaan utama

- **AC-1.** Diberikan workspace mode default, ketika pengguna membuka halaman pipeline, maka empat tahap dan dua sink tampil dan tidak ada kontrol untuk mengubah parameter.
- **AC-2.** Diberikan profil custom hanya p\_pick dan webhook, ketika diaktifkan, maka hanya consumer p\_pick yang memproses, association dan locmag ter-pause, webhook menerima pick, dan tidak ada pesan baru di `cluster_topic`.
- **AC-3.** Diberikan profil dengan association tanpa sumber pick, ketika divalidasi, maka muncul V004 dan aktivasi ditolak.
- **AC-4.** Diberikan aktivasi yang gagal karena bobot model tidak ditemukan, maka sistem kembali ke revisi sebelumnya dalam 60 detik dan mengirim alert.
- **AC-5.** Diberikan paket Basic, ketika memanggil API untuk menyimpan profil custom (walau UI dimanipulasi), maka respons 403 dengan kode V009.
- **AC-6.** Setiap pesan di topic keluaran memuat `profile_rev`; dua profil dengan isi terkompilasi identik menghasilkan `rev` identik.

### 7.8 Antarmuka eksternal

REST `/api/v2` (JWT pengguna atau service token), topic Kafka per artifact dan `config_events`, Socket.IO untuk UI, webhook keluar (tanda tangan HMAC), layanan web FDSN untuk metadata stasiun, dan SeedLink untuk data waveform.

## 8. Desain Kode

### 8.1 Prinsip

- **Domain murni.** Logika katalog, validasi, dan kompilasi tidak boleh melakukan I/O dan tidak bergantung pada FastAPI, MongoDB, atau Kafka. Itu membuatnya mudah dites dan dipakai ulang di tempat lain (UI, CLI, orchestrator).
- **Lapisan.** `routes` → `services` → `domain`; `services` memanggil `repositories` untuk persistensi. Aturan bisnis hanya di `domain` dan `services`.
- **Kontrak sebelum kode.** Setiap topic punya skema pesan berversi dan contoh data; perubahan skema harus lolos uji kontrak.
- **Kompatibilitas.** Endpoint v1 dan koleksi `module` tetap berfungsi selama transisi (pola strangler).
- **Fitur bertanda.** Seluruh jalur baru di balik flag `PIPELINE_V2` sampai Fase 2 stabil.

### 8.2 Struktur direktori tambahan

```
sispro-tews/controller_module/
  domain/pipeline_profile.py        # inti: katalog, profil, validator, compiler (prototipe tersedia)
  catalog/manifests/*.yaml          # manifest provider
  routes/v2/{catalog,profiles,workspaces,runtime,audit}.py
  services/{profile_service,activation_service,entitlement_service}.py
  repositories/{profile_repo,pointer_repo,audit_repo,usage_repo}.py
sispro-tews/orchestrator_module/    # reconciler
sispro-tews/stage_sdk/              # paket Python bersama
  stage_sdk/{runtime.py,config_client.py,envelope.py,providers.py,metrics.py}
AI-TEWS/AI_modules_simple_ai/*/providers/   # phasenet.py, sta_lta.py, dbscan_simple.py, geiger.py
tews-ui-vue/src/views/pipeline/{Wizard.vue,StageCard.vue,ParamForm.vue,GraphPreview.vue}
```

### 8.3 Prototipe inti domain (sudah dibuat dan dites)

Berkas `bizconfig_proto/pipeline_profile.py` dan `test_pipeline_profile.py` mengimplementasikan:

- Katalog (`build_default_catalog`) dengan tahap, provider, status, paket minimal, dan skema parameter.
- `Profile.from_dict`, `resolve` (default memakai preset; custom apa adanya), `validate` (daftar isu), `compile_pipeline` (rencana routing, parameter terisi, `rev` hash), dan `to_legacy_keys` (proyeksi ke format `name/config/type` lama).
- Penamaan topic: workspace `default` memakai nama topic lama, workspace lain memakai `{ws}.{artifact}`.
- 15 tes unit yang lolos: default valid, default menolak override, layanan P-Pick saja, asosiasi dengan pick eksternal, dependensi hilang, aturan sink, validasi parameter (rentang, tipe, enum, parameter tak dikenal, wajib), aturan paket, nama tak dikenal, peringatan, tahap nonaktif diabaikan, `rev` deterministik, topic per workspace, proyeksi kunci lama.

Menjalankan: `cd bizconfig_proto && python -m unittest -v`. Nilai default parameter di katalog adalah contoh; ganti dengan nilai yang berlaku di sistem Anda sekarang. Pemasangan: salin ke `controller_module/domain/`, lalu `profile_service` memanggil `validate` dan `compile_pipeline`.

### 8.4 Kode isu validasi

| Kode | Arti |
| --- | --- |
| V000 | Mode bukan default atau custom |
| V001 | Tahap atau sink tidak dikenal |
| V002 | Provider tidak ada untuk tahap itu |
| V003 | Parameter tidak valid, tidak dikenal, atau wajib tetapi kosong |
| V004 | Tahap membutuhkan artifact yang tidak tersedia |
| V005 | Tidak ada sumber data |
| V006 | Tidak ada sink aktif |
| V007 | Sink meminta artifact yang tidak dihasilkan |
| V008 | Provider tidak tersedia di paket |
| V009 | Mode custom tidak diizinkan di paket |
| V010 | Mode default membawa override |
| V012 | Preset tidak ada |
| V013 | Input eksternal tidak dikenal |
| W001 | Keluaran tidak dipakai siapa pun (peringatan) |
| W003 | Artifact punya dua sumber: internal dan eksternal (peringatan) |

V014 (aturan redistribusi, BR-12) direncanakan dan belum ada di prototipe.

### 8.5 Envelope pesan Kafka

```yaml
envelope:
  schema: pick.v1
  workspace_id: default
  profile_rev: 3f9a1c0b2d7e      # hash hasil kompilasi
  provider: phasenet@1.0.0
  trace_id: 7c1e0a52...
  produced_at: 2026-10-10T08:15:30.120Z
  key: II.KAPI                   # partisi dan idempotensi
payload: {...}                   # sesuai skema artifact
```

### 8.6 Antarmuka provider

```python
from abc import ABC, abstractmethod

class Provider(ABC):
    stage: str

    def __init__(self, params, ctx):
        self.params, self.ctx = params, ctx

    def warmup(self):
        '''Muat bobot dan sumber daya. Dipanggil SEBELUM provider ditukar.'''

    @abstractmethod
    def process(self, batch):
        '''Daftar Envelope masuk -> daftar Envelope keluar.'''

    def close(self):
        '''Lepas sumber daya.'''
```

Provider didaftarkan lewat `entrypoint` di manifest; modul tahap hanya tahu `Provider`, bukan implementasinya.

### 8.7 Loop runtime tahap (Stage SDK)

```python
class StageRuntime:
    def run(self):
        snap = self.config.load_local() or self.config.fetch()   # snapshot terakhir tersimpan
        self.apply(snap)
        self.config.watch(self.on_snapshot)                      # dengar config_events
        while self.alive:
            if not self.state.enabled:
                self.consumer.pause(); self.heartbeat(); time.sleep(1); continue
            msgs = self.consumer.poll(timeout_ms=500)
            out = self.provider.process(msgs)
            self.producer.send_all(out, profile_rev=self.state.rev)
            self.consumer.commit()

    def on_snapshot(self, snap):
        if snap.rev == self.state.rev:
            return
        new = load_provider(snap)
        try:
            new.warmup()                    # gagal -> lapor failed, tetap pakai provider lama
        except Exception as e:
            return self.report_failed(snap.rev, e)
        with self.swap_lock:                # tukar atomik di batas batch
            old, self.provider = self.provider, new
            self.state = snap.state()
        old.close(); self.report_applied(snap.rev)
```

### 8.8 Reconciler (Orchestrator)

```python
def reconcile(workspace):
    desired = profiles.active(workspace)             # revisi aktif, sudah dikompilasi
    for st in desired.all_stages():                  # termasuk yang nonaktif
        actual = heartbeats.get(workspace, st.stage)
        if actual.rev != desired.rev:
            publish(key=workspace + '.' + st.stage, value=st.snapshot(desired.rev))
    if all_applied(desired):
        profiles.mark_good(workspace, desired.rev)   # jadi last-known-good
    elif waited(desired) > APPLY_TIMEOUT:
        profiles.rollback_to_lkg(workspace); alert(workspace, desired.rev)
```

### 8.9 API v2

| Metode | Path | Fungsi | Peran |
| --- | --- | --- | --- |
| GET | `/api/v2/catalog/stages`, `/catalog/providers?stage=` | Katalog tahap dan provider | semua |
| GET | `/api/v2/presets` | Daftar preset dan ringkasannya | semua |
| GET, POST | `/api/v2/workspaces/{ws}/profiles` | Daftar profil, buat draft | operator ke atas |
| GET | `.../profiles/{id}/revisions` | Riwayat revisi | viewer ke atas |
| POST | `.../profiles/{id}/validate` | Validasi, kembalikan daftar isu | operator ke atas |
| POST | `.../profiles/{id}/dry-run` | Uji-coba dengan replay | operator ke atas |
| POST | `.../profiles/{id}/activate` | Aktivasi (paket, RBAC, kompilasi) | workspace\_admin |
| POST | `.../profiles/rollback`, `/reset-default` | Kembali ke revisi lama atau ke default | workspace\_admin |
| GET | `.../runtime/status` | Status applied, pending, failed per tahap | viewer ke atas |
| GET | `/api/v2/runtime/{ws}/{stage}/snapshot` | Snapshot untuk modul | service |
| GET | `.../audit` | Jejak perubahan | workspace\_admin |

Contoh respons validasi:

```yaml
ok: false
issues:
  - code: V004
    severity: error
    path: stages.association
    message: membutuhkan [pick] tetapi tidak ada tahap hulu/input eksternal
  - code: W001
    severity: warning
    path: stages.p_pick
    message: keluaran 'pick' tidak dipakai tahap/sink mana pun (boros sumber daya)
```

### 8.10 Pemetaan kunci config lama ke profil

| Kunci lama | Lokasi di profil |
| --- | --- |
| `seedlink.retry_interval`, `seedlink.buffer_size` | `stages.ingest.params.*` |
| `ai.ppick.p_threshold`, `s_threshold`, `batch_size` | `stages.p_pick.params.*` |
| `ai.ppick.model_path` | Provider `phasenet` + `params.weights`; jalur bobot dikelola Model Registry |
| `ai.association.algorithm` | `stages.association.provider` |
| `ai.association.time_threshold`, `distance_threshold`, `min_picks` | `stages.association.params.*` |
| `ai.locmag.algorithm` | `stages.locmag.provider` |
| `ai.locmag.velocity_model`, `magnitude_relation`, `max_iterations` | `stages.locmag.params.velocity_model`, `magnitude_method`, `max_iterations` |
| `websocket.topics`, `websocket.emit_interval` | `sinks.ws_ui.params.artifacts`, `emit_interval` |
| `websocket.max_clients` | Kuota paket (bukan parameter pipeline) |
| `ui.*` | Preferensi UI per pengguna, di luar profil pipeline |

## 9. Rencana Pengembangan dan Eksekusi

### 9.1 Prinsip

Bertahap tanpa big bang: setiap fase dapat dirilis sendiri, ada flag untuk mematikannya, dan sistem lama tetap jalan. Estimasi di bawah mengasumsikan 2 pengembang backend, 1 pengembang frontend, dan seorang seismolog paruh waktu (A); sesuaikan dengan tim Anda.

### 9.2 Fase

| Fase | Tujuan | Deliverable utama | Kriteria selesai | Estimasi (A) |
| --- | --- | --- | --- | --- |
| 0. Persiapan | Fondasi dan keputusan | Inventaris pemakaian kunci config; skema pesan tiap topic; perbaikan keamanan (Bagian 2.4); CI; baseline performa; keputusan tenancy dan paket | Skema topic terdokumentasi dengan contoh nyata; secret dirotasi; keputusan tercatat | 1-2 minggu |
| 1. Config sebagai data | Katalog, profil, validator tanpa mengubah runtime | Katalog + manifest; profil berversi; validator dan compiler dari prototipe; API v2 (baca, validasi, draft); preset `default@1` meniru perilaku sekarang; proyeksi kunci lama; audit log | Golden test: preset default menghasilkan keluaran setara dengan konfigurasi sekarang pada replay yang sama | 2-3 minggu |
| 2. Runtime dapat dikonfigurasi | Mode custom end-to-end | Stage SDK; hot reload; pause tahap nonaktif; `profile_rev` di envelope; status penerapan; LKG dan rollback; wizard UI v1 | Kasus B (P-Pick saja) berjalan end-to-end; AC-2, AC-3, AC-4 lulus | 3-4 minggu |
| 3. Pilihan model dan sink | Provider kedua per tahap | `sta_lta`, `eqtransformer`, `gamma`, `nonlinloc`; Model Registry; harness evaluasi dan replay; webhook dan kafka\_export; input eksternal; dry-run | Tiap provider punya model card dan hasil evaluasi; status dipromosikan berdasarkan hasil | 3-5 minggu |
| 4. Lapisan bisnis | Siap dijual | Workspace; RBAC; paket dan entitlement; kuota; metering; persetujuan dua orang; UI manajemen paket | AC-5 lulus; isolasi antar workspace teruji | 3-4 minggu |
| 5. Skala dan produk | Efisiensi dan diferensiasi | Orchestrator dinamis (start/stop), K8s dan autoscaling, shadow pipeline (A/B model), unggah model sendiri (sandbox), billing | Ditentukan berdasarkan kebutuhan pasar | Berkelanjutan |

Total Fase 0 sampai 4 sekitar 12-18 minggu (A).

### 9.3 Persiapan teknis

- Lingkungan staging terpisah dari yang dipakai demo.
- Repositori dan CI: lint, tes unit, tes kontrak skema pesan, build image.
- Dataset replay: minimal 20 event historis yang beragam (magnitudo, jarak, jumlah stasiun) beserta katalog pembanding. Replay lewat server SeedLink lokal atau miniSEED seperti rencana sebelumnya.
- Secret store dan rotasi kunci; kebijakan password.
- Observability: metrik, log, dashboard dasar sebelum fitur baru.
- Penyimpanan Model Registry (volume atau object storage) dengan checksum.
- Daftar keputusan (Bagian 10.2) dijawab sebelum Fase 1 selesai.

### 9.4 Strategi pengujian

| Jenis | Fokus |
| --- | --- |
| Unit | Domain: katalog, validator, compiler |
| Kontrak | Skema pesan tiap topic dan envelope |
| Golden/regresi | Preset default vs konfigurasi sekarang pada replay yang sama |
| Integrasi | Compose penuh: aktivasi, hot reload, rollback |
| Beban | API config dan throughput pipeline (target NFR-03) |
| Kekacauan | Matikan config-service, Kafka, satu tahap; verifikasi NFR-04 dan LKG |
| Keamanan | RBAC, bypass entitlement lewat API, injeksi parameter |

### 9.5 Migrasi dan peluncuran

1. Fase 1 berjalan berdampingan (dual-run): kunci lama tetap sumber kebenaran, profil menghasilkan proyeksi yang dibandingkan otomatis.
2. Pada Fase 2, aktifkan `PIPELINE_V2` di workspace uji (canary), lalu workspace produksi.
3. Kunci lama menjadi hasil proyeksi (read-only) setelah dua rilis stabil, lalu dihapus bertahap.
4. Setiap langkah punya rencana rollback tertulis.

### 9.6 Definisi selesai

Fitur dianggap selesai bila: kriteria penerimaan lulus, tes otomatis masuk CI, metrik dan alert tersedia, dokumentasi (API, model card, runbook) terbarui, dan rencana rollback teruji.

## 10. Risiko, Pertanyaan Terbuka, dan Langkah Awal

### 10.1 Risiko

| Risiko | Dampak | Mitigasi |
| --- | --- | --- |
| Skema pesan antar modul belum terdokumentasi | Mengganti provider merusak tahap hilir | Dokumentasikan skema dan uji kontrak pada Fase 0 |
| Hot reload menghasilkan hasil tidak konsisten | Event salah atau hilang saat aktivasi | Tukar atomik di batas batch, `profile_rev` di tiap pesan, canary workspace |
| Kombinasi provider menurunkan akurasi | Kepercayaan pelanggan turun | Model card, evaluasi replay, status experimental dan beta yang jelas |
| Biaya GPU dan memori | Margin tipis | Opsi A awal, provider CPU sebagai baseline, kuota paket |
| Model dilatih di wilayah lain | Positif atau negatif palsu di Indonesia | Kalibrasi ambang per wilayah, evaluasi dengan data regional |
| Pembatasan data sumber | Tidak boleh meredistribusi | BR-12, catatan `terms` per sumber |
| Tanggung jawab hukum atas peringatan | Risiko hukum dan reputasi | Disclaimer, verifikasi organisasi, tinjauan hukum (BR-13) |
| Isolasi tenant lemah | Kebocoran data | Filter per workspace, uji keamanan, mulai dari deployment terpisah |
| Kompleksitas UI | Pengguna bingung | Wizard bertahap, preset, validasi langsung |

### 10.2 Pertanyaan terbuka untuk Anda

1. Siapa pelanggan sasaran (institusi pemerintah, universitas, industri, asuransi) dan bagaimana mereka membayar (SaaS atau on-premise)?
2. Satu deployment per pelanggan atau multi-tenant sejak awal?
3. Apa isi `AI_modules_alpha`, `beta`, `neoalpha`? Apakah ada yang siap menjadi provider alternatif?
4. Apakah skema pesan tiap topic Kafka sudah terdokumentasi di suatu tempat, atau perlu direkonstruksi dari data nyata?
5. Apa nilai default produksi saat ini untuk threshold, DBSCAN, dan model kecepatan (untuk mengisi preset `default@1`)?
6. Berapa kapasitas server (CPU, RAM, GPU) dan apakah ada anggaran GPU?
7. Siapa yang menetapkan ambang evaluasi provider (tim seismologi)?
8. Apakah pelanggan akan membawa stasiun sendiri (push\_api) atau memakai sumber publik?
9. Apakah keluaran akan dipakai untuk notifikasi publik (berimplikasi hukum, BR-13)?

### 10.3 Langkah 14 hari pertama

1. **Hari 1-2.** Rotasi JWT secret dan password admin, bersihkan dokumentasi, batasi CORS. Inventaris semua pembacaan config (`getbyname`, `getall`) di setiap modul.
2. **Hari 2-4.** Ambil contoh pesan nyata dari tiap topic Kafka; tulis JSON Schema dan contoh per artifact.
3. **Hari 3-5.** Pindahkan `pipeline_profile.py` ke `controller_module/domain/`; isi katalog dengan nilai produksi sebenarnya; tambah tes untuk preset `default@1`.
4. **Hari 5-7.** Buat koleksi baru dan endpoint baca `/api/v2/catalog`, `/presets`, `validate`; proyeksi kunci lama.
5. **Hari 6-9.** Putar ulang satu event historis lewat pipeline sekarang dan simpan keluarannya sebagai baseline golden test.
6. **Hari 8-10.** Prototipe Stage SDK pada satu modul (p\_pick): pause dan resume, hot reload provider.
7. **Hari 10-12.** Wireframe wizard (empat layar: mode, tahap, parameter, tinjau dan aktifkan) dan tinjau dengan calon pengguna.
8. **Hari 12-14.** Putuskan tenancy dan paket bersama pemangku kepentingan; finalisasi SRS v1.0; rencanakan sprint Fase 1 dan 2.

### 10.4 Referensi kandidat (periksa sitasi lengkap)

PhaseNet (Zhu dan Beroza, 2019); EQTransformer (Mousavi dkk., 2020); GaMMA (Zhu dkk., 2022); SeisBench (Woollam dkk., 2022); PyOcto (Muenchmeyer, 2024); CODEBASE.md v1.0 (2026-10-09) sebagai sumber kondisi sistem saat ini.
