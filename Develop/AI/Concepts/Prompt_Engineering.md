---
title: 코딩을 위한 프롬프트 엔지니어링
tags: [ai, prompt-engineering, coding, best-practices]
updated: 2026-03-01
---

# 코딩을 위한 프롬프트 엔지니어링

## 1. 프롬프트 엔지니어링이란

**프롬프트 엔지니어링**은 AI 코딩 도구에게 효과적으로 지시하여 원하는 결과를 얻는 기술이다. 2026년에는 단순 프롬프트 작성을 넘어 **"컨텍스트 엔지니어링"** — 컨텍스트 조립 시스템 설계 — 으로 진화하고 있다.

### 1.1 왜 중요한가

같은 AI 도구를 사용해도 프롬프트에 따라 결과 품질이 크게 달라진다.

❌ **비효과적**: `"로그인 고쳐줘"`

✅ **효과적**: `"src/auth/login.ts의 handleLogin 함수에서 bcrypt 비교 로직이 항상 false를 반환하는 버그를 수정해줘. 테스트도 업데이트해줘."`

---

## 2. 4블록 프롬프트 패턴

효과적인 프롬프트의 기본 구조이다.

### 2.1 구조

```
1. INSTRUCTIONS (지시)     — 무엇을 해야 하는지
2. CONTEXT (컨텍스트)       — 배경 정보, 제약 조건
3. TASK (작업)             — 구체적인 작업 내용
4. OUTPUT FORMAT (출력 형식) — 원하는 결과 형태
```

### 2.2 예시

```
[INSTRUCTIONS]
Spring Boot REST API 엔드포인트를 작성해줘.

[CONTEXT]
- 프로젝트: Spring Boot 3.x + Java 17
- 패키지 구조: com.example.api.{domain}
- 인증: Spring Security + JWT
- DB: PostgreSQL + JPA

[TASK]
사용자 프로필 조회 API를 만들어줘.
- GET /api/v1/users/{id}/profile
- 인증 필요 (JWT)
- 응답에 이름, 이메일, 가입일 포함
- 사용자가 없으면 404 반환

[OUTPUT FORMAT]
Controller, Service, Repository, DTO 클래스를 각각 작성해줘.
```

---

## 3. 핵심 원칙

### 3.1 구체적으로 작성

| 원칙 | 나쁜 예 | 좋은 예 |
|------|---------|---------|
| **파일 지정** | "코드 수정해줘" | "src/auth/login.ts 수정해줘" |
| **함수 지정** | "버그 고쳐줘" | "handleLogin 함수의 null 체크 추가해줘" |
| **범위 명시** | "테스트 추가해줘" | "UserService의 createUser 메서드에 대한 단위 테스트 작성해줘" |
| **제약 조건** | "API 만들어줘" | "REST API + JWT 인증 + 페이지네이션 포함해서 만들어줘" |

### 3.2 컨텍스트 제공

```
✅ 좋은 예:
"이 프로젝트는 NestJS + TypeORM을 사용해.
기존 UserModule의 패턴을 따라서
OrderModule을 만들어줘."

❌ 나쁜 예:
"주문 모듈 만들어줘"
```

### 3.3 단계별 분리

복잡한 작업은 한번에 요청하지 말고 단계별로 나눈다.

```
Step 1: "먼저 현재 인증 구조를 분석해줘"
Step 2: "OAuth2 적용 계획을 세워줘"
Step 3: "계획대로 구현해줘"
Step 4: "테스트를 작성하고 실행해줘"
```

### 3.4 출력 형식 지정

```
"결과를 다음 형식으로 보여줘:
- 변경된 파일 목록
- 각 파일별 변경 사항 요약
- 테스트 실행 결과"
```

---

## 4. 컨텍스트 최적화

### 4.1 토큰 한계 인식

LLM의 추론 품질은 **~3,000 토큰**을 넘으면 저하되기 시작한다. 최적 프롬프트 길이는 **150~300 단어**.

| 상황 | 전략 |
|------|------|
| 긴 프롬프트 | 핵심만 추려서 전달 |
| 큰 파일 | 관련 함수/섹션만 지정 |
| 이전 대화 참조 | `/compact`로 압축 후 핵심 정보 재전달 |

### 4.2 프롬프트 체이닝

복잡한 작업을 **순차적 프롬프트**로 분해한다. 지연시간은 늘지만 정확도가 향상된다.

```
Prompt 1: "현재 DB 스키마를 분석해줘"
  ↓ (결과 확인)
Prompt 2: "분석 결과를 바탕으로 마이그레이션 계획을 세워줘"
  ↓ (계획 확인)
Prompt 3: "계획대로 마이그레이션 스크립트를 작성해줘"
  ↓ (코드 확인)
Prompt 4: "작성된 스크립트를 테스트해줘"
```

---

## 5. 도구별 프롬프트 팁

### 5.1 Claude Code

```bash
# CLAUDE.md에 프로젝트 컨텍스트 정의
# → 매번 설명할 필요 없음

# 계획 먼저 요청
> "먼저 계획을 보여줘"

# 컨텍스트 관리
> /compact    # 컨텍스트 압축
> /clear      # 초기화
```

### 5.2 Cursor

```
# .cursor/rules/에 프로젝트 규칙 정의
# → AI가 자동으로 참조

# Composer로 멀티 파일 작업
Cmd + I → "Controller, Service, Repository를 한번에 만들어줘"

# 인라인으로 단일 수정
Cmd + K → "이 함수에 에러 핸들링 추가해줘"
```

### 5.3 GitHub Copilot

```
# @mentions로 컨텍스트 지정
@workspace "이 프로젝트의 인증 방식을 설명해줘"
@terminal "마지막 에러를 분석해줘"
#file:src/auth/login.ts "이 파일의 보안 취약점 확인해줘"
```

---

## 6. 안티패턴 (피해야 할 것)

| 안티패턴 | 문제 | 대안 |
|---------|------|------|
| **과도하게 긴 프롬프트** | 핵심이 묻힘, 토큰 낭비 | 150~300 단어로 압축 |
| **모호한 지시** | AI가 잘못된 방향으로 진행 | 구체적 파일/함수/결과 명시 |
| **한번에 모든 것 요청** | 품질 저하 | 단계별 분리 |
| **컨텍스트 없는 요청** | 프로젝트와 맞지 않는 코드 | 기술 스택/규칙 제공 |
| **결과 확인 없이 연속 요청** | 오류 누적 | 각 단계 결과 확인 후 진행 |

---

## 7. 프로젝트 설정 파일 비교

각 AI 도구의 프로젝트 설정 파일은 "영구적 프롬프트"로, 매 대화에 자동 적용된다.

| 도구 | 파일 | 역할 |
|------|------|------|
| Claude Code | `CLAUDE.md` | 프로젝트 규칙, 컨벤션, 빌드 명령 |
| Codex | `AGENTS.md` | 프로젝트 개요, 테스트 명령, 스타일 가이드 |
| Cursor | `.cursor/rules/*.mdc` | glob 패턴별 규칙 |
| Gemini CLI | `GEMINI.md` | 프로젝트 규칙 |
| Copilot | `.copilot/settings.json` | 커스텀 지시, 설정 |

📌 **핵심**: 이 설정 파일들을 잘 작성하면 매번 프롬프트에 컨텍스트를 반복할 필요가 없다.

---

## 참고

- [Anthropic 프롬프트 엔지니어링 가이드](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering)
- [OpenAI 프롬프트 엔지니어링](https://platform.openai.com/docs/guides/prompt-engineering)
- [Google AI 프롬프트 전략](https://ai.google.dev/docs/prompt_best_practices)
