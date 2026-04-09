---
title: Claude Code
tags: [ai, claude-code, anthropic, cli, agentic-coding]
updated: 2026-04-09
---

# Claude Code

## 1. Claude Code란

Anthropic이 만든 CLI 기반 에이전틱 코딩 도구다. 터미널에서 자연어로 지시하면 코드를 읽고, 수정하고, 생성하고, 테스트까지 자율적으로 수행한다.

2025년 CLI로 시작해서, 현재는 **CLI, VS Code/JetBrains 확장, Desktop App(Mac/Windows), Web App(claude.ai/code)** 네 가지 형태로 사용할 수 있다.

### 1.1 핵심 특징

- **터미널 네이티브**: 별도 IDE 없이 터미널에서 바로 사용
- **에이전틱 실행**: 탐색 → 계획 → 구현 → 검증까지 자율 수행
- **파일시스템 직접 접근**: 프로젝트의 모든 파일을 읽고 수정
- **Git 통합**: 커밋, PR 생성, 브랜치 관리를 자연어로 처리
- **멀티 플랫폼**: CLI, IDE 확장, Desktop App, Web App 지원

### 1.2 다른 AI 코딩 도구와의 비교

| 특징 | Claude Code | GitHub Copilot | Cursor |
|------|------------|----------------|--------|
| **인터페이스** | CLI + IDE + Desktop + Web | IDE 플러그인 | 전용 IDE |
| **작동 방식** | 에이전틱 (자율 수행) | 자동완성 + Chat | 에이전틱 + 에디터 |
| **파일 접근** | 전체 프로젝트 | 현재 파일 중심 | 전체 프로젝트 |
| **터미널 명령** | 직접 실행 | 제한적 | 가능 |
| **Git 통합** | 네이티브 | 제한적 | 부분 지원 |
| **커스터마이징** | CLAUDE.md, Hooks, MCP | 설정 파일 | Rules, MCP |
| **비용 모델** | API 사용량 / Max 구독 | 월 구독 | 월 구독 |

---

## 2. 설치 및 설정

### 2.1 시스템 요구사항

- **Node.js**: 18 이상
- **OS**: macOS, Linux, Windows (WSL2 필수)
- **Git**: 프로젝트 내에서 사용 시 필요

### 2.2 설치

```bash
# npm으로 글로벌 설치
npm install -g @anthropic-ai/claude-code

# 설치 확인
claude --version
```

### 2.3 인증

```bash
# 프로젝트 디렉토리에서 실행
cd my-project
claude
```

첫 실행 시 인증 절차가 진행된다.

| 방식 | 설명 |
|------|------|
| **OAuth (기본)** | Anthropic Console 계정으로 브라우저 인증 |
| **API Key** | `ANTHROPIC_API_KEY` 환경 변수 설정 |
| **Max 플랜** | Anthropic Console에서 직접 연동 |

```bash
# API Key 방식
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

---

## 3. 핵심 개념

### 3.1 에이전틱 코딩

기존 AI 코딩 도구가 코드 자동완성에 집중한다면, Claude Code는 에이전트로서 자율적으로 작업을 수행한다.

```
사용자: "로그인 API에 rate limiting 추가해줘"

