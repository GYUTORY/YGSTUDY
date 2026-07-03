---
title: Agent Harness — Claude Code 하네스로 보는 에이전트 런타임
tags: [ai, agent, harness, claude-code, runtime, hooks, session]
updated: 2026-06-06
---

# Agent Harness — Claude Code 하네스로 보는 에이전트 런타임

## 1. 하네스가 뭔지

LLM 에이전트를 "루프 돌리면 에이전트"라고 설명하는 글이 많다. 맞는 말이지만, 실제로 프로덕션에서 돌리려면 그 루프를 감싸는 런타임이 필요하다. 이 런타임을 **하네스(Harness)**라고 부른다.

하네스는 에이전트의 실행 환경 전체다. LLM에게 "다음에 뭘 할지" 물어보고, 응답에서 도구 호출을 파싱하고, 실제로 도구를 실행하고, 결과를 다시 LLM에게 돌려주는 일련의 과정을 관리한다. 여기에 권한 검사, 컨텍스트 압축, 후크 실행, 세션 저장까지 포함된다.

비유하자면 이렇다:

- LLM = 판단을 내리는 두뇌
- 도구 = 두뇌가 사용하는 손과 발
- **하네스 = 두뇌와 손발을 연결하고, 안전하게 작동하게 만드는 신경계와 골격**

에이전트 프레임워크(LangChain, CrewAI 등)를 쓰든, Claude Code처럼 CLI로 돌리든, 내부에는 반드시 하네스가 존재한다. 프레임워크가 하네스를 추상화해줄 뿐이다.

이 문서는 Claude Code의 하네스 구조를 사례로 잡고 다섯 가지 핵심 책임을 다룬다. 컨텍스트 관리, 도구 라우팅, 권한 모델, 후크 시스템, 세션 영속화. 모두 직접 에이전트를 만들 때 한 번씩은 막히는 지점들이다.


## 2. 하네스의 다섯 가지 책임

```
┌──────────────────────────────────────────────────────────────┐
│                       Agent Harness                          │
│                                                              │
│   ┌────────────┐         ┌───────────────┐                   │
│   │ Context    │◀───────▶│ Agent Loop    │                   │
│   │ Manager    │         │ (LLM 호출)    │                   │
│   └────────────┘         └───────┬───────┘                   │
│         ▲                        │                            │
│         │                        ▼                            │
│   ┌─────┴──────┐         ┌───────────────┐                   │
│   │ Session    │         │ Tool Router   │                   │
│   │ Store      │         └───────┬───────┘                   │
│   └────────────┘                 │                            │
│         ▲                        ▼                            │
│         │                ┌───────────────┐                    │
│         │                │ Permission    │                    │
│         │                │ Gate          │                    │
│         │                └───────┬───────┘                    │
│         │                        │                            │
│         │                        ▼                            │
│         │                ┌───────────────┐                    │
│         └────────────────│ Hook Runner   │                    │
│                          └───────┬───────┘                    │
│                                  │                            │
│                                  ▼                            │
│                          ┌───────────────┐                    │
│                          │ Tool Execution│                    │
│                          └───────────────┘                    │
└──────────────────────────────────────────────────────────────┘
```

각 컴포넌트가 처리하는 일:

- **Agent Loop**: LLM 호출과 응답 파싱. 종료 조건 판정.
- **Context Manager**: 메시지 히스토리, 시스템 프롬프트, 자동 압축, 인젝션된 리마인더 관리.
- **Tool Router**: 도구 이름을 실행 가능한 함수로 매핑. 동적 로딩 처리.
- **Permission Gate**: 도구 실행 직전에 허용 여부 판단. 사용자 확인이 필요한 경우 인터럽트.
- **Hook Runner**: 사전/사후 정의된 셸 명령을 이벤트에 맞춰 실행.
- **Session Store**: 대화 전체를 디스크에 직렬화. 재개 가능하게 보존.

뒤쪽 절에서 각 컴포넌트를 Claude Code 사례로 깊게 다룬다.


## 3. 에이전트 루프의 골격

루프 자체는 단순하다. 의사 코드로 적으면 이렇다.

