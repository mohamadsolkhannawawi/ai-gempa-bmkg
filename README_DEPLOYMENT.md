# AI-GEMPA BMKG — Deployment Guide

## Quick Start (Development)

### Prerequisites
- Docker 20.10+ & Docker Compose 2.0+
- Git
- 8GB RAM minimum, 16GB recommended
- Ports: 4002 (API), 5173 (frontend), 27017 (MongoDB), 6379 (Redis), 29092 (Kafka)

### Clone & Run
```bash
git clone https://github.com/mohamadsolkhannawawi/ai-gempa-bmkg.git
cd ai-gempa-bmkg
git checkout feature/architecture-refactor

# Start all services
docker-compose -f docker-compose.dev.yml up --build -d

# Check health
curl http://localhost:4002/health
curl http://localhost:5173

# View logs
docker-compose -f docker-compose.dev.yml logs -f api
```

### Services
- **API**: http://localhost:4002
- **Frontend**: http://localhost:5173  
- **MongoDB**: localhost:27017 (user: gempa, pass: gempa_dev_pass)
- **Redis**: localhost:6379
- **Kafka**: localhost:29092

---

## Architecture Overview

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Frontend   │─────▶│   API (v2)   │─────▶│   MongoDB    │
│  Vue 3 + TS  │      │  FastAPI     │      │   Profiles   │
└──────────────┘      └──────────────┘      │   Invoices   │
                             │               └──────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │    Redis     │
                      │  (cache +    │
                      │   metering)  │
                      └──────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │    Kafka     │
                      │ (metering    │
                      │  events)     │
                      └──────────────┘
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
          ┌─────────────┐        ┌─────────────┐
          │  Metering   │        │   Billing   │
          │   Worker    │        │   Worker    │
          └─────────────┘        └─────────────┘
```

---

## Project Structure

```
ai-gempa-bmkg/
├── sispro-tews/                  # Backend (Python)
│   ├── api/                      # FastAPI routes (v2)
│   ├── catalog_module/           # Provider registry
│   ├── profile_module/           # Compute profiles
│   ├── pricing_module/           # Usage tracking
│   ├── billing_module/           # Invoice generation
│   ├── metering_module/          # Kafka consumer
│   ├── providers/                # AI provider adapters
│   │   ├── p_pick/               # STALTA, PhaseNet, EQTransformer
│   │   ├── association/          # DBSCAN, GaMMA
│   │   └── locmag/               # PyOcto, Geiger, NonLinLoc
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── e2e/
│
├── frontend/                     # Frontend (Vue 3 + TypeScript)
│   ├── src/
│   │   ├── stores/               # Pinia state management
│   │   ├── services/             # API clients
│   │   ├── components/           # Vue components
│   │   ├── views/                # Page views
│   │   └── router/               # Vue Router
│   └── package.json
│
├── docs/
│   ├── API_DOCUMENTATION_v2.md   # API reference
│   └── CODEBASE_ANALYSIS.md      # Architecture deep dive
│
├── development/
│   ├── DEVELOPMENT_PLANNING_AI_GEMPA.md  # Phase tracking
│   └── HERMES_PROMPT_AI_GEMPA.md         # Implementation spec
│
├── Dockerfile                    # API image
├── Dockerfile.metering           # Metering worker
├── Dockerfile.billing            # Billing worker
└── docker-compose.dev.yml        # Full stack
```

---

## Environment Variables

Create `.env` file:

```bash
# MongoDB
MONGODB_URI=mongodb://gempa:gempa_dev_pass@mongodb:27017/gempa?authSource=admin

# Redis
REDIS_URL=redis://redis:6379/0

# Kafka
KAFKA_BROKERS=kafka:9092

# API
API_HOST=0.0.0.0
API_PORT=4002
ENVIRONMENT=development
LOG_LEVEL=debug

# SMTP (for billing emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# Frontend
VITE_API_BASE_URL=http://localhost:4002/api/v2
```

---

## Testing

### Unit Tests
```bash
cd sispro-tews
pytest tests/unit/ -v
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### E2E Tests (requires running stack)
```bash
docker-compose -f docker-compose.dev.yml up -d
pytest tests/e2e/ -v -s
```

