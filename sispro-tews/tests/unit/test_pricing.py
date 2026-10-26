"""
tests/unit/test_pricing.py - Unit tests untuk core/pricing.py.
"""
import sys
sys.path.insert(0, "..")

from decimal import Decimal
import pytest

from core.pricing import (
    UnitRate, UsageRecord, PriceBreakdown, PricingService, 
    ProviderTier, Tax
)


class TestUnitRate:
    """Test UnitRate value object."""
    
    def test_cpu_provider_rate(self):
        """CPU provider: Rp 50/1K picks."""
        rate = UnitRate(provider="sta_lta", tier=ProviderTier.CPU, 
                       price_per_1k_units=Decimal("50"))
        assert rate.tier == ProviderTier.CPU
        assert rate.price_per_1k_units == Decimal("50")
    
    def test_gpu_basic_provider_rate(self):
        """GPU_BASIC provider: Rp 500/1K picks."""
        rate = UnitRate(provider="phasenet", tier=ProviderTier.GPU_BASIC,
                       price_per_1k_units=Decimal("500"))
        assert rate.tier == ProviderTier.GPU_BASIC
        assert rate.price_per_1k_units == Decimal("500")
    
    def test_gpu_premium_provider_rate(self):
        """GPU_PREMIUM provider: Rp 1500/1K picks."""
        rate = UnitRate(provider="gamma", tier=ProviderTier.GPU_PREMIUM,
                       price_per_1k_units=Decimal("1500"))
        assert rate.tier == ProviderTier.GPU_PREMIUM
        assert rate.price_per_1k_units == Decimal("1500")


class TestUsageRecord:
    """Test UsageRecord entity."""
    
    def test_empty_usage(self):
        """New workspace = 0 usage."""
        rec = UsageRecord(workspace_id="ws1", date="2026-10-19")
        assert rec.picks == 0
        assert rec.events == 0
        assert rec.storage_gb == Decimal("0")
    
    def test_add_picks(self):
        """Track picks usage."""
        rec = UsageRecord(workspace_id="ws1", date="2026-10-19")
        rec.add_picks(1000)
        assert rec.picks == 1000
        rec.add_picks(500)
        assert rec.picks == 1500
    
    def test_add_events(self):
        """Track events usage."""
        rec = UsageRecord(workspace_id="ws1", date="2026-10-19")
        rec.add_events(10)
        assert rec.events == 10
    
    def test_set_storage(self):
        """Track storage usage (daily snapshot)."""
        rec = UsageRecord(workspace_id="ws1", date="2026-10-19")
        rec.set_storage(Decimal("25.5"))
        assert rec.storage_gb == Decimal("25.5")


class TestPriceBreakdown:
    """Test PriceBreakdown calculation."""
    
    def test_sta_lta_1k_picks(self):
        """STA/LTA 1K picks = Rp 50."""
        bd = PriceBreakdown(workspace_id="ws1", month="2026-10")
        bd.add_stage_cost("p_pick", "sta_lta", 1000, Decimal("50"))
        assert bd.stage_costs["p_pick"]["sta_lta"] == Decimal("50")
    
    def test_phasenet_5k_picks(self):
        """PhaseNet 5K picks = Rp 500 * 5 = Rp 2500."""
        bd = PriceBreakdown(workspace_id="ws1", month="2026-10")
        bd.add_stage_cost("p_pick", "phasenet", 5000, Decimal("500"))
        # 5K picks = 5 x 1K
        expected = Decimal("500") * 5
        assert bd.stage_costs["p_pick"]["phasenet"] == expected
    
    def test_storage_cost(self):
        """Storage: Rp 50/GB/hari x 30 hari x 10 GB = Rp 15000."""
        bd = PriceBreakdown(workspace_id="ws1", month="2026-10")
        # 10 GB storage x 30 hari
        bd.set_storage_cost(Decimal("10"), 30, Decimal("50"))
        expected = Decimal("10") * 30 * Decimal("50")  # 15000
        assert bd.storage_cost == expected
    
    def test_tax_11_percent(self):
        """PPN 11%."""
        bd = PriceBreakdown(workspace_id="ws1", month="2026-10")
        bd.add_stage_cost("p_pick", "sta_lta", 10000, Decimal("50"))  # 10K picks = 500
        bd.set_storage_cost(Decimal("10"), 30, Decimal("50"))  # 15000
        # Subtotal = 500 + 15000 = 15500
        subtotal = bd.subtotal()
        assert subtotal == Decimal("15500")
        
        # Tax = 11%
        tax = bd.calculate_tax(Tax.PPN_11)
        expected_tax = subtotal * Decimal("0.11")  # 1705
        assert tax == expected_tax
        
        # Total = subtotal + tax
        total = bd.total()
        assert total == subtotal + tax  # 17205
    
    def test_free_quota_deduction(self):
        """Free quota: STA/LTA 10K picks gratis."""
        bd = PriceBreakdown(workspace_id="ws1", month="2026-10")
        # 15K picks, tapi 10K free quota
        bd.add_stage_cost("p_pick", "sta_lta", 15000, Decimal("50"))
        bd.apply_free_quota("p_pick", "sta_lta", 10000)  # deduct 10K
        
        # Billable = 15K - 10K = 5K picks
        # Cost = 5K / 1K * Rp50 = Rp 250
        billable_picks = 15000 - 10000  # 5000
        expected = Decimal(billable_picks / 1000) * Decimal("50")  # 250
        assert bd.stage_costs["p_pick"]["sta_lta"] == expected


