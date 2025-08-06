"""
main.py - Review Service FastAPI Application
리뷰 관리 시스템의 메인 애플리케이션
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import traceback

from database import create_tables, check_database_connection
from routes import router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Wellness MediTrip - Review Service",
    description="병원 리뷰 관리 시스템 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
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

# 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # 요청 로깅
    logger.info(f"📨 {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 응답 로깅
        logger.info(f"✅ {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"❌ {request.method} {request.url.path} - Error ({process_time:.3f}s): {str(e)}")
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "내부 서버 오류가 발생했습니다.",
                "error": str(e) if app.debug else "Internal Server Error"
            }
        )

# 라우터 등록
app.include_router(router, prefix="/api/v1")

# 전역 예외 처리
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ 전역 예외 발생: {str(exc)}")
    logger.error(f"❌ 스택 트레이스: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "서버 내부 오류가 발생했습니다.",
            "error": str(exc) if app.debug else "Internal Server Error"
        }
    )

# 애플리케이션 시작 시 실행
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 초기화"""
    logger.info("🚀 Review Service 시작 중...")
    
    try:
        # 데이터베이스 연결 확인
        if not check_database_connection():
            raise Exception("데이터베이스 연결 실패")
        
        # 데이터베이스 테이블 생성
        create_tables()
        
        logger.info("✅ Review Service 시작 완료!")
        logger.info("📋 API 문서: http://localhost:8000/docs")
        
    except Exception as e:
        logger.error(f"❌ Review Service 시작 실패: {e}")
        raise

# 애플리케이션 종료 시 실행
@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 정리"""
    logger.info("🔄 Review Service 종료 중...")
    logger.info("👋 Review Service 종료 완료!")

# 루트 엔드포인트
@app.get("/")
async def root():
    """서비스 정보 조회"""
    return {
        "service": "Wellness MediTrip - Review Service",
        "version": "1.0.0",
        "status": "running",
        "description": "병원 리뷰 관리 시스템",
        "docs_url": "/docs",
        "health_check": "/api/v1/health"
    }

# 서비스 상태 확인
@app.get("/health")
async def health_check():
    """간단한 헬스 체크"""
    return {
        "status": "healthy",
        "service": "review-service",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🔧 개발 모드로 Review Service 실행")
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