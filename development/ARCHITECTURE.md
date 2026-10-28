# Architecture Design: AI-GEMPA Business Config System

Dokumen ini merancang ulang struktur project untuk mendukung **UI-driven pipeline configuration + pay-per-use pricing**.

---

## 1. Current State Analysis

### 1.1 Existing Structure

```
ai-gempa-bmkg/
├── sispro-tews/
│   ├── controller_module/           # Main API server (FastAPI)
│   │   ├── app.py, app1.py, ...    # Multiple entry points (MESSY)
│   │   ├── routes/                  # API endpoints
│   │   ├── services/                # Business logic (user, station, etc)
│   │   └── configuration/           # DB config
│   ├── seedlink_module/             # SeedLink consumer
│   ├── api_incoming_module/         # External API integration
│   ├── archiving_module/            # Data archiving
│   ├── fdsn_module/                 # FDSN server
│   └── docker-compose.yml
├── tews-ui-vue/                     # Frontend (Vue)
├── AI-TEWS/                         # Separate AI module directory (?)
└── development/                     # Design docs
```

### 1.2 Pain Points

| Issue | Impact | Root Cause |
|-------|--------|-----------|
| Multiple `app.py` files | Confusion, duplicate code | No clear entry point |
| Services dir flat | Hard to scale new services | No domain organization |
| Config hardcoded | Can't switch models at runtime | No config abstraction layer |
| No pricing system | Can't bill per usage | Architecture not designed for it |
| Metering missing | Can't track usage | No event emission |
| Profile/revision tracking missing | Can't activate/deactivate pipelines | No versioning system |
| Frontend tightly coupled to backend | Hard to support multiple configs | Backend controls all decisions |
| AI modules separate | Hard to integrate multiple providers | No provider abstraction |

---

## 2. Target Architecture

### 2.1 Design Principles

1. **Domain-Driven Design**: Services organized by business capability, not layer
2. **Provider Abstraction**: AI models pluggable, not hardcoded
3. **Event-Driven**: All state changes emit events (Kafka)
4. **Configuration as Code**: Profile = immutable, versioned specification
5. **Clear Contracts**: API-first design, strong schemas
6. **Testability**: Each module independently testable
7. **Observability**: Usage tracking, metrics, audit trail

### 2.2 New Structure

