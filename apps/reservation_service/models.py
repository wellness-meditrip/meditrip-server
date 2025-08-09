"""
models.py - Reservation Service Database Models
예약 관리 시스템의 데이터베이스 모델 정의
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, Time, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, date, time
from enum import Enum
import pytz

Base = declarative_base()

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

class ReservationStatus(str, Enum):
    """예약 상태"""
    PENDING = "PENDING"      # 대기
    CONFIRMED = "CONFIRMED"  # 확정
    COMPLETED = "COMPLETED"  # 완료
    CANCELLED = "CANCELLED"  # 취소

class InterpreterLanguage(str, Enum):
    """통역 언어"""
    KOREAN = "한국어"
    JAPANESE = "일본어"
    ENGLISH = "영어"

class Reservation(Base):
    """예약 메인 테이블"""
    __tablename__ = "reservations"

    reservation_id = Column(Integer, primary_key=True, index=True, comment="예약 ID")
    
    # 외래키 관계
    user_id = Column(Integer, nullable=False, comment="사용자 ID (auth-service 참조)")
    hospital_id = Column(Integer, nullable=False, comment="병원 ID (hospital-service 참조)")
    doctor_id = Column(Integer, nullable=True, comment="의사 ID (doctor-service 참조)")
    
    # 진료 정보
    symptoms = Column(Text, nullable=False, comment="진료목적/증상")
    current_medications = Column(Text, nullable=True, comment="복용중인 약물 (선택사항)")
    
    # 예약 날짜 및 시간
    reservation_date = Column(Date, nullable=False, comment="예약 날짜")
    reservation_time = Column(Time, nullable=False, comment="예약 시간")
    
    # 연락처 정보
    contact_email = Column(String(100), nullable=False, comment="이메일 연락처")
    contact_phone = Column(String(20), nullable=False, comment="전화번호")
    
    # 통역 및 기타 정보
    interpreter_language = Column(String(20), nullable=False, comment="통역 언어")
    additional_notes = Column(Text, nullable=True, comment="기타정보/문의사항")
    
    # 예약 상태
    status = Column(String(20), default=ReservationStatus.PENDING, comment="예약 상태")
    
    # 메타 정보
    created_at = Column(DateTime, default=lambda: datetime.now(KST), comment="예약 생성일시")
    updated_at = Column(DateTime, default=lambda: datetime.now(KST), onupdate=lambda: datetime.now(KST), comment="수정일시")
    
    # 관계 설정
    images = relationship("ReservationImage", back_populates="reservation", cascade="all, delete-orphan")

class ReservationImage(Base):
    """예약 첨부 이미지 (Base64 저장 방식)"""
    __tablename__ = "reservation_images"

    id = Column(Integer, primary_key=True, index=True, comment="이미지 ID")
    reservation_id = Column(Integer, ForeignKey("reservations.reservation_id", ondelete="CASCADE"), nullable=False, comment="예약 ID")
    
    # 이미지 정보 (Base64 저장 방식 - review-service와 동일)
    image_data = Column(Text, nullable=False, comment="Base64 인코딩된 이미지 데이터")
    image_type = Column(String(10), nullable=False, comment="이미지 타입 (jpg, png, webp)")
    original_filename = Column(String(255), nullable=True, comment="원본 파일명")
    file_size = Column(Integer, nullable=False, comment="파일 크기 (bytes)")
    width = Column(Integer, nullable=True, comment="이미지 너비")
    height = Column(Integer, nullable=True, comment="이미지 높이")
    image_order = Column(Integer, default=1, comment="이미지 순서")
    alt_text = Column(String(200), nullable=True, comment="이미지 설명")
    
    # 메타 정보
    created_at = Column(DateTime, default=lambda: datetime.now(KST), comment="생성일시")
    
    # 관계 설정
    reservation = relationship("Reservation", back_populates="images")