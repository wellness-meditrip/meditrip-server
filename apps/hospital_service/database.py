"""
database.py - Hospital Service Database Connection
병원 관리 시스템의 데이터베이스 연결 설정
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from models import Base
import logging

logger = logging.getLogger(__name__)

# 환경변수에서 데이터베이스 연결 정보 가져오기 (Docker 환경변수 사용)
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
HOSPITAL_DB = os.getenv("HOSPITAL_DB")

# 환경변수 디버깅
logger.info(f"🔍 환경변수 확인: USER={POSTGRES_USER}, HOST={POSTGRES_HOST}, PORT={POSTGRES_PORT}, DB={HOSPITAL_DB}")

# PostgreSQL 연결 URL 구성
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{HOSPITAL_DB}"

logger.info(f"🔗 Hospital Service DB 연결: {POSTGRES_USER}@{POSTGRES_HOST}:{POSTGRES_PORT}/{HOSPITAL_DB}")

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # 커넥션 풀 크기
    max_overflow=20,        # 최대 오버플로 커넥션
    pool_pre_ping=True,     # 연결 유효성 검사
    pool_recycle=300,       # 5분마다 커넥션 재활용
    echo=False              # SQL 쿼리 로깅 (개발 시에만 True)
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_database():
    """
    데이터베이스 세션 의존성 함수
    FastAPI에서 Dependency Injection으로 사용
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"❌ Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_tables():
    """
    데이터베이스 테이블 생성
    애플리케이션 시작 시 호출
    """
    try:
        logger.info("🏗️ Hospital Service 데이터베이스 테이블 생성 중...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Hospital Service 데이터베이스 테이블 생성 완료!")
    except Exception as e:
        logger.error(f"❌ 테이블 생성 실패: {e}")
        raise

def check_database_connection():
    """
    데이터베이스 연결 상태 확인
    """
    try:
        with engine.connect() as connection:
            from sqlalchemy import text
            connection.execute(text("SELECT 1"))
            logger.info("✅ Hospital Service 데이터베이스 연결 성공!")
            return True
    except Exception as e:
        logger.error(f"❌ Hospital Service 데이터베이스 연결 실패: {e}")
        return False