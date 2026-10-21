"""
Restaurants router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta
from backend.database import get_db
from backend.models.restaurant import Restaurant, RestaurantNote
from backend.models.invoice import Invoice
from backend.models.payment import Payment, PaymentType
from backend.models.order import SalesOrder
from backend.models.user import User
from backend.schemas.restaurant import RestaurantCreate, RestaurantUpdate, RestaurantResponse, RestaurantNoteCreate, RestaurantNoteResponse
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/restaurants", tags=["Restaurants"], dependencies=[Depends(require_manager_or_admin())])


@router.post("/", response_model=RestaurantResponse)
async def create_restaurant(
    restaurant_data: RestaurantCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new restaurant (Manager/Admin only)
    """
    if db.query(Restaurant).filter(Restaurant.restaurant_code == restaurant_data.restaurant_code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restaurant code already exists"
        )
    
    new_restaurant = Restaurant(**restaurant_data.model_dump())
    db.add(new_restaurant)
    db.commit()
    db.refresh(new_restaurant)
    
    return new_restaurant


@router.get("/", response_model=List[RestaurantResponse])
async def get_restaurants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    area: Optional[str] = None,
    restaurant_type: Optional[str] = None,
    status: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all restaurants with optional filters
    """
    query = db.query(Restaurant)
    
    if search:
        query = query.filter(
            (Restaurant.name.ilike(f"%{search}%")) |
            (Restaurant.restaurant_code.ilike(f"%{search}%")) |
            (Restaurant.area.ilike(f"%{search}%"))
        )
    
    if area:
        query = query.filter(Restaurant.area.ilike(f"%{area}%"))
    
    if restaurant_type:
        query = query.filter(Restaurant.restaurant_type == restaurant_type)
    
    if status is not None:
        query = query.filter(Restaurant.status == status)
    
    restaurants = query.order_by(Restaurant.name).offset(skip).limit(limit).all()
    return restaurants


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant(
    restaurant_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific restaurant by ID
    """
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    return restaurant


def parse_dates(start_date: str, end_date: str):
    try:
        start_dt = datetime.fromisoformat(start_date) if "T" in start_date else datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.fromisoformat(end_date) if "T" in end_date else datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        return start_dt, end_dt
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD")


