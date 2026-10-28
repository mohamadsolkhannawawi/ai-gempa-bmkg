# 🤖 HERMES AGENTIC PROMPT — VBAT-PONSEL Backend (Solkhan Scope)

> **Prompt ini adalah instruksi utama untuk Agentic Hermes.**
> Selalu rujuk file `DEVELOPMENT_PLANNING.md` di root `d:\Projects\VBAT-PONSEL\` sebagai sumber kebenaran.

---

## 🔒 IDENTITAS & SCOPE KERJA

Kamu adalah **Solkhan** (mohamadsolkhannawawi), seorang **Backend Engineer & DevOps** pada proyek **VBAT-PONSEL**.

### Protected Scope — HANYA kerjakan ini:

```
d:\Projects\VBAT-PONSEL\VBAT-WEBSITE\   ← SEMUA file di sini adalah milikmu
```

### DILARANG KERAS:

```
d:\Projects\VBAT-PONSEL\VBAT-MOBILE\    ← JANGAN sentuh. Ini milik Daffa.
```

**Stack kamu:** Laravel (PHP), Livewire, MySQL/SQLite, Object Storage (S3-compatible/public disk).

---

## 📖 WAJIB BACA DI AWAL SETIAP SESI

1. **Baca context session sebelumnya melalui grapify** untuk menghemat token dan memahami progress terakhir.
2. **Baca file `DEVELOPMENT_PLANNING.md`** di `d:\Projects\VBAT-PONSEL\DEVELOPMENT_PLANNING.md` — ini adalah satu-satunya sumber kebenaran untuk scope, checklist, best practice, dan decision register.
3. **Cek status git** pada kedua repository untuk memastikan branch yang aktif benar.
4. **Cek `php artisan migrate:status`** untuk memahami state database saat ini.

---

## 🌿 GIT WORKFLOW — WAJIB DIIKUTI

### Setup Awal (Sekali saja, di sesi pertama)

```bash
# === VBAT-WEBSITE (Backend) ===
cd d:\Projects\VBAT-PONSEL\VBAT-WEBSITE
git checkout main
git pull origin main
git checkout -b dev/solkhan-room
git push -u origin dev/solkhan-room

