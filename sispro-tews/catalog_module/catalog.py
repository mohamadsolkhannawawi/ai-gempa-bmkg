"""
catalog_module/catalog.py - ProviderCatalog loader untuk manifest.yaml + rates.yaml.

Load katalog model AI + tarif dari YAML files, expose via Python API.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional
import yaml


@dataclass
class ProviderManifest:
    """Provider metadata dari manifest.yaml."""
    id: str
    name: str
    description: str
    stage: str              # p_pick | association | locmag
    tier: str               # CPU | GPU_BASIC | GPU_PREMIUM
    repo: str
    supported_channels: List[str]
    min_sample_rate: float
    max_sample_rate: float
    input_shape: str
    output_format: str
    docker_image: str
    health_check_url: str
    status: str             # active | deprecated | experimental
    tags: List[str]


@dataclass
class ProviderRate:
    """Tarif provider dari rates.yaml."""
    provider: str
    tier: str
    price_per_1k_units: Decimal     # per 1K picks/clusters/events
    free_quota_monthly: int
    description: str


class ProviderCatalog:
    """Katalog model AI + tarif (singleton pattern)."""
    
    _instance = None
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.manifest_path = data_dir / "manifest.yaml"
        self.rates_path = data_dir / "rates.yaml"
        
        self.providers: Dict[str, ProviderManifest] = {}
        self.rates: Dict[str, ProviderRate] = {}
        self.tier_info: Dict[str, dict] = {}
        
        self._load_manifest()
        self._load_rates()
    
    @classmethod
    def instance(cls, data_dir: Optional[Path] = None) -> ProviderCatalog:
        """Singleton instance."""
        if cls._instance is None:
            if data_dir is None:
                # Default: catalog_module/data/
                data_dir = Path(__file__).parent / "data"
            cls._instance = cls(data_dir)
        return cls._instance
    
    def _load_manifest(self):
        """Load manifest.yaml → dict."""
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        for provider_id, manifest in data["providers"].items():
            self.providers[provider_id] = ProviderManifest(
                id=provider_id,
                name=manifest["name"],
                description=manifest["description"],
                stage=manifest["stage"],
                tier=manifest["tier"],
                repo=manifest["repo"],
                supported_channels=manifest["supported_channels"],
                min_sample_rate=manifest["min_sample_rate"],
                max_sample_rate=manifest["max_sample_rate"],
                input_shape=manifest["input_shape"],
                output_format=manifest["output_format"],
                docker_image=manifest["docker_image"],
                health_check_url=manifest["health_check_url"],
                status=manifest["status"],
                tags=manifest.get("tags", [])
            )
    
    def _load_rates(self):
        """Load rates.yaml → dict."""
        with open(self.rates_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Pick pricing
        for provider_id, rate in data.get("pick_pricing", {}).items():
            self.rates[provider_id] = ProviderRate(
                provider=provider_id,
                tier=rate["tier"],
                price_per_1k_units=Decimal(str(rate["price_per_1k_picks"])),
                free_quota_monthly=rate["free_quota_monthly"],
                description=rate["description"]
            )
        
        # Association pricing
        for provider_id, rate in data.get("association_pricing", {}).items():
            self.rates[provider_id] = ProviderRate(
                provider=provider_id,
                tier=rate["tier"],
                price_per_1k_units=Decimal(str(rate["price_per_1k_clusters"])),
                free_quota_monthly=rate["free_quota_monthly"],
                description=rate["description"]
            )
        
        # Locmag pricing
        for provider_id, rate in data.get("locmag_pricing", {}).items():
            self.rates[provider_id] = ProviderRate(
                provider=provider_id,
                tier=rate["tier"],
                price_per_1k_units=Decimal(str(rate["price_per_1k_events"])),
                free_quota_monthly=rate["free_quota_monthly"],
                description=rate["description"]
            )
        
        # Tier info (for UI)
        self.tier_info = data.get("tier_info", {})
    
    def get_provider(self, provider_id: str) -> Optional[ProviderManifest]:
        """Get provider manifest by ID."""
        return self.providers.get(provider_id)
    
    def get_rate(self, provider_id: str) -> Optional[ProviderRate]:
        """Get provider rate by ID."""
        return self.rates.get(provider_id)
    
    def list_providers(self, stage: Optional[str] = None, tier: Optional[str] = None) -> List[ProviderManifest]:
        """List providers, optionally filter by stage/tier."""
        result = list(self.providers.values())
        if stage:
            result = [p for p in result if p.stage == stage]
        if tier:
            result = [p for p in result if p.tier == tier]
        return result
    
    def list_by_stage(self) -> Dict[str, List[ProviderManifest]]:
        """Group providers by stage."""
        stages = {}
        for provider in self.providers.values():
            if provider.stage not in stages:
                stages[provider.stage] = []
            stages[provider.stage].append(provider)
        return stages
    
    def estimate_cost(self, provider_id: str, units: int, free_quota: int = 0) -> Decimal:
        """Estimate cost for N units (picks/clusters/events)."""
        rate = self.get_rate(provider_id)
        if not rate:
            return Decimal("0")
        
        billable = max(0, units - free_quota)
        cost = (Decimal(billable) / 1000) * rate.price_per_1k_units
        return cost.quantize(Decimal("0.01"))  # round to 2 decimal places


if __name__ == "__main__":
    # Example usage
    catalog = ProviderCatalog.instance()
    
    print(f"Loaded {len(catalog.providers)} providers:")
    for stage, providers in catalog.list_by_stage().items():
        print(f"\n{stage}:")
        for p in providers:
            rate = catalog.get_rate(p.id)
            price = rate.price_per_1k_units if rate else "N/A"
            print(f"  - {p.name} ({p.tier}): Rp {price}/1K")
    
    # Cost estimation
    print("\n--- Cost Estimation ---")
    cost_sta = catalog.estimate_cost("sta_lta", 15000, free_quota=10000)
    print(f"STA/LTA 15K picks (10K free): Rp {cost_sta}")
    
    cost_phasenet = catalog.estimate_cost("phasenet", 50000, free_quota=2000)
    print(f"PhaseNet 50K picks (2K free): Rp {cost_phasenet}")
