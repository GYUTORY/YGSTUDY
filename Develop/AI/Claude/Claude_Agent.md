---
title: Claude Agent
tags: [ai, claude, agent, tool-use, agent-sdk, multi-agent]
updated: 2026-03-30
---

# Claude Agent

Claude API를 기반으로 직접 에이전트를 만드는 방법을 다룬다. Claude Code라는 완성된 도구를 쓰는 게 아니라, Tool Use API와 Agent SDK를 써서 내 서비스에 맞는 에이전트를 구축하는 내용이다.

---

## 1. Tool Use (Function Calling)

### 1.1 Tool Use란

LLM이 텍스트만 생성하는 게 아니라, 사전에 정의한 함수를 호출할 수 있게 하는 기능이다. Claude에게 "이런 도구가 있다"고 알려주면, 사용자 요청에 따라 어떤 도구를 어떤 인자로 호출해야 하는지 JSON으로 응답한다. 실제 함수 실행은 개발자가 한다.

흐름은 이렇다:

```
1. 개발자가 tool 목록을 정의해서 API에 전달
2. Claude가 사용자 메시지를 보고 tool 호출이 필요한지 판단
3. 필요하면 tool_use 블록으로 함수명과 인자를 응답
4. 개발자가 해당 함수를 실행하고 결과를 tool_result로 돌려줌
5. Claude가 결과를 보고 최종 답변을 생성
```

### 1.2 Tool 정의

도구는 JSON Schema 형식으로 정의한다. `name`, `description`, `input_schema`가 필수다.

```python
tools = [
    {
        "name": "get_weather",
        "description": "특정 도시의 현재 날씨 정보를 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "도시 이름 (예: Seoul, Tokyo)"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "온도 단위"
                }
            },
            "required": ["city"]
        }
    },
    {
        "name": "search_database",
        "description": "사용자 데이터베이스에서 조건에 맞는 레코드를 검색한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "description": "테이블 이름"
                },
                "conditions": {
                    "type": "object",
                    "description": "검색 조건 (컬럼명: 값)"
                },
                "limit": {
                    "type": "integer",
                    "description": "최대 결과 수"
                }
            },
            "required": ["table"]
        }
    }
]
```

`description`이 빈약하면 Claude가 도구를 잘못 선택하거나 엉뚱한 인자를 넣는 경우가 생긴다. "무엇을 하는 도구인지", "어떤 상황에서 써야 하는지"를 구체적으로 적어야 한다.

### 1.3 Tool Use 호출과 결과 처리

```python
import anthropic
import json

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": "서울 날씨 알려줘"}
    ]
)

# stop_reason이 "tool_use"이면 도구 호출 요청이 온 것
if response.stop_reason == "tool_use":
    # content에서 tool_use 블록을 찾는다
    for block in response.content:
        if block.type == "tool_use":
            tool_name = block.name      # "get_weather"
            tool_input = block.input    # {"city": "Seoul"}
            tool_use_id = block.id      # 고유 ID

            # 실제 함수 실행
            result = call_actual_function(tool_name, tool_input)

            # 결과를 Claude에게 돌려보낸다
            followup = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                tools=tools,
                messages=[
                    {"role": "user", "content": "서울 날씨 알려줘"},
                    {"role": "assistant", "content": response.content},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": json.dumps(result, ensure_ascii=False)
                            }
                        ]
                    }
                ]
            )
```

`tool_result`의 `tool_use_id`는 반드시 대응하는 `tool_use` 블록의 `id`와 일치해야 한다. 불일치하면 API에서 에러가 난다.

### 1.4 한 번에 여러 도구 호출 (Parallel Tool Use)

Claude가 한 번의 응답에서 여러 tool_use 블록을 보내는 경우가 있다. "서울이랑 도쿄 날씨 비교해줘"라고 하면 `get_weather`를 두 번 호출하는 식이다.

