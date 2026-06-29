---
title: Claude Code OMC (Orchestrated Multi-Claude)
tags: [ai, claude-code, headless, multi-instance, git-worktree, automation]
updated: 2026-06-29
---

# Claude Code OMC (Orchestrated Multi-Claude)

OMC는 Claude Code 인스턴스를 여러 개 동시에 띄워서 조율하는 운영 방식이다. 한 세션 안에서 Workflow 도구로 서브에이전트를 fan-out하는 것과는 층위가 다르다. 그쪽은 한 프로세스 안의 일이고, OMC는 프로세스 자체를 N개 돌린다.

이 구분을 먼저 잡아야 한다. [Claude Code 오케스트레이션](Claude_Code_Orchestration.md)은 단일 세션 안에서 `agent()` 호출로 컨텍스트를 격리한다. 부모 세션이 결과를 모으고 머지하고 검증한다. 전부 한 런타임 안에서 일어나니까 토큰 회계도 공유되고, 동시 실행 수도 런타임이 알아서 캡을 건다. OMC는 그 위 계층이다. 셸에서 `claude -p`로 비대화형 프로세스를 여러 개 띄우고, 각각을 별도 작업 디렉토리에 묶고, 결과 파일을 직접 취합한다. 조율 주체가 Claude Code 런타임이 아니라 내가 짠 셸 스크립트다.

언제 어느 쪽을 쓰는지부터 정리한다.

- 작업이 서로 의존하고, 중간 결과를 부모가 보고 다음 단계를 정해야 하면 → in-session Workflow
- 작업이 서로 독립적이고, 각각이 분 단위로 오래 걸리고, 파일 충돌 없이 병렬로 갈 수 있으면 → OMC
- 빌드·테스트처럼 출력만 크고 판단이 단순한 단일 장기 작업이면 → [롱잡 운영](Claude_Code_Long_Job.md)의 백그라운드 Bash

---

## 1. headless 모드: claude -p

OMC의 출발점은 headless 모드다. `claude -p "프롬프트"`는 대화형 TUI를 띄우지 않고 프롬프트 하나를 받아 작업을 끝낸 뒤 결과를 stdout으로 뱉고 종료한다. `-p`는 `--print`의 줄임이다.

```bash
claude -p "src/auth 디렉토리의 함수마다 JSDoc 주석을 달아라" \
  --output-format json
```

스크립트에서 여러 개를 띄우려면 이게 전제다. 대화형 세션은 입력을 기다리니까 백그라운드로 묶을 수 없다. headless는 입력을 안 받고 끝까지 자율로 돌기 때문에 `&`로 묶거나 `xargs -P`로 풀에 넣을 수 있다.

### 1.1 출력 포맷 세 가지

`--output-format`은 결과 파싱 방식을 결정한다. OMC에서는 거의 항상 `text`가 아니라 `json`을 쓴다.

| 포맷 | 출력 | 용도 |
|---|---|---|
| `text` (기본) | 최종 답변 텍스트만 | 사람이 눈으로 볼 때 |
| `json` | 결과 + 메타데이터(비용, 토큰, 종료 이유)를 한 덩어리 JSON으로 | 스크립트가 끝나고 파싱할 때 |
| `stream-json` | 이벤트마다 한 줄씩 JSON(JSONL) | 진행 중에 실시간으로 파싱할 때 |

`json`은 작업이 끝나야 한 번에 나온다. 그래서 N개를 띄워놓고 각 프로세스의 stdout을 파일로 받은 다음, 전부 끝나면 `jq`로 긁는 패턴에 맞는다.

```bash
claude -p "리팩토링해라" --output-format json > result.json
# 끝난 뒤
jq -r '.result' result.json          # 최종 텍스트
jq -r '.total_cost_usd' result.json  # 이 실행에 든 비용
jq -r '.num_turns' result.json       # 턴 수
jq -r '.is_error' result.json        # 에러 종료 여부
```

`stream-json`은 한 줄에 이벤트 하나씩 흘러나온다. 장시간 도는 인스턴스의 진행 상황을 실시간으로 모니터링하거나, 특정 도구 호출이 나오면 곧바로 끊고 싶을 때 쓴다.

```bash
claude -p "통합 테스트를 돌리고 실패를 고쳐라" \
  --output-format stream-json --verbose \
| while IFS= read -r line; do
    type=$(echo "$line" | jq -r '.type')
    [ "$type" = "result" ] && echo "$line" | jq -r '.result'
  done
```