```python
def agent_loop(messages, tools, max_turns=50):
    for turn in range(max_turns):
        response = llm.chat(messages, tools=tools)

        if not response.tool_calls:
            return response.content

        for call in response.tool_calls:
            result = tool_dispatcher.execute(call)
            messages.append({"role": "tool", "content": result, "tool_call_id": call.id})

        messages.append({"role": "assistant", "content": response.content})

    raise MaxTurnsExceeded(f"{max_turns}턴 초과")
```

`max_turns`를 빼면 무한 루프다. 종료 조건이 없으면 에이전트가 "할 일을 찾아서" 영원히 도구를 호출한다. 실제로 가장 흔한 사고다. 시스템 프롬프트에 "작업이 끝나면 도구 호출 없이 텍스트로만 답하라"는 지시를 명시하지 않으면, LLM이 "추가로 개선할 점이 있으니 계속 작업하겠습니다"라면서 무한히 돌아간다.

하네스에서 루프를 멈추는 조건은 보통 네 개가 함께 들어간다:

- `stop_reason == "end_turn"`: LLM이 도구 호출 없이 응답함
- `max_turns` 초과
- 토큰 예산 초과
- 사용자 인터럽트 (Ctrl+C, ESC)

Claude Code는 여기에 더해 "같은 도구를 같은 인자로 N회 반복" 같은 휴리스틱 루프 감지도 들어간다. 무한 반복이 의심되면 사용자에게 멈출지 물어본다.


## 4. 컨텍스트 관리

LLM은 매 호출마다 메시지 히스토리 전체를 다시 받는다. 루프를 돌수록 히스토리가 누적되고, 도구 결과가 크면(파일 전체 내용, 긴 명령 출력) 순식간에 컨텍스트 윈도우를 채운다. 컨텍스트 관리는 이 누적을 통제하는 일이다.

### 4.1 메시지 히스토리의 구조

Claude Code 기준 메시지 히스토리는 대략 이렇게 생겼다.

```
[1] system          : 하네스의 마스터 프롬프트 + 환경 정보 + CLAUDE.md
[2] user            : 사용자 첫 메시지
[3] assistant       : LLM 응답 (text + tool_use 블록)
[4] user            : tool_result 블록들
[5] assistant       : LLM 다음 응답
...
[N] system-reminder : 컨텍스트에 인젝션된 리마인더 (도구 가용성, 모드 알림 등)
```

`system-reminder`는 일반 메시지처럼 보이지만 실제로는 하네스가 동적으로 끼워넣는 내용이다. 자동 메모리(MEMORY.md), 플랜 모드 상태, 새로 활성화된 도구 목록 같은 정보가 들어간다. 이게 LLM에게 "지금 상황이 바뀌었다"는 신호를 주는 채널이다.

### 4.2 자동 압축 (Compaction)

히스토리가 모델 컨텍스트 윈도우의 일정 비율을 넘으면 하네스가 오래된 메시지를 요약한다. Claude Code는 200K 윈도우의 약 80% 지점에서 자동 압축을 트리거한다.

압축이 작동하는 방식:

1. 최근 N개 턴은 그대로 유지 (활성 작업 컨텍스트 보존)
2. 그 이전 메시지들을 별도 LLM 호출로 요약
3. 원본 메시지를 요약본으로 교체
4. 다음 LLM 호출부터는 요약본이 히스토리에 들어감

요약 품질이 낮으면 에이전트가 "방금 뭐 하고 있었지" 상태로 빠진다. Claude Code의 압축 프롬프트는 "현재 작업 목표, 시도한 접근, 발견한 사실, 다음에 할 일"을 명시적으로 보존하도록 설계되어 있다.

직접 구현할 때 주의할 점이 두 가지 있다. 압축 트리거 임계값을 너무 낮게 잡으면 요약본이 누적되면서 정보가 흐려진다. 임계값이 너무 높으면 한 번의 큰 도구 결과로 윈도우가 갑자기 터질 수 있다.

### 4.3 도구 결과 잘라내기

압축 이전에 1차 방어선이 도구 결과 절단이다. `Read` 도구로 10000줄짜리 파일을 읽으면 그 결과가 히스토리에 다 들어가지 않는다. Claude Code는 기본 2000줄로 자른다. `Bash` 출력도 30000자 정도에서 끝부분만 남기고 가운데를 생략한다.

```python
def truncate_tool_result(result: str, limit: int = 10_000) -> str:
    if len(result) <= limit:
        return result
    head = result[: limit // 2]
    tail = result[-limit // 2 :]
    return f"{head}\n\n... [생략 {len(result) - limit}자] ...\n\n{tail}"
```

가운데를 자르고 양 끝을 남기는 이유는, 에러 메시지나 결과 요약이 보통 출력의 시작이나 끝에 있기 때문이다. 중간을 자르면 핵심 정보 손실 가능성이 낮다.

### 4.4 시스템 리마인더 인젝션

Claude Code는 매 사용자 턴마다 시스템 리마인더를 동적으로 추가한다.

- 현재 활성화된 슬래시 명령 목록
- 자동 메모리(MEMORY.md) 내용
- 플랜 모드 / 오토 모드 상태
- 새로 로드된 도구의 가용성 알림

이건 시스템 프롬프트가 아닌, 매번 새로 인젝션되는 별도 메시지로 들어간다. 시스템 프롬프트는 한 번 캐싱되면 바뀌기 어렵지만, 리마인더는 턴마다 갱신할 수 있다. 캐시 효율과 동적 정보 전달을 분리한 설계다.


## 5. 도구 라우팅

도구 라우터는 LLM이 `{"name": "Read", "input": {"file_path": "/etc/passwd"}}` 같은 호출을 반환했을 때, 이걸 실제 함수 호출로 변환하는 역할을 한다. 단순히 이름 매핑처럼 보이지만, 실제로는 몇 가지 어려운 문제가 있다.

### 5.1 도구 정의의 비용

도구마다 LLM에게 보내는 정의(이름, 설명, JSON Schema)는 시스템 프롬프트의 일부로 들어간다. 도구 한 개당 평균 500토큰 정도다. 100개 도구를 등록하면 5만 토큰을 매 호출마다 소비한다. 컨텍스트 윈도우의 25%를 도구 정의가 먹는 셈이다.

Claude Code는 이걸 두 단계 라우팅으로 해결한다.

1. **상시 로드된 도구**: 자주 쓰는 핵심 도구(Read, Edit, Bash, Grep 등)는 시작부터 정의를 노출한다.
2. **지연 로드 도구(deferred tools)**: 잘 안 쓰는 도구(CronCreate, WebSearch, MCP 도구 등)는 이름만 알려주고 스키마는 숨긴다. 호출 직전에 `ToolSearch`로 스키마를 가져온다.

지연 로드 도구는 `system-reminder`에 이렇게 등장한다.

```
The following deferred tools are now available via ToolSearch.
Their schemas are NOT loaded — calling them directly will fail.
Use ToolSearch with query "select:<name>" to load tool schemas before calling them:
CronCreate, CronDelete, WebSearch, ...
```

LLM이 이 중 하나를 쓰려고 하면 먼저 `ToolSearch`를 호출해서 스키마를 로드한 뒤, 그 다음 턴에 실제 도구를 호출한다. 라운드 트립이 한 번 늘지만, 토큰 비용은 크게 줄어든다.

### 5.2 MCP 서버를 통한 동적 라우팅

Model Context Protocol(MCP)은 외부 프로세스에 정의된 도구를 라우팅하는 표준 프로토콜이다. Claude Code는 시작 시 등록된 MCP 서버에 연결하고, 서버가 제공하는 도구 목록을 받아온다.

```
Claude Code 하네스
    │
    ├─ 내장 도구 (Read, Edit, Bash, ...)
    │
    └─ MCP 클라이언트
         │
         ├─ MCP 서버 A (예: GitHub)
         │   └─ mcp__github__create_pr, mcp__github__list_issues, ...
         │
         └─ MCP 서버 B (예: Slack)
             └─ mcp__slack__send_message, ...
```

라우터 입장에서 MCP 도구 호출은 내장 도구와 동일하게 보인다. 이름을 받아서 처리할 핸들러를 찾고, 핸들러는 stdio나 HTTP로 MCP 서버에 요청을 보낸다. 도구 실행 결과는 다시 메시지로 변환되어 LLM에게 돌아간다.

MCP의 운영 함정 하나. MCP 서버 응답이 느리면 에이전트 루프 전체가 그만큼 멈춘다. 도구 실행에 타임아웃이 없으면, 죽은 MCP 서버가 에이전트를 영원히 블로킹할 수 있다. 라우터에 도구별 타임아웃을 박아야 한다.

### 5.3 인자 검증

라우터가 LLM의 도구 호출을 받으면, 실행 전에 JSON Schema로 인자를 검증한다.

```python
import jsonschema

def route_and_execute(call_name: str, call_input: dict) -> str:
    tool = TOOL_REGISTRY.get(call_name)
    if tool is None:
        return f"ERROR: 알 수 없는 도구 '{call_name}'"

    try:
        jsonschema.validate(call_input, tool.input_schema)
    except jsonschema.ValidationError as e:
        return f"ERROR: 인자 검증 실패: {e.message}"

    return tool.execute(call_input)
```

검증 실패를 에러로 돌려주면 LLM이 다음 턴에 인자를 고쳐서 다시 호출한다. 검증 없이 그대로 실행하면 `KeyError`나 `TypeError`가 핸들러 안에서 터지고, 트레이스백이 LLM에게 노출되어 토큰을 낭비한다.


## 6. 권한 모델

도구를 실제로 실행하기 전에 "이걸 해도 되는가"를 결정하는 게이트다. Claude Code의 권한 모델은 도구별 정책과 전역 모드의 조합으로 동작한다.

### 6.1 도구별 권한 정책

`~/.claude/settings.json`이나 프로젝트의 `.claude/settings.json`에 권한 규칙을 정의한다.

```json
{
  "permissions": {
    "allow": [
      "Bash(npm:*)",
      "Bash(git status)",
      "Read(./src/**)",
      "WebFetch"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(curl:* | sh)",
      "Read(.env)"
    ],
    "ask": [
      "Edit(./src/**)",
      "Bash(*)"
    ]
  }
}
```

규칙 평가 순서:

1. `deny`에 매칭되면 즉시 거부 (LLM에게 거부 사유 반환)
2. `allow`에 매칭되면 사용자 확인 없이 실행
3. `ask`에 매칭되거나 어디에도 매칭 안 되면 사용자에게 인터럽트

`Bash(npm:*)`는 "npm으로 시작하는 모든 명령 허용"이고, `Read(./src/**)`는 "src 디렉토리 하위 파일 읽기만 허용"이다. 글롭과 도구 인자 패턴을 조합한 DSL이다.

### 6.2 전역 모드

도구별 정책 위에 세션 단위 모드가 있다.

- **plan mode**: 도구 호출 없이 계획만 출력. 파일을 수정하지 않는다.
- **auto mode (Auto Mode)**: 사용자 확인 없이 합리적 판단으로 진행. 막힐 때만 멈춤.
- **dangerously skip permissions**: 모든 권한 검사 우회. CI/스크립트에서만 써야 함.

플랜 모드는 `EnterPlanMode` 도구로 진입한다. 진입하면 `Edit`, `Write`, `Bash(쓰기 명령)` 같은 변경 도구가 자동으로 잠긴다. LLM이 `ExitPlanMode`를 호출해서 계획을 사용자에게 보여주고 승인을 받아야 잠금이 풀린다.

### 6.3 권한 인터럽트의 UX

권한 게이트가 사용자 확인을 요청할 때 에이전트 루프는 블로킹된다. LLM이 다음 토큰을 생성하던 중이라도 멈춘다. 사용자가 "허용"을 누르면 루프가 재개되고, "거부"를 누르면 거부 결과가 tool_result로 들어가서 LLM이 다른 방법을 찾는다.

이 인터럽트 자체가 하네스 설계에서 까다로운 부분이다. LLM 호출은 비동기 스트리밍이고, 권한 다이얼로그는 사용자 입력을 기다린다. 둘을 깔끔하게 조율하지 않으면 "도구 실행 중인데 화면이 멈춘 것처럼 보이는" 상태가 생긴다.


## 7. 후크 시스템

