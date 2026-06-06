---
title: Claude Code Auto Mode 실전 활용
tags: [ai, claude-code, auto-mode, workflow, permissions]
updated: 2026-06-06
---

# Claude Code Auto Mode 실전 활용

Claude Code를 한참 쓰다 보면 같은 패턴이 반복된다. "X를 Y로 바꿔달라"고 하면 Claude가 "어떤 방식으로 바꾸길 원하세요? A, B, C 중 선택해주세요"라고 되묻고, 답하고 나면 또 "어떤 파일부터 작업할까요?"라고 물어본다. 명확한 작업인데도 클릭 3~4번을 더 해야 끝난다. Auto Mode(자동 모드)는 이런 마찰을 줄이려고 만든 모드다. 모델이 합리적인 기본값으로 판단해서 일단 진행하고, 사용자는 결과를 보고 redirect 한다.

문제는 이 동작 방식이 잘 맞는 작업과 안 맞는 작업이 분명히 갈린다는 점이다. 잘못 쓰면 의도하지 않은 파일이 수정되거나, 잘못된 가정으로 작업이 진행돼서 롤백 비용이 커진다. 이 문서는 Auto Mode의 실제 동작 원리와 어떤 작업에 켜고 어떤 작업에 꺼야 하는지 정리한다.

---

## 1. Auto Mode가 무엇인가

Auto Mode는 모델의 "확인-진행 비율"을 조정하는 모드다. 일반 모드에서 모델은 모호한 지시를 만나면 `AskUserQuestion`으로 사용자에게 되묻거나, 두 갈래 길에서 어느 쪽으로 갈지 확인받는다. Auto Mode가 켜지면 그 확인 단계 대부분을 건너뛰고 모델이 직접 합리적 판단을 내린 뒤 그대로 실행한다.

내부적으로는 시스템 프롬프트에 다음과 같은 지시가 주입된다.

```
## Auto Mode Active

Bias toward working without stopping for clarifying questions —
when you'd normally pause to check, make the reasonable call and keep going;
they'll redirect you if needed.
```

핵심은 "redirect 한다"는 가정이다. 모델이 잘못된 방향으로 가도 사용자가 중간에 끊고 다시 잡아줄 거라는 전제 위에 동작한다. 그래서 Auto Mode는 사용자가 작업을 실시간으로 모니터링한다는 가정 하에 켜는 게 안전하다. 켜놓고 자리를 비우면 망친다.

### 1.1 일반 모드와의 차이

일반 모드에서 모델은 다음과 같은 상황에서 멈춘다.

- 두 개 이상의 합리적 선택지가 있을 때 (예: "TypeScript 타입을 어떻게 정의할까요?")
- 사용자 의도가 명확하지 않을 때 (예: "전부 라는 게 어디까지인가요?")
- 외부 입력이 필요할 때 (예: "DB 비밀번호를 알려주세요")

Auto Mode가 켜지면 처음 두 경우는 모델이 직접 결정하고 진행한다. 세 번째 같은 진짜 블로커는 여전히 멈춘다. "지시가 모호한가" 와 "정보가 부재한가"는 다른 문제고, Auto Mode가 해결하는 건 전자다.

### 1.2 Plan Mode와의 차이

Plan Mode는 "쓰기 전에 계획을 보여달라"는 모드고, Auto Mode는 "물어보지 말고 진행해라"는 모드다. 방향이 정반대인 것 같지만 둘 다 동시에 켤 수 있고 오히려 궁합이 좋다. Plan Mode가 켜진 상태에서 Auto Mode를 같이 켜면, 모델은 계획을 짤 때 사용자에게 세부사항을 묻지 않고 합리적으로 결정해서 한 번에 완성도 높은 플랜을 제시한다. 그 플랜을 사용자가 ExitPlanMode 단계에서 검토해서 승인하거나 수정 요청을 보낸다.

---

## 2. 활성화 방법

### 2.1 슬래시 명령어

가장 흔한 방법은 `/auto` 토글이다. 입력창에서 `/auto`를 치면 현재 세션의 Auto Mode가 켜지거나 꺼진다. 상태는 입력창 하단 모드 표시 영역에서 확인할 수 있다.

```
/auto
→ Auto mode enabled
```

다시 한 번 치면 꺼진다.

