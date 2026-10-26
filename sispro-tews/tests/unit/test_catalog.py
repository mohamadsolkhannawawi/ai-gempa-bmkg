"""
tests/unit/test_catalog.py - Unit tests untuk catalog_module + API schemas.
"""
import sys
sys.path.insert(0, "..")

from pathlib import Path
from decimal import Decimal
import pytest

from catalog_module.catalog import ProviderCatalog, ProviderManifest, ProviderRate
from api.schemas.catalog import (
    ProviderSchema, ProviderRateSchema, CostEstimateRequest, CostEstimateResponse
)


class TestProviderCatalog:
    """Unit tests untuk ProviderCatalog."""
    
    @pytest.fixture
    def catalog(self):
        """Load catalog from test data."""
        data_dir = Path(__file__).parent.parent.parent / "catalog_module" / "data"
        return ProviderCatalog(data_dir)
    
    def test_load_manifest(self, catalog):
        """Manifest berhasil load."""
        assert len(catalog.providers) == 8
        assert "sta_lta" in catalog.providers
        assert "phasenet" in catalog.providers
        assert "gamma" in catalog.providers
    
    def test_load_rates(self, catalog):
        """Rates berhasil load."""
        assert len(catalog.rates) >= 8
        assert "sta_lta" in catalog.rates
        assert "phasenet" in catalog.rates
    
    def test_get_provider(self, catalog):
        """Get provider by ID."""
        sta = catalog.get_provider("sta_lta")
        assert sta is not None
        assert sta.name == "STA/LTA P‑Pick"
        assert sta.tier == "CPU"
        assert sta.stage == "p_pick"
    
    def test_get_rate(self, catalog):
        """Get rate by provider ID."""
        rate = catalog.get_rate("sta_lta")
        assert rate is not None
        assert rate.price_per_1k_units == Decimal("50")
        assert rate.free_quota_monthly == 10000
    
    def test_list_providers_all(self, catalog):
        """List semua providers."""
        providers = catalog.list_providers()
        assert len(providers) == 8
    
    def test_list_providers_by_stage(self, catalog):
        """Filter providers by stage."""
        picks = catalog.list_providers(stage="p_pick")
        assert len(picks) == 3  # sta_lta, phasenet, eqtransformer
        assert all(p.stage == "p_pick" for p in picks)
        
        assoc = catalog.list_providers(stage="association")
        assert len(assoc) == 2  # dbscan, gamma
        
        locmag = catalog.list_providers(stage="locmag")
        assert len(locmag) == 3  # pyocto, geiger, nonlinloc
    
    def test_list_providers_by_tier(self, catalog):
        """Filter providers by tier."""
        cpu = catalog.list_providers(tier="CPU")
        assert len(cpu) == 3  # sta_lta, dbscan, geiger
        assert all(p.tier == "CPU" for p in cpu)
        
        gpu_basic = catalog.list_providers(tier="GPU_BASIC")
        assert len(gpu_basic) == 3  # phasenet, eqtransformer, pyocto
        
        gpu_premium = catalog.list_providers(tier="GPU_PREMIUM")
        assert len(gpu_premium) == 2  # gamma, nonlinloc
    
    def test_list_by_stage(self, catalog):
        """Group providers by stage."""
        stages = catalog.list_by_stage()
        assert "p_pick" in stages
        assert "association" in stages
        assert "locmag" in stages
        assert len(stages["p_pick"]) == 3
        assert len(stages["association"]) == 2
        assert len(stages["locmag"]) == 3
    
    def test_estimate_cost_within_free_quota(self, catalog):
        """Cost = 0 jika units dalam free quota."""
        cost = catalog.estimate_cost("sta_lta", units=5000, free_quota=10000)
        assert cost == Decimal("0")
    
    def test_estimate_cost_exceed_quota(self, catalog):
        """Cost billable untuk units di atas free quota."""
        # 15K picks, 10K free → billable 5K
        # Cost = 5K / 1K * 50 = Rp 250
        cost = catalog.estimate_cost("sta_lta", units=15000, free_quota=10000)
        expected = Decimal("250")
        assert cost == expected
    
    def test_estimate_cost_phasenet(self, catalog):
        """PhaseNet 50K picks, 2K free → Rp 24000."""
        # 50K - 2K = 48K billable
        # 48K / 1K * 500 = Rp 24000
        cost = catalog.estimate_cost("phasenet", units=50000, free_quota=2000)
        expected = Decimal("24000")
        assert cost == expected
    
    def test_estimate_cost_gamma(self, catalog):
        """GaMMA 10K clusters, 1K free → Rp 13500."""
        # 10K - 1K = 9K billable
        # 9K / 1K * 1500 = Rp 13500
        cost = catalog.estimate_cost("gamma", units=10000, free_quota=1000)
        expected = Decimal("13500")
        assert cost == expected


class TestCatalogSchemas:
    """Unit tests untuk Pydantic schemas."""
    
    def test_provider_schema_valid(self):
        """ProviderSchema accept valid data."""
        data = {
            "id": "sta_lta",
            "name": "STA/LTA P‑Pick",
            "description": "Classic picker",
            "stage": "p_pick",
            "tier": "CPU",
            "repo": "https://github.com/...",
            "supported_channels": ["BHZ"],
            "min_sample_rate": 20.0,
            "max_sample_rate": 100.0,
            "input_shape": "...",
            "output_format": "...",
            "docker_image": "...",
            "health_check_url": "/health",
            "status": "active",
            "tags": ["cpu"]
        }
        schema = ProviderSchema(**data)
        assert schema.id == "sta_lta"
        assert schema.tier == "CPU"
    
    def test_rate_schema_with_decimal(self):
        """ProviderRateSchema accept Decimal."""
        data = {
            "provider": "phasenet",
            "tier": "GPU_BASIC",
            "price_per_1k_units": Decimal("500"),
            "free_quota_monthly": 2000,
            "description": "GPU picker"
        }
        schema = ProviderRateSchema(**data)
        assert schema.price_per_1k_units == Decimal("500")
    
    def test_cost_estimate_request(self):
        """CostEstimateRequest validation."""
        req = CostEstimateRequest(
            provider_id="sta_lta",
            units=15000,
            free_quota=10000
        )
        assert req.units == 15000
        assert req.free_quota == 10000
    
    def test_cost_estimate_response(self):
        """CostEstimateResponse construction."""
        resp = CostEstimateResponse(
            provider_id="sta_lta",
            units=15000,
            billable_units=5000,
            price_per_1k_units=Decimal("50"),
            estimated_cost_idr=Decimal("250"),
            tax_11_percent=Decimal("27.50"),
            total_cost_idr=Decimal("277.50")
        )
        assert resp.total_cost_idr == Decimal("277.50")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
