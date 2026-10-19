"""
Restaurant and RestaurantNote schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class RestaurantType(str, Enum):
    restaurant = "restaurant"
    hotel = "hotel"
    cloud_kitchen = "cloud_kitchen"
    cafe = "cafe"
    catering = "catering"
    other = "other"


class RestaurantCreate(BaseModel):
    restaurant_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    restaurant_type: RestaurantType
    owner_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: str = Field(..., max_length=20)
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    area: Optional[str] = None
    gst_number: Optional[str] = None
    credit_limit: float = 0
    payment_terms: Optional[str] = None
    assigned_salesperson: Optional[str] = None
    notes: Optional[str] = None


class RestaurantUpdate(BaseModel):
    restaurant_code: Optional[str] = None
    name: Optional[str] = None
    restaurant_type: Optional[RestaurantType] = None
    owner_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    area: Optional[str] = None
    gst_number: Optional[str] = None
    credit_limit: Optional[float] = None
    payment_terms: Optional[str] = None
    assigned_salesperson: Optional[str] = None
    status: Optional[bool] = None
    notes: Optional[str] = None


class RestaurantResponse(BaseModel):
    id: int
    restaurant_code: str
    name: str
    restaurant_type: str
    owner_name: Optional[str]
    contact_person: Optional[str]
    phone: str
    whatsapp: Optional[str]
    email: Optional[str]
    address: Optional[str]
    area: Optional[str]
    gst_number: Optional[str]
    credit_limit: float
    payment_terms: Optional[str]
    assigned_salesperson: Optional[str]
    status: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RestaurantNoteCreate(BaseModel):
    restaurant_id: int
    note: str


class RestaurantNoteResponse(BaseModel):
    id: int
    restaurant_id: int
    note: str
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
