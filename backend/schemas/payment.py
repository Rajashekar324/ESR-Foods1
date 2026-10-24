"""
Payment schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class PaymentMethod(str, Enum):
    cash = "cash"
    upi = "upi"
    bank_transfer = "bank_transfer"
    card = "card"
    cheque = "cheque"
    other = "other"


class PaymentType(str, Enum):
    receipt = "receipt"
    payment = "payment"


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"
    reversed = "reversed"


class PaymentCreate(BaseModel):
    payment_code: Optional[str] = None
    payment_type: PaymentType
    date: datetime
    invoice_id: Optional[int] = None
    purchase_id: Optional[int] = None
    expense_id: Optional[int] = None
    restaurant_id: Optional[int] = None
    vendor_id: Optional[int] = None
    customer_id: Optional[int] = None
    amount: float = Field(..., gt=0)
    payment_method: PaymentMethod
    status: Optional[str] = "completed"
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None
    category: Optional[str] = None
    paid_to: Optional[str] = None


class PaymentStatusUpdate(BaseModel):
    status: str


class PaymentUpdate(BaseModel):
    date: Optional[datetime] = None
    invoice_id: Optional[int] = None
    amount: Optional[float] = Field(None, gt=0)
    payment_method: Optional[PaymentMethod] = None
    status: Optional[str] = None
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    payment_code: str
    payment_type: str
    date: datetime
    invoice_id: Optional[int] = None
    purchase_id: Optional[int] = None
    expense_id: Optional[int] = None
    restaurant_id: Optional[int] = None
    vendor_id: Optional[int] = None
    customer_id: Optional[int] = None
    amount: float
    payment_method: str
    status: str = "completed"
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None
    category: Optional[str] = None
    paid_to: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
