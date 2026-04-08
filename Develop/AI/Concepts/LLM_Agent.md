---
title: LLM 기반 에이전트 구현
tags: [ai, llm, agent, react, multi-agent, orchestration]
updated: 2026-04-08
---

# LLM 기반 에이전트 구현

## 1. 에이전트란

LLM의 Function Calling(Tool Use)은 "LLM이 도구를 한 번 호출하고, 결과를 받아서 응답하는 것"이다. 에이전트는 이걸 루프로 돌린다. LLM이 스스로 판단해서 도구를 고르고, 결과를 보고, 다음 행동을 결정하는 과정을 목표를 달성할 때까지 반복한다.

단순 Tool Use와 에이전트의 차이:

| 구분 | Tool Use (1회) | 에이전트 (루프) |
|------|---------------|---------------|
| 호출 횟수 | LLM → 도구 → 응답, 1사이클 | 목표 달성까지 N사이클 반복 |
| 판단 주체 | 개발자가 흐름 설계 | LLM이 다음 행동 결정 |
| 상태 관리 | 없음 | 대화 히스토리, 중간 결과 누적 |
| 실패 처리 | 호출 실패 시 에러 반환 | 다른 방법 시도, 재시도, 포기 판단 |

핵심은 **루프 안에서 LLM이 "다음에 뭘 할지"를 결정한다**는 것이다. 개발자가 if-else로 분기를 짜는 게 아니라, LLM의 추론 능력에 흐름 제어를 맡긴다.


## 2. ReAct 패턴

ReAct는 Reasoning + Acting의 줄임말이다. LLM이 행동하기 전에 먼저 생각(Thought)을 출력하고, 그 다음에 행동(Action)하고, 결과를 관찰(Observation)하는 패턴이다. 2022년 Yao et al. 논문에서 제안됐고, 현재 대부분의 에이전트 프레임워크가 이 패턴을 기반으로 한다.

### 2.1 Thought-Action-Observation 사이클

```
Thought: 사용자가 서울 날씨를 물어봤다. 날씨 API를 호출해야 한다.
Action: get_weather(location="서울")
Observation: {"temp": 18, "condition": "맑음", "humidity": 45}

Thought: 날씨 정보를 받았다. 사용자에게 알려주면 된다.
Action: finish(answer="서울 현재 기온 18도, 맑음, 습도 45%입니다.")
```

이 흐름이 반복되면서 복잡한 작업도 단계별로 처리할 수 있다. Thought 단계에서 LLM이 현재 상황을 분석하고, 어떤 도구를 왜 호출하는지 추론한다. 이 추론 과정이 있기 때문에 단순 Tool Use보다 정확도가 높다.

### 2.2 Python으로 구현하기

OpenAI API 기준으로 ReAct 에이전트의 핵심 루프를 구현하면 이렇다:

```python
import json
from openai import OpenAI

client = OpenAI()

# 도구 정의
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_db",
            "description": "주문 DB에서 주문 정보를 조회한다",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "주문 ID"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "고객에게 이메일을 발송한다",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    }
]

# 실제 도구 실행 함수
def execute_tool(name: str, arguments: dict) -> str:
    if name == "search_db":
        # 실제로는 DB 조회
        return json.dumps({"order_id": arguments["order_id"], "status": "배송중", "eta": "2026-04-10"})
    elif name == "send_email":
        # 실제로는 이메일 발송
        return json.dumps({"success": True, "message_id": "msg_123"})
    return json.dumps({"error": f"unknown tool: {name}"})


def run_agent(user_message: str, max_turns: int = 10) -> str:
    messages = [
        {"role": "system", "content": "너는 주문 관리 에이전트다. 도구를 사용해서 사용자의 요청을 처리해라."},
        {"role": "user", "content": user_message}
    ]

    for turn in range(max_turns):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools
        )

        message = response.choices[0].message
        messages.append(message)

        # 도구 호출이 없으면 최종 응답
        if not message.tool_calls:
            return message.content

        # 도구 호출 처리
        for tool_call in message.tool_calls:
            result = execute_tool(
                tool_call.function.name,
                json.loads(tool_call.function.arguments)
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    return "최대 반복 횟수를 초과했습니다."


# 실행
answer = run_agent("주문 ORD-456 상태 확인하고, 고객 kim@example.com에게 배송 안내 메일 보내줘")
print(answer)
```

`run_agent` 함수의 for 루프가 에이전트의 핵심이다. LLM이 `tool_calls`를 반환하면 도구를 실행하고 결과를 messages에 추가한다. `tool_calls`가 없으면 LLM이 최종 응답을 내린 것이므로 루프를 종료한다.

### 2.3 ReAct 구현 시 주의할 점

**max_turns 제한은 필수다.** LLM이 같은 도구를 무한 반복하거나, 해결할 수 없는 문제에 계속 시도하는 경우가 있다. max_turns 없이 배포하면 API 비용이 걷잡을 수 없이 늘어난다. 프로덕션에서는 10~20회가 적당하다.

**도구 실행 결과가 너무 길면 문제가 된다.** DB 조회 결과가 수천 행이면 컨텍스트 윈도우를 다 먹는다. 도구 함수 안에서 결과를 요약하거나 페이지네이션 처리해야 한다.

**Thought를 명시적으로 출력하게 만드는 게 디버깅에 도움된다.** 시스템 프롬프트에 "도구를 호출하기 전에 왜 이 도구를 사용하는지 먼저 설명해라"를 추가하면, 에이전트가 잘못된 판단을 할 때 원인을 파악하기 쉽다. 다만 토큰 소비가 늘어나므로 프로덕션에서는 trade-off를 따져야 한다.


## 3. Planning-Execution 루프

ReAct는 한 단계씩 생각하고 행동한다. 복잡한 작업에서는 이것만으로 부족할 때가 있다. 10단계짜리 작업을 하는데 3단계에서 잘못된 방향으로 빠지면, 나머지 7단계가 전부 낭비된다.

Planning-Execution은 이 문제를 해결한다. **먼저 전체 계획을 세우고, 계획대로 실행하되, 중간에 계획을 수정할 수 있다.**

### 3.1 구조

```
[Plan 단계]
1. 주문 DB에서 ORD-789 조회
2. 반품 가능 여부 확인 (구매일로부터 30일 이내인지)
3. 반품 가능하면 반품 접수 처리
4. 고객에게 반품 접수 완료 메일 발송

[Execute 단계 - Step 1]
Action: search_db(order_id="ORD-789")
Observation: {"order_date": "2026-02-01", "status": "배송완료"}

[Replan]
구매일이 2026-02-01이고 오늘이 2026-04-08이므로 30일이 지났다.
계획 수정: 반품 불가 사유를 고객에게 안내한다.
1. 고객에게 반품 기한 초과 안내 메일 발송
```

ReAct와 다른 점은, 전체 계획이 먼저 나오고, 실행 중간에 관찰 결과에 따라 계획을 바꿀 수 있다는 것이다.

### 3.2 구현

```python
import json
from openai import OpenAI

client = OpenAI()

def plan(messages: list, tools: list) -> list[str]:
    """LLM에게 계획을 세우게 한다. 단계별 목록을 반환한다."""
    plan_messages = messages + [
        {"role": "user", "content": (
            "위 요청을 처리하기 위한 단계별 계획을 JSON 배열로 작성해라. "
            "각 단계는 문자열이다. 예: [\"DB에서 주문 조회\", \"결과 확인\", \"메일 발송\"]"
        )}
    ]
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=plan_messages,
        response_format={"type": "json_object"}
    )
    content = json.loads(response.choices[0].message.content)
    return content.get("steps", content.get("plan", []))


def execute_step(step: str, messages: list, tools: list) -> dict:
    """한 단계를 실행한다. 도구 호출이 필요하면 처리한다."""
    messages.append({"role": "user", "content": f"다음 단계를 실행해라: {step}"})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools
    )
    message = response.choices[0].message
    messages.append(message)

    results = []
    if message.tool_calls:
        for tool_call in message.tool_calls:
            result = execute_tool(tool_call.function.name,
                                  json.loads(tool_call.function.arguments))
            results.append(result)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    return {"response": message.content, "tool_results": results}


def should_replan(step_result: dict, remaining_steps: list[str], messages: list) -> list[str] | None:
    """실행 결과를 보고 남은 계획을 수정할지 판단한다."""
    replan_messages = messages + [
        {"role": "user", "content": (
            f"방금 실행 결과를 확인했다. 남은 계획: {json.dumps(remaining_steps, ensure_ascii=False)}\n"
            "이 계획을 그대로 진행해도 되면 null을 반환해라. "
            "수정이 필요하면 새로운 단계 목록을 JSON 배열로 반환해라."
        )}
    ]
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=replan_messages,
        response_format={"type": "json_object"}
    )
    content = json.loads(response.choices[0].message.content)
    new_steps = content.get("steps")
    if new_steps and isinstance(new_steps, list):
        return new_steps
    return None


def run_plan_execute(user_message: str, tools: list, max_replans: int = 3) -> str:
    messages = [
        {"role": "system", "content": "너는 주문 관리 에이전트다."},
        {"role": "user", "content": user_message}
    ]

    steps = plan(messages, tools)
    replan_count = 0

    while steps:
        current_step = steps.pop(0)
        result = execute_step(current_step, messages, tools)

        if steps and replan_count < max_replans:
            new_steps = should_replan(result, steps, messages)
            if new_steps is not None:
                steps = new_steps
                replan_count += 1

    # 최종 응답 생성
    messages.append({"role": "user", "content": "모든 단계를 완료했다. 결과를 요약해라."})
    response = client.chat.completions.create(model="gpt-4o", messages=messages)
    return response.choices[0].message.content
```

### 3.3 ReAct vs Planning-Execution

| 상황 | ReAct | Planning-Execution |
|------|-------|-------------------|
| 단순 조회 + 응답 | 적합 | 과도함 |
| 3단계 이하 작업 | 적합 | 과도함 |
| 5단계 이상 복합 작업 | 방향을 잃기 쉬움 | 적합 |
| 중간 결과에 따라 분기가 많은 작업 | 가능하지만 비효율적 | 적합 |
| API 비용을 줄여야 할 때 | 유리 (LLM 호출 적음) | 불리 (Plan, Replan에 추가 호출) |

실무에서는 둘을 섞어 쓴다. 전체 흐름은 Planning-Execution으로 관리하고, 각 단계의 실행은 ReAct로 처리하는 방식이다.


## 4. 상태 관리와 메모리

에이전트가 루프를 돌면서 가장 먼저 부딪히는 문제가 메모리다. LLM의 컨텍스트 윈도우에는 한계가 있고, 에이전트가 10번, 20번 도구를 호출하면 이전 대화를 다 담을 수 없다.

### 4.1 컨텍스트 윈도우 관리

가장 흔한 실수는 모든 도구 호출 결과를 messages 배열에 그대로 쌓는 것이다. DB 조회 결과가 매번 수백 행이면 5번만 호출해도 컨텍스트가 가득 찬다.

```python
class ConversationMemory:
    """에이전트의 대화 메모리를 관리한다."""

    def __init__(self, max_tokens: int = 50000):
        self.messages: list[dict] = []
        self.max_tokens = max_tokens
        self.summaries: list[str] = []

    def add(self, message: dict):
        self.messages.append(message)
        self._maybe_compress()

    def _maybe_compress(self):
        """토큰 수가 한계에 가까워지면 오래된 메시지를 요약으로 압축한다."""
        estimated_tokens = sum(len(str(m.get("content", ""))) // 4 for m in self.messages)

        if estimated_tokens > self.max_tokens * 0.8:
            # 앞쪽 메시지를 요약으로 교체
            old_messages = self.messages[:len(self.messages) // 2]
            summary = self._summarize(old_messages)
            self.summaries.append(summary)
            self.messages = [
                {"role": "system", "content": f"이전 대화 요약: {summary}"}
            ] + self.messages[len(self.messages) // 2:]

    def _summarize(self, messages: list[dict]) -> str:
        """LLM을 사용해서 메시지를 요약한다. 실제 구현에서는 API 호출."""
        # 간단한 구현 - 프로덕션에서는 LLM API로 요약
        contents = [str(m.get("content", "")) for m in messages if m.get("role") != "system"]
        return f"[{len(contents)}개 메시지 요약] " + "; ".join(c[:100] for c in contents[:5])

    def get_messages(self) -> list[dict]:
        return self.messages.copy()
```

