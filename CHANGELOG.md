# Changelog

All notable changes to AI-GEMPA BMKG project.

## [2.0.0-alpha] - 2026-10-19

### Added — Pay-Per-Use Architecture

#### PHASE 0 — Foundation ✅
- 8 decision registers (DR-FOUNDATION-001 to 008)
- FastAPI v2 base structure with `/api/v2` prefix
- MongoDB collections: `profiles`, `catalog`, `usage_events`, `invoices`
- Redis integration for caching and metering buffer
- Kafka setup for async metering events
- Git workflow: feature branch `feature/architecture-refactor`
- Repository: https://github.com/mohamadsolkhannawawi/ai-gempa-bmkg

#### PHASE 1 — Catalog Service ✅
- Provider registry: 8 providers (STALTA, PhaseNet, EQTransformer, DBSCAN, GaMMA, PyOcto, Geiger, NonLinLoc)
- Model tier pricing (CPU/GPU) in IDR
- `GET /api/v2/catalog` — list providers
- `GET /api/v2/catalog/model-tiers` — pricing table
- Unit tests: `tests/unit/test_catalog.py`

#### PHASE 2 — Profile Service ✅
- Compute profile CRUD
- Dynamic pipeline compilation
- Cost estimation per profile
- Endpoints:
  - `POST /api/v2/profiles` — create profile
  - `GET /api/v2/profiles` — list profiles
  - `PUT /api/v2/profiles/{id}` — update profile
  - `DELETE /api/v2/profiles/{id}` — delete profile
  - `POST /api/v2/profiles/{id}/compile` — compile pipeline
  - `POST /api/v2/profiles/{id}/estimate-cost` — cost estimate
  - `GET /api/v2/profiles/{id}/compute-specs` — recommended specs
- Unit + integration tests

#### PHASE 3 — Pricing Service ✅
- Usage tracking per workspace/profile
- Invoice generation with 11% PPN
- Usage statement aggregation
- Endpoints:
  - `GET /api/v2/pricing/invoices` — list invoices
  - `GET /api/v2/pricing/invoices/{id}` — invoice detail
  - `GET /api/v2/pricing/invoices/{id}/pdf` — download PDF
  - `GET /api/v2/pricing/usage-statement` — usage report
- ReportLab PDF generation
- Unit tests: `tests/unit/test_pricing.py`

#### PHASE 4 — Provider Abstraction ✅
- Unified provider interface: `BaseProvider`
- 8 provider implementations:
  - **p_pick**: STALTA (CPU 5 IDR), PhaseNet (CPU 10/GPU 15), EQTransformer (GPU 20)
  - **association**: DBSCAN (CPU 20), GaMMA (CPU 25/GPU 30)
  - **locmag**: PyOcto (CPU 100), Geiger (CPU 80), NonLinLoc (CPU 120)
- Async execution via `asyncio`
- Error handling and retry logic
- Provider factory pattern
- Unit tests: 14 test files

#### PHASE 5 — Metering Module ✅
- Kafka consumer for metering events (topic: `gempa.metering.events`)
- Redis buffer aggregation (5-minute window)
- MongoDB persistence: `usage_events` collection
- Async worker: `metering_module/worker.py`
- Real-time usage tracking per workspace/profile/provider
- Integration tests: `tests/integration/test_metering.py`

#### PHASE 6 — Billing Module ✅
- Monthly invoice generation (1st of each month)
- 11% PPN calculation
- Invoice status: DRAFT → ISSUED → PAID/OVERDUE
- Email notification via SMTP
- Payment webhook: `POST /billing/webhooks/payment-confirmation`
- Cron worker: `billing_module/cron.py`
- Integration tests: `tests/integration/test_billing_cron.py`

#### PHASE 7 — Frontend ✅
- Vue 3 + TypeScript + Vite + Pinia + Vue Router
- Pinia stores: catalog, profile, pricing
- API service clients with Axios
- Components:
  - `PipelineWizard.vue` (426 lines) — 4-step wizard (p_pick → association → locmag → review)
  - `PriceCalculator.vue` (168 lines) — live cost estimator
  - `PipelineBuilder.vue` (427 lines) — profile CRUD page
  - `Billing.vue` (559 lines) — invoice dashboard
- Composables: `useDebounce`
- Utils: `formatIDR`, `formatDate`
- Tailwind CSS + responsive design
- Unit tests: 12 test cases (Vitest)
- Dev server: http://localhost:5173

#### PHASE 8 — Deployment & QA ✅
- Dockerfile.metering — metering worker image
- Dockerfile.billing — billing worker image
- docker-compose.dev.yml — full stack (API, MongoDB, Redis, Kafka, frontend, workers)
- E2E test: `tests/e2e/test_full_pipeline.py` (profile → metering → billing → invoice)
- API documentation: `docs/API_DOCUMENTATION_v2.md`
- Deployment guide: `README_DEPLOYMENT.md`
- Changelog: `CHANGELOG.md`
- Migration guide: `MIGRATION_GUIDE_v1_to_v2.md`
- Git tag: `v2.0.0-alpha`

### Changed
- API prefix: `/api/v1` → `/api/v2`
- Architecture: Monolith → Microservices (API + metering worker + billing worker)
- Pricing model: Fixed → Pay-per-use (IDR per inference)
- Database: Added `profiles`, `usage_events`, `invoices` collections
- Frontend: New Vue 3 app (replaced old UI)

### Deprecated
- `/api/v1/*` endpoints (to be removed in v3.0)

### Fixed
- N/A (new architecture)

### Security
- Input validation on all API endpoints
- MongoDB injection prevention via parameterized queries
- CORS configured for frontend origin
- Environment secrets via `.env` (SMTP, MongoDB credentials)

---

## [1.0.0] - 2025-XX-XX (Legacy)

### Features
- SeedLink data ingestion
- Real-time WebSocket streaming
- Fixed-price seismic processing

### Status
- **DEPRECATED**: Legacy architecture
- **Migration path**: See `MIGRATION_GUIDE_v1_to_v2.md`
- **Support ends**: 2026-12-31

---

## Version Scheme

- **Major.Minor.Patch** (SemVer)
- **Alpha/Beta/RC** suffixes for pre-release
- Examples:
  - `2.0.0-alpha` — Initial pay-per-use release (current)
  - `2.0.0-beta` — Feature-complete, stabilization
  - `2.0.0-rc1` — Release candidate
  - `2.0.0` — Production-ready
  - `2.1.0` — Minor feature additions
  - `2.0.1` — Patch/bugfix

---

## Contributing

See [development/HERMES_PROMPT_AI_GEMPA.md](development/HERMES_PROMPT_AI_GEMPA.md) for implementation phases.
