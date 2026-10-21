"""
User and Role schemas
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional


class RoleCreate(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = None
    permissions: Optional[str] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    permissions: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role_id: int = Field(..., gt=0)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be no more than 72 bytes")
        if not any(char.islower() for char in value):
            raise ValueError("Password must contain a lowercase letter")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain an uppercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain a number")
        return value


class RoleAssignment(BaseModel):
    role_id: int = Field(..., gt=0)


class UserLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    role_id: int
    is_active: bool
    approval_status: str
    last_login: Optional[datetime]
    created_at: datetime
    role: Optional[RoleResponse] = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    user: UserResponse
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None
