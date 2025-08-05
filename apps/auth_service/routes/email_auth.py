"""
이메일/비밀번호 기반 인증 API 라우터
회원가입, 로그인, 토큰 갱신, 프로필 관리
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from common.base import get_db
from services.email_auth_service import EmailAuthService
from services.jwt_service import JWTService
from services.password_service import PasswordService
from dto.auth import (
    RegisterRequestDTO, 
    LoginRequestDTO, 
    TokenRefreshRequestDTO,
    AuthResponseDTO,
    PasswordChangeDTO
)
from repository.user import UserRepository
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth/email",
    tags=["Email Authentication"],
    responses={404: {"description": "Not found"}}
)

@router.post("/register", response_model=AuthResponseDTO, status_code=status.HTTP_201_CREATED)
async def register(
    register_data: RegisterRequestDTO,
    db: Session = Depends(get_db)
):
    """
    이메일/비밀번호 기반 회원가입 - 기본 정보만
    
    - **email**: 이메일 주소 (유효한 형식)
    - **password**: 비밀번호 (8자 이상, 영문/숫자 혼합)
    - **confirm_password**: 비밀번호 확인
    - **nickname**: 닉네임 (2-50자)
    - **country_id**: 국가 ID
    - **terms_agreement**: 약관 동의 (필수)
    - **marketing_agreement**: 마케팅 수신 동의 (선택)
    
    개인 정보(성별, 생년월일, 키, 몸무게, 관심사)는 회원가입 후 별도 프로필 API로 설정하세요.
    """
    try:
        # 비밀번호 강도 검사
        is_strong, message = PasswordService.is_password_strong(register_data.password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        result = EmailAuthService.register_user(register_data, db)
        
        return AuthResponseDTO(
            success=result["success"],
            message=result["message"],
            user=result["user"],
            tokens=result["tokens"],
            is_new_user=result["is_new_user"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"회원가입 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 처리 중 오류가 발생했습니다."
        )

@router.post("/login", response_model=AuthResponseDTO)
async def login(
    login_data: LoginRequestDTO,
    db: Session = Depends(get_db)
):
    """
    이메일/비밀번호 기반 로그인
    
    - **email**: 이메일 주소
    - **password**: 비밀번호
    - **remember_me**: 로그인 상태 유지 (선택)
    """
    try:
        result = EmailAuthService.login_user(login_data, db)
        
        return AuthResponseDTO(
            success=result["success"],
            message=result["message"],
            user=result["user"],
            tokens=result["tokens"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"로그인 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다."
        )

@router.post("/refresh", response_model=dict)
async def refresh_token(
    token_data: TokenRefreshRequestDTO,
    db: Session = Depends(get_db)
):
    """
    JWT 토큰 갱신
    
    - **refresh_token**: 리프레시 토큰
    """
    try:
        # 리프레시 토큰 검증
        payload = JWTService.verify_refresh_token(token_data.refresh_token)
        user_id = payload["user_id"]
        
        # 저장된 리프레시 토큰과 비교
        stored_token = UserRepository.get_refresh_token(user_id, db)
        if not stored_token or stored_token != token_data.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 리프레시 토큰입니다."
            )
        
        # 사용자 정보 조회
        user = UserRepository.get_by_id(user_id, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 새로운 토큰 생성
        new_tokens = JWTService.create_token_pair(user.id, user.email)
        
        # 새로운 리프레시 토큰 저장
        UserRepository.update_refresh_token(user.id, new_tokens["refresh_token"], db)
        
        return {
            "success": True,
            "message": "토큰이 성공적으로 갱신되었습니다.",
            "tokens": new_tokens
        }
        
    except Exception as e:
        logger.error(f"토큰 갱신 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 갱신에 실패했습니다."
        )

@router.put("/password", response_model=dict)
async def change_password(
    password_data: PasswordChangeDTO,
    current_user: dict = Depends(JWTService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    비밀번호 변경
    
    - **current_password**: 현재 비밀번호
    - **new_password**: 새 비밀번호 (8자 이상, 영문/숫자 혼합)
    - **confirm_new_password**: 새 비밀번호 확인
    
    JWT 토큰을 Authorization 헤더에 포함해야 합니다.
    """
    try:
        # 새 비밀번호 강도 검사
        is_strong, message = PasswordService.is_password_strong(password_data.new_password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        user_id = current_user["user_id"]
        result = EmailAuthService.change_password(
            user_id, 
            password_data.current_password, 
            password_data.new_password, 
            db
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"비밀번호 변경 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 변경 중 오류가 발생했습니다."
        )

@router.post("/logout", response_model=dict)
async def logout(
    current_user: dict = Depends(JWTService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    로그아웃
    
    사용자의 리프레시 토큰을 무효화합니다.
    JWT 토큰을 Authorization 헤더에 포함해야 합니다.
    """
    try:
        user_id = current_user["user_id"]
        
        # 리프레시 토큰 제거
        UserRepository.clear_refresh_token(user_id, db)
        
        return {
            "success": True,
            "message": "성공적으로 로그아웃되었습니다."
        }
        
    except Exception as e:
        logger.error(f"로그아웃 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그아웃 처리 중 오류가 발생했습니다."
        )