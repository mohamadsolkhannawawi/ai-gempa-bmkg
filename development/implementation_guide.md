# Implementation Guide: Pay-Per-Use Pricing System (IDR)

Panduan implementasi lengkap untuk sistem konfigurasi bisnis AI-GEMPA dengan **pay-per-use pricing** (IDR, bukan langganan).

---

## 1. Arsitektur Lengkap

```
┌──────────────── FRONTEND (Vue) ────────────────┐
│  PipelineWizard.vue                            │
│  ├── StageSelector.vue                         │
│  ├── ModelSelector.vue (per stage)             │
│  ├── PriceCalculator.vue (sidebar real-time)   │
│  └── ReviewPanel.vue                           │
└────────────────────────────────────────────────┘
         ↓ POST /api/v2/pricing/estimate (debounce 500ms)
         ↓ POST /api/v2/profiles (save draft)
         ↓ POST /api/v2/profiles/{id}/validate
         ↓ POST /api/v2/profiles/{id}/activate
         ↓
┌──────────────── BACKEND (FastAPI) ─────────────┐
│  PricingService                                │
│  ├── estimate_from_profile()                   │
│  ├── calculate_invoice()                       │
│  └── get_model_catalog()                       │
│                                                │
│  ProfileService                                │
│  ├── validate_profile()                        │
│  ├── compile_pipeline()                        │
│  └── activate_profile()                        │
└────────────────────────────────────────────────┘
         ↓ emit config_events (Kafka)
         ↓
┌──────────────── DATA PLANE ────────────────────┐
│  Stage Modules (ingest, p_pick, assoc, locmag) │
│  ├── Consume from Kafka                        │
│  ├── Process with selected AI model            │
│  └── Emit usage_events (metering)              │
└────────────────────────────────────────────────┘
         ↓ Kafka metering_events
         ↓
┌──────────────── METERING PLANE ────────────────┐
│  MeteringAggregator                            │
│  ├── Consume metering_events                   │
│  ├── Aggregate per workspace per day           │
│  └── Write to MongoDB usage_daily              │
│                                                │
│  BillingService (cron monthly)                 │
│  ├── Query usage_daily for current month       │
│  ├── Calculate invoice with PricingCalculator  │
│  ├── Generate invoice PDF                      │
│  └── Send to user email                        │
└────────────────────────────────────────────────┘
```

---

## 2. API Endpoints (Backend FastAPI)

### 2.1 GET /api/v2/models - Model Catalog dengan Pricing

```python
# File: sispro-tews/controller_module/routes/models.py
from fastapi import APIRouter
from pricing_model import build_model_catalog

router = APIRouter()

@router.get("/api/v2/models")
async def get_model_catalog(stage: str = None):
    """
    Return model catalog dengan pricing info.
    
    Query params:
      - stage (optional): filter by stage (p_pick, association, locmag)
    
    Response:
    {
      "models": [
        {
          "provider_id": "phasenet",
          "stage": "p_pick",
          "name": "PhaseNet",
          "tier": "GPU_BASIC",
          "status": "stable",
          "pricing": {
            "unit_price": 500,
            "unit_name": "per 1K picks",
            "free_quota": 5000,
            "currency": "IDR",
            "example_monthly": "~Rp 247,500 untuk 500K picks/bulan"
          },
          "metrics": {
            "precision": "94%",
            "recall": "91%",
            "latency": "180ms"
          },
          "gpu_required": false,
          "description": "Neural network model, GPU optional, akurasi tinggi"
        },
        ...
      ]
    }
    """
    catalog = build_model_catalog()
    
    if stage:
        catalog = [m for m in catalog if m.stage == stage]
    
    return {
        "models": [m.to_dict() for m in catalog],
        "total": len(catalog)
    }
```

### 2.2 POST /api/v2/pricing/estimate - Real-Time Price Calculator

```python
# File: sispro-tews/controller_module/routes/pricing.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
from pricing_model import estimate_from_ui_selection

router = APIRouter()

class PricingEstimateRequest(BaseModel):
    workspace_id: str = "default"
    mode: str  # "default" | "custom"
    selected_models: Dict[str, str]  # {"p_pick": "phasenet", "association": "dbscan_simple"}
    estimated_daily_volume: Dict[str, int]  # {"waveforms": 10000, "picks": 500, "events": 10}

@router.post("/api/v2/pricing/estimate")
async def estimate_pricing(req: PricingEstimateRequest):
    """
    Real-time pricing estimate dari UI selection.
    
    Request body:
    {
      "workspace_id": "default",
      "mode": "custom",
      "selected_models": {
        "ingest": "seedlink_v3",
        "p_pick": "phasenet",
        "association": "dbscan_simple"
      },
      "estimated_daily_volume": {
        "waveforms": 10000,
        "picks": 500,
        "events": 10,
        "storage_gb": 50
      }
    }
    
    Response:
    {
      "breakdown": {
        "stages": {
          "ingest.seedlink_v3": 1500000,
          "p_pick.phasenet": 7425000,
          "association.dbscan_simple": 150000
        },
        "storage": 75000,
        "subtotal": 9150000,
        "tax": 1006500,
        "total": 10156500
      },
      "monthly_total": 10156500,
      "currency": "IDR",
      "period": "monthly",
      "free_quota_applied": true,
      "detail_rows": [
        {
          "stage": "p_pick",
          "provider": "phasenet",
          "unit_name": "per 1K picks",
          "monthly_units": 15000,
          "free_quota": 5000,
          "billable_units": 10000,
          "unit_price": 500,
          "cost": 5000000
        }
      ]
    }
    """
    try:
        result = estimate_from_ui_selection(
            req.selected_models,
            req.estimated_daily_volume
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 2.3 POST /api/v2/profiles - Save Profile Draft

```python
# File: sispro-tews/controller_module/routes/profiles.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List
from datetime import datetime