```python
# response.content에 tool_use 블록이 여러 개 들어있을 수 있다
tool_results = []
for block in response.content:
    if block.type == "tool_use":
        result = call_actual_function(block.name, block.input)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": json.dumps(result, ensure_ascii=False)
        })

# 모든 결과를 한 번에 돌려보내야 한다
followup = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": "서울이랑 도쿄 날씨 비교해줘"},
        {"role": "assistant", "content": response.content},
        {"role": "user", "content": tool_results}
    ]
)
```

결과를 하나만 보내고 다른 하나를 빠뜨리면 에러가 발생한다. 모든 tool_use에 대한 tool_result를 빠짐없이 보내야 한다.

병렬 호출을 원치 않으면 `tool_choice`에 `disable_parallel_tool_use: true`를 설정한다.

### 1.5 Tool Choice 옵션

Claude의 도구 사용 방식을 제어하는 옵션이다.

```python
# 도구 사용을 강제
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=tools,
    tool_choice={"type": "any"},  # 반드시 도구를 하나 이상 호출
    messages=[...]
)

# 특정 도구만 사용하도록 강제
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=tools,
    tool_choice={"type": "tool", "name": "get_weather"},
    messages=[...]
)

# 자동 판단 (기본값)
tool_choice={"type": "auto"}
```

`any`는 Claude가 "도구 없이도 답할 수 있는데요"라고 판단하더라도 억지로 도구를 쓰게 만든다. 파이프라인에서 반드시 특정 도구를 거쳐야 하는 경우에 쓴다.

### 1.6 Tool 정의 시 주의사항

- tool description에 "언제 이 도구를 쓰지 말아야 하는지"도 적어두면 오용이 줄어든다.
- `input_schema`의 `description`을 빼먹으면 Claude가 필드의 의미를 추측해야 하므로 정확도가 떨어진다.
- tool 개수가 30개를 넘으면 선택 정확도가 떨어지는 경우가 있다. 10~15개 이내가 적당하다.
- tool 정의도 입력 토큰에 포함된다. 도구를 많이 넣으면 비용이 늘어난다.

---

## 2. 에이전트 루프

### 2.1 기본 구조

에이전트는 단순 질의응답이 아니라, 스스로 판단하고 도구를 호출하고 결과를 관찰하는 루프를 돈다. 핵심은 `stop_reason`이 `"end_turn"`이 될 때까지 반복하는 것이다.

```python
import anthropic
import json

client = anthropic.Anthropic()

def run_agent(user_message: str, tools: list, system: str = "") -> str:
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system,
            tools=tools,
            messages=messages
        )

        # 도구 호출이 없으면 최종 답변
        if response.stop_reason == "end_turn":
            return extract_text(response)

        # assistant 메시지를 대화에 추가
        messages.append({"role": "assistant", "content": response.content})

        # tool_use 블록 처리
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        # tool 결과를 대화에 추가
        messages.append({"role": "user", "content": tool_results})


def extract_text(response) -> str:
    return "".join(
        block.text for block in response.content if block.type == "text"
    )


def execute_tool(name: str, input_data: dict):
    """등록된 도구를 실행한다. 실제 구현은 도구마다 다르다."""
    tool_map = {
        "get_weather": get_weather,
        "search_database": search_database,
        "run_query": run_query,
    }
    fn = tool_map.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}
    try:
        return fn(**input_data)
    except Exception as e:
        return {"error": str(e)}
```

이 루프가 에이전트의 뼈대다. Claude가 도구를 호출하면 실행하고 결과를 돌려주고, 다시 Claude가 판단하고, 이걸 반복한다.

### 2.2 루프 안전장치

무한 루프를 방지해야 한다. Claude가 같은 도구를 반복 호출하거나, 의미 없는 결과에 계속 재시도하는 경우가 실제로 발생한다.

