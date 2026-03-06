---
title: GitHub Copilot 사용법 및 핵심 개념
tags: [ai, github-copilot, code-completion, agent-mode, ide]
updated: 2026-03-01
---

# GitHub Copilot

## 1. GitHub Copilot이란

**GitHub Copilot**은 GitHub(Microsoft)이 개발한 **AI 코딩 어시스턴트**이다. IDE에서 코드 자동완성, 채팅, Agent Mode를 통한 자율 작업, PR 리뷰까지 지원하며, 가장 널리 사용되는 AI 코딩 도구이다.

### 1.1 주요 특징

- **코드 자동완성**: 타이핑 중 인라인 코드 제안
- **Agent Mode**: 멀티 파일 자율 편집, 테스트 실행, PR 생성
- **멀티 모델**: GPT, Claude, Gemini, Grok 등 다양한 모델 선택 가능
- **GitHub 통합**: Issue → PR 자동 워크플로우, 코드 리뷰, 보안 스캔
- **멀티 IDE**: VS Code, JetBrains, Visual Studio, Vim, Xcode 등 지원

### 1.2 다른 AI 도구와의 비교

| 특징 | GitHub Copilot | Claude Code | Cursor |
|------|---------------|------------|--------|
| **인터페이스** | IDE 플러그인 | CLI | 독립 IDE |
| **접근 방식** | 보조형 (사용자 주도) | 에이전틱 (자율 실행) | 에이전틱 (IDE 내장) |
| **코드 완성** | 인라인 자동완성 | 없음 | Tab 자동완성 |
| **Agent Mode** | 지원 (2026~) | 기본 동작 방식 | 장시간 에이전트 지원 |
| **IDE 지원** | 다양한 IDE | 터미널 전용 | VS Code 포크 전용 |
| **가격** | $10~39/월 | API 사용량 기반 | $20~200/월 |

---

## 2. 가격

### 2.1 개인 플랜

| 플랜 | 가격 | 코드 완성 | 프리미엄 요청 |
|------|------|----------|-------------|
| **Free** | $0 | 2,000회/월 | 50회/월 |
| **Pro** | $10/월 | 무제한 | 300회/월 |
| **Pro+** | $39/월 | 무제한 | 1,500회/월 |

### 2.2 조직 플랜

| 플랜 | 가격 | 특징 |
|------|------|------|
| **Business** | $19/사용자/월 | 조직 관리, 감사 로그, 정책 제어, IP 보상 |
| **Enterprise** | $39/사용자/월 | 지식 베이스, 커스텀 모델, GitHub.com 채팅 |

---

## 3. 핵심 기능

### 3.1 코드 자동완성

IDE에서 코딩 중 실시간으로 코드 제안을 표시한다. Tab 키로 수락.

```python
# 함수 시그니처를 작성하면 본문을 자동 완성
def calculate_discount(price, discount_rate):
    # Copilot이 아래 코드를 자동 제안
    if discount_rate < 0 or discount_rate > 1:
        raise ValueError("할인율은 0~1 사이여야 합니다")
    return price * (1 - discount_rate)
```

### 3.2 Agent Mode

Agent Mode는 GitHub Issue를 할당하면 **자율적으로 코드를 분석, 수정, 테스트하고 PR을 생성**한다.

**동작 방식**:
```
1. GitHub Issue에 Copilot 할당
2. 요구사항 분석 및 변경 계획 수립
3. 멀티 파일 편집 실행
4. 테스트 실행 및 검증
5. 보안 스캔 (코드 스캐닝, 시크릿 스캐닝)
6. PR 생성 → 사람이 리뷰
```

**Agent Mode 기능**:
- 멀티 파일 동시 편집
- 자체 코드 리뷰 수행
- 보안 취약점 자동 스캔
- 테스트 실행 및 반복 개선
- 커스텀 에이전트 (`.github/agents/` 디렉토리에 정의)

### 3.3 채팅 인터페이스

자연어로 코딩 질문, 코드 설명, 리팩토링 요청 가능.

**채팅 참여자 (@mentions)**:

| 참여자 | 설명 |
|--------|------|
| `@github` | GitHub 컨텍스트 (이슈, PR, 디스커션) |
| `@workspace` | 프로젝트 전체 컨텍스트 |
| `@terminal` | 터미널/CLI 컨텍스트 |
| `@vscode` | VS Code 관련 기능 |

