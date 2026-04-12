---
title: Functional RAG
tags: [RAG, Functional Programming, LangChain, LCEL, Pipeline, Python]
updated: 2026-04-12
---

# Functional RAG

RAG 파이프라인을 짜다 보면 코드가 금방 복잡해진다. retriever 결과를 가공하고, reranker를 통과시키고, 프롬프트에 끼워넣고, LLM을 호출하는 과정이 한 함수 안에 뒤엉키면 디버깅도 테스트도 어려워진다.

함수형 프로그래밍의 아이디어를 RAG에 가져오면 이 문제를 상당 부분 해결할 수 있다. 각 단계를 순수 함수로 분리하고, 파이프라인을 함수 합성으로 구성하고, 실패를 명시적으로 처리하는 방식이다.

---

## 1. 절차형 RAG의 문제

실무에서 흔히 보는 RAG 코드부터 살펴보자.

```python
def answer_question(query: str) -> str:
    # 임베딩 생성
    embedding = openai.embeddings.create(input=query, model="text-embedding-3-small")
    vector = embedding.data[0].embedding
    
    # 벡터 검색
    results = pinecone_index.query(vector=vector, top_k=10)
    
    # 문서 가져오기
    docs = []
    for match in results.matches:
        doc = db.get_document(match.id)
        if doc:
            docs.append(doc)
    
    # reranking
    scored = cohere_client.rerank(query=query, documents=[d.text for d in docs], top_n=3)
    reranked = [docs[r.index] for r in scored.results]
    
    # 프롬프트 구성
    context = "\n\n".join([d.text for d in reranked])
    prompt = f"다음 문서를 참고해서 답변하세요:\n\n{context}\n\n질문: {query}"
    
    # LLM 호출
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

이 코드의 문제점:

- **테스트 불가능** — 함수 하나가 임베딩, 벡터DB, 외부 DB, Cohere, OpenAI 전부 호출한다. 단위 테스트를 짜려면 mock이 5개 필요하다.
- **재사용 불가능** — reranker를 빼고 싶으면? 검색을 BM25로 바꾸고 싶으면? 함수 내부를 뜯어야 한다.
- **에러 처리가 애매** — 벡터 검색이 빈 결과를 반환하면? Cohere API가 죽으면? try-except를 덕지덕지 붙이게 된다.
- **디버깅이 어렵다** — 파이프라인 중간에서 어떤 문서가 검색되었는지 확인하려면 print를 여기저기 넣어야 한다.

---

## 2. 함수형 RAG의 핵심 원칙

### 2.1 순수 함수로 각 단계를 분리한다

RAG 파이프라인의 각 단계를 입력과 출력이 명확한 순수 함수로 만든다. 외부 상태를 변경하지 않고, 같은 입력에 대해 같은 출력을 반환하는 함수다.

물론 실제로 API 호출이나 DB 조회는 부수 효과(side effect)가 있다. 여기서 말하는 "순수"는 수학적 의미의 순수 함수가 아니라, **각 함수가 자신의 역할만 하고 다른 단계에 간섭하지 않는 것**을 뜻한다.

```python
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class Document:
    id: str
    text: str
    metadata: dict
    score: float = 0.0

# 각 단계를 독립적인 함수로 정의
Retriever = Callable[[str], list[Document]]
Reranker = Callable[[str, list[Document]], list[Document]]
Generator = Callable[[str, list[Document]], str]
```

`Document`를 `frozen=True`로 선언한 이유가 있다. 파이프라인을 통과하면서 Document가 변경되면 어느 단계에서 값이 바뀌었는지 추적이 안 된다. 불변 객체를 쓰면 각 단계가 새 Document를 반환하게 되므로, 파이프라인 어느 지점에서든 상태를 확인할 수 있다.

### 2.2 함수 합성으로 파이프라인을 구성한다

각 단계를 따로 만들었으면, 이를 합성해서 파이프라인을 만든다.

```python
from functools import reduce
from typing import TypeVar, Callable

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')

def compose(f: Callable[[B], C], g: Callable[[A], B]) -> Callable[[A], C]:
    """두 함수를 합성한다. compose(f, g)(x) == f(g(x))"""
    return lambda x: f(g(x))

def pipe(*functions):
    """왼쪽에서 오른쪽으로 함수를 합성한다. pipe(f, g, h)(x) == h(g(f(x)))"""
    return reduce(lambda f, g: lambda x: g(f(x)), functions)