```
ai-gempa-bmkg/
├── sispro-tews/
│   ├── core/                        # [NEW] Core domain models
│   │   ├── __init__.py
│   │   ├── profile.py               # Pipeline profile (from pipeline_profile.py)
│   │   ├── pricing.py               # Pricing models (from pricing_model.py)
│   │   ├── artifacts.py             # Data flowing through pipeline
│   │   └── events.py                # Domain events
│   │
│   ├── services/                    # [NEW] Domain services layer
│   │   ├── __init__.py
│   │   ├── profile_service.py       # Profile CRUD + validation + compilation
│   │   ├── pricing_service.py       # Pricing calculations + invoicing
│   │   ├── metering_service.py      # Usage tracking + aggregation
│   │   ├── catalog_service.py       # Model catalog + provider registry
│   │   ├── user_service.py          # [MOVED from controller]
│   │   ├── station_service.py       # [MOVED from controller]
│   │   ├── event_service.py         # [MOVED from controller]
│   │   └── ...                      # Other domain services
│   │
│   ├── infrastructure/              # [NEW] Adapters & infrastructure
│   │   ├── __init__.py
│   │   ├── repositories/
│   │   │   ├── profile_repository.py
│   │   │   ├── user_repository.py
│   │   │   ├── invoice_repository.py
│   │   │   └── usage_repository.py
│   │   ├── kafka/
│   │   │   ├── producers.py         # Event emitters
│   │   │   ├── consumers.py         # Event listeners
│   │   │   └── topics.py            # Topic definitions
│   │   ├── cache/
│   │   │   └── redis_client.py      # Redis caching
│   │   └── storage/
│   │       └── mongodb_client.py    # MongoDB connections
│   │
│   ├── api/                         # [NEW] Clean API layer
│   │   ├── __init__.py
│   │   ├── main.py                  # [NEW] Single entry point (MAIN APP)
│   │   ├── routes/
│   │   │   ├── profiles.py          # GET/POST /profiles/*
│   │   │   ├── pricing.py           # POST /pricing/estimate, etc
│   │   │   ├── models.py            # GET /models, /models/{id}
│   │   │   ├── users.py             # [MOVED]
│   │   │   ├── stations.py          # [MOVED]
│   │   │   ├── events.py            # [MOVED]
│   │   │   └── ...
│   │   ├── schemas/                 # Pydantic models
│   │   │   ├── profile_schema.py
│   │   │   ├── pricing_schema.py
│   │   │   ├── user_schema.py
│   │   │   └── ...
│   │   └── dependencies.py          # FastAPI dependency injection
│   │
│   ├── providers/                   # [NEW] AI model providers
│   │   ├── __init__.py
│   │   ├── base.py                  # Base provider interface
│   │   ├── p_pick/
│   │   │   ├── __init__.py
│   │   │   ├── sta_lta.py           # CPU-based provider
│   │   │   ├── phasenet.py          # GPU provider
│   │   │   └── eqtransformer.py     # Premium provider
│   │   ├── association/
│   │   │   ├── dbscan_simple.py
│   │   │   ├── gamma.py
│   │   │   └── pyocto.py
│   │   ├── locmag/
│   │   │   ├── geiger.py
│   │   │   └── nonlinloc.py
│   │   └── registry.py              # Provider factory + registry
│   │
│   ├── workers/                     # [NEW] Background workers/consumers
│   │   ├── __init__.py
│   │   ├── metering_aggregator.py   # Kafka consumer: aggregate usage
│   │   ├── billing_generator.py     # Cron: generate invoices
│   │   ├── profile_orchestrator.py  # Kafka consumer: apply configs
│   │   └── ...
│   │
│   ├── controller_module/           # [LEGACY] To be refactored
│   │   ├── routes/
│   │   ├── services/
│   │   └── ...
│   │
│   ├── seedlink_module/
│   │   ├── seedlink_consumer.py
│   │   └── ...
│   │
│   └── docker-compose.yml
│
├── tews-ui-vue/                     # Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── PipelineWizard/      # [NEW] 4-step config wizard
│   │   │   ├── PriceCalculator/     # [NEW] Real-time pricing sidebar
│   │   │   ├── ModelSelector/       # [NEW] Model selection grid
│   │   │   └── ...
│   │   ├── pages/
│   │   │   ├── ProfileBuilder.vue   # [NEW] Main config page
│   │   │   ├── Dashboard.vue
│   │   │   └── ...
│   │   ├── api/
│   │   │   ├── profileApi.js        # [NEW] Profile API client
│   │   │   ├── pricingApi.js        # [NEW] Pricing API client
│   │   │   ├── modelsApi.js         # [NEW] Models catalog API
│   │   │   └── ...
│   │   ├── stores/
│   │   │   ├── profile.js           # [NEW] Profile state (Pinia)
│   │   │   ├── pricing.js           # [NEW] Pricing state
│   │   │   └── ...
│   │   └── ...
│   └── ...
│
└── development/
    ├── ARCHITECTURE.md              # [THIS FILE]
    ├── pipeline_profile.py          # Core domain model
    ├── pricing_model.py             # Pricing domain model
    ├── implementation_guide.md      # Implementation details
    └── ...
```

---

## 3. Module Responsibilities

### 3.1 Core Layer (`core/`)

**Purpose**: Domain models, agnostic dari infrastructure.

```python
# core/profile.py
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class Pipeline:
    """Immutable pipeline specification (versioned)."""
    id: str
    workspace_id: str
    mode: str                          # "default" | "custom"
    stages: Dict[str, StageConfig]     # {stage_id: config}
    sinks: Dict[str, SinkConfig]       # {sink_id: config}
    rev: str                           # revision hash (deterministic)
    created_at: str
    activated_at: str = None
    status: str = "draft"              # draft | validating | active | archived

@dataclass
class StageConfig:
    provider_id: str                   # "phasenet", "sta_lta", etc
    enabled: bool = True
    params: Dict = field(default_factory=dict)
    profile_rev: str = None            # To track which config version

@dataclass
class UsageEvent:
    """Emitted by stage modules for metering."""
    workspace_id: str
    stage: str
    provider_id: str
    units: int                         # count of inferences
    timestamp: str
    profile_rev: str
```

### 3.2 Services Layer (`services/`)

**Purpose**: Business logic, orchestration, use cases.

