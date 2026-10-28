# 📋 VBAT-PONSEL — Development Planning Master Document

> **Proyek:** VBAT-PONSEL (Aplikasi Mobile & Admin Panel)
> **Stack:** Laravel (Backend/Admin) · MySQL/SQLite (Database) · S3-Compatible (Storage)
> **Developer:** Solkhan (mohamadsolkhannawawi)
> **Role:** Backend Engineer & DevOps
> **Tanggal Dibuat:** 23 September 2026
> **Status:** 🟡 Active Development

---

## Daftar Isi

1. [Ringkasan Proyek & Arsitektur](#1-ringkasan-proyek--arsitektur)
2. [Peran & Tanggung Jawab](#2-peran--tanggung-jawab)
3. [Konvensi & Best Practice](#3-konvensi--best-practice)
4. [Prosedur Kerja (SOP Development)](#4-prosedur-kerja-sop-development)
5. [Task Planning Detail](#5-task-planning-detail)
6. [Master Checklist](#6-master-checklist)
7. [Catatan Krusial & Decision Register](#7-catatan-krusial--decision-register)

---

## 1. Ringkasan Proyek & Arsitektur

### 1.1 Gambaran Umum

VBAT-PONSEL adalah platform tech-learning untuk teknisi ponsel yang terdiri dari:

| Komponen | Teknologi | Repository |
|----------|-----------|------------|
| **Mobile App** | Flutter (Dart) | `VBAT-MOBILE/` |
| **Backend & Admin Panel** | Laravel (PHP) + Livewire | `VBAT-WEBSITE/` |
| **Database** | SQLite (dev) / MySQL (staging/prod) | Managed via Laravel Migrations |
| **Object Storage** | Local Public / S3-compatible | `config/filesystems.php` |

### 1.2 Arsitektur Tingkat Tinggi

```
┌─────────────────────────────────────────────────────────────────┐
│                        FLUTTER MOBILE APP                       │
│  lib/                                                           │
│  ├── core/network/api_client.dart  (Dio HTTP)                   │
│  ├── features/home/       → Beranda (mixed feed)                │
│  ├── features/shop/       → Shop (product-only feed)            │
│  ├── features/belajar/    → LMS (courses, lessons, videos)      │
│  ├── features/notifikasi/ → In-App Notifications                │
│  └── features/profile/    → User Profile & Settings             │
└─────────────────┬───────────────────────────────────────────────┘
                  │ REST API (JSON)
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LARAVEL BACKEND + ADMIN                       │
│  routes/api.php         → /api/v1/* (Mobile API)                │
│  routes/web.php         → Admin Panel (Livewire)                │
│  app/Models/            → Sponsor, SponsorProduct, Campaign,    │
│                           BestDeal, Course, Lesson, Video, User │
│  app/Http/Controllers/Api/ → CampaignApi, TrackerApi, etc.      │
│  app/Livewire/          → Admin Livewire Components             │
│  database/migrations/   → Schema definitions                    │
│  database/seeders/      → Legacy + BestDeal seeders             │
│  config/filesystems.php → local/public/s3 disk config           │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│           DATABASE + OBJECT STORAGE                             │
│  Tables: users, sponsors, sponsor_products, campaigns,          │
│          campaign_logs, user_wishlists, best_deals,             │
│          best_deal_products, courses, lessons, videos,           │
│          discount_events, push_notifications, ...               │
│  Storage: sponsor/*, learning/*, campaigns/*                    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Kondisi Existing yang Harus Diperhatikan

| Area | Status Saat Ini | Yang Harus Diperbaiki |
|------|----------------|-----------------------|
| **Tier Sponsor** | Kolom `tier` di migration = `partner` (lama: platinum/gold/silver/partner) | Migrasi ke 6 tier baru: kontribusi/bronze/silver/gold/platinum/diamond |
| **Bulk Upload** | `class-bulk-upload.blade.php` hanya CSV/TXT, duration default 600s | Upgrade ke XLSX, validasi YouTube unlisted, unit/PDF support |
| **LMS Schema** | courses → lessons → videos (flat) | Tambah: units, PDF materials, quiz relations, progress, bookmark, entitlement, import_logs |
| **Filesystems** | local/public/s3 dasar, belum terverifikasi | CORS, URL publik/proxy, retention, metadata file di DB |
| **API Auth** | Token auth commented out di `api_client.dart` | Implementasi auth principal, ownership hardening |
| **Campaigns** | Status `pending/approved/rejected` (approval-based) | Sesuaikan policy: sponsor upload tanpa blocking approval |
| **Role System** | `super_admin/owner/sponsor/student` | Verifikasi endpoint per role, student ≠ sponsor ≠ admin |

---

## 2. Peran & Tanggung Jawab

### 2.1 Developer & Scope

Seluruh task backend & DevOps dikerjakan oleh **Solkhan** (`mohamadsolkhannawawi`) sebagai **Backend Engineer & DevOps**.

| Scope | Repository | Tanggung Jawab Solkhan |
|-------|-----------|------------------------|
| **Backend & Admin Panel** | `VBAT-WEBSITE/` | API endpoints, database migrations, seeders, Livewire Admin Panel, object storage integration, auth & session hardening, staging deployment |
| **Mobile App (Protected Scope)** | `VBAT-MOBILE/` | **DILARANG DIUBAH.** Scope khusus Mobile/Flutter (Daffa). Backend hanya menyediakan API contract & handoff documentation. |

### 2.2 Peran per Requirement

| Requirement | Peran Backend | Peran Mobile |
|-------------|--------------|-------------|
| REQ-SF-01 Feed & Infinite Scroll | API feed endpoint, pagination, cursor | Feed UI, infinite scroll, mosaic layout, banner insertion UX |
| REQ-SF-02 Sponsor Tiers | DB schema, tier/benefit CRUD, seed | Tier badge display, marketplace link UI |
| REQ-SF-03 Placement & Best Deal | Probability engine, placement config | Banner rendering, impression tracking |
| REQ-ADM-02 Admin Override | Full admin panel Livewire | Notification push handling |
| REQ-ANA-01 Analytics | Event collection, aggregation, dashboard | Event logging (impression/click/progress) |
| REQ-ANA-02 Notification & Audit | Notification system, audit log | In-app notification UI, deep link |
| TASK-M1-BE-01 Server Setup | Infrastructure setup | — |
| TASK-BE-06 Auth Hardening | Auth & role middleware | Token integration |
| TASK-BE-09 Staging Deploy | Deployment & environment | Smoke test |
| TASK-COORD-BE-01 Branch Contract | Branch & API documentation | — |

---

## 3. Konvensi & Best Practice

### 3.1 Best Practice — Laravel Backend

#### API Design
- **Versioning:** Semua endpoint di bawah `/api/v1/` — sudah existing.
- **Pagination:** Gunakan cursor-based pagination untuk feed (`?cursor=xxx&per_page=20`).
- **Response Format:** Standar JSON envelope:
  ```json
  {
    "success": true,
    "data": { },
    "meta": {
      "next_cursor": "abc123",
      "has_more": true,
      "per_page": 20
    },
    "message": null
  }
  ```
- **Error Response:**
  ```json
  {
    "success": false,
    "data": null,
    "errors": { "field": ["message"] },
    "message": "Validation failed"
  }
  ```

#### Database & Migrations
- Satu migration per concern/feature — jangan campur schema changes.
- Gunakan `stable_code` / `slug` sebagai identifier untuk import/export, bukan auto-increment `id`.
- Semua kolom `enum` disimpan sebagai `string` di migration dan divalidasi di application layer.
- Foreign key constraints wajib; gunakan `nullOnDelete()` untuk referensi opsional.

#### Model & Business Logic
- Gunakan Eloquent scopes untuk query reusable (`scopeActive`, `scopeForTier`, dll.).
- Business logic di Service class (`app/Services/`), bukan di Controller atau Model.
- Validasi input wajib server-side meskipun sudah ada validasi client.
- Soft delete untuk data yang perlu audit trail (sponsor, product, campaign).

#### Storage & Media
- Semua upload file ke managed storage (public disk atau S3-compatible).
- Metadata file (disk, path, MIME, size, checksum, status, owner) disimpan di database.
- Jangan hardcode path lokal developer; gunakan `Storage::disk()` facade.
- `php artisan storage:link` wajib dijalankan di server.
- Credential storage hanya di `.env`, tidak masuk git.

#### Security
- Ownership semua resource dari `auth()->id()`, bukan dari body request.
- Rate limiting pada endpoint publik.
- Input sanitization dan URL validation untuk marketplace links.
- CORS dikonfigurasi sesuai kebutuhan Flutter Web dan mobile.

### 3.2 Best Practice — Flutter Mobile

#### Architecture
- Feature-first folder structure (sudah existing): `features/{feature_name}/data|domain|presentation`.
- Clean Architecture: Repository pattern → Domain Use Case → Presentation (State Management).
- State management konsisten (gunakan satu: Provider/Riverpod/BLoC — sesuaikan dengan existing).

#### API Integration
- Base URL dari environment config, bukan hardcode.
- Auth token attach otomatis via Dio interceptor.
- Retry logic untuk network failures.
- Cache response jika diperlukan untuk offline-first UX.

#### Infinite Scroll & Feed
- Gunakan `ScrollController` + threshold detection untuk trigger load more.
- Maintain cursor/page state di ViewModel/Controller.
- De-duplicate items client-side berdasarkan `id`.
- Handle states: loading, loaded, empty, error, end-of-list.
- Banner insertion sesuai interval kelipatan (contoh: setiap 12 produk di shop).

#### UI/UX
- Card produk dan card materi HARUS memiliki layout berbeda.
- Mosaic layout untuk beranda dipertahankan.
- Marketplace link (`shopee_url`, `tokopedia_url`) membuka external browser/app via `url_launcher`.
- Loading shimmer/skeleton saat data sedang dimuat.
- Pull-to-refresh untuk reset feed dari awal.

#### Video Player
- Tidak ada fast-forward/skip untuk paid content.
- Progress tracking: pause, resume dari posisi terakhir.
- Complete threshold: 70% watched → mark complete.
- Free Class boleh memiliki kontrol berbeda.
- Metadata video dari API, bukan YouTube ID hardcoded.

### 3.3 Best Practice — Admin Panel (Livewire)

- CRUD operations melalui Livewire components dengan real-time validation.
- Semua konfigurasi tier/benefit/quota sebagai data di database, bukan di source code.
- Admin override harus tercatat di audit log.
- Panel menampilkan label "default awal" pada nilai-nilai numerik agar developer/admin tahu ini bukan immutable.
- Semua perubahan sponsor/product/campaign memicu notifikasi Admin.

---

## 4. Prosedur Kerja (SOP Development)

### 4.1 Branching Strategy

```
main (production-ready)
  └── dev/solkhan-room (working branch)
        ├── Commits: [REQ-SF-01] ...
        ├── Commits: [REQ-SF-02] ...
        ├── Commits: [REQ-SF-03] ...
        ├── Commits: [REQ-ADM-02] ...
        ├── Commits: [REQ-ANA-01] ...
        ├── Commits: [REQ-ANA-02] ...
        ├── Commits: [TASK-M1-BE-01] ...
        ├── Commits: [TASK-BE-06] ...
        ├── Commits: [TASK-BE-09] ...
        └── Commits: [TASK-COORD-BE-01] ...
```

### 4.2 Workflow per Task

```
┌─────────────────────────────────────────────────────┐
│  1. PLANNING                                         │
│  → Baca requirement lengkap                         │
│  → Tentukan scope (files, tables, endpoints)        │
│  → Buat sub-task checklist                          │
│  → Identifikasi dependency antar task               │
├─────────────────────────────────────────────────────┤
│  2. DEVELOPMENT                                      │
│  → Pastikan di branch dev/solkhan-room              │
│  → Tulis migration SEBELUM model/controller         │
│  → Validasi dengan `php artisan test`               │
│  → Commit kecil dan sering dengan pesan jelas       │
├─────────────────────────────────────────────────────┤
│  3. TESTING                                          │
│  → Unit test untuk business logic                   │
│  → Feature test untuk API endpoints                 │
│  → Manual test di Android emulator/device           │
│  → Screenshot/recording evidence                    │
├─────────────────────────────────────────────────────┤
│  4. COMMIT & PUSH                                    │
│  → Test pass → commit kecil dengan [TASK-ID]        │
│  → Push ke dev/solkhan-room                         │
│  → Update checklist progress                        │
├─────────────────────────────────────────────────────┤
│  5. INTEGRATION                                      │
│  → Smoke test di staging                            │
│  → Update Trello card status                        │
└─────────────────────────────────────────────────────┘
```

### 4.3 PR Checklist Template

Setiap PR **wajib** mencantumkan:

```markdown
## PR Checklist
- [ ] Changed files listed (paths)
- [ ] API endpoint changes documented (add/modify/remove)
- [ ] New/modified migration documented
- [ ] Migration backward-compatible atau rollback tested
- [ ] Seed data idempotent
- [ ] Test output attached (`php artisan test` / `flutter test`)
- [ ] Screenshot/evidence attached (jika UI change)
- [ ] Known blockers documented
- [ ] Contract version updated (jika API change)
- [ ] No credentials in source code
```

### 4.4 API Contract Versioning

Setiap perubahan API wajib didokumentasikan:

| Version | Date | Endpoint | Change Type | Description |
|---------|------|----------|-------------|-------------|
| v1.0 | 2026-09-12 | Existing endpoints | BASELINE | Initial API endpoints |
| v1.1 | TBD | `GET /feed/home` | NEW | Mixed feed with cursor paging |
| v1.1 | TBD | `GET /feed/shop` | NEW | Product-only feed with cursor |

### 4.5 Evidence Collection Prosedur

Sebelum card di-**DONE**, kumpulkan:

| # | Evidence | Format |
|---|----------|--------|
| 1 | URL staging/server + health check | Screenshot URL + response |
| 2 | `php artisan migrate:status` output | Terminal screenshot |
| 3 | `php artisan test` output | Terminal screenshot |
| 4 | Storage write + read-back test | Screenshot upload + URL buka |
| 5 | Upload gambar sponsor dari panel | Screenshot panel + API URL |
| 6 | Admin upload YouTube unlisted link | Screenshot + API read-back |
| 7 | Download template XLSX, dry-run, commit | Screenshot per step |
| 8 | Panel + API response (no secret leak) | Redacted screenshot |
| 9 | Android test dari device/emulator | Recording/screenshot |

---

## 5. Task Planning Detail

---

### REQ-SF-01 — Feed Dinamis Beranda/Shop & Infinite Scroll

> **Parent Epic:** [EPIC] Sponsor & Feed Dinamis
> **Tujuan:** Mengganti data dummy Home/Shop dengan feed backend, mempertahankan UX mosaic dan banner insertion.

#### 🎭 Peran

| Peran | Scope |
|-------|-------|
| **Backend API Engineer** | Feed API endpoint, pagination cursor, mixed content query, response formatting |
| **Mobile Feed Engineer** | Infinite scroll widget, feed rendering, mosaic layout, banner insertion UX, card variants |

#### 🏗️ Best Practice Implementasi

**Backend:**

1. **Cursor-based Pagination** — Lebih baik dari offset pagination untuk feed karena mencegah item berulang saat data berubah.
   ```php
   // Contoh: cursor = encoded(created_at + id) untuk deterministic ordering
   $query->where(function($q) use ($cursor) {
       $q->where('created_at', '<', $cursor->created_at)
         ->orWhere(function($q2) use ($cursor) {
             $q2->where('created_at', '=', $cursor->created_at)
                ->where('id', '<', $cursor->id);
         });
   })->orderByDesc('created_at')->orderByDesc('id')->limit($perPage);
   ```

2. **Dua Endpoint Terpisah:**
   - `GET /api/v1/feed/shop` — Product-only feed (SponsorProduct aktif).
   - `GET /api/v1/feed/home` — Mixed feed (produk + Free Class material + sponsor cards).

3. **Content Type Field** — Setiap item di mixed feed harus punya `content_type` agar Flutter tahu card mana yang dirender:
   ```json
   {
     "content_type": "product|material|sponsor_card",
     "data": { }
   }
   ```

4. **Banner Metadata Terpisah** — Banner insertion rules (interval, placement) dikonfigurasi di backend dan dikirim sebagai metadata response sehingga Admin bisa mengubah tanpa deploy ulang.

**Mobile:**

1. **ScrollController Pattern:**
   ```dart
   _scrollController.addListener(() {
     if (_scrollController.position.pixels >=
         _scrollController.position.maxScrollExtent - 200) {
       _loadMore();
     }
   });
   ```

2. **Feed Item Deduplication** — Maintain `Set<int> _loadedIds` untuk mencegah duplikat saat scroll.

3. **State Machine:**
   ```
   Initial → Loading → Loaded(items, hasMore, cursor)
                      → Empty (no items)
                      → Error(message, retryCallback)
   LoadingMore → Loaded (append)
              → Error (show inline retry)
   ```

4. **Banner Insertion Logic** — Sisipkan banner setelah setiap `N` items (konfigurable dari backend response metadata).

#### 📋 Prosedur Implementasi

1. Buat migration tambahan jika diperlukan (content_type fields, feed config table).
2. Implementasi `FeedService` dengan cursor pagination.
3. Buat API endpoint `GET /feed/shop` dan `GET /feed/home`.
4. Tulis Feature test untuk pagination, empty, error cases.
5. Implementasi `FeedRepository` + `FeedViewModel` di Flutter.
6. Buat `InfiniteScrollMixin` atau widget reusable.
7. Implementasi card variants (ProductCard, MaterialCard, SponsorCard).
8. Implementasi banner insertion berdasarkan metadata backend.
9. Test end-to-end dari Android emulator ke staging API.

#### ✅ Checklist

- [ ] Migration: feed config table (opsional, untuk insertion rules)
- [ ] `FeedService` dengan cursor-based pagination
- [ ] `GET /api/v1/feed/shop` endpoint (product-only, cursor, per_page)
- [ ] `GET /api/v1/feed/home` endpoint (mixed content, cursor, per_page)
- [ ] Response format dengan `content_type` discriminator
- [ ] Banner/insertion metadata dalam response
- [ ] Filter: hanya `is_active=true`, sponsor aktif, dalam date range
- [ ] Feature test: pagination correctness
- [ ] Feature test: no duplicate items across pages
- [ ] Feature test: empty state response
- [ ] Feature test: error handling
- [ ] `FeedRepository` dengan Dio API calls (Flutter)
- [ ] `FeedViewModel/Controller` dengan state management (Flutter)
- [ ] Infinite scroll trigger dengan `ScrollController` (Flutter)
- [ ] Client-side deduplication `Set<int>` (Flutter)
- [ ] ProductCard widget — membuka marketplace link / detail (Flutter)
- [ ] MaterialCard widget — membuka flow materi / Free Class (Flutter)
- [ ] SponsorCard widget — membuka detail sponsor (Flutter)
- [ ] Banner insertion setelah kelompok card sesuai interval (Flutter)
- [ ] Loading state shimmer/skeleton (Flutter)
- [ ] Empty state UI (Flutter)
- [ ] Error state + retry button (Flutter)
- [ ] Pull-to-refresh / reset cursor (Flutter)
- [ ] Produk tap → marketplace link / detail page (Flutter)
- [ ] Materi tap → flow materi Free Class / paid (Flutter)
- [ ] Android smoke test dari device/emulator
- [ ] API response screenshot evidence
- [ ] Feed screenshot evidence (mosaic layout maintained)
- [ ] Admin dapat mengatur feed source/visibility dari panel

#### ✅ Acceptance Test

- [ ] Tidak ada item berulang setelah scroll multiple pages
- [ ] Scroll berikutnya mengambil data dari backend (bukan dummy)
- [ ] Admin dapat mengatur sumber/visibility tanpa mengubah source code
- [ ] Produk tap → detail/marketplace
- [ ] Materi tap → flow materi

---

### REQ-SF-02 — Akun Sponsor, Enam Tier & Link Marketplace

> **Parent Epic:** [EPIC] Sponsor & Feed Dinamis
> **Tujuan:** Implementasi sponsor self-service terbatas dengan enam tier final dan outbound marketplace.

#### 🎭 Peran

| Peran | Scope |
|-------|-------|
| **Backend System Architect** | Tier schema, benefit config system, URL validation, outbound tracking, admin override, CRUD |
| **Mobile Integration Engineer** | Sponsor profile display, tier badge, marketplace link UI, external URL launching |

#### ⚠️ KOREKSI WAJIB — TIER 1 KONTRIBUSI

> **SEMUA sponsor pada SEMUA tier mendapat outbound marketplace link.**
> Label lama yang menyatakan Tier 1 tidak mendapat Direct Outbound Link adalah **SUPERSEDED**.
> VBAT **tidak memproses transaksi** produk sponsor di dalam aplikasi.
> Semua transaksi dilakukan di marketplace eksternal (Shopee/Tokopedia/lainnya).

#### 🏗️ Best Practice Implementasi

**Backend — Tier & Benefit sebagai Data:**

1. **Tabel `sponsor_tiers`** — Menyimpan definisi tier:
   ```
   id, slug, name, badge_label, sort_order, is_active, created_at, updated_at
   ```
   Default seed: kontribusi, bronze, silver, gold, platinum, diamond.

2. **Tabel `benefit_categories`** — Definisi kategori benefit:
   ```
   id, slug, name, description, value_type (integer/boolean/string/json), is_active, sort_order
   ```
   Contoh: katalog_produk, outbound_marketplace, dedicated_storefront, best_deal_slot, hero_slider, dll.

3. **Tabel `tier_benefits`** — Default benefit per tier-category:
   ```
   id, tier_id, benefit_category_id, value (JSON), label, is_default_awal (boolean)
   ```

4. **Tabel `sponsor_benefit_overrides`** — Override per sponsor:
   ```
   id, sponsor_id, benefit_category_id, override_value (JSON), overridden_by, reason, created_at
   ```

5. **URL Validation** — Server-side validation untuk marketplace URLs:
   ```php
   'shopee_url'     => ['nullable', 'url', 'regex:/^https:\/\/(shopee\.co\.id|www\.shopee\.co\.id)\/.*/'],
   'tokopedia_url'  => ['nullable', 'url', 'regex:/^https:\/\/(www\.tokopedia\.com|tokopedia\.com)\/.*/'],
   'marketplace_url'=> ['nullable', 'url', 'active_url'],
   ```

6. **Outbound Click Tracking** — Log setiap klik marketplace link:
   ```
   campaign_logs: event_type = 'outbound_click', target_url, sponsor_product_id, user_id (from session)
   ```

**Aturan Implementasi Kunci:**
- **JANGAN** hardcode enam tier dan angka benefit di Flutter maupun backend.
- Simpan tier/benefit/category sebagai data backend dengan default seed.
- Admin dapat create/edit/disable/delete kategori benefit dan menambah kategori baru **tanpa perubahan source code**.
- Admin dapat override default tier untuk sponsor tertentu.
- Semua quota wajib divalidasi **server-side**.
- Semua perubahan menghasilkan notifikasi Admin.
- Nilai numerik diberi label **"default awal"** di panel Admin.

#### 📋 Detail Benefit Default per Tier

| Benefit | Kontribusi | Bronze | Silver | Gold | Platinum | Diamond |
|---------|-----------|--------|--------|------|----------|---------|
| Katalog Produk/bln | 5 | 15 | 35 | 75 | 150 | unlimited* |
| Outbound Marketplace | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Dedicated Storefront | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Best Deal Slot/bln | 0 | 1 (3hr) | 3 (7hr) | 8 (14hr) | 15 (21hr) | unlimited |
| Best Deal Priority | — | — | — | Top 5 | Top 3 | #1 & #2 |
| Hero Slider | ❌ | ❌ | 1 slot (slide 5-6, ~20%) | 1 slot (slide 3-4, ~35%) | 2 slot (slide 1-2, ~50%) | Slide #1 Title |
| Popup + CTA | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Horizontal In-Feed | ❌ | 1/24 produk | 2/12 produk | Multi-section | Multi-touchpoint | Eksklusif |
| Push Broadcast | ❌ | ❌ | ❌ | 1x/bln | 3x/bln | Fleksibel |
| Badge | Kontributor | Bronze Partner | Silver Official | Gold Brand | Platinum Premier | Diamond Title |
| Co-branding | ❌ | ❌ | ❌ | ❌ | ❌ | Opsi (Admin) |
| Partner Support | ❌ | ❌ | ❌ | ❌ | Opsi (Admin) | VIP Portal |

> *"unlimited" = default awal, Admin dapat mengubah.

#### ✅ Checklist

- [ ] Migration: `sponsor_tiers` table
- [ ] Migration: `benefit_categories` table
- [ ] Migration: `tier_benefits` table (default per tier-category)
- [ ] Migration: `sponsor_benefit_overrides` table
- [ ] Migration: Update `sponsors.tier` kolom → FK ke `sponsor_tiers`
- [ ] Seeder: 6 tier default (kontribusi→diamond)
- [ ] Seeder: benefit categories default sesuai matriks
- [ ] Seeder: default benefit values per tier sesuai tabel di atas
- [ ] Model: `SponsorTier`, `BenefitCategory`, `TierBenefit`, `SponsorBenefitOverride`
- [ ] Service: `SponsorBenefitService` (resolve effective benefit = default + override)
- [ ] Validation: marketplace URL server-side (shopee/tokopedia/general)
- [ ] Validation: URL invalid ditolak dengan error message
- [ ] Outbound click tracking (event_type = 'outbound_click')
- [ ] Quota validation server-side (produk/bln, best deal/bln, push/bln)
- [ ] Admin CRUD: semua 6 tier
- [ ] Admin CRUD: benefit categories (add/edit/disable/delete)
- [ ] Admin: override benefit per sponsor
- [ ] Admin: label "default awal" pada nilai numerik
- [ ] Sponsor portal: upload/edit produk sendiri (tanpa analytics)
- [ ] Sponsor scope isolation (hanya melihat miliknya)
- [ ] Audit log untuk perubahan benefit (jika fitur diaktifkan)
- [ ] Notifikasi Admin untuk semua perubahan sponsor
- [ ] Tampilkan badge tier pada card sponsor/produk (Flutter)
- [ ] Tombol marketplace link Shopee/Tokopedia pada product detail (Flutter)
- [ ] Tap marketplace link → buka URL external via url_launcher (Flutter)
- [ ] TIDAK ada checkout/transaksi produk sponsor di dalam app (Flutter)
- [ ] Tier/benefit data dari API, bukan hardcode (Flutter)

#### ✅ Acceptance Test — Koreksi Tier 1

- [ ] Buat sponsor Tier Kontribusi → berhasil
- [ ] Tambah produk dengan URL marketplace valid → berhasil
- [ ] Tampilkan produk pada feed/shop → terlihat
- [ ] Tombol/link beli terlihat dan membuka URL marketplace → ✅
- [ ] TIDAK ada checkout/transaksi produk sponsor di app → ✅
- [ ] URL invalid ditolak server-side → ✅
- [ ] Aturan berlaku sama untuk semua 6 tier → ✅
- [ ] Admin dapat edit benefit, tambah/hapus kategori, override sponsor → ✅

#### ✅ Test Minimum Benefit System

- [ ] CRUD keenam tier
- [ ] CRUD kategori benefit
- [ ] Tambah kategori baru → tampil di sponsor configuration
- [ ] Nonaktifkan kategori → tidak muncul pada entitlement baru
- [ ] Override quota sponsor tertentu
- [ ] Sponsor tidak dapat mengubah tier/benefit dirinya sendiri
- [ ] Sponsor tidak dapat membuka analytics Admin
- [ ] Admin delete/deactivate campaign → langsung hilang dari feed/API
- [ ] Link marketplace invalid ditolak
- [ ] Audit perubahan benefit dan notifikasi Admin diverifikasi

---

### REQ-SF-03 — Placement Sponsor, Probabilitas & Best Deal

> **Parent Epic:** [EPIC] Sponsor & Feed Dinamis
> **Tujuan:** Mengatur placement sponsor berdasarkan probabilitas tampil dan Admin kontrol Best Deal manual.

#### 🎭 Peran

| Peran | Scope |
|-------|-------|
| **Backend Algorithm Engineer** | Probability engine, placement selection, campaign config, impression logging, Best Deal manual selection |
| **Mobile UX Engineer** | Banner rendering per placement type, impression event firing, Best Deal carousel UI |

#### 🏗️ Best Practice Implementasi

**Backend — Probabilistic Selection:**

1. **Tabel `placement_configs`:**
   ```
   id, placement_type (hero_slider/horizontal_infeed/popup/best_deal/card_infeed),
   tier_id, max_slots, target_probability (float 0-1), insertion_interval,
   fallback_behavior (hide/show_default), is_active, sort_order
   ```

2. **Selection Algorithm:**
   - Untuk setiap placement opportunity (rendered slot), ambil campaigns aktif yang eligible.
   - Filter berdasarkan tier entitlement, remaining quota, date range, daily limit.
   - Weighted random selection berdasarkan `target_probability` / `weight`.
   - Log selection event untuk analytics.
   - Jangan hanya sort by weight — gunakan probabilistic pick.

3. **Best Deal Manual:**
   - Admin dapat memilih produk Best Deal secara manual via panel.
   - Tabel `best_deals` existing sudah mendukung ini.
   - Tambahkan `selected_by` (admin user_id) dan `selection_type` (manual/auto).

4. **Fallback:**
   - Jika tidak ada campaign aktif untuk placement → hide slot atau tampilkan default content.
   - Campaign expired otomatis tidak tampil tanpa manual intervention.

**Mobile:**
- Impression tracking: fire event saat banner/card muncul di viewport (bukan saat data loaded).
- Gunakan `VisibilityDetector` atau scroll position calculation untuk impression accuracy.

#### ✅ Checklist

- [ ] Migration: `placement_configs` table
- [ ] Service: `PlacementSelectionService` (probabilistic pick)
- [ ] Endpoint: `GET /api/v1/placements/{type}` — returns selected campaigns
- [ ] Best Deal: Admin manual selection via panel
- [ ] Best Deal: `selection_type` field (manual/auto)
- [ ] Impression logging: `campaign_logs.event_type = 'impression'` with placement context
- [ ] Fallback behavior for empty/expired campaigns
- [ ] Daily limit enforcement per campaign
- [ ] Feature test: seeded probability distribution test
- [ ] Feature test: fallback when no active campaigns
- [ ] Hero slider rendering dari API, maks 6 slide (Flutter)
- [ ] Horizontal in-feed banner insertion sesuai interval konfigurasi (Flutter)
- [ ] Popup sponsor rendering + CTA marketplace (Flutter)
- [ ] Best Deal carousel UI (Flutter)
- [ ] Card-sized in-feed placement rendering (Flutter)
- [ ] Impression event: fire saat banner visible di viewport (Flutter)
- [ ] Click event: fire saat banner tapped (Flutter)
- [ ] Placement rendering test per type
- [ ] Analytics log verification

#### ✅ Acceptance Test

- [ ] Campaign aktif dipilih dari konfigurasi backend, bukan sort weight saja
- [ ] Impression dan selection tercatat di log
- [ ] Admin dapat memilih Best Deal manual
- [ ] Campaign kosong/expired memiliki fallback (hide atau default)
- [ ] UX feed dasar tidak berubah tanpa keputusan baru

---

### REQ-ADM-02 — Administrasi Sponsor, Override & Notifikasi Admin

> **Parent Epic:** [EPIC] Control Plane Admin VBAT
> **Tujuan:** Kuasa penuh Admin atas sponsor/product/campaign tanpa approval blocking.

#### 🎭 Peran

| Peran | Scope |
|-------|-------|
| **Backend Admin Panel Engineer** | Full Livewire admin panel, CRUD semua entity, override logic, notification system, permission matrix |

#### 🏗️ Best Practice Implementasi

**Policy: No Approval Blocking**
- Sponsor upload konten → langsung display sesuai policy/tier entitlement.
- Admin override/delete → efek **segera** (real-time).
- Status campaign: `active/paused/deleted` (bukan `pending/approved/rejected`).

**Admin Panel Capabilities:**

| Feature | Detail |
|---------|--------|
| Sponsor Account CRUD | Create, edit, deactivate, delete sponsor account |
| Tier Assignment | Assign/change tier per sponsor |
| Benefit Override | Override default benefit values per sponsor |
| Product Management | View/edit/delete semua produk sponsor |
| Campaign Control | Edit/delete/deactivate/reorder campaigns segera |
| Best Deal Manual | Select/deselect produk untuk Best Deal |
| Notification Inbox | Melihat semua event perubahan (sumber, actor, waktu, status baca) |

**Notification System:**

```
Tabel: admin_notifications
- id, type, title, body, actor_type, actor_id, target_type, target_id,
  deep_link, is_read, read_at, created_at
```

Trigger events:
- Sponsor upload produk baru
- Sponsor edit produk
- Sponsor upload campaign
- Sponsor edit campaign
- Campaign auto-expired
- Quota mendekati limit
- Override applied

#### ✅ Checklist

- [ ] Migration: `admin_notifications` table
- [ ] Service: `AdminNotificationService` (create, mark read, list)
- [ ] Livewire: Sponsor Account CRUD page
- [ ] Livewire: Sponsor Tier Assignment
- [ ] Livewire: Benefit Override per sponsor
- [ ] Livewire: Product Management (admin view all)
- [ ] Livewire: Campaign Management (edit/delete/deactivate segera)
- [ ] Livewire: Best Deal Manual Selection
- [ ] Livewire: Admin Notification Inbox (list, read/unread, deep link)
- [ ] Campaign status: `active/paused/deleted` (bukan approval-based)
- [ ] Sponsor upload → display segera tanpa approval blocking
- [ ] Admin delete → efek segera di API response
- [ ] Admin override → audit log entry
- [ ] Permission: Sponsor HANYA melihat scope miliknya
- [ ] Permission: Sponsor TIDAK punya akses analytics
- [ ] Notification event coverage: semua trigger events
- [ ] Notification: sumber, actor, waktu, status baca, deep link
- [ ] Test: permission/override matrix
- [ ] Test: deletion propagation (campaign dihapus → hilang dari feed/API)
- [ ] Test: notification event coverage
- [ ] Test: role-based access (sponsor vs admin)

#### ✅ Acceptance Test

- [ ] Sponsor upload tanpa membutuhkan approval manual
- [ ] Admin dapat menghapus konten segera
- [ ] Enam tier dan default benefit editable
- [ ] Notifikasi berisi sumber, actor, waktu, status baca, deep link
- [ ] Sponsor TIDAK memiliki akses analytics

---

### REQ-ANA-01 — Analitik Traffic, Produk & Pembelajaran untuk Admin

> **Parent Epic:** [EPIC] Analitik & Notifikasi
> **Tujuan:** Admin data lengkap untuk operasi dan laporan sponsor.

#### 🎭 Peran

| Peran | Scope |
|-------|-------|
| **Backend Analytics Engineer** | Event collection, aggregation, dashboard admin, export, retention policy |
| **Mobile Event Logger** | Client-side event firing (impression, click, progress, quiz, bookmark, video events) |

#### 🏗️ Best Practice Implementasi

**Event Schema Standard:**

```json
{
  "event_type": "product_view|product_click|wishlist_add|outbound_click|impression",
  "actor_id": null,
  "session_id": "uuid",
  "target_type": "sponsor_product|campaign|video|course",
  "target_id": 123,
  "context": {
    "placement": "feed_shop|feed_home|hero_slider",
    "position": 5,
    "page_cursor": "abc123"
  },
  "created_at": "2026-09-23T01:00:00Z"
}
```

**Aturan Kritis:**
- `actor_id` / `user_id` SELALU dari server session — **JANGAN** terima dari client body.
- Anonymous events (visitor tanpa login) menggunakan session ID saja.
- Aggregate harus cocok dengan raw event (reconciliation test).
- Sponsor **TIDAK BOLEH** mengakses analytics — hanya Admin.

**Event Types yang Harus Dilacak:**

| Category | Events |
|----------|--------|
| Traffic | `page_view`, `session_start`, `feed_scroll` |
| Product | `product_view`, `product_click`, `wishlist_add`, `wishlist_remove`, `outbound_click` |
| Campaign | `impression` (per placement type), `banner_click` |
| Learning | `course_start`, `lesson_start`, `video_start`, `video_progress`, `video_complete`, `course_complete` |
| Quiz | `quiz_attempt`, `quiz_pass`, `quiz_fail` |
| Material | `pdf_open`, `pdf_download`, `video_preview_start`, `video_full_start`, `bookmark_add`, `bookmark_remove` |

#### ✅ Checklist

- [ ] Migration: `analytics_events` table (generic event store)
- [ ] Service: `AnalyticsEventService` (log event, validate, sanitize)
- [ ] Endpoint: `POST /api/v1/events` — batch event ingestion
- [ ] Event identity dari server session (bukan client payload)
- [ ] Dashboard Admin: visitor/session stats
- [ ] Dashboard Admin: product analytics (view/click/wishlist/outbound)
- [ ] Dashboard Admin: learning analytics (start/progress/completion)
- [ ] Dashboard Admin: quiz analytics (attempt/pass/fail)
- [ ] Dashboard Admin: campaign impression analytics
- [ ] Aggregate views (materialized atau computed)
- [ ] Filter: date range, sponsor, product, course, placement
- [ ] Export: CSV/XLSX sesuai retention policy
- [ ] Authorization: sponsor TIDAK bisa akses analytics endpoints/pages
- [ ] Test: event contract validation
- [ ] Test: aggregate reconciliation with raw events
- [ ] Test: authorization (sponsor blocked)
- [ ] Test: volume smoke test
- [ ] Event logger utility class (Flutter)
- [ ] Product events: view, click, wishlist, outbound (Flutter)
- [ ] Impression events: per placement with viewport detection (Flutter)
- [ ] Learning events: start, progress, complete, quiz (Flutter)
- [ ] Material events: pdf open/download, video preview/full, bookmark (Flutter)
- [ ] Batch event sending with debounce/offline queue (Flutter)
- [ ] Event contract end-to-end test
- [ ] Dashboard matches event data

#### ✅ Acceptance Test

- [ ] Event memiliki actor/session/time/context yang aman
- [ ] Tidak ada arbitrary user ownership dari client
- [ ] Aggregate cocok dengan raw event
- [ ] Sponsor tidak dapat mengakses analytics

---

### REQ-ANA-02 — Matrix Notifikasi & Audit Trail

> **Parent Epic:** [EPIC] Analitik & Notifikasi
> **Tujuan:** Lifecycle notifikasi untuk Admin dan user serta auditability.

#### 🎭 Peran

| Peran | Scope |
|-------|-------|
| **Backend Notification Engineer** | Notification system, event bus, audit log, push channel, delivery management |
| **Mobile Notification UI Engineer** | In-app notification list, read/unread UI, deep link navigation, push notification handling |

#### 🏗️ Best Practice Implementasi

**Notification Categories:**

| Target | Events |
|--------|--------|
| **Admin** | Sponsor/product/campaign upload, edit, delete, override, quota warning |
| **User (Student)** | Payment status (confirmed/failed), Hardware Solution unlock, subscription reminder |

**Notification Record:**

```
Tabel: notifications
- id, recipient_type (admin/user), recipient_id,
  type (payment_status/sponsor_upload/campaign_edit/hs_unlock/...),
  title, body, deep_link, data (JSON),
  is_read, read_at, created_at
```

**Audit Log:**

```
Tabel: audit_logs
- id, actor_type (admin/sponsor/system), actor_id,
  action (create/update/delete/override),
  auditable_type (sponsor/product/campaign/benefit/...),
  auditable_id, old_values (JSON), new_values (JSON),
  ip_address, user_agent, created_at
```

**Aturan:**
- Notifikasi harus **idempotent** — event yang sama tidak menghasilkan duplikat notifikasi.
- User hanya melihat notifikasi sendiri (scope by `recipient_id`).
- Deep link membuka target context (halaman spesifik di app).
- Read state tersimpan per notifikasi.

#### ✅ Checklist

- [ ] Migration: `notifications` table (polymorphic recipient)
- [ ] Migration: `audit_logs` table
- [ ] Service: `NotificationService` (create, batch, mark read, list by recipient)
- [ ] Service: `AuditLogService` (log changes with old/new values)
- [ ] Event triggers: sponsor upload/edit/delete → admin notification
- [ ] Event triggers: payment confirmed/failed → user notification
- [ ] Event triggers: Hardware Solution unlock → user notification
- [ ] Event triggers: admin override → audit log + admin notification
- [ ] Idempotency: duplicate event → no duplicate notification
- [ ] Endpoint: `GET /api/v1/notifications` (user's own, paginated)
- [ ] Endpoint: `POST /api/v1/notifications/{id}/read` (mark read)
- [ ] Deep link format specification
- [ ] Retention policy implementation
- [ ] Test: trigger → notification created
- [ ] Test: duplicate suppression
- [ ] Test: read/unread state
- [ ] Test: authorization (user only sees own)
- [ ] Test: audit log captures old/new values
- [ ] Notification list page with read/unread visual distinction (Flutter)
- [ ] Pull-to-refresh notification list (Flutter)
- [ ] Tap notification → deep link navigation (Flutter)
- [ ] Mark as read on tap (Flutter)
- [ ] Unread count badge (Flutter)
- [ ] Push notification handling via FCM (Flutter)
- [ ] Test: delivery failure graceful handling (Flutter)

#### ✅ Acceptance Test

- [ ] Event menghasilkan notifikasi idempotent
- [ ] User hanya melihat notifikasi sendiri
- [ ] Admin melihat event operasional yang diizinkan
- [ ] Deep link membuka target context
- [ ] Read state tersimpan

---

### TASK-M1-BE-01 — Setup Backend Runtime, Server, Database & Object Storage

> **Owner:** Solkhan (mohamadsolkhannawawi)
> **Parent:** REQ-SF-01 / REQ-ADM-02 / REQ-ANA-01

#### 🎭 Peran

| Peran | Scope |
|-------|-------|
| **DevOps / Infrastructure Engineer** | Runtime, server, database, object storage, CORS, health check |

#### 🏗️ Best Practice Implementasi

1. **Composer Recovery:**
   ```bash
   composer install --no-dev --optimize-autoloader  # production
   composer install                                  # dev/staging
   ```

2. **Database:**
   ```bash
   php artisan migrate:fresh --seed   # dev only
   php artisan migrate                # staging (incremental)
   ```

3. **Environment Variables yang Wajib Dikonfigurasi:**

   | Variable | Contoh | Keterangan |
   |----------|--------|------------|
   | `APP_URL` | `https://staging.vbat.id` | URL publik |
   | `API_BASE_URL` | `https://staging.vbat.id/api/v1` | Base URL mobile |
   | `FILESYSTEM_DISK` | `public` atau `s3` | Storage aktif |
   | `AWS_BUCKET` | `vbat-assets` | Jika S3-compatible |
   | `AWS_ENDPOINT` | `https://s3.region.com` | Jika non-AWS |
   | `AWS_DEFAULT_REGION` | `ap-southeast-1` | Region |
   | `CORS_ALLOWED_ORIGINS` | `*` atau domain list | CORS Flutter Web |

4. **Object Storage Struktur:**
   ```
   sponsor/logos/
   sponsor/products/
   sponsor/campaigns/hero/
   sponsor/campaigns/card/
   sponsor/campaigns/horizontal/
   sponsor/campaigns/popup/
   learning/thumbnails/
   learning/pdfs/
   learning/offline-encrypted/   (jika ada)
   ```

5. **Storage Link:**
   ```bash
   php artisan storage:link
   # Verify: ls -la public/storage → symlink ke storage/app/public
   ```

#### ✅ Checklist

- [ ] Composer install / vendor recovery berhasil
- [ ] Database dev/test dikonfigurasi dan accessible
- [ ] `php artisan migrate:status` berhasil — semua migration ran
- [ ] `php artisan test` berjalan tanpa error
- [ ] `APP_URL` dikonfigurasi ke URL publik/staging
- [ ] API base URL terdokumentasi untuk mobile
- [ ] `FILESYSTEM_DISK` dikonfigurasi (public atau s3)
- [ ] Object storage bucket/endpoint/region dikonfigurasi (jika S3)
- [ ] CORS dikonfigurasi untuk Flutter Web dan mobile origin
- [ ] `php artisan storage:link` dijalankan di server
- [ ] Permission folder storage benar (775 atau sesuai server)
- [ ] URL media publik/proxy berfungsi
- [ ] Health check endpoint tersedia dan respond 200
- [ ] Storage write test: upload file → berhasil
- [ ] Storage read-back test: baca file dari URL luar server → berhasil
- [ ] Object storage path structure dibuat sesuai spesifikasi
- [ ] Tidak ada credential di source code / git
- [ ] `.env.example` ter-update dengan semua variable baru
- [ ] Evidence: health URL screenshot
- [ ] Evidence: migration output screenshot
- [ ] Evidence: test output screenshot
- [ ] Evidence: storage read-back screenshot
- [ ] Evidence: redacted config checklist

---

### TASK-BE-06 — Auth, Session & Ownership Hardening

> **Owner:** Solkhan (mohamadsolkhannawawi)
> **Parent:** REQ-SF-01 / REQ-ADM-02 / REQ-ANA-01

#### 🎭 Peran

| Peran | Scope |
|-------|-------|
| **Security Engineer** | Auth middleware, role enforcement, ownership hardening, session management |

#### 🏗️ Best Practice Implementasi

1. **Ownership dari Auth Principal:**
   ```php
   // BENAR
   $userId = auth()->id();
   $wishlist = UserWishlist::where('user_id', $userId)->get();

   // SALAH — jangan terima user_id dari body
   $userId = $request->input('user_id'); // DILARANG
   ```

2. **Role Middleware:**
   ```php
   Route::middleware(['auth:sanctum', 'role:admin'])->group(function () {
       // Admin-only routes
   });

   Route::middleware(['auth:sanctum', 'role:sponsor'])->group(function () {
       // Sponsor-only routes (scoped to own data)
   });
   ```

3. **Sponsor Scope Isolation:**
   ```php
   // Sponsor hanya bisa akses data miliknya
   $sponsor = auth()->user()->sponsor;
   $products = $sponsor->products; // scoped
   ```

4. **Anonymous Session:**
   - Hanya untuk event public: feed view, product view (tanpa auth).
   - Gunakan session ID untuk tracking, bukan user_id.

#### ✅ Checklist

- [ ] Semua endpoint yang butuh auth menggunakan middleware `auth:sanctum`
- [ ] User_id/owner_id TIDAK diterima dari request body untuk ownership
- [ ] Ownership resource selalu dari `auth()->id()`
- [ ] Sponsor scope: hanya melihat data `sponsor_id` miliknya
- [ ] Sponsor tidak bisa ubah `sponsor_id` melalui payload
- [ ] Student tidak bisa akses endpoint Admin/Sponsor
- [ ] Sponsor tidak bisa akses endpoint Admin
- [ ] Token invalid → 401 Unauthorized
- [ ] Token expired → 401 Unauthorized
- [ ] Anonymous session hanya untuk event public yang diizinkan
- [ ] Event identity (analytics) berasal dari server, bukan client
- [ ] Role matrix tested: student, sponsor, admin per endpoint
- [ ] Cross-user access test: User A tidak bisa read/write User B data
- [ ] Test: auth integration tests
- [ ] Test: ownership isolation tests
- [ ] Test: role matrix tests
- [ ] Test: unauthorized response format
- [ ] Identity contract terdokumentasi

---

### TASK-BE-09 — Staging Deployment, Environment, Health & Rollback

> **Owner:** Solkhan (mohamadsolkhannawawi)
> **Parent:** REQ-SF-01 / REQ-QA-01

#### 🎭 Peran

| Peran | Scope |
|-------|-------|
| **DevOps / Release Engineer** | Deployment, environment config, health check, rollback procedure |

#### 🏗️ Best Practice Implementasi

1. **Dokumentasi Deployment:**
   ```markdown
   ## Deployment Guide
   - Branch: `dev/solkhan-room` (staging) / `main` (production)
   - Deploy command: [tentukan]
   - Rollback: php artisan migrate:rollback --step=N
   ```

2. **Environment Checklist:**

   | Variable | Staging | Production |
   |----------|---------|------------|
   | APP_ENV | staging | production |
   | APP_DEBUG | true | false |
   | APP_URL | https://staging.vbat.id | https://vbat.id |
   | DB_CONNECTION | mysql | mysql |
   | FILESYSTEM_DISK | public/s3 | s3 |
   | QUEUE_CONNECTION | sync/redis | redis |
   | CACHE_DRIVER | file/redis | redis |

3. **Health Endpoint:**
   ```php
   Route::get('/health', function () {
       return response()->json([
           'status' => 'ok',
           'version' => config('app.version'),
           'timestamp' => now()->toISOString(),
       ]);
   });
   ```

#### ✅ Checklist

- [ ] Branch/deploy command terdokumentasi
- [ ] Environment variables lengkap (APP_URL, DB, storage, CORS, queue, cache, cron)
- [ ] HTTPS dikonfigurasi
- [ ] Health endpoint respond 200 dari network test
- [ ] `php artisan migrate` berhasil di staging
- [ ] `php artisan db:seed` dapat diulang dengan aman (idempotent seeder)
- [ ] Storage write/read-back berhasil dari luar server
- [ ] CORS dan API base URL cocok untuk Android test
- [ ] Log/monitoring minimum aktif
- [ ] Backup procedure terdokumentasi
- [ ] Rollback migration tested atau limitation dicatat
- [ ] Staging terpisah dari production environment
- [ ] Credential redacted (tidak ada secret di log/output)
- [ ] Payment sandbox dikonfigurasi (jika ada payment feature)
- [ ] Evidence: health URL accessible
- [ ] Evidence: deployment log
- [ ] Evidence: migration output
- [ ] Evidence: storage read-back
- [ ] Evidence: redacted config checklist
- [ ] Evidence: rollback evidence atau limitation note
- [ ] Staging siap dipakai untuk QA

---

### TASK-COORD-BE-01 — Branch Boundary & Backend-Mobile Handoff Contract

> **Owner:** Solkhan (mohamadsolkhannawawi)
> **Parent:** Semua backend child tasks

#### 🎭 Peran

| Peran | Scope |
|-------|-------|
| **Project Coordinator** | Branch management, API contract documentation, migration changelog, handoff artifacts |

#### 🏗️ Best Practice Implementasi

1. **Branch Management:**
   - Backend: `dev/solkhan-room` pada `VBAT-WEBSITE`
   - Mobile: `dev/solkhan-room` pada `VBAT-MOBILE`

2. **Shared Artifacts yang harus dipelihara:**
   - API Contract document
   - Migration changelog
   - Seed data fixtures
   - Handoff checklist

3. **Rules:**
   - API change harus punya version/note sebelum integrasi.
   - Migration/seed tidak boleh merusak fixture contract.
   - Setiap PR mencantumkan changed paths, API/migration impact, test output, dan known blocker.

#### ✅ Checklist

- [ ] Branch backend dipilih dan dicatat
- [ ] Branch mobile dipilih dan dicatat
- [ ] API contract document v1 dibuat
- [ ] API change → version/note sebelum integrasi
- [ ] Migration changelog maintained
- [ ] Seed data → fixture contract documented
- [ ] Handoff checklist template dibuat
- [ ] Setiap PR mencantumkan: changed paths, API impact, migration impact, test output, known blockers

---

## 6. Master Checklist

### 📊 Progress Tracker

| # | Task ID | Nama | Status | Progress |
|---|---------|------|--------|----------|
| 1 | REQ-SF-01 | Feed Dinamis & Infinite Scroll | ⬜ READY | 0% |
| 2 | REQ-SF-02 | Sponsor Tiers & Marketplace | ⬜ READY | 0% |
| 3 | REQ-SF-03 | Placement & Best Deal | ⬜ READY | 0% |
| 4 | REQ-ADM-02 | Admin Override & Notifikasi | ⬜ READY | 0% |
| 5 | REQ-ANA-01 | Analytics Admin | ⬜ READY | 0% |
| 6 | REQ-ANA-02 | Notifikasi & Audit Trail | ⬜ READY | 0% |
| 7 | TASK-M1-BE-01 | Server Setup | ⬜ READY | 0% |
| 8 | TASK-BE-06 | Auth Hardening | ⬜ READY | 0% |
| 9 | TASK-BE-09 | Staging Deploy | ⬜ READY | 0% |
| 10 | TASK-COORD-BE-01 | Branch Contract | ⬜ READY | 0% |

### 🔗 Dependency Graph

```
TASK-M1-BE-01 (Server Setup)
    └──▶ TASK-BE-06 (Auth Hardening)
    └──▶ TASK-BE-09 (Staging Deploy)
    └──▶ TASK-COORD-BE-01 (Branch Contract)
            └──▶ REQ-SF-01 (Feed & Scroll)
            └──▶ REQ-SF-02 (Sponsor Tiers)
                    └──▶ REQ-SF-03 (Placement & Best Deal)
                    └──▶ REQ-ADM-02 (Admin Override)
                            └──▶ REQ-ANA-01 (Analytics)
                            └──▶ REQ-ANA-02 (Notification & Audit)
```

### 📋 Urutan Eksekusi yang Direkomendasikan

| Phase | Tasks | Alasan |
|-------|-------|--------|
| **Phase 0 — Foundation** | TASK-M1-BE-01, TASK-COORD-BE-01 | Infrastructure dan koordinasi harus ada dulu |
| **Phase 1 — Security** | TASK-BE-06 | Auth harus benar sebelum fitur lain |
| **Phase 2 — Core Schema** | REQ-SF-02 (tier & benefit schema) | Data model foundation untuk semua fitur |
| **Phase 3 — Feed & Placement** | REQ-SF-01, REQ-SF-03 (parallel) | Feed API + placement engine |
| **Phase 4 — Admin Control** | REQ-ADM-02 | Admin panel setelah data model stabil |
| **Phase 5 — Analytics & Audit** | REQ-ANA-01, REQ-ANA-02 (parallel) | Analytics setelah events flowing |
| **Phase 6 — Staging & QA** | TASK-BE-09 | Deploy dan full integration test |

---

## 7. Catatan Krusial & Decision Register

### 🔴 Decision Register — WAJIB DIIKUTI

| # | Keputusan | Status | Dampak |
|---|-----------|--------|--------|
| D-001 | **SEMUA tier sponsor mendapat outbound marketplace link** | ✅ FINAL | Tier 1 Kontribusi tetap dapat link marketplace |
| D-002 | **VBAT tidak memproses transaksi produk sponsor** | ✅ FINAL | Tidak ada checkout di app; semua transaksi di marketplace |
| D-003 | **Label lama matriks benefit SUPERSEDED** | ✅ FINAL | Jangan pakai label lama yang menyatakan Tier 1 tanpa outbound link |
| D-004 | **Analytics hanya Admin VBAT** | ✅ FINAL | Sponsor tidak mendapat analytics/report dashboard |
| D-005 | **Video LMS = YouTube Unlisted** | ✅ FINAL | Bukan upload MP4; admin input URL/ID YouTube unlisted |
| D-006 | **Bulk upload XLSX sebagai format utama** | ✅ FINAL | CSV/TXT sebagai fallback, bukan satu-satunya |
| D-007 | **Benefit/tier sebagai configurable data** | ✅ FINAL | Bukan hardcode; Admin bisa edit tanpa deploy |
| D-008 | **No approval blocking untuk sponsor upload** | ✅ FINAL | Sponsor upload → display sesuai policy, tanpa pending/approved flow |
| D-009 | **Ownership dari server auth, bukan client payload** | ✅ FINAL | `user_id` selalu dari `auth()->id()` |
| D-010 | **README lama yang bertentangan → ikuti Decision Register/Trello** | ✅ FINAL | README lama bukan source of truth jika bertentangan |

### ⚠️ Catatan Server & Storage

1. Backend HARUS dijalankan di server/staging yang **dapat dijangkau Flutter** — bukan hanya localhost.
2. Tetapkan dan dokumentasikan: `APP_URL`, API base URL, `FILESYSTEM_DISK`, object storage config, CORS, media URL.
3. Gambar sponsor, logo, thumbnail, banner → **managed storage** (bukan path lokal dev).
4. Credential **hanya** di environment server — **JANGAN** masuk git.
5. Admin delete/deactivate harus menghapus/cabut akses object sesuai retention policy.
6. **Test wajib:** upload dari panel Admin/Sponsor → read-back melalui URL API dari jaringan luar server.

### ⚠️ Catatan Video LMS

1. Admin "upload video" = input/kelola link **YouTube unlisted** via CMS — bukan upload MP4.
2. Backend normalisasi dan validasi URL/ID YouTube.
3. Simpan: `source_type=youtube_unlisted`, title, description, thumbnail, duration, sort_order, status.
4. **Unlisted bukan DRM** — app tetap terapkan entitlement dan jangan expose raw URL ke user.
5. Thumbnail/dokumen pendamping tetap pakai object storage.
6. Mobile terima metadata video dari API — **bukan** YouTube ID hardcoded.
7. **Test wajib:** valid URL, invalid/private URL, video unavailable, deleted video, wrong owner/channel, duration fetch failure.

### ⚠️ Catatan Bulk Upload XLSX

1. Format utama: `.xlsx` — CSV/TXT adalah fallback.
2. Template downloadable dari panel Admin.
3. Template sheets: Petunjuk + Materi dengan kolom lengkap (course_slug, lesson_slug, unit_code, unit_title, material_type, title, description, youtube_url, pdf_object_key, thumbnail_object_key, sort_order, is_required, quiz_required, quiz_id, status).
4. Mode import: create new / update by slug / upsert.
5. **Dry-run/preview wajib** sebelum commit.
6. Hasil per baris: valid/warning/error + alasan.
7. Import **transactional** — jangan buat setengah data tanpa laporan.
8. Setelah commit → ringkasan: created/updated/skipped/error + import log tersimpan.

### ⚠️ Placement Configurable (JANGAN Hardcode)

Semua placement berikut harus menjadi **data configurable** di backend:

- Katalog produk quota
- Direct outbound marketplace (wajib semua tier)
- Dedicated storefront flag
- Best Deal: slot, quota, durasi, prioritas
- Hero Slider: max 6 slide, slot assignment per tier
- Target probability / share of voice per placement
- Popup sponsor + CTA
- Horizontal in-feed banner + interval insertion
- Badge sponsor per tier
- Push notification quota
- Admin-only analytics/report scope
- Co-branding / partner support / VIP benefit

---

> **Dokumen ini adalah living document.** Update checklist dan progress tracker setiap kali ada perubahan status task.
>
> **Last Updated:** 24 September 2026
> **Maintained by:** Solkhan (mohamadsolkhannawawi)
