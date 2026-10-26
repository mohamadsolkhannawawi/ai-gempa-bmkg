# Migration Guide: v1.x → v2.0 (Pay-Per-Use Architecture)

## Overview

AI-GEMPA v2.0 introduces pay-per-use pricing, multi-provider AI selection, and dynamic pipeline configuration. This guide helps migrate from v1.x (fixed-price monolith) to v2.0 (microservices).

---

## Breaking Changes

### 1. API Prefix Change
**v1:** `/api/v1/*`  
**v2:** `/api/v2/*`

**Action:** Update all API client URLs.

```diff
- const API_BASE = 'http://localhost:4002/api/v1'
+ const API_BASE = 'http://localhost:4002/api/v2'
```

### 2. Pricing Model
**v1:** Fixed monthly subscription  
**v2:** Pay-per-inference (IDR per inference)

**Action:** Migrate workspace billing to usage-based model.

### 3. Profile Configuration
**v1:** Single hardcoded pipeline  
**v2:** User-defined profiles with provider selection

**Migration script:**
```python
# Migrate existing workspaces to default profile
import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017")
db = client.gempa

for workspace in db.workspaces_legacy.find():
    profile = {
        "workspace_id": workspace["_id"],
        "name": "Default Profile (migrated)",
        "description": "Auto-migrated from v1",
        "config": {
            "p_pick": {"provider": "stalta", "tier": "cpu"},
            "association": {"provider": "dbscan", "tier": "cpu"},
            "locmag": {"provider": "geiger", "tier": "cpu"}
        },
        "is_default": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    db.profiles.insert_one(profile)
    print(f"Migrated workspace {workspace['_id']}")
```

### 4. Database Schema

**New collections:**
- `profiles` — compute profiles
- `catalog` — provider registry
- `usage_events` — metering data
- `invoices` — billing records

**Action:** Run MongoDB migrations (see below).

---

## Migration Steps

### Step 1: Backup v1 Database
```bash
mongodump --uri="mongodb://localhost:27017/gempa" --out=/backup/gempa-v1-$(date +%F)
```

### Step 2: Deploy v2 Alongside v1
```bash
# Keep v1 running on port 4001
# Start v2 on port 4002
docker-compose -f docker-compose.dev.yml up -d
```

### Step 3: Run Migration Scripts
```bash
cd sispro-tews/migrations
python 001_create_collections.py
python 002_migrate_workspaces_to_profiles.py
python 003_backfill_catalog.py
```

### Step 4: Test v2 API
```bash
# Create test profile
curl -X POST http://localhost:4002/api/v2/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "ws_test",
    "name": "Test Profile",
    "config": {
      "p_pick": {"provider": "phasenet", "tier": "cpu"}
    }
  }'

# Get catalog
curl http://localhost:4002/api/v2/catalog
```

### Step 5: Update Frontend
```bash
cd frontend
npm install
npm run build

# Update env
echo "VITE_API_BASE_URL=http://localhost:4002/api/v2" > .env.production
```

### Step 6: Switch Traffic
```nginx
# Nginx config
location /api/v1/ {
    proxy_pass http://localhost:4001;  # v1 (read-only)
}

location /api/v2/ {
    proxy_pass http://localhost:4002;  # v2 (read-write)
}
```

### Step 7: Monitor for 2 Weeks
- Check error logs: `docker-compose logs -f api`
- Monitor usage: `GET /api/v2/pricing/usage-statement`
- Verify invoices generated correctly

### Step 8: Decommission v1
```bash
# After 2 weeks with no issues
docker-compose -f docker-compose.v1.yml down
```

---

## API Endpoint Mapping

