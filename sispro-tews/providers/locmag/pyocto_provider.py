"""
providers/locmag/pyocto_provider.py - PyOcto location provider.

Wrapper untuk PyOcto (Python Octahedral Tree) earthquake location.
CPU-only.
"""
from typing import Dict, Any, List
from decimal import Decimal
import time

from providers.base import BaseProvider, DeviceType, InferenceRequest
from core.event import Cluster, Event


class PyOctoProvider(BaseProvider):
    """PyOcto earthquake location provider."""
    
    @property
    def name(self) -> str:
        return "PyOcto"
    
    @property
    def version(self) -> str:
        return "v1.0"
    
    @property
    def device_type(self) -> DeviceType:
        return DeviceType.CPU
    
    def initialize(self) -> bool:
        """Initialize PyOcto."""
        try:
            # TODO: import PyOcto
            # from locmag.pyocto import PyOctoLocator
            
            self._initialized = True
            return True
        except Exception as e:
            return False
    
    def supports(self, request: InferenceRequest) -> bool:
        """PyOcto requires clusters data."""
        return "clusters" in request.metadata
    
    def infer(self, request: InferenceRequest) -> Dict[str, Any]:
        """
        Run PyOcto location.
        
        Input: clusters
        Output: events (lat, lon, depth, mag)
        """
        start_time = time.time()
        
        clusters: List[Cluster] = request.metadata.get("clusters", [])
        
        # TODO: actual PyOcto location
        # events = pyocto.locate(clusters)
        
        events = self._mock_events(clusters, request)
        
        latency_ms = (time.time() - start_time) * 1000
        cost = self.cost_estimate(request)
        
        return {
            "picks": [],
            "clusters": [],
            "events": events,
            "latency_ms": latency_ms,
            "cost_idr": cost,
            "metadata": {
                "algorithm": "pyocto",
                "n_events": len(events),
                "n_input_clusters": len(clusters)
            }
        }
    
    def _mock_events(self, clusters: List[Cluster], request: InferenceRequest) -> List[Event]:
        """Generate mock events."""
        if not clusters:
            return []
        
        events = []
        for i, cluster in enumerate(clusters):
            event = Event(
                id=f"pyocto_event_{int(request.request_time)}_{i}",
                origin_time=cluster.centroid,
                latitude=-6.5 + i * 0.1,
                longitude=106.8 + i * 0.1,
                depth_km=10.0 + i * 2.0,
                magnitude=2.0 + i * 0.3,
                picks=cluster.picks,
                confidence=0.75
            )
            events.append(event)
        
        return events
    
    def cost_estimate(self, request: InferenceRequest) -> Decimal:
        """PyOcto cost: 100 IDR per event."""
        clusters = request.metadata.get("clusters", [])
        n_events = len(clusters)
        price_per_event = Decimal("100")
        return n_events * price_per_event


if __name__ == "__main__":
    """Test PyOctoProvider."""
    provider = PyOctoProvider()
    assert provider.initialize() == True
    
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
    print(f"PyOcto Result:")
    print(f"  Events: {len(result['events'])}")
    print(f"  Cost: {result['cost_idr']} IDR")