후크는 하네스 이벤트에 사용자가 정의한 셸 명령을 끼워넣는 메커니즘이다. Claude Code의 후크는 `settings.json`에 정의한다.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {"type": "command", "command": "./scripts/check-staged.sh"}
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {"type": "command", "command": "npx prettier --write \"$CLAUDE_FILE_PATHS\""}
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {"type": "command", "command": "./scripts/notify-done.sh"}
        ]
      }
    ]
  }
}
```

이벤트 종류:

- **PreToolUse**: 도구 실행 직전. 후크가 비제로 종료 코드를 반환하면 도구 실행이 차단된다.
- **PostToolUse**: 도구 실행 직후. 결과를 후처리하거나 알림을 보낸다.
- **UserPromptSubmit**: 사용자가 메시지를 보낸 직후. 입력 검증이나 컨텍스트 주입에 쓴다.
- **Stop**: 에이전트가 종료 직전. 작업 완료 알림 같은 곳에 쓴다.
- **Notification**: 권한 확인 같은 인터럽트가 발생했을 때.

### 7.1 후크로 풀 수 있는 문제

후크는 "Claude가 이걸 할 때마다 X를 자동 실행"이라는 요구사항을 처리하는 표준 자리다. 메모리에 "파일 수정 후엔 prettier 돌려"라고 적어도, LLM이 그걸 잊을 수 있다. 후크는 하네스가 강제로 실행한다.

자주 쓰는 패턴:

- Edit/Write 후 자동 포맷팅(prettier, gofmt, ruff format)
- PreToolUse로 위험 명령 차단 (예: `Bash(rm -rf:*)` 매칭되면 후크가 exit 1)
- PostToolUse로 lint 자동 실행 후 에러를 LLM에게 피드백
- Stop 이벤트에서 슬랙/이메일 알림

### 7.2 후크 입출력 프로토콜

후크는 stdin으로 JSON을 받고, stdout으로 JSON을 반환한다. 비제로 종료 코드와 stdout의 `decision` 필드로 하네스 동작을 제어한다.

```bash
#!/bin/bash
# PreToolUse 후크 예시
input=$(cat)  # {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}

command=$(echo "$input" | jq -r '.tool_input.command')

if [[ "$command" =~ rm[[:space:]]+-rf[[:space:]]+/ ]]; then
    echo '{"decision": "block", "reason": "위험한 rm 명령 차단"}'
    exit 2  # exit 2면 stderr를 LLM에게 노출, exit 1이면 사용자에게만 노출
fi

