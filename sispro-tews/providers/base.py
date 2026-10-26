"""
providers/base.py - BaseProvider abstract class.

Interface untuk semua AI providers:
1. StaLTAManual
2. PhaseNet (CPU/GPU)
3. EQTransformer
4. DBSCAN
5. GaMMA
6. PyOcto
7. Geiger
8. NonLinLoc

Setiap provider harus implement:
- `infer()` — run inference + return picks/clusters/events
- `supports()` — check capability
- `metadata()` — model + config
- `cost_estimate()` — biaya inference (IDR)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from decimal import Decimal
import time

from core.event import Pick, Event, Cluster
from core.profile_service import ProfileConfig


class DeviceType(Enum):
    """Device type untuk provider."""
    CPU = "cpu"
    GPU = "gpu"
    TPU = "tpu"


class InferenceRequest:
    """Request untuk inference."""
    
    def __init__(
        self,
        data: bytes,
        sample_rate_hz: float,
        n_stations: int,
        metadata: Dict[str, Any] = None
    ):
        self.data = data
        self.sample_rate_hz = sample_rate_hz
        self.n_stations = n_stations
        self.metadata = metadata or {}
        self.request_time = time.time()
    
    @property
    def duration_seconds(self) -> float:
        """Calculate duration dari data."""
        # For now placeholder
        if "duration" in self.metadata:
            return self.metadata["duration"]
        return 60.0
    
    @property
    def channels_per_station(self) -> int:
        """Channel count per station (default 3)."""
        return self.metadata.get("channels_per_station", 3)


class BaseProvider(ABC):
    """
    Base class untuk semua AI providers.
    
    Semua concrete provider extends ini.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._initialized = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'STALTA', 'PhaseNet')."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Provider version (e.g., 'v1.0')."""
        pass
    
    @property
    @abstractmethod
    def device_type(self) -> DeviceType:
        """Device type yang diperlukan (CPU/GPU)."""
        pass
    
    @property
    def description(self) -> str:
        """Description provider."""
        return self.config.get("description", "")
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize provider (load model, warmup).
        Returns True jika sukses.
        """
        pass
    
    @abstractmethod
    def supports(self, request: InferenceRequest) -> bool:
        """
        Check apakah provider mendukung request ini.
        
        Contoh:
        - PhaseNet: hanya support 3 channels per station
        - EQTransformer: hanya support GPU
        - DBSCAN: hanya support picks data
        """
        pass
    
    @abstractmethod
    def infer(self, request: InferenceRequest) -> Dict[str, Any]:
        """
        Run inference.
        
        Returns dict dengan keys:
        - "picks": List[Pick]
        - "clusters": List[Cluster]
        - "events": List[Event]
        - "latency_ms": float
        - "cost_idr": Decimal
        - "metadata": Dict[str, Any]
        """
        pass
    
    def cost_estimate(self, request: InferenceRequest) -> Decimal:
        """
        Estimate cost untuk request (IDR).
        Default: return config price per inference.
        """
        price_per_infer = self.config.get("price_per_infer_idr", Decimal("0"))
        return price_per_infer
    
    def metadata(self) -> Dict[str, Any]:
        """
        Return provider metadata.
        
        Contoh:
        - model_size_mb
        - framework
        - memory_required_gb
        - max_channels
        - max_duration_seconds
        """
        return {
            "name": self.name,
            "version": self.version,
            "device_type": self.device_type.value,
            "config": self.config,
            "description": self.description,
            "price_per_infer_idr": self.config.get("price_per_infer_idr", Decimal("0"))
        }
    
    def health_check(self) -> Tuple[bool, str]:
        """
        Health check.
        Returns (is_healthy, message).
        """
        if not self._initialized:
            return False, "Provider not initialized"
        
        return True, "OK"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.version}) [{self.device_type.value}]"


class MockProvider(BaseProvider):
    """Mock provider untuk testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._infer_count = 0
    
    @property
    def name(self) -> str:
        return "MockProvider"
    
    @property
    def version(self) -> str:
        return "v1.0"
    
    @property
    def device_type(self) -> DeviceType:
        return DeviceType.CPU
    
    def initialize(self) -> bool:
        self._initialized = True
        return True
    
    def supports(self, request: InferenceRequest) -> bool:
        return True
    
    def infer(self, request: InferenceRequest) -> Dict[str, Any]:
        """Return dummy picks/clusters/events."""
        self._infer_count += 1
        
        # Generate mock picks
        picks = [
            Pick(
                id=f"pick_{self._infer_count}_{i}",
                station="STA1",
                channel="BHZ",
                timestamp=request.request_time + i * 0.1,
                probability=0.9,
                amplitude=0.5,
                phase="P"
            )
            for i in range(10)
        ]
        
        # Generate mock clusters
        clusters = [
            Cluster(
                id=f"cluster_{self._infer_count}_{i}",
                picks=[p.id for p in picks[i:i+2]],
                centroid=picks[i].timestamp,
                radius=0.1
            )
            for i in range(5)
        ]
        
        # Generate mock events
        events = [
            Event(
                id=f"event_{self._infer_count}_{i}",
                origin_time=request.request_time + i * 2.0,
                latitude=0.5 + i * 0.1,
                longitude=100.5 + i * 0.1,
                depth_km=10.0,
                magnitude=2.0 + i * 0.5,
                picks=[picks[i].id],
                confidence=0.8
            )
            for i in range(3)
        ]
        
        latency_ms = 150.0
        
        return {
            "picks": picks,
            "clusters": clusters,
            "events": events,
            "latency_ms": latency_ms,
            "cost_idr": self.cost_estimate(request),
            "metadata": {
                "infer_count": self._infer_count,
                "data_size_bytes": len(request.data)
            }
        }
    
    def cost_estimate(self, request: InferenceRequest) -> Decimal:
        """Override: return Decimal."""
        return Decimal("100")  # 100 IDR per inference


if __name__ == "__main__":
    """Test BaseProvider interface."""
    mock = MockProvider()
    
    # Initialize
    assert mock.initialize() == True
    
    # Check metadata
    meta = mock.metadata()
    print(f"Provider: {mock}")
    print(f"Metadata: {meta}")
    
    # Create request
    request = InferenceRequest(
        data=b"test",
        sample_rate_hz=100.0,
        n_stations=3,
        metadata={"duration": 60.0}
    )
    
    # Cost estimate
    cost = mock.cost_estimate(request)
    print(f"Cost estimate: {cost} IDR")
    
    # Infer
    result = mock.infer(request)
    print(f"Result: {len(result['picks'])} picks, {len(result['clusters'])} clusters, {len(result['events'])} events")
    print(f"Latency: {result['latency_ms']} ms")
    
    # Health check
    healthy, msg = mock.health_check()
    print(f"Health: {healthy} ({msg})")
