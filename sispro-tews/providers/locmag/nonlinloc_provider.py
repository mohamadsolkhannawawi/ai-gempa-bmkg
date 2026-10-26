"""
providers/locmag/nonlinloc_provider.py - NonLinLoc provider.

Wrapper untuk NonLinLoc (Non-Linear earthquake location).
CPU-only, probabilistic.
"""
from typing import Dict, Any, List
from decimal import Decimal
import time

from providers.base import BaseProvider, DeviceType, InferenceRequest
from core.event import Cluster, Event


class NonLinLocProvider(BaseProvider):
    """NonLinLoc earthquake location provider."""
    
    @property
    def name(self) -> str:
        return "NonLinLoc"
    
    @property
    def version(self) -> str:
        return "v1.0"
    
    @property
    def device_type(self) -> DeviceType:
        return DeviceType.CPU
    
    def initialize(self) -> bool:
        """Initialize NonLinLoc."""
        try:
            # TODO: import NonLinLoc
            # from locmag.nonlinloc import NonLinLocLocator
            
            self._initialized = True
            return True
        except Exception as e:
            return False
    
    def supports(self, request: InferenceRequest) -> bool:
        """NonLinLoc requires clusters data."""
        return "clusters" in request.metadata
    
    def infer(self, request: InferenceRequest) -> Dict[str, Any]:
        """Run NonLinLoc location."""
        start_time = time.time()
        
        clusters: List[Cluster] = request.metadata.get("clusters", [])
        
        # TODO: actual NonLinLoc location
        # events = nonlinloc.locate(clusters)
        
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
                "algorithm": "nonlinloc",
                "n_events": len(events),
                "n_input_clusters": len(clusters),
                "grid_type": self.config.get("grid_type", "3D")
            }
        }
    
    def _mock_events(self, clusters: List[Cluster], request: InferenceRequest) -> List[Event]:
        """Generate mock events (NonLinLoc probabilistic)."""
        if not clusters:
            return []
        
        events = []
        for i, cluster in enumerate(clusters):
            event = Event(
                id=f"nonlinloc_event_{int(request.request_time)}_{i}",
                origin_time=cluster.centroid,
                latitude=-6.8 + i * 0.12,
                longitude=107.0 + i * 0.1,
                depth_km=15.0 + i * 2.5,
                magnitude=2.5 + i * 0.2,
                picks=cluster.picks,
                confidence=0.85  # Higher confidence (probabilistic)
            )
            events.append(event)
        
        return events
    
    def cost_estimate(self, request: InferenceRequest) -> Decimal:
        """NonLinLoc cost: 120 IDR per event (paling mahal, paling akurat)."""
        clusters = request.metadata.get("clusters", [])
        n_events = len(clusters)
        price_per_event = Decimal("120")
        return n_events * price_per_event


if __name__ == "__main__":
    """Test NonLinLocProvider."""
    provider = NonLinLocProvider({"grid_type": "3D"})
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
    print(f"NonLinLoc Result:")
    print(f"  Events: {len(result['events'])}")
    print(f"  Cost: {result['cost_idr']} IDR")
