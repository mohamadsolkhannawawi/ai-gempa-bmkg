# Architecture: Project Structure untuk Pay-Per-Use Pricing System

Perubahan struktur project untuk menampung **UI-driven config + pay-per-use pricing (IDR) + metering & billing**.

---

## 1. Struktur Folder Target

```
sispro-tews/
├── api_incoming_module/              (existing: waveform ingestion)
├── archiving_module/                 (existing: data archiving)
├── controller_module/                (existing: main API + WebSocket)
│   ├── routes/
│   │   ├── profiles_routes.py        (NEW: /api/v2/profiles CRUD)
│   │   └── pricing_routes.py         (NEW: /api/v2/pricing/estimate)
│   ├── services/
│   │   ├── pricing_service.py        (NEW: calculate + invoice)
│   │   └── profile_service.py        (NEW: draft/activate/validate profiles)
│   ├── repositories/
│   │   ├── profile_repo.py           (NEW: MongoDB profiles collection)
│   │   └── usage_repo.py             (NEW: MongoDB usage_daily collection)
│   └── models/
│       ├── profile_schema.py         (NEW: Pydantic schema)
│       └── pricing_schema.py         (NEW: Pydantic schema)
├── fdsn_module/                      (existing: FDSN/SeedLink)
├── metering_module/                  (NEW: usage tracking + aggregation)
│   ├── __init__.py
│   ├── consumer.py                   (consume Kafka metering_events)
│   ├── aggregator.py                 (aggregate per workspace/stage/day)
│   ├── models.py
│   ├── repositories/
│   │   └── usage_repo.py
│   └── config.py
├── billing_module/                   (NEW: invoice generation + payment)
│   ├── __init__.py
│   ├── invoice_generator.py          (cron: monthly invoice)
│   ├── payment_handler.py            (webhook: Stripe/Xendit callback)
│   ├── models.py
│   ├── repositories/
│   │   └── invoice_repo.py
│   ├── services/
│   │   └── billing_service.py
│   └── config.py
├── catalog_module/                   (NEW: catalog provider, model, rate)
│   ├── __init__.py
│   ├── provider_catalog.py           (load manifest.yaml)
│   ├── models.py
│   ├── data/
│   │   ├── manifest.yaml             (provider + model registry)
│   │   └── rates.yaml                (IDR pricing per model)
│   └── schemas.py                    (Pydantic)
├── websocket_module/                 (existing: live data streaming)
├── frontend/                         (Vue 3 SPA)
│   ├── src/
│   │   ├── components/
│   │   │   ├── PipelineWizard.vue    (NEW: 4-step config wizard)
│   │   │   ├── PriceCalculator.vue   (NEW: real-time pricing sidebar)
│   │   │   ├── ModelCard.vue         (NEW: model comparison)
│   │   │   ├── ProfileDashboard.vue  (NEW: active profiles)
│   │   │   └── BillingDashboard.vue  (NEW: invoices + usage)
│   │   ├── pages/
│   │   │   ├── PipelineBuilder.vue   (NEW: wizard page)
│   │   │   ├── Profiles.vue          (NEW: saved profiles list)
│   │   │   ├── Billing.vue           (NEW: invoices page)
│   │   │   └── Settings.vue
│   │   ├── services/
│   │   │   ├── profileService.ts     (NEW: API calls)
│   │   │   ├── pricingService.ts     (NEW: pricing calculator)
│   │   │   └── billingService.ts     (NEW: invoice/payment)
│   │   ├── stores/
│   │   │   ├── profileStore.ts       (NEW: Pinia store)
│   │   │   ├── pricingStore.ts       (NEW: Pinia store)
│   │   │   └── catalogStore.ts       (NEW: Pinia store)
│   │   └── router.ts
│   └── package.json
├── development/
│   ├── pricing_model.py              (existing: pricing calculations)
│   ├── pipeline_profile.py           (existing: pipeline domain)
│   ├── test_pipeline_profile.py      (existing: unit tests)
│   ├── Rancangan Konfigurasi Bisnis  (existing: business design)
│   └── implementation_guide.md       (existing: high-level guide)
├── database/
│   ├── migrations/
│   │   ├── 001_init_collections.js   (NEW: profiles, usage_daily, invoices)
│   │   └── 002_indexes.js            (NEW: indexes on workspace_id, date)
│   └── seed/
│       └── pricing_seed.json         (NEW: default rates)
├── docker/
│   ├── Dockerfile.metering           (NEW: metering service container)
│   ├── Dockerfile.billing            (NEW: billing service container)
│   └── Dockerfile.catalog            (NEW: catalog service container)
├── docker-compose.yml                (existing: main orchestration)
├── docker-compose.wrapper.yml        (existing: DinD wrapper)
├── docker-compose.dev.yml            (NEW: dev environment with all services)
└── .github/
    └── workflows/
        ├── test_pricing.yml          (NEW: pricing unit tests)
        └── deploy_pricing.yml        (NEW: staging/prod deployment)
```