exit 0
```

후크 자체가 무거우면 에이전트 응답성이 떨어진다. PreToolUse 후크가 도구 호출마다 5초씩 걸리면, 100턴 짜리 작업에 8분이 추가된다. 후크는 빠르게 짜고, 무거운 작업은 백그라운드로 보내야 한다.


## 8. 세션 영속화

에이전트가 한 번 종료되면 메모리가 다 날아간다고 생각하기 쉽지만, 실제로는 세션을 디스크에 직렬화하고 재개하는 메커니즘이 필요하다. 작업이 길어지면 중간에 멈췄다가 이어 가야 하는 경우가 많기 때문이다.

### 8.1 트랜스크립트 파일

Claude Code는 모든 세션을 `~/.claude/projects/<encoded-path>/` 아래에 JSONL로 저장한다. 한 줄에 메시지 하나씩 들어간다.

```jsonl
{"type":"user","message":{"role":"user","content":"파일 수정해줘"},"timestamp":"2026-06-06T12:00:00Z"}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"..."},{"type":"tool_use","id":"...","name":"Edit","input":{...}}]},"timestamp":"..."}
{"type":"tool_result","tool_use_id":"...","content":"OK","timestamp":"..."}
```

JSONL을 쓰는 이유는 두 가지다. 첫째, 매 턴마다 파일 끝에 append만 하면 되니까 쓰기가 싸다. 둘째, 일부가 손상되어도 나머지 줄을 읽을 수 있다.

세션 재개(`claude --resume`)는 이 JSONL을 처음부터 다시 읽어서 메시지 히스토리를 복원한다. LLM은 첫 호출 때부터 전체 히스토리를 다시 본다. 압축이 들어가 있던 세션이라도, 압축본이 히스토리에 저장되어 있으니 그대로 복원된다.

### 8.2 영속화의 트레이드오프

세션 파일이 길어지면 디스크 용량과 재개 속도가 문제가 된다. 도구 결과가 매번 수만 자씩 저장되면, 며칠 작업한 세션이 수백 MB가 된다.

대응 방식:

- **압축본만 저장**: 원본 메시지를 압축할 때, JSONL에도 압축본을 추가로 기록하고 다음 재개부터는 압축본을 사용
- **도구 결과 분리 저장**: 큰 도구 결과는 별도 파일로 빼고, JSONL에는 참조만 남김
- **세션 분할**: 일정 크기 넘어가면 새 세션 파일을 만들고, 이전 세션을 참조

Claude Code는 세션 단위 ID와 별개로 메시지 ID를 부여해서 일부 메시지만 재처리하거나 분기하는 것도 가능하다. 분기는 "이 시점으로 돌아가서 다시 시도" 같은 UX를 지원한다.

### 8.3 자동 메모리 (MEMORY.md)

세션을 넘어서 영속되는 정보는 따로 관리해야 한다. 세션 트랜스크립트는 그 세션 안에서만 의미가 있고, 다음 세션에서는 처음부터 시작한다.

Claude Code의 자동 메모리는 `~/.claude/projects/<encoded-path>/memory/` 디렉토리에 마크다운 파일로 저장된다. `MEMORY.md`가 인덱스 역할을 하고, 개별 메모리는 별도 파일로 나뉜다.

```
memory/
├── MEMORY.md              # 인덱스 (매 세션 자동 로드됨)
├── user_role.md           # 사용자 역할/선호
├── feedback_testing.md    # 피드백 메모
└── project_context.md     # 프로젝트 컨텍스트
```

`MEMORY.md`는 매 세션 시작 시 자동으로 시스템 컨텍스트에 인젝션된다. LLM이 "이 사용자는 한국어 문서를 선호하고, 커밋은 명시적 요청 시에만 한다"같은 정보를 매 세션 다시 학습할 필요가 없다. 트랜스크립트가 세션 내부 상태라면, 메모리는 세션 간 영속 상태다.

직접 구현할 때 메모리를 함부로 늘리면 안 된다. 메모리가 매 세션 컨텍스트를 차지하기 때문에, 100KB짜리 메모리는 모든 세션의 첫 응답을 느리게 만든다. Claude Code의 메모리 가이드는 "각 메모리 파일은 한 주제, 한 단락"을 권장한다.


## 9. 직접 하네스 구현하기

Anthropic Claude API로 직접 작은 하네스를 만드는 예제다. 위에서 다룬 다섯 가지 책임이 어디에 들어가는지 주석으로 표시한다.

```python
import anthropic
import json
import os
from pathlib import Path

client = anthropic.Anthropic()

