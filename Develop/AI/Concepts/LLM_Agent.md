---
title: LLM 에이전트 (Claude 관점)
tags: [ai, llm, agent, claude, react, tool-use, agent-loop, planning, memory]
updated: 2026-06-06
---

# LLM 에이전트 (Claude 관점)

## 들어가기 전에

이 문서는 "LLM 에이전트가 무엇이고 어떻게 동작하는가"를 Claude 에이전트(Claude Code, Claude Agent SDK)를 실제 다뤄본 경험을 바탕으로 정리한 것이다. Anthropic의 공식 설명, OpenAI의 ReAct 논문, LangChain/AutoGen 같은 프레임워크 문서를 보면 다들 비슷한 그림을 그리는데, 막상 구현해보면 미묘한 차이가 결과 품질을 가르는 경우가 많다.

특히 Claude는 도구 호출(tool use)과 멀티턴 대화에서 다른 모델과 다르게 동작하는 부분이 있다. `tool_use` 블록을 멈춰서 반환하는 시점, `tool_result`를 다시 받았을 때 컨텍스트를 해석하는 방식, prompt caching이 에이전트 루프에 미치는 영향 같은 것들. 이 문서는 그런 실무 디테일을 모은다.

## LLM 에이전트란

### 한 줄 정의

LLM 에이전트는 "LLM이 도구를 호출하고 그 결과를 다시 자기 컨텍스트로 받아서 다음 행동을 결정하는 루프"다. 그게 전부다.

복잡한 정의를 붙이는 문서가 많지만, 본질은 위 한 줄이다. 챗봇과 에이전트의 차이는 "외부 세계에 영향을 미치는가, 외부 세계의 결과를 보고 다시 판단하는가"에 있다.

```
챗봇:        사용자 입력 → LLM → 텍스트 응답 (끝)
에이전트:    사용자 입력 → LLM → 도구 호출 → 결과 → LLM → 도구 호출 → ... → 최종 응답
```

### 왜 에이전트가 필요한가

일반 LLM 호출만으로 안 되는 것들이 있다.

- 실시간 데이터 조회 (주가, 날씨, 최신 뉴스)
- 파일 시스템 접근 (코드 읽기, 쓰기, 실행)
- 외부 API 호출 (Slack 메시지 보내기, GitHub PR 생성)
- 멀티스텝 추론 (계산 결과를 보고 다음 계산을 결정)
- 자기 검증 (테스트를 실행해서 코드가 동작하는지 확인)

특히 코딩 에이전트(Claude Code, Cursor, Codex)는 "파일을 읽고 수정하고 테스트를 돌리는" 루프 자체가 가치의 핵심이다. LLM 한 번 호출해서 코드를 뱉는 것과는 차원이 다르다.

### 에이전트의 자율성 스펙트럼

자율성은 0/1이 아니라 스펙트럼이다.

| 단계 | 예시 | 특징 |
|---|---|---|
| 단순 도구 호출 | "현재 시간 알려줘" → time API | LLM이 호출할 도구를 고르기만 함 |
| 멀티스텝 체이닝 | "이 PDF 요약하고 Slack에 보내" | 2~3개 도구를 순차 호출 |
| 자유 루프 | Claude Code의 코드 수정 | LLM이 종료 시점을 스스로 판단 |
| 멀티 에이전트 | Workflow + subagent | 에이전트가 다른 에이전트를 호출 |

자율성이 높을수록 강력하지만 그만큼 통제가 어렵다. 무한 루프, 잘못된 도구 호출, 환각 기반 행동 같은 실패 모드가 늘어난다. 실무에서는 "필요한 만큼만 자율성을 주는 것"이 핵심이다.

## 에이전트 루프

### 기본 루프 구조

모든 에이전트의 심장은 이 루프다.

```python
while not done:
    response = llm.invoke(messages)
    if response.has_tool_calls:
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call)
            messages.append(tool_result(result))
    else:
        done = True
        return response.text
```

직관적이지만 실제 구현에서는 고려할 게 많다.

- 무한 루프를 어떻게 막을 것인가 (최대 turn 수, 토큰 예산)
- 도구가 실패했을 때 LLM에게 어떻게 알릴 것인가
- 도구 호출이 동시에 여러 개일 때 병렬로 실행할 것인가
- 사용자가 중간에 개입할 수 있게 할 것인가
- 컨텍스트가 길어지면 어떻게 압축할 것인가

### Claude의 에이전트 루프 구체화

Claude API에서는 `stop_reason`이 루프 종료 신호다.

```python
import anthropic

client = anthropic.Anthropic()
messages = [{"role": "user", "content": "현재 디렉토리의 파일 개수 알려줘"}]

while True:
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        tools=[{
            "name": "run_bash",
            "description": "Run a bash command",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }],
        messages=messages,
    )

    if response.stop_reason == "end_turn":
        # 도구 호출 없이 일반 응답으로 끝남
        print(response.content[-1].text)
        break

    if response.stop_reason == "tool_use":
        # 도구 호출 블록 처리
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                output = execute_bash(block.input["command"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })

        messages.append({"role": "user", "content": tool_results})
        # 다음 루프 반복
```