`stream-json`은 `--verbose`를 같이 줘야 모든 이벤트가 나온다. 안 주면 일부 이벤트가 누락되는 경우가 있다.

### 1.2 자율 실행과 권한

headless로 띄우면 권한 프롬프트를 사람이 눌러줄 수 없다. 그래서 도구 권한을 미리 정해놓고 띄워야 한다.

```bash
claude -p "타입 에러를 고쳐라" \
  --allowedTools "Read,Edit,Bash(npm run typecheck:*)" \
  --output-format json
```

`--allowedTools`로 허용할 도구를 명시한다. 여기에 없는 도구를 쓰려고 하면 그 호출은 거부되고, 인스턴스는 다른 방법을 찾거나 그 단계를 건너뛴다. 멈추지는 않는다.

`--dangerously-skip-permissions`로 권한 확인을 통째로 건너뛰는 옵션도 있는데, 이름 그대로 위험하다. OMC로 N개를 자율로 돌릴 때 이걸 켜면 N개가 전부 무방비로 임의 명령을 실행할 수 있다. 격리된 컨테이너나 일회용 worktree 안에서만 써야 하고, 호스트 작업 디렉토리에서 바로 켜면 안 된다.

---

## 2. worktree로 파일 충돌 피하기

OMC의 가장 큰 함정은 여러 인스턴스가 같은 작업 디렉토리에서 같은 파일을 건드리는 거다. 두 인스턴스가 `package.json`을 동시에 수정하면 나중에 쓴 쪽이 앞쪽을 덮어쓴다. git 단계로 가기도 전에 파일 시스템 레벨에서 깨진다.

해법은 인스턴스마다 작업 디렉토리를 분리하는 거다. git worktree가 여기에 맞는다. worktree 자체의 기본 동작과 정리 방법은 [Claude Code Worktree](Claude_Code_Worktree.md) 문서에 정리해뒀고, 여기서는 OMC 관점에서 어떻게 엮는지만 본다.

### 2.1 인스턴스마다 worktree 하나

```bash
#!/bin/bash
# 작업 3개를 각각 별도 worktree + 별도 인스턴스로

TASKS=(
  "auth:src/auth 모듈에 입력 검증을 추가해라"
  "api:src/api 응답에 타입을 명시해라"
  "db:db 쿼리에 인덱스 힌트 주석을 달아라"
)

for entry in "${TASKS[@]}"; do
  name="${entry%%:*}"
  prompt="${entry#*:}"
  wt="../omc-$name"

  git worktree add -b "omc/$name" "$wt"

  (
    cd "$wt"
    claude -p "$prompt" \
      --allowedTools "Read,Edit,Bash(npm run lint:*)" \
      --output-format json > "../omc-result-$name.json"
  ) &
done

wait
echo "전부 종료"
```

각 인스턴스가 `omc/auth`, `omc/api`, `omc/db` 브랜치를 자기 worktree에서 체크아웃하니까 파일이 물리적으로 분리된다. 같은 `package.json`을 셋이 수정해도 각자 자기 디렉토리의 사본을 건드린다. 충돌은 나중에 머지할 때 git이 잡는다. 파일이 통째로 덮어써지는 사고는 안 난다.

`( cd "$wt"; ... ) &` 로 서브셸 안에서 디렉토리를 바꾸고 백그라운드로 띄운다. 서브셸이라 부모 셸의 작업 디렉토리는 안 바뀐다. `wait`로 전부 끝날 때까지 막는다.

### 2.2 worktree를 안 나눠도 되는 경우

전부 worktree로 가를 필요는 없다. 작업들이 서로 다른 디렉토리만 건드린다고 확신하면(예: 한 인스턴스는 `frontend/`, 다른 인스턴스는 `backend/`만) 같은 작업 디렉토리에서 돌려도 충돌이 안 난다. 하지만 이건 인스턴스가 정말 그 범위 밖을 안 건드린다는 보장이 있어야 한다. Claude Code는 작업하다 공통 설정 파일(`tsconfig.json`, lockfile)을 손대는 경우가 있어서, 조금이라도 애매하면 worktree로 가르는 게 안전하다.

### 2.3 node_modules 문제

worktree마다 `node_modules`가 따로 있어야 빌드·린트가 돈다. worktree를 새로 만들면 의존성이 안 깔려 있다. 인스턴스가 빌드를 돌려야 하면 띄우기 전에 깔아주거나, lint/typecheck처럼 의존성이 필요한 명령을 권한에서 빼야 한다.