---

## 2. Modul Baru Terperinci

### 2.1 Catalog Module
**Fungsi**: Serve daftar tahap, provider, model, dan pricing dari manifest.

```
catalog_module/
├── provider_catalog.py              # Load manifest.yaml → in-memory registry
├── models.py                        # ProviderInfo, ModelInfo dataclass
├── schemas.py                       # Pydantic ProviderSchema, ModelSchema
├── data/
│   ├── manifest.yaml                # Provider registry + model definition
│   └── rates.yaml                   # IDR pricing per model tier
└── __init__.py
```

**manifest.yaml struktur:**
```yaml
providers:
  waveform:
    - name: SeedLink
      status: stable
      models: [rtserve]
  p_pick:
    - name: STA/LTA
      status: stable
      price_per_unit: 50        # IDR per 1K picks
      free_quota_monthly: 10000  # 10K picks free
    - name: PhaseNet
      status: stable
      price_per_unit: 500        # IDR per 1K picks
      free_quota_monthly: 5000
    - name: EQTransformer
      status: beta
      price_per_unit: 1000       # IDR per 1K picks
      free_quota_monthly: 1000
  association:
    - name: DBSCAN Simple
      status: stable
      price_per_unit: 100        # IDR per 1K clusters
      free_quota_monthly: 5000
    - name: GaMMA
      status: beta
      price_per_unit: 500        # IDR per 1K clusters
      free_quota_monthly: 500
```

---

### 2.2 Metering Module
**Fungsi**: Track usage real-time dari setiap tahap.

```
metering_module/
├── consumer.py                      # Consume Kafka metering_events
├── aggregator.py                    # Aggregate per workspace/stage/day
├── models.py                        # UsageEvent, DailyUsage dataclass
├── repositories/
│   └── usage_repo.py                # MongoDB usage_daily collection
├── config.py                        # Kafka config, MongoDB config
└── __init__.py
```

**Data flow:**
```
Stage module emit Kafka metering_events:
  {
    workspace_id: "acme",
    stage: "p_pick",
    provider: "phasenet",
    timestamp: 1728554463,
    unit_count: 42,
    processing_time_ms: 1234
  }
  ↓
metering_consumer subscribe → deserialize
  ↓
aggregator window (10 min) → buffer events
  ↓
flush ke MongoDB usage_daily:
  {
    workspace_id: "acme",
    date: "2026-10-10",
    stage: "p_pick",
    provider: "phasenet",
    total_units: 424,
    event_count: 10,
    total_processing_ms: 12340
  }
```

---

### 2.3 Billing Module
**Fungsi**: Monthly invoice generation + payment processing.

```
billing_module/
├── invoice_generator.py             # Cron job: monthly billing
├── payment_handler.py               # Webhook: Stripe/Xendit callback
├── models.py                        # Invoice, Payment dataclass
├── repositories/
│   └── invoice_repo.py              # MongoDB invoices collection
├── services/
│   └── billing_service.py           # Calculate invoice amount (Rp)
├── config.py                        # Payment gateway config
└── __init__.py
```

