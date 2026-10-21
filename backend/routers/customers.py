"""
Retail Customers router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from backend.database import get_db
from backend.models.customer import RetailCustomer
from backend.models.order import SalesOrder
from backend.models.payment import Payment, PaymentType
from backend.models.user import User
from backend.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/customers", tags=["Retail Customers"], dependencies=[Depends(require_manager_or_admin())])


@router.post("/", response_model=CustomerResponse)
async def create_customer(
    customer_data: CustomerCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new retail customer (Manager/Admin only)
    """
    if db.query(RetailCustomer).filter(RetailCustomer.customer_code == customer_data.customer_code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer code already exists"
        )
    
    new_customer = RetailCustomer(**customer_data.model_dump())
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    
    return new_customer


@router.get("/", response_model=List[CustomerResponse])
async def get_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    status: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all retail customers with optional filters
    """
    query = db.query(RetailCustomer)
    
    if search:
        query = query.filter(
            (RetailCustomer.name.ilike(f"%{search}%")) |
            (RetailCustomer.customer_code.ilike(f"%{search}%")) |
            (RetailCustomer.phone.ilike(f"%{search}%"))
        )
    
    if status is not None:
        query = query.filter(RetailCustomer.status == status)
    
    customers = query.order_by(RetailCustomer.name).offset(skip).limit(limit).all()
    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific customer by ID
    """
    customer = db.query(RetailCustomer).filter(RetailCustomer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Update a retail customer (Manager/Admin only)
    """
    customer = db.query(RetailCustomer).filter(RetailCustomer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    update_data = customer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    customer.updated_at = func.now()
    db.commit()
    db.refresh(customer)
    
    return customer


@router.get("/{customer_id}/orders")
async def get_customer_orders(
    customer_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all orders for a specific customer
    """
    customer = db.query(RetailCustomer).filter(RetailCustomer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    orders = db.query(SalesOrder).filter(
        SalesOrder.customer_id == customer_id
    ).order_by(SalesOrder.order_date.desc()).offset(skip).limit(limit).all()
    
    return orders


@router.get("/{customer_id}/payments")
async def get_customer_payments(
    customer_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get receipt history recorded against a retail customer."""
    customer = db.query(RetailCustomer).filter(RetailCustomer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return db.query(Payment).filter(
        Payment.customer_id == customer_id,
        Payment.payment_type == PaymentType.RECEIPT
    ).order_by(Payment.date.desc()).offset(skip).limit(limit).all()


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Delete a retail customer (Manager/Admin only)
    """
    customer = db.query(RetailCustomer).filter(RetailCustomer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    if db.query(Payment).filter(Payment.customer_id == customer_id).count():
        raise HTTPException(status_code=400, detail="Customers with payment history cannot be deleted. Keep the financial history intact.")
    
    db.delete(customer)
    db.commit()
    return {"message": "Customer deleted successfully"}
