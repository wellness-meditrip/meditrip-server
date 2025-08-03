"""
routes.py - Hospital Service API Routes
병원 관리 시스템의 API 엔드포인트 정의
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import json
import logging

from database import get_database
from models import Hospital, HospitalDetail
from schemas import (
    HospitalCreate, HospitalUpdate, HospitalResponse, HospitalListResponse,
    HospitalDetailCreate, HospitalDetailUpdate, HospitalDetailResponse,
    HospitalSearchParams, ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hospitals", tags=["hospitals"])

# =============================================================================
# 병원 기본 정보 API
# =============================================================================

@router.get("/", response_model=HospitalListResponse)
async def get_hospitals(
    keyword: Optional[str] = Query(None, description="병원명, 주소 검색 키워드"),
    city: Optional[str] = Query(None, description="도시별 필터"),
    department: Optional[str] = Query(None, description="진료과목 필터"),
    parking_required: Optional[bool] = Query(None, description="주차장 필요 여부"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지 크기"),
    db: Session = Depends(get_database)
):
    """
    병원 목록 조회 (검색 및 필터링 지원)
    """
    try:
        # 기본 쿼리
        query = db.query(Hospital)
        
        # 키워드 검색 (병원명, 주소)
        if keyword:
            query = query.filter(
                or_(
                    Hospital.hospital_name.ilike(f"%{keyword}%"),
                    Hospital.address.ilike(f"%{keyword}%")
                )
            )
        
        # 도시별 필터
        if city:
            query = query.filter(Hospital.address.ilike(f"%{city}%"))
        
        # 진료과목 필터 (세부정보 테이블 조인 필요)
        if department:
            query = query.join(HospitalDetail).filter(
                HospitalDetail.departments.ilike(f"%{department}%")
            )
        
        # 주차장 필터
        if parking_required is not None:
            query = query.join(HospitalDetail).filter(
                HospitalDetail.parking_available == parking_required
            )
        
        # 전체 개수
        total = query.count()
        
        # 페이징
        offset = (page - 1) * size
        hospitals = query.offset(offset).limit(size).all()
        
        return HospitalListResponse(
            hospitals=hospitals,
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"❌ 병원 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="병원 목록 조회 중 오류가 발생했습니다.")

@router.get("/{hospital_id}", response_model=HospitalResponse)
async def get_hospital(hospital_id: int, db: Session = Depends(get_database)):
    """
    특정 병원 정보 조회
    """
    try:
        hospital = db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
        
        if not hospital:
            raise HTTPException(status_code=404, detail="병원을 찾을 수 없습니다.")
        
        return hospital
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 병원 정보 조회 실패 (ID: {hospital_id}): {e}")
        raise HTTPException(status_code=500, detail="병원 정보 조회 중 오류가 발생했습니다.")

@router.post("/", response_model=HospitalResponse)
async def create_hospital(hospital_data: HospitalCreate, db: Session = Depends(get_database)):
    """
    새 병원 등록
    """
    try:
        # 병원명 중복 확인
        existing_hospital = db.query(Hospital).filter(
            Hospital.hospital_name == hospital_data.hospital_name
        ).first()
        
        if existing_hospital:
            raise HTTPException(status_code=400, detail="이미 등록된 병원명입니다.")
        
        # 새 병원 생성
        new_hospital = Hospital(**hospital_data.dict())
        db.add(new_hospital)
        db.commit()
        db.refresh(new_hospital)
        
        logger.info(f"✅ 새 병원 등록 성공: {new_hospital.hospital_name} (ID: {new_hospital.hospital_id})")
        return new_hospital
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 병원 등록 실패: {e}")
        raise HTTPException(status_code=500, detail="병원 등록 중 오류가 발생했습니다.")

@router.put("/{hospital_id}", response_model=HospitalResponse)
async def update_hospital(
    hospital_id: int, 
    hospital_data: HospitalUpdate, 
    db: Session = Depends(get_database)
):
    """
    병원 정보 수정
    """
    try:
        hospital = db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
        
        if not hospital:
            raise HTTPException(status_code=404, detail="병원을 찾을 수 없습니다.")
        
        # 수정할 데이터만 업데이트
        update_data = hospital_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(hospital, field, value)
        
        db.commit()
        db.refresh(hospital)
        
        logger.info(f"✅ 병원 정보 수정 성공: {hospital.hospital_name} (ID: {hospital_id})")
        return hospital
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 병원 정보 수정 실패 (ID: {hospital_id}): {e}")
        raise HTTPException(status_code=500, detail="병원 정보 수정 중 오류가 발생했습니다.")

@router.delete("/{hospital_id}")
async def delete_hospital(hospital_id: int, db: Session = Depends(get_database)):
    """
    병원 삭제
    """
    try:
        hospital = db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
        
        if not hospital:
            raise HTTPException(status_code=404, detail="병원을 찾을 수 없습니다.")
        
        hospital_name = hospital.hospital_name
        db.delete(hospital)
        db.commit()
        
        logger.info(f"✅ 병원 삭제 성공: {hospital_name} (ID: {hospital_id})")
        return {"message": f"병원 '{hospital_name}'이(가) 성공적으로 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 병원 삭제 실패 (ID: {hospital_id}): {e}")
        raise HTTPException(status_code=500, detail="병원 삭제 중 오류가 발생했습니다.")

# =============================================================================
# 병원 세부 정보 API
# =============================================================================

@router.get("/{hospital_id}/details", response_model=List[HospitalDetailResponse])
async def get_hospital_details(hospital_id: int, db: Session = Depends(get_database)):
    """
    병원 세부 정보 조회
    """
    try:
        # 병원 존재 확인
        hospital = db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
        if not hospital:
            raise HTTPException(status_code=404, detail="병원을 찾을 수 없습니다.")
        
        # 세부 정보 조회
        details = db.query(HospitalDetail).filter(
            HospitalDetail.hospital_id == hospital_id
        ).all()
        
        return details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 병원 세부 정보 조회 실패 (Hospital ID: {hospital_id}): {e}")
        raise HTTPException(status_code=500, detail="병원 세부 정보 조회 중 오류가 발생했습니다.")

@router.post("/{hospital_id}/details", response_model=HospitalDetailResponse)
async def create_hospital_detail(
    hospital_id: int,
    detail_data: HospitalDetailCreate,
    db: Session = Depends(get_database)
):
    """
    병원 세부 정보 등록
    """
    try:
        # 병원 존재 확인
        hospital = db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
        if not hospital:
            raise HTTPException(status_code=404, detail="병원을 찾을 수 없습니다.")
        
        # JSON 직렬화 처리
        detail_dict = detail_data.dict()
        detail_dict['hospital_id'] = hospital_id
        
        # 리스트 타입 필드들을 JSON 문자열로 변환
        if detail_dict.get('operating_hours'):
            detail_dict['operating_hours'] = json.dumps(
                [item.dict() if hasattr(item, 'dict') else item for item in detail_dict['operating_hours']]
            )
        
        if detail_dict.get('images'):
            detail_dict['images'] = json.dumps(
                [item.dict() if hasattr(item, 'dict') else item for item in detail_dict['images']]
            )
        
        if detail_dict.get('departments'):
            detail_dict['departments'] = json.dumps(
                [item.dict() if hasattr(item, 'dict') else item for item in detail_dict['departments']]
            )
        
        # 세부 정보 생성
        new_detail = HospitalDetail(**detail_dict)
        db.add(new_detail)
        db.commit()
        db.refresh(new_detail)
        
        logger.info(f"✅ 병원 세부 정보 등록 성공 (Hospital ID: {hospital_id})")
        return new_detail
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 병원 세부 정보 등록 실패 (Hospital ID: {hospital_id}): {e}")
        raise HTTPException(status_code=500, detail="병원 세부 정보 등록 중 오류가 발생했습니다.")

@router.put("/{hospital_id}/details/{detail_id}", response_model=HospitalDetailResponse)
async def update_hospital_detail(
    hospital_id: int,
    detail_id: int,
    detail_data: HospitalDetailUpdate,
    db: Session = Depends(get_database)
):
    """
    병원 세부 정보 수정
    """
    try:
        detail = db.query(HospitalDetail).filter(
            and_(
                HospitalDetail.id == detail_id,
                HospitalDetail.hospital_id == hospital_id
            )
        ).first()
        
        if not detail:
            raise HTTPException(status_code=404, detail="병원 세부 정보를 찾을 수 없습니다.")
        
        # 수정할 데이터 처리
        update_data = detail_data.dict(exclude_unset=True)
        
        # JSON 직렬화 처리
        for field, value in update_data.items():
            if field in ['operating_hours', 'images', 'departments'] and value is not None:
                if isinstance(value, list):
                    value = json.dumps([item.dict() if hasattr(item, 'dict') else item for item in value])
            setattr(detail, field, value)
        
        db.commit()
        db.refresh(detail)
        
        logger.info(f"✅ 병원 세부 정보 수정 성공 (Hospital ID: {hospital_id}, Detail ID: {detail_id})")
        return detail
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 병원 세부 정보 수정 실패 (Hospital ID: {hospital_id}, Detail ID: {detail_id}): {e}")
        raise HTTPException(status_code=500, detail="병원 세부 정보 수정 중 오류가 발생했습니다.")

@router.delete("/{hospital_id}/details/{detail_id}")
async def delete_hospital_detail(
    hospital_id: int,
    detail_id: int,
    db: Session = Depends(get_database)
):
    """
    병원 세부 정보 삭제
    """
    try:
        detail = db.query(HospitalDetail).filter(
            and_(
                HospitalDetail.id == detail_id,
                HospitalDetail.hospital_id == hospital_id
            )
        ).first()
        
        if not detail:
            raise HTTPException(status_code=404, detail="병원 세부 정보를 찾을 수 없습니다.")
        
        db.delete(detail)
        db.commit()
        
        logger.info(f"✅ 병원 세부 정보 삭제 성공 (Hospital ID: {hospital_id}, Detail ID: {detail_id})")
        return {"message": "병원 세부 정보가 성공적으로 삭제되었습니다."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 병원 세부 정보 삭제 실패 (Hospital ID: {hospital_id}, Detail ID: {detail_id}): {e}")
        raise HTTPException(status_code=500, detail="병원 세부 정보 삭제 중 오류가 발생했습니다.")