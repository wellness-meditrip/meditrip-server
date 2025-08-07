"""
Account Service Routes
계정 관리 및 프로필 이미지 관련 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional
import logging
import json
import base64
from datetime import datetime, timedelta
from PIL import Image
import io
import secrets

from database import get_database
from models import AccountDeletionLog, AccountRecoveryRequest, ProfileImage, ImageUploadHistory
from schemas import (
    AccountDeletionRequestDTO, AccountDeletionResponseDTO,
    AccountRecoveryRequestDTO, AccountRecoveryResponseDTO,
    ProfileImageUploadDTO, ProfileImageUpdateDTO, ProfileImageResponseDTO,
    ProfileImageListResponseDTO, ImageUploadHistoryResponseDTO,
    ApiResponseDTO, PaginatedResponseDTO, AccountDeletionSearchDTO,
    ImageHistorySearchDTO, AccountDeletionStatsDTO, ProfileImageStatsDTO
)

router = APIRouter()
logger = logging.getLogger(__name__)

# === Account Deletion APIs ===

@router.post("/delete-account", response_model=AccountDeletionResponseDTO, status_code=status.HTTP_200_OK)
async def delete_account(
    request_data: AccountDeletionRequestDTO,
    request: Request,
    db: Session = Depends(get_database)
):
    """
    사용자 계정 삭제
    
    - 계정 삭제 로그 생성
    - 30일 복구 기간 설정
    - 실제 계정은 auth_service에서 처리 (별도 API 호출 필요)
    """
    try:
        # IP 주소 및 User-Agent 추출
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        # 복구 기한 설정 (30일)
        recovery_deadline = datetime.utcnow() + timedelta(days=30)
        
        # 삭제 로그 생성
        deletion_log = AccountDeletionLog(
            user_id=request_data.user_id,
            email="temp@example.com",  # 실제로는 auth_service에서 가져와야 함
            deletion_reason=request_data.deletion_reason,
            deletion_type="user_request",
            recovery_deadline=recovery_deadline,
            ip_address=client_ip,
            user_agent=user_agent,
            is_recoverable=True
        )
        
        db.add(deletion_log)
        db.commit()
        db.refresh(deletion_log)
        
        logger.info(f"✅ 계정 삭제 로그 생성: user_id={request_data.user_id}, log_id={deletion_log.id}")
        
        return AccountDeletionResponseDTO(
            success=True,
            message=f"계정이 삭제되었습니다. {recovery_deadline.strftime('%Y-%m-%d')}까지 복구 가능합니다.",
            deletion_log_id=deletion_log.id,
            recovery_deadline=recovery_deadline
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 계정 삭제 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="계정 삭제 처리 중 오류가 발생했습니다."
        )

@router.post("/recover-account", response_model=AccountRecoveryResponseDTO)
async def request_account_recovery(
    recovery_data: AccountRecoveryRequestDTO,
    request: Request,
    db: Session = Depends(get_database)
):
    """
    계정 복구 요청
    """
    try:
        # 삭제된 계정 확인
        deletion_log = db.query(AccountDeletionLog).filter(
            and_(
                AccountDeletionLog.email == recovery_data.email,
                AccountDeletionLog.is_recoverable == True,
                AccountDeletionLog.recovery_deadline > datetime.utcnow()
            )
        ).first()
        
        if not deletion_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="복구 가능한 삭제된 계정을 찾을 수 없습니다."
            )
        
        # 복구 토큰 생성
        recovery_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # 복구 요청 생성
        recovery_request = AccountRecoveryRequest(
            deletion_log_id=deletion_log.id,
            email=recovery_data.email,
            recovery_token=recovery_token,
            expires_at=expires_at,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        db.add(recovery_request)
        db.commit()
        
        logger.info(f"✅ 계정 복구 요청 생성: email={recovery_data.email}")
        
        return AccountRecoveryResponseDTO(
            success=True,
            message="복구 요청이 접수되었습니다. 24시간 내에 복구 절차를 완료해주세요.",
            recovery_token=recovery_token,
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 계정 복구 요청 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="계정 복구 요청 처리 중 오류가 발생했습니다."
        )

# === Profile Image APIs ===

def process_base64_image(image_data: str, image_type: str) -> dict:
    """Base64 이미지 처리 및 메타데이터 추출"""
    try:
        # Data URL 형식 처리
        if image_data.startswith('data:image'):
            if ',' in image_data:
                image_data = image_data.split(',', 1)[1]
        
        # Base64 디코딩
        decoded_image = base64.b64decode(image_data)
        file_size = len(decoded_image)
        
        # PIL로 이미지 정보 추출
        image_io = io.BytesIO(decoded_image)
        with Image.open(image_io) as img:
            width, height = img.size
            format_type = img.format.lower() if img.format else image_type
        
        return {
            "file_size": file_size,
            "width": width,
            "height": height,
            "image_type": format_type,
            "processed_data": image_data
        }
        
    except Exception as e:
        raise ValueError(f"이미지 처리 중 오류: {str(e)}")

@router.post("/profile-image", response_model=ApiResponseDTO, status_code=status.HTTP_201_CREATED)
async def upload_profile_image(
    image_data: ProfileImageUploadDTO,
    request: Request,
    db: Session = Depends(get_database)
):
    """
    프로필 이미지 업로드 (Base64)
    """
    try:
        # 기존 이미지 확인
        existing_image = db.query(ProfileImage).filter(
            ProfileImage.user_id == image_data.user_id
        ).first()
        
        if existing_image:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 프로필 이미지가 존재합니다. 업데이트를 사용해주세요."
            )
        
        # 이미지 처리
        processed = process_base64_image(image_data.image_data, image_data.image_type.value)
        
        # 프로필 이미지 생성
        profile_image = ProfileImage(
            user_id=image_data.user_id,
            image_data=processed["processed_data"],
            image_type=processed["image_type"],
            original_filename=image_data.original_filename,
            file_size=processed["file_size"],
            width=processed["width"],
            height=processed["height"],
            upload_ip=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        db.add(profile_image)
        db.flush()
        
        # 업로드 히스토리 기록
        history = ImageUploadHistory(
            user_id=image_data.user_id,
            profile_image_id=profile_image.id,
            action_type="upload",
            original_filename=image_data.original_filename,
            file_size=processed["file_size"],
            image_type=processed["image_type"],
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        db.add(history)
        db.commit()
        
        logger.info(f"✅ 프로필 이미지 업로드 완료: user_id={image_data.user_id}, image_id={profile_image.id}")
        
        return ApiResponseDTO(
            success=True,
            message="프로필 이미지가 성공적으로 업로드되었습니다.",
            data={"image_id": profile_image.id}
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 프로필 이미지 업로드 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 이미지 업로드 중 오류가 발생했습니다."
        )

@router.put("/profile-image/{user_id}", response_model=ApiResponseDTO)
async def update_profile_image(
    user_id: int,
    image_data: ProfileImageUpdateDTO,
    request: Request,
    db: Session = Depends(get_database)
):
    """
    프로필 이미지 업데이트
    """
    try:
        # 기존 이미지 확인
        existing_image = db.query(ProfileImage).filter(
            ProfileImage.user_id == user_id
        ).first()
        
        if not existing_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로필 이미지를 찾을 수 없습니다."
            )
        
        # 이미지 처리
        processed = process_base64_image(image_data.image_data, image_data.image_type.value)
        
        # 기존 이미지 업데이트
        existing_image.image_data = processed["processed_data"]
        existing_image.image_type = processed["image_type"]
        existing_image.original_filename = image_data.original_filename
        existing_image.file_size = processed["file_size"]
        existing_image.width = processed["width"]
        existing_image.height = processed["height"]
        existing_image.updated_at = datetime.utcnow()
        
        # 업로드 히스토리 기록
        history = ImageUploadHistory(
            user_id=user_id,
            profile_image_id=existing_image.id,
            action_type="update",
            original_filename=image_data.original_filename,
            file_size=processed["file_size"],
            image_type=processed["image_type"],
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        db.add(history)
        db.commit()
        
        logger.info(f"✅ 프로필 이미지 업데이트 완료: user_id={user_id}")
        
        return ApiResponseDTO(
            success=True,
            message="프로필 이미지가 성공적으로 업데이트되었습니다."
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 프로필 이미지 업데이트 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 이미지 업데이트 중 오류가 발생했습니다."
        )

@router.get("/profile-image/{user_id}", response_model=ProfileImageResponseDTO)
async def get_profile_image(
    user_id: int,
    db: Session = Depends(get_database)
):
    """
    프로필 이미지 조회
    """
    try:
        profile_image = db.query(ProfileImage).filter(
            and_(
                ProfileImage.user_id == user_id,
                ProfileImage.is_active == True
            )
        ).first()
        
        if not profile_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로필 이미지를 찾을 수 없습니다."
            )
        
        return profile_image
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 프로필 이미지 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 이미지 조회 중 오류가 발생했습니다."
        )

@router.delete("/profile-image/{user_id}", response_model=ApiResponseDTO)
async def delete_profile_image(
    user_id: int,
    request: Request,
    db: Session = Depends(get_database)
):
    """
    프로필 이미지 삭제 (소프트 삭제)
    """
    try:
        profile_image = db.query(ProfileImage).filter(
            ProfileImage.user_id == user_id
        ).first()
        
        if not profile_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="프로필 이미지를 찾을 수 없습니다."
            )
        
        # 소프트 삭제
        profile_image.is_active = False
        profile_image.updated_at = datetime.utcnow()
        
        # 삭제 히스토리 기록
        history = ImageUploadHistory(
            user_id=user_id,
            profile_image_id=profile_image.id,
            action_type="delete",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        db.add(history)
        db.commit()
        
        logger.info(f"✅ 프로필 이미지 삭제 완료: user_id={user_id}")
        
        return ApiResponseDTO(
            success=True,
            message="프로필 이미지가 성공적으로 삭제되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 프로필 이미지 삭제 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 이미지 삭제 중 오류가 발생했습니다."
        )

# === Statistics APIs ===

@router.get("/stats/deletions", response_model=AccountDeletionStatsDTO)
async def get_deletion_stats(
    db: Session = Depends(get_database)
):
    """
    계정 삭제 통계 조회
    """
    try:
        # 전체 삭제 수
        total_deletions = db.query(AccountDeletionLog).count()
        
        # 삭제 유형별 통계
        user_requests = db.query(AccountDeletionLog).filter(
            AccountDeletionLog.deletion_type == "user_request"
        ).count()
        
        admin_actions = db.query(AccountDeletionLog).filter(
            AccountDeletionLog.deletion_type == "admin_action"
        ).count()
        
        system_cleanups = db.query(AccountDeletionLog).filter(
            AccountDeletionLog.deletion_type == "system_cleanup"
        ).count()
        
        # 복구 관련 통계
        recoverable_accounts = db.query(AccountDeletionLog).filter(
            and_(
                AccountDeletionLog.is_recoverable == True,
                AccountDeletionLog.recovery_deadline > datetime.utcnow()
            )
        ).count()
        
        recovered_accounts = db.query(AccountRecoveryRequest).filter(
            AccountRecoveryRequest.status == "approved"
        ).count()
        
        permanent_deletions = total_deletions - recoverable_accounts
        
        return AccountDeletionStatsDTO(
            total_deletions=total_deletions,
            user_requests=user_requests,
            admin_actions=admin_actions,
            system_cleanups=system_cleanups,
            recoverable_accounts=recoverable_accounts,
            recovered_accounts=recovered_accounts,
            permanent_deletions=permanent_deletions
        )
        
    except Exception as e:
        logger.error(f"❌ 삭제 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="삭제 통계 조회 중 오류가 발생했습니다."
        )

@router.get("/stats/images", response_model=ProfileImageStatsDTO)
async def get_image_stats(
    db: Session = Depends(get_database)
):
    """
    프로필 이미지 통계 조회
    """
    try:
        # 기본 통계
        total_images = db.query(ProfileImage).count()
        active_images = db.query(ProfileImage).filter(ProfileImage.is_active == True).count()
        verified_images = db.query(ProfileImage).filter(ProfileImage.is_verified == True).count()
        
        # 크기 통계
        size_stats = db.query(func.sum(ProfileImage.file_size), func.avg(ProfileImage.file_size)).first()
        total_size = size_stats[0] or 0
        average_size = int(size_stats[1]) if size_stats[1] else 0
        
        # 가장 많이 사용되는 이미지 타입
        type_stats = db.query(
            ProfileImage.image_type,
            func.count(ProfileImage.image_type)
        ).group_by(ProfileImage.image_type).order_by(desc(func.count(ProfileImage.image_type))).first()
        
        most_common_type = type_stats[0] if type_stats else "none"
        
        # 압축률 (임시로 50%로 설정)
        compression_rate = 50.0
        
        return ProfileImageStatsDTO(
            total_images=total_images,
            active_images=active_images,
            verified_images=verified_images,
            total_size=total_size,
            average_size=average_size,
            most_common_type=most_common_type,
            compression_rate=compression_rate
        )
        
    except Exception as e:
        logger.error(f"❌ 이미지 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 통계 조회 중 오류가 발생했습니다."
        )

# === Health Check ===

@router.get("/health", response_model=ApiResponseDTO)
async def health_check(db: Session = Depends(get_database)):
    """헬스 체크"""
    try:
        from sqlalchemy import text
        # 간단한 DB 쿼리로 연결 확인
        db.execute(text("SELECT 1"))
        
        return ApiResponseDTO(
            success=True,
            message="Account Service is healthy"
        )
        
    except Exception as e:
        logger.error(f"❌ 헬스 체크 실패: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")