"""
schemas.py - Hospital Service Pydantic Schemas
병원 관리 시스템의 API 요청/응답 스키마 정의
"""

from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import json

# =============================================================================
# 병원 기본 정보 스키마
# =============================================================================

class HospitalBase(BaseModel):
    """병원 기본 정보 베이스 스키마"""
    hospital_name: str
    address: str
    contact: Optional[str] = None
    website: Optional[str] = None
    line: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None
    established_date: Optional[date] = None
    hospital_description: Optional[str] = None
    hospital_description_jp: Optional[str] = None
    hospital_description_en: Optional[str] = None
    hospital_address_jp: Optional[str] = None
    hospital_address_en: Optional[str] = None

class HospitalCreate(HospitalBase):
    """병원 생성 요청 스키마"""
    pass

class HospitalUpdate(BaseModel):
    """병원 정보 수정 요청 스키마"""
    hospital_name: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    website: Optional[str] = None
    line: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None
    established_date: Optional[date] = None
    hospital_description: Optional[str] = None
    hospital_description_jp: Optional[str] = None
    hospital_description_en: Optional[str] = None
    hospital_address_jp: Optional[str] = None
    hospital_address_en: Optional[str] = None

# =============================================================================
# 병원 세부 정보 스키마
# =============================================================================

class OperatingHour(BaseModel):
    """운영시간 스키마"""
    day_of_week: int  # 0:월요일, 6:일요일
    open_time: Optional[str] = None  # "09:00"
    close_time: Optional[str] = None  # "18:00"
    lunch_start: Optional[str] = None  # "12:00"
    lunch_end: Optional[str] = None  # "13:00"
    is_closed: bool = False
    notes: Optional[str] = None

class HospitalImage(BaseModel):
    """병원 이미지 스키마"""
    image_type: str  # "main", "interior", "exterior", "equipment"
    image_url: str
    alt_text: Optional[str] = None
    is_main: bool = False

class Department(BaseModel):
    """진료과목 스키마"""
    name: str
    name_en: Optional[str] = None
    name_jp: Optional[str] = None
    description: Optional[str] = None
    is_available: bool = True

class HospitalDetailBase(BaseModel):
    """병원 세부 정보 베이스 스키마"""
    # 편의시설
    parking_available: Optional[bool] = False
    parking_description: Optional[str] = None
    
    wifi_available: Optional[bool] = False
    wifi_description: Optional[str] = None
    
    luggage_storage: Optional[bool] = False
    luggage_storage_description: Optional[str] = None
    
    private_treatment: Optional[bool] = False
    private_treatment_description: Optional[str] = None
    
    airport_pickup: Optional[bool] = False
    airport_pickup_description: Optional[str] = None
    
    translation_service: Optional[bool] = False
    translation_description: Optional[str] = None
    
    operating_hours: Optional[List[OperatingHour]] = None
    images: Optional[List[HospitalImage]] = None
    departments: Optional[List[Department]] = None

    @validator('operating_hours', pre=True)
    def parse_operating_hours(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return None
        return v

    @validator('images', pre=True)
    def parse_images(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return None
        return v

    @validator('departments', pre=True)
    def parse_departments(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return None
        return v

class HospitalDetailCreate(HospitalDetailBase):
    """병원 세부 정보 생성 요청 스키마"""
    hospital_id: int

class HospitalDetailUpdate(BaseModel):
    """병원 세부 정보 수정 요청 스키마"""
    # 편의시설
    parking_available: Optional[bool] = None
    parking_description: Optional[str] = None
    wifi_available: Optional[bool] = None
    wifi_description: Optional[str] = None
    luggage_storage: Optional[bool] = None
    luggage_storage_description: Optional[str] = None
    private_treatment: Optional[bool] = None
    private_treatment_description: Optional[str] = None
    airport_pickup: Optional[bool] = None
    airport_pickup_description: Optional[str] = None
    translation_service: Optional[bool] = None
    translation_description: Optional[str] = None
    
    operating_hours: Optional[List[OperatingHour]] = None
    images: Optional[List[HospitalImage]] = None
    departments: Optional[List[Department]] = None

# =============================================================================
# 응답 스키마
# =============================================================================

class HospitalDetailResponse(HospitalDetailBase):
    """병원 세부 정보 응답 스키마"""
    id: int
    hospital_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class HospitalResponse(HospitalBase):
    """병원 기본 정보 응답 스키마"""
    hospital_id: int
    created_at: datetime
    updated_at: datetime
    hospital_details: Optional[List[HospitalDetailResponse]] = None

    class Config:
        from_attributes = True

class HospitalListResponse(BaseModel):
    """병원 목록 응답 스키마"""
    hospitals: List[HospitalResponse]
    total: int
    page: int
    size: int

# =============================================================================
# 검색 및 필터링 스키마
# =============================================================================

class HospitalSearchParams(BaseModel):
    """병원 검색 파라미터"""
    keyword: Optional[str] = None  # 병원명, 주소 검색
    city: Optional[str] = None  # 도시별 필터
    department: Optional[str] = None  # 진료과목 필터
    parking_required: Optional[bool] = None  # 주차장 필요 여부
    page: int = 1
    size: int = 10

    @validator('page')
    def validate_page(cls, v):
        if v < 1:
            raise ValueError('page must be greater than 0')
        return v

    @validator('size')
    def validate_size(cls, v):
        if v < 1 or v > 100:
            raise ValueError('size must be between 1 and 100')
        return v

# =============================================================================
# 에러 응답 스키마
# =============================================================================

class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    error: str
    message: str
    status_code: int