```python
def run_agent(user_message: str, tools: list, max_iterations: int = 20) -> str:
    messages = [{"role": "user", "content": user_message}]
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            return extract_text(response)

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        messages.append({"role": "user", "content": tool_results})

    return "최대 반복 횟수 초과. 에이전트가 작업을 완료하지 못했다."
```

`max_iterations`는 도구 호출 횟수 제한이다. 복잡한 작업이면 20~30, 단순한 작업이면 5~10 정도가 적당하다. 제한 없이 돌리면 토큰 비용이 순식간에 불어난다.

### 2.3 에러 처리

도구 실행 중 에러가 나면 에러 메시지를 그대로 Claude에게 돌려보내야 한다. Claude가 에러를 보고 다른 접근법을 시도하거나, 사용자에게 문제를 설명하는 게 에이전트의 자연스러운 동작이다.

```python
def execute_tool(name: str, input_data: dict):
    fn = tool_map.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}
    try:
        return fn(**input_data)
    except ValueError as e:
        return {"error": f"잘못된 입력: {e}"}
    except TimeoutError:
        return {"error": "도구 실행 시간 초과"}
    except Exception as e:
        return {"error": f"내부 오류: {type(e).__name__}: {e}"}
```

에러를 삼키고 빈 결과를 돌려보내면 Claude가 혼란스러워하면서 같은 호출을 반복하는 경우가 생긴다. 에러 메시지는 구체적으로 보내는 게 좋다.

`tool_result`에 `is_error: true`를 설정하면 Claude가 에러 상황임을 더 명확히 인식한다.

```python
tool_results.append({
    "type": "tool_result",
    "tool_use_id": block.id,
    "content": json.dumps({"error": "테이블이 존재하지 않음"}),
    "is_error": True
})
```

---

## 3. Agent SDK

### 3.1 Agent SDK란

Anthropic이 제공하는 `claude_agent_sdk`는 에이전트 루프를 직접 구현할 필요 없이 에이전트를 만들 수 있는 Python SDK다. 위에서 설명한 while 루프, tool 실행, 메시지 관리를 SDK가 처리해준다.

Claude Code(`@anthropic-ai/claude-code`)를 라이브러리로 임포트해서 쓰는 것과는 다르다. Claude Code는 코딩 전용 도구이고, Agent SDK는 범용 에이전트를 만들기 위한 프레임워크다.

```bash
pip install claude-agent-sdk
```

### 3.2 기본 에이전트 생성

```python
from claude_agent_sdk import Agent, tool

@tool
def lookup_order(order_id: str) -> dict:
    """주문 ID로 주문 정보를 조회한다."""
    # 실제로는 DB 조회
    return {
        "order_id": order_id,
        "status": "shipped",
        "item": "무선 키보드",
        "tracking_number": "KR1234567890"
    }

@tool
def cancel_order(order_id: str, reason: str) -> dict:
    """주문을 취소한다. 배송 시작 전에만 가능하다."""
    # 실제로는 주문 취소 API 호출
    return {"success": False, "message": "이미 배송 중인 주문은 취소할 수 없습니다"}

agent = Agent(
    model="claude-sonnet-4-6",
    system="너는 이커머스 고객 지원 에이전트다. 주문 조회와 취소를 도와준다.",
    tools=[lookup_order, cancel_order]
)

result = agent.run("주문번호 ORD-12345 상태 확인해줘")
print(result.output)
```

`@tool` 데코레이터를 붙이면 함수의 이름, docstring, 타입 힌트에서 tool 정의를 자동 생성한다. 직접 JSON Schema를 작성할 필요가 없다.

### 3.3 에이전트 설정

```python
agent = Agent(
    model="claude-sonnet-4-6",
    system="...",
    tools=[lookup_order, cancel_order],
    max_turns=15,           # 최대 도구 호출 턴 수
    temperature=0.0,        # 결정적 응답 (에이전트에서는 보통 0)
    stop_sequences=None,    # 특정 문자열에서 멈추기
)
```

