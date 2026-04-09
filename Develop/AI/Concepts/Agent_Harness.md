---
title: Agent Harness — 에이전트 런타임의 구조와 동작
tags: [ai, agent, harness, runtime, sandbox, tool-dispatch]
updated: 2026-04-09
---

# Agent Harness — 에이전트 런타임의 구조와 동작

## 1. 하네스가 뭔지

LLM 에이전트를 "루프 돌리면 에이전트"라고 설명하는 글이 많다. 맞는 말이지만, 실제로 프로덕션에서 에이전트를 돌리려면 그 루프를 감싸는 런타임이 필요하다. 이 런타임을 **하네스(Harness)**라고 부른다.

하네스는 에이전트의 실행 환경 전체를 가리킨다. LLM에게 "다음에 뭘 할지" 물어보고, 응답에서 도구 호출을 파싱하고, 실제로 도구를 실행하고, 결과를 다시 LLM에게 돌려주는 일련의 과정을 관리한다. 여기에 권한 검사, 샌드박싱, 토큰 예산 관리, 에러 처리까지 포함된다.

비유하자면 이렇다:

- LLM = 판단을 내리는 두뇌
- 도구 = 두뇌가 사용하는 손과 발
- **하네스 = 두뇌와 손발을 연결하고, 안전하게 작동하게 만드는 신경계와 골격**

에이전트 프레임워크(LangChain, CrewAI 등)를 쓰든, Claude Code처럼 CLI로 돌리든, 내부에는 반드시 하네스가 존재한다. 프레임워크가 하네스를 추상화해줄 뿐이다.


## 2. 하네스 내부 구조

하네스는 크게 다섯 개의 컴포넌트로 구성된다.

```
┌─────────────────────────────────────────────────┐
│                  Agent Harness                   │
│                                                  │
│  ┌───────────┐    ┌──────────────┐               │
│  │ Agent Loop │───▶│ Tool         │               │
│  │ (상태 머신) │◀───│ Dispatcher   │               │
│  └─────┬─────┘    └──────┬───────┘               │
│        │                 │                        │
│        ▼                 ▼                        │
│  ┌───────────┐    ┌──────────────┐               │
│  │ State      │    │ Permission   │               │
│  │ Manager    │    │ Gate         │               │
│  └───────────┘    └──────┬───────┘               │
│                          │                        │
│                    ┌─────▼────────┐               │
│                    │  Sandbox     │               │
│                    │  (실행 격리)  │               │
│                    └──────────────┘               │
└─────────────────────────────────────────────────┘
```

### 2.1 에이전트 루프 (Agent Loop)

하네스의 핵심이다. 아래 사이클을 반복한다:

1. 현재 메시지 히스토리를 LLM에 보낸다
2. LLM 응답을 받는다
3. 응답에 도구 호출이 있으면 → Tool Dispatcher로 넘긴다
4. 도구 실행 결과를 메시지 히스토리에 추가한다
5. 종료 조건을 확인한다 (도구 호출 없음, 토큰 한도 초과, 최대 반복 횟수 도달 등)
6. 종료 조건 미충족 시 1번으로 돌아간다

종료 조건이 없으면 에이전트가 영원히 돌아간다. 실제로 이게 가장 흔한 사고다. 에이전트가 "할 일을 찾아서" 무한히 도구를 호출하는 상황이 생긴다.

```python
# 에이전트 루프의 골격 (의사 코드)
def agent_loop(messages, tools, max_turns=50):
    for turn in range(max_turns):
        response = llm.chat(messages, tools=tools)

        # 텍스트만 반환했으면 종료
        if not response.tool_calls:
            return response.content

        # 도구 호출 처리
        for call in response.tool_calls:
            result = tool_dispatcher.execute(call)
            messages.append({"role": "tool", "content": result, "tool_call_id": call.id})

        messages.append({"role": "assistant", "content": response.content})

    raise MaxTurnsExceeded(f"{max_turns}턴 초과")
```

이 코드에서 `max_turns`를 빼면 무한 루프다. 단순해 보이지만, 실제 하네스는 이 루프 안에서 권한 확인, 토큰 카운팅, 에러 핸들링, 사용자 인터럽트 처리를 전부 해야 한다.


### 2.2 도구 디스패처 (Tool Dispatcher)

LLM이 `{"name": "read_file", "arguments": {"path": "/etc/passwd"}}` 같은 도구 호출을 반환하면, 디스패처가 이걸 실제 함수 호출로 변환한다.

디스패처가 처리하는 것들:

- **이름 매핑**: LLM이 반환한 도구 이름을 실제 구현체와 매핑
- **인자 검증**: JSON Schema 기반으로 인자 타입/필수값 검증
- **실행**: 실제 함수 호출, 외부 API 호출, 쉘 명령 실행 등
- **결과 직렬화**: 실행 결과를 LLM이 읽을 수 있는 문자열로 변환
- **타임아웃 처리**: 도구 실행이 일정 시간 초과하면 강제 종료

디스패처 없이 에이전트를 만들면 `eval()`이나 `exec()` 같은 걸 쓰게 되는데, 이건 보안 사고의 시작이다.


### 2.3 권한 게이트 (Permission Gate)

에이전트에게 파일 시스템 접근, 쉘 명령 실행, 네트워크 요청 같은 권한을 무제한으로 주면 안 된다. 권한 게이트는 도구 호출을 실행하기 전에 "이 동작을 허용할지" 판단한다.

권한 모델의 종류:

| 모델 | 동작 방식 | 예시 |
|------|----------|------|
| Allowlist | 허용된 도구만 실행 | Read, Glob만 허용 |
| Ask-on-use | 실행 전에 사용자에게 확인 | "bash rm -rf를 실행할까요?" |
| Rule-based | 조건부 허용 | 현재 디렉토리 내 파일만 읽기 허용 |
| Capability-based | 토큰 기반 권한 위임 | OAuth 스코프처럼 세분화된 권한 |

Claude Code의 경우 Ask-on-use 모델을 기본으로 쓴다. Bash 명령이나 파일 수정 같은 위험한 동작은 사용자 승인을 받는다. 설정에서 특정 패턴을 자동 허용할 수도 있다.


### 2.4 샌드박스 (Sandbox)

도구가 실제로 실행되는 격리 환경이다. 에이전트가 `rm -rf /`를 실행하려고 해도, 샌드박싱이 되어 있으면 호스트 시스템에 영향을 주지 않는다.

샌드박싱 방식은 하네스마다 다르다:

- **컨테이너 격리**: Docker 컨테이너 안에서 실행. Codex가 이 방식을 쓴다. 네트워크도 차단할 수 있다.
- **파일 시스템 격리**: 특정 디렉토리만 접근 가능. chroot나 mount namespace 사용.
- **프로세스 격리**: 별도 프로세스에서 실행하고, 시스템 콜을 제한 (seccomp, AppArmor).
- **언어 레벨 격리**: Python의 `RestrictedPython` 같은 런타임 내 제한. 우회가 쉬워서 신뢰도가 낮다.

샌드박싱 없이 에이전트를 돌리는 건, root 권한으로 인터넷에서 받은 스크립트를 실행하는 것과 비슷하다. LLM은 확률 모델이라 예상 못한 동작을 할 수 있고, 프롬프트 인젝션으로 조작될 수도 있다.


### 2.5 상태 머신 (State Machine)

에이전트 루프가 단순 while문이 아닌 이유는, 에이전트가 여러 상태를 가지기 때문이다.

```
IDLE → THINKING → TOOL_CALLING → TOOL_EXECUTING → PROCESSING_RESULT
  ↑                                                        │
  └───────────── (종료 조건 충족) ◀────────────────────────┘
                                                           │
  ERROR ◀──────────────────────────────────────────────────┘
```

각 상태에서 다른 이벤트를 처리해야 한다:

- **IDLE**: 사용자 입력 대기. 새로운 메시지가 오면 THINKING으로 전환.
- **THINKING**: LLM API 호출 중. 스트리밍 응답 처리, 취소 요청 감지.
- **TOOL_CALLING**: LLM이 도구 호출을 반환함. 권한 확인 후 TOOL_EXECUTING으로.
- **TOOL_EXECUTING**: 도구 실행 중. 타임아웃 감시, 결과 수집.
- **PROCESSING_RESULT**: 도구 결과를 메시지에 추가. 종료 조건 확인 후 THINKING 또는 IDLE로.
- **ERROR**: 에러 발생. 재시도할지, 사용자에게 알릴지, 루프를 중단할지 결정.

