---
title: Claude Code Worktree 병렬 스크립트
tags: [ai, claude-code, git-worktree, automation, cicd, shell-script]
updated: 2026-07-15
---

# Claude Code Worktree 병렬 스크립트

## 1. --print 모드

`claude` CLI의 기본 실행 방식은 대화형 세션이다. `--print` 플래그를 붙이면 비대화형으로 전환된다. 프롬프트 하나를 처리하고 결과를 stdout에 출력한 뒤 종료한다.

```bash
claude --print "user.service.ts의 findById에서 N+1 쿼리 문제를 찾아서 수정해줘"
```

스크립트에서 claude를 쓸 때 이 모드를 사용한다. 출력 형식은 `--output-format` 옵션으로 바꿀 수 있다.

```bash
# 기본: 마지막 assistant 메시지 텍스트만 출력
claude --print "프롬프트"

# JSON: 전체 메시지 배열, 비용 정보, tool_use 내역 포함
claude --print --output-format json "프롬프트"

# 스트리밍 JSON: 메시지가 생성되는 대로 JSON 이벤트 출력
claude --print --output-format stream-json "프롬프트"
```

`--print` 모드에서는 세션 상태가 없다. 각 실행이 독립된 대화다. 이전 실행의 컨텍스트가 필요하면 프롬프트에 직접 넣어야 한다. 단, 파일 시스템 상태는 유지되기 때문에 1단계에서 수정한 파일을 2단계에서 그대로 읽을 수 있다.

---

## 2. worktree + --print 병렬 실행

여러 태스크를 동시에 처리할 때 git worktree로 작업 디렉토리를 격리하고, 각 worktree에서 `claude --print`를 백그라운드 프로세스로 실행한다. 이렇게 하면 각 claude 인스턴스가 독립된 파일 시스템 컨텍스트에서 작업하기 때문에 파일 수정 충돌이 발생하지 않는다.

흐름은 단순하다. worktree를 만들고, 거기서 claude를 백그라운드로 띄우고, 전부 끝나면 결과를 수집하고, worktree를 정리한다.

```bash
#!/bin/bash
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel)
TASKS=("fix-auth-bug" "add-user-validation" "update-api-docs")
PIDS=()
WORKTREES=()

cleanup() {
    jobs -p | xargs -r kill 2>/dev/null || true
    for wt in "${WORKTREES[@]}"; do
        git worktree remove --force "$wt" 2>/dev/null || true
    done
    git worktree prune 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for task in "${TASKS[@]}"; do
    wt_path="/tmp/wt-$$-${task}"
    git worktree add "$wt_path" -b "auto/${task}-$$" HEAD

    WORKTREES+=("$wt_path")

    (
        cd "$wt_path"
        claude --print "$(cat "${REPO_ROOT}/prompts/${task}.txt")"
    ) > "/tmp/result-${task}.txt" 2>&1 &

    PIDS+=($!)
done

for i in "${!PIDS[@]}"; do
    pid=${PIDS[$i]}
    task=${TASKS[$i]}

    if wait "$pid"; then
        echo "SUCCESS: $task"
    else
        echo "FAILED: $task (exit: $?)"
        cat "/tmp/result-${task}.txt" >&2
    fi
done
```

`cd "$wt_path"`로 작업 디렉토리를 바꾼 뒤 claude를 실행하는 게 핵심이다. claude가 파일을 읽고 수정하는 모든 작업이 해당 worktree 안에서 일어난다.

---

## 3. 결과 수집

### 3.1 텍스트 결과

기본 출력은 마지막 assistant 응답 텍스트다. 파일에 저장하고 읽으면 된다. 코드 리뷰 결과나 분석 요약처럼 텍스트 자체가 목적인 경우에 쓴다.

### 3.2 JSON 파싱

수정된 파일 목록이나 tool_use 내역이 필요하면 JSON 출력을 쓴다. `jq`로 파싱하면 자동화 파이프라인에서 다음 단계로 넘기기 편하다.

```bash
(
    cd "$wt_path"
    claude --print --output-format json "인증 버그를 수정해줘"
) > result.json

# claude가 어떤 파일을 수정했는지 확인
jq '[.messages[].content[] | select(.type == "tool_use" and .name == "Write") | .input.file_path]' result.json

# 정상 완료 여부 확인
stop_reason=$(jq -r '.stop_reason // "unknown"' result.json)
if [ "$stop_reason" != "end_turn" ]; then
    echo "WARNING: stop_reason=$stop_reason"
fi
```

