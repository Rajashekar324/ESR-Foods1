"""Authoritative, derived restaurant receivable calculations."""
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.models.invoice import Invoice
from backend.models.order import OrderStatus, SalesOrder
from backend.models.payment import Payment, PaymentStatus, PaymentType


def finalized_restaurant_invoices(db: Session, restaurant_id: int):
    """Invoices that contribute a debit; cancelled order invoices are excluded."""
    return db.query(Invoice).outerjoin(
        SalesOrder, Invoice.order_id == SalesOrder.id
    ).filter(
        Invoice.restaurant_id == restaurant_id,
        Invoice.is_finalized.is_(True),
        or_(Invoice.order_id.is_(None), SalesOrder.order_status != OrderStatus.CANCELLED),
    )


def restaurant_balance_totals(db: Session, restaurant_id: int):
    """Return debit, receipt, and outstanding totals from the persisted ledger."""
    total_debits = finalized_restaurant_invoices(db, restaurant_id).with_entities(
        func.coalesce(func.sum(Invoice.grand_total), 0)
    ).scalar() or 0
    total_receipts = completed_restaurant_receipts(db, restaurant_id).with_entities(
        func.coalesce(func.sum(Payment.amount), 0)
    ).scalar() or 0
    total_debits = float(total_debits)
    total_receipts = float(total_receipts)
    return {
        "total_debits": total_debits,
        "total_receipts": total_receipts,
        "outstanding": max(0.0, total_debits - total_receipts),
    }


def completed_restaurant_receipts(db: Session, restaurant_id: int):
    return db.query(Payment).filter(
        Payment.restaurant_id == restaurant_id,
        Payment.payment_type == PaymentType.RECEIPT,
        Payment.status == PaymentStatus.COMPLETED,
    )