```

파이프라인은 이렇게 만든다:

```python
def build_rag_pipeline(
    retriever: Retriever,
    reranker: Reranker,
    generator: Generator
) -> Callable[[str], str]:
    
    def pipeline(query: str) -> str:
        docs = retriever(query)
        reranked = reranker(query, docs)
        return generator(query, reranked)
    
    return pipeline
```

이제 파이프라인의 각 구성요소를 바꿔 끼울 수 있다:

```python
# 벡터 검색 기반 파이프라인
vector_pipeline = build_rag_pipeline(
    retriever=vector_retriever,
    reranker=cohere_reranker,
    generator=openai_generator
)

# BM25 + cross-encoder 파이프라인
bm25_pipeline = build_rag_pipeline(
    retriever=bm25_retriever,
    reranker=cross_encoder_reranker,
    generator=openai_generator
)

# reranker 없는 간단한 파이프라인
simple_pipeline = build_rag_pipeline(
    retriever=vector_retriever,
    reranker=lambda query, docs: docs,  # 그냥 통과
    generator=openai_generator
)
```

### 2.3 불변 Document 체인

파이프라인 각 단계를 거치면서 Document가 어떻게 변했는지 추적하고 싶을 때가 있다. 검색 점수는 얼마였는지, reranking 후 점수는 얼마로 바뀌었는지 같은 것들이다.

`frozen=True`인 Document를 쓰고 있으므로, 각 단계에서 새 Document를 만들 때 이전 정보를 metadata에 넣어두면 된다.

```python
from dataclasses import replace

def cohere_reranker(query: str, docs: list[Document]) -> list[Document]:
    response = cohere_client.rerank(
        query=query,
        documents=[d.text for d in docs],
        top_n=5
    )
    
    reranked = []
    for result in response.results:
        original = docs[result.index]
        # 기존 Document를 변경하지 않고 새로 만든다
        new_doc = replace(
            original,
            score=result.relevance_score,
            metadata={
                **original.metadata,
                "original_score": original.score,
                "rerank_score": result.relevance_score
            }
        )
        reranked.append(new_doc)
    
    return reranked
```

`dataclasses.replace`는 frozen dataclass에서 일부 필드만 바꾼 새 인스턴스를 만든다. 원본은 그대로 남아 있으므로 이전 단계의 결과를 언제든 확인할 수 있다.

---

## 3. Either/Result 모나드로 실패 처리

RAG 파이프라인은 실패 지점이 많다. 벡터 DB 타임아웃, 검색 결과 0건, reranker API 오류, LLM rate limit 등. try-except를 단계마다 붙이면 코드가 지저분해진다.

함수형 프로그래밍의 Either(또는 Result) 패턴을 쓰면 실패를 값으로 다룰 수 있다. 예외를 던지는 대신, 성공 또는 실패를 담은 객체를 반환한다.

### 3.1 Result 타입 구현

```python
from dataclasses import dataclass
from typing import TypeVar, Generic, Callable, Union

T = TypeVar('T')
E = TypeVar('E')
U = TypeVar('U')

@dataclass(frozen=True)
class Success(Generic[T]):
    value: T

@dataclass(frozen=True)
class Failure(Generic[E]):
    error: E
    stage: str  # 어느 단계에서 실패했는지

Result = Union[Success[T], Failure[E]]

def map_result(result: Result, f: Callable[[T], U]) -> Result:
    """성공이면 함수를 적용하고, 실패면 그대로 전달한다."""
    if isinstance(result, Failure):
        return result
    return Success(f(result.value))

def bind_result(result: Result, f: Callable[[T], Result]) -> Result:
    """성공이면 함수를 적용하고(함수도 Result를 반환), 실패면 그대로 전달한다."""
    if isinstance(result, Failure):
        return result
    return f(result.value)
```

### 3.2 Result 기반 파이프라인

```python
def safe_retrieve(retriever: Retriever) -> Callable[[str], Result]:
    def _retrieve(query: str) -> Result:
        try:
            docs = retriever(query)
            if not docs:
                return Failure(error="검색 결과 없음", stage="retrieval")
            return Success(docs)
        except Exception as e:
            return Failure(error=str(e), stage="retrieval")
    return _retrieve

def safe_rerank(reranker: Reranker) -> Callable[[str, list[Document]], Result]:
    def _rerank(query: str, docs: list[Document]) -> Result:
        try:
            reranked = reranker(query, docs)
            return Success(reranked)
        except Exception as e:
            # reranker 실패 시 원본 문서를 그대로 사용하는 fallback
            return Success(docs)
    return _rerank

def build_safe_pipeline(
    retriever: Retriever,
    reranker: Reranker,
    generator: Generator
) -> Callable[[str], Result]:
    
    _retrieve = safe_retrieve(retriever)
    _rerank = safe_rerank(reranker)
    
    def pipeline(query: str) -> Result:
        result = _retrieve(query)
        if isinstance(result, Failure):
            return result
        
        docs = result.value
        result = _rerank(query, docs)
        if isinstance(result, Failure):
            return result
        
        reranked = result.value
        try:
            answer = generator(query, reranked)
            return Success(answer)
        except Exception as e:
            return Failure(error=str(e), stage="generation")
    
    return pipeline
```

이 패턴의 장점은 실패가 파이프라인을 조용히 흘러간다는 것이다. retrieval에서 실패하면 reranker와 generator는 실행되지 않고, Failure가 그대로 최종 결과로 나온다. 어느 단계에서 무슨 이유로 실패했는지가 Failure 객체에 담겨 있다.

reranker처럼 실패해도 파이프라인이 계속 돌아야 하는 단계는 fallback 로직을 함수 내부에 넣으면 된다. 위 코드에서 reranker가 죽으면 원본 문서를 그대로 넘긴다.

---

## 4. LangChain LCEL의 Runnable 합성 구조

LangChain의 LCEL(LangChain Expression Language)은 사실 함수형 RAG 사상을 프레임워크 레벨에서 구현한 것이다. `Runnable` 인터페이스가 핵심이고, `|` 연산자로 파이프라인을 합성한다.

### 4.1 Runnable이 하는 일

LCEL의 모든 컴포넌트는 `Runnable` 인터페이스를 구현한다. `invoke(input) -> output` 메서드가 있고, 입력 타입과 출력 타입이 정해져 있다.

```python
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import Chroma

