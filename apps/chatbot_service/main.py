"""
main.py - Chatbot Service FastAPI 애플리케이션
RAG 기반 의료 상담 챗봇 서비스
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from schemas import ChatRequest, ChatResponse, HealthResponse, ErrorResponse
from rag_engine import RAGEngine

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# RAG 엔진 인스턴스
rag_engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 라이프사이클 관리"""
    global rag_engine
    
    # 🚀 서비스 시작
    logger.info("🚀 Chatbot Service 시작 중...")
    
    try:
        # RAG 엔진 초기화
        logger.info("🤖 RAG 엔진 초기화 중...")
        rag_engine = RAGEngine()
        
        # 문서 로딩
        logger.info("📄 의료 문서 로딩 중...")
        success = await rag_engine.initialize_documents()
        
        if success:
            logger.info("🎉 Chatbot Service 준비 완료!")
        else:
            logger.warning("⚠️ 문서 로딩 실패, 제한된 기능으로 시작")
            
    except Exception as e:
        logger.error(f"❌ 서비스 초기화 실패: {e}")
        # 서비스는 계속 시작하되, 에러 응답 준비
        rag_engine = None
    
    yield  # 애플리케이션 실행
    
    # 🛑 서비스 종료
    logger.info("👋 Chatbot Service 종료 중...")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Chatbot Service API",
    description="""
    **의료 상담 챗봇 서비스**
    
    ## 주요 기능
    - **RAG 기반 질답**: 의료 문서 기반 정확한 답변
    -  **PDF 문서 활용**: 400페이지 의료 가이드라인 기반
    -  **유사도 검색**: Qdrant 벡터 데이터베이스 활용
    -  **GPT-4o-mini 생성**: 
    
    ## 기술 스택
    - **Vector DB**: Qdrant
    - **LLM**: OpenAI GPT-4o-mini
    - **Framework**: LangChain
    - **Embeddings**: OpenAI Ada-002
    
    ## 포트
    - 8009 (Docker 내부: 8000)
    """,
    version="1.0.0",
    contact={
        "name": "남두현(kndh2914@gmail.com)",
    },
    lifespan=lifespan
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# API 엔드포인트
# =============================================================================

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    RAG 기반 의료 상담 질답
    - 사용자 질문을 받아 의료 문서 기반으로 답변 생성
    """
    try:
        if not rag_engine:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG 엔진이 초기화되지 않았습니다."
            )
        
        logger.info(f"💬 새로운 질문: {request.question[:100]}...")
        
        # RAG로 답변 생성
        result = await rag_engine.generate_answer(request.question)
        
        response = ChatResponse(**result)
        logger.info(f"✅ 답변 완료 (신뢰도: {response.confidence})")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 채팅 처리 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅 처리 중 오류가 발생했습니다."
        )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    서비스 헬스체크
    - RAG 엔진, Qdrant, OpenAI 연결 상태 확인
    """
    try:
        if not rag_engine:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "service": "Chatbot Service",
                    "status": "unhealthy",
                    "qdrant_status": "disconnected",
                    "openai_status": "disconnected",
                    "documents_loaded": 0,
                    "error": "RAG 엔진 초기화 실패"
                }
            )
        
        # RAG 엔진 상태 확인
        status_info = rag_engine.get_status()
        
        return HealthResponse(
            service="Chatbot Service",
            status="healthy" if status_info["documents_loaded"] else "degraded",
            qdrant_status=status_info["qdrant_status"],
            openai_status=status_info["openai_status"],
            documents_loaded=status_info["documents_count"]
        )
        
    except Exception as e:
        logger.error(f"❌ 헬스체크 실패: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "service": "Chatbot Service", 
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/", tags=["Info"])
async def root():
    """서비스 기본 정보"""
    return {
        "service": "Chatbot Service",
        "status": "running",
        "version": "1.0.0",
        "description": "RAG 기반 의료 상담 챗봇 서비스 🤖",
        "endpoints": {
            "chat": "/chat",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/info", tags=["Info"])
async def service_info():
    """상세 서비스 정보"""
    status_info = rag_engine.get_status() if rag_engine else {}
    
    return {
        "service_name": "Chatbot Service",
        "version": "1.0.0",
        "description": "RAG 기반 의료 상담 챗봇",
        "technology": {
            "llm": "OpenAI GPT-4o-mini",
            "embeddings": "OpenAI Ada-002",
            "vector_db": "Qdrant",
            "framework": "LangChain + FastAPI"
        },
        "status": status_info,
        "port": 8009
    }


# =============================================================================
# 전역 예외 처리
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 예외 처리"""
    logger.error(f"HTTP 에러: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """일반 예외 처리"""
    logger.error(f"예상치 못한 에러: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="내부 서버 오류가 발생했습니다.",
            error_code="INTERNAL_ERROR"
        ).dict()
    )


# =============================================================================
# 개발 서버 실행
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    logger.info("🔧 개발 모드로 서버 시작...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )