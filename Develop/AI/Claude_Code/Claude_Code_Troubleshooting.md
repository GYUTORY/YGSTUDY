---
title: Claude Code 트러블슈팅
tags: [ai, devops, mcp]
updated: 2026-09-12
volatility: high
---

# Claude Code 트러블슈팅

Claude Code를 실무에서 쓰다 보면 생각보다 다양한 문제에 부딪힌다. 공식 문서에는 나오지 않는, 실제로 겪어봐야 아는 문제들을 정리했다.

---

## 1. Edit 도구 충돌

### old_string이 고유하지 않아서 실패

Edit 도구는 `old_string`이 파일 내에서 유일해야 동작한다. 동일한 문자열이 여러 곳에 있으면 실패한다.

```
Error: old_string is not unique in the file.
Either provide a larger string with more surrounding context to make it unique
or use replace_all to change every instance.
```

같은 변수명, 같은 패턴의 코드가 반복되는 파일에서 발생한다. 특히 테스트 파일이나 설정 파일에서 자주 겪는다.

수정 대상 줄만 `old_string`으로 넣지 말고, 위아래 2~3줄을 같이 포함해서 고유성을 확보해야 한다. 모든 인스턴스를 동일하게 바꿀 거면 `replace_all: true`를 쓴다. 그래도 안 되면 Write 도구로 파일 전체를 덮어쓰는 방법이 있는데, 파일이 크면 위험하다.

### 들여쓰기 불일치

Read 도구 출력에는 줄 번호 프리픽스가 붙는다. 이걸 복사해서 Edit에 넣으면 들여쓰기가 안 맞아서 실패한다.

```bash
# Read 출력 (줄번호 + 탭 + 내용)
42	    const result = await fetch(url);

# Edit에 넣을 때는 줄번호 제거 후 넣어야 함
    const result = await fetch(url);
```

탭과 스페이스가 섞인 파일에서도 같은 문제가 발생한다. `.editorconfig`나 IDE 설정을 확인해야 한다.

---

## 2. Bash 도구 타임아웃

### 기본 타임아웃은 2분

Bash 도구의 기본 타임아웃은 120초(2분)다. 빌드, 테스트, 대규모 마이그레이션 같은 작업에서 자주 걸린다.

```
Error: Command timed out after 120000ms
```

`timeout` 파라미터를 명시적으로 설정한다. 최대 600초(10분)까지 가능하다. 오래 걸리는 명령은 `run_in_background: true`로 백그라운드 실행한다. 완료되면 알림이 온다. `sleep`으로 폴링하지 말 것 — 백그라운드 실행 후 완료 알림을 기다리는 게 맞다.

### Shell 상태가 유지되지 않음

각 Bash 호출 사이에 shell 상태(환경 변수, alias 등)가 유지되지 않는다. 작업 디렉토리는 유지된다.

```bash
# 이렇게 하면 두 번째 명령에서 MY_VAR이 없다
# 첫 번째 호출
export MY_VAR=hello

# 두 번째 호출
echo $MY_VAR  # 빈 값
```

한 번의 Bash 호출에서 `&&`로 연결하거나, 필요한 환경 변수를 매번 설정해야 한다.

```bash
export MY_VAR=hello && echo $MY_VAR
```

---

## 3. 컨텍스트 윈도우 초과

### 증상을 보고 판단하는 법

세션이 길어지면 Claude Code가 대화 히스토리를 자동으로 압축한다. 언제 압축이 일어났는지 명확하게 알려주지는 않는다. 간접 신호가 세 가지 있다.

**같은 파일을 반복해서 읽는다.** 100줄짜리 설정 파일을 한 세션에서 세 번 Read한 걸 실제로 본 적 있다. 압축되면서 파일 내용이 날아갔기 때문이다.

**앞에서 내린 결정을 틀리게 기억한다.** "A 방식으로 구현하기로 했잖아요"라고 해도 다른 세부사항으로 응답하거나 "그건 기억나지 않는다"는 반응이 나온다.

