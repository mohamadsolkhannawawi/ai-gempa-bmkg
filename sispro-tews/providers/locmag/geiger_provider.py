"""
providers/locmag/geiger_provider.py - Geiger location provider.

Wrapper untuk Geiger (classical iterative earthquake location).
CPU-only, fast.
"""
from typing import Dict, Any, List
from decimal import Decimal
import time

from providers.base import BaseProvider, DeviceType, InferenceRequest
from core.event import Cluster, Event


class GeigerProvider(BaseProvider):
    """Geiger earthquake location provider."""
    
    @property
    def name(self) -> str:
        return "Geiger"
    
    @property
    def version(self) -> str:
        return "v1.0"
    
    @property
    def device_type(self) -> DeviceType:
        return DeviceType.CPU
    
    def initialize(self) -> bool:
        """Initialize Geiger."""
        try:
            # TODO: import Geiger
            # from locmag.geiger import GeigerLocator
            
            self._initialized = True
            return True
        except Exception as e:
            return False
    
    def supports(self, request: InferenceRequest) -> bool:
        """Geiger requires clusters data."""
        return "clusters" in request.metadata
    
    def infer(self, request: InferenceRequest) -> Dict[str, Any]:
        """Run Geiger location."""
        start_time = time.time()
        
        clusters: List[Cluster] = request.metadata.get("clusters", [])
        
        # TODO: actual Geiger location
        # events = geiger.locate(clusters)
        
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
                "algorithm": "geiger",
                "n_events": len(events),
                "n_input_clusters": len(clusters),
                "max_iterations": self.config.get("max_iterations", 10)
            }
        }
    
    def _mock_events(self, clusters: List[Cluster], request: InferenceRequest) -> List[Event]:
        """Generate mock events."""
        if not clusters:
            return []
        
        events = []
        for i, cluster in enumerate(clusters):
            event = Event(
                id=f"geiger_event_{int(request.request_time)}_{i}",
                origin_time=cluster.centroid,
                latitude=-7.0 + i * 0.15,
                longitude=107.5 + i * 0.12,
                depth_km=12.0 + i * 1.5,
                magnitude=2.2 + i * 0.25,
                picks=cluster.picks,
                confidence=0.80
            )
            events.append(event)
        
        return events
    
    def cost_estimate(self, request: InferenceRequest) -> Decimal:
        """Geiger cost: 80 IDR per event (cheaper than PyOcto)."""
        clusters = request.metadata.get("clusters", [])
        n_events = len(clusters)
        price_per_event = Decimal("80")
        return n_events * price_per_event


if __name__ == "__main__":
    """Test GeigerProvider."""
    provider = GeigerProvider({"max_iterations": 10})
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
    print(f"Geiger Result:")
    print(f"  Events: {len(result['events'])}")
    print(f"  Cost: {result['cost_idr']} IDR")
