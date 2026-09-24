---
title: OpenAI Assistants API vs Claude Agent SDK
tags: [ai, llm, api, backend]
updated: 2026-09-24
---

# OpenAI Assistants API vs Claude Agent SDK

두 API를 나란히 써봐야 차이가 드러난다. 겉으로 비슷해 보이는 기능인데, 상태를 어디서 관리하느냐는 설계 결정이 코드 구조와 운영 방식을 완전히 다르게 만든다.

## 핵심 차이

OpenAI Assistants API는 **서버 사이드 상태** 모델이다. Thread(대화 세션), Run(실행), Message가 OpenAI 서버에 저장된다. 클라이언트는 ID만 들고 다니고, 서버 상태를 폴링하면서 진행 상황을 추적한다.

Anthropic SDK로 에이전트를 구현하면 **클라이언트 사이드 상태** 모델이 된다. 메시지 히스토리는 클라이언트 코드 안의 배열에 있다. API 호출마다 전체 대화를 서버에 전송한다. 서버는 아무것도 기억하지 않는다.

이 차이가 파일 처리, 도구 구현, 비용 계산에 전부 영향을 준다.

## 시나리오

사용자가 Python 파일을 업로드하면 타입 힌트가 없는 함수를 찾아 줄 번호와 함께 보고하는 에이전트다. 첫 번째 요청 후 "반환 타입 힌트만 빠진 것도 따로 정리해줘"라는 후속 질문이 오는 2턴 대화로 스레드 모델, 파일 처리, 도구 구현을 비교한다.

## 스레드 모델

### OpenAI

```python
from openai import OpenAI
import json, ast
client = OpenAI()

# 어시스턴트는 한 번 만들어 재사용한다. assistant_id를 DB에 저장해 두면 된다.
assistant = client.beta.assistants.create(
    name="코드 분석기",
    instructions="Python 파일을 분석해서 타입 힌트 누락을 보고한다. 파일명, 줄 번호, 함수명을 포함한다.",
    tools=[
        {
            "type": "function",
            "function": {
                "name": "analyze_type_hints",
                "description": "Python 코드에서 타입 힌트가 없는 함수를 찾는다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "check_return_only": {"type": "boolean"}
                    },
                    "required": ["code"]
                }
            }
        }
    ],
    model="gpt-4o"
)

# Thread = 하나의 대화 세션. OpenAI 서버에 저장되고 thread_id로 참조한다.
thread = client.beta.threads.create()

with open("main.py") as f:
    code = f.read()

client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content=f"이 파일에서 타입 힌트가 없는 함수를 찾아줘:\n\n```python\n{code}\n```"
)

run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id,
    assistant_id=assistant.id,
    poll_interval_ms=500
)

# create_and_poll은 requires_action 상태에서 멈춘다.
# 함수 도구 결과는 직접 제출해야 한다.
if run.status == "requires_action":
    tool_calls = run.required_action.submit_tool_outputs.tool_calls
    outputs = []
    for call in tool_calls:
        args = json.loads(call.function.arguments)
        result = analyze_type_hints(**args)
        outputs.append({
            "tool_call_id": call.id,
            "output": json.dumps(result, ensure_ascii=False)
        })
    run = client.beta.threads.runs.submit_tool_outputs_and_poll(
        thread_id=thread.id, run_id=run.id, tool_outputs=outputs
    )

# 두 번째 턴: thread_id만 있으면 이전 대화가 이어진다
client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="반환 타입 힌트만 빠진 것도 따로 정리해줘"
)
run2 = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id, assistant_id=assistant.id
)
# requires_action 처리 반복
```

두 번째 메시지를 추가할 때 이전 대화 내용을 보낼 필요가 없다. `thread_id`만 알면 서버가 맥락을 연결한다.

### Anthropic SDK

```python
import anthropic, json
client = anthropic.Anthropic()

tools = [
    {
        "name": "analyze_type_hints",
        "description": "Python 코드에서 타입 힌트가 없는 함수를 찾는다",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "check_return_only": {"type": "boolean"}
            },
            "required": ["code"]
        }
    }
]

# 대화 히스토리는 클라이언트가 관리한다
conversation: list[dict] = []

def run_turn(messages: list, user_text: str) -> str:
    messages.append({"role": "user", "content": user_text})
    while True:
        resp = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            system="Python 파일을 분석해서 타입 힌트 누락을 보고한다.",
            tools=tools,
            messages=messages
        )
        if resp.stop_reason == "end_turn":
            text = next(b.text for b in resp.content if b.type == "text")
            messages.append({"role": "assistant", "content": text})
            return text

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            result = analyze_type_hints(**block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, ensure_ascii=False)
            })
        messages.append({"role": "user", "content": tool_results})

with open("main.py") as f:
    code = f.read()

result1 = run_turn(
    conversation,
    f"이 파일에서 타입 힌트가 없는 함수를 찾아줘:\n\n```python\n{code}\n```"
)

# 두 번째 턴: conversation 배열 전체(파일 내용 포함)가 다시 API로 전송된다
result2 = run_turn(conversation, "반환 타입 힌트만 빠진 것도 따로 정리해줘")
```