상태 머신을 제대로 구현하지 않으면, 에이전트가 도구 실행 도중 사용자가 취소를 눌렀을 때 어떻게 해야 하는지 같은 문제를 처리할 수 없다.


## 3. 주요 도구별 하네스 비교

Claude Code, Codex, Cursor, Copilot은 각각 다른 방식으로 하네스를 구현한다. 같은 "AI 코딩 도구"지만 런타임 설계 철학이 상당히 다르다.

### 3.1 비교 테이블

| 항목 | Claude Code | Codex | Cursor | GitHub Copilot |
|------|------------|-------|--------|----------------|
| 실행 환경 | 로컬 터미널 (Node.js) | 로컬 + Docker 샌드박스 | VS Code 확장 (Electron) | VS Code/JetBrains 확장 |
| 샌드박싱 | 권한 게이트 (Ask-on-use) | 컨테이너 격리 (네트워크 차단) | 에디터 프로세스 내 | 에디터 프로세스 내 |
| 도구 확장 | MCP 서버로 커스텀 도구 추가 | 제한적 (CLI 도구 위주) | 커스텀 도구 제한적 | Extensions + MCP |
| 에이전트 루프 | 멀티턴, 사용자 인터럽트 지원 | 단일 태스크 실행 후 diff 반환 | 멀티턴, 에디터 내 | Copilot Chat 기반 멀티턴 |
| 상태 관리 | 대화 히스토리 + 컨텍스트 압축 | 태스크 단위 (상태 비유지) | 에디터 세션 기반 | 에디터 세션 기반 |
| 권한 모델 | 3단계 (자동/확인/거부) | 샌드박스로 격리 | 에디터 내 파일 접근만 | 에디터 내 파일 접근만 |

### 3.2 설계 차이가 만드는 실질적 차이

**Claude Code**는 터미널에서 돌아가기 때문에 사용자의 쉘 환경 전체에 접근한다. git, docker, npm 같은 시스템 도구를 그대로 쓸 수 있다. 대신 샌드박싱이 약하기 때문에 권한 게이트에 의존한다. 위험한 명령을 실행하기 전에 사용자에게 물어본다.

**Codex**는 반대 접근이다. Docker 컨테이너 안에서 코드를 실행하고, 네트워크를 차단한다. 에이전트가 뭘 하든 호스트 시스템에 영향을 줄 수 없다. 권한을 물어볼 필요 없이, 격리 환경에서 자유롭게 실행하고 결과(diff)만 꺼내오는 방식이다.

**Cursor**는 에디터 안에 하네스가 내장되어 있다. 에디터가 열고 있는 파일만 대상으로 동작하기 때문에 별도 샌드박싱 없이도 범위가 제한된다. 에디터의 Language Server Protocol(LSP)을 도구처럼 활용해서 코드 분석, 리팩토링 같은 작업을 수행한다.

**GitHub Copilot**은 자동완성에서 시작해서 에이전트 모드를 추가한 케이스다. Copilot Chat과 Copilot Agent Mode가 별도의 하네스로 동작한다. Agent Mode에서는 터미널 명령 실행, 파일 편집 같은 도구를 사용하지만, VS Code의 Extension API를 통해 접근 범위가 제한된다.


## 4. 커스텀 에이전트를 하네스 위에 올리기

Anthropic의 Claude API를 사용해서 직접 하네스를 구현하는 예제다. 파일을 읽고 수정하는 간단한 코딩 에이전트를 만든다.

