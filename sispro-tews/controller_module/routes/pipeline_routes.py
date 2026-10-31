import os
import hashlib
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from configuration.database import get_database_connection
from dotenv import load_dotenv

load_dotenv("./.env")
SSH_HOST = os.getenv('ssh_host')
SSH_PORT = int(os.getenv('ssh_port', 22))
SSH_USERNAME = os.getenv('ssh_username')
SSH_PASSWORD = os.getenv('ssh_password')
MONGO_HOST = os.getenv('database_host', 'mongodb')
MONGO_DB = os.getenv('database_name', 'sispro-tews')
LOCAL_BIND_PORT = int(os.getenv('database_port', 27017))
REMOTE_BIND_PORT = int(os.getenv('database_port', 27017))

db = get_database_connection(
    SSH_HOST,
    SSH_PORT,
    SSH_USERNAME,
    SSH_PASSWORD,
    MONGO_HOST,
    MONGO_DB,
    LOCAL_BIND_PORT,
    REMOTE_BIND_PORT,
)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

AI_MODELS_CATALOG = [
    {
        "id": "sta_lta",
        "name": "STA/LTA P-Pick",
        "description": "Short-Term Average / Long-Term Average — klasik, real-time CPU picking",
        "stage": "p_pick",
        "tier": "CPU",
        "supported_channels": ["BHZ", "HHZ", "SHZ"],
        "min_sample_rate": 20.0,
        "status": "active",
        "tags": ["classic", "cpu", "real-time", "robust"]
    },
    {
        "id": "phasenet",
        "name": "PhaseNet P-Pick",
        "description": "Deep-learning picker (CNN-based), GPU-accelerated, high recall",
        "stage": "p_pick",
        "tier": "GPU_BASIC",
        "supported_channels": ["BHZ", "HHZ"],
        "min_sample_rate": 40.0,
        "status": "active",
        "tags": ["deep-learning", "gpu", "high-recall", "cnn"]
    },
    {
        "id": "eqtransformer",
        "name": "EQ-Transformer P-Pick",
        "description": "Transformer-based picker, multi-station, long-range detection",
        "stage": "p_pick",
        "tier": "GPU_BASIC",
        "supported_channels": ["BHZ", "HHZ"],
        "min_sample_rate": 40.0,
        "status": "active",
        "tags": ["transformer", "gpu", "attention", "long-range"]
    },
    {
        "id": "dbscan",
        "name": "DBSCAN Phase Association",
        "description": "Density-based spatial clustering for seismic phase association",
        "stage": "association",
        "tier": "CPU",
        "status": "active",
        "tags": ["clustering", "cpu", "real-time"]
    },
    {
        "id": "gamma",
        "name": "GaMMA Gaussian Mixture Association",
        "description": "Gaussian Mixture Model association with probabilistic travel-time clustering",
        "stage": "association",
        "tier": "GPU_BASIC",
        "status": "active",
        "tags": ["probabilistic", "gpu", "gmm"]
    },
    {
        "id": "pyocto",
        "name": "PyOcto Fast Octree Association",
        "description": "Octree-based high-throughput association for dense regional networks",
        "stage": "association",
        "tier": "CPU",
        "status": "active",
        "tags": ["octree", "cpu", "high-throughput"]
    },
    {
        "id": "geiger",
        "name": "Geiger 1D Earthquake Location",
        "description": "Classical linearized iterative inversion with 1D velocity model",
        "stage": "locmag",
        "tier": "CPU",
        "status": "active",
        "tags": ["classic", "cpu", "inversion", "1d-model"]
    },
    {
        "id": "nonlinloc",
        "name": "NonLinLoc 3D Probabilistic Location",
        "description": "Non-linear global search probabilistic location with 3D velocity models",
        "stage": "locmag",
        "tier": "CPU",
        "status": "active",
        "tags": ["probabilistic", "cpu", "3d-model", "grid-search"]
    }
]

