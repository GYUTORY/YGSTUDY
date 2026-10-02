---
title: Claude Code Auto Mode 실전 활용
tags: [ai]
updated: 2026-09-24
volatility: high
---

# Claude Code Auto Mode 실전 활용

Claude Code를 한참 쓰다 보면 같은 패턴이 반복된다. "X를 Y로 바꿔달라"고 하면 Claude가 "어떤 방식으로 바꾸길 원하세요? A, B, C 중 선택해주세요"라고 되묻고, 답하고 나면 또 "어떤 파일부터 작업할까요?"라고 물어본다. 명확한 작업인데도 클릭 3~4번을 더 해야 끝난다. Auto Mode는 이런 마찰을 줄이려고 만든 모드다. 모델이 합리적인 기본값으로 판단해서 일단 진행하고, 사용자는 결과를 보고 redirect한다.

문제는 이 동작 방식이 잘 맞는 작업과 안 맞는 작업이 분명히 갈린다는 점이다. 잘못 쓰면 의도하지 않은 파일이 수정되거나, 잘못된 가정으로 작업이 진행돼서 롤백 비용이 커진다.

---

## Auto Mode가 하는 일

Auto Mode는 모델의 "확인-진행 비율"을 조정하는 모드다. 일반 모드에서 모델은 모호한 지시를 만나면 `AskUserQuestion`으로 사용자에게 되묻거나, 두 갈래 길에서 어느 쪽으로 갈지 확인받는다. Auto Mode가 켜지면 그 확인 단계 대부분을 건너뛰고 모델이 직접 합리적 판단을 내린 뒤 그대로 실행한다.

내부적으로는 시스템 프롬프트에 다음 지시가 주입된다.

```
## Auto Mode Active

Bias toward working without stopping for clarifying questions —
when you'd normally pause to check, make the reasonable call and keep going;
they'll redirect you if needed.
```

핵심은 "redirect 한다"는 가정이다. 모델이 잘못된 방향으로 가도 사용자가 중간에 끊고 다시 잡아줄 거라는 전제 위에 동작한다. 사용자가 화면을 안 보고 있으면 그 전제가 깨진다.

일반 모드에서 모델이 멈추는 상황은 세 가지다. 두 개 이상의 합리적 선택지가 있을 때, 사용자 의도가 명확하지 않을 때, 외부 입력이 필요할 때다. Auto Mode가 켜지면 처음 두 경우는 모델이 직접 결정하고 진행한다. 세 번째 같은 진짜 블로커는 여전히 멈춘다. "지시가 모호한가"와 "정보가 부재한가"는 다른 문제고, Auto Mode가 해결하는 건 전자다.

Plan Mode와의 차이도 있다. Plan Mode는 "쓰기 전에 계획을 보여달라"는 모드고, Auto Mode는 "물어보지 말고 진행해라"는 모드다. 방향이 정반대인 것 같지만 둘 다 동시에 켤 수 있다. Plan Mode가 켜진 상태에서 Auto Mode를 같이 켜면, 모델은 계획을 짤 때 세부사항을 묻지 않고 합리적으로 결정해서 완성도 높은 플랜을 한 번에 제시한다.

---

## 진입 조건과 활성화 방법

Auto Mode는 세 가지 방법으로 켜진다.

**슬래시 명령어**

```
/auto
→ Auto mode enabled
```

세션 내에서 토글로 작동한다. 다시 치면 꺼진다. 세션이 끝나면 상태가 초기화된다.

**settings.json 영구 설정**

```json
{
  "autoMode": true
}
```

`~/.claude/settings.json`에 두면 전역, 프로젝트 루트의 `.claude/settings.json`에 두면 해당 프로젝트에서만 적용된다. 프로젝트 단위로 잡는 게 안전하다. 테스트 추가나 리팩토링을 자주 하는 안정된 프로젝트에서는 켜놓고, 처음 만지는 코드베이스에서는 꺼두는 식이다.

**세션 중간 전환 패턴**

```
사용자: 이 모듈 구조 파악해줘
       (Auto Mode 꺼진 상태, 모델이 차근차근 질문하며 탐색)
사용자: 좋아. 이제 이 패턴으로 나머지 12개 파일도 똑같이 바꿔
사용자: /auto
사용자: 시작해
       (Auto Mode 켜진 상태, 모델이 멈추지 않고 12개를 순차 처리)
```