# 각 컴포넌트가 Runnable이다
embeddings = OpenAIEmbeddings()
vectorstore = Chroma(embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
llm = ChatOpenAI(model="gpt-4o")
prompt = ChatPromptTemplate.from_template(
    "다음 문서를 참고해서 답변하세요:\n\n{context}\n\n질문: {question}"
)
```

### 4.2 파이프 연산자로 합성

`|` 연산자는 내부적으로 `RunnableSequence`를 만든다. 앞 Runnable의 출력이 뒤 Runnable의 입력으로 들어간다.

```python
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# LCEL 파이프라인
chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# 실행
answer = chain.invoke("RAG에서 chunking은 어떻게 하나요?")
```

이 코드에서 `retriever | format_docs`는 retriever의 출력(Document 리스트)을 format_docs 함수에 넣겠다는 뜻이다. dict로 묶은 부분은 `RunnableParallel`이 되어서 context와 question을 병렬로 처리한다.

### 4.3 LCEL이 함수형인 이유

LCEL이 함수형 RAG 패턴과 맞닿는 지점:

| 함수형 개념 | LCEL 구현 |
|------------|----------|
| 함수 합성 | `chain_a \| chain_b` (RunnableSequence) |
| 병렬 처리 | `{"a": chain_a, "b": chain_b}` (RunnableParallel) |
| 고차 함수 | `RunnableLambda(fn)`으로 일반 함수를 Runnable로 변환 |
| 불변성 | 각 Runnable은 상태를 갖지 않고 입출력만 정의 |
| 에러 처리 | `chain.with_fallbacks([fallback_chain])` |

실제로 fallback을 붙이면 이런 모양이 된다:

```python
from langchain_community.retrievers import BM25Retriever

# 벡터 검색 실패 시 BM25로 대체
retriever_with_fallback = retriever.with_fallbacks([bm25_retriever])

chain = (
    {"context": retriever_with_fallback | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
```

### 4.4 커스텀 Runnable 만들기

기존 Runnable로 안 되는 로직은 `RunnableLambda`로 감싸면 된다.

```python
from langchain_core.runnables import RunnableLambda

def rerank_docs(input_dict: dict) -> dict:
    """Cohere reranker를 Runnable로 감싼다."""
    query = input_dict["question"]
    docs = input_dict["docs"]
    
    response = cohere_client.rerank(
        query=query,
        documents=[d.page_content for d in docs],
        top_n=3
    )
    reranked = [docs[r.index] for r in response.results]
    return {**input_dict, "docs": reranked}

# reranker를 파이프라인에 끼워넣기
chain = (
    {"docs": retriever, "question": RunnablePassthrough()}
    | RunnableLambda(rerank_docs)
    | (lambda x: {"context": format_docs(x["docs"]), "question": x["question"]})
    | prompt
    | llm
    | StrOutputParser()
)
```

---

## 5. 함수형 RAG vs 절차형 RAG

### 5.1 구조 비교

**절차형** — 한 함수 안에 모든 로직이 순서대로 들어간다.

```python
def rag_answer(query):
    docs = search(query)          # 1. 검색
    docs = filter(docs)           # 2. 필터링
    docs = rerank(query, docs)    # 3. 재정렬
    context = format(docs)        # 4. 포맷팅
    answer = generate(query, ctx) # 5. 생성
    return answer
```

**함수형** — 각 단계가 독립 함수이고, 합성으로 파이프라인을 만든다.

```python
pipeline = pipe(
    lambda q: (q, search(q)),
    lambda qd: (qd[0], filter_docs(qd[1])),
    lambda qd: (qd[0], rerank(qd[0], qd[1])),
    lambda qd: (qd[0], format_docs(qd[1])),
    lambda qd: generate(qd[0], qd[1])
)
```

튜플을 넘기는 게 보기 좋지는 않다. 실제로는 dict나 dataclass를 쓰는 게 낫다:

```python
@dataclass(frozen=True)
class RAGState:
    query: str
    documents: list[Document] = field(default_factory=list)
    context: str = ""
    answer: str = ""

pipeline = pipe(
    lambda s: replace(s, documents=search(s.query)),
    lambda s: replace(s, documents=filter_docs(s.documents)),
    lambda s: replace(s, documents=rerank(s.query, s.documents)),
    lambda s: replace(s, context=format_docs(s.documents)),
    lambda s: replace(s, answer=generate(s.query, s.context))
)

result = pipeline(RAGState(query="함수형 RAG가 뭔가요?"))
# result.documents → 검색된 문서들
# result.context → 포맷팅된 컨텍스트
# result.answer → 최종 답변
```

`RAGState`가 frozen이므로 각 단계에서 `replace`로 새 상태를 만든다. 이전 단계의 상태도 그대로 남아 있어서 디버깅할 때 유용하다.

### 5.2 어떤 상황에 어떤 방식이 맞나

**절차형이 나은 경우:**

- 파이프라인이 단순하고 바뀔 일이 없다
- 팀원 대부분이 함수형 패턴에 익숙하지 않다
- 프로토타이핑 단계라 빨리 돌아가는 게 중요하다

**함수형이 나은 경우:**

- 검색 방식이나 reranker를 자주 바꿔가며 실험한다
- 파이프라인 단계별로 단위 테스트가 필요하다
- 여러 파이프라인을 조합해서 써야 한다 (예: 도메인별로 다른 retriever)
- 실패 처리를 체계적으로 해야 한다

현실적으로는 LCEL 같은 프레임워크를 쓰면 함수형 패턴이 강제되므로 별도로 고민할 필요가 줄어든다. 프레임워크 없이 직접 파이프라인을 짠다면 함수형 패턴을 의식적으로 적용하는 게 좋다.

---

## 6. 실제 Python 구현: 함수형 RAG 파이프라인

앞에서 설명한 개념을 합쳐서 실제로 동작하는 파이프라인을 만들어 보자.

```python
from dataclasses import dataclass, field, replace
from typing import Callable, Union
from functools import reduce

# --- 1. 타입 정의 ---

@dataclass(frozen=True)
class Document:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)
    score: float = 0.0

@dataclass(frozen=True)
class Success:
    value: object

@dataclass(frozen=True)
class Failure:
    error: str
    stage: str

Result = Union[Success, Failure]

# --- 2. 파이프라인 유틸리티 ---

def pipe(*functions):
    return reduce(lambda f, g: lambda x: g(f(x)), functions)

def safe(stage_name: str, fn, fallback=None):
    """함수를 Result 기반으로 감싼다."""
    def wrapper(result):
        if isinstance(result, Failure):
            return result
        try:
            value = fn(result.value if isinstance(result, Success) else result)
            return Success(value)
        except Exception as e:
            if fallback:
                return Success(fallback(result.value if isinstance(result, Success) else result))
            return Failure(error=str(e), stage=stage_name)
    return wrapper

# --- 3. 각 단계 구현 ---

def create_vector_retriever(vectorstore, k: int = 10) -> Callable:
    def retrieve(query: str) -> list[Document]:
        results = vectorstore.similarity_search_with_score(query, k=k)
        return [
            Document(
                id=doc.metadata.get("id", str(i)),
                text=doc.page_content,
                metadata=doc.metadata,
                score=score
            )
            for i, (doc, score) in enumerate(results)
        ]
    return retrieve

def create_reranker(cohere_client, top_n: int = 3) -> Callable:
    def rerank(query_and_docs: tuple) -> tuple:
        query, docs = query_and_docs
        response = cohere_client.rerank(
            query=query,
            documents=[d.text for d in docs],
            top_n=top_n
        )
        reranked = [
            replace(
                docs[r.index],
                score=r.relevance_score,
                metadata={**docs[r.index].metadata, "rerank_score": r.relevance_score}
            )
            for r in response.results
        ]
        return (query, reranked)
    return rerank

def create_generator(llm_client, model: str = "gpt-4o") -> Callable:
    def generate(query_and_docs: tuple) -> str:
        query, docs = query_and_docs
        context = "\n\n---\n\n".join(d.text for d in docs)
        response = llm_client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": f"다음 문서를 참고해서 답변하세요:\n\n{context}\n\n질문: {query}"
            }]
        )
        return response.choices[0].message.content
    return generate

