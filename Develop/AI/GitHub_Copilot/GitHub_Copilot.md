---
title: GitHub Copilot 사용법 및 핵심 개념
tags: [ai, github-copilot, code-completion, agent-mode, ide]
updated: 2026-05-03
---

# GitHub Copilot

## 1. GitHub Copilot이란

GitHub Copilot은 GitHub(Microsoft)이 만든 AI 코딩 어시스턴트다. IDE 안에 붙어서 인라인 자동완성, 채팅, Agent Mode를 통한 자율 작업, PR 리뷰까지 처리한다. 2021년 OpenAI Codex 기반으로 출시된 이후 모델 라인업이 GPT, Claude, Gemini, Grok까지 확장되면서 사실상 IDE 통합 AI 도구의 표준 자리에 가깝게 자리잡았다.

5년차 정도 백엔드 일을 하다 보면 새 도구를 도입할 때 회사 정책(보안, 라이선스, IP)이 같이 걸린다. Copilot이 다른 도구보다 회사에서 통과되기 쉬운 이유는 Microsoft/GitHub라는 공급자 신뢰도, Business 플랜의 IP indemnity, 그리고 GitHub Enterprise 권한 모델과의 연동 때문이다. 기능적으로 가장 앞서서가 아니라 "도입 마찰"이 가장 적어서 선택되는 경우가 많다.

### 1.1 실제 동작 방식

Copilot은 크게 세 가지 모드로 동작한다.

**인라인 자동완성**은 커서 위치 주변 코드를 컨텍스트로 보내고 다음에 올 코드를 받아서 회색 텍스트(ghost text)로 보여준다. 한 줄 단위가 아니라 함수 단위, 블록 단위로 제안하기도 한다. 백엔드에서 비슷한 패턴의 DTO나 Mapper, 테스트 코드를 반복 작성할 때 가장 효율이 잘 나온다. 반대로 도메인 로직이나 비즈니스 규칙이 들어가는 코드에서는 그럴듯하지만 틀린 제안이 자주 나온다.

**채팅**은 IDE 사이드 패널에서 자연어로 질문하고 답을 받는 형태다. 현재 파일이나 선택한 영역을 컨텍스트로 명시적으로 첨부할 수 있다. 코드 리뷰 전 "이 함수 어떻게 동작하는지 설명해줘"같이 한 번씩 도움을 받는 용도로 쓰면 무난하다.

**Agent Mode**는 GitHub Issue를 Copilot에 할당하면 백그라운드에서 코드를 분석하고 수정한 뒤 PR을 만들어주는 모드다. CI 환경에서 도커 컨테이너를 띄워서 테스트까지 돌린다. 단순한 의존성 업데이트나 명확한 버그 수정 정도는 자동으로 처리되지만, 도메인 컨텍스트가 필요한 작업은 여전히 사람 손이 더 들어간다.

### 1.2 다른 AI 도구와의 비교

| 특징 | GitHub Copilot | Claude Code | Cursor |
|------|---------------|------------|--------|
| 인터페이스 | IDE 플러그인 | CLI | 독립 IDE |
| 접근 방식 | 보조형 (사용자 주도) | 에이전틱 (자율 실행) | 에이전틱 (IDE 내장) |
| 코드 완성 | 인라인 자동완성 | 없음 | Tab 자동완성 |
| Agent Mode | 지원 (2026~) | 기본 동작 방식 | 장시간 에이전트 지원 |
| IDE 지원 | 다양한 IDE | 터미널 전용 | VS Code 포크 전용 |
| 가격 | $10~39/월 | API 사용량 기반 | $20~200/월 |

Copilot의 강점은 "이미 쓰던 IDE에 붙는다"는 점 하나다. JetBrains 라이선스가 있는 팀에 Cursor를 강제로 도입하기는 어렵지만 Copilot은 IntelliJ 플러그인으로 그냥 깔린다.

---

## 2. 가격

### 2.1 개인 플랜

