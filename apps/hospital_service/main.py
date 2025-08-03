"""
main.py - Hospital Service Main Application
병원 관리 시스템의 FastAPI 애플리케이션 진입점
"""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 로컬 모듈 import
from models import Base
from database import engine, check_database_connection, create_tables
from routes import router as hospital_router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 시작/종료 시 실행할 작업들
    """
    # 시작 시 실행
    logger.info("🏥 Hospital Service 시작 중...")
    
    # 데이터베이스 연결 확인
    if not check_database_connection():
        logger.error("❌ 데이터베이스 연결 실패")
        raise Exception("데이터베이스 연결에 실패했습니다.")
    
    # 테이블 생성
    try:
        create_tables()
        logger.info("✅ Hospital Service 준비 완료!")
    except Exception as e:
        logger.error(f"❌ 테이블 생성 실패: {e}")
        raise e
    
    yield
    
    # 종료 시 실행
    logger.info("🏥 Hospital Service 종료 중...")

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Hospital Service API",
    description="""
    **병원 정보 관리 서비스**
    
    ## 주요 기능
    - **병원 정보 관리** (등록, 조회, 수정, 삭제)
    - **병원 세부 정보** (운영시간, 주차장, 진료과목, 이미지)
    - **병원 검색** (키워드, 지역, 진료과목별 검색)
    - **다국어 지원** (한국어, 영어, 일본어)
    
    ## 데이터베이스
    - PostgreSQL의 `hospital_db` 사용
    - 2개 테이블: hospitals, hospital_details
    
    ## 포트
    - 8004 (Docker 내부: 8000)
    """,
    version="1.0.0",
    contact={
        "name": "이규연",
    },
    lifespan=lifespan
)

# CORS 미들웨어 추가 (프론트엔드와의 통신을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 출처 허용
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# 라우터 등록
app.include_router(hospital_router)

# 전역 예외 처리기
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)}
    )

# =============================================================================
# 헬스 체크 및 기본 엔드포인트
# =============================================================================

@app.get("/", tags=["Health Check"])
def root():
    """
    서비스 상태 확인 (루트 엔드포인트)
    """
    return {
        "service": "Hospital Service",
        "status": "healthy",
        "version": "1.0.0",
        "message": "병원 정보 관리 서비스가 정상적으로 작동 중입니다! 🏥"
    }

@app.get("/health", tags=["Health Check"])
def health_check():
    """
    상세 헬스 체크
    """
    try:
        db_status = check_database_connection()
        
        return {
            "service": "Hospital Service",
            "status": "healthy" if db_status else "unhealthy",
            "database": "connected" if db_status else "disconnected",
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "service": "Hospital Service",
                "status": "unhealthy",
                "error": str(e)
            }
        )

# =============================================================================
# 개발용 디버그 엔드포인트
# =============================================================================

@app.get("/debug/tables", tags=["Debug"])
def debug_tables():
    """
    데이터베이스 테이블 정보 확인 (개발용)
    """
    try:
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        table_info = {}
        for table in tables:
            columns = inspector.get_columns(table)
            table_info[table] = [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"]
                }
                for col in columns
            ]
        
        return {
            "database": "hospital_db",
            "tables": table_info,
            "total_tables": len(tables)
        }
        
    except Exception as e:
        logger.error(f"❌ Debug tables failed: {e}")
        raise HTTPException(status_code=500, detail=f"테이블 정보 조회 실패: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )