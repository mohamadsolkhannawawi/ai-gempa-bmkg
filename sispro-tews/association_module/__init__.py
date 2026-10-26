"""
association_module/__init__.py - Association module orchestrator.

Koordinasi association providers (DBSCAN, GaMMA).
Clustering picks → clusters.
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging

from providers.base import InferenceRequest, BaseProvider
from providers.registry import get_registry, ProviderRegistry
from core.event import Pick, Cluster
from core.profile_service import ProfileConfig

logger = logging.getLogger(__name__)


class AssociationModule:
    """
    Association module (event association/clustering).
    
    Tanggung jawab:
    1. Select best association provider
    2. Run clustering picks → clusters
    3. Return clusters + cost
    """
    
    def __init__(self, registry: Optional[ProviderRegistry] = None):
        self.registry = registry or get_registry()
        self._last_provider = None
    
    def get_association_providers(self) -> List[str]:
        """List association providers."""
        assoc_names = ["DBSCAN", "GaMMA"]
        available = []
        
        for name in assoc_names:
            provider = self.registry.get(name)
            if provider:
                available.append(name)
        
        return available
    
    def associate(
        self,
        picks: List[Pick],
        profile: Optional[ProfileConfig] = None,
        force_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run event association (clustering).
        
        Args:
        - picks: List[Pick] dari p_pick
        - profile: ProfileConfig
        - force_provider: Force spesifik provider
        
        Returns:
        - clusters: List[Cluster]
        - provider_name: str
        - cost_idr: Decimal
        - latency_ms: float
        """
        # Create request dengan picks dalam metadata
        request = InferenceRequest(
            data=b"",
            sample_rate_hz=100.0,
            n_stations=len(set(p.station for p in picks)) if picks else 1,
            metadata={"picks": picks}
        )
        
        # Select provider
        if force_provider:
            provider = self.registry.get(force_provider)
            if not provider:
                raise ValueError(f"Provider {force_provider} not available")
        else:
            provider = self.registry.find_best(request, profile)
            if not provider:
                raise ValueError("No association provider available")
        
        logger.info(f"Selected association provider: {provider.name}")
        self._last_provider = provider.name
        
        # Run inference
        try:
            result = provider.infer(request)
        except Exception as e:
            logger.error(f"Association inference failed: {e}")
            raise
        
        return {
            "clusters": result["clusters"],
            "provider_name": provider.name,
            "cost_idr": result["cost_idr"],
            "latency_ms": result["latency_ms"],
            "metadata": result["metadata"]
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check health dari association providers."""
        providers = self.get_association_providers()
        
        health = {}
        for name in providers:
            provider = self.registry.get(name)
            if provider:
                healthy, msg = provider.health_check()
                health[name] = {
                    "healthy": healthy,
                    "message": msg
                }
        
        return {
            "total": len(providers),
            "healthy": sum(1 for h in health.values() if h["healthy"]),
            "providers": health
        }


if __name__ == "__main__":
    """Test AssociationModule."""
    from providers.base import MockProvider
    from core.event import Pick
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    registry = get_registry()
    registry.clear()
    
    mock = MockProvider()
    type(mock).name = property(lambda self: "DBSCAN")
    registry.register(mock)
    
    module = AssociationModule(registry)
    
    # Create mock picks
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
    
    result = module.associate(picks)
    print(f"Association Result:")
    print(f"  Clusters: {len(result['clusters'])}")
    print(f"  Provider: {result['provider_name']}")
    print(f"  Cost: {result['cost_idr']} IDR")