탐색 단계는 일반 모드로 천천히, 반복 적용 단계는 Auto Mode로 빠르게 가는 패턴이다.

**진입 전 확인 사항**

Auto Mode를 켜기 전에 세 가지를 확인한다. 현재 셸에 `NODE_ENV=production` 같은 운영 환경 변수가 로드돼 있지 않은가. `git status`가 깨끗한가 — 작업 전 스냅샷이 없으면 롤백이 어렵다. deny 리스트가 설정돼 있는가. 이 세 가지 중 하나라도 빠지면 Auto Mode 진입을 미룬다.

---

## 도구별 자동 승인 범위

Auto Mode를 켜도 모든 도구가 자동 승인되는 건 아니다. Claude Code의 도구는 실행 전에 사용자 승인을 받는 것과 받지 않는 것으로 나뉜다. Auto Mode는 모델의 질문 행동을 바꾸는 설정이지, 도구 실행 권한을 바꾸는 설정이 아니다.

### 항상 즉시 실행 (승인 불필요)

파일 읽기 계열 도구는 Auto Mode와 관계없이 항상 즉시 실행된다.

| 도구 | 설명 |
|---|---|
| `Read` | 파일 읽기 |
| `Glob` | 파일 경로 검색 |
| `Grep` | 내용 검색 |
| `WebFetch` | 웹 페이지 읽기 |
| `WebSearch` | 웹 검색 |
| `TodoWrite` | 할 일 목록 관리 |

이 도구들은 상태를 변경하지 않으니 승인 프롬프트가 없다.

### 파일 편집 도구

`Edit`, `Write`, `NotebookEdit` 같은 파일 편집 도구는 기본적으로 승인 없이 실행된다. Auto Mode가 켜지면 모델이 파일을 대량으로 수정해도 중간에 멈추지 않는다는 뜻이다. 편집 범위를 의도치 않게 벗어나는 사고가 주로 여기서 난다.

파일 편집 도구는 deny 리스트로 제한하기 어렵다. 대신 CLAUDE.md로 컨텍스트를 주는 방법이 더 현실적이다.

```markdown
## 절대 수정하지 말 것
- src/legacy/** : 호환성 유지를 위해 보존
- src/generated/** : 빌드 산출물. 직접 수정 금지
```

### settings.json allow/deny에 따라 결정

Bash 명령 계열은 기본적으로 승인 프롬프트가 뜬다. allow 리스트에 명시된 패턴만 프롬프트 없이 실행된다.

```json
{
  "permissions": {
    "allow": [
      "Bash(npm:*)",
      "Bash(git status)",
      "Bash(git diff:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)"
    ],
    "deny": [
      "Bash(git push:*)",
      "Bash(rm -rf:*)",
      "Bash(kubectl apply:*)"
    ]
  }
}
```

Auto Mode가 켜지면 모델이 멈추지 않고 연속 호출하려 한다. allow 리스트에 있는 명령은 프롬프트 없이 바로 실행되고, deny에 있는 명령은 차단되고, 둘 다 없는 명령은 여전히 승인 프롬프트가 뜬다. Auto Mode에서 매번 승인 프롬프트가 뜬다면 allow 리스트가 부족한 것이다.

---

## trust level 단계별 동작

Claude Code는 실행 환경에 따라 세 가지 권한 수준으로 동작한다. Auto Mode가 켜진 상태에서 각 수준의 동작이 다르다.

### 기본 모드 (대화형)

터미널에서 `claude` 명령으로 실행하는 일반 모드다. Bash 명령에는 승인 프롬프트가 뜨고, 파일 편집은 프롬프트 없이 실행된다. allow/deny 리스트로 세부 조정이 가능하다.

Auto Mode가 켜지면 모델이 멈추지 않고 연속 호출하려 한다. Bash 명령마다 승인 프롬프트가 뜨면 실질적으로 자동화가 안 된다. 아래처럼 핵심 명령을 allow에 올려야 의도한 대로 동작한다.

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

이 설정에서 Auto Mode를 켜면 npm 명령, git 조회·스테이징·커밋은 프롬프트 없이 실행되고, push나 rm -rf는 deny로 막힌다. allow/deny 모두에 없는 명령은 여전히 프롬프트가 뜬다.

### 하위 에이전트 모드

