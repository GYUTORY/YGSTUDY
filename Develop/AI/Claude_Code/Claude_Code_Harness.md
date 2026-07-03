---
title: Claude Code 하네스 — 내부 동작과 디버깅
tags: [ai, claude-code, harness, runtime, permission, hooks, mcp, sandbox]
updated: 2026-05-07
---

# Claude Code 하네스 — 내부 동작과 디버깅

## 1. 이 문서의 범위

[Agent_Harness.md](../Concepts/Agent_Harness.md)는 일반적인 에이전트 하네스 개념을 다룬다. [Claude_Code.md](Claude_Code.md)와 [Claude_Code_Agent.md](Claude_Code_Agent.md)는 사용자 입장에서 어떤 기능이 있는지를 설명한다. 그 사이에 비어있는 부분이 있다. 사용자가 엔터를 친 순간부터 LLM이 도구를 호출하고 결과가 화면에 찍히기까지, Claude Code 런타임 내부에서 무슨 일이 벌어지는가.

5년차 백엔드 시각에서 보면 Claude Code 하네스는 결국 잘 만든 RPC 디스패처에 컨텍스트 관리자와 권한 미들웨어를 붙인 구조다. 에이전트 루프 자체는 단순하다. 진짜 복잡한 부분은 시스템 프롬프트 조립, 토큰 예산 관리, 권한 룰 매칭, 훅 실행 순서다. 이 문서는 그 부분을 정리한다.

설치, 기본 사용법, CLAUDE.md 작성법은 다른 문서를 참고해라.


## 2. 한 턴이 시작될 때 일어나는 일

사용자가 프롬프트를 입력하고 엔터를 친다. 화면에는 `Claude is thinking...` 같은 표시가 뜨고, 잠시 후 도구 호출이나 응답이 나온다. 이 사이에서 하네스가 처리하는 작업을 순서대로 풀어보면 다음 흐름이다.

```
사용자 입력
  │
  ▼
1. 시스템 프롬프트 조립
   ├─ 기본 시스템 프롬프트 (모델별)
   ├─ CLAUDE.md 로드 (~/.claude, 프로젝트 루트, 현재 디렉토리)
   ├─ 자동 메모리 인젝션 (MEMORY.md)
   ├─ 환경 정보 (cwd, git status, 플랫폼, 셸)
   └─ 사용 가능한 스킬/도구 목록
  │
  ▼
2. 도구 정의 주입
   ├─ 내장 도구 (Read, Edit, Bash, Grep ...)
   ├─ MCP 서버 도구
   └─ deferred tools 이름 목록 (스키마는 미로드)
  │
  ▼
3. PreSubmit 훅 실행 (UserPromptSubmit)
  │
  ▼
4. Anthropic API 호출
   ├─ messages 배열 + tools 배열
   ├─ 캐시 마커 (cache_control)
   └─ 스트리밍 응답
  │
  ▼
5. 응답 파싱
   ├─ 텍스트 블록 → 화면에 출력
   └─ 도구 호출 블록 → Tool Dispatcher
  │
  ▼
6. 도구 호출 처리 (각 호출마다)
   ├─ PreToolUse 훅
   ├─ Permission Gate (룰 매칭)
   ├─ 사용자 승인 (필요 시)
   ├─ 실제 실행
   └─ PostToolUse 훅
  │
  ▼
7. 결과를 messages에 추가, 컨텍스트 한계 검사
  │
  ▼
8. 종료 조건 미충족이면 4번으로
```

이 흐름에서 흥미로운 부분은 1번과 6번이다. 1번에서는 어디서 어떤 텍스트가 어떤 순서로 시스템 프롬프트에 들어가는지가 결정되고, 6번에서는 권한 룰이 어떻게 매칭되어 도구가 실행되거나 차단되는지가 결정된다. 나머지 단계는 일반적인 LLM API 호출과 크게 다르지 않다.


## 3. 시스템 프롬프트가 조립되는 방식

Claude Code의 시스템 프롬프트는 단일 문자열이 아니다. 여러 소스에서 모은 텍스트를 조각으로 붙인 결과물이다. 문제가 생겼을 때 어느 조각이 영향을 줬는지 추적해야 하므로 각 소스의 위치를 기억해두면 좋다.

### 3.1 로드 우선순위

| 순서 | 소스 | 경로 | 비고 |
|------|------|------|------|
| 1 | 기본 시스템 프롬프트 | 바이너리 내장 | 모델·버전별로 고정 |
| 2 | 사용자 전역 CLAUDE.md | `~/.claude/CLAUDE.md` | 모든 세션에 적용 |
| 3 | 프로젝트 CLAUDE.md | `<repo>/CLAUDE.md` | git 루트에서 탐색 |
| 4 | 현재 디렉토리 CLAUDE.md | `<cwd>/CLAUDE.md` | 프로젝트와 다르면 덧붙임 |
| 5 | 자동 메모리 | `~/.claude/projects/<encoded>/memory/MEMORY.md` | 자동 메모리가 켜진 경우 |
| 6 | 사용자 정의 시스템 프롬프트 | `--system-prompt` 또는 settings | 비어있는 경우가 많음 |

여기서 5번 자동 메모리는 디렉토리명이 인코딩된 형태로 저장된다는 점에 주의한다. 프로젝트 경로가 `/Users/foo/work/api-server`라면 인코딩된 이름은 `-Users-foo-work-api-server`다. 슬래시가 하이픈으로 치환되는데, 이 이름이 충돌할 수 있어서 다른 경로의 동일한 폴더명이 같은 메모리를 공유하지 않도록 주의해야 한다.

### 3.2 프롬프트 캐시 마커

Claude API의 prompt caching을 활용해서 시스템 프롬프트와 도구 정의에 캐시 마커를 붙인다. 캐시 TTL은 기본 5분, ephemeral 마커는 길게 잡으면 1시간까지 늘릴 수 있다.

캐시가 깨지는 경우는 정해져 있다. 시스템 프롬프트의 끝에 한 글자라도 다른 텍스트가 붙으면 그 이후는 캐시 미스다. CLAUDE.md를 수정하면 다음 호출부터는 새로 캐싱된다. 자동 메모리가 활성화된 상태에서 MEMORY.md를 자주 갱신하면 캐시 적중률이 떨어진다. 메모리는 대화 단위로 안정시키고 세션 도중에는 가능하면 건드리지 않는 편이 비용 면에서 유리하다.

### 3.3 환경 블록

시스템 프롬프트의 마지막에는 매번 갱신되는 환경 블록이 붙는다. cwd, git 브랜치, 최근 커밋, 플랫폼, OS 버전 등이 들어간다. 이 블록은 캐싱되지 않는 부분이다. 그래서 git 상태가 자주 바뀌면 이 블록도 매번 새로 붙는다. 매번 짧은 텍스트가 새로 붙기 때문에 캐시 효율에는 큰 영향을 주지 않지만, 시스템 프롬프트 끝부분에 사용자가 직접 텍스트를 추가하려고 하면 환경 블록보다 앞에 들어간다는 사실을 인지해야 한다.


## 4. 도구 디스패처와 deferred tools

### 4.1 내장 도구의 등록 방식

Claude Code의 내장 도구는 코드 안에 정의된 핸들러 + JSON Schema 페어다. 하네스 시작 시 사용 가능한 도구를 모아서 Anthropic API의 `tools` 파라미터에 넣는다. 도구 호출이 오면 이름으로 핸들러를 찾아 실행한다.

여기서 발생하는 첫 번째 문제는 도구가 너무 많을 때다. MCP 서버를 5~6개 연결하면 도구 개수가 100개를 가볍게 넘는다. 도구 정의 자체가 토큰을 먹는다. 도구 하나당 평균 200~300 토큰이라고 잡으면 100개면 2~3만 토큰이다. 컨텍스트 윈도우의 상당 부분이 도구 정의로만 채워진다.

### 4.2 deferred tools와 ToolSearch

이 문제를 해결하려고 도입된 개념이 deferred tools다. 자주 쓰지 않는 도구는 이름만 시스템 프롬프트에 노출하고, 실제 JSON Schema는 로드하지 않는다. 호출하려면 먼저 ToolSearch로 스키마를 가져와야 한다.

```
ToolSearch(query="select:CronCreate,CronList", max_results=5)
  ↓
<functions>
<function>{"description": "...", "name": "CronCreate", "parameters": {...}}</function>
<function>{"description": "...", "name": "CronList", "parameters": {...}}</function>
</functions>
```

ToolSearch가 반환한 결과는 다음 턴부터 정식 도구처럼 호출 가능하다. 하네스가 결과를 보고 디스패처에 등록하는 방식이다. 이 동작은 LLM에게는 보이지 않는다. 모델 입장에서는 ToolSearch 결과가 시스템 메시지로 주입된 다음 그 도구를 호출하면 정상 동작한다.

deferred tools를 직접 호출하려고 하면 `InputValidationError`가 난다. 스키마가 없으니 인자 검증이 안 되기 때문이다. 이 에러는 사용자가 보는 게 아니라 LLM이 보는 에러 메시지로 돌아온다. 모델이 알아서 ToolSearch를 다시 호출하도록 시스템 프롬프트에 명시되어 있다.

### 4.3 도구 결과 직렬화 시 잘리는 부분

도구 실행 결과는 토큰을 먹기 때문에 일정 길이 이상이면 잘린다. Read 도구의 경우 기본 2000줄, Bash는 출력 길이 제한, Grep은 head_limit 기본값이 250줄이다. 잘렸다는 표시가 결과 끝에 붙는다.

여기서 자주 겪는 문제가 있다. 큰 파일을 한 번에 읽으려다가 중간이 잘리는데, 모델이 이 사실을 무시하고 작업을 계속하는 경우다. 실제로는 파일의 절반밖에 못 봤는데 마치 전체를 본 것처럼 코드를 수정한다. Read의 offset/limit 파라미터를 명시해서 페이지네이션하거나, Grep으로 필요한 부분만 찾아 읽는 식으로 우회한다.


## 5. Permission Gate와 권한 모드

### 5.1 permission mode

Claude Code는 도구 호출 전에 권한 검사를 한다. 모드는 네 가지다.

| 모드 | 동작 |
|------|------|
| `default` | 위험한 도구는 매번 사용자 승인 |
| `acceptEdits` | Edit/Write는 자동 허용, Bash 등은 승인 필요 |
| `plan` | 모든 변경 도구 차단, 읽기만 허용 |
| `bypassPermissions` | 권한 검사 비활성화 (위험) |

`plan` 모드는 `EnterPlanMode` 도구로 진입한다. 이 모드에서는 Edit/Write/Bash 같은 변경 도구가 권한 게이트에서 차단된다. 사용자가 `ExitPlanMode`로 빠져나오면서 계획을 승인해야 실제 작업이 시작된다.

`bypassPermissions`는 컨테이너처럼 격리된 환경에서만 쓰는 게 안전하다. 로컬 macOS/Linux 셸에서 켜고 돌리면 에이전트가 실수로 `rm -rf` 같은 명령을 실행해도 막아주는 게 없다.

### 5.2 룰 매칭 방식

settings.json의 `permissions` 키에서 `allow`, `ask`, `deny` 룰을 정의한다. 룰은 `<도구명>` 또는 `<도구명>(<패턴>)` 형식이다.

```json
{
  "permissions": {
    "allow": [
      "Bash(npm test:*)",
      "Bash(git status)",
      "Bash(git diff:*)",
      "Read",
      "Glob",
      "Grep"
    ],
    "ask": [
      "Bash(git push:*)",
      "Bash(npm install:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(curl:*)"
    ]
  }
}
```

매칭 우선순위는 `deny > ask > allow` 순이다. 같은 명령이 여러 룰에 걸릴 수 있는데, 가장 강한 제약이 적용된다. `Bash(rm -rf:*)`가 `deny`에 있으면 `allow`에 `Bash` 전체가 들어있어도 차단된다.

패턴 끝의 `:*`는 와일드카드다. `npm test:*`는 `npm test`, `npm test --watch`, `npm test src/`를 전부 매칭한다. 와일드카드 없이 `Bash(git status)`만 쓰면 정확히 그 명령만 매칭한다.

룰을 매칭할 때 자주 헷갈리는 부분이 있다. 명령 안에 셸 메타문자(`&&`, `|`, `;`)가 들어있으면 룰이 깨진다. `npm test && npm run lint`는 `Bash(npm test:*)`로 매칭되지 않는다. 컴파운드 명령은 별도 룰을 만들거나, 사용자가 매번 승인하도록 두는 편이 안전하다.

### 5.3 settings.json 우선순위

설정 파일은 여러 위치에 있다. 우선순위는 다음과 같다.

1. `~/.claude/settings.json` (사용자 전역)
2. `<repo>/.claude/settings.json` (프로젝트 공유, 커밋 대상)
3. `<repo>/.claude/settings.local.json` (프로젝트 로컬, gitignore 대상)

뒤로 갈수록 우선순위가 높다. 같은 룰이 여러 파일에 있으면 더 가까운 파일이 이긴다. 다만 `deny`는 어느 위치에 있든 항상 적용된다.


## 6. 컨텍스트 관리

### 6.1 자동 압축

대화가 길어지면 컨텍스트 윈도우가 한계에 다가간다. Claude Opus는 1M, Sonnet은 200K~1M인데, 도구 결과로 큰 파일을 여러 번 읽으면 빠르게 채워진다. Claude Code는 일정 임계치(보통 75~80%)를 넘으면 자동 압축을 시도한다.

압축은 별도 LLM 호출로 처리된다. 오래된 메시지를 모아서 "이 대화의 요점은 X였고, 사용자가 Y를 요청했고, Z 도구를 호출해서 결과 W를 얻었다"는 식의 요약문을 만든다. 그 요약을 메시지 히스토리의 앞부분에 두고 원본 메시지는 버린다.

압축이 일어나면 그동안 캐시되어 있던 프롬프트가 깨진다. 압축 직후 첫 번째 호출은 캐시 미스라서 응답이 느려진다. 작업 중에 갑자기 토큰 사용량이 늘고 응답이 느려지면 압축이 일어났다고 의심하면 된다.

### 6.2 자동 메모리 인젝션

`~/.claude/projects/<encoded>/memory/MEMORY.md`에 메모리를 저장하면 다음 세션부터 시스템 프롬프트에 자동으로 인젝션된다. MEMORY.md는 인덱스 역할이고, 실제 메모리 본문은 같은 디렉토리의 별도 파일들에 들어간다.

주의할 점은 MEMORY.md가 200줄을 넘으면 잘린다는 것이다. 인덱스로만 쓰고 본문은 분리하라는 강제다. 이 제약을 무시하고 MEMORY.md에 직접 긴 내용을 쓰면 다음 세션에서 끝부분이 사라진다.

자동 메모리는 모든 세션에 영향을 준다. 한 프로젝트에서 등록한 메모리가 같은 디렉토리에서 시작한 다른 세션에도 적용된다. 그래서 메모리에 토큰이 큰 내용을 쌓으면 모든 세션의 시작 비용이 올라간다.

### 6.3 토큰 예산 모니터링

`/cost` 명령으로 현재 세션의 누적 비용을 본다. `/context`는 현재 컨텍스트 사용 비율을 보여준다. 두 값을 보면서 작업 스타일을 조정한다.

토큰을 빨리 소모하는 도구 호출 패턴이 있다.

- 큰 디렉토리에서 `Glob("**/*")` 같은 패턴 매칭 후 모두 Read
- 큰 로그 파일을 head_limit 없이 Grep
- node_modules가 포함된 디렉토리에서 재귀 탐색

이런 호출은 한 번에 수만 토큰을 먹는다. 이런 호출을 줄이는 가장 빠른 방법은 도구 결과를 본인이 처리하지 말고 서브 에이전트(Agent 도구)에게 넘기는 것이다. 서브 에이전트는 별도 컨텍스트라 결과 전체를 자기 윈도우에서 소화한 다음 요약만 메인 에이전트에 돌려준다.


## 7. 훅 실행 시점

훅은 settings.json의 `hooks` 키에서 정의한다. 셸 명령을 등록하면 특정 이벤트가 발생할 때 하네스가 그 명령을 실행한다.

### 7.1 훅 종류와 발화 시점

| 훅 이름 | 발화 시점 | 입력 (stdin) | 차단 가능 |
|---------|----------|-------------|----------|
| `UserPromptSubmit` | 사용자 입력 직후, LLM 호출 전 | 사용자 메시지 | 가능 |
| `PreToolUse` | 도구 호출 직전 | 도구 이름·인자 JSON | 가능 |
| `PostToolUse` | 도구 실행 직후 | 결과 JSON | 불가 |
| `Stop` | 어시스턴트 응답 종료 시 | 마지막 메시지 | 불가 |
| `SubagentStop` | 서브 에이전트 종료 시 | 결과 JSON | 불가 |
| `Notification` | 사용자에게 알림이 갈 때 | 알림 텍스트 | 불가 |

차단 가능한 훅은 종료 코드 2를 반환하면 해당 동작을 막을 수 있다. 종료 코드 0이면 통과, 1이면 경고, 2면 차단이다.

### 7.2 훅 예제 — 위험한 명령 차단

`PreToolUse` 훅으로 특정 명령을 추가 검사한다.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "~/.claude/hooks/bash-guard.sh" }
        ]
      }
    ]
  }
}
```

훅 스크립트는 stdin으로 도구 호출 정보를 받는다.

```bash
#!/usr/bin/env bash
# ~/.claude/hooks/bash-guard.sh

input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command')

# 프로덕션 DB 접속 차단
if echo "$command" | grep -qE 'psql.*prod-db|mysql.*-h prod'; then
  echo "프로덕션 DB 직접 접속 차단" >&2
  exit 2
fi

# 강제 푸시 차단
if echo "$command" | grep -qE 'git push.*--force(\s|$)|git push.*-f(\s|$)'; then
  echo "force push 차단. 명시적 승인이 필요하다" >&2
  exit 2
fi

