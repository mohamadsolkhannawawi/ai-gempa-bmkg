"""
tests/unit/test_pricing_service.py - Unit tests untuk PricingService domain.
"""
import sys
sys.path.insert(0, "..")

from datetime import date
from decimal import Decimal
import pytest

from core.pricing_service import (
    PricingService, Invoice, InvoiceItem, InvoiceStatus, BillingPeriod,
    InvoiceItemType, UsageRecord
)
from infrastructure.repositories.invoice_repo import InMemoryInvoiceRepository


class TestInvoice:
    """Test Invoice domain."""
    
    def test_create_invoice_basic(self):
        """Create new invoice."""
        invoice = Invoice(
            workspace_id="ws_001",
            invoice_number="INV-2026-10-001",
            billing_period=BillingPeriod.MONTHLY,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31)
        )
        
        assert invoice.workspace_id == "ws_001"
        assert invoice.invoice_number == "INV-2026-10-001"
        assert invoice.status == InvoiceStatus.DRAFT
        assert invoice.total_idr == Decimal("0")
    
    def test_add_item_and_calculate(self):
        """Add items dan calculate totals."""
        invoice = Invoice(
            workspace_id="ws_001",
            invoice_number="INV-2026-10-001",
            billing_period=BillingPeriod.MONTHLY
        )
        
        item1 = InvoiceItem(
            type=InvoiceItemType.PICKS,
            description="STA/LTA picks (5000 units)",
            quantity=Decimal("5000"),
            unit_price_idr=Decimal("5")
        )
        
        item2 = InvoiceItem(
            type=InvoiceItemType.CLUSTERS,
            description="DBSCAN clusters (1500 units)",
            quantity=Decimal("1500"),
            unit_price_idr=Decimal("20")
        )
        
        invoice.add_item(item1)
        invoice.add_item(item2)
        
        # Verify calculation
        # 5000*5 + 1500*20 = 25000 + 30000 = 55000
        assert invoice.subtotal_idr == Decimal("55000")
        
        # PPN 11% = 55000 * 0.11 = 6050
        assert invoice.ppn_amount_idr == Decimal("6050")
        
        # Total = 55000 + 6050 = 61050
        assert invoice.total_idr == Decimal("61050")
    
    def test_mark_issued(self):
        """Transition DRAFT → ISSUED."""
        invoice = Invoice(
            workspace_id="ws_001",
            invoice_number="INV-2026-10-001"
        )
        
        invoice.mark_issued()
        
        assert invoice.status == InvoiceStatus.ISSUED
        assert invoice.issued_date is not None
        assert invoice.due_date is not None
        assert invoice.pdf_url is not None
    
    def test_mark_issued_fails_if_not_draft(self):
        """Mark issued gagal jika bukan DRAFT."""
        invoice = Invoice(
            workspace_id="ws_001",
            invoice_number="INV-2026-10-001",
            status=InvoiceStatus.ISSUED
        )
        
        with pytest.raises(ValueError, match="Cannot issue invoice"):
            invoice.mark_issued()
    
    def test_mark_paid(self):
        """Transition ISSUED → PAID."""
        invoice = Invoice(
            workspace_id="ws_001",
            invoice_number="INV-2026-10-001",
            status=InvoiceStatus.ISSUED,
            issued_date=date(2026, 10, 1)
        )
        
        invoice.mark_paid(date(2026, 10, 15))
        
        assert invoice.status == InvoiceStatus.PAID
        assert invoice.paid_date == date(2026, 10, 15)
    
    def test_mark_paid_fails_if_not_issued(self):
        """Mark paid gagal jika bukan ISSUED."""
        invoice = Invoice(
            workspace_id="ws_001",
            invoice_number="INV-2026-10-001"
        )
        
        with pytest.raises(ValueError, match="Cannot pay invoice"):
            invoice.mark_paid()
    
    def test_invoice_serialization(self):
        """Serialize invoice to dict."""
        invoice = Invoice(
            workspace_id="ws_001",
            invoice_number="INV-2026-10-001",
            billing_period=BillingPeriod.MONTHLY,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31)
        )
        
        data = invoice.to_dict()
        
        assert "id" in data
        assert data["workspace_id"] == "ws_001"
        assert data["invoice_number"] == "INV-2026-10-001"
        assert data["status"] == "draft"
        assert "items" in data
        assert "total_idr" in data
    
    def test_invoice_deserialization(self):
        """Deserialize invoice from dict."""
        original = Invoice(
            workspace_id="ws_001",
            invoice_number="INV-2026-10-001"
        )
        
        data = original.to_dict()
        restored = Invoice.from_dict(data)
        
        assert restored.id == original.id
        assert restored.workspace_id == "ws_001"
        assert restored.invoice_number == "INV-2026-10-001"
        assert restored.status == InvoiceStatus.DRAFT


