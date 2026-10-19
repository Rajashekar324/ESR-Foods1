"""
Product and Category schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class SeafoodType(str, Enum):
    fish = "fish"
    prawns = "prawns"
    shrimp = "shrimp"
    crab = "crab"
    squid = "squid"
    other = "other"


class UnitType(str, Enum):
    kg = "kg"
    gram = "gram"
    box = "box"
    packet = "packet"
    piece = "piece"


class CategoryCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    product_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    category_id: Optional[int] = None
    seafood_type: SeafoodType
    variety: Optional[str] = None
    brand: Optional[str] = None
    grade: Optional[str] = None
    size: Optional[str] = None
    unit: UnitType
    weight_per_packet: Optional[float] = None
    packaging_type: Optional[str] = None
    is_frozen: bool = True
    purchase_price: float = Field(..., gt=0)
    selling_price: float = Field(..., gt=0)
    wholesale_price: Optional[float] = None
    retail_price: Optional[float] = None
    minimum_stock: float = 10
    maximum_stock: Optional[float] = None
    reorder_level: float = 20
    preferred_vendor_id: Optional[int] = None
    storage_location: Optional[str] = None
    manufacturing_date: Optional[datetime] = None
    expiry_info: Optional[str] = None
    product_image: Optional[str] = None
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    seafood_type: Optional[SeafoodType] = None
    variety: Optional[str] = None
    brand: Optional[str] = None
    grade: Optional[str] = None
    size: Optional[str] = None
    unit: Optional[UnitType] = None
    weight_per_packet: Optional[float] = None
    packaging_type: Optional[str] = None
    is_frozen: Optional[bool] = None
    purchase_price: Optional[float] = None
    selling_price: Optional[float] = None
    wholesale_price: Optional[float] = None
    retail_price: Optional[float] = None
    minimum_stock: Optional[float] = None
    maximum_stock: Optional[float] = None
    reorder_level: Optional[float] = None
    preferred_vendor_id: Optional[int] = None
    storage_location: Optional[str] = None
    manufacturing_date: Optional[datetime] = None
    expiry_info: Optional[str] = None
    product_image: Optional[str] = None
    status: Optional[bool] = None
    description: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    product_code: str
    name: str
    category_id: Optional[int]
    seafood_type: str
    variety: Optional[str]
    brand: Optional[str]
    grade: Optional[str]
    size: Optional[str]
    unit: str
    weight_per_packet: Optional[float]
    packaging_type: Optional[str]
    is_frozen: bool
    purchase_price: float
    selling_price: float
    wholesale_price: Optional[float]
    retail_price: Optional[float]
    current_stock: float
    minimum_stock: float
    maximum_stock: Optional[float]
    reorder_level: float
    preferred_vendor_id: Optional[int]
    storage_location: Optional[str]
    manufacturing_date: Optional[datetime]
    expiry_info: Optional[str]
    product_image: Optional[str]
    is_active: bool = True
    status: bool = True
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    category: Optional[CategoryResponse] = None

    class Config:
        from_attributes = True