### 2.2 settings.json에 영구 설정

특정 프로젝트에서 항상 Auto Mode로 시작하고 싶으면 settings.json에 박아둔다.

```json
{
  "autoMode": true,
  "permissions": {
    "allow": [
      "Bash(npm test:*)",
      "Bash(npm run lint:*)"
    ],
    "deny": [
      "Bash(git push:*)",
      "Bash(rm -rf:*)"
    ]
  }
}
```

`~/.claude/settings.json`에 두면 전역, 프로젝트 루트의 `.claude/settings.json`에 두면 해당 프로젝트에서만 적용된다. 보통은 프로젝트 단위로 잡는 게 안전하다. 테스트 추가나 리팩토링을 자주 하는 안정된 프로젝트에서는 켜놓고, 새로 만지는 코드베이스에서는 꺼두는 식이다.

### 2.3 세션 중간 전환

작업 도중에도 `/auto`로 자유롭게 켜고 끌 수 있다. 보통 다음과 같은 흐름이 나온다.

```
사용자: 이 모듈 구조 파악해줘
       (Auto Mode 꺼진 상태, 모델이 차근차근 질문하며 탐색)
사용자: 좋아. 이제 이 패턴으로 나머지 12개 파일도 똑같이 바꿔
사용자: /auto
사용자: 시작해
       (Auto Mode 켜진 상태, 모델이 멈추지 않고 12개를 순차 처리)
```

탐색 단계는 일반 모드로 천천히, 반복 적용 단계는 Auto Mode로 빠르게 가는 패턴이다.

---

## 3. Auto Mode가 잘 맞는 상황

Auto Mode의 장점이 살아나는 작업은 공통점이 있다. 결과를 검증하기 쉽고, 잘못돼도 롤백이 싸고, 의사결정 폭이 좁은 작업이다.

### 3.1 반복 작업

같은 패턴을 N개 파일에 적용하는 작업. 한 번 정답을 확인한 다음, 나머지를 자동으로 돌리면 된다.

```
"src/api 하위 컨트롤러 17개에 동일한 try/catch 래퍼를 적용해라.
형식은 src/api/user.controller.ts 와 똑같이"
```

이런 지시는 Auto Mode와 궁합이 좋다. 첫 파일에서 사용자가 결과를 확인했으니 나머지는 같은 패턴으로 진행해도 안전하다.

### 3.2 명확한 스펙의 구현

타입 정의, 인터페이스, 테스트 케이스가 이미 확정된 상태에서 구현체만 채우는 작업.

```typescript
// 이미 작성된 인터페이스
interface PaymentProcessor {
  charge(amount: number, currency: string): Promise<Receipt>;
  refund(receiptId: string): Promise<void>;
}

// "StripeProcessor 클래스로 위 인터페이스를 구현해라" → Auto Mode 적합
```

인터페이스가 결정의 폭을 좁혀주니까 모델이 잘못 판단할 여지가 적다.

### 3.3 리팩토링

추출, 이름 변경, 위치 이동 같은 의미 보존 리팩토링. 동작이 바뀌지 않아야 하니까 테스트가 깨지면 즉시 실패가 감지된다.

```
"UserService의 sendNotification 메서드를 NotificationService로 추출해라.
호출부도 전부 업데이트해라"
```

### 3.4 테스트 추가

기존 코드에 테스트를 붙이는 작업. 프로덕션 코드를 건드리지 않으니 위험도가 낮다.

```
"src/utils/date.ts 의 모든 export 함수에 대해 단위 테스트를 추가해라.
파일 위치는 __tests__ 하위에 같은 이름으로"
```

### 3.5 일괄 변환

import 경로 변경, deprecated API 마이그레이션, lint 룰 일괄 적용 같은 기계적 변환.

```
"전체 코드베이스에서 moment 를 dayjs 로 교체해라.
.format() 호출은 그대로 두되, moment(x) 는 dayjs(x) 로"
```

---

## 4. Auto Mode가 위험한 상황

여기서부터가 더 중요하다. Auto Mode를 켜둔 채로 다음 작업을 시키면 후회한다.

### 4.1 파괴적 작업

