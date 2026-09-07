---
title: LCEL — LangChain Expression Language
tags: [ai, llm, python, backend]
updated: 2026-09-07
---

# LCEL — LangChain Expression Language

LCEL은 LangChain 0.1 시절의 `LLMChain`, `SequentialChain` 같은 레거시 체인을 대체하는 조합 방식이다. 파이프(`|`)로 컴포넌트를 연결하면 내부에서 `RunnableSequence`가 만들어지는 구조다. 추상화 수준이 얇아서 내부 동작을 이해하면 디버깅이 쉬워지지만, 타입 제약을 잘못 이해하면 파이프라인이 조용히 깨진다.

## Runnable 인터페이스

LCEL의 모든 컴포넌트는 `Runnable` 프로토콜을 구현한다. 4개의 호출 방식이 있고 각각 쓰는 상황이 다르다.

```python
from langchain_core.runnables import Runnable
```

**invoke** — 단건 동기 호출. 입력을 넣고 완성된 출력을 기다린다. 배치 처리나 스트리밍이 필요 없을 때 쓴다.

```python
result = chain.invoke({"question": "Redis TTL이 뭔가요?"})
```

**stream** — 제너레이터를 반환한다. 첫 토큰부터 순서대로 나온다. FastAPI의 `StreamingResponse`에 바로 연결할 수 있다.

```python
for chunk in chain.stream({"question": "설명해주세요"}):
    print(chunk, end="", flush=True)
```

**batch** — 여러 입력을 동시에 처리한다. 내부적으로 `asyncio.gather`나 `ThreadPoolExecutor`를 쓴다. `max_concurrency`로 동시 실행 수를 제한한다.

```python
results = chain.batch(
    [{"question": "Q1"}, {"question": "Q2"}, {"question": "Q3"}],
    config={"max_concurrency": 5},
)
```

**astream** — 비동기 스트리밍. `async for`로 받는다. FastAPI 비동기 엔드포인트에서 주로 쓴다.

```python
async def generate():
    async for chunk in chain.astream({"question": "설명해주세요"}):
        yield chunk
```

`ainvoke`, `abatch`도 있다. 비동기 컨텍스트라면 이쪽을 쓴다.

## RunnableSequence — 파이프로 연결되는 실체

`|` 연산자를 쓰면 `RunnableSequence`가 생긴다.

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template("다음을 설명해라: {topic}")
model = ChatOpenAI(model="gpt-4o-mini")
parser = StrOutputParser()

chain = prompt | model | parser
```

실행 흐름은 단순하다. `invoke({"topic": "Redis"})`를 호출하면 `prompt.invoke({"topic": "Redis"})` → `model.invoke(결과)` → `parser.invoke(결과)` 순서로 왼쪽에서 오른쪽으로 순차 실행된다.

타입 제약이 있다. 각 컴포넌트의 출력 타입이 다음 컴포넌트의 입력 타입과 맞아야 한다. `ChatPromptTemplate`의 출력은 `ChatPromptValue`이고 `ChatOpenAI`의 입력은 `BaseMessage` 목록을 담은 시퀀스다. LangChain 내부에서 자동 변환해주지만, 커스텀 컴포넌트를 중간에 끼우면 이 변환이 일어나지 않는다.

가장 흔한 실수는 딕셔너리를 반환하는 함수를 체인 중간에 넣을 때다.

```python
def extract_content(ai_message):
    # AIMessage 객체에서 content 문자열을 꺼내려는 의도
    return {"content": ai_message.content}

# 이렇게 하면 다음 단계에서 dict가 들어간다
broken_chain = prompt | model | extract_content | some_other_step
```

`some_other_step`이 문자열을 기대하고 있으면, `dict`가 들어와도 오류 없이 실행되다가 나중에 예상치 못한 동작을 한다.

## RunnableParallel — 병렬 실행과 딕셔너리 타입

여러 체인을 동시에 실행하고 결과를 딕셔너리로 합친다.

```python
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

