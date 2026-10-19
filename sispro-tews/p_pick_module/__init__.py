"""
p_pick_module/__init__.py - P-pick module orchestrator.

Koordinasi p_pick providers (STA/LTA, PhaseNet, EQTransformer).
Memilih provider terbaik, run inference, aggregate hasil.
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging

from providers.base import InferenceRequest, BaseProvider
from providers.registry import get_registry, ProviderRegistry
from core.event import Pick
from core.profile_service import ProfileConfig

logger = logging.getLogger(__name__)


class PPickModule:
    """
    P-pick module (phase picking).
    
    Tanggung jawab:
    1. Select best p_pick provider dari registry
    2. Run inference
    3. Aggregate picks dari multiple providers (optional)
    4. Return picks + cost metadata
    """
    
    def __init__(self, registry: Optional[ProviderRegistry] = None):
        self.registry = registry or get_registry()
        self._last_provider = None
    
    def get_p_pick_providers(self) -> List[str]:
        """List semua p_pick providers di registry."""
        p_pick_names = ["STALTA", "PhaseNet", "EQTransformer"]
        available = []
        
        for name in p_pick_names:
            provider = self.registry.get(name)
            if provider:
                available.append(name)
        
        return available
    
    def pick(
        self,
        request: InferenceRequest,
        profile: Optional[ProfileConfig] = None,
        force_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run P-pick inference.
        
        Args:
        - request: InferenceRequest dengan waveform data
        - profile: ProfileConfig (optional, untuk prefer device)
        - force_provider: Force spesifik provider (bypass auto-select)
        
        Returns:
        - picks: List[Pick]
        - provider_name: str
        - cost_idr: Decimal
        - latency_ms: float
        """
        # Select provider
        if force_provider:
            provider = self.registry.get(force_provider)
            if not provider:
                raise ValueError(f"Provider {force_provider} not available")
        else:
            provider = self.registry.find_best(request, profile)
            if not provider:
                raise ValueError("No p_pick provider available")
        
        logger.info(f"Selected p_pick provider: {provider.name}")
        self._last_provider = provider.name
        
        # Run inference
        try:
            result = provider.infer(request)
        except Exception as e:
            logger.error(f"P-pick inference failed: {e}")
            raise
        
        return {
            "picks": result["picks"],
            "provider_name": provider.name,
            "cost_idr": result["cost_idr"],
            "latency_ms": result["latency_ms"],
            "metadata": result["metadata"]
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check health dari p_pick providers."""
        providers = self.get_p_pick_providers()
        
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
    """Test PPickModule."""
    from providers.base import MockProvider, DeviceType
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Register mock providers
    registry = get_registry()
    registry.clear()
    
    mock1 = MockProvider({"price_per_infer_idr": Decimal("100")})
    # Monkey-patch name for testing
    type(mock1).name = property(lambda self: "STALTA")
    registry.register(mock1)
    
    # Create module
    module = PPickModule(registry)
    
    # Create request
    request = InferenceRequest(
        data=b"test_waveform",
        sample_rate_hz=100.0,
        n_stations=5,
        metadata={"duration": 60.0}
    )
    
    # Pick
    result = module.pick(request)
    print(f"P-pick Result:")
    print(f"  Picks: {len(result['picks'])}")
    print(f"  Provider: {result['provider_name']}")
    print(f"  Cost: {result['cost_idr']} IDR")
    
    # Health check
    health = module.health_check()
    print(f"\nHealth: {health}")
