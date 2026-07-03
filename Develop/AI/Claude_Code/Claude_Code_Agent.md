---
title: Claude Code Agent 시스템
tags: [ai, claude-code, agent, sub-agent, context-management]
updated: 2026-06-06
---

# Claude Code Agent 시스템

Claude Code 세션 안에서 작업을 위임하는 도구가 Agent다. 복잡한 작업을 서브 에이전트에게 넘기면 메인 컨텍스트 윈도우를 보호하면서 병렬 처리가 가능하다. 외부에서 Agent SDK로 여러 인스턴스를 띄우는 [오케스트레이션](Claude_Code_Orchestration.md)과 다르게, 이건 **하나의 Claude Code 세션 내부에서 동작하는 위임 메커니즘**이다.

서브 에이전트는 별도 컨텍스트 윈도우에서 돈다. 메인 에이전트가 50개 파일을 읽으면 그만큼 컨텍스트가 차오르지만, 서브 에이전트가 같은 작업을 한 뒤 요약본만 돌려주면 메인은 그 요약만 받는다. 이게 위임의 본질이고, 나머지 옵션(병렬, 백그라운드, worktree)은 전부 이 골격 위에서 동작한다.

---

## 1. Agent 도구의 기본 구조

Agent 도구를 호출하면 새 서브 에이전트가 생성된다. 서브 에이전트는 독립된 컨텍스트에서 실행되고, 작업이 끝나면 결과를 메인 에이전트에게 텍스트로 반환한다.

필수 파라미터는 둘이다.

- `description`: 3~5단어로 작업을 요약한다. 에이전트 관리와 로그에 쓰인다.
- `prompt`: 서브 에이전트에게 넘기는 지시사항. 서브 에이전트가 받는 유일한 컨텍스트다.

선택 파라미터는 다음과 같다.

- `subagent_type`: 에이전트 유형. 기본값은 `general-purpose`다.
- `isolation`: `"worktree"`로 지정하면 git worktree에서 격리 실행된다.
- `model`: 서브 에이전트가 쓸 모델 지정(`sonnet`, `opus`, `haiku`).
- `run_in_background`: `true`면 백그라운드 실행.

```
Agent({
  description: "토큰 갱신 버그 조사",
  subagent_type: "general-purpose",
  prompt: "src/auth/token.service.ts의 refreshToken 메서드에서
    만료 토큰 처리 시 500 에러가 발생한다. 원인을 찾고 수정 방안을 제시해.",
})
```

서브 에이전트는 한 번의 응답으로 메인에게 결과 텍스트를 돌려준다. 메인 에이전트는 그 결과를 받아 다음 판단을 내린다.

---

## 2. 빌트인 서브 에이전트 유형

Claude Code에는 세 가지 빌트인 에이전트가 들어 있다. 각각 사용 도구와 시스템 프롬프트가 다르다.

### 2.1 general-purpose

모든 도구에 접근 가능한 범용 에이전트다. 코드 검색, 파일 수정, 셸 명령 실행까지 대부분의 작업을 처리한다. `subagent_type`을 지정하지 않으면 이 유형이 선택된다.

```
Agent({
  description: "인증 버그 조사 및 수정",
  prompt: "src/auth/token.service.ts:45에서 refreshToken()이
    만료 토큰을 받았을 때 catch 블록이 비어 있어 500이 떨어진다.
    catch에서 InvalidTokenException을 던지도록 수정하고,
    src/auth/__tests__/token.service.spec.ts의 케이스도 보강해.",
})
```

읽기·쓰기·실행을 모두 해야 하는 작업에 쓴다. 조사 후 바로 수정까지 자율적으로 마무리하게 하고 싶을 때 적합하다.

### 2.2 Explore

코드베이스 탐색에 특화된 에이전트다. 파일 검색(Glob), 코드 검색(Grep), 파일 읽기(Read)만 가능하고 Edit, Write, Agent 호출은 막혀 있다.

탐색 범위는 `quick`, `medium`, `very thorough` 중 하나로 지정한다. 프롬프트 안에 명시하면 된다.

```
Agent({
  description: "결제 모듈 구조 파악",
  subagent_type: "Explore",
  prompt: "src/payment/ 디렉토리의 구조를 파악해.
    어떤 서비스가 있고, 외부 PG사 연동은 어떤 파일에서 처리하는지,
    트랜잭션 처리 방식은 어떤지 정리해. thoroughness: very thorough",
})
```

Explore 에이전트를 쓰는 기준은 단순하다. 파일 패턴 검색이나 키워드 검색이 3번 이상 필요할 것 같으면 띄운다. 1~2번의 Grep이나 Glob으로 끝나는 작업이면 직접 도구를 호출하는 쪽이 빠르다.

### 2.3 Plan

구현 계획 수립에 특화된 에이전트다. 코드를 읽고 분석할 수 있지만 수정은 못 한다. 단계별 계획, 관련 파일 식별, 아키텍처 트레이드오프 분석을 반환한다.

```
Agent({
  description: "TypeORM 마이그레이션 계획",
  subagent_type: "Plan",
  prompt: "TypeORM 0.2에서 0.3으로 마이그레이션해야 한다.
    현재 코드에서 0.2 전용 API를 쓰는 부분을 찾고,
    수정 순서와 각 단계에서 막힐 만한 부분을 정리해.",
})
```

구현이 시작된 후 코드를 만지기 전에 한 번 띄우면 좋다. Plan 에이전트의 출력은 메인 에이전트가 구현을 어떻게 쪼갤지 결정하는 입력이 된다.

### 유형 선택 기준

| 상황 | 적합한 유형 |
|------|------------|
| 코드 탐색, 구조 파악, 사용처 검색 | Explore |
| 구현 전 설계, 리팩토링 단계 분해 | Plan |
| 코드 수정, 버그 수정, 기능 구현 | general-purpose |
| 조사 + 수정이 한 흐름인 작업 | general-purpose |

---

## 3. 커스텀 에이전트 정의 (`.claude/agents/`)

빌트인 에이전트로 안 풀리는 작업이 있다. 예를 들어 "마이그레이션 SQL을 검토하면서 락 동시성 위험을 봐 달라"든가 "API 응답 스키마와 OpenAPI 문서가 어긋났는지 확인해 달라" 같은 작업은 매번 긴 프롬프트로 동작 규칙을 풀어 쓰는 게 비효율이다. 이럴 때 `.claude/agents/` 디렉토리에 마크다운 파일로 커스텀 에이전트를 정의한다.

### 3.1 디렉토리 위치

- `프로젝트_루트/.claude/agents/*.md`: 프로젝트별 에이전트
- `~/.claude/agents/*.md`: 사용자 전역 에이전트

같은 이름의 에이전트가 두 곳에 있으면 프로젝트 로컬이 우선이다. 프로젝트 단위로 동작 규칙을 고정하고 싶으면 로컬에 두고, 모든 프로젝트에 공유할 도구라면 전역에 둔다.

### 3.2 마크다운 정의 형식

에이전트 파일은 YAML frontmatter + 본문 형태다. frontmatter가 에이전트 메타데이터, 본문이 시스템 프롬프트가 된다.

```markdown
---
name: db-migration-reviewer
description: 마이그레이션 SQL을 검토해서 락 위험, NULL 처리, 인덱스 변경 영향을 짚어낸다. 새 마이그레이션 파일을 작성하거나 수정한 직후에 사용한다.
tools: Read, Grep, Glob, Bash
model: opus
---

너는 5년차 DBA 출신 백엔드 개발자다.

검토 대상 마이그레이션을 읽고 다음 항목을 진단해라.

1. ALTER TABLE이 수반하는 락 등급 (ACCESS EXCLUSIVE 여부, 큰 테이블에서의 위험)
2. NOT NULL 컬럼 추가 시 기본값 처리 방식
3. 인덱스 생성이 CONCURRENTLY인지, 아니면 차단 락인지
4. 기존 코드 경로(서비스 레이어, ORM 모델)에 미치는 영향

결과는 다음 구조로 반환해라.
- safety: safe | risky | dangerous
- reasons: 위 항목별 진단
- recommended_actions: 위험 등급일 때 권장 조치
```

frontmatter 필드의 의미는 다음과 같다.

- `name`: 에이전트 식별자. `subagent_type`에 이 이름을 넘겨 호출한다.
- `description`: 에이전트의 목적과 호출 타이밍. 메인 에이전트가 어떤 작업에 이걸 띄울지 판단하는 근거다. 구체적으로 써야 한다.
- `tools`: 쉼표 구분으로 허용 도구를 지정한다. 생략하면 모든 도구에 접근한다. 읽기 전용 에이전트로 만들고 싶으면 `Read, Grep, Glob` 정도로 제한한다.
- `model`: 서브 에이전트가 쓸 모델. `opus`, `sonnet`, `haiku` 중 선택. 비용이 큰 작업이 아니면 보통 생략한다.