```python
# services/profile_service.py
class ProfileService:
    """Manage pipeline profiles (CRUD, validate, compile, activate)."""
    
    def __init__(self, profile_repo, catalog_svc, pricing_svc, kafka_producer):
        self.profile_repo = profile_repo
        self.catalog_svc = catalog_svc
        self.pricing_svc = pricing_svc
        self.kafka_producer = kafka_producer
    
    def create_draft(self, workspace_id, mode, stages, sinks) -> Pipeline:
        """Create profile draft (not activated yet)."""
        pipeline = Pipeline(id=..., status="draft", ...)
        self.profile_repo.save(pipeline)
        return pipeline
    
    def validate(self, pipeline_id) -> ValidationResult:
        """Validate profile before activation."""
        # Check: all providers exist, params valid, sinks have sources, etc
        pass
    
    def compile(self, pipeline_id, workspace_id) -> CompiledPipeline:
        """Compile profile to executable plan (topics, consumer groups, etc)."""
        # Generate: topics, consumer_groups, runtime params filled in
        # Deterministic: same input always = same rev
        pass
    
    def activate(self, pipeline_id) -> str:
        """Activate profile → emit config_events to Kafka."""
        # Emit to Kafka config_events topic
        # Stage runtime will pick up and apply
        pass

# services/pricing_service.py
class PricingService:
    """Calculate pricing from profiles and usage."""
    
    def estimate_from_profile(self, profile: Pipeline, volume_estimate) -> PriceEstimate:
        """Live pricing estimate from UI selection."""
        pass
    
    def calculate_invoice(self, workspace_id, month, usage_records) -> Invoice:
        """Generate invoice from actual usage."""
        pass

# services/metering_service.py
class MeteringService:
    """Aggregate usage events for billing."""
    
    def process_usage_event(self, event: UsageEvent):
        """Process individual usage event (called by consumer)."""
        pass
    
    def aggregate_daily(self, workspace_id, date) -> UsageDaily:
        """Aggregate all events for a day."""
        pass

# services/catalog_service.py
class CatalogService:
    """Model catalog + provider registry."""
    
    def list_providers(self, stage: str) -> List[ProviderInfo]:
        """Get available providers for a stage."""
        pass
    
    def get_provider_info(self, provider_id: str) -> ProviderInfo:
        """Get provider details (pricing, status, metrics, etc)."""
        pass
```

### 3.3 Infrastructure Layer (`infrastructure/`)

**Purpose**: Adapters, external integrations.

```python
# infrastructure/repositories/profile_repository.py
class ProfileRepository:
    """MongoDB adapter for profiles."""
    
    async def save(self, pipeline: Pipeline):
        """Save profile (insert or upsert)."""
        pass
    
    async def find_by_id(self, profile_id: str) -> Pipeline:
        pass

# infrastructure/kafka/producers.py
class EventProducer:
    """Kafka event publisher."""
    
    async def emit_profile_activated(self, pipeline: Pipeline):
        """Emit to config_events topic."""
        pass
    
    async def emit_usage_event(self, event: UsageEvent):
        """Emit to metering_events topic."""
        pass

# infrastructure/kafka/consumers.py
class MeteringConsumer:
    """Kafka consumer for metering_events."""
    
    async def run(self):
        """Main loop: consume events, call MeteringService."""
        async for event in self.consumer:
            await self.metering_svc.process_usage_event(event)
```

### 3.4 API Layer (`api/`)

**Purpose**: HTTP routes, request/response serialization.

