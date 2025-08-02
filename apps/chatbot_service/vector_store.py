"""
vector_store.py - Qdrant 벡터 데이터베이스 클라이언트
문서 임베딩 저장 및 유사도 검색 관리
"""

import os
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from langchain.embeddings import OpenAIEmbeddings

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    """Qdrant 벡터 저장소 클라이언트"""
    
    def __init__(self):
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection_name = "medical_documents"
        self.client = None
        self.embeddings = None
        self._initialize_client()
        self._initialize_embeddings()
    
    def _initialize_client(self):
        """Qdrant 클라이언트 초기화"""
        try:
            self.client = QdrantClient(url=self.qdrant_url)
            logger.info(f"✅ Qdrant 연결 성공: {self.qdrant_url}")
        except Exception as e:
            logger.error(f"❌ Qdrant 연결 실패: {e}")
            raise
    
    def _initialize_embeddings(self):
        """OpenAI 임베딩 클라이언트 초기화"""
        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
            
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=openai_api_key,
                model="text-embedding-ada-002"
            )
            logger.info("✅ OpenAI 임베딩 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"❌ OpenAI 임베딩 초기화 실패: {e}")
            raise
    
    def create_collection(self, vector_size: int = 1536):
        """컬렉션 생성 (OpenAI ada-002는 1536 차원)"""
        try:
            # 기존 컬렉션 확인
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name in collection_names:
                logger.info(f"📋 컬렉션 '{self.collection_name}' 이미 존재함")
                return True
            
            # 새 컬렉션 생성
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"✅ 컬렉션 '{self.collection_name}' 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 컬렉션 생성 실패: {e}")
            return False
    
    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        """문서를 벡터로 변환하여 저장 (배치 처리)"""
        try:
            if len(texts) != len(metadatas):
                raise ValueError("텍스트와 메타데이터 개수가 일치하지 않습니다.")
            
            logger.info(f"📄 {len(texts)}개 문서 배치 임베딩 시작...")
            
            # 배치 크기 설정 (OpenAI 토큰 제한 고려)
            batch_size = 50  # 한 번에 50개씩 처리
            total_batches = (len(texts) + batch_size - 1) // batch_size
            
            all_points = []
            point_id = 0
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(texts))
                
                batch_texts = texts[start_idx:end_idx]
                batch_metadatas = metadatas[start_idx:end_idx]
                
                logger.info(f"🔄 배치 {batch_idx + 1}/{total_batches} 처리 중... ({len(batch_texts)}개 문서)")
                
                try:
                    # 배치별 임베딩 생성
                    batch_embeddings = self.embeddings.embed_documents(batch_texts)
                    
                    # 포인트 생성
                    for text, metadata, vector in zip(batch_texts, batch_metadatas, batch_embeddings):
                        point = PointStruct(
                            id=point_id,
                            vector=vector,
                            payload={
                                "text": text,
                                "page": metadata.get("page", 0),
                                "source": metadata.get("source", "unknown"),
                                **metadata
                            }
                        )
                        all_points.append(point)
                        point_id += 1
                    
                    logger.info(f"✅ 배치 {batch_idx + 1} 임베딩 완료")
                    
                except Exception as batch_error:
                    logger.error(f"❌ 배치 {batch_idx + 1} 실패: {batch_error}")
                    # 배치 실패해도 계속 진행
                    continue
            
            if not all_points:
                raise Exception("모든 배치가 실패했습니다.")
            
            # Qdrant에 저장 (배치 업로드)
            logger.info(f"💾 Qdrant에 {len(all_points)}개 문서 저장 중...")
            
            # Qdrant도 배치 크기 제한
            upload_batch_size = 100
            for i in range(0, len(all_points), upload_batch_size):
                batch_points = all_points[i:i + upload_batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch_points
                )
                logger.info(f"📦 {i + len(batch_points)}/{len(all_points)} 문서 저장 완료")
            
            logger.info(f"🎉 총 {len(all_points)}개 문서 저장 완료!")
            return True
            
        except Exception as e:
            logger.error(f"❌ 문서 저장 실패: {e}")
            return False
    
    def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """유사도 기반 문서 검색"""
        try:
            # 쿼리 임베딩 생성
            query_vector = self.embeddings.embed_query(query)
            
            # Qdrant에서 유사도 검색
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True
            )
            
            # 결과 정리
            results = []
            for result in search_results:
                results.append({
                    "text": result.payload.get("text", ""),
                    "page": result.payload.get("page", 0),
                    "source": result.payload.get("source", "unknown"),
                    "score": result.score,
                    "metadata": result.payload
                })
            
            logger.info(f"🔍 검색 결과: {len(results)}개 문서 발견")
            return results
            
        except Exception as e:
            logger.error(f"❌ 검색 실패: {e}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "status": info.status,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance
            }
        except Exception as e:
            logger.error(f"❌ 컬렉션 정보 조회 실패: {e}")
            return {}
    
    def health_check(self) -> bool:
        """Qdrant 연결 상태 확인"""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"❌ Qdrant 헬스체크 실패: {e}")
            return False