### Frontend Tests
```bash
cd frontend
npm install
npm run test
```

---

## Development Workflow

### Backend Changes
```bash
# Edit code in sispro-tews/
# Restart API container
docker-compose -f docker-compose.dev.yml restart api

# View logs
docker-compose -f docker-compose.dev.yml logs -f api
```

### Frontend Changes
```bash
cd frontend
npm run dev  # Hot reload on http://localhost:5173
```

### Database Migrations
```bash
# Connect to MongoDB
docker exec -it gempa-mongodb-dev mongosh -u gempa -p gempa_dev_pass

# Run migration scripts (future)
python sispro-tews/migrations/001_initial_schema.py
```

---

## Production Deployment

### Prerequisites
- Server: Ubuntu 22.04, 16GB RAM, 4 vCPU
- Docker + Docker Compose installed
- Domain with SSL cert (Let's Encrypt)
- SMTP credentials (Gmail, SendGrid, Mailgun)

### Steps
1. Clone repo on server
2. Copy `.env.production` from `.env.example`
3. Configure reverse proxy (Nginx/Caddy)
4. Start services:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```
5. Verify health: `curl https://your-domain.com/health`
6. Setup cron for billing worker:
   ```cron
   0 0 1 * * cd /app && docker-compose exec billing python -m billing_module.cron
   ```

### SSL Setup (Caddy)
```
api.your-domain.com {
    reverse_proxy localhost:4002
}

app.your-domain.com {
    reverse_proxy localhost:5173
}
```

---

## Monitoring

### Health Checks
```bash
# API health
curl http://localhost:4002/health

# MongoDB
docker exec gempa-mongodb-dev mongosh --eval "db.adminCommand('ping')"

# Redis
docker exec gempa-redis-dev redis-cli ping

# Kafka topics
docker exec gempa-kafka-dev kafka-topics --list --bootstrap-server localhost:9092
```

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f metering
docker-compose logs -f billing
```

### Metrics (Future)
- Prometheus + Grafana
- Sentry error tracking
- DataDog APM

---

## Troubleshooting

### Port conflicts
```bash
# Check ports
lsof -i :4002
lsof -i :5173

# Kill conflicting process
kill -9 <PID>
```

### MongoDB connection failed
```bash
# Verify MongoDB running
docker ps | grep mongodb

# Check logs
docker logs gempa-mongodb-dev

# Restart
docker-compose restart mongodb
```

### Kafka consumer lag
```bash
# Check consumer groups
docker exec gempa-kafka-dev kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group metering-consumer
```

### Frontend build fails
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## API Documentation

See [API_DOCUMENTATION_v2.md](docs/API_DOCUMENTATION_v2.md) for full endpoint reference.

**Key endpoints:**
- `POST /api/v2/profiles` — Create compute profile
- `GET /api/v2/catalog` — List AI providers
- `GET /api/v2/pricing/invoices` — Get invoices
- `GET /api/v2/pricing/usage-statement` — Usage report

---

## Pricing (IDR per inference)

| Provider       | Module      | CPU  | GPU  |
|----------------|-------------|------|------|
| STALTA         | p_pick      | 5    | -    |
| PhaseNet       | p_pick      | 10   | 15   |
| EQTransformer  | p_pick      | -    | 20   |
| DBSCAN         | association | 20   | -    |
| GaMMA          | association | 25   | 30   |
| PyOcto         | locmag      | 100  | -    |
| Geiger         | locmag      | 80   | -    |
| NonLinLoc      | locmag      | 120  | -    |

Tax: 11% PPN added to all invoices.

---

## Support

- GitHub Issues: https://github.com/mohamadsolkhannawawi/ai-gempa-bmkg/issues
- Email: support@bmkg.go.id
- Docs: [development/HERMES_PROMPT_AI_GEMPA.md](development/HERMES_PROMPT_AI_GEMPA.md)

---

## License

Internal BMKG project. Not for public distribution.