```python
# api/main.py - SINGLE ENTRY POINT
from fastapi import FastAPI
from .routes import profiles, pricing, models, users, stations

app = FastAPI(title="AI-GEMPA Controller")

# Include routers
app.include_router(profiles.router)
app.include_router(pricing.router)
app.include_router(models.router)
app.include_router(users.router)
app.include_router(stations.router)

# Dependency injection setup
@app.on_event("startup")
async def startup():
    # Initialize services, connect to DBs, start background tasks
    pass

# api/routes/profiles.py
from fastapi import APIRouter, HTTPException
from ..services.profile_service import ProfileService
from ..schemas.profile_schema import ProfileCreateRequest

router = APIRouter(prefix="/api/v2/profiles", tags=["profiles"])

@router.post("")
async def create_profile(req: ProfileCreateRequest, svc: ProfileService = Depends(get_profile_service)):
    """POST /api/v2/profiles - Create profile draft."""
    pipeline = await svc.create_draft(...)
    return pipeline.dict()

@router.get("/{profile_id}")
async def get_profile(profile_id: str, svc: ProfileService = Depends()):
    """GET /api/v2/profiles/{id}."""
    pass

@router.post("/{profile_id}/validate")
async def validate_profile(profile_id: str, svc: ProfileService = Depends()):
    """POST /api/v2/profiles/{id}/validate."""
    result = await svc.validate(profile_id)
    return result.dict()

@router.post("/{profile_id}/activate")
async def activate_profile(profile_id: str, svc: ProfileService = Depends()):
    """POST /api/v2/profiles/{id}/activate."""
    rev = await svc.activate(profile_id)
    return {"rev": rev, "status": "activating"}

# api/routes/pricing.py
from fastapi import APIRouter
from ..schemas.pricing_schema import PricingEstimateRequest

router = APIRouter(prefix="/api/v2/pricing", tags=["pricing"])

@router.post("/estimate")
async def estimate_pricing(req: PricingEstimateRequest, svc: PricingService = Depends()):
    """POST /api/v2/pricing/estimate - Real-time price calculation."""
    estimate = await svc.estimate_from_profile(req.profile_dict, req.volume)
    return estimate.dict()
```

### 3.5 Providers Layer (`providers/`)

**Purpose**: Pluggable AI model implementations.

```python
# providers/base.py
from abc import ABC, abstractmethod

class BaseProvider(ABC):
    """Base class for all AI model providers."""
    
    provider_id: str
    stage: str
    version: str
    tier: str  # CPU | GPU_BASIC | GPU_PREMIUM | EXPERIMENTAL
    
    @abstractmethod
    async def predict(self, input_data) -> output_data:
        """Run inference."""
        pass
    
    @abstractmethod
    def get_info(self) -> ProviderInfo:
        """Get provider metadata (pricing, status, metrics)."""
        pass

# providers/p_pick/phasenet.py
class PhaseNetProvider(BaseProvider):
    provider_id = "phasenet"
    stage = "p_pick"
    tier = "GPU_BASIC"
    
    async def predict(self, waveform) -> Pick:
        # Load model from /app/models/phasenet.pt
        # Run inference
        # Emit usage event
        pass
    
    def get_info(self):
        return ProviderInfo(
            provider_id="phasenet",
            name="PhaseNet",
            tier="GPU_BASIC",
            pricing={
                "unit_price": 500,  # IDR per 1K
                "unit_name": "per 1K picks",
                "free_quota": 5000
            },
            metrics={"precision": "94%", "latency": "180ms"}
        )

# providers/registry.py
class ProviderRegistry:
    """Factory + registry for all providers."""
    
    _providers = {}
    
    @classmethod
    def register(cls, provider_class):
        cls._providers[provider_class.provider_id] = provider_class
    
    @classmethod
    def get_provider(cls, provider_id: str) -> BaseProvider:
        if provider_id not in cls._providers:
            raise ProviderNotFound(provider_id)
        return cls._providers[provider_id]()
    
    @classmethod
    def list_by_stage(cls, stage: str) -> List[BaseProvider]:
        return [p() for p in cls._providers.values() if p.stage == stage]

# Auto-register all providers
from . import p_pick, association, locmag
ProviderRegistry.register(p_pick.PhaseNetProvider)
ProviderRegistry.register(p_pick.STALTAProvider)
# ... etc
```

### 3.6 Workers Layer (`workers/`)

**Purpose**: Background jobs, async processing.

```python
# workers/metering_aggregator.py
class MeteringAggregatorWorker:
    """Consume metering_events from Kafka, aggregate to daily usage."""
    
    async def run(self):
        consumer = KafkaConsumer('metering_events', ...)
        async for message in consumer:
            event = UsageEvent.from_json(message)
            await self.metering_svc.process_usage_event(event)

# workers/billing_generator.py
class BillingGeneratorWorker:
    """Cron job: generate invoices on day 1 of month."""
    
    @scheduled(cron="0 0 1 * *")  # 1st of each month
    async def generate_invoices(self):
        workspaces = await self.workspace_repo.find_all()
        for ws in workspaces:
            invoice = await self.pricing_svc.calculate_invoice(ws.id, current_month)
            await self.invoice_repo.save(invoice)
            # Send email, etc

# workers/profile_orchestrator.py
class ProfileOrchestratorWorker:
    """Consume config_events, verify stages applied, handle rollback."""
    
    async def run(self):
        consumer = KafkaConsumer('config_events', ...)
        async for message in consumer:
            config = CompiledPipeline.from_json(message)
            # Check: did stage apply this config?
            # If failed: rollback to last-known-good
```

