from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from core.config import get_env

# データベースエンジンの作成
engine = create_engine(
    get_env().database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600
)

# セッションファクトリーの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """データベースセッションを取得する依存性関数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()