본문은 시스템 프롬프트로 들어간다. 역할, 작업 절차, 출력 형식을 분명히 적는다. 본문이 비어 있으면 빌트인 에이전트와 다를 게 없으니 굳이 만들지 마라.

### 3.3 호출 방법

정의한 이름을 `subagent_type`에 넘긴다.

```
Agent({
  description: "마이그레이션 0042 검토",
  subagent_type: "db-migration-reviewer",
  prompt: "db/migrations/0042_add_user_status.sql을 검토해.
    대상 테이블 users는 약 5천만 행이다.
    배포 시 다운타임 없이 적용 가능한지 판단해.",
})
```

메인 에이전트는 frontmatter의 `description`을 보고 "이 작업에 이 에이전트가 맞다"고 판단해서 호출한다. 그래서 `description`은 단순 설명이 아니라 **언제 띄워야 하는지**를 명시해야 한다. "마이그레이션 검토용 에이전트"보다 "새 마이그레이션 파일을 작성하거나 수정한 직후에 사용한다"가 훨씬 잘 작동한다.

### 3.4 커스텀 에이전트가 빛을 발하는 상황

- 같은 종류의 검토를 반복적으로 돌려야 할 때 (예: PR마다 보안 리뷰, 마이그레이션 리뷰)
- 도메인 특화 규칙을 시스템 프롬프트에 박아두고 싶을 때 (예: 자사 API 컨벤션 체커)
- 도구 권한을 제한하고 싶을 때 (예: Read만 허용해서 수정 사고를 막는 코드 리뷰 에이전트)

같은 프롬프트를 두 번 이상 손으로 쓰고 있으면 커스텀 에이전트로 옮길 때다.

---

## 4. 컨텍스트 분리 원칙

서브 에이전트는 **메인 대화의 컨텍스트를 전혀 모른다.** 이전에 어떤 대화가 오갔는지, 어떤 파일을 읽었는지, 어떤 시도를 했는지 — 서브 에이전트가 아는 건 오직 `prompt`로 넘긴 내용뿐이다.

분리가 의도된 이유가 셋 있다.

1. **메인 컨텍스트 보호**: 대규모 검색 결과나 긴 파일 내용이 메인 윈도우를 잡아먹지 않는다.
2. **독립적 판단**: 메인 에이전트의 선입견 없이 새로운 시각으로 접근한다.
3. **실패 격리**: 서브 에이전트가 잘못된 방향으로 가도 메인 컨텍스트에 영향이 없다.

### 4.1 프롬프트 작성의 핵심

서브 에이전트에게 넘기는 프롬프트는 **방금 들어온 동료에게 브리핑하듯** 작성한다.

나쁜 예:

```
Agent({
  description: "버그 수정",
  prompt: "위에서 찾은 문제를 수정해줘.",  // 서브 에이전트는 '위'가 뭔지 모른다
})
```

좋은 예:

```
Agent({
  description: "토큰 갱신 버그 수정",
  prompt: "src/auth/token.service.ts의 refreshToken() 메서드(약 45번째 줄)에서
    만료된 refresh token을 검증할 때 catch 블록이 비어 있어
    500 에러가 발생한다. catch에서 InvalidTokenException을 던지도록 수정해.
    기존 테스트 파일은 src/auth/__tests__/token.service.spec.ts다.",
})
```

프롬프트에 포함해야 하는 것:

- 달성하려는 목표와 그 이유
- 이미 확인한 사실 (파일 경로, 라인 번호, 에러 메시지)
- 시도해서 안 된 접근 방법
- 코드 수정 작업인지, 조사만 하면 되는지 명시

### 4.2 결과 활용 시 주의점

서브 에이전트가 반환하는 건 **요약 텍스트**다. "파일을 수정했다"는 보고가 와도 그 보고만 가지고 사용자에게 "완료됐다"고 말하면 안 된다. 보고는 의도를 설명하는 것이지 결과를 보장하는 게 아니다. 수정 결과는 직접 확인해야 한다.

---

## 5. 포그라운드 vs 백그라운드 실행

### 5.1 포그라운드 (기본)

서브 에이전트가 끝날 때까지 메인 에이전트가 기다린다. 서브 에이전트의 결과가 다음 작업의 입력일 때 쓴다.

```
Agent({
  description: "API 엔드포인트 조사",
  prompt: "src/api/ 디렉토리에서 인증이 필요한 엔드포인트 목록을 정리해.",
})
// 결과를 받아서 다음 작업에 사용
```