---

## 4. Data Flow Diagrams

### 4.1 Profile Activation Flow

```
User (UI)
  ↓
POST /profiles (draft)
  ↓
ProfileService.create_draft()
  ↓
Saved to MongoDB profiles collection
  ↓
User selects models, clicks Activate
  ↓
POST /profiles/{id}/activate
  ↓
ProfileService.validate()
  ↓
ProfileService.compile()
  ↓
Emit config_events to Kafka
  ↓
ProfileOrchestratorWorker consumes
  ↓
Apply config to stage modules (via API or env vars)
  ↓
Stage module reports applied(rev)
  ↓
Profile status = "active"
```

### 4.2 Pricing Estimate Flow

```
User in UI selects stages/models
  ↓
Debounce 500ms
  ↓
POST /pricing/estimate
  {
    selected_models: {p_pick: phasenet, assoc: dbscan},
    volume: {picks: 500/day, events: 10/day}
  }
  ↓
PricingService.estimate_from_profile()
  ↓
Lookup unit rates from CatalogService
  ↓
Calculate: (units - free_quota) × price_per_unit
  ↓
Calculate tax (PPN 11%)
  ↓
Return estimate
  ↓
PriceCalculator.vue updates sidebar
```

### 4.3 Metering & Billing Flow

```
Runtime (every inference)
  ↓
Stage module calls:
  usage_event = UsageEvent(
    workspace_id, stage, provider_id, units, timestamp, profile_rev
  )
  EventProducer.emit_usage_event(usage_event)
  ↓
Emit to Kafka metering_events
  ↓
MeteringAggregatorWorker consumes
  ↓
MeteringService.process_usage_event()
  ↓
Upsert to MongoDB usage_daily
  ↓
[End of month]
  ↓
BillingGeneratorWorker.generate_invoices() (cron)
  ↓
PricingService.calculate_invoice()
  Query usage_daily for month
  Calculate per-provider usage
  Apply free quotas
  Calculate total + tax
  ↓
Save Invoice to MongoDB
  ↓
Send email to user
```

---

## 5. Configuration & Dependency Injection

### 5.1 Dependency Injection (FastAPI)

```python
# api/dependencies.py
from fastapi import Depends
from ..services import ProfileService, PricingService, MeteringService

# Initialize singletons on app startup
_profile_service = None
_pricing_service = None
_metering_service = None

async def get_profile_service() -> ProfileService:
    """FastAPI dependency for ProfileService."""
    return _profile_service

async def get_pricing_service() -> PricingService:
    return _pricing_service

async def get_metering_service() -> MeteringService:
    return _metering_service

# api/main.py
app = FastAPI()

@app.on_event("startup")
async def startup():
    global _profile_service, _pricing_service, _metering_service
    
    # Initialize infrastructure
    profile_repo = ProfileRepository(mongodb_client)
    usage_repo = UsageRepository(mongodb_client)
    event_producer = EventProducer(kafka_client)
    
    # Initialize services
    _profile_service = ProfileService(profile_repo, ...)
    _pricing_service = PricingService(usage_repo, ...)
    _metering_service = MeteringService(usage_repo, ...)
    
    # Start background workers
    asyncio.create_task(MeteringAggregatorWorker(...).run())
    asyncio.create_task(BillingGeneratorWorker(...).run())
```

### 5.2 Environment Configuration

```bash
# .env
WORKSPACE_ID=default
PROFILE_REV=current
MONGODB_URL=mongodb://mongodb:27017/sispro-tews
KAFKA_BROKERS=kafka:9092
REDIS_URL=redis://redis:6379/0

# Pricing configuration
PRICING_CONFIG_FILE=/app/config/pricing_rules.json
STORAGE_RATE_IDR=50  # IDR per GB per day
TAX_RATE=0.11        # PPN 11%
```

---

## 6. Migration Plan (Phased)

### Phase 1: Setup New Structure (1 minggu)

- [x] Create `core/`, `services/`, `infrastructure/`, `api/`, `providers/`, `workers/` directories
- [ ] Move `pipeline_profile.py` → `core/profile.py`
- [ ] Move `pricing_model.py` → `core/pricing.py`
- [ ] Create `api/main.py` as single entry point
- [ ] Setup dependency injection
- [ ] Write tests for core models