`temperature`는 에이전트에서 0으로 두는 게 일반적이다. 도구 선택에 랜덤성이 들어가면 같은 입력에 다른 동작을 하게 되어 디버깅이 어렵다.

### 3.4 @tool 데코레이터 상세

타입 힌트가 input_schema로 변환된다.

```python
from typing import Optional

@tool
def search_products(
    query: str,
    category: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    sort_by: str = "relevance"
) -> list[dict]:
    """상품을 검색한다.

    Args:
        query: 검색 키워드
        category: 카테고리 필터 (예: electronics, clothing)
        min_price: 최소 가격 (원)
        max_price: 최대 가격 (원)
        sort_by: 정렬 기준 (relevance, price_asc, price_desc)
    """
    # 실제 검색 로직
    ...
```

docstring의 Args 섹션이 각 파라미터의 description으로 들어간다. 타입 힌트에서 `Optional`이면 required에서 빠진다.

### 3.5 비동기 도구

I/O 작업이 많은 도구는 async로 정의할 수 있다.

```python
import httpx

@tool
async def fetch_url(url: str) -> dict:
    """URL의 내용을 가져온다."""
    async with httpx.AsyncClient() as http:
        resp = await http.get(url, timeout=10)
        return {
            "status_code": resp.status_code,
            "body": resp.text[:5000]  # 너무 길면 잘라내기
        }

# 비동기 에이전트 실행
result = await agent.run_async("https://example.com 페이지 내용 확인해줘")
```

---

## 4. 멀티 에이전트 아키텍처

### 4.1 왜 에이전트를 나누는가

하나의 에이전트에 도구를 20~30개 넣으면 도구 선택 정확도가 떨어진다. system prompt도 길어지면서 지시 사항을 놓치는 일이 생긴다.

에이전트를 역할별로 나누면 각 에이전트의 도구와 system prompt가 짧아지고, 책임 범위가 명확해진다. 마이크로서비스 아키텍처와 비슷한 발상이다.

### 4.2 오케스트레이터 패턴

상위 에이전트가 하위 에이전트를 도구처럼 호출하는 구조다.

```python
from claude_agent_sdk import Agent, tool

# 하위 에이전트: 주문 처리 전담
order_agent = Agent(
    model="claude-sonnet-4-6",
    system="너는 주문 관련 업무만 처리한다. 주문 조회, 취소, 변경을 담당한다.",
    tools=[lookup_order, cancel_order, modify_order]
)

# 하위 에이전트: 상품 검색 전담
product_agent = Agent(
    model="claude-sonnet-4-6",
    system="너는 상품 검색과 추천을 담당한다.",
    tools=[search_products, get_product_detail, get_recommendations]
)

# 오케스트레이터가 하위 에이전트를 도구로 사용
@tool
def handle_order_request(request: str) -> str:
    """주문 관련 요청을 처리한다. 주문 조회, 취소, 변경 등."""
    result = order_agent.run(request)
    return result.output

@tool
def handle_product_request(request: str) -> str:
    """상품 검색, 상세 정보, 추천 관련 요청을 처리한다."""
    result = product_agent.run(request)
    return result.output

orchestrator = Agent(
    model="claude-sonnet-4-6",
    system="""너는 고객 지원 오케스트레이터다.
사용자 요청을 분석해서 적절한 담당 에이전트에게 전달한다.
주문 관련이면 handle_order_request, 상품 관련이면 handle_product_request를 쓴다.""",
    tools=[handle_order_request, handle_product_request]
)

result = orchestrator.run("주문한 키보드 언제 오나요? 그리고 마우스도 추천해줘")
```

"주문 확인 + 상품 추천"처럼 여러 도메인에 걸친 요청이 들어오면 오케스트레이터가 알아서 두 에이전트를 호출한다.

### 4.3 핸드오프 패턴

