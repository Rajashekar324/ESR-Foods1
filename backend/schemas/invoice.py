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
    discount: float = Field(0, ge=0)
    tax: float = Field(0, ge=0)


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
    invoice_number: Optional[str] = Field(None, max_length=50)
    order_id: Optional[int] = None
    restaurant_id: int
    invoice_date: datetime
    due_date: Optional[datetime] = None
    discount: float = Field(0, ge=0)
    tax: float = Field(0, ge=0)
    notes: Optional[str] = None
    items: List[InvoiceItemCreate] = Field(..., min_length=1)


class InvoiceUpdate(BaseModel):
    due_date: Optional[datetime] = None
    discount: Optional[float] = Field(None, ge=0)
    tax: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    items: Optional[List[InvoiceItemCreate]] = Field(None, min_length=1)


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
