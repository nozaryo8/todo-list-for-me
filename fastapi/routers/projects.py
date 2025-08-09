from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from schemas import ProjectCreate, ProjectResponse, ProjectUpdate, ProjectMemberCreate, ProjectMemberResponse
from migration.models import User, Project, ProjectMember

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """新しいプロジェクトを作成"""
    db_project = Project(
        name=project_data.name,
        description=project_data.description,
        color=project_data.color,
        owner_id=current_user.id
    )
    
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # 作成者をオーナーとしてメンバーに追加
    db_member = ProjectMember(
        project_id=db_project.id,
        user_id=current_user.id,
        role="owner"
    )
    db.add(db_member)
    db.commit()
    
    return db_project

@router.get("", response_model=List[ProjectResponse])
async def get_user_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザーが参加しているプロジェクト一覧を取得"""
    projects = db.query(Project).join(ProjectMember).filter(
        ProjectMember.user_id == current_user.id,
        Project.is_archived == False
    ).all()
    
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """指定されたプロジェクトの詳細を取得"""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # ユーザーがプロジェクトメンバーかチェック
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """プロジェクトを更新"""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # オーナーまたは管理者権限をチェック
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id,
        ProjectMember.role.in_(["owner", "admin"])
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    # 更新データを適用
    update_data = project_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    
    return project

@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """プロジェクトを削除（アーカイブ）"""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # オーナー権限をチェック
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner can delete the project"
        )
    
    project.is_archived = True
    db.commit()
    
    return {"message": "Project archived successfully"}

@router.post("/{project_id}/members", response_model=ProjectMemberResponse)
async def add_project_member(
    project_id: int,
    member_data: ProjectMemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """プロジェクトにメンバーを追加"""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # オーナーまたは管理者権限をチェック
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id,
        ProjectMember.role.in_(["owner", "admin"])
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    # 既存メンバーかチェック
    existing_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == member_data.user_id
    ).first()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member"
        )
    
    # ユーザーが存在するかチェック
    user = db.query(User).filter(User.id == member_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db_member = ProjectMember(
        project_id=project_id,
        user_id=member_data.user_id,
        role=member_data.role
    )
    
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    
    return db_member

@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
async def get_project_members(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """プロジェクトのメンバー一覧を取得"""
    # ユーザーがプロジェクトメンバーかチェック
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    members = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id
    ).all()
    
    return members