**응답이 추상적으로 바뀐다.** 구체적인 파일명, 함수명, 라인 번호 대신 "적절한 위치에 추가하세요" 같은 답이 나오기 시작하면 컨텍스트가 많이 날아간 거다.

### 자동 압축과 `/compact`

Claude Code는 컨텍스트가 임계값을 넘으면 이전 대화를 요약본으로 교체한다. 이 과정에서 도구 호출 결과, 파일 내용, 중간 결정 사항이 모두 요약본으로 대체된다.

`/compact` 명령으로 수동 트리거하면 타이밍을 직접 통제할 수 있다. 한 기능 구현을 마쳤고 다음 기능으로 넘어가기 전에 압축하면, 불필요한 중간 과정 없이 완료된 상태만 요약에 남는다.

```
/compact
```

자동 압축보다 수동 압축이 낫다. 자동 압축은 컨텍스트가 꽉 찬 직후에 일어나서, 요약 시점에 작업이 절반쯤 진행 중인 경우가 많다. 수동으로 자연스러운 완료 지점에서 압축하면 다음 작업을 깔끔하게 시작할 수 있다.

### 대규모 작업을 세션 단위로 쪼개는 법

컨텍스트 부족으로 작업이 중단되는 걸 막으려면 태스크를 세션 단위로 미리 쪼개야 한다.

CLAUDE.md에 현재 상태를 기록하는 습관이 필요하다. "auth 모듈 완료, payment 모듈 다음" 같은 식으로 남겨두면 새 세션을 열어도 이어서 진행할 수 있다. 상세한 작업 맥락은 CLAUDE.md 대신 별도 파일에 두고 필요할 때 읽는 방식이 낫다. CLAUDE.md가 너무 커지면 매 세션 시작마다 컨텍스트를 소비한다.

서브에이전트를 쓰는 방법도 있다. Agent 도구는 별도 컨텍스트 윈도우를 사용하므로, 파일 탐색이나 정보 수집 같은 작업을 서브에이전트에 위임하면 메인 컨텍스트를 아낄 수 있다.

### CLAUDE.md 크기 관리

`CLAUDE.md` 파일은 매 대화 시작 시 컨텍스트에 로드된다. 여기에 너무 많은 내용을 넣으면 실제 작업에 쓸 컨텍스트가 줄어든다.

500줄 이하로 유지하는 걸 목표로 한다. 상세한 내용은 별도 파일에 두고, 필요할 때 읽도록 `CLAUDE.md`에 경로만 적는다. 여러 `CLAUDE.md` 파일(프로젝트 루트, 하위 디렉토리별)로 분리하면 해당 디렉토리 작업 시에만 로드된다.

---

## 4. Tool Permission 거부 패턴

### 세 가지 실행 결과

도구 호출은 세 가지 중 하나의 결과가 된다.

**자동 허용**: Read, Glob, Grep, TodoRead 등 읽기 전용 도구. 기본 설정에서 확인 없이 바로 실행된다.

**사용자 확인**: Edit, Write, Bash, git 명령 등 상태를 바꾸는 도구. 실행 전에 사용자 확인이 필요하다.

**자동 거부 또는 경고**: 파괴적이거나 복구 불가능한 결과를 낳는 명령. `rm -rf`, `git push --force`, `git reset --hard`, SQL `DROP TABLE` 등. 이 명령들은 `allowedTools`에 Bash를 추가해도 별도 확인이 뜬다.

### 도구 레벨 거부 vs 모델 레벨 거부

거부가 어디서 왔는지에 따라 해결 방법이 다르다.

```
# 도구 레벨 거부 — settings.json으로 해결 가능
Tool call blocked by permission settings

# 모델 레벨 거부 — settings.json으로 해결 안 됨
I don't feel comfortable executing that command because...
```

모델 레벨 거부는 Claude 자체가 위험하다고 판단한 경우다. 이 경우 settings.json을 아무리 바꿔도 소용없고, 명령어를 다른 방식으로 바꾸거나 목적을 설명해야 한다.

### MCP 도구 허용

