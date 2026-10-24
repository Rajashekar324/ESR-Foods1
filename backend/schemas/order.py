"""
Sales Order and SalesOrderItem schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class OrderStatus(str, Enum):
    draft = "draft"
    confirmed = "confirmed"
    processing = "processing"
    packed = "packed"
    delivered = "delivered"
    cancelled = "cancelled"


class DeliveryStatus(str, Enum):
    pending = "pending"
    in_transit = "in_transit"
    delivered = "delivered"
    cancelled = "cancelled"


class CustomerType(str, Enum):
    restaurant = "restaurant"
    retail = "retail"


class OrderItemCreate(BaseModel):
    id: Optional[int] = None
    product_id: int
    quantity: float = Field(..., gt=0)
    unit: str
    selling_price: float = Field(..., gt=0)
    discount: float = Field(0, ge=0)
    tax: float = Field(0, ge=0)


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: int
    quantity: float
    unit: str
    selling_price: float
    discount: float
    tax: float
    total: float

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    order_code: Optional[str] = None
    customer_type: CustomerType
    restaurant_id: Optional[int] = None
    customer_id: Optional[int] = None
    order_date: datetime
    delivery_date: Optional[datetime] = None
    discount: float = Field(0, ge=0)
    tax: float = Field(0, ge=0)
    notes: Optional[str] = None
    items: List[OrderItemCreate] = Field(..., min_length=1)


class OrderUpdate(BaseModel):
    order_date: Optional[datetime] = None
    delivery_date: Optional[datetime] = None
    discount: Optional[float] = Field(None, ge=0)
    tax: Optional[float] = Field(None, ge=0)
    items: Optional[List[OrderItemCreate]] = Field(None, min_length=1)
    payment_status: Optional[str] = None
    order_status: Optional[OrderStatus] = None
    delivery_status: Optional[DeliveryStatus] = None
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    order_code: str
    customer_type: str
    restaurant_id: Optional[int]
    customer_id: Optional[int]
    order_date: datetime
    delivery_date: Optional[datetime]
    subtotal: float
    discount: float
    tax: float
    total: float
    payment_status: str
    order_status: str
    delivery_status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True