`/agent` 명령이나 Agent SDK로 생성된 하위 에이전트는 부모 세션의 권한 설정을 상속한다. 부모가 Auto Mode이면 하위 에이전트도 Auto Mode로 동작한다.

하위 에이전트는 부모의 컨텍스트 밖에서 독립적으로 동작하기 때문에, 부모가 생각한 범위 밖의 결정을 내릴 수 있다. "이 디렉토리만 처리해"라는 지시가 에이전트에게 전달될 때 불명확하면, 에이전트가 합리적이라고 판단한 범위로 스스로 결정해서 진행한다. 이 결정이 부모의 의도와 다를 수 있다.

에이전트에게 넘길 지시는 일반 Auto Mode보다 더 명확해야 한다. 에이전트가 질문 없이 진행하기 때문에, 범위가 불명확하면 redirect할 기회가 없다.

### 위험 모드 (`--dangerously-skip-permissions`)

```bash
claude --dangerously-skip-permissions
```

이 플래그로 실행하면 모든 도구가 승인 없이 즉시 실행된다. deny 리스트도 무시된다. CI 환경이나 완전히 격리된 환경에서 자동화할 때 쓰는 옵션이다.

Auto Mode와 이 플래그를 같이 켜면 모델이 어떤 행동을 해도 중단이 없다. 운영 환경에서 절대 쓰면 안 된다. Docker 컨테이너나 VM처럼 호스트 시스템과 완전히 격리된 환경에서만 써야 한다.

```bash
# 격리된 컨테이너 안에서만 사용
docker run --rm -it \
  -v $(pwd):/workspace \
  my-claude-image \
  claude --dangerously-skip-permissions "테스트 전부 실행하고 리포트 만들어"
```

컨테이너 밖에서 이 플래그를 쓰면 모델이 시스템 전체를 건드릴 수 있다.

---

## side effect가 발생하는 구체적 시나리오

Auto Mode에서 실제로 문제가 생기는 패턴을 시나리오별로 정리한다.

### 시나리오 1: 운영 환경 변수가 로드된 셸

```bash
# .env.production을 실수로 source한 셸에서 Claude Code 실행
source .env.production
claude  # 여기서 Auto Mode 켜면 위험
```

이 상태에서 "DB 마이그레이션 스크립트 실행해봐"라고 하면 모델이 `npm run migrate`를 호출하고, 그게 `DATABASE_URL`을 읽어 운영 DB에 실행된다. 마이그레이션 스크립트 작성까지는 Auto Mode가 괜찮지만, 실행 명령은 deny 리스트에 박아두는 게 안전하다.

```json
{
  "permissions": {
    "deny": [
      "Bash(npm run migrate:*)",
      "Bash(prisma migrate:*)",
      "Bash(typeorm migration:run:*)"
    ]
  }
}
```

### 시나리오 2: 외부 API 호출이 섞인 코드 작업

Slack 알림 기능을 구현하면서 Auto Mode를 켰다. 모델이 테스트 코드를 짜고, 동작 확인을 위해 실제 Slack API를 호출하는 테스트를 실행했다. 테스트 채널에 메시지가 수십 개 쌓였다.

deny 리스트로 막기는 어렵다. 코드 안에서 API를 호출하는 거라 `Bash(curl:*)` 패턴으로 걸리지 않는다. 이런 작업은 CLAUDE.md에 테스트 환경 규칙을 명시하는 방법이 낫다.

```markdown
## 테스트 규칙
- 외부 API 호출이 포함된 테스트는 직접 실행 전 확인
- Slack, 이메일, 결제 API: 항상 mock을 써라
- 실제 API를 테스트해야 할 때는 별도 알림
```

### 시나리오 3: 공유 파일 수정 후 push

GitHub Actions 워크플로 파일을 수정하는 작업을 Auto Mode로 진행했다. 모델이 몇 가지 최적화를 판단해서 `.github/workflows/deploy.yml`에 적용하고 push까지 했다. 다른 팀 배포 파이프라인에 영향이 갔다.

push를 deny에 박아두면 로컬에서는 아무리 수정해도 원격에 나가지 않는다. 공유 파일은 사람이 직접 확인하는 단계를 두는 게 맞다.

```json
{
  "permissions": {
    "deny": [
      "Bash(git push:*)"
    ]
  }
}
```

### 시나리오 4: 범위 모호한 지시 + 대형 코드베이스

