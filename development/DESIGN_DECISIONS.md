# DESIGN DECISIONS — AI-GEMPA BMKG

**Timestamp:** 2026-10-19  
**Phase:** 0 — FOUNDATION  
**Rev:** v0.1

---

## 1. EXISTING ARCHITECTURE PATTERNS (Sebelum Refactor)

### 1.1 Current Structure
```
sispro-tews/
├── api_incoming_module/       # REST API untuk data masuk
├── controller_module/          # WebSocket + Kafka consumer
├── seedlink_module/           # SeedLink ingest
├── archiving_module/          # Archive ke MongoDB
├── fdsn_module/               # FDSN protocol
├── flush_module/              # Flush cache
├── record_stream_module/      # Stream management
├── billing_module/            # (kosong, baru dibuat)
├── metering_module/           # (kosong, baru dibuat)
└── catalog_module/            # (kosong, baru dibuat)
```

### 1.2 Anti-Patterns Detected
1. **Kafka Consumer di App Layer** (controller_module/app.py:14-20)
   - KafkaConsumer instantiated langsung di FastAPI app
   - Tight coupling, sulit test, sulit ganti message broker
   
2. **Code Duplication** 
   - `archiving_app.py`, `archiving_app_2.py` ... `archiving_app_7.py`
   - `archiving_app copy 2.py` ... `archiving_app copy 7.py`
   - 14 file hampir identik untuk 1 fungsi

3. **Fat Service, Anemic Domain**
   - Service layer hanya transform data (auto_gempa_service.py)
   - No business logic encapsulation
   - No domain validation

4. **Missing Abstractions**
   - No repository interface (concrete implementation only)
   - No Kafka abstraction layer
   - Hard-coded connection strings

---

## 2. TARGET DOMAIN BOUNDARIES (Setelah Refactor)

### 2.1 Core Domains (Pure Business Logic)

#### A. Pipeline Profile Domain
**Bounded Context:** Konfigurasi pipeline seismik end-to-end  
**Entities:**
- `Profile` — mode (default/custom), stages, sinks, external_inputs
- `StageCfg` — enabled, provider, params
- `Catalog` — available providers per stage
- `Provider` — id, version, status, params, resources

**Business Rules:**
- Default mode = preset sistem, tidak boleh ada override
- Custom mode = butuh paket Pro/Enterprise
- Stage dependency harus terpenuhi (p_pick butuh waveform)
- Sink minimal 1 aktif
- Artifact yang tidak dipakai = warning (boros resource)

**File:** `core/profile.py` (✅ done)

#### B. Pricing Domain
**Bounded Context:** Pay-per-use billing dalam IDR  
**Entities:**
- `UnitRate` — harga per unit processing (per 1K picks/events)
- `UsageRecord` — track usage per workspace per hari
- `PriceBreakdown` — invoice breakdown (stages, sinks, storage, tax)

**Business Rules:**
- Free quota per model (STA/LTA 10K picks, PhaseNet 5K picks)
- Storage: IDR 50/GB/hari
- PPN 11% untuk semua transaksi
- Pay-per-use, BUKAN subscription

**File:** `core/pricing.py` (✅ done)

#### C. Event Detection Domain
**Bounded Context:** Earthquake event lifecycle  
**Entities:**
- `Waveform` — raw seismic signal (3-channel: BH*, HH*, SH*)
- `Pick` — P-wave/S-wave arrival time + confidence
- `Cluster` — grouped picks (spatial + temporal proximity)
- `Arrival` — refined pick post-association
- `Event` — located earthquake (lat, lon, depth, magnitude)

**Stages:**
1. **ingest** (source) → produce `waveform`
2. **p_pick** (transform) → consume `waveform`, produce `pick`
3. **association** (transform) → consume `pick`, produce `cluster` + `arrival`
4. **locmag** (transform) → consume `cluster` + `arrival`, produce `event`

**Providers:**
- ingest: `seedlink_v3`, `fdsn_poll`, `push_api`, `file_replay`
- p_pick: `phasenet` (GPU), `sta_lta` (CPU), `eqtransformer` (GPU)
- association: `dbscan_simple` (CPU), `gamma` (GPU), `pyocto` (GPU)
- locmag: `geiger` (CPU), `nonlinloc` (GPU)

