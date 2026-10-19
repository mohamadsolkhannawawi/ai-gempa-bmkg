"""
infrastructure/repositories/invoice_repo.py - InvoiceRepository (MongoDB adapter).

Interface + MongoDB implementation untuk invoice persistence.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone, date

from core.pricing_service import Invoice, InvoiceStatus


class IInvoiceRepository(ABC):
    """Interface untuk invoice repository."""
    
    @abstractmethod
    async def save(self, invoice: Invoice) -> Invoice:
        """Save atau update invoice."""
        pass
    
    @abstractmethod
    async def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID."""
        pass
    
    @abstractmethod
    async def list_by_workspace(self, workspace_id: str, status: Optional[InvoiceStatus] = None) -> List[Invoice]:
        """List invoices by workspace, optionally filter by status."""
        pass
    
    @abstractmethod
    async def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by invoice number."""
        pass
    
    @abstractmethod
    async def list_overdue(self) -> List[Invoice]:
        """List all overdue invoices (issued + past due_date)."""
        pass
    
    @abstractmethod
    async def delete(self, invoice_id: str) -> bool:
        """Delete invoice (hard delete, only DRAFT allowed)."""
        pass


class MongoInvoiceRepository(IInvoiceRepository):
    """MongoDB implementation."""
    
    def __init__(self, db_client=None):
        """
        db_client: MongoDB client (injected, atau lazily initialized).
        Assumes collection 'invoices' exists.
        """
        self.db_client = db_client
        self._collection = None
    
    @property
    def collection(self):
        """Lazy-load MongoDB collection."""
        if self._collection is None:
            # TODO: initialize from db_client
            pass
        return self._collection
    
    async def save(self, invoice: Invoice) -> Invoice:
        """Save invoice to MongoDB."""
        data = invoice.to_dict()
        
        # Upsert
        result = await self.collection.update_one(
            {"id": invoice.id},
            {"$set": data},
            upsert=True
        )
        
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice
    
    async def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID."""
        doc = await self.collection.find_one({"id": invoice_id})
        if not doc:
            return None
        
        doc.pop("_id", None)
        return Invoice.from_dict(doc)
    
    async def list_by_workspace(self, workspace_id: str, status: Optional[InvoiceStatus] = None) -> List[Invoice]:
        """List invoices by workspace."""
        query = {"workspace_id": workspace_id}
        
        if status:
            query["status"] = status.value
        
        docs = await self.collection.find(query).sort("created_at", -1).to_list(None)
        
        invoices = []
        for doc in docs:
            doc.pop("_id", None)
            invoices.append(Invoice.from_dict(doc))
        
        return invoices
    
    async def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by invoice number."""
        doc = await self.collection.find_one({"invoice_number": invoice_number})
        if not doc:
            return None
        
        doc.pop("_id", None)
        return Invoice.from_dict(doc)
    
    async def list_overdue(self) -> List[Invoice]:
        """List overdue invoices."""
        today = date.today().isoformat()
        
        docs = await self.collection.find({
            "status": InvoiceStatus.ISSUED.value,
            "due_date": {"$lt": today}
        }).to_list(None)
        
        invoices = []
        for doc in docs:
            doc.pop("_id", None)
            invoices.append(Invoice.from_dict(doc))
        
        return invoices
    
    async def delete(self, invoice_id: str) -> bool:
        """Delete invoice (hard delete)."""
        # Check status first (only DRAFT allowed)
        invoice = await self.get_by_id(invoice_id)
        if invoice and invoice.status != InvoiceStatus.DRAFT:
            raise ValueError(f"Cannot delete invoice with status {invoice.status}")
        
        result = await self.collection.delete_one({"id": invoice_id})
        return result.deleted_count > 0


class InMemoryInvoiceRepository(IInvoiceRepository):
    """In-memory implementation untuk testing."""
    
    def __init__(self):
        self.invoices: dict[str, Invoice] = {}
    
    async def save(self, invoice: Invoice) -> Invoice:
        """Save invoice to memory."""
        invoice.updated_at = datetime.now(timezone.utc)
        self.invoices[invoice.id] = invoice
        return invoice
    
    async def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID."""
        return self.invoices.get(invoice_id)
    
    async def list_by_workspace(self, workspace_id: str, status: Optional[InvoiceStatus] = None) -> List[Invoice]:
        """List invoices by workspace."""
        result = [inv for inv in self.invoices.values() if inv.workspace_id == workspace_id]
        
        if status:
            result = [inv for inv in result if inv.status == status]
        
        return sorted(result, key=lambda inv: inv.created_at, reverse=True)
    
    async def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by invoice number."""
        for invoice in self.invoices.values():
            if invoice.invoice_number == invoice_number:
                return invoice
        return None
    
    async def list_overdue(self) -> List[Invoice]:
        """List overdue invoices."""
        today = date.today()
        result = []
        
        for invoice in self.invoices.values():
            if invoice.status == InvoiceStatus.ISSUED and invoice.due_date and invoice.due_date < today:
                result.append(invoice)
        
        return result
    
    async def delete(self, invoice_id: str) -> bool:
        """Delete invoice."""
        invoice = self.invoices.get(invoice_id)
        if invoice and invoice.status != InvoiceStatus.DRAFT:
            raise ValueError(f"Cannot delete invoice with status {invoice.status}")
        
        if invoice_id in self.invoices:
            del self.invoices[invoice_id]
            return True
        return False


if __name__ == "__main__":
    import asyncio
    from core.pricing_service import PricingService, BillingPeriod, UsageRecord
    
    async def test():
        repo = InMemoryInvoiceRepository()
        service = PricingService(invoice_repo=repo)
        
        # Generate invoice
        usage = UsageRecord(
            workspace_id="ws_001",
            billing_period=BillingPeriod.MONTHLY,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            sta_lta_picks=5000,
            phasenet_picks=3000,
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
        
        # Save
        saved = await repo.save(invoice)
        print(f"Saved: {saved.invoice_number} (IDR {saved.total_idr:,.0f})")
        
        # Retrieve
        retrieved = await repo.get_by_id(saved.id)
        print(f"Retrieved: {retrieved.invoice_number} ({retrieved.status})")
        
        # List
        invoices = await repo.list_by_workspace("ws_001")
        print(f"Total invoices: {len(invoices)}")
    
    asyncio.run(test())
