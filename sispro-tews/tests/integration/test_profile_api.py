"""
tests/integration/test_profile_api.py - Integration tests untuk profile API endpoints.
"""
import sys
sys.path.insert(0, "..")

from fastapi.testclient import TestClient
from decimal import Decimal
import pytest

from api.routes.profile import router, _repo
from fastapi import FastAPI


# Setup test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestProfileAPI:
    """Test profile API endpoints."""
    
    def setup_method(self):
        """Reset repo before each test."""
        _repo.profiles.clear()
    
    def test_create_profile_success(self):
        """POST /api/v2/profiles — create success."""
        response = client.post(
            "/api/v2/profiles?workspace_id=ws_001&created_by=user_001",
            json={
                "name": "Test Pipeline",
                "description": "Integration test",
                "p_pick_provider_id": "sta_lta",
                "association_provider_id": "dbscan",
                "locmag_provider_id": "geiger"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "Test Pipeline"
        assert data["description"] == "Integration test"
        assert data["status"] == "draft"
        assert data["workspace_id"] == "ws_001"
        assert "id" in data
    
    def test_create_profile_with_preferences(self):
        """POST /api/v2/profiles — create dengan preferences."""
        response = client.post(
            "/api/v2/profiles?workspace_id=ws_002&created_by=user_002",
            json={
                "name": "GPU Pipeline",
                "description": "High performance",
                "p_pick_provider_id": "phasenet",
                "association_provider_id": "gamma",
                "locmag_provider_id": "pyocto",
                "preferences": {
                    "sample_rate": 80.0,
                    "channels": ["BHZ"],
                    "min_magnitude": 2.5,
                    "p_pick_sensitivity": "high",
                    "association_distance_km": 30.0
                }
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["preferences"]["sample_rate"] == 80.0
        assert data["preferences"]["channels"] == ["BHZ"]
        assert data["preferences"]["p_pick_sensitivity"] == "high"
    
    def test_get_profile_by_id(self):
        """GET /api/v2/profiles/{id} — get single profile."""
        create_resp = client.post(
            "/api/v2/profiles?workspace_id=ws_003&created_by=user_003",
            json={"name": "Get Test", "description": "Test"}
        )
        profile_id = create_resp.json()["id"]
        
        response = client.get(f"/api/v2/profiles/{profile_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == profile_id
        assert data["name"] == "Get Test"
    
    def test_get_profile_not_found(self):
        """GET /api/v2/profiles/{id} — 404 not found."""
        response = client.get("/api/v2/profiles/nonexistent_id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_list_profiles_by_workspace(self):
        """GET /api/v2/profiles?workspace_id=X — list profiles."""
        # Create 3 profiles
        for i in range(3):
            client.post(
                f"/api/v2/profiles?workspace_id=ws_list&created_by=user_{i}",
                json={"name": f"Profile {i}", "description": "Test"}
            )
        
        response = client.get("/api/v2/profiles?workspace_id=ws_list")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 3
        assert len(data["profiles"]) == 3
        assert data["active_profile_id"] is None
    
    def test_list_profiles_filter_by_status(self):
        """GET /api/v2/profiles?status=draft — filter by status."""
        client.post(
            "/api/v2/profiles?workspace_id=ws_filter&created_by=user_001",
            json={"name": "Draft 1", "description": "Test"}
        )
        
        response = client.get("/api/v2/profiles?workspace_id=ws_filter&status=draft")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        assert data["profiles"][0]["status"] == "draft"
    
    def test_update_profile_success(self):
        """PUT /api/v2/profiles/{id} — update success."""
        create_resp = client.post(
            "/api/v2/profiles?workspace_id=ws_update&created_by=user_update",
            json={"name": "Old Name", "description": "Old Desc"}
        )
        profile_id = create_resp.json()["id"]
        
        response = client.put(
            f"/api/v2/profiles/{profile_id}?updated_by=user_updated",
            json={
                "name": "New Name",
                "description": "New Desc",
                "p_pick_provider_id": "eqtransformer"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "New Name"
        assert data["description"] == "New Desc"
        assert data["p_pick_config"]["provider_id"] == "eqtransformer"
    
    def test_update_profile_fails_if_not_draft(self):
        """PUT /api/v2/profiles/{id} — fails if not DRAFT."""
        # Create + activate profile
        create_resp = client.post(
            "/api/v2/profiles?workspace_id=ws_active&created_by=user_001",
            json={"name": "Active Profile", "description": "Test"}
        )
        profile_id = create_resp.json()["id"]
        
        # Activate
        client.post(
            f"/api/v2/profiles/{profile_id}/activate",
            json={"profile_id": profile_id}
        )
        
        # Try update
        response = client.put(
            f"/api/v2/profiles/{profile_id}?updated_by=user_001",
            json={"name": "Updated"}
        )
        
        assert response.status_code == 400
        assert "Cannot update profile with status" in response.json()["detail"]
    
    def test_activate_profile_success(self):
        """POST /api/v2/profiles/{id}/activate — activate success."""
        create_resp = client.post(
            "/api/v2/profiles?workspace_id=ws_activate&created_by=user_activate",
            json={"name": "To Activate", "description": "Test"}
        )
        profile_id = create_resp.json()["id"]
        
        response = client.post(
            f"/api/v2/profiles/{profile_id}/activate?updated_by=user_activate",
            json={"profile_id": profile_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "active"
        assert data["activated_at"] is not None
    
    def test_activate_profile_fails_if_invalid(self):
        """POST /api/v2/profiles/{id}/activate — fails validation."""
        create_resp = client.post(
            "/api/v2/profiles?workspace_id=ws_invalid&created_by=user_001",
            json={"name": "", "description": "Empty name"}
        )
        profile_id = create_resp.json()["id"]
        
        response = client.post(
            f"/api/v2/profiles/{profile_id}/activate",
            json={"profile_id": profile_id}
        )
        
        assert response.status_code == 400
        assert "validation failed" in response.json()["detail"]
    
    def test_delete_profile_success(self):
        """DELETE /api/v2/profiles/{id} — delete success."""
        create_resp = client.post(
            "/api/v2/profiles?workspace_id=ws_delete&created_by=user_delete",
            json={"name": "To Delete", "description": "Test"}
        )
        profile_id = create_resp.json()["id"]
        
        response = client.delete(f"/api/v2/profiles/{profile_id}")
        
        assert response.status_code == 204
        
        # Verify deleted
        get_resp = client.get(f"/api/v2/profiles/{profile_id}")
        assert get_resp.status_code == 404
    
    def test_delete_profile_fails_if_not_draft(self):
        """DELETE /api/v2/profiles/{id} — fails if not DRAFT."""
        create_resp = client.post(
            "/api/v2/profiles?workspace_id=ws_del_active&created_by=user_001",
            json={"name": "Active Profile", "description": "Test"}
        )
        profile_id = create_resp.json()["id"]
        
        # Activate
        client.post(
            f"/api/v2/profiles/{profile_id}/activate",
            json={"profile_id": profile_id}
        )
        
        # Try delete
        response = client.delete(f"/api/v2/profiles/{profile_id}")
        
        assert response.status_code == 400
        assert "Cannot delete profile with status" in response.json()["detail"]
    
    def test_validate_profile_success(self):
        """POST /api/v2/profiles/{id}/validate — validation success."""
        create_resp = client.post(
            "/api/v2/profiles?workspace_id=ws_validate&created_by=user_validate",
            json={"name": "Valid Profile", "description": "Test"}
        )
        profile_id = create_resp.json()["id"]
        
        response = client.post(f"/api/v2/profiles/{profile_id}/validate")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert len(data["errors"]) == 0
    
    def test_validate_profile_failure(self):
        """POST /api/v2/profiles/{id}/validate — validation fails."""
        create_resp = client.post(
            "/api/v2/profiles?workspace_id=ws_val_fail&created_by=user_001",
            json={"name": "", "description": "Empty name"}
        )
        profile_id = create_resp.json()["id"]
        
        response = client.post(f"/api/v2/profiles/{profile_id}/validate")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert len(data["errors"]) > 0
    
    def test_estimate_cost_success(self):
        """GET /api/v2/profiles/{id}/cost — cost estimation."""
        create_resp = client.post(
            "/api/v2/profiles?workspace_id=ws_cost&created_by=user_cost",
            json={"name": "Cost Profile", "description": "Test"}
        )
        profile_id = create_resp.json()["id"]
        
        response = client.get(f"/api/v2/profiles/{profile_id}/cost")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["profile_id"] == profile_id
        assert "estimated_monthly_cost_idr" in data
        assert "assumptions" in data
    
    def test_health_check(self):
        """GET /api/v2/health/profiles — health check."""
        response = client.get("/api/v2/health/profiles")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "profile"
    
    def test_list_profiles_with_active_profile(self):
        """GET /api/v2/profiles — list dengan active_profile_id."""
        # Create 2 profiles
        p1_resp = client.post(
            "/api/v2/profiles?workspace_id=ws_active_list&created_by=user_001",
            json={"name": "Profile 1", "description": "Test"}
        )
        p1_id = p1_resp.json()["id"]
        
        client.post(
            "/api/v2/profiles?workspace_id=ws_active_list&created_by=user_002",
            json={"name": "Profile 2", "description": "Test"}
        )
        
        # Activate profile 1
        client.post(
            f"/api/v2/profiles/{p1_id}/activate",
            json={"profile_id": p1_id}
        )
        
        # List
        response = client.get("/api/v2/profiles?workspace_id=ws_active_list")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 2
        assert data["active_profile_id"] == p1_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