# === 도구 정의 (Tool Router에서 사용) ===
TOOLS = [
    {
        "name": "read_file",
        "description": "파일 내용을 읽는다",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "파일에 내용을 쓴다",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
]

ALLOWED_BASE = Path("/workspace").resolve()
SESSION_FILE = Path(".session.jsonl")


# === Permission Gate ===
def check_permission(tool_name: str, tool_input: dict) -> tuple[bool, str]:
    if tool_name in ("read_file", "write_file"):
        path = Path(tool_input["path"]).resolve()
        if not path.is_relative_to(ALLOWED_BASE):
            return False, f"경로 {path}는 허용된 범위 밖이다"
    if tool_name == "write_file":
        if input(f"쓰기 허용? {tool_input['path']} [y/N]: ").lower() != "y":
            return False, "사용자가 거부했다"
    return True, ""


# === Hook Runner ===
def run_post_tool_hook(tool_name: str, tool_input: dict, result: str):
    hook_path = Path(".hooks/post_tool.sh")
    if not hook_path.exists():
        return
    import subprocess
    payload = json.dumps({"tool": tool_name, "input": tool_input, "result": result[:1000]})
    subprocess.run([str(hook_path)], input=payload, text=True, timeout=5, check=False)


# === Tool Router ===
def execute_tool(name: str, arguments: dict) -> str:
    allowed, reason = check_permission(name, arguments)
    if not allowed:
        return f"PERMISSION_DENIED: {reason}"

    try:
        if name == "read_file":
            path = Path(arguments["path"]).resolve()
            if not path.exists():
                return f"ERROR: {path} 없음"
            content = path.read_text()
            return content[:8000] + ("\n... [생략] ..." if len(content) > 8000 else "")
        elif name == "write_file":
            path = Path(arguments["path"]).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(arguments["content"])
            run_post_tool_hook(name, arguments, "OK")
            return f"OK: {path}"
        return f"ERROR: 알 수 없는 도구 {name}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


# === Session Store ===
def append_session(entry: dict):
    with SESSION_FILE.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_session() -> list[dict]:
    if not SESSION_FILE.exists():
        return []
    return [json.loads(line) for line in SESSION_FILE.read_text().splitlines()]


# === Context Manager (간단한 압축) ===
def compact_if_needed(messages: list[dict], threshold: int = 20) -> list[dict]:
    if len(messages) <= threshold:
        return messages
    # 오래된 메시지 요약
    head = messages[: -threshold + 5]
    tail = messages[-threshold + 5 :]
    summary_text = f"[이전 {len(head)}개 메시지 요약 생략] 사용자가 파일 작업을 진행 중이다."
    return [{"role": "user", "content": summary_text}] + tail


# === Agent Loop ===
def run_agent(task: str, max_turns: int = 30):
    messages = load_session() or []
    messages.append({"role": "user", "content": task})
    append_session({"role": "user", "content": task})

    token_usage = 0
    token_budget = 100_000

    for turn in range(max_turns):
        messages = compact_if_needed(messages)

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system="파일을 읽고 수정하는 코딩 에이전트다. 작업이 끝나면 도구 호출 없이 텍스트로 보고한다.",
            tools=TOOLS,
            messages=messages,
        )

        token_usage += response.usage.input_tokens + response.usage.output_tokens
        if token_usage > token_budget:
            print(f"[하네스] 토큰 예산 초과: {token_usage}/{token_budget}")
            break

        if response.stop_reason == "end_turn":
            text = "\n".join(b.text for b in response.content if b.type == "text")
            append_session({"role": "assistant", "content": text})
            return text

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[하네스] 호출: {block.name}")
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result[:10_000],
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
        append_session({"role": "assistant", "content": str(response.content)})
        append_session({"role": "tool_results", "content": tool_results})

    return "[하네스] 최대 턴 도달"


if __name__ == "__main__":
    print(run_agent("src/main.py를 읽고 함수 이름을 snake_case로 바꿔줘"))
```

각 컴포넌트가 어디 있는지 확인하면:

- 컨텍스트 관리: `compact_if_needed`, 도구 결과 8000자 절단, `messages` 길이 통제
- 도구 라우팅: `execute_tool`이 이름으로 핸들러를 디스패치
- 권한 모델: `check_permission`이 경로 검증 + 사용자 확인
- 후크: `run_post_tool_hook`이 외부 스크립트 호출
- 세션 영속화: `append_session` / `load_session`이 JSONL로 직렬화

프로덕션 수준으로 가려면 비동기 처리, 인터럽트 처리, 도구 타임아웃, 후크 출력 파싱, 메시지 분기/재시도 같은 게 더 들어가야 한다.


## 10. 하네스 설계 시 자주 걸리는 함정

### 10.1 무한 루프

같은 도구를 같은 인자로 반복 호출하는 경우가 가장 흔하다. LLM이 도구 결과를 제대로 해석 못 하고 같은 호출을 반복한다. 최근 N개 호출을 기록해두고 동일 호출이 3회 이상 반복되면 루프를 중단한다.

```python
from collections import Counter

recent_calls = []

def detect_loop(call_name, call_args, window=5, threshold=3):
    recent_calls.append((call_name, json.dumps(call_args, sort_keys=True)))
    if len(recent_calls) > window:
        recent_calls.pop(0)
    counts = Counter(recent_calls)
    return any(c >= threshold for c in counts.values())
