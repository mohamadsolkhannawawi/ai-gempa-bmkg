"""
core/profile_service.py - ProfileService domain (business logic, tanpa framework).

Profile = konfigurasi pipeline per workspace:
  - p_pick provider (STA/LTA, PhaseNet, EQTransformer)
  - association provider (DBSCAN, GaMMA)
  - locmag provider (PyOcto, Geiger, NonLinLoc)
  - preferences (sample rate, channels, sensitivity)

Status tracking: DRAFT → ACTIVE → ARCHIVED
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4


class ProfileStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass
class ProviderConfig:
    """Konfigurasi provider untuk satu stage."""
    provider_id: str           # sta_lta, phasenet, dbscan, gamma, etc.
    tier: str                  # CPU, GPU_BASIC, GPU_PREMIUM
    enabled: bool = True
    custom_params: Dict[str, Any] = field(default_factory=dict)  # provider-specific settings
    
    def to_dict(self) -> Dict:
        return {
            "provider_id": self.provider_id,
            "tier": self.tier,
            "enabled": self.enabled,
            "custom_params": self.custom_params
        }


@dataclass
class PipelinePreferences:
    """Preferensi umum pipeline."""
    sample_rate: float = 100.0         # Hz, 20-100
    channels: List[str] = field(default_factory=lambda: ["BHZ", "BHN", "BHE"])
    min_magnitude: Decimal = Decimal("2.0")
    p_pick_sensitivity: str = "normal" # low, normal, high
    association_distance_km: float = 20.0
    locmag_depth_constraint: Optional[float] = None
    auto_publish_events: bool = False
    webhook_url: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "min_magnitude": str(self.min_magnitude),
            "p_pick_sensitivity": self.p_pick_sensitivity,
            "association_distance_km": self.association_distance_km,
            "locmag_depth_constraint": self.locmag_depth_constraint,
            "auto_publish_events": self.auto_publish_events,
            "webhook_url": self.webhook_url
        }


@dataclass
class Profile:
    """Pipeline configuration per workspace."""
    id: str = field(default_factory=lambda: str(uuid4()))
    workspace_id: str = ""
    name: str = ""
    description: str = ""
    
    # Provider chain
    p_pick_config: ProviderConfig = field(default_factory=lambda: ProviderConfig("sta_lta", "CPU"))
    association_config: ProviderConfig = field(default_factory=lambda: ProviderConfig("dbscan", "CPU"))
    locmag_config: ProviderConfig = field(default_factory=lambda: ProviderConfig("geiger", "CPU"))
    
    # Preferences
    preferences: PipelinePreferences = field(default_factory=PipelinePreferences)
    
    # Metadata
    status: ProfileStatus = ProfileStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    activated_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    
    # Audit
    created_by: str = ""
    updated_by: str = ""
    
    def to_dict(self) -> Dict:
        """Serialize untuk MongoDB."""
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "p_pick_config": self.p_pick_config.to_dict(),
            "association_config": self.association_config.to_dict(),
            "locmag_config": self.locmag_config.to_dict(),
            "preferences": self.preferences.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> Profile:
        """Deserialize dari MongoDB."""
        return cls(
            id=data.get("id", str(uuid4())),
            workspace_id=data.get("workspace_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            p_pick_config=ProviderConfig(**data.get("p_pick_config", {})),
            association_config=ProviderConfig(**data.get("association_config", {})),
            locmag_config=ProviderConfig(**data.get("locmag_config", {})),
            preferences=PipelinePreferences(**data.get("preferences", {})),
            status=ProfileStatus(data.get("status", "draft")),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(timezone.utc).isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now(timezone.utc).isoformat())),
            activated_at=datetime.fromisoformat(data["activated_at"]) if data.get("activated_at") else None,
            archived_at=datetime.fromisoformat(data["archived_at"]) if data.get("archived_at") else None,
            created_by=data.get("created_by", ""),
            updated_by=data.get("updated_by", "")
        )


class ProfileService:
    """Business logic untuk profile management."""
    
    def __init__(self, repository=None):
        self.repository = repository  # injected, akan di-implement di infrastructure layer
    
    def create_profile(
        self,
        workspace_id: str,
        name: str,
        description: str,
        created_by: str,
        p_pick_provider_id: str = "sta_lta",
        association_provider_id: str = "dbscan",
        locmag_provider_id: str = "geiger",
        preferences: Optional[Dict] = None
    ) -> Profile:
        """Create new profile (DRAFT status)."""
        profile = Profile(
            workspace_id=workspace_id,
            name=name,
            description=description,
            status=ProfileStatus.DRAFT,
            created_by=created_by,
            updated_by=created_by
        )
        
        # Set providers
        profile.p_pick_config.provider_id = p_pick_provider_id
        profile.association_config.provider_id = association_provider_id
        profile.locmag_config.provider_id = locmag_provider_id
        
        # Set preferences jika provided
        if preferences:
            for key, value in preferences.items():
                if hasattr(profile.preferences, key):
                    setattr(profile.preferences, key, value)
        
        return profile
    
    def activate_profile(self, profile: Profile, updated_by: str) -> Profile:
        """Transition DRAFT → ACTIVE (only one active per workspace)."""
        if profile.status != ProfileStatus.DRAFT:
            raise ValueError(f"Cannot activate profile with status {profile.status}")
        
        profile.status = ProfileStatus.ACTIVE
        profile.activated_at = datetime.now(timezone.utc)
        profile.updated_at = datetime.now(timezone.utc)
        profile.updated_by = updated_by
        
        # Deactivate sibling profiles dalam workspace yg sama
        # TODO: repository.deactivate_other_profiles(profile.workspace_id, profile.id)
        
        return profile
    
    def update_profile(
        self,
        profile: Profile,
        updated_by: str,
        **kwargs
    ) -> Profile:
        """Update profile properties (only if DRAFT)."""
        if profile.status != ProfileStatus.DRAFT:
            raise ValueError(f"Cannot update profile with status {profile.status}")
        
        allowed_fields = {
            "name", "description",
            "p_pick_provider_id", "association_provider_id", "locmag_provider_id",
            "sample_rate", "channels", "min_magnitude", "p_pick_sensitivity"
        }
        
        for key, value in kwargs.items():
            if key not in allowed_fields:
                continue
            
            if key == "p_pick_provider_id":
                profile.p_pick_config.provider_id = value
            elif key == "association_provider_id":
                profile.association_config.provider_id = value
            elif key == "locmag_provider_id":
                profile.locmag_config.provider_id = value
            elif hasattr(profile.preferences, key):
                setattr(profile.preferences, key, value)
            else:
                setattr(profile, key, value)
        
        profile.updated_at = datetime.now(timezone.utc)
        profile.updated_by = updated_by
        
        return profile
    
    def archive_profile(self, profile: Profile, updated_by: str) -> Profile:
        """Archive profile (DRAFT/ACTIVE → ARCHIVED)."""
        if profile.status == ProfileStatus.ARCHIVED:
            raise ValueError("Profile already archived")
        
        profile.status = ProfileStatus.ARCHIVED
        profile.archived_at = datetime.now(timezone.utc)
        profile.updated_at = datetime.now(timezone.utc)
        profile.updated_by = updated_by
        
        return profile
    
    def validate_profile(self, profile: Profile) -> tuple[bool, str]:
        """Validate profile sebelum activate."""
        errors = []
        
        if not profile.name:
            errors.append("Profile name required")
        
        if not profile.p_pick_config.provider_id:
            errors.append("P-pick provider required")
        
        if not profile.association_config.provider_id:
            errors.append("Association provider required")
        
        if not profile.locmag_config.provider_id:
            errors.append("Locmag provider required")
        
        if profile.preferences.sample_rate < 20 or profile.preferences.sample_rate > 100:
            errors.append("Sample rate must be 20-100 Hz")
        
        if len(profile.preferences.channels) == 0:
            errors.append("At least one channel required")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, "OK"
    
    def estimate_monthly_cost(self, profile: Profile) -> Decimal:
        """
        Estimate monthly cost untuk profile ini.
        Assumption: average 10K picks/day, 2K clusters/day, 1K events/day.
        """
        daily_picks = 10000
        daily_clusters = 2000
        daily_events = 1000
        
        monthly_picks = daily_picks * 30
        monthly_clusters = daily_clusters * 30
        monthly_events = daily_events * 30
        
        # TODO: lookup rates dari catalog + apply free quota
        total_cost = Decimal("0")
        
        return total_cost


if __name__ == "__main__":
    # Example usage
    service = ProfileService()
    
    profile = service.create_profile(
        workspace_id="ws_001",
        name="Default Pipeline",
        description="Standard STA/LTA + DBSCAN + Geiger",
        created_by="user_001",
        p_pick_provider_id="sta_lta",
        association_provider_id="dbscan",
        locmag_provider_id="geiger",
        preferences={
            "sample_rate": 50.0,
            "channels": ["BHZ", "BHN", "BHE"],
            "min_magnitude": Decimal("2.5")
        }
    )
    
    print(f"Created profile: {profile.id}")
    print(f"Status: {profile.status}")
    print(f"Providers: {profile.p_pick_config.provider_id} → {profile.association_config.provider_id} → {profile.locmag_config.provider_id}")
    
    # Validate
    valid, msg = service.validate_profile(profile)
    print(f"Valid: {valid} ({msg})")
    
    # Activate
    profile = service.activate_profile(profile, "user_001")
    print(f"Activated: {profile.status} at {profile.activated_at}")
