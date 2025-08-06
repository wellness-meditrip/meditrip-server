
import os
import importlib
from pathlib import Path
from fastapi import FastAPI, APIRouter, Request, HTTPException
from dotenv import load_dotenv
import logging
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from common.init_data import initialize_all_data

load_dotenv()

app = FastAPI(
    title="Auth Service API",
    description="""
    **인증 관리 서비스**
    
    ## 주요 기능
    - **로그인/로그아웃** 관리
    - **소셜 로그인** (Google, LINE) 연동
    - **토큰 관리** (JWT 발급/검증)
    - **사용자 인증** 상태 확인
    - **세션/쿠키** 관리
    
    ## 데이터베이스
    - PostgreSQL의 `auth_db` 사용
    - 2개 테이블: users, refresh_tokens
    
    ## 포트
    - 8001 (Docker 내부: 8000)
    """,
    version="1.0.0",
    contact={
        "name": "이규연(lee@gyuyeon.dev)"
    }
)


# CORS 미들웨어 추가 (프론트엔드와의 통신을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "https://localhost:3000",
        "https://localhost:3001",
        "https://wellness-meditrip-frontend.vercel.app",
        "https://wellness-meditrip-backend.eastus2.cloudapp.azure.com",
        "*"  # 개발 환경을 위해 모든 origin 허용
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 초기 데이터 생성"""
    try:
        logger.info("Auth Service가 시작됩니다. 초기 데이터를 생성합니다...")
        initialize_all_data()
        logger.info("Auth Service 초기화가 완료되었습니다.")
    except Exception as e:
        logger.error(f"Auth Service 초기화 중 오류가 발생했습니다: {e}")

async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})

app.exception_handler(Exception)(global_exception_handler)

def auto_register_routes():
    routes_dir = Path(__file__).parent / "routes"
    
    for route_file in routes_dir.glob("*.py"):
        if route_file.name.startswith("_"): 
            continue
            
        module_name = route_file.stem 
        
        try:
            module = importlib.import_module(f"routes.{module_name}")
            
            possible_router_names = [
                module_name,
                f"{module_name}_router", 
                "router",
            ]
            
            for router_name in possible_router_names:
                if hasattr(module, router_name):
                    router = getattr(module, router_name)
                    if isinstance(router, APIRouter):
                        app.include_router(router)
                        print(f"Registered router: {module_name} -> {router_name}")
                        break
            else:
                print(f"No router found in {module_name}.py")
                
        except Exception as e:
            print(f"Failed to load {module_name}: {e}")

# 라우터 자동 등록 실행
auto_register_routes()

# =============================================================================
# 헬스 체크 및 기본 엔드포인트
# =============================================================================


@app.get("/", tags=["Health Check"])
def root():
    """
    서비스 상태 확인 (루트 엔드포인트)
    """
    return {
        "service": "Auth Service",
        "status": "healthy",
        "version": "1.0.0",
        "message": "인증 관리 서비스가 정상적으로 작동 중입니다!️"
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        # 50MB 제한 설정
        limit_max_requests=1000,
        timeout_keep_alive=60
    )
