"""
billing/webhook.py - PaymentHandler webhook untuk payment confirmation.

Tanggungjawab:
1. Terima webhook dari payment gateway (manual/bank transfer)
2. Update invoice status → PAID
3. Log payment confirmation
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from infrastructure.repositories.invoice_repo import InvoiceRepository
from core.pricing_service import InvoiceStatus

logger = logging.getLogger(__name__)


class PaymentWebhookHandler:
    """
    Handler untuk payment webhook.
    
    Endpoint: POST /api/v2/billing/webhook/payment
    """
    
    def __init__(self, invoice_repository: InvoiceRepository):
        self.invoice_repo = invoice_repository
    
    async def handle_payment_confirmation(
        self,
        invoice_number: str,
        payment_method: str,
        payment_reference: str,
        paid_amount: float,
        payment_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process payment confirmation webhook.
        
        Args:
            invoice_number: Invoice number
            payment_method: "bank_transfer", "va", "credit_card", etc
            payment_reference: Bank reference / transaction ID
            paid_amount: Amount paid (IDR)
            payment_date: Payment date (ISO format)
        
        Returns:
            Dict dengan status + message
        """
        try:
            # Get invoice
            invoice = await self.invoice_repo.get_by_invoice_number(invoice_number)
            
            if not invoice:
                logger.warning(f"Invoice not found: {invoice_number}")
                return {
                    "success": False,
                    "message": f"Invoice {invoice_number} not found"
                }
            
            # Validate status (must be ISSUED)
            if invoice.status != InvoiceStatus.ISSUED:
                logger.warning(
                    f"Invoice {invoice_number} status {invoice.status}, cannot mark paid"
                )
                return {
                    "success": False,
                    "message": f"Invoice status {invoice.status}, expected ISSUED"
                }
            
            # Validate amount
            if abs(paid_amount - float(invoice.total_idr)) > 1.0:  # Tolerance 1 IDR
                logger.warning(
                    f"Payment amount mismatch: paid {paid_amount}, expected {invoice.total_idr}"
                )
                return {
                    "success": False,
                    "message": f"Amount mismatch: paid {paid_amount}, expected {invoice.total_idr}"
                }
            
            # Update invoice status
            invoice.status = InvoiceStatus.PAID
            invoice.updated_at = datetime.now(timezone.utc)
            
            # Add payment metadata (jika Invoice support payment_info field)
            # invoice.payment_info = {
            #     "method": payment_method,
            #     "reference": payment_reference,
            #     "date": payment_date or datetime.now(timezone.utc).isoformat()
            # }
            
            # Save
            await self.invoice_repo.save(invoice)
            
            logger.info(
                f"Invoice {invoice_number} marked PAID "
                f"(method: {payment_method}, ref: {payment_reference})"
            )
            
            return {
                "success": True,
                "message": f"Invoice {invoice_number} marked as paid",
                "invoice_id": invoice.id
            }
        
        except Exception as e:
            logger.error(f"Failed to process payment webhook: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    async def handle_payment_failed(
        self,
        invoice_number: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Handle payment failure notification.
        
        Status tetap ISSUED, log failure reason.
        """
        try:
            invoice = await self.invoice_repo.get_by_invoice_number(invoice_number)
            
            if not invoice:
                return {
                    "success": False,
                    "message": f"Invoice {invoice_number} not found"
                }
            
            logger.warning(f"Payment failed for invoice {invoice_number}: {reason}")
            
            # Optionally: add retry logic atau email notification
            
            return {
                "success": True,
                "message": f"Payment failure logged for {invoice_number}"
            }
        
        except Exception as e:
            logger.error(f"Failed to handle payment failure: {e}")
            return {
                "success": False,
                "message": str(e)
            }


# Singleton
_payment_handler: Optional[PaymentWebhookHandler] = None


def get_payment_handler() -> PaymentWebhookHandler:
    """Get or create singleton handler."""
    global _payment_handler
    if _payment_handler is None:
        from infrastructure.repositories.invoice_repo import InMemoryInvoiceRepository
        _payment_handler = PaymentWebhookHandler(
            invoice_repository=InMemoryInvoiceRepository()
        )
    return _payment_handler


if __name__ == "__main__":
    # Test script
    import asyncio
    from core.pricing_service import Invoice, BillingPeriod
    from datetime import date
    from decimal import Decimal
    
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        handler = get_payment_handler()
        
        # Create test invoice
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
        
        await handler.invoice_repo.save(invoice)
        
        # Simulate payment confirmation webhook
        result = await handler.handle_payment_confirmation(
            invoice_number="INV-2026-10-001",
            payment_method="bank_transfer",
            payment_reference="TRX-12345",
            paid_amount=1110000.0
        )
        
        print(f"Payment confirmation result: {result}")
        
        # Verify status
        updated = await handler.invoice_repo.get_by_invoice_number("INV-2026-10-001")
        print(f"Invoice status after payment: {updated.status}")
    
    asyncio.run(test())