`stop_reason`이 `max_tokens`면 응답이 잘린 것이다. 작업이 완전히 끝나지 않았을 수 있으니 결과를 그대로 사용하면 안 된다.

### 3.3 exit code

`claude --print`는 성공하면 0, 실패하면 비 0을 반환한다. 실패 원인은 크게 세 가지다: API 오류(rate limit, 네트워크), safety filter, 작업 디렉토리 접근 오류. stderr에 오류 내용이 출력되니까 별도 파일로 캡처해두는 게 좋다.

```bash
(
    cd "$wt_path"
    claude --print "$prompt"
) > result.txt 2> error.txt
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo "Exit: $exit_code, Error: $(cat error.txt)"
fi
```

---

## 4. 병렬 프로세스 관리

### 4.1 동시 실행 수 제한

worktree와 claude 프로세스를 제한 없이 띄우면 API rate limit에 걸린다. 계정 tier에 따라 분당 요청 수 한도가 있고, 병렬로 10개를 동시에 실행하면 금방 초과한다. 동시 실행 수를 3~5개로 제한하는 게 현실적이다.

```bash
#!/bin/bash
MAX_PARALLEL=3
TASKS=("t1" "t2" "t3" "t4" "t5" "t6")
declare -A pid_to_task
running=0

for task in "${TASKS[@]}"; do
    while [ $running -ge $MAX_PARALLEL ]; do
        for pid in "${!pid_to_task[@]}"; do
            if ! kill -0 "$pid" 2>/dev/null; then
                wait "$pid" && echo "done: ${pid_to_task[$pid]}" || true
                unset "pid_to_task[$pid]"
                ((running--)) || true
            fi
        done
        sleep 1
    done

    wt_path="/tmp/wt-$$-${task}"
    git worktree add "$wt_path" -b "auto/${task}-$$" HEAD

    (cd "$wt_path" && claude --print "$(cat "prompts/${task}.txt")") \
        > "/tmp/result-${task}.txt" 2>&1 &

    pid=$!
    pid_to_task[$pid]=$task
    ((running++)) || true
done

for pid in "${!pid_to_task[@]}"; do
    wait "$pid" && echo "done: ${pid_to_task[$pid]}" || echo "failed: ${pid_to_task[$pid]}"
done
```

### 4.2 타임아웃

복잡한 작업은 claude가 오래 걸릴 수 있다. `timeout` 커맨드로 제한을 걸지 않으면 파이프라인이 무한정 대기한다. exit code 124가 반환되면 타임아웃으로 종료된 것이다.

```bash
TIMEOUT=300  # 5분

timeout "$TIMEOUT" bash -c "cd '$wt_path' && claude --print '$prompt'" \
    > result.txt 2>&1
code=$?

if [ $code -eq 124 ]; then
    echo "TIMEOUT after ${TIMEOUT}s"
fi
```

### 4.3 인터럽트 처리

스크립트가 Ctrl+C나 시그널로 종료될 때 worktree가 남으면 디스크에 쌓인다. `trap cleanup EXIT INT TERM`으로 정리 로직을 항상 등록해야 한다. `EXIT`에 걸면 정상 종료든 비정상 종료든 실행된다.

cleanup 함수 안에서 worktree를 `--force`로 제거하는 이유는, claude가 파일을 수정하다 중단된 경우 커밋되지 않은 변경사항이 남아있어서 일반 remove가 실패할 수 있기 때문이다.

---

## 5. CI/CD 파이프라인 연동

### 5.1 GitHub Actions

```yaml
name: Claude Auto Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Claude review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          CHANGED=$(git diff --name-only origin/main...HEAD -- '*.ts' '*.go' '*.py')

          for file in $CHANGED; do
            [ -f "$file" ] || continue
            diff=$(git diff origin/main...HEAD -- "$file")

            claude --print \
              "다음 diff를 리뷰해줘. 버그와 보안 이슈 위주로 짧게:

              ${diff}" > "review-${file//\//_}.txt" 2>&1 || true
          done

      - uses: actions/upload-artifact@v4
        with:
          name: reviews
          path: review-*.txt
```

