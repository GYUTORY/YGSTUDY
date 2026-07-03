---
title: Cursor - AI 네이티브 IDE
tags: [ai, cursor, ide, agentic-coding, composer, context-management]
updated: 2026-04-10
---

# Cursor

## 1. Cursor란

Cursor는 Anysphere가 개발한 AI 네이티브 IDE다. VS Code를 포크했지만, 에디터 코어에 AI를 심어서 멀티 파일 추론, 장시간 자율 에이전트, 코드베이스 전체 이해를 지원한다.

### 1.1 주요 특징

- **AI 네이티브**: 플러그인이 아닌 에디터 코어에 AI 통합
- **Composer**: 멀티 파일 동시 편집 전용 모드
- **장시간 에이전트**: 25~52시간 이상 자율 작업 가능 (Ultra 플랜)
- **클라우드 에이전트**: 클라우드 환경에서 에이전트 실행 후 PR 생성
- **멀티 모델**: Claude, GPT, Gemini, Grok 등 자유롭게 전환
- **Tab 자동완성**: Supermaven 기술 기반 초저지연 코드 완성
- **Context 시스템**: @멘션으로 파일, 코드베이스, 문서, 웹 정보를 프롬프트에 첨부
- **MCP 지원**: 외부 도구 연결

### 1.2 VS Code + Copilot과의 차이

| 항목 | Cursor | VS Code + Copilot |
|------|--------|-------------------|
| **아키텍처** | 독립 AI 네이티브 IDE | IDE + 플러그인 |
| **멀티 파일 편집** | Composer (네이티브) | Agent Mode (2026~) |
| **에이전트** | 장시간 에이전트, 서브에이전트 | 백그라운드 에이전트 |
| **모델 유연성** | 다양한 모델 + 커스텀 모델 | 플랜별 제한 |
| **Context 관리** | @멘션 시스템 (파일, 코드베이스, 문서, 웹) | 제한적 |
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

Agent Mode는 자율적으로 코드베이스를 탐색하고, 파일을 읽고 수정하며, 터미널 명령을 실행한다. 단순 코드 생성이 아니라, 프로젝트 구조를 파악한 뒤 여러 파일을 걸쳐 작업한다.

**실제 사용 예시: Spring Boot 프로젝트에 OAuth2 추가**

아래처럼 프롬프트를 입력하면 Agent가 프로젝트를 분석한 뒤 작업을 진행한다.

```
프롬프트: "로그인 API에 Google OAuth2 인증 추가해줘.
기존 SecurityConfig.java의 필터 체인에 OAuth2 로그인 설정을 추가하고,
callback 엔드포인트는 /api/auth/callback/google로 해줘."
```

Agent가 실제로 수행하는 작업 흐름:

```
[1] 프로젝트 탐색
    - SecurityConfig.java, build.gradle 등 기존 인증 관련 파일 확인
    - 패키지 구조 파악 (도메인 기반인지, 계층형인지)

[2] 의존성 추가
    - build.gradle에 spring-boot-starter-oauth2-client 추가
    - 터미널에서 ./gradlew dependencies로 확인

[3] 코드 수정/생성
    - SecurityConfig.java: OAuth2 로그인 설정 추가
    - OAuth2UserService.java: 사용자 정보 매핑 로직 생성
    - application.yml: Google OAuth2 클라이언트 설정 추가

[4] 테스트
    - OAuth2LoginTest.java 생성
    - 터미널에서 테스트 실행
```

Agent Mode에서 중요한 점은 **프롬프트의 구체성**이다. "OAuth2 추가해줘"만 쓰면 Agent가 프로젝트 구조에 맞지 않는 코드를 생성하는 경우가 있다. 기존 파일명이나 엔드포인트 패턴을 함께 알려주면 결과가 훨씬 낫다.

### 3.2 Composer (멀티 파일 편집)

Composer는 여러 파일을 동시에 편집하는 Cursor 전용 기능이다. `Cmd + I`로 실행한다.

- **병렬 에이전트**: 하나의 프롬프트로 최대 8개 에이전트 동시 실행
- **격리 실행**: 각 에이전트가 git worktree에서 독립 작업
- **속도**: 대부분의 대화 턴이 30초 이내 완료

**실제 사용 예시: REST API CRUD 생성**

