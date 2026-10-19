"""
Inventory router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta
from backend.database import get_db
from backend.models.product import Product
from backend.models.batch import ProductBatch, BatchStatus
from backend.models.stock_movement import StockMovement, MovementType
from backend.models.user import User
from backend.schemas.batch import BatchCreate, BatchResponse
from backend.schemas.stock_movement import StockMovementCreate, StockMovementResponse
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/inventory", tags=["Inventory"], dependencies=[Depends(require_manager_or_admin())])


@router.get("/")
async def get_inventory(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    low_stock_only: bool = False,
    expiring_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current inventory with optional filters
    """
    query = db.query(Product).filter(Product.is_active == True)
    
    if low_stock_only:
        query = query.filter(
            (Product.current_stock <= Product.reorder_level) |
            (Product.current_stock <= Product.minimum_stock)
        )
    
    products = query.order_by(Product.name).offset(skip).limit(limit).all()
    
    # Add expiring info if requested
    result = []
    for product in products:
        product_data = {
            "id": product.id,
            "product_code": product.product_code,
            "name": product.name,
            "current_stock": product.current_stock,
            "minimum_stock": product.minimum_stock,
            "reorder_level": product.reorder_level,
            "unit": product.unit,
            "purchase_price": product.purchase_price,
            "selling_price": product.selling_price,
            "stock_value": product.current_stock * product.purchase_price,
            "is_low_stock": product.current_stock <= product.reorder_level,
            "is_critical": product.current_stock <= product.minimum_stock
        }
        
        if expiring_only:
            # Check for expiring batches
            warning_days = 7
            warning_date = datetime.utcnow() + timedelta(days=warning_days)
            expiring_batches = db.query(ProductBatch).filter(
                and_(
                    ProductBatch.product_id == product.id,
                    ProductBatch.expiry_date <= warning_date,
                    ProductBatch.expiry_date > datetime.utcnow(),
                    ProductBatch.remaining_quantity > 0
                )
            ).count()
            
            if expiring_batches > 0:
                product_data["expiring_batches"] = expiring_batches
                result.append(product_data)
        else:
            result.append(product_data)
    
    return result


@router.get("/movements", response_model=List[StockMovementResponse])
async def get_stock_movements(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    product_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get stock movements with optional filters
    """
    query = db.query(StockMovement)
    
    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    
    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)
    
    movements = query.order_by(StockMovement.created_at.desc()).offset(skip).limit(limit).all()
    return movements


@router.post("/adjustment", response_model=StockMovementResponse)
async def create_stock_adjustment(
    movement_data: StockMovementCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a stock adjustment (Manager/Admin only)
    """
    product = db.query(Product).filter(Product.id == movement_data.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Determine if it's an IN or OUT adjustment
    if movement_data.movement_type in [MovementType.STOCK_ADJUSTMENT_IN, MovementType.CUSTOMER_RETURN]:
        # Stock increase
        new_balance = product.current_stock + movement_data.quantity
    else:
        # Stock decrease
        new_balance = product.current_stock - movement_data.quantity
        if new_balance < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient stock for adjustment"
            )
    
    # Create stock movement
    total = movement_data.quantity * movement_data.rate if movement_data.rate else None
    stock_movement = StockMovement(
        product_id=movement_data.product_id,
        movement_type=movement_data.movement_type,
        reference_id=movement_data.reference_id,
        reference_type=movement_data.reference_type,
        quantity=movement_data.quantity,
        unit=movement_data.unit,
        rate=movement_data.rate,
        total=total,
        balance_after=new_balance,
        notes=movement_data.notes
    )
    
    # Update product stock
    product.current_stock = new_balance
    
    db.add(stock_movement)
    db.commit()
    db.refresh(stock_movement)
    
    return stock_movement


@router.get("/batches", response_model=List[BatchResponse])
async def get_batches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    product_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get product batches with optional filters
    """
    query = db.query(ProductBatch)
    
    if product_id:
        query = query.filter(ProductBatch.product_id == product_id)
    
    if status:
        query = query.filter(ProductBatch.status == status)
    
    batches = query.order_by(ProductBatch.expiry_date.asc()).offset(skip).limit(limit).all()
    return batches


@router.post("/batches", response_model=BatchResponse)
async def create_batch(
    batch_data: BatchCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new product batch (Manager/Admin only)
    """
    # Check if batch number exists
    if db.query(ProductBatch).filter(ProductBatch.batch_number == batch_data.batch_number).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch number already exists"
        )
    
    # Verify product exists
    product = db.query(Product).filter(Product.id == batch_data.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Determine batch status based on expiry date
    batch_status = BatchStatus.NORMAL
    if batch_data.expiry_date:
        if batch_data.expiry_date < datetime.utcnow():
            batch_status = BatchStatus.EXPIRED
        elif batch_data.expiry_date < datetime.utcnow() + timedelta(days=7):
            batch_status = BatchStatus.EXPIRING_SOON
    
    new_batch = ProductBatch(
        **batch_data.model_dump(),
        remaining_quantity=batch_data.quantity,
        status=batch_status
    )
    
    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)
    
    return new_batch


@router.get("/summary")
async def get_inventory_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get inventory summary statistics
    """
    total_products = db.query(Product).filter(Product.is_active == True).count()
    total_stock_value = db.query(
        func.sum(Product.current_stock * Product.purchase_price)
    ).scalar() or 0
    
    low_stock_count = db.query(Product).filter(
        and_(
            Product.is_active == True,
            Product.current_stock <= Product.reorder_level
        )
    ).count()
    
    # Count expiring products (within 7 days)
    warning_date = datetime.utcnow() + timedelta(days=7)
    expiring_count = db.query(ProductBatch).filter(
        and_(
            ProductBatch.expiry_date <= warning_date,
            ProductBatch.expiry_date > datetime.utcnow(),
            ProductBatch.remaining_quantity > 0
        )
    ).count()
    
    # Count expired products
    expired_count = db.query(ProductBatch).filter(
        and_(
            ProductBatch.expiry_date < datetime.utcnow(),
            ProductBatch.remaining_quantity > 0
        )
    ).count()
    
    return {
        "total_products": total_products,
        "total_stock_value": total_stock_value,
        "low_stock_products": low_stock_count,
        "expiring_products": expiring_count,
        "expired_products": expired_count
    }
