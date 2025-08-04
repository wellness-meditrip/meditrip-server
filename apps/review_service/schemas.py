"""
schemas.py - Review Service Pydantic Schemas
리뷰 관리 시스템의 데이터 검증 및 직렬화 스키마
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class KeywordCategory(str, Enum):
    """키워드 카테고리"""
    CARE = "CARE"
    SERVICE = "SERVICE"
    FACILITY = "FACILITY"

# === Review Keyword Schemas ===

class ReviewKeywordBase(BaseModel):
    """리뷰 키워드 기본 스키마"""
    category: KeywordCategory
    keyword_code: str = Field(..., max_length=50)
    keyword_name: str = Field(..., max_length=100)
    is_positive: bool

class ReviewKeywordCreate(ReviewKeywordBase):
    """리뷰 키워드 생성 스키마"""
    pass

class ReviewKeywordResponse(ReviewKeywordBase):
    """리뷰 키워드 응답 스키마"""
    id: int
    review_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# === Review Image Schemas ===

class ReviewImageBase(BaseModel):
    """리뷰 이미지 기본 스키마"""
    image_url: str = Field(..., max_length=500)
    image_order: int = Field(default=1, ge=1)
    alt_text: Optional[str] = Field(None, max_length=200)

class ReviewImageCreate(ReviewImageBase):
    """리뷰 이미지 생성 스키마"""
    pass

class ReviewImageResponse(ReviewImageBase):
    """리뷰 이미지 응답 스키마"""
    id: int
    review_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# === Review Schemas ===

class ReviewBase(BaseModel):
    """리뷰 기본 스키마"""
    hospital_id: int
    user_id: int
    doctor_id: Optional[int] = None
    doctor_name: Optional[str] = Field(None, max_length=100)
    title: str = Field(..., max_length=200)
    content: str = Field(..., min_length=10)
    rating: float = Field(..., ge=1.0, le=5.0)

    @validator('rating')
    def validate_rating(cls, v):
        """평점 검증 (소수점 첫째자리까지만)"""
        return round(v, 1)

class ReviewCreate(ReviewBase):
    """리뷰 생성 스키마"""
    keywords: List[ReviewKeywordCreate] = []
    images: List[ReviewImageCreate] = []

class ReviewUpdate(BaseModel):
    """리뷰 수정 스키마"""
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    doctor_id: Optional[int] = None
    doctor_name: Optional[str] = Field(None, max_length=100)

    @validator('rating')
    def validate_rating(cls, v):
        if v is not None:
            return round(v, 1)
        return v

class ReviewResponse(ReviewBase):
    """리뷰 응답 스키마"""
    review_id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    keywords: List[ReviewKeywordResponse] = []
    images: List[ReviewImageResponse] = []

    class Config:
        from_attributes = True

class ReviewListResponse(BaseModel):
    """리뷰 목록 응답 스키마"""
    review_id: int
    hospital_id: int
    user_id: int
    doctor_id: Optional[int]
    doctor_name: Optional[str]
    title: str
    rating: float
    is_verified: bool
    created_at: datetime
    keyword_count: int = 0
    image_count: int = 0

    class Config:
        from_attributes = True

# === Review Keyword Template Schemas ===

class ReviewKeywordTemplateBase(BaseModel):
    """리뷰 키워드 템플릿 기본 스키마"""
    category: KeywordCategory
    keyword_code: str = Field(..., max_length=50)
    keyword_name: str = Field(..., max_length=100)
    is_positive: bool
    keyword_name_en: Optional[str] = Field(None, max_length=100)
    keyword_name_jp: Optional[str] = Field(None, max_length=100)

class ReviewKeywordTemplateCreate(ReviewKeywordTemplateBase):
    """리뷰 키워드 템플릿 생성 스키마"""
    pass

class ReviewKeywordTemplateUpdate(BaseModel):
    """리뷰 키워드 템플릿 수정 스키마"""
    keyword_name: Optional[str] = Field(None, max_length=100)
    is_positive: Optional[bool] = None
    keyword_name_en: Optional[str] = Field(None, max_length=100)
    keyword_name_jp: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None

class ReviewKeywordTemplateResponse(ReviewKeywordTemplateBase):
    """리뷰 키워드 템플릿 응답 스키마"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# === Review Stats Schemas ===

class ReviewStatsResponse(BaseModel):
    """리뷰 통계 응답 스키마"""
    hospital_id: int
    total_reviews: int
    average_rating: float
    rating_5: int
    rating_4: int
    rating_3: int
    rating_2: int
    rating_1: int
    care_keywords: Optional[Dict[str, Any]] = None
    service_keywords: Optional[Dict[str, Any]] = None
    facility_keywords: Optional[Dict[str, Any]] = None
    last_updated: datetime

    class Config:
        from_attributes = True

# === API Response Schemas ===

class ReviewSearchParams(BaseModel):
    """리뷰 검색 파라미터"""
    hospital_id: Optional[int] = None
    user_id: Optional[int] = None
    doctor_id: Optional[int] = None
    rating_min: Optional[float] = Field(None, ge=1.0, le=5.0)
    rating_max: Optional[float] = Field(None, ge=1.0, le=5.0)
    is_verified: Optional[bool] = None
    keyword_category: Optional[KeywordCategory] = None
    keyword_code: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class PaginatedResponse(BaseModel):
    """페이지네이션 응답 스키마"""
    items: List[Any]
    total: int
    limit: int
    offset: int
    has_next: bool
    has_prev: bool

class ApiResponse(BaseModel):
    """API 응답 스키마"""
    success: bool
    message: str
    data: Optional[Any] = None

# === Bulk Operations ===

class BulkKeywordCreate(BaseModel):
    """키워드 템플릿 일괄 생성"""
    keywords: List[ReviewKeywordTemplateCreate]

class ReviewAnalytics(BaseModel):
    """리뷰 분석 데이터"""
    period: str = Field(..., description="분석 기간")
    total_reviews: int
    average_rating: float
    rating_distribution: Dict[str, int]
    top_positive_keywords: List[Dict[str, Any]]
    top_negative_keywords: List[Dict[str, Any]]
    monthly_trends: List[Dict[str, Any]]