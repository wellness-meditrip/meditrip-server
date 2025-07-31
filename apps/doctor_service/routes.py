"""
routes.py - FastAPI 라우터 정의
doctor_service의 모든 API 엔드포인트 구현
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import Doctor, DoctorSpecialization, DoctorStatistics, DoctorFees, DoctorSchedule
import schemas

# API 라우터 생성
router = APIRouter(
    prefix="/doctors",  # 모든 엔드포인트에 /doctors 접두사
    tags=["doctors"]    # Swagger UI에서 그룹화
)


# =============================================================================
# Doctor (의사 기본정보) 엔드포인트
# =============================================================================

@router.post("/", response_model=schemas.DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(
    doctor_data: schemas.DoctorCreate,
    db: Session = Depends(get_db)
):
    """
    새로운 의사 등록
    - 의사 기본정보를 데이터베이스에 저장
    """
    # 면허번호 중복 확인
    existing_doctor = db.query(Doctor).filter(Doctor.license_number == doctor_data.license_number).first()
    if existing_doctor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"면허번호 '{doctor_data.license_number}'가 이미 등록되어 있습니다."
        )
    
    # 새 의사 생성
    new_doctor = Doctor(**doctor_data.dict())
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)
    
    return new_doctor


@router.get("/", response_model=List[schemas.DoctorResponse])
def get_doctors(
    skip: int = 0,      # 건너뛸 레코드 수 (페이징용)
    limit: int = 100,   # 가져올 레코드 수 (페이징용)
    db: Session = Depends(get_db)
):
    """
    모든 의사 목록 조회 (페이징 지원)
    - skip: 건너뛸 개수 (기본값: 0)
    - limit: 가져올 개수 (기본값: 100)
    """
    doctors = db.query(Doctor).offset(skip).limit(limit).all()
    return doctors


@router.get("/{doctor_id}", response_model=schemas.DoctorDetailResponse)
def get_doctor_detail(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 의사의 상세 정보 조회 (모든 관련 정보 포함)
    - 전문과목, 통계, 진료비, 일정 정보 모두 포함
    """
    doctor = db.query(Doctor).options(
        joinedload(Doctor.specializations),
        joinedload(Doctor.statistics),
        joinedload(Doctor.fees),
        joinedload(Doctor.schedules)
    ).filter(Doctor.doctor_id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"의사 ID {doctor_id}를 찾을 수 없습니다."
        )
    
    return doctor


@router.put("/{doctor_id}", response_model=schemas.DoctorResponse)
def update_doctor(
    doctor_id: int,
    doctor_update: schemas.DoctorUpdate,
    db: Session = Depends(get_db)
):
    """
    의사 정보 수정
    - 제공된 필드만 업데이트 (부분 업데이트)
    """
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"의사 ID {doctor_id}를 찾을 수 없습니다."
        )
    
    # 수정할 데이터만 업데이트
    update_data = doctor_update.dict(exclude_unset=True)  # None이 아닌 값만
    for field, value in update_data.items():
        setattr(doctor, field, value)
    
    doctor.updated_at = datetime.utcnow()  # 수정 시간 업데이트
    db.commit()
    db.refresh(doctor)
    
    return doctor


@router.delete("/{doctor_id}", response_model=schemas.MessageResponse)
def delete_doctor(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    """
    의사 정보 삭제
    - 관련된 모든 정보도 함께 삭제
    """
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"의사 ID {doctor_id}를 찾을 수 없습니다."
        )
    
    db.delete(doctor)
    db.commit()
    
    return schemas.MessageResponse(message=f"의사 ID {doctor_id}가 삭제되었습니다.")


# =============================================================================
# DoctorSpecialization (의사 전문과목) 엔드포인트
# =============================================================================

@router.post("/{doctor_id}/specializations", response_model=schemas.DoctorSpecializationResponse, status_code=status.HTTP_201_CREATED)
def create_doctor_specialization(
    doctor_id: int,
    specialization_data: schemas.DoctorSpecializationCreate,
    db: Session = Depends(get_db)
):
    """
    의사 전문과목 추가
    """
    # 의사 존재 확인
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"의사 ID {doctor_id}를 찾을 수 없습니다."
        )
    
    # 동일한 전문과목 중복 확인
    existing_spec = db.query(DoctorSpecialization).filter(
        DoctorSpecialization.doctor_id == doctor_id,
        DoctorSpecialization.specializations_name == specialization_data.specializations_name,
        DoctorSpecialization.hospital_id == specialization_data.hospital_id
    ).first()
    
    if existing_spec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 전문과목입니다."
        )
    
    # 새 전문과목 생성
    new_specialization = DoctorSpecialization(**specialization_data.dict())
    db.add(new_specialization)
    db.commit()
    db.refresh(new_specialization)
    
    # JOIN으로 의사 이름 추가
    result = db.query(DoctorSpecialization, Doctor.doctor_name).join(Doctor).filter(
        DoctorSpecialization.doctor_id == new_specialization.doctor_id,
        DoctorSpecialization.specializations_name == new_specialization.specializations_name
    ).first()
    
    # 응답 데이터 구성
    response_data = schemas.DoctorSpecializationResponse(
        **new_specialization.__dict__,
        doctor_name=result[1]
    )
    
    return response_data


