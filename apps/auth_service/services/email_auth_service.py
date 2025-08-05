"""
이메일/비밀번호 인증 서비스
회원가입, 로그인, 프로필 관리
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.user import User
from models.country import Country
from services.password_service import PasswordService
from services.jwt_service import JWTService
from dto.auth import RegisterRequestDTO, LoginRequestDTO
from repository.user import UserRepository
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EmailAuthService:
    """이메일/비밀번호 기반 인증 서비스"""
    
    @staticmethod
    def register_user(register_data: RegisterRequestDTO, db: Session) -> dict:
        """
        일반 회원가입
        
        Args:
            register_data: 회원가입 데이터
            db: 데이터베이스 세션
            
        Returns:
            dict: 회원가입 결과
        """
        try:
            # 이메일 중복 확인
            existing_user = db.query(User).filter(User.email == register_data.email).first()
            if existing_user:
                raise ValueError("이미 가입된 이메일 주소입니다.")
            
            # 국가 정보 확인
            country = db.query(Country).filter(Country.id == register_data.country_id).first()
            if not country:
                raise ValueError("유효하지 않은 국가 정보입니다.")
            
            # 비밀번호 해싱
            hashed_password = PasswordService.hash_password(register_data.password)
            
            # 새 사용자 생성 (기본 정보만)
            new_user = User(
                email=register_data.email,
                password=hashed_password,
                username=register_data.email,  # username을 email로 설정
                nickname=register_data.nickname,
                name=register_data.nickname,  # name도 nickname으로 설정
                country_id=register_data.country_id,
                terms_agreement=register_data.terms_agreement,
                marketing_agreement=register_data.marketing_agreement,
                account_type='email',
                is_active=True,
                date_joined=datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            logger.info(f"새 사용자 가입 성공: {new_user.email}")
            
            # JWT 토큰 생성
            tokens = JWTService.create_token_pair(new_user.id, new_user.email)
            
            # 리프레시 토큰 저장
            UserRepository.update_refresh_token(new_user.id, tokens["refresh_token"], db)
            
            return {
                "success": True,
                "message": "회원가입이 완료되었습니다.",
                "is_new_user": True,
                "user": {
                    "id": new_user.id,
                    "email": new_user.email,
                    "nickname": new_user.nickname,
                    "country_id": new_user.country_id,
                    "account_type": new_user.account_type
                },
                "tokens": tokens
            }
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"회원가입 DB 오류: {e}")
            if "email" in str(e):
                raise ValueError("이미 가입된 이메일 주소입니다.")
            else:
                raise ValueError("데이터베이스 오류가 발생했습니다.")
        except Exception as e:
            db.rollback()
            logger.error(f"회원가입 오류: {e}")
            raise
    
    @staticmethod
    def login_user(login_data: LoginRequestDTO, db: Session) -> dict:
        """
        일반 로그인
        
        Args:
            login_data: 로그인 데이터
            db: 데이터베이스 세션
            
        Returns:
            dict: 로그인 결과
        """
        try:
            # 이메일로 사용자 조회
            user = db.query(User).filter(
                User.email == login_data.email,
                User.account_type == 'email'
            ).first()
            
            if not user:
                raise ValueError("등록되지 않은 이메일 주소입니다.")
            
            if not user.is_active:
                raise ValueError("비활성화된 계정입니다.")
            
            # 비밀번호 검증
            if not PasswordService.verify_password(login_data.password, user.password):
                raise ValueError("비밀번호가 올바르지 않습니다.")
            
            # 마지막 로그인 시간 업데이트
            UserRepository.update_last_login(user.id, db)
            
            # JWT 토큰 생성
            tokens = JWTService.create_token_pair(user.id, user.email)
            
            # 리프레시 토큰 저장
            UserRepository.update_refresh_token(user.id, tokens["refresh_token"], db)
            
            logger.info(f"사용자 로그인 성공: {user.email}")
            
            return {
                "success": True,
                "message": "로그인 성공",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "nickname": user.nickname,
                    "name": user.name,
                    "country_id": user.country_id,
                    "account_type": user.account_type,
                    "gender": user.gender,
                    "birthdate": user.birthdate.isoformat() if user.birthdate else None,
                    "height": user.height,
                    "weight": user.weight,
                    "marketing_agreement": user.marketing_agreement
                },
                "tokens": tokens,
                "remember_me": login_data.remember_me
            }
            
        except Exception as e:
            logger.error(f"로그인 오류: {e}")
            raise
    
    @staticmethod
    def get_user_profile(user_id: int, db: Session) -> dict:
        """
        사용자 프로필 조회
        
        Args:
            user_id: 사용자 ID
            db: 데이터베이스 세션
            
        Returns:
            dict: 사용자 프로필 정보
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("사용자를 찾을 수 없습니다.")
        
        # 관심사 JSON 파싱
        topics_of_interest = []
        if user.topics_of_interest:
            try:
                topics_of_interest = json.loads(user.topics_of_interest)
            except:
                topics_of_interest = []
        
        return {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "name": user.name,
            "gender": user.gender,
            "birthdate": user.birthdate,
            "height": user.height,
            "weight": user.weight,
            "topics_of_interest": topics_of_interest,
            "country_id": user.country_id,
            "account_type": user.account_type,
            "is_active": user.is_active,
            "date_joined": user.date_joined.isoformat(),
            "marketing_agreement": user.marketing_agreement,
            "terms_agreement": user.terms_agreement
        }
    
    @staticmethod
    def change_password(user_id: int, current_password: str, new_password: str, db: Session) -> dict:
        """
        비밀번호 변경
        
        Args:
            user_id: 사용자 ID
            current_password: 현재 비밀번호
            new_password: 새 비밀번호
            db: 데이터베이스 세션
            
        Returns:
            dict: 변경 결과
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("사용자를 찾을 수 없습니다.")
            
            # 현재 비밀번호 확인
            if not PasswordService.verify_password(current_password, user.password):
                raise ValueError("현재 비밀번호가 올바르지 않습니다.")
            
            # 새 비밀번호 해싱
            hashed_new_password = PasswordService.hash_password(new_password)
            
            # 비밀번호 업데이트
            user.password = hashed_new_password
            db.commit()
            
            logger.info(f"사용자 비밀번호 변경 성공: {user.email}")
            
            return {
                "success": True,
                "message": "비밀번호가 성공적으로 변경되었습니다."
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"비밀번호 변경 오류: {e}")
            raise