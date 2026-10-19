"""
tests/unit/test_billing.py - Unit tests untuk billing components.
"""
import sys
sys.path.insert(0, "..")

from datetime import date, timedelta
from decimal import Decimal
import pytest

from billing.generator import BillingGeneratorWorker
from billing.webhook import PaymentWebhookHandler
from billing.email import build_invoice_email_body, send_invoice_email
from infrastructure.repositories.usage_repo import InMemoryUsageRepository
from infrastructure.repositories.invoice_repo import InMemoryInvoiceRepository
from core.pricing_service import Invoice, InvoiceStatus, BillingPeriod


class TestBillingGenerator:
    """Tests untuk BillingGeneratorWorker."""
    
    def test_get_last_period_monthly(self):
        """Get last month period."""
        generator = BillingGeneratorWorker(
            usage_repository=InMemoryUsageRepository(),
            invoice_repository=InMemoryInvoiceRepository(),
            billing_period=BillingPeriod.MONTHLY
        )
        
        period_start, period_end = generator.get_last_period()
        
        # Should return last month
        assert isinstance(period_start, date)
        assert isinstance(period_end, date)
        assert period_start < period_end
        assert (period_end - period_start).days >= 27  # At least 28 days
    
    def test_get_workspace_ids_placeholder(self):
        """get_workspace_ids_with_usage returns empty (placeholder)."""
        generator = BillingGeneratorWorker(
            usage_repository=InMemoryUsageRepository(),
            invoice_repository=InMemoryInvoiceRepository()
        )
        
        workspace_ids = generator.get_workspace_ids_with_usage(
            date(2026, 10, 1), date(2026, 10, 31)
        )
        
        assert workspace_ids == []
    
    def test_get_usage_for_workspace_no_data(self):
        """No usage returns None."""
        generator = BillingGeneratorWorker(
            usage_repository=InMemoryUsageRepository(),
            invoice_repository=InMemoryInvoiceRepository()
        )
        
        usage = generator.get_usage_for_workspace(
            "ws_test", date(2026, 10, 1), date(2026, 10, 31)
        )
        
        assert usage is None