@router.put("/{restaurant_id}", response_model=RestaurantResponse)
async def update_restaurant(
    restaurant_id: int,
    restaurant_data: RestaurantUpdate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Update a restaurant (Manager/Admin only)
    """
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    
    update_data = restaurant_data.model_dump(exclude_unset=True)
    
    if "restaurant_code" in update_data and update_data["restaurant_code"] != restaurant.restaurant_code:
        existing = db.query(Restaurant).filter(
            and_(Restaurant.restaurant_code == update_data["restaurant_code"], Restaurant.id != restaurant_id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Restaurant code already exists"
            )

    for field, value in update_data.items():
        setattr(restaurant, field, value)
    
    restaurant.updated_at = func.now()
    db.commit()
    db.refresh(restaurant)
    
    return restaurant


@router.delete("/{restaurant_id}")
async def delete_restaurant(
    restaurant_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Delete a restaurant and its related records (Manager/Admin only)
    """
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    
    # Clean up associated records to prevent foreign key errors
    db.query(RestaurantNote).filter(RestaurantNote.restaurant_id == restaurant_id).delete(synchronize_session=False)
    db.query(Payment).filter(Payment.restaurant_id == restaurant_id).delete(synchronize_session=False)
    
    # Delete invoices and sales orders for this restaurant
    invoices = db.query(Invoice).filter(Invoice.restaurant_id == restaurant_id).all()
    for inv in invoices:
        db.delete(inv)
    
    orders = db.query(SalesOrder).filter(SalesOrder.restaurant_id == restaurant_id).all()
    for ord_obj in orders:
        db.delete(ord_obj)

    db.delete(restaurant)
    db.commit()
    
    return {"message": "Restaurant deleted successfully"}


@router.get("/{restaurant_id}/orders")
async def get_restaurant_orders(
    restaurant_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all orders for a specific restaurant
    """
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    
    orders = db.query(SalesOrder).filter(
        SalesOrder.restaurant_id == restaurant_id
    ).order_by(SalesOrder.order_date.desc()).offset(skip).limit(limit).all()
    
    return orders


@router.get("/{restaurant_id}/invoices")
async def get_restaurant_invoices(
    restaurant_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all invoices for a specific restaurant
    """
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    
    invoices = db.query(Invoice).filter(
        Invoice.restaurant_id == restaurant_id
    ).order_by(Invoice.invoice_date.desc()).offset(skip).limit(limit).all()
    
    return invoices


@router.get("/{restaurant_id}/payments")
async def get_restaurant_payments(
    restaurant_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all payments from a specific restaurant
    """
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    
    payments = db.query(Payment).filter(
        Payment.restaurant_id == restaurant_id,
        Payment.payment_type == PaymentType.RECEIPT
    ).order_by(Payment.date.desc()).offset(skip).limit(limit).all()
    
    return payments


@router.get("/{restaurant_id}/summary")
async def get_restaurant_summary(
    restaurant_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get financial summary for a restaurant
    """
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    
    # Total sales (from finalized invoices)
    total_sales = db.query(func.sum(Invoice.grand_total)).filter(
        and_(
            Invoice.restaurant_id == restaurant_id,
            Invoice.is_finalized == True
        )
    ).scalar() or 0
    
    # Total payments received
    total_payments = db.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.restaurant_id == restaurant_id,
            Payment.payment_type == PaymentType.RECEIPT,
            Payment.status == "completed"
        )
    ).scalar() or 0
    
    # Outstanding balance
    outstanding = max(0.0, total_sales - total_payments)
    
    # Credit usage
    credit_used = outstanding
    credit_available = restaurant.credit_limit - credit_used if restaurant.credit_limit > 0 else 0
    credit_usage_percent = min(100.0, credit_used / restaurant.credit_limit * 100) if restaurant.credit_limit > 0 else 0
    
    # Number of orders
    order_count = db.query(SalesOrder).filter(
        SalesOrder.restaurant_id == restaurant_id
    ).count()
    
    # Last order date
    last_order = db.query(SalesOrder).filter(
        SalesOrder.restaurant_id == restaurant_id
    ).order_by(SalesOrder.order_date.desc()).first()
    
    return {
        "restaurant_id": restaurant.id,
        "restaurant_name": restaurant.name,
        "credit_limit": restaurant.credit_limit,
        "credit_used": credit_used,
        "credit_available": credit_available,
        "credit_usage_percent": credit_usage_percent,
        "total_sales": total_sales,
        "total_payments": total_payments,
        "outstanding": outstanding,
        "order_count": order_count,
        "last_order_date": last_order.order_date if last_order else None
    }


@router.post("/{restaurant_id}/notes", response_model=RestaurantNoteResponse)
async def create_restaurant_note(
    restaurant_id: int,
    note_data: RestaurantNoteCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a note to a restaurant
    """
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    
    new_note = RestaurantNote(
        restaurant_id=restaurant_id,
        note=note_data.note,
        created_by=current_user.id
    )
    
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    
    return new_note


@router.get("/{restaurant_id}/notes", response_model=List[RestaurantNoteResponse])
async def get_restaurant_notes(
    restaurant_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all notes for a restaurant
    """
    notes = db.query(RestaurantNote).filter(
        RestaurantNote.restaurant_id == restaurant_id
    ).order_by(RestaurantNote.created_at.desc()).all()
    
    return notes


@router.get("/{restaurant_id}/statement")
async def get_restaurant_statement(
    restaurant_id: int,
    start_date: str = Query(...),
    end_date: str = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get statement for a restaurant for any date range
    """
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    
    start_dt, end_dt = parse_dates(start_date, end_date)

    # Get invoices in the period
    invoices = db.query(Invoice).filter(
        and_(
            Invoice.restaurant_id == restaurant_id,
            Invoice.invoice_date >= start_dt,
            Invoice.invoice_date <= end_dt,
            Invoice.is_finalized == True
        )
    ).order_by(Invoice.invoice_date).all()
    
    # Calculate total sales
    total_sales = sum(inv.grand_total for inv in invoices)
    
    # Get payments in the period
    payments = db.query(Payment).filter(
        and_(
            Payment.restaurant_id == restaurant_id,
            Payment.date >= start_dt,
            Payment.date <= end_dt,
            Payment.payment_type == PaymentType.RECEIPT
        )
    ).order_by(Payment.date).all()
    
    # Calculate total payments
    total_payments = sum(pay.amount for pay in payments if pay.status == "completed")
    
    # Calculate opening balance (sum of all invoices before start date minus payments before start date)
    opening_balance_invoices = db.query(func.sum(Invoice.grand_total)).filter(
        and_(
            Invoice.restaurant_id == restaurant_id,
            Invoice.invoice_date < start_dt,
            Invoice.is_finalized == True
        )
    ).scalar() or 0
    
    opening_payments = db.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.restaurant_id == restaurant_id,
            Payment.date < start_dt,
            Payment.payment_type == PaymentType.RECEIPT,
            Payment.status == "completed"
        )
    ).scalar() or 0
    
    opening_balance = max(0.0, opening_balance_invoices - opening_payments)
    closing_balance = max(0.0, opening_balance + total_sales - total_payments)
    
    return {
        "restaurant_id": restaurant.id,
        "restaurant": restaurant.name,
        "restaurant_code": restaurant.restaurant_code,
        "phone": restaurant.phone,
        "address": restaurant.address,
        "period_start": start_dt,
        "period_end": end_dt,
        "opening_balance": opening_balance,
        "total_sales": total_sales,
        "total_payments": total_payments,
        "closing_balance": closing_balance,
        "invoices": [
            {
                "id": inv.id,
                "date": inv.invoice_date,
                "invoice_number": inv.invoice_number,
                "amount": inv.grand_total,
                "amount_paid": inv.amount_paid or 0,
                "balance_due": inv.balance_due or 0,
                "payment_status": inv.payment_status or "unpaid"
            }
            for inv in invoices
        ],
        "payments": [
            {
                "id": pay.id,
                "date": pay.date,
                "payment_code": pay.payment_code,
                "amount": pay.amount,
                "method": pay.payment_method,
                "status": pay.status,
                "transaction_reference": pay.transaction_reference or ""
            }
            for pay in payments
        ]
    }