"전부 TypeScript로 바꿔줘"라는 지시를 Auto Mode에서 받으면 모델이 "전부"의 범위를 스스로 결정한다. 레거시 폴더, 테스트 설정 파일, 빌드 스크립트까지 건드리기 시작하면 롤백 범위가 커진다.

Auto Mode로 대형 작업을 시킬 때는 지시가 명확할수록 좋다.

```
나쁜 지시: "전부 TypeScript로 바꿔줘"

좋은 지시: "src/api 하위의 .js 파일만 .ts로 바꿔줘.
           src/legacy, src/generated 는 건드리지 마라.
           tsconfig.json은 내가 따로 할 테니 파일 변환만 해라"
```

### 시나리오 5: 임시 파일 커밋

모델이 Auto Mode에서 파일을 여러 개 수정하다가 테스트를 위해 임시 파일을 만들었다. 작업 마무리에 `git add -A && git commit`을 실행하면서 임시 파일까지 커밋됐다.

allow 리스트에 `git add -A`나 `git add .`를 넣기보다 경로를 명시하는 편이 낫다.

```json
{
  "permissions": {
    "allow": [
      "Bash(git add src/:*)",
      "Bash(git commit:*)"
    ]
  }
}
```

---

## 승인 임계값 조정 — 케이스 스터디

allow/deny 리스트를 처음 만들 때 적정 범위를 한 번에 잡기는 어렵다. 너무 좁히면 Auto Mode가 매번 승인 프롬프트를 띄워서 자동화 효과가 없어지고, 너무 넓히면 예상치 못한 명령이 실행된다. 설정을 조정하면서 실제로 발생한 케이스들이다.

### npm 와일드카드 allow가 publish를 열었다

npm 관련 명령을 자동화하려고 `"Bash(npm:*)"` 를 allow에 넣었다. `npm install`, `npm run build`, `npm test`가 프롬프트 없이 실행되길 기대했다.

모델이 의존성 충돌을 해결하다가 `npm publish --dry-run`으로 패키지 상태를 확인했다. dry-run이라 실제 배포는 아니었지만, allow 패턴이 `npm publish` 자체를 막지 않는다는 걸 그때 알았다. `--dry-run`이 빠진 채로 다음에 실행됐다면 실제 배포가 나갔을 것이다.

`npm:*` 를 쓰면 `npm publish`, `npm deprecate`, `npm unpublish`도 전부 포함된다. 필요한 서브 커맨드만 명시하는 방식으로 바꿨다.

```json
{
  "permissions": {
    "allow": [
      "Bash(npm install:*)",
      "Bash(npm run:*)",
      "Bash(npm test:*)",
      "Bash(npm ci:*)"
    ],
    "deny": [
      "Bash(npm publish:*)",
      "Bash(npm deprecate:*)"
    ]
  }
}
```

와일드카드 패턴을 쓸 때는 "이 커맨드의 서브 커맨드가 전부 열려도 괜찮은가"를 확인한다. `npm:*`, `git:*`, `docker:*`, `kubectl:*`, `terraform:*` 전부 같은 함정이 있다.

### git add -A allow로 .env.local이 커밋됐다

`"Bash(git add:*)"` 와 `"Bash(git commit:*)"` 를 allow에 넣었다. Auto Mode에서 모델이 작업을 마무리하면서 `git add -A && git commit -m "..."` 을 실행했다.

`.env.local` 파일이 `.gitignore`에 빠져 있었다. 그 파일에 로컬 DB 접속 정보가 들어 있었다. 커밋이 된 걸 `git log` 확인하다 발견했고 히스토리 정리에 시간이 꽤 걸렸다.

`git add -A` 는 deny에 박고, 경로를 명시하는 패턴만 allow에 올린다.

```json
{
  "permissions": {
    "allow": [
      "Bash(git add src/:*)",
      "Bash(git add tests/:*)",
      "Bash(git commit:*)"
    ],
    "deny": [
      "Bash(git add -A:*)",
      "Bash(git add .:*)",
      "Bash(git push:*)"
    ]
  }
}
```

### deny만 쓰고 allow를 비우면 자동화가 안 된다

처음에 deny 리스트만 정성껏 만들었다. `git push`, `rm -rf`, `kubectl apply` 같은 위험한 것들을 막았다.

