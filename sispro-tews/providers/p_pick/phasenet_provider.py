"""
providers/p_pick/phasenet_provider.py - PhaseNet provider adapter.

Wrapper untuk PhaseNet deep learning picker.
Support CPU dan GPU mode.
"""
from typing import Dict, Any
from decimal import Decimal
import time

from providers.base import BaseProvider, DeviceType, InferenceRequest
from core.event import Pick


class PhaseNetProvider(BaseProvider):
    """PhaseNet deep learning picker."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._device = config.get("device", "cpu") if config else "cpu"
    
    @property
    def name(self) -> str:
        return "PhaseNet"
    
    @property
    def version(self) -> str:
        return "v1.0"
    
    @property
    def device_type(self) -> DeviceType:
        return DeviceType.GPU if self._device == "gpu" else DeviceType.CPU
    
    def initialize(self) -> bool:
        """Initialize PhaseNet model."""
        try:
            # TODO: load PhaseNet model
            # from p_pick.phasenet import PhaseNetModel
            # self._model = PhaseNetModel.load(device=self._device)
            
            self._initialized = True
            return True
        except Exception as e:
            return False
    
    def supports(self, request: InferenceRequest) -> bool:
        """PhaseNet requires 3 channels per station."""
        return request.channels_per_station == 3
    
    def infer(self, request: InferenceRequest) -> Dict[str, Any]:
        """Run PhaseNet inference."""
        start_time = time.time()
        
        # TODO: actual PhaseNet inference
        # picks = self._model.predict(request.data)
        
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
                "algorithm": "phasenet",
                "device": self._device,
                "n_picks": len(picks),
                "model_version": self.version
            }
        }
    
    def _mock_picks(self, request: InferenceRequest) -> list:
        """Generate mock picks."""
        n_picks = int(request.duration_seconds * 3.0)  # PhaseNet lebih presisi
        
        picks = []
        for i in range(n_picks):
            pick = Pick(
                id=f"phasenet_pick_{int(request.request_time)}_{i}",
                station=f"STA{i % request.n_stations + 1}",
                channel="BHZ",
                timestamp=request.request_time + i * 0.4,
                probability=0.85 + (i % 10) * 0.01,
                amplitude=0.02 * (i % 8 + 1),
                phase="P" if i % 2 == 0 else "S"
            )
            picks.append(pick)
        
        return picks
    
    def cost_estimate(self, request: InferenceRequest) -> Decimal:
        """
        PhaseNet cost:
        - CPU: 10 IDR per pick
        - GPU: 15 IDR per pick (lebih cepat, lebih mahal)
        """
        n_picks = int(request.duration_seconds * 3.0)
        price_per_pick = Decimal("15") if self._device == "gpu" else Decimal("10")
        return n_picks * price_per_pick


if __name__ == "__main__":
    """Test PhaseNetProvider."""
    # CPU mode
    provider_cpu = PhaseNetProvider({"device": "cpu"})
    assert provider_cpu.initialize() == True
    
    request = InferenceRequest(
        data=b"test_waveform",
        sample_rate_hz=100.0,
        n_stations=5,
        metadata={"duration": 60.0, "channels_per_station": 3}
    )
    
    result = provider_cpu.infer(request)
    print(f"PhaseNet (CPU) Result:")
    print(f"  Picks: {len(result['picks'])}")
    print(f"  Cost: {result['cost_idr']} IDR")
    
    # GPU mode
    provider_gpu = PhaseNetProvider({"device": "gpu"})
    assert provider_gpu.initialize() == True
    
    result_gpu = provider_gpu.infer(request)
    print(f"\nPhaseNet (GPU) Result:")
    print(f"  Picks: {len(result_gpu['picks'])}")
    print(f"  Cost: {result_gpu['cost_idr']} IDR")
