---
title: Claude Code 오케스트레이션
tags: [ai, claude-code, orchestration, automation, agent-sdk, ci-cd]
updated: 2026-03-25
---

# Claude Code 오케스트레이션

Claude Code를 단일 세션에서 쓰는 건 금방 익숙해진다. 문제는 "분석하고, 구현하고, 테스트하고, 리뷰까지 자동으로 돌리고 싶다"는 시점에서 시작된다. 개별 기능(헤드리스 모드, Worktree, 서브에이전트, Schedule)은 [Claude Code 문서](Claude_Code.md)에서 다루고 있다. 이 문서는 그것들을 **조합해서 복잡한 작업을 자동화하는 패턴**에 집중한다.

---

## 1. Claude Agent SDK로 커스텀 에이전트 만들기

`@anthropic-ai/claude-code`를 라이브러리로 import하면 Claude Code를 코드에서 직접 제어할 수 있다. CLI에서 대화하는 게 아니라, 프로그래밍으로 워크플로우를 짜는 거다.

### 기본 구조

```typescript
import { ClaudeCode } from "@anthropic-ai/claude-code";

const claude = new ClaudeCode({
  model: "claude-sonnet-4-6",
  maxTurns: 20,
  permissionMode: "dangerously-skip-permissions", // CI 환경 전용
});

const result = await claude.run({
  prompt: "src/auth/auth.service.ts의 refreshToken 메서드에서 만료된 토큰 처리 로직을 수정해줘.",
  workingDirectory: "/home/project",
});

console.log(result.output);
console.log(`사용 토큰: ${result.usage.totalTokens}`);
```

### 다단계 워크플로우

한 에이전트의 출력을 다음 에이전트의 입력으로 넘기는 패턴이다. 각 단계마다 모델을 바꿀 수 있다.

```typescript
import { ClaudeCode } from "@anthropic-ai/claude-code";

async function refactorWorkflow(targetDir: string) {
  // 1단계: Opus로 설계
  const planner = new ClaudeCode({ model: "claude-opus-4-6", maxTurns: 5 });
  const plan = await planner.run({
    prompt: `${targetDir} 디렉토리의 코드를 분석해서 리팩토링 계획을 세워줘.
수정 대상 파일 목록과 각 파일에서 바꿀 내용을 JSON으로 출력해.`,
    workingDirectory: targetDir,
    outputFormat: "json",
  });

  // 2단계: Sonnet으로 구현
  const implementer = new ClaudeCode({ model: "claude-sonnet-4-6", maxTurns: 30 });
  const impl = await implementer.run({
    prompt: `아래 리팩토링 계획대로 코드를 수정해줘. 기존 테스트가 깨지면 안 된다.
계획: ${plan.output}`,
    workingDirectory: targetDir,
  });

  // 3단계: 테스트 실행
  const tester = new ClaudeCode({ model: "claude-sonnet-4-6", maxTurns: 10 });
  const testResult = await tester.run({
    prompt: "npm test 실행해서 결과 알려줘. 실패하면 원인을 분석해줘.",
    workingDirectory: targetDir,
  });

  return { plan: plan.output, implementation: impl.output, test: testResult.output };
}
```

핵심은 **각 단계의 컨텍스트가 분리**된다는 점이다. 설계 단계에서 읽은 파일 수십 개가 구현 단계의 컨텍스트를 먹지 않는다. 대화형 세션에서 `/clear`를 치는 것과 같은 효과인데, 프로그래밍으로 자동화된 것이다.

---

## 2. 멀티 인스턴스 병렬 실행

모노레포에서 패키지 10개를 동시에 리팩토링해야 하는 상황을 생각해보자. 하나씩 돌리면 30분, 병렬로 돌리면 5분이다.

### 패키지별 병렬 실행

```typescript
import { ClaudeCode } from "@anthropic-ai/claude-code";

async function parallelRefactor(packages: string[], instruction: string) {
  const claude = new ClaudeCode({
    model: "claude-sonnet-4-6",
    maxTurns: 20,
    permissionMode: "dangerously-skip-permissions",
  });

  // 모든 패키지에 동시에 Claude Code 투입
  const tasks = packages.map((pkg) =>
    claude.run({
      prompt: instruction,
      workingDirectory: pkg,
    }).then((result) => ({
      package: pkg,
      success: result.exitCode === 0,
      output: result.output,
    })).catch((err) => ({
      package: pkg,
      success: false,
      output: err.message,
    }))
  );

  return Promise.allSettled(tasks);
}

// 사용
const packages = [
  "/repo/packages/auth",
  "/repo/packages/payment",
  "/repo/packages/notification",
  "/repo/packages/user",
];

const results = await parallelRefactor(
  packages,
  "console.log를 전부 logger.info/warn/error로 교체해줘. winston logger를 import해서 사용."
);
```

### 동시 실행 수 제한

패키지가 20개인데 한꺼번에 20개를 돌리면 API rate limit에 걸린다. 동시 실행 수를 제한해야 한다.

```typescript
async function parallelWithLimit<T>(
  tasks: (() => Promise<T>)[],
  concurrency: number
): Promise<T[]> {
  const results: T[] = [];
  const executing = new Set<Promise<void>>();

  for (const task of tasks) {
    const p = task().then((result) => {
      results.push(result);
      executing.delete(p);
    });
    executing.add(p);

    if (executing.size >= concurrency) {
      await Promise.race(executing);
    }
  }

  await Promise.all(executing);
  return results;
}

// 동시에 최대 4개만 실행
await parallelWithLimit(
  packages.map((pkg) => () =>
    claude.run({ prompt: instruction, workingDirectory: pkg })
  ),
  4
);
```

실무에서는 동시 실행 수를 3~5개로 잡는 게 안전하다. API 호출 수 기준이 아니라 Claude Code 인스턴스 기준이고, 각 인스턴스가 내부적으로 여러 번 API를 호출한다.

---

## 3. 파이프라인 오케스트레이션

분석 → 구현 → 테스트 → 리뷰를 자동으로 연결하는 구조다. CI/CD 파이프라인과 비슷하게 단계별로 실행하되, 이전 단계의 결과에 따라 분기한다.

### 파이프라인 정의

```typescript
import { ClaudeCode } from "@anthropic-ai/claude-code";

interface PipelineStep {
  name: string;
  model: string;
  prompt: (prevResult: string) => string;
  maxTurns: number;
  continueOnFail?: boolean;
}

async function runPipeline(steps: PipelineStep[], workDir: string) {
  let prevOutput = "";
  const results: { step: string; success: boolean; output: string }[] = [];

  for (const step of steps) {
    console.log(`[파이프라인] ${step.name} 시작`);

    const claude = new ClaudeCode({
      model: step.model,
      maxTurns: step.maxTurns,
      permissionMode: "dangerously-skip-permissions",
    });

    try {
      const result = await claude.run({
        prompt: step.prompt(prevOutput),
        workingDirectory: workDir,
      });

      prevOutput = result.output;
      results.push({ step: step.name, success: true, output: result.output });
      console.log(`[파이프라인] ${step.name} 완료`);
    } catch (err) {
      results.push({ step: step.name, success: false, output: String(err) });
      console.error(`[파이프라인] ${step.name} 실패: ${err}`);

      if (!step.continueOnFail) {
        console.error("[파이프라인] 중단됨");
        break;
      }
    }
  }

  return results;
}
```

### 실제 사용 예시

```typescript
const migrationPipeline: PipelineStep[] = [
  {
    name: "분석",
    model: "claude-opus-4-6",
    maxTurns: 10,
    prompt: () =>
      "이 프로젝트의 TypeORM 0.2 사용 패턴을 분석해줘. 0.3으로 마이그레이션할 때 깨질 부분을 파일별로 정리해서 JSON으로 출력해.",
  },
  {
    name: "구현",
    model: "claude-sonnet-4-6",
    maxTurns: 40,
    prompt: (analysis) =>
      `아래 분석 결과를 기반으로 TypeORM 0.3 마이그레이션을 수행해줘. 한 파일씩 수정하고, 수정할 때마다 타입 체크가 통과하는지 확인해.
분석: ${analysis}`,
  },
  {
    name: "테스트",
    model: "claude-sonnet-4-6",
    maxTurns: 15,
    prompt: () =>
      "npm test를 실행해줘. 실패하는 테스트가 있으면 원인을 파악해서 수정해.",
  },
  {
    name: "리뷰",
    model: "claude-opus-4-6",
    maxTurns: 10,
    continueOnFail: true,
    prompt: () =>
      "git diff를 보고 이번 마이그레이션의 변경 사항을 리뷰해줘. 놓친 부분이나 위험한 변경이 있는지 확인해.",
  },
];

const results = await runPipeline(migrationPipeline, "/home/project");
```