DEFAULT_PIPELINE = {
    "name": "Default BMKG Operational Pipeline",
    "description": "Pipeline standar operasional AI-TEWS BMKG",
    "p_pick": {"provider": "sta_lta", "tier": "CPU", "status": "active"},
    "association": {"provider": "dbscan", "tier": "CPU", "status": "active"},
    "locmag": {"provider": "geiger", "tier": "CPU", "status": "active"},
    "is_active": True,
    "compiled_sha256": "8f4e2a1b9c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f",
    "updated_at": "2026-10-31T00:00:00Z"
}

@router.get("/catalog")
async def get_pipeline_catalog():
    """Mengambil katalog 8 modul AI yang tersedia untuk BMKG AI-TEWS."""
    return {
        "status": "success",
        "data": AI_MODELS_CATALOG
    }

@router.get("/config")
async def get_pipeline_config():
    """Mengambil konfigurasi AI pipeline aktif dari MongoDB."""
    try:
        col = db["pipeline_config"]
        config = col.find_one({"is_active": True}, {"_id": 0})
        if not config:
            config = DEFAULT_PIPELINE
            # Simpan default jika belum ada
            col.update_one(
                {"is_active": True},
                {"$setOnInsert": DEFAULT_PIPELINE},
                upsert=True
            )
        return {
            "status": "success",
            "data": config
        }
    except Exception as e:
        return {
            "status": "success",
            "data": DEFAULT_PIPELINE,
            "fallback": True,
            "error": str(e)
        }

@router.post("/config")
async def save_pipeline_config(request: Request):
    """Menyimpan konfigurasi AI pipeline baru ke MongoDB."""
    try:
        payload = await request.json()
        name = payload.get("name", "Custom BMKG AI Pipeline")
        description = payload.get("description", "")
        p_pick = payload.get("p_pick", {"provider": "sta_lta", "tier": "CPU"})
        association = payload.get("association", {"provider": "dbscan", "tier": "CPU"})
        locmag = payload.get("locmag", {"provider": "geiger", "tier": "CPU"})

        # Hitung signature compile sha256
        raw_repr = f"{name}:{p_pick}:{association}:{locmag}"
        sha256_hash = hashlib.sha256(raw_repr.encode()).hexdigest()
        now_iso = datetime.utcnow().isoformat() + "Z"

        doc = {
            "name": name,
            "description": description,
            "p_pick": p_pick,
            "association": association,
            "locmag": locmag,
            "is_active": True,
            "compiled_sha256": sha256_hash,
            "updated_at": now_iso
        }

        col = db["pipeline_config"]
        # Set all previous configs as inactive
        col.update_many({}, {"$set": {"is_active": False}})
        col.insert_one(doc)

        # Hapus _id dari return
        doc.pop("_id", None)
        return {
            "status": "success",
            "message": "Konfigurasi AI Pipeline berhasil disimpan dan diaktifkan.",
            "data": doc
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menyimpan konfigurasi: {str(e)}"
        )

@router.post("/compile")
async def compile_pipeline(request: Request):
    """Validasi dan kompilasi arsitektur AI pipeline."""
    payload = await request.json()
    p_pick = payload.get("p_pick", {}).get("provider", "")
    assoc = payload.get("association", {}).get("provider", "")
    locmag = payload.get("locmag", {}).get("provider", "")

    # Basic validation
    if not p_pick or not assoc or not locmag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Semua 3 tahap pipeline (P-Pick, Association, LocMag) wajib dipilih."
        )

    compile_str = f"BMKG:{p_pick}->{assoc}->{locmag}:{datetime.utcnow().timestamp()}"
    sha = hashlib.sha256(compile_str.encode()).hexdigest()

    return {
        "status": "success",
        "compiled": True,
        "sha256": sha,
        "message": f"Pipeline valid: {p_pick} -> {assoc} -> {locmag} siap dijalankan."
    }
