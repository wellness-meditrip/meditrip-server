"""
main.py - Reservation Service FastAPI Application
예약 관리 시스템의 메인 애플리케이션
"""

import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import create_tables, test_connection
from routes import router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 이벤트"""
    # 시작 시 실행
    logger.info("🚀 Reservation Service 시작")
    
    # 데이터베이스 연결 테스트
    if test_connection():
        logger.info("✅ 데이터베이스 연결 확인됨")
        
        # 테이블 생성
        try:
            create_tables()
            logger.info("✅ 데이터베이스 테이블 준비 완료")
        except Exception as e:
            logger.error(f"❌ 테이블 생성 실패: {e}")
    else:
        logger.error("❌ 데이터베이스 연결 실패")
    
    yield
    
    # 종료 시 실행
    logger.info("🛑 Reservation Service 종료")

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Reservation Service API",
    description="""
    🏥 **예약 관리 시스템 API**
    
    의료 관광 플랫폼의 예약 관리를 위한 RESTful API 서비스입니다.
    
    ## 주요 기능
    
    ### 📅 예약 관리
    - **예약 생성**: 병원 운영시간 검증 포함
    - **예약 조회**: 상세 정보 및 첨부 이미지
    - **예약 수정**: 상태 변경 및 정보 업데이트
    - **예약 취소**: 안전한 취소 처리
    
    ### 🔍 검색 및 필터링
    - **다중 조건 검색**: 병원, 사용자, 의사, 상태별
    - **날짜 범위 검색**: 기간별 예약 조회
    - **통역 언어 필터**: 언어별 예약 분류
    
    ### ⏰ 예약 가능 시간
    - **운영시간 조회**: Hospital Service 연동
    - **시간대 확인**: 30분 간격 예약 가능 시간
    - **중복 방지**: 기존 예약과의 충돌 검사
    
    ### 🖼️ 이미지 관리
    - **Base64 저장**: 안전한 이미지 저장
    - **메타데이터 추출**: 크기, 형식 자동 인식
    - **다중 첨부**: 최대 10장 이미지 지원
    
    ## 데이터 검증
    
    - ✅ 이메일 및 전화번호 형식 검증
    - ✅ 예약 날짜 미래일 검증
    - ✅ 병원 운영시간 검증
    - ✅ 이미지 개수 및 형식 검증
    
    ## 서비스 연동
    
    - 🏥 **Hospital Service**: 운영시간 조회
    - 👨‍⚕️ **Doctor Service**: 의사 정보 (선택)
    - 👤 **Auth Service**: 사용자 인증
    
    ---
    
    **Port**: 8006 | **Database**: reservation_db
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "https://meditrip-web-eta.vercel.app",
        "https://meditrip-web-eta.vercel.app/",
        "http://localhost:3000",
        "http://localhost:3001"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(router, tags=["Reservations"])

# 루트 엔드포인트
@app.get("/", tags=["Root"])
async def root():
    """서비스 상태 확인"""
    return {
        "service": "Reservation Service",
        "status": "healthy",
        "version": "1.0.0",
        "message": "🏥 예약 관리 시스템이 정상적으로 운영 중입니다.",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "reservations": "/reservations",
            "available_times": "/available-times/{hospital_id}"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        reload=True,
        log_level="info"
    )