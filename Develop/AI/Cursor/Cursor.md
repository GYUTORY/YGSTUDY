---
title: Cursor 사용법 및 핵심 개념
tags: [ai, cursor, ide, agentic-coding, composer]
updated: 2026-03-01
---

# Cursor

## 1. Cursor란

**Cursor**는 Anysphere가 개발한 **AI 네이티브 IDE**이다. VS Code를 포크하여 만들었지만, 에디터 핵심에 AI를 통합하여 멀티 파일 추론, 장시간 자율 에이전트, 코드베이스 전체 이해를 지원한다. Fortune 500 기업의 절반 이상이 사용 중이다.

### 1.1 주요 특징

- **AI 네이티브**: 플러그인이 아닌 에디터 코어에 AI 통합
- **Composer**: 멀티 파일 동시 편집 전용 모델
- **장시간 에이전트**: 25~52시간 이상 자율 작업 가능
- **클라우드 에이전트**: 클라우드 환경에서 에이전트 실행 후 PR 생성
- **멀티 모델**: Claude, GPT, Gemini, Grok 등 자유롭게 전환
- **Tab 자동완성**: Supermaven 기술 기반 초저지연 코드 완성
- **MCP 지원**: 외부 도구 연결

### 1.2 VS Code + Copilot과의 차이

| 항목 | Cursor | VS Code + Copilot |
|------|--------|-------------------|
| **아키텍처** | 독립 AI 네이티브 IDE | IDE + 플러그인 |
| **멀티 파일 편집** | Composer (네이티브) | Agent Mode (2026~) |
| **에이전트** | 장시간 에이전트, 서브에이전트 | 백그라운드 에이전트 |
| **모델 유연성** | 다양한 모델 + 커스텀 모델 | 플랜별 제한 |
| **코드베이스 이해** | 전체 인덱싱 + 팀 공유 | 제한적 |
| **가격** | $20/월 | $10/월 |

---

## 2. 가격

| 플랜 | 가격 | 주요 기능 |
|------|------|----------|
| **Free** | $0 | 50 Fast 요청/월, 2,000 자동완성 |
| **Pro** | $20/월 | 500 Fast 요청/월, 무제한 자동완성, $20 크레딧 |
| **Teams** | $32/사용자/월 | Pro + 팀 관리 도구 |
| **Business** | $40/사용자/월 | 중앙 결제, 관리자 대시보드 |
| **Ultra** | $200/월 | 장시간 에이전트, 클라우드 에이전트 |
| **Enterprise** | 커스텀 | 맞춤 약관 |

---

## 3. 핵심 기능

### 3.1 Agent Mode

Agent Mode는 자율적으로 코드베이스를 탐색하고, 파일을 읽고 수정하며, 터미널 명령을 실행한다.

```
사용자: "로그인 API에 OAuth2 인증 추가해줘"

Cursor Agent:
1. 기존 인증 코드 탐색
2. OAuth2 관련 패키지 설치 (터미널)
3. Controller, Service, Config 파일 생성/수정
4. 테스트 작성 및 실행
5. 변경 사항 요약
```

### 3.2 Composer (멀티 파일 편집)

Composer는 여러 파일을 동시에 편집하는 Cursor 전용 기능이다.

- **단축키**: `Cmd + I`
- **병렬 에이전트**: 하나의 프롬프트로 최대 8개 에이전트 동시 실행
- **격리 실행**: 각 에이전트가 git worktree에서 독립 작업
- **속도**: 대부분의 대화 턴이 30초 이내 완료

### 3.3 Tab 자동완성

Supermaven 기술 기반의 초저지연 코드 자동완성. 시맨틱 이해를 바탕으로 정확한 완성을 제안한다.

### 3.4 인라인 편집 (Cmd + K)

커서 위치에서 바로 코드를 수정한다.

```
1. 수정하고 싶은 코드 블록 선택
2. Cmd + K 입력
3. 프롬프트 바에 원하는 변경 사항 입력
4. 인라인 diff로 변경 사항 확인 후 적용
```

### 3.5 장시간 에이전트 (Cursor 2.5)

25~52시간 이상 자율적으로 작업하는 에이전트이다.

