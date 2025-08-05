from common.base import Base 
from sqlalchemy import Column, String, Integer, DATE, ForeignKey, Boolean, DateTime, BigInteger, Text
from sqlalchemy.orm import relationship
from datetime import datetime

class User(Base):
    __tablename__ = "meditrip_user"

    # 기존 Django User 모델 필드들
    id = Column(BigInteger, primary_key=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime, nullable=True)
    is_superuser = Column(Boolean, nullable=False, default=False)
    username = Column(String(150), unique=True, nullable=False)
    first_name = Column(String(150), nullable=False, default='')
    last_name = Column(String(150), nullable=False, default='')
    is_staff = Column(Boolean, nullable=False, default=False) 
    is_active = Column(Boolean, nullable=False, default=True)
    date_joined = Column(DateTime, nullable=False, default=datetime.utcnow)
    phone_number = Column(String(15), nullable=False, default='')
    name = Column(String(100), nullable=False, default='')
    country = Column(String(50), nullable=False, default='')
    email = Column(String(254), nullable=False, unique=True, index=True)
    height = Column(Integer, nullable=True)
    weight = Column(Integer, nullable=True)
    
    # OAuth 관련 추가 필드들
    nickname = Column(String(255), nullable=True)
    line_id = Column(String(255), nullable=True, index=True)
    line_auth_info = Column(Text, nullable=True)
    google_auth_info = Column(Text, nullable=True)
    google_id = Column(String(255), nullable=True, index=True)
    refresh_token = Column(Text, nullable=True)
    gender = Column(String(10), nullable=True)  # 'male', 'female'
    birthdate = Column(DATE, nullable=True)
    
    # 관심사 및 동의 필드
    topics_of_interest = Column(Text, nullable=True)  # JSON 문자열로 저장
    terms_agreement = Column(Boolean, nullable=False, default=False)  # 약관 동의 (필수)
    marketing_agreement = Column(Boolean, nullable=False, default=False)  # 마케팅 수신 동의 (선택)
    
    # 계정 타입 구분
    account_type = Column(String(20), nullable=False, default='email')  # 'email', 'google', 'line'

    country_id = Column(Integer, ForeignKey('meditrip_country.id'), nullable=True)
    country_obj = relationship("Country", back_populates="users")