Agent SDK에서 제공하는 handoff 기능을 쓰면 에이전트 간 대화 전환이 가능하다.

```python
from claude_agent_sdk import Agent, handoff

refund_agent = Agent(
    model="claude-sonnet-4-6",
    system="환불 처리를 담당한다. 환불 정책 확인, 환불 신청, 환불 상태 조회를 할 수 있다.",
    tools=[check_refund_policy, request_refund, check_refund_status]
)

support_agent = Agent(
    model="claude-sonnet-4-6",
    system="일반 고객 지원을 담당한다. 환불 관련 요청이 들어오면 환불 전담 에이전트로 넘긴다.",
    tools=[lookup_order, cancel_order],
    handoffs=[handoff(refund_agent, description="환불 관련 문의를 처리하는 에이전트")]
)
```

handoff가 일어나면 대화 맥락이 다음 에이전트로 넘어간다. 오케스트레이터 패턴과 달리 에이전트가 교체되는 방식이어서, 긴 대화에서 맥락 손실이 적다.

### 4.4 멀티 에이전트 설계 시 주의사항

- 에이전트를 너무 잘게 나누면 오케스트레이터의 라우팅 실수가 늘어난다. 3~5개 정도가 관리하기 좋다.
- 하위 에이전트의 응답이 길면 오케스트레이터의 컨텍스트가 빠르게 찬다. 하위 에이전트의 `max_tokens`를 제한하거나, 요약해서 돌려보내는 게 낫다.
- 각 에이전트의 API 호출이 순차적으로 일어나므로 응답 시간이 길어진다. 병렬 처리가 필요하면 비동기 실행을 고려해야 한다.
- 에이전트 간 상태 공유가 필요하면 별도 저장소(Redis, DB 등)를 두는 게 깔끔하다. 메시지로 상태를 넘기면 맥락이 복잡해진다.

---

## 5. ReAct 패턴

### 5.1 ReAct란

Reasoning + Acting의 줄임말이다. 모델이 먼저 추론(Reasoning)을 하고, 그 결과에 따라 행동(Acting)을 하고, 다시 관찰(Observation)한 뒤 추론하는 패턴이다. 에이전트 루프와 본질적으로 같지만, "추론 과정을 명시적으로 출력하게 한다"는 점이 다르다.

```
Thought: 사용자가 서울 날씨를 물어봤다. get_weather를 호출해야 한다.
Action: get_weather(city="Seoul")
Observation: {"temp": 15, "condition": "cloudy"}
Thought: 날씨 정보를 받았다. 사용자에게 알려주면 된다.
Answer: 서울은 현재 15도이고 흐린 날씨입니다.
```

### 5.2 Claude에서 ReAct 구현

Claude의 Extended Thinking을 켜면 Thought 부분이 자연스럽게 구현된다. thinking 블록에서 추론하고, tool_use로 행동하고, tool_result로 관찰하는 흐름이 된다.

```python
def run_react_agent(user_message: str, tools: list) -> str:
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            thinking={
                "type": "enabled",
                "budget_tokens": 4096
            },
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            return extract_text(response)

        # thinking 블록 로깅 — 디버깅에 필수
        for block in response.content:
            if block.type == "thinking":
                print(f"[Reasoning] {block.thinking}")

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[Action] {block.name}({block.input})")
                result = execute_tool(block.name, block.input)
                print(f"[Observation] {result}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        messages.append({"role": "user", "content": tool_results})
```

thinking을 켜지 않더라도 system prompt에서 "도구를 호출하기 전에 왜 그 도구를 선택했는지 설명해라"고 지시하면 비슷한 효과를 낼 수 있다. 다만 이 경우 추론 내용이 사용자에게 노출되는 출력 텍스트에 섞인다.

### 5.3 ReAct vs 단순 에이전트 루프

