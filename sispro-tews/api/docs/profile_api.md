# Profile API Documentation

Version: v2  
Base URL: `/api/v2`  
Authentication: Bearer token (TODO)

## Overview

Profile API mengelola konfigurasi pipeline seismik per workspace. Setiap workspace bisa punya multiple profiles (DRAFT), tapi hanya 1 profile ACTIVE.

**Profile lifecycle:**
```
DRAFT → ACTIVE → ARCHIVED
```

- **DRAFT**: editable, bisa di-update/delete
- **ACTIVE**: read-only, sedang digunakan pipeline
- **ARCHIVED**: historical, tidak aktif lagi

---

## Endpoints

### 1. List Profiles

**GET** `/api/v2/profiles`

Query params:
- `workspace_id` (required): Workspace ID
- `status` (optional): `draft` | `active` | `archived`

Response:
```json
{
  "profiles": [
    {
      "id": "prof_xyz",
      "workspace_id": "ws_001",
      "name": "Production Pipeline",
      "description": "Standard seismic processing",
      "p_pick_config": {
        "provider_id": "phasenet",
        "tier": "GPU_BASIC",
        "enabled": true,
        "custom_params": {}
      },
      "association_config": {
        "provider_id": "gamma",
        "tier": "CPU",
        "enabled": true,
        "custom_params": {}
      },
      "locmag_config": {
        "provider_id": "pyocto",
        "tier": "CPU",
        "enabled": true,
        "custom_params": {}
      },
      "preferences": {
        "sample_rate": 50.0,
        "channels": ["BHZ", "BHN", "BHE"],
        "min_magnitude": 2.0,
        "p_pick_sensitivity": "normal",
        "association_distance_km": 20.0,
        "locmag_depth_constraint": null,
        "auto_publish_events": false,
        "webhook_url": null
      },
      "status": "active",
      "created_at": "2026-10-19T12:00:00Z",
      "updated_at": "2026-10-19T12:30:00Z",
      "activated_at": "2026-10-19T12:30:00Z",
      "archived_at": null,
      "created_by": "user_001",
      "updated_by": "user_001"
    }
  ],
  "count": 1,
  "active_profile_id": "prof_xyz"
}
```

---

### 2. Get Profile by ID

**GET** `/api/v2/profiles/{profile_id}`

Response: single profile object (sama seperti list response item).

Errors:
- `404`: Profile not found

---

### 3. Create Profile

**POST** `/api/v2/profiles`

Query params:
- `workspace_id` (required): Workspace ID
- `created_by` (required): User ID

Request body:
```json
{
  "name": "New Pipeline",
  "description": "Optional description",
  "p_pick_provider_id": "sta_lta",
  "association_provider_id": "dbscan",
  "locmag_provider_id": "geiger",
  "preferences": {
    "sample_rate": 50.0,
    "channels": ["BHZ", "BHN", "BHE"],
    "min_magnitude": 2.0,
    "p_pick_sensitivity": "normal",
    "association_distance_km": 20.0
  }
}
```

Response: `201 Created` dengan profile object.

Defaults:
- `p_pick_provider_id`: `sta_lta`
- `association_provider_id`: `dbscan`
- `locmag_provider_id`: `geiger`
- `status`: `draft`
- `preferences`: sensible defaults (sample_rate=100.0, channels=["BHZ","BHN","BHE"], min_magnitude=2.0)

---

### 4. Update Profile

**PUT** `/api/v2/profiles/{profile_id}`

Query params:
- `updated_by` (required): User ID

Request body (partial update):
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "p_pick_provider_id": "eqtransformer",
  "preferences": {
    "sample_rate": 80.0,
    "p_pick_sensitivity": "high"
  }
}
```

Response: `200 OK` dengan updated profile object.

Constraints:
- Only DRAFT profiles dapat di-update
- `400` jika status != DRAFT

---

### 5. Activate Profile

**POST** `/api/v2/profiles/{profile_id}/activate`

Query params:
- `updated_by` (required): User ID

Request body:
```json
{
  "profile_id": "prof_xyz"
}
```

Response: `200 OK` dengan activated profile object.

Behavior:
- Transition DRAFT → ACTIVE
- Validasi profile sebelum activate (nama, providers, preferences)
- Auto-archive sibling profiles (workspace yang sama) yang ACTIVE
- `400` jika validation gagal atau status != DRAFT

---

### 6. Delete Profile

**DELETE** `/api/v2/profiles/{profile_id}`

Response: `204 No Content`

Constraints:
- Only DRAFT profiles dapat di-delete
- `400` jika status != DRAFT
- `404` jika profile not found

---

### 7. Validate Profile

**POST** `/api/v2/profiles/{profile_id}/validate`

Response:
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

Validation rules:
- Profile name tidak boleh kosong
- P-pick, association, locmag provider harus ada
- Sample rate harus 20-100 Hz
- Minimal 1 channel

---

### 8. Estimate Cost

**GET** `/api/v2/profiles/{profile_id}/cost`

Response:
```json
{
  "profile_id": "prof_xyz",
  "estimated_monthly_cost_idr": 1250000.0,
  "assumptions": {
    "picks_per_day": 10000,
    "clusters_per_day": 2000,
    "events_per_day": 1000
  }
}
```

Assumptions:
- Average 10K picks/day
- Average 2K clusters/day
- Average 1K events/day
- 30 days/month

Cost calculation:
```
total_cost = (picks_cost + clusters_cost + events_cost) - free_quota_value
```

Provider rates lookup dari `catalog_module/data/rates.yaml`.

---

### 9. Health Check

**GET** `/api/v2/health/profiles`

Response:
```json
{
  "status": "healthy",
  "service": "profile"
}
```

---

## Error Responses

Standard error format:
```json
{
  "detail": "Error message"
}
```

Status codes:
- `400`: Bad request (validation failure, invalid state transition)
- `404`: Resource not found
- `500`: Internal server error

---

## Provider IDs

**P-Pick Providers:**
- `sta_lta` (CPU) — classic STA/LTA algorithm
- `phasenet` (GPU_BASIC, GPU_PREMIUM) — PhaseNet deep learning
- `eqtransformer` (GPU_BASIC, GPU_PREMIUM) — EQTransformer deep learning

**Association Providers:**
- `dbscan` (CPU) — DBSCAN clustering
- `gamma` (CPU, GPU_BASIC) — GaMMA association

**Locmag Providers:**
- `geiger` (CPU) — Geiger location method
- `pyocto` (CPU) — PyOcto location
- `nonlinloc` (CPU) — NonLinLoc probabilistic location

---

## Pipeline Preferences

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `sample_rate` | float | 100.0 | 20-100 | Sampling rate (Hz) |
| `channels` | list | ["BHZ","BHN","BHE"] | min 1 | Channel codes |
| `min_magnitude` | decimal | 2.0 | - | Minimum magnitude threshold |
| `p_pick_sensitivity` | string | "normal" | low/normal/high | P-pick sensitivity |
| `association_distance_km` | float | 20.0 | 5-100 | Association distance (km) |
| `locmag_depth_constraint` | float | null | - | Depth constraint (km, optional) |
| `auto_publish_events` | bool | false | - | Auto-publish detected events |
| `webhook_url` | string | null | - | Webhook untuk notifications |

---

## Usage Examples

### Create a basic profile
```bash
curl -X POST "http://localhost:8000/api/v2/profiles?workspace_id=ws_001&created_by=user_001" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Pipeline",
    "description": "Testing profile API"
  }'
```

### Activate a profile
```bash
curl -X POST "http://localhost:8000/api/v2/profiles/prof_xyz/activate?updated_by=user_001" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "prof_xyz"
  }'
```

### List all profiles in workspace
```bash
curl "http://localhost:8000/api/v2/profiles?workspace_id=ws_001"
```

### Estimate monthly cost
```bash
curl "http://localhost:8000/api/v2/profiles/prof_xyz/cost"
```
