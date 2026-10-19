"""
Expenses router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime
from backend.database import get_db
from backend.models.expense import Expense, ExpenseCategory
from backend.models.payment import Payment, PaymentType, PaymentMethod
from backend.models.user import User
from backend.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/expenses", tags=["Expenses"], dependencies=[Depends(require_manager_or_admin())])


def parse_dates(start_date: str, end_date: str):
    try:
        start_dt = datetime.fromisoformat(start_date) if "T" in start_date else datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.fromisoformat(end_date) if "T" in end_date else datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        return start_dt, end_dt
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD")


@router.post("/", response_model=ExpenseResponse)
async def create_expense(
    expense_data: ExpenseCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new expense (Manager/Admin only) and auto-add to payments
    """
    data = expense_data.model_dump()
    reference_number = data.pop("reference_number", None)
    
    if not data.get("expense_code"):
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        data["expense_code"] = f"EXP-{timestamp}"
    elif db.query(Expense).filter(Expense.expense_code == data["expense_code"]).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expense code already exists"
        )
    
    if reference_number and not data.get("notes"):
        data["notes"] = f"Ref: {reference_number}"
    elif reference_number:
        data["notes"] = f"{data.get('notes')} (Ref: {reference_number})"
        
    new_expense = Expense(**data)
    db.add(new_expense)
    db.flush()

    # Auto create corresponding payment record
    try:
        timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        pm_raw = (new_expense.payment_method or "cash").lower().replace(" ", "_")
        valid_methods = [m.value for m in PaymentMethod]
        method = pm_raw if pm_raw in valid_methods else PaymentMethod.CASH.value

        auto_payment = Payment(
            payment_code=f"PAY-{new_expense.expense_code}",
            payment_type=PaymentType.PAYMENT,
            date=new_expense.date,
            expense_id=new_expense.id,
            amount=new_expense.amount,
            payment_method=method,
            status="completed",
            notes=f"Expense: {new_expense.description}"
        )
        db.add(auto_payment)
    except Exception as e:
        print("Notice: Auto payment creation for expense failed:", e)

    db.commit()
    db.refresh(new_expense)
    
    return new_expense


@router.get("/", response_model=List[ExpenseResponse])
async def get_expenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all expenses with optional filters
    """
    query = db.query(Expense)
    
    if category:
        query = query.filter(Expense.category == category)
    
    if start_date:
        start_dt = datetime.fromisoformat(start_date) if "T" in start_date else datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(Expense.date >= start_dt)
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date) if "T" in end_date else datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.filter(Expense.date <= end_dt)
    
    expenses = query.order_by(Expense.date.desc()).offset(skip).limit(limit).all()
    return expenses


@router.get("/{expense_id:int}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific expense by ID
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    expense_data: ExpenseUpdate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Update an expense (Manager/Admin only)
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    update_data = expense_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense, field, value)
    
    expense.updated_at = func.now()

    # Also update linked payment if exists
    linked_payment = db.query(Payment).filter(Payment.expense_id == expense_id).first()
    if linked_payment:
        linked_payment.amount = expense.amount
        linked_payment.date = expense.date
        if expense.description:
            linked_payment.notes = f"Expense: {expense.description}"

    db.commit()
    db.refresh(expense)
    
    return expense


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Delete an expense (Manager/Admin only)
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    # Preserve the payment ledger when an expense is removed.
    db.query(Payment).filter(Payment.expense_id == expense_id).update(
        {Payment.status: "reversed"}, synchronize_session=False
    )

    db.delete(expense)
    db.commit()
    
    return {"message": "Expense deleted successfully"}


@router.get("/summary")
async def get_expenses_summary(
    start_date: str = Query(...),
    end_date: str = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get expenses summary for a date range
    """
    start_dt, end_dt = parse_dates(start_date, end_date)

    # Total expenses
    total_expenses = db.query(func.sum(Expense.amount)).filter(
        and_(
            Expense.date >= start_dt,
            Expense.date <= end_dt
        )
    ).scalar() or 0
    
    # Expenses by category
    expenses_by_category = db.query(
        Expense.category,
        func.sum(Expense.amount).label('total')
    ).filter(
        and_(
            Expense.date >= start_dt,
            Expense.date <= end_dt
        )
    ).group_by(Expense.category).all()
    
    return {
        "period_start": start_dt,
        "period_end": end_dt,
        "total_expenses": total_expenses,
        "expenses_by_category": [
            {"category": cat, "total": total}
            for cat, total in expenses_by_category
        ]
    }