```bash
git worktree add -b "omc/$name" "$wt"
(cd "$wt" && cp -R ../main-project/node_modules ./node_modules)  # 복사가 install보다 빠르다
```

모노레포면 worktree 3개에 `npm install`을 세 번 돌리는 것만으로도 디스크와 시간이 크게 든다. 원본의 `node_modules`를 복사하거나, pnpm 같은 글로벌 스토어 기반 패키지 매니저를 쓰면 부담이 준다.

---

## 3. 동시 인스턴스 수 정하기

몇 개를 동시에 띄울지가 OMC 운영의 핵심 변수다. 무작정 늘리면 세 군데서 막힌다.

### 3.1 API rate limit

각 인스턴스가 독립적으로 API를 호출한다. 10개를 띄우면 같은 계정/조직의 rate limit을 10개가 나눠 쓴다. 분당 요청 수나 분당 토큰 수 한도에 걸리면 인스턴스들이 429를 맞고 백오프에 들어간다. 백오프 중인 인스턴스는 일을 안 하면서 자리만 차지하니까, 한도를 넘겨 띄우면 오히려 전체가 느려진다.

조직의 rate limit을 모르면 적게 시작해서 올려야 한다. 4개로 시작해서 429가 안 나오면 6개, 8개로 늘린다. 로그에 `rate_limit` 관련 에러가 보이기 시작하면 그 직전 숫자가 상한이다.

### 3.2 토큰 비용

인스턴스 수만큼 비용이 곱해진다. in-session Workflow는 부모가 토큰 풀을 공유하고 캡을 걸지만, OMC는 각 프로세스가 독립이라 자동 캡이 없다. 8개를 각각 풀 코드베이스 분석에 붙이면 8배 토큰이 그대로 청구된다.

`--output-format json`의 `total_cost_usd`로 인스턴스별 실제 비용이 찍힌다. 돌려보고 합산해서 작업 한 건당 비용을 잡아두면, 다음에 N개 띄울 때 예산을 미리 계산할 수 있다.

```bash
jq -s 'map(.total_cost_usd) | add' omc-result-*.json  # 전체 합산
```

### 3.3 머신 CPU/메모리

인스턴스마다 Node 런타임이 뜨고, 각자 빌드나 테스트를 돌리면 그 프로세스도 추가로 뜬다. 인스턴스 3개가 각각 webpack 빌드를 돌리면 빌드 프로세스만 셋이라 8코어 머신도 금방 포화된다. 메모리는 더 빨리 터진다. 빌드 한 번에 2~3GB 먹는 프로젝트면 인스턴스 4개로 OOM이 난다.

API 한도보다 머신 한도가 먼저 걸리는 경우가 실무에서 더 흔하다. 인스턴스 자체는 가벼워도, 인스턴스가 시키는 빌드/테스트가 무겁다.

### 3.4 큐로 동시 실행 수 제한

작업이 동시 인스턴스 수보다 많으면 전부 한꺼번에 띄우지 말고 풀로 돌린다. `xargs -P`가 제일 간단하다.

```bash
# tasks.txt: 한 줄에 작업 하나
cat tasks.txt | xargs -P 4 -I {} bash -c '
  name=$(echo "{}" | cut -d: -f1)
  prompt=$(echo "{}" | cut -d: -f2-)
  claude -p "$prompt" --output-format json > "result-$name.json"
'
```

`-P 4`가 동시 실행 4개로 제한한다. 작업이 20개여도 한 번에 4개만 돌고, 하나 끝나면 다음 게 들어간다. rate limit·비용·머신 부하를 한 숫자로 통제할 수 있어서, OMC 스크립트는 이 풀 패턴을 기본으로 잡는 게 좋다.

GNU `parallel`을 쓸 수 있으면 작업별 로그 분리, 실패 재시도, 진행률 표시까지 붙는다.

```bash
parallel -j 4 --joblog omc.log --retries 2 \
  'claude -p {} --output-format json > result-{#}.json' :::: tasks.txt
```

`--joblog`로 작업별 종료 코드와 소요 시간이 파일에 남고, `--retries 2`로 실패한 작업을 두 번까지 다시 돌린다.

---

## 4. 결과 취합과 검증

인스턴스를 띄우는 것보다 결과를 모으고 합치는 게 더 손이 간다. 각자 따로 돌았으니 결과도 흩어져 있다.

### 4.1 공통 작업 큐 파일