### 5.2 worktree로 코드 수정 자동화

리뷰만 하는 게 아니라 코드를 직접 수정하고 커밋까지 해야 할 때 worktree가 필요하다. 여러 브랜치에 린트 수정을 자동으로 적용하는 예시다.

```bash
#!/bin/bash
BRANCHES=($(git branch --list 'feature/*' --format='%(refname:short)'))
PIDS=()

for branch in "${BRANCHES[@]}"; do
    wt_path="/tmp/fix-$$-${branch//\//-}"
    git worktree add "$wt_path" "$branch"

    (
        cd "$wt_path"
        claude --print \
            "TypeScript 린트 오류를 전부 수정하고 git commit해줘. \
             커밋 메시지는 'fix: auto lint fix'로." > /tmp/log-${branch//\//-}.txt 2>&1

        if ! git diff --quiet HEAD; then
            git push origin "$branch"
            echo "PUSHED: $branch"
        else
            echo "NO CHANGES: $branch"
        fi
    ) &

    PIDS+=($!)
done

for pid in "${PIDS[@]}"; do
    wait "$pid" || true
done

for branch in "${BRANCHES[@]}"; do
    git worktree remove --force "/tmp/fix-$$-${branch//\//-}" 2>/dev/null || true
done
git worktree prune
```

push는 병렬 subshell 안에서 하지 않고 모든 worktree 작업이 끝난 뒤 순서대로 처리하는 게 더 안전하다. git refs lock 충돌을 피할 수 있다.

---

## 6. 주의사항

### 6.1 worktree 이름 충돌

스크립트 두 개가 동시에 실행되면 같은 이름의 worktree를 만들려다 충돌한다. PID(`$$`)와 타임스탬프를 경로에 반드시 포함해야 한다.

```bash
# 충돌 가능
wt_path="/tmp/worktree-${task}"

# 안전
wt_path="/tmp/wt-$$-${task}-$(date +%s)"
```

브랜치 이름도 마찬가지다. `auto/${task}-$$` 같이 PID를 붙여서 유니크하게 만든다.

### 6.2 git lock 충돌

여러 worktree에서 동시에 git refs를 업데이트하면 `.git/packed-refs.lock` 충돌이 날 수 있다. 브랜치 생성이나 push가 동시에 일어날 때 발생한다. 에러 메시지는 `Unable to create '.git/packed-refs.lock'`이다.

push는 모든 claude 작업이 완료된 뒤 직렬로 처리하는 게 안전하다. 병렬 subshell 안에서 바로 push하면 이 문제를 마주친다.

### 6.3 디스크 사용량

worktree는 체크아웃된 파일을 별도로 갖는다. node_modules가 500MB인 프로젝트에서 worktree 5개를 동시에 띄우면 2.5GB가 필요하다. 작업이 끝나는 즉시 정리하는 게 중요하다.

node_modules가 동일한 경우엔 symlink로 공유할 수 있지만, 브랜치마다 다른 패키지 버전을 쓴다면 별도 설치해야 하고 이 방법은 쓰면 안 된다.

```bash
# 패키지가 동일할 때만 symlink 사용
ln -s "$REPO_ROOT/node_modules" "$wt_path/node_modules"
```

### 6.4 rate limit

병렬로 실행하는 모든 claude 프로세스가 같은 API 키를 공유한다. 3개 이상 동시에 실행하면 rate limit에 걸리는 경우가 많다. 계정 tier를 확인하고 `MAX_PARALLEL`을 조정해야 한다. rate limit 에러는 exit code가 0이 아니고 stderr에 429 관련 메시지가 찍힌다.

### 6.5 컨텍스트 길이 제한

프롬프트에 파일 내용을 통째로 포함하면 context window를 초과할 수 있다. 큰 파일을 다룰 때는 파일 경로만 넘기고 claude가 직접 읽게 하는 게 낫다. `--print` 모드에서도 claude는 작업 디렉토리의 파일을 읽을 수 있다.

```bash
# 파일 내용을 프롬프트에 직접 넣으면 컨텍스트 낭비
claude --print "다음 코드를 리뷰해줘: $(cat huge-file.ts)"

# 파일 경로만 넘기기
claude --print "huge-file.ts를 리뷰해줘"
```