router = APIRouter()

class ProfileDraft(BaseModel):
    workspace_id: str
    mode: str
    name: str
    stages: Dict[str, Dict]
    sinks: Dict[str, Dict]
    external_inputs: List[str] = []

@router.post("/api/v2/profiles")
async def save_profile_draft(profile: ProfileDraft, db=Depends(get_db)):
    """
    Save profile draft (belum aktif).
    
    Response:
    {
      "id": "67890abcdef",
      "status": "draft",
      "created_at": "2026-10-10T00:00:00Z"
    }
    """
    profile_dict = profile.dict()
    profile_dict["status"] = "draft"
    profile_dict["created_at"] = datetime.utcnow()
    
    result = await db.profiles.insert_one(profile_dict)
    
    return {
        "id": str(result.inserted_id),
        "status": "draft",
        "created_at": profile_dict["created_at"].isoformat()
    }

@router.post("/api/v2/profiles/{profile_id}/validate")
async def validate_profile(profile_id: str, db=Depends(get_db)):
    """
    Validate profile sebelum activate.
    
    Response:
    {
      "valid": true,
      "issues": [],
      "warnings": [
        {"code": "W001", "message": "Stage 'association' menghasilkan 'cluster' tapi tidak ada sink yang memakainya"}
      ]
    }
    """
    from pipeline_profile import validate, Profile, build_default_catalog, PLANS
    
    profile_doc = await db.profiles.find_one({"_id": ObjectId(profile_id)})
    if not profile_doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = Profile.from_dict(profile_doc)
    catalog = build_default_catalog()
    plan = PLANS.get("basic")  # TODO: get from user subscription
    
    issues = validate(profile, catalog, plan)
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    
    return {
        "valid": len(errors) == 0,
        "issues": [{"code": i.code, "message": i.message, "severity": i.severity} for i in errors],
        "warnings": [{"code": i.code, "message": i.message} for i in warnings]
    }

@router.post("/api/v2/profiles/{profile_id}/activate")
async def activate_profile(profile_id: str, db=Depends(get_db)):
    """
    Activate profile → compile → emit config_events ke Kafka.
    
    Response:
    {
      "status": "activating",
      "rev": "a3b2c1d4",
      "expected_stages": ["ingest", "p_pick"],
      "message": "Profile activation in progress. Check /api/v2/profiles/{id}/status"
    }
    """
    from pipeline_profile import compile_pipeline, Profile, build_default_catalog, PLANS
    
    profile_doc = await db.profiles.find_one({"_id": ObjectId(profile_id)})
    if not profile_doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = Profile.from_dict(profile_doc)
    catalog = build_default_catalog()
    plan = PLANS.get("basic")
    
    # Compile
    compiled = compile_pipeline(profile, catalog, plan, workspace=profile_doc["workspace_id"])
    
    if not compiled["ok"]:
        raise HTTPException(status_code=400, detail={"errors": compiled["errors"]})
    
    # Save revision
    await db.profiles.update_one(
        {"_id": ObjectId(profile_id)},
        {"$set": {
            "status": "activating",
            "rev": compiled["rev"],
            "compiled": compiled,
            "activated_at": datetime.utcnow()
        }}
    )
    
    # Emit config_events to Kafka (orchestrator will pick up)
    await emit_config_events(compiled, kafka_producer)
    
    return {
        "status": "activating",
        "rev": compiled["rev"],
        "expected_stages": [s["stage"] for s in compiled["stages"]],
        "message": f"Profile activation in progress. Check /api/v2/profiles/{profile_id}/status"
    }