Claude Code의 동작:
1. 프로젝트 구조 탐색 (Glob, Grep)
2. 기존 인증 코드 분석 (Read)
3. rate limiting 미들웨어 구현 (Write/Edit)
4. 관련 테스트 코드 수정 (Edit)
5. 테스트 실행 (Bash)
6. 결과 보고
```

### 3.2 컨텍스트 윈도우

대화가 길어질수록 컨텍스트 윈도우(토큰 한도)를 소모한다. 파일 읽기 결과, 명령 실행 결과 등이 모두 쌓인다.

- 컨텍스트가 가득 차면 이전 대화를 자동 압축
- `/compact`로 수동 압축 가능
- `/clear`로 대화 초기화

서로 다른 작업을 할 때는 `/clear`로 초기화하는 게 정확도에 도움이 된다.

### 3.3 도구 시스템 (Tools)

Claude Code는 내부적으로 다양한 도구를 사용한다.

| 도구 | 역할 |
|------|------|
| **Read** | 파일 읽기 (이미지, PDF 포함) |
| **Write** | 새 파일 생성 |
| **Edit** | 기존 파일 수정 |
| **Bash** | 터미널 명령 실행 |
| **Glob** | 파일 패턴 검색 |
| **Grep** | 코드 내용 검색 |
| **WebFetch** | 웹 페이지 가져오기 |
| **WebSearch** | 웹 검색 |
| **Agent** | 서브 에이전트 실행 (병렬 탐색) |
| **NotebookEdit** | Jupyter 노트북 편집 |
| **TodoWrite** | 작업 목록 관리 |

### 3.4 하네스 아키텍처

Claude Code는 LLM이 도구를 직접 실행하는 게 아니다. **하네스(Harness)**라는 실행 환경이 중간에 있고, 이 하네스가 도구 호출을 가로채서 권한 검사, 샌드박스 적용, 실행, 결과 반환까지 전부 관리한다.

#### 전체 구조

```mermaid
graph TB
    subgraph 사용자 환경
        A[사용자 입력]
    end

    subgraph 하네스 Harness
        B[메시지 루프]
        C[도구 호출 파서]
        D[권한 검사]
        E[샌드박스 레이어]
        F[도구 실행기]
        G[결과 수집기]
        H[Hook 실행기]
    end

    subgraph LLM
        I[Claude 모델]
    end

    subgraph 도구
        J[Read / Write / Edit]
        K[Bash]
        L[Glob / Grep]
        M[Agent 서브에이전트]
        N[MCP 서버 도구]
    end

    A --> B
    B --> I
    I -->|도구 호출 요청| C
    C --> H
    H -->|PreToolUse Hook| D
    D -->|승인| E
    D -->|거부| G
    E --> F
    F --> J & K & L & M & N
    J & K & L & M & N -->|실행 결과| G
    G --> H
    H -->|PostToolUse Hook| B
    B -->|최종 응답| A
```

핵심은 LLM이 "Read로 파일 읽고 싶다"고 요청하면, 하네스가 그 요청을 받아서 권한 확인 → 샌드박스 적용 → 실행 → 결과 전달 순서로 처리한다는 것이다. LLM은 실행 결과만 돌려받는다.

#### 도구 호출 처리 파이프라인

하나의 도구 호출이 실행되는 과정을 단계별로 보면 다음과 같다.

```mermaid
flowchart LR
    A[LLM 응답에서<br/>도구 호출 파싱] --> B[PreToolUse<br/>Hook 실행]
    B --> C{Hook 결과}
    C -->|block| H[실행 차단<br/>→ 결과 반환]
    C -->|pass / 없음| D{권한 검사}
    D -->|deny 매칭| H
    D -->|allow 매칭| F[도구 실행]
    D -->|매칭 없음| E[사용자에게<br/>승인 요청]
    E -->|승인| F
    E -->|거부| H
    F --> G[PostToolUse<br/>Hook 실행]
    G --> I[결과를 LLM<br/>컨텍스트에 추가]
```

이 파이프라인에서 주목할 점:

- **Hook이 권한 검사보다 먼저 실행된다.** PreToolUse Hook에서 `block`을 반환하면 권한 검사 자체를 건너뛰고 바로 차단한다. 팀 정책을 Hook으로 강제할 수 있는 이유다.
- **deny가 allow보다 우선한다.** settings.json의 deny 목록에 매칭되면 allow에 있어도 차단된다.
- **매칭되는 규칙이 없으면 사용자에게 물어본다.** Ask Mode에서는 대부분의 도구 호출이 여기에 해당한다.

#### 권한 모드별 동작

```mermaid
flowchart TD
    A[도구 호출 요청] --> B{권한 모드}

    B -->|Ask Mode| C{allow 목록?}
    C -->|매칭| F[자동 승인]
    C -->|미매칭| D[사용자에게 승인 요청]

    B -->|Auto-Accept| E{도구 종류}
    E -->|읽기 도구<br/>Read, Glob, Grep| F
    E -->|쓰기 도구<br/>Write, Edit, Bash| D

    B -->|Full Auto| F

    D -->|승인| F
    D -->|거부| G[실행 차단]
    F --> H[샌드박스 적용 후 실행]
```

| 모드 | 읽기 도구 | 쓰기 도구 | 적합한 상황 |
|------|----------|----------|------------|
| Ask Mode | 승인 필요 | 승인 필요 | 처음 사용하거나 민감한 프로젝트에서 작업할 때 |
| Auto-Accept | 자동 승인 | 승인 필요 | 일상적인 개발 작업. 파일 탐색은 자유롭게, 수정은 확인하면서 진행 |
| Full Auto | 자동 승인 | 자동 승인 | 신뢰할 수 있는 환경에서 반복 작업을 돌릴 때. CI/CD와 비슷한 맥락 |

Full Auto 모드에서도 `settings.json`의 deny 목록은 여전히 적용된다. `rm -rf`를 deny에 넣어두면 Full Auto에서도 차단된다.

#### 샌드박스 계층

하네스는 도구 실행 시 여러 겹의 샌드박스를 적용한다.

```mermaid
graph TB
    subgraph "샌드박스 계층 구조"
        A["프로세스 격리<br/>각 Bash 명령은 독립 프로세스로 실행"]
        B["파일시스템 범위 제한<br/>프로젝트 디렉토리 기준으로 접근 범위 제한"]
        C["네트워크 제한<br/>Bash 명령의 외부 네트워크 접근 제한"]
        D["시간 제한 (Timeout)<br/>Bash 기본 2분, 최대 10분"]
    end

    A --> B --> C --> D

    style A fill:#2d2d2d,stroke:#666,color:#e0e0e0
    style B fill:#2d2d2d,stroke:#666,color:#e0e0e0
    style C fill:#2d2d2d,stroke:#666,color:#e0e0e0
    style D fill:#2d2d2d,stroke:#666,color:#e0e0e0
```

| 계층 | 적용 대상 | 동작 |
|------|----------|------|
| 프로세스 격리 | Bash 도구 | 각 명령이 별도 프로세스에서 실행. 이전 명령의 셸 상태(변수, alias)가 유지되지 않는다 |
| 파일시스템 범위 | Read, Write, Edit | 프로젝트 디렉토리 바깥의 파일 접근을 제한한다 |
| 네트워크 제한 | Bash 도구 | 샌드박스 모드에서 외부 네트워크 요청을 차단한다. `dangerouslyDisableSandbox` 옵션으로 해제 가능하지만 권장하지 않는다 |
| 시간 제한 | Bash 도구 | 기본 2분(120초) 타임아웃. 빌드나 테스트처럼 오래 걸리는 작업은 최대 10분까지 설정 가능 |

Bash 도구의 `dangerouslyDisableSandbox` 옵션이 이름에 "dangerously"가 들어간 이유가 있다. 샌드박스를 끄면 네트워크 제한이 풀리면서 외부에 요청을 보낼 수 있게 된다. CI 환경이 아니면 쓸 일이 거의 없다.

### 3.5 권한 모델

도구 실행 전 사용자 승인을 요청하는 구조다.

```
세 가지 모드:
1. Ask Mode (기본)    → 모든 도구 사용 시 승인 요청
2. Auto-Accept Mode  → 읽기 도구는 자동, 쓰기는 승인 요청
3. Full Auto Mode    → 모든 도구 자동 승인 (주의 필요)
```

`settings.json`에서 특정 명령을 허용하거나 차단할 수 있다.

```json
{
  "permissions": {
    "allow": ["Bash(npm test)", "Bash(npm run lint)"],
    "deny": ["Bash(rm -rf *)", "Bash(git push --force)"]
  }
}
```

#### allow/deny 패턴 상세

패턴은 `도구명(인자)` 형식이다. 괄호 안에 들어가는 문자열은 prefix 매칭으로 동작한다. `Bash(npm test)`를 allow에 넣으면 `npm test`, `npm test -- --coverage` 모두 자동 승인된다.

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Edit",
      "Write",
      "Glob",
      "Grep",
      "Bash(npm test)",
      "Bash(npm run lint)",
      "Bash(npm run build)",
      "Bash(git status)",
      "Bash(git diff)",
      "Bash(git log)",
      "Bash(cd )"
    ],
    "deny": [
      "Bash(rm -rf)",
      "Bash(git push --force)",
      "Bash(git reset --hard)",
      "Bash(curl)",
      "Bash(wget)"
    ]
  }
}
```

패턴 작성 시 주의할 점:

- **도구명만 쓰면 해당 도구 전체 허용**: `"Read"`는 모든 파일 읽기를 자동 승인한다. 특정 경로만 허용하는 건 안 된다.
- **Bash는 prefix 매칭**: `"Bash(git)"` 하나면 `git status`, `git push --force` 모두 통과한다. `git push --force`를 막으려면 deny에 별도로 넣어야 한다.
- **deny가 allow보다 우선**: 같은 명령이 양쪽에 매칭되면 deny가 이긴다.
- **설정 파일 우선순위**: `.claude/settings.local.json` > `.claude/settings.json` > `~/.claude/settings.json` 순서로 병합된다. deny는 어디에 있든 최종적으로 합산된다.

실무에서 쓸만한 설정 조합:

```json
// .claude/settings.json (팀 공유용)
{
  "permissions": {
    "deny": [
      "Bash(rm -rf)",
      "Bash(git push --force)",
      "Bash(git reset --hard)",
      "Bash(docker rm)",
      "Bash(docker rmi)"
    ]
  }
}
```

```json
// .claude/settings.local.json (개인용)
{
  "permissions": {
    "allow": [
      "Read",
      "Edit",
      "Glob",
      "Grep",
      "Bash(npm )",
      "Bash(git status)",
      "Bash(git diff)",
      "Bash(git log)"
    ]
  }
}
```

팀 공유 설정에는 deny 위주로 위험한 명령을 차단하고, 개인 설정에는 allow로 자주 쓰는 도구를 자동 승인하는 패턴이 실용적이다.

---

## 4. 사용 환경

### 4.1 CLI (터미널)

가장 기본적인 사용 방식이다. 터미널에서 `claude` 명령으로 실행한다.

```bash
claude                          # 대화형 모드
claude "이 프로젝트 구조 설명해줘"  # 원샷 모드
claude --print "코드 리뷰해줘"    # 출력만 (비대화형)
```

### 4.2 Desktop App (Mac / Windows)

별도 설치 가능한 데스크탑 앱이다. CLI와 동일한 기능을 GUI 환경에서 사용한다. 터미널에 익숙하지 않은 팀원과 협업할 때 유용하다.

### 4.3 Web App (claude.ai/code)

브라우저에서 접속해서 사용하는 방식이다. 별도 설치 없이 쓸 수 있어서 빠르게 확인하거나 모바일에서 접근할 때 편하다.

### 4.4 IDE 확장

**VS Code**:
```bash
# Extensions에서 "Claude Code" 검색 후 설치
code --install-extension anthropic.claude-code
```

- 터미널 패널에서 Claude Code 실행
- 에디터에서 파일 변경 사항 실시간 확인
- Diff 뷰에서 변경 사항 리뷰

**JetBrains**:
```
Settings → Plugins → "Claude Code" 검색 → Install
```

---

## 5. 주요 기능

### 5.1 CLAUDE.md (프로젝트 설정)

대화가 시작될 때 자동으로 로드되는 설정 파일이다. 프로젝트 컨텍스트와 규칙을 담는다.

```
~/.claude/CLAUDE.md          ← 전역 (모든 프로젝트)
프로젝트루트/CLAUDE.md        ← 프로젝트 레벨 (git 공유 가능)
프로젝트루트/.claude/CLAUDE.md ← 프로젝트 로컬 (개인 설정)
하위폴더/CLAUDE.md            ← 폴더 레벨 (해당 폴더 작업 시)
```

`/init` 명령으로 현재 프로젝트의 CLAUDE.md 초안을 자동 생성할 수 있다.

### 5.2 Auto Memory

CLAUDE.md가 사용자가 직접 작성하는 설정이라면, Auto Memory는 Claude Code가 대화 중에 학습한 내용을 자동으로 저장하는 기능이다.

저장 위치는 `~/.claude/projects/{project}/memory/`이고, 대화가 끝나도 다음 세션에서 기억이 유지된다.

"이거 기억해줘"라고 말하면 즉시 저장하고, "잊어줘"라고 하면 삭제한다. 명시적으로 지시하지 않아도 대화 중 반복되는 패턴이나 교정 사항은 자동으로 메모리에 반영된다.

#### 메모리 타입

메모리는 네 가지 타입으로 분류된다. 각 타입마다 저장하는 정보의 성격이 다르다.

