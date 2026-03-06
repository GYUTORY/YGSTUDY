---
title: OpenAI Codex 사용법 및 핵심 개념
tags: [ai, codex, openai, cli, agentic-coding]
updated: 2026-03-01
---

# OpenAI Codex

## 1. Codex란

**Codex**는 OpenAI가 개발한 **에이전틱 코딩 도구**이다. CLI, 웹 앱, IDE 확장, 클라우드 플랫폼을 모두 아우르며, 코드를 읽고 수정하고 실행까지 자율적으로 수행한다. Apache-2.0 라이선스로 **오픈소스**로 공개되어 있다.

> ⚠️ **구분**: 2021년의 "Codex 모델"(GPT-3 기반, GitHub Copilot 초기 엔진, 2023년 폐지)과는 다른 **새로운 Codex**(2025년 출시)이다.

### 1.1 주요 특징

- **오픈소스**: Apache-2.0 라이선스 ([github.com/openai/codex](https://github.com/openai/codex))
- **Rust 기반**: Node.js 런타임 불필요, 네이티브 바이너리 설치
- **샌드박스 보안**: OS 레벨 격리 실행 (macOS Seatbelt, Linux Landlock)
- **로컬 + 클라우드**: 로컬 터미널 실행 & Codex Cloud 원격 작업
- **멀티 에이전트**: 병렬 서브 에이전트로 동시 작업 가능
- **세션 관리**: 세션 저장, 이어하기(resume), 분기(fork) 지원
- **이미지 입력**: 스크린샷이나 디자인 스펙을 프롬프트에 첨부 가능

### 1.2 다른 AI 코딩 도구와의 비교

| 특징 | Codex | Claude Code | Grok |
|------|-------|------------|------|
| **개발사** | OpenAI | Anthropic | xAI |
| **오픈소스** | Apache-2.0 | 비공개 | CLI 일부 |
| **언어** | Rust | TypeScript | - |
| **CLI** | codex (TUI) | claude | Grok Build |
| **클라우드 실행** | Codex Cloud | 없음 | 계획 중 |
| **멀티 에이전트** | 지원 (실험적) | 없음 | 없음 |
| **샌드박스** | Seatbelt/Landlock | OS 레벨 | - |
| **세션 관리** | resume, fork | 세션 기반 | - |
| **프로젝트 설정** | AGENTS.md | CLAUDE.md | - |
| **MCP 지원** | 지원 | 지원 | - |
| **가격 모델** | 구독($20/월~) 또는 API | API 사용량 기반 | API 사용량 기반 |

---

## 2. 설치 및 설정

### 2.1 시스템 요구사항

- **macOS**: 완전 지원 (Seatbelt 샌드박스)
- **Linux**: 완전 지원 (Landlock + seccomp 샌드박스)
- **Windows**: 실험적 (WSL 권장)

### 2.2 설치 방법

```bash
# npm으로 설치
npm install -g @openai/codex

# macOS — Homebrew로 설치
brew install --cask codex

# 또는 GitHub Releases에서 바이너리 직접 다운로드
# https://github.com/openai/codex/releases
```

### 2.3 인증

```bash
# 브라우저 기반 OAuth (ChatGPT 계정)
codex login

# 디바이스 코드 인증
codex login --device-auth

# API Key 인증
codex login --with-api-key

# 인증 상태 확인
codex login status
```

**인증 방식**:

| 방식 | 설명 |
|------|------|
| **ChatGPT 계정 (권장)** | Plus, Pro, Team, Edu, Enterprise 구독 활용 |
| **API Key** | 표준 API 토큰 과금 |

### 2.4 업데이트

```bash
npm i -g @openai/codex@latest
```

---

## 3. 핵심 개념

### 3.1 실행 모드

Codex는 **대화형**과 **비대화형** 두 가지 모드를 지원한다.

```bash
# 대화형 TUI (기본)
codex

# 비대화형 실행 (스크립트/CI/CD용)
codex exec "모든 테스트를 실행하고 결과를 알려줘"
# 또는 축약형
codex e "빌드 후 린트 실행해줘"
```

### 3.2 샌드박스 보안 모델

Codex는 **2계층 보안 모델**로 코드 실행을 격리한다.

**계층 1 — OS 레벨 샌드박스**:

| 모드 | 설명 |
|------|------|
| `read-only` | 파일 쓰기 불가 |
| `workspace-write` | 작업 디렉토리와 `/tmp`만 쓰기 가능 |
| `danger-full-access` | 파일시스템 전체 접근 (주의 필요) |

| 플랫폼 | 샌드박스 기술 |
|--------|-------------|
| macOS | Apple Seatbelt (`sandbox-exec`) |
| Linux | Landlock + seccomp |
| Windows | 네이티브 샌드박스 |

**계층 2 — 승인 정책**:

| 정책 | 동작 |
|------|------|
| `untrusted` | 안전한 읽기만 자동 승인, 상태 변경 시 확인 요청 |
| `on-request` | 위험한 작업만 확인 요청 |
| `never` | 확인 없이 모두 실행 |

📌 **보호 경로**: `.git/`, `.agents/`, `.codex/`는 항상 읽기 전용으로 보호됨

📌 **네트워크**: 로컬 실행 시 기본적으로 **네트워크 비활성화**. 설정으로 활성화 가능.

### 3.3 클라우드 실행 (Codex Cloud)

Codex Cloud는 클라우드 환경에서 작업을 실행한다. 2단계로 나뉜다:

```
1단계: Setup Phase (네트워크 활성화)
  → 의존성 설치, 시크릿 접근 가능

2단계: Agent Phase (네트워크 비활성화)
  → 시크릿 제거, 격리 컨테이너에서 실행
```

```bash
# 클라우드 작업 실행
codex cloud "이 프로젝트의 테스트 커버리지를 80%로 올려줘"

# 클라우드 작업 목록 확인
codex cloud list

# 클라우드 작업 결과를 로컬에 적용
codex apply
```

### 3.4 AGENTS.md (프로젝트 설정)

Claude Code의 `CLAUDE.md`와 동일한 역할. 프로젝트 루트부터 작업 디렉토리까지 순서대로 읽는다.

```markdown
# 프로젝트 개요
Spring Boot 3.x 기반 백엔드 서비스

## 빌드 및 테스트
- 빌드: `./gradlew build`
- 테스트: `./gradlew test`
- 린트: `./gradlew ktlintCheck`

## 코드 스타일
- Kotlin 사용
- 도메인 기반 패키지 구조

## 보안
- .env 파일 커밋 금지
- API Key는 환경 변수로 관리

## 배포
- main 브랜치에 push → GitHub Actions 자동 배포
```

```bash
# AGENTS.md 스캐폴드 자동 생성
> /init
```

---

## 4. 주요 기능

### 4.1 CLI 명령어

| 명령어 | 축약 | 설명 |
|--------|------|------|
| `codex` | - | 대화형 TUI 실행 |
| `codex exec` | `codex e` | 비대화형 실행 (JSON 출력 지원) |
| `codex cloud` | - | 클라우드 작업 실행/관리 |
| `codex cloud list` | - | 최근 클라우드 작업 목록 |
| `codex apply` | `codex a` | 클라우드 작업 결과 로컬 적용 |
| `codex resume` | - | 이전 세션 이어하기 |
| `codex fork` | - | 세션 분기 (새 스레드로 복제) |
| `codex login/logout` | - | 인증 관리 |
| `codex mcp` | - | MCP 서버 관리 |
| `codex sandbox` | - | 샌드박스 정책으로 명령 실행 |
| `codex app` | - | Codex Desktop 실행 (macOS) |
| `codex completion` | - | 셸 자동완성 생성 (bash, zsh, fish) |

### 4.2 주요 플래그

```bash
codex \
  -m gpt-5.3-codex \              # 모델 지정
  -a on-request \                  # 승인 정책
  -s workspace-write \             # 샌드박스 모드
  -C /path/to/project \            # 작업 디렉토리
  -i screenshot.png \              # 이미지 첨부
  --full-auto \                    # on-request + workspace-write
  --search \                       # 웹 검색 활성화
  --add-dir /extra/path            # 추가 쓰기 경로
```

### 4.3 세션 내 슬래시 명령어

| 명령어 | 설명 |
|--------|------|
| `/model` | 모델 및 추론 강도 변경 |
| `/permissions` | 승인 모드 변경 |
| `/diff` | Git diff 표시 (untracked 포함) |
| `/review` | 작업 트리 코드 리뷰 요청 |
| `/mention` | 파일을 대화에 첨부 |
| `/compact` | 대화 요약하여 토큰 절약 |
| `/plan` | 실행 전 계획 먼저 제안하는 모드 |
| `/new` | 새 대화 시작 |
| `/resume` | 이전 대화 불러오기 |
| `/fork` | 대화를 새 스레드로 분기 |
| `/agent` | 서브 에이전트 스레드 전환 |
| `/status` | 세션 설정 및 토큰 사용량 표시 |
| `/init` | AGENTS.md 스캐폴드 생성 |
| `/mcp` | 설정된 MCP 도구 목록 |
| `/ps` | 백그라운드 터미널 표시 |
| `/quit` | 종료 |

### 4.4 MCP (Model Context Protocol)

외부 도구를 Codex에 연결하는 프로토콜이다.

```bash
# MCP 서버 추가
codex mcp add my-server -- npx my-mcp-server

# MCP 서버 목록
codex mcp list

# MCP 서버 제거
codex mcp remove my-server
```

### 4.5 멀티 에이전트 (실험적)

병렬 서브 에이전트를 생성하여 동일 레포에서 동시 작업이 가능하다. 각 에이전트는 격리된 worktree에서 작업한다.

```bash
# /agent 명령으로 서브 에이전트 전환
> /agent
```

---

## 5. 모델

### 5.1 모델 라인업

| 모델 | 시기 | 특징 |
|------|------|------|
| **codex-1** | 2025.05 | 최초 모델. o3 기반, RL 튜닝 |
| **gpt-5.1-codex** | 2025 후반 | 장시간 에이전틱 작업 최적화 |
| **gpt-5.1-codex-max** | 2025 후반 | 강화 버전 |
| **gpt-5.3-codex** | 2026.02 | 현재 주력. "가장 강력한 에이전틱 코딩 모델" |
| **gpt-5.3-codex-spark** | 2026.02 | 연구 프리뷰, 실시간 반복, Pro 전용 |

### 5.2 모델 선택

```bash
# CLI 실행 시 지정
codex -m gpt-5.3-codex

# 세션 중 변경
> /model
```

---

## 6. 설정 및 구성

### 6.1 config.toml

```toml
# ~/.codex/config.toml (사용자 레벨)
# .codex/config.toml (프로젝트 레벨)

# 모델
model = "gpt-5.3-codex"
model_reasoning_effort = "high"    # minimal|low|medium|high|xhigh
model_verbosity = "medium"         # low|medium|high

# 보안
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[sandbox_workspace_write]
network_access = false
writable_roots = ["/additional/path"]

# 웹 검색
web_search = "cached"              # disabled|cached|live

# 멀티 에이전트
[agents]
max_depth = 1
max_threads = 4

# MCP 서버
[mcp_servers.my-server]
command = "npx my-mcp-server"
enabled_tools = ["tool1", "tool2"]

# UI
[tui]
notifications = true
animations = true
personality = "pragmatic"          # none|friendly|pragmatic

# 히스토리
[history]
persistence = "save-all"           # save-all|none
```

### 6.2 커스텀 모델 프로바이더

Codex는 OpenAI 이외의 모델 프로바이더도 설정 가능하다.

```toml
[model_providers.custom]
base_url = "https://my-api.example.com/v1"
env_key = "MY_API_KEY"
wire_api = "responses"             # chat|responses
```

---

## 7. 사용 패턴 및 워크플로우

### 7.1 기본 워크플로우

```bash
# 1. 프로젝트 디렉토리에서 Codex 실행
cd my-project
codex

# 2. 자연어로 작업 지시
> "로그인 API에 JWT 인증 추가해줘"

# 3. 변경 사항 확인
> /diff

# 4. 코드 리뷰
> /review

# 5. 만족하면 커밋
> "변경 사항 커밋해줘"
```

### 7.2 CI/CD 자동화

```bash
# 비대화형으로 테스트 실행
codex e "모든 테스트를 실행하고 실패한 테스트를 수정해줘" \
  --full-auto \
  --json

# 파이프라인에서 코드 리뷰
codex e "이 PR의 변경 사항을 리뷰해줘" \
  -s read-only
```

### 7.3 세션 관리

```bash
# 세션 이어하기
codex resume

# 세션 분기 (현재 대화를 복제하여 다른 방향 탐색)
codex fork
```

### 7.4 이미지 입력

```bash
# 스크린샷을 첨부하여 UI 구현 요청
codex -i design.png "이 디자인대로 React 컴포넌트 만들어줘"
```

---

## 8. 가격

### 8.1 구독 플랜 (ChatGPT 계정)

| 플랜 | 가격 | 로컬 메시지/5시간 | 클라우드 작업/5시간 |
|------|------|-----------------|-------------------|
| **Plus** | $20/월 | 45-225 | 10-60 |
| **Pro** | $200/월 | Plus의 6배 | Plus의 6배 |
| **Business** | $30/사용자/월 | Plus 수준 | Plus 수준 |
| **Enterprise/Edu** | 커스텀 | 크레딧 기반 | 크레딧 기반 |

### 8.2 API Key 과금 (1M 토큰)

| 모델 | 입력 | 출력 |
|------|------|------|
| gpt-5.1-codex-mini | $0.25 | $2.00 |
| gpt-5.1-codex | $1.25 | $10.00 |
| gpt-5.3-codex | $1.75 | $14.00 |

### 8.3 크레딧 소비

| 작업 | 크레딧 |
|------|--------|
| 로컬 메시지 (gpt-5.3-codex) | ~5 |
| 로컬 메시지 (codex-mini) | ~1 |
| 클라우드 작업 | ~25 |
| 코드 리뷰 | ~25 |

---

## 9. 팁 및 모범 사례

### 9.1 효과적인 사용법

| 팁 | 설명 |
|----|------|
| **AGENTS.md 작성** | `/init`으로 생성 후 프로젝트 맥락 기입. 정확도 향상 |
| **`--full-auto` 활용** | 반복 작업에는 `on-request` + `workspace-write` 조합 |
| **`/compact` 활용** | 대화가 길어지면 토큰 절약을 위해 요약 |
| **`/plan` 먼저** | 큰 작업은 계획 모드에서 확인 후 실행 |
| **이미지 첨부** | UI 관련 작업 시 디자인 스크린샷 첨부로 정확도 향상 |
| **세션 분기** | 다른 접근법을 시도할 때 `/fork`로 분기 |

### 9.2 보안 주의사항

- 기본 `workspace-write` 모드를 유지하고, `danger-full-access`는 최소한으로 사용
- 네트워크 접근은 기본 비활성화 — 필요 시에만 설정으로 활성화
- `.git/`, `.agents/`, `.codex/`는 자동 보호됨
- `--yolo` 플래그(승인 없음 + 샌드박스 없음)는 신뢰할 수 있는 환경에서만 사용

---

## 참고

- [Codex 소개 (OpenAI)](https://openai.com/index/introducing-codex/)
- [GitHub — openai/codex](https://github.com/openai/codex)
- [Codex CLI 문서](https://developers.openai.com/codex/cli)
- [Codex CLI 명령어 레퍼런스](https://developers.openai.com/codex/cli/reference/)
- [Codex 모델](https://developers.openai.com/codex/models/)
- [Codex 가격](https://developers.openai.com/codex/pricing/)
- [Codex 설정 레퍼런스](https://developers.openai.com/codex/config-reference/)
- [Codex 보안](https://developers.openai.com/codex/security/)
- [AGENTS.md 가이드](https://developers.openai.com/codex/guides/agents-md/)
- [Codex IDE 확장](https://developers.openai.com/codex/ide/)
