"""
api/schemas/pricing.py - Pydantic schemas untuk pricing + billing API.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal
from datetime import date, datetime


class InvoiceItemSchema(BaseModel):
    """Invoice item schema."""
    type: str = Field(..., description="picks | clusters | events | inference | storage")
    description: str
    quantity: Decimal
    unit_price_idr: Decimal
    amount_idr: Decimal
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class UsageRecordSchema(BaseModel):
    """Usage record schema (input untuk estimate)."""
    workspace_id: str
    billing_period: str = Field("monthly", description="monthly | quarterly | annual")
    period_start: date
    period_end: date
    
    picks_count: int = 0
    clusters_count: int = 0
    events_count: int = 0
    inference_hours: float = 0.0
    storage_gb: float = 0.0
    
    # Per-provider usage
    sta_lta_picks: int = 0
    phasenet_picks: int = 0
    eqtransformer_picks: int = 0
    dbscan_clusters: int = 0
    gamma_clusters: int = 0
    geiger_events: int = 0
    pyocto_events: int = 0


class CostEstimateRequest(BaseModel):
    """Request untuk estimate cost."""
    workspace_id: str
    billing_period: str = Field("monthly", description="monthly | quarterly | annual")
    custom_usage: Optional[UsageRecordSchema] = None


class CostEstimateResponse(BaseModel):
    """Response untuk cost estimation."""
    workspace_id: str
    period: str
    usage_summary: dict = Field(
        default_factory=lambda: {
            "total_picks": 0,
            "total_clusters": 0,
            "total_events": 0,
            "inference_hours": 0.0,
            "storage_gb": 0.0
        }
    )
    items: List[dict]
    subtotal_idr: float
    ppn_percent: float
    ppn_amount_idr: float
    total_idr: float
    currency: str = "IDR"


class InvoiceSchema(BaseModel):
    """Full invoice schema."""
    id: str
    workspace_id: str
    invoice_number: str
    billing_period: str
    period_start: date
    period_end: date
    status: str = Field(..., description="draft | issued | paid | overdue | cancelled")
    items: List[InvoiceItemSchema]
    subtotal_idr: Decimal
    ppn_percent: Decimal = Decimal("11.0")
    ppn_amount_idr: Decimal
    total_idr: Decimal
    issued_date: Optional[date] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    pdf_url: Optional[str] = None
    pdf_generated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class InvoiceListResponse(BaseModel):
    """Response untuk GET /api/v2/invoices."""
    invoices: List[InvoiceSchema]
    count: int
    total_unpaid_idr: Decimal = Decimal("0")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class GenerateInvoiceRequest(BaseModel):
    """Request untuk generate invoice."""
    workspace_id: str
    billing_period: str = Field("monthly", description="monthly | quarterly | annual")
    period_start: date
    period_end: date
    usage: UsageRecordSchema


class MarkInvoicePaidRequest(BaseModel):
    """Request untuk mark invoice as PAID."""
    invoice_id: str
    paid_date: Optional[date] = None


class InvoiceSummaryResponse(BaseModel):
    """Dashboard summary untuk billing."""
    workspace_id: str
    total_invoices: int
    total_issued: int
    total_paid: int
    total_overdue: int
    total_unpaid_idr: Decimal
    current_month_idr: Decimal
    last_invoice_date: Optional[date] = None
    next_due_date: Optional[date] = None
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