작업 목록을 파일 하나로 관리하면 어느 작업이 누구에게 갔는지, 어디까지 됐는지 추적할 수 있다. 단순하게는 위에서 쓴 `tasks.txt`면 되고, 상태를 추적하려면 JSON 한 줄씩 쓰는 방식이 낫다.

```bash
# queue.jsonl
{"id":"auth","prompt":"입력 검증 추가","status":"pending"}
{"id":"api","prompt":"타입 명시","status":"pending"}
```

인스턴스가 시작할 때 `status`를 `running`으로, 끝나면 `done`이나 `failed`로 바꿔 쓴다. 여러 프로세스가 같은 파일을 동시에 쓰면 깨지니까, 상태 갱신은 인스턴스별 파일에 각자 쓰고 나중에 합치는 편이 안전하다. 공유 파일 한 개에 동시 append하는 건 race condition의 출발점이다.

### 4.2 결과 JSON 수집

`--output-format json`으로 받은 결과 파일들을 한 번에 긁는다.

```bash
# 실패한 인스턴스만 추리기
for f in omc-result-*.json; do
  if [ "$(jq -r '.is_error' "$f")" = "true" ]; then
    echo "실패: $f"
    jq -r '.result' "$f"
  fi
done

# 전체 요약
jq -s 'map({id: input_filename, cost: .total_cost_usd, error: .is_error})' \
  omc-result-*.json
```

`is_error`로 정상 종료와 에러 종료를 가른다. 인스턴스가 작업을 "했다고 주장"하는 것과 실제로 코드가 맞는지는 별개라서, 결과 텍스트만 믿으면 안 된다. 다음 단계로 검증이 필요하다.

### 4.3 머지와 충돌 처리

worktree로 갈라 작업했으면 각 브랜치를 main으로 합쳐야 한다. 순서대로 머지하면서 충돌을 본다.

```bash
for name in auth api db; do
  if git merge --no-ff "omc/$name" -m "merge omc/$name"; then
    echo "$name 머지 성공"
  else
    echo "$name 머지 충돌 — 수동 처리 필요"
    git merge --abort
    echo "$name" >> merge-conflicts.txt
  fi
done
```

충돌이 나면 `--abort`로 되돌리고 목록에 적어둔다. 충돌 난 브랜치들은 나중에 한 곳에 모아 사람이나 별도 Claude Code 세션이 처리한다. 자동 머지를 강행해서 충돌 마커가 코드에 박힌 채로 커밋되는 게 제일 나쁜 결과다.

충돌 자체를 줄이려면 작업을 가를 때부터 디렉토리 경계로 가르는 게 낫다. 같은 파일을 여러 작업이 건드릴 게 뻔하면 그건 애초에 병렬화에 안 맞는 작업이다.

### 4.4 검증 패스

머지가 끝났다고 일이 끝난 게 아니다. 합쳐진 코드가 빌드되고 테스트를 통과하는지 마지막에 한 번 돌린다. OMC는 각 인스턴스가 자기 worktree에서만 검증했으니, 합쳐진 전체는 아무도 안 봤다. 머지 후 통합 검증은 OMC에서 빼먹기 쉬운데 빼면 안 되는 단계다.

```bash
git checkout main
npm run build && npm test || echo "통합 검증 실패 — 머지 결과 재검토 필요"
```

---

## 5. 실패 모드

OMC는 실패 지점이 분산돼 있어서, 어디서 깨졌는지 찾는 것부터 일이다. 자주 겪는 것들.

### 5.1 두 인스턴스가 같은 파일을 건드림

worktree로 안 갈랐을 때 제일 먼저 터진다. 증상은 둘 중 한 인스턴스의 변경이 통째로 사라지는 거다. A가 파일을 읽고 수정하는 사이 B가 같은 파일을 다른 내용으로 덮으면, A의 변경은 흔적도 없다. git에도 안 남는다(아직 커밋 전이니까).

방어는 worktree 분리 하나뿐이다. 같은 디렉토리에서 돌려야 하는 사정이 있으면 작업 범위가 파일 단위로 안 겹치는지 띄우기 전에 확인해야 한다.

### 5.2 인스턴스가 멈춤

headless 인스턴스가 무한 루프에 빠지거나, 응답을 기다리며 멈춰 있을 수 있다. 대화형이면 화면에 보이지만 백그라운드 headless는 안 보인다. `wait`로 무작정 기다리면 멈춘 인스턴스 하나 때문에 전체가 안 끝난다.

타임아웃을 걸어야 한다.