`rm`, `DROP TABLE`, `git branch -D`, `git reset --hard` 같은 명령은 되돌릴 수 없다. Auto Mode가 켜져 있어도 모델은 보통 이런 명령 전에 한 번 확인을 요청하긴 하지만, "redirect" 가정에 의존하는 모드라 100% 보장되지 않는다. 파괴적 작업이 예상되는 세션은 Auto Mode를 끄고 들어가는 게 안전하다.

### 4.2 외부 API 호출

이메일 발송, Slack 메시지, GitHub PR 코멘트, 결제 API 같은 외부 효과가 발생하는 작업. 한 번 나가면 회수가 안 된다. 특히 사내 시스템 API를 자동화 스크립트로 호출하는 코드를 짜다가 테스트 도중 실제 호출이 나가면 사고로 이어진다.

`settings.json`의 deny 리스트로 가드를 걸어둘 수 있다.

```json
{
  "autoMode": true,
  "permissions": {
    "deny": [
      "Bash(curl * https://api.slack.com/*)",
      "Bash(gh pr comment:*)",
      "Bash(gh issue create:*)"
    ]
  }
}
```

### 4.3 git push, force push

push는 원격 저장소를 변경하는 행위라 로컬 작업과 격이 다르다. force push는 더 위험하다. Auto Mode가 켜진 상태에서 "변경사항 푸시해라"고 하면 모델이 그대로 실행한다.

```json
{
  "permissions": {
    "deny": [
      "Bash(git push:*)",
      "Bash(git push --force:*)",
      "Bash(git push -f:*)"
    ]
  }
}
```

push는 항상 명시적으로 사용자가 직접 하는 게 좋다.

### 4.4 DB 마이그레이션

마이그레이션 스크립트 작성까지는 Auto Mode가 괜찮지만, 실제 실행은 별개다. `npm run migrate`나 `prisma migrate deploy` 같은 명령은 deny 리스트에 넣어두는 게 안전하다. 개발 DB는 괜찮아도 실수로 환경 변수가 production을 가리키고 있으면 그대로 운영 DB가 날아간다.

### 4.5 공유 리소스 변경

CI/CD 설정, GitHub Actions 워크플로, Docker 이미지 태그, 인프라 설정 파일. 한 번 머지되면 팀 전체에 영향이 가는 파일들이다. Auto Mode로 진행하기보다 일반 모드에서 Plan Mode를 같이 켜고 차근차근 확인받는 게 맞다.

---

## 5. Auto Mode와 Plan Mode 조합

가장 실전적인 조합이다. "계획은 확인받고 실행은 자동으로"라는 패턴이다.

작업 흐름은 이렇다.

```
1. /plan 으로 Plan Mode 진입
2. /auto 로 Auto Mode 활성화
3. 사용자가 작업 요청
4. 모델이 사용자에게 세부사항을 묻지 않고 합리적 결정으로 플랜 완성
5. ExitPlanMode 시점에 사용자가 플랜 검토
6. 승인하면 일반 모드로 전환, 그대로 자동 실행
7. 실행 중에도 Auto Mode 유지되어 모델이 끊지 않고 진행
```

이 조합의 장점은 "사용자가 한 번만 깊이 검토하면 된다"는 점이다. 플랜이라는 단일 산출물에 의사결정이 모여 있으니까 그것만 잘 보면 된다. 일반 모드에서는 작업 중간중간 확인 요청이 흩어져서 사용자가 매번 작은 결정을 내려야 한다.

작업 예시.

```
사용자: /plan
사용자: /auto
사용자: 인증 미들웨어를 JWT 기반으로 교체해라.
       기존 세션 쿠키 방식은 deprecated 처리만 하고 지우진 마라.
       테스트도 같이 업데이트해라.

(모델이 합리적 결정으로 플랜 작성)

모델: 다음 플랜을 제시합니다.
      1. src/middleware/auth.ts 에 verifyJWT 함수 추가
      2. src/middleware/session.ts 의 verifySession 에 @deprecated 주석
      3. src/routes/* 의 authMiddleware 호출부를 verifyJWT 로 변경
      4. __tests__/auth.test.ts 에 JWT 검증 케이스 추가
      ...

사용자: 좋아. 진행해.

(여기서부터 일반 모드 + Auto Mode 로 자동 진행)
```

---

## 6. Auto Mode와 Worktree 조합