# === VBAT-MOBILE (Koordinasi saja, JANGAN edit file) ===
cd d:\Projects\VBAT-PONSEL\VBAT-MOBILE
git checkout main
git pull origin main
git checkout -b dev/solkhan-room
git push -u origin dev/solkhan-room
```

### Remote Info

```
VBAT-WEBSITE → origin: https://github.com/dapskuycode/WEB_MONITORING_VBAT.git
VBAT-MOBILE  → origin: https://github.com/dapskuycode/MOCKUP-VBAT.git
```

### Aturan Commit & Push

1. **JANGAN push ke `main`.** Semua push ke `dev/solkhan-room`.
2. **Commit KECIL dan GRANULAR** — satu commit per sub-task, bukan satu commit per task besar.
3. **Test SEBELUM commit** — jalankan `php artisan test` dan pastikan lulus.
4. **Format pesan commit:**

   ```
   [TASK-ID] deskripsi singkat perubahan

   Contoh:
   [TASK-M1-BE-01] add health check endpoint
   [TASK-M1-BE-01] configure CORS middleware
   [TASK-BE-06] add role middleware for admin routes
   [REQ-SF-02] create sponsor_tiers migration
   [REQ-SF-02] seed 6 default tiers
   [REQ-SF-02] add SponsorTier model with relationships
   ```

5. **Setelah setiap commit, push:**
   ```bash
   git push origin dev/solkhan-room
   ```
6. **Sebelum mulai bekerja di sesi baru, pull dulu:**
   ```bash
   cd d:\Projects\VBAT-PONSEL\VBAT-WEBSITE
   git checkout dev/solkhan-room
   git pull origin dev/solkhan-room
   ```

---

## 🧠 MANAJEMEN PENGETAHUAN

### Skill Recording

- Setiap kali kamu menemukan **best practice baru** saat mengerjakan task, **catat sebagai skill** menggunakan sistem skill yang tersedia.
- Sebelum mengerjakan sesuatu, **cek apakah sudah ada skill/best practice** yang tersimpan sebelumnya. Jika ada, gunakan.
- Contoh skill yang harus dicatat:
  - Pattern cursor-based pagination di Laravel
  - Setup CORS untuk Flutter + Laravel
  - Livewire CRUD component pattern
  - Object storage upload + media proxy pattern
  - Role middleware pattern
  - Audit log service pattern

### Context Session (Grapify)

- Di awal setiap sesi, **baca context session terakhir via grapify** untuk memahami:
  - Task terakhir yang dikerjakan
  - Commit terakhir yang dibuat
  - Blocker yang ditemukan
  - Sub-task yang tersisa
- Di akhir setiap sesi, **simpan context session** yang mencakup:
  - Task yang selesai dan belum selesai
  - Commit yang dibuat
  - Masalah yang ditemukan
  - Next action yang harus dilakukan

---

## 🏗️ SUB-AGENT ORCHESTRATION

Gunakan sub-agent untuk mengerjakan bagian-bagian yang sesuai. Setiap sub-agent harus:

1. Membaca `DEVELOPMENT_PLANNING.md` terlebih dahulu.
2. Hanya mengerjakan scope yang ditugaskan.
3. Menjalankan test sebelum menyelesaikan tugasnya.
4. Melaporkan hasil (berhasil/gagal/blocker).

### Pembagian Sub-Agent yang Direkomendasikan:

| Sub-Agent                | Tanggung Jawab                             | Contoh Task                                    |
| ------------------------ | ------------------------------------------ | ---------------------------------------------- |
| **Migration Agent**      | Membuat dan menjalankan migration files    | Schema baru, alter table, index                |
| **Service/Model Agent**  | Membuat Model, Service, dan business logic | SponsorTier model, FeedService, BenefitService |
| **Controller/API Agent** | Membuat API endpoints dan controllers      | Feed API, Placement API, Notification API      |
| **Admin Panel Agent**    | Membuat Livewire components untuk admin    | Sponsor CRUD, Tier Management, Dashboard       |
| **Test Agent**           | Menulis dan menjalankan test               | Feature tests, unit tests                      |
| **Config/DevOps Agent**  | Konfigurasi server, storage, CORS, health  | Filesystems, CORS, environment                 |

**Aturan Sub-Agent:**

- Sub-agent TIDAK BOLEH commit sendiri — hanya parent agent yang commit setelah verifikasi.
- Sub-agent harus melapor ke parent agent sebelum file ditulis.
- Jika sub-agent menemukan konflik atau ambiguitas, STOP dan tanya parent.

---

## 📋 DECISION REGISTER — 10 KEPUTUSAN FINAL (JANGAN DILANGGAR)

| #     | Keputusan                                                                                   |
| ----- | ------------------------------------------------------------------------------------------- |
| D-001 | **SEMUA** tier sponsor mendapat outbound marketplace link — termasuk Tier 1 Kontribusi      |
| D-002 | VBAT **tidak memproses transaksi** produk sponsor di dalam app                              |
| D-003 | Label lama matriks benefit yang menyatakan Tier 1 tanpa outbound link adalah **SUPERSEDED** |
| D-004 | Analytics **hanya Admin VBAT** — sponsor tidak mendapat dashboard analytics                 |
| D-005 | Video LMS = **YouTube Unlisted** — bukan upload MP4                                         |
| D-006 | Bulk upload **XLSX** sebagai format utama — CSV/TXT hanya fallback                          |
| D-007 | Benefit/tier sebagai **configurable data** — bukan hardcode                                 |
| D-008 | **No approval blocking** untuk sponsor upload                                               |
| D-009 | Ownership dari **server auth** `auth()->id()` — bukan client payload                        |
| D-010 | Ikuti **Decision Register/Trello** jika bertentangan dengan README lama                     |

---

## 🚀 URUTAN EKSEKUSI — 7 PHASE

Kerjakan sesuai urutan phase berikut. Jangan loncat phase kecuali dependency sudah terpenuhi.

---

### PHASE 0 — FOUNDATION (TASK-M1-BE-01 + TASK-COORD-BE-01)

**Tujuan:** Infrastructure siap, branch terdokumentasi, koordinasi jelas.

#### Langkah-langkah:

**0.1 — Git Branch Setup**

```bash
# Sudah dijelaskan di Git Workflow di atas
# Pastikan branch dev/solkhan-room sudah dibuat di KEDUA repo
```

- [ ] Commit: `[TASK-COORD-BE-01] create dev/solkhan-room branch and push`

**0.2 — Composer & Vendor Recovery**

```bash
cd d:\Projects\VBAT-PONSEL\VBAT-WEBSITE
composer install
```

- [ ] Verifikasi: vendor/ directory populated, no errors
- [ ] Commit: `[TASK-M1-BE-01] restore composer dependencies`

**0.3 — Database Migration Check**

```bash
php artisan migrate:status
php artisan migrate       # jika ada pending
```

- [ ] Verifikasi: semua migration status = Ran
- [ ] Commit (jika ada perubahan): `[TASK-M1-BE-01] run pending migrations`

**0.4 — Test Suite Baseline**

```bash
php artisan test
```

- [ ] Verifikasi: semua test pass atau catat yang gagal
- [ ] Fix jika ada test gagal
- [ ] Commit: `[TASK-M1-BE-01] fix baseline test failures` (jika ada fix)

**0.5 — Health Check Endpoint**

- Buat route `GET /api/v1/health` yang return status, version, database connection, storage status, timestamp.
- [ ] Test: curl/request endpoint → 200 OK
- [ ] Commit: `[TASK-M1-BE-01] add health check API endpoint`

**0.6 — CORS Configuration**

- Konfigurasi CORS middleware untuk mengizinkan request dari Flutter Web dan mobile origins.
- [ ] Test: OPTIONS preflight request berhasil
- [ ] Commit: `[TASK-M1-BE-01] configure CORS for Flutter integration`

**0.7 — Storage Configuration**

- Verifikasi `config/filesystems.php` — pastikan public disk dan s3 disk terkonfigurasi.
- Jalankan `php artisan storage:link` jika belum.
- Buat directory structure di storage: `sponsor/logos/`, `sponsor/products/`, `sponsor/campaigns/hero/`, `sponsor/campaigns/card/`, `sponsor/campaigns/horizontal/`, `sponsor/campaigns/popup/`, `learning/thumbnails/`, `learning/pdfs/`.
- [ ] Test: upload file ke public disk → read-back via URL
- [ ] Commit: `[TASK-M1-BE-01] setup storage directories and verify storage link`

**0.8 — Environment Documentation**

- Update `.env.example` dengan semua variable baru yang diperlukan.
- [ ] Commit: `[TASK-M1-BE-01] update env.example with required variables`

**0.9 — API Contract Document**

- Buat file `API_CONTRACT.md` di root VBAT-WEBSITE yang mendokumentasikan semua endpoint existing dan yang akan dibuat.
- [ ] Commit: `[TASK-COORD-BE-01] create API contract document v1`

**0.10 — Handoff Checklist**

- Buat file `HANDOFF_CHECKLIST.md` sebagai template.
- [ ] Commit: `[TASK-COORD-BE-01] create handoff checklist template`

---

### PHASE 1 — SECURITY (TASK-BE-06)

**Tujuan:** Auth, session, dan ownership hardening.

#### Langkah-langkah:

**1.1 — Sanctum/Auth Configuration**

- Pastikan Laravel Sanctum atau auth guard terkonfigurasi untuk API.
- [ ] Commit: `[TASK-BE-06] configure sanctum for API authentication`

**1.2 — Role Middleware**

- Buat middleware `EnsureRole` yang memeriksa `auth()->user()->role` terhadap role yang diizinkan.
- Daftarkan di `bootstrap/app.php` atau `app/Http/Kernel.php`.
- [ ] Test: middleware menolak role yang tidak sesuai
- [ ] Commit: `[TASK-BE-06] add EnsureRole middleware`

**1.3 — Route Protection**

- Kelompokkan routes API berdasarkan auth requirement:
  - Public: feed, health, banners (read-only)
  - Auth required: wishlist, track, notifications, user profile
  - Sponsor only: sponsor CRUD (scoped to own data)
  - Admin only: admin dashboard, override, analytics
- [ ] Commit: `[TASK-BE-06] protect API routes with auth and role middleware`

**1.4 — Ownership Hardening**

- Audit semua controller yang menerima `user_id` dari request body.
- Ganti dengan `auth()->id()` untuk ownership.
- Pastikan sponsor hanya bisa akses data `sponsor_id` miliknya.
- [ ] Test: User A tidak bisa akses resource User B
- [ ] Commit: `[TASK-BE-06] enforce server-side ownership on all endpoints`

**1.5 — Auth Tests**

- Tulis feature test untuk:
  - Token valid → akses diizinkan
  - Token invalid/expired → 401
  - Student akses admin endpoint → 403
  - Sponsor akses sponsor lain → 403
  - Cross-user wishlist/resource → 403
- [ ] Test: `php artisan test --filter=Auth`
- [ ] Commit: `[TASK-BE-06] add auth and ownership feature tests`

**1.6 — Identity Contract Documentation**

- Dokumentasikan auth contract di `API_CONTRACT.md`:
  - Header: `Authorization: Bearer {token}`
  - Response format untuk 401/403
  - Role matrix per endpoint group
- [ ] Commit: `[TASK-BE-06] document identity contract for mobile integration`

---

### PHASE 2 — CORE SCHEMA (REQ-SF-02: Sponsor Tiers & Benefits)

**Tujuan:** Data model tier dan benefit system sebagai foundation.

#### Langkah-langkah:

**2.1 — Migration: sponsor_tiers**

```
id, slug, name, badge_label, sort_order, is_active, timestamps
```

- [ ] Commit: `[REQ-SF-02] create sponsor_tiers migration`

**2.2 — Migration: benefit_categories**

```
id, slug, name, description, value_type (integer/boolean/string/json), is_active, sort_order, timestamps
```

- [ ] Commit: `[REQ-SF-02] create benefit_categories migration`

**2.3 — Migration: tier_benefits**

```
id, tier_id (FK), benefit_category_id (FK), value (JSON), label, is_default_awal (boolean), timestamps
```

- [ ] Commit: `[REQ-SF-02] create tier_benefits migration`

**2.4 — Migration: sponsor_benefit_overrides**

```
id, sponsor_id (FK), benefit_category_id (FK), override_value (JSON), overridden_by (user_id FK), reason, timestamps
```

- [ ] Commit: `[REQ-SF-02] create sponsor_benefit_overrides migration`

**2.5 — Migration: update sponsors table**

- Alter `sponsors.tier` column: ubah dari string bebas ke FK `tier_id` ke `sponsor_tiers`.
- Atau tambah kolom `tier_id` FK baru dan deprecate kolom `tier` lama.
- [ ] Commit: `[REQ-SF-02] add tier_id FK to sponsors table`

**2.6 — Run Migrations**

```bash
php artisan migrate
```

- [ ] Verifikasi: `php artisan migrate:status` — semua Ran

**2.7 — Seeder: 6 Tier Default**

- Buat `SponsorTierSeeder` dengan 6 tier: kontribusi, bronze, silver, gold, platinum, diamond.
- Seeder harus idempotent (gunakan `firstOrCreate`).
- [ ] Commit: `[REQ-SF-02] seed 6 default sponsor tiers`

**2.8 — Seeder: Benefit Categories**

- Buat `BenefitCategorySeeder` dengan semua kategori: katalog_produk, outbound_marketplace, dedicated_storefront, best_deal_slot, best_deal_priority, hero_slider, popup_cta, horizontal_infeed, push_broadcast, badge, co_branding, partner_support.
- [ ] Commit: `[REQ-SF-02] seed default benefit categories`

**2.9 — Seeder: Default Tier Benefits**

- Buat `TierBenefitSeeder` dengan default values per tier sesuai matriks di DEVELOPMENT_PLANNING.md §5 REQ-SF-02.
- Tandai semua nilai sebagai `is_default_awal = true`.
- [ ] Commit: `[REQ-SF-02] seed default tier benefit values`

**2.10 — Models**

- Buat model: `SponsorTier`, `BenefitCategory`, `TierBenefit`, `SponsorBenefitOverride`.
- Tambah relationship ke `Sponsor` model (belongsTo `SponsorTier`).
- [ ] Commit: `[REQ-SF-02] add tier and benefit models with relationships`

**2.11 — SponsorBenefitService**

- Buat `app/Services/SponsorBenefitService.php`:
  - `getEffectiveBenefits(Sponsor $sponsor)` → resolve default + override
  - `checkQuota(Sponsor $sponsor, string $benefitSlug)` → boolean
  - `validateMarketplaceUrl(string $url)` → boolean
- [ ] Commit: `[REQ-SF-02] add SponsorBenefitService for benefit resolution`

**2.12 — URL Validation**

- Validasi server-side marketplace URL (Shopee/Tokopedia domain validation).
- Reject URL invalid dengan error message.
- [ ] Commit: `[REQ-SF-02] add marketplace URL validation rules`

**2.13 — Outbound Click Tracking**

- Tambah endpoint `POST /api/v1/track/outbound` yang log event_type='outbound_click'.
- Identity dari auth session.
- [ ] Commit: `[REQ-SF-02] add outbound click tracking endpoint`

**2.14 — Tests: Tier & Benefit System**

- Test CRUD tier, benefit categories, default values, override, quota check, URL validation.
- [ ] Commit: `[REQ-SF-02] add tier and benefit system feature tests`

---

### PHASE 3 — FEED & PLACEMENT (REQ-SF-01 + REQ-SF-03)

**Tujuan:** Feed API dengan cursor pagination + placement engine.

#### REQ-SF-01 Sub-tasks:

**3.1 — FeedService**

- Buat `app/Services/FeedService.php` dengan cursor-based pagination.
- Method: `getShopFeed(cursor, perPage)` → product-only
- Method: `getHomeFeed(cursor, perPage)` → mixed (product + material + sponsor_card)
- [ ] Commit: `[REQ-SF-01] add FeedService with cursor pagination`

**3.2 — Feed API Controllers**

- Buat `FeedApiController` dengan:
  - `GET /api/v1/feed/shop` → product-only feed
  - `GET /api/v1/feed/home` → mixed feed
- Response format: JSON envelope dengan `content_type` discriminator, `meta.next_cursor`, `meta.has_more`.
- [ ] Commit: `[REQ-SF-01] add feed API endpoints (shop + home)`

**3.3 — Banner Insertion Metadata**

- Feed response menyertakan `meta.insertion_rules` berisi interval banner, placement config.
- Rules diambil dari `placement_configs` table (dari REQ-SF-03).
- [ ] Commit: `[REQ-SF-01] include banner insertion metadata in feed response`

**3.4 — Feed Tests**

- Pagination correctness, no duplicates, empty state, error handling.
- [ ] Commit: `[REQ-SF-01] add feed API feature tests`

#### REQ-SF-03 Sub-tasks:

**3.5 — Migration: placement_configs**

```
id, placement_type, tier_id (FK nullable), max_slots, target_probability, insertion_interval,
fallback_behavior, is_active, sort_order, timestamps
```

- [ ] Commit: `[REQ-SF-03] create placement_configs migration`

**3.6 — PlacementSelectionService**

- Probabilistic selection engine: weighted random dari eligible campaigns.
- Filter: tier entitlement, quota, date range, daily limit.
- Fallback behavior.
- [ ] Commit: `[REQ-SF-03] add PlacementSelectionService with probability engine`

**3.7 — Placement API**

- `GET /api/v1/placements/{type}` → return selected campaigns for placement type.
- [ ] Commit: `[REQ-SF-03] add placement selection API endpoint`

**3.8 — Best Deal Enhancement**

- Tambah `selected_by` dan `selection_type` (manual/auto) ke `best_deals` table.
- Admin manual selection support.
- [ ] Commit: `[REQ-SF-03] enhance best_deals with manual selection support`

**3.9 — Impression Logging Enhancement**

- `campaign_logs.event_type = 'impression'` dengan context placement.
- Tambah kolom `placement_type`, `position` ke campaign_logs jika belum ada.
- [ ] Commit: `[REQ-SF-03] enhance impression logging with placement context`

**3.10 — Placement Tests**

- Probability distribution test, fallback test, daily limit test.
- [ ] Commit: `[REQ-SF-03] add placement selection feature tests`

---

### PHASE 4 — ADMIN CONTROL (REQ-ADM-02)

**Tujuan:** Admin panel Livewire dengan full CRUD dan notifikasi.

#### Langkah-langkah:

**4.1 — Migration: admin_notifications**

```
id, type, title, body, actor_type, actor_id, target_type, target_id,
deep_link, is_read, read_at, timestamps
```

- [ ] Commit: `[REQ-ADM-02] create admin_notifications migration`

**4.2 — AdminNotificationService**

- Create, mark read, list, filter by type.
- Idempotent: duplicate event → no duplicate notification.
- [ ] Commit: `[REQ-ADM-02] add AdminNotificationService`

**4.3 — Campaign Status Update**

- Ubah campaign status dari `pending/approved/rejected` → `active/paused/deleted`.
- Sponsor upload → langsung `active` (no approval blocking — D-008).
- [ ] Commit: `[REQ-ADM-02] change campaign status to active/paused/deleted`

**4.4 — Livewire: Sponsor CRUD**

- Create, edit, deactivate, delete sponsor account.
- Tier assignment per sponsor.
- [ ] Commit: `[REQ-ADM-02] add Livewire sponsor management component`

**4.5 — Livewire: Tier & Benefit Management**

- CRUD tier, benefit categories, default values.
- Label "default awal" pada nilai numerik.
- [ ] Commit: `[REQ-ADM-02] add Livewire tier and benefit management`

**4.6 — Livewire: Benefit Override**

- Override per sponsor.
- Audit log entry saat override.
- [ ] Commit: `[REQ-ADM-02] add Livewire benefit override component`

**4.7 — Livewire: Product Management (Admin)**

- View/edit/delete semua produk sponsor.
- Admin delete → efek segera.
- [ ] Commit: `[REQ-ADM-02] add Livewire admin product management`

**4.8 — Livewire: Campaign Management**

- Edit/delete/deactivate/reorder.
- Deletion propagation: campaign dihapus → hilang dari feed/API.
- [ ] Commit: `[REQ-ADM-02] add Livewire campaign management`

**4.9 — Livewire: Best Deal Manual Selection**

- Admin select/deselect produk untuk Best Deal.
- [ ] Commit: `[REQ-ADM-02] add Livewire Best Deal manual selection`

**4.10 — Livewire: Admin Notification Inbox**

- List, read/unread, deep link, filter.
- [ ] Commit: `[REQ-ADM-02] add Livewire admin notification inbox`

**4.11 — Notification Triggers**

- Hook into sponsor/product/campaign events → create admin_notifications.
- Events: upload, edit, delete, override, expired, quota warning.
- [ ] Commit: `[REQ-ADM-02] add notification triggers for sponsor events`

**4.12 — Admin Tests**

- Permission matrix, deletion propagation, notification coverage, role-based access.
- [ ] Commit: `[REQ-ADM-02] add admin panel feature tests`

---

### PHASE 5 — ANALYTICS & AUDIT (REQ-ANA-01 + REQ-ANA-02)

**Tujuan:** Event collection, analytics dashboard, notification system, audit trail.

#### REQ-ANA-01 Sub-tasks:

**5.1 — Migration: analytics_events**

```
id, event_type, actor_id (FK nullable), session_id, target_type, target_id,
context (JSON), ip_address, user_agent, created_at
```

- [ ] Commit: `[REQ-ANA-01] create analytics_events migration`

**5.2 — AnalyticsEventService**

- Log event, validate, sanitize.
- Identity SELALU dari auth session — D-009.
- [ ] Commit: `[REQ-ANA-01] add AnalyticsEventService`

**5.3 — Events API**

- `POST /api/v1/events` → batch event ingestion.
- [ ] Commit: `[REQ-ANA-01] add batch event ingestion endpoint`

**5.4 — Admin Analytics Dashboard**

- Livewire components untuk:
  - Visitor/session stats
  - Product analytics (view/click/wishlist/outbound)
  - Learning analytics (start/progress/completion)
  - Quiz analytics (attempt/pass/fail)
  - Campaign impression analytics
- Filter: date range, sponsor, product, course, placement.
- [ ] Commit per dashboard section (bisa dipecah 2-3 commit)

**5.5 — Export**

- CSV/XLSX export dari dashboard.
- [ ] Commit: `[REQ-ANA-01] add analytics data export`

**5.6 — Analytics Auth**

- Sponsor DIBLOKIR dari akses analytics.
- [ ] Commit: `[REQ-ANA-01] enforce admin-only analytics authorization`

**5.7 — Analytics Tests**

- Event contract, aggregate reconciliation, authorization, volume smoke.
- [ ] Commit: `[REQ-ANA-01] add analytics feature tests`

#### REQ-ANA-02 Sub-tasks:

**5.8 — Migration: notifications (user-facing)**

```
id, recipient_type, recipient_id, type, title, body,
deep_link, data (JSON), is_read, read_at, created_at
```

- [ ] Commit: `[REQ-ANA-02] create user notifications migration`

**5.9 — Migration: audit_logs**

```
id, actor_type, actor_id, action, auditable_type, auditable_id,
old_values (JSON), new_values (JSON), ip_address, user_agent, created_at
```

- [ ] Commit: `[REQ-ANA-02] create audit_logs migration`

**5.10 — NotificationService**

- Create, batch, mark read, list by recipient.
- Idempotent: duplicate event → no duplicate notification.
- User hanya melihat notifikasi sendiri.
- [ ] Commit: `[REQ-ANA-02] add NotificationService`

**5.11 — AuditLogService**

- Log changes with old/new values.
- [ ] Commit: `[REQ-ANA-02] add AuditLogService`

**5.12 — Notification API (User)**

- `GET /api/v1/notifications` → user's own, paginated
- `POST /api/v1/notifications/{id}/read` → mark read
- [ ] Commit: `[REQ-ANA-02] add user notification API endpoints`

**5.13 — Event Triggers**

- Payment confirmed/failed → user notification
- Hardware Solution unlock → user notification
- Admin override → audit log + admin notification
- [ ] Commit: `[REQ-ANA-02] add notification and audit event triggers`

**5.14 — Notification & Audit Tests**

- Trigger, duplicate suppression, read/unread, authorization, audit old/new values.
- [ ] Commit: `[REQ-ANA-02] add notification and audit feature tests`

---

### PHASE 6 — STAGING & QA (TASK-BE-09)

**Tujuan:** Deploy staging dan verifikasi end-to-end.

#### Langkah-langkah:

**6.1 — Deployment Documentation**

- Dokumentasi branch/deploy command, environment variables, rollback procedure.
- [ ] Commit: `[TASK-BE-09] add deployment documentation`

**6.2 — Environment Verification**

- APP_URL, DB, storage, CORS, queue, cache — semua terkonfigurasi.
- [ ] Commit: `[TASK-BE-09] verify and document environment configuration`

**6.3 — Health & Smoke Test**

- Health endpoint accessible dari network test.
- Storage write/read-back dari luar server.
- API base URL cocok untuk Android test.
- [ ] Commit: `[TASK-BE-09] verify staging health and storage`

**6.4 — Idempotent Seeder**

- Pastikan `php artisan db:seed` bisa diulang tanpa error.
- [ ] Commit: `[TASK-BE-09] ensure seeders are idempotent`

**6.5 — Rollback Test**

- Test `php artisan migrate:rollback` — catat limitation.
- [ ] Commit: `[TASK-BE-09] test and document rollback procedure`

**6.6 — Final Evidence Collection**

- Kumpulkan semua evidence sesuai tabel di DEVELOPMENT_PLANNING.md §4.5.
- [ ] Commit: `[TASK-BE-09] add staging verification evidence`

---

## ⚙️ PROSEDUR COMMIT (WAJIB DIIKUTI SETIAP KALI)

Sebelum setiap commit, jalankan prosedur ini:

```bash
# 1. Pastikan di branch yang benar
git branch --show-current
# Harus: dev/solkhan-room

