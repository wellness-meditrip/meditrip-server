from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc
from sqlalchemy import and_, or_
from typing import List, Dict, Optional
from contextlib import contextmanager
from common.base import session_factory
from models.user import User
from models.country import Country


@contextmanager
def get_db_session():
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

class UserRepository:
    @staticmethod
    def get_user_statistics(db: Session) -> Dict:
        total_users = db.query(func.count(User.id)).scalar()
        avg_age = db.query(func.avg(User.height)).scalar()
        
        gender_stats = db.query(
            User.gender, 
            func.count(User.id)
        ).group_by(User.gender).all()
        
        return {
            "total_users": total_users,
            "average_height": avg_age,
            "gender_distribution": dict(gender_stats)
        }
    
    @staticmethod
    def get_recent_users(db: Session, limit: int = 10) -> List[User]:
        return db.query(User)\
            .order_by(desc(User.id))\
            .limit(limit)\
            .all()
    
    # CREATE
    @staticmethod
    def create_user(user_data: Dict) -> User:
        with get_db_session() as db:
            # 필수 필드들이 없으면 기본값 설정
            if 'password' not in user_data:
                user_data['password'] = ''  # OAuth 사용자는 패스워드 없음
            if 'username' not in user_data:
                user_data['username'] = user_data.get('email', 'user')
            if 'name' not in user_data:
                user_data['name'] = user_data.get('nickname', 'User')
            if 'is_active' not in user_data:
                user_data['is_active'] = True
            if 'is_staff' not in user_data:
                user_data['is_staff'] = False
            if 'is_superuser' not in user_data:
                user_data['is_superuser'] = False
            if 'first_name' not in user_data:
                user_data['first_name'] = ''
            if 'last_name' not in user_data:
                user_data['last_name'] = ''
            if 'phone_number' not in user_data:
                user_data['phone_number'] = ''
            if 'country' not in user_data:
                user_data['country'] = ''
                
            new_user = User(**user_data)
            db.add(new_user)
            db.flush()
            db.refresh(new_user)  # 세션에서 객체 새로고침
            
            # SQLAlchemy에서 객체를 detach 상태에서 벗어나게 함
            db.expunge(new_user)
            
            # 필요한 속성들을 미리 로드하여 detached 에러 방지
            try:
                _ = new_user.id, new_user.email, new_user.nickname, new_user.line_id, new_user.google_id, new_user.country_id
                _ = new_user.name, new_user.username, new_user.is_active, new_user.password
                _ = new_user.first_name, new_user.last_name, new_user.phone_number, new_user.country
                _ = new_user.line_auth_info, new_user.google_auth_info, new_user.refresh_token
            except:
                pass
            
            return new_user
    
    # READ
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        with get_db_session() as db:
            return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        with get_db_session() as db:
            user = db.query(User).filter(User.email == email).first()
            if user:
                # SQLAlchemy에서 객체를 detach 상태에서 벗어나게 함
                db.expunge(user)
                # 모든 필요한 속성을 미리 로드
                try:
                    _ = user.id, user.email, user.nickname, user.line_id, user.google_id, user.country_id
                    _ = user.name, user.username, user.is_active, user.password
                    _ = user.first_name, user.last_name, user.phone_number, user.country
                    _ = user.line_auth_info, user.google_auth_info, user.refresh_token
                except:
                    pass  # 일부 속성이 없을 수 있음
            return user
    
    @staticmethod
    def get_user_by_line_id(line_id: str) -> Optional[User]:
        with get_db_session() as db:
            user = db.query(User).filter(User.line_id == line_id).first()
            if user:
                # SQLAlchemy에서 객체를 detach 상태에서 벗어나게 함
                db.expunge(user)
                # 모든 필요한 속성을 미리 로드
                try:
                    _ = user.id, user.email, user.nickname, user.line_id, user.google_id, user.country_id
                    _ = user.name, user.username, user.is_active, user.password
                    _ = user.first_name, user.last_name, user.phone_number, user.country
                    _ = user.line_auth_info, user.google_auth_info, user.refresh_token
                except:
                    pass
            return user
    
    @staticmethod
    def get_user_by_google_id(google_id: str) -> Optional[User]:
        with get_db_session() as db:
            user = db.query(User).filter(User.google_id == google_id).first()
            if user:
                # SQLAlchemy에서 객체를 detach 상태에서 벗어나게 함
                db.expunge(user)
                # 모든 필요한 속성을 미리 로드
                try:
                    _ = user.id, user.email, user.nickname, user.line_id, user.google_id, user.country_id
                    _ = user.name, user.username, user.is_active, user.password
                    _ = user.first_name, user.last_name, user.phone_number, user.country
                    _ = user.line_auth_info, user.google_auth_info, user.refresh_token
                except:
                    pass
            return user
    
    @staticmethod
    def get_users(skip: int = 0, limit: int = 100) -> List[User]:
        with get_db_session() as db:
            return db.query(User).offset(skip).limit(limit).all()
    
    # UPDATE
    @staticmethod
    def update_user(user_id: int, update_data: Dict) -> Optional[User]:
        with get_db_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                for key, value in update_data.items():
                    if hasattr(user, key) and value is not None:
                        setattr(user, key, value)
                db.flush()
                db.refresh(user)  # 세션에서 객체 새로고침
                
                # 필요한 속성들을 미리 로드하여 detached 에러 방지
                _ = user.id
                _ = user.email
                _ = user.nickname
                _ = user.line_id
                _ = user.google_id
                _ = user.country_id
                
                return user
            return None
    
    @staticmethod
    def update_line_auth_info(line_id: str, auth_info: str) -> Optional[User]:
        with get_db_session() as db:
            user = db.query(User).filter(User.line_id == line_id).first()
            if user:
                user.line_auth_info = auth_info
                db.flush()
                db.refresh(user)  # 세션에서 객체 새로고침
                
                # 필요한 속성들을 미리 로드하여 detached 에러 방지
                _ = user.id
                _ = user.email
                _ = user.nickname
                _ = user.line_id
                _ = user.google_id
                _ = user.country_id
                
                return user
            return None
    
    @staticmethod
    def update_google_auth_info(google_id: str, auth_info: str) -> Optional[User]:
        with get_db_session() as db:
            user = db.query(User).filter(User.google_id == google_id).first()
            if user:
                user.google_auth_info = auth_info
                db.flush()
                db.refresh(user)  # 세션에서 객체 새로고침
                
                # 필요한 속성들을 미리 로드하여 detached 에러 방지
                _ = user.id
                _ = user.email
                _ = user.nickname
                _ = user.line_id
                _ = user.google_id
                _ = user.country_id
                
                return user
            return None
    
    @staticmethod
    def update_refresh_token(user_id: int, refresh_token: str) -> Optional[User]:
        """사용자의 리프레시 토큰 업데이트"""
        with get_db_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.refresh_token = refresh_token
                db.flush()
                return user
            return None
    
    @staticmethod
    def get_user_by_refresh_token(refresh_token: str) -> Optional[User]:
        """리프레시 토큰으로 사용자 조회"""
        with get_db_session() as db:
            return db.query(User).filter(User.refresh_token == refresh_token).first()
    
    @staticmethod
    def revoke_refresh_token(user_id: int) -> bool:
        """사용자의 리프레시 토큰 무효화"""
        with get_db_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.refresh_token = None
                db.flush()
                return True
            return False
    
    @staticmethod
    def get_country_by_name(country_name: str) -> Optional[Country]:
        """국가명으로 국가 조회"""
        with get_db_session() as db:
            return db.query(Country).filter(Country.name == country_name).first()
    
    @staticmethod
    def get_default_countries() -> Dict[str, int]:
        """기본 국가들의 ID 반환"""
        with get_db_session() as db:
            countries = db.query(Country).filter(Country.name.in_(['Japan', 'South Korea'])).all()
            return {country.name: country.id for country in countries}
    
    @staticmethod
    def update_last_login(user_id: int) -> Optional[User]:
        """사용자의 마지막 로그인 시간 업데이트"""
        from datetime import datetime
        
        with get_db_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login = datetime.now()
                db.flush()
                db.refresh(user)
                
                # DetachedInstanceError 방지를 위한 속성 로드
                try:
                    _ = user.id
                    _ = user.email
                    _ = user.nickname
                    _ = user.last_login
                    _ = user.country_id
                except Exception:
                    pass
                
                db.expunge(user)  # 세션에서 분리하여 외부에서 사용 가능하게 함
                return user
            return None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        with get_db_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                # DetachedInstanceError 방지를 위한 속성 로드
                try:
                    _ = user.id
                    _ = user.email
                    _ = user.nickname
                    _ = user.line_id
                    _ = user.google_id
                    _ = user.country_id
                    _ = user.last_login
                    _ = user.is_active
                except Exception:
                    pass
                
                db.expunge(user)  # 세션에서 분리
                return user
            return None
    
    # DELETE
    @staticmethod
    def delete_user(user_id: int) -> bool:
        with get_db_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                db.delete(user)
                return True
            return False