```python
import anthropic
import json
from pathlib import Path

client = anthropic.Anthropic()

# 도구 정의
tools = [
    {
        "name": "read_file",
        "description": "파일 내용을 읽는다",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "읽을 파일 경로"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "파일에 내용을 쓴다",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "쓸 파일 경로"},
                "content": {"type": "string", "description": "파일 내용"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_files",
        "description": "디렉토리의 파일 목록을 반환한다",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "대상 디렉토리"}
            },
            "required": ["directory"]
        }
    }
]

# 도구 디스패처
ALLOWED_BASE = Path("/workspace")  # 허용된 디렉토리

def execute_tool(name: str, arguments: dict) -> str:
    """도구 실행. 경로 검증 포함."""
    if name == "read_file":
        path = Path(arguments["path"]).resolve()
        if not path.is_relative_to(ALLOWED_BASE):
            return f"ERROR: {path}는 허용된 경로 밖이다"
        if not path.exists():
            return f"ERROR: {path} 파일이 없다"
        return path.read_text()

    elif name == "write_file":
        path = Path(arguments["path"]).resolve()
        if not path.is_relative_to(ALLOWED_BASE):
            return f"ERROR: {path}는 허용된 경로 밖이다"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(arguments["content"])
        return f"OK: {path}에 작성 완료"

    elif name == "list_files":
        path = Path(arguments["directory"]).resolve()
        if not path.is_relative_to(ALLOWED_BASE):
            return f"ERROR: {path}는 허용된 경로 밖이다"
        files = [str(f.relative_to(path)) for f in path.rglob("*") if f.is_file()]
        return "\n".join(files[:100])  # 최대 100개

    return f"ERROR: 알 수 없는 도구 {name}"


# 에이전트 루프
def run_agent(task: str, max_turns: int = 30):
    messages = [{"role": "user", "content": task}]
    token_usage = 0
    token_budget = 100_000

    for turn in range(max_turns):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system="파일을 읽고 수정하는 코딩 에이전트다. 작업이 끝나면 도구 호출 없이 결과를 텍스트로 보고한다.",
            tools=tools,
            messages=messages,
        )

        # 토큰 예산 확인
        token_usage += response.usage.input_tokens + response.usage.output_tokens
        if token_usage > token_budget:
            print(f"[하네스] 토큰 예산 초과: {token_usage}/{token_budget}")
            break

        # 종료 조건: stop_reason이 "end_turn"이면 LLM이 도구 호출 없이 응답한 것
        if response.stop_reason == "end_turn":
            text_blocks = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_blocks)

        # 도구 호출 처리
        assistant_content = response.content
        tool_results = []

        for block in assistant_content:
            if block.type == "tool_use":
                print(f"[하네스] 도구 호출: {block.name}({json.dumps(block.input, ensure_ascii=False)[:200]})")
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result[:10_000],  # 결과 길이 제한
                })

        messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_results})

    return "[하네스] 최대 턴 수 도달, 작업 중단"


# 실행
result = run_agent("src/main.py 파일을 읽고, 함수 이름을 snake_case로 변경해줘")
print(result)
```

이 코드에서 하네스 컴포넌트가 어디에 있는지 보면:

- **에이전트 루프**: `run_agent()` 함수의 for 루프
- **도구 디스패처**: `execute_tool()` 함수
- **권한 게이트**: `is_relative_to(ALLOWED_BASE)` 경로 검증
- **토큰 예산**: `token_usage > token_budget` 확인
- **종료 조건**: `max_turns`, `stop_reason == "end_turn"`, 토큰 예산 초과

프로덕션에서 쓰려면 여기에 비동기 처리, 에러 재시도, 로깅, 사용자 인터럽트 처리를 추가해야 한다.


## 5. 하네스 설계 시 주의사항

### 5.1 무한 루프 방지

에이전트가 무한 루프에 빠지는 패턴은 정해져 있다:

**같은 도구를 같은 인자로 반복 호출하는 경우.** LLM이 도구 결과를 제대로 해석하지 못하고 같은 호출을 반복한다. 최근 N개의 도구 호출을 기록해두고, 동일한 호출이 3회 이상 반복되면 루프를 중단한다.

```python
recent_calls = []

def detect_loop(call_name, call_args, window=5, threshold=3):
    recent_calls.append((call_name, json.dumps(call_args, sort_keys=True)))
    if len(recent_calls) > window:
        recent_calls.pop(0)

    # 같은 호출이 threshold번 이상이면 루프
    from collections import Counter
    counts = Counter(recent_calls)
    for key, count in counts.items():
        if count >= threshold:
            return True
    return False
```

**"할 일을 찾아서" 스스로 작업을 만들어내는 경우.** 시스템 프롬프트에 "작업이 끝나면 반드시 종료하라"는 지시를 넣어야 한다. 시스템 프롬프트 없이 에이전트를 돌리면, LLM이 "추가로 개선할 점이 있으니 계속 작업하겠습니다"라며 끝없이 돌아가는 경우가 있다.

**에러가 발생했는데 계속 재시도하는 경우.** 같은 에러가 연속으로 발생하면 재시도를 멈추고 사용자에게 보고해야 한다.


### 5.2 토큰 예산 관리

에이전트가 루프를 돌 때마다 메시지 히스토리가 길어진다. 도구 결과가 크면 (파일 전체 내용, 긴 명령 출력 등) 순식간에 컨텍스트 윈도우를 채운다.

