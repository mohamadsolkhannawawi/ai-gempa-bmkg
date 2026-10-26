"""
locmag_module/__init__.py - Location & magnitude module orchestrator.

Koordinasi locmag providers (PyOcto, Geiger, NonLinLoc).
Clustering clusters → events (dengan lat, lon, depth, mag).
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging

from providers.base import InferenceRequest, BaseProvider
from providers.registry import get_registry, ProviderRegistry
from core.event import Cluster, Event
from core.profile_service import ProfileConfig

logger = logging.getLogger(__name__)


class LocmagModule:
    """
    Location & magnitude module.
    
    Tanggung jawab:
    1. Select best locmag provider
    2. Run location dari clusters → events
    3. Return events + cost
    """
    
    def __init__(self, registry: Optional[ProviderRegistry] = None):
        self.registry = registry or get_registry()
        self._last_provider = None
    
    def get_locmag_providers(self) -> List[str]:
        """List locmag providers."""
        locmag_names = ["PyOcto", "Geiger", "NonLinLoc"]
        available = []
        
        for name in locmag_names:
            provider = self.registry.get(name)
            if provider:
                available.append(name)
        
        return available
    
    def locate_and_magnitude(
        self,
        clusters: List[Cluster],
        profile: Optional[ProfileConfig] = None,
        force_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run location & magnitude determination.
        
        Args:
        - clusters: List[Cluster] dari association
        - profile: ProfileConfig
        - force_provider: Force spesifik provider
        
        Returns:
        - events: List[Event] dengan lat, lon, depth, mag
        - provider_name: str
        - cost_idr: Decimal
        - latency_ms: float
        """
        # Create request dengan clusters
        request = InferenceRequest(
            data=b"",
            sample_rate_hz=100.0,
            n_stations=5,  # Default
            metadata={"clusters": clusters}
        )
        
        # Select provider
        if force_provider:
            provider = self.registry.get(force_provider)
            if not provider:
                raise ValueError(f"Provider {force_provider} not available")
        else:
            provider = self.registry.find_best(request, profile)
            if not provider:
                raise ValueError("No locmag provider available")
        
        logger.info(f"Selected locmag provider: {provider.name}")
        self._last_provider = provider.name
        
        # Run inference
        try:
            result = provider.infer(request)
        except Exception as e:
            logger.error(f"Location inference failed: {e}")
            raise
        
        return {
            "events": result["events"],
            "provider_name": provider.name,
            "cost_idr": result["cost_idr"],
            "latency_ms": result["latency_ms"],
            "metadata": result["metadata"]
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check health dari locmag providers."""
        providers = self.get_locmag_providers()
        
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
    """Test LocmagModule."""
    from providers.base import MockProvider
    from core.event import Cluster
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    registry = get_registry()
    registry.clear()
    
    mock = MockProvider()
    type(mock).name = property(lambda self: "PyOcto")
    registry.register(mock)
    
    module = LocmagModule(registry)
    
    # Create mock clusters
    clusters = [
        Cluster(
            id=f"cluster_{i}",
            picks=[f"pick_{i}_{j}" for j in range(5)],
            centroid=1000.0 + i * 10.0,
            radius=0.5
        )
        for i in range(5)
    ]
    
    result = module.locate_and_magnitude(clusters)
    print(f"Locmag Result:")
    print(f"  Events: {len(result['events'])}")
    print(f"  Provider: {result['provider_name']}")
    print(f"  Cost: {result['cost_idr']} IDR")
