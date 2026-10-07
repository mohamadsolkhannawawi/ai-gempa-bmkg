# GEMPA AI-TEWS Secure Deployment Guide

## Ringkasan Perubahan

Best practice security untuk admin credential seeding:
- ✓ Credentials dari environment variables (bukan hardcoded)
- ✓ Auto-seed pada container startup
- ✓ One-command deployment via wrapper
- ✓ No password exposure di logs
- ✓ Validation di entrypoint
- ✓ Health check setelah deployment

## Prerequisites

1. Server: Ubuntu 22.04 dengan Docker & Docker Compose
2. Ports tersedia: 8000-8007, 32717, 36379, 39092, 32181
3. Volume mount: `/mnt/archive` untuk data seismik
4. GPU (optional): NVIDIA dengan CUDA 11.8+

## Setup Credentials (WAJIB)

### 1. Copy Template Env File

```bash
cd /path/to/ai-gempa-bmkg
cp .env.seed.example .env.seed
```

### 2. Edit Credentials

```bash
# Edit dengan editor favorit
nano .env.seed

# Atau gunakan password generator
SECURE_PASSWORD=$(openssl rand -base64 24)
sed -i "s/ChangeMe123!SecurePassword/$SECURE_PASSWORD/" .env.seed
```

**Minimal yang WAJIB diubah:**
```bash
INITIAL_ADMIN_USERNAME=admin                    # Username admin
INITIAL_ADMIN_PASSWORD=YourSecurePassword123!   # MIN 8 chars, gunakan strong password
INITIAL_ADMIN_EMAIL=admin@bmkg.go.id           # Email admin
```

### 3. Set Permissions (Keamanan)

```bash
chmod 600 .env.seed
```

Jangan commit `.env.seed` ke git (sudah di `.gitignore`)

## Deployment

### One-Command Deploy (Recommended)

```bash
# Build dan start semua services
docker-compose -f docker-compose.wrapper.yml up -d --build

# Monitor logs
docker logs -f gempa-dind-wrapper
```

**Proses otomatis:**
1. Validate credentials dari `.env.seed`
2. Start infrastructure (MongoDB, Kafka, Redis, Zookeeper)
3. Start backend services
4. **Auto-seed admin user** (dari env vars)
5. Start AI modules
6. Start frontend
7. Health check

### Verifikasi Deployment

```bash
# Check semua container running
docker exec gempa-dind-wrapper docker ps

# Verify admin user berhasil di-seed
docker exec gempa-dind-wrapper docker exec requirements_mongodb_1 \
  mongo sispro-tews --eval 'db.user.findOne({username: "admin"})'
```

Expected output: JSON dengan `_id`, `username: "admin"`, `role: "superadmin"`

### Access Application

- **Frontend:** http://152.118.31.54:8006
- **Controller API:** http://152.118.31.54:8003
- **MongoDB:** `152.118.31.54:32717`

Login dengan credentials dari `.env.seed`:
- Username: `INITIAL_ADMIN_USERNAME`
- Password: `INITIAL_ADMIN_PASSWORD`

⚠️ **WAJIB:** Ganti password setelah first login via UI

## Troubleshooting

### Admin User Tidak Bisa Login

```bash
# Check apakah user exist
docker exec gempa-dind-wrapper docker exec requirements_mongodb_1 \
  mongo sispro-tews --eval 'db.user.findOne({username: "admin"})'

# Re-run seed manual (jika perlu)
docker exec gempa-dind-wrapper docker exec sispro-tews_controller_module_1 \
  python3 /app/seed_admin_user.py
```

### Environment Variables Not Loaded

```bash
# Check env di controller container
docker exec gempa-dind-wrapper docker exec sispro-tews_controller_module_1 \
  env | grep INITIAL_ADMIN

# Jika kosong, check .env.seed di host
cat .env.seed
```

### MongoDB Connection Failed

```bash
# Check MongoDB running
docker exec gempa-dind-wrapper docker exec requirements_mongodb_1 \
  mongo --eval 'db.adminCommand("ping")'

# Check MongoDB logs
docker exec gempa-dind-wrapper docker logs requirements_mongodb_1
```

### Port Already in Use

```bash
# Check port conflicts
netstat -tulpn | grep -E "8006|32717|36379|39092"

# Stop conflicting services atau ubah port mapping di docker-compose.wrapper.yml
```

## Security Best Practices

### ✓ Implemented

1. **Credentials dari env** (bukan hardcoded)
2. **Auto-validation** di entrypoint (password min 8 chars)
3. **No password di logs** (hanya hash tersimpan)
4. **File permissions** (`.env.seed` dengan chmod 600)
5. **Git ignore** (credentials tidak ter-commit)

### 🔒 Recommended Post-Deployment

1. **Change admin password** via UI setelah first login
2. **Enable HTTPS** dengan reverse proxy (nginx + Let's Encrypt)
3. **Firewall rules** untuk limit akses dari IP internal saja
4. **Backup MongoDB** secara berkala
5. **Rotate credentials** setiap 90 hari

```bash
# Example: Setup firewall (UFW)
ufw allow from 192.168.0.0/16 to any port 8006
ufw allow from 192.168.0.0/16 to any port 8003
ufw deny 8006
ufw deny 8003
```

## Architecture Flow

```
.env.seed (host)
    ↓
docker-compose.wrapper.yml
    ↓ env_file: .env.seed
gempa-dind-wrapper container
    ↓ export env vars
entrypoint-wrapper.sh
    ↓ docker-compose up
sispro-tews/docker-compose.yml
    ↓ environment: ${INITIAL_ADMIN_*}
controller_module container
    ↓ entrypoint.sh
seed_admin_user.py (reads os.getenv)
    ↓
MongoDB: user collection
```

## Files Modified

```
Modified:
- sispro-tews/controller_module/seed_admin_user.py      # Env-based seeding
- sispro-tews/controller_module/Dockerfile              # Add entrypoint
- sispro-tews/docker-compose.yml                        # Pass env to controller
- docker-compose.wrapper.yml                            # Load .env.seed
- entrypoint-wrapper.sh                                 # Validate & export credentials
- DEPLOYMENT_GUIDE.md                                   # Update admin setup section

Created:
- sispro-tews/controller_module/entrypoint.sh           # Seed before app start
- .env.seed.example                                     # Template credentials
- .gitignore                                            # Protect credentials
- SECURE_DEPLOYMENT.md                                  # This guide
```

## Rollback (jika diperlukan)

```bash
# Stop services
docker-compose -f docker-compose.wrapper.yml down

# Restore old seed script (if needed)
git checkout HEAD -- sispro-tews/controller_module/seed_admin_user.py

# Redeploy
docker-compose -f docker-compose.wrapper.yml up -d --build
```

## Support

Dokumentasi lengkap: `DEPLOYMENT_GUIDE.md`

Issues: Contact BMKG DevOps team