class TestInvoiceItem:
    """Test InvoiceItem class."""
    
    def test_invoice_item_amount_calculation(self):
        """Invoice item calculate amount."""
        item = InvoiceItem(
            type=InvoiceItemType.PICKS,
            description="Test picks",
            quantity=Decimal("1000"),
            unit_price_idr=Decimal("10")
        )
        
        # Amount should be calculated
        assert item.amount_idr == Decimal("10000")
    
    def test_invoice_item_custom_amount(self):
        """Invoice item dengan custom amount."""
        item = InvoiceItem(
            type=InvoiceItemType.PICKS,
            description="Test picks",
            quantity=Decimal("1000"),
            unit_price_idr=Decimal("10"),
            amount_idr=Decimal("9500")  # discount
        )
        
        # Keep custom amount
        assert item.amount_idr == Decimal("9500")


class TestUsageRecord:
    """Test UsageRecord class."""
    
    def test_usage_record_totals(self):
        """Usage record calculate totals."""
        usage = UsageRecord(
            workspace_id="ws_001",
            billing_period=BillingPeriod.MONTHLY,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            sta_lta_picks=3000,
            phasenet_picks=2000,
            eqtransformer_picks=1000,
            dbscan_clusters=1000,
            gamma_clusters=500,
            geiger_events=600,
            pyocto_events=200
        )
        
        assert usage.total_picks() == 6000
        assert usage.total_clusters() == 1500
        assert usage.total_events() == 800


class TestPricingService:
    """Test PricingService business logic."""
    
    def test_estimate_cost_basic(self):
        """Estimate cost untuk workspace."""
        service = PricingService()
        
        estimate = service.estimate_cost("ws_001", BillingPeriod.MONTHLY)
        
        assert "workspace_id" in estimate
        assert estimate["workspace_id"] == "ws_001"
        assert estimate["period"] == "monthly"
        assert "subtotal_idr" in estimate
        assert "ppn_amount_idr" in estimate
        assert "total_idr" in estimate
        assert estimate["currency"] == "IDR"
    
    def test_estimate_cost_with_custom_usage(self):
        """Estimate cost dengan custom usage."""
        service = PricingService()
        
        custom_usage = UsageRecord(
            workspace_id="ws_001",
            billing_period=BillingPeriod.MONTHLY,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            sta_lta_picks=10000,
            phasenet_picks=0,
            eqtransformer_picks=0,
            dbscan_clusters=2000,
            gamma_clusters=0,
            geiger_events=1000,
            pyocto_events=0,
            inference_hours=0.0,
            storage_gb=100.0
        )
        
        estimate = service.estimate_cost("ws_001", BillingPeriod.MONTHLY, custom_usage)
        
        # Verify items
        assert len(estimate["items"]) > 0
        
        # 10000 picks @ 5 IDR = 50000
        # 2000 clusters @ 20 IDR = 40000
        # 1000 events @ 100 IDR = 100000
        # 100 GB storage @ 1000 IDR = 100000
        # Subtotal = 290000
        # PPN 11% = 31900
        # Total = 321900
        
        assert estimate["subtotal_idr"] > 0
        assert estimate["ppn_amount_idr"] > 0
        assert estimate["total_idr"] > estimate["subtotal_idr"]
    
    def test_generate_invoice(self):
        """Generate invoice dari usage."""
        repo = InMemoryInvoiceRepository()
        service = PricingService(invoice_repo=repo)
        
        usage = UsageRecord(
            workspace_id="ws_001",
            billing_period=BillingPeriod.MONTHLY,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            sta_lta_picks=5000,
            dbscan_clusters=1500,
            geiger_events=800
        )
        
        invoice = service.generate_invoice(
            workspace_id="ws_001",
            period=BillingPeriod.MONTHLY,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            usage=usage
        )
        
        assert invoice.status == InvoiceStatus.ISSUED
        assert invoice.invoice_number is not None
        assert invoice.issued_date is not None
        assert invoice.due_date is not None
        assert invoice.total_idr > Decimal("0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