exit 0
```

`exit 2`로 끝내면 도구 호출이 막히고, stderr 메시지가 LLM에게 돌아간다. 모델은 그 메시지를 보고 다른 방법을 찾는다.

### 7.3 훅이 자주 무너지는 경우

훅 스크립트에 실행 권한이 없으면 조용히 실패한다. `chmod +x` 안 한 스크립트는 실행되지 않고, 에러도 잘 안 보인다. 디버깅하려면 `~/.claude/projects/<encoded>/` 아래 로그를 봐야 한다.

훅이 너무 오래 걸리면 하네스가 타임아웃을 걸고 그냥 진행한다. 타임아웃은 기본 60초다. 외부 API를 호출하는 훅은 타임아웃에 걸리기 쉽다.

훅 안에서 또 다른 Claude Code 세션을 호출하면 무한 재귀에 빠질 수 있다. 훅 안에서 `claude` CLI를 호출하지 않거나, 환경 변수로 재귀 호출을 감지해서 차단해야 한다.


## 8. MCP 서버 연결

### 8.1 연결 시점

MCP 서버는 Claude Code 시작 시점에 연결된다. settings.json의 `mcpServers` 키에 정의된 서버를 stdio 또는 SSE로 띄운다. stdio 방식은 서버를 자식 프로세스로 실행하고 stdin/stdout으로 통신한다.

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/work"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

연결이 끝나면 각 서버가 노출하는 도구 목록을 받아서 디스패처에 등록한다. 이때 도구 이름은 `mcp__<server>__<tool>` 형식으로 prefix가 붙는다. 같은 이름의 도구가 여러 서버에 있어도 충돌하지 않는다.

### 8.2 서버 죽었을 때

MCP 서버가 작업 도중 죽으면 그 서버의 도구를 호출할 때마다 연결 에러가 난다. Claude Code는 자동 재시작을 하지 않는다. 사용자가 `/mcp` 명령으로 재연결을 시도하거나, 세션을 다시 시작해야 한다.

서버가 자주 죽는 패턴이 있다. 서버 프로세스가 메모리를 누수해서 OOM으로 죽는 경우, 자식 프로세스가 좀비가 되어 통신이 멈추는 경우, stdio 버퍼가 막히는 경우다. 어떤 서버가 문제인지 파악하려면 `~/.claude/projects/<encoded>/` 아래 mcp 로그를 봐야 한다.


## 9. 백그라운드 작업과 Monitor

### 9.1 run_in_background

`Bash`와 `Agent` 도구는 `run_in_background: true` 옵션을 지원한다. 이 옵션을 켜면 프로세스가 백그라운드로 시작되고, 즉시 핸들이 반환된다. LLM은 다른 작업을 계속하다가 나중에 결과를 확인한다.

내부적으로는 자식 프로세스를 데몬화하고, stdout/stderr를 임시 파일에 리다이렉트한다. 프로세스 ID와 출력 파일 경로를 핸들로 반환한다.

### 9.2 Monitor 도구

백그라운드 프로세스의 출력을 스트리밍으로 보려면 `Monitor` 도구를 쓴다. Monitor는 출력 파일을 tail -f처럼 따라가면서, 새 줄이 추가될 때마다 LLM에게 알림으로 보낸다.

Monitor를 쓰지 않으면 LLM은 백그라운드 프로세스가 끝났는지 매번 폴링해서 확인해야 한다. 폴링은 토큰을 먹기 때문에 Monitor가 효율적이다. 다만 Monitor가 출력하는 알림도 결국 컨텍스트에 들어가므로, 출력이 너무 많은 프로세스(예: 빌드 로그)는 Monitor로 따라가지 말고 종료 후 한 번에 결과를 가져오는 편이 낫다.

### 9.3 작업 중단

`TaskStop` 도구로 백그라운드 작업을 중단한다. 내부적으로는 SIGTERM을 보내고, 일정 시간 후에도 종료되지 않으면 SIGKILL을 보낸다. 자식 프로세스를 가진 작업은 SIGTERM이 부모에게만 전달되어 자식이 좀비로 남을 수 있다. 빌드 도구나 dev 서버는 process group 단위로 종료해야 안전하다.


## 10. 워크트리 격리

`Agent` 도구의 `isolation: "worktree"` 옵션은 git worktree로 서브 에이전트를 격리한다. 자세한 내용은 [Claude_Code_Worktree.md](Claude_Code_Worktree.md)에 있다. 여기서는 하네스 관점에서 짚고 넘어갈 부분만 정리한다.

워크트리 격리가 켜지면 하네스는 다음 동작을 한다.

1. 임시 디렉토리에 `git worktree add`로 새 워크트리 생성
2. 서브 에이전트의 cwd를 그 디렉토리로 설정
3. 서브 에이전트 실행
4. 종료 시 변경사항이 없으면 워크트리 삭제, 있으면 경로와 브랜치를 결과에 포함해서 반환

서브 에이전트가 여러 개 동시에 돌아가도 각자 다른 워크트리에서 작업하기 때문에 파일 충돌이 안 난다. 다만 데이터베이스나 외부 API 같은 공유 리소스는 격리되지 않는다. 서브 에이전트 두 개가 동시에 같은 DB에 데이터를 쓰면 그건 워크트리로 막을 수 없다.


## 11. OS별 차이

| 항목 | macOS/Linux | Windows |
|------|-------------|---------|
| 셸 | bash/zsh | WSL2 필수 |
| 경로 구분자 | `/` | WSL 안에서 `/` |
| 훅 스크립트 | shebang 인식 | WSL 안에서 실행 |
| 권한 모드 | `default` 권장 | 동일 |
| MCP stdio | 기본 동작 | WSL 안에서 동일 |
| 프로세스 그룹 | setpgid 사용 | WSL 안에서 동일 |

Windows 네이티브에서 직접 돌리는 경로는 공식적으로 지원하지 않는다. PowerShell에서 시작하려는 시도는 빠르게 막힌다. 처음부터 WSL2 안에서 돌리는 게 안전하다.

macOS와 Linux 사이에서도 차이가 있다. macOS는 BSD 계열 유틸이라 `sed`, `find`, `xargs`의 동작이 GNU 계열과 다르다. 훅 스크립트를 macOS에서 만들었다가 Linux 컨테이너에서 안 도는 경우가 자주 있다. POSIX 호환 옵션만 쓰거나, 양쪽을 분기 처리한다.


## 12. 디버깅과 로그 위치

### 12.1 로그 위치

Claude Code는 모든 세션 로그를 `~/.claude/projects/<encoded>/` 아래에 저장한다. 인코딩된 디렉토리 이름은 cwd의 슬래시를 하이픈으로 치환한 형태다.

```
~/.claude/projects/-Users-me-work-api-server/
├── <session-id>.jsonl   # 메시지·도구 호출·결과 전체 로그
├── memory/              # 자동 메모리
│   ├── MEMORY.md
│   └── *.md
└── ...
```

`.jsonl` 파일은 한 줄에 하나의 이벤트가 들어있는 JSON Lines 형식이다. 각 줄은 timestamp, type, content를 포함한다. 어떤 도구가 언제 호출되었고 결과가 무엇이었는지 전부 기록된다.

특정 세션의 도구 호출만 보고 싶으면 `jq`로 필터링한다.

```bash
jq -r 'select(.type=="tool_use") | "\(.timestamp) \(.name) \(.input)"' \
  ~/.claude/projects/-Users-me-work-api-server/<session-id>.jsonl