여기서 중요한 디테일.

`stop_reason="tool_use"`는 "이번 응답이 도구 호출에서 끊겼다"는 뜻이다. 다음 호출 때 `tool_result`를 user role로 넣어줘야 한다. assistant가 자기 응답을 보낸 후 user가 도구 결과를 알려주는 형식이다.

response.content는 여러 블록의 배열이다. text 블록과 tool_use 블록이 섞여 있을 수 있다. Claude가 "파일을 확인해보겠습니다" 같은 자연어를 먼저 출력하고 도구를 호출하는 패턴이 흔하다. 이걸 다 messages에 보존해야 다음 턴에서 일관성이 유지된다.

### 종료 조건 설계

루프가 안 끝나는 게 가장 흔한 사고다. Claude가 도구 호출에 빠져서 같은 파일을 반복해서 읽거나, 검색 결과가 만족스럽지 않다고 계속 다른 키워드로 시도하는 경우가 있다.

종료 조건은 세 층으로 둔다.

1. **자연 종료**: `stop_reason="end_turn"` (모델이 끝났다고 판단)
2. **턴 상한**: `max_turns=50` 같은 하드 캡 (안전장치)
3. **토큰 예산**: 누적 토큰이 예산 초과 시 강제 종료

Claude Code 내부 구현을 보면 비슷한 패턴이 있다. "1000 agent 호출 캡"은 워크플로우가 무한 루프에 빠지는 걸 막는 백스톱이다. 평소 워크플로우는 10~30개 에이전트로 끝나지만, 버그로 폭주할 때 사용자가 청구서를 받지 않도록 한다.

### 병렬 도구 호출

Claude는 한 응답에서 여러 tool_use 블록을 동시에 반환할 수 있다. 이걸 활용하면 루프 반복 횟수가 줄어든다.

```python
# 한 번의 응답에서 3개 도구를 병렬 호출
response.content = [
    TextBlock(text="세 파일을 한 번에 확인하겠습니다"),
    ToolUseBlock(id="1", name="read_file", input={"path": "a.py"}),
    ToolUseBlock(id="2", name="read_file", input={"path": "b.py"}),
    ToolUseBlock(id="3", name="read_file", input={"path": "c.py"}),
]
```

이 경우 실제 도구 실행은 클라이언트 쪽에서 `asyncio.gather` 같은 걸로 병렬 처리하면 된다. Claude Code가 "여러 Read를 한 메시지에 묶어서 호출하라"고 시스템 프롬프트에 명시한 이유도 이거다. 순차 호출하면 LLM 왕복이 N번, 병렬이면 1번이다.

다만 도구 간 의존성이 있으면(A의 결과로 B의 입력을 만들어야 하면) 모델이 알아서 순차로 호출한다. 강제할 필요 없다.

## ReAct 패턴

### ReAct의 핵심 아이디어

ReAct(Reasoning + Acting)는 2022년 Yao et al. 논문에서 나온 패턴이다. 핵심은 "도구를 호출하기 전에 LLM이 자기 추론을 텍스트로 출력하게 한다"는 것.

```
Thought: 사용자가 파일 개수를 원하니까 ls 명령어를 실행해야겠다
Action: run_bash(command="ls | wc -l")
Observation: 42
Thought: 42개 파일이 있다고 답하면 된다
Answer: 현재 디렉토리에는 42개 파일이 있습니다
```

이 패턴이 왜 잘 동작하느냐면, LLM이 추론 과정을 "글로 쓰면서" 다음 행동을 더 정확하게 결정하기 때문이다. Chain-of-Thought의 에이전트 버전이라고 보면 된다.

### Claude의 ReAct 변형

Claude는 기본적으로 자기 사고 과정을 텍스트로 출력하는 경향이 강하다. 시스템 프롬프트에서 "Don't narrate your internal deliberation"이라고 명시하지 않으면 "I'll check the file structure first..." 같은 메타 진술이 끼어든다.

Claude Code 시스템 프롬프트에 다음과 같은 지시가 있다.

> Don't narrate your internal deliberation. User-facing text should be relevant communication to the user, not a running commentary on your thought process.

이건 ReAct를 끄라는 게 아니라, "사용자 화면에는 결과만 보이게 하라"는 뜻이다. 내부적으로는 extended thinking(`thinking` 블록)에서 추론을 하고, 외부 출력은 행동과 결과만 남긴다.

### Extended Thinking과 ReAct

Claude 4 시리즈부터 extended thinking이라는 별도 블록이 있다. 모델이 명시적으로 "생각하는" 영역이 분리된 것.