```
프롬프트: "@OrderController.java 이 컨트롤러 패턴을 참고해서
Product 도메인의 CRUD API를 만들어줘.
Controller, Service, Repository, DTO, Entity 전부 생성하고
기존 패키지 구조를 따라가줘."
```

Composer가 생성하는 파일 목록:

```
src/main/java/com/example/product/
  ├── controller/ProductController.java
  ├── service/ProductService.java
  ├── repository/ProductRepository.java
  ├── dto/ProductRequest.java
  ├── dto/ProductResponse.java
  └── entity/Product.java
```

핵심은 **@멘션으로 기존 파일을 참조하는 것**이다. 기존 패턴을 명시하지 않으면 Composer가 프로젝트 컨벤션과 다른 구조로 코드를 생성한다. `@OrderController.java`처럼 참조할 파일을 지정하면 같은 패턴으로 코드를 만든다.

**Composer와 Agent Mode의 차이**

| 상황 | 추천 |
|------|------|
| 파일 2~3개 수정, 패턴이 명확할 때 | Composer |
| 프로젝트 구조 파악이 필요한 작업 | Agent Mode |
| 의존성 설치나 터미널 명령이 필요할 때 | Agent Mode |
| 기존 파일 참조해서 비슷한 파일 생성 | Composer + @멘션 |

### 3.3 Context 관리 (@멘션 시스템)

Cursor의 핵심 차별점 중 하나다. 채팅이나 Composer에서 `@`를 입력하면 다양한 소스를 프롬프트에 첨부할 수 있다.

```
┌─────────────────────────────────────────────────┐
│  @files        특정 파일을 컨텍스트에 추가       │
│  @folders      폴더 전체를 컨텍스트에 추가       │
│  @codebase     코드베이스 전체를 검색/참조       │
│  @docs         공식 문서를 검색하여 참조         │
│  @web          웹 검색 결과를 참조               │
│  @git          최근 커밋, diff 등 git 정보 참조  │
│  @definitions  심볼 정의를 참조                  │
│  @notepads     작성해둔 Notepad 내용 참조        │
└─────────────────────────────────────────────────┘
```

**@files / @folders**

가장 자주 쓰는 멘션이다. 채팅창에 `@SecurityConfig.java`처럼 입력하면 해당 파일의 전체 내용이 프롬프트에 포함된다.

```
"@SecurityConfig.java 여기서 CORS 설정이 왜 안 먹히는지 봐줘"
"@src/main/resources/ 이 폴더의 설정 파일들 보고 프로파일 분리해줘"
```

**@codebase**

코드베이스 전체를 임베딩 인덱스로 검색한다. 특정 파일을 모를 때 쓴다.

```
"@codebase 우리 프로젝트에서 Redis 캐시 쓰는 곳이 어디야?"
"@codebase 예외 처리 패턴이 어떻게 되어 있어?"
```

프로젝트를 처음 열면 인덱싱이 진행된다. 인덱싱이 끝나기 전에 `@codebase`를 쓰면 결과가 불완전하다. 우측 하단 상태바에서 인덱싱 진행률을 확인할 수 있다.

**@docs**

외부 라이브러리 공식 문서를 검색해서 참조한다. `Cursor Settings > Features > Docs`에서 자주 쓰는 문서를 미리 등록해두면 좋다.

```
"@Spring Boot 3.x @docs 에서 SecurityFilterChain 설정 방법 알려줘"
```

**@web**

실시간 웹 검색 결과를 가져온다. 최신 라이브러리 버전이나 변경사항을 확인할 때 쓴다.

```
"@web Spring Security 6.x에서 deprecated된 메서드 목록"
```

**Context 관리 시 주의점**

- 파일을 너무 많이 첨부하면 컨텍스트 윈도우를 낭비한다. 관련 파일만 골라서 첨부해야 한다.
- `@codebase`는 인덱스 기반이라 방금 수정한 파일이 바로 반영되지 않는 경우가 있다.
- `@docs`에 등록하지 않은 문서는 검색 정확도가 떨어진다. 자주 쓰는 프레임워크 문서는 미리 등록한다.

### 3.4 Tab 자동완성

Supermaven 기술 기반의 초저지연 코드 자동완성이다. 단순 텍스트 매칭이 아니라 현재 파일과 열린 탭의 컨텍스트를 분석해서 제안한다.