retrieval_chain = RunnableParallel(
    context=retriever,
    question=RunnablePassthrough(),
)
```

입력이 `{"question": "Redis TTL이 뭔가요?"}`라면 출력은 `{"context": [...검색결과...], "question": "Redis TTL이 뭔가요?"}` 형태가 된다.

딕셔너리 문법으로도 쓸 수 있다. 동작은 같다.

```python
retrieval_chain = {
    "context": retriever,
    "question": RunnablePassthrough(),
}
```

LangChain이 딕셔너리를 `RunnableParallel`로 자동 변환한다.

병렬 실행이라는 이름과 달리, 각 브랜치가 완전히 독립적이어야 한다. 한 브랜치의 출력을 다른 브랜치의 입력으로 쓸 수 없다. 그게 필요하면 `RunnableSequence`를 먼저 구성하고 그 안에 `RunnableParallel`을 넣어야 한다.

실제로 문제가 생기는 패턴이 있다. `RunnableParallel` 안에서 상태를 공유하려 할 때다.

```python
# 잘못된 예 — context를 retriever가 가져오고 question을 동시에 처리하는데
# question_with_context는 context가 이미 있어야 한다
broken = RunnableParallel(
    context=retriever,
    question=RunnablePassthrough(),
    question_with_context=lambda x: f"{x['question']} (context: {x['context']})",  # context가 없다
)
```

이 경우 `question_with_context`가 실행될 때 `context`가 아직 없어서 `KeyError`가 난다.

## RunnableBranch — 조건 분기

입력에 따라 다른 체인을 실행한다.

```python
from langchain_core.runnables import RunnableBranch

branch = RunnableBranch(
    (lambda x: x["language"] == "ko", korean_chain),
    (lambda x: x["language"] == "en", english_chain),
    default_chain,  # 어느 조건도 맞지 않을 때
)
```

각 튜플의 첫 번째 원소가 조건 함수이고 두 번째가 실행할 체인이다. 마지막 인자는 기본 체인이다. 기본 체인을 빠뜨리면 어느 조건도 맞지 않을 때 `ValueError`가 난다.

조건 함수가 `bool`을 반환해야 하는데, Truthy 값을 반환하면 첫 번째로 Truthy인 브랜치가 실행된다. 조건이 복잡해질수록 `RunnableLambda`를 써서 분기 로직을 명시적으로 작성하는 편이 디버깅하기 쉽다.

```python
from langchain_core.runnables import RunnableLambda

def route(input_dict):
    if input_dict.get("language") == "ko":
        return korean_chain.invoke(input_dict)
    elif input_dict.get("language") == "en":
        return english_chain.invoke(input_dict)
    return default_chain.invoke(input_dict)

branch = RunnableLambda(route)
```

`RunnableBranch`보다 코드가 길지만, 조건이 세 개 이상 생기거나 조건 자체가 복잡해지면 이 방식이 낫다.

## RunnablePassthrough — 입력을 그대로 전달

입력을 변환 없이 다음 단계로 넘긴다. 주로 `RunnableParallel`과 함께 원래 질문을 체인 끝까지 유지할 때 쓴다.

```python
from langchain_core.runnables import RunnablePassthrough

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)
```

`assign()`을 쓰면 기존 딕셔너리에 새 키를 추가할 수 있다.

```python
chain = (
    RunnablePassthrough.assign(context=retriever)
    | prompt
    | model
)
```

입력이 `{"question": "..."}` 이면 `assign(context=retriever)` 이후에 `{"question": "...", "context": [...]}` 가 된다. 원래 키를 유지하면서 새 데이터를 붙일 때 유용하다.

주의할 점은 `RunnablePassthrough()`는 입력 전체를 넘기지만, `RunnablePassthrough.assign()`은 딕셔너리 입력을 가정한다. 입력이 딕셔너리가 아니면 `assign()`이 `AttributeError`를 낸다.

## RunnableLambda — 커스텀 Runnable 구현

Python 함수를 Runnable로 감싼다. 체인 중간에 커스텀 로직을 넣을 때 쓴다.

```python
from langchain_core.runnables import RunnableLambda

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

