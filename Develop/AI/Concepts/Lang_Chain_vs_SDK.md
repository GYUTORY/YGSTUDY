---
title: LangChain / LlamaIndex vs 순수 SDK
tags: [llm, rag, ai]
updated: 2026-09-07
volatility: high
---

# LangChain / LlamaIndex vs 순수 SDK

LangChain과 LlamaIndex는 LLM 파이프라인 구성을 빠르게 시작할 수 있도록 추상화를 제공하는 프레임워크다. 문제는 그 추상화가 특정 시점에서 오히려 짐이 된다는 것이다.

## LangChain이 매력적인 이유

처음 LLM 기능을 붙일 때 LangChain이 빠르게 보인다. RAG 파이프라인 하나를 만들려면 문서 로더, 텍스트 분할기, 임베딩, 벡터 스토어, 리트리버, 프롬프트 템플릿, 모델 호출, 출력 파서를 각각 구현해야 한다. LangChain은 이걸 체인 하나로 묶어 준다.

LlamaIndex는 인덱싱과 검색 쪽에 집중한다. 문서 트리 구조나 요약 인덱스 같은 개념이 내장되어 있어서, 계층적 문서 검색이 필요한 경우 처음 세팅하는 데 드는 시간이 줄어든다.

## 마이그레이션에서 실제로 깨지는 것들

### LangChain: import 경로가 버전마다 바뀐다

LangChain은 0.1에서 0.3으로 오면서 패키지 구조가 두 번 크게 바뀌었다. 0.1 코드를 0.3 환경에서 실행하면 이런 오류가 바로 나온다.

```
ModuleNotFoundError: No module named 'langchain.chains'
ImportError: cannot import name 'LLMChain' from 'langchain'
```

실제로 0.1 시절 코드가 0.3에서 어떻게 달라지는지:

```python
# 0.1 시절 — 패키지 전체가 langchain 하나였다
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatAnthropic
from langchain.memory import ConversationBufferMemory

chain = LLMChain(
    llm=ChatAnthropic(model="claude-3-opus-20240229"),
    prompt=PromptTemplate.from_template("{input}"),
    memory=ConversationBufferMemory()
)
result = chain.run(input="질문")
```

```python
# 0.3 — 패키지가 langchain-core, langchain-community, langchain-anthropic으로 쪼개졌다
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_anthropic import ChatAnthropic  # 별도 패키지
# ConversationBufferMemory는 deprecated, RunnableWithMessageHistory로 교체

chain = PromptTemplate.from_template("{input}") | ChatAnthropic(model="claude-opus-4-7") | StrOutputParser()
result = chain.invoke({"input": "질문"})
```

이 변경은 이름만 바뀐 게 아니다. LCEL(LangChain Expression Language)이라는 새 패러다임 전체를 다시 배워야 한다. 6개월 묵은 LangChain 코드베이스를 열면 deprecation 경고가 수십 개 쌓여 있고, 마이그레이션 가이드를 따라가다 보면 체인 구조를 통째로 다시 쓰게 된다.

`find . -name "*.py" | xargs grep "from langchain" | grep -v langchain_core`로 레거시 import를 찾을 수 있지만, 단순 find-and-replace로는 안 된다. `LLMChain`을 LCEL 파이프로 바꾸려면 체인이 어떻게 연결되는지 파악한 다음 재작성해야 한다.

### LlamaIndex: 패키지 분리가 더 급격했다

LlamaIndex는 0.10.x에서 패키지를 `llama-index` 단일 패키지에서 아래처럼 쪼갰다.

```
llama-index-core
llama-index-llms-anthropic
llama-index-llms-openai
llama-index-vector-stores-qdrant
llama-index-vector-stores-chroma
llama-index-embeddings-huggingface
...
```

기존 코드에서 이런 import는 전부 깨진다.

```python
# 구버전
from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores import QdrantVectorStore
from llama_index.embeddings import HuggingFaceEmbedding
```

```python
# 신버전
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
```

클래스 이름도 `GPTVectorStoreIndex` → `VectorStoreIndex`로 바뀌었다. 단순 sed 치환으로는 해결이 안 되고, 새로 설치해야 하는 패키지 목록을 파악한 다음 `requirements.txt`를 통째로 갱신해야 한다.

