"""
Users router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from backend.database import get_db
from backend.models.user import User, Role
from backend.models.audit_log import AuditLog
from backend.schemas.user import UserCreate, UserResponse, RoleAssignment
from backend.auth.security import hash_password, require_admin

router = APIRouter(prefix="/api/users", tags=["Users"])


def commit_user_status(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The change would remove the last active Admin.") from exc


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new user (Admin only)
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
    
    # Verify role exists
    role = db.query(Role).filter(Role.id == user_data.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )
    
    # Create user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        role_id=user_data.role_id,
        is_active=True,
        approval_status="approved"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.add(AuditLog(user_id=current_user.id, action="user_created", module="users", record_id=new_user.id, new_value="approved"))
    db.commit()
    
    return new_user


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    role_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    approval_status: Optional[str] = Query(None, pattern="^(pending|approved|rejected|disabled)$"),
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Get all users with optional filters
    """
    query = db.query(User)
    
    if role_id:
        query = query.filter(User.role_id == role_id)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if approval_status:
        query = query.filter(User.approval_status == approval_status)
    
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Get a specific user by ID
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


def ensure_another_active_admin(db: Session, user: User):
    if user.role and user.role.name == "admin" and user.is_active and user.approval_status == "approved":
        count = db.query(User).join(Role).filter(
            Role.name == "admin", User.is_active.is_(True), User.approval_status == "approved"
        ).count()
        if count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The application must retain at least one active Admin.")


@router.put("/{user_id}/approve")
async def approve_user(
    user_id: int,
    role_assignment: RoleAssignment,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.approval_status == "disabled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Disabled accounts must be re-enabled explicitly.")
    role = db.query(Role).filter(Role.id == role_assignment.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role")
    if user.role_id != role.id:
        previous_role = user.role.name if user.role else str(user.role_id)
        user.role_id = role.id
        user.token_version += 1
        db.add(AuditLog(user_id=current_user.id, action="user_role_changed", module="users", record_id=user.id, previous_value=previous_role, new_value=role.name))
    user.approval_status = "approved"
    user.is_active = True
    db.add(AuditLog(user_id=current_user.id, action="user_approved", module="users", record_id=user.id, new_value=f"approved; role={role.name}"))
    commit_user_status(db)
    return {"message": "User approved successfully"}


@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_assignment: RoleAssignment,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """Change a user's role and revoke existing sessions so new permissions apply."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = db.query(Role).filter(Role.id == role_assignment.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role")
    if user.id == current_user.id and user.role_id != role.id:
        raise HTTPException(status_code=400, detail="You cannot change your own administrator role.")
    if user.role_id == role.id:
        return user

    previous_role = user.role.name if user.role else str(user.role_id)
    ensure_another_active_admin(db, user)
    user.role_id = role.id
    user.token_version += 1
    db.add(AuditLog(
        user_id=current_user.id,
        action="user_role_changed",
        module="users",
        record_id=user.id,
        previous_value=previous_role,
        new_value=role.name
    ))
    commit_user_status(db)
    db.refresh(user)
    return user


@router.put("/{user_id}/reject")
async def reject_user(
    user_id: int,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot reject your own administrator account.")
    ensure_another_active_admin(db, user)
    user.approval_status = "rejected"
    user.is_active = False
    user.token_version += 1
    db.add(AuditLog(user_id=current_user.id, action="user_rejected", module="users", record_id=user.id, new_value="rejected"))
    commit_user_status(db)
    return {"message": "User rejected successfully"}


@router.put("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    ensure_another_active_admin(db, user)
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot disable your own administrator account.")
    user.is_active = False
    user.approval_status = "disabled"
    user.token_version += 1
    db.add(AuditLog(user_id=current_user.id, action="user_disabled", module="users", record_id=user.id, new_value="disabled"))
    commit_user_status(db)
    
    return {"message": "User deactivated successfully"}


@router.put("/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Activate a user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
    )
    
    if user.approval_status == "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approve a pending user before enabling access.")
    user.is_active = True
    user.approval_status = "approved"
    db.add(AuditLog(user_id=current_user.id, action="user_enabled", module="users", record_id=user.id, new_value="approved"))
    db.commit()
    
    return {"message": "User activated successfully"}
