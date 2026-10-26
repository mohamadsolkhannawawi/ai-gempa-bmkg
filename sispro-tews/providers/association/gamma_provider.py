"""
providers/association/gamma_provider.py - GaMMA (Generalized Arrival-time Matching Algorithm).

Wrapper untuk GaMMA clustering provider.
CPU/GPU support.
"""
from typing import Dict, Any, List
from decimal import Decimal
import time

from providers.base import BaseProvider, DeviceType, InferenceRequest
from core.event import Pick, Cluster


class GaMMAProvider(BaseProvider):
    """GaMMA clustering provider."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._device = config.get("device", "cpu") if config else "cpu"
    
    @property
    def name(self) -> str:
        return "GaMMA"
    
    @property
    def version(self) -> str:
        return "v1.0"
    
    @property
    def device_type(self) -> DeviceType:
        return DeviceType.GPU if self._device == "gpu" else DeviceType.CPU
    
    def initialize(self) -> bool:
        """Initialize GaMMA."""
        try:
            # TODO: import GaMMA
            # from association.gamma import GaMMA
            
            self._initialized = True
            return True
        except Exception as e:
            return False
    
    def supports(self, request: InferenceRequest) -> bool:
        """GaMMA requires picks data."""
        return "picks" in request.metadata
    
    def infer(self, request: InferenceRequest) -> Dict[str, Any]:
        """
        Run GaMMA clustering.
        
        Input: picks
        Output: clusters (lebih akurat dari DBSCAN)
        """
        start_time = time.time()
        
        picks: List[Pick] = request.metadata.get("picks", [])
        
        # TODO: actual GaMMA clustering
        # clusters = gamma.associate(picks)
        
        clusters = self._mock_clusters(picks, request)
        
        latency_ms = (time.time() - start_time) * 1000
        cost = self.cost_estimate(request)
        
        return {
            "picks": [],
            "clusters": clusters,
            "events": [],
            "latency_ms": latency_ms,
            "cost_idr": cost,
            "metadata": {
                "algorithm": "gamma",
                "device": self._device,
                "n_clusters": len(clusters),
                "n_input_picks": len(picks)
            }
        }
    
    def _mock_clusters(self, picks: List[Pick], request: InferenceRequest) -> List[Cluster]:
        """Generate mock clusters (GaMMA lebih presisi)."""
        if not picks:
            return []
        
        # GaMMA lebih efisien: 1 cluster per 6 picks
        n_clusters = max(1, len(picks) // 6)
        
        clusters = []
        for i in range(n_clusters):
            start_idx = i * 6
            end_idx = min(start_idx + 6, len(picks))
            cluster_picks = picks[start_idx:end_idx]
            
            if not cluster_picks:
                break
            
            centroid = sum(p.timestamp for p in cluster_picks) / len(cluster_picks)
            
            cluster = Cluster(
                id=f"gamma_cluster_{int(request.request_time)}_{i}",
                picks=[p.id for p in cluster_picks],
                centroid=centroid,
                radius=0.3  # Tighter radius
            )
            clusters.append(cluster)
        
        return clusters
    
    def cost_estimate(self, request: InferenceRequest) -> Decimal:
        """
        GaMMA cost:
        - CPU: 25 IDR per cluster
        - GPU: 30 IDR per cluster
        """
        picks = request.metadata.get("picks", [])
        n_clusters = max(1, len(picks) // 6)
        price_per_cluster = Decimal("30") if self._device == "gpu" else Decimal("25")
        return n_clusters * price_per_cluster


if __name__ == "__main__":
    """Test GaMMAProvider."""
    provider_cpu = GaMMAProvider({"device": "cpu"})
    assert provider_cpu.initialize() == True
    
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
    
    result = provider_cpu.infer(request)
    print(f"GaMMA (CPU) Result:")
    print(f"  Clusters: {len(result['clusters'])}")
    print(f"  Cost: {result['cost_idr']} IDR")