format_chain = RunnableLambda(format_docs)
```

비동기 함수도 감쌀 수 있다.

```python
async def async_format(docs):
    return "\n\n".join(doc.page_content for doc in docs)

async_format_chain = RunnableLambda(async_format)
```

`astream`을 지원하게 하려면 제너레이터를 반환하는 함수를 넘기면 된다.

```python
def streaming_format(docs):
    for doc in docs:
        yield doc.page_content + "\n\n"

stream_chain = RunnableLambda(streaming_format)
```

`RunnableLambda`로 만든 체인은 `stream()`을 호출해도 내부 함수가 제너레이터가 아니면 완성된 결과를 한 번에 내보낸다. 스트리밍이 필요한 구간에 `RunnableLambda`를 쓸 때는 이 점을 확인해야 한다.

## bind(), with_config(), with_fallbacks()

**bind()** — 특정 파라미터를 고정한다. 런타임마다 같은 설정을 반복하지 않을 때 쓴다.

```python
model_with_stop = model.bind(stop=["Human:"])

# temperature를 고정한 버전
creative_model = model.bind(temperature=0.9)
```

`bind()`는 새 Runnable을 반환한다. 원본 `model`은 바뀌지 않는다.

**with_config()** — 런타임 설정을 주입한다. 태깅, 콜백, 재귀 제한 등을 건다.

```python
chain.with_config(
    run_name="my_rag_chain",
    tags=["production", "v2"],
    callbacks=[my_callback_handler],
)
```

`invoke()` 호출 시 `config` 인자로도 줄 수 있지만, `with_config()`로 기본값을 고정하면 매번 넘기지 않아도 된다.

**with_fallbacks()** — 실패 시 대체 체인을 실행한다.

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

primary = ChatOpenAI(model="gpt-4o")
fallback = ChatAnthropic(model="claude-3-5-sonnet-20241022")

chain = primary.with_fallbacks([fallback])
```

`primary`가 `RateLimitError`, `Timeout`, `APIError` 같은 예외를 던지면 `fallback`으로 재시도한다. 어떤 예외에서 fallback을 실행할지 `exceptions_to_handle`로 지정할 수 있다.

```python
chain = primary.with_fallbacks(
    [fallback],
    exceptions_to_handle=(RateLimitError, Timeout),
)
```

`exceptions_to_handle`를 지정하지 않으면 모든 예외에서 fallback을 시도한다. 버그로 인한 예외까지 삼켜버리는 경우가 있어서, 운영 환경에서는 명시적으로 지정하는 편이 낫다.

## 스트리밍 중단 처리

스트리밍 도중 클라이언트가 연결을 끊으면 서버 쪽에서 처리해야 한다. FastAPI에서 `StreamingResponse`를 쓸 때, 클라이언트가 끊으면 `astream()`의 비동기 루프가 다음 토큰을 생성하기 전까지 모른다.

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from starlette.requests import Request

app = FastAPI()

@app.post("/stream")
async def stream_endpoint(request: Request, body: dict):
    async def generate():
        async for chunk in chain.astream(body):
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")
```

`request.is_disconnected()`를 매 청크마다 확인한다. LLM 호출 자체를 취소하려면 `asyncio.Task`를 만들고 `cancel()`을 호출해야 한다.

```python
import asyncio

@app.post("/stream")
async def stream_endpoint(request: Request, body: dict):
    async def generate():
        task = asyncio.create_task(collect_stream(body))
        try:
            async for chunk in task:
                if await request.is_disconnected():
                    task.cancel()
                    break
                yield chunk
        except asyncio.CancelledError:
            pass

    return StreamingResponse(generate(), media_type="text/plain")
