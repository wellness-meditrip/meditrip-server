"""
database.py - PostgreSQL 데이터베이스 연결 설정
SQLAlchemy를 사용하여 doctor_db와 연결하고 세션 관리
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator

# Docker에서는 환경변수가 이미 설정됨 (docker-compose.yml에서)
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD") 
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
DOCTOR_DB = os.getenv("DOCTOR_DB")

if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, DOCTOR_DB]):
    print("❌ 환경변수 상태:")
    print(f"  POSTGRES_USER: {POSTGRES_USER}")
    print(f"  POSTGRES_PASSWORD: {'***' if POSTGRES_PASSWORD else None}")
    print(f"  POSTGRES_HOST: {POSTGRES_HOST}")
    print(f"  POSTGRES_PORT: {POSTGRES_PORT}")
    print(f"  DOCTOR_DB: {DOCTOR_DB}")
    raise ValueError("❌ 환경변수가 설정되지 않았습니다!")

# PostgreSQL 연결 URL 생성
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{DOCTOR_DB}"

print(f"🔗 데이터베이스 연결 URL: {DATABASE_URL}")

# SQLAlchemy 엔진 생성
# echo=True: SQL 쿼리를 콘솔에 출력 (개발 중 디버깅용)
# pool_pre_ping=True: 연결 상태를 자동으로 확인
engine = create_engine(
    DATABASE_URL,
    echo=True,  # 개발환경에서 SQL 로그 확인용
    pool_pre_ping=True,  # 연결 끊김 방지
    pool_recycle=300,  # 5분마다 연결 갱신
)

# 세션 팩토리 생성
# autocommit=False: 수동으로 commit 해야 함 (트랜잭션 안전성)
# autoflush=False: 수동으로 flush 해야 함
# bind=engine: 위에서 생성한 엔진과 연결
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base 클래스 (models.py에서도 사용)
Base = declarative_base()


def create_tables():
    """
    데이터베이스 테이블 생성 함수
    models.py에서 정의한 모든 테이블을 실제 DB에 생성
    """
    print("📋 데이터베이스 테이블 생성 중...")
    print(f"등록된 테이블들: {list(Base.metadata.tables.keys())}")
    Base.metadata.create_all(bind=engine)
    print("✅ 테이블 생성 완료!")


def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션 제공 함수 (Dependency Injection용)
    FastAPI의 Depends()와 함께 사용
    
    사용 예시:
    @app.get("/doctors")
    def get_doctors(db: Session = Depends(get_db)):
        return db.query(Doctor).all()
    """
    db = SessionLocal()  # 새로운 세션 생성
    try:
        print("🔓 데이터베이스 세션 시작")
        yield db  # 세션을 API 함수에 전달
    except Exception as e:
        print(f"❌ 데이터베이스 오류: {e}")
        db.rollback()  # 오류 시 롤백
        raise
    finally:
        print("🔒 데이터베이스 세션 종료")
        db.close()  # 세션 종료


def test_connection():
    """
    데이터베이스 연결 테스트 함수
    서비스 시작 시 DB 연결 상태 확인용
    """
    try:
        db = SessionLocal()
        # 간단한 쿼리로 연결 테스트 (SQLAlchemy 2.0 방식)
        result = db.execute(text("SELECT 1 as test"))
        test_value = result.fetchone()
        db.close()
        
        if test_value and test_value[0] == 1:
            print("✅ 데이터베이스 연결 성공!")
            return True
        else:
            print("❌ 데이터베이스 연결 실패: 응답이 올바르지 않음")
            return False
            
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return False


# 모듈 임포트 시 자동으로 연결 테스트 실행
if __name__ == "__main__":
    print("🚀 데이터베이스 연결 테스트 시작...")
    if test_connection():
        print("🎉 데이터베이스 준비 완료!")
        create_tables()
    else:
        print("💥 데이터베이스 연결 실패!")