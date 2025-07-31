from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date

class UserCreateDTO(BaseModel):
    email: EmailStr
    nickname: str = Field(..., min_length=2, max_length=20)
    password: Optional[str] = None
    line_id: Optional[str] = None
    line_auth_info: Optional[str] = None
    google_auth_info: Optional[str] = None
    google_id: Optional[str] = None
    gender: Optional[str] = Field(None, pattern="^(M|F|Other)$")
    birthdate: Optional[date] = None
    height: Optional[int] = Field(None, ge=50, le=250)
    weight: Optional[int] = Field(None, ge=20, le=300)
    country_id: Optional[int] = None

class UserResponseDTO(BaseModel):
    id: int
    email: str
    nickname: str
    line_id: Optional[str] = None
    gender: Optional[str] = None
    birthdate: Optional[date] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    country_id: Optional[int] = None
    google_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserUpdateDTO(BaseModel):
    nickname: Optional[str] = Field(None, min_length=2, max_length=20)
    gender: Optional[str] = Field(None, pattern="^(M|F|Other)$")
    birthdate: Optional[date] = None
    height: Optional[int] = Field(None, ge=50, le=250)
    weight: Optional[int] = Field(None, ge=20, le=300)
    country_id: Optional[int] = None

class LineUserInfoDTO(BaseModel):
    user_id: str
    display_name: str
    picture_url: Optional[str] = None
    status_message: Optional[str] = None
    email: Optional[str] = None  # OpenID Connect에서 이메일 정보

class GoogleUserInfoDTO(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    picture: Optional[str] = None