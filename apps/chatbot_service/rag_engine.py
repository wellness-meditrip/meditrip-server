"""
rag_engine.py - RAG (Retrieval-Augmented Generation) 엔진
PDF 문서 기반 질답 시스템 핵심 로직
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from vector_store import QdrantVectorStore

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG 기반 질답 엔진"""
    
    def __init__(self):
        self.vector_store = QdrantVectorStore()
        self.llm = None
        self.text_splitter = None
        self.documents_loaded = False
        self._initialize_llm()
        self._initialize_text_splitter()
    
    def _initialize_llm(self):
        """OpenAI ChatGPT 모델 초기화"""
        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
            
            self.llm = ChatOpenAI(
                openai_api_key=openai_api_key,
                model_name="gpt-4o-mini",
                temperature=0.1,
                max_tokens=1000
            )
            logger.info("✅ OpenAI ChatGPT 모델 초기화 완료")
        except Exception as e:
            logger.error(f"❌ OpenAI 모델 초기화 실패: {e}")
            raise
    
    def _initialize_text_splitter(self):
        """텍스트 분할기 초기화 (토큰 제한 고려)"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,         # 800자 단위로 분할 (토큰 절약)
            chunk_overlap=100,      # 100자 오버랩
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        logger.info("✅ 텍스트 분할기 초기화 완료 (800자 청크)")
    
    async def initialize_documents(self):
        """PDF 문서 로드 및 벡터 저장소 초기화"""
        try:
            # 컬렉션 생성
            if not self.vector_store.create_collection():
                raise Exception("벡터 컬렉션 생성 실패")
            
            # 기존 문서가 있는지 확인
            collection_info = self.vector_store.get_collection_info()
            if collection_info.get("points_count", 0) > 0:
                logger.info(f"📋 기존 문서 {collection_info['points_count']}개 발견, 로딩 건너뜀")
                self.documents_loaded = True
                return True
            
            # PDF 파일 로드
            data_dir = Path("/app/data")  # Docker 컨테이너 내부 경로
            pdf_files = list(data_dir.glob("*.pdf"))
            
            if not pdf_files:
                logger.warning("❌ PDF 파일을 찾을 수 없습니다.")
                return False
            
            all_chunks = []
            all_metadatas = []
            
            for pdf_file in pdf_files:
                logger.info(f"📄 PDF 로딩 중: {pdf_file.name}")
                
                # PDF 로더로 문서 로드
                loader = PyPDFLoader(str(pdf_file))
                documents = loader.load()
                
                # 텍스트 분할
                chunks = self.text_splitter.split_documents(documents)
                
                # 메타데이터 추가
                for i, chunk in enumerate(chunks):
                    all_chunks.append(chunk.page_content)
                    all_metadatas.append({
                        "source": pdf_file.name,
                        "page": chunk.metadata.get("page", i),
                        "chunk_id": len(all_chunks) - 1
                    })
                
                logger.info(f"✅ {pdf_file.name}: {len(chunks)}개 청크 생성")
            
            # 벡터 저장소에 저장
            if self.vector_store.add_documents(all_chunks, all_metadatas):
                self.documents_loaded = True
                logger.info(f"🎉 총 {len(all_chunks)}개 문서 청크 로딩 완료!")
                return True
            else:
                raise Exception("문서 저장 실패")
                
        except Exception as e:
            logger.error(f"❌ 문서 초기화 실패: {e}")
            return False
    
    async def generate_answer(self, question: str) -> Dict[str, Any]:
        """질문에 대한 RAG 기반 답변 생성"""
        try:
            if not self.documents_loaded:
                return {
                    "answer": "죄송합니다. 문서가 아직 로딩되지 않았습니다. 잠시 후 다시 시도해주세요.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # 1. 유사한 문서 검색
            logger.info(f"🔍 질문 검색 중: {question[:50]}...")
            search_results = self.vector_store.search_similar(question, limit=5)
            
            if not search_results:
                return {
                    "answer": "죄송합니다. 관련 정보를 찾을 수 없습니다.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # 2. 검색된 문서들을 컨텍스트로 구성
            context_texts = []
            sources = []
            
            for result in search_results:
                context_texts.append(f"[페이지 {result['page']}] {result['text']}")
                sources.append(f"page_{result['page']}")
            
            context = "\n\n".join(context_texts)
            
            # 3. 프롬프트 구성
            system_prompt = """당신은 의료 전문 상담 AI입니다. 제공된 의료 문서를 기반으로 정확하고 도움이 되는 답변을 제공해주세요.

답변 규칙:
1. 제공된 문서 내용만을 기반으로 답변하세요
2. 의료 조언이 필요한 경우 전문의 상담을 권하세요
3. 불확실한 정보는 "문서에서 명확하지 않습니다"라고 명시하세요
4. 친절하고 이해하기 쉽게 설명하세요
5. 한국어로 답변하세요

참고 문서:
{context}"""
            
            user_prompt = f"질문: {question}"
            
            # 4. GPT로 답변 생성
            messages = [
                SystemMessage(content=system_prompt.format(context=context)),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm(messages)
            answer = response.content
            
            # 5. 신뢰도 계산 (검색 결과 점수 기반)
            confidence = min(search_results[0]["score"], 1.0) if search_results else 0.0
            
            logger.info(f"✅ 답변 생성 완료 (신뢰도: {confidence:.2f})")
            
            return {
                "answer": answer,
                "sources": list(set(sources)),  # 중복 제거
                "confidence": round(confidence, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ 답변 생성 실패: {e}")
            return {
                "answer": "죄송합니다. 답변을 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                "sources": [],
                "confidence": 0.0
            }
    
    def get_status(self) -> Dict[str, Any]:
        """RAG 엔진 상태 정보"""
        collection_info = self.vector_store.get_collection_info()
        
        return {
            "documents_loaded": self.documents_loaded,
            "qdrant_status": "connected" if self.vector_store.health_check() else "disconnected",
            "openai_status": "connected" if self.llm else "disconnected",
            "documents_count": collection_info.get("points_count", 0),
            "collection_info": collection_info
        }