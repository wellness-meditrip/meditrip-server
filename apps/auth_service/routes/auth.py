from fastapi import APIRouter, HTTPException, Cookie, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from services.jwt_service import JWTService
from repository.user import UserRepository

security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/auth", tags=["auth"])

# 사용자 인증 의존성 함수
async def get_current_user(
    access_token: Optional[str] = Cookie(None),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """쿠키 또는 Authorization 헤더에서 현재 사용자 추출"""
    token = None
    
    # Authorization 헤더에서 토큰 추출 (우선순위)
    if authorization:
        token = authorization.credentials
    # 쿠키에서 토큰 추출 (대안)
    elif access_token:
        token = access_token
    
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    return JWTService.get_current_user_from_token(token)

@router.get("/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """현재 로그인된 사용자 정보 조회"""
    return {
        "success": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "nickname": current_user.nickname,
            "line_id": current_user.line_id,
            "google_id": current_user.google_id,
            "country_id": current_user.country_id,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            "is_active": current_user.is_active
        }
    }

@router.post("/logout")
async def logout(response: Response, current_user = Depends(get_current_user)):
    """로그아웃 - 쿠키 삭제 및 리프레시 토큰 무효화"""
    
    # 리프레시 토큰 무효화
    UserRepository.revoke_refresh_token(current_user.id)
    
    # 쿠키 삭제
    response.delete_cookie(key="access_token", httponly=True, secure=True, samesite="lax")
    response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="lax")
    
    return {
        "success": True,
        "message": "로그아웃되었습니다"
    }