### 4.2 도구 결과 크기 제한

도구 실행 결과를 messages에 넣기 전에 크기를 제한해야 한다:

```python
def truncate_tool_result(result: str, max_chars: int = 2000) -> str:
    """도구 결과가 너무 길면 잘라낸다."""
    if len(result) <= max_chars:
        return result

    try:
        data = json.loads(result)
        if isinstance(data, list) and len(data) > 10:
            truncated = data[:10]
            return json.dumps(truncated, ensure_ascii=False) + f"\n... 외 {len(data) - 10}건"
    except (json.JSONDecodeError, TypeError):
        pass

    return result[:max_chars] + f"\n... (총 {len(result)}자 중 {max_chars}자만 표시)"
```

### 4.3 장기 메모리 (세션 간 지속)

단일 대화 내에서의 메모리와 세션 간 지속되는 메모리는 다른 문제다. 세션 간 메모리가 필요하면 외부 저장소를 써야 한다.

```python
import hashlib
from datetime import datetime


class AgentLongTermMemory:
    """벡터 DB 기반 장기 메모리. 세션이 끝나도 유지된다."""

    def __init__(self, vector_store):
        self.store = vector_store  # Chroma, Pinecone 등

    def save(self, content: str, metadata: dict | None = None):
        doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        self.store.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[{
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            }]
        )

    def recall(self, query: str, top_k: int = 5) -> list[str]:
        results = self.store.query(query_texts=[query], n_results=top_k)
        return results["documents"][0] if results["documents"] else []


# 에이전트 루프에서 사용
def run_agent_with_memory(user_message: str, memory: AgentLongTermMemory, **kwargs):
    # 관련 기억을 먼저 조회
    relevant_memories = memory.recall(user_message)
    context = "\n".join(f"- {m}" for m in relevant_memories)

    system_prompt = f"너는 주문 관리 에이전트다.\n\n과거 관련 정보:\n{context}" if context else "너는 주문 관리 에이전트다."

    # ... 에이전트 루프 실행 ...
    # 중요한 결과는 장기 메모리에 저장
    # memory.save("고객 kim@example.com은 반품을 자주 요청한다", {"type": "customer_pattern"})
```

벡터 DB를 쓰는 이유는 키워드 매칭이 아니라 의미 기반으로 관련 기억을 찾기 위해서다. "배송 지연 불만"이라는 기억이 "물건이 안 와요"라는 쿼리에도 매칭된다.


## 5. 에러 복구

에이전트가 프로덕션에서 돌아가려면 에러 복구가 필수다. API 호출 실패, 도구 실행 에러, LLM의 잘못된 판단 등 실패 지점이 많다.

### 5.1 도구 실행 실패 처리

도구가 실패했을 때 에이전트에게 에러 정보를 돌려주면, LLM이 스스로 대안을 찾는 경우가 있다.

```python
def safe_execute_tool(name: str, arguments: dict, max_retries: int = 2) -> str:
    """도구를 실행하되, 실패하면 재시도하고, 그래도 실패하면 에러 메시지를 반환한다."""
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            result = execute_tool(name, arguments)
            return result
        except TimeoutError:
            last_error = "도구 실행 시간 초과"
        except ConnectionError:
            last_error = "외부 서비스 연결 실패"
        except Exception as e:
            last_error = str(e)

    # 재시도 실패 - 에러 정보를 LLM에게 돌려준다
    return json.dumps({
        "error": True,
        "message": last_error,
        "tool": name,
        "suggestion": "다른 방법을 시도하거나 사용자에게 알려라"
    })
```

