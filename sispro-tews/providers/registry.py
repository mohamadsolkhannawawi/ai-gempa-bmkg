"""
providers/registry.py - ProviderRegistry.

Registry untuk manage + hot-swap providers.
Mendukung:
- Register/unregister providers
- Find best provider for request
- Load from profile config
- Health monitoring
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional, Type, Tuple
from datetime import datetime, timezone
import threading
import logging

from providers.base import BaseProvider, DeviceType, InferenceRequest
from core.profile_service import ProfileConfig


logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Central registry untuk semua providers.
    
    Memungkinkan hot‑swap provider berdasarkan profile config.
    """
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._lock = threading.RLock()
        self._last_health_check: Dict[str, datetime] = {}
    
    def register(self, provider: BaseProvider) -> bool:
        """
        Register provider.
        Returns True jika sukses.
        """
        with self._lock:
            name = provider.name
            if name in self._providers:
                logger.warning(f"Provider {name} already registered, overwriting")
            
            # Initialize provider
            if not provider.initialize():
                logger.error(f"Provider {name} failed to initialize")
                return False
            
            self._providers[name] = provider
            self._last_health_check[name] = datetime.now(timezone.utc)
            logger.info(f"Registered provider: {name} ({provider.version})")
            return True
    
    def unregister(self, name: str) -> bool:
        """Unregister provider."""
        with self._lock:
            if name in self._providers:
                del self._providers[name]
                del self._last_health_check[name]
                logger.info(f"Unregistered provider: {name}")
                return True
            return False
    
    def get(self, name: str) -> Optional[BaseProvider]:
        """Get provider by name."""
        with self._lock:
            return self._providers.get(name)
    
    def list(self) -> List[str]:
        """List semua provider names."""
        with self._lock:
            return list(self._providers.keys())
    
    def list_all(self) -> List[BaseProvider]:
        """List semua provider objects."""
        with self._lock:
            return list(self._providers.values())
    
    def list_by_device_type(self, device_type: DeviceType) -> List[BaseProvider]:
        """List providers by device type."""
        with self._lock:
            return [
                p for p in self._providers.values()
                if p.device_type == device_type
            ]
    
    def find_best(self, request: InferenceRequest, profile: ProfileConfig = None) -> Optional[BaseProvider]:
        """
        Find best provider untuk request.
        
        Criteria (urut prioritas):
        1. Provider yang support request
        2. Device type match (CPU/GPU)
        3. Health status
        4. Cost terendah
        """
        with self._lock:
            candidates = []
            
            for provider in self._providers.values():
                # Check health
                healthy, _ = provider.health_check()
                if not healthy:
                    continue
                
                # Check support
                if not provider.supports(request):
                    continue
                
                # Device type preference
                device_match = True
                if profile:
                    preferred = profile.get("preferred_device", DeviceType.CPU)
                    device_match = (provider.device_type == preferred)
                
                # Calculate score
                cost = provider.cost_estimate(request)
                score = 0
                
                if device_match:
                    score += 100
                
                # Lower cost = higher score
                score += max(0, 1000 - int(cost))
                
                candidates.append((score, cost, provider))
            
            if not candidates:
                return None
            
            # Pick highest score
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][2]
    
    def load_from_profile(self, profile: ProfileConfig) -> bool:
        """
        Load providers dari profile config.
        
        Profile berisi:
        - p_pick_providers
        - association_providers
        - locmag_providers
        
        Untuk setiap provider di config, coba register jika belum ada.
        """
        with self._lock:
            providers_to_load = []
            
            # P picks providers
            for p_name in profile.get("p_pick_providers", []):
                providers_to_load.append(p_name)
            
            # Association providers
            for a_name in profile.get("association_providers", []):
                providers_to_load.append(a_name)
            
            # Locmag providers
            for l_name in profile.get("locmag_providers", []):
                providers_to_load.append(l_name)
            
            # Remove duplicates
            providers_to_load = list(set(providers_to_load))
            
            # TODO: actually load provider classes
            # For now, just log
            for name in providers_to_load:
                if name not in self._providers:
                    logger.info(f"Would load provider: {name}")
            
            return True
    
    def health_check_all(self) -> Dict[str, Tuple[bool, str]]:
        """
        Health check semua providers.
        
        Returns dict: provider_name -> (is_healthy, message)
        """
        with self._lock:
            results = {}
            
            for name, provider in self._providers.items():
                healthy, msg = provider.health_check()
                results[name] = (healthy, msg)
                self._last_health_check[name] = datetime.now(timezone.utc)
            
            return results
    
    def stats(self) -> Dict[str, Any]:
        """Return registry statistics."""
        with self._lock:
            total = len(self._providers)
            
            by_device = {}
            for device in DeviceType:
                count = len(self.list_by_device_type(device))
                if count > 0:
                    by_device[device.value] = count
            
            healthy_count = 0
            health_results = self.health_check_all()
            for healthy, _ in health_results.values():
                if healthy:
                    healthy_count += 1
            
            return {
                "total_providers": total,
                "providers_by_device": by_device,
                "healthy_count": healthy_count,
                "unhealthy_count": total - healthy_count,
                "last_health_check": {
                    name: last.isoformat()
                    for name, last in self._last_health_check.items()
                }
            }
    
    def clear(self):
        """Clear semua providers."""
        with self._lock:
            self._providers.clear()
            self._last_health_check.clear()
            logger.info("Cleared all providers")


# Global registry singleton
_registry = None


def get_registry() -> ProviderRegistry:
    """Get global registry singleton."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


if __name__ == "__main__":
    """Test ProviderRegistry."""
    from providers.base import MockProvider, DeviceType, InferenceRequest
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Get registry
    registry = get_registry()
    
    # Register mock providers
    mock1 = MockProvider({"price_per_infer_idr": 100})
    mock1.name = "MockProvider1"
    
    mock2 = MockProvider({"price_per_infer_idr": 150})
    mock2.name = "MockProvider2"
    mock2.device_type = DeviceType.GPU
    
    registry.register(mock1)
    registry.register(mock2)
    
    # List
    print(f"Providers: {registry.list()}")
    
    # Stats
    stats = registry.stats()
    print(f"Stats: {stats}")
    
    # Create request
    request = InferenceRequest(
        data=b"test",
        sample_rate_hz=100.0,
        n_stations=3
    )
    
    # Find best
    best = registry.find_best(request)
    print(f"Best provider: {best.name}")
    
    # Health check
    health = registry.health_check_all()
    print(f"Health: {health}")
    
    # Unregister
    registry.unregister("MockProvider1")
    print(f"After unregister: {registry.list()}")
