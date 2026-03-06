---
title: Claude Code 사용법 및 핵심 개념
tags: [ai, claude-code, anthropic, cli, agentic-coding]
updated: 2026-03-01
---

# Claude Code

## 1. Claude Code란

**Claude Code**는 Anthropic이 만든 **CLI(Command Line Interface) 기반 에이전틱 코딩 어시스턴트**이다. 터미널에서 직접 실행되며, 자연어로 지시하면 코드를 읽고, 수정하고, 생성하고, 테스트까지 자율적으로 수행한다.

### 1.1 주요 특징

- **터미널 네이티브**: 별도 IDE 없이 터미널에서 바로 사용
- **파일시스템 직접 접근**: 프로젝트의 모든 파일을 읽고 수정 가능
- **에이전틱 실행**: 단순 코드 생성이 아닌, 탐색 → 계획 → 구현 → 검증까지 자율적으로 수행
- **Git 통합**: 커밋, PR 생성, 브랜치 관리를 자연어로 처리
- **컨텍스트 인식**: 프로젝트 구조와 코딩 컨벤션을 이해하고 따름

### 1.2 다른 AI 코딩 도구와의 비교

| 특징 | Claude Code | GitHub Copilot | Cursor |
|------|------------|----------------|--------|
| **인터페이스** | CLI (터미널) | IDE 플러그인 | 전용 IDE |
| **작동 방식** | 에이전틱 (자율 수행) | 자동완성 + Chat | 에이전틱 + 에디터 |
| **파일 접근** | 전체 프로젝트 | 현재 파일 중심 | 전체 프로젝트 |
| **터미널 명령** | 직접 실행 가능 | 제한적 | 가능 |
| **Git 통합** | 네이티브 지원 | 제한적 | 부분 지원 |
| **커스터마이징** | CLAUDE.md, Hooks, MCP | 설정 파일 | Rules, MCP |
| **비용 모델** | API 사용량 기반 | 월 구독 | 월 구독 |

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

### 2.3 초기 실행 및 인증

```bash
# 프로젝트 디렉토리에서 실행
cd my-project
claude

# 첫 실행 시 인증 절차 진행
# 1. Anthropic Console 계정으로 OAuth 인증
# 2. 또는 API Key 직접 입력
```

**인증 방식**:

| 방식 | 설명 |
|------|------|
| **OAuth (기본)** | Anthropic Console 계정으로 브라우저 인증 |
| **API Key** | `ANTHROPIC_API_KEY` 환경 변수 설정 |
| **Anthropic Console** | Max 플랜 사용 시 직접 연동 |

```bash
# API Key 방식
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# .zshrc 또는 .bashrc에 추가하면 영구 설정
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-..."' >> ~/.zshrc
```

### 2.4 업데이트

```bash
# 최신 버전으로 업데이트
npm update -g @anthropic-ai/claude-code

# 또는 특정 버전 설치
npm install -g @anthropic-ai/claude-code@latest
```

---

## 3. 핵심 개념

### 3.1 에이전틱 코딩 (Agentic Coding)

기존 AI 코딩 도구가 **코드 자동완성**에 집중한다면, Claude Code는 **에이전트로서 자율적으로 작업을 수행**한다.

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

### 3.2 컨텍스트 윈도우 (Context Window)

Claude Code는 대화가 길어질수록 **컨텍스트 윈도우**(토큰 한도)를 소모한다.

- **대화 내용**, **파일 읽기 결과**, **명령 실행 결과** 등이 모두 컨텍스트에 쌓임
- 컨텍스트가 가득 차면 이전 대화를 자동 압축(summarize)
- `/compact` 명령으로 수동 압축 가능
- `/clear` 명령으로 대화 초기화

```bash
# 컨텍스트가 많이 쌓였을 때
> /compact     # 이전 대화를 요약하여 컨텍스트 절약

# 완전히 새로운 작업을 시작할 때
> /clear       # 대화 히스토리 초기화
```

📌 **팁**: 서로 다른 작업을 할 때는 `/clear`로 초기화하는 것이 정확도에 도움이 된다.

### 3.3 도구 시스템 (Tools)

Claude Code는 내부적으로 다양한 **도구(Tools)**를 사용하여 작업을 수행한다.

| 도구 | 역할 | 예시 |
|------|------|------|
| **Read** | 파일 읽기 | 소스 코드, 설정 파일 확인 |
| **Write** | 새 파일 생성 | 새로운 컴포넌트 생성 |
| **Edit** | 기존 파일 수정 | 함수 변경, 버그 수정 |
| **Bash** | 터미널 명령 실행 | 테스트 실행, 빌드, git 명령 |
| **Glob** | 파일 패턴 검색 | `**/*.ts` 패턴으로 파일 찾기 |
| **Grep** | 코드 내용 검색 | 함수명, 변수명 검색 |
| **WebFetch** | 웹 페이지 가져오기 | API 문서 참조 |
| **WebSearch** | 웹 검색 | 최신 라이브러리 정보 검색 |
| **Agent** | 서브 에이전트 실행 | 복잡한 탐색을 병렬 처리 |

### 3.4 권한 모델 (Permission Model)

Claude Code는 안전을 위해 **도구 실행 전 사용자 승인**을 요청한다.

```
세 가지 모드:

1. Ask Mode (기본)    → 모든 도구 사용 시 승인 요청
2. Auto-Accept Mode  → 읽기 도구는 자동, 쓰기는 승인 요청
3. Full Auto Mode    → 모든 도구 자동 승인 (주의 필요)
```

**권한 수준 체계**:

| 수준 | 설명 | 예시 도구 |
|------|------|-----------|
| **읽기 전용** | 자동 허용 가능 | Read, Glob, Grep |
| **쓰기** | 승인 필요 | Write, Edit |
| **실행** | 승인 필요 | Bash |
| **위험** | 항상 확인 | `rm`, `git push --force` |

---

## 4. 주요 기능

### 4.1 슬래시 명령어 (Slash Commands)

| 명령어 | 설명 |
|--------|------|
| `/help` | 도움말 표시 |
| `/clear` | 대화 히스토리 초기화 |
| `/compact` | 대화 컨텍스트 압축 (토큰 절약) |
| `/config` | 설정 열기/수정 |
| `/cost` | 현재 세션 토큰 사용량 및 비용 확인 |
| `/doctor` | Claude Code 설치 상태 진단 |
| `/init` | 프로젝트에 CLAUDE.md 초기화 |
| `/login` | 인증 로그인 |
| `/logout` | 인증 로그아웃 |
| `/status` | 현재 상태 표시 (모델, 컨텍스트 등) |
| `/review` | 코드 리뷰 요청 |
| `/bug` | 버그 리포트 생성 |
| `/commit` | 변경 사항을 분석하여 커밋 메시지 생성 및 커밋 |

### 4.2 MCP 서버 (Model Context Protocol)

MCP는 Claude Code에 **외부 도구를 연결**하는 프로토콜이다. 데이터베이스 조회, API 호출, 사내 도구 연동 등을 추가할 수 있다.

```json
// .claude/settings.json 또는 ~/.claude/settings.json
{
  "mcpServers": {
    "my-database": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "postgresql://localhost:5432/mydb"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_..."
      }
    }
  }
}
```

**MCP 활용 예시**:
- PostgreSQL/MySQL 데이터베이스 직접 쿼리
- GitHub Issues/PRs 조회 및 관리
- Slack 메시지 전송
- 사내 API 연동

### 4.3 훅 시스템 (Hooks)

훅은 **도구 실행 전후에 자동으로 실행되는 셸 명령**이다. 린트, 포맷팅, 알림 등을 자동화할 수 있다.

```json
// .claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "echo '파일 수정 시작'"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write $CLAUDE_FILE_PATH"
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "terminal-notifier -message '$CLAUDE_NOTIFICATION'"
          }
        ]
      }
    ]
  }
}
```

| 훅 이벤트 | 실행 시점 | 활용 예시 |
|-----------|-----------|-----------|
| **PreToolUse** | 도구 실행 전 | 유효성 검사, 백업 |
| **PostToolUse** | 도구 실행 후 | 포맷팅, 린트, 알림 |
| **Notification** | 알림 발생 시 | 시스템 알림, Slack 전송 |

### 4.4 메모리 시스템 (CLAUDE.md)

CLAUDE.md는 Claude Code에게 **프로젝트 컨텍스트와 규칙을 알려주는 파일**이다. 대화가 시작될 때 자동으로 로드된다.

**계층 구조**:

```
~/.claude/CLAUDE.md          ← 전역 (모든 프로젝트에 적용)
프로젝트루트/CLAUDE.md        ← 프로젝트 레벨 (git 공유 가능)
프로젝트루트/.claude/CLAUDE.md ← 프로젝트 로컬 (개인 설정)
하위폴더/CLAUDE.md            ← 폴더 레벨 (해당 폴더 작업 시)
```

**CLAUDE.md 작성 예시**:

```markdown
# 프로젝트 규칙

## 기술 스택
- Backend: Spring Boot 3.x + Java 17
- Database: PostgreSQL 15
- ORM: JPA/Hibernate

## 코딩 컨벤션
- 패키지 구조: domain 기반 (user/, order/, payment/)
- 클래스명: PascalCase
- 메서드명: camelCase
- 테스트: JUnit 5 + Mockito

## 커밋 규칙
- conventional commits 형식 사용
- 한글 커밋 메시지 허용

## 주의사항
- main 브랜치에 직접 force push 금지
- .env 파일 절대 커밋하지 말 것
```

📌 **팁**: `/init` 명령으로 현재 프로젝트의 CLAUDE.md를 자동 생성할 수 있다.

### 4.5 Git 통합

Claude Code는 Git 작업을 자연어로 처리한다.

```bash
# 커밋
> "변경 사항 커밋해줘"
# → 변경 내용 분석 → 커밋 메시지 자동 생성 → 커밋

# PR 생성
> "이 브랜치로 PR 만들어줘"
# → 커밋 히스토리 분석 → PR 제목/본문 작성 → gh pr create

# 브랜치 관리
> "feature/login 브랜치 만들어줘"
# → git checkout -b feature/login
```

---

## 5. 사용 패턴 및 워크플로우

### 5.1 기본 워크플로우

Claude Code의 작업 흐름은 네 단계로 이루어진다:

```
탐색 (Explore)  →  계획 (Plan)  →  구현 (Implement)  →  검증 (Verify)
    |                  |                 |                   |
  Glob, Grep,      사용자 확인      Write, Edit,       Bash (테스트),
  Read, Agent      후 진행         Bash              코드 리뷰
```

### 5.2 실전 워크플로우 예시

**버그 수정**:
```
> "로그인 시 500 에러가 발생해. 원인을 찾아서 수정해줘"

Claude Code:
1. 에러 로그 확인 (Bash: tail logs)
2. 관련 코드 검색 (Grep: "login", "auth")
3. 코드 분석 (Read: AuthController.java)
4. 원인 파악 및 수정 (Edit)
5. 테스트 실행 (Bash: mvn test)
```

**새 기능 추가**:
```
> "사용자 프로필에 프로필 이미지 업로드 기능 추가해줘"

Claude Code:
1. 기존 프로필 관련 코드 탐색
2. 파일 업로드 관련 패턴 확인
3. 구현 계획 제시 (사용자 확인)
4. Controller, Service, Repository 수정
5. 테스트 작성 및 실행
```

**코드 리뷰**:
```
> /review

Claude Code:
1. 현재 브랜치의 변경 사항 분석
2. 잠재적 이슈 식별 (보안, 성능, 유지보수성)
3. 개선 제안 사항 리포트
```

### 5.3 파이프라인/헤드리스 모드

CI/CD 환경이나 스크립트에서 비대화형으로 사용할 수 있다.

```bash
# 파이프라인 사용 (stdin → claude → stdout)
echo "이 코드를 리뷰해줘" | claude --print

# 파일 내용을 전달
cat error.log | claude --print "이 에러 로그를 분석해줘"

# 헤드리스 모드 (완전 자동)
claude --print --dangerously-skip-permissions "프로젝트의 모든 테스트를 실행해줘"
```

---

## 6. IDE 통합

### 6.1 VS Code 확장

```bash
# VS Code 확장 설치
# Extensions에서 "Claude Code" 검색 후 설치

# 또는 CLI에서 설치
code --install-extension anthropic.claude-code
```

**VS Code 통합 기능**:
- 터미널 패널에서 Claude Code 실행
- 에디터에서 파일 변경 사항 실시간 확인
- 문제(Problems) 패널과 연동
- Diff 뷰에서 변경 사항 리뷰

### 6.2 JetBrains 통합

```
Settings → Plugins → "Claude Code" 검색 → Install
```

**JetBrains 통합 기능**:
- 내장 터미널에서 Claude Code 실행
- 에디터 내 인라인 Diff 확인
- 프로젝트 구조 탐색기와 연동

### 6.3 사용 환경 비교

| 항목 | 터미널 직접 사용 | VS Code | JetBrains |
|------|-----------------|---------|-----------|
| **설정 편의성** | 가장 간단 | 확장 설치 필요 | 플러그인 설치 필요 |
| **파일 Diff 확인** | 터미널 출력 | 에디터 내 표시 | 에디터 내 표시 |
| **속도** | 가장 빠름 | 약간 오버헤드 | 약간 오버헤드 |
| **멀티태스킹** | 터미널 탭 활용 | 패널 분할 | 패널 분할 |
| **추천 대상** | 터미널 익숙한 개발자 | VS Code 사용자 | IntelliJ 사용자 |

---

## 7. 설정 및 구성

### 7.1 CLAUDE.md 작성 가이드

효과적인 CLAUDE.md를 작성하면 Claude Code의 정확도가 크게 향상된다.