파이프라인에서 주의할 점은 **이전 단계의 출력 크기**다. 분석 결과가 5000자가 넘어가면 다음 단계 프롬프트에 넣을 때 컨텍스트를 많이 먹는다. 분석 단계에서 JSON 형식으로 핵심만 출력하도록 지정하고, `outputFormat: "json"`을 쓰면 파싱도 편하다.

---

## 4. Worktree + Sub-agent 병렬 작업

Git worktree로 격리된 작업 공간을 만들고, 각 worktree에서 서브에이전트가 독립적으로 작업하는 패턴이다. 메인 브랜치를 건드리지 않고 여러 작업을 동시에 진행할 수 있다.

### 셸 스크립트로 구성

```bash
#!/bin/bash
# scripts/parallel-worktree.sh
# 여러 브랜치에서 동시에 독립적인 작업 수행

REPO_ROOT=$(git rev-parse --show-toplevel)
WORK_BASE="${REPO_ROOT}/.worktrees"

# 작업 정의: "브랜치명|프롬프트"
TASKS=(
  "fix/login-bug|src/auth/login.service.ts의 세션 만료 버그를 수정해줘. 만료된 세션으로 요청 시 401을 반환해야 한다."
  "feat/rate-limit|src/middleware/에 rate limiter 미들웨어를 추가해줘. IP당 분당 100요청 제한."
  "refactor/error-handling|src/common/errors.ts의 에러 클래스를 NestJS HttpException 기반으로 바꿔줘."
)

mkdir -p "$WORK_BASE"

pids=()

for task in "${TASKS[@]}"; do
  IFS='|' read -r branch prompt <<< "$task"

  worktree_dir="${WORK_BASE}/${branch//\//-}"

  # worktree 생성
  git worktree add -b "$branch" "$worktree_dir" main 2>/dev/null

  # 각 worktree에서 Claude Code 실행 (백그라운드)
  (
    cd "$worktree_dir"
    claude --print --dangerously-skip-permissions --max-turns 20 "$prompt" \
      > "${worktree_dir}/claude-output.log" 2>&1

    if [ $? -eq 0 ]; then
      git add -A
      git commit -m "feat: ${branch} - automated by Claude Code"
      echo "[완료] $branch"
    else
      echo "[실패] $branch — 로그: ${worktree_dir}/claude-output.log"
    fi
  ) &

  pids+=($!)
done

# 모든 작업 완료 대기
for pid in "${pids[@]}"; do
  wait "$pid"
done

echo "모든 작업 완료. 결과 확인:"
for task in "${TASKS[@]}"; do
  IFS='|' read -r branch _ <<< "$task"
  worktree_dir="${WORK_BASE}/${branch//\//-}"
  echo "  $branch: $(cat "${worktree_dir}/claude-output.log" | tail -5)"
done
```

### 작업 완료 후 정리

```bash
#!/bin/bash
# scripts/cleanup-worktrees.sh

REPO_ROOT=$(git rev-parse --show-toplevel)
WORK_BASE="${REPO_ROOT}/.worktrees"

# 각 worktree의 브랜치를 PR로 올림
for dir in "$WORK_BASE"/*/; do
  branch=$(cd "$dir" && git branch --show-current)
  if [ -n "$branch" ]; then
    cd "$dir"
    git push origin "$branch"
    gh pr create --base main --head "$branch" \
      --title "Auto: ${branch}" \
      --body "Claude Code 자동 생성 PR. 리뷰 필요."
  fi
done

# worktree 제거
git worktree list --porcelain | grep "^worktree " | grep ".worktrees" | \
  awk '{print $2}' | while read wt; do
    git worktree remove --force "$wt"
  done
```

이 패턴의 핵심은 **각 worktree가 완전히 독립된 파일시스템**이라는 거다. 같은 파일을 동시에 수정해도 충돌이 안 생긴다. 충돌은 나중에 PR을 머지할 때 한 번만 해결하면 된다.

주의할 점: worktree를 너무 많이 만들면 디스크 공간을 잡아먹는다. 작업 끝나면 반드시 정리하고, `.gitignore`에 `.worktrees/`를 추가해둔다.

---

## 5. 헤드리스 모드 체이닝

`--print`로 실행한 Claude Code의 stdout을 다음 Claude Code의 stdin으로 파이핑하는 패턴이다. Agent SDK 없이 셸 스크립트만으로 파이프라인을 구성할 수 있다.

### 기본 체이닝

```bash
#!/bin/bash
# scripts/chain-analysis.sh
# 분석 → 구현 → 검증 체이닝

set -euo pipefail

PROJECT_DIR="$(pwd)"

# 1단계: 분석 — JSON으로 출력받아서 다음 단계에 넘김
echo "[1/3] 분석 중..."
ANALYSIS=$(claude --print --output-format json \
  --model claude-opus-4-6 \
  --max-turns 10 \
  "src/payment/ 디렉토리의 결제 로직에서 동시성 문제가 발생할 수 있는 지점을 찾아줘. 파일명과 라인 번호를 JSON 배열로 출력해.")

echo "$ANALYSIS" | jq '.'

# 2단계: 수정 — 분석 결과를 프롬프트에 포함
echo "[2/3] 수정 중..."
echo "$ANALYSIS" | claude --print \
  --model claude-sonnet-4-6 \
  --max-turns 25 \
  --dangerously-skip-permissions \
  "stdin으로 받은 JSON은 동시성 문제가 있는 코드 위치 목록이다. 각 위치를 확인하고 적절한 락이나 트랜잭션으로 수정해줘."

# 3단계: 검증
echo "[3/3] 테스트 실행 중..."
TEST_OUTPUT=$(npm test 2>&1) || true

if echo "$TEST_OUTPUT" | grep -q "FAIL"; then
  echo "$TEST_OUTPUT" | claude --print \
    --max-turns 10 \
    --dangerously-skip-permissions \
    "테스트가 실패했다. 로그를 보고 원인을 파악해서 수정해줘."
else
  echo "모든 테스트 통과"
fi
```

### 조건 분기가 있는 체이닝

```bash
#!/bin/bash
# scripts/smart-fix.sh
# 에러 타입에 따라 다른 처리 경로로 분기

set -uo pipefail

# 빌드 시도
BUILD_OUTPUT=$(npm run build 2>&1)
BUILD_EXIT=$?

if [ $BUILD_EXIT -eq 0 ]; then
  echo "빌드 성공"
  exit 0
fi

# 에러 분류
ERROR_TYPE=$(echo "$BUILD_OUTPUT" | claude --print \
  --output-format json \
  --max-turns 3 \
  "이 빌드 에러를 분류해줘. type 필드에 'type-error', 'import-error', 'syntax-error', 'other' 중 하나를 넣어서 JSON으로 출력해.")

TYPE=$(echo "$ERROR_TYPE" | jq -r '.type // "other"')

case "$TYPE" in
  "type-error")
    echo "$BUILD_OUTPUT" | claude --print \
      --dangerously-skip-permissions \
      --max-turns 15 \
      "타입 에러다. tsconfig.json 설정과 관련 타입 정의를 확인해서 수정해줘."
    ;;
  "import-error")
    echo "$BUILD_OUTPUT" | claude --print \
      --dangerously-skip-permissions \
      --max-turns 10 \
      "import 에러다. 경로가 잘못됐거나 모듈이 설치 안 된 거다. 확인해서 수정해줘."
    ;;
  *)
    echo "$BUILD_OUTPUT" | claude --print \
      --dangerously-skip-permissions \
      --max-turns 20 \
      "빌드 에러를 분석하고 수정해줘."
    ;;
esac
```

### 체이닝에서 자주 겪는 문제

**출력이 너무 길어서 다음 프롬프트가 터진다.** Claude Code의 출력이 만 자가 넘으면 다음 단계 프롬프트의 대부분을 이전 출력이 차지한다. 해결 방법:

```bash
# 출력을 JSON으로 받아서 핵심만 추출
RESULT=$(claude --print --output-format json ... | jq '.result | .[:5]')
```

**stdin과 프롬프트를 같이 넘길 때.** `--print` 모드에서 stdin과 위치 인자 프롬프트를 동시에 쓸 수 있다. stdin이 컨텍스트로 들어가고, 위치 인자가 지시사항이 된다.

```bash
cat error.log | claude --print "이 에러 분석해줘"
# stdin(error.log 내용)이 컨텍스트, "이 에러 분석해줘"가 프롬프트
```

---

## 6. 에러 전파와 복구

멀티 에이전트로 병렬 실행하면 일부가 실패하는 건 당연하다. 문제는 실패를 어떻게 감지하고 복구하느냐다.

### 기본 에러 처리 구조

