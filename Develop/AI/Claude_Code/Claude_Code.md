---
title: Claude Code
tags: [ai, claude-code, anthropic, cli, agentic-coding]
updated: 2026-03-25
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

### 3.4 권한 모델

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

저장되는 정보:
- 사용자의 역할과 선호 (예: "한국어로 답변", "커밋은 수동으로만")
- 피드백 이력 (예: "테스트에서 DB 모킹하지 마")
- 프로젝트 관련 컨텍스트 (예: "3월 5일 이후 머지 프리즈")
- 외부 리소스 참조 (예: "버그 트래킹은 Linear INGEST 프로젝트")

"이거 기억해줘"라고 말하면 즉시 저장하고, "잊어줘"라고 하면 삭제한다. 명시적으로 지시하지 않아도 대화 중 반복되는 패턴이나 교정 사항은 자동으로 메모리에 반영된다.

### 5.3 MCP 서버 (Model Context Protocol)

Claude Code에 외부 도구를 연결하는 프로토콜이다.

```json
// .claude/settings.json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "postgresql://localhost:5432/mydb"
      }
    }
  }
}
```

연결하고 나면 "users 테이블에서 최근 가입자 수 뽑아줘" 같은 자연어 요청이 가능해진다.

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
