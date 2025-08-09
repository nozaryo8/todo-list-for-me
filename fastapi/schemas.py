from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# User関連のスキーマ
class UserBase(BaseModel):
    name: str
    login_id: str
    email: EmailStr
    timezone: str = "Asia/Tokyo"
    notification_enabled: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    notification_enabled: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Auth関連のスキーマ
class LoginRequest(BaseModel):
    login_id: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Project関連のスキーマ
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#3498db"

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_archived: Optional[bool] = None

class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ProjectMember関連のスキーマ
class ProjectMemberBase(BaseModel):
    user_id: int
    role: str = "member"

class ProjectMemberCreate(ProjectMemberBase):
    pass

class ProjectMemberUpdate(BaseModel):
    role: Optional[str] = None

class ProjectMemberResponse(ProjectMemberBase):
    id: int
    project_id: int
    joined_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        orm_mode = True


# Task関連のスキーマ
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    priority: str = "medium"
    status: str = "todo"
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    position: Optional[int] = None

class TaskCreate(TaskBase):
    project_id: int
    parent_task_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    position: Optional[int] = None
    is_archived: Optional[bool] = None

class TaskResponse(TaskBase):
    id: int
    project_id: int
    parent_task_id: Optional[int] = None
    creator_id: int
    completed_at: Optional[datetime] = None
    actual_hours: Optional[float] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    
    # リレーション
    assignee: Optional[UserResponse] = None
    creator: Optional[UserResponse] = None

    class Config:
        orm_mode = True


# Tag関連のスキーマ
class TagBase(BaseModel):
    name: str
    color: str = "#95a5a6"

class TagCreate(TagBase):
    project_id: Optional[int] = None

class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

class TagResponse(TagBase):
    id: int
    project_id: Optional[int] = None
    created_by: int
    created_at: datetime

    class Config:
        orm_mode = True


# TaskComment関連のスキーマ
class TaskCommentBase(BaseModel):
    content: str

class TaskCommentCreate(TaskCommentBase):
    task_id: int

class TaskCommentUpdate(BaseModel):
    content: Optional[str] = None

class TaskCommentResponse(TaskCommentBase):
    id: int
    task_id: int
    user_id: int
    is_edited: bool
    created_at: datetime
    updated_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        orm_mode = True


# TaskAttachment関連のスキーマ
class TaskAttachmentResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: Optional[str] = None
    created_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        orm_mode = True


# Notification関連のスキーマ
class NotificationBase(BaseModel):
    type: str
    title: str
    message: Optional[str] = None

class NotificationCreate(NotificationBase):
    user_id: int
    task_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    task_id: Optional[int] = None
    is_read: bool
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True


# レスポンス用のページネーション
class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    size: int
    pages: int


# TaskResponseの前方参照はPydantic v1では自動解決される