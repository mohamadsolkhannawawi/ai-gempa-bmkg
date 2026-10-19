"""
tests/unit/test_profile_service.py - Unit tests untuk ProfileService domain.
"""
import sys
sys.path.insert(0, "..")

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from core.profile_service import (
    ProfileService, Profile, ProfileConfig, PipelinePreferences, ProfileStatus
)
from infrastructure.repositories.profile_repo import InMemoryProfileRepository


class TestProfileService:
    """Test domain business logic."""
    
    def setup_method(self):
        self.repo = InMemoryProfileRepository()
        self.service = ProfileService(self.repo)
    
    def test_create_profile_basic(self):
        """Create new profile dengan defaults."""
        profile = self.service.create_profile(
            workspace_id="ws_001",
            name="Test Pipeline",
            description="Test",
            created_by="user_001"
        )
        
        assert profile.workspace_id == "ws_001"
        assert profile.name == "Test Pipeline"
        assert profile.description == "Test"
        assert profile.status == ProfileStatus.DRAFT
        assert profile.created_by == "user_001"
        
        assert profile.p_pick_config.provider_id == "sta_lta"
        assert profile.association_config.provider_id == "dbscan"
        assert profile.locmag_config.provider_id == "geiger"
        
        assert profile.preferences.sample_rate == 100.0
        assert profile.preferences.channels == ["BHZ", "BHN", "BHE"]
        assert profile.preferences.min_magnitude == Decimal("2.0")
    
    def test_create_profile_with_custom_providers(self):
        """Create profile dengan custom provider IDs."""
        profile = self.service.create_profile(
            workspace_id="ws_002",
            name="GPU Pipeline",
            description="Use GPU models",
            created_by="user_002",
            p_pick_provider_id="phasenet",
            association_provider_id="gamma",
            locmag_provider_id="pyocto"
        )
        
        assert profile.p_pick_config.provider_id == "phasenet"
        assert profile.association_config.provider_id == "gamma"
        assert profile.locmag_config.provider_id == "pyocto"
    
    def test_create_profile_with_preferences(self):
        """Create profile dengan custom preferences."""
        profile = self.service.create_profile(
            workspace_id="ws_003",
            name="Sensitive Pipeline",
            description="High sample rate, low threshold",
            created_by="user_003",
            preferences={
                "sample_rate": 80.0,
                "channels": ["BHZ"],
                "min_magnitude": Decimal("1.5"),
                "p_pick_sensitivity": "high"
            }
        )
        
        assert profile.preferences.sample_rate == 80.0
        assert profile.preferences.channels == ["BHZ"]
        assert profile.preferences.min_magnitude == Decimal("1.5")
        assert profile.preferences.p_pick_sensitivity == "high"
    
    def test_activate_profile_success(self):
        """Activate profile (DRAFT → ACTIVE)."""
        profile = self.service.create_profile(
            workspace_id="ws_004",
            name="Activate Test",
            description="Test",
            created_by="user_004"
        )
        
        activated = self.service.activate_profile(profile, "user_004")
        
        assert activated.status == ProfileStatus.ACTIVE
        assert activated.activated_at is not None
        assert activated.updated_by == "user_004"
        assert activated.updated_at >= profile.updated_at
    
    def test_activate_profile_fails_if_not_draft(self):
        """Activation gagal jika status bukan DRAFT."""
        profile = self.service.create_profile(
            workspace_id="ws_005",
            name="Already Active",
            description="Test",
            created_by="user_005"
        )
        
        profile.status = ProfileStatus.ACTIVE
        
        with pytest.raises(ValueError, match="Cannot activate profile with status"):
            self.service.activate_profile(profile, "user_005")
    
    def test_update_profile_success(self):
        """Update profile (DRAFT only)."""
        profile = self.service.create_profile(
            workspace_id="ws_006",
            name="Old Name",
            description="Old Desc",
            created_by="user_006"
        )
        
        updated = self.service.update_profile(
            profile,
            updated_by="user_006_updated",
            name="New Name",
            description="New Desc",
            p_pick_provider_id="eqtransformer",
            sample_rate=60.0
        )
        
        assert updated.name == "New Name"
        assert updated.description == "New Desc"
        assert updated.p_pick_config.provider_id == "eqtransformer"
        assert updated.preferences.sample_rate == 60.0
        assert updated.updated_by == "user_006_updated"
    
    def test_update_profile_fails_if_not_draft(self):
        """Update gagal jika status bukan DRAFT."""
        profile = self.service.create_profile(
            workspace_id="ws_007",
            name="Test",
            description="Test",
            created_by="user_007"
        )
        
        profile.status = ProfileStatus.ACTIVE
        
        with pytest.raises(ValueError, match="Cannot update profile with status"):
            self.service.update_profile(
                profile,
                updated_by="user_007",
                name="Updated"
            )
    
    def test_archive_profile(self):
        """Archive profile (DRAFT/ACTIVE → ARCHIVED)."""
        profile = self.service.create_profile(
            workspace_id="ws_008",
            name="To Archive",
            description="Test",
            created_by="user_008"
        )
        
        archived = self.service.archive_profile(profile, "user_008")
        
        assert archived.status == ProfileStatus.ARCHIVED
        assert archived.archived_at is not None
        assert archived.updated_by == "user_008"
    
    def test_archive_profile_fails_if_already_archived(self):
        """Archive gagal jika sudah ARCHIVED."""
        profile = self.service.create_profile(
            workspace_id="ws_009",
            name="Already Archived",
            description="Test",
            created_by="user_009"
        )
        
        profile.status = ProfileStatus.ARCHIVED
        
        with pytest.raises(ValueError, match="Profile already archived"):
            self.service.archive_profile(profile, "user_009")
    
    def test_validate_profile_success(self):
        """Validation sukses untuk valid profile."""
        profile = self.service.create_profile(
            workspace_id="ws_010",
            name="Valid Profile",
            description="All fields filled",
            created_by="user_010"
        )
        
        valid, msg = self.service.validate_profile(profile)
        
        assert valid is True
        assert msg == "OK"
    
    def test_validate_profile_missing_name(self):
        """Validation gagal jika nama kosong."""
        profile = self.service.create_profile(
            workspace_id="ws_011",
            name="",
            description="Test",
            created_by="user_011"
        )
        
        valid, msg = self.service.validate_profile(profile)
        
        assert valid is False
        assert "Profile name required" in msg
    
    def test_validate_profile_missing_provider(self):
        """Validation gagal jika provider kosong."""
        profile = self.service.create_profile(
            workspace_id="ws_012",
            name="Missing Provider",
            description="Test",
            created_by="user_012"
        )
        
        profile.p_pick_config.provider_id = ""
        
        valid, msg = self.service.validate_profile(profile)
        
        assert valid is False
        assert "P-pick provider required" in msg
    
    def test_validate_profile_invalid_sample_rate(self):
        """Validation gagal jika sample rate di luar range."""
        profile = self.service.create_profile(
            workspace_id="ws_013",
            name="Bad Sample Rate",
            description="Test",
            created_by="user_013",
            preferences={
                "sample_rate": 10.0  # < 20
            }
        )
        
        valid, msg = self.service.validate_profile(profile)
        
        assert valid is False
        assert "Sample rate must be 20-100 Hz" in msg
    
    def test_estimate_monthly_cost(self):
        """Estimate monthly cost (placeholder)."""
        profile = self.service.create_profile(
            workspace_id="ws_014",
            name="Cost Test",
            description="Test",
            created_by="user_014"
        )
        
        cost = self.service.estimate_monthly_cost(profile)
        
        assert isinstance(cost, Decimal)
        assert cost >= Decimal("0")
    
    def test_profile_to_dict_serialization(self):
        """Test serialization to_dict."""
        profile = self.service.create_profile(
            workspace_id="ws_015",
            name="Serialize Test",
            description="Test",
            created_by="user_015"
        )
        
        data = profile.to_dict()
        
        assert "id" in data
        assert data["workspace_id"] == "ws_015"
        assert data["name"] == "Serialize Test"
        assert data["status"] == "draft"
        assert "p_pick_config" in data
        assert "preferences" in data
    
    def test_profile_from_dict_deserialization(self):
        """Test deserialization from_dict."""
        original = self.service.create_profile(
            workspace_id="ws_016",
            name="Deserialize Test",
            description="Test",
            created_by="user_016"
        )
        
        data = original.to_dict()
        
        restored = Profile.from_dict(data)
        
        assert restored.id == original.id
        assert restored.workspace_id == "ws_016"
        assert restored.name == "Deserialize Test"
        assert restored.status == ProfileStatus.DRAFT
        assert restored.created_by == "user_016"


