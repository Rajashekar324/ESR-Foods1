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
    product_id: int
    quantity: float = Field(..., gt=0)
    unit: str
    selling_price: float = Field(..., gt=0)
    discount: float = 0
    tax: float = 0


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
    discount: float = 0
    tax: float = 0
    notes: Optional[str] = None
    items: List[OrderItemCreate] = Field(..., min_length=1)


class OrderUpdate(BaseModel):
    delivery_date: Optional[datetime] = None
    discount: Optional[float] = None
    tax: Optional[float] = None
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
