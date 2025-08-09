"""
개인 프로필 관리 API 라우터
프로필 생성, 조회, 업데이트, 삭제
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from common.base import get_db
from services.profile_service import ProfileService
from services.jwt_service import JWTService
from dto.auth import (
    ProfileCreateDTO,
    ProfileUpdateDTO,
    UserProfileDTO
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/profile",
    tags=["Profile Management"],
    responses={404: {"description": "Not found"}}
)

@router.post("/create", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreateDTO,
    current_user: dict = Depends(JWTService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    개인 프로필 최초 생성
    
    회원가입 후 개인 정보를 설정합니다.
    
    - **gender**: 성별 (male/female, 선택사항)
    - **birthdate**: 생년월일 (선택사항)
    - **height**: 키 (cm, 선택사항)
    - **weight**: 몸무게 (kg, 선택사항)
    - **topics_of_interest**: 관심사 목록 (선택사항)
    
    JWT 토큰을 Authorization 헤더에 포함해야 합니다.
    """
    try:
        user_id = current_user["user_id"]
        result = ProfileService.create_profile(user_id, profile_data, db)
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"프로필 생성 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 생성 중 오류가 발생했습니다."
        )

@router.get("/", response_model=UserProfileDTO)
async def get_profile(
    current_user: dict = Depends(JWTService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    현재 사용자 프로필 조회
    
    JWT 토큰을 Authorization 헤더에 포함해야 합니다.
    프로필 완성도도 함께 반환합니다.
    """
    try:
        user_id = current_user["user_id"]
        profile = ProfileService.get_profile(user_id, db)
        
        return UserProfileDTO(**profile)
        
    except Exception as e:
        logger.error(f"프로필 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 조회 중 오류가 발생했습니다."
        )

@router.put("/update", response_model=dict)
async def update_profile(
    profile_data: ProfileUpdateDTO,
    current_user: dict = Depends(JWTService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자 프로필 업데이트
    
    - **nickname**: 닉네임 (2-50자, 선택사항)
    - **gender**: 성별 (male/female, 선택사항)
    - **birthdate**: 생년월일 (선택사항)
    - **height**: 키 (cm, 선택사항)
    - **weight**: 몸무게 (kg, 선택사항)
    - **topics_of_interest**: 관심사 목록 (선택사항)
    - **marketing_agreement**: 마케팅 수신 동의 (선택사항)
    
    JWT 토큰을 Authorization 헤더에 포함해야 합니다.
    """
    try:
        user_id = current_user["user_id"]
        result = ProfileService.update_profile(user_id, profile_data, db)
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"프로필 업데이트 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 업데이트 중 오류가 발생했습니다."
        )

@router.delete("/reset", response_model=dict)
async def reset_profile(
    current_user: dict = Depends(JWTService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    프로필 데이터 초기화
    
    개인 정보(성별, 생년월일, 키, 몸무게, 관심사)를 모두 삭제합니다.
    기본 정보(이메일, 닉네임, 국가)는 유지됩니다.
    
    JWT 토큰을 Authorization 헤더에 포함해야 합니다.
    """
    try:
        user_id = current_user["user_id"]
        result = ProfileService.delete_profile_data(user_id, db)
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"프로필 초기화 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 초기화 중 오류가 발생했습니다."
        )

@router.get("/completion", response_model=dict)
async def get_profile_completion(
    current_user: dict = Depends(JWTService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    프로필 완성도 조회
    
    사용자 프로필의 완성도를 퍼센트로 반환합니다.
    JWT 토큰을 Authorization 헤더에 포함해야 합니다.
    """
    try:
        user_id = current_user["user_id"]
        profile = ProfileService.get_profile(user_id, db)
        
        return {
            "profile_completion": profile["profile_completion"],
            "completed_fields": [
                field for field in ["gender", "birthdate", "height", "weight", "topics_of_interest"]
                if profile.get(field) is not None and profile.get(field) != []
            ],
            "missing_fields": [
                field for field in ["gender", "birthdate", "height", "weight", "topics_of_interest"]
                if profile.get(field) is None or profile.get(field) == []
            ]
        }
        
    except Exception as e:
        logger.error(f"프로필 완성도 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 완성도 조회 중 오류가 발생했습니다."
        )

@router.get("/user/{user_id}", response_model=dict)
async def get_user_basic_info(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    사용자 기본 정보 조회 (review-service 등에서 사용)
    
    user_id로 사용자의 기본 정보(username, email, nickname)를 조회합니다.
    """
    try:
        from repository.user import UserRepository
        
        user = UserRepository.get_by_id(user_id, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "nickname": user.nickname
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 기본 정보 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 정보 조회 중 오류가 발생했습니다."
        )