두 번째 메시지를 보낼 때 `conversation` 전체, 즉 파일 내용까지 포함한 배열이 그대로 전송된다.

## 파일 처리

### OpenAI Files API

```python
# 파일을 OpenAI 서버에 업로드한다
with open("main.py", "rb") as f:
    file_obj = client.files.create(file=f, purpose="assistants")

# file_search를 쓰려면 벡터 스토어가 필요하다
vector_store = client.beta.vector_stores.create(name="코드베이스")
client.beta.vector_stores.files.create_and_poll(
    vector_store_id=vector_store.id,
    file_id=file_obj.id
)
client.beta.assistants.update(
    assistant.id,
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
)

# 메시지에 파일 첨부
client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="이 파일에서 타입 힌트 누락을 찾아줘",
    attachments=[{"file_id": file_obj.id, "tools": [{"type": "file_search"}]}]
)

# 작업 후 직접 삭제하지 않으면 스토리지 비용이 계속 발생한다
client.beta.vector_stores.delete(vector_store.id)
client.files.delete(file_obj.id)
```

파일이 서버에 남아 있어서 여러 스레드에서 같은 파일을 참조할 수 있다. 대신 파일 수명을 직접 관리해야 한다. 테스트 중 업로드한 파일을 지우지 않아 스토리지 요금이 조용히 쌓이는 경우가 있다.

### Anthropic Files API (beta)

```python
# Files API로 업로드하면 파일 ID로 참조할 수 있다
with open("main.py", "rb") as f:
    file_obj = client.beta.files.upload(
        file=("main.py", f, "text/plain")
    )

conversation.append({
    "role": "user",
    "content": [
        {"type": "text", "text": "이 파일에서 타입 힌트 누락을 찾아줘"},
        {
            "type": "document",
            "source": {"type": "file", "file_id": file_obj.id}
        }
    ]
})

# 사용 후 삭제
client.beta.files.delete(file_obj.id)
```

파일이 수 KB 수준이라면 f-string으로 코드 내용을 메시지에 직접 붙이는 게 더 단순하다. 파일이 크거나 같은 파일을 여러 대화에서 재사용한다면 Files API 쪽이 낫다. 단, Anthropic Files API는 현재 beta라 지원 파일 타입과 크기 제한을 확인해야 한다.

## Tool 구현 — 공통 함수

```python
import ast

def analyze_type_hints(code: str, check_return_only: bool = False) -> dict:
    tree = ast.parse(code)
    results = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        missing = []
        if not check_return_only:
            for arg in node.args.args:
                if arg.annotation is None and arg.arg != "self":
                    missing.append(f"인자 '{arg.arg}'")

        if node.returns is None:
            missing.append("반환 타입")

        if missing:
            results.append({
                "line": node.lineno,
                "function": node.name,
                "missing": missing
            })

    return {"findings": results, "total": len(results)}
```

도구 함수 자체는 두 API에서 동일하다. 차이는 이 함수를 **언제, 어떻게 호출하고 결과를 모델에게 돌려주는가**에 있다.

OpenAI는 Run이 `requires_action` 상태가 됐을 때 클라이언트가 결과를 제출하면 실행이 재개되는 폴링 구조다. Anthropic은 단일 HTTP 응답 안에 `tool_use` 블록이 오고, 다음 메시지에 `tool_result`를 붙여서 다시 호출하는 구조다. 폴링 루프가 없고, 상태 코드도 없다.

## 상태 관리

**OpenAI 서버 상태에서 생기는 문제**

Thread는 30일 뒤 삭제된다. DB에 `thread_id`를 저장해두었다가 30일 후에 조회하면 404가 난다.

```python
try:
    messages = client.beta.threads.messages.list(thread_id=saved_thread_id)
except openai.NotFoundError:
    # 스레드 만료. ID는 DB에 있지만 내용은 없다.
    pass
```

