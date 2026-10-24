"""
Invoices router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
from io import BytesIO
from xml.sax.saxutils import escape
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from backend.database import get_db
from backend.models.invoice import Invoice, InvoiceItem
from backend.models.restaurant import Restaurant
from backend.models.payment import Payment
from backend.models.product import Product
from backend.models.setting import Setting
from backend.models.order import SalesOrder
from backend.models.user import User
from backend.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceItemCreate, InvoiceItemResponse
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/invoices", tags=["Invoices"], dependencies=[Depends(require_manager_or_admin())])


def generate_invoice_number(db: Session) -> str:
    """Generate unique invoice number"""
    year = datetime.utcnow().year
    configured_prefix = db.query(Setting).filter(Setting.key == "invoice_prefix").first()
    prefix = f"{(configured_prefix.value if configured_prefix and configured_prefix.value else 'ESR-INV')}-{year}-"
    
    # Find the highest invoice number for this year
    last_invoice = db.query(Invoice).filter(
        Invoice.invoice_number.like(f"{prefix}%")
    ).order_by(Invoice.invoice_number.desc()).first()
    
    try:
        new_num = int(last_invoice.invoice_number.split("-")[-1]) + 1 if last_invoice else 1
    except (ValueError, IndexError):
        new_num = db.query(Invoice).count() + 1
    
    return f"{prefix}{new_num:05d}"


@router.post("/", response_model=InvoiceResponse)
async def create_invoice(
    invoice_data: InvoiceCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new invoice (Manager/Admin only)
    """
    # Verify restaurant exists
    restaurant = db.query(Restaurant).filter(Restaurant.id == invoice_data.restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    if invoice_data.order_id:
        order = db.query(SalesOrder).filter(SalesOrder.id == invoice_data.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Sales order not found")
        if order.restaurant_id != invoice_data.restaurant_id:
            raise HTTPException(status_code=400, detail="The selected order does not belong to this restaurant")
        if db.query(Invoice).filter(Invoice.order_id == invoice_data.order_id).first():
            raise HTTPException(status_code=400, detail="This order already has an invoice")
    
    # Generate invoice number if not provided
    invoice_number = invoice_data.invoice_number
    if not invoice_number:
        invoice_number = generate_invoice_number(db)
    else:
        # Check if invoice number exists
        if db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice number already exists"
            )
    
    # Calculate totals
    for item in invoice_data.items:
        if item.discount > item.quantity * item.rate:
            raise HTTPException(status_code=400, detail="An invoice line discount cannot exceed its line subtotal")
    subtotal = sum(item.quantity * item.rate for item in invoice_data.items)
    item_discounts = sum(item.discount for item in invoice_data.items)
    item_taxes = sum(item.tax for item in invoice_data.items)
    discount = invoice_data.discount
    tax = invoice_data.tax
    if item_discounts + discount > subtotal:
        raise HTTPException(status_code=400, detail="Total discounts cannot exceed the invoice subtotal")
    grand_total = subtotal - item_discounts - discount + item_taxes + tax
    if grand_total <= 0:
        raise HTTPException(status_code=400, detail="Invoice total must be greater than zero")
    
    # Set due date if not provided (default 30 days)
    due_date = invoice_data.due_date
    if not due_date:
        billing_cycle = db.query(Setting).filter(Setting.key == "billing_cycle").first()
        try:
            due_days = max(1, min(365, int(billing_cycle.value))) if billing_cycle and billing_cycle.value else 30
        except ValueError:
            due_days = 30
        due_date = invoice_data.invoice_date + timedelta(days=due_days)
    if due_date < invoice_data.invoice_date:
        raise HTTPException(status_code=400, detail="Due date cannot be earlier than the invoice date")
    
    # Create invoice
    new_invoice = Invoice(
        invoice_number=invoice_number,
        order_id=invoice_data.order_id,
        restaurant_id=invoice_data.restaurant_id,
        invoice_date=invoice_data.invoice_date,
        due_date=due_date,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        grand_total=grand_total,
        balance_due=grand_total,
        notes=invoice_data.notes
    )
    
    db.add(new_invoice)
    db.flush()
    
    # Create invoice items
    for item_data in invoice_data.items:
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with ID {item_data.product_id} not found"
            )
        
        item_amount = item_data.quantity * item_data.rate - item_data.discount + item_data.tax
        invoice_item = InvoiceItem(
            invoice_id=new_invoice.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit=item_data.unit,
            rate=item_data.rate,
            discount=item_data.discount,
            tax=item_data.tax,
            amount=item_amount
        )
        db.add(invoice_item)
    
    db.commit()
    db.refresh(new_invoice)
    
    return new_invoice