- `Tab`: 제안 수락
- `Esc`: 제안 무시
- 부분 수락: 제안의 일부만 `Tab`으로 수락하고 나머지는 무시할 수 있다

### 3.5 인라인 편집 (Cmd + K)

커서 위치에서 바로 코드를 수정한다. 한두 군데만 고칠 때 Composer보다 빠르다.

```
1. 수정하고 싶은 코드 블록 선택
2. Cmd + K 입력
3. 프롬프트 바에 원하는 변경 사항 입력
4. 인라인 diff로 변경 사항 확인 후 적용
```

터미널에서도 `Cmd + K`가 동작한다. 명령어가 기억나지 않을 때 자연어로 설명하면 해당 명령어를 생성해준다.

### 3.6 Notepads

Notepads는 프로젝트별로 재사용할 수 있는 컨텍스트 메모장이다. `.cursor/notepads/` 폴더에 저장되며, 채팅이나 Composer에서 `@notepads`로 참조한다.

Rules와 다른 점은 **Rules는 자동 적용되고, Notepads는 명시적으로 호출해야 적용된다**는 것이다.

**사용 예시**

```markdown
<!-- .cursor/notepads/api-convention.md -->
# API 컨벤션

- 응답 형식: { "code": 200, "data": {}, "message": "success" }
- 에러 코드: 비즈니스 에러는 4xxx, 시스템 에러는 5xxx
- 페이징: offset 방식, page/size 파라미터
- 날짜 형식: ISO 8601 (yyyy-MM-dd'T'HH:mm:ss)
```

```
프롬프트: "@notepads/api-convention 이 컨벤션에 맞춰서
Product 목록 조회 API 응답 DTO 만들어줘"
```

Rules로 만들기엔 항상 적용될 필요가 없고, 매번 프롬프트에 쓰기엔 반복적인 내용을 Notepads에 정리해두면 된다. 팀 프로젝트라면 `.cursor/notepads/`를 git에 포함시켜 팀원 간 공유할 수 있다.

### 3.7 장시간 에이전트 (Cursor 2.5)

25~52시간 이상 자율적으로 작업하는 에이전트다. Ultra 플랜에서 사용 가능하다.

- 대규모 기능 구현, 복잡한 리팩토링, 버그 수정에 적합
- **서브에이전트 생성**: 에이전트가 스스로 서브에이전트를 생성하여 협업
- PR 생성까지 자동 처리
- **Mission Control**: 그리드 뷰로 여러 에이전트 작업을 동시 모니터링

### 3.8 클라우드 에이전트

에이전트가 클라우드 환경에서 독립적으로 실행된다. 로컬 환경을 차지하지 않고 백그라운드에서 작업이 돌아간다.

```
작업 흐름:
1. 에이전트가 자체 클라우드 환경 생성
2. 코드베이스 자동 온보딩
3. 엔드투엔드 테스트 실행
4. 머지 가능한 PR 생성
```

### 3.9 BugBot

GitHub PR에 대한 자동 코드 리뷰를 수행한다. Slack, 터미널과도 연동 가능하다.

---

## 4. Privacy Mode

Cursor는 Privacy Mode를 제공한다. `Cursor Settings > General > Privacy Mode`에서 설정한다.

**Privacy Mode가 켜져 있으면:**

- 코드가 Cursor 서버에 저장되지 않는다
- 코드가 모델 학습에 사용되지 않는다
- 요청 처리 후 즉시 삭제된다

**Privacy Mode가 꺼져 있으면:**

- 프롬프트와 코드 스니펫이 로그에 저장될 수 있다
- 제품 개선 목적으로 사용될 수 있다

회사 코드를 다루는 경우 반드시 Privacy Mode를 켜야 한다. Teams/Business/Enterprise 플랜은 기본적으로 Privacy Mode가 활성화되어 있다. 개인 플랜(Free, Pro)에서는 수동으로 켜야 한다.

SOC 2 인증을 받았고, 코드는 제3자와 공유되지 않는다고 명시하고 있지만, 사내 보안 정책에 따라 확인이 필요하다.

---

## 5. 지원 모델

| 제공사 | 모델 |
|--------|------|
| **Anthropic** | Claude 4 Sonnet, Claude 4.5/4.6 (Haiku, Opus, Sonnet) |
| **OpenAI** | GPT-5, GPT-5.1/5.2/5.3, GPT Codex |
| **Google** | Gemini 2.5/3 Flash, Gemini 3 Pro |
| **xAI** | Grok Code Fast |
| **Cursor** | Composer 1, Composer 1.5 (자체 코딩 모델) |
| **기타** | Kimi K2.5 (Moonshot), 커스텀 모델 |