MCP 도구는 기본적으로 모두 확인이 필요하다. `allowedTools`에 추가하려면 도구명을 정확히 써야 한다.

```json
{
  "permissions": {
    "allowedTools": [
      "mcp__filesystem__read_file",
      "mcp__github__create_issue"
    ]
  }
}
```

도구명은 `mcp__<서버명>__<도구명>` 형식이다. 서버명은 `claude mcp list`로 확인한다.

### allowedTools 설정 충돌

```json
{
  "permissions": {
    "allowedTools": ["Read", "Glob", "Grep"],
    "deniedTools": ["Bash"]
  }
}
```

주의할 점이 있다. `deniedTools`가 `allowedTools`보다 우선한다. 글로벌 설정과 프로젝트 설정이 충돌하면 더 제한적인 쪽이 적용된다. `allowedTools`에 넣었어도 MCP 도구는 별도로 허용해야 한다.

### 연속 거부 시 진단

같은 도구가 계속 거부될 때는 이 순서로 확인한다.

```bash
# deniedTools에 등록됐는지 확인
cat .claude/settings.json | grep -A 10 deniedTools

# 글로벌 설정에서 막고 있는지 확인
cat ~/.claude/settings.json | grep -A 10 deniedTools
```

훅이 차단하는지도 확인해야 한다. 훅 스크립트의 종료 코드가 0이 아니면 해당 도구 호출이 막힌다.

### 파일 시스템 권한 문제

Claude Code가 파일을 수정할 권한이 없을 때 발생한다. Docker 컨테이너 안에서 실행할 때 자주 겪는다.

```bash
# 파일 소유자 확인
ls -la target-file.js

# 현재 사용자 확인
whoami
```

---

## 5. 반복 루프 탈출

### 루프 유형과 신호

Claude Code가 루프에 빠지는 패턴은 크게 세 가지다.

**탐색 루프**: 파일이나 함수를 찾는데 계속 실패한다. Grep으로 찾고, 다른 패턴으로 Grep하고, Glob으로 찾고, 또 다른 Grep을 시도한다. 5회 이상 찾기를 시도했는데 못 찾고 있다면 전제가 잘못된 거다.

**수정 루프**: 코드를 고치고 테스트하면 다른 에러가 나고, 그걸 고치면 처음 에러가 돌아오는 패턴. 두 부분 간의 가정 불일치가 원인인 경우가 많다.

**Edit 실패 루프**: `old_string`이 매칭이 안 되는데 비슷한 문자열로 계속 시도하는 패턴. 파일이 Read 이후 변경됐거나, 줄번호 프리픽스가 섞여 들어간 경우다. 컨텍스트 압축으로 파일 내용이 날아간 경우에도 발생한다.

### 탈출 방법

**탐색 루프**: 직접 경로를 알려준다. "찾는 걸 그만하고 경로를 알려줄게. `src/auth/middleware/jwt.ts` 이 파일이다." 그 다음 Claude가 해당 파일을 Read하도록 유도한다.

**수정 루프**: `/compact` 후 문제를 다시 설명한다. 이번엔 증상 대신 근본 원인에 대한 가설을 직접 제시한다. "TokenService가 stateless인데 JwtGuard가 state를 기대하는 게 문제다. 이 인터페이스 불일치를 해결해라."

**Edit 실패 루프**: Claude에게 파일을 Read하게 한 다음, 수정할 부분의 정확한 텍스트를 확인하고 그걸 `old_string`으로 쓰라고 지시한다. Read 출력을 직접 복사해서 주기보다 Claude가 직접 읽게 하는 게 낫다 - 줄번호 프리픽스 처리를 Claude 쪽에서 하게 되니까.

**공통 탈출**: Ctrl+C로 현재 작업을 중단한다. 그 다음 지금까지 어떤 방법을 시도했고 왜 실패했는지 명시적으로 알려준다.

```
지금 동일한 방법을 네 번 반복했다.
그 방법으로는 해결이 안 된다.
왜 그 방법이 실패하는지 먼저 분석하고, 완전히 다른 접근법을 제안해라.
```