| 타입 | 저장 내용 | 예시 |
|------|----------|------|
| **user** | 사용자 역할, 선호, 지식 수준 | "한국어로 답변", "Go 10년차, React는 처음" |
| **feedback** | 작업 방식에 대한 교정·확인 | "테스트에서 DB 모킹하지 마", "요약 생략해" |
| **project** | 프로젝트 일정, 의사결정, 제약사항 | "3월 5일 이후 머지 프리즈", "인증 리팩토링은 법무팀 요청" |
| **reference** | 외부 시스템 위치 정보 | "버그 트래킹은 Linear INGEST 프로젝트" |

#### 파일 구조

메모리 디렉토리 안에는 `MEMORY.md`(인덱스)와 개별 메모리 파일들이 있다.

```
~/.claude/projects/{project-hash}/memory/
├── MEMORY.md                  # 인덱스 파일 (전체 목록)
├── user_role.md               # user 타입 메모리
├── feedback_testing.md        # feedback 타입 메모리
├── project_merge_freeze.md    # project 타입 메모리
└── reference_linear.md        # reference 타입 메모리
```

개별 메모리 파일은 YAML frontmatter를 가진다.

```markdown
---
name: 테스트 방침
description: 통합 테스트에서 DB 모킹 금지
type: feedback
---

통합 테스트에서 DB를 모킹하지 말 것.

**Why:** 모킹된 테스트가 통과했는데 프로덕션 마이그레이션에서 장애 발생한 적 있음.

**How to apply:** 테스트 코드 작성 시 실제 DB 연결을 사용한다.
```

`MEMORY.md`는 각 메모리 파일을 한 줄로 가리키는 인덱스다. 200줄 넘으면 잘리니까 항목당 한 줄로 유지해야 한다.

```markdown
# 프로젝트 메모리

- [사용자 역할](user_role.md) — 백엔드 개발자, 한국어 선호
- [테스트 방침](feedback_testing.md) — 통합 테스트에서 DB 모킹 금지
- [머지 프리즈](project_merge_freeze.md) — 3월 5일 이후 비긴급 PR 보류
```

#### 메모리에 저장하면 안 되는 것

코드 패턴, 아키텍처, 파일 경로, git 히스토리 같은 건 코드나 `git log`에서 바로 확인할 수 있으니 메모리에 넣을 필요 없다. 디버깅 해결 방법도 마찬가지다 — 수정 내용은 코드에 있고, 맥락은 커밋 메시지에 있다. CLAUDE.md에 이미 적힌 내용을 중복으로 저장하는 것도 낭비다.

#### 메모리 관리

메모리가 쌓이면 오래된 정보가 현재 상태와 맞지 않는 경우가 생긴다. Claude Code는 메모리를 참조하기 전에 해당 내용이 아직 유효한지 확인하도록 되어 있지만, 직접 정리해주는 게 확실하다.

```bash
# 메모리 디렉토리 직접 확인
ls ~/.claude/projects/*/memory/

# 특정 메모리 삭제 (대화 중)
> "머지 프리즈 메모리 삭제해줘"
```

project 타입 메모리는 특히 유효기간이 짧다. 일정이나 의사결정은 시간이 지나면 바뀌니까 주기적으로 확인하는 게 좋다.

### 5.3 MCP 서버 (Model Context Protocol)

Claude Code에 외부 도구를 연결하는 프로토콜이다. MCP 서버를 등록하면 Claude Code가 해당 서버의 도구를 자동으로 인식하고 사용한다.

#### 기본 설정 방법

`.claude/settings.json`의 `mcpServers` 필드에 서버를 등록한다.

```json
{
  "mcpServers": {
    "서버이름": {
      "command": "실행할 명령",
      "args": ["인자 목록"],
      "env": {
        "환경변수": "값"
      }
    }
  }
}
```

설정 파일 위치에 따라 적용 범위가 달라진다.

| 위치 | 범위 |
|------|------|
| `~/.claude/settings.json` | 모든 프로젝트에서 사용 |
| `.claude/settings.json` | 해당 프로젝트 전용 (git 공유 가능) |
| `.claude/settings.local.json` | 해당 프로젝트 전용 (개인) |

DB 접속 정보가 포함된 MCP 설정은 `settings.local.json`에 넣는다. git에 올라가면 안 되니까.

#### 자주 쓰는 MCP 서버 예시

**PostgreSQL** — DB 쿼리를 자연어로 실행:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/mydb"
      }
    }
  }
}
```

등록하면 "users 테이블에서 최근 가입자 수 뽑아줘" 같은 요청이 가능해진다.

**GitHub** — 이슈, PR, 리포지토리 조작:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
      }
    }
  }
}
```

