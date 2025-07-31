import os
import requests
import json
import secrets
from urllib.parse import urlencode
from typing import Optional, Dict
from fastapi import HTTPException
from dto.user import UserResponseDTO  # 필요시 GoogleUserInfoDTO 추가 가능
from repository.user import UserRepository

class GoogleOAuthService:
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    GOOGLE_SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
    
    @staticmethod
    def get_authorization_url(redirect_uri: str, state: str = None) -> str:
        """Google OAuth 인증 URL 생성"""
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "redirect_uri": redirect_uri,
            "scope": " ".join(GoogleOAuthService.GOOGLE_SCOPES),
            "response_type": "code",
            "state": state,
            "access_type": "offline",  # 리프레시 토큰을 위해
            "prompt": "consent"  # 항상 동의 화면 표시
        }
        
        return f"{GoogleOAuthService.GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    @staticmethod
    def get_access_token(code: str, redirect_uri: str) -> Optional[Dict]:
        try:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET")
            }
            response = requests.post(GoogleOAuthService.GOOGLE_TOKEN_URL, headers=headers, data=data, timeout=10)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Google Token Error: {e}")
            return None
    
    @staticmethod
    def get_user_profile(access_token: str) -> Optional[Dict]:
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(GoogleOAuthService.GOOGLE_USERINFO_URL, headers=headers, timeout=10)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Google Profile Error: {e}")
            return None
    
    @staticmethod
    def process_google_auth(code: str, redirect_uri: str) -> Dict:
        token_data = GoogleOAuthService.get_access_token(code, redirect_uri)
        if not token_data:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        access_token = token_data["access_token"]
        user_profile = GoogleOAuthService.get_user_profile(access_token)
        if not user_profile:
            raise HTTPException(status_code=400, detail="Failed to get user profile")
        
        google_id = user_profile["id"]
        email = user_profile.get("email")
        
        if not email:
            raise HTTPException(status_code=400, detail="이메일 정보를 가져올 수 없습니다.")
        
        # 먼저 이메일로 기존 사용자 찾기
        existing_user = UserRepository.get_user_by_email(email)
        
        if existing_user:
            # 기존 사용자에게 Google OAuth 정보가 없으면 추가
            # DetachedInstanceError 방지를 위해 속성 값을 변수에 저장
            user_google_id = existing_user.google_id
            user_id = existing_user.id
            
            if not user_google_id:
                update_data = {
                    "google_id": google_id,
                    "google_auth_info": json.dumps(token_data)
                }
                user = UserRepository.update_user(user_id, update_data)
            else:
                # Google OAuth 정보만 업데이트
                UserRepository.update_google_auth_info(google_id, json.dumps(token_data))
                user = existing_user
            is_new_user = False
        else:
            # 새 사용자 생성 (국가 자동 추적)
            default_countries = UserRepository.get_default_countries()
            country_id = default_countries.get('South Korea', None)  # 기본적으로 한국으로 설정
            
            # Google에서 locale 정보 확인 (있다면)
            locale = user_profile.get("locale", "")
            if locale.startswith("ja"):
                country_id = default_countries.get('Japan', country_id)
            
            user_data = {
                "email": email,
                "username": f"{email.split('@')[0]}_{secrets.token_hex(4)}",  # 고유성 보장
                "name": user_profile.get("name", "Google User"),
                "nickname": user_profile.get("name", "Google User"),
                "google_id": google_id,
                "google_auth_info": json.dumps(token_data),
                "country_id": country_id,
                "is_active": True
            }
            user = UserRepository.create_user(user_data)
            is_new_user = True
            
        return {"user": user, "access_token": access_token, "google_profile": user_profile, "is_new_user": is_new_user}