Plan Mode로 전환하는 것도 효과가 있다. 실행 전에 계획을 작성하게 하면 같은 실패를 반복하는 걸 막을 수 있다.

### `/clear` vs `/compact`

루프를 탈출할 때 두 명령의 차이를 이해해야 한다.

`/compact`는 대화 히스토리를 요약본으로 교체한다. 지금까지의 작업 맥락은 유지되면서 컨텍스트를 확보한다. 루프에 빠졌지만 지금까지의 작업 결과는 유지해야 할 때 쓴다.

`/clear`는 대화 히스토리를 완전히 날린다. 완전히 다른 방향으로 접근하고 싶을 때 쓴다. 단, 지금까지의 작업 결과도 컨텍스트에서 사라지므로, 파일에 커밋하지 않은 중간 결과가 있으면 먼저 저장해야 한다.

---

## 6. MCP 연결 문제

### 서버 연결 끊김

MCP 서버가 갑자기 응답을 멈추거나 프로세스가 죽는 경우가 있다. 특히 장시간 세션에서 자주 발생한다.

**증상**: MCP 도구 호출 시 타임아웃, `EPIPE` 에러, 또는 아무 응답 없이 멈춤

```bash
# MCP 서버 상태 확인
claude mcp list

# 특정 서버 설정 확인
claude mcp get <server-name>

# 서버를 지웠다 다시 등록 (재시작 명령은 없다)
claude mcp remove <server-name>
claude mcp add <server-name> <command> [args...]
```

### stdio vs SSE 선택 기준

- **stdio**: 로컬에서 돌리는 서버에 적합. 프로세스를 Claude Code가 직접 관리한다.
- **SSE (Server-Sent Events)**: 원격 서버나 공유 서버에 적합. URL로 연결한다.

stdio 방식은 Claude Code 세션이 끝나면 서버 프로세스도 같이 죽는다. 다른 클라이언트와 공유할 MCP 서버라면 SSE를 써야 한다.

### MCP 설정 파일 위치와 우선순위

```
~/.claude/settings.json          # 글로벌 (모든 프로젝트)
.claude/settings.json             # 프로젝트 레벨 (Git에 포함)
.claude/settings.local.json       # 프로젝트 레벨 (Git에서 제외)
```

같은 이름의 MCP 서버가 여러 레벨에 정의되면, 더 구체적인 설정이 우선한다. 프로젝트 레벨이 글로벌보다 우선.

---

## 7. 훅(Hooks) 에러

### 훅이 작업을 차단하는 경우

커스텀 훅이 실패하면 Claude Code의 도구 실행이 중단된다. pre-commit 훅이 대표적이다.

```
Error: Hook failed with exit code 1
```

흔한 원인들:

- **린터/포매터 훅**: 코드 스타일 위반. Claude Code가 생성한 코드가 프로젝트의 ESLint, Prettier 설정과 안 맞는 경우
- **타입 체크 훅**: TypeScript strict 모드에서 any 타입 사용
- **파일 크기 제한 훅**: 대용량 파일 커밋 시도

Claude Code에게 훅의 피드백을 반영해서 다시 시도하라고 하면 된다. `--no-verify`로 건너뛰는 건 근본 해결이 아니다.

```
# 나쁜 방법: 훅 우회
git commit --no-verify -m "bypass"

# 좋은 방법: 훅 피드백 확인 후 수정
# Claude Code에게 린터 에러를 보여주고 수정 요청
```

### settings.json의 hooks 설정

`settings.json`에서 커스텀 훅을 등록할 수 있다. 오타나 잘못된 경로를 넣으면 모든 도구 호출이 실패한다.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit",
        "command": "/path/to/validation-script.sh $TOOL_INPUT"
      }
    ]
  }
}
```

`command`에 지정한 스크립트가 존재하지 않거나 실행 권한이 없으면 도구 호출이 전부 막힌다. 훅 등록 전에 스크립트 경로와 권한을 확인해야 한다.

```bash
# 실행 권한 확인 및 부여
chmod +x /path/to/validation-script.sh
```

---

## 8. API 키 및 인증 문제

### API 키 인식 실패

```
Error: Invalid API key provided
```

확인 순서:

1. 환경 변수 확인: `echo $ANTHROPIC_API_KEY`
2. 키 형식 확인: `sk-ant-`로 시작해야 한다
3. 키 만료 여부: Anthropic Console에서 확인
4. 조직 설정: 팀/조직 API 키는 별도 설정이 필요할 수 있다

```bash
# 환경 변수로 설정
export ANTHROPIC_API_KEY=sk-ant-xxxxx