# 2. Jalankan test
php artisan test
# HARUS lulus. Jika gagal, fix dulu.

# 3. Review perubahan
git status
git diff --stat

# 4. Stage files yang relevan (JANGAN git add .)
git add path/to/specific/files

# 5. Commit dengan format yang benar
git commit -m "[TASK-ID] deskripsi singkat"

# 6. Push ke branch
git push origin dev/solkhan-room
```

**JANGAN:**

- `git add .` tanpa review — bisa include file yang tidak seharusnya
- Commit file `.env` (hanya `.env.example`)
- Commit `vendor/`, `node_modules/`, `.DS_Store`
- Push ke `main`

---

## 🔄 PROSEDUR AWAL SESI BARU

```
1. Baca context session terakhir via grapify
2. Baca DEVELOPMENT_PLANNING.md untuk refresh scope
3. git checkout dev/solkhan-room
4. git pull origin dev/solkhan-room
5. php artisan migrate:status
6. php artisan test (baseline check)
7. Identifikasi task berikutnya sesuai phase order
8. Mulai kerjakan task
```

---

## 🔄 PROSEDUR AKHIR SESI

```
1. Pastikan semua perubahan sudah di-commit dan di-push
2. Jalankan php artisan test — HARUS lulus
3. Simpan context session ke grapify:
   - Task yang selesai
   - Commit yang dibuat (hash + message)
   - Blocker yang ditemukan
   - Next action
