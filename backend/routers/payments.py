"""
Payments router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta
from backend.database import get_db
from backend.models.payment import Payment, PaymentType, PaymentStatus
from backend.models.invoice import Invoice
from backend.models.purchase import Purchase
from backend.models.order import SalesOrder
from backend.models.restaurant import Restaurant
from backend.models.vendor import Vendor
from backend.models.user import User
from backend.schemas.payment import PaymentCreate, PaymentResponse, PaymentStatusUpdate
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/payments", tags=["Payments"], dependencies=[Depends(require_manager_or_admin())])


def parse_dates(start_date: str, end_date: str):
    try:
        start_dt = datetime.fromisoformat(start_date) if "T" in start_date else datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.fromisoformat(end_date) if "T" in end_date else datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        return start_dt, end_dt
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD")


def recalculate_linked_payment_status(db: Session, invoice_id: Optional[int], purchase_id: Optional[int]):
    if invoice_id:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            total_paid = db.query(func.sum(Payment.amount)).filter(
                and_(
                    Payment.invoice_id == invoice.id,
                    Payment.payment_type == PaymentType.RECEIPT,
                    Payment.status == PaymentStatus.COMPLETED
                )
            ).scalar() or 0
            
            invoice.amount_paid = total_paid
            invoice.balance_due = max(0.0, invoice.grand_total - invoice.amount_paid)
            if invoice.amount_paid <= 0:
                invoice.payment_status = "unpaid"
            elif invoice.amount_paid < invoice.grand_total:
                invoice.payment_status = "partially_paid"
            else:
                invoice.payment_status = "paid"
                invoice.balance_due = 0
            
            if invoice.order_id:
                order = db.query(SalesOrder).filter(SalesOrder.id == invoice.order_id).first()
                if order:
                    order.payment_status = invoice.payment_status

    if purchase_id:
        purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
        if purchase:
            total_paid = db.query(func.sum(Payment.amount)).filter(
                and_(
                    Payment.purchase_id == purchase.id,
                    Payment.payment_type == PaymentType.PAYMENT,
                    Payment.status == PaymentStatus.COMPLETED
                )
            ).scalar() or 0
            
            if total_paid <= 0:
                purchase.payment_status = "unpaid"
            elif total_paid < purchase.total:
                purchase.payment_status = "partially_paid"
            else:
                purchase.payment_status = "paid"


@router.post("/", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new payment (Manager/Admin only)
    """
    payment_dict = payment_data.model_dump()
    
    if not payment_dict.get("status"):
        payment_dict["status"] = "completed"

    if payment_dict["payment_type"] == PaymentType.PAYMENT:
        if payment_dict.get("vendor_id") and payment_dict.get("expense_id"):
            raise HTTPException(status_code=400, detail="A payment can be linked to a vendor or an expense, not both")
        if not payment_dict.get("vendor_id") and not payment_dict.get("expense_id") and not payment_dict.get("paid_to"):
            raise HTTPException(status_code=400, detail="Paid To is required for an operations payment")
    elif payment_dict.get("category") or payment_dict.get("paid_to"):
        raise HTTPException(status_code=400, detail="Operations fields are only valid for payments")
    
    # Auto generate payment code if missing
    if not payment_dict.get("payment_code"):
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        payment_dict["payment_code"] = f"PAY-{timestamp}"
    elif db.query(Payment).filter(Payment.payment_code == payment_dict["payment_code"]).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment code already exists"
        )
    
    # Verify purchase if linked
    if payment_dict.get("purchase_id"):
        purchase = db.query(Purchase).filter(Purchase.id == payment_dict["purchase_id"]).first()
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase bill not found"
            )
        if not payment_dict.get("vendor_id"):
            payment_dict["vendor_id"] = purchase.vendor_id

    # Verify invoice if linked
    if payment_dict.get("invoice_id"):
        invoice = db.query(Invoice).filter(Invoice.id == payment_dict["invoice_id"]).first()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        
        if payment_dict["payment_type"] == PaymentType.RECEIPT:
            if invoice.restaurant_id and not payment_dict.get("restaurant_id"):
                payment_dict["restaurant_id"] = invoice.restaurant_id
    
    # Create payment
    new_payment = Payment(**payment_dict)
    db.add(new_payment)
    db.flush()
    
    recalculate_linked_payment_status(db, new_payment.invoice_id, new_payment.purchase_id)

    db.commit()
    db.refresh(new_payment)
    
    return new_payment


