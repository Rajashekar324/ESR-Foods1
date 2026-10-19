"""
Invoices router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta
from backend.database import get_db
from backend.models.invoice import Invoice, InvoiceItem
from backend.models.restaurant import Restaurant
from backend.models.payment import Payment, PaymentType
from backend.models.product import Product
from backend.models.user import User
from backend.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceItemCreate, InvoiceItemResponse
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/invoices", tags=["Invoices"], dependencies=[Depends(require_manager_or_admin())])


def generate_invoice_number(db: Session) -> str:
    """Generate unique invoice number"""
    year = datetime.utcnow().year
    prefix = f"ESR-INV-{year}-"
    
    # Find the highest invoice number for this year
    last_invoice = db.query(Invoice).filter(
        Invoice.invoice_number.like(f"{prefix}%")
    ).order_by(Invoice.invoice_number.desc()).first()
    
    if last_invoice:
        # Extract the number part and increment
        last_num = int(last_invoice.invoice_number.split("-")[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
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
    subtotal = sum(item.quantity * item.rate for item in invoice_data.items)
    discount = invoice_data.discount
    tax = invoice_data.tax
    grand_total = subtotal - discount + tax
    
    # Set due date if not provided (default 30 days)
    due_date = invoice_data.due_date
    if not due_date:
        due_date = invoice_data.invoice_date + timedelta(days=30)
    
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
    
    update_data = invoice_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)
    
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
    
    db.delete(invoice)
    db.commit()
    return {"message": "Invoice deleted successfully"}
