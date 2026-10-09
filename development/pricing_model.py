"""
pricing_model.py - Pay-per-use pricing model untuk AI-GEMPA (IDR).

Konsep:
  - Pay-per-use: ditagih per inference/processing, BUKAN langganan bulanan
  - Unit pricing: per pick detection, per event location, per waveform ingested
  - Model tier: CPU/GPU_BASIC/GPU_PREMIUM dengan harga berbeda per inference
  - Metering: track usage real-time, aggregate per workspace per hari
  - Invoice: generate di akhir bulan berdasarkan usage actual
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional
import hashlib
import json


# -----------------------------------------------------------------------------
# Pricing Tier & Unit Rates (IDR)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class UnitRate:
    """Harga per unit processing untuk satu model/provider."""
    provider_id: str
    stage: str
    tier: str                           # CPU | GPU_BASIC | GPU_PREMIUM | EXPERIMENTAL
    price_per_unit: Decimal             # IDR per inference/processing
    unit_name: str                      # "pick detection" | "event location" | "waveform ingested"
    included_quota: int = 0             # quota gratis per bulan (untuk trial/free tier)
    
    def calculate(self, units: int, used_quota: int = 0) -> Decimal:
        """Hitung biaya untuk N units, kurangi quota gratis yang tersisa."""
        remaining_quota = max(0, self.included_quota - used_quota)
        billable = max(0, units - remaining_quota)
        return Decimal(billable) * self.price_per_unit


# Default unit rates (IDR) - CONTOH, sesuaikan dengan cost actual
UNIT_RATES = {
    # INGEST (per 1000 waveform samples ingested)
    ("ingest", "seedlink_v3"): UnitRate("seedlink_v3", "ingest", "CPU", Decimal("5"), "per 1K waveforms"),
    ("ingest", "fdsn_poll"): UnitRate("fdsn_poll", "ingest", "CPU", Decimal("10"), "per 1K waveforms"),
    ("ingest", "push_api"): UnitRate("push_api", "ingest", "CPU", Decimal("3"), "per 1K waveforms"),
    
    # P-PICK (per pick detection inference)
    ("p_pick", "sta_lta"): UnitRate("sta_lta", "p_pick", "CPU", Decimal("50"), "per 1K picks", included_quota=10000),
    ("p_pick", "phasenet"): UnitRate("phasenet", "p_pick", "GPU_BASIC", Decimal("500"), "per 1K picks", included_quota=5000),
    ("p_pick", "eqtransformer"): UnitRate("eqtransformer", "p_pick", "GPU_PREMIUM", Decimal("1500"), "per 1K picks"),
    
    # ASSOCIATION (per cluster/arrival generated)
    ("association", "dbscan_simple"): UnitRate("dbscan_simple", "association", "CPU", Decimal("100"), "per 1K clusters"),
    ("association", "gamma"): UnitRate("gamma", "association", "GPU_BASIC", Decimal("300"), "per 1K clusters"),
    ("association", "pyocto"): UnitRate("pyocto", "association", "EXPERIMENTAL", Decimal("1000"), "per 1K clusters"),
    
    # LOCMAG (per event located)
    ("locmag", "geiger"): UnitRate("geiger", "locmag", "CPU", Decimal("200"), "per 1K events"),
    ("locmag", "nonlinloc"): UnitRate("nonlinloc", "locmag", "GPU_BASIC", Decimal("500"), "per 1K events"),
}

# Sink rates (per message delivered)
SINK_RATES = {
    "ws_ui": Decimal("0"),              # gratis (internal)
    "archive": Decimal("2"),             # per 1K messages archived
    "webhook": Decimal("5"),             # per 1K webhook calls
    "kafka_export": Decimal("10"),       # per 1K messages exported
}

# Storage rates (per GB per hari)
STORAGE_RATE = Decimal("50")            # IDR 50 per GB per hari


# -----------------------------------------------------------------------------
# Usage Record
# -----------------------------------------------------------------------------

@dataclass
class UsageRecord:
    """Record usage untuk satu workspace dalam satu periode (1 hari)."""
    workspace_id: str
    date: str                           # YYYY-MM-DD
    stage_usage: Dict[str, int] = field(default_factory=dict)  # {stage.provider: unit_count}
    sink_usage: Dict[str, int] = field(default_factory=dict)   # {sink: message_count}
    storage_gb_days: Decimal = Decimal("0")
    
    def add_stage_usage(self, stage: str, provider: str, units: int):
        key = f"{stage}.{provider}"
        self.stage_usage[key] = self.stage_usage.get(key, 0) + units
    
    def add_sink_usage(self, sink: str, messages: int):
        self.sink_usage[sink] = self.sink_usage.get(sink, 0) + messages


# -----------------------------------------------------------------------------
# Pricing Calculator
# -----------------------------------------------------------------------------

@dataclass
class PriceBreakdown:
    """Breakdown biaya untuk satu workspace dalam satu periode."""
    workspace_id: str
    period: str                         # "2026-10" (year-month)
    stage_costs: Dict[str, Decimal] = field(default_factory=dict)
    sink_costs: Dict[str, Decimal] = field(default_factory=dict)
    storage_cost: Decimal = Decimal("0")
    subtotal: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")         # PPN 11%
    total: Decimal = Decimal("0")
    currency: str = "IDR"
    
    def add_stage_cost(self, stage: str, provider: str, cost: Decimal):
        key = f"{stage}.{provider}"
        self.stage_costs[key] = cost
        self.subtotal += cost
    
    def add_sink_cost(self, sink: str, cost: Decimal):
        self.sink_costs[sink] = cost
        self.subtotal += cost
    
    def finalize(self, discount_pct: Decimal = Decimal("0"), apply_tax: bool = True):
        """Hitung discount, tax, dan total akhir."""
        self.discount = self.subtotal * discount_pct / Decimal("100")
        taxable = self.subtotal - self.discount + self.storage_cost
        if apply_tax:
            self.tax = taxable * Decimal("0.11")  # PPN 11%
        self.total = taxable + self.tax


class PricingCalculator:
    """Calculator untuk estimasi dan invoice actual dari usage records."""
    
    def __init__(self, unit_rates: Dict = None, sink_rates: Dict = None):
        self.unit_rates = unit_rates or UNIT_RATES
        self.sink_rates = sink_rates or SINK_RATES
    
    def estimate_from_profile(self, profile_dict: Dict, estimated_volume: Dict) -> PriceBreakdown:
        """
        Estimasi biaya dari profile config + estimated volume.
        
        Args:
            profile_dict: compiled pipeline dari pipeline_profile.py
            estimated_volume: {
                "waveforms_per_day": 100000,
                "picks_per_day": 500,
                "events_per_day": 10,
                "storage_gb": 50
            }
        """
        breakdown = PriceBreakdown("estimate", "2026-10")
        
        # Stage costs
        for stage_cfg in profile_dict.get("stages", []):
            stage = stage_cfg["stage"]
            provider = stage_cfg["provider"]
            rate = self.unit_rates.get((stage, provider))
            if not rate:
                continue
            
            # Map stage ke volume key
            volume_map = {
                "ingest": estimated_volume.get("waveforms_per_day", 0) * 30 / 1000,  # monthly, per 1K
                "p_pick": estimated_volume.get("picks_per_day", 0) * 30 / 1000,
                "association": estimated_volume.get("picks_per_day", 0) * 30 / 1000 * 0.1,  # ~10% menjadi cluster
                "locmag": estimated_volume.get("events_per_day", 0) * 30 / 1000,
            }
            units = int(volume_map.get(stage, 0))
            cost = rate.calculate(units)
            breakdown.add_stage_cost(stage, provider, cost)
        
        # Sink costs
        for sink_cfg in profile_dict.get("sinks", []):
            sink = sink_cfg["sink"]
            rate = self.sink_rates.get(sink, Decimal("0"))
            # Estimasi messages = sum of artifacts
            messages = estimated_volume.get("events_per_day", 10) * 30 / 1000  # per 1K
            cost = Decimal(int(messages)) * rate
            breakdown.add_sink_cost(sink, cost)
        
        # Storage
        storage_gb = Decimal(str(estimated_volume.get("storage_gb", 0)))
        breakdown.storage_cost = storage_gb * STORAGE_RATE * Decimal("30")  # 30 hari
        
        breakdown.finalize()
        return breakdown
    
    def calculate_invoice(self, usage_records: List[UsageRecord], workspace_id: str, 
                         month: str, quota_used: Dict[str, int] = None) -> PriceBreakdown:
        """
        Generate invoice dari actual usage records untuk 1 bulan.
        
        Args:
            usage_records: list of UsageRecord untuk workspace dalam 1 bulan
            workspace_id: ID workspace
            month: "2026-10"
            quota_used: {stage.provider: units_used_this_month} untuk track quota gratis
        """
        breakdown = PriceBreakdown(workspace_id, month)
        quota_used = quota_used or {}
        
        # Aggregate usage
        total_stage_usage = {}
        total_sink_usage = {}
        total_storage = Decimal("0")
        
        for rec in usage_records:
            for key, units in rec.stage_usage.items():
                total_stage_usage[key] = total_stage_usage.get(key, 0) + units
            for sink, msgs in rec.sink_usage.items():
                total_sink_usage[sink] = total_sink_usage.get(sink, 0) + msgs
            total_storage += rec.storage_gb_days
        
        # Calculate stage costs
        for key, units in total_stage_usage.items():
            stage, provider = key.split(".", 1)
            rate = self.unit_rates.get((stage, provider))
            if not rate:
                continue
            used_quota = quota_used.get(key, 0)
            cost = rate.calculate(units, used_quota)
            breakdown.add_stage_cost(stage, provider, cost)
            quota_used[key] = used_quota + units  # update quota tracker
        
        # Calculate sink costs
        for sink, msgs in total_sink_usage.items():
            rate = self.sink_rates.get(sink, Decimal("0"))
            cost = Decimal(msgs // 1000) * rate  # per 1K messages
            breakdown.add_sink_cost(sink, cost)
        
        # Storage cost
        breakdown.storage_cost = total_storage * STORAGE_RATE
        
        breakdown.finalize()
        return breakdown


# -----------------------------------------------------------------------------
# Model Catalog dengan Pricing Info
# -----------------------------------------------------------------------------

@dataclass
class ModelInfo:
    """Info model untuk ditampilkan di UI (termasuk pricing)."""
    provider_id: str
    stage: str
    name: str
    tier: str                           # CPU | GPU_BASIC | GPU_PREMIUM | EXPERIMENTAL
    status: str                         # stable | beta | experimental
    price_per_unit: Decimal
    unit_name: str
    free_quota: int
    metrics: Dict[str, str]             # {"precision": "94%", "latency": "180ms"}
    gpu_required: bool
    description: str
    
    def to_dict(self):
        return {
            "provider_id": self.provider_id,
            "stage": self.stage,
            "name": self.name,
            "tier": self.tier,
            "status": self.status,
            "pricing": {
                "unit_price": float(self.price_per_unit),
                "unit_name": self.unit_name,
                "free_quota": self.free_quota,
                "currency": "IDR",
                "example_monthly": self._example_cost()
            },
            "metrics": self.metrics,
            "gpu_required": self.gpu_required,
            "description": self.description
        }
    
    def _example_cost(self) -> str:
        """Contoh biaya untuk volume typical."""
        # Contoh: 500K picks/month
        example_units = {"p_pick": 500, "association": 50, "locmag": 10, "ingest": 1000}
        units = example_units.get(self.stage, 100)
        billable = max(0, units - (self.free_quota // 1000))
        cost = billable * self.price_per_unit
        return f"~Rp {int(cost):,} untuk {units}K {self.unit_name}/bulan"


def build_model_catalog() -> List[ModelInfo]:
    """Build catalog model untuk API /api/v2/models."""
    catalog = [
        # P-PICK models
        ModelInfo("sta_lta", "p_pick", "STA/LTA", "CPU", "stable",
                  Decimal("50"), "per 1K picks", 10000,
                  {"precision": "78%", "recall": "82%", "latency": "50ms"},
                  False, "Classic algorithm, CPU-only, cepat tapi akurasi rendah"),
        ModelInfo("phasenet", "p_pick", "PhaseNet", "GPU_BASIC", "stable",
                  Decimal("500"), "per 1K picks", 5000,
                  {"precision": "94%", "recall": "91%", "latency": "180ms"},
                  False, "Neural network model, GPU optional, akurasi tinggi"),
        ModelInfo("eqtransformer", "p_pick", "EQTransformer", "GPU_PREMIUM", "beta",
                  Decimal("1500"), "per 1K picks", 0,
                  {"precision": "96%", "recall": "93%", "latency": "250ms"},
                  True, "State-of-the-art transformer model, GPU required"),
        
        # ASSOCIATION models
        ModelInfo("dbscan_simple", "association", "DBSCAN Simple", "CPU", "stable",
                  Decimal("100"), "per 1K clusters", 0,
                  {"precision": "85%", "recall": "80%", "latency": "100ms"},
                  False, "Simple clustering algorithm, CPU-only"),
        ModelInfo("gamma", "association", "GaMMA", "GPU_BASIC", "beta",
                  Decimal("300"), "per 1K clusters", 0,
                  {"precision": "92%", "recall": "88%", "latency": "300ms"},
                  False, "Gaussian Mixture Model association"),
        ModelInfo("pyocto", "association", "PyOcto", "EXPERIMENTAL", "experimental",
                  Decimal("1000"), "per 1K clusters", 0,
                  {"precision": "95%", "recall": "90%", "latency": "500ms"},
                  True, "Experimental multi-station octree association"),
        
        # LOCMAG models
        ModelInfo("geiger", "locmag", "Geiger", "CPU", "stable",
                  Decimal("200"), "per 1K events", 0,
                  {"location_error": "5km", "magnitude_error": "0.3", "latency": "50ms"},
                  False, "Classic iterative location algorithm"),
        ModelInfo("nonlinloc", "locmag", "NonLinLoc", "GPU_BASIC", "beta",
                  Decimal("500"), "per 1K events", 0,
                  {"location_error": "2km", "magnitude_error": "0.2", "latency": "200ms"},
                  False, "Grid-based non-linear location"),
    ]
    return catalog


# -----------------------------------------------------------------------------
# Helper: Pricing Estimation from UI Input
# -----------------------------------------------------------------------------

def estimate_from_ui_selection(selected_models: Dict[str, str], 
                               estimated_daily_volume: Dict[str, int]) -> Dict:
    """
    Estimasi biaya dari pilihan user di UI.
    
    Args:
        selected_models: {"p_pick": "phasenet", "association": "dbscan_simple"}
        estimated_daily_volume: {"waveforms": 10000, "picks": 500, "events": 10}
    
    Returns:
        {
            "breakdown": {...},
            "monthly_total": 12500000,
            "currency": "IDR",
            "examples": [...]
        }
    """
    calc = PricingCalculator()
    
    # Build minimal profile dict
    stages = []
    for stage, provider in selected_models.items():
        stages.append({"stage": stage, "provider": provider})
    
    profile = {"stages": stages, "sinks": [{"sink": "ws_ui"}]}
    
    # Estimate
    estimated_volume = {
        "waveforms_per_day": estimated_daily_volume.get("waveforms", 10000),
        "picks_per_day": estimated_daily_volume.get("picks", 500),
        "events_per_day": estimated_daily_volume.get("events", 10),
        "storage_gb": estimated_daily_volume.get("storage_gb", 50)
    }
    
    breakdown = calc.estimate_from_profile(profile, estimated_volume)
    
    return {
        "breakdown": {
            "stages": {k: float(v) for k, v in breakdown.stage_costs.items()},
            "storage": float(breakdown.storage_cost),
            "subtotal": float(breakdown.subtotal),
            "tax": float(breakdown.tax),
            "total": float(breakdown.total)
        },
        "monthly_total": float(breakdown.total),
        "currency": "IDR",
        "period": "monthly",
        "free_quota_applied": True
    }


if __name__ == "__main__":
    # Example: estimate dari UI selection
    selected = {"p_pick": "phasenet", "association": "dbscan_simple", "locmag": "geiger"}
    volume = {"waveforms": 10000, "picks": 500, "events": 10, "storage_gb": 50}
    
    result = estimate_from_ui_selection(selected, volume)
    print("Estimasi biaya bulanan:")
    print(f"  Subtotal: Rp {result['breakdown']['subtotal']:,.0f}")
    print(f"  PPN 11%:  Rp {result['breakdown']['tax']:,.0f}")
    print(f"  Total:    Rp {result['monthly_total']:,.0f}")
    
    # Example: model catalog
    catalog = build_model_catalog()
    print(f"\nModel catalog ({len(catalog)} models):")
    for m in catalog[:3]:
        print(f"  {m.name} ({m.tier}): {m.pricing['example_monthly']}")
