"""
Sales Orders router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime
from backend.database import get_db
from backend.models.order import SalesOrder, SalesOrderItem, OrderStatus, CustomerType
from backend.models.restaurant import Restaurant
from backend.models.customer import RetailCustomer
from backend.models.product import Product
from backend.models.stock_movement import StockMovement, MovementType
from backend.models.user import User
from backend.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderItemCreate, OrderItemResponse
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/orders", tags=["Orders"], dependencies=[Depends(require_manager_or_admin())])


@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new sales order
    """
    order_code = order_data.order_code
    if not order_code:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        order_code = f"SO-{timestamp}"
    elif db.query(SalesOrder).filter(SalesOrder.order_code == order_code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order code already exists"
        )
    
    # Verify customer exists
    if order_data.customer_type == CustomerType.RESTAURANT:
        customer = db.query(Restaurant).filter(Restaurant.id == order_data.restaurant_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
    else:
        customer = db.query(RetailCustomer).filter(RetailCustomer.id == order_data.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
    
    # Calculate totals
    subtotal = 0
    for item_data in order_data.items:
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with ID {item_data.product_id} not found"
            )
        
        subtotal += item_data.quantity * item_data.selling_price
    
    discount = order_data.discount
    tax = order_data.tax
    total = subtotal - discount + tax
    
    # Create order
    new_order = SalesOrder(
        order_code=order_code,
        customer_type=order_data.customer_type,
        restaurant_id=order_data.restaurant_id,
        customer_id=order_data.customer_id,
        order_date=order_data.order_date,
        delivery_date=order_data.delivery_date,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total=total,
        notes=order_data.notes,
        order_status=OrderStatus.CONFIRMED
    )
    
    db.add(new_order)
    db.flush()
    
    # Create order items
    for item_data in order_data.items:
        item_total = item_data.quantity * item_data.selling_price - item_data.discount + item_data.tax
        order_item = SalesOrderItem(
            order_id=new_order.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit=item_data.unit,
            selling_price=item_data.selling_price,
            discount=item_data.discount,
            tax=item_data.tax,
            total=item_total
        )
        db.add(order_item)

    # Automatically generate Invoice for restaurant order so it appears in restaurant records
    if order_data.customer_type == CustomerType.RESTAURANT and order_data.restaurant_id:
        from backend.models.invoice import Invoice, InvoiceItem
        inv_num = f"INV-{order_code}"
        if not db.query(Invoice).filter(Invoice.invoice_number == inv_num).first():
            new_invoice = Invoice(
                invoice_number=inv_num,
                order_id=new_order.id,
                restaurant_id=new_order.restaurant_id,
                invoice_date=new_order.order_date,
                due_date=new_order.delivery_date or new_order.order_date,
                subtotal=subtotal,
                discount=discount,
                tax=tax,
                grand_total=total,
                amount_paid=0,
                balance_due=total,
                payment_status="unpaid",
                notes=f"Auto-generated invoice for order {order_code}",
                is_finalized=True
            )
            db.add(new_invoice)
            db.flush()
            for item_data in order_data.items:
                item_total = item_data.quantity * item_data.selling_price - item_data.discount + item_data.tax
                inv_item = InvoiceItem(
                    invoice_id=new_invoice.id,
                    product_id=item_data.product_id,
                    quantity=item_data.quantity,
                    unit=item_data.unit,
                    rate=item_data.selling_price,
                    discount=item_data.discount,
                    tax=item_data.tax,
                    amount=item_total
                )
                db.add(inv_item)
    
    db.commit()
    db.refresh(new_order)
    
    return new_order


@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    customer_type: Optional[str] = None,
    restaurant_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    order_status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all orders with optional filters
    """
    query = db.query(SalesOrder)
    
    if customer_type:
        query = query.filter(SalesOrder.customer_type == customer_type)
    
    if restaurant_id:
        query = query.filter(SalesOrder.restaurant_id == restaurant_id)
    
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)
    
    if order_status:
        query = query.filter(SalesOrder.order_status == order_status)
    
    orders = query.order_by(SalesOrder.order_date.desc()).offset(skip).limit(limit).all()
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific order by ID
    """
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Update an order (Manager/Admin only)
    """
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    update_data = order_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    order.updated_at = func.now()
    db.commit()
    db.refresh(order)
    
    return order


@router.post("/{order_id}/complete")
async def complete_order(
    order_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Complete an order and deduct stock (Manager/Admin only)
    """
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.order_status == OrderStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order already completed"
        )
    
    # Update order status
    order.order_status = OrderStatus.DELIVERED
    order.delivery_status = "delivered"
    
    # Deduct stock for each item
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            if product.current_stock < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for product {product.name}"
                )
            
            product.current_stock -= item.quantity
            
            # Create stock movement
            stock_movement = StockMovement(
                product_id=item.product_id,
                movement_type=MovementType.RESTAURANT_SALE if order.customer_type == CustomerType.RESTAURANT else MovementType.RETAIL_SALE,
                reference_id=order.id,
                reference_type="order",
                quantity=item.quantity,
                unit=item.unit,
                rate=item.selling_price,
                total=item.total,
                balance_after=product.current_stock,
                notes=f"Sale from order {order.order_code}"
            )
            db.add(stock_movement)
    
    db.commit()
    
    return {"message": "Order completed successfully, stock deducted"}


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Cancel an order and restore stock if already deducted (Manager/Admin only)
    """
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.order_status == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order already cancelled"
        )
    
    # If order was delivered, restore stock
    if order.order_status == OrderStatus.DELIVERED:
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.current_stock += item.quantity
                
                # Create stock movement for restoration
                stock_movement = StockMovement(
                    product_id=item.product_id,
                    movement_type=MovementType.STOCK_ADJUSTMENT_IN,
                    reference_id=order.id,
                    reference_type="order_cancellation",
                    quantity=item.quantity,
                    unit=item.unit,
                    rate=item.selling_price,
                    total=item.total,
                    balance_after=product.current_stock,
                    notes=f"Stock restored from cancelled order {order.order_code}"
                )
                db.add(stock_movement)
    
    # Update order status
    order.order_status = OrderStatus.CANCELLED
    order.delivery_status = "cancelled"
    
    db.commit()
    
    return {"message": "Order cancelled successfully"}


@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Delete an order and its linked invoice (Manager/Admin only)
    """
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Delete linked invoice if any
    from backend.models.invoice import Invoice
    linked_invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
    if linked_invoice:
        db.delete(linked_invoice)
        
    db.delete(order)
    db.commit()
    
    return {"message": "Order deleted successfully"}