```

실제로는 OpenAI SDK 수준의 취소가 쉽지 않다. `httpx`의 스트리밍 연결이 `task.cancel()`로 바로 끊기지 않는 경우가 있다. 이때는 `timeout`을 짧게 걸거나 별도의 취소 플래그를 두는 방식이 현실적이다.

## 타입 불일치로 파이프라인이 조용히 깨지는 사례

LCEL에서 타입 오류가 오류 없이 지나가는 경우가 몇 가지 있다.

**문자열 대신 딕셔너리가 들어올 때.** `StrOutputParser`는 `AIMessage`의 `content`를 문자열로 꺼낸다. 그런데 파이프라인 중간에 딕셔너리를 반환하는 단계가 있으면, `StrOutputParser`에 딕셔너리가 들어간다.

```python
def add_metadata(ai_message):
    return {"answer": ai_message.content, "model": "gpt-4o"}

# StrOutputParser는 AIMessage가 들어온다고 가정한다
# 딕셔너리가 들어오면 str(dict)를 반환한다 — "{'answer': '...', 'model': 'gpt-4o'}"
broken = prompt | model | add_metadata | StrOutputParser()
```

오류는 없다. `str()` 변환이 되어버린다. 결과를 사용하는 쪽에서 파싱을 하려고 할 때 처음 발견된다.

**RunnableParallel 출력을 그대로 프롬프트에 넣을 때.** `RunnableParallel`의 출력은 항상 딕셔너리다. 프롬프트 템플릿의 변수명과 딕셔너리 키가 맞아야 한다. 키 이름이 조금 다르면 렌더링 시 빈 문자열이 들어간다.

```python
retrieval = RunnableParallel(
    ctx=retriever,        # "ctx"
    question=RunnablePassthrough(),
)

prompt = ChatPromptTemplate.from_template(
    "컨텍스트: {context}\n질문: {question}"  # "context" — ctx와 키가 다르다
)

# LangChain이 ctx를 context에 매핑하지 않는다
# {context}는 빈 문자열이 된다. 오류는 없다.
chain = retrieval | prompt | model
```

`{context}` 자리에 아무것도 들어가지 않아 모델이 컨텍스트 없이 답변한다. RAG가 동작하지 않는데 오류가 없어서 찾기 어렵다.

**RunnableLambda에서 None을 반환할 때.** 함수가 명시적으로 `return`하지 않으면 `None`이 다음 단계로 넘어간다.

```python
def process(input_dict):
    result = do_something(input_dict)
    # return을 빠뜨렸다

chain = prompt | model | RunnableLambda(process) | next_step
```

`next_step`에 `None`이 들어간다. `next_step`이 딕셔너리를 기대하면 `TypeError`가 나지만, 문자열을 기대하면 `str(None)` = `"None"`이 된다.

**batch()에서 일부 입력만 실패할 때.** `batch()`는 기본적으로 하나가 실패해도 나머지를 계속 실행한다. 실패한 입력의 결과는 예외 객체가 된다.

```python
results = chain.batch([input1, input2, input3])
# input2가 실패하면 results[1]은 Exception 객체다
# 리스트를 그냥 쓰면 나중에 타입 오류가 난다
```

`return_exceptions=False`로 설정하면 첫 번째 예외에서 전체 `batch()`가 실패한다. 어느 쪽을 원하는지 명시해야 한다.

```python
results = chain.batch(inputs, config={"max_concurrency": 5}, return_exceptions=False)
```

## 파이프라인 디버깅

`with_config(verbose=True)`로 각 단계의 입출력을 로그로 볼 수 있다. LangSmith를 쓰면 트레이스 단위로 입출력을 확인할 수 있다.

LangSmith 없이 빠르게 확인하려면 중간 단계를 분리해서 `invoke()`로 직접 실행해보는 것이 빠르다.

```python
# 체인 전체 대신 중간까지만 실행
partial = prompt | model
result = partial.invoke({"topic": "Redis"})
print(type(result), result)  # AIMessage 타입인지, 내용이 맞는지 확인
```

타입 불일치 문제는 대부분 중간 결과를 직접 찍어보면 금방 찾는다. 전체 체인을 한 번에 연결하기 전에 단계별로 확인하는 습관이 필요하다.