```

### 12.2 디버그 모드

`claude --debug`로 시작하면 stderr에 추가 정보가 출력된다. 시스템 프롬프트의 일부, 도구 호출 직전의 상태, MCP 서버 응답 시간 등을 볼 수 있다. 출력이 많아서 평소 작업에는 끄고 쓰는데, 훅이 안 도는 이유나 MCP 연결이 늦는 이유를 추적할 때 유용하다.

`ANTHROPIC_LOG=debug` 환경변수를 추가로 설정하면 SDK 레벨 로그도 같이 나온다. 캐시 적중 여부, 토큰 사용량, 재시도 횟수가 찍힌다.

### 12.3 자주 마주치는 증상과 추적 순서

**도구가 호출되지 않는다** — settings.json의 `permissions.deny`에 매칭되는 룰이 있는지 확인. 그 다음 PreToolUse 훅이 종료 코드 2로 끝내고 있지 않은지 확인. 마지막으로 도구 이름이 LLM이 알고 있는 이름과 일치하는지 확인 (deferred tools는 ToolSearch가 먼저 필요하다).

**시스템 프롬프트에 추가한 지시가 무시된다** — CLAUDE.md의 어느 위치에 썼는지 확인. 사용자 전역과 프로젝트 둘 다 있으면 프로젝트가 이긴다. 그래도 무시되면 프롬프트 캐시가 stale 상태일 수 있다. 새 세션을 시작해서 비교한다.

**응답이 갑자기 느려진다** — `/context`로 컨텍스트 사용률을 본다. 75% 이상이면 압축이 곧 일어난다. 이미 압축이 일어났다면 캐시 미스라서 다음 한두 턴이 느리다.

**비용이 예상보다 많이 나온다** — 큰 도구 결과가 메시지 히스토리에 쌓이고 있을 가능성이 크다. `.jsonl` 로그에서 `tool_result`의 content 길이를 확인한다. 50KB가 넘는 결과가 여러 번 있으면 그게 누적되어서 매 턴마다 같은 토큰을 다시 보내고 있는 것이다. 서브 에이전트로 격리하거나, head_limit/limit 파라미터를 명시해서 결과 크기를 제한한다.

**MCP 서버 도구가 사라진다** — `/mcp` 명령으로 서버 상태를 본다. `disconnected`로 표시되면 자식 프로세스가 죽었다. 같은 프로젝트의 mcp 로그에서 마지막 에러를 확인한다.


## 13. 정리

Claude Code의 하네스는 일반적인 에이전트 하네스 위에 캐시 관리, deferred tool 시스템, 자동 메모리, 훅 체계를 얹은 구조다. 사용자가 보는 것은 CLI 인터페이스와 도구 호출이지만, 그 뒤에서는 시스템 프롬프트가 매번 조립되고, 권한 룰이 매칭되고, 컨텍스트가 압축되고, MCP 서버와 자식 프로세스가 관리된다.

내부 동작을 이해하면 디버깅이 빨라진다. 도구가 안 도는 이유, 응답이 느려지는 이유, 비용이 튀는 이유는 대부분 위에 정리한 메커니즘 중 하나에 걸려있다. `~/.claude/projects/<encoded>/` 아래 로그를 읽는 습관을 들이면 추측 없이 원인을 찾을 수 있다.
