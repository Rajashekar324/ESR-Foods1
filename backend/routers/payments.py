"""
Payments router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import uuid4
from backend.database import get_db
from backend.models.payment import Payment, PaymentType, PaymentStatus
from backend.models.invoice import Invoice
from backend.models.purchase import Purchase, PurchaseStatus
from backend.models.order import SalesOrder
from backend.models.restaurant import Restaurant
from backend.models.vendor import Vendor
from backend.models.customer import RetailCustomer
from backend.models.expense import Expense
from backend.models.user import User
from backend.schemas.payment import PaymentCreate, PaymentResponse, PaymentStatusUpdate, PaymentUpdate
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/payments", tags=["Payments"], dependencies=[Depends(require_manager_or_admin())])


def parse_dates(start_date: str, end_date: str):
    try:
        start_dt = datetime.fromisoformat(start_date) if "T" in start_date else datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.fromisoformat(end_date) if "T" in end_date else datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        return start_dt, end_dt
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD")


def as_naive_datetime(value: datetime) -> datetime:
    """Normalize persisted date values for comparisons across SQLite and other DB drivers."""
    return value.replace(tzinfo=None) if value.tzinfo else value


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

    if payment_dict["status"] not in {item.value for item in PaymentStatus}:
        raise HTTPException(status_code=400, detail="Invalid payment status")

    if payment_dict["payment_type"] == PaymentType.PAYMENT:
        if payment_dict.get("restaurant_id") or payment_dict.get("customer_id") or payment_dict.get("invoice_id"):
            raise HTTPException(status_code=400, detail="Outgoing payments cannot be linked to a sales customer or invoice")
        if payment_dict.get("vendor_id") and payment_dict.get("expense_id"):
            raise HTTPException(status_code=400, detail="A payment can be linked to a vendor or an expense, not both")
        if not payment_dict.get("vendor_id") and not payment_dict.get("expense_id") and not payment_dict.get("paid_to") and not payment_dict.get("purchase_id"):
            raise HTTPException(status_code=400, detail="Paid To is required for an operations payment")
        if payment_dict.get("category") and not payment_dict.get("paid_to"):
            raise HTTPException(status_code=400, detail="Paid To is required for an operations payment")
    else:
        if payment_dict.get("purchase_id") or payment_dict.get("expense_id") or payment_dict.get("category") or payment_dict.get("paid_to"):
            raise HTTPException(status_code=400, detail="Received receipts cannot be linked to outgoing payments or operations")
    
    # Auto generate payment code if missing
    if not payment_dict.get("payment_code"):
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        payment_dict["payment_code"] = f"{'REC' if payment_dict['payment_type'] == PaymentType.RECEIPT else 'PAY'}-{timestamp}-{uuid4().hex[:6].upper()}"
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
        elif payment_dict["vendor_id"] != purchase.vendor_id:
            raise HTTPException(status_code=400, detail="The selected vendor does not match the purchase")

    if payment_dict.get("vendor_id") and not db.query(Vendor).filter(Vendor.id == payment_dict["vendor_id"]).first():
        raise HTTPException(status_code=404, detail="Vendor not found")
    if payment_dict.get("customer_id") and not db.query(RetailCustomer).filter(RetailCustomer.id == payment_dict["customer_id"]).first():
        raise HTTPException(status_code=404, detail="Customer not found")
    if payment_dict.get("restaurant_id") and not db.query(Restaurant).filter(Restaurant.id == payment_dict["restaurant_id"]).first():
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if payment_dict.get("expense_id") and not db.query(Expense).filter(Expense.id == payment_dict["expense_id"]).first():
        raise HTTPException(status_code=404, detail="Expense not found")

    # Verify invoice if linked
    if payment_dict.get("invoice_id"):
        invoice = db.query(Invoice).filter(Invoice.id == payment_dict["invoice_id"]).first()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        
        if payment_dict["payment_type"] != PaymentType.RECEIPT:
            raise HTTPException(status_code=400, detail="Invoices can only be linked to received payments")
        if not invoice.is_finalized:
            raise HTTPException(status_code=400, detail="Only finalized invoices can receive payments")
        if payment_dict.get("restaurant_id") and payment_dict["restaurant_id"] != invoice.restaurant_id:
            raise HTTPException(status_code=400, detail="The selected restaurant does not match the invoice")
        if payment_dict.get("customer_id") or payment_dict.get("vendor_id"):
            raise HTTPException(status_code=400, detail="Restaurant invoices cannot be linked to a vendor or retail customer")
        payment_dict["restaurant_id"] = invoice.restaurant_id
        if payment_dict["status"] == PaymentStatus.COMPLETED:
            already_received = db.query(func.sum(Payment.amount)).filter(
                Payment.invoice_id == invoice.id,
                Payment.payment_type == PaymentType.RECEIPT,
                Payment.status == PaymentStatus.COMPLETED
            ).scalar() or 0
            if already_received + payment_dict["amount"] > invoice.grand_total:
                raise HTTPException(status_code=400, detail="Receipt amount exceeds the invoice balance due")

    if payment_dict["payment_type"] == PaymentType.RECEIPT:
        entity_ids = [payment_dict.get("restaurant_id"), payment_dict.get("vendor_id"), payment_dict.get("customer_id")]
        if sum(value is not None for value in entity_ids) != 1:
            raise HTTPException(status_code=400, detail="Choose exactly one receipt source: restaurant, vendor, or customer")
    
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
    if status_update.status == PaymentStatus.COMPLETED and payment.invoice_id and payment.payment_type == PaymentType.RECEIPT:
        invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
        if invoice:
            other_completed = db.query(func.sum(Payment.amount)).filter(
                Payment.invoice_id == invoice.id,
                Payment.payment_type == PaymentType.RECEIPT,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.id != payment.id
            ).scalar() or 0
            if other_completed + payment.amount > invoice.grand_total:
                raise HTTPException(status_code=400, detail="Completing this receipt would exceed the invoice balance due")
    payment.status = status_update.status
    payment.updated_at = func.now()
    db.flush()

    recalculate_linked_payment_status(db, payment.invoice_id, payment.purchase_id)

    db.commit()
    db.refresh(payment)
    return payment


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db),
):
    """Edit a payment ledger entry and reconcile linked document status."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    update_data = payment_data.model_dump(exclude_unset=True)
    new_invoice_id = update_data.get("invoice_id", payment.invoice_id)
    new_amount = update_data.get("amount", payment.amount)
    new_status = update_data.get("status", payment.status)
    if new_status not in {item.value for item in PaymentStatus}:
        raise HTTPException(status_code=400, detail="Invalid payment status")
    if new_invoice_id is not None:
        if payment.payment_type != PaymentType.RECEIPT or not payment.restaurant_id:
            raise HTTPException(status_code=400, detail="Only restaurant receipts can be linked to an invoice")
        invoice = db.query(Invoice).filter(Invoice.id == new_invoice_id).first()
        if not invoice or not invoice.is_finalized:
            raise HTTPException(status_code=400, detail="A finalized invoice is required")
        if invoice.restaurant_id != payment.restaurant_id:
            raise HTTPException(status_code=400, detail="The selected restaurant does not match the invoice")
        if new_status == PaymentStatus.COMPLETED:
            other_paid = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
                Payment.invoice_id == new_invoice_id,
                Payment.payment_type == PaymentType.RECEIPT,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.id != payment.id,
            ).scalar() or 0
            if other_paid + new_amount > invoice.grand_total:
                raise HTTPException(status_code=400, detail="Receipt amount exceeds the invoice balance due")
    old_invoice_id, purchase_id = payment.invoice_id, payment.purchase_id
    for field, value in update_data.items():
        setattr(payment, field, value)
    payment.updated_at = func.now()
    db.flush()
    recalculate_linked_payment_status(db, old_invoice_id, purchase_id)
    if payment.invoice_id != old_invoice_id:
        recalculate_linked_payment_status(db, payment.invoice_id, purchase_id)
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
    payment_source: Optional[str] = Query(None, pattern="^(restaurant|vendor|customer|operations)$"),
    restaurant_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    customer_id: Optional[int] = None,
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

    if payment_source == "restaurant":
        query = query.filter(Payment.restaurant_id.isnot(None))
    elif payment_source == "vendor":
        query = query.filter(Payment.vendor_id.isnot(None))
    elif payment_source == "customer":
        query = query.filter(Payment.customer_id.isnot(None))
    elif payment_source == "operations":
        query = query.filter(Payment.payment_type == PaymentType.PAYMENT, Payment.vendor_id.is_(None), Payment.restaurant_id.is_(None), Payment.customer_id.is_(None))
    
    if restaurant_id:
        query = query.filter(Payment.restaurant_id == restaurant_id)
    
    if vendor_id:
        query = query.filter(Payment.vendor_id == vendor_id)

    if customer_id:
        query = query.filter(Payment.customer_id == customer_id)
    
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

    purchases = db.query(Purchase).filter(
        Purchase.vendor_id == vendor_id,
        Purchase.status != PurchaseStatus.CANCELLED
    ).order_by(Purchase.purchase_date.desc()).all()
    payments = db.query(Payment).filter(
        Payment.vendor_id == vendor_id,
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
    statement_purchases = [purchase for purchase in purchases if start_dt <= as_naive_datetime(purchase.purchase_date) <= end_dt]
    statement_payments = [payment for payment in payments if start_dt <= as_naive_datetime(payment.date) <= end_dt]
    opening_purchases = sum(purchase.total or 0 for purchase in purchases if as_naive_datetime(purchase.purchase_date) < start_dt)
    opening_payments = sum(payment.amount or 0 for payment in payments if as_naive_datetime(payment.date) < start_dt and payment.status == PaymentStatus.COMPLETED and payment.payment_type == PaymentType.PAYMENT)
    opening_refunds = sum(payment.amount or 0 for payment in payments if as_naive_datetime(payment.date) < start_dt and payment.status == PaymentStatus.COMPLETED and payment.payment_type == PaymentType.RECEIPT)
    opening_balance = opening_purchases - opening_payments - opening_refunds - adjustments
    period_purchases = sum(purchase.total or 0 for purchase in statement_purchases)
    period_payments = sum(payment.amount or 0 for payment in statement_payments if payment.status == PaymentStatus.COMPLETED and payment.payment_type == PaymentType.PAYMENT)
    period_refunds = sum(payment.amount or 0 for payment in statement_payments if payment.status == PaymentStatus.COMPLETED and payment.payment_type == PaymentType.RECEIPT)
    total_purchases = sum(purchase.total or 0 for purchase in purchases)
    total_payments = sum(payment.amount or 0 for payment in payments if payment.status == PaymentStatus.COMPLETED and payment.payment_type == PaymentType.PAYMENT)
    total_refunds = sum(payment.amount or 0 for payment in payments if payment.status == PaymentStatus.COMPLETED and payment.payment_type == PaymentType.RECEIPT)
    current_balance = total_purchases - total_payments - total_refunds - adjustments

    return {
        "vendor_id": vendor.id,
        "vendor_name": vendor.name,
        "total_purchases": total_purchases,
        "total_payments": total_payments,
        "refunds_received": total_refunds,
        "credit_adjustments": adjustments,
        "pending_amount": max(0, current_balance),
        "vendor_credit": max(0, -current_balance),
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
            "period_refunds": period_refunds,
            "closing_balance": opening_balance + period_purchases - period_payments - period_refunds
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