스레드가 길어져 모델 컨텍스트를 초과하면 OpenAI가 오래된 메시지를 자동으로 잘라낸다. 어디서 잘렸는지 명시적으로 알기 어렵다. 잘린 맥락 때문에 모델이 엉뚱한 답을 해도 원인 추적이 어렵다.

**Anthropic SDK 클라이언트 상태**

히스토리 배열이 코드 안에 있어서 직접 검사하고 조작할 수 있다.

```python
total_chars = sum(len(str(m["content"])) for m in conversation)

if total_chars > 200_000:
    # 처음 두 메시지(핵심 맥락)를 유지하고 오래된 것을 자른다
    conversation = conversation[:2] + conversation[-10:]
```

DB에 저장할 때는 배열을 JSON으로 직렬화한다. 만료 걱정이 없고 이식성이 있다.

```python
# 저장
db.save(session_id, json.dumps(conversation, ensure_ascii=False))

# 복원
conversation = json.loads(db.load(session_id))
```

## 비용 구조

| 항목 | OpenAI Assistants | Anthropic SDK |
|---|---|---|
| 메시지 토큰 | 입력/출력 기준 | 입력/출력 기준 |
| 파일 스토리지 | $0.10/GB/day | Files API 스토리지 비용 |
| 벡터 스토어 | $0.10/GB/day | 없음 (직접 구현) |
| Code Interpreter | 세션당 $0.03 | 없음 (직접 샌드박스) |
| 프롬프트 캐싱 | 없음 | 입력 토큰 최대 90% 절감 |

히스토리가 길어질수록 입력 토큰이 누적된다는 점은 양쪽 다 같다. 차이는 Anthropic의 Prompt Caching이다. 파일 내용이 크고 여러 턴에 걸쳐 반복 전송될 때 캐시 히트가 발생하면 비용이 크게 줄어든다.

```python
# system과 파일 내용을 캐시한다
resp = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=2048,
    system=[
        {
            "type": "text",
            "text": "Python 파일을 분석하는 에이전트다.",
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": code_content,
                    "cache_control": {"type": "ephemeral"}
                },
                {"type": "text", "text": "타입 힌트 누락을 찾아줘"}
            ]
        }
    ]
)
# 두 번째 호출부터 캐시 히트 → 입력 토큰 비용 감소
```

OpenAI에서 파일 스토리지 비용은 명시적으로 추가된다. 벡터 스토어를 만들면 $0.10/GB/day가 쌓인다. 단발성 코드 분석 작업은 끝나는 즉시 파일과 벡터 스토어를 삭제해야 한다.

## 선택 기준

**OpenAI Assistants API가 맞는 경우**

- Code Interpreter가 필요하다. 코드 실행 샌드박스를 직접 구성하는 건 복잡하다.
- 파일 검색(file_search)을 빠르게 붙여야 한다. 벡터 스토어 구축 없이 쓸 수 있다.
- 히스토리 관리를 직접 하고 싶지 않다. `thread_id` 하나로 대화를 이어갈 수 있다.
- GPT-4o 계열 모델로 고정해도 된다.

스레드 만료(30일), 파일 스토리지 관리, `requires_action` 폴링 처리, 히스토리 자동 절단 문제는 직접 대응해야 한다.

**Anthropic SDK가 맞는 경우**

- 대화 상태를 직접 제어해야 한다. 히스토리 잘라내기, 요약 주입, 맥락 관리를 직접 결정하고 싶다.
- 파일이 크고 대화 턴이 많다. Prompt Caching으로 비용을 줄일 수 있다.
- 서버 만료 리스크를 없애고 싶다. 대화 내용을 내 DB에 직접 보관한다.
- Claude 모델 계열이 필요하다.

히스토리 직렬화/복원, 컨텍스트 압축 로직은 직접 구현해야 한다.

**실제로 갈리는 지점**

Code Interpreter 없이 단순 함수 도구만 쓰는 경우, Anthropic SDK 코드가 더 단순하다. 폴링이 없고, `requires_action` 상태 처리가 없고, 서버 상태 동기화 문제가 없다.

멀티 사용자 서비스에서 사용자별 대화를 DB에 저장해야 한다면, 두 방식 모두 DB가 필요하다. OpenAI는 `thread_id`를 저장하고, Anthropic은 `conversation` 배열을 저장한다. `thread_id` 저장 방식은 저장 크기가 작지만 30일 만료와 서버 의존성이 따라온다. "사용자 A의 1월 대화 내역을 6개월 후에 조회해야 한다"는 요구사항이 있다면 배열을 직접 저장하는 Anthropic 방식이 안전하다.
