"""
api/schemas/profile.py - Pydantic schemas untuk profile API.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime


class ProviderConfigSchema(BaseModel):
    """Provider config schema."""
    provider_id: str = Field(..., description="sta_lta, phasenet, dbscan, gamma, etc.")
    tier: str = Field(..., description="CPU, GPU_BASIC, GPU_PREMIUM")
    enabled: bool = True
    custom_params: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "phasenet",
                "tier": "GPU_BASIC",
                "enabled": True,
                "custom_params": {"threshold": 0.3}
            }
        }


class PipelinePreferencesSchema(BaseModel):
    """Pipeline preferences schema."""
    sample_rate: float = Field(50.0, ge=20, le=100, description="Hz")
    channels: List[str] = Field(["BHZ", "BHN", "BHE"], min_items=1)
    min_magnitude: Decimal = Field(Decimal("2.0"), description="Magnitude threshold")
    p_pick_sensitivity: str = Field("normal", description="low | normal | high")
    association_distance_km: float = Field(20.0, ge=5, le=100)
    locmag_depth_constraint: Optional[float] = None
    auto_publish_events: bool = False
    webhook_url: Optional[str] = None
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
        json_schema_extra = {
            "example": {
                "sample_rate": 50.0,
                "channels": ["BHZ", "BHN", "BHE"],
                "min_magnitude": 2.0,
                "p_pick_sensitivity": "normal",
                "association_distance_km": 20.0
            }
        }


class ProfileCreateRequest(BaseModel):
    """Request untuk CREATE profile."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    p_pick_provider_id: str = Field("sta_lta")
    association_provider_id: str = Field("dbscan")
    locmag_provider_id: str = Field("geiger")
    preferences: Optional[PipelinePreferencesSchema] = None
    
    @validator("name")
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Profile name cannot be empty")
        return v.strip()


class ProfileUpdateRequest(BaseModel):
    """Request untuk UPDATE profile (DRAFT only)."""
    name: Optional[str] = None
    description: Optional[str] = None
    p_pick_provider_id: Optional[str] = None
    association_provider_id: Optional[str] = None
    locmag_provider_id: Optional[str] = None
    preferences: Optional[PipelinePreferencesSchema] = None


class ProfileSchema(BaseModel):
    """Full profile schema (response)."""
    id: str
    workspace_id: str
    name: str
    description: Optional[str]
    p_pick_config: ProviderConfigSchema
    association_config: ProviderConfigSchema
    locmag_config: ProviderConfigSchema
    preferences: PipelinePreferencesSchema
    status: str = Field(..., description="draft | active | archived")
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_by: str
    updated_by: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "prof_xyz",
                "workspace_id": "ws_001",
                "name": "Production Pipeline",
                "description": "Standard seismic processing",
                "status": "active",
                "created_by": "user_001",
                "updated_by": "user_001"
            }
        }


class ProfileListResponse(BaseModel):
    """Response untuk GET /api/v2/profiles."""
    profiles: List[ProfileSchema]
    count: int
    active_profile_id: Optional[str] = None


class ProfileActivateRequest(BaseModel):
    """Request untuk activate profile."""
    profile_id: str = Field(..., description="Profile ID to activate")


class ProfileArchiveRequest(BaseModel):
    """Request untuk archive profile."""
    profile_id: str = Field(..., description="Profile ID to archive")


class ProfileValidationResponse(BaseModel):
    """Response untuk profile validation."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ProfileCostEstimateResponse(BaseModel):
    """Response untuk cost estimation."""
    profile_id: str
    estimated_monthly_cost_idr: Decimal
    assumptions: Dict[str, Any] = Field(
        default_factory=lambda: {
            "picks_per_day": 10000,
            "clusters_per_day": 2000,
            "events_per_day": 1000
        }
    )
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