Worktree는 격리된 git working directory에서 작업하는 기능이다. Auto Mode와 함께 쓰면 "잘못돼도 메인 working directory는 안 더럽혀진다"는 안전망이 생긴다.

worktree 안에서 Auto Mode를 켜두면, 모델이 좀 더 공격적으로 작업을 진행해도 부담이 적다. 마음에 안 들면 worktree 통째로 버리면 그만이다.

```
사용자: /worktree experiment-rate-limiter
사용자: /auto
사용자: rate limiter를 Redis 기반으로 새로 짜봐라.
       기존 in-memory 구현은 그대로 두고, 새 구현체만 추가해라.

(worktree 안에서 자동 실행. 메인 브랜치 영향 없음)

검토 후 마음에 들면 머지, 아니면 worktree 삭제
```

특히 "어떤 구조가 좋을지 모르겠으니 일단 짜본다" 류의 탐색적 작업에서 강력하다. 결과물이 마음에 안 들어도 손실이 없으니 Auto Mode의 적극적인 진행 성향이 단점이 되지 않는다.

---

## 7. 권한 설정과의 관계

Auto Mode와 permissions(allow/deny)는 서로 보완적이다. Auto Mode는 "묻지 말고 진행해라"고 시키고, permissions는 "이 명령은 절대 실행하지 마라"를 강제한다. 둘 다 켜놓으면 "deny 리스트에 안 걸리는 한 자동 진행"이 된다.

실전에서는 deny 리스트를 단단히 짜놓고 Auto Mode를 켜는 패턴이 안정적이다.

```json
{
  "autoMode": true,
  "permissions": {
    "allow": [
      "Bash(npm:*)",
      "Bash(yarn:*)",
      "Bash(pnpm:*)",
      "Bash(git status)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)"
    ],
    "deny": [
      "Bash(git push:*)",
      "Bash(git reset --hard:*)",
      "Bash(rm -rf:*)",
      "Bash(npm publish:*)",
      "Bash(docker push:*)",
      "Bash(kubectl apply:*)",
      "Bash(terraform apply:*)"
    ]
  }
}
```

allow에 명시된 명령은 권한 프롬프트 없이 즉시 실행되고, deny에 명시된 명령은 Auto Mode가 켜져 있어도 차단된다. allow에도 deny에도 없는 명령은 일반 권한 프롬프트가 뜬다.

deny 리스트가 비어 있으면 Auto Mode가 위험하다. 모델이 "redirect 받을 거다"라는 가정에 의존하는데, 사용자가 화면을 안 보고 있으면 redirect할 사람이 없다.

---

## 8. 실무 트러블슈팅

### 8.1 의도치 않은 파일이 수정됐을 때

Auto Mode 켜놓고 자리를 비웠더니 엉뚱한 파일이 건드려진 경우. 우선 `git status`와 `git diff`로 수정 범위를 파악한다.

```bash
git status
git diff --stat
```

원본으로 돌리고 싶은 파일은 `git checkout`으로 되돌린다.

```bash
git checkout -- src/unintended-file.ts
```

이런 사고를 줄이려면 작업 시작 전에 `git add -A && git stash` 로 깔끔한 상태에서 시작하는 습관을 들인다. 작업이 끝나고 마음에 들면 stash를 버리고, 망치면 stash로 돌아간다.

### 8.2 잘못된 가정으로 진행됐을 때

모델이 "프로젝트가 TypeScript니까 JSX는 TSX로"라는 가정으로 진행했는데, 사실 해당 디렉토리만 JS인 경우. Auto Mode의 가장 흔한 사고 유형이다.

이럴 땐 일단 Ctrl+C로 중단하고, 모델에게 가정을 명시적으로 정정한다.

```
사용자: 잠깐. src/legacy 하위는 .js 그대로 둬라. .ts로 바꾸지 마라.
       지금까지 바꾼 src/legacy 하위 파일들 전부 원래대로 되돌려라.
```

`git status`로 어느 파일이 수정됐는지 확인한 다음, 정정 지시와 함께 일반 모드로 전환(`/auto`로 끄기)해서 차근차근 정리하는 게 안전하다.

### 8.3 중간 redirect 방법