class TestProfileConfig:
    """Test ProviderConfig class."""
    
    def test_provider_config_to_dict(self):
        """ProviderConfig to_dict."""
        config = ProfileConfig(
            provider_id="phasenet",
            tier="GPU_BASIC",
            enabled=True,
            custom_params={"threshold": 0.3}
        )
        
        data = config.to_dict()
        
        assert data["provider_id"] == "phasenet"
        assert data["tier"] == "GPU_BASIC"
        assert data["enabled"] is True
        assert data["custom_params"] == {"threshold": 0.3}
    
    def test_provider_config_from_dict(self):
        """ProviderConfig from_dict (via **)."""
        data = {
            "provider_id": "sta_lta",
            "tier": "CPU",
            "enabled": False,
            "custom_params": {}
        }
        
        config = ProfileConfig(**data)
        
        assert config.provider_id == "sta_lta"
        assert config.tier == "CPU"
        assert config.enabled is False


class TestPipelinePreferences:
    """Test PipelinePreferences class."""
    
    def test_preferences_to_dict(self):
        """PipelinePreferences to_dict."""
        prefs = PipelinePreferences(
            sample_rate=80.0,
            channels=["BHZ"],
            min_magnitude=Decimal("2.5"),
            p_pick_sensitivity="high",
            association_distance_km=30.0,
            locmag_depth_constraint=20.0,
            auto_publish_events=True,
            webhook_url="https://example.com/webhook"
        )
        
        data = prefs.to_dict()
        
        assert data["sample_rate"] == 80.0
        assert data["channels"] == ["BHZ"]
        assert data["min_magnitude"] == "2.5"
        assert data["p_pick_sensitivity"] == "high"
        assert data["association_distance_km"] == 30.0
        assert data["locmag_depth_constraint"] == 20.0
        assert data["auto_publish_events"] is True
        assert data["webhook_url"] == "https://example.com/webhook"
    
    def test_preferences_from_dict(self):
        """PipelinePreferences from_dict (via **)."""
        data = {
            "sample_rate": 50.0,
            "channels": ["BHZ", "BHE"],
            "min_magnitude": "3.0",
            "p_pick_sensitivity": "low",
            "association_distance_km": 15.0
        }
        
        prefs = PipelinePreferences(**data)
        
        assert prefs.sample_rate == 50.0
        assert prefs.channels == ["BHZ", "BHE"]
        assert prefs.min_magnitude == Decimal("3.0")
        assert prefs.p_pick_sensitivity == "low"
        assert prefs.association_distance_km == 15.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
