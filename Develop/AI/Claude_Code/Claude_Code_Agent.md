---
title: Claude Code Agent 시스템
tags: [ai, claude-code, agent, sub-agent, context-management]
updated: 2026-04-15
---

# Claude Code Agent 시스템

Claude Code 세션 안에서 작업을 위임하는 도구가 Agent다. 복잡한 작업을 서브 에이전트에게 넘기면 메인 컨텍스트 윈도우를 보호하면서 병렬 처리가 가능하다. 외부에서 Agent SDK로 여러 인스턴스를 띄우는 [오케스트레이션](Claude_Code_Orchestration.md)과 다르게, 이건 **하나의 Claude Code 세션 내부에서 동작하는 위임 메커니즘**이다.

---

## 1. Agent 도구의 기본 구조

Agent 도구를 호출하면 새로운 서브 에이전트가 생성된다. 서브 에이전트는 독립된 컨텍스트에서 실행되고, 작업이 끝나면 결과를 메인 에이전트에게 텍스트로 반환한다.

필수 파라미터는 두 개다:

- `description`: 3~5단어로 작업을 요약한다. 에이전트 관리와 로그에 쓰인다.
- `prompt`: 서브 에이전트에게 넘기는 지시사항이다. 이게 서브 에이전트가 받는 유일한 컨텍스트다.

선택 파라미터:

- `subagent_type`: 에이전트 유형. 기본값은 `general-purpose`
- `isolation`: `"worktree"` 설정 시 git worktree에서 격리 실행
- `model`: 서브 에이전트에 사용할 모델 지정 (`sonnet`, `opus`, `haiku`)
- `run_in_background`: `true`로 설정하면 백그라운드 실행

---

## 2. 서브 에이전트 유형

### 2.1 general-purpose (기본값)

모든 도구에 접근 가능한 범용 에이전트다. 코드 검색, 파일 수정, 셸 명령 실행 등 대부분의 작업을 처리한다. `subagent_type`을 지정하지 않으면 이 유형이 선택된다.

```
Agent({
  description: "인증 버그 조사",
  prompt: "src/auth/token.service.ts에서 refreshToken 메서드가 만료된 토큰에 대해 
    500 에러를 반환하는 문제를 조사해줘. 원인을 찾고 수정 방안을 제시해."
})
```

### 2.2 Explore

코드베이스 탐색에 특화된 에이전트다. 파일 검색(Glob), 코드 검색(Grep), 파일 읽기(Read) 등 읽기 전용 도구만 사용할 수 있다. Edit, Write, Agent 호출은 불가능하다.

탐색 범위를 `quick`, `medium`, `very thorough` 중 하나로 지정할 수 있다.

```
Agent({
  description: "결제 모듈 구조 파악",
  subagent_type: "Explore",
  prompt: "src/payment/ 디렉토리의 구조를 파악해줘. 
    어떤 서비스가 있고, 외부 PG사 연동은 어떤 파일에서 하는지, 
    트랜잭션 처리 방식은 어떤지 정리해. thoroughness: very thorough"
})
```

Explore 에이전트를 쓰는 기준:

- 파일 패턴 검색이나 키워드 검색이 3번 이상 필요할 것 같을 때
- 코드베이스 전반을 훑어야 할 때
- 구조 파악, 의존성 추적, 사용처 조사 같은 읽기 전용 작업

1~2번의 Grep이나 Glob으로 끝나는 작업이면 Explore 에이전트를 띄울 필요 없다. 직접 도구를 호출하는 게 빠르다.

### 2.3 Plan

구현 계획 수립에 특화된 에이전트다. 코드를 읽고 분석할 수 있지만 수정은 못 한다. 단계별 계획, 관련 파일 식별, 아키텍처 트레이드오프 분석을 반환한다.

```
Agent({
  description: "마이그레이션 계획 수립",
  subagent_type: "Plan",
  prompt: "TypeORM 0.2에서 0.3으로 마이그레이션해야 한다. 
    현재 코드에서 0.2 전용 API를 쓰는 부분을 찾고, 
    수정 순서와 각 단계에서 주의할 점을 정리해줘."
})
```

### 유형 선택 기준

| 상황 | 적합한 유형 |
|------|------------|
| 코드 탐색, 구조 파악, 사용처 검색 | Explore |
| 구현 전 설계, 리팩토링 계획 | Plan |
| 코드 수정, 버그 수정, 기능 구현 | general-purpose |
| 복잡한 조사 + 수정이 필요한 작업 | general-purpose |

---