**File:** `core/event.py` (TODO — TASK-FOUNDATION-04)

### 2.2 Application Services (Orchestration)

#### A. Profile Service
**Responsibility:** Validate, compile, deploy pipeline profile  
**Operations:**
- `validate_profile(profile, catalog, plan) -> List[Issue]`
- `compile_pipeline(profile, catalog, workspace) -> Dict[topics, stages, sinks, rev]`
- `deploy_profile(workspace_id, compiled) -> bool`
- `rollback_profile(workspace_id, prev_rev) -> bool`

**File:** `services/profile_service.py` (TODO — TASK-FOUNDATION-05)

#### B. Metering Service
**Responsibility:** Track usage real-time, aggregate per workspace  
**Operations:**
- `record_stage_usage(workspace, stage, provider, units)`
- `record_sink_usage(workspace, sink, messages)`
- `get_daily_usage(workspace, date) -> UsageRecord`
- `get_monthly_usage(workspace, month) -> List[UsageRecord]`

**File:** `services/metering_service.py` (TODO — TASK-FOUNDATION-06)

#### C. Billing Service
**Responsibility:** Generate invoice dari usage records  
**Operations:**
- `estimate_cost(profile, estimated_volume) -> PriceBreakdown`
- `generate_invoice(workspace, month) -> Invoice`
- `apply_discount(workspace, discount_pct)`
- `export_invoice(invoice_id, format="pdf") -> bytes`

**File:** `services/billing_service.py` (TODO — TASK-FOUNDATION-07)

### 2.3 Infrastructure Layer

#### A. Kafka Abstraction
**Problem:** KafkaConsumer hard-coded di app layer (controller_module/app.py:14)  
**Solution:** Repository pattern untuk message broker

```python
# infrastructure/kafka/consumer.py
class KafkaConsumerRepository:
    def subscribe(self, topics: List[str], group_id: str)
    def poll(self, timeout_ms: int) -> List[Message]
    def commit()
    def close()

# infrastructure/kafka/producer.py
class KafkaProducerRepository:
    def send(self, topic: str, message: dict)
    def flush()
    def close()
```

**Benefit:**
- Testable (mock Kafka di unit test)
- Swappable (Redis Streams, RabbitMQ, etc.)
- Config injection (no hard-coded `bootstrap_servers`)

**File:** `infrastructure/kafka/` (TODO — TASK-FOUNDATION-08)

#### B. MongoDB Repository
**Current:** Concrete repo langsung query MongoDB  
**Target:** Interface + implementation separation

```python
# infrastructure/repositories/event_repo.py
class EventRepository(ABC):
    @abstractmethod
    def save_event(self, event: Event) -> str
    
    @abstractmethod
    def get_latest_event(self) -> Optional[Event]

class MongoEventRepository(EventRepository):
    # implementation dengan pymongo
```

**File:** `infrastructure/repositories/` (TODO — TASK-FOUNDATION-08)

---

## 3. ARCHITECTURAL DECISIONS REGISTER

### ADR-001: Domain-Driven Design (DDD) Architecture
**Status:** ✅ ACCEPTED  
**Context:** Existing codebase sulit scale, tight coupling, duplicate code  
**Decision:** Refactor ke DDD dengan 3 layers (core → services → infrastructure)  
**Consequences:**
- (+) Clear separation of concerns
- (+) Testable tanpa external dependencies
- (+) Easier to add new providers/stages
- (-) Initial refactor cost tinggi (8 phases)
- (-) Learning curve untuk team

### ADR-002: Pay-Per-Use Pricing (IDR)
**Status:** ✅ ACCEPTED  
**Context:** User ingin transparansi biaya, hanya bayar yang dipakai  
**Decision:** Pricing model per-unit (per 1K picks/events), BUKAN subscription  
**Consequences:**
- (+) Fair billing (no idle cost)
- (+) Easy cost prediction (UI estimator)
- (+) Free quota untuk trial
- (-) Butuh real-time metering system
- (-) Invoice generation lebih kompleks