Auto Mode를 켜고 테스트 추가 작업을 시켰더니 모델이 `npm test` 를 실행하려 할 때마다 승인 프롬프트가 떴다. deny에 없는 명령은 기본적으로 승인이 필요하다는 걸 놓쳤다. 결국 매번 엔터를 쳐야 했고, Auto Mode를 켠 의미가 없었다.

deny는 막는 것, allow는 여는 것이다. Auto Mode에서 실질적인 자동화가 되려면 자주 쓰는 명령을 allow에 명시해야 한다. 한쪽만 채워서는 안 된다.

### git push 허용 범위를 좁혀간 과정

처음엔 모든 git 명령을 열었다.

```json
"allow": ["Bash(git:*)"]
```

`git log`, `git diff`, `git status` 전부 프롬프트 없이 실행되니 편했다. 그런데 모델이 브랜치 확인 없이 `git push origin main`을 실행했다. feature 브랜치에서 작업 중이었는데 main으로 나가버렸다.

1차 조정 — push를 deny로 이동했다.

```json
"deny": ["Bash(git push:*)"]
```

push 자체가 막혔다. 그런데 며칠 후 브랜치 히스토리를 정리해야 할 상황이 생겼고, `git rebase`도 같이 막혀 있었다. deny 패턴이 `git:*`로 열었던 범위 전부를 역으로 커버하지 못한다는 걸 다시 실감했다.

2차 조정 — 읽기 전용과 로컬 변경만 allow, 원격에 영향 가는 건 전부 프롬프트로 남겼다.

```json
{
  "permissions": {
    "allow": [
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(git add src/:*)",
      "Bash(git commit:*)"
    ],
    "deny": [
      "Bash(git push:*)",
      "Bash(git reset --hard:*)",
      "Bash(git rebase:*)"
    ]
  }
}
```

읽기·스테이징·커밋은 allow, 원격에 영향 가거나 히스토리를 바꾸는 건 deny, 나머지는 프롬프트. 이 구조가 안정적이었다.

---

## 권한 범위별 실패 패턴

Auto Mode에서 사고가 나는 경로는 어떤 권한이 어떻게 열려 있는지에 따라 유형이 나뉜다.

### 파일 편집 — 지시 범위 밖의 파일이 수정된다

파일 편집 도구(`Edit`, `Write`)는 allow/deny 리스트 밖에 있다. 기본적으로 프롬프트 없이 실행된다. Auto Mode에서 가장 조용히 문제가 생기는 경로다.

모델이 "관련 있다"고 판단한 파일을 스스로 수정 범위에 포함시킨다. "src/api/user.ts 고쳐줘"라고 했는데 같은 폴더의 `auth.ts`와 `types.ts`까지 건드리고 나서 "의존성 정리까지 했다"고 리포트한다. 지시에 없던 파일이 수정됐고 `git diff`를 보기 전까지 몰랐다.

파일 편집 범위는 CLAUDE.md로 제어한다. deny 리스트로는 특정 파일 경로를 막을 수 없다.

```markdown
## 수정 범위
- 지시에 명시된 파일만 수정
- 의존성이 있다고 판단해도 지시에 없는 파일은 수정 전에 확인
- 아래 경로는 절대 수정 금지:
  - src/generated/
  - migrations/
  - .github/workflows/
```

이 규칙을 넣어도 완전히 막히지는 않는다. 중간에 redirect할 수 있는 환경에서만 파일 편집 위주 작업을 Auto Mode로 돌린다.

### Bash allow 와일드카드 — 서브 커맨드 전체가 열린다

상위 커맨드를 allow로 열면 서브 커맨드 전체가 따라온다.

| allow 패턴 | 의도치 않게 열리는 서브 커맨드 |
|---|---|
| `Bash(npm:*)` | `npm publish`, `npm unpublish`, `npm deprecate` |
| `Bash(git:*)` | `git push --force`, `git reset --hard`, `git clean -fd` |
| `Bash(docker:*)` | `docker rm`, `docker rmi`, `docker volume rm` |
| `Bash(kubectl:*)` | `kubectl delete`, `kubectl apply`, `kubectl exec` |
| `Bash(terraform:*)` | `terraform destroy`, `terraform apply` |

안전한 서브 커맨드를 명시하고 나머지는 deny나 프롬프트로 남겨두는 게 낫다.

### deny 패턴 — 우회 표현에 뚫린다

deny에 등록된 패턴은 그 문자열이 정확히 일치할 때만 차단된다.

