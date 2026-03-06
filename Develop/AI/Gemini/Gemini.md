---
title: Gemini Code Assist & CLI 사용법
tags: [ai, gemini, google, code-assist, gemini-cli]
updated: 2026-03-01
---

# Gemini Code Assist & CLI

## 1. Gemini Code Assist란

**Gemini Code Assist**는 Google이 개발한 AI 코딩 어시스턴트이다. IDE 플러그인(Code Assist)과 터미널 에이전트(Gemini CLI) 두 가지 형태로 제공된다. 개인 사용자에게 **무료**이며, 최대 **1M 토큰 컨텍스트 윈도우**를 제공한다.

### 1.1 두 가지 도구

| 도구 | 형태 | 라이선스 | 주요 특징 |
|------|------|---------|----------|
| **Gemini Code Assist** | IDE 플러그인 | 상용 | VS Code, JetBrains, Android Studio |
| **Gemini CLI** | 터미널 에이전트 | Apache-2.0 (오픈소스) | 터미널 네이티브, 무료 |

### 1.2 다른 AI 도구와의 비교

| 항목 | Gemini CLI | Claude Code | Codex CLI |
|------|-----------|------------|-----------|
| **가격** | 무료 (개인) | API 사용량 기반 | $20/월~ |
| **오픈소스** | Apache-2.0 | 비공개 | Apache-2.0 |
| **컨텍스트** | 1M 토큰 | 200K 토큰 | 모델별 상이 |
| **기본 모델** | Gemini 3 | Claude Opus 4.6 | gpt-5.3-codex |
| **MCP** | 지원 | 지원 | 지원 |
| **설정 파일** | GEMINI.md | CLAUDE.md | AGENTS.md |

---

## 2. Gemini CLI

### 2.1 설치

```bash
# npx로 바로 실행 (설치 불필요)
npx @google/gemini-cli

# npm 글로벌 설치
npm install -g @google/gemini-cli

# Google Cloud Shell에서는 내장
```

### 2.2 인증

```bash
# Google 계정으로 인증 (무료)
# 첫 실행 시 브라우저에서 자동 인증
gemini

# 무료 사용량
# - 60 요청/분
# - 1,000 요청/일
```

### 2.3 주요 기능

- **내장 도구**: Google Search, 파일 작업, 셸 명령, 웹 페칭
- **MCP 지원**: 커스텀 도구 연결
- **ReAct 루프**: 추론(Reason) → 행동(Act) 반복
- **1M 토큰 컨텍스트**: 대규모 코드베이스 탐색에 유리

### 2.4 사용 예시

```bash
# 프로젝트 디렉토리에서 실행
cd my-project
gemini

# 버그 수정
> "src/auth/login.ts에서 비밀번호 검증 에러 수정해줘"

# 테스트 커버리지 개선
> "테스트 커버리지를 80%로 올려줘"

# 새 기능 추가
> "사용자 프로필 API 엔드포인트 추가해줘"
```

### 2.5 GEMINI.md 설정

Claude Code의 CLAUDE.md, Codex의 AGENTS.md와 동일한 역할이다.

```markdown
# 프로젝트 규칙

## 기술 스택
- Node.js + TypeScript
- Express.js
- PostgreSQL + Prisma

## 코딩 스타일
- ESLint + Prettier 사용
- 함수형 프로그래밍 선호
- 에러는 커스텀 에러 클래스 사용
```

---

## 3. Gemini Code Assist (IDE)

### 3.1 지원 IDE

| IDE | Agent Mode |
|-----|-----------|
| **VS Code** | Preview |
| **JetBrains** (IntelliJ 등) | Stable |
| **Android Studio** | 지원 |

### 3.2 주요 기능

- **코드 자동완성**: 인라인 코드 제안
- **Agent Mode**: 파일 조작, 명령 실행, 동적 문제 해결
- **코드 이해**: 코드 설명, 리팩토링 제안
- **인라인 Diff**: 변경 사항 비교
- **통합 채팅**: IDE 내 AI 채팅

### 3.3 가격

| 플랜 | 가격 | 특징 |
|------|------|------|
| **Individual** | 무료 | 개인 사용, 신용카드 불필요 |
| **Standard** | $22.80/월 | 팀 기능 |
| **Enterprise** | $75/사용자/월 | Google Cloud 통합, 커스텀 모델 |

---

## 4. 모델 라인업

### 4.1 현재 모델 (2026년 3월)

| 모델 | 특징 |
|------|------|
| **Gemini 3 Pro** | 최상위. LMArena 1위 (1501 Elo) |
| **Gemini 3 Flash** | 차세대 성능의 경량 모델 |
| **Gemini 2.5 Pro** | 이전 세대 (점진적 폐지 중) |
| **Gemini 2.5 Flash** | 이전 세대 경량 |

### 4.2 폐지 일정

| 모델 | 폐지일 |
|------|--------|
| Gemini 3 Pro Preview | 2026.03.09 → Gemini 3.1 Pro로 마이그레이션 |
| Gemini 2.0 Flash/Flash-Lite | 2026.06.01 |

---

## 5. Google Cloud 통합 (Enterprise)

Enterprise 플랜에서는 Google Cloud 서비스와 긴밀하게 연동된다.

- **BigQuery**: 쿼리 생성, 데이터 분석
- **Cloud Run**: 배포 설정 자동 생성
- **Cloud Functions**: 함수 코드 및 설정 생성
- **Firestore**: 스키마 설계 및 쿼리 코드

---

## 6. 팁 및 모범 사례

| 팁 | 설명 |
|----|------|
| **무료 활용** | 개인 사용은 무료. Google 계정만 있으면 바로 시작 |
| **대규모 코드베이스** | 1M 토큰 컨텍스트로 큰 프로젝트도 한번에 분석 |
| **GEMINI.md** | 프로젝트 규칙 파일로 정확도 향상 |
| **CLI 선호** | 터미널 사용자는 Gemini CLI가 가장 접근성 좋은 무료 옵션 |
| **GCP 환경** | Google Cloud 사용 팀은 Enterprise로 최대 시너지 |

---

## 참고

- [Gemini Code Assist 공식 사이트](https://codeassist.google)
- [Gemini Code Assist 문서](https://developers.google.com/gemini-code-assist/docs/overview)
- [Gemini CLI GitHub](https://github.com/google-gemini/gemini-cli)
- [Gemini CLI 문서](https://developers.google.com/gemini-code-assist/docs/gemini-cli)
- [Gemini 모델](https://ai.google.dev/gemini-api/docs/models)
