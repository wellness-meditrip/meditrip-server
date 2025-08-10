"""
routes.py - Review Service API Routes
리뷰 관리 시스템의 API 엔드포인트 정의
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional
import logging
import json
import base64
import io
import httpx
import asyncio
import os
import requests
from datetime import datetime
from PIL import Image

from database import get_database
from models import Review, ReviewKeyword, ReviewImage, ReviewKeywordTemplate, ReviewStats
from schemas import (
    ReviewCreate, ReviewUpdate, ReviewResponse, ReviewListResponse,
    ReviewKeywordTemplateCreate, ReviewKeywordTemplateUpdate, ReviewKeywordTemplateResponse,
    ReviewStatsResponse, ReviewSearchParams, PaginatedResponse, ApiResponse,
    KeywordCategory, BulkKeywordCreate, ReviewAnalytics
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Auth Service URL 설정 (프로덕션용)
AUTH_SERVICE_URL = "https://wellness-meditrip-backend.eastus2.cloudapp.azure.com:8013"

# === Review CRUD Operations ===

@router.post("/reviews", response_model=ApiResponse, status_code=201)
async def create_review(
    request: Request,
    db: Session = Depends(get_database)
):
    """새 리뷰 생성"""
    try:
        # 요청 데이터 상세 로깅
        raw_data = await request.json()
        logger.info(f"🔍 리뷰 생성 요청 원본 데이터: {raw_data}")
        
        # Pydantic으로 데이터 검증
        try:
            review_data = ReviewCreate(**raw_data)
            logger.info(f"🔍 리뷰 생성 파싱된 데이터: hospital_id={review_data.hospital_id}, user_id={review_data.user_id}, 이미지 수={len(review_data.images)}")
        except Exception as validation_error:
            logger.error(f"❌ Pydantic 검증 실패: {validation_error}")
            raise HTTPException(status_code=422, detail=f"데이터 검증 실패: {str(validation_error)}")
        
        # 새 리뷰 생성
        new_review = Review(
            hospital_id=review_data.hospital_id,
            user_id=review_data.user_id,
            doctor_id=review_data.doctor_id,
            doctor_name=review_data.doctor_name,
            title=review_data.title,
            content=review_data.content,
            rating=review_data.rating
        )
        
        db.add(new_review)
        db.flush()  # review_id 생성을 위해 flush
        
        # 키워드 추가
        for keyword_data in review_data.keywords:
            keyword = ReviewKeyword(
                review_id=new_review.review_id,
                category=keyword_data.category,
                keyword_code=keyword_data.keyword_code,
                keyword_name=keyword_data.keyword_name,
                is_positive=keyword_data.is_positive
            )
            db.add(keyword)
        
        # 이미지 추가 (Base64 처리)
        for i, image_data in enumerate(review_data.images):
            logger.info(f"🖼️ 이미지 {i+1} 처리 중...")
            # Base64 이미지 처리
            processed_image = process_base64_image(
                image_data.image_data, 
                image_data.image_type
            )
            
            image = ReviewImage(
                review_id=new_review.review_id,
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
        
        # 병원 통계 업데이트 (비동기로 처리 가능)
        await update_hospital_stats(db, review_data.hospital_id)
        
        logger.info(f"✅ 새 리뷰 생성 완료: {new_review.review_id}")
        
        return ApiResponse(
            success=True,
            message="리뷰가 성공적으로 생성되었습니다.",
            data={"review_id": new_review.review_id}
        )
        
    except ValueError as e:
        db.rollback()
        logger.error(f"❌ 리뷰 생성 validation 실패: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 리뷰 생성 실패: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="리뷰 생성 중 오류가 발생했습니다.")


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int = Path(..., description="리뷰 ID"),
    db: Session = Depends(get_database)
):
    """리뷰 상세 조회"""
    review = db.query(Review).filter(
        and_(Review.review_id == review_id, Review.is_active == True)
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")
    
    return review


@router.put("/reviews/{review_id}", response_model=ApiResponse)
async def update_review(
    review_id: int = Path(..., description="리뷰 ID"),
    review_data: ReviewUpdate = ...,
    db: Session = Depends(get_database)
):
    """리뷰 수정"""
    try:
        review = db.query(Review).filter(
            and_(Review.review_id == review_id, Review.is_active == True)
        ).first()
        
        if not review:
            raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")
        
        # 수정할 필드들 업데이트
        update_data = review_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(review, field, value)
        
        review.updated_at = datetime.now()
        db.commit()
        
        # 평점이 변경된 경우 통계 업데이트
        if review_data.rating is not None:
            await update_hospital_stats(db, review.hospital_id)
        
        logger.info(f"✅ 리뷰 수정 완료: {review_id}")
        
        return ApiResponse(
            success=True,
            message="리뷰가 성공적으로 수정되었습니다."
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 리뷰 수정 실패: {e}")
        raise HTTPException(status_code=500, detail="리뷰 수정 중 오류가 발생했습니다.")


@router.delete("/reviews/{review_id}", response_model=ApiResponse)
async def delete_review(
    review_id: int = Path(..., description="리뷰 ID"),
    db: Session = Depends(get_database)
):
    """리뷰 삭제 (소프트 삭제)"""
    try:
        review = db.query(Review).filter(Review.review_id == review_id).first()
        
        if not review:
            raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")
        
        review.is_active = False
        review.updated_at = datetime.now()
        db.commit()
        
        # 통계 업데이트
        await update_hospital_stats(db, review.hospital_id)
        
        logger.info(f"✅ 리뷰 삭제 완료: {review_id}")
        
        return ApiResponse(
            success=True,
            message="리뷰가 성공적으로 삭제되었습니다."
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 리뷰 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="리뷰 삭제 중 오류가 발생했습니다.")


# === Review Search and List ===

@router.get("/reviews", response_model=PaginatedResponse)
async def search_reviews(
    hospital_id: Optional[int] = Query(None, description="병원 ID"),
    user_id: Optional[int] = Query(None, description="사용자 ID"),
    doctor_id: Optional[int] = Query(None, description="의사 ID"),
    rating_min: Optional[float] = Query(None, ge=1.0, le=5.0, description="최소 평점"),
    rating_max: Optional[float] = Query(None, ge=1.0, le=5.0, description="최대 평점"),
    keyword_category: Optional[KeywordCategory] = Query(None, description="키워드 카테고리"),
    keyword_code: Optional[str] = Query(None, description="키워드 코드"),
    limit: int = Query(20, ge=1, le=100, description="페이지 크기"),
    offset: int = Query(0, ge=0, description="페이지 오프셋"),
    db: Session = Depends(get_database)
):
    """리뷰 검색 및 목록 조회"""
    try:
        # 기본 쿼리
        query = db.query(Review).filter(Review.is_active == True)
        
        # 필터 조건 적용
        if hospital_id:
            query = query.filter(Review.hospital_id == hospital_id)
        if user_id:
            query = query.filter(Review.user_id == user_id)
        if doctor_id:
            query = query.filter(Review.doctor_id == doctor_id)
        if rating_min:
            query = query.filter(Review.rating >= rating_min)
        if rating_max:
            query = query.filter(Review.rating <= rating_max)
        
        # 키워드 필터
        if keyword_category or keyword_code:
            query = query.join(ReviewKeyword)
            if keyword_category:
                query = query.filter(ReviewKeyword.category == keyword_category)
            if keyword_code:
                query = query.filter(ReviewKeyword.keyword_code == keyword_code)
        
        # 총 개수 조회
        total = query.count()
        
        # 페이지네이션 적용
        reviews = query.order_by(desc(Review.created_at)).offset(offset).limit(limit).all()
        
        # 사용자 이름 조회 (병렬 처리)
        user_ids = [review.user_id for review in reviews]
        user_names = await get_multiple_user_names(user_ids) if user_ids else {}
        
        # 응답 데이터 구성
        items = []
        for review in reviews:
            keyword_count = len(review.keywords)
            user_name = user_names.get(review.user_id, f"User_{review.user_id}")
            
            # 이미지 리스트 구성
            images = []
            for image in review.images:
                images.append({
                    "id": image.id,
                    "image_data": image.image_data,
                    "image_type": image.image_type,
                    "original_filename": image.original_filename,
                    "file_size": image.file_size,
                    "width": image.width,
                    "height": image.height,
                    "image_order": image.image_order,
                    "alt_text": image.alt_text,
                    "created_at": image.created_at
                })
            
            items.append({
                "review_id": review.review_id,
                "hospital_id": review.hospital_id,
                "user_id": review.user_id,
                "user_name": user_name,
                "doctor_id": review.doctor_id,
                "doctor_name": review.doctor_name,
                "content": review.content,
                "rating": review.rating,
                "created_at": review.created_at,
                "keyword_count": keyword_count,
                "images": images
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
        logger.error(f"❌ 리뷰 검색 실패: {e}")
        raise HTTPException(status_code=500, detail="리뷰 검색 중 오류가 발생했습니다.")


# === Keyword Template Management ===

@router.post("/keyword-templates", response_model=ApiResponse, status_code=201)
async def create_keyword_template(
    template_data: ReviewKeywordTemplateCreate,
    db: Session = Depends(get_database)
):
    """키워드 템플릿 생성"""
    try:
        # 중복 확인
        existing = db.query(ReviewKeywordTemplate).filter(
            ReviewKeywordTemplate.keyword_code == template_data.keyword_code
        ).first()
        
        if existing:
            raise HTTPException(status_code=409, detail="이미 존재하는 키워드 코드입니다.")
        
        template = ReviewKeywordTemplate(**template_data.dict())
        db.add(template)
        db.commit()
        
        logger.info(f"✅ 키워드 템플릿 생성 완료: {template.keyword_code}")
        
        return ApiResponse(
            success=True,
            message="키워드 템플릿이 성공적으로 생성되었습니다.",
            data={"template_id": template.id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 키워드 템플릿 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="키워드 템플릿 생성 중 오류가 발생했습니다.")


@router.get("/keyword-templates", response_model=List[ReviewKeywordTemplateResponse])
async def get_keyword_templates(
    category: Optional[KeywordCategory] = Query(None, description="키워드 카테고리"),
    is_positive: Optional[bool] = Query(None, description="긍정/부정 필터"),
    is_active: bool = Query(True, description="활성 상태"),
    db: Session = Depends(get_database)
):
    """키워드 템플릿 목록 조회"""
    query = db.query(ReviewKeywordTemplate).filter(
        ReviewKeywordTemplate.is_active == is_active
    )
    
    if category:
        query = query.filter(ReviewKeywordTemplate.category == category)
    if is_positive is not None:
        query = query.filter(ReviewKeywordTemplate.is_positive == is_positive)
    
    templates = query.order_by(
        ReviewKeywordTemplate.category,
        ReviewKeywordTemplate.keyword_code
    ).all()
    
    return templates


@router.post("/keyword-templates/bulk", response_model=ApiResponse)
async def create_bulk_keyword_templates(
    bulk_data: BulkKeywordCreate,
    db: Session = Depends(get_database)
):
    """키워드 템플릿 일괄 생성"""
    try:
        created_count = 0
        skipped_count = 0
        
        for template_data in bulk_data.keywords:
            # 중복 확인
            existing = db.query(ReviewKeywordTemplate).filter(
                ReviewKeywordTemplate.keyword_code == template_data.keyword_code
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            template = ReviewKeywordTemplate(**template_data.dict())
            db.add(template)
            created_count += 1
        
        db.commit()
        
        logger.info(f"✅ 키워드 템플릿 일괄 생성 완료: {created_count}개 생성, {skipped_count}개 건너뜀")
        
        return ApiResponse(
            success=True,
            message=f"키워드 템플릿 일괄 생성 완료: {created_count}개 생성, {skipped_count}개 건너뜀"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 키워드 템플릿 일괄 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="키워드 템플릿 일괄 생성 중 오류가 발생했습니다.")


# === Review Statistics ===

@router.get("/stats/{hospital_id}", response_model=ReviewStatsResponse)
async def get_hospital_review_stats(
    hospital_id: int = Path(..., description="병원 ID"),
    db: Session = Depends(get_database)
):
    """병원별 리뷰 통계 조회"""
    stats = db.query(ReviewStats).filter(
        ReviewStats.hospital_id == hospital_id
    ).first()
    
    if not stats:
        # 통계가 없으면 새로 생성
        stats = await create_hospital_stats(db, hospital_id)
    
    return stats


@router.post("/stats/{hospital_id}/refresh", response_model=ApiResponse)
async def refresh_hospital_stats(
    hospital_id: int = Path(..., description="병원 ID"),
    db: Session = Depends(get_database)
):
    """병원 리뷰 통계 갱신"""
    try:
        await update_hospital_stats(db, hospital_id)
        
        return ApiResponse(
            success=True,
            message="리뷰 통계가 성공적으로 갱신되었습니다."
        )
        
    except Exception as e:
        logger.error(f"❌ 통계 갱신 실패: {e}")
        raise HTTPException(status_code=500, detail="통계 갱신 중 오류가 발생했습니다.")


# === Helper Functions ===

async def get_user_name(user_id: int) -> str:
    """auth-service에서 사용자 이름 조회"""
    try:
        response = requests.get(
            f"{AUTH_SERVICE_URL}/profile/user/{user_id}",
            timeout=10.0
        )
        if response.status_code == 200:
            user_data = response.json()
            # nickname이 있으면 nickname 사용, 없으면 username 사용
            nickname = user_data.get("nickname")
            if nickname:
                return nickname
            return user_data.get("username", f"User_{user_id}")
        else:
            logger.warning(f"사용자 {user_id} 정보 조회 실패: {response.status_code}")
            return f"User_{user_id}"
    except Exception as e:
        logger.error(f"사용자 {user_id} 이름 조회 중 오류: {e}")
        return f"User_{user_id}"

async def get_multiple_user_names(user_ids: List[int]) -> dict:
    """여러 사용자 이름을 한 번에 조회"""
    user_names = {}
    
    # 중복 제거
    unique_user_ids = list(set(user_ids))
    
    # 병렬로 사용자 정보 조회
    tasks = [get_user_name(user_id) for user_id in unique_user_ids]
    results = await asyncio.gather(*tasks)
    
    for user_id, user_name in zip(unique_user_ids, results):
        user_names[user_id] = user_name
    
    return user_names

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

async def update_hospital_stats(db: Session, hospital_id: int):
    """병원 리뷰 통계 업데이트"""
    try:
        # 기존 통계 조회 또는 생성
        stats = db.query(ReviewStats).filter(
            ReviewStats.hospital_id == hospital_id
        ).first()
        
        if not stats:
            stats = ReviewStats(hospital_id=hospital_id)
            db.add(stats)
        
        # 리뷰 통계 계산
        reviews = db.query(Review).filter(
            and_(Review.hospital_id == hospital_id, Review.is_active == True)
        ).all()
        
        if not reviews:
            stats.total_reviews = 0
            stats.average_rating = 0.0
            stats.rating_5 = stats.rating_4 = stats.rating_3 = stats.rating_2 = stats.rating_1 = 0
        else:
            stats.total_reviews = len(reviews)
            stats.average_rating = round(sum(r.rating for r in reviews) / len(reviews), 1)
            
            # 평점별 분포
            ratings = [r.rating for r in reviews]
            stats.rating_5 = len([r for r in ratings if r >= 4.5])
            stats.rating_4 = len([r for r in ratings if 3.5 <= r < 4.5])
            stats.rating_3 = len([r for r in ratings if 2.5 <= r < 3.5])
            stats.rating_2 = len([r for r in ratings if 1.5 <= r < 2.5])
            stats.rating_1 = len([r for r in ratings if r < 1.5])
        
        # 키워드 통계 계산
        keyword_stats = {}
        for category in ["CARE", "SERVICE", "FACILITY"]:
            keywords = db.query(ReviewKeyword).join(Review).filter(
                and_(
                    Review.hospital_id == hospital_id,
                    Review.is_active == True,
                    ReviewKeyword.category == category
                )
            ).all()
            
            category_stats = {}
            for keyword in keywords:
                key = f"{keyword.keyword_code}_{keyword.is_positive}"
                if key not in category_stats:
                    category_stats[key] = {
                        "keyword_code": keyword.keyword_code,
                        "keyword_name": keyword.keyword_name,
                        "is_positive": keyword.is_positive,
                        "count": 0
                    }
                category_stats[key]["count"] += 1
            
            keyword_stats[category.lower() + "_keywords"] = list(category_stats.values())
        
        stats.care_keywords = keyword_stats.get("care_keywords", [])
        stats.service_keywords = keyword_stats.get("service_keywords", [])
        stats.facility_keywords = keyword_stats.get("facility_keywords", [])
        
        stats.last_updated = datetime.now()
        db.commit()
        
        logger.info(f"✅ 병원 {hospital_id} 통계 업데이트 완료")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 통계 업데이트 실패: {e}")
        raise


async def create_hospital_stats(db: Session, hospital_id: int) -> ReviewStats:
    """새 병원 통계 생성"""
    stats = ReviewStats(hospital_id=hospital_id)
    db.add(stats)
    await update_hospital_stats(db, hospital_id)
    return stats


# === Health Check ===

@router.get("/health", response_model=ApiResponse)
async def health_check(db: Session = Depends(get_database)):
    """헬스 체크"""
    try:
        # 간단한 DB 쿼리로 연결 확인
        db.execute("SELECT 1")
        
        return ApiResponse(
            success=True,
            message="Review Service is healthy"
        )
        
    except Exception as e:
        logger.error(f"❌ 헬스 체크 실패: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")