class TestPricingService:
    """Test PricingService domain service."""
    
    def test_calculate_pick_cost_cpu(self):
        """CPU provider: 10K picks @ Rp50/1K = Rp 500."""
        cost = PricingService.calculate_pick_cost(
            provider="sta_lta",
            tier=ProviderTier.CPU,
            picks=10000,
            rate_per_1k=Decimal("50")
        )
        expected = Decimal("10") * Decimal("50")  # 500
        assert cost == expected
    
    def test_calculate_pick_cost_gpu_basic(self):
        """GPU_BASIC provider: 5K picks @ Rp500/1K = Rp 2500."""
        cost = PricingService.calculate_pick_cost(
            provider="phasenet",
            tier=ProviderTier.GPU_BASIC,
            picks=5000,
            rate_per_1k=Decimal("500")
        )
        expected = Decimal("5") * Decimal("500")  # 2500
        assert cost == expected
    
    def test_calculate_storage_cost(self):
        """Storage: 25 GB x 30 hari @ Rp50/GB/hari = Rp 37500."""
        cost = PricingService.calculate_storage_cost(
            storage_gb=Decimal("25"),
            days=30,
            rate_per_gb_day=Decimal("50")
        )
        expected = Decimal("25") * 30 * Decimal("50")  # 37500
        assert cost == expected
    
    def test_estimate_monthly_cost_sta_lta(self):
        """Estimate: 50K picks/month STA/LTA + 10 GB storage."""
        estimate = PricingService.estimate_monthly_cost(
            profile={
                "stages": {
                    "p_pick": {"provider": "sta_lta", "tier": "CPU"}
                }
            },
            estimated_picks=50000,
            estimated_storage_gb=Decimal("10"),
            days=30
        )
        
        # Picks: 50K / 1K * 50 = 2500
        # Storage: 10 * 30 * 50 = 15000
        # Subtotal: 17500
        # Tax (11%): 1925
        # Total: 19425
        assert "subtotal" in estimate
        assert "tax" in estimate
        assert "total" in estimate
        assert estimate["total"] == Decimal("19425")
    
    def test_free_quota_applied(self):
        """Free quota: 10K picks gratis untuk STA/LTA."""
        # 15K picks, 10K free quota → billable 5K
        billable = PricingService.apply_free_quota(
            provider="sta_lta",
            usage_picks=15000,
            free_quota=10000
        )
        assert billable == 5000
    
    def test_free_quota_exceed_fully_used(self):
        """Free quota sudah habis → all picks billable."""
        billable = PricingService.apply_free_quota(
            provider="sta_lta",
            usage_picks=5000,
            free_quota=0  # quota habis
        )
        assert billable == 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
