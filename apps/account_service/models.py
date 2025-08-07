"""
Account Service Models
계정 관리 및 프로필 이미지 관련 데이터베이스 모델
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class AccountDeletionLog(Base):
    """
    계정 삭제 로그 모델
    사용자 계정 삭제 시 기록을 남기기 위한 테이블
    """
    __tablename__ = "account_deletion_logs"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, index=True, comment="로그 ID")
    user_id = Column(Integer, nullable=False, comment="삭제된 사용자 ID")
    email = Column(String(320), nullable=False, comment="삭제된 사용자 이메일")
    nickname = Column(String(50), nullable=True, comment="삭제된 사용자 닉네임")
    
    # 삭제 관련 정보
    deletion_reason = Column(String(200), nullable=True, comment="삭제 사유 (선택사항)")
    deletion_type = Column(String(20), nullable=False, default="user_request", comment="삭제 유형 (user_request, admin_action, system_cleanup)")
    
    # 사용자 통계 (삭제 시점 기준)
    account_created_at = Column(DateTime, nullable=True, comment="계정 생성일")
    last_login_at = Column(DateTime, nullable=True, comment="마지막 로그인")
    total_reviews = Column(Integer, default=0, comment="작성한 리뷰 수")
    total_reservations = Column(Integer, default=0, comment="예약 건수")
    
    # 메타 정보
    deleted_at = Column(DateTime, default=datetime.utcnow, comment="삭제 처리 시간")
    deleted_by_admin = Column(Boolean, default=False, comment="관리자에 의한 삭제 여부")
    admin_id = Column(Integer, nullable=True, comment="삭제 처리한 관리자 ID")
    
    # 복구 관련
    is_recoverable = Column(Boolean, default=True, comment="복구 가능 여부")
    recovery_deadline = Column(DateTime, nullable=True, comment="복구 가능 기한")
    
    # 추가 정보
    user_agent = Column(String(500), nullable=True, comment="삭제 요청 시 User-Agent")
    ip_address = Column(String(45), nullable=True, comment="삭제 요청 IP 주소")
    additional_data = Column(Text, nullable=True, comment="추가 데이터 (JSON 형태)")
    
    def __repr__(self):
        return f"<AccountDeletionLog(id={self.id}, user_id={self.user_id}, email={self.email})>"

class AccountRecoveryRequest(Base):
    """
    계정 복구 요청 모델
    삭제된 계정의 복구 요청을 관리하기 위한 테이블
    """
    __tablename__ = "account_recovery_requests"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, index=True, comment="요청 ID")
    deletion_log_id = Column(Integer, nullable=False, comment="삭제 로그 ID")
    email = Column(String(320), nullable=False, comment="복구 요청 이메일")
    
    # 요청 정보
    recovery_token = Column(String(255), nullable=False, unique=True, comment="복구 토큰")
    requested_at = Column(DateTime, default=datetime.utcnow, comment="복구 요청 시간")
    expires_at = Column(DateTime, nullable=False, comment="토큰 만료 시간")
    
    # 처리 상태
    status = Column(String(20), default="pending", comment="처리 상태 (pending, approved, rejected, expired)")
    processed_at = Column(DateTime, nullable=True, comment="처리 완료 시간")
    processed_by_admin = Column(Integer, nullable=True, comment="처리한 관리자 ID")
    
    # 검증 정보
    verification_code = Column(String(10), nullable=True, comment="인증 코드")
    verification_attempts = Column(Integer, default=0, comment="인증 시도 횟수")
    is_verified = Column(Boolean, default=False, comment="이메일 인증 완료 여부")
    
    # 메타 정보
    user_agent = Column(String(500), nullable=True, comment="요청 시 User-Agent")
    ip_address = Column(String(45), nullable=True, comment="요청 IP 주소")
    rejection_reason = Column(String(200), nullable=True, comment="거절 사유")
    
    def __repr__(self):
        return f"<AccountRecoveryRequest(id={self.id}, email={self.email}, status={self.status})>"

class ProfileImage(Base):
    """
    프로필 이미지 모델
    사용자 프로필 이미지 관리 (base64 저장 지원)
    """
    __tablename__ = "profile_images"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, index=True, comment="이미지 ID")
    user_id = Column(Integer, nullable=False, unique=True, comment="사용자 ID (고유)")
    
    # 이미지 데이터
    image_data = Column(Text, nullable=False, comment="Base64 인코딩된 이미지 데이터")
    image_type = Column(String(10), nullable=False, comment="이미지 타입 (jpg, png, webp)")
    original_filename = Column(String(255), nullable=True, comment="원본 파일명")
    
    # 이미지 메타데이터
    file_size = Column(Integer, nullable=False, comment="파일 크기 (바이트)")
    width = Column(Integer, nullable=True, comment="이미지 너비 (픽셀)")
    height = Column(Integer, nullable=True, comment="이미지 높이 (픽셀)")
    
    # 압축 정보
    is_compressed = Column(Boolean, default=False, comment="압축 여부")
    compression_quality = Column(Integer, nullable=True, comment="압축 품질 (1-100)")
    original_size = Column(Integer, nullable=True, comment="압축 전 원본 크기")
    
    # 시간 정보
    created_at = Column(DateTime, default=datetime.utcnow, comment="업로드 시간")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="수정 시간")
    
    # 메타 정보
    upload_ip = Column(String(45), nullable=True, comment="업로드 IP 주소")
    user_agent = Column(String(500), nullable=True, comment="업로드 시 User-Agent")
    
    # 상태 관리
    is_active = Column(Boolean, default=True, comment="활성 상태")
    is_verified = Column(Boolean, default=False, comment="이미지 검증 상태")
    
    def __repr__(self):
        return f"<ProfileImage(id={self.id}, user_id={self.user_id}, type={self.image_type})>"

class ImageUploadHistory(Base):
    """
    이미지 업로드 히스토리 모델
    프로필 이미지 변경 이력 추적
    """
    __tablename__ = "image_upload_history"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, index=True, comment="히스토리 ID")
    user_id = Column(Integer, nullable=False, comment="사용자 ID")
    profile_image_id = Column(Integer, nullable=True, comment="프로필 이미지 ID (삭제된 경우 NULL)")
    
    # 업로드 정보
    action_type = Column(String(20), nullable=False, comment="액션 타입 (upload, update, delete)")
    original_filename = Column(String(255), nullable=True, comment="원본 파일명")
    file_size = Column(Integer, nullable=True, comment="파일 크기")
    image_type = Column(String(10), nullable=True, comment="이미지 타입")
    
    # 시간 정보
    created_at = Column(DateTime, default=datetime.utcnow, comment="액션 실행 시간")
    
    # 메타 정보
    ip_address = Column(String(45), nullable=True, comment="요청 IP 주소")
    user_agent = Column(String(500), nullable=True, comment="요청 시 User-Agent")
    result_status = Column(String(20), nullable=False, default="success", comment="결과 상태 (success, failed)")
    error_message = Column(String(500), nullable=True, comment="에러 메시지 (실패 시)")
    
    def __repr__(self):
        return f"<ImageUploadHistory(id={self.id}, user_id={self.user_id}, action={self.action_type})>"