**포함하면 좋은 내용**:

```markdown
# 프로젝트명

## 기술 스택
- 사용 언어, 프레임워크, 주요 라이브러리

## 프로젝트 구조
- 디렉토리 구조 설명
- 주요 파일 위치

## 코딩 컨벤션
- 네이밍 규칙
- 코드 스타일 (들여쓰기, 세미콜론 등)
- import 순서

## 빌드/실행 방법
- 빌드 명령어
- 테스트 실행 명령어
- 로컬 개발 서버 실행법

## 금지 사항
- 커밋하면 안 되는 파일
- 사용하면 안 되는 패턴
```

### 7.2 settings.json

```json
// 프로젝트 레벨: .claude/settings.json
// 사용자 레벨: ~/.claude/settings.json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Bash(npm test)",
      "Bash(npm run lint)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(git push --force)"
    ]
  },
  "mcpServers": {},
  "hooks": {}
}
```

### 7.3 환경 변수

| 환경 변수 | 설명 | 예시 |
|-----------|------|------|
| `ANTHROPIC_API_KEY` | API 인증 키 | `sk-ant-api03-...` |
| `CLAUDE_CODE_MAX_TURNS` | 최대 대화 턴 수 (헤드리스 모드) | `10` |
| `CLAUDE_CODE_USE_BEDROCK` | AWS Bedrock 사용 | `1` |
| `CLAUDE_CODE_USE_VERTEX` | GCP Vertex AI 사용 | `1` |

### 7.4 모델 선택

```bash
# 기본 모델 사용
claude

# 특정 모델 지정
claude --model claude-sonnet-4-6

# 사용 가능한 모델
# - claude-opus-4-6     (가장 강력, 비용 높음)
# - claude-sonnet-4-6   (균형, 기본값)
# - claude-haiku-4-5    (빠르고 저렴)
```

### 7.5 비용 관리

```bash
# 현재 세션 비용 확인
> /cost

# 출력 예시:
# Session cost: $0.42
# Input tokens: 125,000
# Output tokens: 8,500
```

**비용 절약 팁**:
- `/compact`로 컨텍스트 정기적 압축
- 관련 없는 작업 시 `/clear`로 초기화
- 간단한 작업은 Haiku 모델 사용
- `--print` 모드로 불필요한 대화 줄이기

---

## 8. 팁 및 모범 사례

### 8.1 효과적인 프롬프트 작성법

✅ **좋은 예시**:
```
"src/auth/login.ts의 handleLogin 함수에서 비밀번호 검증 로직을
bcrypt 해싱 방식으로 변경해줘. 기존 테스트도 업데이트해줘."
```

❌ **나쁜 예시**:
```
"로그인 고쳐줘"
```

**효과적인 프롬프트 원칙**:
1. **구체적인 파일/함수명** 언급
2. **원하는 결과**를 명확히 설명
3. **제약 조건** 명시 (기존 코드 스타일 유지, 특정 라이브러리 사용 등)
4. **범위** 명시 (테스트 포함 여부, 관련 파일 수정 여부)

### 8.2 컨텍스트 관리

| 상황 | 추천 명령 |
|------|-----------|
| 대화가 길어져서 느려질 때 | `/compact` |
| 완전히 다른 작업을 시작할 때 | `/clear` |
| 토큰 사용량이 궁금할 때 | `/cost` |
| 특정 파일에 집중하고 싶을 때 | 파일 경로를 직접 언급 |

### 8.3 보안 모범 사례

- **API 키**나 **비밀번호**를 프롬프트에 직접 입력하지 않기
- `.env` 파일은 `deny` 목록에 추가하여 커밋 방지
- `--dangerously-skip-permissions`는 신뢰할 수 있는 환경에서만 사용
- MCP 서버 설정에 민감한 토큰은 환경 변수로 관리

### 8.4 자주 하는 실수와 해결법

| 실수 | 해결법 |
|------|--------|
| 컨텍스트 초과로 이전 내용을 잊음 | `/compact`로 압축 또는 `/clear` 후 핵심 정보만 재전달 |
| 너무 큰 범위의 작업을 한번에 요청 | 작업을 단계별로 나누어 요청 |
| CLAUDE.md 없이 사용 | `/init`으로 프로젝트 설정 초기화 |
| 변경 사항 확인 없이 진행 | "먼저 계획을 보여줘" 요청 후 승인 |
| 잘못된 수정 사항 되돌리기 | `git diff`로 확인 후 `git checkout -- file` 또는 undo |

---

## 참고

- [Claude Code 공식 문서](https://docs.anthropic.com/en/docs/claude-code)
- [Anthropic 공식 사이트](https://www.anthropic.com)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
