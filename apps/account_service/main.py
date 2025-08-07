"""
main.py - account_service FastAPI 애플리케이션 메인 진입점
계정 관리 및 프로필 이미지 관리 마이크로서비스
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from contextlib import asynccontextmanager

from database import create_tables, check_database_connection, get_database_info
from routes import router as account_router
# 모델들을 임포트해서 Base.metadata에 등록
from models import AccountDeletionLog, AccountRecoveryRequest, ProfileImage, ImageUploadHistory


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
    logger.info("🚀 Account Service 시작 중...")
    
    logger.info("🔗 데이터베이스 연결 테스트 중...")
    if check_database_connection():
        logger.info("✅ 데이터베이스 연결 성공!")
        
        # 테이블 생성
        logger.info("🗄️ 데이터베이스 테이블 생성/확인 중...")
        try:
            create_tables()
            logger.info("✅ 테이블 생성/확인 완료!")
        except Exception as e:
            logger.error(f"❌ 테이블 생성 실패: {e}")
            raise
    else:
        logger.error("❌ 데이터베이스 연결 실패!")
        raise Exception("데이터베이스 연결에 실패했습니다.")
    
    logger.info("✅ Account Service 준비 완료!")
    
    yield  # 애플리케이션 실행
    
    # 🔄 애플리케이션 종료
    logger.info("🔄 Account Service 종료 중...")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Account Service API",
    description="""
    **계정 관리 및 프로필 이미지 서비스**
    
    ## 주요 기능
    - 🗑️ **계정 삭제** 관리 (30일 복구 기간)
    - 🔄 **계정 복구** 요청 처리
    - 🖼️ **프로필 이미지** 업로드 (Base64 지원)
    - 📊 **업로드 히스토리** 추적
    - 📈 **통계** 정보 제공
    
    ## 데이터베이스
    - PostgreSQL의 `account_db` 사용
    - 4개 테이블: account_deletion_logs, account_recovery_requests, profile_images, image_upload_history
    
    ## 포트
    - 8002 (Docker 내부: 8000)
    """,
    version="1.0.0",
    contact={
        "name": "Backend Team"
    },
    lifespan=lifespan  # 라이프사이클 관리 함수 등록
)

# CORS 미들웨어 추가 (프론트엔드와의 통신을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "https://localhost:3000",
        "https://localhost:3001",
        "https://wellness-meditrip-frontend.vercel.app",
        "https://wellness-meditrip-backend.eastus2.cloudapp.azure.com",
        "*"  # 개발 환경을 위해 모든 origin 허용
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(account_router, prefix="/api/v1")


# =============================================================================
# 헬스 체크 및 기본 엔드포인트
# =============================================================================

@app.get("/", tags=["Health Check"])
def root():
    """
    서비스 상태 확인 (루트 엔드포인트)
    """
    return {
        "service": "Account Service",
        "status": "healthy",
        "version": "1.0.0",
        "message": "계정 관리 및 프로필 이미지 서비스가 정상적으로 작동 중입니다!🛡️"
    }


@app.get("/health", tags=["Health Check"])
def health_check():
    """
    상세 헬스 체크
    - 데이터베이스 연결 상태 확인
    """
    try:
        # 데이터베이스 연결 테스트
        db_status = "connected" if check_database_connection() else "disconnected"
        
        return {
            "service": "Account Service",
            "status": "healthy",
            "database": db_status,
            "timestamp": "2025-08-07T00:00:00Z",
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
                "service": "Account Service",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2025-08-07T00:00:00Z"
            }
        )


@app.get("/info", tags=["Service Info"])
def service_info():
    """
    서비스 정보 조회
    """
    return {
        "service_name": "Account Service",
        "version": "1.0.0",
        "description": "계정 관리 및 프로필 이미지 서비스",
        "author": "Backend Team",
        "database": "PostgreSQL (account_db)",
        "port": 8002,
        "endpoints": {
            "delete_account": "POST /api/v1/delete-account",
            "recover_account": "POST /api/v1/recover-account",
            "profile_images": {
                "upload": "POST /api/v1/profile-image",
                "update": "PUT /api/v1/profile-image/{user_id}",
                "get": "GET /api/v1/profile-image/{user_id}",
                "delete": "DELETE /api/v1/profile-image/{user_id}"
            },
            "statistics": {
                "deletions": "GET /api/v1/stats/deletions",
                "images": "GET /api/v1/stats/images"
            },
            "health": "GET /api/v1/health"
        },
        "features": {
            "account_deletion": "30일 복구 기간",
            "profile_images": "Base64 지원, 최대 10MB",
            "supported_formats": ["jpg", "jpeg", "png", "webp"],
            "upload_history": "완전한 이력 추적"
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
            "service": "Account Service"
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
            "service": "Account Service"
        }
    )


if __name__ == "__main__":
    logger.info("🔧 개발 모드로 Account Service 실행")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        # 50MB 제한 설정
        limit_max_requests=1000,
        timeout_keep_alive=60
    )