버전 고정(`pip install llama-index==0.9.x`)을 걸어도 문제는 해결되지 않는다. 하위 의존 패키지들의 버전까지 모두 고정해야 하고, 보안 패치가 필요할 때 업그레이드 경로가 막힌다.

### 추상화 누수

LangChain이 숨겨 놓은 동작이 예상과 다르게 작동할 때 디버깅이 어렵다. `ConversationalRetrievalChain`을 쓰면 내부에서 질문을 먼저 재작성(condense)하는 서브체인이 돌아간다. 사용자 입장에서는 프롬프트가 하나인 것처럼 보이지만 실제로는 LLM 호출이 두 번 일어난다.

비용 계산이 틀려지거나 레이턴시가 예상보다 두 배가 나오는 상황이 여기서 발생한다. 내부를 뜯어보려면 LangSmith 트레이싱을 켜야 하는데, 그것도 별도 가입과 설정이 필요하다.

## LlamaIndex vs LangChain: 문서 구조별 판단

두 프레임워크를 동시에 다루는 문서가 많은데, 실제 선택 기준은 "문서 구조가 어떻게 생겼는가"에서 갈린다.

### Flat 구조 (FAQ, 지원 티켓, 뉴스 기사)

단일 레벨 문서 컬렉션이라면 LangChain도 LlamaIndex도 오버킬이다. pgvector + 직접 쿼리로 충분하다.

```sql
-- pgvector로 코사인 유사도 검색
SELECT content, 1 - (embedding <=> $1::vector) AS similarity
FROM documents
WHERE 1 - (embedding <=> $1::vector) > 0.7
ORDER BY similarity DESC
LIMIT 5;
```

프레임워크 없이 임베딩 API + SQL 조합으로 RAG를 만들면 의존성이 `psycopg2`와 임베딩 API 클라이언트뿐이다. 버전 이슈가 생길 지점 자체가 없다.

### 계층 구조 (법률 문서, 기술 매뉴얼, 정책 문서)

"3장 2절 a항"처럼 구조가 있는 문서는 LlamaIndex가 낫다. `SummaryIndex`와 `VectorStoreIndex`를 조합해 상위 요약 → 하위 청크 순으로 탐색하는 구조를 만들 수 있다.

```python
from llama_index.core import SummaryIndex, VectorStoreIndex, Document
from llama_index.core.node_parser import HierarchicalNodeParser

# 계층 파서: 섹션 → 문단 → 문장으로 분리
parser = HierarchicalNodeParser.from_defaults(chunk_sizes=[2048, 512, 128])
nodes = parser.get_nodes_from_documents(documents)

# 상위 레벨은 요약 검색, 하위 레벨은 벡터 검색
summary_index = SummaryIndex(nodes)
vector_index = VectorStoreIndex(nodes)
```

직접 구현하면 계층 탐색 로직만 200~300줄이 된다. 이 도메인에서 LlamaIndex는 실제로 코드를 줄여 준다.

### 코드 저장소 검색

LangChain에 코드 분할기(`RecursiveCharacterTextSplitter`의 language 옵션)가 있지만, AST 기반 분할이 아니라 라인 수 기반이라 함수 경계를 무시하고 자른다. 함수 중간에서 청크가 끊기면 검색 품질이 나빠진다.

코드 검색은 Tree-sitter로 직접 AST 파싱해서 함수·클래스 단위로 청크를 만드는 게 더 낫다. 어떤 프레임워크든 이 부분은 직접 짜야 한다.

### 이기종 소스 (PDF + DB + API)

프레임워크의 로더 모듈이 가장 자주 실망을 주는 지점이다. `langchain-community`의 PDF 로더는 테이블 파싱이 약하고, DB 로더는 스키마 변경에 취약하다. 이 경우 각 소스별로 직접 파서를 만들고 통일된 `Document` 객체로 변환하는 커스텀 레이어를 쓰는 게 결국 낫다. 프레임워크 로더를 쓰다가 문제가 생기면 내부 코드를 파악해야 하는데, 그 비용이 처음부터 직접 짜는 것보다 크다.

