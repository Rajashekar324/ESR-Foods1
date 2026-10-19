"""
Expense schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class ExpenseCategory(str, Enum):
    transport = "transport"
    transportation = "transportation"
    utilities = "utilities"
    electricity = "electricity"
    cold_storage = "cold_storage"
    packaging = "packaging"
    supplies = "supplies"
    salaries = "salaries"
    fuel = "fuel"
    maintenance = "maintenance"
    ice = "ice"
    rent = "rent"
    other = "other"
    miscellaneous = "miscellaneous"


class ExpenseCreate(BaseModel):
    expense_code: Optional[str] = None
    date: datetime
    category: ExpenseCategory
    description: str = Field(..., max_length=255)
    amount: float = Field(..., gt=0)
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class ExpenseUpdate(BaseModel):
    date: Optional[datetime] = None
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: int
    expense_code: str
    date: datetime
    category: str
    description: str
    amount: float
    payment_method: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
