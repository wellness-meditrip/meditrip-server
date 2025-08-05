"""
models.py - Hospital Service Database Models
병원 관리 시스템의 데이터베이스 모델 정의
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz

Base = declarative_base()

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

class Hospital(Base):
    """병원 기본 정보"""
    __tablename__ = "hospitals"

    hospital_id = Column(Integer, primary_key=True, index=True, comment="병원 ID")
    hospital_name = Column(String(100), nullable=False, comment="병원명")
    address = Column(String(200), nullable=False, comment="병원 주소")
    contact = Column(String(50), nullable=True, comment="연락처")
    
    # SNS 및 웹사이트 링크
    website = Column(String(200), nullable=True, comment="웹사이트 링크")
    line = Column(String(200), nullable=True, comment="라인 링크")
    instagram = Column(String(200), nullable=True, comment="인스타그램 링크")
    youtube = Column(String(200), nullable=True, comment="유튜브 링크")
    
    # 개설일자
    established_date = Column(Date, nullable=True, comment="개설일자")
    
    # 병원 소개 (다국어)
    hospital_description = Column(Text, nullable=True, comment="병원 소개")
    hospital_description_jp = Column(Text, nullable=True, comment="병원 소개(일본어)")
    hospital_description_en = Column(Text, nullable=True, comment="병원 소개(영어)")
    
    # 병원 주소 (다국어)
    hospital_address_jp = Column(String(200), nullable=True, comment="병원 주소(일본어)")
    hospital_address_en = Column(String(200), nullable=True, comment="병원 주소(영어)")
    
    # 메타 정보
    created_at = Column(DateTime, default=lambda: datetime.now(KST), comment="생성일시")
    updated_at = Column(DateTime, default=lambda: datetime.now(KST), onupdate=lambda: datetime.now(KST), comment="수정일시")

    # 관계 설정
    hospital_details = relationship("HospitalDetail", back_populates="hospital", cascade="all, delete-orphan")


class HospitalDetail(Base):
    """병원 세부 정보"""
    __tablename__ = "hospital_details"

    id = Column(Integer, primary_key=True, index=True, comment="세부정보 ID")
    hospital_id = Column(Integer, ForeignKey("hospitals.hospital_id", ondelete="CASCADE"), nullable=False, comment="병원 ID")
    
    # 편의시설 정보
    parking_available = Column(Boolean, default=False, comment="주차장 유무")
    parking_description = Column(String(200), nullable=True, comment="주차장 설명")
    
    wifi_available = Column(Boolean, default=False, comment="무료 와이파이")
    wifi_description = Column(String(200), nullable=True, comment="와이파이 설명")
    
    luggage_storage = Column(Boolean, default=False, comment="짐보관 서비스")
    luggage_storage_description = Column(String(200), nullable=True, comment="짐보관 설명")
    
    private_treatment = Column(Boolean, default=False, comment="프라이빗 진료")
    private_treatment_description = Column(String(200), nullable=True, comment="프라이빗 진료 설명")
    
    airport_pickup = Column(Boolean, default=False, comment="공항 픽업 서비스")
    airport_pickup_description = Column(String(200), nullable=True, comment="공항 픽업 설명")
    
    translation_service = Column(Boolean, default=False, comment="통역 서비스")
    translation_description = Column(String(200), nullable=True, comment="통역 서비스 설명")
    
    # 병원 운영시간 (JSON 형태로 저장)
    operating_hours = Column(Text, nullable=True, comment="병원 운영시간 (JSON)")
    
    # 이미지 정보 (JSON 형태로 저장)
    images = Column(Text, nullable=True, comment="병원 이미지 (JSON)")
    
    # 진료과목 (JSON 형태로 저장)
    departments = Column(Text, nullable=True, comment="진료과목 (JSON)")
    
    # 메타 정보
    created_at = Column(DateTime, default=lambda: datetime.now(KST), comment="생성일시")
    updated_at = Column(DateTime, default=lambda: datetime.now(KST), onupdate=lambda: datetime.now(KST), comment="수정일시")

    # 관계 설정
    hospital = relationship("Hospital", back_populates="hospital_details")