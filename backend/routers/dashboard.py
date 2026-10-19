"""
Dashboard router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, timedelta
from backend.database import get_db
from backend.models.invoice import Invoice, InvoiceItem
from backend.models.purchase import Purchase
from backend.models.product import Product, Category
from backend.models.restaurant import Restaurant
from backend.models.payment import Payment, PaymentType, PaymentStatus
from backend.models.vendor import Vendor
from backend.models.batch import ProductBatch
from backend.models.user import User
from backend.schemas.dashboard import DashboardSummary, DashboardCharts, FifteenDaySummary
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"], dependencies=[Depends(require_manager_or_admin())])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard summary statistics
    """
    today = datetime.utcnow().date()
    month_start = datetime.utcnow().replace(day=1).date()
    
    # Today's sales
    today_sales = db.query(func.sum(Invoice.grand_total)).filter(
        and_(
            Invoice.invoice_date == today,
            Invoice.is_finalized == True
        )
    ).scalar() or 0
    
    # Today's purchases
    today_purchases = db.query(func.sum(Purchase.total)).filter(
        Purchase.purchase_date == today
    ).scalar() or 0
    
    # Monthly sales
    monthly_sales = db.query(func.sum(Invoice.grand_total)).filter(
        and_(
            Invoice.invoice_date >= month_start,
            Invoice.is_finalized == True
        )
    ).scalar() or 0
    
    # Outstanding receivables
    outstanding_receivables = db.query(func.sum(Invoice.grand_total) - func.sum(Invoice.amount_paid)).filter(
        Invoice.is_finalized == True
    ).scalar() or 0

    total_purchases = db.query(func.sum(Purchase.total)).scalar() or 0
    total_vendor_payments = db.query(func.sum(Payment.amount)).filter(
        Payment.payment_type == PaymentType.PAYMENT,
        Payment.vendor_id.isnot(None),
        Payment.status == PaymentStatus.COMPLETED
    ).scalar() or 0
    total_vendor_adjustments = db.query(func.sum(Vendor.credit_adjustments)).scalar() or 0
    outstanding_vendor_payables = max(0, total_purchases - total_vendor_payments - total_vendor_adjustments)
    
    # Total stock value
    total_stock_value = db.query(func.sum(Product.current_stock * Product.purchase_price)).scalar() or 0
    
    # Active restaurants
    active_restaurants = db.query(Restaurant).filter(Restaurant.is_active == True).count()
    
    # Low stock products
    low_stock_products = db.query(Product).filter(
        Product.current_stock <= Product.minimum_stock
    ).count()
    
    # Expiring products (within 7 days)
    seven_days_from_now = datetime.utcnow() + timedelta(days=7)
    expiring_products = db.query(ProductBatch).filter(
        and_(
            ProductBatch.expiry_date <= seven_days_from_now,
            ProductBatch.expiry_date >= datetime.utcnow(),
            ProductBatch.quantity > 0
        )
    ).count()
    
    return DashboardSummary(
        today_sales=today_sales,
        today_purchases=today_purchases,
        monthly_sales=monthly_sales,
        outstanding_receivables=outstanding_receivables,
        outstanding_vendor_payables=outstanding_vendor_payables,
        total_stock_value=total_stock_value,
        active_restaurants=active_restaurants,
        low_stock_products=low_stock_products,
        expiring_products=expiring_products
    )