- 대규모 기능 구현, 복잡한 리팩토링, 버그 수정
- **서브에이전트 생성**: 에이전트가 스스로 서브에이전트를 생성하여 협업
- PR 생성까지 자동 처리
- **Mission Control**: 그리드 뷰로 여러 에이전트 작업을 동시 모니터링

### 3.6 클라우드 에이전트

에이전트가 클라우드 환경에서 독립적으로 실행된다.

```
1. 에이전트가 자체 클라우드 환경 생성
2. 코드베이스 자동 온보딩
3. 엔드투엔드 테스트 실행
4. 머지 가능한 PR 생성
```

### 3.7 BugBot

GitHub PR에 대한 자동 코드 리뷰를 수행한다. Slack, 터미널과도 연동 가능.

---

## 4. 지원 모델

| 제공사 | 모델 |
|--------|------|
| **Anthropic** | Claude 4 Sonnet, Claude 4.5/4.6 (Haiku, Opus, Sonnet) |
| **OpenAI** | GPT-5, GPT-5.1/5.2/5.3, GPT Codex |
| **Google** | Gemini 2.5/3 Flash, Gemini 3 Pro |
| **xAI** | Grok Code Fast |
| **Cursor** | Composer 1, Composer 1.5 (자체 코딩 모델) |
| **기타** | Kimi K2.5 (Moonshot), 커스텀 모델 |

📌 **Auto 모드**: 작업에 따라 최적 모델 자동 선택

---

## 5. 주요 단축키

| 단축키 | 기능 |
|--------|------|
| `Cmd + L` | 채팅 (질문/설명 요청) |
| `Cmd + I` | Composer (멀티 파일 편집) |
| `Cmd + K` | 인라인 편집 |
| `Cmd + Shift + P` | 커맨드 팔레트 |
| `Ctrl + `` ` | 터미널 토글 |
| `Cmd + B` | 사이드바 토글 |

---

## 6. 설정 및 구성

### 6.1 프로젝트 규칙 (.cursor/rules)

```markdown
<!-- .cursor/rules/backend.mdc -->
---
description: 백엔드 코딩 규칙
globs: ["src/**/*.java", "src/**/*.kt"]
alwaysApply: true
---

# 백엔드 규칙
- Spring Boot 3.x + Kotlin 사용
- 도메인 기반 패키지 구조
- JUnit 5 + Mockito로 테스트 작성
- 모든 API는 DTO를 사용하여 요청/응답
```

```
생성 방법:
Cmd + Shift + P → "New Cursor Rule" 선택
```

> ⚠️ `.cursorrules` 파일(프로젝트 루트)은 레거시. `.cursor/rules/` 폴더를 권장.

### 6.2 MCP 설정

```json
// .cursor/mcp.json (프로젝트 레벨)
// ~/.cursor/mcp.json (글로벌 레벨)
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

### 6.3 커스텀 모델 추가

```
Cursor Settings → Models → API Keys
→ Override OpenAI Base URL 설정
→ API Key 입력
→ Custom Model 추가
```

OpenRouter를 사용하면 다양한 모델을 하나의 API로 접근 가능:
```
Base URL: https://openrouter.ai/api/v1
```

---

## 7. 팁 및 모범 사례

| 팁 | 설명 |
|----|------|
| **규칙 파일 활용** | `.cursor/rules/`에 프로젝트 컨벤션 정의 → 코드 생성 정확도 향상 |
| **Composer 활용** | 단일 파일은 `Cmd+K`, 멀티 파일은 `Cmd+I` |
| **모델 전환** | 복잡한 작업은 Claude Opus, 간단한 작업은 Haiku |
| **MCP 연결** | DB, API 등 자주 쓰는 도구는 MCP로 연결 |
| **장시간 에이전트** | 대규모 리팩토링은 Ultra 플랜의 장시간 에이전트 활용 |
| **팀 인덱싱** | Teams 이상 플랜에서 팀원 간 인덱스 공유로 온보딩 단축 |

---

## 참고

- [Cursor 공식 사이트](https://cursor.com)
- [Cursor 기능](https://cursor.com/features)
- [Cursor 문서](https://docs.cursor.com)
- [Cursor 모델](https://cursor.com/docs/models)
- [Cursor Rules 디렉토리](https://cursor.directory)
- [Cursor 가격](https://cursor.com/docs/account/pricing)
