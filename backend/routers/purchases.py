"""
Purchases router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from backend.database import get_db
from backend.models.purchase import Purchase, PurchaseItem, PurchaseStatus
from backend.models.vendor import Vendor
from backend.models.batch import ProductBatch
from backend.models.stock_movement import StockMovement, MovementType
from backend.models.product import Product
from backend.models.payment import Payment, PaymentType, PaymentMethod
from backend.models.user import User
from backend.schemas.purchase import PurchaseCreate, PurchaseUpdate, PurchaseResponse, PurchaseItemCreate, PurchaseItemResponse
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/purchases", tags=["Purchases"], dependencies=[Depends(require_manager_or_admin())])


@router.post("/", response_model=PurchaseResponse)
async def create_purchase(
    purchase_data: PurchaseCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new purchase (Manager/Admin only) and auto-add payment record
    """
    purchase_code = purchase_data.purchase_code
    if not purchase_code:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        purchase_code = f"PO-{timestamp}"
    elif db.query(Purchase).filter(Purchase.purchase_code == purchase_code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purchase code already exists"
        )
    
    # Verify vendor exists
    vendor = db.query(Vendor).filter(Vendor.id == purchase_data.vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Calculate totals
    subtotal = sum(item.quantity * item.rate for item in purchase_data.items)
    item_discounts = sum(item.discount for item in purchase_data.items)
    item_taxes = sum(item.tax for item in purchase_data.items)
    discount = purchase_data.discount
    tax = purchase_data.tax
    if discount < 0 or tax < 0 or item_discounts < 0 or item_taxes < 0 or discount + item_discounts > subtotal:
        raise HTTPException(status_code=400, detail="Purchase discounts and taxes must be non-negative, and discounts cannot exceed subtotal")
    for item in purchase_data.items:
        if item.discount > item.quantity * item.rate:
            raise HTTPException(status_code=400, detail="A purchase line discount cannot exceed its line subtotal")
    total = subtotal - discount - item_discounts + tax + item_taxes
    if total <= 0:
        raise HTTPException(status_code=400, detail="Purchase total must be greater than zero")
    
    # Create purchase
    new_purchase = Purchase(
        purchase_code=purchase_code,
        vendor_id=purchase_data.vendor_id,
        vendor_invoice_number=purchase_data.vendor_invoice_number,
        purchase_date=purchase_data.purchase_date,
        expected_date=purchase_data.expected_date,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total=total,
        notes=purchase_data.notes,
        status=PurchaseStatus.DRAFT
    )
    
    db.add(new_purchase)
    db.flush()
    
    # Create purchase items
    for item_data in purchase_data.items:
        # Verify product exists
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with ID {item_data.product_id} not found"
            )
        
        item_total = item_data.quantity * item_data.rate - item_data.discount + item_data.tax
        purchase_item = PurchaseItem(
            purchase_id=new_purchase.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit=item_data.unit,
            rate=item_data.rate,
            discount=item_data.discount,
            tax=item_data.tax,
            total=item_total
        )
        db.add(purchase_item)
    
    # Auto-create payment entry for purchase
    try:
        timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        auto_payment = Payment(
            payment_code=f"PAY-{new_purchase.purchase_code}",
            payment_type=PaymentType.PAYMENT,
            date=new_purchase.purchase_date,
            purchase_id=new_purchase.id,
            vendor_id=new_purchase.vendor_id,
            amount=new_purchase.total,
            payment_method=PaymentMethod.CASH,
            status="pending",
            notes=f"Auto payment entry for Purchase {new_purchase.purchase_code}"
        )
        db.add(auto_payment)
    except Exception as e:
        print("Notice: Auto payment creation for purchase failed:", e)

    db.commit()
    db.refresh(new_purchase)
    
    return new_purchase


@router.get("/", response_model=List[PurchaseResponse])
async def get_purchases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    vendor_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all purchases with optional filters
    """
    query = db.query(Purchase)
    
    if vendor_id:
        query = query.filter(Purchase.vendor_id == vendor_id)
    
    if status:
        query = query.filter(Purchase.status == status)
    
    purchases = query.order_by(Purchase.purchase_date.desc()).offset(skip).limit(limit).all()
    return purchases


@router.get("/{purchase_id}", response_model=PurchaseResponse)
async def get_purchase(
    purchase_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific purchase by ID
    """
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found"
        )
    return purchase


