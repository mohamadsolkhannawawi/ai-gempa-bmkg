"""
providers/p_pick/stalta_provider.py - STA/LTA provider adapter.

Wrapper untuk p_pick.stalta_manual modul.
Klasik algoritma STA/LTA (Short-Term Average / Long-Term Average).
"""
from typing import Dict, Any
from decimal import Decimal
import time

from providers.base import BaseProvider, DeviceType, InferenceRequest
from core.event import Pick


class STALTAProvider(BaseProvider):
    """STA/LTA picker provider."""
    
    @property
    def name(self) -> str:
        return "STALTA"
    
    @property
    def version(self) -> str:
        return "v1.0"
    
    @property
    def device_type(self) -> DeviceType:
        return DeviceType.CPU
    
    def initialize(self) -> bool:
        """Initialize STA/LTA (no model loading needed)."""
        try:
            # Import p_pick.stalta_manual untuk verify module exists
            # TODO: actual import when module ready
            # from p_pick.stalta_manual import pick_stalta
            
            self._initialized = True
            return True
        except Exception as e:
            return False
    
    def supports(self, request: InferenceRequest) -> bool:
        """STA/LTA support any waveform data."""
        return True
    
    def infer(self, request: InferenceRequest) -> Dict[str, Any]:
        """
        Run STA/LTA picking.
        
        Steps:
        1. Parse waveform data
        2. Run STA/LTA algorithm (short_window, long_window, threshold)
        3. Convert triggers → Pick objects
        4. Return picks + cost
        """
        start_time = time.time()
        
        # TODO: actual STA/LTA inference
        # from p_pick.stalta_manual import pick_stalta
        # triggers = pick_stalta(request.data, ...)
        
        # Mock picks for now
        picks = self._mock_picks(request)
        
        latency_ms = (time.time() - start_time) * 1000
        cost = self.cost_estimate(request)
        
        return {
            "picks": picks,
            "clusters": [],
            "events": [],
            "latency_ms": latency_ms,
            "cost_idr": cost,
            "metadata": {
                "algorithm": "stalta",
                "n_picks": len(picks),
                "short_window": self.config.get("short_window", 0.5),
                "long_window": self.config.get("long_window", 10.0),
                "threshold": self.config.get("threshold", 3.0)
            }
        }
    
    def _mock_picks(self, request: InferenceRequest) -> list:
        """Generate mock picks (sementara)."""
        # Estimate 100-200 picks per 60 seconds
        n_picks = int(request.duration_seconds * 2.5)
        
        picks = []
        for i in range(n_picks):
            pick = Pick(
                id=f"stalta_pick_{int(request.request_time)}_{i}",
                station=f"STA{i % request.n_stations + 1}",
                channel="BHZ",
                timestamp=request.request_time + i * 0.3,
                probability=0.7 + (i % 3) * 0.1,
                amplitude=0.01 * (i % 10 + 1),
                phase="P" if i % 2 == 0 else "S"
            )
            picks.append(pick)
        
        return picks
    
    def cost_estimate(self, request: InferenceRequest) -> Decimal:
        """
        STA/LTA cost: 5 IDR per pick (baseline cheap).
        Estimate 100 picks per 60 seconds.
        """
        n_picks = int(request.duration_seconds * 2.5)
        price_per_pick = Decimal("5")
        return n_picks * price_per_pick


if __name__ == "__main__":
    """Test STALTAProvider."""
    provider = STALTAProvider({"threshold": 3.5})
    
    # Initialize
    assert provider.initialize() == True
    
    # Request
    request = InferenceRequest(
        data=b"test_waveform",
        sample_rate_hz=100.0,
        n_stations=5,
        metadata={"duration": 60.0}
    )
    
    # Infer
    result = provider.infer(request)
    print(f"STA/LTA Result:")
    print(f"  Picks: {len(result['picks'])}")
    print(f"  Latency: {result['latency_ms']:.2f} ms")
    print(f"  Cost: {result['cost_idr']} IDR")
    print(f"  Metadata: {result['metadata']}")