**파일시스템** — 특정 디렉토리에 대한 읽기/쓰기 접근:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    }
  }
}
```

**Slack** — 채널 메시지 읽기/쓰기:

```json
{
  "mcpServers": {
    "slack": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-...",
        "SLACK_TEAM_ID": "T0..."
      }
    }
  }
}
```

#### 커스텀 MCP 서버 연결

직접 만든 MCP 서버도 같은 방식으로 등록한다. 실행 가능한 바이너리나 스크립트 경로를 command에 넣으면 된다.

```json
{
  "mcpServers": {
    "internal-api": {
      "command": "node",
      "args": ["/home/user/mcp-servers/internal-api/index.js"],
      "env": {
        "API_BASE_URL": "https://internal.company.com/api",
        "API_TOKEN": "..."
      }
    }
  }
}
```

Python으로 만든 서버:

```json
{
  "mcpServers": {
    "ml-pipeline": {
      "command": "python",
      "args": ["/home/user/mcp-servers/ml-pipeline/server.py"],
      "env": {
        "MODEL_REGISTRY_URL": "https://mlflow.internal.com"
      }
    }
  }
}
```

커스텀 서버 연결 시 주의사항:

- **command 경로**: `node`, `python` 같은 명령이 PATH에 있어야 한다. `nvm`이나 `pyenv`를 쓰는 환경에서는 절대 경로(`/usr/local/bin/node`)를 쓰는 게 안전하다.
- **stdio 통신**: MCP 서버는 stdin/stdout으로 JSON-RPC 메시지를 주고받는다. 서버가 stdout에 로그를 찍으면 통신이 깨진다. 로그는 반드시 stderr로 보내야 한다.
- **서버 이름 충돌**: `mcpServers`의 키가 서버 이름이 된다. 같은 이름으로 두 개 등록하면 나중 것이 덮어쓴다.
- **타임아웃**: 서버 시작이 느리면 Claude Code가 연결 실패로 판단한다. 서버 초기화에 시간이 걸리는 경우(DB 커넥션 풀 생성 등) 초기화를 비동기로 처리하거나 lazy하게 하는 게 낫다.

#### MCP 서버 디버깅

서버가 제대로 동작하는지 확인하는 방법:

**1단계 — 서버 단독 실행 확인:**

```bash
# 서버를 직접 실행해서 프로세스가 정상 시작되는지 확인
npx -y @modelcontextprotocol/server-postgres
# Ctrl+C로 종료
```

시작 시 에러 메시지가 나오면 환경 변수나 의존성 문제다.

**2단계 — Claude Code에서 연결 상태 확인:**

```bash
# Claude Code 실행 후
> /doctor
```

`/doctor`가 MCP 서버 연결 상태를 보여준다. 연결 실패 시 에러 메시지가 표시된다.

**3단계 — 서버 로그 확인:**

```bash
# MCP 서버 로그 위치
ls ~/.claude/logs/mcp*.log
```

`stderr`로 보낸 로그가 여기에 남는다. 연결은 됐는데 도구 호출이 실패하는 경우 이 로그에서 원인을 찾을 수 있다.

**자주 발생하는 문제:**

| 증상 | 원인 | 해결 |
|------|------|------|
| 서버가 도구 목록에 안 보임 | command 경로 문제 | 절대 경로로 변경 |
| 연결 후 바로 끊김 | stdout에 로그 출력 | stderr로 변경 |
| 도구 호출 시 타임아웃 | 서버 응답 지연 | 서버 측 처리 시간 확인 |
| 환경 변수 인식 안 됨 | env 필드 누락 | settings.json의 env 확인 |
| npx 실행 실패 | 패키지 버전 문제 | `npx -y 패키지@latest`로 버전 지정 |

### 5.4 훅 시스템 (Hooks)

도구 실행 전후에 자동으로 실행되는 셸 명령이다.

| 훅 이벤트 | 실행 시점 |
|-----------|-----------|
| **PreToolUse** | 도구 실행 전 |
| **PostToolUse** | 도구 실행 후 |
| **Notification** | 알림 발생 시 |
| **Stop** | Claude 응답 완료 후 |

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [{
          "type": "command",
          "command": "npx prettier --write $CLAUDE_FILE_PATH"
        }]
      }
    ]
  }
}
```

