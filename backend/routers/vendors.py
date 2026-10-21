"""
Vendors router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from backend.database import get_db
from backend.models.vendor import Vendor
from backend.models.purchase import Purchase, PurchaseStatus
from backend.models.payment import Payment, PaymentType, PaymentStatus
from backend.models.user import User
from backend.schemas.vendor import VendorCreate, VendorUpdate, VendorResponse
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/vendors", tags=["Vendors"], dependencies=[Depends(require_manager_or_admin())])


@router.post("/", response_model=VendorResponse)
async def create_vendor(
    vendor_data: VendorCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new vendor (Manager/Admin only)
    """
    if db.query(Vendor).filter(Vendor.vendor_code == vendor_data.vendor_code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor code already exists"
        )
    
    new_vendor = Vendor(**vendor_data.model_dump())
    db.add(new_vendor)
    db.commit()
    db.refresh(new_vendor)
    
    return new_vendor


@router.get("/", response_model=List[VendorResponse])
async def get_vendors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    status: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all vendors with optional filters
    """
    query = db.query(Vendor)
    
    if search:
        query = query.filter(
            (Vendor.name.ilike(f"%{search}%")) |
            (Vendor.vendor_code.ilike(f"%{search}%")) |
            (Vendor.company_name.ilike(f"%{search}%"))
        )
    
    if status is not None:
        query = query.filter(Vendor.status == status)
    
    vendors = query.order_by(Vendor.name).offset(skip).limit(limit).all()
    return vendors


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific vendor by ID
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    return vendor


@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: int,
    vendor_data: VendorUpdate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Update a vendor (Manager/Admin only)
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    update_data = vendor_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor, field, value)
    
    vendor.updated_at = func.now()
    db.commit()
    db.refresh(vendor)
    
    return vendor


@router.get("/{vendor_id}/purchases")
async def get_vendor_purchases(
    vendor_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all purchases for a specific vendor
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    purchases = db.query(Purchase).filter(
        Purchase.vendor_id == vendor_id,
        Purchase.status != PurchaseStatus.CANCELLED
    ).order_by(Purchase.purchase_date.desc()).offset(skip).limit(limit).all()
    
    return purchases


@router.get("/{vendor_id}/payments")
async def get_vendor_payments(
    vendor_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all payments made to a specific vendor
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    payments = db.query(Payment).filter(
        Payment.vendor_id == vendor_id
    ).order_by(Payment.date.desc()).offset(skip).limit(limit).all()
    
    return payments


@router.get("/{vendor_id}/summary")
async def get_vendor_summary(
    vendor_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get financial summary for a vendor
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Total purchases
    total_purchases = db.query(func.sum(Purchase.total)).filter(
        Purchase.vendor_id == vendor_id,
        Purchase.status != PurchaseStatus.CANCELLED
    ).scalar() or 0
    
    # Outgoing payments and incoming refunds both reduce the net payable.
    total_payments = db.query(func.sum(Payment.amount)).filter(
        Payment.vendor_id == vendor_id,
        Payment.payment_type == PaymentType.PAYMENT,
        Payment.status == PaymentStatus.COMPLETED
    ).scalar() or 0

    total_refunds_received = db.query(func.sum(Payment.amount)).filter(
        Payment.vendor_id == vendor_id,
        Payment.payment_type == PaymentType.RECEIPT,
        Payment.status == PaymentStatus.COMPLETED
    ).scalar() or 0
    
    adjustments = vendor.credit_adjustments or 0
    net_balance = total_purchases - total_payments - total_refunds_received - adjustments
    outstanding = max(0, net_balance)
    
    # Number of purchases
    purchase_count = db.query(Purchase).filter(
        Purchase.vendor_id == vendor_id,
        Purchase.status != PurchaseStatus.CANCELLED
    ).count()
    
    # Last purchase date
    last_purchase = db.query(Purchase).filter(
        Purchase.vendor_id == vendor_id,
        Purchase.status != PurchaseStatus.CANCELLED
    ).order_by(Purchase.purchase_date.desc()).first()
    
    return {
        "vendor_id": vendor.id,
        "vendor_name": vendor.name,
        "total_purchases": total_purchases,
        "total_payments": total_payments,
        "refunds_received": total_refunds_received,
        "credit_adjustments": adjustments,
        "outstanding_payable": outstanding,
        "vendor_credit": max(0, -net_balance),
        "purchase_count": purchase_count,
        "last_purchase_date": last_purchase.purchase_date if last_purchase else None
    }


@router.delete("/{vendor_id}")
async def delete_vendor(
    vendor_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Delete a vendor (Manager/Admin only)
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    has_purchase_history = db.query(Purchase).filter(Purchase.vendor_id == vendor_id).first()
    has_payment_history = db.query(Payment).filter(Payment.vendor_id == vendor_id).first()
    if has_purchase_history or has_payment_history:
        raise HTTPException(status_code=400, detail="Vendors with purchase or payment history cannot be deleted. Deactivate the vendor to preserve financial records.")
    
    db.delete(vendor)
    db.commit()
    return {"message": "Vendor deleted successfully"}