### 5.2 백그라운드

`run_in_background: true`로 지정하면 서브 에이전트가 백그라운드에서 실행된다. 메인 에이전트는 다른 작업을 계속 진행하고, 서브 에이전트가 끝나면 자동으로 알림을 받는다.

```
Agent({
  description: "테스트 커버리지 분석",
  prompt: "전체 테스트 커버리지를 분석하고 커버리지 낮은 모듈 상위 5개를 정리해.",
  run_in_background: true,
})
// 백그라운드에서 도는 동안 메인은 다른 작업 진행
```

백그라운드 에이전트를 쓰는 상황:

- 시간이 오래 걸리는 분석 작업을 돌려놓고 다른 일을 먼저 처리할 때
- 결과가 당장은 필요 없지만 나중에 참고할 정보를 모을 때

백그라운드 에이전트가 실행 중일 때 sleep이나 polling으로 상태를 확인할 필요가 없다. 완료되면 자동으로 알림이 온다. 폴링은 토큰만 낭비한다.

---

## 6. Worktree 격리 모드

`isolation: "worktree"`를 지정하면 서브 에이전트가 임시 git worktree에서 작업한다. 메인 작업 디렉토리의 파일을 건드리지 않으므로, 실험적인 변경을 안전하게 시도한다.

```
Agent({
  description: "리팩토링 실험",
  isolation: "worktree",
  prompt: "src/payment/checkout.service.ts의 processPayment 메서드를
    Command 패턴으로 리팩토링해봐. 테스트가 통과하는지도 확인해.",
})
```

동작 방식은 다음과 같다.

- 서브 에이전트 시작 시 임시 worktree가 생성된다 (약 200~500ms 셋업 오버헤드)
- 서브 에이전트는 그 worktree 안에서 파일을 읽고 수정한다
- 작업이 끝나면 변경 사항이 없을 때 worktree가 자동 삭제되고, 변경이 있으면 worktree 경로와 브랜치 이름이 결과에 포함된다

worktree를 쓰는 경우:

- 파괴적인 리팩토링을 시험해보고 싶을 때
- 여러 접근 방법을 동시에 시도하고 비교하고 싶을 때 (각 에이전트가 별도 worktree에서 동작하므로 충돌이 없다)
- 메인 브랜치 상태를 확실히 보전해야 할 때

worktree 생성에는 비용이 든다. 한 줄 수정 같은 작업에 worktree를 띄우는 건 낭비다. 병렬로 같은 파일을 만지는 에이전트 여러 개를 띄우는 게 아니라면 굳이 쓸 필요 없다.

---

## 7. 병렬 에이전트 패턴

독립적인 작업 여러 개를 동시에 돌려야 할 때, **하나의 응답에서 여러 Agent 호출을 한꺼번에 발사**하면 병렬로 실행된다.

```
// 하나의 응답에서 세 개의 Agent를 동시에 호출
Agent({
  description: "인증 모듈 분석",
  subagent_type: "Explore",
  prompt: "src/auth/ 디렉토리의 구조와 인증 방식을 분석해.",
})

Agent({
  description: "결제 모듈 분석",
  subagent_type: "Explore",
  prompt: "src/payment/ 디렉토리의 구조와 PG사 연동 방식을 분석해.",
})

Agent({
  description: "알림 모듈 분석",
  subagent_type: "Explore",
  prompt: "src/notification/ 디렉토리의 구조와 알림 발송 채널을 분석해.",
})
```

병렬 실행의 조건은 하나다. 각 에이전트의 작업이 서로 의존하지 않아야 한다. A 에이전트의 결과가 B 에이전트의 입력이 되는 구조라면 순차 실행해야 한다.

### 7.1 병렬 + 순차 조합

실무에서는 "먼저 탐색을 병렬로 돌리고, 결과를 모아서 다음 단계를 진행"하는 패턴을 자주 쓴다.

```
// 1단계: 병렬 탐색 (하나의 메시지에서 동시 호출)
Agent({ description: "프론트 코드 조사", ... })
Agent({ description: "백엔드 코드 조사", ... })
Agent({ description: "DB 스키마 조사", ... })

// 2단계: 세 에이전트의 결과를 종합해서 구현 에이전트에 전달
Agent({
  description: "기능 구현",
  prompt: `아래 조사 결과를 바탕으로 사용자 프로필 수정 기능을 구현해.
    프론트 조사: ${result1}
    백엔드 조사: ${result2}
    DB 스키마: ${result3}`,
})
```

