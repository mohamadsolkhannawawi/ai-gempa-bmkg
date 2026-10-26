"""
billing/email.py - Email notification untuk invoice.

Tanggungjawab:
1. Send invoice via email (SMTP)
2. Attach PDF invoice (optional)
3. Template HTML email

SMTP config: env vars SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
"""
import os
import logging
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from core.pricing_service import Invoice

logger = logging.getLogger(__name__)


def get_smtp_config() -> dict:
    """Get SMTP config from env vars."""
    return {
        "host": os.getenv("SMTP_HOST", "localhost"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "pass": os.getenv("SMTP_PASS", ""),
        "from": os.getenv("SMTP_FROM", "billing@ai-gempa.bmkg.go.id")
    }


def build_invoice_email_body(invoice: Invoice) -> str:
    """
    Build HTML email body untuk invoice.
    
    Template sederhana dengan detail invoice.
    """
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #0066cc; color: white; padding: 20px; }}
            .content {{ padding: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Invoice AI-GEMPA BMKG</h1>
        </div>
        
        <div class="content">
            <h2>Tagihan Bulanan</h2>
            
            <p><strong>Invoice Number:</strong> {invoice.invoice_number}</p>
            <p><strong>Workspace ID:</strong> {invoice.workspace_id}</p>
            <p><strong>Periode:</strong> {invoice.period_start} s/d {invoice.period_end}</p>
            <p><strong>Tanggal Jatuh Tempo:</strong> {invoice.due_date}</p>
            <p><strong>Status:</strong> {invoice.status.value}</p>
            
            <h3>Rincian Biaya</h3>
            <table>
                <tr>
                    <th>Item</th>
                    <th>Jumlah</th>
                    <th>Biaya (IDR)</th>
                </tr>
                <tr>
                    <td>Subtotal</td>
                    <td>-</td>
                    <td>{invoice.subtotal_idr:,.0f}</td>
                </tr>
                <tr>
                    <td>PPN 11%</td>
                    <td>-</td>
                    <td>{invoice.tax_idr:,.0f}</td>
                </tr>
                <tr style="font-weight: bold;">
                    <td>Total</td>
                    <td>-</td>
                    <td>{invoice.total_idr:,.0f}</td>
                </tr>
            </table>
            
            <p style="margin-top: 20px;">
                Silakan lakukan pembayaran sebelum tanggal jatuh tempo.
            </p>
            
            <div class="footer">
                <p>Email ini dikirim otomatis oleh sistem AI-GEMPA BMKG.</p>
                <p>Jika ada pertanyaan, hubungi support@ai-gempa.bmkg.go.id</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_invoice_email(
    to_email: str,
    invoice: Invoice,
    attach_pdf: bool = False
) -> bool:
    """
    Send invoice via email.
    
    Args:
        to_email: Recipient email
        invoice: Invoice object
        attach_pdf: True untuk attach PDF (belum implemented)
    
    Returns:
        True jika sukses
    """
    try:
        config = get_smtp_config()
        
        # Build email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Invoice {invoice.invoice_number} - AI-GEMPA BMKG"
        msg["From"] = config["from"]
        msg["To"] = to_email
        
        # Plain text fallback
        text = f"Invoice {invoice.invoice_number}\nTotal: IDR {invoice.total_idr:,.0f}"
        part1 = MIMEText(text, "plain")
        msg.attach(part1)
        
        # HTML body
        html = build_invoice_email_body(invoice)
        part2 = MIMEText(html, "html")
        msg.attach(part2)
        
        # TODO: Attach PDF jika attach_pdf=True
        
        # Send via SMTP
        if not config["user"]:
            logger.warning("SMTP not configured, email not sent (dry run)")
            return False
        
        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.starttls()
            server.login(config["user"], config["pass"])
            server.send_message(msg)
        
        logger.info(f"Invoice email sent to {to_email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send invoice email: {e}")
        return False


def send_overdue_reminder(
    to_email: str,
    invoice: Invoice
) -> bool:
    """
    Send overdue reminder email.
    
    Untuk invoice yang sudah past due date.
    """
    try:
        config = get_smtp_config()
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"REMINDER: Invoice {invoice.invoice_number} Overdue"
        msg["From"] = config["from"]
        msg["To"] = to_email
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #cc0000;">Reminder: Invoice Overdue</h2>
            
            <p>Invoice <strong>{invoice.invoice_number}</strong> telah melewati tanggal jatuh tempo.</p>
            
            <p><strong>Tanggal Jatuh Tempo:</strong> {invoice.due_date}</p>
            <p><strong>Total:</strong> IDR {invoice.total_idr:,.0f}</p>
            
            <p>Mohon segera lakukan pembayaran untuk menghindari penangguhan layanan.</p>
            
            <p>Terima kasih.</p>
        </body>
        </html>
        """
        
        part = MIMEText(html, "html")
        msg.attach(part)
        
        if not config["user"]:
            logger.warning("SMTP not configured, reminder not sent")
            return False
        
        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.starttls()
            server.login(config["user"], config["pass"])
            server.send_message(msg)
        
        logger.info(f"Overdue reminder sent to {to_email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send overdue reminder: {e}")
        return False


if __name__ == "__main__":
    # Test script
    from core.pricing_service import InvoiceStatus
    from datetime import date, timedelta
    from decimal import Decimal
    
    logging.basicConfig(level=logging.INFO)
    
    # Mock invoice
    invoice = Invoice(
        id="inv_test_001",
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
    
    # Dry run (SMTP not configured)
    send_invoice_email("test@example.com", invoice)
