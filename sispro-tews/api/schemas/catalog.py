"""
api/schemas/catalog.py - Pydantic schemas untuk catalog API.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal


class ProviderSchema(BaseModel):
    """Provider manifest schema."""
    id: str = Field(..., description="Provider unique ID (sta_lta, phasenet, ...)")
    name: str = Field(..., description="Provider display name")
    description: str
    stage: str = Field(..., description="p_pick | association | locmag")
    tier: str = Field(..., description="CPU | GPU_BASIC | GPU_PREMIUM")
    repo: str
    supported_channels: List[str]
    min_sample_rate: float
    max_sample_rate: float
    input_shape: str
    output_format: str
    docker_image: str
    health_check_url: str
    status: str = Field(..., description="active | deprecated | experimental")
    tags: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "sta_lta",
                "name": "STA/LTA P‑Pick",
                "description": "Short‑Term Average / Long‑Term Average — klasik, CPU‑only, real‑time",
                "stage": "p_pick",
                "tier": "CPU",
                "repo": "https://github.com/BMKG‑seismo/sta‑lta‑gempa",
                "supported_channels": ["BHZ", "BHN", "BHE"],
                "min_sample_rate": 20.0,
                "max_sample_rate": 100.0,
                "status": "active",
                "tags": ["classic", "cpu", "real‑time"]
            }
        }


class ProviderRateSchema(BaseModel):
    """Provider rate schema."""
    provider: str
    tier: str
    price_per_1k_units: Decimal = Field(..., description="Rp per 1K units (picks/clusters/events)")
    free_quota_monthly: int = Field(..., description="Free units per month")
    description: str
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
        json_schema_extra = {
            "example": {
                "provider": "phasenet",
                "tier": "GPU_BASIC",
                "price_per_1k_units": 500,
                "free_quota_monthly": 2000,
                "description": "PhaseNet deep-learning, GPU basic"
            }
        }


class CatalogListResponse(BaseModel):
    """Response untuk GET /api/v2/models."""
    providers: List[ProviderSchema]
    stages: dict = Field(..., description="Providers grouped by stage")
    count: int


class CatalogFilterRequest(BaseModel):
    """Request filter untuk model catalog."""
    stage: Optional[str] = Field(None, description="p_pick | association | locmag")
    tier: Optional[str] = Field(None, description="CPU | GPU_BASIC | GPU_PREMIUM")
    status: Optional[str] = Field(None, description="active | deprecated | experimental")


class CostEstimateRequest(BaseModel):
    """Request untuk cost estimation."""
    provider_id: str
    units: int = Field(..., gt=0, description="Number of units (picks/clusters/events)")
    free_quota: int = Field(0, ge=0)


class CostEstimateResponse(BaseModel):
    """Response cost estimation."""
    provider_id: str
    units: int
    billable_units: int
    price_per_1k_units: Decimal
    estimated_cost_idr: Decimal
    tax_11_percent: Decimal
    total_cost_idr: Decimal
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