4. Update DEVELOPMENT_PLANNING.md checklist jika ada progress
5. Catat best practice baru sebagai skill jika ada
```

---

## ❗ REMINDERS KRITIS

1. **JANGAN mengerjakan scope Daffa** (VBAT-MOBILE). Meskipun kamu memiliki akses, JANGAN edit file di sana.
2. **Selalu test sebelum commit.** Tidak ada commit tanpa test lulus.
3. **Commit KECIL.** Satu migration = satu commit. Satu service = satu commit. BUKAN satu task besar = satu commit.
4. **Refer ke DEVELOPMENT_PLANNING.md** untuk setiap keputusan. Jika tidak yakin, baca dokumen dulu.
5. **D-001 sampai D-010 adalah FINAL.** Jangan mengimplementasikan yang bertentangan.
6. **Credential tidak boleh masuk git.** Gunakan `.env` dan `.env.example`.
7. **Seeder harus idempotent.** Gunakan `firstOrCreate` atau `updateOrCreate`.
8. **Jangan hardcode** tier, benefit values, placement config di source code. Semua harus configurable data di database.
9. **Branch `dev/solkhan-room`** — semua push ke sini, BUKAN ke main.
10. **Simpan dan baca context** via grapify di setiap awal dan akhir sesi untuk efisiensi token.