```python
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=8096,
    thinking={"type": "enabled", "budget_tokens": 4000},
    messages=messages,
)

# response.content
# [
#   ThinkingBlock(thinking="사용자가 파일 개수를 원한다. ls | wc -l을 쓰면 되겠지만..."),
#   ToolUseBlock(name="run_bash", input={"command": "ls | wc -l"}),
# ]
```

ReAct의 Thought 부분이 ThinkingBlock에 들어가고, Action 부분이 ToolUseBlock에 들어간다. 사용자에게 보이는 출력은 깔끔하지만 모델은 충분히 추론한다.

주의할 점: thinking 블록도 컨텍스트에 누적된다. 멀티턴이 길어지면 thinking이 컨텍스트를 갉아먹는다. Claude API에서는 이전 턴의 thinking을 다음 턴 컨텍스트에서 제거하지 않는 게 기본인데, 비용과 컨텍스트 윈도우 관점에서 신경 써야 한다.

### Reflection 패턴

ReAct를 한 단계 확장한 게 Reflexion(2023, Shinn et al.)이다. 에이전트가 자기 결과를 보고 "이게 맞나?" 자체 검증하는 단계를 추가한다.

```
Action: 코드 작성
Observation: 테스트 통과
Reflection: 엣지 케이스를 빠뜨린 것 같다. 빈 배열 입력을 처리하지 않았다
Action: 빈 배열 처리 추가
Observation: 테스트 통과
Answer: 완료
```

Claude Code의 워크플로우에 비슷한 패턴이 있다. "Adversarial verify"라고 부르는데, 어떤 발견(finding)이 나오면 별도 에이전트가 "이걸 반박해봐"라고 시키는 방식이다.

```javascript
const votes = await parallel(Array.from({length: 3}, () => () =>
  agent(`Try to refute: ${claim}. Default to refuted=true if uncertain.`)));
const survives = votes.filter(v => !v.refuted).length >= 2;
```

3명의 검증자 에이전트가 독립적으로 "이 발견이 틀렸다는 증거"를 찾고, 2명 이상이 반박하면 발견을 폐기한다. 단순 ReAct로는 잡지 못하는 hallucination을 걸러낸다.

## 도구 호출 (Tool Use)

### 도구 스키마 설계

도구 스펙은 JSON Schema로 정의한다. 잘 쓴 도구 스키마와 못 쓴 도구 스키마는 에이전트 성능을 크게 가른다.

```python
{
    "name": "read_file",
    "description": "Read contents of a file. Returns the file content as a string. Fails if file doesn't exist or is binary.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the file. Relative paths are not supported."
            },
            "start_line": {
                "type": "integer",
                "description": "Line number to start reading from (1-indexed). Defaults to 1.",
                "default": 1
            },
            "end_line": {
                "type": "integer",
                "description": "Line number to stop at (inclusive). Defaults to end of file."
            }
        },
        "required": ["file_path"]
    }
}
```

도구 설명에 꼭 포함해야 할 것.

- **무엇을 하는가**: 한 문장으로 동작
- **언제 사용하는가**: 다른 비슷한 도구와의 차이
- **언제 사용하지 않는가**: 명시적 부정 케이스
- **반환값 형식**: 모델이 결과를 해석할 때 필요
- **실패 조건**: 어떤 입력이면 실패하는지

Claude Code의 Read 도구 설명을 보면 "do NOT re-read a file you just edited to verify" 같은 부정 지시가 있다. 모델이 불필요한 호출을 줄이도록 유도한다.

### tool_use와 tool_result 블록

Claude API에서 도구 호출 메시지 흐름은 이렇다.

```python
# 1턴: 사용자 입력
{"role": "user", "content": "현재 시간 알려줘"}

# 2턴: assistant가 도구 호출
{"role": "assistant", "content": [
    {"type": "text", "text": "현재 시간을 확인하겠습니다"},
    {"type": "tool_use", "id": "toolu_01", "name": "get_time", "input": {}}
]}

# 3턴: user role로 tool_result를 전달 (이게 자연스럽지 않게 느껴지지만 API 스펙이 그렇다)
{"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "toolu_01", "content": "2026-06-06T14:30:00"}
]}

# 4턴: assistant 최종 응답
{"role": "assistant", "content": "현재 시간은 2026년 6월 6일 14시 30분입니다"}
```

`tool_result`가 user role에 들어가는 게 처음 보면 어색하다. Anthropic이 이렇게 설계한 이유는 "외부 세계에서 들어온 정보는 모두 user 채널로"라는 일관성 때문이다. 사용자 입력과 도구 결과를 같은 채널로 합치면 모델이 "외부에서 들어온 정보"로 통일해서 처리할 수 있다.

`tool_use_id`는 반드시 매칭시켜야 한다. 안 그러면 InvalidRequestError가 난다. 도구 호출이 여러 개면 모든 호출에 대한 result를 다음 user 메시지에 다 넣어야 한다.

### 도구 실패 처리

도구가 실패했을 때 어떻게 LLM에게 알리느냐가 에이전트 견고성을 결정한다.

```python
# 나쁜 예: 예외를 그대로 던지고 루프 중단
try:
    result = read_file(path)
except FileNotFoundError as e:
    raise  # 에이전트 루프가 죽는다

# 좋은 예: 에러도 tool_result로 모델에게 전달
try:
    result = read_file(path)
    tool_results.append({"type": "tool_result", "tool_use_id": id, "content": result})
except FileNotFoundError as e:
    tool_results.append({
        "type": "tool_result",
        "tool_use_id": id,
        "content": f"Error: File not found: {path}",
        "is_error": True,
    })
```

`is_error=True` 플래그를 주면 모델이 더 명확하게 "이건 실패한 호출"로 인식한다. 같은 호출을 반복하지 않고 다른 접근을 시도한다.

특히 검색 도구 결과가 비었을 때 그냥 빈 문자열을 반환하면 모델이 "정보 없음"으로 받아들이고 환각으로 채울 수 있다. "No results found for query 'xyz'"처럼 명시적으로 알려줘야 한다.

### 도구 호출 빈도 제어

도구가 너무 많거나 비슷한 도구가 여러 개면 모델이 헷갈린다. Claude Code의 시스템 프롬프트에 다음 같은 지시가 있다.

> Prefer dedicated tools over Bash when one fits (Read, Edit, Write, Glob, Grep) — reserve Bash for shell-only operations.

이런 지시가 없으면 모델은 뭐든지 Bash로 처리하려는 경향이 있다. `cat`, `grep`, `find` 같은 명령으로 다 되니까. 명시적으로 "전용 도구를 써라"고 해야 적절한 도구를 고른다.

도구 호출 빈도를 줄이는 다른 패턴.

- **결과 캐싱**: 같은 파일을 두 번 읽지 않게 클라이언트에서 캐시
- **결과 압축**: 대용량 출력은 요약해서 모델에 전달
- **배치 API**: read_files(paths=[...]) 같이 여러 입력을 한 번에 받는 도구 제공

### MCP (Model Context Protocol)

도구를 정의하는 표준 프로토콜이 MCP다. Anthropic이 2024년 말 공개했다.

기존에는 도구 정의가 클라이언트 코드에 박혀 있었다. Claude Code가 알고 있는 도구, Cursor가 알고 있는 도구가 따로따로였다. MCP는 도구 서버를 별도 프로세스로 띄우고 표준 프로토콜로 도구 목록과 호출을 주고받는다.

```
[Claude Code] ←→ MCP Server (filesystem) ←→ 로컬 파일시스템
            ←→ MCP Server (github) ←→ GitHub API
            ←→ MCP Server (slack) ←→ Slack API
```

도구 생태계가 클라이언트와 독립적으로 자라난다. Slack용 MCP 서버 하나 만들면 Claude Code, Cursor, Codex가 다 쓸 수 있다. 단점은 프로세스 간 통신 오버헤드와 보안 검토 비용.

자세한 건 [MCP 문서](../MCP/MCP.md) 참고.

## 메모리

### 컨텍스트 윈도우 vs 메모리

LLM의 "메모리"는 헷갈리는 용어다. 두 가지가 섞여 있다.

1. **단기 메모리**: 한 대화 세션 내 컨텍스트 윈도우. Claude는 최대 1M 토큰까지 가능
2. **장기 메모리**: 세션이 끝나도 유지되는 정보. 별도 저장소 필요

단기 메모리는 LLM이 알아서 처리한다. messages 배열에 누적되니까. 문제는 장기 메모리다. 다음 세션에서 "지난번에 이 사용자가 Python 백엔드 개발자라고 했지"를 어떻게 기억하는가.

### 메모리 패턴들

**1. 메시지 히스토리 저장**

가장 단순한 방법. 모든 대화를 DB에 저장하고 다음 세션에서 일부를 컨텍스트에 주입한다.

```python
# 다음 세션 시작 시
recent_messages = load_last_n_messages(user_id, n=20)
messages = recent_messages + [{"role": "user", "content": new_input}]
```

단점: 대화가 길어지면 토큰 비용이 폭발한다. 100번째 세션이면 100x의 컨텍스트.

**2. 요약 기반 메모리**

각 세션 끝에 LLM이 요약을 만들어 저장. 다음 세션에서 요약만 주입.

```python
summary = llm.invoke(f"이 대화를 3문장으로 요약: {full_conversation}")
save_memory(user_id, summary)

# 다음 세션
past_summary = load_memory(user_id)
system_prompt = f"이전 대화 요약: {past_summary}\n\n이제 새 대화를 시작합니다"
```

단점: 요약 과정에서 디테일이 손실된다. "그 함수 이름이 뭐였더라"를 못 떠올린다.

**3. 구조화된 메모리 (Claude Code 패턴)**