```typescript
import { ClaudeCode } from "@anthropic-ai/claude-code";

interface TaskResult {
  name: string;
  success: boolean;
  output: string;
  retryCount: number;
}

async function runWithRetry(
  name: string,
  prompt: string,
  workDir: string,
  maxRetries: number = 2
): Promise<TaskResult> {
  const claude = new ClaudeCode({
    model: "claude-sonnet-4-6",
    maxTurns: 20,
    permissionMode: "dangerously-skip-permissions",
  });

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const result = await claude.run({
        prompt: attempt === 0
          ? prompt
          : `이전 시도가 실패했다. 에러: ${lastError}\n원래 요청: ${prompt}`,
        workingDirectory: workDir,
      });

      // 테스트 실행해서 실제로 성공인지 확인
      const verify = await claude.run({
        prompt: "npm test를 실행해서 결과만 알려줘. pass/fail로.",
        workingDirectory: workDir,
      });

      if (verify.output.toLowerCase().includes("fail")) {
        throw new Error(`테스트 실패: ${verify.output}`);
      }

      return { name, success: true, output: result.output, retryCount: attempt };
    } catch (err) {
      var lastError = String(err);
      console.warn(`[${name}] 시도 ${attempt + 1}/${maxRetries + 1} 실패: ${lastError}`);

      if (attempt === maxRetries) {
        return { name, success: false, output: lastError, retryCount: attempt };
      }
    }
  }

  return { name, success: false, output: "최대 재시도 초과", retryCount: maxRetries };
}
```

### 부분 실패 처리

5개 패키지 중 2개가 실패했을 때, 성공한 3개는 커밋하고 실패한 2개만 리포트하는 패턴이다.

```typescript
async function handlePartialFailure(results: TaskResult[]) {
  const succeeded = results.filter((r) => r.success);
  const failed = results.filter((r) => !r.success);

  // 성공한 작업은 커밋
  for (const result of succeeded) {
    console.log(`[성공] ${result.name} (시도 ${result.retryCount + 1}회)`);
  }

  // 실패한 작업은 이슈로 생성
  if (failed.length > 0) {
    const issueBody = failed
      .map((r) => `### ${r.name}\n\n에러:\n\`\`\`\n${r.output}\n\`\`\``)
      .join("\n\n");

    console.error(`[실패] ${failed.length}개 작업 실패:`);
    failed.forEach((r) => console.error(`  - ${r.name}: ${r.output.slice(0, 200)}`));

    // GitHub 이슈 생성 (선택)
    // gh issue create --title "자동화 실패: ..." --body "$issueBody"
  }

  return { succeeded: succeeded.length, failed: failed.length };
}
```

### 셸 스크립트에서의 에러 처리

```bash
#!/bin/bash
# scripts/safe-parallel.sh

LOG_DIR="./logs/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LOG_DIR"

run_task() {
  local name="$1"
  local prompt="$2"
  local log_file="${LOG_DIR}/${name}.log"

  claude --print --dangerously-skip-permissions --max-turns 20 "$prompt" \
    > "$log_file" 2>&1

  if [ $? -ne 0 ]; then
    echo "FAIL:${name}" >> "${LOG_DIR}/summary.txt"
    return 1
  else
    echo "PASS:${name}" >> "${LOG_DIR}/summary.txt"
    return 0
  fi
}

# 병렬 실행
run_task "auth-fix" "src/auth의 토큰 갱신 로직 수정해줘" &
run_task "payment-fix" "src/payment의 금액 계산 반올림 오류 수정해줘" &
run_task "noti-fix" "src/notification의 중복 발송 방지 로직 추가해줘" &

wait

# 결과 집계
echo "=== 실행 결과 ==="
if [ -f "${LOG_DIR}/summary.txt" ]; then
  PASS_COUNT=$(grep -c "^PASS:" "${LOG_DIR}/summary.txt" || echo 0)
  FAIL_COUNT=$(grep -c "^FAIL:" "${LOG_DIR}/summary.txt" || echo 0)
  echo "성공: ${PASS_COUNT}, 실패: ${FAIL_COUNT}"

  # 실패한 작업 로그 출력
  grep "^FAIL:" "${LOG_DIR}/summary.txt" | while IFS=: read _ name; do
    echo "--- ${name} 실패 로그 (마지막 20줄) ---"
    tail -20 "${LOG_DIR}/${name}.log"
  done
