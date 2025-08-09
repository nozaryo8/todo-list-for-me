from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from schemas import TaskCommentCreate, TaskCommentResponse, TaskCommentUpdate, TaskAttachmentResponse
from migration.models import User, Task, TaskComment, TaskAttachment, ProjectMember
import os
import uuid
from pathlib import Path

router = APIRouter(prefix="/comments", tags=["Comments"])

def check_task_access(db: Session, task_id: int, user_id: int):
    """タスクへのアクセス権限をチェック"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == task.project_id,
        ProjectMember.user_id == user_id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this task"
        )
    return task

@router.post("", response_model=TaskCommentResponse)
async def create_comment(
    comment_data: TaskCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """タスクにコメントを作成"""
    # タスクアクセス権限チェック
    check_task_access(db, comment_data.task_id, current_user.id)
    
    db_comment = TaskComment(
        task_id=comment_data.task_id,
        user_id=current_user.id,
        content=comment_data.content
    )
    
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    
    return db_comment

@router.get("/task/{task_id}", response_model=List[TaskCommentResponse])
async def get_task_comments(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """指定されたタスクのコメント一覧を取得"""
    # タスクアクセス権限チェック
    check_task_access(db, task_id, current_user.id)
    
    comments = db.query(TaskComment).filter(
        TaskComment.task_id == task_id
    ).order_by(TaskComment.created_at).all()
    
    return comments

@router.put("/{comment_id}", response_model=TaskCommentResponse)
async def update_comment(
    comment_id: int,
    comment_update: TaskCommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """コメントを更新"""
    comment = db.query(TaskComment).filter(TaskComment.id == comment_id).first()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # コメント作成者のみ編集可能
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only comment author can edit"
        )
    
    # タスクアクセス権限チェック
    check_task_access(db, comment.task_id, current_user.id)
    
    if comment_update.content:
        comment.content = comment_update.content
        comment.is_edited = True
    
    db.commit()
    db.refresh(comment)
    
    return comment

@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """コメントを削除"""
    comment = db.query(TaskComment).filter(TaskComment.id == comment_id).first()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # コメント作成者または管理者のみ削除可能
    task = db.query(Task).filter(Task.id == comment.task_id).first()
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == task.project_id,
        ProjectMember.user_id == current_user.id
    ).first()
    
    if comment.user_id != current_user.id and membership.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this comment"
        )
    
    db.delete(comment)
    db.commit()
    
    return {"message": "Comment deleted successfully"}

# ファイル添付API
@router.post("/task/{task_id}/attachments", response_model=TaskAttachmentResponse)
async def upload_attachment(
    task_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """タスクにファイルを添付"""
    # タスクアクセス権限チェック
    check_task_access(db, task_id, current_user.id)
    
    # ファイルサイズ制限（10MB）
    max_file_size = 10 * 1024 * 1024  # 10MB
    file_content = await file.read()
    if len(file_content) > max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size too large. Maximum size is 10MB."
        )
    
    # ファイル保存用ディレクトリを作成
    upload_dir = Path("uploads/attachments")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # ユニークなファイル名を生成
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename
    
    # ファイルを保存
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    
    # データベースに記録
    db_attachment = TaskAttachment(
        task_id=task_id,
        user_id=current_user.id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=len(file_content),
        mime_type=file.content_type
    )
    
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    
    return db_attachment

@router.get("/task/{task_id}/attachments", response_model=List[TaskAttachmentResponse])
async def get_task_attachments(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """指定されたタスクの添付ファイル一覧を取得"""
    # タスクアクセス権限チェック
    check_task_access(db, task_id, current_user.id)
    
    attachments = db.query(TaskAttachment).filter(
        TaskAttachment.task_id == task_id
    ).order_by(TaskAttachment.created_at).all()
    
    return attachments

@router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添付ファイルを削除"""
    attachment = db.query(TaskAttachment).filter(TaskAttachment.id == attachment_id).first()
    
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )
    
    # アップロードユーザーまたは管理者のみ削除可能
    task = db.query(Task).filter(Task.id == attachment.task_id).first()
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == task.project_id,
        ProjectMember.user_id == current_user.id
    ).first()
    
    if attachment.user_id != current_user.id and membership.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this attachment"
        )
    
    # ファイルを削除
    try:
        os.remove(attachment.file_path)
    except FileNotFoundError:
        pass  # ファイルが既に存在しない場合は無視
    
    db.delete(attachment)
    db.commit()
    
    return {"message": "Attachment deleted successfully"}