ReAct 패턴의 장점은 디버깅이 쉽다는 것이다. 에이전트가 왜 그런 판단을 했는지 추론 과정이 남으니, 잘못된 도구를 선택했을 때 원인을 파악하기 쉽다.

단점은 토큰 소모가 늘어난다는 것이다. thinking에 할당한 토큰도 과금 대상이다. 단순한 도구 호출에는 오버킬이고, 여러 도구를 조합해서 복잡한 작업을 수행해야 하는 경우에 가치가 있다.

---

## 6. 에이전트 상태 관리와 메모리

### 6.1 대화 내 상태 관리

에이전트 루프에서 messages 배열이 곧 상태다. 대화가 길어지면 두 가지 문제가 생긴다.

1. **컨텍스트 윈도우 초과**: messages가 200K 토큰을 넘으면 API 에러가 난다.
2. **비용 폭증**: 매 요청마다 전체 messages를 보내므로 대화가 길어질수록 비용이 기하급수적으로 증가한다.

```python
def trim_messages(messages: list, max_pairs: int = 10) -> list:
    """오래된 메시지를 잘라낸다. 첫 메시지(사용자 원래 요청)는 유지한다."""
    if len(messages) <= max_pairs * 2 + 1:
        return messages
    # 첫 메시지 + 최근 N쌍만 유지
    return [messages[0]] + messages[-(max_pairs * 2):]
```

### 6.2 대화 간 메모리 — 요약 기반

이전 대화의 맥락을 다음 대화에서 이어가려면 메모리가 필요하다. 가장 단순한 방법은 대화를 요약해서 저장하고, 다음 대화의 system prompt에 넣는 것이다.

```python
def summarize_conversation(messages: list) -> str:
    """대화를 요약한다."""
    summary_response = client.messages.create(
        model="claude-haiku-4-5",  # 요약은 저렴한 모델로
        max_tokens=500,
        system="이전 대화 내용을 3~5문장으로 요약해라. 사용자의 핵심 요청과 결과만 남겨라.",
        messages=[
            {"role": "user", "content": f"대화 내용:\n{format_messages(messages)}"}
        ]
    )
    return summary_response.content[0].text


def run_agent_with_memory(user_message: str, memory_store: dict, session_id: str):
    # 이전 대화 요약이 있으면 system prompt에 포함
    previous_summary = memory_store.get(session_id, "")
    system = "너는 고객 지원 에이전트다."
    if previous_summary:
        system += f"\n\n이전 대화 요약:\n{previous_summary}"

    result = run_agent(user_message, tools=tools, system=system)

    # 이번 대화 요약 저장
    memory_store[session_id] = summarize_conversation(messages)

    return result
```

### 6.3 구조화된 메모리

요약 대신 키-값 형태로 구조화된 정보를 저장하는 방법도 있다. 사용자 선호, 이전 작업 결과 등을 명시적으로 기록한다.

```python
@tool
def save_memory(key: str, value: str) -> dict:
    """기억할 정보를 저장한다. 사용자 선호, 중요한 결정 사항 등."""
    memory_db[current_session][key] = value
    return {"saved": True, "key": key}

@tool
def recall_memory(key: str) -> dict:
    """저장된 정보를 조회한다."""
    value = memory_db[current_session].get(key)
    if value is None:
        return {"found": False}
    return {"found": True, "key": key, "value": value}

@tool
def list_memories() -> dict:
    """저장된 모든 기억 키 목록을 반환한다."""
    keys = list(memory_db[current_session].keys())
    return {"keys": keys}
```

메모리 도구를 에이전트에 등록하면, Claude가 중요하다고 판단한 정보를 스스로 저장하고 필요할 때 꺼내 쓴다. 다만 "뭘 기억할지"의 판단을 모델에게 맡기므로, 중요한 정보를 안 저장하거나 불필요한 정보를 저장하는 경우가 있다. system prompt에서 "어떤 정보를 저장해야 하는지" 기준을 명시해두면 정확도가 올라간다.