Claude Code가 쓰는 방식이 흥미롭다. 메모리를 타입별로 분류해서 파일로 저장한다.

```
~/.claude/memory/
├── MEMORY.md           # 인덱스
├── user_role.md        # 사용자 정보
├── feedback_testing.md # 사용자 피드백
├── project_overview.md # 프로젝트 컨텍스트
└── reference_linear.md # 외부 시스템 참조
```

타입은 user / feedback / project / reference 네 가지. 각각 언제 저장하고 언제 활용할지 명확한 규칙이 있다.

```markdown
---
name: feedback-testing
description: integration tests must hit real DB, not mocks
metadata:
  type: feedback
---

통합 테스트는 모킹 DB가 아닌 실제 DB를 써야 한다.

**Why:** 지난 분기에 모킹 테스트가 통과했는데 프로덕션 마이그레이션이 실패한 사고가 있었음.
**How to apply:** 통합 테스트 작성 시 DB 모킹을 발견하면 사용자에게 확인 요청.
```

각 메모리는 "Why"와 "How to apply"를 명시한다. 규칙만 저장하면 모델이 엣지 케이스에서 잘못 적용한다. 이유를 알면 판단할 수 있다.

**4. RAG 기반 메모리**

장기 메모리를 벡터 DB에 저장하고 의미 검색으로 끌어온다.

```python
# 저장
embedding = embed(memory_text)
vector_db.insert(embedding, memory_text, user_id=user_id)

# 검색
query_embedding = embed(current_user_input)
relevant_memories = vector_db.search(query_embedding, top_k=5)
```

장점: 메모리가 무제한으로 늘어나도 컨텍스트 비용은 일정. 단점: 의미적으로 비슷한데 실제로는 관련 없는 메모리가 끌려올 수 있다.

### Stale memory 문제

가장 흔한 사고: 메모리가 한 번 저장되면 영원히 유지된다는 가정. 실제로는 코드, 정책, 사용자 상황이 다 바뀐다.

```
[메모리] 사용자의 메인 브랜치는 'master'다
[몇 달 후 현실] 사용자가 'main'으로 바꿈
[다음 대화] 에이전트가 'git push master' 시도 → 실패
```

대응책.

- 메모리에 시간 정보 포함 (언제 저장됐는지)
- 메모리 활용 전에 현재 상태 확인 (파일이 정말 그 경로에 있는지)
- 주기적 메모리 검증 루프

Claude Code 시스템 프롬프트에 다음 지시가 있다.

> A memory that names a specific function, file, or flag is a claim that it existed when the memory was written. It may have been renamed, removed, or never merged. Before recommending it: check the file exists. Grep for the function or flag.

메모리를 "현재 상태"가 아니라 "특정 시점의 스냅샷"으로 다루라는 것. 실무적으로 매우 중요한 관점이다.

## 플래닝

### 왜 플래닝이 필요한가

단순 도구 호출 루프로는 못 푸는 문제가 있다. "이 모노레포에서 deprecated API를 모두 새 API로 마이그레이션해"같은 작업.

- 어떤 파일을 수정해야 하는지 모름 (탐색 필요)
- 수정 순서가 중요 (의존성 그래프)
- 중간에 테스트가 깨질 수 있음 (검증 필요)
- 전체 진행률을 알아야 함 (관리)

플래닝은 "큰 작업을 작은 단계로 쪼개고 순서를 정하는" 과정이다.

### 플랜 패턴

**1. Plan-then-Execute**

플랜을 먼저 만들고, 그 다음에 한 단계씩 실행.

```
입력: "이 PR을 리뷰하고 발견사항을 정리해"

플랜 단계:
1. PR diff 가져오기
2. 변경된 파일 목록 추출
3. 각 파일별로 리뷰 수행
4. 발견사항 종합
5. Markdown 리포트 생성

실행 단계: 위 5단계를 순차 실행
```

장점: 사용자가 플랜을 보고 승인할 수 있음. Claude Code의 Plan Mode가 이 패턴.

단점: 플랜이 실행 전에 결정되니까, 실행 중 발견된 정보로 플랜을 못 바꿈.

**2. ReAct 기반 동적 플래닝**

매 단계마다 모델이 "다음에 뭘 할지"를 결정. 플랜이 동적으로 변함.

```
Step 1: ls로 디렉토리 확인 → src/, tests/ 발견
Step 2: src/에서 deprecated 호출 grep → 5개 파일 발견
Step 3: 첫 파일 수정 → 테스트 실행 → 실패
Step 4: 실패 원인 분석 → 의존성 파일 추가 발견
Step 5: 의존성 파일 먼저 수정 → 첫 파일 다시 수정 → 성공
...
```

장점: 새로 발견한 정보로 계획 조정 가능. 단점: 사용자가 어디까지 진행됐는지 추적하기 어려움.

**3. Plan + Task List**

플랜을 만들고, 각 단계를 task로 관리. 진행 상황이 가시적.

