"""
개인 프로필 관리 서비스
프로필 생성, 조회, 업데이트 기능
"""

from sqlalchemy.orm import Session
from models.user import User
from dto.auth import ProfileCreateDTO, ProfileUpdateDTO
import json
import logging

logger = logging.getLogger(__name__)

class ProfileService:
    """개인 프로필 관리 서비스"""
    
    @staticmethod
    def create_profile(user_id: int, profile_data: ProfileCreateDTO, db: Session) -> dict:
        """
        개인 프로필 최초 생성
        
        Args:
            user_id: 사용자 ID
            profile_data: 프로필 데이터
            db: 데이터베이스 세션
            
        Returns:
            dict: 생성 결과
        """
        try:
            # 사용자 조회
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("사용자를 찾을 수 없습니다.")
            
            # 이미 프로필이 설정되어 있는지 확인
            if user.gender or user.birthdate or user.height or user.weight or user.topics_of_interest:
                raise ValueError("이미 프로필이 설정되어 있습니다. 업데이트를 사용해주세요.")
            
            # 관심사를 JSON 문자열로 변환
            topics_json = None
            if profile_data.topics_of_interest:
                topics_json = json.dumps(profile_data.topics_of_interest)
            
            # 프로필 정보 업데이트
            user.gender = profile_data.gender
            user.birthdate = profile_data.birthdate
            user.height = profile_data.height
            user.weight = profile_data.weight
            user.topics_of_interest = topics_json
            
            db.commit()
            db.refresh(user)
            
            logger.info(f"사용자 프로필 생성 성공: {user.email}")
            
            return {
                "success": True,
                "message": "프로필이 성공적으로 생성되었습니다.",
                "profile": {
                    "gender": user.gender,
                    "birthdate": user.birthdate.isoformat() if user.birthdate else None,
                    "height": user.height,
                    "weight": user.weight,
                    "topics_of_interest": profile_data.topics_of_interest or []
                }
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"프로필 생성 오류: {e}")
            raise
    
    @staticmethod
    def get_profile(user_id: int, db: Session) -> dict:
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
        
        # 프로필 완성도 계산
        profile_fields = [
            user.gender,
            user.birthdate,
            user.height,
            user.weight,
            topics_of_interest
        ]
        completed_fields = sum(1 for field in profile_fields if field)
        profile_completion = (completed_fields / len(profile_fields)) * 100
        
        return {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "name": user.name,
            "gender": user.gender,
            "birthdate": user.birthdate.isoformat() if user.birthdate else None,
            "height": user.height,
            "weight": user.weight,
            "topics_of_interest": topics_of_interest,
            "country_id": user.country_id,
            "account_type": user.account_type,
            "is_active": user.is_active,
            "date_joined": user.date_joined.isoformat(),
            "marketing_agreement": user.marketing_agreement,
            "terms_agreement": user.terms_agreement,
            "profile_completion": round(profile_completion, 1)
        }
    
    @staticmethod
    def update_profile(user_id: int, profile_data: ProfileUpdateDTO, db: Session) -> dict:
        """
        사용자 프로필 업데이트
        
        Args:
            user_id: 사용자 ID
            profile_data: 업데이트할 프로필 데이터
            db: 데이터베이스 세션
            
        Returns:
            dict: 업데이트 결과
        """
        try:
            # 사용자 조회
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("사용자를 찾을 수 없습니다.")
            
            updated_fields = []
            
            # 업데이트할 필드들 확인 및 적용
            if profile_data.nickname is not None:
                user.nickname = profile_data.nickname
                user.name = profile_data.nickname  # name도 함께 업데이트
                updated_fields.append("nickname")
            
            if profile_data.gender is not None:
                user.gender = profile_data.gender
                updated_fields.append("gender")
            
            if profile_data.birthdate is not None:
                user.birthdate = profile_data.birthdate
                updated_fields.append("birthdate")
            
            if profile_data.height is not None:
                user.height = profile_data.height
                updated_fields.append("height")
            
            if profile_data.weight is not None:
                user.weight = profile_data.weight
                updated_fields.append("weight")
            
            if profile_data.topics_of_interest is not None:
                topics_json = json.dumps(profile_data.topics_of_interest)
                user.topics_of_interest = topics_json
                updated_fields.append("topics_of_interest")
            
            if profile_data.marketing_agreement is not None:
                user.marketing_agreement = profile_data.marketing_agreement
                updated_fields.append("marketing_agreement")
            
            if not updated_fields:
                raise ValueError("업데이트할 정보가 없습니다.")
            
            db.commit()
            db.refresh(user)
            
            logger.info(f"사용자 프로필 업데이트 성공: {user.email}, 필드: {updated_fields}")
            
            return {
                "success": True,
                "message": "프로필이 성공적으로 업데이트되었습니다.",
                "updated_fields": updated_fields
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"프로필 업데이트 오류: {e}")
            raise
    
    @staticmethod
    def delete_profile_data(user_id: int, db: Session) -> dict:
        """
        프로필 데이터 삭제 (초기화)
        
        Args:
            user_id: 사용자 ID
            db: 데이터베이스 세션
            
        Returns:
            dict: 삭제 결과
        """
        try:
            # 사용자 조회
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("사용자를 찾을 수 없습니다.")
            
            # 프로필 데이터 초기화
            user.gender = None
            user.birthdate = None
            user.height = None
            user.weight = None
            user.topics_of_interest = None
            
            db.commit()
            
            logger.info(f"사용자 프로필 데이터 삭제 성공: {user.email}")
            
            return {
                "success": True,
                "message": "프로필 데이터가 성공적으로 삭제되었습니다."
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"프로필 데이터 삭제 오류: {e}")
            raise