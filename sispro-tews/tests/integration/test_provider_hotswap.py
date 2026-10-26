"""
tests/integration/test_provider_hotswap.py - Hot-swap provider tests.

Verifikasi bahwa provider dapat di-swap tanpa downtime.
Test ProviderRegistry + module orchestrators.
"""
import sys
sys.path.insert(0, "..")

from datetime import date
from decimal import Decimal
import pytest

from providers.registry import get_registry, ProviderRegistry
from providers.base import MockProvider, InferenceRequest, DeviceType
from providers.p_pick.stalta_provider import STALTAProvider
from providers.p_pick.phasenet_provider import PhaseNetProvider
from providers.association.dbscan_provider import DBSCANProvider
from providers.association.gamma_provider import GaMMAProvider
from providers.locmag.geiger_provider import GeigerProvider
from providers.locmag.pyocto_provider import PyOctoProvider

from p_pick_module import PPickModule
from association_module import AssociationModule
from locmag_module import LocmagModule

from core.event import Pick, Cluster


class TestProviderRegistry:
    """Test ProviderRegistry hot-swap capability."""
    
    def test_register_unregister(self):
        """Register dan unregister providers."""
        registry = ProviderRegistry()
        
        provider1 = STALTAProvider()
        assert registry.register(provider1) == True
        assert "STALTA" in registry.list()
        
        # Unregister
        assert registry.unregister("STALTA") == True
        assert "STALTA" not in registry.list()
    
    def test_override_provider(self):
        """Override existing provider (hot-swap)."""
        registry = ProviderRegistry()
        
        # Register first version
        provider1 = STALTAProvider({"threshold": 3.0})
        assert registry.register(provider1) == True
        
        old_provider = registry.get("STALTA")
        assert old_provider.config["threshold"] == 3.0
        
        # Override dengan version baru
        provider2 = STALTAProvider({"threshold": 4.0})
        assert registry.register(provider2) == True
        
        new_provider = registry.get("STALTA")
        assert new_provider.config["threshold"] == 4.0
    
    def test_find_best_provider(self):
        """Find best provider dari registry."""
        registry = ProviderRegistry()
        
        # Register providers
        stalta = STALTAProvider({"price_per_infer_idr": Decimal("100")})
        phasenet = PhaseNetProvider({"device": "cpu", "price_per_infer_idr": Decimal("200")})
        
        registry.register(stalta)
        registry.register(phasenet)
        
        # Request
        request = InferenceRequest(
            data=b"test",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"duration": 60.0, "channels_per_station": 3}
        )
        
        # Find best (should pick cheaper if both support)
        best = registry.find_best(request)
        assert best is not None
        # STALTA supports any, cheaper, so should be selected
        assert best.name == "STALTA"
    
    def test_find_best_with_device_preference(self):
        """Find best provider considering device preference."""
        registry = ProviderRegistry()
        
        # Register CPU and GPU variants
        phasenet_cpu = PhaseNetProvider({"device": "cpu"})
        phasenet_gpu = PhaseNetProvider({"device": "gpu"})
        
        registry.register(phasenet_cpu)
        registry.register(phasenet_gpu)
        
        request = InferenceRequest(
            data=b"test",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"duration": 60.0, "channels_per_station": 3}
        )
        
        # Without preference, should find one
        best = registry.find_best(request)
        assert best is not None
    
    def test_health_check_all(self):
        """Health check all providers."""
        registry = ProviderRegistry()
        
        provider1 = STALTAProvider()
        provider2 = DBSCANProvider()
        
        registry.register(provider1)
        registry.register(provider2)
        
        health = registry.health_check_all()
        
        assert len(health) >= 2
        assert "STALTA" in health
        assert "DBSCAN" in health
        assert health["STALTA"][0] == True  # healthy
    
    def test_registry_stats(self):
        """Get registry statistics."""
        registry = ProviderRegistry()
        
        # Register mix of CPU/GPU
        registry.register(STALTAProvider())  # CPU
        registry.register(PhaseNetProvider({"device": "gpu"}))  # GPU
        registry.register(DBSCANProvider())  # CPU
        
        stats = registry.stats()
        
        assert stats["total_providers"] >= 3
        assert stats["healthy_count"] >= 3
        assert stats["unhealthy_count"] == 0


