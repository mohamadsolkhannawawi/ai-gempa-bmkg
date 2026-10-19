# 📋 AI-GEMPA BMKG — Development Planning Master Document

> **Proyek:** AI-GEMPA BMKG (Sistem Deteksi & Pemantauan Gempa Bumi Real-Time)
> **Stack:** Python (FastAPI) · Vue 3 · Apache Kafka · MongoDB · Docker
> **Developer:** Hermes (AI Agent) + Mohamad Solkhan Nawawi (Owner)
> **Tanggal Dibuat:** 19 Oktober 2026
> **Status:** 🟡 Architecture Refactoring — Active Planning

---

## Daftar Isi

1. [Ringkasan Proyek & Arsitektur](#1-ringkasan-proyek--arsitektur)
2. [Kondisi Existing & Gap Analysis](#2-kondisi-existing--gap-analysis)
3. [Peran & Tanggung Jawab](#3-peran--tanggung-jawab)
4. [Konvensi & Best Practice](#4-konvensi--best-practice)
5. [Prosedur Kerja (SOP Development)](#5-prosedur-kerja-sop-development)
6. [Task Planning Detail — 8 Phase](#6-task-planning-detail--8-phase)
7. [Master Checklist](#7-master-checklist)
8. [Catatan Krusial & Decision Register](#8-catatan-krusial--decision-register)
9. [Catatan Teknis & Bug Register](#9-catatan-teknis--bug-register)
10. [Struktur Direktori Target](#10-struktur-direktori-target)
11. [Referensi Arsitektur](#11-referensi-arsitektur)

---

## 1. Ringkasan Proyek & Arsitektur

### 1.1 Gambaran Umum

AI-GEMPA BMKG adalah sistem real-time berbasis AI untuk deteksi, asosiasi, dan lokalisasi gempa bumi yang dioperasikan oleh BMKG. Sistem saat ini memiliki arsitektur monolitik dengan pilihan model AI yang statis, tanpa kemampuan penggantian model secara dinamis dari antarmuka pengguna.

**Tujuan Pengembangan ini:**
1. Menghadirkan **UI-Driven Pipeline Configuration** — operator BMKG dapat memilih dan mengganti algoritma AI (STA/LTA, PhaseNet, EQTransformer, GaMMA, PyOcto, dsb.) langsung dari antarmuka web tanpa perlu merestart kontainer atau menyentuh kode.
2. Menghadirkan **Pay-Per-Use Metering & Billing (IDR)** — sistem penagihan berbasis volume pemakaian riil, dengan kuota gratis bulanan, kalkulasi PPN 11%, dan invoice bulanan otomatis.

### 1.2 Komponen Sistem

| Komponen | Teknologi | Lokasi Kode |
|---|---|---|
| **Backend Controller (API)** | Python 3.10+, FastAPI, Uvicorn | `sispro-tews/` |
| **AI Inference Modules** | TensorFlow, ObsPy, SciPy, NumPy | `AI-TEWS/AI_modules_simple_ai/` |
| **Frontend Dashboard** | Vue 3, TypeScript, Vite, Pinia | `tews-ui-vue/` |
| **Messaging Bus** | Apache Kafka | Docker service `kafka` |
| **Database** | MongoDB | Docker service `mongodb` |
| **Cache / State** | Redis | Docker service `redis` |
| **Container Runtime** | Docker Compose + DinD Wrapper | `gempa-dind-wrapper/` |

### 1.3 Arsitektur Target (Tingkat Tinggi)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        OPERATOR (Browser)                                │
│  Vue 3 Dashboard: PipelineWizard • PriceCalculator • BillingDashboard   │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ REST API (HTTPS)
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  CONTROL PLANE  (sispro-tews / FastAPI)                  │
│                                                                          │
│  api/main.py ← single entry point /api/v2/*                              │
│  ├── /profiles   (CRUD + validate + activate)                            │
│  ├── /models     (catalog penyedia AI)                                   │
│  ├── /pricing    (estimasi biaya real-time)                              │
│  └── /billing    (invoice + payment)                                     │
│                                                                          │
│  services/: ProfileService • PricingService • MeteringService           │
│  core/:     Pipeline • Pricing • UsageEvent • CompiledPipeline           │
│  providers/: BaseProvider • ProviderRegistry • [adapters]                │
└──────┬───────────────────────┬───────────────────────────────────────────┘
       │ Kafka config_events   │ Kafka metering_events
       ▼                       ▼
┌──────────────────┐   ┌────────────────────────────────────────────────┐
│  AI-TEWS MODULES │   │           METERING & BILLING PLANE              │
│                  │   │  metering_module/consumer.py + aggregator.py   │
│  p_pick_module   │   │  billing_module/invoice_generator.py (cron)    │
│  assoc_module    │   │  MongoDB: usage_daily, invoices                │
│  locmag_module   │   └────────────────────────────────────────────────┘
│  (via BaseProvider│
│   + ProviderRegistry)│
└──────────────────┘
```

### 1.4 Aliran Data Utama

```
[Operator: Pilih Model di UI]
  ↓ POST /api/v2/profiles/{id}/activate
  ↓ ProfileService.compile() → SHA-256 rev
  ↓ Kafka: config_events topic
  ↓ ProfileOrchestratorWorker.consume()
  ↓ Redis: set active_provider_{stage} = provider_id
  ↓ AI-TEWS Modules: ProviderRegistry.get_provider(active_provider_id)
  ↓ Inference berjalan dengan model baru

[Setiap Inferensi]
  ↓ Provider.infer(data) → emit metering_events (fire-and-forget)
  ↓ MeteringAggregatorWorker.consume()
  ↓ MongoDB: upsert usage_daily{workspace, stage, provider, date}

[Hari ke-1 Setiap Bulan, 00:00:00 WIB]
  ↓ BillingGeneratorWorker.generate_invoices()
  ↓ PricingService.calculate_invoice(workspace, prev_month)
  ↓ MongoDB: insert invoices{workspace, period, breakdown, ppn, total_idr}
  ↓ Email notifikasi ke billing contact workspace
```

---

## 2. Kondisi Existing & Gap Analysis

### 2.1 State Saat Ini

| Area | Kondisi Existing | Status |
|---|---|---|
| **Entry Point** | Multiple: `app.py`, `app1.py`, `controller_api_app.py` | ❌ Perlu konsolidasi |
| **Model AI** | Hardcoded di tiap stage module | ❌ Perlu Provider Abstraction |
| **Pipeline Config** | Static di environment var & kode | ❌ Perlu Profile Service |
| **Harga & Tarif** | Tidak ada sistem tarif | ❌ Perlu Catalog + Rates |
| **Metering** | Tidak ada pencatatan beban komputasi | ❌ Perlu Kafka + Aggregator |
| **Billing** | Tidak ada sistem penagihan | ❌ Perlu Invoice Generator |
| **Frontend Wizard** | Tidak ada wizard konfigurasi pipeline | ❌ Perlu PipelineWizard.vue |
| **Struktur Domain** | Flat files di `controller_module/` | ❌ Perlu DDD structure |
| **Test Coverage** | Minimal, beberapa di `development/test_*.py` | ⚠️ Perlu ekspansi |

### 2.2 Yang TIDAK Berubah (Stable — Jangan Ganggu)

| Area | Status |
|---|---|
| **SeedLink Client** (`seedlink_module/`) | ✅ Stabil, tetap utuh |
| **WebSocket Gateway** (real-time push picks ke UI) | ✅ Stabil, tetap utuh |
| **MongoDB schema `picks`, `events`** | ✅ Tetap, hanya tambah koleksi baru |
| **Docker Compose outer** (DinD Wrapper, Kafka, MongoDB, Redis) | ✅ Hanya tambah services, tidak ubah yang ada |
| **Endpoint lama `/api/*`** | ✅ Tetap aktif (backward compatible) |

---

## 3. Peran & Tanggung Jawab

### 3.1 Owner & Arsitek

**Mohamad Solkhan Nawawi** — Pemilik proyek dan arsitek utama. Semua decision register (D-001 s/d D-012) adalah keputusan final dari Owner. Hermes berkonsultasi ke Owner jika ada ambiguitas atau konflik arsitektur.

### 3.2 AI Agent Hermes — Scope

| Scope | Repository/Direktori | Tanggung Jawab Hermes |
|---|---|---|
| **Backend Domain** | `sispro-tews/core/`, `services/`, `infrastructure/`, `api/`, `providers/`, `workers/` | Implementasi penuh |
| **Catalog Module** | `sispro-tews/catalog_module/` | YAML loader + endpoint |
| **Metering Module** | `sispro-tews/metering_module/` | Consumer + Aggregator |
| **Billing Module** | `sispro-tews/billing_module/` | Invoice generator + webhook |
| **Frontend** | `tews-ui-vue/src/` | Vue components + Pinia stores |
| **AI Provider Adapters** | `sispro-tews/providers/` | Wrapper adapters (bukan implementasi model) |
| **Dokumentasi** | `development/` | Perbarui planning + API contract |

### 3.3 Tanggung Jawab Per Phase

| Phase | Tanggung Jawab | Estimasi |
|---|---|---|
| P0 Foundation | Struktur direktori, entry point, DI setup | 3-4 hari |
| P1 Catalog | manifest.yaml, rates.yaml, API endpoint | 2-3 hari |
| P2 Profile Service | CRUD pipeline profiles, compile, activate | 4-5 hari |
| P3 Pricing Service | Estimasi IDR, hitung invoice | 3-4 hari |
| P4 Provider Abstraction | BaseProvider, Registry, 8 adapters | 6-8 hari |
| P5 Metering | Kafka producer, consumer, aggregator | 4-5 hari |
| P6 Billing | Invoice cron, payment webhook | 3-4 hari |
| P7 Frontend | Wizard, PriceCalc, Billing dashboard | 7-10 hari |
| P8 Deployment & QA | Docker, e2e tests, docs | 4-5 hari |
| **Total Estimasi** | | **~36-48 hari kerja** |

---

## 4. Konvensi & Best Practice

### 4.1 Backend Python (FastAPI + Domain-Driven Design)

#### Struktur Domain

```
sispro-tews/
├── core/           ← Entitas murni, tanpa dependency eksternal
├── services/       ← Orkestrasi business logic
├── infrastructure/ ← Adapter: DB, Kafka, Redis, Storage
├── api/            ← HTTP routes, schemas, DI
├── providers/      ← AI model adapters
├── workers/        ← Background jobs, Kafka consumers
├── catalog_module/ ← Data YAML + loader
├── metering_module/← Metering consumer + aggregator
└── billing_module/ ← Invoice generator + payment handler
```

#### Aturan Lapisan (Dependency Rule)

```
api/ → services/ → core/
              ↓
        infrastructure/   ← hanya services yang boleh memanggil infrastructure
```

- `core/` **TIDAK** boleh import dari `services/`, `infrastructure/`, atau `api/`
- `services/` boleh import dari `core/` dan `infrastructure/`
- `api/` boleh import dari `services/` dan `core/` (via DI)

#### API Design

- **Versioning:** semua endpoint baru di bawah `/api/v2/`
- **Response format standar:**
  ```json
  {
    "success": true,
    "data": {},
    "meta": {"page": 1, "total": 100},
    "message": null
  }
  ```
- **Error format:**
  ```json
  {
    "success": false,
    "data": null,
    "errors": {"field": ["validation message"]},
    "message": "Validation failed"
  }
  ```
- Gunakan Pydantic v2 untuk semua schema request/response
- HTTP status code semantik: 200, 201, 400, 404, 422, 500

#### Database (MongoDB)

- Gunakan `pymongo` (sync) atau `motor` (async) — pilih satu dan konsisten
- Setiap operasi write gunakan `upsert=True` untuk idempotency
- Semua koleksi baru wajib memiliki index yang relevan sebelum production
- Jangan gunakan `_id` MongoDB langsung di response API — expose sebagai `id` string

#### Providers & BaseProvider

- Setiap provider **wajib** implement semua abstract method `BaseProvider`
- `infer()` wajib emit metering event **setelah** inferensi selesai (bukan sebelum)
- Gunakan `try/except` di setiap `emit_metering_event()` — kegagalan metering **tidak boleh** menghentikan inferensi
- `health_check()` harus bisa dipanggil oleh health endpoint tanpa efek samping

### 4.2 Frontend Vue 3 + TypeScript

#### Pinia Store Pattern

```typescript
// Pattern standar untuk async actions
export const useCatalogStore = defineStore('catalog', () => {
  const providers = ref<ProviderInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchProviders = async (stage?: string) => {
    loading.value = true
    error.value = null
    try {
      providers.value = await catalogApi.getAll(stage)
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  return { providers, loading, error, fetchProviders }
})
```

#### API Client Pattern

```typescript
// services/catalogApi.ts — tidak ada axios global, gunakan fetch atau axios instance
import axios from './axiosInstance'  // base URL dari env

export const catalogApi = {
  getAll: (stage?: string) =>
    axios.get<ProviderInfo[]>('/api/v2/models', { params: { stage } })
      .then(r => r.data.data),
}
```

#### Debounce untuk Pricing Estimate

```typescript
// Wajib debounce 500ms untuk POST /api/v2/pricing/estimate
// Gunakan VueUse: useDebounceFn atau implementasi manual dengan clearTimeout
```

#### Komponen Design Rules

- Satu komponen = satu tanggung jawab
- Props hanya untuk data yang datang dari parent
- Emit events untuk komunikasi child → parent
- Gunakan Composables untuk logika yang digunakan di >1 komponen
- Semua teks IDR diformat dengan `Intl.NumberFormat('id-ID', {style: 'currency', currency: 'IDR'})`

### 4.3 Kafka Messaging

- Topik yang digunakan:
  - `config_events` — aktivasi profil pipeline
  - `metering_events` — tiket beban inferensi
- Setiap message adalah JSON dengan field `event_type`, `workspace_id`, `timestamp`, dan payload spesifik
- Producer: **non-blocking, fire-and-forget** untuk metering (tidak `await`)
- Consumer: **loop tak terbatas** dengan graceful shutdown via signal

### 4.4 Git & Versioning

- Branch kerja: `feature/architecture-refactor`
- Branch `main` hanya disentuh saat merge final setelah QA lulus
- Tag semantic version saat milestone phase selesai: `v2.0.0-alpha`, `v2.0.0-beta`, `v2.0.0`

---

## 5. Prosedur Kerja (SOP Development)

### 5.1 Branching Strategy

```
main (stable baseline)
  └── feature/architecture-refactor  ← semua pekerjaan di sini
        ├── [P0] Commits: [P0][TASK-FOUNDATION-*]
        ├── [P1] Commits: [P1][TASK-CATALOG-*]
        ├── [P2] Commits: [P2][TASK-PROFILE-*]
        ├── [P3] Commits: [P3][TASK-PRICING-*]
        ├── [P4] Commits: [P4][TASK-PROVIDER-*]
        ├── [P5] Commits: [P5][TASK-METERING-*]
        ├── [P6] Commits: [P6][TASK-BILLING-*]
        ├── [P7] Commits: [P7][TASK-FRONTEND-*]
        └── [P8] Commits: [P8][TASK-DEPLOY-*]
```

### 5.2 Workflow Per Task

```
┌──────────────────────────────────────────────────────┐
│  1. PLANNING                                          │
│  → Baca task di DEVELOPMENT_PLANNING_AI_GEMPA.md     │
│  → Identifikasi file yang akan dibuat/diubah         │
│  → Identifikasi dependency pada task lain            │
│  → Buat rencana implementasi (pseudo-code jika perlu)│
├──────────────────────────────────────────────────────┤
│  2. DEVELOPMENT                                       │
│  → Pastikan di branch feature/architecture-refactor  │
│  → Buat/edit file sesuai rencana                     │
│  → Validasi dengan test (pytest / npm run build)     │
│  → Commit KECIL per satu unit logis                  │
├──────────────────────────────────────────────────────┤
│  3. VERIFIKASI                                        │
│  → Jalankan test suite penuh                         │
│  → Cek backward compatibility endpoint lama          │
│  → Cek tidak ada credential di dalam file yang commit│
├──────────────────────────────────────────────────────┤
│  4. DOKUMENTASI                                       │
│  → Update checklist di §7 dokumen ini                │
│  → Update API_CONTRACT.md jika ada endpoint baru     │
│  → Catat blocker atau keputusan baru di §9           │
└──────────────────────────────────────────────────────┘
```

### 5.3 Test Protocol

| Layer | Tool | Kapan Dijalankan |
|---|---|---|
| Unit Backend | `pytest -v` | Sebelum setiap commit |
| Integration Backend | `pytest tests/integration/ -v` | Sebelum merge ke `main` |
| Frontend Build | `npm run build` | Sebelum setiap commit |
| Frontend Unit | `npm run test:unit` | Sebelum setiap commit |
| E2E | Manual + script | Sebelum release milestone |

---

## 6. Task Planning Detail — 8 Phase

### PHASE 0 — FOUNDATION

**Goal:** Struktur direktori DDD siap, entry point tunggal, dependency injection terkonfigurasi.  
**Estimasi:** 3-4 hari kerja  
**Dependency:** Tidak ada. Ini titik mulai.

| Task ID | Deskripsi | File yang Dibuat/Diubah | Priority |
|---|---|---|---|
| TASK-FOUNDATION-01 | Buat seluruh direktori `core/`, `services/`, `infrastructure/`, `api/`, `providers/`, `workers/`, `catalog_module/`, `metering_module/`, `billing_module/` beserta `__init__.py` | ~25 `__init__.py` files | 🔴 Critical |
| TASK-FOUNDATION-02 | Salin & adaptasikan `pipeline_profile.py` → `core/profile.py`; `pricing_model.py` → `core/pricing.py` | `core/profile.py`, `core/pricing.py` | 🔴 Critical |
| TASK-FOUNDATION-03 | Buat `core/events.py` (UsageEvent, ConfigActivatedEvent) | `core/events.py` | 🔴 Critical |
| TASK-FOUNDATION-04 | Buat `api/main.py` single FastAPI entry point dengan placeholder routers | `api/main.py`, `api/dependencies.py` | 🔴 Critical |
| TASK-FOUNDATION-05 | Update `.env.example` dengan semua env var baru | `sispro-tews/.env.example` | 🟡 High |
| TASK-FOUNDATION-06 | Setup pytest dengan `conftest.py` dan fixtures dasar | `tests/conftest.py`, `pytest.ini` | 🟡 High |
| TASK-FOUNDATION-07 | Verifikasi baseline test dari `development/test_*.py` lulus di struktur baru | — | 🟡 High |

---

### PHASE 1 — CATALOG & MODEL REGISTRY

**Goal:** Registry penyedia model AI dan tabel tarif IDR siap; endpoint `/api/v2/models` aktif.  
**Estimasi:** 2-3 hari kerja  
**Dependency:** PHASE 0 selesai

| Task ID | Deskripsi | File yang Dibuat/Diubah | Priority |
|---|---|---|---|
| TASK-CATALOG-01 | Buat `manifest.yaml` dengan semua 8 provider (STA/LTA, PhaseNet, EQTransformer, DBSCAN, GaMMA, PyOcto, Geiger, NonLinLoc) | `catalog_module/data/manifest.yaml` | 🔴 Critical |
| TASK-CATALOG-02 | Buat `rates.yaml` dengan tarif IDR, free quota, dan unit per provider | `catalog_module/data/rates.yaml` | 🔴 Critical |
| TASK-CATALOG-03 | Implementasi `ProviderCatalog` class — loader YAML ke memori, method `get_all()`, `get_by_stage()`, `get_info()` | `catalog_module/provider_catalog.py` | 🔴 Critical |
| TASK-CATALOG-04 | Buat Pydantic schemas untuk provider response | `api/schemas/catalog_schema.py` | 🟡 High |
| TASK-CATALOG-05 | Buat route `GET /api/v2/models` dan `GET /api/v2/models?stage=p_pick` | `api/routes/models_routes.py` | 🟡 High |
| TASK-CATALOG-06 | Unit test: `test_catalog_load_yaml()`, `test_filter_by_stage()` | `tests/unit/catalog/test_provider_catalog.py` | 🟡 High |
| TASK-CATALOG-07 | Integration test: `test_get_models_endpoint()` → 200, correct shape | `tests/integration/api/test_models_api.py` | 🟢 Medium |

---

### PHASE 2 — PROFILE SERVICE & PROFILES API

**Goal:** Siklus hidup pipeline profile (Draft → Validate → Compile → Activate) berfungsi penuh via REST API.  
**Estimasi:** 4-5 hari kerja  
**Dependency:** PHASE 1 selesai (butuh CatalogService untuk validasi)

| Task ID | Deskripsi | File yang Dibuat/Diubah | Priority |
|---|---|---|---|
| TASK-PROFILE-01 | Implementasi `ProfileService`: `create_draft()`, `validate()`, `compile()` (SHA-256 rev), `activate()` (emit Kafka) | `services/profile_service.py` | 🔴 Critical |
| TASK-PROFILE-02 | Implementasi `ProfileRepository` — MongoDB adapter (CRUD + status update) | `infrastructure/repositories/profile_repository.py` | 🔴 Critical |
| TASK-PROFILE-03 | Buat Pydantic schemas: `ProfileCreateRequest`, `ProfileUpdateRequest`, `ProfileResponse` | `api/schemas/profile_schema.py` | 🟡 High |
| TASK-PROFILE-04 | Buat router `/api/v2/profiles` (7 endpoints: list, get, create, update, delete, validate, activate) | `api/routes/profiles_routes.py` | 🔴 Critical |
| TASK-PROFILE-05 | Implementasi `ProfileOrchestratorWorker` — Kafka consumer `config_events`, tulis ke Redis `active_provider_{stage}` | `workers/profile_orchestrator.py` | 🟡 High |
| TASK-PROFILE-06 | Unit test: `test_compile_deterministic()`, `test_validate_unknown_provider()`, `test_validate_incompatible_stages()` | `tests/unit/services/test_profile_service.py` | 🟡 High |
| TASK-PROFILE-07 | Integration test: `test_create_draft_validate_activate_flow()` | `tests/integration/api/test_profiles_api.py` | 🟡 High |

---

### PHASE 3 — PRICING SERVICE & BILLING API

**Goal:** Kalkulasi estimasi biaya live (IDR) dari pilihan model; API pricing dan billing siap.  
**Estimasi:** 3-4 hari kerja  
**Dependency:** PHASE 1 selesai

| Task ID | Deskripsi | File yang Dibuat/Diubah | Priority |
|---|---|---|---|
| TASK-PRICING-01 | Implementasi `PricingService`: `estimate_from_stages(stages, volume)` dan `calculate_invoice(workspace_id, month)` | `services/pricing_service.py` | 🔴 Critical |
| TASK-PRICING-02 | Buat Pydantic schemas: `PriceEstimateRequest`, `PriceEstimateResponse`, `InvoiceResponse` | `api/schemas/pricing_schema.py` | 🟡 High |
| TASK-PRICING-03 | Buat router `/api/v2/pricing/estimate` (POST), `/api/v2/pricing/rates` (GET), `/api/v2/pricing/usage/{workspace}` (GET) | `api/routes/pricing_routes.py` | 🔴 Critical |
| TASK-PRICING-04 | Buat router `/api/v2/billing/invoices` (GET list + GET detail), `/api/v2/billing/invoices/{id}/pdf` | `api/routes/billing_routes.py` | 🟡 High |
| TASK-PRICING-05 | Implementasi `InvoiceRepository` — MongoDB adapter untuk koleksi `invoices` | `infrastructure/repositories/invoice_repository.py` | 🟡 High |
| TASK-PRICING-06 | Unit test: `test_estimate_within_free_quota()` (total = 0), `test_estimate_ppn_11_percent()`, `test_invoice_full_calculation()` | `tests/unit/services/test_pricing_service.py` | 🟡 High |

---

### PHASE 4 — PROVIDER ABSTRACTION

**Goal:** Semua 8 algoritma AI seismik dibungkus `BaseProvider`; dapat ditukar secara dinamis via profil aktif.  
**Estimasi:** 6-8 hari kerja  
**Dependency:** PHASE 0 selesai; PHASE 5 (metering) berjalan paralel

| Task ID | Deskripsi | File yang Dibuat/Diubah | Priority |
|---|---|---|---|
| TASK-PROVIDER-01 | Definisikan `BaseProvider` abstract class dengan `infer()`, `get_info()`, `health_check()` | `providers/base.py` | 🔴 Critical |
| TASK-PROVIDER-02 | Implementasi `ProviderRegistry` — auto-register + factory `get_provider(id)` + `list_by_stage(stage)` | `providers/registry.py` | 🔴 Critical |
| TASK-PROVIDER-03 | Adapter: `STALTAProvider` | `providers/p_pick/sta_lta.py` | 🔴 Critical |
| TASK-PROVIDER-04 | Adapter: `PhaseNetProvider` | `providers/p_pick/phasenet.py` | 🔴 Critical |
| TASK-PROVIDER-05 | Adapter: `EQTransformerProvider` | `providers/p_pick/eqtransformer.py` | 🟡 High |
| TASK-PROVIDER-06 | Adapter: `DBSCANProvider` | `providers/association/dbscan_simple.py` | 🔴 Critical |
| TASK-PROVIDER-07 | Adapter: `GaMMAProvider` | `providers/association/gamma.py` | 🟡 High |
| TASK-PROVIDER-08 | Adapter: `PyOctoProvider` | `providers/association/pyocto.py` | 🟡 High |
| TASK-PROVIDER-09 | Adapter: `GeigerProvider` | `providers/locmag/geiger.py` | 🟡 High |
| TASK-PROVIDER-10 | Adapter: `NonLinLocProvider` | `providers/locmag/nonlinloc.py` | 🟡 High |
| TASK-PROVIDER-11 | Integrasi Registry ke `AI-TEWS/p_pick_module` — baca `active_provider` dari Redis | `AI-TEWS/.../p_pick_module/process.py` | 🔴 Critical |
| TASK-PROVIDER-12 | Integrasi Registry ke `assoc_module` dan `locmag_module` | `AI-TEWS/.../assoc_module/`, `locmag_module/` | 🟡 High |
| TASK-PROVIDER-13 | Unit test per provider: infer() dengan fixture waveform dummy, health_check() | `tests/unit/providers/test_*.py` | 🟡 High |
| TASK-PROVIDER-14 | Test: hot-swap provider saat pipeline aktif (via Kafka config_events mock) | `tests/integration/test_provider_hot_swap.py` | 🟢 Medium |

---

### PHASE 5 — METERING INFRASTRUCTURE

**Goal:** Tiket beban inferensi dikumpulkan asinkron via Kafka dan diagregasikan ke MongoDB `usage_daily`.  
**Estimasi:** 4-5 hari kerja  
**Dependency:** PHASE 4 (provider emit event); berjalan paralel dengan P4

| Task ID | Deskripsi | File yang Dibuat/Diubah | Priority |
|---|---|---|---|
| TASK-METERING-01 | Implementasi `EventProducer` — Kafka producer non-blocking untuk `metering_events` | `infrastructure/kafka/producers.py` | 🔴 Critical |
| TASK-METERING-02 | Implementasi `MeteringConsumer` — Kafka consumer untuk `metering_events` | `metering_module/consumer.py` | 🔴 Critical |
| TASK-METERING-03 | Implementasi `MeteringAggregator` — in-memory buffer, flush ke MongoDB setiap 10 menit | `metering_module/aggregator.py` | 🔴 Critical |
| TASK-METERING-04 | Buat `UsageRepository` — MongoDB adapter untuk `usage_daily` dengan `upsert` | `infrastructure/repositories/usage_repository.py` | 🟡 High |
| TASK-METERING-05 | Script migrasi index: `{workspace_id, date, stage, provider_id}` compound unique | `database/migrations/002_usage_daily_index.js` | 🟡 High |
| TASK-METERING-06 | Unit test: `test_aggregator_accumulates_correctly()`, `test_flush_to_mongodb()` | `tests/unit/metering/test_aggregator.py` | 🟡 High |
| TASK-METERING-07 | Test ketahanan: Kafka mati → pipeline tidak crash, metering tertunda tapi inferensi lanjut | `tests/integration/test_metering_fault_tolerance.py` | 🟡 High |

---

### PHASE 6 — BILLING MODULE

**Goal:** Invoice bulanan dibuat otomatis pada hari pertama setiap bulan; webhook pembayaran berfungsi.  
**Estimasi:** 3-4 hari kerja  
**Dependency:** PHASE 3 (PricingService) + PHASE 5 (usage_daily data)

| Task ID | Deskripsi | File yang Dibuat/Diubah | Priority |
|---|---|---|---|
| TASK-BILLING-01 | Implementasi `BillingGeneratorWorker` — cron `0 0 1 * *`, loop workspaces, panggil `PricingService.calculate_invoice()` | `billing_module/invoice_generator.py` | 🔴 Critical |
| TASK-BILLING-02 | Implementasi `PaymentHandler` — webhook endpoint, signature verification, update status invoice | `billing_module/payment_handler.py` | 🟡 High |
| TASK-BILLING-03 | Script migrasi koleksi `invoices` + index `{workspace_id, period_start}` | `database/migrations/003_invoices_collection.js` | 🟡 High |
| TASK-BILLING-04 | Implementasi email notifikasi invoice (SMTP atau SendGrid) | `billing_module/email_sender.py` | 🟢 Medium |
| TASK-BILLING-05 | Unit test: `test_invoice_correct_breakdown()`, `test_invoice_free_quota_deducted()`, `test_invoice_ppn()` | `tests/unit/billing/test_invoice_generator.py` | 🟡 High |
| TASK-BILLING-06 | Test manual cron: jalankan generate_invoices() secara manual, verifikasi dokumen di MongoDB | — | 🟡 High |

---

### PHASE 7 — FRONTEND PIPELINE WIZARD & BILLING DASHBOARD

**Goal:** Operator dapat mengkonfigurasi pipeline AI dan melihat estimasi biaya live via antarmuka web.  
**Estimasi:** 7-10 hari kerja  
**Dependency:** PHASE 1 (model catalog API), PHASE 2 (profiles API), PHASE 3 (pricing API)

| Task ID | Deskripsi | File yang Dibuat/Diubah | Priority |
|---|---|---|---|
| TASK-FRONTEND-01 | Setup Pinia stores: `catalogStore.ts`, `profileStore.ts`, `pricingStore.ts` | `tews-ui-vue/src/stores/*.ts` | 🔴 Critical |
| TASK-FRONTEND-02 | Buat API service clients: `catalogApi.ts`, `profileApi.ts`, `pricingApi.ts`, `billingApi.ts` | `tews-ui-vue/src/services/*.ts` | 🔴 Critical |
| TASK-FRONTEND-03 | Implementasi `PipelineWizard.vue` (4 langkah: Mode → Stages → Models → Review) | `tews-ui-vue/src/components/wizard/PipelineWizard.vue` | 🔴 Critical |
| TASK-FRONTEND-04 | Komponen pendamping wizard: `StageSelector.vue`, `ModelCard.vue`, `ReviewPanel.vue` | `tews-ui-vue/src/components/wizard/*.vue` | 🟡 High |
| TASK-FRONTEND-05 | Implementasi `PriceCalculator.vue` (sidebar estimasi IDR live, debounce 500ms) | `tews-ui-vue/src/components/pricing/PriceCalculator.vue` | 🔴 Critical |
| TASK-FRONTEND-06 | Implementasi komposisi `useDebounce.ts` | `tews-ui-vue/src/composables/useDebounce.ts` | 🟡 High |
| TASK-FRONTEND-07 | Buat halaman `PipelineBuilder.vue` (route `/pipeline-builder`) — host Wizard + PriceCalculator | `tews-ui-vue/src/views/PipelineBuilder.vue` | 🔴 Critical |
| TASK-FRONTEND-08 | Buat halaman `Billing.vue` (route `/billing`) — chart pemakaian harian, sisa kuota, tabel faktur | `tews-ui-vue/src/views/Billing.vue` | 🟡 High |
| TASK-FRONTEND-09 | Integrasi routing di `router/index.ts` | `tews-ui-vue/src/router/index.ts` | 🟡 High |
| TASK-FRONTEND-10 | Utilitas format IDR: `useFormatCurrency.ts` | `tews-ui-vue/src/composables/useFormatCurrency.ts` | 🟡 High |
| TASK-FRONTEND-11 | Unit test Pinia stores (Vitest) | `tews-ui-vue/src/stores/__tests__/*.spec.ts` | 🟢 Medium |
| TASK-FRONTEND-12 | Build check: `npm run build` harus zero error | — | 🔴 Critical |

---

### PHASE 8 — DEPLOYMENT, TESTING & FINALISASI

**Goal:** Semua service baru berjalan stabil di lingkungan Docker; backward compat terjaga; dokumentasi lengkap.  
**Estimasi:** 4-5 hari kerja  
**Dependency:** SEMUA phase sebelumnya selesai

| Task ID | Deskripsi | File yang Dibuat/Diubah | Priority |
|---|---|---|---|
| TASK-DEPLOY-01 | Tambah services `metering_aggregator` dan `billing_generator` ke `docker-compose.yml` internal sispro-tews | `sispro-tews/docker-compose.yml` | 🔴 Critical |
| TASK-DEPLOY-02 | Buat `Dockerfile.metering` dan `Dockerfile.billing` | `sispro-tews/docker/Dockerfile.*` | 🟡 High |
| TASK-DEPLOY-03 | Buat `docker-compose.dev.yml` untuk development lokal tanpa DinD | `docker-compose.dev.yml` | 🟡 High |
| TASK-DEPLOY-04 | E2E test skenario: operator pilih model → aktivasi → inferensi → metering → invoice | `tests/e2e/test_full_pipeline_flow.py` | 🔴 Critical |
| TASK-DEPLOY-05 | Verifikasi backward compat: semua endpoint `/api/*` lama merespons 200 | `tests/e2e/test_backward_compat.py` | 🔴 Critical |
| TASK-DEPLOY-06 | Update `API_CONTRACT.md` dengan semua endpoint `/api/v2/*` baru | `development/API_CONTRACT.md` | 🟡 High |
| TASK-DEPLOY-07 | Buat `PROVIDER_DEVELOPMENT_GUIDE.md` — cara menambah provider model AI baru | `development/PROVIDER_DEVELOPMENT_GUIDE.md` | 🟡 High |
| TASK-DEPLOY-08 | Update `DEPLOYMENT_GUIDE.md` dengan service baru dan environment vars | `development/DEPLOYMENT_GUIDE.md` | 🟡 High |
| TASK-DEPLOY-09 | Tag milestone: `git tag v2.0.0-alpha` setelah semua phase lulus | — | 🟢 Medium |

---

## 7. Master Checklist

### PHASE 0 — Foundation

- [x] TASK-FOUNDATION-01: Direktori DDD + `__init__.py` dibuat — ✅ (core/, services/, infrastructure/, api/, providers/, workers/, catalog_module/, metering_module/, billing_module/)
- [x] TASK-FOUNDATION-02: Core domain models dipindahkan — ✅ (core/profile.py, core/pricing.py)
- [x] TASK-FOUNDATION-03: DESIGN_DECISIONS.md + ADR register — ✅ (8 ADR documented)
- [x] TASK-FOUNDATION-04: `core/event.py` Event Detection Domain — ✅ (Waveform, Pick, Cluster, Arrival, Event entities)
- [x] TASK-FOUNDATION-05: `core/workspace.py` Workspace & User Domain — ✅ (User, Workspace, Subscription, WorkspaceService)
- [x] TASK-FOUNDATION-06,07: Unit tests TDD stubs — ✅ (tests/unit/test_profile.py, test_pricing.py)
- [x] TASK-FOUNDATION-08: Kafka abstraction + Event repository — ✅ (infrastructure/kafka/consumer.py, producer.py, infrastructure/repositories/event_repo.py)

### PHASE 1 — Catalog

- [x] TASK-CATALOG-01: `manifest.yaml` dibuat dengan 8 provider — ✅ 19‑Okt‑2026 (catalog_module/data/manifest.yaml, 147 lines)
- [x] TASK-CATALOG-02: `rates.yaml` dibuat dengan tarif IDR — ✅ 19‑Okt‑2026 (catalog_module/data/rates.yaml, 138 lines)
- [x] TASK-CATALOG-03: `ProviderCatalog` loader diimplementasi — ✅ 19‑Okt‑2026 (catalog_module/catalog.py, 189 lines)
- [x] TASK-CATALOG-04: Schemas katalog dibuat — ✅ 19‑Okt‑2026 (api/schemas/catalog.py, 102 lines)
- [x] TASK-CATALOG-05: Endpoint `GET /api/v2/models` aktif — ✅ 19‑Okt‑2026 (api/routes/catalog.py, 196 lines)
- [x] TASK-CATALOG-06: Unit test catalog lulus — ✅ 19‑Okt‑2026 (tests/unit/test_catalog.py, 186 lines)
- [x] TASK-CATALOG-07: Integration test endpoint lulus — ✅ 19‑Okt‑2026 (tests/integration/test_catalog_api.py, 209 lines)

### PHASE 2 — Profile Service

- [x] TASK-PROFILE-01: `ProfileService` domain diimplementasi — ✅ 19‑Okt‑2026 19:50 (core/profile_service.py, 353 lines, lifecycle DRAFT→ACTIVE→ARCHIVED)
- [x] TASK-PROFILE-02: `ProfileRepository` MongoDB adapter dibuat — ✅ 19‑Okt‑2026 19:51 (infrastructure/repositories/profile_repo.py, MongoDB + in-memory)
- [x] TASK-PROFILE-03: Pydantic schemas dibuat — ✅ 19‑Okt‑2026 19:52 (api/schemas/profile.py, 151 lines)
- [x] TASK-PROFILE-04: Endpoint `/api/v2/profiles` dibuat (9 endpoints) — ✅ 19‑Okt‑2026 19:53 (api/routes/profile.py, 353 lines)
- [x] TASK-PROFILE-05: Unit tests dibuat — ✅ 19‑Okt‑2026 19:54 (tests/unit/test_profile_service.py, 17 test cases)
- [x] TASK-PROFILE-06: Integration tests dibuat — ✅ 19‑Okt‑2026 19:55 (tests/integration/test_profile_api.py, 19 test cases)
- [x] TASK-PROFILE-07: API documentation ditulis — ✅ 19‑Okt‑2026 19:56 (api/docs/profile_api.md, 7.2KB)

### PHASE 3 — Pricing Service

- [x] TASK-PRICING-01: `PricingService` estimate + invoice — ✅ 19‑Okt‑2026 20:00 (core/pricing_service.py, 515 lines, PPN 11% included)
- [x] TASK-PRICING-02: Schemas pricing — ✅ 19‑Okt‑2026 20:01 (api/schemas/pricing.py, 145 lines)
- [x] TASK-PRICING-03: Router pricing — ✅ 19‑Okt‑2026 20:02 (api/routes/pricing.py, 133 lines)
- [x] TASK-PRICING-04: Router billing — ✅ 19‑Okt‑2026 20:03 (api/routes/billing.py, 379 lines, 6 endpoints)
- [x] TASK-PRICING-05: `InvoiceRepository` — ✅ 19‑Okt‑2026 20:04 (infrastructure/repositories/invoice_repo.py, MongoDB + in-memory)
- [x] TASK-PRICING-06: Unit tests — ✅ 19‑Okt‑2026 20:05 (tests/unit/test_pricing_service.py, 11 test cases)

### PHASE 4 — Provider Abstraction

- [ ] TASK-PROVIDER-01: `BaseProvider` abstract class
- [ ] TASK-PROVIDER-02: `ProviderRegistry`
- [ ] TASK-PROVIDER-03: STALTAProvider adapter
- [ ] TASK-PROVIDER-04: PhaseNetProvider adapter
- [ ] TASK-PROVIDER-05: EQTransformerProvider adapter
- [ ] TASK-PROVIDER-06: DBSCANProvider adapter
- [ ] TASK-PROVIDER-07: GaMMAProvider adapter
- [ ] TASK-PROVIDER-08: PyOctoProvider adapter
- [ ] TASK-PROVIDER-09: GeigerProvider adapter
- [ ] TASK-PROVIDER-10: NonLinLocProvider adapter
- [ ] TASK-PROVIDER-11: Integrasi ke p_pick_module
- [ ] TASK-PROVIDER-12: Integrasi ke assoc dan locmag module
- [ ] TASK-PROVIDER-13: Unit test per provider lulus
- [ ] TASK-PROVIDER-14: Test hot-swap lulus

### PHASE 5 — Metering

- [ ] TASK-METERING-01: `EventProducer` Kafka
- [ ] TASK-METERING-02: `MeteringConsumer`
- [ ] TASK-METERING-03: `MeteringAggregator` (windowing + flush)
- [ ] TASK-METERING-04: `UsageRepository`
- [ ] TASK-METERING-05: Index `usage_daily` dibuat
- [ ] TASK-METERING-06: Unit test aggregator lulus
- [ ] TASK-METERING-07: Test fault tolerance lulus

### PHASE 6 — Billing

- [ ] TASK-BILLING-01: `BillingGeneratorWorker` cron
- [ ] TASK-BILLING-02: `PaymentHandler` webhook
- [ ] TASK-BILLING-03: Koleksi `invoices` dan index
- [ ] TASK-BILLING-04: Email notifikasi invoice
- [ ] TASK-BILLING-05: Unit test billing lulus
- [ ] TASK-BILLING-06: Test manual cron berhasil

### PHASE 7 — Frontend

- [ ] TASK-FRONTEND-01: Pinia stores (catalog, profile, pricing)
- [ ] TASK-FRONTEND-02: API service clients
- [ ] TASK-FRONTEND-03: `PipelineWizard.vue` (4 langkah)
- [ ] TASK-FRONTEND-04: Komponen pendamping wizard
- [ ] TASK-FRONTEND-05: `PriceCalculator.vue` sidebar live
- [ ] TASK-FRONTEND-06: `useDebounce.ts` composable
- [ ] TASK-FRONTEND-07: Halaman `PipelineBuilder.vue`
- [ ] TASK-FRONTEND-08: Halaman `Billing.vue`
- [ ] TASK-FRONTEND-09: Routing `/pipeline-builder` dan `/billing`
- [ ] TASK-FRONTEND-10: Utilitas format IDR
- [ ] TASK-FRONTEND-11: Unit test Pinia stores
- [ ] TASK-FRONTEND-12: `npm run build` zero error

### PHASE 8 — Deployment & QA

- [ ] TASK-DEPLOY-01: Docker services metering + billing
- [ ] TASK-DEPLOY-02: Dockerfile.metering dan Dockerfile.billing
- [ ] TASK-DEPLOY-03: `docker-compose.dev.yml`
- [ ] TASK-DEPLOY-04: E2E test full pipeline flow
- [ ] TASK-DEPLOY-05: Backward compat test lulus
- [ ] TASK-DEPLOY-06: `API_CONTRACT.md` diperbarui
- [ ] TASK-DEPLOY-07: `PROVIDER_DEVELOPMENT_GUIDE.md` dibuat
- [ ] TASK-DEPLOY-08: `DEPLOYMENT_GUIDE.md` diperbarui
- [ ] TASK-DEPLOY-09: Tag `v2.0.0-alpha`

---

## 8. Catatan Krusial & Decision Register

| Kode | Keputusan | Tanggal | Alasan |
|---|---|---|---|
| D-001 | Single entry point: `api/main.py` adalah satu-satunya FastAPI app | 19-Okt-2026 | Eliminasi konflik routing dari multiple entry points |
| D-002 | Provider wajib implement `BaseProvider` | 19-Okt-2026 | Memungkinkan hot-swap tanpa mengubah stage module |
| D-003 | Profil immutable setelah dikompilasi (SHA-256 rev) | 19-Okt-2026 | Reproducibility dan audit trail |
| D-004 | Metering TIDAK BOLEH memblokir pipeline seismik | 19-Okt-2026 | Keselamatan operasional — gempa harus tetap terdeteksi meski metering gagal |
| D-005 | Semua tarif IDR dari `rates.yaml` saja, tidak ada hardcode | 19-Okt-2026 | Perubahan tarif tidak perlu deploy ulang |
| D-006 | Versioning REST API `/api/v2/*`; endpoint lama tetap hidup | 19-Okt-2026 | Backward compatibility selama transisi |
| D-007 | Credential tidak masuk git — hanya `.env.example` | 19-Okt-2026 | Keamanan dasar |
| D-008 | MongoDB sebagai primary store; Redis hanya cache & state | 19-Okt-2026 | Konsistensi dengan infrastruktur existing |
| D-009 | Ownership dari JWT server context, bukan client payload | 19-Okt-2026 | Keamanan server-side authorization |
| D-010 | Seeder dan setiap script init harus idempotent | 19-Okt-2026 | Dapat dijalankan berulang di staging/prod |
| D-011 | Hot-reload model via Kafka `config_events`, bukan restart kontainer | 19-Okt-2026 | Zero downtime pipeline configuration |
| D-012 | PPN 11% selalu ditambahkan ke total tagihan bulanan | 19-Okt-2026 | Kewajiban perpajakan Indonesia |

---

## 9. Catatan Teknis & Bug Register

> Gunakan bagian ini untuk mencatat temuan teknis, bug, dan blocker selama development.

### 9.1 Format Entri

```
### [YYYY-MM-DD] Judul Singkat
**Phase:** Px
**Task:** TASK-XXX-YY
**Status:** 🔴 Open | 🟡 In Progress | ✅ Resolved
**Deskripsi:** ...
**Root Cause:** ...
**Solusi/Workaround:** ...
**Referensi:** ...
```

### 9.2 Catatan Awal

*(Diisi selama proses development berlangsung)*

---

## 10. Struktur Direktori Target

Berikut adalah struktur direktori lengkap setelah semua phase selesai:

```
d:\Projects\GEMPA\ai-gempa-bmkg\
├── development/                          ← Dokumen desain & planning
│   ├── HERMES_PROMPT_AI_GEMPA.md         ← Prompt utama Hermes
│   ├── DEVELOPMENT_PLANNING_AI_GEMPA.md  ← Dokumen ini
│   ├── ARCHITECTURE.md                   ← Desain arsitektur DDD
│   ├── ARCHITECTURE_PAY_PER_USE.md       ← Desain pricing & billing
│   ├── implementation_guide.md           ← Panduan implementasi
│   ├── API_CONTRACT.md                   ← Kontrak endpoint (dibuat P8)
│   ├── PROVIDER_DEVELOPMENT_GUIDE.md     ← Panduan tambah provider (dibuat P8)
│   └── DEPLOYMENT_GUIDE.md              ← Panduan deployment (update P8)
│
├── sispro-tews/                          ← SCOPE UTAMA HERMES
│   ├── core/                             ← Entitas domain murni
│   │   ├── __init__.py
│   │   ├── profile.py                    ← Pipeline, CompiledPipeline
│   │   ├── pricing.py                    ← PriceEstimate, Invoice
│   │   ├── events.py                     ← UsageEvent, ConfigActivatedEvent
│   │   └── artifacts.py                  ← Waveform, Pick, Cluster
│   │
│   ├── services/                         ← Business logic
│   │   ├── __init__.py
│   │   ├── profile_service.py
│   │   ├── pricing_service.py
│   │   ├── catalog_service.py
│   │   └── metering_service.py
│   │
│   ├── infrastructure/                   ← Adapters eksternal
│   │   ├── repositories/
│   │   │   ├── profile_repository.py
│   │   │   ├── usage_repository.py
│   │   │   └── invoice_repository.py
│   │   ├── kafka/
│   │   │   ├── producers.py              ← EventProducer
│   │   │   └── consumers.py             ← Base consumer
│   │   └── cache/
│   │       └── redis_client.py
│   │
│   ├── api/                              ← HTTP layer
│   │   ├── main.py                       ← SINGLE ENTRY POINT
│   │   ├── dependencies.py              ← FastAPI DI
│   │   ├── routes/
│   │   │   ├── profiles_routes.py
│   │   │   ├── models_routes.py
│   │   │   ├── pricing_routes.py
│   │   │   └── billing_routes.py
│   │   └── schemas/
│   │       ├── profile_schema.py
│   │       ├── catalog_schema.py
│   │       └── pricing_schema.py
│   │
│   ├── providers/                        ← AI model adapters
│   │   ├── base.py                       ← BaseProvider (ABC)
│   │   ├── registry.py                   ← ProviderRegistry
│   │   ├── p_pick/
│   │   │   ├── sta_lta.py
│   │   │   ├── phasenet.py
│   │   │   └── eqtransformer.py
│   │   ├── association/
│   │   │   ├── dbscan_simple.py
│   │   │   ├── gamma.py
│   │   │   └── pyocto.py
│   │   └── locmag/
│   │       ├── geiger.py
│   │       └── nonlinloc.py
│   │
│   ├── workers/                          ← Background jobs
│   │   └── profile_orchestrator.py       ← Kafka config_events consumer
│   │
│   ├── catalog_module/
│   │   ├── __init__.py
│   │   ├── provider_catalog.py           ← YAML loader
│   │   └── data/
│   │       ├── manifest.yaml             ← Provider registry
│   │       └── rates.yaml                ← IDR pricing table
│   │
│   ├── metering_module/
│   │   ├── __init__.py
│   │   ├── consumer.py                   ← Kafka metering_events consumer
│   │   └── aggregator.py                 ← Windowing + MongoDB flush
│   │
│   ├── billing_module/
│   │   ├── __init__.py
│   │   ├── invoice_generator.py          ← Cron hari ke-1 tiap bulan
│   │   ├── payment_handler.py            ← Webhook gateway pembayaran
│   │   └── email_sender.py
│   │
│   ├── database/
│   │   └── migrations/
│   │       ├── 002_usage_daily_index.js
│   │       └── 003_invoices_collection.js
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── core/
│   │   │   ├── services/
│   │   │   ├── providers/
│   │   │   ├── catalog/
│   │   │   ├── metering/
│   │   │   └── billing/
│   │   ├── integration/
│   │   │   └── api/
│   │   └── e2e/
│   │
│   └── .env.example                      ← Template environment variables
│
├── tews-ui-vue/                          ← SCOPE FRONTEND HERMES
│   └── src/
│       ├── stores/
│       │   ├── catalogStore.ts
│       │   ├── profileStore.ts
│       │   └── pricingStore.ts
│       ├── services/
│       │   ├── catalogApi.ts
│       │   ├── profileApi.ts
│       │   ├── pricingApi.ts
│       │   └── billingApi.ts
│       ├── composables/
│       │   ├── useDebounce.ts
│       │   └── useFormatCurrency.ts
│       ├── components/
│       │   ├── wizard/
│       │   │   ├── PipelineWizard.vue
│       │   │   ├── StageSelector.vue
│       │   │   ├── ModelCard.vue
│       │   │   └── ReviewPanel.vue
│       │   └── pricing/
│       │       └── PriceCalculator.vue
│       └── views/
│           ├── PipelineBuilder.vue
│           └── Billing.vue
│
└── AI-TEWS/                              ← SCOPE TERBATAS — HANYA INTEGRASI
    └── AI_modules_simple_ai/
        ├── p-pick_module/                ← Integrasi ProviderRegistry P4
        ├── assoc_module/                 ← Integrasi ProviderRegistry P4
        └── locmag_module/               ← Integrasi ProviderRegistry P4
```

---

## 11. Referensi Arsitektur

| Dokumen | Deskripsi | Path |
|---|---|---|
| `ARCHITECTURE.md` | Desain domain lengkap: DDD layers, Provider abstraction, data flow, testing strategy | `development/ARCHITECTURE.md` |
| `ARCHITECTURE_PAY_PER_USE.md` | Spesifikasi pricing IDR: rates, quotas, metering, billing, direktori target | `development/ARCHITECTURE_PAY_PER_USE.md` |
| `implementation_guide.md` | Panduan implementasi teknis: API endpoints, Kafka topics, MongoDB schemas | `development/implementation_guide.md` |
| `HERMES_PROMPT_AI_GEMPA.md` | Prompt operasional Hermes: identitas, scope, git workflow, phase checklist | `development/HERMES_PROMPT_AI_GEMPA.md` |
| `LAPORAN_RENCANA_PENGEMBANGAN_ARSITEKTUR_AI_GEMPA.md` | Laporan eksekutif untuk atasan | `development/LAPORAN_RENCANA_PENGEMBANGAN_ARSITEKTUR_AI_GEMPA.md` |
| `DIAGRAM_SEQUENCE_ARSITEKTUR_BARU.md` | PlantUML sequence diagrams untuk arsitektur baru | `development/DIAGRAM_SEQUENCE_ARSITEKTUR_BARU.md` |

---

**Document Version:** 1.0
**Dibuat oleh:** Antigravity AI (assisted by Hermes Agent)
**Terakhir Diperbarui:** 19 Oktober 2026
**Status:** 🟡 Active — Diperbarui setiap phase selesai
