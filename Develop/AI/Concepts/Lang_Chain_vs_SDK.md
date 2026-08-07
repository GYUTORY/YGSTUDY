---
title: LangChain / LlamaIndex vs 순수 SDK
tags: [langchain, llamaindex, sdk, llm, rag, abstraction, framework]
updated: 2026-08-04
volatility: high
---

# LangChain / LlamaIndex vs 순수 SDK

LangChain과 LlamaIndex는 LLM 파이프라인 구성을 빠르게 시작할 수 있도록 추상화를 제공하는 프레임워크다. 문제는 그 추상화가 특정 시점에서 오히려 짐이 된다는 것이다.

## LangChain이 매력적인 이유

처음 LLM 기능을 붙일 때 LangChain이 빠르게 보인다. RAG 파이프라인 하나를 만들려면 문서 로더, 텍스트 분할기, 임베딩, 벡터 스토어, 리트리버, 프롬프트 템플릿, 모델 호출, 출력 파서를 각각 구현해야 한다. LangChain은 이걸 체인 하나로 묶어 준다.

LlamaIndex는 인덱싱과 검색 쪽에 집중한다. 문서 트리 구조나 요약 인덱스 같은 개념이 내장되어 있어서, 계층적 문서 검색이 필요한 경우 처음 세팅하는 데 드는 시간이 줄어든다.

## 실제로 쓰면 무슨 문제가 생기는가

### 버전 의존성

LangChain은 0.x 시절부터 API 변경이 잦았다. 0.1에서 0.2로 넘어갈 때 `LLMChain`이 deprecated 되고 `RunnableSequence`로 교체됐다. 0.3에서는 패키지가 `langchain-core`, `langchain-community`, `langchain-anthropic` 등으로 쪼개졌다.

6개월 묵은 LangChain 코드베이스를 열면 deprecation 경고가 수십 개 쌓여 있는 경우가 있다. 마이그레이션 가이드를 따라가다 보면 결국 체인 구조를 통째로 다시 쓰게 된다.

```python
# 0.1 시절 코드
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

chain = LLMChain(llm=llm, prompt=PromptTemplate(...))
result = chain.run(input="...")

# 0.3에서는 이렇게 써야 한다
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

chain = PromptTemplate(...) | llm | StrOutputParser()
result = chain.invoke({"input": "..."})
```

이 변경은 단순 이름 바꾸기가 아니다. LCEL(LangChain Expression Language)이라는 새 패러다임을 배워야 한다. 기존 코드를 LCEL로 옮기는 과정에서 체인의 동작 방식 자체가 달라질 수 있다.

### 추상화 누수

LangChain이 숨겨 놓은 동작이 예상과 다르게 작동할 때 디버깅이 어렵다. `ConversationalRetrievalChain`을 쓰면 내부에서 질문을 먼저 재작성(condense)하는 서브체인이 돌아간다. 사용자 입장에서는 프롬프트가 하나인 것처럼 보이지만 실제로는 LLM 호출이 두 번 일어난다.

비용 계산이 틀려지거나 레이턴시가 예상보다 두 배가 나오는 상황이 여기서 발생한다. 내부를 뜯어보려면 LangSmith 트레이싱을 켜야 하는데, 그것도 별도 가입과 설정이 필요하다.

### 커뮤니티 패키지 품질

`langchain-community`에는 수백 개의 통합 모듈이 있다. 그 중 상당수는 관리가 잘 안 되는 서드파티 기여분이다. Chroma 통합 버전이 Chroma 클라이언트 업데이트를 따라가지 못해서, Chroma를 업그레이드하면 LangChain 통합이 깨지는 상황이 실제로 생긴다. LangChain 핵심 패키지와 커뮤니티 패키지의 릴리스 주기가 맞지 않는 탓이다.

### LlamaIndex의 패키지 분리

LlamaIndex도 비슷한 문제를 겪었다. `llama-index` 단일 패키지에서 `llama-index-core`, `llama-index-llms-anthropic`, `llama-index-vector-stores-qdrant` 식으로 분리되면서 기존 코드가 대규모로 깨진 적이 있다. import 경로가 전부 바뀌는 수준이라 단순 find-and-replace로 해결이 안 됐다.

## 순수 SDK로 직접 구현하면

Anthropic SDK나 OpenAI SDK를 직접 쓰면 의존성이 단순해진다. LLM 호출 흐름 전체가 코드에 그대로 드러나서, 무언가 잘못됐을 때 어디서 잘못됐는지 바로 보인다.

```python
import anthropic

client = anthropic.Anthropic()

def rag_query(question: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(context_chunks)

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system="주어진 컨텍스트만 사용해서 답변한다. 컨텍스트에 없는 내용은 모른다고 말한다.",
        messages=[{
            "role": "user",
            "content": f"컨텍스트:\n{context}\n\n질문: {question}"
        }]
    )
    return response.content[0].text
```

