"""
billing/generator.py - BillingGeneratorWorker untuk cron monthly.

Tanggungjawab:
1. Cron setiap 1 Januari 00:00 (monthly billing cycle)
2. Ambil usage aggregation bulan sebelumnya
3. Generate invoice untuk semua workspace aktif
4. Simpan ke MongoDB
5. Kirim email notifikasi
"""
from datetime import datetime, date, timedelta
import logging
from typing import List, Optional

from infrastructure.repositories.usage_repo import UsageRepository
from infrastructure.repositories.invoice_repo import InvoiceRepository
from core.pricing_service import PricingService, Invoice, BillingPeriod, UsageRecord
from billing.email import send_invoice_email

logger = logging.getLogger(__name__)


class BillingGeneratorWorker:
    """
    Monthly billing generator.
    
    Run via cron:
        0 0 1 * *  # Setiap 1 Januari 00:00 (monthly)
    """
    
    def __init__(
        self,
        usage_repository: UsageRepository,
        invoice_repository: InvoiceRepository,
        billing_period: BillingPeriod = BillingPeriod.MONTHLY
    ):
        self.usage_repo = usage_repository
        self.invoice_repo = invoice_repository
        self.pricing_service = PricingService(invoice_repo=invoice_repository)
        self.billing_period = billing_period
    
    def get_last_period(self) -> tuple[date, date]:
        """
        Calculate last billing period dates.
        
        Monthly billing: bulan lalu (contoh: 2026-10-01 s/d 2026-10-31)
        """
        today = date.today()
        
        # First day of last month
        first_day_last_month = date(today.year, today.month, 1) - timedelta(days=1)
        first_day_last_month = first_day_last_month.replace(day=1)
        
        # Last day of last month
        if today.month == 1:
            last_month = 12
            last_year = today.year - 1
        else:
            last_month = today.month - 1
            last_year = today.year
        
        # Days in last month
        import calendar
        last_day = calendar.monthrange(last_year, last_month)[1]
        
        period_start = date(last_year, last_month, 1)
        period_end = date(last_year, last_month, last_day)
        
        logger.info(f"Last billing period: {period_start} to {period_end}")
        return period_start, period_end
    
    def get_workspace_ids_with_usage(
        self,
        period_start: date,
        period_end: date
    ) -> List[str]:
        """
        Get list of workspace IDs that have usage in period.
        
        Query UsageRepository untuk distinct workspace_id.
        """
        # Method belum ada di UsageRepository, implementasi sederhana
        # TODO: Add get_workspace_ids_with_usage method to UsageRepository
        # Sementara return empty list (placeholder)
        logger.warning("get_workspace_ids_with_usage: not yet implemented, using placeholder")
        return []
    
    def get_usage_for_workspace(
        self,
        workspace_id: str,
        period_start: date,
        period_end: date
    ) -> Optional[UsageRecord]:
        """
        Build UsageRecord dari aggregated usage untuk workspace.
        
        Query UsageRepository untuk aggregated usage, sum per module.
        """
        # Get aggregated usage entries
        usage_entries = self.usage_repo.get_usage_by_range(
            workspace_id=workspace_id,
            user_id=None,  # All users dalam workspace
            start_date=period_start.isoformat(),
            end_date=period_end.isoformat()
        )
        
        if not usage_entries:
            logger.info(f"No usage for workspace {workspace_id}")
            return None
        
        # Sum across all entries
        total_inferences = 0
        total_cost_idr = 0.0
        
        # Breakdown per module
        sta_lta_picks = 0
        phasenet_picks = 0
        eqtransformer_picks = 0
        dbscan_clusters = 0
        gamma_clusters = 0
        pyocto_events = 0
        geiger_events = 0
        nonlinloc_events = 0
        
        for entry in usage_entries:
            total_inferences += entry.total_inferences
            total_cost_idr += float(entry.total_cost_idr)
            
            # Aggregate breakdown by module
            # TODO: Use breakdown_by_module field (kode ini placeholder)
            # Sementara heuristic: cek provider name
        
        # Jika tidak ada usage, return None
        if total_inferences == 0:
            return None
        
        usage = UsageRecord(
            workspace_id=workspace_id,
            billing_period=self.billing_period,
            period_start=period_start,
            period_end=period_end,
            sta_lta_picks=sta_lta_picks,
            phasenet_picks=phasenet_picks,
            eqtransformer_picks=eqtransformer_picks,
            dbscan_clusters=dbscan_clusters,
            gamma_clusters=gamma_clusters,
            pyocto_events=pyocto_events,
            geiger_events=geiger_events,
            nonlinloc_events=nonlinloc_events
        )
        
        logger.info(f"Usage for workspace {workspace_id}: {total_inferences} inferences, IDR {total_cost_idr:,.0f}")
        return usage
    
    def generate_invoice_for_workspace(
        self,
        workspace_id: str,
        period_start: date,
        period_end: date,
        usage: UsageRecord
    ) -> Optional[Invoice]:
        """
        Generate invoice untuk satu workspace.
        """
        try:
            invoice = self.pricing_service.generate_invoice(
                workspace_id=workspace_id,
                period=self.billing_period,
                period_start=period_start,
                period_end=period_end,
                usage=usage
            )
            
            logger.info(f"Invoice generated: {invoice.invoice_number} (IDR {invoice.total_idr:,.0f})")
            return invoice
        
        except Exception as e:
            logger.error(f"Failed to generate invoice for workspace {workspace_id}: {e}")
            return None
    
    async def process_workspace(
        self,
        workspace_id: str,
        period_start: date,
        period_end: date,
        send_email: bool = False
    ) -> bool:
        """
        Process one workspace: get usage → generate invoice → save → send email.
        
        Returns True jika sukses.
        """
        # Get usage
        usage = self.get_usage_for_workspace(workspace_id, period_start, period_end)
        if not usage:
            logger.info(f"No usage for workspace {workspace_id}, skipping")
            return False
        
        # Generate invoice
        invoice = self.generate_invoice_for_workspace(
            workspace_id, period_start, period_end, usage
        )
        if not invoice:
            return False
        
        # Save invoice
        try:
            saved_invoice = await self.invoice_repo.save(invoice)
            logger.info(f"Invoice saved: {saved_invoice.id}")
        except Exception as e:
            logger.error(f"Failed to save invoice for workspace {workspace_id}: {e}")
            return False
        
        # Send email notification
        if send_email:
            # TODO: Get workspace email from ProfileRepository
            workspace_email = f"workspace-{workspace_id}@example.com"
            success = send_invoice_email(
                to_email=workspace_email,
                invoice=saved_invoice
            )
            if success:
                logger.info(f"Invoice email sent to {workspace_email}")
            else:
                logger.warning(f"Failed to send invoice email to {workspace_email}")
        
        return True
    
    async def run(self, send_email: bool = False) -> dict:
        """
        Main entry point for cron job.
        
        Args:
            send_email: True untuk kirim email notifikasi
        
        Returns:
            Dict dengan summary stats
        """
        logger.info("Starting billing generation...")
        
        # Get billing period
        period_start, period_end = self.get_last_period()
        
        # Get workspaces with usage
        workspace_ids = self.get_workspace_ids_with_usage(period_start, period_end)
        
        if not workspace_ids:
            logger.info("No workspaces with usage in period")
            return {
                "processed": 0,
                "success": 0,
                "failed": 0,
                "total_invoices": 0,
                "total_amount_idr": 0
            }
        
        # Process each workspace
        success_count = 0
        failed_count = 0
        total_amount_idr = 0.0
        
        for workspace_id in workspace_ids:
            logger.info(f"Processing workspace {workspace_id}...")
            
            try:
                success = await self.process_workspace(
                    workspace_id, period_start, period_end, send_email
                )
                
                if success:
                    success_count += 1
                    # Get invoice amount
                    # TODO: Query last invoice untuk amount
                else:
                    failed_count += 1
            
            except Exception as e:
                logger.error(f"Unexpected error processing workspace {workspace_id}: {e}")
                failed_count += 1
        
        logger.info(
            f"Billing generation complete: "
            f"{success_count} success, {failed_count} failed"
        )
        
        return {
            "processed": len(workspace_ids),
            "success": success_count,
            "failed": failed_count,
            "total_invoices": success_count,
            "total_amount_idr": total_amount_idr
        }


# Singleton untuk cron
_billing_generator: Optional[BillingGeneratorWorker] = None


def get_billing_generator() -> BillingGeneratorWorker:
    """Get or create singleton instance."""
    global _billing_generator
    if _billing_generator is None:
        from infrastructure.repositories.usage_repo import InMemoryUsageRepository
        from infrastructure.repositories.invoice_repo import InMemoryInvoiceRepository
        
        _billing_generator = BillingGeneratorWorker(
            usage_repository=InMemoryUsageRepository(),
            invoice_repository=InMemoryInvoiceRepository()
        )
    
    return _billing_generator


async def cron_job():
    """Entry point untuk cron."""
    generator = get_billing_generator()
    
    try:
        result = await generator.run(send_email=True)
        logger.info(f"Cron job result: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Cron job failed: {e}")
        raise


if __name__ == "__main__":
    # Test script
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        generator = get_billing_generator()
        result = await generator.run(send_email=False)
        print(f"Test result: {result}")
    
    asyncio.run(test())