```json
"deny": ["Bash(rm -rf:*)"]
```

`rm -rf /tmp/test`는 막히지만 `rm -r -f /tmp/test`, `find . -type f -delete`는 통과한다. 셸 one-liner로 같은 결과를 내는 표현은 무수히 많다.

deny는 "이 커맨드는 절대 안 된다"는 확실한 것에 쓴다. "이 외에는 전부 허용"이라는 의미로 deny를 allowlist처럼 쓰면 안 된다. 중요한 경계는 allow로 좁히는 쪽이 맞다.

### 하위 에이전트 — 세션 컨텍스트가 없다

`/agent`로 만든 하위 에이전트는 부모 세션에서 누적된 대화 컨텍스트를 받지 않는다. CLAUDE.md는 읽지만, 세션 중에 암묵적으로 확립된 제약들은 모른다.

부모가 Auto Mode이면 에이전트도 Auto Mode 상태로 동작하면서 자신이 합리적이라고 판단한 범위로 일을 처리한다. "아까 legacy 폴더는 건드리지 말라고 했잖아"는 에이전트에게 없는 컨텍스트다.

에이전트로 넘기는 지시는 그 자체로 완결된 제약을 담아야 한다.

```
나쁜 지시:
"아까 합의한 방식으로 나머지 파일도 처리해"

좋은 지시:
"src/api 하위 .js 파일을 .ts로 변환해.
src/legacy, src/generated는 수정하지 마.
타입 추론이 안 되면 any 쓰지 말고 확인 요청해라."
```

### --dangerously-skip-permissions — deny가 작동하지 않는다

이 플래그로 실행하면 deny 리스트가 완전히 무시된다. 모든 도구가 승인 없이 실행된다. Auto Mode와 함께 쓰면 어떤 제약도 없는 상태가 된다.

실제로 문제가 난 케이스: CI 환경에서 격리된 컨테이너가 아닌 공유 빌드 서버에서 이 플래그로 실행했다. 클린업 단계에서 경로를 잘못 잡은 `rm -rf` 명령이 실행됐다. 공유 서버라 다른 빌드 산출물도 같이 날아갔다.

이 플래그는 컨테이너 안에서만 써야 한다. 실행 환경이 컨테이너인지 확인하는 방법:

```bash
cat /proc/1/cgroup | grep -q docker && echo "container" || echo "host"
ls /.dockerenv 2>/dev/null && echo "container"
```

컨테이너 밖이라면 `--dangerously-skip-permissions`는 쓰지 않는다.

---

## Auto Mode와 Plan Mode 조합

"계획은 확인받고 실행은 자동으로"라는 패턴이다.

```
사용자: /plan
사용자: /auto
사용자: 인증 미들웨어를 JWT 기반으로 교체해라.
       기존 세션 쿠키 방식은 deprecated 처리만 하고 지우진 마라.
       테스트도 같이 업데이트해라.

(모델이 합리적 결정으로 플랜 작성 — 중간에 묻지 않음)

모델: 다음 플랜을 제시합니다.
      1. src/middleware/auth.ts 에 verifyJWT 함수 추가
      2. src/middleware/session.ts 의 verifySession 에 @deprecated 주석
      3. src/routes/* 의 authMiddleware 호출부를 verifyJWT 로 변경
      4. __tests__/auth.test.ts 에 JWT 검증 케이스 추가

사용자: 좋아. 진행해.

(여기서부터 Auto Mode로 자동 진행)
```

일반 모드에서는 작업 중간중간 확인 요청이 흩어져서 매번 작은 결정을 내려야 한다. 이 조합을 쓰면 의사결정이 플랜 한 군데로 모인다. 플랜을 잘 검토하면 그 뒤는 안심하고 자동 실행을 맡길 수 있다.

---

## Auto Mode와 Worktree 조합

Worktree는 격리된 git working directory에서 작업하는 기능이다. Auto Mode와 함께 쓰면 "잘못돼도 메인 working directory는 안 더럽혀진다"는 안전망이 생긴다.

```
사용자: /worktree experiment-rate-limiter
사용자: /auto
사용자: rate limiter를 Redis 기반으로 새로 짜봐라.
       기존 in-memory 구현은 그대로 두고, 새 구현체만 추가해라.

(worktree 안에서 자동 실행. 메인 브랜치 영향 없음)

검토 후 마음에 들면 머지, 아니면 worktree 삭제
```

