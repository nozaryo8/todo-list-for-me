from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user, get_password_hash
from schemas import UserResponse, UserUpdate
from migration.models import User

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """現在のユーザー情報を取得"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """現在のユーザー情報を更新"""
    
    # emailの重複チェック
    if user_update.email:
        existing_user = db.query(User).filter(
            User.email == user_update.email,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
    
    # 更新データを適用
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """指定されたユーザー情報を取得"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user