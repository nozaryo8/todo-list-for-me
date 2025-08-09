from datetime import datetime

from sqlalchemy import create_engine, Column, String, Integer, Text, Boolean, ForeignKey, DECIMAL, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from core.config import get_env

# Engine の作成
Engine = create_engine(
    get_env().database_url,
    encoding="utf-8",
    echo=False
)

BaseModel = declarative_base()

class User(BaseModel):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    login_id = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(Text, nullable=False)
    avatar_url = Column(String(500))
    timezone = Column(String(50), default='Asia/Tokyo')
    notification_enabled = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)

    # リレーション
    owned_projects = relationship("Project", back_populates="owner")
    project_memberships = relationship("ProjectMember", back_populates="user")
    assigned_tasks = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")
    created_tasks = relationship("Task", foreign_keys="Task.creator_id", back_populates="creator")
    comments = relationship("TaskComment", back_populates="user")
    attachments = relationship("TaskAttachment", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    created_tags = relationship("Tag", back_populates="created_by_user")


class Project(BaseModel):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    color = Column(String(7), default='#3498db')
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)

    # リレーション
    owner = relationship("User", back_populates="owned_projects")
    members = relationship("ProjectMember", back_populates="project")
    tasks = relationship("Task", back_populates="project")
    tags = relationship("Tag", back_populates="project")


class ProjectMember(BaseModel):
    __tablename__ = 'project_members'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), default='member')  # owner, admin, member, viewer
    joined_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)

    __table_args__ = (UniqueConstraint('project_id', 'user_id'),)

    # リレーション
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")


class Task(BaseModel):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)  # マークダウン対応
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    parent_task_id = Column(Integer, ForeignKey('tasks.id'))  # サブタスク用
    assignee_id = Column(Integer, ForeignKey('users.id'))
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    priority = Column(String(10), default='medium')  # low, medium, high, urgent
    status = Column(String(20), default='todo')  # todo, in_progress, review, done, cancelled
    start_date = Column(TIMESTAMP(timezone=True))
    due_date = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    estimated_hours = Column(DECIMAL(5, 2))
    actual_hours = Column(DECIMAL(5, 2))
    position = Column(Integer)  # 表示順序用
    is_archived = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)

    # リレーション
    project = relationship("Project", back_populates="tasks")
    parent_task = relationship("Task", remote_side=[id])
    subtasks = relationship("Task")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_tasks")
    comments = relationship("TaskComment", back_populates="task")
    attachments = relationship("TaskAttachment", back_populates="task")
    tags = relationship("TaskTag", back_populates="task")


class Tag(BaseModel):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    color = Column(String(7), default='#95a5a6')
    project_id = Column(Integer, ForeignKey('projects.id'))  # プロジェクト固有またはグローバル
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)

    __table_args__ = (UniqueConstraint('name', 'project_id'),)

    # リレーション
    project = relationship("Project", back_populates="tags")
    created_by_user = relationship("User", back_populates="created_tags")
    tasks = relationship("TaskTag", back_populates="tag")


class TaskTag(BaseModel):
    __tablename__ = 'task_tags'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    tag_id = Column(Integer, ForeignKey('tags.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)

    __table_args__ = (UniqueConstraint('task_id', 'tag_id'),)

    # リレーション
    task = relationship("Task", back_populates="tags")
    tag = relationship("Tag", back_populates="tasks")


class TaskComment(BaseModel):
    __tablename__ = 'task_comments'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)  # マークダウン対応
    is_edited = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)

    # リレーション
    task = relationship("Task", back_populates="comments")
    user = relationship("User", back_populates="comments")


class TaskAttachment(BaseModel):
    __tablename__ = 'task_attachments'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # BIGINT → Integer (SQLAlchemyでは自動でBIGINTになる)
    mime_type = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)

    # リレーション
    task = relationship("Task", back_populates="attachments")
    user = relationship("User", back_populates="attachments")


class Notification(BaseModel):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'))
    type = Column(String(50), nullable=False)  # task_due, task_assigned, comment_added, etc.
    title = Column(String(200), nullable=False)
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    scheduled_at = Column(TIMESTAMP(timezone=True))  # 予約通知用
    sent_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)

    # リレーション
    user = relationship("User", back_populates="notifications")
    task = relationship("Task")


class ActivityLog(BaseModel):
    __tablename__ = 'activity_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'))
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'))
    action = Column(String(50), nullable=False)  # created, updated, completed, etc.
    details = Column(JSONB)  # 変更内容の詳細
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now, nullable=False)

    # リレーション
    user = relationship("User")
    task = relationship("Task")
    project = relationship("Project")