**채팅 변수 (#mentions)**:

| 변수 | 설명 |
|------|------|
| `#file` | 현재 파일 |
| `#selection` | 선택한 코드 영역 |
| `#project` | 프로젝트 전체 |

### 3.4 슬래시 명령어

| 명령어 | 설명 |
|--------|------|
| `/clear` | 대화 초기화 |
| `/explain` | 코드 동작 설명 |
| `/fix` | 문제 해결 제안 |
| `/tests` | 유닛 테스트 생성 |
| `/new` | 새 프로젝트 설정 (VS Code) |
| `/doc` | 문서 생성 (Visual Studio) |
| `/optimize` | 성능 분석 (VS Code, Visual Studio) |
| `/simplify` | 코드 단순화 (Xcode) |
| `/help` | 도움말 |

### 3.5 코드 리뷰

PR에 대해 AI 기반 코드 리뷰를 자동으로 수행한다. 버그, 보안 이슈, 성능 문제를 식별한다.

---

## 4. 지원 모델

### 4.1 사용 가능한 모델

| 제공사 | 모델 | 비고 |
|--------|------|------|
| **OpenAI** | GPT-5.2, GPT-4.1, GPT-5 mini | GPT-4.1이 기본 |
| **Anthropic** | Claude Opus 4.6, Sonnet 4.5, Haiku 4.5 | Opus는 Enterprise |
| **Google** | Gemini 3 Pro, Gemini 2.5 Pro | 프리뷰 |
| **xAI** | Grok Code Fast | 코딩 특화 |

📌 **자동 선택**: 작업에 따라 최적 모델을 자동 선택하는 Auto 모드 지원

---

## 5. 지원 IDE

| IDE | 기능 |
|-----|------|
| **VS Code** | 전체 기능 (Agent Mode, 채팅, 자동완성) |
| **Visual Studio** | 전체 기능 |
| **JetBrains** | IntelliJ, PyCharm, WebStorm 등 |
| **Vim/Neovim** | 자동완성, 채팅 |
| **Xcode** | 자동완성, 채팅, 명령어 |
| **Eclipse** | 자동완성 |
| **GitHub.com** | 웹 채팅, 에이전트 |
| **GitHub CLI** | 터미널 에이전트 |
| **GitHub Mobile** | 모바일 채팅 |

---

## 6. 설정 및 구성

### 6.1 프로젝트 레벨 설정

```json
// .copilot/settings.json (레포에 커밋)
{
  "copilot": {
    "chat": {
      "instructions": "이 프로젝트는 Spring Boot 3.x + Kotlin을 사용합니다."
    }
  }
}
```

```json
// .copilot/settings.local.json (개인 설정, .gitignore에 추가)
{
  "copilot": {
    "chat": {
      "instructions": "응답은 한국어로 해주세요."
    }
  }
}
```

### 6.2 커스텀 에이전트

```yaml
# .github/agents/performance-optimizer.yml
name: Performance Optimizer
description: 성능 최적화에 특화된 에이전트
instructions: |
  코드를 분석하여 성능 병목점을 찾고 최적화 방안을 제안합니다.
  N+1 쿼리, 불필요한 메모리 할당, 동기 블로킹 등을 식별합니다.
```

### 6.3 MCP 지원

MCP 서버를 연결하여 Copilot의 기능을 확장할 수 있다.

- VS Code에서 MCP 서버 설정
- GitHub MCP 서버로 이슈/PR/레포 접근
- GitHub MCP Registry에서 원클릭 설치

---

## 7. 팁 및 모범 사례

| 팁 | 설명 |
|----|------|
| **컨텍스트 제공** | `#file`, `@workspace`로 관련 파일/프로젝트 컨텍스트 첨부 |
| **Agent Mode 활용** | 반복 작업(이슈 처리, PR 생성)은 Agent Mode에 위임 |
| **모델 선택** | 복잡한 작업은 Claude/GPT-5, 간단한 작업은 경량 모델 |
| **코드 리뷰 자동화** | PR에 Copilot 리뷰 자동 할당으로 리뷰 품질 향상 |
| **프로젝트 설정** | `.copilot/settings.json`으로 프로젝트 맥락 제공 |

---

## 참고

- [GitHub Copilot 공식 문서](https://docs.github.com/en/copilot)
- [GitHub Copilot 기능](https://github.com/features/copilot)
- [GitHub Copilot 가격](https://github.com/features/copilot/plans)
- [Agent Mode 가이드](https://github.blog/ai-and-ml/github-copilot/agent-mode-101-all-about-github-copilots-powerful-mode/)
- [지원 모델](https://docs.github.com/en/copilot/reference/ai-models/supported-models)
