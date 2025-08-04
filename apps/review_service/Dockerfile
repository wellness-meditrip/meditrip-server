# review_service Dockerfile
# 리뷰 관리 마이크로서비스용 Docker 이미지

# Python 3.11 slim 이미지 사용 (경량화)
FROM python:3.11-slim

# 메타데이터 설정
LABEL maintainer="Development Team <dev@meditrip.com>"
LABEL service="review_service"
LABEL version="1.0.0"
LABEL description="리뷰 관리 마이크로서비스"

# 환경변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요 패키지 설치
# PostgreSQL 클라이언트 라이브러리 설치 (psycopg2 의존성)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 먼저 복사 (Docker 레이어 캐싱 최적화)
COPY requirements.txt /app/requirements.txt

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY apps/review_service/ /app/

# 애플리케이션 사용자 생성 (보안 강화)
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# 컨테이너가 사용할 포트 노출
EXPOSE 8000

# 헬스체크 설정 (컨테이너 상태 모니터링)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행 명령어
# uvicorn으로 FastAPI 서버 시작
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]