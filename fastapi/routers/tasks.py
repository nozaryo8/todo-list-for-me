from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from schemas import TaskCreate, TaskResponse, TaskUpdate
from migration.models import User, Task, Project, ProjectMember

router = APIRouter(prefix="/tasks", tags=["Tasks"])

def check_project_access(db: Session, project_id: int, user_id: int):
    """プロジェクトへのアクセス権限をチェック"""
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this project"
        )
    return membership

@router.post("", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """新しいタスクを作成"""
    # プロジェクトアクセス権限チェック
    check_project_access(db, task_data.project_id, current_user.id)
    
    # 親タスクが存在する場合、同じプロジェクト内かチェック
    if task_data.parent_task_id:
        parent_task = db.query(Task).filter(Task.id == task_data.parent_task_id).first()
        if not parent_task or parent_task.project_id != task_data.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent task not found or not in the same project"
            )
    
    # 担当者が指定されている場合、プロジェクトメンバーかチェック
    if task_data.assignee_id:
        check_project_access(db, task_data.project_id, task_data.assignee_id)
    
    db_task = Task(
        title=task_data.title,
        description=task_data.description,
        project_id=task_data.project_id,
        parent_task_id=task_data.parent_task_id,
        assignee_id=task_data.assignee_id,
        creator_id=current_user.id,
        priority=task_data.priority,
        status=task_data.status,
        start_date=task_data.start_date,
        due_date=task_data.due_date,
        estimated_hours=task_data.estimated_hours,
        position=task_data.position
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return db_task

@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    project_id: Optional[int] = Query(None),
    assignee_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    parent_task_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """タスク一覧を取得"""
    query = db.query(Task)
    
    # プロジェクトフィルター
    if project_id:
        check_project_access(db, project_id, current_user.id)
        query = query.filter(Task.project_id == project_id)
    else:
        # ユーザーがアクセス可能なプロジェクトのタスクのみ
        accessible_projects = db.query(ProjectMember.project_id).filter(
            ProjectMember.user_id == current_user.id
        ).subquery()
        query = query.filter(Task.project_id.in_(accessible_projects))
    
    # その他のフィルター
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if parent_task_id:
        query = query.filter(Task.parent_task_id == parent_task_id)
    
    # アーカイブされていないタスクのみ
    query = query.filter(Task.is_archived == False)
    
    # 作成日時で並び替え
    tasks = query.order_by(Task.created_at.desc()).all()
    
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """指定されたタスクの詳細を取得"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # プロジェクトアクセス権限チェック
    check_project_access(db, task.project_id, current_user.id)
    
    return task

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """タスクを更新"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # プロジェクトアクセス権限チェック
    check_project_access(db, task.project_id, current_user.id)
    
    # 担当者が指定されている場合、プロジェクトメンバーかチェック
    if task_update.assignee_id:
        check_project_access(db, task.project_id, task_update.assignee_id)
    
    # ステータスが完了に変更された場合、完了日時を設定
    if task_update.status == "done" and task.status != "done":
        task.completed_at = datetime.now()
    elif task_update.status != "done" and task.status == "done":
        task.completed_at = None
    
    # 更新データを適用
    update_data = task_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field != "status":  # statusは上記で特別処理済み
            setattr(task, field, value)
    
    if task_update.status:
        task.status = task_update.status
    
    db.commit()
    db.refresh(task)
    
    return task

@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """タスクを削除（アーカイブ）"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # プロジェクトアクセス権限チェック
    check_project_access(db, task.project_id, current_user.id)
    
    # 作成者またはプロジェクトオーナー/管理者のみ削除可能
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == task.project_id,
        ProjectMember.user_id == current_user.id
    ).first()
    
    if task.creator_id != current_user.id and membership.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this task"
        )
    
    task.is_archived = True
    db.commit()
    
    return {"message": "Task archived successfully"}

@router.get("/{task_id}/subtasks", response_model=List[TaskResponse])
async def get_subtasks(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """指定されたタスクのサブタスク一覧を取得"""
    parent_task = db.query(Task).filter(Task.id == task_id).first()
    
    if not parent_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent task not found"
        )
    
    # プロジェクトアクセス権限チェック
    check_project_access(db, parent_task.project_id, current_user.id)
    
    subtasks = db.query(Task).filter(
        Task.parent_task_id == task_id,
        Task.is_archived == False
    ).order_by(Task.position, Task.created_at).all()
    
    return subtasks

@router.get("/calendar", response_model=List[TaskResponse])
async def get_calendar_tasks(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """カレンダー表示用のタスク一覧を取得"""
    # ユーザーがアクセス可能なプロジェクトのタスクのみ
    accessible_projects = db.query(ProjectMember.project_id).filter(
        ProjectMember.user_id == current_user.id
    ).subquery()
    
    tasks = db.query(Task).filter(
        Task.project_id.in_(accessible_projects),
        Task.is_archived == False,
        # 開始日または期限日が指定期間内にあるタスク
        (
            (Task.start_date >= start_date) & (Task.start_date <= end_date) |
            (Task.due_date >= start_date) & (Task.due_date <= end_date) |
            (Task.start_date <= start_date) & (Task.due_date >= end_date)
        )
    ).order_by(Task.start_date, Task.due_date).all()
    
    return tasks