| 플랜 | 가격 | 코드 완성 | 프리미엄 요청 |
|------|------|----------|-------------|
| Free | $0 | 2,000회/월 | 50회/월 |
| Pro | $10/월 | 무제한 | 300회/월 |
| Pro+ | $39/월 | 무제한 | 1,500회/월 |

### 2.2 조직 플랜

| 플랜 | 가격 | 특징 |
|------|------|------|
| Business | $19/사용자/월 | 조직 관리, 감사 로그, 정책 제어, IP indemnity |
| Enterprise | $39/사용자/월 | 지식 베이스, 커스텀 모델, GitHub.com 지식 검색 |

### 2.3 프리미엄 요청과 모델별 비용

가격표에서 가장 헷갈리는 게 "프리미엄 요청"이다. 인라인 자동완성과 GPT-4.1 같은 기본 모델 호출은 카운트되지 않는다. 카운트되는 건 Claude Opus, GPT-5, Gemini Pro 같은 상위 모델을 채팅이나 Agent Mode에서 호출했을 때다.

요청 1건당 차감되는 가중치가 모델마다 다르다. 대략적인 비율은 다음과 같다.

| 모델 | 요청당 차감 |
|------|-----------|
| GPT-4.1, GPT-5 mini | 0배 (무제한) |
| Claude Sonnet, GPT-5 | 1배 |
| Gemini Pro | 1배 |
| Claude Opus | 10배 |

Pro 플랜의 300회 한도에서 Opus를 30번 쓰면 한도 끝이다. Agent Mode 1회 실행이 내부적으로 여러 번의 모델 호출을 트리거하기 때문에 Opus로 Agent Mode를 몇 번 돌리면 금방 한도가 차는 경험을 한다.

한도를 초과하면 두 가지 동작이 있다. 개인 플랜은 다음 달까지 프리미엄 모델 호출이 막히고 기본 모델만 쓸 수 있다. 조직 플랜은 관리자가 "초과분 과금 허용" 옵션을 켜두면 초과분이 사용자당 청구된다. 무심코 켜두면 월말에 청구서가 꽤 커지는 경우가 있어서 조직 단위로 한도와 알림을 같이 설정해야 한다.

---

## 3. 핵심 기능

### 3.1 코드 자동완성

IDE에서 코딩 중 실시간으로 코드 제안을 표시한다. Tab 키로 수락, Esc로 거부.

```python
def calculate_discount(price, discount_rate):
    if discount_rate < 0 or discount_rate > 1:
        raise ValueError("할인율은 0~1 사이여야 합니다")
    return price * (1 - discount_rate)
```

자동완성이 잘 안 맞을 때는 거의 컨텍스트 부족이 원인이다. Copilot은 현재 파일 상단, 같은 디렉토리의 다른 파일, 그리고 최근 열어둔 탭을 컨텍스트로 사용한다. 관련된 인터페이스나 타입 정의 파일을 미리 열어두는 것만으로도 제안 품질이 눈에 띄게 달라진다.

### 3.2 Agent Mode

Agent Mode는 GitHub Issue를 할당하면 백그라운드에서 코드를 분석, 수정, 테스트하고 PR을 생성한다.

동작 흐름:

```
1. GitHub Issue에 Copilot 할당
2. 요구사항 분석 및 변경 계획 수립
3. 멀티 파일 편집 실행
4. 테스트 실행 및 검증
5. 보안 스캔 (코드 스캐닝, 시크릿 스캐닝)
6. PR 생성 → 사람이 리뷰
```

Agent Mode는 GitHub Actions 환경 위에서 컨테이너를 띄워 동작한다. 즉 로컬에서 잘 빌드되고 테스트되는 코드라도, Actions 컨테이너에서 빌드/테스트가 안 되면 Agent는 같은 자리에서 막힌다.

### 3.3 채팅 인터페이스

자연어로 코딩 질문, 코드 설명, 리팩토링 요청 가능.

채팅 참여자(@mentions):

