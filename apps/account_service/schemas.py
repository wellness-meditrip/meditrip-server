"""
Account Service Schemas
계정 관리 및 프로필 이미지 관련 Pydantic 스키마
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import base64
import re

class DeletionType(str, Enum):
    """계정 삭제 유형"""
    USER_REQUEST = "user_request"
    ADMIN_ACTION = "admin_action"
    SYSTEM_CLEANUP = "system_cleanup"

class RecoveryStatus(str, Enum):
    """복구 요청 상태"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ImageType(str, Enum):
    """지원하는 이미지 타입"""
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"

class ActionType(str, Enum):
    """이미지 업로드 액션 타입"""
    UPLOAD = "upload"
    UPDATE = "update"
    DELETE = "delete"

# === Account Deletion Schemas ===

class AccountDeletionRequestDTO(BaseModel):
    """계정 삭제 요청 DTO"""
    user_id: int = Field(..., description="삭제할 사용자 ID")
    deletion_reason: Optional[str] = Field(None, max_length=200, description="삭제 사유 (선택사항)")
    confirm_deletion: bool = Field(..., description="삭제 확인 (true 필수)")
    
    @validator('confirm_deletion')
    def validate_confirm_deletion(cls, v):
        if not v:
            raise ValueError("계정 삭제를 위해서는 confirm_deletion이 true여야 합니다.")
        return v

class AccountDeletionResponseDTO(BaseModel):
    """계정 삭제 응답 DTO"""
    success: bool
    message: str
    deletion_log_id: Optional[int] = None
    recovery_deadline: Optional[datetime] = None
    
class AccountRecoveryRequestDTO(BaseModel):
    """계정 복구 요청 DTO"""
    email: str = Field(..., max_length=320, description="복구할 계정 이메일")
    verification_code: Optional[str] = Field(None, max_length=10, description="인증 코드")

class AccountRecoveryResponseDTO(BaseModel):
    """계정 복구 응답 DTO"""
    success: bool
    message: str
    recovery_token: Optional[str] = None
    expires_at: Optional[datetime] = None

# === Profile Image Schemas ===

class ProfileImageUploadDTO(BaseModel):
    """프로필 이미지 업로드 DTO"""
    user_id: int = Field(..., description="사용자 ID")
    image_data: str = Field(..., description="Base64 인코딩된 이미지 데이터")
    image_type: ImageType = Field(..., description="이미지 타입")
    original_filename: Optional[str] = Field(None, max_length=255, description="원본 파일명")
    
    @validator('image_data')
    def validate_base64_image(cls, v):
        """Base64 이미지 데이터 검증"""
        try:
            # Base64 데이터 URL 형식 체크 (data:image/jpeg;base64,...)
            if v.startswith('data:image'):
                # data URL에서 실제 base64 데이터 추출
                if ',' in v:
                    v = v.split(',', 1)[1]
            
            # Base64 디코딩 테스트
            decoded = base64.b64decode(v)
            
            # 최소 크기 체크 (1KB)
            if len(decoded) < 1024:
                raise ValueError("이미지 크기가 너무 작습니다. (최소 1KB)")
            
            # 최대 크기 체크 (10MB)
            if len(decoded) > 10 * 1024 * 1024:
                raise ValueError("이미지 크기가 너무 큽니다. (최대 10MB)")
                
            return v
            
        except Exception as e:
            raise ValueError(f"올바른 Base64 이미지 데이터가 아닙니다: {str(e)}")
    
    @validator('original_filename')
    def validate_filename(cls, v):
        """파일명 검증"""
        if v is None:
            return v
        
        # 파일명 패턴 검증 (영문, 숫자, 점, 하이픈, 언더스코어만 허용)
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError("파일명에 허용되지 않은 문자가 포함되어 있습니다.")
        
        return v

class ProfileImageUpdateDTO(BaseModel):
    """프로필 이미지 업데이트 DTO"""
    image_data: str = Field(..., description="Base64 인코딩된 이미지 데이터")
    image_type: ImageType = Field(..., description="이미지 타입")
    original_filename: Optional[str] = Field(None, max_length=255, description="원본 파일명")
    
    @validator('image_data')
    def validate_base64_image(cls, v):
        """Base64 이미지 데이터 검증"""
        try:
            if v.startswith('data:image'):
                if ',' in v:
                    v = v.split(',', 1)[1]
            
            decoded = base64.b64decode(v)
            
            if len(decoded) < 1024:
                raise ValueError("이미지 크기가 너무 작습니다. (최소 1KB)")
            
            if len(decoded) > 10 * 1024 * 1024:
                raise ValueError("이미지 크기가 너무 큽니다. (최대 10MB)")
                
            return v
            
        except Exception as e:
            raise ValueError(f"올바른 Base64 이미지 데이터가 아닙니다: {str(e)}")

class ProfileImageResponseDTO(BaseModel):
    """프로필 이미지 응답 DTO"""
    id: int
    user_id: int
    image_data: str
    image_type: str
    original_filename: Optional[str]
    file_size: int
    width: Optional[int]
    height: Optional[int]
    is_compressed: bool
    compression_quality: Optional[int]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    is_verified: bool
    
    class Config:
        from_attributes = True

class ProfileImageListResponseDTO(BaseModel):
    """프로필 이미지 목록 응답 DTO (이미지 데이터 제외)"""
    id: int
    user_id: int
    image_type: str
    original_filename: Optional[str]
    file_size: int
    width: Optional[int]
    height: Optional[int]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    is_verified: bool
    
    class Config:
        from_attributes = True

# === Image Upload History Schemas ===

class ImageUploadHistoryResponseDTO(BaseModel):
    """이미지 업로드 히스토리 응답 DTO"""
    id: int
    user_id: int
    action_type: str
    original_filename: Optional[str]
    file_size: Optional[int]
    image_type: Optional[str]
    created_at: datetime
    ip_address: Optional[str]
    result_status: str
    error_message: Optional[str]
    
    class Config:
        from_attributes = True

# === API Response Schemas ===

class ApiResponseDTO(BaseModel):
    """API 응답 공통 스키마"""
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None

class PaginatedResponseDTO(BaseModel):
    """페이지네이션 응답 스키마"""
    items: List[dict]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool

# === Statistics Schemas ===

class AccountDeletionStatsDTO(BaseModel):
    """계정 삭제 통계 DTO"""
    total_deletions: int
    user_requests: int
    admin_actions: int
    system_cleanups: int
    recoverable_accounts: int
    recovered_accounts: int
    permanent_deletions: int

class ProfileImageStatsDTO(BaseModel):
    """프로필 이미지 통계 DTO"""
    total_images: int
    active_images: int
    verified_images: int
    total_size: int  # bytes
    average_size: int  # bytes
    most_common_type: str
    compression_rate: float  # percentage

# === Validation Schemas ===

class UserValidationDTO(BaseModel):
    """사용자 검증 DTO"""
    user_id: int
    email: Optional[str] = None
    is_active: bool = True
    
class ImageValidationResultDTO(BaseModel):
    """이미지 검증 결과 DTO"""
    is_valid: bool
    file_size: int
    image_type: str
    width: Optional[int]
    height: Optional[int]
    error_message: Optional[str]

# === Search and Filter Schemas ===

class AccountDeletionSearchDTO(BaseModel):
    """계정 삭제 검색 DTO"""
    deletion_type: Optional[DeletionType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    email_contains: Optional[str] = None
    is_recoverable: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

class ImageHistorySearchDTO(BaseModel):
    """이미지 히스토리 검색 DTO"""
    user_id: Optional[int] = None
    action_type: Optional[ActionType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    result_status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)