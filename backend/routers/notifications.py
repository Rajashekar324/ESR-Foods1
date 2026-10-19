"""
Notifications router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.database import get_db
from backend.models.notification import Notification
from backend.models.user import User
from backend.schemas.notification import NotificationCreate, NotificationResponse
from backend.auth.security import get_current_active_user, require_manager_or_admin

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.post("/", response_model=NotificationResponse)
async def create_notification(
    notification_data: NotificationCreate,
    current_user: User = Depends(require_manager_or_admin()),
    db: Session = Depends(get_db)
):
    """
    Create a new notification
    """
    new_notification = Notification(**notification_data.model_dump())
    db.add(new_notification)
    db.commit()
    db.refresh(new_notification)
    
    return new_notification


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get notifications for current user
    """
    query = db.query(Notification).filter(
        (Notification.user_id == current_user.id) | (Notification.user_id.is_(None))
    )
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    return notifications


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark a notification as read
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}


@router.put("/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark all notifications as read for current user
    """
    db.query(Notification).filter(
        (Notification.user_id == current_user.id) | (Notification.user_id.is_(None)),
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    
    return {"message": "All notifications marked as read"}


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get count of unread notifications
    """
    count = db.query(Notification).filter(
        (Notification.user_id == current_user.id) | (Notification.user_id.is_(None)),
        Notification.is_read == False
    ).count()
    
    return {"unread_count": count}
