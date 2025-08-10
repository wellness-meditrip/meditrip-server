"""
routes.py - Reservation Service API Routes
예약 관리 시스템의 API 엔드포인트 정의
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from typing import List, Optional
import logging
import json
import base64
import io
import requests
import asyncio
from datetime import datetime, date, time, timedelta
from PIL import Image

from database import get_database
from models import Reservation, ReservationImage
from schemas import (
    ReservationCreate, ReservationUpdate, ReservationResponse, ReservationListResponse,
    PaginatedResponse, ApiResponse, ReservationSearchParams, AvailableTimesResponse,
    TimeSlotResponse, ReservationStatus, InterpreterLanguage
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Service URLs 설정 (프로덕션 환경)
HOSPITAL_SERVICE_URL = "https://wellness-meditrip-backend.eastus2.cloudapp.azure.com:8015"
DOCTOR_SERVICE_URL = "https://wellness-meditrip-backend.eastus2.cloudapp.azure.com:8011"

# === Reservation CRUD Operations ===

@router.post("/reservations", response_model=ApiResponse, status_code=201)
async def create_reservation(
    reservation_data: ReservationCreate,
    db: Session = Depends(get_database)
):
    print(f"🚀 RESERVATION CREATE CALLED: {reservation_data.hospital_id}")
    logger.error(f"🚀 RESERVATION CREATE CALLED: {reservation_data.hospital_id}")
    """새 예약 생성"""
    try:
        logger.info(f"🎯 예약 생성 요청: 병원 {reservation_data.hospital_id}, 날짜 {reservation_data.reservation_date}, 시간 {reservation_data.reservation_time}")
        
        # 병원 운영시간 검증
        is_valid = await validate_hospital_operating_hours(
            reservation_data.hospital_id,
            reservation_data.reservation_date,
            reservation_data.reservation_time
        )
        
        logger.info(f"🔍 운영시간 검증 결과: {is_valid}")
        
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="선택한 날짜와 시간이 병원 운영시간에 포함되지 않습니다."
            )
        
        # 중복 예약 확인
        existing_reservation = db.query(Reservation).filter(
            and_(
                Reservation.hospital_id == reservation_data.hospital_id,
                Reservation.reservation_date == reservation_data.reservation_date,
                Reservation.reservation_time == reservation_data.reservation_time,
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.CONFIRMED])
            )
        ).first()
        
        if existing_reservation:
            raise HTTPException(
                status_code=409,
                detail="해당 시간에 이미 예약이 존재합니다."
            )
        
        # 새 예약 생성
        new_reservation = Reservation(
            user_id=reservation_data.user_id,
            hospital_id=reservation_data.hospital_id,
            doctor_id=reservation_data.doctor_id,
            symptoms=reservation_data.symptoms,
            current_medications=reservation_data.current_medications,
            reservation_date=reservation_data.reservation_date,
            reservation_time=reservation_data.reservation_time,
            contact_email=reservation_data.contact_email,
            contact_phone=reservation_data.contact_phone,
            interpreter_language=reservation_data.interpreter_language,
            additional_notes=reservation_data.additional_notes,
            status=ReservationStatus.PENDING
        )
        
        db.add(new_reservation)
        db.flush()  # reservation_id 생성을 위해 flush
        
        # 이미지 추가 (Base64 처리)
        for image_data in reservation_data.images:
            # Base64 이미지 처리
            processed_image = process_base64_image(
                image_data.image_data,
                image_data.image_type
            )
            
            image = ReservationImage(
                reservation_id=new_reservation.reservation_id,
                image_data=processed_image["processed_data"],
                image_type=processed_image["image_type"],
                original_filename=image_data.original_filename,
                file_size=processed_image["file_size"],
                width=processed_image["width"],
                height=processed_image["height"],
                image_order=image_data.image_order,
                alt_text=image_data.alt_text
            )
            db.add(image)
        
        db.commit()
        
        logger.info(f"✅ 새 예약 생성 완료: {new_reservation.reservation_id}")
        
        return ApiResponse(
            success=True,
            message="예약이 성공적으로 생성되었습니다.",
            data={"reservation_id": new_reservation.reservation_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 예약 생성 실패: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="예약 생성 중 오류가 발생했습니다.")

@router.get("/reservations/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: int = Path(..., description="예약 ID"),
    db: Session = Depends(get_database)
):
    """예약 상세 조회"""
    reservation = db.query(Reservation).filter(
        Reservation.reservation_id == reservation_id
    ).first()
    
    if not reservation:
        raise HTTPException(status_code=404, detail="예약을 찾을 수 없습니다.")
    
    return reservation

@router.put("/reservations/{reservation_id}", response_model=ApiResponse)
async def update_reservation(
    reservation_id: int = Path(..., description="예약 ID"),
    reservation_data: ReservationUpdate = ...,
    db: Session = Depends(get_database)
):
    """예약 수정"""
    try:
        reservation = db.query(Reservation).filter(
            Reservation.reservation_id == reservation_id
        ).first()
        
        if not reservation:
            raise HTTPException(status_code=404, detail="예약을 찾을 수 없습니다.")
        
        # 예약 날짜/시간이 변경되는 경우 운영시간 검증
        if reservation_data.reservation_date or reservation_data.reservation_time:
            check_date = reservation_data.reservation_date or reservation.reservation_date
            check_time = reservation_data.reservation_time or reservation.reservation_time
            
            is_valid = await validate_hospital_operating_hours(
                reservation.hospital_id, check_date, check_time
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail="선택한 날짜와 시간이 병원 운영시간에 포함되지 않습니다."
                )
        
        # 수정할 필드들 업데이트
        update_data = reservation_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(reservation, field, value)
        
        reservation.updated_at = datetime.now()
        db.commit()
        
        logger.info(f"✅ 예약 수정 완료: {reservation_id}")
        
        return ApiResponse(
            success=True,
            message="예약이 성공적으로 수정되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 예약 수정 실패: {e}")
        raise HTTPException(status_code=500, detail="예약 수정 중 오류가 발생했습니다.")

@router.delete("/reservations/{reservation_id}", response_model=ApiResponse)
async def cancel_reservation(
    reservation_id: int = Path(..., description="예약 ID"),
    db: Session = Depends(get_database)
):
    """예약 취소"""
    try:
        reservation = db.query(Reservation).filter(
            Reservation.reservation_id == reservation_id
        ).first()
        
        if not reservation:
            raise HTTPException(status_code=404, detail="예약을 찾을 수 없습니다.")
        
        if reservation.status == ReservationStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="이미 취소된 예약입니다.")
        
        if reservation.status == ReservationStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="완료된 예약은 취소할 수 없습니다.")
        
        reservation.status = ReservationStatus.CANCELLED
        reservation.updated_at = datetime.now()
        db.commit()
        
        logger.info(f"✅ 예약 취소 완료: {reservation_id}")
        
        return ApiResponse(
            success=True,
            message="예약이 성공적으로 취소되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 예약 취소 실패: {e}")
        raise HTTPException(status_code=500, detail="예약 취소 중 오류가 발생했습니다.")

# === Reservation Search and List ===

@router.get("/reservations", response_model=PaginatedResponse)
async def search_reservations(
    hospital_id: Optional[int] = Query(None, description="병원 ID"),
    user_id: Optional[int] = Query(None, description="사용자 ID"),
    doctor_id: Optional[int] = Query(None, description="의사 ID"),
    status: Optional[ReservationStatus] = Query(None, description="예약 상태"),
    date_from: Optional[date] = Query(None, description="시작 날짜"),
    date_to: Optional[date] = Query(None, description="종료 날짜"),
    interpreter_language: Optional[InterpreterLanguage] = Query(None, description="통역 언어"),
    limit: int = Query(20, ge=1, le=100, description="페이지 크기"),
    offset: int = Query(0, ge=0, description="페이지 오프셋"),
    db: Session = Depends(get_database)
):
    """예약 검색 및 목록 조회"""
    try:
        # 기본 쿼리
        query = db.query(Reservation)
        
        # 필터 조건 적용
        if hospital_id:
            query = query.filter(Reservation.hospital_id == hospital_id)
        if user_id:
            query = query.filter(Reservation.user_id == user_id)
        if doctor_id:
            query = query.filter(Reservation.doctor_id == doctor_id)
        if status:
            query = query.filter(Reservation.status == status)
        if date_from:
            query = query.filter(Reservation.reservation_date >= date_from)
        if date_to:
            query = query.filter(Reservation.reservation_date <= date_to)
        if interpreter_language:
            query = query.filter(Reservation.interpreter_language == interpreter_language)
        
        # 총 개수 조회
        total = query.count()
        
        # 페이지네이션 적용
        reservations = query.order_by(desc(Reservation.created_at)).offset(offset).limit(limit).all()
        
        # 병원명과 의사명 조회를 위한 ID 수집
        hospital_ids = list(set([r.hospital_id for r in reservations if r.hospital_id]))
        doctor_ids = list(set([r.doctor_id for r in reservations if r.doctor_id]))
        
        # 병원명과 의사명 병렬 조회
        hospital_names = await get_multiple_hospital_names(hospital_ids) if hospital_ids else {}
        doctor_names = await get_multiple_doctor_names(doctor_ids) if doctor_ids else {}
        
        # 응답 데이터 구성
        items = []
        for reservation in reservations:
            image_count = len(reservation.images)
            hospital_name = hospital_names.get(reservation.hospital_id, f"병원_{reservation.hospital_id}")
            doctor_name = doctor_names.get(reservation.doctor_id, f"의사_{reservation.doctor_id}") if reservation.doctor_id else None
            
            items.append({
                "reservation_id": reservation.reservation_id,
                "hospital_id": reservation.hospital_id,
                "hospital_name": hospital_name,
                "doctor_id": reservation.doctor_id,
                "doctor_name": doctor_name,
                "user_id": reservation.user_id,
                "symptoms": reservation.symptoms,
                "reservation_date": reservation.reservation_date,
                "reservation_time": reservation.reservation_time,
                "status": reservation.status,
                "contact_email": reservation.contact_email,
                "contact_phone": reservation.contact_phone,
                "interpreter_language": reservation.interpreter_language,
                "created_at": reservation.created_at,
                "image_count": image_count
            })
        
        return PaginatedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_next=offset + limit < total,
            has_prev=offset > 0
        )
        
    except Exception as e:
        logger.error(f"❌ 예약 검색 실패: {e}")
        raise HTTPException(status_code=500, detail="예약 검색 중 오류가 발생했습니다.")

# === Available Times API ===

@router.get("/available-times/{hospital_id}", response_model=AvailableTimesResponse)
async def get_available_times(
    hospital_id: int = Path(..., description="병원 ID"),
    date: date = Query(..., description="조회할 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_database)
):
    """특정 병원의 특정 날짜 가능한 시간대 조회"""
    try:
        # 병원 운영시간 조회
        operating_hours = await get_hospital_operating_hours(hospital_id)
        
        if not operating_hours:
            raise HTTPException(status_code=404, detail="병원 정보를 찾을 수 없습니다.")
        
        # 해당 날짜의 기존 예약 조회
        existing_reservations = db.query(Reservation).filter(
            and_(
                Reservation.hospital_id == hospital_id,
                Reservation.reservation_date == date,
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.CONFIRMED])
            )
        ).all()
        
        reserved_times = [res.reservation_time for res in existing_reservations]
        
        # 시간대 생성 (30분 간격)
        time_slots = []
        
        if not isinstance(operating_hours, list):
            operating_hours = []
        
        # 요일 변환: 0=월요일, 1=화요일, ..., 6=일요일
        weekday_num = date.weekday()
        
        # 해당 요일의 운영시간 찾기
        day_schedule = None
        for schedule in operating_hours:
            if schedule.get('day_of_week') == weekday_num:
                day_schedule = schedule
                break
        
        if day_schedule and not day_schedule.get('is_closed', True):
            open_time = datetime.strptime(day_schedule['open_time'], '%H:%M').time()
            close_time = datetime.strptime(day_schedule['close_time'], '%H:%M').time()
            
            # 점심시간 정보
            lunch_start = day_schedule.get('lunch_start')
            lunch_end = day_schedule.get('lunch_end')
            lunch_start_time = None
            lunch_end_time = None
            
            if lunch_start and lunch_end:
                lunch_start_time = datetime.strptime(lunch_start, '%H:%M').time()
                lunch_end_time = datetime.strptime(lunch_end, '%H:%M').time()
            
            current_time = open_time
            
            while current_time < close_time:
                # 예약 가능 여부 확인
                is_available = current_time not in reserved_times
                reason = None
                
                if not is_available:
                    reason = "이미 예약됨"
                elif lunch_start_time and lunch_end_time and lunch_start_time <= current_time <= lunch_end_time:
                    is_available = False
                    reason = "점심시간"
                
                time_slots.append(TimeSlotResponse(
                    time=current_time.strftime('%H:%M'),
                    available=is_available,
                    reason=reason
                ))
                
                # 30분 추가
                current_datetime = datetime.combine(date.today(), current_time)
                current_datetime += timedelta(minutes=30)
                current_time = current_datetime.time()
        
        return AvailableTimesResponse(
            hospital_id=hospital_id,
            date=date,
            time_slots=time_slots,
            operating_hours=operating_hours
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 가능한 시간대 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="가능한 시간대 조회 중 오류가 발생했습니다.")

# === Helper Functions ===

async def get_hospital_operating_hours(hospital_id: int):
    """hospital-service에서 병원 운영시간 조회"""
    try:
        logger.info(f"🏥 병원 {hospital_id} 정보 조회 시작: {HOSPITAL_SERVICE_URL}/hospitals/{hospital_id}")
        response = requests.get(
            f"{HOSPITAL_SERVICE_URL}/hospitals/{hospital_id}",
            timeout=10.0
        )
        logger.info(f"🔄 Hospital-service 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            hospital_data = response.json()
            logger.info(f"📋 병원 데이터 수신: hospital_details 길이 = {len(hospital_data.get('hospital_details', []))}")
            
            # hospital_details에서 operating_hours 추출
            if hospital_data.get("hospital_details") and hospital_data["hospital_details"]:
                operating_hours = hospital_data["hospital_details"][0].get("operating_hours")
                logger.info(f"📊 운영시간 원본 데이터: {operating_hours} (타입: {type(operating_hours)})")
                
                if operating_hours and isinstance(operating_hours, str):
                    parsed_hours = json.loads(operating_hours)
                    logger.info(f"📅 파싱된 운영시간: {parsed_hours}")
                    return parsed_hours
                elif operating_hours and isinstance(operating_hours, list):
                    logger.info(f"📅 이미 리스트인 운영시간: {operating_hours}")
                    return operating_hours
        else:
            logger.error(f"❌ Hospital-service 응답 오류: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"병원 {hospital_id} 운영시간 조회 중 오류: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        return None

async def validate_hospital_operating_hours(hospital_id: int, reservation_date: date, reservation_time: time) -> bool:
    """병원 운영시간 검증"""
    try:
        operating_hours = await get_hospital_operating_hours(hospital_id)
        logger.info(f"🔍 병원 {hospital_id} 운영시간 조회 결과: {operating_hours}")
        
        if not operating_hours or not isinstance(operating_hours, list):
            logger.error(f"❌ 운영시간 정보가 없거나 잘못된 형식: {operating_hours}")
            return False
        
        # 요일 변환: 0=월요일, 1=화요일, ..., 6=일요일
        weekday_num = reservation_date.weekday()
        logger.info(f"🗓️ 예약 날짜 {reservation_date}의 요일: {weekday_num} (0=월요일)")
        
        # 해당 요일의 운영시간 찾기
        day_schedule = None
        for schedule in operating_hours:
            if schedule.get('day_of_week') == weekday_num:
                day_schedule = schedule
                break
        
        logger.info(f"📅 해당 요일 운영시간: {day_schedule}")
        
        if not day_schedule:
            logger.error("❌ 해당 요일의 운영시간 정보가 없음")
            return False
        
        # 휴무일인지 확인
        if day_schedule.get('is_closed', True):
            logger.error("❌ 해당 요일은 휴무일")
            return False
        
        # 운영시간 확인
        open_time = datetime.strptime(day_schedule['open_time'], '%H:%M').time()
        close_time = datetime.strptime(day_schedule['close_time'], '%H:%M').time()
        logger.info(f"⏰ 운영시간: {open_time} ~ {close_time}, 예약시간: {reservation_time}")
        
        # 점심시간 확인 (선택사항)
        lunch_start = day_schedule.get('lunch_start')
        lunch_end = day_schedule.get('lunch_end')
        
        # 기본 운영시간 내인지 확인
        if not (open_time <= reservation_time <= close_time):
            logger.error(f"❌ 예약시간 {reservation_time}이 운영시간 {open_time}~{close_time} 범위를 벗어남")
            return False
        
        # 점심시간 제외 확인
        if lunch_start and lunch_end:
            lunch_start_time = datetime.strptime(lunch_start, '%H:%M').time()
            lunch_end_time = datetime.strptime(lunch_end, '%H:%M').time()
            logger.info(f"🍽️ 점심시간: {lunch_start_time} ~ {lunch_end_time}")
            
            # 점심시간 중이면 예약 불가
            if lunch_start_time <= reservation_time <= lunch_end_time:
                logger.error(f"❌ 예약시간 {reservation_time}이 점심시간 {lunch_start_time}~{lunch_end_time} 중")
                return False
        
        logger.info("✅ 운영시간 검증 통과")
        return True
        
    except Exception as e:
        logger.error(f"운영시간 검증 중 오류: {e}")
        return False

async def get_hospital_name(hospital_id: int) -> str:
    """hospital-service에서 병원명 조회"""
    try:
        response = requests.get(
            f"{HOSPITAL_SERVICE_URL}/hospitals/{hospital_id}",
            timeout=5.0
        )
        if response.status_code == 200:
            hospital_data = response.json()
            return hospital_data.get("hospital_name", f"병원_{hospital_id}")
        else:
            return f"병원_{hospital_id}"
    except Exception as e:
        logger.error(f"병원 {hospital_id} 이름 조회 중 오류: {e}")
        return f"병원_{hospital_id}"

async def get_doctor_name(doctor_id: int) -> str:
    """doctor-service에서 의사명 조회"""
    try:
        response = requests.get(
            f"{DOCTOR_SERVICE_URL}/doctors/{doctor_id}",
            timeout=5.0
        )
        if response.status_code == 200:
            doctor_data = response.json()
            return doctor_data.get("doctor_name", f"의사_{doctor_id}")
        else:
            return f"의사_{doctor_id}"
    except Exception as e:
        logger.error(f"의사 {doctor_id} 이름 조회 중 오류: {e}")
        return f"의사_{doctor_id}"

async def get_multiple_hospital_names(hospital_ids: List[int]) -> dict:
    """여러 병원명을 병렬로 조회"""
    if not hospital_ids:
        return {}
    
    tasks = [get_hospital_name(hospital_id) for hospital_id in hospital_ids]
    results = await asyncio.gather(*tasks)
    
    return dict(zip(hospital_ids, results))

async def get_multiple_doctor_names(doctor_ids: List[int]) -> dict:
    """여러 의사명을 병렬로 조회"""
    if not doctor_ids:
        return {}
    
    tasks = [get_doctor_name(doctor_id) for doctor_id in doctor_ids]
    results = await asyncio.gather(*tasks)
    
    return dict(zip(doctor_ids, results))

def process_base64_image(image_data: str, image_type: str) -> dict:
    """Base64 이미지 처리 및 메타데이터 추출"""
    try:
        # Data URL 형식 처리
        if image_data.startswith('data:image'):
            if ',' in image_data:
                image_data = image_data.split(',', 1)[1]
        
        # Base64 디코딩
        decoded_image = base64.b64decode(image_data)
        file_size = len(decoded_image)
        
        # PIL로 이미지 정보 추출
        image_io = io.BytesIO(decoded_image)
        with Image.open(image_io) as img:
            width, height = img.size
            format_type = img.format.lower() if img.format else image_type
        
        return {
            "file_size": file_size,
            "width": width,
            "height": height,
            "image_type": format_type,
            "processed_data": image_data
        }
        
    except Exception as e:
        raise ValueError(f"이미지 처리 중 오류: {str(e)}")

# === Health Check ===

@router.get("/health", response_model=ApiResponse)
async def health_check(db: Session = Depends(get_database)):
    """헬스 체크"""
    try:
        # 간단한 DB 쿼리로 연결 확인
        db.execute(text("SELECT 1"))
        
        return ApiResponse(
            success=True,
            message="Reservation Service is healthy"
        )
        
    except Exception as e:
        logger.error(f"❌ 헬스 체크 실패: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")