@router.put("/{payment_id}/status", response_model=PaymentResponse)
async def update_payment_status(
    payment_id: int,
    status_update: PaymentStatusUpdate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Update payment status (completed, pending, cancelled) and sync linked invoices/purchases/orders
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if status_update.status not in {item.value for item in PaymentStatus}:
        raise HTTPException(status_code=400, detail="Invalid payment status")
    payment.status = status_update.status
    payment.updated_at = func.now()
    db.flush()

    recalculate_linked_payment_status(db, payment.invoice_id, payment.purchase_id)

    db.commit()
    db.refresh(payment)
    return payment


@router.delete("/{payment_id}")
async def delete_payment(
    payment_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """Reverse a payment without removing its permanent ledger record."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    invoice_id = payment.invoice_id
    purchase_id = payment.purchase_id
    payment.status = PaymentStatus.REVERSED
    payment.updated_at = func.now()
    db.flush()

    recalculate_linked_payment_status(db, invoice_id, purchase_id)

    db.commit()
    return {"message": "Payment reversed successfully"}


@router.get("/", response_model=List[PaymentResponse])
async def get_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    payment_type: Optional[str] = None,
    restaurant_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    payment_method: Optional[str] = None,
    payment_status: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all payments with optional filters
    """
    query = db.query(Payment)
    
    if payment_type:
        query = query.filter(Payment.payment_type == payment_type)
    
    if restaurant_id:
        query = query.filter(Payment.restaurant_id == restaurant_id)
    
    if vendor_id:
        query = query.filter(Payment.vendor_id == vendor_id)
    
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)

    if payment_status:
        query = query.filter(Payment.status == payment_status)
    
    payments = query.order_by(Payment.date.desc()).offset(skip).limit(limit).all()
    return payments


@router.get("/{payment_id:int}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific payment by ID
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    return payment


@router.get("/vendor/{vendor_id}/ledger")
async def get_vendor_ledger(
    vendor_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    purchases = db.query(Purchase).filter(Purchase.vendor_id == vendor_id).order_by(Purchase.purchase_date.desc()).all()
    payments = db.query(Payment).filter(
        Payment.vendor_id == vendor_id,
        Payment.payment_type == PaymentType.PAYMENT
    ).order_by(Payment.date.desc()).all()
    if start_date or end_date:
        start_dt, end_dt = parse_dates(
            start_date or (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d"),
            end_date or datetime.utcnow().strftime("%Y-%m-%d")
        )
    else:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=60)
    adjustments = vendor.credit_adjustments or 0
    statement_purchases = [purchase for purchase in purchases if start_dt <= purchase.purchase_date <= end_dt]
    statement_payments = [payment for payment in payments if start_dt <= payment.date <= end_dt]
    opening_purchases = sum(purchase.total or 0 for purchase in purchases if purchase.purchase_date < start_dt)
    opening_payments = sum(payment.amount or 0 for payment in payments if payment.date < start_dt and payment.status == PaymentStatus.COMPLETED)
    opening_balance = max(0, opening_purchases - opening_payments - adjustments)
    period_purchases = sum(purchase.total or 0 for purchase in statement_purchases)
    period_payments = sum(payment.amount or 0 for payment in statement_payments if payment.status == PaymentStatus.COMPLETED)
    total_purchases = sum(purchase.total or 0 for purchase in purchases)
    total_payments = sum(payment.amount or 0 for payment in payments if payment.status == PaymentStatus.COMPLETED)

    return {
        "vendor_id": vendor.id,
        "vendor_name": vendor.name,
        "total_purchases": total_purchases,
        "total_payments": total_payments,
        "credit_adjustments": adjustments,
        "pending_amount": max(0, total_purchases - total_payments - adjustments),
        "purchases": purchases,
        "payments": payments,
        "statement": {
            "start_date": start_dt,
            "end_date": end_dt,
            "opening_balance": opening_balance,
            "purchases": statement_purchases,
            "payments": statement_payments,
            "period_purchases": period_purchases,
            "period_payments": period_payments,
            "closing_balance": max(0, opening_balance + period_purchases - period_payments)
        }
    }


@router.get("/summary")
async def get_payments_summary(
    start_date: str = Query(...),
    end_date: str = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get payments summary for a date range
    """
    start_dt, end_dt = parse_dates(start_date, end_date)
    
    # Total receipts (from restaurants/customers)
    total_receipts = db.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.payment_type == PaymentType.RECEIPT,
            Payment.status == "completed",
            Payment.date >= start_dt,
            Payment.date <= end_dt
        )
    ).scalar() or 0
    
    # Total payments (to vendors)
    total_payments = db.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.payment_type == PaymentType.PAYMENT,
            Payment.status == "completed",
            Payment.date >= start_dt,
            Payment.date <= end_dt
        )
    ).scalar() or 0
    
    # Net cash flow
    net_cash_flow = total_receipts - total_payments
    
    return {
        "period_start": start_dt,
        "period_end": end_dt,
        "total_receipts": total_receipts,
        "total_payments": total_payments,
        "net_cash_flow": net_cash_flow
    }