@router.put("/{purchase_id}", response_model=PurchaseResponse)
async def update_purchase(
    purchase_id: int,
    purchase_data: PurchaseUpdate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Update a purchase (Manager/Admin only)
    """
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found"
        )
    
    update_data = purchase_data.model_dump(exclude_unset=True)
    requested_status = update_data.get("status")
    if requested_status in {PurchaseStatus.RECEIVED, PurchaseStatus.PARTIALLY_RECEIVED} and requested_status != purchase.status:
        raise HTTPException(status_code=400, detail="Use the Receive action to update inventory for a purchase")
    if requested_status == PurchaseStatus.CANCELLED and purchase.status != PurchaseStatus.CANCELLED:
        if purchase.status in {PurchaseStatus.RECEIVED, PurchaseStatus.PARTIALLY_RECEIVED}:
            raise HTTPException(status_code=400, detail="Received purchases cannot be cancelled because they affect inventory")
        if db.query(Payment).filter(Payment.purchase_id == purchase_id, Payment.status == "completed").first():
            raise HTTPException(status_code=400, detail="Purchases with completed payment history cannot be cancelled")
    if "discount" in update_data or "tax" in update_data:
        discount = update_data.get("discount", purchase.discount or 0)
        tax = update_data.get("tax", purchase.tax or 0)
        if discount < 0 or tax < 0:
            raise HTTPException(status_code=400, detail="Purchase discount and tax cannot be negative")
        if discount > (purchase.subtotal or 0):
            raise HTTPException(status_code=400, detail="Purchase discount cannot exceed subtotal")
            line_discounts = sum(item.discount or 0 for item in purchase.items)
            line_taxes = sum(item.tax or 0 for item in purchase.items)
            if discount + line_discounts > (purchase.subtotal or 0):
                raise HTTPException(status_code=400, detail="Purchase discounts cannot exceed subtotal")
            purchase.total = (purchase.subtotal or 0) - discount - line_discounts + tax + line_taxes
            if purchase.total <= 0:
                raise HTTPException(status_code=400, detail="Purchase total must be greater than zero")
    new_vendor_id = update_data.get("vendor_id")
    if new_vendor_id is not None and new_vendor_id != purchase.vendor_id:
        if not db.query(Vendor).filter(Vendor.id == new_vendor_id).first():
            raise HTTPException(status_code=404, detail="Vendor not found")
        if purchase.status in {PurchaseStatus.RECEIVED, PurchaseStatus.CANCELLED}:
            raise HTTPException(status_code=400, detail="Received or cancelled purchases cannot be reassigned to another vendor")
        completed_payment = db.query(Payment).filter(
            Payment.purchase_id == purchase_id,
            Payment.payment_type == PaymentType.PAYMENT,
            Payment.status == "completed"
        ).first()
        if completed_payment:
            raise HTTPException(status_code=400, detail="A purchase with completed payments cannot be reassigned to another vendor")
    for field, value in update_data.items():
        setattr(purchase, field, value)

    if purchase.status == PurchaseStatus.CANCELLED:
        for pending_payment in db.query(Payment).filter(
            Payment.purchase_id == purchase_id,
            Payment.status == "pending"
        ).all():
            pending_payment.status = "cancelled"
    
    purchase.updated_at = func.now()

    # Sync linked payment amount if exists
    linked_payments = db.query(Payment).filter(
        Payment.purchase_id == purchase_id,
        Payment.status == "pending"
    ).all()
    for linked_payment in linked_payments:
        linked_payment.vendor_id = purchase.vendor_id
        if (linked_payment.notes or "").startswith("Auto payment entry"):
            linked_payment.amount = purchase.total
            linked_payment.date = purchase.purchase_date

    db.commit()
    db.refresh(purchase)
    
    return purchase


@router.post("/{purchase_id}/receive")
async def receive_purchase(
    purchase_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Receive goods for a purchase and update inventory (Manager/Admin only)
    """
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found"
        )
    
    if purchase.status == PurchaseStatus.RECEIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purchase already received"
        )
    if purchase.status == PurchaseStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cancelled purchases cannot be received")
    
    # Update purchase status
    purchase.status = PurchaseStatus.RECEIVED
    purchase.received_date = datetime.utcnow()
    
    # Process each item
    for item in purchase.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            # Update product stock
            product.current_stock += item.quantity
            
            # Create stock movement
            stock_movement = StockMovement(
                product_id=item.product_id,
                movement_type=MovementType.PURCHASE_RECEIVED,
                reference_id=purchase.id,
                reference_type="purchase",
                quantity=item.quantity,
                unit=item.unit,
                rate=item.rate,
                total=item.total,
                balance_after=product.current_stock,
                notes=f"Received from purchase {purchase.purchase_code}"
            )
            db.add(stock_movement)
            
            # Create batch
            batch_number = f"BATCH-{purchase.purchase_code}-{item.id}"
            new_batch = ProductBatch(
                batch_number=batch_number,
                product_id=item.product_id,
                vendor_id=purchase.vendor_id,
                purchase_date=purchase.purchase_date,
                received_date=datetime.utcnow(),
                quantity=item.quantity,
                remaining_quantity=item.quantity,
                purchase_rate=item.rate
            )
            db.add(new_batch)
    
    db.commit()
    
    return {"message": "Purchase received successfully, inventory updated"}


@router.delete("/{purchase_id}")
async def delete_purchase(
    purchase_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Delete a purchase (Manager/Admin only) with safe cascade cleanup
    """
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found"
        )

    if purchase.status in {PurchaseStatus.RECEIVED, PurchaseStatus.PARTIALLY_RECEIVED}:
        raise HTTPException(status_code=400, detail="Received purchases cannot be deleted because they affect inventory. Use an inventory adjustment instead.")
    if db.query(Payment).filter(Payment.purchase_id == purchase_id, Payment.status == "completed").first():
        raise HTTPException(status_code=400, detail="Purchases with completed payment history cannot be deleted. Reverse the payment first.")

    # Keep the purchase and its audit trail, while removing its unpaid draft payable.
    purchase.status = PurchaseStatus.CANCELLED
    for pending_payment in db.query(Payment).filter(
        Payment.purchase_id == purchase_id,
        Payment.status == "pending"
    ).all():
        pending_payment.status = "cancelled"
    db.commit()
    return {"message": "Purchase cancelled; its financial history was retained."}