파일 수정할 때마다 Prettier가 자동으로 돌게 된다.

### 5.5 Worktree (병렬 작업 공간)

Git worktree를 활용해서 현재 작업을 중단하지 않고 별도 브랜치에서 독립적인 작업을 수행하는 기능이다.

```
사용자: "현재 작업은 그대로 두고, 별도 브랜치에서 로그인 버그 수정해줘"

Claude Code:
1. git worktree로 새 작업 디렉토리 생성
2. 해당 디렉토리에서 버그 수정
3. 완료 후 결과 보고
4. 원래 작업 디렉토리는 그대로 유지
```

현재 진행 중인 피처 개발을 멈추지 않고 핫픽스를 처리해야 할 때 쓴다. `/enter-worktree`로 진입하고 `/exit-worktree`로 빠져나온다.

### 5.6 Schedule / Remote Agent

Claude Code를 원격에서 cron 스케줄로 실행하는 기능이다. 사람이 없어도 정해진 시간에 자동으로 작업을 수행한다.

```bash
# 매일 오전 9시에 의존성 업데이트 체크
claude schedule create \
  --cron "0 9 * * *" \
  --prompt "package.json의 outdated 의존성을 확인하고 PR로 올려줘"

# 등록된 스케줄 확인
claude schedule list
```

활용 예시:
- 매일 의존성 보안 취약점 스캔 → 이슈 자동 생성
- 매주 코드 품질 리포트 생성
- 새 이슈가 등록되면 자동으로 분석 코멘트 달기

Remote Agent는 로컬 머신이 아닌 클라우드에서 실행되므로, 노트북을 닫아도 작업이 계속 진행된다.

### 5.7 Git 통합

Git 작업을 자연어로 처리한다.

```bash
# 커밋
> "변경 사항 커밋해줘"
# → 변경 내용 분석 → 커밋 메시지 자동 생성 → 커밋

# PR 생성
> "이 브랜치로 PR 만들어줘"
# → 커밋 히스토리 분석 → PR 제목/본문 작성 → gh pr create
```

### 5.8 슬래시 명령어

| 명령어 | 설명 |
|--------|------|
| `/clear` | 대화 히스토리 초기화 |
| `/compact` | 대화 컨텍스트 압축 |
| `/cost` | 현재 세션 토큰 사용량 및 비용 확인 |
| `/config` | 설정 열기/수정 |
| `/init` | CLAUDE.md 초기화 |
| `/commit` | 변경 사항 커밋 |
| `/review` | 코드 리뷰 |
| `/doctor` | 설치 상태 진단 |
| `/status` | 현재 상태 표시 |
| `/bug` | 버그 리포트 생성 |
| `/login` | 인증 |
| `/logout` | 인증 해제 |

---

## 6. 헤드리스 모드와 CI/CD 연동

### 6.1 기본 사용법

대화형 UI 없이 실행하는 모드다. CI/CD 파이프라인이나 스크립트에서 사용한다.

```bash
# --print: 결과만 stdout으로 출력
claude --print "이 프로젝트의 테스트 커버리지 분석해줘"

# stdin으로 입력 전달
cat error.log | claude --print "이 에러 로그 분석해줘"

# --dangerously-skip-permissions: 권한 확인 생략 (CI 전용)
claude --print --dangerously-skip-permissions "테스트 실행해줘"
```

`--dangerously-skip-permissions`는 이름 그대로 위험하다. 신뢰할 수 있는 CI 환경에서만 사용해야 한다.

### 6.2 GitHub Actions 연동

PR이 올라올 때 자동으로 코드 리뷰를 수행하는 워크플로우다.

```yaml
# .github/workflows/claude-review.yml
name: Claude Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Claude Code
        run: npm install -g @anthropic-ai/claude-code

      - name: Run Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          DIFF=$(git diff origin/main...HEAD)
          echo "$DIFF" | claude --print \
            "이 diff를 리뷰해줘. 버그, 보안 이슈, 성능 문제를 중심으로."
```

### 6.3 커밋 메시지 자동 생성

pre-commit hook이나 CI에서 커밋 메시지 품질을 자동으로 검증하는 패턴이다.

