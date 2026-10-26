"""
api/routes/billing.py - FastAPI router untuk billing endpoints.

Endpoints:
1. GET    /api/v2/billing/invoices — list invoices per workspace
2. GET    /api/v2/billing/invoices/{id} — get single invoice
3. POST   /api/v2/billing/invoices — generate new invoice
4. PATCH  /api/v2/billing/invoices/{id}/pay — mark invoice as PAID
5. GET    /api/v2/billing/summary — dashboard summary
6. GET    /api/v2/billing/invoices/{id}/pdf — download PDF
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Optional
from decimal import Decimal

from api.schemas.pricing import (
    InvoiceSchema, InvoiceListResponse, GenerateInvoiceRequest,
    MarkInvoicePaidRequest, InvoiceSummaryResponse
)
from core.pricing_service import PricingService, Invoice, BillingPeriod, UsageRecord, InvoiceStatus
from infrastructure.repositories.invoice_repo import IInvoiceRepository, InMemoryInvoiceRepository

router = APIRouter(prefix="/api/v2/billing", tags=["billing"])

# Inject repository (default: in-memory)
_repo = InMemoryInvoiceRepository()


def get_repo() -> IInvoiceRepository:
    return _repo


def get_pricing_service(repo: IInvoiceRepository = Depends(get_repo)) -> PricingService:
    return PricingService(invoice_repo=repo)


@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    workspace_id: str,
    status: Optional[str] = None,
    repo: IInvoiceRepository = Depends(get_repo)
):
    """
    List invoices per workspace.
    
    Query params:
    - workspace_id (required)
    - status (optional): draft | issued | paid | overdue | cancelled
    """
    status_filter = InvoiceStatus(status) if status else None
    invoices = await repo.list_by_workspace(workspace_id, status_filter)
    
    # Calculate unpaid total
    total_unpaid = Decimal("0")
    for inv in invoices:
        if inv.status in [InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE]:
            total_unpaid += inv.total_idr
    
    # Convert to schema
    invoice_schemas = [
        InvoiceSchema(
            id=inv.id,
            workspace_id=inv.workspace_id,
            invoice_number=inv.invoice_number,
            billing_period=inv.billing_period.value,
            period_start=inv.period_start,
            period_end=inv.period_end,
            status=inv.status.value,
            items=[
                {
                    "type": item.type.value,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price_idr": item.unit_price_idr,
                    "amount_idr": item.amount_idr
                }
                for item in inv.items
            ],
            subtotal_idr=inv.subtotal_idr,
            ppn_percent=inv.ppn_percent,
            ppn_amount_idr=inv.ppn_amount_idr,
            total_idr=inv.total_idr,
            issued_date=inv.issued_date,
            due_date=inv.due_date,
            paid_date=inv.paid_date,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            pdf_url=inv.pdf_url,
            pdf_generated_at=inv.pdf_generated_at
        )
        for inv in invoices
    ]
    
    return InvoiceListResponse(
        invoices=invoice_schemas,
        count=len(invoice_schemas),
        total_unpaid_idr=total_unpaid
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceSchema)
async def get_invoice(
    invoice_id: str,
    repo: IInvoiceRepository = Depends(get_repo)
):
    """Get single invoice by ID."""
    invoice = await repo.get_by_id(invoice_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    
    return InvoiceSchema(
        id=invoice.id,
        workspace_id=invoice.workspace_id,
        invoice_number=invoice.invoice_number,
        billing_period=invoice.billing_period.value,
        period_start=invoice.period_start,
        period_end=invoice.period_end,
        status=invoice.status.value,
        items=[
            {
                "type": item.type.value,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price_idr": item.unit_price_idr,
                "amount_idr": item.amount_idr
            }
            for item in invoice.items
        ],
        subtotal_idr=invoice.subtotal_idr,
        ppn_percent=invoice.ppn_percent,
        ppn_amount_idr=invoice.ppn_amount_idr,
        total_idr=invoice.total_idr,
        issued_date=invoice.issued_date,
        due_date=invoice.due_date,
        paid_date=invoice.paid_date,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        pdf_url=invoice.pdf_url,
        pdf_generated_at=invoice.pdf_generated_at
    )


@router.post("/invoices", response_model=InvoiceSchema, status_code=201)
async def generate_invoice(
    request: GenerateInvoiceRequest,
    service: PricingService = Depends(get_pricing_service)
):
    """
    Generate new invoice dari usage data.
    
    Steps:
    1. Calculate cost
    2. Apply free quota
    3. Generate invoice number
    4. Mark as ISSUED
    5. Save to DB
    """
    period = BillingPeriod(request.billing_period)
    
    usage = UsageRecord(
        workspace_id=request.usage.workspace_id,
        billing_period=period,
        period_start=request.usage.period_start,
        period_end=request.usage.period_end,
        picks_count=request.usage.picks_count,
        clusters_count=request.usage.clusters_count,
        events_count=request.usage.events_count,
        inference_hours=request.usage.inference_hours,
        storage_gb=request.usage.storage_gb,
        sta_lta_picks=request.usage.sta_lta_picks,
        phasenet_picks=request.usage.phasenet_picks,
        eqtransformer_picks=request.usage.eqtransformer_picks,
        dbscan_clusters=request.usage.dbscan_clusters,
        gamma_clusters=request.usage.gamma_clusters,
        geiger_events=request.usage.geiger_events,
        pyocto_events=request.usage.pyocto_events
    )
    
    invoice = service.generate_invoice(
        workspace_id=request.workspace_id,
        period=period,
        period_start=request.period_start,
        period_end=request.period_end,
        usage=usage
    )
    
    # Save to repo
    saved = await service.invoice_repo.save(invoice)
    
    return InvoiceSchema(
        id=saved.id,
        workspace_id=saved.workspace_id,
        invoice_number=saved.invoice_number,
        billing_period=saved.billing_period.value,
        period_start=saved.period_start,
        period_end=saved.period_end,
        status=saved.status.value,
        items=[
            {
                "type": item.type.value,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price_idr": item.unit_price_idr,
                "amount_idr": item.amount_idr
            }
            for item in saved.items
        ],
        subtotal_idr=saved.subtotal_idr,
        ppn_percent=saved.ppn_percent,
        ppn_amount_idr=saved.ppn_amount_idr,
        total_idr=saved.total_idr,
        issued_date=saved.issued_date,
        due_date=saved.due_date,
        paid_date=saved.paid_date,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
        pdf_url=saved.pdf_url,
        pdf_generated_at=saved.pdf_generated_at
    )


@router.patch("/invoices/{invoice_id}/pay", response_model=InvoiceSchema)
async def mark_invoice_paid(
    invoice_id: str,
    request: MarkInvoicePaidRequest,
    repo: IInvoiceRepository = Depends(get_repo)
):
    """Mark invoice as PAID."""
    if request.invoice_id != invoice_id:
        raise HTTPException(
            status_code=400,
            detail="Invoice ID in path and body must match"
        )
    
    invoice = await repo.get_by_id(invoice_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    
    if invoice.status != InvoiceStatus.ISSUED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pay invoice with status {invoice.status.value}"
        )
    
    invoice.mark_paid(request.paid_date)
    saved = await repo.save(invoice)
    
    return InvoiceSchema(
        id=saved.id,
        workspace_id=saved.workspace_id,
        invoice_number=saved.invoice_number,
        billing_period=saved.billing_period.value,
        period_start=saved.period_start,
        period_end=saved.period_end,
        status=saved.status.value,
        items=[
            {
                "type": item.type.value,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price_idr": item.unit_price_idr,
                "amount_idr": item.amount_idr
            }
            for item in saved.items
        ],
        subtotal_idr=saved.subtotal_idr,
        ppn_percent=saved.ppn_percent,
        ppn_amount_idr=saved.ppn_amount_idr,
        total_idr=saved.total_idr,
        issued_date=saved.issued_date,
        due_date=saved.due_date,
        paid_date=saved.paid_date,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
        pdf_url=saved.pdf_url,
        pdf_generated_at=saved.pdf_generated_at
    )


@router.get("/summary", response_model=InvoiceSummaryResponse)
async def get_billing_summary(
    workspace_id: str,
    repo: IInvoiceRepository = Depends(get_repo)
):
    """
    Dashboard summary untuk billing.
    
    Returns:
    - Total invoices
    - Total issued/paid/overdue
    - Total unpaid (IDR)
    - Current month cost
    """
    invoices = await repo.list_by_workspace(workspace_id)
    
    total_invoices = len(invoices)
    total_issued = sum(1 for inv in invoices if inv.status == InvoiceStatus.ISSUED)
    total_paid = sum(1 for inv in invoices if inv.status == InvoiceStatus.PAID)
    total_overdue = sum(1 for inv in invoices if inv.status == InvoiceStatus.OVERDUE)
    
    total_unpaid_idr = Decimal("0")
    for inv in invoices:
        if inv.status in [InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE]:
            total_unpaid_idr += inv.total_idr
    
    # Current month cost
    from datetime import date
    current_month = date.today().month
    current_year = date.today().year
    
    current_month_idr = Decimal("0")
    for inv in invoices:
        if inv.period_start.month == current_month and inv.period_start.year == current_year:
            current_month_idr += inv.total_idr
    
    # Last invoice + next due date
    last_invoice_date = None
    next_due_date = None
    
    if invoices:
        sorted_invoices = sorted(invoices, key=lambda x: x.created_at, reverse=True)
        last_invoice_date = sorted_invoices[0].issued_date
        
        # Find next due date (earliest unpaid invoice)
        unpaid = [inv for inv in invoices if inv.status in [InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE]]
        if unpaid:
            sorted_unpaid = sorted(unpaid, key=lambda x: x.due_date if x.due_date else date.max)
            if sorted_unpaid and sorted_unpaid[0].due_date:
                next_due_date = sorted_unpaid[0].due_date
    
    return InvoiceSummaryResponse(
        workspace_id=workspace_id,
        total_invoices=total_invoices,
        total_issued=total_issued,
        total_paid=total_paid,
        total_overdue=total_overdue,
        total_unpaid_idr=total_unpaid_idr,
        current_month_idr=current_month_idr,
        last_invoice_date=last_invoice_date,
        next_due_date=next_due_date
    )


@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    repo: IInvoiceRepository = Depends(get_repo)
):
    """
    Download invoice PDF.
    
    TODO: generate real PDF dengan reportlab/weasyprint.
    """
    invoice = await repo.get_by_id(invoice_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    
    if not invoice.pdf_url:
        raise HTTPException(status_code=404, detail="PDF not generated yet")
    
    # TODO: return real PDF file
    return {
        "message": "PDF download not implemented yet",
        "invoice_id": invoice_id,
        "pdf_url": invoice.pdf_url
    }


@router.get("/health/billing")
async def health_check():
    """Health check untuk billing service."""
    return {
        "status": "healthy",
        "service": "billing"
    }
