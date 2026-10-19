"""
Security utilities for JWT authentication and password hashing
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.user import User, RoleType
import os

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# JWT configuration. Do not silently rotate the signing key between restarts.
SECRET_KEY = os.getenv("SECRET_KEY", "")
if len(SECRET_KEY) < 32 or SECRET_KEY.startswith("replace-with-"):
    raise RuntimeError("Set a unique SECRET_KEY of at least 32 characters in the private .env before starting ESR Foods.")
ALGORITHM = "HS256"
if os.getenv("ALGORITHM", "HS256") != ALGORITHM:
    raise RuntimeError("Only HS256 is supported for JWT signing.")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))  # 24 hours default

# Central capability policy: update the role's allowed capabilities here.
ROLE_CAPABILITIES = {
    RoleType.ADMIN.value: frozenset({"*"}),
    RoleType.MANAGER.value: frozenset({"business", "financial_reports"}),
    RoleType.STAFF.value: frozenset({"notifications"}),
}


def has_capability(user: User, capability: str) -> bool:
    if not user.role:
        return False
    capabilities = ROLE_CAPABILITIES.get(user.role.name, frozenset())
    return "*" in capabilities or capability in capabilities


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict]:
    """
    Decode and verify a JWT token
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session_token: Optional[str] = Cookie(None, alias="esr_session"),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(session_token or token) if (session_token or token) else None
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    if user.approval_status != "approved" or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account access is not approved or has been disabled")
    if payload.get("ver", 0) != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired. Sign in again.")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user
    """
    if not current_user.is_active or current_user.approval_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_page_user(
    session_token: Optional[str] = Cookie(None, alias="esr_session"),
    db: Session = Depends(get_db)
) -> User:
    """Authenticate full-page navigations using the HttpOnly session cookie."""
    if not session_token:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, detail="Authentication required", headers={"Location": "/login.html"})
    payload = decode_access_token(session_token)
    username = payload.get("sub") if payload else None
    user = db.query(User).filter(User.username == username).first() if username else None
    if not user or not user.is_active or user.approval_status != "approved":
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, detail="Authentication required", headers={"Location": "/login.html"})
    if payload.get("ver", 0) != user.token_version:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, detail="Authentication required", headers={"Location": "/login.html"})
    return user


def require_admin_page():
    async def page_role_checker(current_user: User = Depends(get_current_page_user)) -> User:
        if not has_capability(current_user, "users:manage"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
        return current_user
    return page_role_checker


def require_manager_page():
    async def page_role_checker(current_user: User = Depends(get_current_page_user)) -> User:
        if not has_capability(current_user, "business"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager access required")
        return current_user
    return page_role_checker


def require_role(required_role: RoleType):
    """
    Dependency to check if user has required role
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        allowed = (
            has_capability(current_user, "users:manage")
            if required_role == RoleType.ADMIN
            else has_capability(current_user, "business")
            if required_role == RoleType.MANAGER
            else bool(current_user.role and current_user.role.name == required_role.value)
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {required_role.value}"
            )
        return current_user
    return role_checker


def require_admin():
    """Require admin role"""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not has_capability(current_user, "users:manage"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
        return current_user
    return role_checker


def require_manager_or_admin():
    """Require manager or admin role"""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not has_capability(current_user, "business"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have required role: manager or admin"
            )
        return current_user
    return role_checker
