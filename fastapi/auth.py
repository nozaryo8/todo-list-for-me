from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from migration.models import User

# パスワード暗号化設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT設定
SECRET_KEY = "your-secret-key-here"  # 本番環境では環境変数から取得
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# HTTP Bearer トークン設定
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """パスワードを検証する"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """パスワードをハッシュ化する"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """アクセストークンを作成する"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """トークンを検証してユーザーIDを返す"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None

def authenticate_user(db: Session, login_id: str, password: str) -> Optional[User]:
    """ユーザーを認証する"""
    user = db.query(User).filter(User.login_id == login_id).first()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """現在のユーザーを取得する依存性関数"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user_id = verify_token(credentials.credentials)
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    return user