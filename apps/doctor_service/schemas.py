"""
schemas.py - Pydantic 스키마 정의
API 요청/응답 데이터 구조를 정의하고 유효성 검사
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, time
import pytz


# =============================================================================
# Doctor (의사 기본정보) 스키마
# =============================================================================

class DoctorBase(BaseModel):
    """의사 생성/수정 시 공통 필드"""
    doctor_name: str = Field(..., min_length=1, max_length=100, description="의사 이름")
    doctor_position: Optional[str] = Field(None, max_length=50, description="의사 직급")
    doctor_phone: Optional[str] = Field(None, max_length=20, description="의사 연락처")
    license_number: str = Field(..., min_length=1, max_length=50, description="의사 면허번호")
    bio: Optional[str] = Field(None, description="의사 소개/약력")
    profile_image: Optional[str] = Field(None, max_length=255, description="프로필 이미지 URL")
    hospital_id: int = Field(..., description="소속 병원 ID")


class DoctorCreate(DoctorBase):
    """의사 생성 요청 스키마"""
    pass


class DoctorUpdate(BaseModel):
    """의사 정보 수정 요청 스키마 (모든 필드 선택적)"""
    doctor_name: Optional[str] = Field(None, min_length=1, max_length=100)
    doctor_position: Optional[str] = Field(None, max_length=50)
    doctor_phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = None
    profile_image: Optional[str] = Field(None, max_length=255)
    hospital_id: Optional[int] = Field(None, description="소속 병원 ID")


class DoctorResponse(DoctorBase):
    """의사 정보 응답 스키마"""
    doctor_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # SQLAlchemy 모델과 호환


# =============================================================================
# DoctorSpecialization (의사 전문과목) 스키마
# =============================================================================

class DoctorSpecializationBase(BaseModel):
    """전문과목 공통 필드"""
    specializations_name: str = Field(..., min_length=1, max_length=50, description="전문과목명")
    doctor_id: int = Field(..., description="의사 ID")
    hospital_id: int = Field(..., description="병원 ID")


class DoctorSpecializationCreate(DoctorSpecializationBase):
    """전문과목 생성 요청 스키마"""
    pass


class DoctorSpecializationResponse(DoctorSpecializationBase):
    """전문과목 응답 스키마"""
    doctor_name: Optional[str] = Field(None, description="의사 이름 (JOIN으로 가져옴)")
    
    class Config:
        from_attributes = True


# =============================================================================
# DoctorStatistics (의사 통계정보) 스키마
# =============================================================================

class DoctorStatisticsBase(BaseModel):
    """통계정보 공통 필드"""
    rating_average: float = Field(0.0, ge=0.0, le=5.0, description="평균 평점 (0.0~5.0)")
    total_reviews: int = Field(0, ge=0, description="총 리뷰 개수")
    total_patients: int = Field(0, ge=0, description="총 진료 환자 수")


class DoctorStatisticsCreate(DoctorStatisticsBase):
    """통계정보 생성 요청 스키마"""
    doctor_id: int = Field(..., description="의사 ID")


class DoctorStatisticsUpdate(BaseModel):
    """통계정보 수정 요청 스키마"""
    rating_average: Optional[float] = Field(None, ge=0.0, le=5.0)
    total_reviews: Optional[int] = Field(None, ge=0)
    total_patients: Optional[int] = Field(None, ge=0)


class DoctorStatisticsResponse(DoctorStatisticsBase):
    """통계정보 응답 스키마"""
    doctor_id: int
    doctor_name: Optional[str] = Field(None, description="의사 이름 (JOIN으로 가져옴)")
    
    class Config:
        from_attributes = True


# =============================================================================
# DoctorFees (의사 진료비) 스키마
# =============================================================================

class DoctorFeesBase(BaseModel):
    """진료비 공통 필드"""
    doctor_id: int = Field(..., description="의사 ID")
    package_id: int = Field(..., description="패키지 ID")


class DoctorFeesCreate(DoctorFeesBase):
    """진료비 생성 요청 스키마"""
    pass


class DoctorFeesResponse(DoctorFeesBase):
    """진료비 응답 스키마"""
    fee_id: int
    doctor_name: Optional[str] = Field(None, description="의사 이름 (JOIN으로 가져옴)")
    
    class Config:
        from_attributes = True


# =============================================================================
# DoctorSchedule (의사 근무일정) 스키마
# =============================================================================

class DoctorScheduleBase(BaseModel):
    """근무일정 공통 필드"""
    doctor_id: int = Field(..., description="의사 ID")
    available_days: str = Field(..., min_length=1, max_length=20, description="근무 요일 (예: '월,화,수,목,금')")
    work_start_time: time = Field(..., description="근무 시작 시간 (한국시간 KST, 예: '09:00:00')")
    work_end_time: time = Field(..., description="근무 종료 시간 (한국시간 KST, 예: '18:00:00')")
    
    @validator('available_days')
    def validate_available_days(cls, v):
        """근무 요일 형식 검증 (예: '월,화,수,목,금')"""
        valid_days = ['월', '화', '수', '목', '금', '토', '일']
        days = [day.strip() for day in v.split(',')]
        for day in days:
            if day not in valid_days:
                raise ValueError(f"올바르지 않은 요일입니다: '{day}'. 사용 가능한 요일: {valid_days}")
        return ','.join(days)  # 공백 제거해서 반환
    
    @validator('work_start_time')
    def validate_work_start_time(cls, v):
        """근무 시작 시간 검증 (한국 시간 기준)"""
        if not isinstance(v, time):
            raise ValueError("시간 형식이 올바르지 않습니다. 예: '09:00:00'")
        return v
    
    @validator('work_end_time')
    def validate_work_end_time(cls, v, values):
        """근무 종료 시간이 시작 시간보다 늦은지 검증"""
        if not isinstance(v, time):
            raise ValueError("시간 형식이 올바르지 않습니다. 예: '18:00:00'")
        
        if 'work_start_time' in values and v <= values['work_start_time']:
            raise ValueError("근무 종료 시간은 시작 시간보다 늦어야 합니다")
        return v
    
    class Config:
        json_encoders = {
            time: lambda v: v.strftime('%H:%M:%S')  # 한국 시간 형식으로 출력
        }
        schema_extra = {
            "example": {
                "doctor_id": 1,
                "available_days": "월,화,수,목,금",
                "work_start_time": "09:00:00",
                "work_end_time": "18:00:00"
            }
        }


class DoctorScheduleCreate(DoctorScheduleBase):
    """근무일정 생성 요청 스키마"""
    pass


class DoctorScheduleUpdate(BaseModel):
    """근무일정 수정 요청 스키마"""
    available_days: Optional[str] = Field(None, min_length=1, max_length=20)
    work_start_time: Optional[time] = None
    work_end_time: Optional[time] = None


class DoctorScheduleResponse(DoctorScheduleBase):
    """근무일정 응답 스키마"""
    schedule_id: int
    doctor_name: Optional[str] = Field(None, description="의사 이름 (JOIN으로 가져옴)")
    
    class Config:
        from_attributes = True


# =============================================================================
# 복합 응답 스키마 (의사 + 관련 정보)
# =============================================================================

class DoctorDetailResponse(DoctorResponse):
    """의사 상세 정보 응답 (관련 정보 포함)"""
    specializations: List[DoctorSpecializationResponse] = []
    statistics: Optional[DoctorStatisticsResponse] = None
    fees: List[DoctorFeesResponse] = []
    schedules: List[DoctorScheduleResponse] = []


# =============================================================================
# 공통 응답 스키마
# =============================================================================

class MessageResponse(BaseModel):
    """일반적인 메시지 응답"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """에러 응답"""
    message: str
    success: bool = False
    error_code: Optional[str] = None