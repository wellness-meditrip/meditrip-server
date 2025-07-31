from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from typing import Optional
import os
import secrets
from services.line_oauth import LineOAuthService
from services.jwt_service import JWTService
from dto.user import UserResponseDTO
from services.google_oauth import GoogleOAuthService
from repository.user import UserRepository

router = APIRouter(prefix="/oauth", tags=["oauth"])

@router.get("/login/google")
async def google_login(request: Request):
    """Google OAuth 로그인 시작"""
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    redirect_uri = f"{base_url}/oauth/callback/google"
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Generate Google OAuth authorization URL
    auth_url = GoogleOAuthService.get_authorization_url(redirect_uri, state)
    
    return {
        "auth_url": auth_url,
        "state": state
    }

@router.get("/login/line")
async def line_login(request: Request):
    """LINE OAuth 로그인 시작"""
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    redirect_uri = f"{base_url}/oauth/callback/line"
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Generate LINE OAuth authorization URL
    auth_url = LineOAuthService.get_authorization_url(redirect_uri, state)
    
    return {
        "auth_url": auth_url,
        "state": state
    }

@router.get("/callback/line")
async def line_callback(request: Request, response: Response, code: str = Query(...), state: Optional[str] = Query(None)):
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    redirect_uri = f"{base_url}/oauth/callback/line"
    
    # Process LINE OAuth (login or register)
    auth_result = LineOAuthService.process_line_auth(code, redirect_uri)
    user = auth_result["user"]
    
    # Update last login time
    UserRepository.update_last_login(user.id)
    
    # Generate JWT tokens
    tokens = JWTService.create_token_pair(user.id, user.email or "")
    
    # Save refresh token to database
    UserRepository.update_refresh_token(user.id, tokens["refresh_token"])
    
    # Set JWT tokens in cookies
    is_https = request.url.scheme == "https"
    
    # Access token cookie (30분)
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        max_age=30 * 60,  # 30 minutes
        httponly=True,
        secure=is_https,
        samesite="lax"
    )
    
    # Refresh token cookie (30일)
    response.set_cookie(
        key="refresh_token", 
        value=tokens["refresh_token"],
        max_age=30 * 24 * 60 * 60,  # 30 days
        httponly=True,
        secure=is_https,
        samesite="lax"
    )
    
    return {
        "success": True,
        "message": "로그인 성공" if not auth_result.get("is_new_user") else "회원가입 및 로그인 성공",
        "is_new": auth_result.get("is_new_user", False),
        "user": {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "line_id": user.line_id,
            "country_id": user.country_id
        },
        "tokens": tokens,
        "line_profile": auth_result["line_profile"].model_dump()
    }

@router.get("/callback/google")
async def google_callback(request: Request, response: Response, code: str = Query(...), state: Optional[str] = Query(None)):
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    redirect_uri = f"{base_url}/oauth/callback/google"
    
    # Process Google OAuth (login or register)
    auth_result = GoogleOAuthService.process_google_auth(code, redirect_uri)
    user = auth_result["user"]
    
    # Update last login time
    UserRepository.update_last_login(user.id)
    
    # Generate JWT tokens
    tokens = JWTService.create_token_pair(user.id, user.email)
    
    # Save refresh token to database
    UserRepository.update_refresh_token(user.id, tokens["refresh_token"])
    
    # Set JWT tokens in cookies
    is_https = request.url.scheme == "https"
    
    # Access token cookie (30분)
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        max_age=30 * 60,  # 30 minutes
        httponly=True,
        secure=is_https,
        samesite="lax"
    )
    
    # Refresh token cookie (30일)
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        max_age=30 * 24 * 60 * 60,  # 30 days
        httponly=True,
        secure=is_https,
        samesite="lax"
    )
    
    return {
        "success": True,
        "message": "로그인 성공" if not auth_result.get("is_new_user") else "회원가입 및 로그인 성공",
        "is_new": auth_result.get("is_new_user", False),
        "user": {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "google_id": user.google_id,
            "country_id": user.country_id
        },
        "tokens": tokens,
        "google_profile": auth_result["google_profile"]
    }