병렬 호출은 응답 한 번에 묶어야 진짜 병렬이다. 응답을 끊어서 차례로 호출하면 순차 실행과 다를 게 없다.

---

## 8. 직접 도구 호출 vs 서브 에이전트 위임

모든 작업에 서브 에이전트를 쓸 필요는 없다. 간단한 작업에 서브 에이전트를 띄우면 오버헤드만 생긴다.

### 직접 도구를 호출하는 게 나은 경우

- 파일 하나를 읽거나 수정할 때
- 특정 키워드로 Grep 한두 번 돌릴 때
- 이미 경로를 알고 있는 파일에 접근할 때
- 결과를 즉시 다음 판단에 써야 할 때

### 서브 에이전트에 위임하는 게 나은 경우

- 탐색 범위가 넓어서 Grep/Glob을 여러 번 조합해야 할 때
- 검색 결과가 클 것으로 예상되어 메인 컨텍스트를 보호하고 싶을 때
- 독립적인 작업을 병렬로 처리하고 싶을 때
- 코드 수정 후 테스트까지 자율적으로 마무리하게 하고 싶을 때
- worktree 격리가 필요한 실험적 작업일 때

판단 기준을 하나로 압축하면: **메인 에이전트가 직접 했을 때 컨텍스트가 지저분해지거나 시간이 오래 걸리는 작업**을 위임한다.

---

## 9. 흔한 실수와 대응

### 9.1 컨텍스트 누락

가장 빈번한 실수다. 메인 대화에서 이미 알고 있는 정보를 프롬프트에 넣지 않는다.

```
// 이렇게 하면 서브 에이전트가 처음부터 다시 조사한다
Agent({
  prompt: "이 버그를 수정해줘",
})

// 이미 파악한 정보를 전부 넘겨야 한다
Agent({
  prompt: "src/auth/session.ts:72에서 isExpired() 체크 후
    세션 갱신 로직이 빠져 있어 만료된 세션이 유지되는 버그가 있다.
    isExpired()가 true일 때 renewSession()을 호출하도록 수정해.",
})
```

### 9.2 이해를 위임하기

서브 에이전트에게 "조사 결과를 바탕으로 수정해줘"라고 하면서 정작 조사 결과를 분석하지 않고 그대로 넘기는 경우다. 합성과 판단은 메인 에이전트의 몫이다.

```
// 나쁜 패턴: 이해를 위임
const result = await Agent({ prompt: "문제를 조사해줘" })
Agent({ prompt: `조사 결과를 바탕으로 수정해줘: ${result}` })

// 좋은 패턴: 메인 에이전트가 이해하고, 구체적 지시를 내린다
const result = await Agent({ prompt: "문제를 조사해줘" })
// 메인이 결과를 분석한 뒤:
Agent({
  prompt: "src/auth/session.ts:72에 renewSession() 호출을 추가해.
    조건은 isExpired()가 true일 때.",
})
```

### 9.3 짧은 프롬프트

"간결함"과 "부족함"은 다르다. 3줄짜리 프롬프트로 서브 에이전트를 보내면 에이전트가 자기 판단으로 채워야 할 빈칸이 너무 많다. 그 판단이 항상 맞지는 않는다.

### 9.4 결과 맹신

서브 에이전트가 "수정 완료"라고 보고했다고 끝이 아니다. 보고는 서브 에이전트가 **의도한 바**를 설명하는 거지, 실제로 그렇게 됐다는 보장이 아니다. 코드를 수정한 서브 에이전트의 결과는 반드시 실제 파일 변경을 확인한다.

### 9.5 불필요한 에이전트 남용

파일 하나 읽는 데 서브 에이전트를 쓰거나, 간단한 Grep 하나에 Explore 에이전트를 띄우는 경우다. 서브 에이전트를 생성하고 결과를 주고받는 데 오버헤드가 있다. 직접 할 수 있는 건 직접 한다.

### 9.6 커스텀 에이전트의 description 부실

`.claude/agents/` 마크다운에서 `description`을 "리뷰 에이전트"처럼 짧게 적으면 메인이 언제 띄워야 할지 모른다. 호출 트리거 조건을 명확히 적는다. "새 마이그레이션 파일을 작성하거나 기존 마이그레이션을 수정한 직후에 사용한다"처럼 구체적이어야 메인이 정확한 타이밍에 호출한다.

