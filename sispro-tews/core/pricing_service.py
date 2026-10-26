"""
core/pricing_service.py - PricingService domain (estimate + invoice).

Tanggung jawab:
1. Hitung biaya monthly/quarterly/annual (IDR)
2. Generate invoice PDF (template)
3. Apply PPN 11%
4. Apply free quota per tier
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class BillingPeriod(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class InvoiceItemType(str, Enum):
    PICKS = "picks"
    CLUSTERS = "clusters"
    EVENTS = "events"
    INFERENCE = "inference"  # per-hari compute cost
    STORAGE = "storage"      # per-GB per-month
    SUPPORT = "support"      # optional support fee


@dataclass
class InvoiceItem:
    """Item dalam invoice."""
    type: InvoiceItemType
    description: str
    quantity: Decimal
    unit_price_idr: Decimal          # price per unit (IDR)
    amount_idr: Decimal              # quantity * unit_price_idr
    
    def __post_init__(self):
        if not self.amount_idr:
            self.amount_idr = self.quantity * self.unit_price_idr


@dataclass
class UsageRecord:
    """Usage snapshot per billing period."""
    workspace_id: str
    billing_period: BillingPeriod
    period_start: date
    period_end: date
    
    picks_count: int = 0
    clusters_count: int = 0
    events_count: int = 0
    inference_hours: float = 0.0     # GPU hours
    storage_gb: float = 0.0
    
    # Per-provider usage
    sta_lta_picks: int = 0
    phasenet_picks: int = 0
    eqtransformer_picks: int = 0
    dbscan_clusters: int = 0
    gamma_clusters: int = 0
    geiger_events: int = 0
    pyocto_events: int = 0
    
    def total_picks(self) -> int:
        return self.sta_lta_picks + self.phasenet_picks + self.eqtransformer_picks
    
    def total_clusters(self) -> int:
        return self.dbscan_clusters + self.gamma_clusters
    
    def total_events(self) -> int:
        return self.geiger_events + self.pyocto_events


@dataclass
class Invoice:
    """Invoice untuk billing period."""
    id: str = field(default_factory=lambda: str(uuid4()))
    workspace_id: str = ""
    invoice_number: str = ""         # INV-2026-10-001
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    period_start: date = field(default_factory=lambda: date.today())
    period_end: date = field(default_factory=lambda: date.today())
    status: InvoiceStatus = InvoiceStatus.DRAFT
    
    # Items
    items: List[InvoiceItem] = field(default_factory=list)
    
    # Summary
    subtotal_idr: Decimal = Decimal("0")
    ppn_percent: Decimal = Decimal("11.0")   # PPN 11%
    ppn_amount_idr: Decimal = Decimal("0")
    total_idr: Decimal = Decimal("0")
    
    # Metadata
    issued_date: Optional[date] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # PDF
    pdf_url: Optional[str] = None
    pdf_generated_at: Optional[datetime] = None
    
    def calculate_totals(self):
        """Calculate subtotal, PPN, total."""
        self.subtotal_idr = Decimal("0")
        
        for item in self.items:
            self.subtotal_idr += item.amount_idr
        
        # Round subtotal
        self.subtotal_idr = self.subtotal_idr.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        
        # PPN 11%
        self.ppn_amount_idr = (self.subtotal_idr * self.ppn_percent / Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        
        self.total_idr = self.subtotal_idr + self.ppn_amount_idr
    
    def add_item(self, item: InvoiceItem):
        """Add item + recalc totals."""
        self.items.append(item)
        self.calculate_totals()
    
    def mark_issued(self):
        """Mark invoice as ISSUED."""
        if self.status != InvoiceStatus.DRAFT:
            raise ValueError(f"Cannot issue invoice with status {self.status}")
        
        self.status = InvoiceStatus.ISSUED
        self.issued_date = date.today()
        
        # Set due date (30 days)
        self.due_date = self.issued_date + timedelta(days=30)
        
        # Generate PDF (TODO)
        self.pdf_generated_at = datetime.now(timezone.utc)
        self.pdf_url = f"/invoices/{self.id}.pdf"
        
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_paid(self, paid_date: Optional[date] = None):
        """Mark invoice as PAID."""
        if self.status != InvoiceStatus.ISSUED:
            raise ValueError(f"Cannot pay invoice with status {self.status}")
        
        self.status = InvoiceStatus.PAID
        self.paid_date = paid_date or date.today()
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_overdue(self):
        """Mark invoice as OVERDUE."""
        if self.status != InvoiceStatus.ISSUED:
            raise ValueError(f"Cannot mark overdue invoice with status {self.status}")
        
        self.status = InvoiceStatus.OVERDUE
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict:
        """Serialize untuk MongoDB."""
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "invoice_number": self.invoice_number,
            "billing_period": self.billing_period.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "status": self.status.value,
            "items": [
                {
                    "type": item.type.value,
                    "description": item.description,
                    "quantity": str(item.quantity),
                    "unit_price_idr": str(item.unit_price_idr),
                    "amount_idr": str(item.amount_idr)
                }
                for item in self.items
            ],
            "subtotal_idr": str(self.subtotal_idr),
            "ppn_percent": str(self.ppn_percent),
            "ppn_amount_idr": str(self.ppn_amount_idr),
            "total_idr": str(self.total_idr),
            "issued_date": self.issued_date.isoformat() if self.issued_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "paid_date": self.paid_date.isoformat() if self.paid_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "pdf_url": self.pdf_url,
            "pdf_generated_at": self.pdf_generated_at.isoformat() if self.pdf_generated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> Invoice:
        """Deserialize dari MongoDB."""
        items = []
        for item_data in data.get("items", []):
            items.append(InvoiceItem(
                type=InvoiceItemType(item_data["type"]),
                description=item_data["description"],
                quantity=Decimal(item_data["quantity"]),
                unit_price_idr=Decimal(item_data["unit_price_idr"]),
                amount_idr=Decimal(item_data["amount_idr"])
            ))
        
        invoice = cls(
            id=data.get("id", str(uuid4())),
            workspace_id=data.get("workspace_id", ""),
            invoice_number=data.get("invoice_number", ""),
            billing_period=BillingPeriod(data.get("billing_period", "monthly")),
            period_start=date.fromisoformat(data.get("period_start", date.today().isoformat())),
            period_end=date.fromisoformat(data.get("period_end", date.today().isoformat())),
            status=InvoiceStatus(data.get("status", "draft")),
            items=items,
            subtotal_idr=Decimal(data.get("subtotal_idr", "0")),
            ppn_percent=Decimal(data.get("ppn_percent", "11.0")),
            ppn_amount_idr=Decimal(data.get("ppn_amount_idr", "0")),
            total_idr=Decimal(data.get("total_idr", "0")),
            pdf_url=data.get("pdf_url"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(timezone.utc).isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now(timezone.utc).isoformat()))
        )
        
        if data.get("issued_date"):
            invoice.issued_date = date.fromisoformat(data["issued_date"])
        if data.get("due_date"):
            invoice.due_date = date.fromisoformat(data["due_date"])
        if data.get("paid_date"):
            invoice.paid_date = date.fromisoformat(data["paid_date"])
        if data.get("pdf_generated_at"):
            invoice.pdf_generated_at = datetime.fromisoformat(data["pdf_generated_at"])
        
        return invoice


class PricingService:
    """Business logic untuk pricing + invoice generation."""
    
    def __init__(self, catalog_client=None, usage_repo=None, invoice_repo=None):
        self.catalog_client = catalog_client  # lookup rates
        self.usage_repo = usage_repo
        self.invoice_repo = invoice_repo
    
    def estimate_cost(
        self,
        workspace_id: str,
        period: BillingPeriod = BillingPeriod.MONTHLY,
        custom_usage: Optional[UsageRecord] = None
    ) -> Dict[str, Any]:
        """
        Estimate cost untuk workspace + period.
        
        Jika custom_usage diberikan, pakai itu.
        Jika tidak, ambil historical usage dari usage_repo.
        """
        # Dummy rates (TODO: lookup dari catalog)
        rates = {
            "sta_lta_pick": Decimal("5"),       # IDR per pick
            "phasenet_pick": Decimal("10"),
            "eqtransformer_pick": Decimal("12"),
            "dbscan_cluster": Decimal("20"),
            "gamma_cluster": Decimal("30"),
            "geiger_event": Decimal("100"),
            "pyocto_event": Decimal("120"),
            "inference_hour": Decimal("5000"),   # per GPU hour
            "storage_gb_month": Decimal("1000")  # per GB per month
        }
        
        # Dummy usage jika tidak ada
        usage = custom_usage or UsageRecord(
            workspace_id=workspace_id,
            billing_period=period,
            period_start=date.today(),
            period_end=date.today(),
            picks_count=10000,
            clusters_count=2000,
            events_count=1000,
            inference_hours=24.0,
            storage_gb=50.0
        )
        
        # Calculate items
        items = []
        
        # Picks
        if usage.sta_lta_picks > 0:
            items.append(InvoiceItem(
                type=InvoiceItemType.PICKS,
                description=f"STA/LTA picks ({usage.sta_lta_picks} units)",
                quantity=Decimal(usage.sta_lta_picks),
                unit_price_idr=rates["sta_lta_pick"]
            ))
        
        if usage.phasenet_picks > 0:
            items.append(InvoiceItem(
                type=InvoiceItemType.PICKS,
                description=f"PhaseNet picks ({usage.phasenet_picks} units)",
                quantity=Decimal(usage.phasenet_picks),
                unit_price_idr=rates["phasenet_pick"]
            ))
        
        if usage.eqtransformer_picks > 0:
            items.append(InvoiceItem(
                type=InvoiceItemType.PICKS,
                description=f"EQTransformer picks ({usage.eqtransformer_picks} units)",
                quantity=Decimal(usage.eqtransformer_picks),
                unit_price_idr=rates["eqtransformer_pick"]
            ))
        
        # Clusters
        if usage.dbscan_clusters > 0:
            items.append(InvoiceItem(
                type=InvoiceItemType.CLUSTERS,
                description=f"DBSCAN clusters ({usage.dbscan_clusters} units)",
                quantity=Decimal(usage.dbscan_clusters),
                unit_price_idr=rates["dbscan_cluster"]
            ))
        
        if usage.gamma_clusters > 0:
            items.append(InvoiceItem(
                type=InvoiceItemType.CLUSTERS,
                description=f"GaMMA clusters ({usage.gamma_clusters} units)",
                quantity=Decimal(usage.gamma_clusters),
                unit_price_idr=rates["gamma_cluster"]
            ))
        
        # Events
        if usage.geiger_events > 0:
            items.append(InvoiceItem(
                type=InvoiceItemType.EVENTS,
                description=f"Geiger events ({usage.geiger_events} units)",
                quantity=Decimal(usage.geiger_events),
                unit_price_idr=rates["geiger_event"]
            ))
        
        if usage.pyocto_events > 0:
            items.append(InvoiceItem(
                type=InvoiceItemType.EVENTS,
                description=f"PyOcto events ({usage.pyocto_events} units)",
                quantity=Decimal(usage.pyocto_events),
                unit_price_idr=rates["pyocto_event"]
            ))
        
        # Inference hours
        if usage.inference_hours > 0:
            items.append(InvoiceItem(
                type=InvoiceItemType.INFERENCE,
                description=f"GPU inference ({usage.inference_hours:.1f} hours)",
                quantity=Decimal(str(usage.inference_hours)),
                unit_price_idr=rates["inference_hour"]
            ))
        
        # Storage
        if usage.storage_gb > 0:
            items.append(InvoiceItem(
                type=InvoiceItemType.STORAGE,
                description=f"Storage ({usage.storage_gb:.1f} GB)",
                quantity=Decimal(str(usage.storage_gb)),
                unit_price_idr=rates["storage_gb_month"]
            ))
        
        # Create invoice (draft)
        invoice = Invoice(
            workspace_id=workspace_id,
            billing_period=period,
            period_start=usage.period_start,
            period_end=usage.period_end,
            status=InvoiceStatus.DRAFT
        )
        
        for item in items:
            invoice.add_item(item)
        
        return {
            "workspace_id": workspace_id,
            "period": period.value,
            "usage_summary": {
                "total_picks": usage.total_picks(),
                "total_clusters": usage.total_clusters(),
                "total_events": usage.total_events(),
                "inference_hours": usage.inference_hours,
                "storage_gb": usage.storage_gb
            },
            "items": [
                {
                    "description": item.description,
                    "quantity": float(item.quantity),
                    "unit_price_idr": float(item.unit_price_idr),
                    "amount_idr": float(item.amount_idr)
                }
                for item in invoice.items
            ],
            "subtotal_idr": float(invoice.subtotal_idr),
            "ppn_percent": float(invoice.ppn_percent),
            "ppn_amount_idr": float(invoice.ppn_amount_idr),
            "total_idr": float(invoice.total_idr),
            "currency": "IDR"
        }
    
    def generate_invoice(
        self,
        workspace_id: str,
        period: BillingPeriod,
        period_start: date,
        period_end: date,
        usage: UsageRecord
    ) -> Invoice:
        """
        Generate invoice real dari usage.
        
        Steps:
        1. Hitung cost
        2. Apply free quota
        3. Generate invoice number
        4. Create Invoice object
        5. Mark as ISSUED
        """
        # Estimate
        estimate = self.estimate_cost(workspace_id, period, usage)
        
        # Apply free quota (first 1K picks free, etc.)
        # TODO: implement free quota per tier
        
        # Generate invoice number
        now = datetime.now(timezone.utc)
        invoice_number = f"INV-{now.year}-{now.month:02d}-{now.day:02d}-{now.hour:02d}{now.minute:02d}"
        
        # Build invoice
        invoice = Invoice(
            workspace_id=workspace_id,
            invoice_number=invoice_number,
            billing_period=period,
            period_start=period_start,
            period_end=period_end
        )
        
        # Add items
        for item_data in estimate["items"]:
            invoice.add_item(InvoiceItem(
                type=InvoiceItemType.PICKS,  # placeholder
                description=item_data["description"],
                quantity=Decimal(str(item_data["quantity"])),
                unit_price_idr=Decimal(str(item_data["unit_price_idr"]))
            ))
        
        # Mark as issued
        invoice.mark_issued()
        
        return invoice


if __name__ == "__main__":
    service = PricingService()
    
    # Estimate
    estimate = service.estimate_cost("ws_001", BillingPeriod.MONTHLY)
    
    print("=== Cost Estimate ===")
    print(f"Workspace: {estimate['workspace_id']}")
    print(f"Period: {estimate['period']}")
    print(f"Subtotal: IDR {estimate['subtotal_idr']:,.0f}")
    print(f"PPN 11%: IDR {estimate['ppn_amount_idr']:,.0f}")
    print(f"Total: IDR {estimate['total_idr']:,.0f}")
    print("\nItems:")
    for item in estimate["items"]:
        print(f"  - {item['description']}: {item['quantity']} × IDR {item['unit_price_idr']:,.0f} = IDR {item['amount_idr']:,.0f}")
    
    # Generate invoice
    usage = UsageRecord(
        workspace_id="ws_001",
        billing_period=BillingPeriod.MONTHLY,
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        sta_lta_picks=5000,
        phasenet_picks=3000,
        eqtransformer_picks=2000,
        dbscan_clusters=1500,
        gamma_clusters=500,
        geiger_events=800,
        pyocto_events=200,
        inference_hours=24.0,
        storage_gb=50.0
    )
    
    invoice = service.generate_invoice(
        workspace_id="ws_001",
        period=BillingPeriod.MONTHLY,
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        usage=usage
    )
    
    print("\n=== Generated Invoice ===")
    print(f"Invoice #: {invoice.invoice_number}")
    print(f"Status: {invoice.status}")
    print(f"Due date: {invoice.due_date}")
    print(f"Total: IDR {invoice.total_idr:,.0f}")
    print(f"PDF URL: {invoice.pdf_url}")
