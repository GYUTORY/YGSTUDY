---
title: RAG for Code (코드 기반 RAG)
tags: [ai, rag, retrieval-augmented-generation, code, architecture]
updated: 2026-03-27
---

# RAG for Code

## 1. RAG란

**RAG(Retrieval-Augmented Generation)**는 LLM이 응답을 생성하기 전에 관련 정보를 **검색(Retrieval)**하여 컨텍스트에 추가하는 아키텍처 패턴이다. 코드에 적용하면, AI가 코드베이스를 검색하여 관련 파일/함수를 이해한 뒤 코드를 생성한다.

### 1.1 모든 AI 코딩 도구의 기반

실제로 우리가 사용하는 AI 코딩 도구들은 내부적으로 RAG를 사용한다.

```
Cursor가 코드를 수정할 때:
1. 코드베이스 인덱싱 (임베딩 생성)     ← Retrieval
2. 관련 파일/함수 검색                ← Retrieval
3. 검색된 코드를 컨텍스트에 추가        ← Augmented
4. 코드 생성/수정                     ← Generation
```

| AI 도구 | RAG 구현 방식 |
|---------|-------------|
| **Cursor** | 전체 코드베이스 인덱싱 + 시맨틱 검색 |
| **Claude Code** | Glob, Grep으로 파일 검색 후 Read |
| **GitHub Copilot** | @workspace로 프로젝트 컨텍스트 검색 |
---

## 2. 코드 RAG 아키텍처

### 2.1 기본 흐름

```
코드베이스                    RAG 파이프라인                    LLM
┌──────────┐     ┌─────────────────────────┐     ┌──────────┐
│ .ts 파일  │────▶│ 1. 청킹 (Chunking)       │     │          │
│ .java 파일│     │ 2. 임베딩 (Embedding)     │     │  코드    │
│ .py 파일  │     │ 3. 벡터 DB 저장          │     │  생성    │
│ 설정 파일  │     │ 4. 유사도 검색           │────▶│  /수정   │
│ 문서      │     │ 5. 컨텍스트 구성          │     │          │
└──────────┘     └─────────────────────────┘     └──────────┘
```

### 2.2 각 단계 설명

| 단계 | 설명 | 코드에서의 의미 |
|------|------|---------------|
| **청킹** | 코드를 적절한 단위로 분할 | 함수, 클래스, 모듈 단위로 분할 |
| **임베딩** | 텍스트를 벡터(숫자 배열)로 변환 | 코드의 의미를 수치화 |
| **벡터 저장** | 임베딩을 벡터 DB에 저장 | Pinecone, Chroma, Weaviate 등 |
| **유사도 검색** | 쿼리와 유사한 코드 검색 | "인증 로직" → 관련 코드 반환 |
| **컨텍스트 구성** | 검색 결과를 LLM 프롬프트에 추가 | 관련 코드 + 사용자 질문 결합 |

---

## 3. 코드 청킹 전략

코드를 어떻게 분할하느냐가 RAG 품질을 결정한다.

### 3.1 청킹 방식 비교

| 방식 | 설명 | 장점 | 단점 |
|------|------|------|------|
| **고정 크기** | N줄씩 분할 | 간단 | 의미 단위 무시 |
| **함수/클래스 단위** | AST 기반 분할 | 의미 보존 | 구현 복잡 |
| **파일 단위** | 파일 전체를 하나의 청크 | 컨텍스트 완전 | 큰 파일에 비효율 |
| **슬라이딩 윈도우** | 겹치는 구간으로 분할 | 경계 정보 보존 | 중복 저장 |

코드는 **함수/클래스 단위** 청킹이 가장 결과가 좋다. 전체 함수 시그니처, 주석, 본문이 함께 보존되기 때문이다.

### 3.2 코드 청킹 예시

```python
# 함수 단위 청킹 예시

# Chunk 1: UserService.createUser
class UserService:
    async def create_user(self, data: UserCreate) -> User:
        """새 사용자를 생성합니다"""
        existing = await self.repo.find_by_email(data.email)
        if existing:
            raise DuplicateEmailError(data.email)
        user = User(**data.dict())
        return await self.repo.save(user)

# Chunk 2: UserService.get_user
    async def get_user(self, user_id: str) -> User:
        """사용자를 조회합니다"""
        user = await self.repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        return user
```

---

## 4. 임베딩 모델

### 4.1 코드 임베딩 모델 비교

| 모델 | 제공사 | 특징 |
|------|--------|------|
| **text-embedding-3-large** | OpenAI | 범용, 코드도 우수 |
| **Voyage Code 3** | Voyage AI | 코드 특화 |
| **CodeBERT** | Microsoft | 코드+NL 이해 |
| **StarEncoder** | BigCode | 다국어 코드 지원 |

### 4.2 임베딩 생성 예시

```python
from openai import OpenAI

client = OpenAI()

def embed_code(code_chunk: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=code_chunk
    )
    return response.data[0].embedding
```

---

## 5. 벡터 데이터베이스

### 5.1 주요 벡터 DB

