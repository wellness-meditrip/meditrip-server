import logging
from sqlalchemy.exc import IntegrityError
from common.base import session_factory
from models.country import Country

logger = logging.getLogger(__name__)

def initialize_countries():
    """초기 국가 데이터 생성 (South Korea, Japan)"""
    session = session_factory()
    
    try:
        # 기존 국가 데이터 확인
        existing_countries = session.query(Country).filter(
            Country.name.in_(["South Korea", "Japan"])
        ).all()
        
        existing_names = {country.name for country in existing_countries}
        
        countries_to_create = []
        
        # South Korea 생성
        if "South Korea" not in existing_names:
            countries_to_create.append(Country(name="South Korea"))
            logger.info("South Korea 국가 데이터를 생성합니다.")
        else:
            logger.info("South Korea 국가 데이터가 이미 존재합니다.")
            
        # Japan 생성  
        if "Japan" not in existing_names:
            countries_to_create.append(Country(name="Japan"))
            logger.info("Japan 국가 데이터를 생성합니다.")
        else:
            logger.info("Japan 국가 데이터가 이미 존재합니다.")
        
        # 새로운 국가들 저장
        if countries_to_create:
            session.add_all(countries_to_create)
            session.commit()
            logger.info(f"{len(countries_to_create)}개의 초기 국가 데이터가 생성되었습니다.")
        else:
            logger.info("모든 초기 국가 데이터가 이미 존재합니다.")
            
    except IntegrityError as e:
        session.rollback()
        logger.warning(f"국가 데이터 생성 중 무결성 오류가 발생했습니다 (이미 존재할 수 있음): {e}")
    except Exception as e:
        session.rollback()
        logger.error(f"초기 국가 데이터 생성 중 오류가 발생했습니다: {e}")
        raise
    finally:
        session.close()


def initialize_all_data():
    """모든 초기 데이터 생성"""
    logger.info("초기 데이터 생성을 시작합니다...")
    
    try:
        # 국가 데이터 초기화
        initialize_countries()
        
        logger.info("모든 초기 데이터 생성이 완료되었습니다.")
        
    except Exception as e:
        logger.error(f"초기 데이터 생성 중 오류가 발생했습니다: {e}")
        raise