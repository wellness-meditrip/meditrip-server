"""
인증 관련 DTO (Data Transfer Object)
회원가입, 로그인, 프로필 관련 데이터 구조 정의
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import date
import re
import json

class RegisterRequestDTO(BaseModel):
    """일반 회원가입 요청 DTO - 기본 정보만"""
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., min_length=8, max_length=128, description="비밀번호 (8자 이상)")
    confirm_password: str = Field(..., description="비밀번호 확인")
    nickname: str = Field(..., min_length=2, max_length=50, description="닉네임")
    country_id: int = Field(..., description="국가 ID")
    
    # 약관 동의
    terms_agreement: bool = Field(..., description="약관 동의 (필수)")
    marketing_agreement: bool = Field(default=False, description="마케팅 수신 동의 (선택)")
    
    @validator('password')
    def validate_password(cls, v):
        """비밀번호 유효성 검사: 8자 이상, 영문/숫자 혼합"""
        if len(v) < 8:
            raise ValueError('비밀번호는 8자 이상이어야 합니다.')
        
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('비밀번호에 영문자가 포함되어야 합니다.')
        
        if not re.search(r'\d', v):
            raise ValueError('비밀번호에 숫자가 포함되어야 합니다.')
        
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """비밀번호 확인"""
        if 'password' in values and v != values['password']:
            raise ValueError('비밀번호가 일치하지 않습니다.')
        return v
    
    @validator('terms_agreement')
    def validate_terms_agreement(cls, v):
        """약관 동의 필수 체크"""
        if not v:
            raise ValueError('약관 동의는 필수입니다.')
        return v

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "password123",
                "confirm_password": "password123",
                "nickname": "김건강",
                "country_id": 1,
                "terms_agreement": True,
                "marketing_agreement": False
            }
        }

class LoginRequestDTO(BaseModel):
    """일반 로그인 요청 DTO"""
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., description="비밀번호")
    remember_me: bool = Field(default=False, description="로그인 상태 유지")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com", 
                "password": "password123",
                "remember_me": True
            }
        }

class TokenRefreshRequestDTO(BaseModel):
    """토큰 갱신 요청 DTO"""
    refresh_token: str = Field(..., description="리프레시 토큰")

class AuthResponseDTO(BaseModel):
    """인증 응답 DTO"""
    success: bool = Field(..., description="요청 성공 여부")
    message: str = Field(..., description="응답 메시지")
    user: Optional[dict] = Field(None, description="사용자 정보")
    tokens: Optional[dict] = Field(None, description="토큰 정보")
    is_new_user: bool = Field(default=False, description="신규 사용자 여부")

class UserProfileDTO(BaseModel):
    """사용자 프로필 정보 DTO"""
    id: int
    email: str
    nickname: Optional[str]
    name: Optional[str]
    gender: Optional[str]
    birthdate: Optional[date]
    height: Optional[int]
    weight: Optional[int]
    topics_of_interest: Optional[List[str]]
    country_id: Optional[int]
    account_type: str
    is_active: bool
    date_joined: str
    marketing_agreement: bool
    
    @validator('topics_of_interest', pre=True)
    def parse_topics_of_interest(cls, v):
        """JSON 문자열을 리스트로 변환"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return []
        return v or []

    class Config:
        from_attributes = True

class ProfileCreateDTO(BaseModel):
    """개인 프로필 생성 DTO - 처음 프로필 설정"""
    gender: Optional[str] = Field(None, description="성별 (male/female)")
    birthdate: Optional[date] = Field(None, description="생년월일")
    height: Optional[int] = Field(None, ge=100, le=250, description="키 (cm)")
    weight: Optional[int] = Field(None, ge=30, le=300, description="몸무게 (kg)")
    topics_of_interest: Optional[List[str]] = Field(None, description="관심사 목록")
    
    @validator('gender')
    def validate_gender(cls, v):
        """성별 유효성 검사"""
        if v and v not in ['male', 'female']:
            raise ValueError("성별은 'male' 또는 'female'이어야 합니다.")
        return v
    

    class Config:
        schema_extra = {
            "example": {
                "gender": "male",
                "birthdate": "1990-01-01",
                "height": 175,
                "weight": 70,
                "topics_of_interest": ["다이어트", "건강관리", "성형수술", "치과"]
            }
        }

class ProfileUpdateDTO(BaseModel):
    """프로필 업데이트 DTO"""
    nickname: Optional[str] = Field(None, min_length=2, max_length=50)
    gender: Optional[str] = Field(None)
    birthdate: Optional[date] = Field(None)
    height: Optional[int] = Field(None, ge=100, le=250)
    weight: Optional[int] = Field(None, ge=30, le=300)
    topics_of_interest: Optional[List[str]] = Field(None)
    marketing_agreement: Optional[bool] = Field(None)
    
    @validator('gender')
    def validate_gender(cls, v):
        if v and v not in ['male', 'female']:
            raise ValueError("성별은 'male' 또는 'female'이어야 합니다.")
        return v
    

class PasswordChangeDTO(BaseModel):
    """비밀번호 변경 DTO"""
    current_password: str = Field(..., description="현재 비밀번호")
    new_password: str = Field(..., min_length=8, max_length=128, description="새 비밀번호")
    confirm_new_password: str = Field(..., description="새 비밀번호 확인")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """새 비밀번호 유효성 검사"""
        if len(v) < 8:
            raise ValueError('비밀번호는 8자 이상이어야 합니다.')
        
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('비밀번호에 영문자가 포함되어야 합니다.')
        
        if not re.search(r'\d', v):
            raise ValueError('비밀번호에 숫자가 포함되어야 합니다.')
        
        return v
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('새 비밀번호가 일치하지 않습니다.')
        return v