"어떤 구조가 좋을지 모르겠으니 일단 짜본다" 류의 탐색적 작업에서 유용하다. 결과물이 마음에 안 들어도 worktree 통째로 버리면 그만이라, Auto Mode의 적극적인 진행 성향이 단점이 되지 않는다.

---

## 컨텍스트 부족으로 나는 사고

Auto Mode는 컨텍스트를 신뢰해서 빠르게 진행하는 모드다. 컨텍스트가 부정확하면 그만큼 빠르게 망친다.

**모델이 틀린 가정으로 진행**

모델이 "프로젝트가 TypeScript니까 JSX는 TSX로"라는 가정으로 진행했는데, 해당 디렉토리만 JS인 경우가 대표적이다. Ctrl+C로 중단하고 가정을 정정한다.

```
사용자: 잠깐. src/legacy 하위는 .js 그대로 둬라. .ts로 바꾸지 마라.
       지금까지 바꾼 src/legacy 하위 파일들 전부 원래대로 되돌려라.
```

같은 사고가 반복되면 CLAUDE.md에 프로젝트 규칙을 추가한다.

```markdown
# CLAUDE.md
## 절대 수정하지 말 것
- src/legacy/** : 호환성 유지를 위해 보존. .js 그대로
- src/generated/** : 빌드 산출물. 직접 수정 금지
- migrations/**/*.sql : 이미 운영에 적용된 마이그레이션
```

**처음 보는 라이브러리 도입**

모델이 라이브러리 사용법을 잘못 알고 있을 수 있다. 한 번 동작하는 걸 확인한 다음, 그 패턴을 반복 적용할 때 Auto Mode를 켜는 순서가 맞다. 처음부터 Auto Mode로 들어가면 잘못된 패턴이 파일 10개에 퍼지고 나서야 발견된다.

---

## 실무 트러블슈팅

### 의도치 않은 파일이 수정됐을 때

`git diff`로 수정 범위를 먼저 파악한다.

```bash
git status
git diff --stat
```

원본으로 돌리고 싶은 파일은 `git checkout`으로 되돌린다.

```bash
git checkout -- src/unintended-file.ts
```

Auto Mode로 큰 작업을 시작하기 전에 `git stash`로 깔끔한 상태를 만들어두는 게 습관이 돼야 한다. 작업이 끝나고 마음에 들면 stash를 버리고, 망치면 stash로 돌아간다.

### 중간 redirect 방법

작업이 30% 정도 진행됐는데 방향이 약간 어긋난 게 보인다. ESC나 Ctrl+C로 멈추고 추가 지시를 보낸다.

```
사용자: 잠깐. 지금까지 만든 BaseService 추상 클래스는 좋은데,
       메서드 이름을 fetch가 아니라 load 로 통일해라.
       이미 만든 파일들도 같이 수정.
사용자: 계속.
```

Auto Mode가 켜져 있으면 모델이 이 지시를 받아 묻지 않고 반영한다.

---

## 꺼야 하는 시점

새 코드베이스를 처음 탐색할 때. 모델이 프로젝트 구조를 모르는 상태라 잘못된 가정으로 진행할 가능성이 높다. 일반 모드에서 차근차근 질문하면서 구조를 파악하게 하는 게 맞다.

아키텍처 결정이 필요할 때. "이 기능을 어떤 패턴으로 구현할까"는 두세 가지 합리적 선택지가 있고, 어느 쪽을 고르냐에 따라 후속 작업이 달라진다. Auto Mode가 켜져 있으면 모델이 임의로 한 가지를 골라 진행해버려서 나중에 갈아엎는 비용이 커진다.

보안 관련 변경. 인증, 권한, 암호화, 비밀 관리 코드는 작은 실수가 큰 사고로 이어진다. 일반 모드에서 모델이 의문을 제기하면 정확히 답하고, 결과를 한 줄씩 검토한다.

production 환경 변수가 로드된 세션. `NODE_ENV=production`, `DATABASE_URL=prod...` 같은 환경 변수가 로드된 셸에서 Claude Code를 띄웠다면 Auto Mode를 끈다.

처음 보는 외부 라이브러리를 도입할 때. 한 번 동작하는 걸 확인한 다음, 그 패턴을 반복 적용할 때 Auto Mode를 켜는 순서가 맞다.