```bash
timeout 600 claude -p "$prompt" --output-format json > "result-$name.json" \
  || echo "$name 타임아웃 또는 실패 (exit $?)" >> failed.txt
```

`timeout 600`으로 10분 넘으면 강제 종료한다. 종료된 인스턴스는 `failed.txt`에 적어 따로 처리한다. GNU `parallel`을 쓰면 `--timeout`으로 같은 걸 작업별로 건다.

진행 중인 인스턴스가 살아 있는지 보려면 `stream-json` 출력을 tail해서 마지막 이벤트 시각을 본다. 몇 분째 새 이벤트가 없으면 멈춘 거다.

### 5.3 부분 실패 재시도

10개 중 2개만 실패하면 10개를 다 다시 돌릴 이유가 없다. 실패한 것만 다시 돌린다. 그래서 작업 ID와 결과 파일을 1:1로 매칭해두는 게 중요하다.

```bash
# 1차 실행 후, 결과 파일이 없거나 에러인 작업만 재실행
while IFS=: read -r name prompt; do
  f="result-$name.json"
  if [ ! -f "$f" ] || [ "$(jq -r '.is_error' "$f")" = "true" ]; then
    echo "재시도: $name"
    claude -p "$prompt" --output-format json > "$f"
  fi
done < tasks.txt
```

재시도가 의미 있으려면 작업이 멱등이어야 한다. 같은 프롬프트를 다시 줘도 처음부터 다시 하는 작업이면 안전하다. "기존 코드에 한 줄 추가"처럼 이미 한 번 적용됐을 수 있는 작업을 재시도하면 두 번 적용되는 사고가 난다. worktree를 매번 새로 만들어 깨끗한 상태에서 재시도하면 이 문제를 피한다.

---

## 6. OMC를 쓰지 말아야 할 때

OMC는 오버헤드가 크다. worktree 만들고, 인스턴스 띄우고, 결과 모으고, 머지하고, 통합 검증하는 과정 전체가 비용이다. 이 오버헤드를 정당화할 만큼 작업이 크고 병렬적일 때만 의미가 있다.

다음 경우는 OMC가 손해다.

**작업이 작을 때.** 파일 두세 개 고치는 작업을 OMC로 가르면 셋업 시간이 작업 시간보다 길다. 한 세션에서 순서대로 하는 게 빠르다.

**작업이 순차 의존적일 때.** "스키마 바꾸고 → 그 스키마 쓰는 코드 고치고 → 테스트 갱신"처럼 앞 단계 결과가 다음 단계 입력이면 병렬이 안 된다. 억지로 가르면 인스턴스끼리 서로의 결과를 못 봐서 어긋난 코드를 만든다. 이건 in-session Workflow의 `pipeline`이 맞는다. 한 런타임 안에서 단계 간 결과를 넘길 수 있으니까.

**중간 판단이 필요할 때.** 작업 진행 중에 "이 방향이 맞나" 같은 판단을 부모가 내려야 하면, 부모가 자식의 컨텍스트를 봐야 한다. OMC는 인스턴스가 각자 끝까지 자율로 가고 결과만 파일로 남기니까, 중간 개입이 안 된다. 부모-자식 간 컨텍스트 공유가 필요하면 in-session Workflow다.

**단일 장기 작업일 때.** 빌드 하나, 마이그레이션 하나처럼 병렬화할 게 없는 긴 작업은 OMC가 아니라 [롱잡 운영](Claude_Code_Long_Job.md)의 백그라운드 Bash다. 인스턴스를 추가로 띄울 이유가 없다.

정리하면 OMC가 맞는 건 이 조건이 다 모일 때다. 작업이 여러 개고, 서로 독립적이고, 각각이 분 단위로 오래 걸리고, 파일 경계로 깔끔하게 나뉜다. 하나라도 어긋나면 in-session Workflow나 롱잡 쪽이 낫다.

---

## 관련 문서

- [Claude Code 오케스트레이션](Claude_Code_Orchestration.md) — 단일 세션 안에서 Workflow 도구로 서브에이전트를 fan-out하는 in-session 방식
- [Claude Code Worktree](Claude_Code_Worktree.md) — git worktree 기본 동작, 정리, lock 문제
- [Claude Code 롱잡 운영](Claude_Code_Long_Job.md) — 단일 세션에서 분 단위 백그라운드 작업 돌리기
- [Claude Code Agent](Claude_Code_Agent.md) — Agent SDK로 직접 에이전트 구성하기