@router.get("/{doctor_id}/specializations", response_model=List[schemas.DoctorSpecializationResponse])
def get_doctor_specializations(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 의사의 전문과목 목록 조회
    """
    # JOIN으로 의사 이름과 함께 조회
    results = db.query(DoctorSpecialization, Doctor.doctor_name).join(Doctor).filter(
        DoctorSpecialization.doctor_id == doctor_id
    ).all()
    
    if not results:
        # 의사가 존재하는지 확인
        doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"의사 ID {doctor_id}를 찾을 수 없습니다."
            )
        return []  # 의사는 존재하지만 전문과목이 없음
    
    # 응답 데이터 구성
    specializations = []
    for spec, doctor_name in results:
        specializations.append(schemas.DoctorSpecializationResponse(
            **spec.__dict__,
            doctor_name=doctor_name
        ))
    
    return specializations


# =============================================================================
# DoctorStatistics (의사 통계정보) 엔드포인트
# =============================================================================

@router.post("/{doctor_id}/statistics", response_model=schemas.DoctorStatisticsResponse, status_code=status.HTTP_201_CREATED)
def create_doctor_statistics(
    doctor_id: int,
    statistics_data: schemas.DoctorStatisticsCreate,
    db: Session = Depends(get_db)
):
    """
    의사 통계정보 생성 (1:1 관계)
    """
    # 의사 존재 확인
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"의사 ID {doctor_id}를 찾을 수 없습니다."
        )
    
    # 이미 통계정보가 있는지 확인
    existing_stats = db.query(DoctorStatistics).filter(DoctorStatistics.doctor_id == doctor_id).first()
    if existing_stats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 통계정보가 존재합니다. 수정을 원하시면 PUT 메서드를 사용하세요."
        )
    
    # 새 통계정보 생성
    new_statistics = DoctorStatistics(**statistics_data.dict())
    db.add(new_statistics)
    db.commit()
    db.refresh(new_statistics)
    
    # 응답 데이터에 의사 이름 추가
    response_data = schemas.DoctorStatisticsResponse(
        **new_statistics.__dict__,
        doctor_name=doctor.doctor_name
    )
    
    return response_data


@router.get("/{doctor_id}/statistics", response_model=schemas.DoctorStatisticsResponse)
def get_doctor_statistics(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 의사의 통계정보 조회
    """
    # JOIN으로 의사 이름과 함께 조회
    result = db.query(DoctorStatistics, Doctor.doctor_name).join(Doctor).filter(
        DoctorStatistics.doctor_id == doctor_id
    ).first()
    
    if not result:
        # 의사가 존재하는지 확인
        doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"의사 ID {doctor_id}를 찾을 수 없습니다."
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"의사 ID {doctor_id}의 통계정보를 찾을 수 없습니다."
        )
    
    statistics, doctor_name = result
    response_data = schemas.DoctorStatisticsResponse(
        **statistics.__dict__,
        doctor_name=doctor_name
    )
    
    return response_data


@router.put("/{doctor_id}/statistics", response_model=schemas.DoctorStatisticsResponse)
def update_doctor_statistics(
    doctor_id: int,
    statistics_update: schemas.DoctorStatisticsUpdate,
    db: Session = Depends(get_db)
):
    """
    의사 통계정보 수정
    """
    # JOIN으로 통계정보와 의사 이름 조회
    result = db.query(DoctorStatistics, Doctor.doctor_name).join(Doctor).filter(
        DoctorStatistics.doctor_id == doctor_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"의사 ID {doctor_id}의 통계정보를 찾을 수 없습니다."
        )
    
    statistics, doctor_name = result
    
    # 수정할 데이터만 업데이트
    update_data = statistics_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(statistics, field, value)
    
    db.commit()
    db.refresh(statistics)
    
    response_data = schemas.DoctorStatisticsResponse(
        **statistics.__dict__,
        doctor_name=doctor_name
    )
    
    return response_data


# =============================================================================
# DoctorFees (의사 진료비) 엔드포인트
# =============================================================================

@router.post("/{doctor_id}/fees", response_model=schemas.DoctorFeesResponse, status_code=status.HTTP_201_CREATED)
def create_doctor_fees(
    doctor_id: int,
    fees_data: schemas.DoctorFeesCreate,
    db: Session = Depends(get_db)
):
    """
    의사 진료비 정보 추가
    """
    # 의사 존재 확인
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"의사 ID {doctor_id}를 찾을 수 없습니다."
        )
    
    # 새 진료비 정보 생성
    new_fees = DoctorFees(**fees_data.dict())
    db.add(new_fees)
    db.commit()
    db.refresh(new_fees)
    
    # 응답 데이터에 의사 이름 추가
    response_data = schemas.DoctorFeesResponse(
        **new_fees.__dict__,
        doctor_name=doctor.doctor_name
    )
    
    return response_data