# 또는 로그인으로 인증
claude login
```

### Max 구독 vs API 사용량

Claude Max 구독(Pro/Team/Enterprise)과 API 직접 사용은 인증 방식이 다르다.

- **Max 구독**: `claude login`으로 OAuth 인증. 사용량 제한이 있다.
- **API 키**: `ANTHROPIC_API_KEY` 환경 변수. 사용한 만큼 과금된다.

Max 구독에서 사용량 한도에 걸리면 응답이 느려지거나 거부된다. 대량 작업 시 API 키 방식이 예측 가능하다.

### 프록시/VPN 환경

회사 프록시나 VPN 뒤에서 연결이 안 되는 경우:

```bash
# 프록시 설정
export HTTPS_PROXY=http://proxy.company.com:8080
export HTTP_PROXY=http://proxy.company.com:8080

# 인증서 문제 시
export NODE_EXTRA_CA_CERTS=/path/to/company-ca.pem
```

자체 서명 인증서를 쓰는 회사 네트워크에서는 `NODE_EXTRA_CA_CERTS`를 설정하지 않으면 `UNABLE_TO_VERIFY_LEAF_SIGNATURE` 에러가 난다.

---

## 9. Worktree 문제

### Worktree 충돌

Agent 도구에서 `isolation: "worktree"`를 쓰면 임시 Git worktree를 만든다. 이미 같은 브랜치에 worktree가 존재하면 충돌이 발생한다.

```
fatal: 'path/to/worktree' is already checked out at 'another/path'
```

```bash
# 기존 worktree 목록 확인
git worktree list

# 사용하지 않는 worktree 제거
git worktree remove /path/to/stale-worktree

# 강제 제거 (잠긴 worktree)
git worktree remove --force /path/to/locked-worktree
```

### Worktree에서 변경사항 유실

Agent가 worktree에서 작업을 완료했는데, 변경사항을 메인 작업 디렉토리로 가져오지 않는 경우가 있다. Agent의 결과에 worktree 경로와 브랜치명이 포함되어 있으니, 그걸 확인해서 수동으로 merge하거나 cherry-pick해야 한다.

```bash
# Agent가 반환한 브랜치에서 변경사항 가져오기
git merge <agent-branch-name>

# 또는 특정 커밋만
git cherry-pick <commit-hash>
```

---

## 10. CI/CD 환경에서의 헤드리스 모드

### 비대화형 모드 설정

CI 환경에서는 사용자 입력을 받을 수 없다. `-p` 플래그로 프롬프트를 전달해야 한다.

```bash
# CI에서 실행
claude -p "Run tests and report results" --output-format json
```

### CI에서 자주 발생하는 문제들

**TTY 없음 에러**

```
Error: Cannot prompt for user input in non-interactive mode
```

권한 확인이 필요한 도구를 호출할 때 발생한다. CI에서는 `dangerouslySkipPermissions`를 쓰거나, 필요한 도구를 미리 `allowedTools`에 등록해야 한다.

```json
// .claude/settings.json
{
  "permissions": {
    "allowedTools": ["Read", "Glob", "Grep", "Bash"]
  }
}
```

**Git 설정 누락**

CI 러너에 Git user.name, user.email이 설정되지 않으면 커밋 관련 작업이 실패한다.

```yaml
# GitHub Actions 예시
- name: Configure Git
  run: |
    git config --global user.name "CI Bot"
    git config --global user.email "ci@example.com"
```

**타임아웃**

CI에서 Claude Code가 오래 생각하면 CI 자체 타임아웃에 걸린다. `max_turns` 옵션으로 대화 턴 수를 제한하거나, CI의 타임아웃을 넉넉하게 잡아야 한다.

```bash
# 최대 턴 수 제한
claude -p "Fix lint errors" --max-turns 10
```

---

## 11. 오류 메시지별 해결 흐름

자주 나오는 오류와 어디서 원인을 찾을지 정리한다.

| 오류 메시지 | 원인 | 해결 |
|---|---|---|
| `old_string is not unique in the file` | Edit 대상 문자열 중복 | 컨텍스트를 넓히거나 `replace_all` 사용 (§1) |
| `Command timed out after 120000ms` | Bash 기본 타임아웃 초과 | `timeout: 600000` 설정 또는 background 실행 (§2) |
| `Cannot prompt for user input in non-interactive mode` | CI에서 권한 확인 필요한 도구 호출 | `allowedTools`에 필요한 도구 사전 등록 (§10) |
| `Invalid API key provided` | API 키 없거나 형식 오류 | `ANTHROPIC_API_KEY` 확인, `sk-ant-` 접두어 확인 (§8) |
| `fatal: '...' is already checked out` | Worktree 브랜치 충돌 | `git worktree list` 확인 후 stale worktree 제거 (§9) |
| `EPIPE` | MCP 서버 프로세스 종료 | `claude mcp remove` → `claude mcp add` 재등록 (§6) |
| `Hook failed with exit code 1` | pre-commit 또는 커스텀 훅 실패 | 훅 스크립트 직접 실행해서 에러 확인 (§7) |
| `UNABLE_TO_VERIFY_LEAF_SIGNATURE` | 회사 프록시 인증서 문제 | `NODE_EXTRA_CA_CERTS`에 CA 인증서 경로 설정 (§8) |
| `Tool call blocked by permission settings` | `deniedTools` 등록 또는 설정 충돌 | `settings.json` 확인 (§4) |
| `I don't feel comfortable executing...` | 모델 레벨 거부 | `settings.json`으로 해결 안 됨. 명령 방식을 바꾸거나 목적 설명 (§4) |

---

## 12. 기타 자주 겪는 문제들

### Node.js 버전 호환성

Claude Code는 Node.js 18 이상이 필요하다. nvm으로 버전을 관리하는 환경에서, 터미널을 열 때마다 다른 버전이 활성화되면 문제가 생긴다.

```bash
# 현재 노드 버전 확인
node -v

# nvm으로 고정
nvm alias default 20
```

### 대용량 레포지토리에서 느림

파일이 수만 개인 모노레포에서 Glob이나 Grep이 느려지는 경우가 있다.

`.gitignore`에 `node_modules`, `dist`, `build` 등을 넣어두면 검색에서 제외된다. Grep의 `glob` 파라미터로 검색 범위를 좁힌다: `glob: "src/**/*.ts"`. `git status`에 `-uall` 플래그를 쓰면 대규모 레포에서 메모리 문제가 발생한다. 절대 쓰지 말 것.

### 네트워크 끊김 시 동작

API 호출 중 네트워크가 끊기면 현재 작업이 중단된다. 로컬 파일 변경은 이미 반영된 상태일 수 있으니, 네트워크 복구 후 `git diff`로 변경사항을 확인해야 한다.

```bash
# 네트워크 복구 후 확인
git diff
git status
```

중간에 끊긴 Edit이 파일을 깨뜨린 경우:

```bash
# 마지막 커밋 상태로 특정 파일 복구
git checkout -- path/to/broken-file.js
```

### 멀티 세션 충돌

같은 프로젝트에서 Claude Code 세션을 여러 개 열면, 동시에 같은 파일을 수정하면서 충돌이 발생할 수 있다. 한 세션이 Edit으로 바꾼 내용을 다른 세션이 덮어쓰는 식이다.

한 프로젝트에는 하나의 세션만 사용하거나, 서로 다른 파일을 다루도록 분리해야 한다. Worktree 격리를 쓰면 파일 충돌을 피할 수 있다.
