"""
models.py - Review Service Database Models
리뷰 관리 시스템의 데이터베이스 모델 정의
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz

Base = declarative_base()

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

class Review(Base):
    """리뷰 메인 테이블"""
    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, index=True, comment="리뷰 ID")
    hospital_id = Column(Integer, nullable=False, comment="병원 ID")
    user_id = Column(Integer, nullable=False, comment="사용자 ID")
    doctor_id = Column(Integer, nullable=True, comment="의사 ID")
    doctor_name = Column(String(100), nullable=True, comment="의사 이름")
    
    # 기본 리뷰 정보
    title = Column(String(200), nullable=False, comment="리뷰 제목")
    content = Column(Text, nullable=False, comment="리뷰 내용")
    rating = Column(Float, nullable=False, comment="전체 평점 (1.0 ~ 5.0)")
    
    # 리뷰 상태
    is_active = Column(Boolean, default=True, comment="활성 상태")
    
    # 메타 정보
    created_at = Column(DateTime, default=lambda: datetime.now(KST), comment="생성일시")
    updated_at = Column(DateTime, default=lambda: datetime.now(KST), onupdate=lambda: datetime.now(KST), comment="수정일시")

    # 관계 설정
    keywords = relationship("ReviewKeyword", back_populates="review", cascade="all, delete-orphan")
    images = relationship("ReviewImage", back_populates="review", cascade="all, delete-orphan")


class ReviewKeyword(Base):
    """리뷰 키워드 테이블"""
    __tablename__ = "review_keywords"

    id = Column(Integer, primary_key=True, index=True, comment="키워드 ID")
    review_id = Column(Integer, ForeignKey("reviews.review_id", ondelete="CASCADE"), nullable=False, comment="리뷰 ID")
    
    # 키워드 카테고리 및 정보
    category = Column(String(20), nullable=False, comment="키워드 카테고리 (CARE, SERVICE, FACILITY)")
    keyword_code = Column(String(50), nullable=False, comment="키워드 코드")
    keyword_name = Column(String(100), nullable=False, comment="키워드 이름")
    is_positive = Column(Boolean, nullable=False, comment="긍정/부정 여부")
    
    # 메타 정보
    created_at = Column(DateTime, default=lambda: datetime.now(KST), comment="생성일시")

    # 관계 설정
    review = relationship("Review", back_populates="keywords")


class ReviewImage(Base):
    """리뷰 이미지 테이블"""
    __tablename__ = "review_images"

    id = Column(Integer, primary_key=True, index=True, comment="이미지 ID")
    review_id = Column(Integer, ForeignKey("reviews.review_id", ondelete="CASCADE"), nullable=False, comment="리뷰 ID")
    
    # 이미지 정보 (Base64 저장 방식)
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
    review = relationship("Review", back_populates="images")


class ReviewKeywordTemplate(Base):
    """리뷰 키워드 템플릿 (마스터 데이터)"""
    __tablename__ = "review_keyword_templates"

    id = Column(Integer, primary_key=True, index=True, comment="템플릿 ID")
    
    # 키워드 정보
    category = Column(String(20), nullable=False, comment="키워드 카테고리 (CARE, SERVICE, FACILITY)")
    keyword_code = Column(String(50), unique=True, nullable=False, comment="키워드 코드")
    keyword_name = Column(String(100), nullable=False, comment="키워드 이름")
    is_positive = Column(Boolean, nullable=False, comment="긍정/부정 여부")
    
    # 다국어 지원
    keyword_name_en = Column(String(100), nullable=True, comment="키워드 이름 (영어)")
    keyword_name_jp = Column(String(100), nullable=True, comment="키워드 이름 (일본어)")
    
    # 메타 정보
    is_active = Column(Boolean, default=True, comment="활성 상태")
    created_at = Column(DateTime, default=lambda: datetime.now(KST), comment="생성일시")
    updated_at = Column(DateTime, default=lambda: datetime.now(KST), onupdate=lambda: datetime.now(KST), comment="수정일시")


class ReviewStats(Base):
    """병원별 리뷰 통계 테이블"""
    __tablename__ = "review_stats"

    id = Column(Integer, primary_key=True, index=True, comment="통계 ID")
    hospital_id = Column(Integer, unique=True, nullable=False, comment="병원 ID")
    
    # 전체 통계
    total_reviews = Column(Integer, default=0, comment="총 리뷰 수")
    average_rating = Column(Float, default=0.0, comment="평균 평점")
    
    # 평점별 분포
    rating_5 = Column(Integer, default=0, comment="5점 리뷰 수")
    rating_4 = Column(Integer, default=0, comment="4점 리뷰 수")
    rating_3 = Column(Integer, default=0, comment="3점 리뷰 수")
    rating_2 = Column(Integer, default=0, comment="2점 리뷰 수")
    rating_1 = Column(Integer, default=0, comment="1점 리뷰 수")
    
    # 키워드 통계 (JSON 형태로 저장)
    care_keywords = Column(JSON, comment="진료/치료 키워드 통계")
    service_keywords = Column(JSON, comment="서비스/가격 키워드 통계")
    facility_keywords = Column(JSON, comment="시설 키워드 통계")
    
    # 메타 정보
    last_updated = Column(DateTime, default=lambda: datetime.now(KST), onupdate=lambda: datetime.now(KST), comment="마지막 업데이트")