class TestPaymentWebhook:
    """Tests untuk PaymentWebhookHandler."""
    
    @pytest.mark.asyncio
    async def test_payment_confirmation_success(self):
        """Payment confirmation marks invoice PAID."""
        repo = InMemoryInvoiceRepository()
        handler = PaymentWebhookHandler(invoice_repository=repo)
        
        # Create invoice
        invoice = Invoice(
            id="inv_001",
            invoice_number="INV-2026-10-001",
            workspace_id="ws_test",
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            due_date=date(2026, 11, 15),
            subtotal_idr=Decimal("1000000"),
            tax_idr=Decimal("110000"),
            total_idr=Decimal("1110000"),
            status=InvoiceStatus.ISSUED,
            line_items=[]
        )
        await repo.save(invoice)
        
        # Payment confirmation
        result = await handler.handle_payment_confirmation(
            invoice_number="INV-2026-10-001",
            payment_method="bank_transfer",
            payment_reference="TRX-123",
            paid_amount=1110000.0
        )
        
        assert result["success"] is True
        assert "marked as paid" in result["message"]
        
        # Verify status
        updated = await repo.get_by_invoice_number("INV-2026-10-001")
        assert updated.status == InvoiceStatus.PAID
    
    @pytest.mark.asyncio
    async def test_payment_confirmation_invoice_not_found(self):
        """Payment for non-existent invoice fails."""
        repo = InMemoryInvoiceRepository()
        handler = PaymentWebhookHandler(invoice_repository=repo)
        
        result = await handler.handle_payment_confirmation(
            invoice_number="INV-NOT-EXISTS",
            payment_method="bank_transfer",
            payment_reference="TRX-123",
            paid_amount=1000000.0
        )
        
        assert result["success"] is False
        assert "not found" in result["message"]
    
    @pytest.mark.asyncio
    async def test_payment_confirmation_wrong_status(self):
        """Payment on DRAFT invoice fails."""
        repo = InMemoryInvoiceRepository()
        handler = PaymentWebhookHandler(invoice_repository=repo)
        
        invoice = Invoice(
            id="inv_002",
            invoice_number="INV-2026-10-002",
            workspace_id="ws_test",
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            due_date=date(2026, 11, 15),
            subtotal_idr=Decimal("1000000"),
            tax_idr=Decimal("110000"),
            total_idr=Decimal("1110000"),
            status=InvoiceStatus.DRAFT,  # DRAFT, not ISSUED
            line_items=[]
        )
        await repo.save(invoice)
        
        result = await handler.handle_payment_confirmation(
            invoice_number="INV-2026-10-002",
            payment_method="bank_transfer",
            payment_reference="TRX-123",
            paid_amount=1110000.0
        )
        
        assert result["success"] is False
        assert "expected ISSUED" in result["message"]
    
    @pytest.mark.asyncio
    async def test_payment_confirmation_amount_mismatch(self):
        """Payment with wrong amount fails."""
        repo = InMemoryInvoiceRepository()
        handler = PaymentWebhookHandler(invoice_repository=repo)
        
        invoice = Invoice(
            id="inv_003",
            invoice_number="INV-2026-10-003",
            workspace_id="ws_test",
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            due_date=date(2026, 11, 15),
            subtotal_idr=Decimal("1000000"),
            tax_idr=Decimal("110000"),
            total_idr=Decimal("1110000"),
            status=InvoiceStatus.ISSUED,
            line_items=[]
        )
        await repo.save(invoice)
        
        result = await handler.handle_payment_confirmation(
            invoice_number="INV-2026-10-003",
            payment_method="bank_transfer",
            payment_reference="TRX-123",
            paid_amount=500000.0  # Wrong amount
        )
        
        assert result["success"] is False
        assert "mismatch" in result["message"]
    
    @pytest.mark.asyncio
    async def test_payment_failed_logged(self):
        """Payment failure logged."""
        repo = InMemoryInvoiceRepository()
        handler = PaymentWebhookHandler(invoice_repository=repo)
        
        invoice = Invoice(
            id="inv_004",
            invoice_number="INV-2026-10-004",
            workspace_id="ws_test",
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            due_date=date(2026, 11, 15),
            subtotal_idr=Decimal("1000000"),
            tax_idr=Decimal("110000"),
            total_idr=Decimal("1110000"),
            status=InvoiceStatus.ISSUED,
            line_items=[]
        )
        await repo.save(invoice)
        
        result = await handler.handle_payment_failed(
            invoice_number="INV-2026-10-004",
            reason="Insufficient funds"
        )
        
        assert result["success"] is True


class TestEmailNotification:
    """Tests untuk email notification."""
    
    def test_build_email_body(self):
        """Email body includes invoice details."""
        invoice = Invoice(
            id="inv_test",
            invoice_number="INV-2026-10-001",
            workspace_id="ws_test",
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            due_date=date(2026, 11, 15),
            subtotal_idr=Decimal("1000000"),
            tax_idr=Decimal("110000"),
            total_idr=Decimal("1110000"),
            status=InvoiceStatus.ISSUED,
            line_items=[]
        )
        
        body = build_invoice_email_body(invoice)
        
        assert "INV-2026-10-001" in body
        assert "1,000,000" in body
        assert "1,110,000" in body
        assert "AI-GEMPA BMKG" in body
    
    def test_send_email_dry_run(self):
        """Send email without SMTP config (dry run)."""
        invoice = Invoice(
            id="inv_test",
            invoice_number="INV-2026-10-001",
            workspace_id="ws_test",
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            due_date=date(2026, 11, 15),
            subtotal_idr=Decimal("1000000"),
            tax_idr=Decimal("110000"),
            total_idr=Decimal("1110000"),
            status=InvoiceStatus.ISSUED,
            line_items=[]
        )
        
        # Without SMTP config, returns False
        result = send_invoice_email("test@example.com", invoice)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
