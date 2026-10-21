"""
Reports router
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import List, Optional
from datetime import datetime, timedelta
from backend.database import get_db
from backend.models.invoice import Invoice
from backend.models.purchase import Purchase
from backend.models.product import Product
from backend.models.restaurant import Restaurant
from backend.models.order import SalesOrder
from backend.models.payment import Payment, PaymentType
from backend.models.expense import Expense
from backend.models.user import User
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/reports", tags=["Reports"], dependencies=[Depends(require_manager_or_admin())])


@router.get("/sales")
async def get_sales_report(
    start_date: datetime,
    end_date: datetime,
    restaurant_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get sales report for date range
    """
    query = db.query(Invoice).filter(
        and_(
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
            Invoice.is_finalized == True
        )
    )
    
    if restaurant_id:
        query = query.filter(Invoice.restaurant_id == restaurant_id)
    
    invoices = query.all()
    
    total_sales = sum(inv.grand_total for inv in invoices)
    total_collected = sum(inv.amount_paid for inv in invoices)
    outstanding = total_sales - total_collected
    
    return {
        "period_start": start_date,
        "period_end": end_date,
        "total_sales": total_sales,
        "total_collected": total_collected,
        "outstanding": outstanding,
        "invoice_count": len(invoices),
        "invoices": [
            {
                "invoice_number": inv.invoice_number,
                "restaurant_id": inv.restaurant_id,
                "invoice_date": inv.invoice_date,
                "grand_total": inv.grand_total,
                "amount_paid": inv.amount_paid,
                "balance_due": inv.balance_due,
                "payment_status": inv.payment_status
            }
            for inv in invoices
        ]
    }