## 순수 SDK로 직접 구현

Anthropic SDK나 OpenAI SDK를 직접 쓰면 의존성이 단순해진다. LLM 호출 흐름 전체가 코드에 그대로 드러나서, 무언가 잘못됐을 때 어디서 잘못됐는지 바로 보인다.

### 기본 RAG 호출

```python
import anthropic

client = anthropic.Anthropic()

def rag_query(question: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(context_chunks)
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system="주어진 컨텍스트만 사용해서 답변한다. 컨텍스트에 없는 내용은 모른다고 말한다.",
        messages=[{"role": "user", "content": f"컨텍스트:\n{context}\n\n질문: {question}"}]
    )
    return response.content[0].text
```

`response.usage`에서 input/output 토큰을 직접 읽을 수 있다. LLM 호출이 몇 번 일어나는지, 토큰이 얼마나 쓰이는지 숨겨진 것이 없다.

### 재시도 로직

LangChain의 `with_retry()`는 한 줄이지만, 직접 구현해도 40줄 안에 끝난다. 재시도 조건을 정확하게 제어할 수 있다.

```python
import time
import logging
from anthropic import RateLimitError, APIConnectionError, APIStatusError

def call_with_retry(client, max_attempts: int = 3, **kwargs) -> str:
    last_error = None
    for attempt in range(max_attempts):
        try:
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except RateLimitError as e:
            last_error = e
            if attempt == max_attempts - 1:
                break
            wait = 2 ** attempt  # 1s, 2s, 4s
            logging.warning(f"Rate limited (attempt {attempt + 1}/{max_attempts}), waiting {wait}s")
            time.sleep(wait)
        except APIConnectionError as e:
            last_error = e
            if attempt == max_attempts - 1:
                break
            time.sleep(1)
        except APIStatusError as e:
            if e.status_code >= 500 and attempt < max_attempts - 1:
                last_error = e
                time.sleep(1)
            else:
                raise
    raise last_error
```

`RateLimitError`와 `APIStatusError(5xx)`는 재시도하고, 4xx는 바로 올린다. LangChain의 기본 재시도는 모든 API 오류를 재시도하는데, 400 Bad Request를 재시도하면 요금만 날린다.

### 스트리밍

LangChain의 스트리밍은 콜백 시스템을 써야 해서 처음엔 어색하다. SDK 직접 사용은 context manager로 깔끔하게 처리한다.

```python
import anthropic

client = anthropic.Anthropic()

def stream_rag(question: str, context: str) -> str:
    full_text = ""
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=1024,
        system="주어진 컨텍스트만 사용해서 답변한다.",
        messages=[{"role": "user", "content": f"컨텍스트:\n{context}\n\n질문: {question}"}]
    ) as stream:
        for chunk in stream.text_stream:
            print(chunk, end="", flush=True)
            full_text += chunk
    print()
    return full_text
```

async 환경이라면 `AsyncAnthropic`으로 바꾸면 된다. LangChain 스트리밍은 콜백 핸들러를 구현해야 하고, LCEL 체인에서 스트리밍이 어떻게 전파되는지 이해해야 한다.

### 멀티 프로바이더

LangChain의 LLM 추상화 대신 Protocol로 직접 만들면 의존성 없이 같은 효과를 낼 수 있다.

```python
from typing import Protocol
import anthropic
import openai

class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str: ...

class AnthropicProvider:
    def __init__(self, model: str = "claude-opus-4-7"):
        self._client = anthropic.Anthropic()
        self._model = model

    def complete(self, system: str, user: str) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        return resp.content[0].text

class OpenAIProvider:
    def __init__(self, model: str = "gpt-4o"):
        self._client = openai.OpenAI()
        self._model = model

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )
        return resp.choices[0].message.content

class FallbackProvider:
    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self._primary = primary
        self._fallback = fallback

    def complete(self, system: str, user: str) -> str:
        try:
            return self._primary.complete(system, user)
        except Exception:
            return self._fallback.complete(system, user)
```