이 코드는 LangChain `ConversationalRetrievalChain` 100줄짜리보다 이해하기 쉽다. LLM 호출이 몇 번 일어나는지, 토큰이 얼마나 쓰이는지 바로 알 수 있다. `response.usage`에서 input/output 토큰을 직접 읽을 수 있다.

단점은 직접 만들어야 하는 게 많다는 것이다. 재시도 로직, 스트리밍 처리, 멀티 프로바이더 추상화, 토큰 계산, 대화 히스토리 관리를 전부 손으로 써야 한다. LangChain이 이미 해결해 놓은 것들이다.

```python
# 재시도 로직 직접 구현 예시
import time
from anthropic import RateLimitError, APIStatusError

def call_with_retry(client, **kwargs) -> str:
    for attempt in range(3):
        try:
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except RateLimitError:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
        except APIStatusError as e:
            if e.status_code >= 500:
                time.sleep(1)
            else:
                raise
```

LangChain에서는 `with_retry()`로 한 줄에 끝난다. 직접 구현하면 이런 유틸리티 코드가 여기저기 생긴다.

## 팀 규모와 요구사항별 판단

**혼자 또는 소규모(1~3명)이고 요구사항이 단순한 경우**

LangChain으로 시작해도 된다. RAG 파이프라인 하나, 단순 챗봇 수준이면 빠르게 만들 수 있다. 다만 프로젝트가 6개월 이상 유지된다면 버전 업그레이드 비용을 계산에 넣어야 한다.

**중간 규모(5명 이상)이고 프로덕션 서비스인 경우**

LangChain의 추상화가 팀원 사이에서 공통 언어가 되려면 모두가 그 추상화를 깊이 이해해야 한다. 모르면 잘못 쓴다. 디버깅할 때 LangChain 내부를 아는 사람이 없으면 블랙박스가 된다.

이 규모에서는 핵심 파이프라인을 순수 SDK로 짜고, 유틸리티 레벨에서만 LangChain 컴포넌트를 빌려 쓰는 방식이 유지보수 비용이 낮다.

**LLM 파인튜닝이나 커스텀 모델을 쓰는 경우**

LangChain의 LLM 추상화가 커스텀 엔드포인트를 충분히 지원하지 못하는 경우가 있다. 커스텀 서버에 맞추려다 오히려 래퍼 코드가 늘어나서 더 복잡해진다. 처음부터 순수 HTTP 또는 SDK로 직접 구현하는 게 낫다.

**LlamaIndex는 언제 고려하는가**

복잡한 문서 구조를 다룰 때 LangChain보다 낫다. 계층적 요약 인덱스, 문서 트리 탐색, 멀티 인덱스 결합 같은 기능이 필요하면 직접 구현보다 LlamaIndex가 코드를 줄여 준다. 단순 flat 검색이면 pgvector + 직접 쿼리로도 충분하다.

LlamaIndex도 버전 의존성 문제는 마찬가지라는 점을 염두에 둬야 한다.

## 프레임워크 없이도 가능한 것들

LangChain 없이 순수 SDK로 구현할 수 있는 대표적인 것들:

```python
# 대화 히스토리 관리 — LangChain ConversationBufferMemory 없이
class ChatSession:
    def __init__(self, system_prompt: str):
        self.system = system_prompt
        self.messages: list[dict] = []

    def chat(self, client, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=1024,
            system=self.system,
            messages=self.messages,
        )

        assistant_msg = response.content[0].text
        self.messages.append({"role": "assistant", "content": assistant_msg})
        return assistant_msg

    def trim_to_last_n_turns(self, n: int):
        # 오래된 메시지를 잘라내서 컨텍스트 폭발 방지
        self.messages = self.messages[-(n * 2):]
```

이 정도 코드면 LangChain `ConversationChain`을 대체한다. 동작 방식이 명확하고 히스토리 잘라내기 로직도 직접 제어할 수 있다.

## 선택할 때 실제로 하는 판단

프레임워크 선택에서 가장 자주 틀리는 판단은 "나중에 복잡해지면 갈아타면 된다"는 생각이다. LangChain 위에 쌓인 코드는 LangChain의 추상화에 의존하기 때문에 걷어내는 비용이 처음부터 순수 SDK로 짰을 때보다 크다.

빠르게 프로토타이핑하고 폐기할 거라면 LangChain이 맞다. 프로덕션에서 2년 이상 운영할 거라면 핵심 파이프라인은 SDK로 직접 짜고, 필요한 부분만 라이브러리를 가져다 쓰는 쪽이 낫다.

버전 고정(`pip install langchain==0.3.x`)을 걸어도 문제는 해결되지 않는다. LangChain이 의존하는 하위 패키지들의 버전까지 모두 고정해야 하고, 보안 패치가 필요할 때 업그레이드 경로가 막힌다.
