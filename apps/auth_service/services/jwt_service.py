import os
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets

security = HTTPBearer()

class JWTService:
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 30
    
    @staticmethod
    def create_access_token(user_id: int, email: str) -> str:
        """JWT 액세스 토큰 생성"""
        expire = datetime.utcnow() + timedelta(minutes=JWTService.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, JWTService.SECRET_KEY, algorithm=JWTService.ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: int) -> str:
        """리프레시 토큰 생성"""
        expire = datetime.utcnow() + timedelta(days=JWTService.REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(32)  # JWT ID for token revocation
        }
        return jwt.encode(payload, JWTService.SECRET_KEY, algorithm=JWTService.ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        """토큰 검증 및 페이로드 반환"""
        try:
            payload = jwt.decode(token, JWTService.SECRET_KEY, algorithms=[JWTService.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    @staticmethod
    def verify_refresh_token(token: str) -> Optional[Dict]:
        """리프레시 토큰 검증"""
        payload = JWTService.verify_token(token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        return payload
    
    @staticmethod
    def create_token_pair(user_id: int, email: str) -> Dict[str, str]:
        """액세스 토큰과 리프레시 토큰 쌍 생성"""
        access_token = JWTService.create_access_token(user_id, email)
        refresh_token = JWTService.create_refresh_token(user_id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": JWTService.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    @staticmethod
    def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """JWT 토큰에서 현재 사용자 정보 추출 (FastAPI Dependency)"""
        token = credentials.credentials
        
        payload = JWTService.verify_token(token)
        if not payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return {
            "user_id": user_id,
            "email": email,
            "exp": payload.get("exp"),
            "iat": payload.get("iat")
        }
    
    @staticmethod
    def get_current_user_from_token(token: str):
        """토큰에서 현재 사용자 정보 추출 (직접 사용)"""
        from repository.user import UserRepository
        from common.base import get_db
        
        payload = JWTService.verify_token(token)
        if not payload or payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # 데이터베이스 세션이 필요한 경우에만 사용
        db = next(get_db())
        try:
            user = UserRepository.get_by_id(user_id, db)
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            
            if not user.is_active:
                raise HTTPException(status_code=401, detail="User account is disabled")
            
            return user
        finally:
            db.close()