이 에러 메시지를 messages에 tool 역할로 넣으면, LLM이 "이 도구가 실패했으니 다른 방법을 쓰자"고 판단할 수 있다. 모든 에러를 LLM에게 맡기면 안 된다 — 인증 실패나 권한 문제 같은 건 에이전트가 아무리 재시도해도 해결 못한다. 이런 경우는 즉시 사용자에게 알려야 한다.

### 5.2 무한 루프 방지

LLM이 같은 행동을 반복하는 경우가 실제로 발생한다. 같은 파라미터로 같은 도구를 계속 호출하거나, 도구 호출과 포기를 번갈아 반복하는 패턴이다.

```python
def detect_loop(messages: list[dict], window: int = 6) -> bool:
    """최근 도구 호출 패턴이 반복되는지 탐지한다."""
    recent_calls = []
    for msg in messages[-window * 2:]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                recent_calls.append(f"{tc.function.name}:{tc.function.arguments}")

    if len(recent_calls) < 4:
        return False

    # 최근 2개 호출이 그 전 2개와 동일하면 루프
    if recent_calls[-2:] == recent_calls[-4:-2]:
        return True

    # 같은 호출이 3번 이상이면 루프
    from collections import Counter
    counts = Counter(recent_calls)
    return any(count >= 3 for count in counts.values())


def run_agent_safe(user_message: str, max_turns: int = 10, **kwargs) -> str:
    messages = [
        {"role": "system", "content": "너는 주문 관리 에이전트다."},
        {"role": "user", "content": user_message}
    ]

    for turn in range(max_turns):
        if detect_loop(messages):
            messages.append({
                "role": "user",
                "content": "같은 동작을 반복하고 있다. 다른 접근 방법을 시도하거나, 해결할 수 없으면 그 이유를 설명해라."
            })

        response = client.chat.completions.create(
            model="gpt-4o", messages=messages, tools=tools
        )
        # ... 나머지 루프 처리 ...
```

루프를 탐지하면 LLM에게 "반복하고 있다"고 알려주는 메시지를 주입한다. 이것만으로 LLM이 다른 접근을 시도하는 경우가 많다.

### 5.3 타임아웃과 비용 제어

에이전트 하나가 API 비용을 얼마나 쓸 수 있는지 제한하는 건 프로덕션에서 필수다.

```python
import time


class AgentBudget:
    """에이전트의 실행 시간과 API 호출 횟수를 제한한다."""

    def __init__(self, max_llm_calls: int = 20, max_tool_calls: int = 50, max_seconds: int = 300):
        self.max_llm_calls = max_llm_calls
        self.max_tool_calls = max_tool_calls
        self.max_seconds = max_seconds
        self.llm_calls = 0
        self.tool_calls = 0
        self.start_time = time.time()

    def check_llm_call(self):
        self.llm_calls += 1
        if self.llm_calls > self.max_llm_calls:
            raise BudgetExceededError(f"LLM 호출 {self.max_llm_calls}회 초과")

    def check_tool_call(self):
        self.tool_calls += 1
        if self.tool_calls > self.max_tool_calls:
            raise BudgetExceededError(f"도구 호출 {self.max_tool_calls}회 초과")

    def check_time(self):
        elapsed = time.time() - self.start_time
        if elapsed > self.max_seconds:
            raise BudgetExceededError(f"실행 시간 {self.max_seconds}초 초과")


class BudgetExceededError(Exception):
    pass
```

max_turns만으로는 부족하다. 한 턴에서 도구를 5개 병렬 호출할 수도 있고, 하나의 도구가 10초 걸릴 수도 있다. 시간, LLM 호출 횟수, 도구 호출 횟수를 각각 제한해야 한다.


## 6. 멀티 에이전트 오케스트레이션

하나의 에이전트로 모든 걸 처리하려고 하면 시스템 프롬프트가 비대해지고, 도구가 수십 개가 되면서 LLM의 판단 정확도가 떨어진다. 역할별로 에이전트를 나누고, 오케스트레이터가 조율하는 방식이 멀티 에이전트다.

### 6.1 라우터 패턴

