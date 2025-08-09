"""
database.py - Reservation Service Database Configuration
예약 관리 시스템의 데이터베이스 연결 및 설정
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수에서 데이터베이스 설정 로드
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/reservation_db")

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # SQL 로깅 비활성화 (개발 시에는 True로 설정 가능)
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_database():
    """
    데이터베이스 세션 의존성
    FastAPI의 Depends에서 사용
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """
    데이터베이스 테이블 생성
    애플리케이션 시작 시 호출
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Reservation service 데이터베이스 테이블이 성공적으로 생성되었습니다.")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 테이블 생성 실패: {e}")
        raise

def test_connection():
    """
    데이터베이스 연결 테스트
    """
    try:
        db = SessionLocal()
        # 간단한 쿼리 실행으로 연결 확인
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Reservation service 데이터베이스 연결이 성공적으로 확인되었습니다.")
        return True
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        return False

if __name__ == "__main__":
    # 직접 실행 시 연결 테스트 및 테이블 생성
    test_connection()
    create_tables()