Claude Code의 TaskCreate가 이 패턴이다. 작업을 시작할 때 task list를 만들고, 각 task 상태(pending/in_progress/completed)를 업데이트한다.

```
tasks:
- [x] PR diff 가져오기
- [x] 변경 파일 추출
- [ ] 파일 1/5 리뷰 중
- [ ] 파일 2/5 리뷰
- [ ] 파일 3/5 리뷰
- [ ] 리포트 생성
```

사용자가 중간에 진행률을 볼 수 있고, 모델도 자기 진행 상황을 인지할 수 있다.

### 멀티 에이전트 플래닝

작업이 너무 크면 단일 에이전트로 못 한다. 멀티 에이전트를 오케스트레이션한다.

Claude Code Workflow의 패턴.

```javascript
phase('Discover')
const files = await agent('Find all files using deprecated API')

phase('Migrate')
const results = await pipeline(
    files.list,
    f => agent(`Migrate ${f} to new API`, {isolation: 'worktree'}),
    r => agent(`Run tests in ${r.file}`),
    t => agent(`If failed, fix: ${t.errors}`)
)

phase('Verify')
const summary = await agent(`Summarize: ${JSON.stringify(results)}`)
return summary
```

플랜이 코드로 표현된다. 각 phase는 명확한 입출력이 있고, 실패한 단계는 재시도 가능하다. LLM이 매번 "다음에 뭘 할지" 결정하는 것보다 결정론적이다.

자세한 건 [Agent Harness 문서](Agent_Harness.md) 참고.

## Claude 에이전트의 특수성

### Claude는 도구 호출에서 신중하다

다른 모델 대비 Claude는 도구를 적게 호출하는 경향이 있다. 정보가 부족하면 사용자에게 물어보거나, 가설을 세우고 검증하는 방식.

장점은 불필요한 도구 호출로 컨텍스트와 비용을 낭비하지 않는다는 점. 단점은 충분한 정보가 있는데도 "확인해도 될까요?" 물어볼 때가 있다는 점.

시스템 프롬프트로 행동을 조정할 수 있다.

```
- Bias toward working without stopping for clarifying questions
- When you'd normally pause to check, make the reasonable call and keep going
- They'll redirect you if needed
```

Claude Code의 Auto Mode가 이런 프롬프트로 행동을 조정한다. 기본적으로는 신중하지만, 컨텍스트가 있으면 자율 모드로 전환된다.

### Prompt Caching과 에이전트 루프

Claude의 prompt caching은 에이전트 성능에 결정적이다.

```python
# 시스템 프롬프트에 cache_control 설정
system_prompt = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,  # 보통 5000~20000 토큰
        "cache_control": {"type": "ephemeral"}
    }
]
```

에이전트는 같은 시스템 프롬프트로 수십 번 호출되니까, 캐시 히트가 90%+ 나온다. 비용이 1/10로 줄고 응답도 빨라진다.

주의: 캐시 TTL은 5분이다. 그 사이에 다음 호출이 없으면 캐시가 만료된다. 에이전트가 5분 이상 sleep하는 패턴은 피해야 한다.

```javascript
// 나쁜 예: 5분 자고 폴링
await sleep(300_000);
checkStatus();

// 좋은 예: 270초로 줄여서 캐시 유지
await sleep(270_000);
checkStatus();

// 또는: 한참 자야 한다면 1200초+ 이상으로 (캐시 미스 비용 분산)
await sleep(1200_000);
```

### Subagent 패턴

복잡한 작업은 메인 에이전트가 직접 하지 않고 subagent에 위임한다.

```python
# 메인 에이전트가 토큰 절약을 위해 위임
result = invoke_subagent(
    task="이 모노레포에서 unused exports를 모두 찾아라",
    agent_type="Explore"
)
# subagent가 수많은 grep/read를 수행. 결과만 메인에 반환.
# 메인 컨텍스트에는 grep 결과 수천 줄이 안 쌓임.
```

서브에이전트의 핵심 가치는 "컨텍스트 격리"다. 100개 파일을 읽어야 하는 작업을 메인에서 하면 메인 컨텍스트가 폭발한다. Subagent에 시키면 그 100개 파일은 subagent 컨텍스트에 들어가고, 메인에는 요약된 결과만 돌아온다.

Claude Code의 Agent tool 설명을 보면 이런 점이 강조된다.

> The result returned by the agent is not visible to the user. To show the user the result, you should send a text message back to the user with a concise summary of the result.

Subagent 결과는 메인이 한 번 더 요약해서 사용자에게 보여줘야 한다. 메인이 "최종 책임자" 역할을 하는 패턴.

### Workflow vs 자유 루프

작업 성격에 따라 두 패턴이 갈린다.