### Phase 2: Implement Profiles API (1-2 minggu)

- [ ] Create `services/profile_service.py` with CRUD + validate + compile + activate
- [ ] Create `infrastructure/repositories/profile_repository.py`
- [ ] Create `api/routes/profiles.py`
- [ ] Create `api/schemas/profile_schema.py`
- [ ] Implement validation logic
- [ ] Implement compilation (deterministic rev)
- [ ] Write integration tests

### Phase 3: Implement Pricing API (1 minggu)

- [ ] Create `services/pricing_service.py`
- [ ] Create `services/catalog_service.py`
- [ ] Create `api/routes/pricing.py`
- [ ] Create `api/routes/models.py`
- [ ] Integrate with `core/pricing.py`
- [ ] Write tests

### Phase 4: Implement Metering Infrastructure (1-2 minggu)

- [ ] Create `infrastructure/kafka/producers.py` + consumers.py
- [ ] Create `services/metering_service.py`
- [ ] Create `workers/metering_aggregator.py`
- [ ] Create MongoDB schemas for `usage_daily`, `invoices`
- [ ] Write consumer tests

### Phase 5: Implement Provider Abstraction (2 minggu)

- [ ] Create `providers/base.py`
- [ ] Create `providers/registry.py`
- [ ] Implement providers: PhaseNet, STA/LTA, DBSCAN, GaMMA, Geiger, NonLinLoc
- [ ] Update stage modules to use ProviderRegistry
- [ ] Write tests for provider loading

### Phase 6: Refactor Existing Modules (2 minggu)

- [ ] Move `controller_module/services/*.py` → `services/`
- [ ] Move `controller_module/routes/*.py` → `api/routes/`
- [ ] Consolidate multiple entry points → single `api/main.py`
- [ ] Update imports across all modules
- [ ] Smoke tests on all existing endpoints

### Phase 7: Frontend Integration (2-3 minggu)

- [ ] Create Vue components: PipelineWizard, PriceCalculator, ModelSelector
- [ ] Implement profile API client
- [ ] Implement pricing API client
- [ ] Implement state management (Pinia)
- [ ] E2E testing

### Phase 8: Deployment & Monitoring (1 minggu)

- [ ] Add Prometheus metrics
- [ ] Add Grafana dashboards
- [ ] Add logging/tracing
- [ ] Document deployment process
- [ ] Runbook for common issues

**Total: ~10-12 minggu** untuk full implementation

---

## 7. Key Architectural Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Domain-Driven Design** | Clear separation of concerns, scalable | Learning curve for new team members |
| **Provider Abstraction** | Easy to add/remove models | Some overhead for simple models |
| **Event-Driven** | Decoupled modules, good audit trail | Complexity in eventual consistency |
| **Single Entry Point** | Clear API contract | Need to refactor existing routes |
| **Immutable Pipelines (versioned)** | Deterministic, reproducible | Can't modify active pipeline in-place |
| **Pay-per-use in Core** | Billing first-class concern | Needs metering infrastructure |
| **Workspace Isolation** | Multi-tenant ready | Some complexity in queries |
| **Kafka for Events** | Durable, replayed, audit trail | Additional infrastructure |

---

## 8. Testing Strategy

### 8.1 Unit Tests (per module)

```python
# tests/unit/services/test_profile_service.py
@pytest.mark.asyncio
async def test_create_profile_draft():
    repo = MockProfileRepository()
    svc = ProfileService(repo, ...)
    
    pipeline = await svc.create_draft("default", "custom", {...})
    
    assert pipeline.status == "draft"
    assert repo.save.called

@pytest.mark.asyncio
async def test_compile_deterministic():
    svc = ProfileService(...)
    
    rev1 = svc.compile(pipeline1).rev
    rev2 = svc.compile(pipeline1).rev
    
    assert rev1 == rev2  # Same input = same output

# tests/unit/providers/test_phasenet_provider.py
@pytest.mark.asyncio
async def test_phasenet_predict():
    provider = PhaseNetProvider()
    waveform = load_test_waveform()
    
    pick = await provider.predict(waveform)
    
    assert pick.phase in ["P", "S"]
    assert 0 <= pick.probability <= 1
```

### 8.2 Integration Tests (API)

