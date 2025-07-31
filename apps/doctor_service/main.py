"""
main.py - doctor_service FastAPI 애플리케이션 메인 진입점
의사 정보 관리 마이크로서비스
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from contextlib import asynccontextmanager

from database import create_tables, test_connection
from routes import router as doctor_router
# 모델들을 임포트해서 Base.metadata에 등록
from models import Doctor, DoctorSpecialization, DoctorStatistics, DoctorFees, DoctorSchedule


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 라이프사이클 관리
    - 시작 시: DB 연결 테스트, 테이블 생성
    - 종료 시: 정리 작업
    """
    logger.info(" Doctor Service 시작 중...")
    
    logger.info(" 데이터베이스 연결 테스트 중...")
    if test_connection():
        logger.info(" 데이터베이스 연결 성공!")
        
        # 테이블 생성
        logger.info(" 데이터베이스 테이블 생성/확인 중...")
        try:
            create_tables()
            logger.info(" 테이블 생성/확인 완료!")
        except Exception as e:
            logger.error(f" 테이블 생성 실패: {e}")
            raise
    else:
        logger.error(" 데이터베이스 연결 실패!")
        raise Exception("데이터베이스 연결에 실패했습니다.")
    
    logger.info(" Doctor Service 준비 완료!")
    
    yield  # 애플리케이션 실행
    
    #  애플리케이션 종료
    logger.info(" Doctor Service 종료 중...")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Doctor Service API",
    description="""
    **의사 정보 관리 서비스**
    
    ## 주요 기능
    - ️**의사 기본정보** 관리 (CRUD)
    -  **전문과목** 관리
    -  **통계정보** 관리 (평점, 리뷰 수, 환자 수) -추후 업데이트 예정
    -  **진료비** 정보 관리 - 추후 업데이트 예정
    -  **근무일정** 관리
    -  **검색** 기능 (이름, 전문과목)
    
    ## 데이터베이스
    - PostgreSQL의 `doctor_db` 사용
    - 5개 테이블: doctors, doctor_specializations, doctor_statistics, doctor_fees, doctor_schedules
    
    ## 포트
    - 8007 (Docker 내부: 8000)
    """,
    version="1.0.0",
    contact={
        "name": "남두현(kndh2914@gmail.com)"
    },
    lifespan=lifespan  # 라이프사이클 관리 함수 등록
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
app.include_router(doctor_router)


# =============================================================================
# 헬스 체크 및 기본 엔드포인트
# =============================================================================

@app.get("/", tags=["Health Check"])
def root():
    """
    서비스 상태 확인 (루트 엔드포인트)
    """
    return {
        "service": "Doctor Service",
        "status": "healthy",
        "version": "1.0.0",
        "message": "의사 정보 관리 서비스가 정상적으로 작동 중입니다!️"
    }


@app.get("/health", tags=["Health Check"])
def health_check():
    """
    상세 헬스 체크
    - 데이터베이스 연결 상태 확인
    """
    try:
        # 데이터베이스 연결 테스트
        db_status = "connected" if test_connection() else "disconnected"
        
        return {
            "service": "Doctor Service",
            "status": "healthy",
            "database": db_status,
            "timestamp": "2025-01-30T00:00:00Z",
            "components": {
                "api": "healthy",
                "database": db_status,
                "models": "loaded",
                "routes": "registered"
            }
        }
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "service": "Doctor Service",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2025-01-30T00:00:00Z"
            }
        )


@app.get("/info", tags=["Service Info"])
def service_info():
    """
    서비스 정보 조회
    """
    return {
        "service_name": "Doctor Service",
        "version": "1.0.0",
        "description": "의사 정보 관리 서비스",
        "author": "Backend Team",
        "database": "PostgreSQL (doctor_db)",
        "port": 8007,
        "endpoints": {
            "doctors": "/doctors/",
            "specializations": "/doctors/{doctor_id}/specializations",
            "statistics": "/doctors/{doctor_id}/statistics",
            "fees": "/doctors/{doctor_id}/fees",
            "schedules": "/doctors/{doctor_id}/schedules",
            "search": {
                "by_name": "/doctors/search/by-name/{doctor_name}",
                "by_specialty": "/doctors/search/by-specialty/{specialty_name}"
            }
        },
        "docs": "/docs",
        "redoc": "/redoc"
    }


# =============================================================================
# 전역 예외 처리
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    HTTP 예외 처리기
    - 일관된 에러 응답 형식 제공
    """
    logger.error(f"HTTP 에러 발생: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
            "service": "Doctor Service"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """
    일반 예외 처리기
    - 예상치 못한 에러 처리
    """
    logger.error(f"예상치 못한 에러 발생: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "내부 서버 오류가 발생했습니다.",
            "detail": str(exc),
            "service": "Doctor Service"
        }
    )