# --- 4. 파이프라인 조립 ---

def build_functional_rag(vectorstore, cohere_client, openai_client):
    retrieve = create_vector_retriever(vectorstore, k=10)
    rerank = create_reranker(cohere_client, top_n=3)
    generate = create_generator(openai_client)
    
    # reranker 실패 시 원본 문서를 그대로 쓰는 fallback
    def rerank_fallback(query_and_docs):
        return query_and_docs
    
    pipeline = pipe(
        safe("retrieval", lambda q: (q, retrieve(q))),
        safe("reranking", rerank, fallback=rerank_fallback),
        safe("generation", generate)
    )
    
    return pipeline

# --- 5. 사용 ---

# pipeline = build_functional_rag(vectorstore, cohere_client, openai_client)
# result = pipeline("RAG 파이프라인에서 chunking 크기는 어떻게 정하나요?")
# 
# if isinstance(result, Success):
#     print(result.value)
# elif isinstance(result, Failure):
#     print(f"[{result.stage}] 실패: {result.error}")
```

---

## 7. 실무에서 주의할 점

### 디버깅이 오히려 어려워지는 경우

함수 합성을 너무 깊게 하면 스택 트레이스가 lambda 지옥이 된다. `pipe(f, g, h)`에서 `g`가 터지면 트레이스에 `<lambda>`만 잔뜩 나온다.

대응 방법은 간단하다. lambda 대신 이름 있는 함수를 쓴다.

```python
# 디버깅 어려움
pipeline = pipe(
    lambda x: (x, retrieve(x)),
    lambda x: (x[0], rerank(x[0], x[1])),
    lambda x: generate(x[0], x[1])
)

# 디버깅 가능
def retrieve_step(query):
    return (query, retrieve(query))

def rerank_step(query_and_docs):
    query, docs = query_and_docs
    return (query, rerank(query, docs))

def generate_step(query_and_docs):
    query, docs = query_and_docs
    return generate(query, docs)

pipeline = pipe(retrieve_step, rerank_step, generate_step)
```

### 비동기 파이프라인

RAG는 I/O가 많으므로 async가 거의 필수다. 함수형 패턴은 async와 잘 맞는다.

```python
import asyncio

async def async_pipe(*functions):
    async def run(x):
        result = x
        for fn in functions:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(result)
            else:
                result = fn(result)
        return result
    return run

# 병렬 검색 예시
async def multi_retrieve(query: str) -> list[Document]:
    vector_task = asyncio.create_task(vector_retrieve(query))
    bm25_task = asyncio.create_task(bm25_retrieve(query))
    
    vector_docs, bm25_docs = await asyncio.gather(vector_task, bm25_task)
    
    # 두 검색 결과를 합치고 중복 제거
    seen = set()
    merged = []
    for doc in vector_docs + bm25_docs:
        if doc.id not in seen:
            seen.add(doc.id)
            merged.append(doc)
    return merged
```

### frozen dataclass의 성능

Document가 많으면 `replace`로 매번 새 객체를 만드는 게 부담될 수 있다. 수백 개 수준이면 문제없지만, 수만 개를 다루는 파이프라인이라면 프로파일링 후 판단해야 한다. 대부분의 RAG 파이프라인은 top-k로 걸러진 수십 개 문서만 다루므로 실제로 병목이 되는 경우는 드물다.

### Result 패턴이 과한 경우

파이프라인이 3단계 이하이고 실패 시나리오가 단순하면 그냥 try-except가 낫다. Result 패턴은 실패 경로가 여러 개이고, 각 실패에 대해 다른 처리가 필요할 때 쓸 만하다. 패턴을 쓰는 것 자체가 목적이 되면 안 된다.