fi
```

재시도할 때 **이전 에러 메시지를 프롬프트에 포함**시키는 게 중요하다. "이전 시도가 실패했다"라고만 하면 Claude가 같은 실수를 반복하는 경우가 있다. 구체적인 에러 메시지를 넣어야 다른 접근을 시도한다.

---

## 7. Schedule + Remote Agent 야간 자동화

낮에는 개발하고, 밤에 Claude Code가 자동으로 유지보수 작업을 돌리는 구성이다. Schedule 기능으로 cron을 걸고, Remote Agent가 클라우드에서 실행한다.

### 야간 파이프라인 구성

```bash
# 매일 새벽 2시: 의존성 보안 스캔 + 자동 업데이트
claude schedule create \
  --cron "0 2 * * *" \
  --prompt "npm audit을 실행해서 취약점을 확인해줘. high 이상 취약점이 있으면 npm audit fix로 수정하고, 수정된 내용을 정리해서 PR을 만들어줘. PR 제목은 'chore: security patch YYYY-MM-DD' 형식으로."

# 매주 월요일 새벽 3시: 의존성 업데이트 체크
claude schedule create \
  --cron "0 3 * * 1" \
  --prompt "npx npm-check-updates로 업데이트 가능한 패키지를 확인해줘. major 업데이트는 제외하고 minor/patch만 업데이트해. npm test가 통과하면 PR을 만들어줘."

# 매일 새벽 4시: 코드 품질 리포트
claude schedule create \
  --cron "0 4 * * *" \
  --prompt "어제 머지된 PR들의 코드를 리뷰해줘. git log --since='1 day ago' --merges로 확인하고, 주요 변경사항에 대한 코드 품질 리포트를 GitHub Issue로 만들어줘."
```

### 이벤트 기반 트리거

cron뿐 아니라 GitHub 이벤트에 반응하는 패턴도 가능하다. GitHub Actions에서 Schedule을 트리거하는 방식이다.

```yaml
# .github/workflows/auto-triage.yml
name: Auto Triage Issues

on:
  issues:
    types: [opened]

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Claude Code
        run: npm install -g @anthropic-ai/claude-code

      - name: Analyze Issue
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          ISSUE_TITLE: ${{ github.event.issue.title }}
          ISSUE_BODY: ${{ github.event.issue.body }}
        run: |
          ANALYSIS=$(claude --print --max-turns 10 \
            "새 이슈가 등록됐다.
            제목: ${ISSUE_TITLE}
            내용: ${ISSUE_BODY}

            1. 관련 코드 파일을 찾아줘
            2. 원인을 추정해줘
            3. 수정 방향을 제안해줘
            결과를 마크다운으로 출력해.")

          gh issue comment "${{ github.event.issue.number }}" \
            --body "## 자동 분석 결과

          ${ANALYSIS}

          ---
          *이 분석은 Claude Code가 자동 생성했습니다. 참고용으로 활용하세요.*"
```

### 스케줄 관리

```bash
# 등록된 스케줄 목록 확인
claude schedule list

# 특정 스케줄 삭제
claude schedule delete --id <schedule-id>

# 스케줄을 수동으로 즉시 실행 (테스트용)
claude schedule run --id <schedule-id>
```

야간 자동화에서 조심할 것 두 가지:

1. **PR을 자동으로 머지하지 마라.** 생성까지만 자동화하고, 머지는 사람이 확인한다. 새벽에 자동 머지된 코드가 아침에 장애를 내면 원인 추적이 힘들다.
2. **`--max-turns`를 반드시 설정해라.** 사람이 안 보고 있는 시간에 Claude Code가 무한 루프에 빠지면 API 비용이 감당이 안 된다. 야간 작업은 10~20턴 정도로 제한하는 게 안전하다.

---

## 정리

오케스트레이션의 핵심은 **각 단계의 컨텍스트를 분리하면서 결과를 연결하는 것**이다. 하나의 Claude Code 세션에서 모든 걸 처리하면 컨텍스트가 터진다. Agent SDK로 인스턴스를 분리하든, 셸 스크립트로 `--print` 체이닝을 하든, 원리는 같다.

간단한 자동화는 셸 스크립트 체이닝으로 충분하다. 조건 분기나 에러 복구가 필요해지면 Agent SDK로 넘어가면 된다. 처음부터 복잡하게 짜지 말고, 수동으로 하던 반복 작업 하나를 자동화하는 것부터 시작하는 게 맞다.

---

## 참고

- [Claude Code 공식 문서](https://docs.anthropic.com/en/docs/claude-code)
- [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-code/sdk)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)