```bash
#!/bin/bash
# scripts/generate-commit-msg.sh

STAGED=$(git diff --cached)
if [ -z "$STAGED" ]; then
  echo "스테이징된 변경사항 없음"
  exit 1
fi

MSG=$(echo "$STAGED" | claude --print \
  "이 diff에 대한 conventional commit 메시지를 한 줄로 생성해줘. 메시지만 출력해.")

git commit -m "$MSG"
```

### 6.4 테스트 실패 자동 분석

CI에서 테스트가 실패했을 때 원인을 분석하는 스크립트다.

```bash
#!/bin/bash
# scripts/analyze-test-failure.sh

TEST_OUTPUT=$(npm test 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "$TEST_OUTPUT" | claude --print \
    "테스트 실패 로그다. 실패 원인과 수정 방향을 분석해줘."
fi
```

### 6.5 주요 플래그

| 플래그 | 설명 |
|--------|------|
| `--print` | 비대화형 모드. 결과를 stdout으로 출력 |
| `--dangerously-skip-permissions` | 권한 확인 생략 |
| `--model` | 사용할 모델 지정 |
| `--max-turns` | 최대 대화 턴 수 제한 |
| `--output-format json` | JSON 형식으로 출력 |

`--output-format json`을 쓰면 다른 도구와 파이프라인으로 연결하기 편하다.

```bash
claude --print --output-format json "package.json 의존성 분석해줘" \
  | jq '.result'
```

---

## 7. 설정

### 7.1 settings.json

설정 파일은 두 단계로 나뉜다.

| 위치 | 범위 |
|------|------|
| `~/.claude/settings.json` | 사용자 전역 |
| `.claude/settings.json` | 프로젝트 레벨 (git 공유 가능) |
| `.claude/settings.local.json` | 프로젝트 로컬 (개인 전용) |

### 7.2 환경 변수

| 환경 변수 | 설명 |
|-----------|------|
| `ANTHROPIC_API_KEY` | API 인증 키 |
| `CLAUDE_CODE_MAX_TURNS` | 최대 대화 턴 수 (헤드리스 모드) |
| `CLAUDE_CODE_USE_BEDROCK` | AWS Bedrock 사용 (`1`) |
| `CLAUDE_CODE_USE_VERTEX` | GCP Vertex AI 사용 (`1`) |

### 7.3 모델 선택

```bash
claude                            # 기본 모델 (Sonnet)
claude --model claude-opus-4-6    # 복잡한 설계 작업
claude --model claude-sonnet-4-6  # 일반 개발 (기본값)
claude --model claude-haiku-4-5   # 단순 작업, 빠른 응답
```

세션 중에 `/model` 명령이나 Shift+Tab으로 모델을 전환할 수 있다.

---

## 8. 실전에서 겪는 문제들

### 8.1 컨텍스트 초과

대용량 파일을 여러 개 읽거나 대화가 길어지면 컨텍스트 윈도우를 초과한다. Claude가 이전에 읽은 내용을 잊어버리거나 응답 품질이 떨어진다.

대응 방법:
- `/compact`로 압축 후 작업 계속
- 한 번에 하나의 파일/함수 단위로 요청
- 작업 전환 시 `/clear`

### 8.2 파일 수정 충돌

Claude가 파일을 수정하는 도중에 IDE에서도 같은 파일을 편집하면 충돌이 생긴다. Claude Code가 수정 중인 파일은 건드리지 않는 게 좋다. IDE 확장을 쓰면 Diff 뷰에서 변경 사항을 확인할 수 있어서 이 문제가 줄어든다.

### 8.3 비용이 예상보다 많이 나올 때

"전체 프로젝트 분석해줘" 같은 넓은 범위 요청이 주된 원인이다. 파일·함수 단위로 범위를 좁히면 비용이 크게 줄어든다. `/cost`로 현재 세션 비용을 수시로 확인하는 습관이 도움된다.

### 8.4 헤드리스 모드에서 무한 루프

`--dangerously-skip-permissions`로 실행할 때 Claude가 같은 작업을 반복하는 경우가 있다. `--max-turns` 플래그로 최대 턴 수를 제한하면 방지된다.

```bash
# 최대 10턴으로 제한
claude --print --dangerously-skip-permissions --max-turns 10 "테스트 수정해줘"
```

---

## 참고

- [Claude Code 공식 문서](https://docs.anthropic.com/en/docs/claude-code)
- [Anthropic 공식 사이트](https://www.anthropic.com)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