**Auto 모드**: 작업에 따라 Cursor가 모델을 자동 선택한다. 간단한 질문에는 경량 모델, 복잡한 코드 생성에는 대형 모델을 배정한다. 대부분의 경우 Auto로 두면 되지만, 특정 모델의 출력이 필요할 때는 수동 전환한다.

---

## 6. 주요 단축키

| 단축키 | 기능 |
|--------|------|
| `Cmd + L` | 채팅 (질문/설명 요청) |
| `Cmd + I` | Composer (멀티 파일 편집) |
| `Cmd + K` | 인라인 편집 |
| `Cmd + Shift + P` | 커맨드 팔레트 |
| `Ctrl + `` ` | 터미널 토글 |
| `Cmd + B` | 사이드바 토글 |
| `@` | 채팅/Composer에서 Context 멘션 |

---

## 7. 설정 및 구성

### 7.1 프로젝트 규칙 (.cursor/rules)

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

생성 방법: `Cmd + Shift + P` → "New Cursor Rule" 선택

Rules의 적용 방식은 네 가지다:

| 방식 | 설명 |
|------|------|
| `alwaysApply: true` | 항상 모든 프롬프트에 적용 |
| `globs` 패턴 | 해당 파일 작업 시 자동 적용 |
| `description` 매칭 | AI가 프롬프트와 관련 있다고 판단하면 적용 |
| 수동 `@rules` 멘션 | 명시적으로 호출할 때만 적용 |

> 참고: `.cursorrules` 파일(프로젝트 루트)은 레거시 방식이다. `.cursor/rules/` 폴더를 사용한다.

### 7.2 MCP 설정

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

### 7.3 커스텀 모델 추가

```
Cursor Settings → Models → API Keys
→ Override OpenAI Base URL 설정
→ API Key 입력
→ Custom Model 추가
```

OpenRouter를 사용하면 다양한 모델을 하나의 API로 접근 가능하다:
```
Base URL: https://openrouter.ai/api/v1
```

---

## 8. 실무에서 자주 겪는 문제

### Context 윈도우 초과

긴 대화를 이어가다 보면 컨텍스트 윈도우가 차서 이전 내용을 잊어버린다. 이때 발생하는 증상:

- 이전에 수정한 파일을 다시 원래대로 되돌리는 경우
- 같은 코드를 중복 생성하는 경우
- 프롬프트를 이해하지 못하는 경우

대응 방법: 대화가 길어지면 새 Composer 세션을 열고, 필요한 파일은 `@`멘션으로 다시 첨부한다. 한 세션에서 너무 많은 작업을 하려고 하지 않는 게 좋다.

### Agent가 엉뚱한 파일을 수정할 때

Agent Mode가 프로젝트 구조를 잘못 파악해서 관계없는 파일을 수정하는 경우가 있다. `.cursor/rules/`에 프로젝트 구조를 명시해두면 이런 문제가 줄어든다.

```markdown
<!-- .cursor/rules/project-structure.mdc -->
---
description: 프로젝트 구조 안내
alwaysApply: true
---

# 프로젝트 구조
- src/main/java/com/example/
  - domain/ : 도메인별 패키지 (order, product, user)
  - common/ : 공통 유틸, 예외 처리
  - config/ : 설정 클래스
- src/main/resources/
  - application.yml : 메인 설정
  - application-{profile}.yml : 프로파일별 설정
```

### diff 적용 실패

가끔 Cursor가 생성한 diff가 현재 파일 상태와 맞지 않아 적용이 실패한다. 파일을 저장하지 않은 상태에서 Agent가 해당 파일을 수정하려 할 때 주로 발생한다. 작업 전 저장 습관이 필요하다.

---

## 참고

- [Cursor 공식 사이트](https://cursor.com)
- [Cursor 기능](https://cursor.com/features)
- [Cursor 문서](https://docs.cursor.com)
- [Cursor 모델](https://cursor.com/docs/models)
- [Cursor Rules 디렉토리](https://cursor.directory)
- [Cursor 가격](https://cursor.com/docs/account/pricing)
