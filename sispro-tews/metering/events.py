"""
metering/events.py - Usage event schema.

Standardisasi event untuk metering system.
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
import json


@dataclass
class UsageEvent:
    """
    Usage event (provider inference).
    
    Fields:
    - event_id: unique event ID
    - workspace_id: workspace yang memanggil
    - user_id: user yang memanggil
    - provider_name: nama provider (STALTA, PhaseNet, dll)
    - module: module (p_pick, association, locmag)
    - cost_idr: biaya dalam IDR
    - latency_ms: latency dalam milliseconds
    - timestamp: kapan event terjadi (Unix epoch)
    - request_id: tracing ID
    - metadata: custom metadata (channels, duration, dll)
    """
    event_id: str
    workspace_id: str
    user_id: str
    provider_name: str
    module: str
    cost_idr: Decimal
    latency_ms: float
    timestamp: float  # Unix epoch
    request_id: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict untuk Kafka."""
        data = asdict(self)
        # Convert Decimal to float untuk JSON
        data["cost_idr"] = float(self.cost_idr)
        return data
    
    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> "UsageEvent":
        """Parse dari JSON."""
        data = json.loads(json_str)
        data["cost_idr"] = Decimal(str(data["cost_idr"]))
        return cls(**data)


@dataclass
class AggregatedUsage:
    """
    Aggregated usage (per-user, per-day).
    
    Fields:
    - workspace_id
    - user_id
    - date: YYYY-MM-DD
    - total_inferences: jumlah inference
    - total_cost_idr: total biaya
    - breakdown_by_provider: dict {provider: cost}
    - breakdown_by_module: dict {module: cost}
    - created_at: timestamp
    """
    workspace_id: str
    user_id: str
    date: str  # YYYY-MM-DD
    total_inferences: int
    total_cost_idr: Decimal
    breakdown_by_provider: Dict[str, Decimal]
    breakdown_by_module: Dict[str, Decimal]
    created_at: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict untuk MongoDB."""
        return {
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "date": self.date,
            "total_inferences": self.total_inferences,
            "total_cost_idr": float(self.total_cost_idr),
            "breakdown_by_provider": {k: float(v) for k, v in self.breakdown_by_provider.items()},
            "breakdown_by_module": {k: float(v) for k, v in self.breakdown_by_module.items()},
            "created_at": self.created_at
        }