```

---

## 3. Frontend Components (Vue 3 + Composition API)

### 3.1 PipelineWizard.vue - Main Wizard

```vue
<template>
  <div class="pipeline-wizard">
    <!-- Step Navigation -->
    <div class="steps">
      <div v-for="(step, idx) in steps" :key="idx" 
           :class="['step', {active: currentStep === idx, completed: idx < currentStep}]">
        {{ step.title }}
      </div>
    </div>

    <!-- Main Content + Sidebar -->
    <div class="wizard-body">
      <div class="wizard-main">
        <!-- Step 1: Mode Selection -->
        <div v-if="currentStep === 0" class="step-content">
          <h2>Pilih Mode Pipeline</h2>
          <div class="mode-options">
            <label class="mode-card">
              <input type="radio" v-model="form.mode" value="default" />
              <div class="card-content">
                <h3>Default (Full Pipeline)</h3>
                <p>Semua tahap aktif: Ingest → P-Pick → Association → LocMag</p>
                <span class="badge">Recommended</span>
              </div>
            </label>
            <label class="mode-card">
              <input type="radio" v-model="form.mode" value="custom" />
              <div class="card-content">
                <h3>Custom (Pilih Tahapan)</h3>
                <p>Aktifkan hanya tahap yang Anda butuhkan</p>
              </div>
            </label>
          </div>
        </div>

        <!-- Step 2: Stage Selection (only if custom mode) -->
        <div v-if="currentStep === 1 && form.mode === 'custom'" class="step-content">
          <h2>Pilih Tahapan yang Aktif</h2>
          <div class="stage-list">
            <label v-for="stage in availableStages" :key="stage.id" class="stage-item">
              <input type="checkbox" v-model="form.selectedStages" :value="stage.id" />
              <div class="stage-info">
                <h4>{{ stage.name }}</h4>
                <p>{{ stage.description }}</p>
              </div>
            </label>
          </div>
        </div>

        <!-- Step 3: Model Selection per Stage -->
        <div v-if="currentStep === 2" class="step-content">
          <h2>Pilih Model AI per Tahap</h2>
          <div v-for="stage in activeStages" :key="stage" class="model-selection">
            <h3>{{ stageNames[stage] }}</h3>
            <div class="model-grid">
              <ModelCard 
                v-for="model in modelsByStage[stage]" 
                :key="model.provider_id"
                :model="model"
                :selected="form.selectedModels[stage] === model.provider_id"
                @select="selectModel(stage, model.provider_id)"
              />
            </div>
          </div>
        </div>

        <!-- Step 4: Review & Activate -->
        <div v-if="currentStep === 3" class="step-content">
          <h2>Review Konfigurasi</h2>
          <ReviewPanel :form="form" :pricing="pricingEstimate" />
          <div class="actions">
            <button @click="validateProfile" class="btn-secondary">Validate</button>
            <button @click="activateProfile" class="btn-primary" :disabled="!canActivate">
              Activate Pipeline
            </button>
          </div>
        </div>
      </div>

      <!-- Sidebar: Real-Time Pricing -->
      <PriceCalculator :form="form" @update="handlePricingUpdate" />
    </div>

    <!-- Navigation Buttons -->
    <div class="wizard-footer">
      <button @click="prevStep" :disabled="currentStep === 0">Previous</button>
      <button @click="nextStep" :disabled="!canProceed">Next</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { debounce } from 'lodash-es';
import ModelCard from './ModelCard.vue';
import PriceCalculator from './PriceCalculator.vue';
import ReviewPanel from './ReviewPanel.vue';
import { estimatePricing, getModelCatalog, validateProfile as apiValidate, activateProfile as apiActivate } from '@/api/pricing';

const currentStep = ref(0);
const form = ref({
  mode: 'default',
  selectedStages: ['ingest', 'p_pick', 'association', 'locmag'],
  selectedModels: {
    ingest: 'seedlink_v3',
    p_pick: 'phasenet',
    association: 'dbscan_simple',
    locmag: 'geiger'
  },
  estimatedVolume: {
    waveforms: 10000,
    picks: 500,
    events: 10,
    storage_gb: 50
  }
});

const pricingEstimate = ref(null);
const modelsByStage = ref({});
const canActivate = ref(false);

const steps = [
  { title: 'Mode' },
  { title: 'Tahapan' },
  { title: 'Model AI' },
  { title: 'Review' }
];

const availableStages = [
  { id: 'ingest', name: 'Ingest (SeedLink)', description: 'Ambil data waveform dari SeedLink server' },
  { id: 'p_pick', name: 'P-Pick', description: 'Deteksi P/S wave arrival dengan AI model' },
  { id: 'association', name: 'Association', description: 'Cluster picks menjadi earthquake candidates' },
  { id: 'locmag', name: 'LocMag', description: 'Hitung lokasi dan magnitude' }
];

const stageNames = {
  ingest: 'Ingest (SeedLink)',
  p_pick: 'P-Pick Detection',
  association: 'Event Association',
  locmag: 'Location & Magnitude'
};

const activeStages = computed(() => {
  return form.value.mode === 'default' 
    ? ['ingest', 'p_pick', 'association', 'locmag']
    : form.value.selectedStages;
});

const canProceed = computed(() => {
  if (currentStep.value === 1 && form.value.mode === 'custom') {
    return form.value.selectedStages.length > 0;
  }
  if (currentStep.value === 2) {
    return activeStages.value.every(stage => form.value.selectedModels[stage]);
  }
  return true;
});

// Load model catalog
onMounted(async () => {
  const { data } = await getModelCatalog();
  modelsByStage.value = data.models.reduce((acc, model) => {
    if (!acc[model.stage]) acc[model.stage] = [];
    acc[model.stage].push(model);
    return acc;
  }, {});
  
  // Initial pricing estimate
  updatePricingEstimate();
});

// Watch form changes and update pricing (debounced)
const updatePricingEstimate = debounce(async () => {
  try {
    const { data } = await estimatePricing({
      workspace_id: 'default',
      mode: form.value.mode,
      selected_models: form.value.selectedModels,
      estimated_daily_volume: form.value.estimatedVolume
    });
    pricingEstimate.value = data;
  } catch (err) {
    console.error('Pricing estimate failed:', err);
  }
}, 500);

watch(() => [form.value.mode, form.value.selectedStages, form.value.selectedModels], updatePricingEstimate, { deep: true });

function selectModel(stage, providerId) {
  form.value.selectedModels[stage] = providerId;
}

