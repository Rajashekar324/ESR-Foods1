"""
Sales Orders router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timezone
from io import BytesIO
import re
from uuid import uuid4
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from backend.database import get_db
from backend.models.order import SalesOrder, SalesOrderItem, OrderStatus, CustomerType
from backend.models.restaurant import Restaurant
from backend.models.customer import RetailCustomer
from backend.models.product import Product
from backend.models.stock_movement import StockMovement, MovementType
from backend.models.user import User
from backend.models.invoice import Invoice, InvoiceItem
from backend.models.payment import Payment, PaymentStatus, PaymentType
from backend.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderItemCreate
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
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        order_code = f"SO-{timestamp}-{uuid4().hex[:6].upper()}"
    elif db.query(SalesOrder).filter(SalesOrder.order_code == order_code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order code already exists"
        )
    
    # Verify customer exists
    if order_data.customer_type == CustomerType.RESTAURANT:
        if not order_data.restaurant_id or order_data.customer_id is not None:
            raise HTTPException(status_code=400, detail="Choose exactly one restaurant for a restaurant order")
        customer = db.query(Restaurant).filter(Restaurant.id == order_data.restaurant_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
    else:
        if not order_data.customer_id or order_data.restaurant_id is not None:
            raise HTTPException(status_code=400, detail="Choose exactly one retail customer for a retail order")
        customer = db.query(RetailCustomer).filter(RetailCustomer.id == order_data.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
    
    # Calculate totals
    subtotal = 0
    item_discounts = 0
    item_taxes = 0
    for item_data in order_data.items:
        if item_data.discount > item_data.quantity * item_data.selling_price:
            raise HTTPException(status_code=400, detail="An order line discount cannot exceed its line subtotal")
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with ID {item_data.product_id} not found"
            )
        
        subtotal += item_data.quantity * item_data.selling_price
        item_discounts += item_data.discount
        item_taxes += item_data.tax
    
    discount = order_data.discount
    tax = order_data.tax
    if item_discounts + discount > subtotal:
        raise HTTPException(status_code=400, detail="Total discounts cannot exceed the order subtotal")
    total = subtotal - item_discounts - discount + item_taxes + tax
    if total <= 0:
        raise HTTPException(status_code=400, detail="Order total must be greater than zero")
    
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


@router.get("/{order_id}/bill.pdf")
async def download_order_bill(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download a printable PDF bill for a sales order."""
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.customer_type == CustomerType.RESTAURANT:
        customer = db.query(Restaurant).filter(Restaurant.id == order.restaurant_id).first()
    else:
        customer = db.query(RetailCustomer).filter(RetailCustomer.id == order.customer_id).first()
    customer_name = escape(customer.name if customer else "Customer")

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Bill {order.order_code}",
        author="ESR Foods"
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BillTitle", parent=styles["Title"], textColor=colors.HexColor("#17324d"),
        alignment=TA_RIGHT, fontSize=20, leading=24
    )
    body_style = styles["BodyText"]
    story = [
        Table(
            [[Paragraph("ESR FOODS", ParagraphStyle("Brand", parent=styles["Heading1"], textColor=colors.HexColor("#167a72"))),
              Paragraph("SALES BILL", title_style)]],
            colWidths=[3.5 * inch, 3.5 * inch]
        ),
        Spacer(1, 12),
        Table([
            [Paragraph(f"<b>Order:</b> {escape(order.order_code)}", body_style),
             Paragraph(f"<b>Date:</b> {order.order_date.strftime('%d %b %Y')}", body_style)],
            [Paragraph(f"<b>Bill to:</b> {customer_name}", body_style),
             Paragraph(f"<b>Customer type:</b> {order.customer_type.value.title()}", body_style)],
            [Paragraph(f"<b>Order status:</b> {order.order_status.value.title()}", body_style),
             Paragraph(f"<b>Payment status:</b> {escape(order.payment_status or 'unpaid').title()}", body_style)]
        ], colWidths=[3.5 * inch, 3.5 * inch]),
        Spacer(1, 18)
    ]

    item_rows = [["Item", "Qty", "Unit", "Rate (Rs.)", "Tax (Rs.)", "Amount (Rs.)"]]
    for item in order.items:
        product_name = item.product.name if item.product else f"Product #{item.product_id}"
        item_rows.append([
            Paragraph(escape(product_name), body_style),
            f"{item.quantity:g}",
            escape(item.unit),
            f"{item.selling_price:,.2f}",
            f"{item.tax:,.2f}",
            f"{item.total:,.2f}"
        ])
    items_table = Table(item_rows, colWidths=[2.55 * inch, 0.55 * inch, 0.55 * inch, 1.05 * inch, 0.9 * inch, 1.1 * inch], repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e1e8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fa")]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8)
    ]))
    story.append(items_table)
    story.append(Spacer(1, 14))

    totals_table = Table([
        ["Subtotal", f"Rs. {order.subtotal:,.2f}"],
        ["Discount", f"- Rs. {order.discount:,.2f}"],
        ["Tax", f"Rs. {order.tax:,.2f}"],
        [Paragraph("<b>Total due</b>", body_style), Paragraph(f"<b>Rs. {order.total:,.2f}</b>", body_style)]
    ], colWidths=[1.8 * inch, 1.5 * inch], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#17324d")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6)
    ]))
    story.append(totals_table)
    if order.notes:
        story.extend([Spacer(1, 18), Paragraph(f"<b>Notes:</b> {escape(order.notes)}", body_style)])
    story.extend([Spacer(1, 26), Paragraph("Thank you for your business.", styles["Italic"])])
    document.build(story)

    safe_order_code = re.sub(r"[^A-Za-z0-9_-]", "_", order.order_code)
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="bill-{safe_order_code}.pdf"'}
    )


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
    items_data = update_data.pop("items", None)
    if items_data is not None:
        items_data = [OrderItemCreate(**item) if isinstance(item, dict) else item for item in items_data]
    if items_data is None and ("discount" in update_data or "tax" in update_data):
        items_data = [OrderItemCreate(
            id=item.id, product_id=item.product_id, quantity=item.quantity, unit=item.unit,
            selling_price=item.selling_price, discount=item.discount or 0, tax=item.tax or 0,
        ) for item in order.items]
    if items_data is not None and order.order_status in {OrderStatus.DELIVERED, OrderStatus.CANCELLED}:
        incoming = {item.id: item for item in items_data}
        current = {item.id: item for item in order.items}
        changed = set(incoming) != set(current) or any(
            (item.product_id, item.quantity, item.unit, item.selling_price, item.discount, item.tax)
            != (current[item_id].product_id, current[item_id].quantity, current[item_id].unit,
                current[item_id].selling_price, current[item_id].discount, current[item_id].tax)
            for item_id, item in incoming.items() if item_id in current
        )
        if changed:
            raise HTTPException(status_code=400, detail="Delivered or cancelled order items cannot be edited")

    if items_data is not None:
        subtotal = item_discounts = item_taxes = 0.0
        existing_items = {item.id: item for item in order.items}
        retained_ids = set()
        for item_data in items_data:
            if item_data.discount > item_data.quantity * item_data.selling_price:
                raise HTTPException(status_code=400, detail="An order line discount cannot exceed its line subtotal")
            if not db.query(Product).filter(Product.id == item_data.product_id).first():
                raise HTTPException(status_code=400, detail=f"Product with ID {item_data.product_id} not found")
            line_total = round(item_data.quantity * item_data.selling_price - item_data.discount + item_data.tax, 2)
            subtotal += item_data.quantity * item_data.selling_price
            item_discounts += item_data.discount
            item_taxes += item_data.tax
            if item_data.id is not None:
                item = existing_items.get(item_data.id)
                if not item:
                    raise HTTPException(status_code=400, detail="An order item does not belong to this order")
                retained_ids.add(item.id)
            else:
                item = SalesOrderItem(order_id=order.id)
                db.add(item)
            item.product_id = item_data.product_id
            item.quantity = item_data.quantity
            item.unit = item_data.unit
            item.selling_price = item_data.selling_price
            item.discount = item_data.discount
            item.tax = item_data.tax
            item.total = line_total
        for item_id, item in existing_items.items():
            if item_id not in retained_ids:
                db.delete(item)
        discount = update_data.get("discount", order.discount or 0)
        tax = update_data.get("tax", order.tax or 0)
        if item_discounts + discount > subtotal:
            raise HTTPException(status_code=400, detail="Total discounts cannot exceed the order subtotal")
        total = round(subtotal - item_discounts - discount + item_taxes + tax, 2)
        if total <= 0:
            raise HTTPException(status_code=400, detail="Order total must be greater than zero")
        order.subtotal, order.total = subtotal, total
        order.discount, order.tax = discount, tax
        linked_invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
        if linked_invoice:
            linked_invoice.subtotal = subtotal
            linked_invoice.discount = discount + item_discounts
            linked_invoice.tax = tax + item_taxes
            linked_invoice.grand_total = total
            linked_invoice.due_date = update_data.get("delivery_date", order.delivery_date) or update_data.get("order_date", order.order_date)
            for invoice_item in list(linked_invoice.items):
                db.delete(invoice_item)
            db.flush()
            from backend.models.invoice import InvoiceItem
            for item_data in items_data:
                db.add(InvoiceItem(
                    invoice_id=linked_invoice.id, product_id=item_data.product_id,
                    quantity=item_data.quantity, unit=item_data.unit, rate=item_data.selling_price,
                    discount=item_data.discount, tax=item_data.tax,
                    amount=round(item_data.quantity * item_data.selling_price - item_data.discount + item_data.tax, 2),
                ))
            paid = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
                Payment.invoice_id == linked_invoice.id,
                Payment.payment_type == PaymentType.RECEIPT,
                Payment.status == PaymentStatus.COMPLETED,
            ).scalar() or 0
            linked_invoice.amount_paid = paid
            linked_invoice.balance_due = max(0, total - paid)
            linked_invoice.payment_status = "unpaid" if paid <= 0 else "partially_paid" if paid < total else "paid"
            order.payment_status = linked_invoice.payment_status

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
    linked_invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
    if linked_invoice:
        # Keep completed receipts in the restaurant ledger; they become unallocated
        # restaurant-level receipts when their linked invoice is deleted.
        db.query(Payment).filter(Payment.invoice_id == linked_invoice.id).update(
            {Payment.invoice_id: None}, synchronize_session=False
        )
        db.delete(linked_invoice)
        
    db.delete(order)
    db.commit()
    
    return {"message": "Order deleted successfully"}