@router.get("/", response_model=List[InvoiceResponse])
async def get_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    restaurant_id: Optional[int] = None,
    payment_status: Optional[str] = None,
    is_finalized: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all invoices with optional filters
    """
    query = db.query(Invoice)
    
    if restaurant_id:
        query = query.filter(Invoice.restaurant_id == restaurant_id)
    
    if payment_status:
        query = query.filter(Invoice.payment_status == payment_status)
    
    if is_finalized is not None:
        query = query.filter(Invoice.is_finalized == is_finalized)
    
    invoices = query.order_by(Invoice.invoice_date.desc()).offset(skip).limit(limit).all()
    return invoices


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific invoice by ID
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    invoice_data: InvoiceUpdate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Update an invoice (Manager/Admin only)
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Prevent editing finalized invoices
    if invoice.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit finalized invoice"
        )
    
    update_data = invoice_data.model_dump(exclude_unset=True, exclude={"items"})
    for field, value in update_data.items():
        setattr(invoice, field, value)

    if invoice_data.items is not None:
        invoice.items.clear()
        db.flush()

    if invoice.due_date and invoice.due_date < invoice.invoice_date:
        raise HTTPException(status_code=400, detail="Due date cannot be earlier than the invoice date")
    if invoice_data.items is not None:
        for item_data in invoice_data.items:
            if item_data.discount > item_data.quantity * item_data.rate:
                raise HTTPException(status_code=400, detail="An invoice line discount cannot exceed its line subtotal")
            if not db.query(Product).filter(Product.id == item_data.product_id).first():
                raise HTTPException(status_code=400, detail=f"Product with ID {item_data.product_id} not found")
            invoice.items.append(InvoiceItem(
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit=item_data.unit,
                rate=item_data.rate,
                discount=item_data.discount,
                tax=item_data.tax,
                amount=item_data.quantity * item_data.rate - item_data.discount + item_data.tax
            ))
        db.flush()

    invoice.subtotal = sum(item.quantity * item.rate for item in invoice.items)
    line_discounts = sum(item.discount or 0 for item in invoice.items)
    line_taxes = sum(item.tax or 0 for item in invoice.items)
    if line_discounts + (invoice.discount or 0) > invoice.subtotal:
        raise HTTPException(status_code=400, detail="Total discounts cannot exceed the invoice subtotal")
    invoice.grand_total = invoice.subtotal - line_discounts - (invoice.discount or 0) + line_taxes + (invoice.tax or 0)
    if invoice.grand_total <= 0:
        raise HTTPException(status_code=400, detail="Invoice total must be greater than zero")
    invoice.balance_due = max(0, invoice.grand_total - (invoice.amount_paid or 0))
    if invoice.amount_paid <= 0:
        invoice.payment_status = "unpaid"
    elif invoice.amount_paid < invoice.grand_total:
        invoice.payment_status = "partially_paid"
    else:
        invoice.payment_status = "paid"
    
    invoice.updated_at = func.now()
    db.commit()
    db.refresh(invoice)
    
    return invoice


@router.post("/{invoice_id}/finalize")
async def finalize_invoice(
    invoice_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Finalize an invoice (Manager/Admin only)
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice already finalized"
        )

    if not invoice.items:
        raise HTTPException(status_code=400, detail="Add at least one invoice item before finalizing")
    
    invoice.is_finalized = True
    
    # Update payment status
    if invoice.amount_paid == 0:
        invoice.payment_status = "unpaid"
    elif invoice.amount_paid < invoice.grand_total:
        invoice.payment_status = "partially_paid"
    else:
        invoice.payment_status = "paid"
    
    db.commit()
    
    return {"message": "Invoice finalized successfully"}


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download a printable, branded invoice with customer, tax and balance details."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    settings = {row.key: row.value for row in db.query(Setting).all()}
    restaurant = invoice.restaurant
    brand = escape(settings.get("company_name") or "ESR Foods")
    placeholders = {
        "company_address": "123 Fish Market Road, Chennai",
        "company_phone": "+91 9876543210",
        "company_email": "info@esrfoods.com",
        "gst_number": "33AABCU9603R1ZN",
    }
    def configured_value(key: str) -> str:
        value = settings.get(key) or ""
        return "" if value == placeholders.get(key) else escape(value)

    address = configured_value("company_address")
    phone = configured_value("company_phone")
    email = configured_value("company_email")
    gst_number = configured_value("gst_number")
    customer_address = escape(restaurant.address or "")

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=0.6 * inch, leftMargin=0.6 * inch,
        topMargin=0.55 * inch, bottomMargin=0.55 * inch,
        title=f"Invoice {invoice.invoice_number}", author=brand
    )
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    title = ParagraphStyle("InvoiceTitle", parent=styles["Title"], textColor=colors.HexColor("#17324d"), alignment=TA_RIGHT, fontSize=22)
    small = ParagraphStyle("InvoiceSmall", parent=body, fontSize=8, leading=11, textColor=colors.HexColor("#526273"))
    story = [
        Table([[Paragraph(f"<b>{brand}</b>", ParagraphStyle("InvoiceBrand", parent=styles["Heading1"], textColor=colors.HexColor("#167a72"))),
            Paragraph("INVOICE", title)]], colWidths=[3.8 * inch, 3.4 * inch]),
        Spacer(1, 8),
        Paragraph("<br/>".join(part for part in [address, phone, email, f"GSTIN: {gst_number}" if gst_number else ""] if part) or "", small),
        Spacer(1, 16),
        Table([
            [Paragraph("<b>BILL TO</b>", body), Paragraph("<b>INVOICE DETAILS</b>", body)],
            [Paragraph("<b>" + escape(restaurant.name) + "</b><br/>" + "<br/>".join(part for part in [customer_address, escape(restaurant.phone or ""), "GSTIN: " + escape(restaurant.gst_number) if restaurant.gst_number else ""] if part), body),
             Paragraph(f"<b>Invoice #:</b> {escape(invoice.invoice_number)}<br/><b>Issue date:</b> {invoice.invoice_date.strftime('%d %b %Y')}<br/><b>Due date:</b> {invoice.due_date.strftime('%d %b %Y') if invoice.due_date else '—'}<br/><b>Order ref:</b> {escape(invoice.order.order_code) if invoice.order else '—'}<br/><b>Status:</b> {escape(invoice.payment_status.replace('_', ' ').title())}", body)]
        ], colWidths=[3.6 * inch, 3.6 * inch], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf3f6")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d7e0e7")),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d7e0e7")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)
        ])),
        Spacer(1, 18)
    ]

    rows = [["Description", "Qty", "Unit", "Rate (INR)", "Discount (INR)", "Tax (INR)", "Amount (INR)"]]
    for item in invoice.items:
        rows.append([
            Paragraph(escape(item.product.name if item.product else f"Product #{item.product_id}"), body),
            f"{item.quantity:g}", escape(item.unit), f"{item.rate:,.2f}", f"{(item.discount or 0):,.2f}",
            f"{(item.tax or 0):,.2f}", f"{item.amount:,.2f}"
        ])
    items_table = Table(rows, colWidths=[2.35 * inch, 0.48 * inch, 0.48 * inch, 0.85 * inch, 0.85 * inch, 0.75 * inch, 0.85 * inch], repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e1e8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fa")]),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)
    ]))
    story.extend([items_table, Spacer(1, 14)])
    totals = [
        ["Subtotal", f"INR {invoice.subtotal:,.2f}"],
        ["Item + invoice discounts", f"- INR {sum((item.discount or 0) for item in invoice.items) + (invoice.discount or 0):,.2f}"],
        ["Item + invoice tax", f"INR {sum((item.tax or 0) for item in invoice.items) + (invoice.tax or 0):,.2f}"],
        [Paragraph("<b>Invoice total</b>", body), Paragraph(f"<b>INR {invoice.grand_total:,.2f}</b>", body)],
        ["Amount received", f"INR {invoice.amount_paid:,.2f}"],
        [Paragraph("<b>Balance due</b>", body), Paragraph(f"<b>INR {invoice.balance_due:,.2f}</b>", body)]
    ]
    totals_table = Table(totals, colWidths=[2.0 * inch, 1.6 * inch], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"), ("LINEABOVE", (0, 3), (-1, 3), 0.8, colors.HexColor("#17324d")), ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#edf3f6")), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.extend([totals_table, Spacer(1, 18)])
    if invoice.notes:
        story.extend([Paragraph("<b>Notes</b>", body), Paragraph(escape(invoice.notes).replace("\n", "<br/>"), body), Spacer(1, 10)])
    if not invoice.is_finalized:
        story.extend([Paragraph("DRAFT — This document is not a finalized invoice.", ParagraphStyle("DraftNotice", parent=body, textColor=colors.HexColor("#b45309"), fontName="Helvetica-Bold")), Spacer(1, 8)])
    story.append(Paragraph("Thank you for your business. Please quote the invoice number when making payment.", small))
    document.build(story)

    filename = re.sub(r"[^A-Za-z0-9._-]+", "-", invoice.invoice_number).strip("-._") or f"invoice-{invoice.id}"
    return Response(content=buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'})


@router.get("/{invoice_id}/payments")
async def get_invoice_payments(
    invoice_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all payments for a specific invoice
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    payments = db.query(Payment).filter(
        Payment.invoice_id == invoice_id
    ).order_by(Payment.date.desc()).all()
    
    return payments


@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Delete an invoice (Manager/Admin only)
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    if db.query(Payment).filter(Payment.invoice_id == invoice_id).count():
        raise HTTPException(status_code=400, detail="Invoices with payment history cannot be deleted. Reverse linked receipts instead.")
    if invoice.is_finalized:
        raise HTTPException(status_code=400, detail="Finalized invoices cannot be deleted. Keep the financial audit trail intact.")
    
    db.delete(invoice)
    db.commit()
    return {"message": "Invoice deleted successfully"}
