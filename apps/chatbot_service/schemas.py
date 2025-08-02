"""
schemas.py - Chatbot Service Pydantic 스키마
RAG 기반 질답 시스템 API 스키마 정의
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ChatRequest(BaseModel):
    """채팅 요청 스키마"""
    question: str = Field(..., min_length=1, max_length=1000, description="사용자 질문")
    
    class Config:
        schema_extra = {
            "example": {
                "question": "의료진 자격 요건이 무엇인가요?"
            }
        }


class ChatResponse(BaseModel):
    """채팅 응답 스키마"""
    answer: str = Field(..., description="RAG 기반 답변")
    sources: List[str] = Field(default=[], description="참조한 문서 페이지")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="답변 신뢰도")
    
    class Config:
        schema_extra = {
            "example": {
                "answer": "의료진 자격 요건은 다음과 같습니다...",
                "sources": ["page_12", "page_45", "page_78"],
                "confidence": 0.85
            }
        }


class HealthResponse(BaseModel):
    """헬스체크 응답 스키마"""
    service: str = "Chatbot Service"
    status: str = "healthy"
    qdrant_status: str = "connected"
    openai_status: str = "connected"
    documents_loaded: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "service": "Chatbot Service",
                "status": "healthy", 
                "qdrant_status": "connected",
                "openai_status": "connected",
                "documents_loaded": 425
            }
        }


class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    success: bool = False
    error: str = Field(..., description="에러 메시지")
    error_code: Optional[str] = Field(None, description="에러 코드")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": "질문을 처리하는 중 오류가 발생했습니다.",
                "error_code": "RAG_ERROR"
            }
        }