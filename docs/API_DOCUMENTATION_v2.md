# AI-GEMPA BMKG API Documentation v2.0

## Base URL
```
http://localhost:4002/api/v2
```

## Authentication
Currently: No auth (internal services).  
Future: JWT tokens via `Authorization: Bearer <token>`.

---

## 1. Catalog Service

### GET /catalog
List all available providers and model tiers.

**Response 200:**
```json
{
  "providers": [
    {
      "name": "stalta",
      "module": "p_pick",
      "tiers": [
        {
          "name": "cpu",
          "available": true,
          "cost_per_inference_idr": 5
        }
      ]
    }
  ]
}
```

### GET /catalog/model-tiers
Get detailed model tier pricing.

**Response 200:**
```json
[
  {
    "id": "stalta_cpu",
    "provider": "stalta",
    "module": "p_pick",
    "tier": "cpu",
    "cost_per_inference_idr": 5,
    "description": "STA/LTA CPU picker"
  }
]
```

---

## 2. Profile Service

### POST /profiles
Create new compute profile.

**Request:**
```json
{
  "workspace_id": "ws_12345",
  "name": "Production Profile",
  "description": "High-accuracy GPU pipeline",
  "config": {
    "p_pick": {
      "provider": "phasenet",
      "tier": "gpu",
      "config": {}
    },
    "association": {
      "provider": "gamma",
      "tier": "gpu"
    },
    "locmag": {
      "provider": "nonlinloc",
      "tier": "cpu"
    }
  }
}
```

**Response 201:**
```json
{
  "id": "prof_abc123",
  "workspace_id": "ws_12345",
  "name": "Production Profile",
  "config": {...},
  "created_at": "2026-10-19T13:45:00Z",
  "updated_at": "2026-10-19T13:45:00Z"
}
```

### GET /profiles
List profiles for workspace.

**Query params:**
- `workspace_id` (required)
- `limit` (default: 50)
- `offset` (default: 0)

**Response 200:**
```json
{
  "items": [...],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

### GET /profiles/{profile_id}
Get profile detail.

**Response 200:** Same as POST response.

### PUT /profiles/{profile_id}
Update profile config.

**Request:** Same as POST (partial allowed).

**Response 200:** Updated profile.

### DELETE /profiles/{profile_id}
Delete profile.

**Response 204:** No content.

### POST /profiles/{profile_id}/compile
Compile profile to executable pipeline spec.

**Response 200:**
```json
{
  "profile_id": "prof_abc123",
  "pipeline_spec": {
    "modules": [
      {"step": "p_pick", "provider": "phasenet", "tier": "gpu", "cost_idr": 15}
    ],
    "estimated_cost_per_inference": 155
  }
}
```

### POST /profiles/{profile_id}/estimate-cost
Quick cost estimation.

**Request:**
```json
{
  "monthly_inferences": 10000
}
```

**Response 200:**
```json
{
  "profile_id": "prof_abc123",
  "estimated_cost_per_inference": 155,
  "monthly_inferences": 10000,
  "estimated_monthly_cost_idr": 1550000,
  "breakdown": [
    {"module": "p_pick", "provider": "phasenet", "tier": "gpu", "cost_idr": 15}
  ]
}
```

### GET /profiles/{profile_id}/compute-specs
Get recommended compute specs for profile.

**Response 200:**
```json
{
  "profile_id": "prof_abc123",
  "cpu_cores": 4,
  "memory_gb": 16,
  "gpu_required": true,
  "gpu_memory_gb": 8,
  "recommended_instance": "g4dn.xlarge"
}
```

---

## 3. Pricing Service

### GET /pricing/invoices
List invoices for workspace.

**Query params:**
- `workspace_id` (required)
- `status` (optional: DRAFT, ISSUED, PAID, OVERDUE, CANCELLED)
- `start_date` (optional: ISO date)
- `end_date` (optional: ISO date)
- `limit` (default: 50)
- `offset` (default: 0)

**Response 200:**
```json
{
  "items": [
    {
      "id": "inv_xyz",
      "invoice_number": "INV-2026-10-001",
      "workspace_id": "ws_12345",
      "period_start": "2026-10-01",
      "period_end": "2026-10-31",
      "subtotal_idr": 1000000,
      "tax_idr": 110000,
      "total_idr": 1110000,
      "status": "ISSUED",
      "due_date": "2026-11-07",
      "issued_at": "2026-11-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

### GET /pricing/invoices/{invoice_id}
Get invoice detail with line items.

**Response 200:**
```json
{
  "id": "inv_xyz",
  "invoice_number": "INV-2026-10-001",
  "workspace_id": "ws_12345",
  "line_items": [
    {
      "profile_id": "prof_abc123",
      "profile_name": "Production Profile",
      "total_inferences": 5000,
      "cost_per_inference_idr": 155,
      "subtotal_idr": 775000
    }
  ],
  "subtotal_idr": 1000000,
  "tax_rate": 0.11,
  "tax_idr": 110000,
  "total_idr": 1110000,
  "status": "ISSUED",
  "pdf_url": "/pricing/invoices/inv_xyz/pdf"
}
```

### GET /pricing/invoices/{invoice_id}/pdf
Download invoice PDF.

**Response 200:** `application/pdf`

### GET /pricing/usage-statement
Get usage statement for period.

**Query params:**
- `workspace_id` (required)
- `start_date` (required: YYYY-MM-DD)
- `end_date` (required: YYYY-MM-DD)
- `profile_id` (optional)

**Response 200:**
```json
{
  "workspace_id": "ws_12345",
  "period_start": "2026-10-01",
  "period_end": "2026-10-31",
  "total_inferences": 10000,
  "total_cost_idr": 1550000,
  "breakdown": [
    {
      "profile_id": "prof_abc123",
      "profile_name": "Production Profile",
      "inferences": 10000,
      "cost_idr": 1550000,
      "by_provider": [
        {"provider": "phasenet", "tier": "gpu", "count": 10000, "cost_idr": 150000}
      ]
    }
  ]
}
```

---

## 4. Health & Status

### GET /health
Service health check.

**Response 200:**
```json
{
  "status": "healthy",
  "version": "2.0.0-alpha",
  "services": {
    "mongodb": "connected",
    "redis": "connected",
    "kafka": "connected"
  }
}
```

---

## Error Responses

All endpoints return standard error format:

**4xx/5xx:**
```json
{
  "error": "ValidationError",
  "message": "workspace_id is required",
  "details": {...}
}
```

Common status codes:
- 400 Bad Request — invalid input
- 404 Not Found — resource not found
- 409 Conflict — duplicate or constraint violation
- 500 Internal Server Error — server-side failure

---

## Rate Limits
Currently: No rate limit (internal).  
Future: 1000 req/min per workspace.

---

## Webhooks

### POST /billing/webhooks/payment-confirmation
External payment gateway callback.

**Request:**
```json
{
  "invoice_id": "inv_xyz",
  "amount_paid": 1110000,
  "payment_method": "bank_transfer",
  "transaction_id": "txn_external_12345",
  "paid_at": "2026-11-05T10:30:00Z"
}
```

**Response 200:**
```json
{
  "status": "processed",
  "invoice_id": "inv_xyz",
  "new_status": "PAID"
}
```
