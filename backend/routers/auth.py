"""
Authentication router
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from backend.database import get_db
from backend.models.user import User, Role
from backend.schemas.user import UserCreate, UserLogin, UserResponse, LoginResponse, RoleCreate, RoleResponse
from backend.auth.security import (
    hash_password, verify_password, create_access_token,
    get_current_active_user, require_admin, ACCESS_TOKEN_EXPIRE_MINUTES
)
from typing import List
from backend.models.audit_log import AuditLog
import os
import logging

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
LOGIN_LOCKOUT_MINUTES = 15
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    # Check if username exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Public registration always receives the least-privileged role. Never trust role_id.
    role = db.query(Role).filter(Role.name == "staff").first()
    if not role:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Registration is temporarily unavailable")
    
    # Create user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        role_id=role.id,
        is_active=False,
        approval_status="pending"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.add(AuditLog(user_id=new_user.id, action="registered", module="auth", new_value="pending"))
    db.commit()
    
    return new_user


@router.post("/login", response_model=LoginResponse)
async def login(credentials: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Login user and return JWT token
    """
    user = db.query(User).filter(
        (User.username == credentials.username) | (User.email == credentials.username)
    ).first()

    now = datetime.now(timezone.utc)
    locked_until = user.locked_until if user else None
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    if locked_until and locked_until > now:
        logger.warning(
            "Authentication failed (reason=account_locked, user_id=%s, client_ip=%s).",
            user.id,
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in {LOGIN_LOCKOUT_MINUTES} minutes.",
        )

    if not user:
        logger.warning(
            "Authentication failed (reason=unknown_account, client_ip=%s).",
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(credentials.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= 5:
            user.failed_login_attempts = 0
            user.locked_until = now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        db.add(AuditLog(user_id=user.id, action="login_failed", module="auth", ip_address=request.client.host if request.client else None))
        db.commit()
        logger.warning(
            "Authentication failed (reason=password_mismatch, user_id=%s, client_ip=%s).",
            user.id,
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.approval_status == "pending":
        logger.warning("Authentication denied (reason=pending_approval, user_id=%s).", user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your registration is awaiting Admin approval.")
    if user.approval_status == "rejected":
        logger.warning("Authentication denied (reason=registration_rejected, user_id=%s).", user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your registration was not approved. Contact your administrator.")
    if user.approval_status == "disabled" or not user.is_active:
        logger.warning("Authentication denied (reason=account_disabled, user_id=%s).", user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled. Contact your administrator."
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(AuditLog(user_id=user.id, action="login", module="auth", ip_address=request.client.host if request.client else None))
    db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "ver": user.token_version},
        expires_delta=access_token_expires
    )

    response.set_cookie(
        key="esr_session",
        value=access_token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", str(request.url.scheme == "https")).lower() == "true",
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    
    return {
        "user": user,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information
    """
    return current_user


@router.post("/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout user (client-side token removal)
    """
    current_user.token_version += 1
    db.commit()
    response.delete_cookie("esr_session", path="/", httponly=True, samesite="lax")
    return {"message": "Successfully logged out"}


# Role management endpoints (Admin only)
@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new role (Admin only)
    """
    if db.query(Role).filter(Role.name == role_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name already exists"
        )
    
    new_role = Role(**role_data.model_dump())
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    return new_role


@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Get all roles (Admin only)
    """
    return db.query(Role).all()
