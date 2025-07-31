import os
import requests
import json
import secrets
from urllib.parse import urlencode
from typing import Optional, Dict
from fastapi import HTTPException
from dto.user import LineUserInfoDTO
from repository.user import UserRepository

class LineOAuthService:
    LINE_AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
    LINE_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
    LINE_PROFILE_URL = "https://api.line.me/v2/profile"  # 기본 프로필 (이메일 없음)
    LINE_USERINFO_URL = "https://api.line.me/oauth2/v2.1/userinfo"  # OpenID Connect userinfo (이메일 포함)
    LINE_VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"
    LINE_SCOPES = ["profile", "openid", "email"]
    
    @staticmethod
    def get_authorization_url(redirect_uri: str, state: str = None) -> str:
        """LINE OAuth 인증 URL 생성 - 이메일 필수 동의"""
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            "response_type": "code",
            "client_id": os.getenv("LINE_CLIENT_ID"),
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(LineOAuthService.LINE_SCOPES),
            "prompt": "consent",  # 항상 동의 화면 표시 (이메일 포함)
            "ui_locales": "ko-KR"  # 한국어 동의 화면
        }
        
        auth_url = f"{LineOAuthService.LINE_AUTH_URL}?{urlencode(params)}"
        
        print(f"LINE Authorization URL: {auth_url}")
        print(f"LINE Scopes: {LineOAuthService.LINE_SCOPES}")
        print(f"LINE Client ID: {os.getenv('LINE_CLIENT_ID')}")
        print(f"Prompt: consent (이메일 필수 동의)")
        
        return auth_url
    
    @staticmethod
    def get_access_token(code: str, redirect_uri: str) -> Optional[Dict]:
        try:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": os.getenv("LINE_CLIENT_ID"),
                "client_secret": os.getenv("LINE_CLIENT_SECRET")
            }
            
            print(f"LINE Token Request - URL: {LineOAuthService.LINE_TOKEN_URL}")
            print(f"LINE Token Request - Data: {data}")
            
            response = requests.post(LineOAuthService.LINE_TOKEN_URL, headers=headers, data=data, timeout=10)
            
            print(f"LINE Token Response Status: {response.status_code}")
            print(f"LINE Token Response: {response.text}")
            
            if response.status_code == 200:
                token_data = response.json()
                print(f"LINE Token Success: {token_data}")
                
                # 토큰 응답에서 scope 확인 (이메일 권한이 포함되어 있는지)
                token_scope = token_data.get("scope", "")
                print(f"TOKEN SCOPE 확인: {token_scope}")
                if "email" not in token_scope:
                    print(f"EMAIL SCOPE가 토큰에 포함되지 않음! LINE Developers Console에서 Email permission을 확인하세요.")
                
                return token_data
            else:
                print(f"LINE Token Failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"LINE Token Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_user_profile(access_token: str) -> Optional[LineUserInfoDTO]:
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            print(f"LINE Access Token: {access_token[:20]}...")  # 디버깅용
            
            # OpenID Connect userinfo 엔드포인트에서 이메일 정보 가져오기 (필수)
            print(f"Calling LINE UserInfo API: {LineOAuthService.LINE_USERINFO_URL}")
            userinfo_response = requests.get(LineOAuthService.LINE_USERINFO_URL, headers=headers, timeout=10)
            
            print(f"LINE UserInfo Status: {userinfo_response.status_code}")
            print(f"LINE UserInfo Headers: {dict(userinfo_response.headers)}")
            
            if userinfo_response.status_code == 200:
                userinfo_data = userinfo_response.json()
                print(f"LINE UserInfo Response: {userinfo_data}")  # 디버깅용
                
                # OpenID Connect의 경우 sub를 user_id로 사용
                user_id = userinfo_data.get("sub")
                email = userinfo_data.get("email")
                name = userinfo_data.get("name", "LINE User")
                picture = userinfo_data.get("picture")
                
                print(f"Extracted - UserID: {user_id}, Email: {email}, Name: {name}")
                
                # 이메일이 없으면 경고 로그만 출력 (에러 없이 진행)
                if not email:
                    print(f"LINE에서 이메일을 제공하지 않습니다.")
                    print(f"UserInfo 응답 전체: {userinfo_data}")
                    print(f"LINE ID({user_id})로 계정을 생성합니다.")
                
                return LineUserInfoDTO(
                    user_id=user_id,
                    display_name=name, 
                    picture_url=picture, 
                    status_message=None,
                    email=email
                )
            else:
                print(f"LINE UserInfo failed with status {userinfo_response.status_code}")
                print(f"Response body: {userinfo_response.text}")
                raise Exception(f"LINE OpenID Connect API 호출 실패: {userinfo_response.status_code}")
            
        except Exception as e:
            print(f"LINE Profile Error: {e}")
            raise e
    
    @staticmethod
    def process_line_auth(code: str, redirect_uri: str) -> Dict:
        try:
            token_data = LineOAuthService.get_access_token(code, redirect_uri)
            if not token_data:
                raise HTTPException(status_code=400, detail="Failed to get access token")
            
            access_token = token_data["access_token"]
            user_profile = LineOAuthService.get_user_profile(access_token)
            if not user_profile:
                raise HTTPException(status_code=400, detail="Failed to get user profile")
            
            # 이메일이 있으면 이메일 기반, 없으면 LINE ID 기반으로 사용자 찾기
            email = user_profile.email
            line_id = user_profile.user_id
            
            print(f"사용자 조회 - Email: {email}, LINE ID: {line_id}")
            
            # 이메일이 있으면 이메일로 먼저 찾고, 없으면 LINE ID로 찾기
            if email:
                existing_user = UserRepository.get_user_by_email(email)
                print(f"이메일로 사용자 조회 결과: {'있음' if existing_user else '없음'}")
            else:
                existing_user = UserRepository.get_user_by_line_id(line_id)
                print(f"📱 LINE ID로 사용자 조회 결과: {'있음' if existing_user else '없음'}")
            
            if existing_user:
                # 기존 사용자 - OAuth 정보 업데이트
                user_line_id = existing_user.line_id if hasattr(existing_user, 'line_id') else None
                user_id = existing_user.id
                
                if not user_line_id and email:
                    # 이메일로 찾은 기존 사용자에게 LINE 정보 추가
                    update_data = {
                        "line_id": line_id,
                        "line_auth_info": json.dumps(token_data)
                    }
                    user = UserRepository.update_user(user_id, update_data)
                    print(f"기존 사용자에게 LINE 정보 추가")
                else:
                    # LINE OAuth 정보만 업데이트
                    UserRepository.update_line_auth_info(line_id, json.dumps(token_data))
                    user = existing_user
                    print(f"기존 LINE 사용자 OAuth 정보 업데이트")
                is_new_user = False
            else:
                # 새 사용자 생성
                default_countries = UserRepository.get_default_countries()
                country_id = default_countries.get('Japan', None)  # LINE은 일본 서비스
                
                # 이메일이 있으면 이메일 기반, 없으면 LINE ID 기반 계정 생성
                if email:
                    user_email = email
                    username = f"{email.split('@')[0]}_{secrets.token_hex(4)}"
                    print(f"이메일 기반 새 계정 생성")
                else:
                    user_email = f"{line_id}@line.local"  # 가짜 이메일
                    username = f"line_{line_id}_{secrets.token_hex(4)}"
                    print(f"📱 LINE ID 기반 새 계정 생성")
                
                user_data = {
                    "email": user_email,
                    "username": username,
                    "name": user_profile.display_name,
                    "nickname": user_profile.display_name,
                    "line_id": line_id,
                    "line_auth_info": json.dumps(token_data),
                    "country_id": country_id,
                    "is_active": True
                }
                user = UserRepository.create_user(user_data)
                is_new_user = True
                print(f"새 사용자 생성 - Email: {user_email}")
                
            return {"user": user, "access_token": access_token, "line_profile": user_profile, "is_new_user": is_new_user}
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"LINE Auth Error: {e}")
            raise HTTPException(status_code=500, detail=f"LINE 로그인 처리 중 오류가 발생했습니다: {str(e)}")