@router.get("/charts", response_model=DashboardCharts)
async def get_dashboard_charts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard chart data
    """
    # Sales trend (last 6 months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    sales_trend = db.query(
        func.strftime('%Y-%m', Invoice.invoice_date).label('month'),
        func.sum(Invoice.grand_total).label('sales')
    ).filter(
        and_(
            Invoice.invoice_date >= six_months_ago,
            Invoice.is_finalized == True
        )
    ).group_by(
        func.strftime('%Y-%m', Invoice.invoice_date)
    ).order_by(
        func.strftime('%Y-%m', Invoice.invoice_date)
    ).all()
    
    sales_trend_data = [{'month': row.month, 'sales': row.sales or 0} for row in sales_trend]
    
    # Top products (by sales amount)
    top_products = db.query(
        Product.name,
        func.sum(InvoiceItem.quantity * InvoiceItem.rate).label('amount')
    ).join(
        InvoiceItem, Product.id == InvoiceItem.product_id
    ).join(
        Invoice, InvoiceItem.invoice_id == Invoice.id
    ).filter(
        Invoice.is_finalized == True
    ).group_by(
        Product.id, Product.name
    ).order_by(
        desc('amount')
    ).limit(10).all()
    
    top_products_data = [{'name': row.name, 'amount': row.amount or 0} for row in top_products]
    
    # Top restaurants (by sales)
    top_restaurants = db.query(
        Restaurant.name,
        func.sum(Invoice.grand_total).label('sales')
    ).join(
        Invoice, Restaurant.id == Invoice.restaurant_id
    ).filter(
        Invoice.is_finalized == True
    ).group_by(
        Restaurant.id, Restaurant.name
    ).order_by(
        desc('sales')
    ).limit(10).all()
    
    top_restaurants_data = [{'name': row.name, 'sales': row.sales or 0} for row in top_restaurants]
    
    # Inventory distribution by category
    inventory_distribution = db.query(
        Product.category_id,
        func.sum(Product.current_stock * Product.purchase_price).label('value')
    ).group_by(
        Product.category_id
    ).all()

    category_names = {
        category.id: category.name
        for category in db.query(Category).filter(Category.id.in_([row.category_id for row in inventory_distribution if row.category_id is not None])).all()
    }
    inventory_distribution_data = [
        {'category': category_names.get(row.category_id, 'Uncategorized'), 'value': row.value or 0}
        for row in inventory_distribution
    ]
    
    return DashboardCharts(
        sales_trend=sales_trend_data,
        top_products=top_products_data,
        top_restaurants=top_restaurants_data,
        inventory_distribution=inventory_distribution_data
    )


@router.get("/15-day-summary", response_model=FifteenDaySummary)
async def get_15_day_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current 15-day billing period summary
    """
    # Calculate current 15-day period
    today = datetime.utcnow().date()
    day_of_month = today.day
    
    if day_of_month <= 15:
        period_start = today.replace(day=1)
        period_end = today.replace(day=15)
    else:
        period_start = today.replace(day=16)
        period_end = today.replace(day=1) + timedelta(days=32)  # Go to next month and adjust
        period_end = period_end.replace(day=15)
    
    # Get all invoices in this period
    invoices = db.query(Invoice).filter(
        and_(
            Invoice.invoice_date >= period_start,
            Invoice.invoice_date <= period_end,
            Invoice.is_finalized == True
        )
    ).all()
    
    total_sales = sum(inv.grand_total for inv in invoices)
    total_collected = sum(inv.amount_paid for inv in invoices)
    total_outstanding = total_sales - total_collected
    collection_rate = (total_collected / total_sales * 100) if total_sales > 0 else 0
    
    # Restaurant breakdown
    restaurant_breakdown = []
    restaurants = db.query(Restaurant).all()
    
    for restaurant in restaurants:
        restaurant_invoices = [inv for inv in invoices if inv.restaurant_id == restaurant.id]
        if restaurant_invoices:
            restaurant_sales = sum(inv.grand_total for inv in restaurant_invoices)
            restaurant_collected = sum(inv.amount_paid for inv in restaurant_invoices)
            restaurant_outstanding = restaurant_sales - restaurant_collected
            
            restaurant_breakdown.append({
                'restaurant_name': restaurant.name,
                'orders': len(restaurant_invoices),
                'sales': restaurant_sales,
                'collected': restaurant_collected,
                'outstanding': restaurant_outstanding
            })
    
    return FifteenDaySummary(
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        total_sales=total_sales,
        total_collected=total_collected,
        total_outstanding=total_outstanding,
        collection_rate=collection_rate,
        restaurant_breakdown=restaurant_breakdown
    )