| 참여자 | 설명 |
|--------|------|
| `@github` | GitHub 컨텍스트 (이슈, PR, 디스커션) |
| `@workspace` | 프로젝트 전체 컨텍스트 |
| `@terminal` | 터미널/CLI 컨텍스트 |
| `@vscode` | VS Code 관련 기능 |

채팅 변수(#mentions):

| 변수 | 설명 |
|------|------|
| `#file` | 현재 파일 |
| `#selection` | 선택한 코드 영역 |
| `#project` | 프로젝트 전체 |

`@workspace`는 인덱싱이 끝나야 제대로 동작한다. 큰 모노레포에서는 인덱싱에 몇 분 걸리거나 메모리를 많이 먹어서 IDE가 느려진다. 이런 환경에서는 `#file`로 명시적으로 파일을 지정하는 편이 더 안정적이다.

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

PR에 대해 AI 기반 코드 리뷰를 자동으로 수행한다. 리뷰 품질은 모델과 PR 크기에 따라 편차가 크다. 작은 PR(파일 5개 이하)에서는 누락된 null 체크나 잘못된 타입 캐스팅 같은 표면적인 이슈를 잘 잡는다. 1000라인이 넘는 큰 PR에서는 컨텍스트가 잘려서 두루뭉실한 코멘트만 다는 경우가 많다.

---

## 4. 지원 모델

### 4.1 사용 가능한 모델

| 제공사 | 모델 | 비고 |
|--------|------|------|
| OpenAI | GPT-5.2, GPT-4.1, GPT-5 mini | GPT-4.1이 기본 |
| Anthropic | Claude Opus 4.6, Sonnet 4.5, Haiku 4.5 | Opus는 Enterprise |
| Google | Gemini 3 Pro, Gemini 2.5 Pro | 프리뷰 |
| xAI | Grok Code Fast | 코딩 특화 |

Auto 모드는 작업 유형을 보고 모델을 골라준다고 되어 있는데, 실제로는 비용이 낮은 쪽으로 라우팅되는 경향이 있다. 중요한 작업이라면 모델을 직접 지정하는 편이 결과가 일관된다.

---

## 5. 지원 IDE

| IDE | 기능 |
|-----|------|
| VS Code | 전체 기능 (Agent Mode, 채팅, 자동완성) |
| Visual Studio | 전체 기능 |
| JetBrains | IntelliJ, PyCharm, WebStorm 등 |
| Vim/Neovim | 자동완성, 채팅 |
| Xcode | 자동완성, 채팅, 명령어 |
| Eclipse | 자동완성 |
| GitHub.com | 웹 채팅, 에이전트 |
| GitHub CLI | 터미널 에이전트 |
| GitHub Mobile | 모바일 채팅 |

### 5.1 JetBrains와 VS Code의 실제 차이

문서상으로는 둘 다 지원되지만, 신기능은 항상 VS Code에 먼저 들어가고 JetBrains는 몇 주~몇 달 늦는다. 실무에서 자주 부딪히는 차이는 다음과 같다.

JetBrains 플러그인은 IDE의 기존 자동완성과 충돌해서 제안이 깜빡거리거나 한 박자 늦게 뜬다. IntelliJ의 ML 기반 자동완성을 끄거나 우선순위를 조정해야 자연스럽게 쓸 수 있다. `.copilot/settings.json` 같은 프로젝트 레벨 인스트럭션 파일을 JetBrains 플러그인이 늦게 인식하거나 무시하는 경우가 있고, 인덱싱이 끝나기 전에 채팅을 열면 `@workspace` 컨텍스트가 비어있다.

Agent Mode와 MCP 서버 연결은 VS Code 쪽이 훨씬 안정적이다. JetBrains에서는 같은 기능이 베타 토글 뒤에 숨어있거나, 아예 GitHub 웹에서만 제공되는 경우가 많다. JetBrains를 메인으로 쓰는 팀이라면 자동완성/채팅은 IDE에서, Agent Mode는 GitHub 웹에서 쓰는 식의 분리 운영이 현실적이다.

---

## 6. 설정 및 구성

### 6.1 프로젝트 레벨 설정

`.copilot/settings.json`을 레포에 커밋하면 팀 전원에게 같은 인스트럭션이 적용된다. 추상적인 설명("좋은 코드를 작성해주세요")은 거의 효과가 없고, 컨벤션을 강제하는 구체적인 지시가 들어가야 동작이 바뀐다.

```json
{
  "copilot": {
    "chat": {
      "instructions": [
        "이 프로젝트는 Spring Boot 3.x + Kotlin + JDK 21 환경이다.",
        "코드 스타일은 ktlint 기본 규칙을 따른다. wildcard import 금지.",
        "엔티티 클래스는 data class를 사용하지 않고 일반 class에 equals/hashCode를 직접 정의한다.",
        "DTO는 record가 아닌 Kotlin data class로 작성한다.",
        "예외는 RuntimeException을 직접 던지지 않고 도메인별 예외 클래스(예: OrderNotFoundException)를 정의한다.",
        "테스트는 JUnit 5 + Kotest assertions를 사용한다. Mockito 대신 MockK를 사용한다.",
        "JPA 엔티티에 @Setter를 붙이지 않는다. 변경은 도메인 메서드로만 수행한다.",
        "Controller는 @RestController, 응답은 ResponseEntity<ApiResponse<T>> 타입으로 통일한다."
      ]
    }
  }
}
```

개인 설정은 `.copilot/settings.local.json`에 두고 `.gitignore`에 추가한다.

```json
{
  "copilot": {
    "chat": {
      "instructions": "응답은 한국어로 한다. 코드 주석은 영어로 작성한다."
    }
  }
}
```

언어/프레임워크 컨벤션을 글로 박아두면 자동완성보다 채팅과 Agent Mode에서 더 효과가 크다. 자동완성은 기본적으로 주변 코드를 따라가므로 기존 코드가 컨벤션을 잘 지키고 있다면 인스트럭션이 없어도 어느 정도 따라가지만, 새 파일을 만들거나 빈 파일에서 시작할 때는 인스트럭션이 없으면 프레임워크 디폴트 스타일이 튀어나온다.

### 6.2 커스텀 에이전트

```yaml
# .github/agents/performance-optimizer.yml
name: Performance Optimizer
description: 성능 최적화에 특화된 에이전트
instructions: |
  코드를 분석하여 성능 병목점을 찾고 최적화 방안을 제안한다.
  N+1 쿼리, 불필요한 메모리 할당, 동기 블로킹 등을 식별한다.
```

### 6.3 MCP 서버 연결과 권한 관리

MCP(Model Context Protocol) 서버를 연결하면 Copilot이 외부 도구(GitHub, Jira, DB, 사내 API 등)에 직접 접근할 수 있다. 편하지만 보안 측면에서 주의할 점이 많다.

MCP 서버는 IDE 프로세스에서 직접 실행되거나 별도 프로세스로 띄워진다. 어느 쪽이든 서버에 넘기는 토큰은 IDE 설정 파일에 평문으로 들어가는 경우가 많다. 실수로 `.vscode/settings.json`을 커밋해서 GitHub 토큰이 유출되는 사고가 종종 발생한다. 토큰은 환경 변수나 OS keychain에서 읽도록 설정해야 한다.

```json
{
  "mcp": {
    "servers": {
      "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "${env:GITHUB_TOKEN}"
        }
      }
    }
  }
}
```

권한 범위도 중요하다. PAT(Personal Access Token)에 `repo` 풀 권한을 주면 Copilot이 모든 사적 레포에 접근할 수 있다. Fine-grained PAT를 발급해서 필요한 레포와 권한만 제한해야 한다. Agent Mode에서 MCP 도구를 호출할 때 사용자 확인 없이 실행되는 도구가 있는지 미리 검토해야 한다. 파일 쓰기, 외부 API 호출 같은 도구는 매번 확인을 받도록 설정하는 편이 안전하다.

조직에서 사용한다면 GitHub MCP Registry에서 검증된 서버만 허용 목록에 넣는 정책이 필요하다. 임의의 npm 패키지를 MCP 서버로 등록하면 그 패키지가 코드와 토큰을 외부로 빼낼 수 있다.

---

## 7. 실무에서 자주 겪는 문제

### 7.1 자동완성이 잘못된 제안을 하는 패턴

자동완성은 "그럴듯한 코드"를 만드는 데 최적화되어 있어서, 실제 동작이 틀린 제안이 자주 나온다. 자주 마주치는 패턴은 다음과 같다.

존재하지 않는 메서드/필드 호출이 가장 흔하다. 라이브러리 버전이 올라가면서 메서드 시그니처가 바뀌었는데도 옛날 버전 기준으로 제안한다. 예를 들어 Spring Data JPA에서 `findById()`가 `Optional<T>`를 반환한다는 건 알지만, 사내 BaseRepository에서 `findByIdOrThrow()` 같은 커스텀 메서드를 만들어 쓰는 경우 Copilot은 그냥 `findById().get()`을 제안한다.

도메인 규칙을 무시한 검증 로직도 잦다. 결제 로직을 작성하다가 할인율 검증 코드를 자동완성으로 받으면 `if (rate < 0 || rate > 1)` 같은 일반적인 검증이 들어오는데, 사내 정책상 할인율 상한이 0.5라면 그냥 잘못된 코드다.

테스트 코드의 mock 설정에서 실제 호출 순서와 다르게 stubbing하는 경우도 흔하다. 함수 이름과 파라미터로 추측해서 mock을 짜기 때문에 실제 SUT(System Under Test)에서 어떤 순서로 호출되는지 모른다.

회피 방법은 두 가지다. 첫째, 자동완성을 받기 전에 관련 인터페이스 파일과 컨벤션 파일을 미리 열어두면 컨텍스트가 보강된다. 둘째, Tab으로 받은 코드를 그대로 두지 말고 한 번 읽고 넘긴다. 5년차쯤 되면 "이 정도는 안 보고 받아도 되겠지"라는 안일함이 가장 큰 버그 원인이다.

### 7.2 Agent Mode 트러블슈팅

**이슈 분석 실패**: Issue 본문이 짧거나 모호하면 Agent가 엉뚱한 방향으로 분석한다. "버튼이 안 눌려요" 같은 이슈를 그대로 넘기면 Agent가 추측으로 PR을 만들어 시간만 쓴다. Agent에 넘길 이슈는 재현 절차, 기대 동작, 관련 파일 경로를 본문에 명시해야 한다. 이게 안 되면 Agent를 쓰지 말고 사람이 분석한 뒤 잘게 쪼갠 작업을 채팅에서 처리하는 편이 빠르다.

**잘못된 PR 생성**: Agent가 만든 PR이 의도와 다르게 광범위하게 코드를 건드리는 경우가 있다. 흔한 원인은 (1) 이슈에 있는 키워드가 여러 파일에 흩어져 있어서 Agent가 전부 손대기로 결정하거나, (2) 테스트가 실패해서 Agent가 테스트를 "고치려고" 하다가 SUT가 아닌 테스트 자체를 망가뜨리는 경우다. 후자는 진짜 자주 나온다. 테스트가 깨졌을 때 Agent에 자동 수정을 맡기는 건 위험하다.

**테스트 실행 환경 문제**: Agent Mode는 GitHub Actions 컨테이너에서 동작한다. 로컬에서 도커 컴포즈로 띄우는 DB나 Redis가 필요한 통합 테스트는 컨테이너 안에서 같은 환경을 만들어주지 않으면 항상 실패한다. `.github/copilot-environment.yml` 같은 환경 정의 파일에 setup-services를 명시하거나, Agent용 워크플로우에 services 블록을 따로 정의해야 한다. 테스트 환경 설정이 어려운 레포에서는 Agent Mode가 거의 무용지물이다.

**시크릿 접근**: Agent가 외부 API 키나 DB 비밀번호가 필요한 작업을 할 때, GitHub Actions 시크릿을 Agent에 노출할지 결정해야 한다. 노출하면 PR 작성 과정에서 시크릿이 로그에 찍히거나 코드에 박힐 위험이 있다. 가능하면 Agent가 접근하는 환경은 운영 시크릿과 분리된 별도 환경으로 둬야 한다.

**모델별 결과 편차**: 같은 이슈를 넘겨도 모델에 따라 결과가 크게 다르다. Sonnet 4.5는 신중하게 한두 파일만 건드리는 경향이 있고, Opus 4.6은 더 넓게 손대는 대신 비용이 10배다. GPT-5는 빠르지만 컨텍스트 손실이 잦다. 팀 안에서 "이런 작업은 어느 모델"이라는 합의를 만들어두는 편이 좋다.

### 7.3 Business 플랜의 IP indemnity와 Public code filter

회사에서 Copilot을 도입할 때 법무팀에서 가장 먼저 묻는 게 "이거 쓰다가 GPL 코드가 우리 코드에 들어오면 어떻게 하냐"다. GitHub은 Business와 Enterprise 플랜에 IP indemnity(지적재산권 보상) 조항을 넣어서 이 우려에 대응한다.

조항의 핵심은 "Copilot이 제안한 코드가 제3자의 저작권을 침해해서 고객이 소송당하면 GitHub이 방어 비용과 합의금을 부담한다"는 것이다. 단, 조건이 있다. **Public code filter**(공개 코드 필터) 옵션을 켜둔 경우에 한해서만 indemnity가 적용된다.

Public code filter는 Copilot이 제안하려는 코드 스니펫이 공개 GitHub 저장소의 코드와 약 150자 이상 일치하면 그 제안을 차단하는 기능이다. 켜두면 라이선스 충돌 위험은 줄지만 자동완성 빈도가 약간 떨어진다는 체감이 있다. 끄면 더 자유롭게 제안받지만 indemnity 보호를 잃는다.

조직 관리자는 GitHub 조직 설정 → Copilot → Policies에서 이 필터를 강제로 켜둘 수 있다. 법무 통과를 받으려면 (1) 플랜은 Business 이상, (2) Public code filter는 조직 정책으로 강제 ON, (3) 데이터 사용 옵션(prompt와 suggestion을 학습에 사용하지 않음)은 OFF, 이 세 가지가 기본 세팅이다.

filter가 켜져 있다고 해서 모든 라이선스 문제가 사라지는 건 아니다. 150자 미만의 작은 스니펫은 필터를 통과하므로 함수 시그니처나 짧은 알고리즘은 여전히 공개 코드와 비슷할 수 있다. 라이선스가 민감한 코드(예: 라이선스 주석을 그대로 복사한 코드)는 사람이 한 번 더 봐야 한다.

### 7.4 컨텍스트 관리

가장 흔한 실수는 채팅에 너무 많은 파일을 첨부하는 것이다. `@workspace`나 `#project`로 전체를 던지면 모델이 정작 중요한 파일을 못 본다. 5개 이상 파일을 첨부했을 때 답변 품질이 급격히 떨어지는 게 체감된다. 변경 대상 파일과 그 파일이 의존하는 인터페이스 1~2개 정도만 첨부하는 게 가장 결과가 좋다.

긴 대화는 끊어가면서 써야 한다. 대화 컨텍스트가 길어지면 초반에 준 인스트럭션을 잊어버리거나, 중간에 한 번 잘못된 방향으로 답한 내용을 계속 끌고 간다. 작업이 한 사이클 끝나면 `/clear`로 컨텍스트를 비우는 편이 안전하다.

---

## 참고

- [GitHub Copilot 공식 문서](https://docs.github.com/en/copilot)
- [GitHub Copilot 기능](https://github.com/features/copilot)
- [GitHub Copilot 가격](https://github.com/features/copilot/plans)
- [Agent Mode 가이드](https://github.blog/ai-and-ml/github-copilot/agent-mode-101-all-about-github-copilots-powerful-mode/)
- [지원 모델](https://docs.github.com/en/copilot/reference/ai-models/supported-models)