@router.get("/purchases")
async def get_purchases_report(
    start_date: datetime,
    end_date: datetime,
    vendor_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get purchases report for date range
    """
    query = db.query(Purchase).filter(
        and_(
            Purchase.purchase_date >= start_date,
            Purchase.purchase_date <= end_date
        )
    )
    
    if vendor_id:
        query = query.filter(Purchase.vendor_id == vendor_id)
    
    purchases = query.all()
    
    total_purchases = sum(pur.total for pur in purchases)
    
    return {
        "period_start": start_date,
        "period_end": end_date,
        "total_purchases": total_purchases,
        "purchase_count": len(purchases),
        "purchases": [
            {
                "purchase_code": pur.purchase_code,
                "vendor_id": pur.vendor_id,
                "purchase_date": pur.purchase_date,
                "total": pur.total,
                "status": pur.status
            }
            for pur in purchases
        ]
    }


@router.get("/inventory")
async def get_inventory_report(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current inventory report
    """
    products = db.query(Product).filter(Product.is_active == True).all()
    
    total_stock_value = sum(prod.current_stock * prod.purchase_price for prod in products)
    low_stock_products = [prod for prod in products if prod.current_stock <= prod.reorder_level]
    
    return {
        "total_products": len(products),
        "total_stock_value": total_stock_value,
        "low_stock_count": len(low_stock_products),
        "products": [
            {
                "product_code": prod.product_code,
                "name": prod.name,
                "current_stock": prod.current_stock,
                "unit": prod.unit,
                "purchase_price": prod.purchase_price,
                "selling_price": prod.selling_price,
                "stock_value": prod.current_stock * prod.purchase_price,
                "is_low_stock": prod.current_stock <= prod.reorder_level
            }
            for prod in products
        ]
    }


@router.get("/restaurants")
async def get_restaurants_report(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get restaurants report
    """
    restaurants = db.query(Restaurant).filter(Restaurant.status == True).all()
    
    report_data = []
    for restaurant in restaurants:
        # Calculate totals
        total_sales = db.query(func.sum(Invoice.grand_total)).filter(
            and_(
                Invoice.restaurant_id == restaurant.id,
                Invoice.is_finalized == True
            )
        ).scalar() or 0
        
        total_payments = db.query(func.sum(Payment.amount)).filter(
            and_(
                Payment.restaurant_id == restaurant.id,
                Payment.payment_type == PaymentType.RECEIPT,
                Payment.status == "completed"
            )
        ).scalar() or 0
        
        outstanding = max(0.0, total_sales - total_payments)
        
        order_count = db.query(SalesOrder).filter(
            SalesOrder.restaurant_id == restaurant.id
        ).count()
        
        report_data.append({
            "restaurant_id": restaurant.id,
            "restaurant_name": restaurant.name,
            "area": restaurant.area,
            "credit_limit": restaurant.credit_limit,
            "total_sales": total_sales,
            "total_payments": total_payments,
            "outstanding": outstanding,
            "order_count": order_count,
            "credit_usage_percent": (outstanding / restaurant.credit_limit * 100) if restaurant.credit_limit > 0 else 0
        })
    
    # Sort by total sales
    report_data.sort(key=lambda x: x["total_sales"], reverse=True)
    
    return {
        "total_restaurants": len(restaurants),
        "restaurants": report_data
    }


@router.get("/restaurants/15-day-summary")
async def get_15_day_summary(
    start_date: datetime,
    end_date: datetime,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get 15-day restaurant summary report
    """
    restaurants = db.query(Restaurant).filter(Restaurant.status == True).all()
    
    report_data = []
    total_sales = 0
    total_collected = 0
    total_outstanding = 0
    
    for restaurant in restaurants:
        # Get sales in period
        period_sales = db.query(func.sum(Invoice.grand_total)).filter(
            and_(
                Invoice.restaurant_id == restaurant.id,
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date,
                Invoice.is_finalized == True
            )
        ).scalar() or 0
        
        # Get payments in period
        period_payments = db.query(func.sum(Payment.amount)).filter(
            and_(
                Payment.restaurant_id == restaurant.id,
                Payment.date >= start_date,
                Payment.date <= end_date,
                Payment.payment_type == PaymentType.RECEIPT,
                Payment.status == "completed"
            )
        ).scalar() or 0
        
        # Calculate opening balance (before period)
        opening_balance = db.query(func.sum(Invoice.grand_total)).filter(
            and_(
                Invoice.restaurant_id == restaurant.id,
                Invoice.invoice_date < start_date,
                Invoice.is_finalized == True
            )
        ).scalar() or 0
        
        opening_payments = db.query(func.sum(Payment.amount)).filter(
            and_(
                Payment.restaurant_id == restaurant.id,
                Payment.date < start_date,
                Payment.payment_type == PaymentType.RECEIPT,
                Payment.status == "completed"
            )
        ).scalar() or 0
        
        opening_balance = max(0.0, opening_balance - opening_payments)
        
        # Calculate closing balance
        closing_balance = max(0.0, opening_balance + period_sales - period_payments)
        outstanding = closing_balance
        
        # Order count in period
        order_count = db.query(SalesOrder).filter(
            and_(
                SalesOrder.restaurant_id == restaurant.id,
                SalesOrder.order_date >= start_date,
                SalesOrder.order_date <= end_date
            )
        ).count()
        
        total_sales += period_sales
        total_collected += period_payments
        total_outstanding += outstanding
        
        report_data.append({
            "restaurant_id": restaurant.id,
            "restaurant_name": restaurant.name,
            "area": restaurant.area,
            "orders": order_count,
            "sales": period_sales,
            "collected": period_payments,
            "outstanding": outstanding
        })
    
    # Sort by sales
    report_data.sort(key=lambda x: x["sales"], reverse=True)
    
    collection_rate = (total_collected / total_sales * 100) if total_sales > 0 else 0
    
    return {
        "period_start": start_date,
        "period_end": end_date,
        "total_sales": total_sales,
        "total_collected": total_collected,
        "total_outstanding": total_outstanding,
        "collection_rate": collection_rate,
        "restaurants": report_data
    }


@router.get("/profit")
async def get_profit_report(
    start_date: datetime,
    end_date: datetime,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get profit report for date range
    """
    # Total revenue
    total_revenue = db.query(func.sum(Invoice.grand_total)).filter(
        and_(
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
            Invoice.is_finalized == True
        )
    ).scalar() or 0
    
    # Total purchases (COGS)
    total_purchases = db.query(func.sum(Purchase.total)).filter(
        and_(
            Purchase.purchase_date >= start_date,
            Purchase.purchase_date <= end_date,
            Purchase.status == "received"
        )
    ).scalar() or 0
    
    # Total expenses
    total_expenses = db.query(func.sum(Expense.amount)).filter(
        and_(
            Expense.date >= start_date,
            Expense.date <= end_date
        )
    ).scalar() or 0
    
    # Calculate profit
    gross_profit = total_revenue - total_purchases
    net_profit = gross_profit - total_expenses
    
    gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return {
        "period_start": start_date,
        "period_end": end_date,
        "total_revenue": total_revenue,
        "total_purchases": total_purchases,
        "total_expenses": total_expenses,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "gross_margin": gross_margin
    }
