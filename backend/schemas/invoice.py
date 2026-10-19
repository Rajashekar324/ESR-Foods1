"""
Invoice and InvoiceItem schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class InvoiceItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(..., gt=0)
    unit: str
    rate: float = Field(..., gt=0)
    discount: float = 0
    tax: float = 0


class InvoiceItemResponse(BaseModel):
    id: int
    invoice_id: int
    product_id: int
    quantity: float
    unit: str
    rate: float
    discount: float
    tax: float
    amount: float

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    invoice_number: str = Field(..., max_length=50)
    order_id: Optional[int] = None
    restaurant_id: int
    invoice_date: datetime
    due_date: Optional[datetime] = None
    discount: float = 0
    tax: float = 0
    notes: Optional[str] = None
    items: List[InvoiceItemCreate]


class InvoiceUpdate(BaseModel):
    due_date: Optional[datetime] = None
    discount: Optional[float] = None
    tax: Optional[float] = None
    notes: Optional[str] = None
    is_finalized: Optional[bool] = None


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    order_id: Optional[int]
    restaurant_id: int
    invoice_date: datetime
    due_date: Optional[datetime]
    subtotal: float
    discount: float
    tax: float
    grand_total: float
    amount_paid: float
    balance_due: float
    payment_status: str
    notes: Optional[str]
    is_finalized: bool
    created_at: datetime
    updated_at: Optional[datetime]
    items: List[InvoiceItemResponse] = []

    class Config:
        from_attributes = True