### 6.4 벡터 DB 기반 메모리 (RAG)

대화 이력이 많아지면 단순 키-값으로는 한계가 있다. 임베딩을 써서 유사한 과거 대화를 검색하는 방식이 필요해진다.

```python
from openai import OpenAI  # 임베딩은 다른 모델 써도 됨

embedding_client = OpenAI()

def embed_text(text: str) -> list[float]:
    resp = embedding_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return resp.data[0].embedding


def store_memory(text: str, metadata: dict):
    vector = embed_text(text)
    # Pinecone, Qdrant, pgvector 등에 저장
    vector_db.upsert(
        id=str(uuid4()),
        vector=vector,
        metadata={**metadata, "text": text}
    )


def retrieve_relevant_memories(query: str, top_k: int = 5) -> list[str]:
    query_vector = embed_text(query)
    results = vector_db.query(vector=query_vector, top_k=top_k)
    return [r.metadata["text"] for r in results.matches]
```

이걸 에이전트 루프에 통합하면 매 요청 전에 관련 과거 정보를 가져와서 system prompt에 주입하는 구조가 된다. RAG for Code 문서에서 다루는 검색 증강 생성과 같은 원리다.

### 6.5 메모리 구현 시 주의사항

- 메모리에 민감한 정보(비밀번호, API 키 등)가 저장되지 않도록 필터링이 필요하다.
- 오래된 메모리는 정리해야 한다. 몇 달 전 대화 내용이 현재 맥락을 오염시키는 경우가 있다.
- 메모리 조회 결과가 너무 많으면 컨텍스트를 낭비한다. top_k를 적절히 제한하고, 관련성이 낮은 결과는 필터링한다.
- 세션 단위 메모리와 사용자 단위 메모리를 구분해야 한다. 세션 메모리는 대화가 끝나면 정리하고, 사용자 메모리는 장기 보존한다.

---

## 7. 프로덕션 에이전트 운영

### 7.1 로깅

에이전트의 모든 턴을 로깅해야 한다. 문제가 발생했을 때 어떤 도구를 어떤 인자로 호출했고, 어떤 결과를 받았는지 추적할 수 있어야 한다.

```python
import logging

logger = logging.getLogger("agent")

def run_agent_with_logging(user_message: str, tools: list) -> str:
    messages = [{"role": "user", "content": user_message}]
    request_id = str(uuid4())
    logger.info(f"[{request_id}] 에이전트 시작: {user_message[:100]}")

    iteration = 0
    while iteration < 20:
        iteration += 1
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        logger.info(
            f"[{request_id}] turn={iteration} "
            f"stop_reason={response.stop_reason} "
            f"input_tokens={response.usage.input_tokens} "
            f"output_tokens={response.usage.output_tokens}"
        )

        if response.stop_reason == "end_turn":
            return extract_text(response)

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                logger.info(f"[{request_id}] tool_call: {block.name} args={block.input}")
                result = execute_tool(block.name, block.input)
                logger.info(f"[{request_id}] tool_result: {json.dumps(result)[:500]}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        messages.append({"role": "user", "content": tool_results})

    logger.warning(f"[{request_id}] max iterations 도달")
    return "작업을 완료하지 못했다."
```

### 7.2 비용 추적

에이전트가 한 요청에 API를 여러 번 호출하므로 비용이 예측하기 어렵다. 턴마다 토큰 사용량을 누적해서 추적해야 한다.

```python
def run_agent_with_cost_tracking(user_message: str, tools: list):
    total_input_tokens = 0
    total_output_tokens = 0
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        if response.stop_reason == "end_turn":
            # Sonnet 4.6 기준 비용 계산
            cost = (total_input_tokens / 1_000_000 * 3) + \
                   (total_output_tokens / 1_000_000 * 15)
            return {
                "output": extract_text(response),
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "estimated_cost_usd": round(cost, 4)
            }

        messages.append({"role": "assistant", "content": response.content})
        tool_results = process_tool_calls(response)
        messages.append({"role": "user", "content": tool_results})
```