관리 방법:

- **도구 결과 잘라내기**: 결과가 일정 길이를 초과하면 잘라낸다. "결과가 10000자를 초과하여 잘렸습니다"라는 메시지를 붙인다.
- **컨텍스트 압축**: 오래된 메시지를 요약해서 짧게 줄인다. Claude Code가 이 방식을 쓴다.
- **슬라이딩 윈도우**: 최근 N개의 메시지만 유지하고 나머지는 버린다. 단순하지만 중요한 맥락을 잃을 수 있다.
- **토큰 카운팅**: 매 턴마다 사용량을 추적하고, 예산을 초과하면 에이전트를 중단한다. API 비용이 직접 발생하기 때문에 예산 없이 돌리면 안 된다.

비용 사고 사례: max_turns를 넉넉하게 잡고, 토큰 예산 없이 에이전트를 돌렸더니 하룻밤 사이에 API 비용이 수백 달러 나온 경우가 실제로 있다.


### 5.3 에러 전파

에이전트 루프 안에서 에러가 발생했을 때 어떻게 처리할지 결정해야 한다. 크게 세 가지 접근이 있다.

**에러를 LLM에게 돌려주기.** 도구 실행이 실패하면 에러 메시지를 tool result로 반환한다. LLM이 에러를 보고 다른 방법을 시도할 수 있다. 대부분의 하네스가 이 방식을 기본으로 쓴다.

```python
try:
    result = execute_tool(call.name, call.input)
except Exception as e:
    result = f"ERROR: {type(e).__name__}: {str(e)}"
```

**에러를 삼키고 재시도.** 네트워크 타임아웃 같은 일시적 에러는 LLM에게 보여줄 필요 없이 재시도한다. 단, 재시도 횟수를 제한해야 한다.

**에러를 상위로 전파해서 루프를 중단.** 인증 실패, 권한 부족 같은 복구 불가능한 에러는 루프를 멈추고 사용자에게 알려야 한다. LLM에게 돌려줘봐야 해결할 수 없는 문제다.

이 세 가지를 에러 종류별로 구분해서 적용한다. 모든 에러를 LLM에게 돌려주면, LLM이 같은 에러를 반복하면서 토큰을 낭비한다. 모든 에러에서 루프를 중단하면, 사소한 문제에도 작업이 멈춘다.


### 5.4 멀티 에이전트 환경에서의 하네스

에이전트가 다른 에이전트를 생성하는 구조에서는 하네스가 더 복잡해진다.

- 부모 에이전트의 토큰 예산을 자식 에이전트가 공유할지, 별도로 관리할지
- 자식 에이전트의 권한 범위를 부모보다 좁게 제한할지
- 자식 에이전트의 에러가 부모 루프에 어떻게 전파되는지
- 자식 에이전트의 결과를 어떤 형태로 부모에게 돌려줄지

Claude Code의 경우, Agent 도구로 서브 에이전트를 생성할 수 있다. 서브 에이전트는 부모와 독립적인 컨텍스트를 가지지만, 같은 파일 시스템에서 동작한다. worktree 격리 옵션을 사용하면 git worktree를 분리해서 파일 충돌을 방지한다.


## 6. 정리

하네스는 "LLM 호출 루프"가 아니라, 에이전트를 안전하고 예측 가능하게 실행하기 위한 런타임 시스템이다. 에이전트를 만들 때 LLM의 성능에만 집중하고 하네스 설계를 대충 하면, 무한 루프, 비용 폭발, 보안 사고가 발생한다.

직접 하네스를 구현할 때 가장 먼저 고려할 것:

1. 종료 조건을 먼저 정한다. max_turns, 토큰 예산, 타임아웃 중 하나라도 빠지면 안 된다.
2. 도구 실행을 격리한다. 최소한 경로 검증이라도 넣는다.
3. 에러 종류별 처리를 구분한다. 재시도 가능한 에러와 불가능한 에러를 나눈다.
4. 도구 결과 크기를 제한한다. 컨텍스트 윈도우를 도구 결과 하나가 다 채우면 에이전트가 멈춘다.

프레임워크를 쓰면 이런 것들이 기본으로 처리되지만, 내부에서 무슨 일이 일어나는지 모르고 쓰면 문제가 생겼을 때 원인을 찾을 수 없다.