| v1 Endpoint                     | v2 Equivalent                              | Notes                     |
|---------------------------------|--------------------------------------------|---------------------------|
| `GET /api/v1/providers`         | `GET /api/v2/catalog`                      | Renamed                   |
| `POST /api/v1/process`          | Use profile + inference endpoint           | Split into profile mgmt   |
| `GET /api/v1/billing/invoices`  | `GET /api/v2/pricing/invoices`             | Moved to pricing service  |
| `GET /api/v1/usage`             | `GET /api/v2/pricing/usage-statement`      | Enhanced with breakdown   |
| N/A                             | `POST /api/v2/profiles` (new)              | New profile CRUD          |
| N/A                             | `POST /api/v2/profiles/{id}/estimate-cost` | New cost estimator        |

---

## Data Migration Scripts

### 001_create_collections.py
```python
import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017")
db = client.gempa

# Create collections with validation
db.create_collection("profiles", validator={...})
db.create_collection("catalog", validator={...})
db.create_collection("usage_events", validator={...})
db.create_collection("invoices", validator={...})

# Create indexes
db.profiles.create_index([("workspace_id", 1), ("name", 1)], unique=True)
db.usage_events.create_index([("workspace_id", 1), ("timestamp", -1)])
db.invoices.create_index([("workspace_id", 1), ("period_start", 1)])

print("✅ Collections created")
```

### 002_migrate_workspaces_to_profiles.py
```python
# See "Profile Configuration" section above
```

### 003_backfill_catalog.py
```python
from catalog_module.service import CatalogService

service = CatalogService()
await service.initialize_catalog()
print("✅ Catalog backfilled")
```

---

## Configuration Changes

### Environment Variables

**New in v2:**
```bash
# Redis (required)
REDIS_URL=redis://localhost:6379/0

# Kafka (required)
KAFKA_BROKERS=localhost:29092

# SMTP (for billing emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=billing@bmkg.go.id
SMTP_PASS=<app-password>
```

### Docker Compose
```yaml
# v2 adds 3 services
services:
  metering:  # New worker
  billing:   # New worker
  kafka:     # New dependency
```

---

## Rollback Plan

If v2 fails:

1. **Stop v2:**
   ```bash
   docker-compose -f docker-compose.dev.yml down
   ```

2. **Restore v1:**
   ```bash
   docker-compose -f docker-compose.v1.yml up -d
   ```

3. **Restore database:**
   ```bash
   mongorestore --drop --uri="mongodb://localhost:27017/gempa" /backup/gempa-v1-<date>
   ```

4. **Revert Nginx config** to point all traffic to v1.

---

## Testing Checklist

- [ ] Create new profile via API
- [ ] Estimate cost for profile
- [ ] Run inference with new profile
- [ ] Verify metering events in Redis
- [ ] Check usage statement reflects correct data
- [ ] Generate test invoice (manually trigger cron)
- [ ] Download invoice PDF
- [ ] Test payment webhook
- [ ] Verify frontend loads profiles
- [ ] Verify frontend displays invoices

---

## FAQ

### Q: Can v1 and v2 run simultaneously?
**A:** Yes, during migration period (2-4 weeks). Run on different ports.

### Q: Will v1 API remain accessible?
**A:** Yes, as read-only for 6 months. Write operations redirect to v2.

### Q: How to migrate historical billing data?
**A:** Run `migrations/004_backfill_invoices.py` to convert v1 invoices to v2 format.

### Q: What happens to existing SeedLink connections?
**A:** No change. SeedLink ingestion unchanged, only processing pipeline differs.

### Q: Are GPU providers available immediately?
**A:** No. GPU tiers require compute node setup. Contact ops team.

---

## Support

- **Issues:** https://github.com/mohamadsolkhannawawi/ai-gempa-bmkg/issues
- **Email:** support@bmkg.go.id
- **Docs:** [README_DEPLOYMENT.md](README_DEPLOYMENT.md)

---

## Timeline

- **2026-10-19:** v2.0.0-alpha released
- **2026-10-26:** Migration period begins (2 weeks)
- **2026-11-09:** v2.0.0-beta (stabilization)
- **2026-11-23:** v2.0.0 GA (production-ready)
- **2027-04-30:** v1 API deprecated (6 months notice)
