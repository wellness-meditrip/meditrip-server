"""
Account Service Database Configuration
PostgreSQL 데이터베이스 연결 및 설정
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from models import Base

logger = logging.getLogger(__name__)

# 데이터베이스 URL 설정
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://meditrip_user:meditrip_password@localhost:5432/account_db"
)

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # 개발 시에는 True로 설정하여 SQL 쿼리 로그 확인
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

def get_database():
    """
    데이터베이스 세션 의존성 주입용 함수
    FastAPI Depends에서 사용
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"데이터베이스 세션 오류: {e}")
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
        logger.info("데이터베이스 테이블 생성 중...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 데이터베이스 테이블 생성 완료")
        
        # 테이블 생성 확인
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('account_deletion_logs', 'account_recovery_requests', 'profile_images', 'image_upload_history')
            """))
            
            tables = [row[0] for row in result]
            logger.info(f"생성된 테이블: {tables}")
            
    except SQLAlchemyError as e:
        logger.error(f"❌ 데이터베이스 테이블 생성 실패: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {e}")
        raise

def check_database_connection():
    """
    데이터베이스 연결 상태 확인
    """
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            logger.info("✅ 데이터베이스 연결 성공")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 중 예상치 못한 오류: {e}")
        return False

def get_database_info():
    """
    데이터베이스 정보 조회
    디버깅 및 모니터링용
    """
    try:
        with engine.connect() as connection:
            # PostgreSQL 버전 확인
            version_result = connection.execute(text("SELECT version()"))
            version = version_result.fetchone()[0]
            
            # 현재 데이터베이스명 확인
            db_result = connection.execute(text("SELECT current_database()"))
            database_name = db_result.fetchone()[0]
            
            # 테이블 개수 확인
            table_result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = table_result.fetchone()[0]
            
            return {
                "version": version,
                "database_name": database_name,
                "table_count": table_count,
                "url": DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('://')[1], '***')  # 비밀번호 마스킹
            }
            
    except Exception as e:
        logger.error(f"데이터베이스 정보 조회 실패: {e}")
        return {"error": str(e)}

def cleanup_old_records():
    """
    오래된 레코드 정리 (선택사항)
    - 만료된 복구 요청
    - 오래된 업로드 히스토리 (90일 이상)
    """
    try:
        with engine.connect() as connection:
            # 만료된 복구 요청 정리
            expired_recovery = connection.execute(text("""
                UPDATE account_recovery_requests 
                SET status = 'expired' 
                WHERE expires_at < NOW() AND status = 'pending'
            """))
            
            # 90일 이상 된 업로드 히스토리 삭제
            old_history = connection.execute(text("""
                DELETE FROM image_upload_history 
                WHERE created_at < NOW() - INTERVAL '90 days'
            """))
            
            connection.commit()
            
            logger.info(f"정리 완료: 만료된 복구요청 {expired_recovery.rowcount}개, 오래된 히스토리 {old_history.rowcount}개")
            
    except Exception as e:
        logger.error(f"레코드 정리 중 오류: {e}")

# 데이터베이스 초기화 함수
def initialize_database():
    """
    데이터베이스 초기화
    애플리케이션 시작 시 호출
    """
    logger.info("Account Service 데이터베이스 초기화 시작...")
    
    # 1. 연결 확인
    if not check_database_connection():
        raise Exception("데이터베이스 연결 실패")
    
    # 2. 테이블 생성
    create_tables()
    
    # 3. 정보 출력
    db_info = get_database_info()
    logger.info(f"데이터베이스 정보: {db_info}")
    
    logger.info("✅ Account Service 데이터베이스 초기화 완료!")

if __name__ == "__main__":
    # 직접 실행 시 데이터베이스 초기화
    logging.basicConfig(level=logging.INFO)
    initialize_database()