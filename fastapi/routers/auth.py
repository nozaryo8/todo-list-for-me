from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from auth import authenticate_user, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
from schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from migration.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """新規ユーザー登録"""
    # 既存ユーザーチェック
    existing_user = db.query(User).filter(
        (User.login_id == user_data.login_id) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this login_id or email already exists"
        )
    
    # パスワードをハッシュ化
    hashed_password = get_password_hash(user_data.password)
    
    # ユーザー作成
    db_user = User(
        name=user_data.name,
        login_id=user_data.login_id,
        email=user_data.email,
        password=hashed_password,
        timezone=user_data.timezone,
        notification_enabled=user_data.notification_enabled
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """ユーザーログイン"""
    user = authenticate_user(db, login_data.login_id, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login_id or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}