@router.get("/{doctor_id}/fees", response_model=List[schemas.DoctorFeesResponse])
def get_doctor_fees(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 의사의 진료비 목록 조회
    """
    # JOIN으로 의사 이름과 함께 조회
    results = db.query(DoctorFees, Doctor.doctor_name).join(Doctor).filter(
        DoctorFees.doctor_id == doctor_id
    ).all()
    
    if not results:
        # 의사가 존재하는지 확인
        doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"의사 ID {doctor_id}를 찾을 수 없습니다."
            )
        return []  # 의사는 존재하지만 진료비 정보가 없음
    
    # 응답 데이터 구성
    fees_list = []
    for fees, doctor_name in results:
        fees_list.append(schemas.DoctorFeesResponse(
            **fees.__dict__,
            doctor_name=doctor_name
        ))
    
    return fees_list


# =============================================================================
# DoctorSchedule (의사 근무일정) 엔드포인트
# =============================================================================

@router.post("/{doctor_id}/schedules", response_model=schemas.DoctorScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_doctor_schedule(
    doctor_id: int,
    schedule_data: schemas.DoctorScheduleCreate,
    db: Session = Depends(get_db)
):
    """
    의사 근무일정 추가
    """
    # 의사 존재 확인
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"의사 ID {doctor_id}를 찾을 수 없습니다."
        )
    
    # 새 근무일정 생성
    new_schedule = DoctorSchedule(**schedule_data.dict())
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    
    # 응답 데이터에 의사 이름 추가
    response_data = schemas.DoctorScheduleResponse(
        **new_schedule.__dict__,
        doctor_name=doctor.doctor_name
    )
    
    return response_data


@router.get("/{doctor_id}/schedules", response_model=List[schemas.DoctorScheduleResponse])
def get_doctor_schedules(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 의사의 근무일정 목록 조회
    """
    # JOIN으로 의사 이름과 함께 조회
    results = db.query(DoctorSchedule, Doctor.doctor_name).join(Doctor).filter(
        DoctorSchedule.doctor_id == doctor_id
    ).all()
    
    if not results:
        # 의사가 존재하는지 확인
        doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"의사 ID {doctor_id}를 찾을 수 없습니다."
            )
        return []  # 의사는 존재하지만 근무일정이 없음
    
    # 응답 데이터 구성
    schedules_list = []
    for schedule, doctor_name in results:
        schedules_list.append(schemas.DoctorScheduleResponse(
            **schedule.__dict__,
            doctor_name=doctor_name
        ))
    
    return schedules_list


@router.put("/{doctor_id}/schedules/{schedule_id}", response_model=schemas.DoctorScheduleResponse)
def update_doctor_schedule(
    doctor_id: int,
    schedule_id: int,
    schedule_update: schemas.DoctorScheduleUpdate,
    db: Session = Depends(get_db)
):
    """
    의사 근무일정 수정
    """
    # JOIN으로 일정과 의사 이름 조회
    result = db.query(DoctorSchedule, Doctor.doctor_name).join(Doctor).filter(
        DoctorSchedule.schedule_id == schedule_id,
        DoctorSchedule.doctor_id == doctor_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"의사 일정 ID {schedule_id}를 찾을 수 없습니다."
        )
    
    schedule, doctor_name = result
    
    # 수정할 데이터만 업데이트
    update_data = schedule_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)
    
    db.commit()
    db.refresh(schedule)
    
    response_data = schemas.DoctorScheduleResponse(
        **schedule.__dict__,
        doctor_name=doctor_name
    )
    
    return response_data


@router.delete("/{doctor_id}/schedules/{schedule_id}", response_model=schemas.MessageResponse)
def delete_doctor_schedule(
    doctor_id: int,
    schedule_id: int,
    db: Session = Depends(get_db)
):
    """
    의사 근무일정 삭제
    """
    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.schedule_id == schedule_id,
        DoctorSchedule.doctor_id == doctor_id
    ).first()
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"의사 일정 ID {schedule_id}를 찾을 수 없습니다."
        )
    
    db.delete(schedule)
    db.commit()
    
    return schemas.MessageResponse(message=f"일정 ID {schedule_id}가 삭제되었습니다.")


# =============================================================================
# 추가 유틸리티 엔드포인트
# =============================================================================

@router.get("/search/by-name/{doctor_name}", response_model=List[schemas.DoctorResponse])
def search_doctors_by_name(
    doctor_name: str,
    db: Session = Depends(get_db)
):
    """
    의사 이름으로 검색 (부분 일치)
    """
    doctors = db.query(Doctor).filter(
        Doctor.doctor_name.ilike(f"%{doctor_name}%")  # 대소문자 무관 부분 일치
    ).all()
    
    return doctors


@router.get("/search/by-specialty/{specialty_name}", response_model=List[schemas.DoctorResponse])
def search_doctors_by_specialty(
    specialty_name: str,
    db: Session = Depends(get_db)
):
    """
    전문과목으로 의사 검색
    """
    doctors = db.query(Doctor).join(DoctorSpecialization).filter(
        DoctorSpecialization.specializations_name.ilike(f"%{specialty_name}%")
    ).distinct().all()
    
    return doctors