---

## 10. 실전 활용 예시

### 10.1 대규모 리팩토링 전 영향도 분석

특정 인터페이스를 변경하기 전 사용처를 전수 조사하는 상황이다.

```
Agent({
  description: "UserService 사용처 전수 조사",
  subagent_type: "Explore",
  prompt: "UserService 인터페이스의 모든 사용처를 찾아.
    import하는 파일, 의존성 주입으로 받는 파일, 테스트에서 mock하는 파일
    전부 정리해. 파일 경로와 사용 방식(직접 호출, DI, mock)을 구분해서 알려줘.
    thoroughness: very thorough",
})
```

### 10.2 두 가지 접근 방식 비교

worktree 격리로 두 가지 구현을 동시에 시도한다.

```
// 두 에이전트를 병렬로, 각각 격리된 worktree에서 실행
Agent({
  description: "전략 A: 캐시 적용",
  isolation: "worktree",
  prompt: "src/product/product.service.ts의 getProductList 메서드에
    Redis 캐시를 적용해. TTL 5분, 캐시 키는 쿼리 파라미터 기반으로.
    테스트도 수정해.",
})

Agent({
  description: "전략 B: 쿼리 최적화",
  isolation: "worktree",
  prompt: "src/product/product.service.ts의 getProductList 메서드의
    DB 쿼리를 최적화해. N+1 문제가 있으면 join으로 바꾸고,
    불필요한 컬럼 조회를 제거해. 테스트도 수정해.",
})
```

두 에이전트가 각각 다른 worktree에서 작업하므로 충돌이 없다. 결과를 비교한 후 나은 쪽을 선택한다.

### 10.3 멀티 모듈 동시 조사

모노레포에서 여러 모듈을 동시에 탐색하는 경우다.

```
Agent({
  description: "auth 모듈 조사",
  subagent_type: "Explore",
  prompt: "packages/auth/에서 JWT 토큰 생성과 검증 로직을 찾아.
    어떤 라이브러리를 쓰는지, 토큰 만료 시간은 어떻게 설정하는지 정리해.",
  run_in_background: true,
})

Agent({
  description: "gateway 모듈 조사",
  subagent_type: "Explore",
  prompt: "packages/gateway/에서 인증 미들웨어가 JWT를 어떻게 검증하는지 찾아.
    토큰 갱신 로직이 있는지, 만료 처리는 어떻게 하는지 정리해.",
  run_in_background: true,
})
```

백그라운드로 돌려놓고, 그 사이 관련 문서를 읽거나 다른 준비 작업을 한다.

### 10.4 커스텀 에이전트로 PR 리뷰 자동화

`.claude/agents/api-contract-reviewer.md`에 다음과 같이 정의해둔다.

```markdown
---
name: api-contract-reviewer
description: 변경된 컨트롤러 코드와 OpenAPI 스펙(openapi.yaml)이 어긋났는지 검증한다. 컨트롤러 파일이 수정된 직후 사용한다.
tools: Read, Grep, Glob
---

너는 API 계약 검토자다.

작업 절차:
1. 변경된 컨트롤러에서 라우트 경로, 메서드, 요청/응답 스키마를 추출한다
2. docs/openapi.yaml의 해당 경로를 찾아 비교한다
3. 불일치가 있으면 정확한 위치와 차이를 보고한다

불일치 항목:
- 라우트 경로/메서드
- 요청 파라미터(쿼리, 바디) 스키마
- 응답 스키마와 상태 코드

코드는 절대 수정하지 마라. 검토 결과만 반환한다.
```

이후 컨트롤러를 수정한 직후 다음 호출이 가능하다.

```
Agent({
  description: "주문 API 컨트랙트 검토",
  subagent_type: "api-contract-reviewer",
  prompt: "src/order/order.controller.ts의 변경을 docs/openapi.yaml과
    대조해. 특히 POST /orders의 요청 바디 스키마 변경에 주목해.",
})
```

같은 검토를 매번 손으로 프롬프트 풀어 쓸 필요가 없어진다. 시스템 프롬프트에 박힌 절차를 따라 일관된 결과가 나온다.

---

## 참고

- [Claude Code 기본 문서](Claude_Code.md)
- [오케스트레이션 (Agent SDK/외부 자동화)](Claude_Code_Orchestration.md)
- [Worktree 격리](Claude_Code_Worktree.md)
- [Claude Code 공식 문서](https://docs.anthropic.com/en/docs/claude-code)
