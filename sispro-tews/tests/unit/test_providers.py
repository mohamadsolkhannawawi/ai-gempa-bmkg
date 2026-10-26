"""
tests/unit/test_providers.py - Unit tests untuk semua providers.
"""
import sys
sys.path.insert(0, "..")

from datetime import date
from decimal import Decimal
import pytest

from providers.base import BaseProvider, MockProvider, InferenceRequest, DeviceType
from providers.p_pick.stalta_provider import STALTAProvider
from providers.p_pick.phasenet_provider import PhaseNetProvider
from providers.p_pick.eqtransformer_provider import EQTransformerProvider
from providers.association.dbscan_provider import DBSCANProvider
from providers.association.gamma_provider import GaMMAProvider
from providers.locmag.pyocto_provider import PyOctoProvider
from providers.locmag.geiger_provider import GeigerProvider
from providers.locmag.nonlinloc_provider import NonLinLocProvider
from core.event import Pick, Cluster


class TestSTALTAProvider:
    """Test STA/LTA provider."""
    
    def test_initialize(self):
        """Initialize STA/LTA."""
        provider = STALTAProvider()
        assert provider.initialize() == True
    
    def test_supports_any_waveform(self):
        """STA/LTA support any waveform."""
        provider = STALTAProvider()
        provider.initialize()
        
        request = InferenceRequest(
            data=b"test",
            sample_rate_hz=100.0,
            n_stations=5
        )
        
        assert provider.supports(request) == True
    
    def test_infer(self):
        """Run STA/LTA inference."""
        provider = STALTAProvider()
        provider.initialize()
        
        request = InferenceRequest(
            data=b"test",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"duration": 60.0}
        )
        
        result = provider.infer(request)
        
        assert "picks" in result
        assert "cost_idr" in result
        assert "latency_ms" in result
        assert len(result["picks"]) > 0


class TestPhaseNetProvider:
    """Test PhaseNet provider."""
    
    def test_initialize_cpu(self):
        """Initialize PhaseNet CPU mode."""
        provider = PhaseNetProvider({"device": "cpu"})
        assert provider.initialize() == True
        assert provider.device_type == DeviceType.CPU
    
    def test_initialize_gpu(self):
        """Initialize PhaseNet GPU mode."""
        provider = PhaseNetProvider({"device": "gpu"})
        assert provider.initialize() == True
        assert provider.device_type == DeviceType.GPU
    
    def test_supports_3_channels(self):
        """PhaseNet requires 3 channels per station."""
        provider = PhaseNetProvider()
        provider.initialize()
        
        # 3 channels: supported
        request_3ch = InferenceRequest(
            data=b"test",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"channels_per_station": 3}
        )
        assert provider.supports(request_3ch) == True
        
        # 1 channel: not supported
        request_1ch = InferenceRequest(
            data=b"test",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"channels_per_station": 1}
        )
        assert provider.supports(request_1ch) == False
    
    def test_cost_cpu_vs_gpu(self):
        """Cost difference: GPU more expensive."""
        provider_cpu = PhaseNetProvider({"device": "cpu"})
        provider_gpu = PhaseNetProvider({"device": "gpu"})
        
        provider_cpu.initialize()
        provider_gpu.initialize()
        
        request = InferenceRequest(
            data=b"test",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"duration": 60.0, "channels_per_station": 3}
        )
        
        cost_cpu = provider_cpu.cost_estimate(request)
        cost_gpu = provider_gpu.cost_estimate(request)
        
        assert cost_gpu > cost_cpu


class TestDBSCANProvider:
    """Test DBSCAN provider."""
    
    def test_initialize(self):
        """Initialize DBSCAN."""
        provider = DBSCANProvider()
        assert provider.initialize() == True
    
    def test_supports_picks(self):
        """DBSCAN requires picks data."""
        provider = DBSCANProvider()
        provider.initialize()
        
        # With picks: supported
        request_picks = InferenceRequest(
            data=b"",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"picks": []}
        )
        assert provider.supports(request_picks) == True
        
        # No picks: not supported
        request_no_picks = InferenceRequest(
            data=b"",
            sample_rate_hz=100.0,
            n_stations=5
        )
        assert provider.supports(request_no_picks) == False
    
    def test_clustering(self):
        """DBSCAN clustering."""
        provider = DBSCANProvider()
        provider.initialize()
        
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
        
        request = InferenceRequest(
            data=b"",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"picks": picks}
        )
        
        result = provider.infer(request)
        
        assert "clusters" in result
        assert len(result["clusters"]) > 0
        assert result["cost_idr"] > Decimal("0")