### ADR-003: Pipeline Profile as Code
**Status:** ✅ ACCEPTED  
**Context:** Manual config via database table prone to error  
**Decision:** Profile JSON dengan validation + compile step (immutable rev hash)  
**Consequences:**
- (+) Version control untuk config (GitOps ready)
- (+) Validation sebelum deploy (catch error early)
- (+) Rollback mudah (revert ke rev sebelumnya)
- (-) Config tidak bisa edit langsung di DB (harus via API)

### ADR-004: Strangler Pattern untuk Migration
**Status:** ✅ ACCEPTED  
**Context:** Sistem production tidak boleh down, gradual migration  
**Decision:** New domain code coexist dengan legacy, strangler pattern  
**Consequences:**
- (+) Zero downtime migration
- (+) Rollback mudah (toggle routing)
- (+) Low risk
- (-) Dual write/read complexity (transition period)
- (-) Legacy code cleanup butuh disiplin

### ADR-005: Kafka Topic Naming Convention
**Status:** ✅ ACCEPTED  
**Context:** Legacy topics tidak konsisten (`waveform_seedlink`, `pick_topic`)  
**Decision:** New workspace pakai `{workspace}.{artifact}` (e.g., `acme.waveform`)  
**Consequences:**
- (+) Namespace isolation per workspace
- (+) Clear topic purpose
- (-) Legacy topics masih ada (perlu mapping)
- (-) Cross-workspace subscription sulit (by design)

### ADR-006: GPU Model Pricing Tier
**Status:** ✅ ACCEPTED  
**Context:** Model GPU cost 10-30x lebih mahal dari CPU  
**Decision:** 3-tier pricing: CPU (Rp50/1K), GPU_BASIC (Rp500/1K), GPU_PREMIUM (Rp1500/1K)  
**Consequences:**
- (+) User aware cost sebelum pilih model
- (+) Encourage CPU model usage (cost optimization)
- (-) GPU model under-utilized jika harga terlalu tinggi
- (-) Perlu benchmark actual GPU cost

### ADR-007: Free Quota untuk Trial
**Status:** ✅ ACCEPTED  
**Context:** User butuh trial sebelum commit  
**Decision:** Free quota per model (STA/LTA 10K, PhaseNet 5K picks/bulan)  
**Consequences:**
- (+) Lower barrier to entry
- (+) User bisa test accuracy sebelum bayar
- (-) Abuse risk (perlu rate limiting)
- (-) Quota tracking overhead

### ADR-008: Default vs Custom Mode
**Status:** ✅ ACCEPTED  
**Context:** Basic plan user tidak boleh ubah config (support overhead)  
**Decision:** 2 mode — default (preset fixed), custom (paket Pro/Enterprise)  
**Consequences:**
- (+) Simplify support untuk Basic user
- (+) Upsell opportunity (custom = premium feature)
- (-) Basic user tidak flexible
- (-) Perlu preset yang "cukup baik" untuk 80% use case

---

## 4. DOMAIN UBIQUITOUS LANGUAGE

| Term | Definition | Example |
|------|-----------|---------|
| **Workspace** | Isolated environment per user/org, punya profile + usage sendiri | `workspace="bmkg_prod"` |
| **Profile** | Konfigurasi pipeline: mode, stages, providers, params | `profile.mode="custom"` |
| **Stage** | Tahap processing: ingest, p_pick, association, locmag | `stage="p_pick"` |
| **Provider** | Implementasi algoritma untuk 1 stage | `provider="phasenet"` |
| **Artifact** | Data yang mengalir antar stage | `artifact="waveform"` |
| **Sink** | Tujuan output: ws_ui, webhook, archive | `sink="ws_ui"` |
| **Rev** | Hash immutable dari compiled profile (12 char SHA256) | `rev="3a7f92d1c8b4"` |
| **Unit** | Satuan billing: per 1K picks, per 1K events | `unit="per 1K picks"` |
| **Quota** | Usage gratis per bulan untuk trial | `free_quota=10000` |
| **Issue** | Error/warning dari validation | `Issue(code="V003", severity="error")` |
| **Tier** | Pricing tier: CPU, GPU_BASIC, GPU_PREMIUM | `tier="GPU_BASIC"` |