비용이 일정 임계값을 넘으면 에이전트를 중단하는 로직도 넣어야 한다. 에이전트가 루프에 빠져서 토큰을 소진하는 사고를 막을 수 있다.

### 7.3 타임아웃과 재시도

Anthropic API는 가끔 타임아웃이 나거나 5xx 에러를 돌려준다. SDK에 기본 재시도 로직이 있지만, 에이전트 전체에 대한 타임아웃도 설정해야 한다.

```python
import asyncio

async def run_agent_with_timeout(user_message: str, timeout_seconds: int = 120):
    try:
        result = await asyncio.wait_for(
            run_agent_async(user_message),
            timeout=timeout_seconds
        )
        return result
    except asyncio.TimeoutError:
        return "에이전트 실행 시간 초과 (120초)"
```

에이전트가 외부 API를 호출하는 도구를 쓸 때, 외부 API 자체가 느린 경우도 있다. 도구 실행에도 개별 타임아웃을 걸어야 한다.

---

## 8. 실제 에이전트 예시 — 코드 리뷰 에이전트

Tool Use와 에이전트 루프를 조합한 실제 예시다. GitHub PR의 코드를 읽고 리뷰 코멘트를 다는 에이전트를 만든다.

```python
import anthropic
import json
import httpx

client = anthropic.Anthropic()
GITHUB_TOKEN = "ghp_..."

@tool
def get_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    """PR에서 변경된 파일 목록을 가져온다."""
    resp = httpx.get(
        f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files",
        headers={"Authorization": f"token {GITHUB_TOKEN}"}
    )
    files = resp.json()
    return [
        {"filename": f["filename"], "patch": f.get("patch", ""), "status": f["status"]}
        for f in files
    ]

@tool
def get_file_content(owner: str, repo: str, path: str, ref: str) -> dict:
    """특정 브랜치의 파일 전체 내용을 가져온다."""
    resp = httpx.get(
        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
        params={"ref": ref},
        headers={"Authorization": f"token {GITHUB_TOKEN}"}
    )
    import base64
    content = base64.b64decode(resp.json()["content"]).decode("utf-8")
    return {"path": path, "content": content}

@tool
def post_review_comment(
    owner: str, repo: str, pr_number: int,
    body: str, path: str, line: int
) -> dict:
    """PR에 라인별 리뷰 코멘트를 남긴다."""
    resp = httpx.post(
        f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments",
        headers={"Authorization": f"token {GITHUB_TOKEN}"},
        json={
            "body": body,
            "commit_id": get_latest_commit(owner, repo, pr_number),
            "path": path,
            "line": line,
            "side": "RIGHT"
        }
    )
    return {"status": resp.status_code, "id": resp.json().get("id")}

review_agent = Agent(
    model="claude-sonnet-4-6",
    system="""너는 코드 리뷰어다. PR의 변경 파일을 확인하고, 문제가 있는 부분에 리뷰 코멘트를 남겨라.
다음을 중점적으로 봐라:
- 버그 가능성이 있는 코드
- 보안 취약점 (SQL injection, XSS 등)
- 에러 처리 누락
- 성능 문제

사소한 스타일 지적은 하지 마라. 실질적인 문제만 코멘트해라.""",
    tools=[get_pr_files, get_file_content, post_review_comment]
)

result = review_agent.run("owner/my-repo 레포의 PR #42를 리뷰해줘")
```

이 에이전트는 PR 파일 목록을 가져오고, 필요하면 파일 전체를 읽고, 문제를 발견하면 코멘트를 남기는 루프를 자동으로 돈다. 실제로 쓸 때는 코멘트를 바로 남기기 전에 확인 단계를 넣는 게 안전하다.
