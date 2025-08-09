"""
schemas.py - Reservation Service Pydantic Schemas
예약 관리 시스템의 데이터 검증 및 직렬화 스키마
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time
from enum import Enum

class ReservationStatus(str, Enum):
    """예약 상태"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class InterpreterLanguage(str, Enum):
    """통역 언어"""
    KOREAN = "한국어"
    JAPANESE = "일본어"
    ENGLISH = "영어"

# === Reservation Image Schemas ===

class ReservationImageBase(BaseModel):
    """예약 이미지 기본 스키마"""
    image_data: str = Field(..., description="Base64 인코딩된 이미지 데이터")
    image_type: str = Field(..., max_length=10, description="이미지 타입 (jpg, png, webp)")
    original_filename: Optional[str] = Field(None, max_length=255, description="원본 파일명")
    image_order: int = Field(default=1, ge=1, description="이미지 순서")
    alt_text: Optional[str] = Field(None, max_length=200, description="이미지 설명")

class ReservationImageCreate(ReservationImageBase):
    """예약 이미지 생성 스키마"""
    pass

class ReservationImageResponse(ReservationImageBase):
    """예약 이미지 응답 스키마"""
    id: int
    reservation_id: int
    file_size: int
    width: Optional[int]
    height: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

# === Reservation Schemas ===

class ReservationBase(BaseModel):
    """예약 기본 스키마"""
    hospital_id: int = Field(..., description="병원 ID")
    doctor_id: Optional[int] = Field(None, description="의사 ID (선택사항)")
    
    # 진료 정보
    symptoms: str = Field(..., min_length=10, description="진료목적/증상")
    current_medications: Optional[str] = Field(None, description="복용중인 약물 (선택사항)")
    
    # 예약 날짜 및 시간
    reservation_date: date = Field(..., description="예약 날짜")
    reservation_time: time = Field(..., description="예약 시간")
    
    # 연락처 정보
    contact_email: str = Field(..., max_length=100, description="이메일 연락처")
    contact_phone: str = Field(..., max_length=20, description="전화번호")
    
    # 통역 및 기타 정보
    interpreter_language: InterpreterLanguage = Field(..., description="통역 언어")
    additional_notes: Optional[str] = Field(None, description="기타정보/문의사항")

    @validator('contact_email')
    def validate_email(cls, v):
        """이메일 형식 검증"""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('올바른 이메일 형식이 아닙니다.')
        return v

    @validator('contact_phone')
    def validate_phone(cls, v):
        """전화번호 형식 검증"""
        import re
        # 국제 번호 또는 한국 번호 형식 허용
        phone_pattern = r'^(\+\d{1,3}[- ]?)?\d{2,3}[- ]?\d{3,4}[- ]?\d{4}$'
        if not re.match(phone_pattern, v.replace(' ', '').replace('-', '')):
            raise ValueError('올바른 전화번호 형식이 아닙니다.')
        return v

    @validator('reservation_time')
    def validate_and_convert_time(cls, v):
        """시간 검증 및 한국시간 변환"""
        from datetime import datetime, timezone, timedelta
        import pytz
        
        if isinstance(v, str):
            # ISO 형식 시간 문자열 처리 (예: "13:16:04.421Z")
            if v.endswith('Z'):
                # UTC 시간을 한국시간으로 변환
                utc_dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                kst = pytz.timezone('Asia/Seoul')
                kst_dt = utc_dt.astimezone(kst)
                return kst_dt.time()
            else:
                # 일반 시간 문자열 처리 (예: "13:16")
                try:
                    return datetime.strptime(v, '%H:%M').time()
                except ValueError:
                    try:
                        return datetime.strptime(v, '%H:%M:%S').time()
                    except ValueError:
                        raise ValueError('올바른 시간 형식이 아닙니다. (HH:MM 또는 ISO 형식)')
        return v

    @validator('reservation_date')
    def validate_future_date(cls, v):
        """예약 날짜가 미래인지 검증"""
        from datetime import date
        if v <= date.today():
            raise ValueError('예약 날짜는 오늘 이후여야 합니다.')
        return v

class ReservationCreate(ReservationBase):
    """예약 생성 스키마"""
    user_id: int = Field(..., description="사용자 ID")
    images: List[ReservationImageCreate] = Field(default=[], description="첨부 이미지")

    @validator('images')
    def validate_image_count(cls, v):
        """이미지 개수 검증"""
        if len(v) > 10:
            raise ValueError('최대 10장까지만 업로드 가능합니다.')
        return v

class ReservationUpdate(BaseModel):
    """예약 수정 스키마"""
    symptoms: Optional[str] = Field(None, min_length=10)
    current_medications: Optional[str] = None
    reservation_date: Optional[date] = None
    reservation_time: Optional[time] = None
    contact_email: Optional[str] = Field(None, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=20)
    interpreter_language: Optional[InterpreterLanguage] = None
    additional_notes: Optional[str] = None
    status: Optional[ReservationStatus] = None

    @validator('contact_email')
    def validate_email(cls, v):
        if v is not None:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('올바른 이메일 형식이 아닙니다.')
        return v

    @validator('contact_phone')
    def validate_phone(cls, v):
        if v is not None:
            import re
            phone_pattern = r'^(\+\d{1,3}[- ]?)?\d{2,3}[- ]?\d{3,4}[- ]?\d{4}$'
            if not re.match(phone_pattern, v.replace(' ', '').replace('-', '')):
                raise ValueError('올바른 전화번호 형식이 아닙니다.')
        return v

    @validator('reservation_date')
    def validate_future_date(cls, v):
        if v is not None:
            from datetime import date
            if v <= date.today():
                raise ValueError('예약 날짜는 오늘 이후여야 합니다.')
        return v

class ReservationResponse(ReservationBase):
    """예약 응답 스키마"""
    reservation_id: int
    user_id: int
    status: ReservationStatus
    created_at: datetime
    updated_at: datetime
    images: List[ReservationImageResponse] = []

    class Config:
        from_attributes = True

class ReservationListResponse(BaseModel):
    """예약 목록 응답 스키마"""
    reservation_id: int
    hospital_id: int
    doctor_id: Optional[int]
    user_id: int
    symptoms: str
    reservation_date: date
    reservation_time: time
    status: ReservationStatus
    contact_email: str
    contact_phone: str
    interpreter_language: str
    created_at: datetime
    image_count: int = 0

    class Config:
        from_attributes = True

# === Available Time Schemas ===

class TimeSlotResponse(BaseModel):
    """시간대 응답 스키마"""
    time: str = Field(..., description="시간 (HH:MM 형식)")
    available: bool = Field(..., description="예약 가능 여부")
    reason: Optional[str] = Field(None, description="불가능한 경우 사유")

class AvailableTimesResponse(BaseModel):
    """가능한 시간대 응답 스키마"""
    hospital_id: int
    date: date
    time_slots: List[TimeSlotResponse]
    operating_hours: Optional[Dict[str, Any]] = Field(None, description="병원 운영시간")

# === API Response Schemas ===

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

# === Search and Filter Schemas ===

class ReservationSearchParams(BaseModel):
    """예약 검색 파라미터"""
    hospital_id: Optional[int] = None
    user_id: Optional[int] = None
    doctor_id: Optional[int] = None
    status: Optional[ReservationStatus] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    interpreter_language: Optional[InterpreterLanguage] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)