class TestGaMMAProvider:
    """Test GaMMA provider."""
    
    def test_device_types(self):
        """GaMMA support CPU and GPU."""
        provider_cpu = GaMMAProvider({"device": "cpu"})
        provider_gpu = GaMMAProvider({"device": "gpu"})
        
        assert provider_cpu.device_type == DeviceType.CPU
        assert provider_gpu.device_type == DeviceType.GPU
    
    def test_clustering_efficiency(self):
        """GaMMA more efficient (fewer picks per cluster)."""
        provider = GaMMAProvider()
        provider.initialize()
        
        picks = [
            Pick(
                id=f"pick_{i}",
                station="STA1",
                channel="BHZ",
                timestamp=1000.0 + i * 0.5,
                probability=0.9,
                amplitude=0.1,
                phase="P"
            )
            for i in range(24)
        ]
        
        request = InferenceRequest(
            data=b"",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"picks": picks}
        )
        
        result = provider.infer(request)
        assert len(result["clusters"]) >= 4  # 24 picks / 6 per cluster


class TestPyOctoProvider:
    """Test PyOcto locmag provider."""
    
    def test_initialize(self):
        """Initialize PyOcto."""
        provider = PyOctoProvider()
        assert provider.initialize() == True
    
    def test_location(self):
        """PyOcto location from clusters."""
        provider = PyOctoProvider()
        provider.initialize()
        
        clusters = [
            Cluster(
                id=f"cluster_{i}",
                picks=[f"pick_{i}_{j}" for j in range(5)],
                centroid=1000.0 + i * 10.0,
                radius=0.5
            )
            for i in range(5)
        ]
        
        request = InferenceRequest(
            data=b"",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"clusters": clusters}
        )
        
        result = provider.infer(request)
        
        assert "events" in result
        assert len(result["events"]) == len(clusters)
        
        # Check event properties
        for event in result["events"]:
            assert hasattr(event, "latitude")
            assert hasattr(event, "longitude")
            assert hasattr(event, "depth_km")
            assert hasattr(event, "magnitude")


class TestGeigerProvider:
    """Test Geiger locmag provider."""
    
    def test_cost_cheaper_than_pyocto(self):
        """Geiger cheaper than PyOcto."""
        provider_geiger = GeigerProvider()
        provider_pyocto = PyOctoProvider()
        
        provider_geiger.initialize()
        provider_pyocto.initialize()
        
        clusters = [
            Cluster(
                id=f"cluster_{i}",
                picks=[],
                centroid=1000.0 + i * 10.0,
                radius=0.5
            )
            for i in range(5)
        ]
        
        request = InferenceRequest(
            data=b"",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"clusters": clusters}
        )
        
        cost_geiger = provider_geiger.cost_estimate(request)
        cost_pyocto = provider_pyocto.cost_estimate(request)
        
        assert cost_geiger < cost_pyocto


class TestNonLinLocProvider:
    """Test NonLinLoc locmag provider."""
    
    def test_initialize(self):
        """Initialize NonLinLoc."""
        provider = NonLinLocProvider()
        assert provider.initialize() == True
    
    def test_probabilistic_location(self):
        """NonLinLoc probabilistic location."""
        provider = NonLinLocProvider()
        provider.initialize()
        
        clusters = [
            Cluster(
                id=f"cluster_{i}",
                picks=[f"pick_{i}_{j}" for j in range(5)],
                centroid=1000.0 + i * 10.0,
                radius=0.5
            )
            for i in range(3)
        ]
        
        request = InferenceRequest(
            data=b"",
            sample_rate_hz=100.0,
            n_stations=5,
            metadata={"clusters": clusters}
        )
        
        result = provider.infer(request)
        assert len(result["events"]) == len(clusters)
        
        # NonLinLoc most expensive
        assert result["cost_idr"] > Decimal("200")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
