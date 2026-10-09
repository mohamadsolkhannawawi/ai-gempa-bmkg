# Deployment Guide - AI-GEMPA-BMKG

## Initial Deployment

### 1. Setup Admin Credentials

Before first deployment, create `.env.seed` file in project root:

```bash
cd ~/GEMPA/ai-gempa-bmkg
cp .env.seed.example .env.seed
nano .env.seed
```

Edit credentials:
```env
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=Bmkg2026
INITIAL_ADMIN_EMAIL=admin@bmkg.go.id
```

**Security**: `.env.seed` is git-ignored. Keep secure, do NOT commit.

### 2. Deploy Wrapper

```bash
docker-compose -f docker-compose.wrapper.yml up -d --build
```

Seed script runs automatically via `controller_module/entrypoint.sh`.

### 3. Verify Admin User

```bash
docker exec -it requirements_mongodb_1 mongo --quiet sispro-tews --eval '
  db.user.findOne({username: "admin"})
'
```

Expected: Document with `username: "admin"`, `role: "superadmin"`, `password: "$pbkdf2-sha256$..."`.

### 4. Login

Frontend: http://SERVER_IP:8006
- Username: `admin`
- Password: (from `.env.seed`)

Change password immediately after first login.

## Troubleshooting

### Admin User Missing

If user deleted or lost:

**Option A: Rebuild controller** (auto-runs seed script):
```bash
docker exec -it gempa-dind-wrapper bash
export DOCKER_API_VERSION=1.41
cd /app/sispro-tews
docker-compose build --no-cache controller_module
docker-compose up -d controller_module
```

Seed script checks: if user exists → update password; if not → create user.

**Option B: Manual seed** (without rebuild):
```bash
docker exec -it gempa-dind-wrapper bash
export DOCKER_API_VERSION=1.41

# Export env vars from host .env.seed (if wrapper already has them)
docker exec \
  -e INITIAL_ADMIN_USERNAME=admin \
  -e INITIAL_ADMIN_PASSWORD=Bmkg2026 \
  -e INITIAL_ADMIN_EMAIL=admin@bmkg.go.id \
  -e INITIAL_ADMIN_FULLNAME="Administrator BMKG" \
  -e INITIAL_ADMIN_REGION="Indonesia" \
  -e MONGO_HOST=mongodb \
  -e MONGO_PORT=27017 \
  -e MONGO_DB_NAME=sispro-tews \
  requirements_controller_module_1 \
  python3 /app/seed_admin_user.py
```

### Wrong Password Hash

Seed script and login both use `pbkdf2_sha256` via passlib. If login fails:
- Verify `.env.seed` password matches login attempt
- Rebuild controller to refresh hash

### Seed Script Fails

Check logs:
```bash
docker exec -it gempa-dind-wrapper bash
docker-compose logs controller_module | grep -E 'SEED|ERROR|admin'
```

Common causes:
- MongoDB not ready (retry logic handles this)
- Missing env vars (wrapper must export from `.env.seed`)
- Collection name mismatch (script uses `user`, not `users`)

## Architecture

**Hash**: `pbkdf2_sha256` (passlib)
**Collection**: `sispro-tews.user`
**Seed script**: `sispro-tews/controller_module/seed_admin_user.py`
**Entrypoint**: `sispro-tews/controller_module/entrypoint.sh` (runs seed before app start)
**Env source**: `docker-compose.wrapper.yml` → `.env.seed` → controller container

Seed is **idempotent**: safe to run multiple times.