function nextStep() {
  if (currentStep.value < steps.length - 1) {
    currentStep.value++;
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
}

async function validateProfile() {
  // TODO: call API validate
  canActivate.value = true;
}

async function activateProfile() {
  // TODO: call API activate
  alert('Profile activated!');
}

function handlePricingUpdate(data) {
  pricingEstimate.value = data;
}
</script>

<style scoped>
.pipeline-wizard {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.steps {
  display: flex;
  justify-content: space-between;
  margin-bottom: 3rem;
}

.step {
  flex: 1;
  padding: 1rem;
  text-align: center;
  border-bottom: 3px solid #ddd;
  color: #999;
  font-weight: 500;
}

.step.active {
  border-color: #2563eb;
  color: #2563eb;
}

.step.completed {
  border-color: #10b981;
  color: #10b981;
}

.wizard-body {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 2rem;
}

.wizard-main {
  min-height: 500px;
}

.mode-options, .model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.mode-card {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-card:has(input:checked) {
  border-color: #2563eb;
  background: #eff6ff;
}

.mode-card input[type="radio"] {
  display: none;
}

.wizard-footer {
  margin-top: 2rem;
  display: flex;
  justify-content: space-between;
}

.btn-primary, .btn-secondary {
  padding: 0.75rem 2rem;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.btn-primary {
  background: #2563eb;
  color: white;
}

.btn-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}
</style>
```

### 3.2 PriceCalculator.vue - Sidebar Real-Time Pricing

```vue
<template>
  <div class="price-calculator">
    <h3>Estimasi Biaya</h3>
    
    <div v-if="loading" class="loading">Menghitung...</div>
    
    <div v-else-if="estimate" class="price-content">
      <!-- Stage Breakdown -->
      <div class="section">
        <h4>Biaya per Tahap</h4>
        <div v-for="(cost, key) in estimate.breakdown.stages" :key="key" class="cost-item">
          <span class="label">{{ formatStageKey(key) }}</span>
          <span class="amount">Rp {{ formatIDR(cost) }}</span>
        </div>
      </div>

      <!-- Storage -->
      <div v-if="estimate.breakdown.storage > 0" class="section">
        <div class="cost-item">
          <span class="label">Storage ({{ form.estimatedVolume.storage_gb }} GB)</span>
          <span class="amount">Rp {{ formatIDR(estimate.breakdown.storage) }}</span>
        </div>
      </div>

      <hr />

      <!-- Subtotal -->
      <div class="cost-item subtotal">
        <span class="label">Subtotal</span>
        <span class="amount">Rp {{ formatIDR(estimate.breakdown.subtotal) }}</span>
      </div>

      <!-- Tax (PPN 11%) -->
      <div class="cost-item tax">
        <span class="label">PPN 11%</span>
        <span class="amount">Rp {{ formatIDR(estimate.breakdown.tax) }}</span>
      </div>

      <hr class="thick" />

      <!-- Total -->
      <div class="cost-item total">
        <span class="label">Total Estimasi/Bulan</span>
        <span class="amount">Rp {{ formatIDR(estimate.monthly_total) }}</span>
      </div>

      <!-- Free Quota Info -->
      <div v-if="estimate.free_quota_applied" class="info-box">
        <span class="icon">ℹ️</span>
        <span>Kuota gratis sudah diperhitungkan</span>
      </div>

      <!-- Detail Button -->
      <button @click="showDetail = !showDetail" class="detail-btn">
        {{ showDetail ? '▼ Tutup Detail' : '▶ Lihat Detail' }}
      </button>

      <!-- Detail Table -->
      <div v-if="showDetail && estimate.detail_rows" class="detail-table">
        <table>
          <thead>
            <tr>
              <th>Tahap</th>
              <th>Model</th>
              <th>Unit</th>
              <th>Biaya</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in estimate.detail_rows" :key="`${row.stage}.${row.provider}`">
              <td>{{ row.stage }}</td>
              <td>{{ row.provider }}</td>
              <td>{{ row.monthly_units.toLocaleString('id-ID') }} {{ row.unit_name }}</td>
              <td>Rp {{ formatIDR(row.cost) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Volume Adjuster -->
      <div class="volume-adjuster">
        <h4>Sesuaikan Estimasi Volume</h4>
        <div class="slider-group">
          <label>Picks/hari: {{ form.estimatedVolume.picks }}</label>
          <input type="range" v-model.number="form.estimatedVolume.picks" 
                 min="100" max="10000" step="100" />
        </div>
        <div class="slider-group">
          <label>Events/hari: {{ form.estimatedVolume.events }}</label>
          <input type="range" v-model.number="form.estimatedVolume.events" 
                 min="1" max="100" step="1" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  form: Object
});

const emit = defineEmits(['update']);

const estimate = ref(null);
const loading = ref(false);
const showDetail = ref(false);

watch(() => props.form, async (newForm) => {
  // Parent component will trigger pricing update
  // This component just displays the result
}, { deep: true });

function formatIDR(amount) {
  return Math.round(amount).toLocaleString('id-ID');
}

function formatStageKey(key) {
  const [stage, provider] = key.split('.');
  const stageNames = {
    'ingest': 'Ingest',
    'p_pick': 'P-Pick',
    'association': 'Association',
    'locmag': 'LocMag'
  };
  return `${stageNames[stage] || stage}: ${provider}`;
}
</script>

<style scoped>
.price-calculator {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.5rem;
  position: sticky;
  top: 2rem;
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
}

.price-calculator h3 {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  color: #111827;
}

.cost-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  font-size: 0.9rem;
}

.cost-item.subtotal, .cost-item.total {
  font-weight: 600;
  font-size: 1rem;
}

.cost-item.total {
  font-size: 1.25rem;
  color: #2563eb;
}

hr {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 0.75rem 0;
}

hr.thick {
  border-top-width: 2px;
  border-color: #d1d5db;
}

.info-box {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
  padding: 0.75rem;
  margin-top: 1rem;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.detail-btn {
  width: 100%;
  padding: 0.5rem;
  margin-top: 1rem;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

.detail-table {
  margin-top: 1rem;
  overflow-x: auto;
}

.detail-table table {
  width: 100%;
  font-size: 0.8rem;
  border-collapse: collapse;
}

.detail-table th, .detail-table td {
  padding: 0.5rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.detail-table th {
  font-weight: 600;
  background: #f3f4f6;
}

.volume-adjuster {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 2px solid #e5e7eb;
}

.volume-adjuster h4 {
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

.slider-group {
  margin-bottom: 1rem;
}

.slider-group label {
  display: block;
  font-size: 0.85rem;
  margin-bottom: 0.25rem;
  color: #6b7280;
}

.slider-group input[type="range"] {
  width: 100%;
}
</style>
```

### 3.3 ModelCard.vue - Model Selection Card

```vue
<template>
  <div :class="['model-card', {selected, recommended: model.tier === 'GPU_BASIC'}]" @click="emit('select')">
    <div class="card-header">
      <h4>{{ model.name }}</h4>
      <span class="badge" :class="model.status">{{ model.status }}</span>
    </div>

    <div class="card-body">
      <div class="metrics">
        <div v-for="(value, key) in model.metrics" :key="key" class="metric">
          <span class="key">{{ formatMetricKey(key) }}:</span>
          <span class="value">{{ value }}</span>
        </div>
      </div>

      <p class="description">{{ model.description }}</p>

      <div class="pricing-info">
        <div class="price">
          <span class="amount">Rp {{ formatPrice(model.pricing.unit_price) }}</span>
          <span class="unit">{{ model.pricing.unit_name }}</span>
        </div>
        <div v-if="model.pricing.free_quota > 0" class="quota">
          Kuota gratis: {{ model.pricing.free_quota.toLocaleString('id-ID') }}/bulan
        </div>
        <div class="example">{{ model.pricing.example_monthly }}</div>
      </div>

      <div class="tags">
        <span v-if="model.gpu_required" class="tag gpu">GPU Required</span>
        <span v-else-if="model.tier.includes('GPU')" class="tag gpu-opt">GPU Optional</span>
        <span v-else class="tag cpu">CPU Only</span>
        <span class="tag tier">{{ model.tier }}</span>
      </div>
    </div>

    <div class="card-footer">
      <button class="select-btn">
        {{ selected ? '✓ Dipilih' : 'Pilih Model' }}
      </button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  model: Object,
  selected: Boolean
});

const emit = defineEmits(['select']);

function formatPrice(price) {
  return Math.round(price).toLocaleString('id-ID');
}

function formatMetricKey(key) {
  const map = {
    'precision': 'Precision',
    'recall': 'Recall',
    'latency': 'Latency',
    'location_error': 'Location Error',
    'magnitude_error': 'Mag Error'
  };
  return map[key] || key;
}
</script>

<style scoped>
.model-card {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
}

.model-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.model-card.selected {
  border-color: #2563eb;
  background: #eff6ff;
}

.model-card.recommended {
  border-color: #10b981;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.card-header h4 {
  margin: 0;
  font-size: 1.1rem;
}

.badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge.stable {
  background: #d1fae5;
  color: #065f46;
}

.badge.beta {
  background: #fef3c7;
  color: #92400e;
}

.badge.experimental {
  background: #fee2e2;
  color: #991b1b;
}

.metrics {
  margin-bottom: 0.75rem;
  font-size: 0.85rem;
}

.metric {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0;
}

.metric .key {
  color: #6b7280;
}

.metric .value {
  font-weight: 600;
}

.description {
  font-size: 0.85rem;
  color: #6b7280;
  margin-bottom: 1rem;
}

.pricing-info {
  background: #f9fafb;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 0.75rem;
}

.price {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.price .amount {
  font-size: 1.25rem;
  font-weight: 700;
  color: #2563eb;
}

.price .unit {
  font-size: 0.75rem;
  color: #6b7280;
}

.quota, .example {
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 0.25rem;
}

.tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}

.tag {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
}

.tag.gpu {
  background: #fef3c7;
  color: #92400e;
}

.tag.gpu-opt {
  background: #dbeafe;
  color: #1e40af;
}

.tag.cpu {
  background: #e0e7ff;
  color: #3730a3;
}

.tag.tier {
  background: #f3f4f6;
  color: #374151;
}

.select-btn {
  width: 100%;
  padding: 0.75rem;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  background: #f3f4f6;
  color: #374151;
  transition: all 0.2s;
}

.model-card.selected .select-btn {
  background: #2563eb;
  color: white;
}

.select-btn:hover {
  background: #e5e7eb;
}

.model-card.selected .select-btn:hover {
  background: #1d4ed8;
}
</style>
```

---

## 4. Metering Service (Python)

### 4.1 Usage Event Emission (di setiap stage module)

```python
# File: sispro-tews/p_pick_module/service.py (contoh di P-Pick)
import json
from kafka import KafkaProducer
from datetime import datetime

class PPickService:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers='kafka:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.workspace_id = os.getenv('WORKSPACE_ID', 'default')
        self.profile_rev = os.getenv('PROFILE_REV', 'unknown')
        self.provider_id = os.getenv('PROVIDER_ID', 'phasenet')
    
    def process_waveform_batch(self, waveforms):
        """Process batch waveforms dan emit usage event."""
        picks = []
        
        for wf in waveforms:
            # Run model inference
            pick = self.model.predict(wf)
            picks.append(pick)
        
        # Emit usage event untuk metering
        self.emit_usage_event(
            stage='p_pick',
            provider=self.provider_id,
            units=len(picks),
            unit_name='picks'
        )
        
        return picks
    
    def emit_usage_event(self, stage, provider, units, unit_name):
        """Emit usage event ke Kafka topic metering_events."""
        event = {
            'workspace_id': self.workspace_id,
            'profile_rev': self.profile_rev,
            'stage': stage,
            'provider': provider,
            'units': units,
            'unit_name': unit_name,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.producer.send('metering_events', value=event, key=self.workspace_id.encode('utf-8'))
        self.producer.flush()
```

### 4.2 Metering Aggregator

```python
# File: sispro-tews/metering_module/aggregator.py
from kafka import KafkaConsumer
from pymongo import MongoClient
from datetime import datetime, date
from collections import defaultdict
import json

class MeteringAggregator:
    """
    Consume metering_events, aggregate per workspace per day, write to MongoDB.
    """
    
    def __init__(self):
        self.consumer = KafkaConsumer(
            'metering_events',
            bootstrap_servers='kafka:9092',
            group_id='metering_aggregator',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        
        self.mongo = MongoClient('mongodb://mongodb:27017/')
        self.db = self.mongo['sispro-tews']
        self.usage_collection = self.db['usage_daily']
        
        # In-memory buffer untuk aggregasi (flush setiap 5 menit atau 1000 events)
        self.buffer = defaultdict(lambda: defaultdict(int))
        self.buffer_size = 0
        self.max_buffer_size = 1000
    
    def run(self):
        """Main loop untuk consume dan aggregate."""
        print("[MeteringAggregator] Starting...")
        
        for message in self.consumer:
            event = message.value
            self.process_event(event)
            
            self.buffer_size += 1
            if self.buffer_size >= self.max_buffer_size:
                self.flush_buffer()
    
    def process_event(self, event):
        """Process satu usage event dan tambahkan ke buffer."""
        workspace_id = event['workspace_id']
        stage = event['stage']
        provider = event['provider']
        units = event['units']
        timestamp = datetime.fromisoformat(event['timestamp'])
        date_str = timestamp.date().isoformat()  # YYYY-MM-DD
        
        key = f"{workspace_id}:{date_str}:{stage}.{provider}"
        self.buffer[key]['units'] += units
        self.buffer[key]['workspace_id'] = workspace_id
        self.buffer[key]['date'] = date_str
        self.buffer[key]['stage'] = stage
        self.buffer[key]['provider'] = provider
    
    def flush_buffer(self):
        """Flush buffer ke MongoDB (upsert per workspace.date.stage.provider)."""
        if not self.buffer:
            return
        
        print(f"[MeteringAggregator] Flushing {len(self.buffer)} records...")
        
        for key, data in self.buffer.items():
            self.usage_collection.update_one(
                {
                    'workspace_id': data['workspace_id'],
                    'date': data['date'],
                    'stage': data['stage'],
                    'provider': data['provider']
                },
                {
                    '$inc': {'units': data['units']},
                    '$set': {'updated_at': datetime.utcnow()}
                },
                upsert=True
            )
        
        self.buffer.clear()
        self.buffer_size = 0
        print("[MeteringAggregator] Flush complete.")

if __name__ == '__main__':
    aggregator = MeteringAggregator()
    aggregator.run()
```

### 4.3 Billing Service (Cron Monthly)

```python
# File: sispro-tews/billing_module/service.py
from pymongo import MongoClient
from datetime import datetime
from pricing_model import PricingCalculator, UsageRecord
import json

class BillingService:
    """Generate monthly invoice dari usage_daily records."""
    
    def __init__(self):
        self.mongo = MongoClient('mongodb://mongodb:27017/')
        self.db = self.mongo['sispro-tews']
        self.usage_collection = self.db['usage_daily']
        self.invoice_collection = self.db['invoices']
        self.calculator = PricingCalculator()
    
    def generate_monthly_invoice(self, workspace_id, year, month):
        """
        Generate invoice untuk workspace di bulan tertentu.
        
        Args:
            workspace_id: "default"
            year: 2026
            month: 10
        """
        month_str = f"{year}-{month:02d}"
        print(f"[BillingService] Generating invoice for {workspace_id} {month_str}...")
        
        # Query all usage_daily untuk bulan ini
        usage_docs = list(self.usage_collection.find({
            'workspace_id': workspace_id,
            'date': {'$regex': f'^{month_str}'}
        }))
        
        if not usage_docs:
            print(f"[BillingService] No usage data for {workspace_id} {month_str}")
            return None
        
        # Aggregate ke UsageRecord per hari
        usage_by_date = {}
        for doc in usage_docs:
            date_str = doc['date']
            if date_str not in usage_by_date:
                usage_by_date[date_str] = UsageRecord(workspace_id, date_str)
            
            usage_by_date[date_str].add_stage_usage(
                doc['stage'],
                doc['provider'],
                doc['units']
            )
        
        usage_records = list(usage_by_date.values())
        
        # Calculate invoice
        invoice = self.calculator.calculate_invoice(
            usage_records,
            workspace_id,
            month_str
        )
        
        # Save invoice to MongoDB
        invoice_doc = {
            'workspace_id': workspace_id,
            'period': month_str,
            'generated_at': datetime.utcnow(),
            'status': 'pending',  # pending | paid | overdue
            'breakdown': {
                'stages': {k: float(v) for k, v in invoice.stage_costs.items()},
                'sinks': {k: float(v) for k, v in invoice.sink_costs.items()},
                'storage': float(invoice.storage_cost),
                'subtotal': float(invoice.subtotal),
                'discount': float(invoice.discount),
                'tax': float(invoice.tax),
                'total': float(invoice.total)
            },
            'currency': invoice.currency,
            'due_date': f"{year}-{month+1:02d}-10"  # jatuh tempo tanggal 10 bulan berikutnya
        }
        
        result = self.invoice_collection.insert_one(invoice_doc)
        print(f"[BillingService] Invoice generated: {result.inserted_id}")
        print(f"  Total: Rp {invoice.total:,.0f}")
        
        # TODO: Send email dengan invoice PDF
        # self.send_invoice_email(workspace_id, invoice_doc)
        
        return invoice_doc

if __name__ == '__main__':
    # Cron job: jalankan setiap tanggal 1 bulan baru
    service = BillingService()
    now = datetime.now()
    prev_month = now.month - 1 if now.month > 1 else 12
    prev_year = now.year if now.month > 1 else now.year - 1
    
    # Generate invoice untuk semua workspace
    workspaces = service.db['profiles'].distinct('workspace_id')
    for ws in workspaces:
        service.generate_monthly_invoice(ws, prev_year, prev_month)
```

---

## 5. Database Schema (MongoDB)

### 5.1 Collection: `profiles`

```javascript
{
  _id: ObjectId("..."),
  workspace_id: "default",
  mode: "custom",
  name: "Production Pipeline",
  status: "active",  // draft | validating | activating | active | inactive
  stages: {
    ingest: { provider: "seedlink_v3", enabled: true, params: {} },
    p_pick: { provider: "phasenet", enabled: true, params: {p_threshold: 0.3} }
  },
  sinks: {
    ws_ui: { params: {artifacts: ["pick", "event"]} },
    archive: {}
  },
  external_inputs: [],
  compiled: { ... },  // hasil compile_pipeline
  rev: "a3b2c1d4",
  created_at: ISODate("2026-10-10T00:00:00Z"),
  activated_at: ISODate("2026-10-10T01:00:00Z")
}
```

### 5.2 Collection: `usage_daily`

```javascript
{
  _id: ObjectId("..."),
  workspace_id: "default",
  date: "2026-10-10",
  stage: "p_pick",
  provider: "phasenet",
  units: 15000,  // jumlah picks yang diproses hari ini
  updated_at: ISODate("2026-10-10T23:59:59Z")
}
```

### 5.3 Collection: `invoices`

```javascript
{
  _id: ObjectId("..."),
  workspace_id: "default",
  period: "2026-10",
  generated_at: ISODate("2026-11-01T00:00:00Z"),
  status: "pending",  // pending | paid | overdue | cancelled
  breakdown: {
    stages: {
      "p_pick.phasenet": 7500000,
      "association.dbscan_simple": 300000
    },
    storage: 75000,
    subtotal: 7875000,
    discount: 0,
    tax: 866250,
    total: 8741250
  },
  currency: "IDR",
  due_date: "2026-11-10",
  paid_at: null,
  payment_method: null
}
```

---

## 6. Deployment Checklist

### Phase 1: API + Pricing Calculator (2 minggu)
- [ ] Implement `/api/v2/models` endpoint
- [ ] Implement `/api/v2/pricing/estimate` endpoint
- [ ] Deploy `pricing_model.py` ke controller_module
- [ ] Test pricing calculation dengan berbagai skenario
- [ ] Build frontend PriceCalculator.vue component
- [ ] Integrate dengan Vue router + state management

### Phase 2: Profile Management (2 minggu)
- [ ] Implement `/api/v2/profiles` CRUD endpoints
- [ ] Implement `/api/v2/profiles/{id}/validate` endpoint
- [ ] Implement `/api/v2/profiles/{id}/activate` endpoint
- [ ] Build frontend PipelineWizard.vue
- [ ] Build ModelCard.vue dan ReviewPanel.vue
- [ ] E2E test: create profile → validate → activate → verify runtime

### Phase 3: Metering Infrastructure (2 minggu)
- [ ] Add usage event emission ke semua stage modules
- [ ] Deploy metering_aggregator service (Kafka consumer)
- [ ] Create MongoDB indexes untuk usage_daily collection
- [ ] Build monitoring dashboard untuk usage metrics
- [ ] Test metering dengan load testing (simulate 10K picks/day)

### Phase 4: Billing System (1 minggu)
- [ ] Implement BillingService cron job
- [ ] Generate invoice PDF template
- [ ] Integrate email service (SMTP/SendGrid)
- [ ] Build invoice viewer UI di frontend
- [ ] Test end-to-end: usage → metering → invoice generation

### Phase 5: Payment Integration (opsional, 2 minggu)
- [ ] Integrate payment gateway (Midtrans/Xendit)
- [ ] Auto-charge workflow
- [ ] Payment success/failure webhooks
- [ ] Workspace suspend/resume berdasarkan payment status

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# test_pricing_calculator.py
def test_estimate_with_free_quota():
    calc = PricingCalculator()
    selected = {"p_pick": "phasenet"}  # 5000 free quota
    volume = {"picks": 3000}  # di bawah quota
    
    result = estimate_from_ui_selection(selected, volume)
    
    assert result['monthly_total'] == 0  # semua masuk quota gratis

def test_estimate_above_quota():
    calc = PricingCalculator()
    selected = {"p_pick": "phasenet"}  # 5000 free quota, Rp 500/1K picks
    volume = {"picks": 10000}  # 10K picks/day × 30 = 300K/month
    
    result = estimate_from_ui_selection(selected, volume)
    
    # (300K - 5K quota) / 1K × 500 = 295 × 500 = 147,500
    # + PPN 11% = 163,725
    assert result['monthly_total'] == pytest.approx(163725, rel=0.01)
```

### 7.2 Integration Tests

```python
# test_profile_activation.py
async def test_profile_activation_flow():
    # 1. Create profile draft
    response = await client.post('/api/v2/profiles', json={
        "workspace_id": "test",
        "mode": "custom",
        "name": "Test Profile",
        "stages": {
            "ingest": {"provider": "seedlink_v3"},
            "p_pick": {"provider": "phasenet"}
        },
        "sinks": {"ws_ui": {}}
    })
    profile_id = response.json()['id']
    
    # 2. Validate
    response = await client.post(f'/api/v2/profiles/{profile_id}/validate')
    assert response.json()['valid'] == True
    
    # 3. Activate
    response = await client.post(f'/api/v2/profiles/{profile_id}/activate')
    assert response.json()['status'] == 'activating'
    
    # 4. Wait for activation
    await asyncio.sleep(10)
    
    # 5. Verify runtime config
    # TODO: check Kafka config_events, check stage module applied config
```

### 7.3 Load Tests (Locust)

```python
# locust_pricing_api.py
from locust import HttpUser, task, between

class PricingUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def estimate_pricing(self):
        self.client.post('/api/v2/pricing/estimate', json={
            "workspace_id": "default",
            "mode": "custom",
            "selected_models": {
                "p_pick": "phasenet",
                "association": "dbscan_simple"
            },
            "estimated_daily_volume": {
                "waveforms": 10000,
                "picks": 500,
                "events": 10
            }
        })
```

---

## 8. Monitoring & Alerting

### Metrics to Track (Prometheus)

```yaml
# Pricing API
- api_pricing_estimate_duration_seconds
- api_pricing_estimate_errors_total

# Metering
- metering_events_consumed_total
- metering_buffer_size
- metering_flush_duration_seconds

# Billing
- invoices_generated_total
- invoice_amount_idr (histogram)
- invoices_overdue_total

# Usage per Workspace
- workspace_usage_units_total{workspace_id, stage, provider}
- workspace_monthly_cost_idr{workspace_id}
```

### Alerts (Grafana)

```yaml
- Alert: "High Pricing API Latency"
  Condition: api_pricing_estimate_duration_seconds > 2s
  Action: Notify #engineering-alerts

- Alert: "Metering Buffer Growing"
  Condition: metering_buffer_size > 5000 for 10m
  Action: Scale metering aggregator

- Alert: "Invoice Generation Failed"
  Condition: invoices_generated_total == 0 on day 1 of month
  Action: Page on-call engineer

- Alert: "Workspace Exceeded Budget"
  Condition: workspace_monthly_cost_idr > user_budget_limit
  Action: Email workspace admin
```

---

## 9. FAQ & Troubleshooting

### Q: Bagaimana cara update harga model tanpa deploy ulang?
A: Harga disimpan di MongoDB collection `pricing_rules` (lihat pricing_model.py). Admin bisa update via UI atau API, akan langsung apply di pricing calculator.

### Q: Bagaimana handle refund jika ada error processing?
A: Setiap usage event punya `profile_rev` dan timestamp. Jika ada error, bisa query usage_daily → adjust units → regenerate invoice.

### Q: Bagaimana prevent quota abuse (user spam low-cost requests)?
A: Implement rate limiting di API gateway (nginx/kong) dan throttle di stage modules (max picks/minute per workspace).

### Q: Bagaimana migrate existing users ke pay-per-use model?
A: 1) Announce via email + in-app banner, 2) Grandfather existing users dengan free quota besar selama 3 bulan, 3) Gradual reduction setiap bulan.

---

## 10. Next Steps

1. **Review dengan tim** — pastikan pricing model dan UI flow sesuai business requirements
2. **Finalize unit rates** — sesuaikan harga per model dengan cost actual (GPU, storage, bandwidth)
3. **Build MVP (Phase 1-2)** — fokus ke pricing calculator + profile management tanpa billing
4. **User testing** — test dengan 5-10 beta users, collect feedback
5. **Iterate** — improve UI/UX berdasarkan feedback
6. **Deploy Phase 3-4** — metering + billing system untuk production

---

**Document Version:** 1.0  
**Last Updated:** 2026-10-10  
**Author:** AI-GEMPA Development Team