가장 단순한 형태다. 사용자 요청을 분류해서 전문 에이전트에게 넘긴다.

```python
class RouterAgent:
    """사용자 요청을 적절한 전문 에이전트에게 라우팅한다."""

    def __init__(self):
        self.agents = {
            "order": OrderAgent(),      # 주문 조회/변경
            "refund": RefundAgent(),     # 환불/반품
            "shipping": ShippingAgent(), # 배송 추적
        }

    def route(self, user_message: str) -> str:
        # LLM으로 의도 분류
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": (
                    "사용자 메시지를 분류해라. "
                    "order, refund, shipping 중 하나를 JSON으로 반환해라. "
                    '예: {"category": "order"}'
                )},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}
        )
        category = json.loads(response.choices[0].message.content)["category"]

        agent = self.agents.get(category)
        if not agent:
            return "처리할 수 없는 요청입니다."

        return agent.run(user_message)
```

라우터 패턴의 한계는 요청이 여러 카테고리에 걸칠 때다. "주문 취소하고 환불해줘"는 order와 refund 둘 다에 해당한다. 이런 경우 오케스트레이터 패턴이 필요하다.

### 6.2 오케스트레이터 패턴

오케스트레이터가 전체 작업을 계획하고, 하위 에이전트에게 단계별로 위임한다.

```python
class OrchestratorAgent:
    """하위 에이전트들을 조율해서 복합 작업을 처리한다."""

    def __init__(self):
        self.sub_agents = {
            "order": OrderAgent(),
            "refund": RefundAgent(),
            "notification": NotificationAgent(),
        }

    def run(self, user_message: str) -> str:
        # 1단계: 작업 분해
        plan = self._decompose(user_message)

        # 2단계: 순서대로 실행
        results = {}
        for step in plan:
            agent_name = step["agent"]
            task = step["task"]

            # 이전 단계 결과를 컨텍스트로 전달
            context = json.dumps(results, ensure_ascii=False) if results else ""
            agent = self.sub_agents[agent_name]
            result = agent.run(task, context=context)
            results[step["id"]] = result

        # 3단계: 결과 종합
        return self._summarize(user_message, results)

    def _decompose(self, user_message: str) -> list[dict]:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": (
                    "사용자 요청을 하위 작업으로 분해해라. "
                    "사용 가능한 에이전트: order, refund, notification. "
                    "JSON 배열로 반환해라. "
                    '예: [{"id": "step1", "agent": "order", "task": "주문 ORD-123 조회"}]'
                )},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}
        )
        content = json.loads(response.choices[0].message.content)
        return content.get("steps", [])

    def _summarize(self, original_request: str, results: dict) -> str:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "하위 작업들의 결과를 종합해서 사용자에게 답변해라."},
                {"role": "user", "content": f"원래 요청: {original_request}\n결과: {json.dumps(results, ensure_ascii=False)}"}
            ]
        )
        return response.choices[0].message.content
```

### 6.3 에이전트 간 통신에서 주의할 점

**하위 에이전트의 결과를 그대로 오케스트레이터에 올리지 마라.** 하위 에이전트가 10번 도구를 호출한 전체 과정을 오케스트레이터에 넘기면 컨텍스트가 폭발한다. 하위 에이전트는 최종 결과만 요약해서 반환해야 한다.

**하위 에이전트끼리 직접 통신하면 디버깅이 불가능해진다.** 모든 통신은 오케스트레이터를 거치게 해야 한다. 에이전트 A가 에이전트 B에게 직접 뭔가를 요청하는 구조는 실행 흐름 추적이 안 된다.

**하위 에이전트별로 별도의 비용 제한을 걸어야 한다.** 오케스트레이터 전체에 100회 제한을 걸어도, 하위 에이전트 하나가 80회를 다 쓰면 나머지 작업을 처리할 수 없다. AgentBudget을 에이전트별로 따로 할당한다.


## 7. 프로덕션 적용 시 고려사항

### 7.1 관찰 가능성 (Observability)

에이전트는 결정론적이지 않다. 같은 입력에 다른 경로로 실행될 수 있다. 디버깅하려면 전체 실행 과정을 추적할 수 있어야 한다.

