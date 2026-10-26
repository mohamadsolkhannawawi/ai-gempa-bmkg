"""
api/routes/pricing.py - FastAPI router untuk pricing endpoints.

Endpoints:
1. POST /api/v2/pricing/estimate — estimate cost untuk usage
2. GET  /api/v2/pricing/rates — get current rates per provider
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from api.schemas.pricing import CostEstimateRequest, CostEstimateResponse
from core.pricing_service import PricingService, BillingPeriod, UsageRecord
from catalog_module.catalog import ProviderCatalog

router = APIRouter(prefix="/api/v2/pricing", tags=["pricing"])


def get_pricing_service() -> PricingService:
    """Inject PricingService."""
    # TODO: inject real catalog + repos
    return PricingService()


@router.post("/estimate", response_model=CostEstimateResponse)
async def estimate_cost(
    request: CostEstimateRequest,
    service: PricingService = Depends(get_pricing_service)
):
    """
    Estimate monthly/quarterly/annual cost untuk workspace.
    
    Jika custom_usage diberikan, pakai itu.
    Jika tidak, ambil historical average usage.
    """
    period = BillingPeriod(request.billing_period)
    
    custom_usage = None
    if request.custom_usage:
        custom_usage = UsageRecord(
            workspace_id=request.custom_usage.workspace_id,
            billing_period=period,
            period_start=request.custom_usage.period_start,
            period_end=request.custom_usage.period_end,
            picks_count=request.custom_usage.picks_count,
            clusters_count=request.custom_usage.clusters_count,
            events_count=request.custom_usage.events_count,
            inference_hours=request.custom_usage.inference_hours,
            storage_gb=request.custom_usage.storage_gb,
            sta_lta_picks=request.custom_usage.sta_lta_picks,
            phasenet_picks=request.custom_usage.phasenet_picks,
            eqtransformer_picks=request.custom_usage.eqtransformer_picks,
            dbscan_clusters=request.custom_usage.dbscan_clusters,
            gamma_clusters=request.custom_usage.gamma_clusters,
            geiger_events=request.custom_usage.geiger_events,
            pyocto_events=request.custom_usage.pyocto_events
        )
    
    estimate = service.estimate_cost(
        workspace_id=request.workspace_id,
        period=period,
        custom_usage=custom_usage
    )
    
    return CostEstimateResponse(**estimate)


@router.get("/rates")
async def get_rates():
    """
    Get current rates per provider (from catalog).
    
    Returns:
    {
      "picks": {
        "sta_lta": 5.0,
        "phasenet": 10.0,
        "eqtransformer": 12.0
      },
      "clusters": {
        "dbscan": 20.0,
        "gamma": 30.0
      },
      "events": {
        "geiger": 100.0,
        "pyocto": 120.0,
        "nonlinloc": 150.0
      },
      "compute": {
        "inference_hour_gpu_basic": 5000.0,
        "inference_hour_gpu_premium": 8000.0
      },
      "storage": {
        "gb_per_month": 1000.0
      },
      "currency": "IDR"
    }
    """
    # TODO: lookup from catalog_module/data/rates.yaml
    return {
        "picks": {
            "sta_lta": 5.0,
            "phasenet": 10.0,
            "eqtransformer": 12.0
        },
        "clusters": {
            "dbscan": 20.0,
            "gamma": 30.0
        },
        "events": {
            "geiger": 100.0,
            "pyocto": 120.0,
            "nonlinloc": 150.0
        },
        "compute": {
            "inference_hour_gpu_basic": 5000.0,
            "inference_hour_gpu_premium": 8000.0
        },
        "storage": {
            "gb_per_month": 1000.0
        },
        "currency": "IDR",
        "ppn_percent": 11.0,
        "effective_date": "2026-10-01"
    }


@router.get("/health/pricing")
async def health_check():
    """Health check untuk pricing service."""
    return {
        "status": "healthy",
        "service": "pricing"
    }