**MongoDB invoices collection:**
```json
{
  "_id": ObjectId("..."),
  "workspace_id": "acme",
  "invoice_date": "2026-10-01",
  "period_start": "2026-10-01",
  "period_end": "2026-10-31",
  "breakdown": {
    "p_pick": {
      "provider": "phasenet",
      "units_free": 5000,
      "units_used": 12000,
      "units_charged": 7000,
      "price_per_unit": 500,
      "subtotal": 3500000
    },
    "association": {...}
  },
  "subtotal_idr": 4200000,
  "ppn_11_percent": 462000,
  "total_idr": 4662000,
  "status": "draft|sent|paid|overdue",
  "paid_at": "2026-10-05T14:30:00Z",
  "payment_method": "stripe|xendit",
  "payment_id": "pi_1234567890",
  "created_at": "2026-10-01T00:00:00Z"
}
```

---

### 2.4 Controller Module Updates
**Tambahan routes + services:**

**routes/profiles_routes.py:**
```python
# GET /api/v2/profiles                    # List all profiles (workspace)
# POST /api/v2/profiles                   # Create draft profile
# GET /api/v2/profiles/{id}               # Get profile detail
# PUT /api/v2/profiles/{id}               # Update draft
# DELETE /api/v2/profiles/{id}            # Delete draft
# POST /api/v2/profiles/{id}/activate     # Activate profile
# POST /api/v2/profiles/{id}/validate     # Validate + estimate cost
```

**routes/pricing_routes.py:**
```python
# POST /api/v2/pricing/estimate           # Estimate cost from profile draft
# GET /api/v2/pricing/rates               # Get all pricing rates
# GET /api/v2/pricing/usage/{workspace}   # Get current month usage
# GET /api/v2/pricing/invoices/{workspace} # Get invoices list
```

---

### 2.5 Frontend Updates
**New pages + components:**

- **pages/PipelineBuilder.vue** — 4-step wizard (Mode → Stages → Models → Review)
- **pages/Profiles.vue** — List active + draft profiles
- **pages/Billing.vue** — Invoice history + usage breakdown
- **components/PipelineWizard.vue** — Multi-step form component
- **components/PriceCalculator.vue** — Real-time pricing sidebar
- **components/ModelCard.vue** — Model comparison grid
- **stores/profileStore.ts** — Pinia state management
- **services/profileService.ts** — API client for profiles
- **services/pricingService.ts** — API client for pricing estimates

---

## 3. Database Schema (MongoDB)

### 3.1 profiles collection
```json
{
  "_id": ObjectId("..."),
  "workspace_id": "acme",
  "name": "Custom P-Pick Production",
  "mode": "custom",
  "stages": {
    "p_pick": {"provider": "phasenet"},
    "association": {"provider": "dbscan_simple"}
  },
  "config": {
    "p_pick": {
      "threshold": 0.5,
      "batch_size": 100
    }
  },
  "status": "draft|active|inactive",
  "activated_at": "2026-10-01T10:00:00Z",
  "created_at": "2026-09-30T15:00:00Z",
  "updated_at": "2026-10-01T10:00:00Z"
}
```

### 3.2 usage_daily collection
```json
{
  "_id": ObjectId("..."),
  "workspace_id": "acme",
  "date": "2026-10-10",
  "stage": "p_pick",
  "provider": "phasenet",
  "total_units": 5000,
  "event_count": 50,
  "created_at": "2026-10-10T23:59:59Z"
}
```

### 3.3 invoices collection
```json
{
  "_id": ObjectId("..."),
  "workspace_id": "acme",
  "invoice_number": "INV-20261001-0001",
  "period_start": "2026-10-01",
  "period_end": "2026-10-31",
  "breakdown": {
    "p_pick_phasenet": {
      "units_free": 5000,
      "units_charged": 7000,
      "price_per_unit": 500,
      "subtotal": 3500000
    }
  },
  "total_idr": 4662000,
  "status": "draft|sent|paid",
  "created_at": "2026-11-01T00:00:00Z"
}
```

---

## 4. API Endpoints Baru