```

시스템 프롬프트에 "작업이 끝나면 반드시 도구 호출 없이 종료하라"는 지시도 필수다. 이 한 줄이 빠지면 LLM이 "조금 더 개선해보겠다"며 무한히 돈다.

### 10.2 토큰 비용 폭발

`max_turns`를 50으로 잡고 토큰 예산 없이 돌렸다가 하룻밤 사이 수백 달러가 나간 사례가 실제로 있다. 도구 결과 길이, 컨텍스트 압축, 최대 턴, 토큰 예산은 네 개가 묶음으로 들어가야 한다. 하나라도 빠지면 비용이 어디서 터질지 예측 못 한다.

### 10.3 에러 전파 방향 잘못 잡기

에러에는 LLM이 고칠 수 있는 것과 없는 것이 있다.

- LLM이 고칠 수 있음: 파일이 없다, 인자가 잘못됐다, 권한이 거부됐다 → tool_result로 돌려준다
- LLM이 못 고침: API 키 만료, 네트워크 끊김, 디스크 가득참 → 루프를 중단하고 사용자에게 알린다

모든 에러를 LLM에게 돌려주면 LLM이 같은 에러를 반복하며 토큰을 태운다. 모든 에러에서 멈추면 사소한 문제로 작업이 중단된다. 도구 호출 단계에서 에러를 분류해서 처리해야 한다.

### 10.4 인터럽트가 깨지는 상황

사용자가 Ctrl+C를 눌렀을 때 도구 실행 중이면 어떻게 해야 하나. 바로 죽이면 도구가 중간 상태로 남는다. 끝까지 기다리면 인터럽트가 안 통하는 것처럼 보인다.

해결책은 도구 실행을 별도 스레드/프로세스에서 돌리고, 인터럽트 신호를 그쪽으로 전파하는 것이다. 도구가 인터럽트를 받으면 자기 상태를 정리하고 종료할 책임을 진다. 이게 잘 안 된 하네스는 사용자가 Ctrl+C를 눌렀는데 5초 동안 응답 없는 상태가 된다.

### 10.5 멀티 에이전트의 자원 공유

서브 에이전트를 생성하는 구조에서는 부모의 토큰 예산을 자식이 어떻게 나눌지가 문제다. Claude Code는 Workflow 시스템에서 부모와 자식이 같은 토큰 풀을 공유한다. 자식이 부모의 예산을 다 써버릴 수 있다. 자식별로 별도 예산을 주면 안전하지만, 동적으로 작업 양에 맞춰 분배하기 어렵다.

권한도 비슷한 문제가 있다. 자식 에이전트가 부모보다 좁은 권한을 가져야 안전한데, 동적으로 권한을 제한하려면 부모 하네스가 자식 호출을 감싸야 한다.


## 11. 정리

하네스는 LLM 호출 루프가 아니라, 에이전트를 안전하고 예측 가능하게 실행하는 런타임 시스템이다. 다섯 가지 책임을 모두 다뤄야 한다.

컨텍스트 관리는 메시지 히스토리의 누적을 통제한다. 도구 결과 절단, 자동 압축, 시스템 리마인더 인젝션이 핵심이다. 도구 라우팅은 LLM의 도구 호출을 실제 함수 호출로 매핑한다. 도구 정의 비용이 무시 못 할 수준이라, 지연 로드 같은 기법이 필요하다. 권한 모델은 도구 실행 전 게이트다. 도구별 정책과 전역 모드의 조합으로 동작한다. 후크는 하네스 이벤트에 사용자 정의 셸 명령을 끼워넣는 자리다. "X 할 때마다 Y 실행"이라는 요구를 LLM에 의존하지 않고 하네스가 강제한다. 세션 영속화는 트랜스크립트를 디스크에 직렬화해서 재개를 가능하게 한다. 세션을 넘어서는 정보는 자동 메모리로 따로 관리한다.

직접 만들 때 가장 먼저 정해야 하는 건 종료 조건이다. `max_turns`, 토큰 예산, 타임아웃, 루프 감지 중 하나라도 빠지면 사고가 난다. 그 다음이 도구 실행 격리고, 그 다음이 에러 분류다. 프레임워크를 쓰면 기본은 처리되지만, 무슨 일이 일어나는지 모르면 문제가 생겼을 때 원인을 찾을 수 없다.