## 3. 컨텍스트 분리 원칙

서브 에이전트는 **메인 대화의 컨텍스트를 전혀 모른다.** 이전에 어떤 대화가 오갔는지, 어떤 파일을 읽었는지, 어떤 시도를 했는지 — 서브 에이전트가 아는 건 오직 `prompt`로 넘긴 내용뿐이다.

이 분리가 의도적인 이유가 있다:

1. **메인 컨텍스트 보호**: 대규모 검색 결과나 긴 파일 내용이 메인 윈도우를 먹지 않는다
2. **독립적 판단**: 메인 에이전트의 선입견 없이 새로운 시각으로 접근할 수 있다
3. **실패 격리**: 서브 에이전트가 잘못된 방향으로 가도 메인 컨텍스트에 영향이 없다

### 3.1 프롬프트 작성의 핵심

서브 에이전트에게 넘기는 프롬프트는 **방금 들어온 동료에게 브리핑하듯** 작성해야 한다.

나쁜 예:

```
Agent({
  description: "버그 수정",
  prompt: "위에서 찾은 문제를 수정해줘."  // 서브 에이전트는 '위'가 뭔지 모른다
})
```

좋은 예:

```
Agent({
  description: "토큰 갱신 버그 수정",
  prompt: "src/auth/token.service.ts의 refreshToken() 메서드(약 45번째 줄)에서 
    만료된 refresh token을 검증할 때 catch 블록이 비어 있어서 
    500 에러가 발생한다. catch에서 InvalidTokenException을 던지도록 수정해줘. 
    기존 테스트 파일은 src/auth/__tests__/token.service.spec.ts다."
})
```

프롬프트에 포함해야 하는 것:

- 달성하려는 목표와 이유
- 이미 확인한 사실 (파일 경로, 라인 번호, 에러 메시지)
- 시도해서 안 된 접근 방법
- 코드를 수정해야 하는지, 조사만 하면 되는지 명시

### 3.2 결과 활용 시 주의점

서브 에이전트가 반환하는 건 **요약 텍스트**다. 서브 에이전트가 "파일을 수정했다"고 보고하면, 실제로 수정됐을 가능성이 높지만 보고 내용만 가지고 사용자에게 "완료됐다"고 말하면 안 된다. 수정 결과를 직접 확인해야 한다.

---

## 4. 포그라운드 vs 백그라운드 실행

### 4.1 포그라운드 (기본)

서브 에이전트가 끝날 때까지 메인 에이전트가 기다린다. 서브 에이전트의 결과가 다음 작업에 필요할 때 쓴다.

```
Agent({
  description: "API 엔드포인트 조사",
  prompt: "src/api/ 디렉토리에서 인증이 필요한 엔드포인트 목록을 정리해줘."
})
// 결과를 받아서 다음 작업에 사용
```

### 4.2 백그라운드

`run_in_background: true`로 설정하면 서브 에이전트가 백그라운드에서 실행된다. 메인 에이전트는 다른 작업을 계속 진행하고, 서브 에이전트가 끝나면 자동으로 알림을 받는다.

```
Agent({
  description: "테스트 커버리지 분석",
  prompt: "전체 테스트 커버리지를 분석하고 커버리지가 낮은 모듈 상위 5개를 정리해줘.",
  run_in_background: true
})
// 백그라운드에서 실행되는 동안 다른 작업 계속 진행
```

백그라운드 에이전트를 쓰는 상황:

- 시간이 오래 걸리는 분석 작업을 돌려놓고 다른 일을 먼저 처리할 때
- 결과가 당장은 필요 없지만 나중에 참고할 정보를 모을 때

주의할 점: 백그라운드 에이전트가 실행 중일 때 sleep이나 polling으로 상태를 확인할 필요가 없다. 완료되면 자동으로 알림이 온다.

---

## 5. Worktree 격리 모드

`isolation: "worktree"`를 설정하면 서브 에이전트가 임시 git worktree에서 작업한다. 메인 작업 디렉토리의 파일을 건드리지 않으므로, 실험적인 변경을 안전하게 시도할 수 있다.

```
Agent({
  description: "리팩토링 실험",
  isolation: "worktree",
  prompt: "src/payment/checkout.service.ts의 processPayment 메서드를 
    Command 패턴으로 리팩토링해봐. 테스트가 통과하는지 확인해줘."
})
```

동작 방식:

- 서브 에이전트 시작 시 임시 worktree가 생성된다
- 서브 에이전트는 그 worktree 안에서 파일을 읽고 수정한다
- 작업이 끝나면:
  - 변경 사항이 없으면 worktree가 자동 삭제된다
  - 변경 사항이 있으면 worktree 경로와 브랜치 이름이 결과에 포함된다

worktree를 쓰는 경우:

- 파괴적인 리팩토링을 시험해보고 싶을 때
- 여러 접근 방법을 동시에 시도하고 비교하고 싶을 때
- 메인 브랜치의 상태를 확실히 보전해야 할 때

---

## 6. 병렬 에이전트 패턴

독립적인 작업 여러 개를 동시에 돌려야 할 때, **하나의 메시지에서 여러 Agent 호출을 포함**하면 병렬로 실행된다.

```
// 하나의 응답에서 세 개의 Agent를 동시에 호출
Agent({
  description: "인증 모듈 분석",
  subagent_type: "Explore",
  prompt: "src/auth/ 디렉토리의 구조와 인증 방식을 분석해줘."
})

Agent({
  description: "결제 모듈 분석",
  subagent_type: "Explore",
  prompt: "src/payment/ 디렉토리의 구조와 PG사 연동 방식을 분석해줘."
})

Agent({
  description: "알림 모듈 분석",
  subagent_type: "Explore",
  prompt: "src/notification/ 디렉토리의 구조와 알림 발송 채널을 분석해줘."
})
```

병렬 실행의 조건: 각 에이전트의 작업이 서로 의존하지 않아야 한다. A 에이전트의 결과가 B 에이전트의 입력이 되는 구조라면 순차 실행해야 한다.

### 6.1 병렬 + 순차 조합

실무에서는 "먼저 탐색을 병렬로 돌리고, 결과를 모아서 다음 단계를 진행"하는 패턴을 자주 쓴다.

```
// 1단계: 병렬 탐색 (하나의 메시지에서 동시 호출)
Agent({ description: "프론트 코드 조사", ... })
Agent({ description: "백엔드 코드 조사", ... })
Agent({ description: "DB 스키마 조사", ... })

// 2단계: 세 에이전트의 결과를 종합해서 구현 에이전트에 전달
Agent({
  description: "기능 구현",
  prompt: "아래 조사 결과를 바탕으로 사용자 프로필 수정 기능을 구현해줘.
    프론트 조사: {결과1}
    백엔드 조사: {결과2}
    DB 스키마: {결과3}"
})
```

---

## 7. 직접 도구 호출 vs 서브 에이전트 위임

모든 작업에 서브 에이전트를 쓸 필요는 없다. 오히려 간단한 작업에 서브 에이전트를 띄우면 오버헤드만 생긴다.

### 직접 도구를 호출하는 게 나은 경우

- 파일 하나를 읽거나 수정할 때
- 특정 키워드로 Grep 한두 번 돌릴 때
- 이미 경로를 알고 있는 파일에 접근할 때
- 결과를 즉시 다음 판단에 써야 할 때

### 서브 에이전트에 위임하는 게 나은 경우

- 탐색 범위가 넓어서 Grep/Glob을 여러 번 조합해야 할 때
- 검색 결과가 클 것으로 예상되어 메인 컨텍스트를 보호하고 싶을 때
- 독립적인 작업을 병렬로 처리하고 싶을 때
- 코드 수정 후 테스트까지 자율적으로 수행하게 하고 싶을 때
- worktree 격리가 필요한 실험적 작업일 때

판단 기준을 하나로 요약하면: **메인 에이전트가 직접 하면 컨텍스트가 지저분해지거나 시간이 오래 걸리는 작업**을 위임한다.

---

## 8. 흔한 실수와 대응

### 8.1 컨텍스트 누락

가장 빈번한 실수다. 메인 대화에서 이미 알고 있는 정보를 프롬프트에 안 넣는다.

```
// 이렇게 하면 서브 에이전트가 처음부터 다시 조사한다
Agent({
  prompt: "이 버그를 수정해줘"
})

// 이미 파악한 정보를 전부 넘겨야 한다
Agent({
  prompt: "src/auth/session.ts:72에서 isExpired() 체크 후 
    세션 갱신 로직이 빠져 있어서 만료된 세션이 유지되는 버그가 있다. 
    isExpired()가 true일 때 renewSession()을 호출하도록 수정해줘."
})
```

### 8.2 이해를 위임하기

서브 에이전트에게 "조사 결과를 바탕으로 수정해줘"라고 하면서 정작 조사 결과를 분석하지 않고 그대로 넘기는 경우다.

