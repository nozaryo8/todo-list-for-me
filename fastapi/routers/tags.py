from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from schemas import TagCreate, TagResponse, TagUpdate, NotificationResponse
from migration.models import User, Tag, ProjectMember, Notification, TaskTag

router = APIRouter(prefix="/tags", tags=["Tags"])

@router.post("", response_model=TagResponse)
async def create_tag(
    tag_data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """新しいタグを作成"""
    # プロジェクト固有タグの場合、プロジェクトアクセス権限をチェック
    if tag_data.project_id:
        membership = db.query(ProjectMember).filter(
            ProjectMember.project_id == tag_data.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to this project"
            )
    
    # 同じ名前のタグが既に存在するかチェック
    existing_tag = db.query(Tag).filter(
        Tag.name == tag_data.name,
        Tag.project_id == tag_data.project_id
    ).first()
    
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists in this project"
        )
    
    db_tag = Tag(
        name=tag_data.name,
        color=tag_data.color,
        project_id=tag_data.project_id,
        created_by=current_user.id
    )
    
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    
    return db_tag

@router.get("", response_model=List[TagResponse])
async def get_tags(
    project_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """タグ一覧を取得"""
    query = db.query(Tag)
    
    if project_id:
        # プロジェクトアクセス権限をチェック
        membership = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to this project"
            )
        
        # 指定されたプロジェクトのタグとグローバルタグを取得
        query = query.filter(
            (Tag.project_id == project_id) | (Tag.project_id.is_(None))
        )
    else:
        # ユーザーがアクセス可能なプロジェクトのタグとグローバルタグを取得
        accessible_projects = db.query(ProjectMember.project_id).filter(
            ProjectMember.user_id == current_user.id
        ).subquery()
        
        query = query.filter(
            (Tag.project_id.in_(accessible_projects)) | (Tag.project_id.is_(None))
        )
    
    tags = query.order_by(Tag.name).all()
    
    return tags

@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    tag_update: TagUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """タグを更新"""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # タグ作成者または管理者のみ編集可能
    if tag.project_id:
        membership = db.query(ProjectMember).filter(
            ProjectMember.project_id == tag.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        
        if tag.created_by != current_user.id and (not membership or membership.role not in ["owner", "admin"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to edit this tag"
            )
    else:
        # グローバルタグは作成者のみ編集可能
        if tag.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tag creator can edit this tag"
            )
    
    # 更新データを適用
    update_data = tag_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tag, field, value)
    
    db.commit()
    db.refresh(tag)
    
    return tag

@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """タグを削除"""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # タグ作成者または管理者のみ削除可能
    if tag.project_id:
        membership = db.query(ProjectMember).filter(
            ProjectMember.project_id == tag.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        
        if tag.created_by != current_user.id and (not membership or membership.role not in ["owner", "admin"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to delete this tag"
            )
    else:
        # グローバルタグは作成者のみ削除可能
        if tag.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tag creator can delete this tag"
            )
    
    # タグが使用されているかチェック
    usage_count = db.query(TaskTag).filter(TaskTag.tag_id == tag_id).count()
    if usage_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag is being used by {usage_count} task(s). Cannot delete."
        )
    
    db.delete(tag)
    db.commit()
    
    return {"message": "Tag deleted successfully"}

# 通知API
@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザーの通知一覧を取得"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.order_by(Notification.created_at.desc()).all()
    
    return notifications

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """通知を既読にする"""
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

@router.put("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """すべての通知を既読にする"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    
    return {"message": "All notifications marked as read"}