| 특성 | 자유 루프 | Workflow |
|---|---|---|
| 결정론 | 낮음 (LLM이 매번 결정) | 높음 (코드가 결정) |
| 유연성 | 높음 | 낮음 |
| 디버깅 | 어려움 | 쉬움 |
| 적합한 작업 | 탐색적 코딩 | 대량 마이그레이션, 감사 |

작은 작업은 자유 루프(Claude Code 메인 루프), 큰 작업은 Workflow로 쪼개는 게 일반적이다.

## 실패 모드와 대응

### 무한 루프

같은 도구를 반복 호출하면서 종료하지 않는 경우. 가장 흔한 원인.

- 검색 결과가 비었는데 모델이 다른 키워드로 계속 시도
- 테스트가 깨졌는데 비슷한 수정을 반복
- 도구 결과를 잘못 해석해서 잘못된 후속 호출

대응.

- 최대 turn 수 캡 (예: 50)
- 토큰 예산 캡 (예: 1M 토큰)
- 같은 도구 호출 N회 반복 감지 → 강제 종료

### 환각 도구 호출

존재하지 않는 도구나 잘못된 입력으로 호출. Claude는 비교적 적지만 발생한다.

대응.

- 도구 스키마 검증을 클라이언트에서 수행 → 잘못된 호출은 즉시 에러 반환
- 에러 메시지에 "사용 가능한 도구 목록" 첨부 → 모델이 자기 수정
- 의심스러운 호출은 사용자 승인 받기

### 도구 결과 무시

도구가 명확한 답을 반환했는데 모델이 무시하고 다른 결론을 내는 경우. 보통 결과 포맷이 모호할 때 발생.

```
도구 결과: "{}"
모델: 결과가 없네요. 추측으로 답하겠습니다.

→ 실제로는 빈 객체가 의미 있는 결과인 경우가 많음
```

대응.

- 도구 결과에 메타 정보 추가 ("0 results", "empty array")
- 도구 설명에 결과 해석 가이드 명시
- 빈 결과는 명시적 텍스트로 ("No matches found")

### 컨텍스트 폭발

에이전트가 오래 돌면 컨텍스트가 점점 커진다. 1M 컨텍스트도 한계가 있다.

대응.

- 오래된 도구 결과는 요약본으로 교체
- 파일 읽기 결과는 필요한 부분만 잘라서 컨텍스트에 넣기
- 일정 길이 초과 시 자동 압축 (Claude Code는 200k 즈음에서 자동 compact 트리거)

### 잘못된 도구 선택

비슷한 도구가 여러 개일 때 부적절한 선택. 예: `Read` 대신 Bash의 `cat`을 사용.

대응.

- 시스템 프롬프트에 도구 선택 가이드 명시
- 도구 설명에 "언제 사용하지 않는가" 추가
- 도구 호출 패턴 분석 → 자주 잘못 선택되는 케이스 발견 → 프롬프트 보강

## 실제 구현: 간단한 코딩 에이전트

다음은 Anthropic SDK로 만든 미니멀한 코딩 에이전트다. 위에서 다룬 패턴들이 실제로 어떻게 합쳐지는지 보여준다.

```python
import anthropic
import subprocess
import json
from pathlib import Path

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file. Returns the full text content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute file path"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file. Overwrites existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "run_command",
        "description": "Run a shell command. Returns stdout. For tests, builds, file operations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"}
            },
            "required": ["command"]
        }
    }
]

def execute_tool(name, input_data):
    try:
        if name == "read_file":
            return Path(input_data["path"]).read_text()
        elif name == "write_file":
            Path(input_data["path"]).write_text(input_data["content"])
            return f"Wrote {len(input_data['content'])} bytes"
        elif name == "run_command":
            result = subprocess.run(
                input_data["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}\nreturn_code: {result.returncode}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"

def run_agent(user_request, max_turns=20):
    messages = [{"role": "user", "content": user_request}]

    system_prompt = [{
        "type": "text",
        "text": (
            "You are a coding agent. Use tools to read files, write code, and run tests. "
            "Be concise. Don't narrate your thinking. "
            "Prefer batched parallel tool calls when independent."
        ),
        "cache_control": {"type": "ephemeral"}
    }]

    for turn in range(max_turns):
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # 응답을 messages에 보존
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text_blocks = [b for b in response.content if b.type == "text"]
            return text_blocks[-1].text if text_blocks else "(empty response)"

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  → {block.name}({json.dumps(block.input)[:80]})")
                    output = execute_tool(block.name, block.input)
                    is_error = output.startswith("Error:")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                        "is_error": is_error,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        # 다른 stop_reason은 예외 케이스
        return f"Unexpected stop_reason: {response.stop_reason}"

    return "Max turns reached without completion"


if __name__ == "__main__":
    result = run_agent(
        "Create a fibonacci.py in /tmp that prints first 10 fib numbers, then run it"
    )
    print("\nFinal:", result)
```

100줄 미만이지만 에이전트의 핵심 요소가 다 들어있다.

