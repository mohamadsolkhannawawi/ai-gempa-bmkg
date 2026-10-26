"""
api/routes/catalog.py - FastAPI router untuk catalog endpoints.

GET /api/v2/models — list semua providers
POST /api/v2/models/estimate-cost — estimate biaya untuk N units
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from pathlib import Path

from api.schemas.catalog import (
    CatalogListResponse, CatalogFilterRequest, ProviderSchema, ProviderRateSchema,
    CostEstimateRequest, CostEstimateResponse
)
from catalog_module.catalog import ProviderCatalog
from decimal import Decimal

router = APIRouter(prefix="/api/v2", tags=["catalog"])

# Lazy-load catalog singleton
_catalog = None

def get_catalog() -> ProviderCatalog:
    global _catalog
    if _catalog is None:
        # Default: sispro-tews/catalog_module/data/
        data_dir = Path(__file__).parent.parent.parent / "catalog_module" / "data"
        _catalog = ProviderCatalog(data_dir)
    return _catalog


@router.get("/models", response_model=CatalogListResponse)
async def list_models(
    stage: Optional[str] = Query(None, description="p_pick | association | locmag"),
    tier: Optional[str] = Query(None, description="CPU | GPU_BASIC | GPU_PREMIUM"),
    status: Optional[str] = Query(None, description="active | deprecated")
):
    """
    List semua AI providers dalam katalog.
    
    Query params:
    - stage: filter by pipeline stage
    - tier: filter by compute tier
    - status: filter by status (active/deprecated)
    
    Response: list provider manifests + metadata.
    """
    catalog = get_catalog()
    
    # Filter
    providers = catalog.list_providers(stage=stage, tier=tier)
    
    if status:
        providers = [p for p in providers if p.status == status]
    
    # Convert to schema
    provider_schemas = [
        ProviderSchema(
            id=p.id,
            name=p.name,
            description=p.description,
            stage=p.stage,
            tier=p.tier,
            repo=p.repo,
            supported_channels=p.supported_channels,
            min_sample_rate=p.min_sample_rate,
            max_sample_rate=p.max_sample_rate,
            input_shape=p.input_shape,
            output_format=p.output_format,
            docker_image=p.docker_image,
            health_check_url=p.health_check_url,
            status=p.status,
            tags=p.tags
        )
        for p in providers
    ]
    
    # Group by stage
    stages_dict = catalog.list_by_stage()
    stages = {
        stage: [p.id for p in stage_providers]
        for stage, stage_providers in stages_dict.items()
    }
    
    return CatalogListResponse(
        providers=provider_schemas,
        stages=stages,
        count=len(provider_schemas)
    )


@router.get("/models/{provider_id}", response_model=ProviderSchema)
async def get_model(provider_id: str):
    """Get single provider by ID."""
    catalog = get_catalog()
    provider = catalog.get_provider(provider_id)
    
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")
    
    return ProviderSchema(
        id=provider.id,
        name=provider.name,
        description=provider.description,
        stage=provider.stage,
        tier=provider.tier,
        repo=provider.repo,
        supported_channels=provider.supported_channels,
        min_sample_rate=provider.min_sample_rate,
        max_sample_rate=provider.max_sample_rate,
        input_shape=provider.input_shape,
        output_format=provider.output_format,
        docker_image=provider.docker_image,
        health_check_url=provider.health_check_url,
        status=provider.status,
        tags=provider.tags
    )


@router.get("/models/{provider_id}/rate", response_model=ProviderRateSchema)
async def get_model_rate(provider_id: str):
    """Get pricing rate for provider."""
    catalog = get_catalog()
    rate = catalog.get_rate(provider_id)
    
    if not rate:
        raise HTTPException(status_code=404, detail=f"Rate for {provider_id} not found")
    
    return ProviderRateSchema(
        provider=rate.provider,
        tier=rate.tier,
        price_per_1k_units=rate.price_per_1k_units,
        free_quota_monthly=rate.free_quota_monthly,
        description=rate.description
    )


@router.post("/models/estimate-cost", response_model=CostEstimateResponse)
async def estimate_cost(request: CostEstimateRequest):
    """
    Estimate biaya untuk N units (picks/clusters/events).
    
    Payload:
    ```json
    {
      "provider_id": "phasenet",
      "units": 50000,
      "free_quota": 2000
    }
    ```
    
    Response: cost breakdown dengan PPN 11%.
    """
    catalog = get_catalog()
    provider = catalog.get_provider(request.provider_id)
    
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider {request.provider_id} not found")
    
    # Calculate cost
    cost_before_tax = catalog.estimate_cost(
        request.provider_id,
        request.units,
        free_quota=request.free_quota
    )
    
    billable = max(0, request.units - request.free_quota)
    rate = catalog.get_rate(request.provider_id)
    price_per_1k = rate.price_per_1k_units if rate else Decimal("0")
    
    tax = cost_before_tax * Decimal("0.11")  # 11% PPN
    total = cost_before_tax + tax
    
    return CostEstimateResponse(
        provider_id=request.provider_id,
        units=request.units,
        billable_units=billable,
        price_per_1k_units=price_per_1k,
        estimated_cost_idr=cost_before_tax,
        tax_11_percent=tax.quantize(Decimal("0.01")),
        total_cost_idr=total.quantize(Decimal("0.01"))
    )


@router.get("/health/catalog")
async def health_check():
    """Health check untuk catalog service."""
    try:
        catalog = get_catalog()
        return {
            "status": "healthy",
            "providers_count": len(catalog.providers),
            "rates_count": len(catalog.rates)
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Catalog service error: {e}")