```python
# tests/integration/api/test_profiles_api.py
@pytest.mark.asyncio
async def test_create_and_activate_profile(client):
    # Create draft
    resp = await client.post("/api/v2/profiles", json={...})
    profile_id = resp.json()["id"]
    
    # Validate
    resp = await client.post(f"/api/v2/profiles/{profile_id}/validate")
    assert resp.json()["valid"] == True
    
    # Activate
    resp = await client.post(f"/api/v2/profiles/{profile_id}/activate")
    assert resp.json()["status"] == "activating"

@pytest.mark.asyncio
async def test_pricing_estimate(client):
    resp = await client.post("/api/v2/pricing/estimate", json={
        "selected_models": {"p_pick": "phasenet"},
        "volume": {"picks": 10000}
    })
    
    assert "monthly_total" in resp.json()
    assert "currency" == "IDR"
```

### 8.3 Load Tests (Locust)

```python
# tests/load/locustfile.py
from locust import HttpUser, task

class PricingUser(HttpUser):
    @task
    def estimate_pricing(self):
        self.client.post("/api/v2/pricing/estimate", json={...})
```

---

## 9. Deployment Architecture

### 9.1 Docker Services

```yaml
# docker-compose.yml
version: '3.8'

services:
  controller:
    build: sispro-tews/api
    ports:
      - "4002:8000"
    environment:
      - PYTHONUNBUFFERED=1
      - WORKSPACE_ID=default
    depends_on:
      - mongodb
      - kafka
      - redis
    volumes:
      - ./sispro-tews:/app

  metering_aggregator:
    build: sispro-tews/workers
    command: python -m workers.metering_aggregator
    depends_on:
      - kafka
      - mongodb
    environment:
      - PYTHONUNBUFFERED=1

  billing_generator:
    build: sispro-tews/workers
    command: python -m workers.billing_generator
    depends_on:
      - mongodb
    environment:
      - PYTHONUNBUFFERED=1

  # ... kafka, mongodb, redis, seedlink, etc
```

### 9.2 Monitoring Stack

```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  volumes:
    - grafana-storage:/var/lib/grafana
```

---

## 10. Monitoring & Observability

### Metrics

```python
# infrastructure/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Profile metrics
profiles_created = Counter('profiles_created_total', 'Total profiles created', ['workspace_id'])
profiles_activated = Counter('profiles_activated_total', 'Total profiles activated', ['workspace_id'])

# Pricing metrics
pricing_estimates = Counter('pricing_estimates_total', 'Total pricing estimates', ['selected_models_count'])
pricing_estimate_duration = Histogram('pricing_estimate_duration_seconds', 'Pricing estimate latency')

# Metering metrics
usage_events_processed = Counter('usage_events_processed_total', 'Usage events processed', ['stage', 'provider'])
usage_events_buffer_size = Gauge('usage_events_buffer_size', 'Pending events in buffer')

# Billing metrics
invoices_generated = Counter('invoices_generated_total', 'Invoices generated', ['workspace_id'])
invoice_total_amount_idr = Histogram('invoice_total_amount_idr', 'Invoice amounts', ['workspace_id'])
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Profile activated", extra={
    "profile_id": "...",
    "workspace_id": "...",
    "stages": ["p_pick", "association"],
    "rev": "..."
})

logger.warning("Usage exceeded quota", extra={
    "workspace_id": "...",
    "stage": "p_pick",
    "units": 50000,
    "free_quota": 5000,
    "overage": 45000
})
```

---

## 11. Security Considerations

- **Authentication**: JWT tokens, workspace isolation
- **Authorization**: Role-based access control (admin, user)
- **Validation**: All inputs validated (Pydantic schemas)
- **Rate Limiting**: Per-workspace API throttling
- **Data Privacy**: PII redaction in logs
- **Audit Trail**: All profile changes logged + versioned

---

## 12. Documentation Requirements

- [ ] API documentation (Swagger/OpenAPI)
- [ ] Provider development guide (how to add new model)
- [ ] Deployment runbook
- [ ] Troubleshooting guide
- [ ] Architecture Decision Records (ADRs)
- [ ] Module-level docstrings

---

## 13. Next Steps

1. **Review with team** — Get alignment on architecture
2. **Create issue for Phase 1** — Start setup
3. **Create decision log** — Track ADRs
4. **Schedule architecture review** — Weekly sync
5. **Plan resource allocation** — Assign phases to team members

---

**Document Version:** 1.0  
**Last Updated:** 2026-10-10  
**Author:** AI-GEMPA Architecture Team  
**Status:** Draft (Ready for Review)