```python
import logging
import uuid

logger = logging.getLogger("agent")


class AgentTracer:
    """에이전트 실행 과정을 추적한다."""

    def __init__(self):
        self.trace_id = str(uuid.uuid4())[:8]
        self.events: list[dict] = []

    def log_llm_call(self, messages_count: int, response_type: str):
        event = {
            "trace_id": self.trace_id,
            "type": "llm_call",
            "messages_count": messages_count,
            "response_type": response_type,  # "text" or "tool_calls"
            "timestamp": datetime.now().isoformat()
        }
        self.events.append(event)
        logger.info(f"[{self.trace_id}] LLM call #{len(self.events)}: {response_type}")

    def log_tool_call(self, tool_name: str, arguments: dict, result: str, success: bool):
        event = {
            "trace_id": self.trace_id,
            "type": "tool_call",
            "tool": tool_name,
            "arguments": arguments,
            "result_length": len(result),
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        self.events.append(event)
        logger.info(f"[{self.trace_id}] Tool: {tool_name}, success={success}")

    def get_summary(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "total_events": len(self.events),
            "llm_calls": sum(1 for e in self.events if e["type"] == "llm_call"),
            "tool_calls": sum(1 for e in self.events if e["type"] == "tool_call"),
            "failed_tools": sum(1 for e in self.events if e["type"] == "tool_call" and not e["success"])
        }
```

LangSmith, Arize, Langfuse 같은 LLM 관찰 도구를 쓰면 이 추적을 시각적으로 볼 수 있다. 직접 구현할 거면 최소한 trace_id, 각 단계의 입출력, 소요 시간은 남겨야 한다.

### 7.2 테스트

에이전트 테스트는 일반적인 유닛 테스트와 다르다. LLM 응답이 매번 다르기 때문에 결정론적인 검증이 불가능하다.

현실적으로 가능한 접근법:

- **도구 레벨 테스트**: 각 도구 함수는 결정론적이다. 입력에 대해 기대하는 출력이 나오는지 일반 유닛 테스트로 검증한다.
- **LLM 호출 모킹**: 에이전트 루프를 테스트할 때는 LLM 응답을 고정해서 루프 로직만 검증한다. "이 도구 호출이 실패하면 에이전트가 재시도하는가?"를 확인하는 식이다.
- **시나리오 테스트 (end-to-end)**: 실제 LLM을 호출해서 시나리오가 완료되는지 확인한다. "주문 조회 후 메일 발송"이 의도대로 수행되는지를 결과의 조건으로 검증한다. 결과가 정확한 텍스트 매칭이 아니라 "메일이 발송됐는지" 같은 조건이어야 한다.

### 7.3 에이전트 프레임워크

직접 구현하지 않고 프레임워크를 쓰는 선택지도 있다.

| 프레임워크 | 특징 | 쓸 만한 상황 |
|-----------|------|-------------|
| LangGraph | 상태 머신 기반, 복잡한 분기 처리 | 에이전트 흐름이 그래프로 표현될 때 |
| CrewAI | 역할 기반 멀티 에이전트 | 빠르게 프로토타입 만들 때 |
| Anthropic Agent SDK | Claude 특화, 핸드오프 패턴 지원 | Claude API 기반 에이전트 |
| OpenAI Agents SDK | OpenAI 특화, 가드레일 내장 | OpenAI API 기반 에이전트 |
| AutoGen | 마이크로소프트, 대화형 멀티 에이전트 | 에이전트 간 협업 시나리오 |

프레임워크를 쓰면 에이전트 루프, 메모리 관리, 도구 연결 같은 보일러플레이트를 줄일 수 있다. 다만 프레임워크의 추상화가 디버깅을 어렵게 만드는 경우가 있다. 에이전트가 예상대로 동작하지 않을 때 프레임워크 내부를 파고들어야 하는 상황이 생긴다. 에이전트의 핵심 루프는 어차피 수십 줄이므로, 요구사항이 단순하면 직접 구현하는 게 나을 수 있다.