- 도구 정의 (JSON Schema)
- 도구 실행 로직 (예외 → tool_result)
- 에이전트 루프 (stop_reason 분기)
- 메시지 누적 (assistant content 보존)
- 시스템 프롬프트 캐싱
- 안전장치 (max_turns)

이걸 기반으로 도구를 추가하고 (search, browser, git), 메모리를 붙이고, 멀티 에이전트로 확장하는 게 실제 코딩 에이전트의 구조다.

## 평가와 디버깅

### 에이전트 평가의 어려움

LLM 평가는 정답이 있어서 자동화하기 쉽다. 에이전트는 그렇지 않다.

- 같은 작업도 여러 정답 경로가 있음
- 중간 상태 (도구 호출 순서)도 평가 대상
- 비결정성 (같은 입력에도 다른 경로)

흔히 쓰는 평가 방법.

**1. 결과 기반 평가**: 최종 출력만 확인 (테스트 통과 여부, 산출물 검증)

**2. Trajectory 평가**: 도구 호출 순서를 사람이 검토하거나 LLM-as-judge로 평가

**3. Cost 평가**: 작업당 토큰 비용, 호출 횟수

코딩 에이전트는 SWE-bench 같은 벤치마크가 있다. 실제 GitHub 이슈를 풀어서 PR을 만들 수 있는지 테스트한다. Claude 4 시리즈는 SWE-bench Verified에서 70% 이상 점수가 나온다.

### Trace 디버깅

에이전트가 잘못 동작했을 때 어디서 틀렸는지 찾기 어렵다. 모든 LLM 호출을 trace로 남겨야 한다.

```python
import logging

class AgentTracer:
    def __init__(self):
        self.events = []

    def log_llm_call(self, messages, response, tokens):
        self.events.append({
            "type": "llm_call",
            "messages_len": len(messages),
            "stop_reason": response.stop_reason,
            "tokens": tokens,
        })

    def log_tool_call(self, name, input, output, duration_ms):
        self.events.append({
            "type": "tool_call",
            "name": name,
            "input": input,
            "output_preview": str(output)[:200],
            "duration_ms": duration_ms,
        })

    def export(self):
        return json.dumps(self.events, indent=2)
```

LangSmith, Helicone, Weights & Biases 같은 외부 서비스도 있다. 직접 만들든 외부 쓰든 trace는 필수.

### 비용 모니터링

에이전트는 한 번 잘못 돌면 비용이 폭발한다. 토큰 예산을 매 호출마다 추적해야 한다.

```python
class TokenBudget:
    def __init__(self, max_tokens=1_000_000):
        self.max_tokens = max_tokens
        self.spent = 0

    def consume(self, usage):
        self.spent += usage.input_tokens + usage.output_tokens
        if self.spent > self.max_tokens:
            raise BudgetExceededError(f"Spent {self.spent}/{self.max_tokens}")

    def remaining(self):
        return max(0, self.max_tokens - self.spent)
```

Claude API 응답의 `usage` 필드로 정확한 토큰 수를 받을 수 있다. cache hit가 발생하면 `cache_read_input_tokens`로 별도 표기되니까 캐시 효율도 모니터링 가능하다.

## 마치며

LLM 에이전트는 복잡한 개념이지만 핵심은 단순하다. "LLM이 도구를 호출하고 결과를 보고 다음을 결정하는 루프". 그 외 모든 것 - ReAct, 메모리, 플래닝, 멀티 에이전트 - 은 이 루프를 더 견고하고 강력하게 만드는 패턴이다.

Claude로 에이전트를 만들 때 신경 쓸 부분을 정리하면.

- `stop_reason`과 `tool_use`/`tool_result` 블록 흐름 정확히 이해하기
- Prompt caching으로 비용과 지연 줄이기
- 도구 스키마와 설명을 꼼꼼하게 (모델 행동을 가장 직접 좌우)
- 에러를 tool_result로 모델에 돌려주기 (예외로 죽이지 말기)
- 메모리는 stale될 수 있다는 전제로 검증 단계 두기
- 큰 작업은 subagent나 workflow로 분할

이 문서는 일반론과 Claude 특수성을 섞어놨다. OpenAI나 Gemini 에이전트도 큰 그림은 같지만 도구 호출 포맷, 캐싱 정책, 컨텍스트 윈도우 같은 디테일이 다르다. 다른 모델로 옮길 때 그 디테일을 확인해야 한다.

관련 문서.

- [Agent Harness](Agent_Harness.md): 에이전트 실행 환경
- [Effort Mode](Effort_Mode.md): 모델 추론 강도 조절
- [MCP](../MCP/MCP.md): 도구 프로토콜
- [Claude Code](../Claude_Code/Claude_Code.md): 실제 에이전트 제품
- [LLM Context Window](LLM_Context_Window.md): 컨텍스트 관리
- [Prompt Engineering](Prompt_Engineering.md): 에이전트 시스템 프롬프트 작성