| DB | 특징 | 적합한 상황 |
|----|------|-----------|
| **Chroma** | 경량, 임베디드 | 로컬 개발, 프로토타입 |
| **Pinecone** | 관리형 SaaS | 프로덕션, 확장성 |
| **Weaviate** | 오픈소스, 하이브리드 검색 | 자체 호스팅 |
| **pgvector** | PostgreSQL 확장 | 기존 PG 사용 팀 |
| **Qdrant** | 고성능, Rust 기반 | 대규모 인덱싱 |

### 5.2 pgvector 예시

```sql
-- PostgreSQL에 벡터 확장 추가
CREATE EXTENSION vector;

-- 코드 청크 테이블
CREATE TABLE code_chunks (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(3072),  -- text-embedding-3-large
    language TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 유사도 검색
SELECT file_path, chunk_text,
       1 - (embedding <=> $1::vector) AS similarity
FROM code_chunks
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

---

## 6. 실전 활용 패턴

### 6.1 사내 코드 검색 챗봇

```
개발자: "주문 결제 처리 로직이 어디에 있어?"

RAG 챗봇:
1. 쿼리 임베딩 생성
2. 벡터 DB에서 유사 코드 검색
3. 관련 파일/함수 위치 반환
4. 코드 설명 생성
```

### 6.2 코드 리뷰 보조

```
PR 변경 사항 → 관련 기존 코드 검색 → 패턴 일관성 체크
```

### 6.3 문서 자동 생성

```
코드 변경 감지 → 관련 코드 컨텍스트 검색 → API 문서 자동 업데이트
```

---

## 7. RAG vs Fine-tuning

| 항목 | RAG | Fine-tuning |
|------|-----|------------|
| **데이터 업데이트** | 즉시 반영 | 재학습 필요 |
| **비용** | 추론 비용만 | 학습 + 추론 비용 |
| **정확도** | 검색 품질에 의존 | 도메인 특화 높음 |
| **환각** | 근거 기반으로 감소 | 여전히 발생 가능 |
| **구현 난이도** | 중간 | 높음 |
| **추천 상황** | 코드베이스가 자주 변경 | 고정된 코딩 스타일 학습 |

대부분의 경우 **RAG가 더 맞다**. 코드베이스는 계속 변경되므로 실시간 검색이 재학습보다 현실적이다. 필요하면 RAG + Fine-tuning을 조합할 수 있다.

---

## 8. Agentic RAG (A-RAG)

**Agentic RAG**는 단순 검색-생성을 넘어, AI 에이전트가 검색 방법을 **스스로 결정**하는 방식이다.

```
기존 RAG:
  쿼리 → 검색 → 생성  (검색 한 번으로 끝)

Agentic RAG:
  쿼리 → 에이전트가 판단:
    "이 질문은 DB 스키마가 필요하군"
    → DB 스키마 검색
    "관련 서비스 코드도 필요해"
    → 서비스 레이어 코드 검색
    "테스트 패턴도 참고하자"
    → 테스트 코드 검색
    "검색 결과가 부족하면 다시 검색"
    → 재검색 (self-reflection)
    → 모든 컨텍스트 조합하여 생성
```

기존 RAG와 가장 큰 차이는 **검색 루프**다. 기존 RAG는 검색을 한 번 하고 끝이지만, Agentic RAG는 검색 결과를 보고 부족하면 다시 검색한다. 검색 쿼리를 재작성하거나, 다른 소스에서 추가 검색하는 판단을 에이전트가 한다.

### 8.1 Agentic RAG의 핵심 구성 요소

| 구성 요소 | 설명 |
|-----------|------|
| **라우터(Router)** | 쿼리를 분석하여 어떤 데이터 소스를 검색할지 결정 |
| **Self-reflection** | 검색 결과가 질문에 충분한지 판단하고, 부족하면 재검색 |
| **쿼리 재작성** | 검색 결과가 부정확하면 쿼리를 바꿔서 다시 시도 |
| **멀티 소스 검색** | 코드, 문서, 이슈 트래커, 위키 등 여러 소스를 동시에 검색 |

### 8.2 실제 도구에서의 동작

Claude Code를 예로 들면:

```
사용자: "주문 취소 시 환불 처리가 안 되는 버그 수정해줘"

에이전트 내부 동작:
1. Grep으로 "cancel", "refund" 키워드 검색
2. 관련 파일 3개 발견 → Read로 코드 확인
3. "환불 로직이 PaymentService에 있을 것 같다"
   → PaymentService 검색
4. 테스트 코드에서 환불 관련 테스트 검색
5. 모든 컨텍스트를 조합하여 버그 원인 파악 + 수정 코드 생성
```

이런 식으로 Claude Code, Cursor 같은 AI 코딩 도구가 내부적으로 Agentic RAG를 수행한다.

RAG 파이프라인의 구현 방법과 각 단계별 세부 사항은 [RAG 파이프라인](RAG_Pipeline.md) 문서를 참고한다.

---

## 참고

- [LangChain RAG 튜토리얼](https://python.langchain.com/docs/tutorials/rag/)
- [OpenAI 임베딩 가이드](https://platform.openai.com/docs/guides/embeddings)
- [pgvector 공식 문서](https://github.com/pgvector/pgvector)
- [Chroma 공식 문서](https://docs.trychroma.com)