Anthropic API가 다운됐을 때 OpenAI로 자동 전환하는 식으로 쓸 수 있다. LangChain의 `FallbackLLM`과 기능이 같지만 코드가 어디서 어디로 떨어지는지 전부 눈에 보인다.

### 대화 히스토리 관리

```python
class ChatSession:
    def __init__(self, system_prompt: str, max_turns: int = 20):
        self.system = system_prompt
        self.max_turns = max_turns
        self.messages: list[dict] = []

    def chat(self, client, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})
        if len(self.messages) > self.max_turns * 2:
            # 오래된 메시지를 잘라내서 컨텍스트 폭발 방지
            self.messages = self.messages[-(self.max_turns * 2):]

        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=1024,
            system=self.system,
            messages=self.messages,
        )
        assistant_msg = response.content[0].text
        self.messages.append({"role": "assistant", "content": assistant_msg})
        return assistant_msg
```

LangChain `ConversationBufferWindowMemory`를 대체한다. 히스토리 잘라내기 로직도 직접 제어할 수 있다.

## 운영 비용 현실

팀 규모별 판단 기준에서 "유지보수 비용"을 막연하게 언급하는 경우가 많은데, 구체적으로 따져보면 다르다.

**솔로 또는 소규모(1~3명), 프로토타입**

LangChain으로 시작해도 된다. 초기 개발 속도가 빠르고, 업그레이드 비용을 나중에 혼자 짊어져도 된다. 다만 6개월 이상 운영한다면 분기당 4~8시간을 deprecation 대응에 쓸 것으로 예상해야 한다. 0.2 → 0.3 마이그레이션에서 실제로 이틀 반 걸린 사례가 있다.

**중간 규모(5명 이상), 프로덕션 서비스**

LangSmith Pro는 월 $39/사용자부터 시작한다. 5명 팀이면 월 $195. 연 $2,340이다. LangSmith 없이 LangChain 체인 내부를 디버깅하기 어렵기 때문에 사실상 필수다.

업그레이드 비용은 다르게 계산된다. 팀원 모두가 LangChain 추상화를 이해해야 하고, 새 버전 마이그레이션을 모두가 리뷰해야 한다. 5명이 각자 반나절씩 쓰면 마이그레이션당 2.5인일이다. 0.1 → 0.3 사이에 이런 업그레이드가 세 번 있었다.

순수 SDK로 처음에 짜는 비용은 2~3일 더 걸린다. 재시도, 스트리밍, 히스토리 관리를 직접 만드는 시간이다. 그 이후 프레임워크 업그레이드 비용은 없다. SDK 자체의 breaking change는 LangChain보다 훨씬 드물다.

**커스텀 모델이나 파인튜닝 엔드포인트를 쓰는 경우**

LangChain의 LLM 추상화가 커스텀 엔드포인트를 충분히 지원하지 못하는 경우가 있다. 커스텀 서버에 맞추려다 래퍼 코드가 늘어나서 더 복잡해진다. 처음부터 직접 HTTP 클라이언트로 구현하는 게 낫다.

## 선택할 때 실제로 하는 판단

프레임워크 선택에서 자주 틀리는 판단은 "나중에 복잡해지면 갈아타면 된다"는 생각이다. LangChain 위에 쌓인 코드는 LangChain의 추상화에 의존하기 때문에 걷어내는 비용이 처음부터 순수 SDK로 짰을 때보다 크다.

정리하면 이렇게 된다.

- **빠른 프로토타입, 폐기 예정**: LangChain. 속도가 우선이다.
- **Flat 문서 RAG**: pgvector + 직접 쿼리. 프레임워크 불필요.
- **계층 문서 검색 (법률, 매뉴얼)**: LlamaIndex가 코드를 줄여 준다.
- **프로덕션 2년 이상, 팀 5명+**: 핵심 파이프라인은 SDK 직접 구현, 필요한 부분만 라이브러리를 가져다 쓴다.
- **멀티 프로바이더, 커스텀 엔드포인트**: SDK 직접 구현.

"LangChain을 쓰지 말아야 한다"는 게 아니다. 버전 의존성과 마이그레이션 비용이 실제로 얼마나 되는지 계산에 넣고 판단해야 한다는 것이다.
