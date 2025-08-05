"""
doctor_service의 데이터베이스 모델들
SQLAlchemy ORM을 사용하여 PostgreSQL과 연동
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Time, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Doctor(Base):
    """의사 기본정보 테이블"""
    __tablename__ = "doctors"
    
    # 의사 고유 ID (Primary Key)
    doctor_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 의사 기본 정보
    doctor_name = Column(String(100), nullable=False, comment="의사 이름")
    doctor_position = Column(String(50), nullable=True, comment="의사 직급 (전문의, 부원장 등)")
    doctor_phone = Column(String(20), nullable=True, comment="의사 연락처")
    license_number = Column(String(50), unique=True, nullable=False, comment="의사 면허번호")
    bio = Column(Text, nullable=True, comment="의사 소개/약력")
    profile_image = Column(String(255), nullable=True, comment="프로필 이미지 URL")
    
    # 병원 정보
    hospital_id = Column(Integer, nullable=False, comment="소속 병원 ID (hospital_service와 연결)")
    
    # 생성/수정 시간 자동 관리
    created_at = Column(DateTime, default=datetime.utcnow, comment="생성일시")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="수정일시")
    
    # 다른 테이블과의 관계 설정 (1:다 관계)
    specializations = relationship("DoctorSpecialization", back_populates="doctor")
    statistics = relationship("DoctorStatistics", back_populates="doctor", uselist=False)  # 1:1 관계
    fees = relationship("DoctorFees", back_populates="doctor")
    schedules = relationship("DoctorSchedule", back_populates="doctor")
    
    def __repr__(self):
        return f"<Doctor(id={self.doctor_id}, name={self.doctor_name})>"


class DoctorSpecialization(Base):
    """의사 전문과목 테이블"""
    __tablename__ = "doctor_specializations"
    
    # 전문과목명이 Primary Key (예: "내과", "외과", "정형외과")
    specializations_name = Column(String(50), primary_key=True, comment="전문과목명")
    
    # 외래키 설정
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), primary_key=True, comment="의사 ID")
    hospital_id = Column(Integer, nullable=False, comment="병원 ID (hospital_service와 연결)")
    
    # 다른 테이블과의 관계 설정
    doctor = relationship("Doctor", back_populates="specializations")
    
    def __repr__(self):
        return f"<DoctorSpecialization(doctor_id={self.doctor_id}, specialty={self.specializations_name})>"


class DoctorStatistics(Base):
    """의사 통계정보 테이블"""
    __tablename__ = "doctor_statistics"
    
    # 의사 ID가 Primary Key이면서 Foreign Key (1:1 관계)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), primary_key=True, comment="의사 ID")
    
    # 통계 정보들
    rating_average = Column(Float, default=0.0, comment="평균 평점 (0.0 ~ 5.0)")
    total_reviews = Column(Integer, default=0, comment="총 리뷰 개수")
    total_patients = Column(Integer, default=0, comment="총 진료 환자 수")
    
    # 다른 테이블과의 관계 설정
    doctor = relationship("Doctor", back_populates="statistics")
    
    def __repr__(self):
        return f"<DoctorStatistics(doctor_id={self.doctor_id}, avg_rating={self.rating_average})>"


class DoctorFees(Base):
    """의사 진료비 테이블"""
    __tablename__ = "doctor_fees"
    
    # 진료비 고유 ID (Primary Key)  
    fee_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 외래키 설정
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False, comment="의사 ID")
    package_id = Column(Integer, nullable=False, comment="패키지 ID (package_service와 연결)")
    
    # 실제 금액 필드는 나중에 추가 예정
    
    # 다른 테이블과의 관계 설정
    doctor = relationship("Doctor", back_populates="fees")
    
    def __repr__(self):
        return f"<DoctorFees(fee_id={self.fee_id}, doctor_id={self.doctor_id})>"


class DoctorSchedule(Base):
    """의사 근무일정 테이블"""
    __tablename__ = "doctor_schedules"
    
    # 일정 고유 ID (Primary Key)
    schedule_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 외래키 설정
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False, comment="의사 ID")
    
    # 근무 일정 정보
    available_days = Column(String(20), nullable=False, comment="근무 요일 (예: '월,화,수,목,금')")
    work_start_time = Column(Time, nullable=False, comment="근무 시작 시간")
    work_end_time = Column(Time, nullable=False, comment="근무 종료 시간")
    
    # 다른 테이블과의 관계 설정
    doctor = relationship("Doctor", back_populates="schedules")
    
    def __repr__(self):
        return f"<DoctorSchedule(schedule_id={self.schedule_id}, doctor_id={self.doctor_id})>"