"""
Stock Movement schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class MovementType(str, Enum):
    purchase_received = "purchase_received"
    customer_return = "customer_return"
    stock_adjustment_in = "stock_adjustment_in"
    restaurant_sale = "restaurant_sale"
    retail_sale = "retail_sale"
    damaged_stock = "damaged_stock"
    expired_stock = "expired_stock"
    stock_adjustment_out = "stock_adjustment_out"
    vendor_return = "vendor_return"


class StockMovementCreate(BaseModel):
    product_id: int
    movement_type: MovementType
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None
    quantity: float = Field(..., gt=0)
    unit: str
    rate: Optional[float] = None
    notes: Optional[str] = None


class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    movement_type: str
    reference_id: Optional[int]
    reference_type: Optional[str]
    quantity: float
    unit: str
    rate: Optional[float]
    total: Optional[float]
    balance_after: float
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