| Endpoint | Method | Fungsi |
|---|---|---|
| `/api/v2/models` | GET | List model catalog |
| `/api/v2/profiles` | POST | Create draft profile |
| `/api/v2/profiles` | GET | List profiles |
| `/api/v2/profiles/{id}` | GET | Get profile detail |
| `/api/v2/profiles/{id}` | PUT | Update draft |
| `/api/v2/profiles/{id}/activate` | POST | Activate profile |
| `/api/v2/profiles/{id}/validate` | POST | Validate + estimate cost |
| `/api/v2/pricing/estimate` | POST | Estimate cost (before save) |
| `/api/v2/pricing/rates` | GET | Get pricing rates |
| `/api/v2/pricing/usage/{workspace}` | GET | Current month usage |
| `/api/v2/billing/invoices` | GET | List invoices |
| `/api/v2/billing/invoices/{id}` | GET | Invoice detail + PDF |

---

## 5. Docker Compose Additions

**docker-compose.yml** tambah services baru:

```yaml
metering:
  build:
    dockerfile: docker/Dockerfile.metering
  environment:
    KAFKA_BROKERS: kafka:9092
    MONGODB_URI: mongodb://mongo:27017
  depends_on:
    - kafka
    - mongo

billing:
  build:
    dockerfile: docker/Dockerfile.billing
  environment:
    MONGODB_URI: mongodb://mongo:27017
    STRIPE_API_KEY: ${STRIPE_API_KEY}
    XENDIT_API_KEY: ${XENDIT_API_KEY}
  depends_on:
    - mongo
  ports:
    - "8004:8000"   # Billing API + webhook endpoint
```

---

## 6. Configuration Files Baru

### 6.1 catalog_module/data/manifest.yaml
Daftar semua provider + model dengan pricing.

### 6.2 catalog_module/data/rates.yaml
IDR rates per model tier (admin dapat update tanpa deploy).

### 6.3 .env.seed
Env vars untuk API keys (Stripe, Xendit), PPN rate (11%), currency defaults.

---

## 7. Deployment Phases

| Phase | Durasi | Deliverables |
|---|---|---|
| **1. Catalog API + Profile Service** | 1 minggu | `/api/v2/models`, profile CRUD endpoints |
| **2. Pricing Calculator UI** | 1 minggu | PipelineWizard.vue, PriceCalculator.vue, real-time estimate |
| **3. Metering Infrastructure** | 1-2 minggu | usage_daily aggregation, Kafka consumer |
| **4. Billing Service** | 1 minggu | Monthly invoice generation, cron job |
| **5. Payment Gateway** | 1 minggu | Stripe/Xendit integration, webhook handling |

---

## 8. Key Design Decisions

### 8.1 Separation of Concerns
- **Catalog Module**: Static metadata (provider, model, pricing) → can scale separately
- **Metering Module**: Real-time usage tracking → separate consumer process
- **Billing Module**: Monthly calculations → separate cron job
- **Controller**: API orchestration → lean, focus on business logic

### 8.2 Pay-Per-Use Architecture
- **No subscription**: Each stage/model priced independently
- **Free quota**: Per model for trial, built into pricing rules
- **PPN 11%**: Auto-calculated, configurable per workspace
- **Flexible rates**: YAML-driven, admin can update without code deployment

### 8.3 Database Strategy
- **MongoDB**: Flexible schema for profile variants
- **Separate collections**: profiles, usage_daily, invoices (easy to scale/archive)
- **Time-series friendly**: usage_daily indexed on (workspace_id, date) for fast aggregation

### 8.4 Frontend State Management
- **Pinia stores**: profileStore, pricingStore, catalogStore (reactive, testable)
- **API-driven**: UI calls backend for pricing estimate (no hardcoded rates)
- **Real-time pricing**: Debounced requests (500ms) on every wizard change

---

## 9. Migration Path (dari existing code)

**Backward compatibility:**
- Old "default profile" → auto-migrated ke new profile system
- Existing Kafka topics `metering_events` → opt-in, non-breaking
- Payment gateway → optional (can disable via env var)

**Phased rollout:**
1. Deploy Catalog + Profile service (no breaking changes)
2. Deploy UI (users can see new pipeline builder, old UI still works)
3. Deploy Metering (silent usage tracking)
4. Enable Billing (users see pricing info)
5. Enable Payment (actual charges)