class TestHotSwapPPickModule:
    """Test hot-swap pada PPickModule."""
    
    def test_select_best_ppick_provider(self):
        """PPickModule select best p_pick provider."""
        registry = ProviderRegistry()
        registry.register(STALTAProvider())
        
        module = PPickModule(registry)
        
        request = InferenceRequest(
            data=b"test",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"duration": 60.0}
        )
        
        result = module.pick(request)
        
        assert "picks" in result
        assert result["provider_name"] == "STALTA"
    
    def test_switch_ppick_provider(self):
        """Switch p_pick provider (hot-swap)."""
        registry = ProviderRegistry()
        
        # Start dengan STALTA
        stalta = STALTAProvider()
        registry.register(stalta)
        module = PPickModule(registry)
        
        request = InferenceRequest(
            data=b"test",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"duration": 60.0, "channels_per_station": 3}
        )
        
        result1 = module.pick(request)
        assert result1["provider_name"] == "STALTA"
        
        # Hot-swap: add PhaseNet
        phasenet = PhaseNetProvider({"device": "cpu"})
        registry.register(phasenet)
        
        result2 = module.pick(request)
        # Might switch to PhaseNet if cheaper
        assert result2["provider_name"] in ["STALTA", "PhaseNet"]
    
    def test_force_ppick_provider(self):
        """Force specific p_pick provider."""
        registry = ProviderRegistry()
        registry.register(STALTAProvider({"price_per_infer_idr": Decimal("10")}))
        registry.register(PhaseNetProvider(
            {"device": "cpu", "price_per_infer_idr": Decimal("5")}  # Cheaper
        ))
        
        module = PPickModule(registry)
        
        request = InferenceRequest(
            data=b"test",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"duration": 60.0, "channels_per_station": 3}
        )
        
        # Force STALTA even though PhaseNet cheaper
        result = module.pick(request, force_provider="STALTA")
        assert result["provider_name"] == "STALTA"


class TestHotSwapAssociationModule:
    """Test hot-swap pada AssociationModule."""
    
    def test_switch_association_provider(self):
        """Switch association provider."""
        registry = ProviderRegistry()
        registry.register(DBSCANProvider())
        
        module = AssociationModule(registry)
        
        picks = [
            Pick(
                id=f"pick_{i}",
                station="STA1",
                channel="BHZ",
                timestamp=1000.0 + i * 0.5,
                probability=0.8,
                amplitude=0.1,
                phase="P"
            )
            for i in range(20)
        ]
        
        result1 = module.associate(picks)
        assert result1["provider_name"] == "DBSCAN"
        
        # Hot-swap: add GaMMA
        gamma = GaMMAProvider({"device": "cpu"})
        registry.register(gamma)
        
        result2 = module.associate(picks)
        # Should still work, may switch to GaMMA
        assert result2["provider_name"] in ["DBSCAN", "GaMMA"]
        assert "clusters" in result2


class TestHotSwapLocmagModule:
    """Test hot-swap pada LocmagModule."""
    
    def test_switch_locmag_provider(self):
        """Switch locmag provider."""
        registry = ProviderRegistry()
        registry.register(GeigerProvider())
        
        module = LocmagModule(registry)
        
        clusters = [
            Cluster(
                id=f"cluster_{i}",
                picks=[f"pick_{i}_{j}" for j in range(5)],
                centroid=1000.0 + i * 10.0,
                radius=0.5
            )
            for i in range(5)
        ]
        
        result1 = module.locate_and_magnitude(clusters)
        assert result1["provider_name"] == "Geiger"
        
        # Hot-swap: add PyOcto
        pyocto = PyOctoProvider()
        registry.register(pyocto)
        
        result2 = module.locate_and_magnitude(clusters)
        # Should work with new provider
        assert result2["provider_name"] in ["Geiger", "PyOcto"]
        assert "events" in result2


class TestEndToEndPipeline:
    """Test end-to-end seismic processing pipeline."""
    
    def test_full_pipeline_p_pick_to_location(self):
        """Full pipeline: waveform → picks → clusters → events."""
        registry = ProviderRegistry()
        
        # Register all providers
        registry.register(STALTAProvider())
        registry.register(DBSCANProvider())
        registry.register(GeigerProvider())
        
        # Create modules
        pppick = PPickModule(registry)
        assoc = AssociationModule(registry)
        locmag = LocmagModule(registry)
        
        # Step 1: P-picking
        waveform_request = InferenceRequest(
            data=b"waveform_data",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"duration": 60.0}
        )
        
        ppick_result = pppick.pick(waveform_request)
        picks = ppick_result["picks"]
        print(f"Step 1: {len(picks)} picks detected")
        
        # Step 2: Association
        assoc_result = assoc.associate(picks)
        clusters = assoc_result["clusters"]
        print(f"Step 2: {len(clusters)} clusters formed")
        
        # Step 3: Location & magnitude
        if clusters:
            locmag_result = locmag.locate_and_magnitude(clusters)
            events = locmag_result["events"]
            print(f"Step 3: {len(events)} events located")
            
            assert len(events) > 0
    
    def test_pipeline_with_provider_switch(self):
        """Pipeline with provider hot-swap mid-execution."""
        registry = ProviderRegistry()
        
        # Initial setup: DBSCAN only
        registry.register(DBSCANProvider())
        assoc = AssociationModule(registry)
        
        picks = [
            Pick(
                id=f"pick_{i}",
                station="STA1",
                channel="BHZ",
                timestamp=1000.0 + i * 0.5,
                probability=0.8,
                amplitude=0.1,
                phase="P"
            )
            for i in range(20)
        ]
        
        # First run with DBSCAN
        result1 = assoc.associate(picks)
        assert result1["provider_name"] == "DBSCAN"
        
        # Hot-swap: remove DBSCAN, add GaMMA
        registry.unregister("DBSCAN")
        registry.register(GaMMAProvider({"device": "cpu"}))
        
        # Second run should use GaMMA now
        result2 = assoc.associate(picks)
        assert result2["provider_name"] == "GaMMA"
        assert len(result1["clusters"]) >= 0
        assert len(result2["clusters"]) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