```
// 나쁜 패턴: 이해를 위임
const result = await Agent({ prompt: "문제를 조사해줘" })
Agent({ prompt: `조사 결과를 바탕으로 수정해줘: ${result}` })

// 좋은 패턴: 메인 에이전트가 이해하고, 구체적 지시를 내린다
const result = await Agent({ prompt: "문제를 조사해줘" })
// 메인 에이전트가 결과를 분석한 후:
Agent({
  prompt: "src/auth/session.ts:72에 renewSession() 호출을 추가해줘. 
    조건은 isExpired()가 true일 때."
})
```

### 8.3 짧은 프롬프트

"간결함"과 "부족함"은 다르다. 3줄짜리 프롬프트로 서브 에이전트를 보내면 에이전트가 자기 판단으로 채워야 할 빈칸이 너무 많다. 그 판단이 항상 맞지는 않는다.

### 8.4 결과 맹신

서브 에이전트가 "수정 완료"라고 보고했다고 끝이 아니다. 보고는 서브 에이전트가 **의도한 바**를 설명하는 거지, 실제로 그렇게 됐다는 보장이 아니다. 코드를 수정하는 서브 에이전트의 결과는 반드시 실제 파일 변경을 확인해야 한다.

### 8.5 불필요한 에이전트 남용

파일 하나 읽는 데 서브 에이전트를 쓰거나, 간단한 Grep 하나에 Explore 에이전트를 띄우는 경우다. 서브 에이전트를 생성하고 결과를 주고받는 데 오버헤드가 있다. 직접 할 수 있는 건 직접 한다.

---

## 9. 실전 활용 예시

### 9.1 대규모 리팩토링 전 영향도 분석

특정 인터페이스를 변경하기 전에 사용처를 전수 조사하는 상황이다.

```
Agent({
  description: "UserService 사용처 전수 조사",
  subagent_type: "Explore",
  prompt: "UserService 인터페이스의 모든 사용처를 찾아줘. 
    import하는 파일, 의존성 주입으로 받는 파일, 테스트에서 mock하는 파일 
    전부 정리해줘. 파일 경로와 사용 방식(직접 호출, DI, mock)을 구분해서 알려줘.
    thoroughness: very thorough"
})
```

### 9.2 두 가지 접근 방식 비교

worktree 격리를 써서 두 가지 구현을 동시에 시도한다.

```
// 두 에이전트를 병렬로, 각각 격리된 worktree에서 실행
Agent({
  description: "전략 A: 캐시 적용",
  isolation: "worktree",
  prompt: "src/product/product.service.ts의 getProductList 메서드에 
    Redis 캐시를 적용해줘. TTL 5분, 캐시 키는 쿼리 파라미터 기반으로. 
    테스트도 수정해줘."
})

Agent({
  description: "전략 B: 쿼리 최적화",
  isolation: "worktree",
  prompt: "src/product/product.service.ts의 getProductList 메서드의 
    DB 쿼리를 최적화해줘. N+1 문제가 있으면 join으로 바꾸고, 
    불필요한 컬럼 조회를 제거해줘. 테스트도 수정해줘."
})
```

두 에이전트가 각각 다른 worktree에서 작업하므로 충돌이 없다. 결과를 비교한 후 나은 쪽을 선택하면 된다.

### 9.3 멀티 모듈 동시 조사

모노레포에서 여러 모듈을 동시에 탐색하는 경우다.

```
Agent({
  description: "auth 모듈 조사",
  subagent_type: "Explore",
  prompt: "packages/auth/에서 JWT 토큰 생성과 검증 로직을 찾아줘. 
    어떤 라이브러리를 쓰는지, 토큰 만료 시간은 어떻게 설정되는지 정리해줘.",
  run_in_background: true
})

Agent({
  description: "gateway 모듈 조사",
  subagent_type: "Explore",
  prompt: "packages/gateway/에서 인증 미들웨어가 JWT를 어떻게 검증하는지 찾아줘. 
    토큰 갱신 로직이 있는지, 만료 처리는 어떻게 하는지 정리해줘.",
  run_in_background: true
})
```

백그라운드로 돌려놓고, 그 사이에 관련 문서를 읽거나 다른 준비 작업을 하면 된다.

---

## 참고

- [Claude Code 기본 문서](Claude_Code.md)
- [오케스트레이션 (Agent SDK/외부 자동화)](Claude_Code_Orchestration.md)
- [Worktree 격리](Claude_Code_Worktree.md)
- [Claude Code 공식 문서](https://docs.anthropic.com/en/docs/claude-code)