---

## 5. DATA FLOW DIAGRAM (Target Architecture)

```
[SeedLink Server] ──┐
[FDSN Server]     ──┼─→ [Ingest Provider] ─→ Kafka(waveform) ─→ [P-Pick Provider] ─→ Kafka(pick)
[Push API]        ──┘                                                     ↓
                                                                  [Metering Service]
                                                                     (track usage)
                                                                          ↓
Kafka(pick) ─→ [Association Provider] ─→ Kafka(cluster,arrival) ─→ [LocMag Provider] ─→ Kafka(event)
                                ↓                                            ↓
                        [Metering Service]                           [Metering Service]
                                                                              ↓
Kafka(event) ─┬─→ [WebSocket Sink] ────→ Frontend UI
              ├─→ [Webhook Sink]    ────→ External System
              ├─→ [Archive Sink]    ────→ MongoDB
              └─→ [Kafka Export]    ────→ External Kafka

[Metering Service] ─→ Redis(usage_records) ─→ [Billing Service] ─→ MongoDB(invoices)
                                                      ↓
                                              [Invoice API] ─→ Frontend
```

---

## 6. MIGRATION STRATEGY (Strangler Pattern)

### Phase 0 (FOUNDATION) — ✅ Current
1. Buat struktur DDD baru (`core/`, `services/`, `infrastructure/`)
2. Implement core domain (`profile.py`, `pricing.py`)
3. No routing change, no production impact

### Phase 1 (DOMAIN LAYER)
1. Implement `core/event.py` (Waveform, Pick, Cluster, Event)
2. Implement `core/workspace.py` (Workspace, User, Subscription)
3. Unit test 100% coverage (no external deps)

### Phase 2 (SERVICE LAYER)
1. Implement `services/profile_service.py`
2. Implement `services/metering_service.py`
3. Implement `services/billing_service.py`
4. Integration test dengan mock infrastructure

### Phase 3 (INFRASTRUCTURE LAYER)
1. Kafka abstraction (`infrastructure/kafka/`)
2. Repository interfaces (`infrastructure/repositories/`)
3. MongoDB + Redis implementation

### Phase 4 (API v2)
1. New FastAPI router (`api/routes/v2/`)
2. Profile CRUD endpoints
3. Metering + billing endpoints
4. Legacy API tetap jalan (strangler coexist)

### Phase 5 (WORKER REFACTOR)
1. Refactor provider workers pakai domain layer
2. Kafka consumer/producer pakai infrastructure abstraction
3. Deploy alongside legacy workers (parallel run)

### Phase 6 (ROUTING SWITCH)
1. Traffic 10% → API v2 (canary)
2. Monitor error rate, latency, billing accuracy
3. Traffic 100% → API v2 jika metrics OK
4. Legacy API deprecated (read-only)

### Phase 7 (CLEANUP)
1. Delete legacy code (old modules)
2. Delete duplicate files (archiving_app copy 2-7)
3. Consolidate Docker images

### Phase 8 (FINALIZATION)
1. Documentation update
2. Team training
3. Production handoff

---

## 7. NEXT STEPS (PHASE 0 Remaining Tasks)

- [ ] TASK-FOUNDATION-04: Implement `core/event.py` (Event Detection Domain)
- [ ] TASK-FOUNDATION-05: Implement `core/workspace.py` (Workspace Domain)
- [ ] TASK-FOUNDATION-06: Write unit tests untuk `core/profile.py`
- [ ] TASK-FOUNDATION-07: Write unit tests untuk `core/pricing.py`
- [ ] TASK-FOUNDATION-08: Document API contracts (OpenAPI schema)

---

**Sign-off:**  
Agent: Kiro (Hermes Agent v0.11.0)  
Date: 2026-10-19  
Branch: feature/architecture-refactor  
Commit: 3a409d3