작업이 30% 정도 진행됐는데 방향이 약간 어긋난 게 보인다. 다 멈추고 처음부터 다시 시키긴 아깝고, 그대로 두자니 결과가 마음에 안 들 것 같다.

이럴 땐 ESC나 Ctrl+C로 일단 멈춘 다음, 추가 지시를 보낸다.

```
사용자: 잠깐. 지금까지 만든 BaseService 추상 클래스는 좋은데,
       메서드 이름을 fetch가 아니라 load 로 통일해라.
       이미 만든 파일들도 같이 수정.
사용자: 계속.
```

Auto Mode가 켜져 있으면 모델이 이 지시를 받아 묻지 않고 그대로 반영한다.

### 8.4 같은 사고가 반복되면

특정 패턴의 사고가 반복된다면 그건 Auto Mode 문제가 아니라 컨텍스트 부족 문제다. `CLAUDE.md`에 프로젝트 규칙을 추가한다.

```markdown
# CLAUDE.md

## 절대 수정하지 말 것
- src/legacy/** : 호환성 유지를 위해 보존. .js 그대로
- src/generated/** : 빌드 산출물. 직접 수정 금지
- migrations/**/*.sql : 이미 운영에 적용된 마이그레이션
```

Auto Mode는 컨텍스트를 신뢰해서 빠르게 진행하는 모드라 컨텍스트가 부정확하면 그만큼 빠르게 망친다.

---

## 9. 언제 Auto Mode를 꺼야 하는가

다음 상황에서는 Auto Mode를 끄고 일반 모드로 작업하는 게 맞다.

새 코드베이스를 처음 탐색할 때. 모델이 프로젝트 구조를 모르는 상태라 잘못된 가정으로 진행할 가능성이 높다. 일반 모드에서 차근차근 질문하면서 구조를 파악하게 하는 게 안전하다.

아키텍처 결정이 필요할 때. "이 기능을 어떤 패턴으로 구현할까"는 두세 가지 합리적 선택지가 있고, 어느 쪽을 고르냐에 따라 후속 작업이 달라진다. 이런 결정은 사용자가 직접 내려야 한다. Auto Mode가 켜져 있으면 모델이 임의로 한 가지를 골라 진행해버려서 나중에 갈아엎는 비용이 커진다.

보안 관련 변경. 인증, 권한, 암호화, 비밀 관리 코드는 작은 실수가 큰 사고로 이어진다. 모델이 "이 정도면 되겠지"로 합리적 판단을 내리는 영역이 아니다. 일반 모드에서 모델이 의문을 제기하면 정확히 답하고, 결과를 한 줄씩 검토한다.

production 환경 변수가 로드된 세션. `NODE_ENV=production`, `DATABASE_URL=prod...` 같은 환경 변수가 로드된 셸에서 Claude Code를 띄웠다면 무조건 Auto Mode를 끈다. 실수로 운영 DB에 마이그레이션이 적용되거나 실제 결제 API가 호출되면 손이 떨린다.

처음 보는 외부 라이브러리를 도입할 때. 모델이 라이브러리 사용법을 잘못 알고 있을 수 있다. 한 번 동작하는 걸 확인한 다음, 그 패턴을 반복 적용할 때 Auto Mode를 켜는 순서가 맞다.

---

## 10. 정리

Auto Mode는 "모델이 redirect 받을 거다"라는 전제로 동작한다. 그 전제가 깨지는 상황(사용자가 화면을 안 본다, 파괴적 명령이 끼어 있다, 컨텍스트가 부족하다)에서는 위험하다. 반대로 그 전제가 성립하는 상황(반복 작업, 명확한 스펙 구현, 격리된 worktree)에서는 일반 모드보다 훨씬 빠르고 마찰이 적다.

가장 안전한 운영 방식은 settings.json에 deny 리스트를 단단히 짜두고, 프로젝트별로 Auto Mode 기본값을 켜고 끄는 것이다. Plan Mode와 함께 쓰면 의사결정이 한 군데로 모여서 검토 비용이 줄어든다. Worktree와 함께 쓰면 사고가 나도 손실이 격리된다.

처음 도입할 때는 작은 작업부터 켜본다. 테스트 추가나 import 정리 같은 저위험 작업에서 감을 잡은 다음, 점점 적용 범위를 늘리는 게 안전하다.
