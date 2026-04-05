---
title: Claude Code 트러블슈팅
tags: [ai, claude-code, troubleshooting, cli, debugging]
updated: 2026-04-05
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

**원인**: 같은 변수명, 같은 패턴의 코드가 반복되는 파일에서 발생한다. 특히 테스트 파일이나 설정 파일에서 자주 겪는다.

**해결 방법**:

- 주변 컨텍스트를 더 포함해서 `old_string`을 넓힌다. 수정 대상 줄만 넣지 말고, 위아래 2~3줄을 같이 넣어야 한다.
- 모든 인스턴스를 동일하게 바꿀 거면 `replace_all: true`를 쓴다.
- 그래도 안 되면 Write 도구로 파일 전체를 덮어쓰는 방법이 있는데, 파일이 크면 위험하다.

### 들여쓰기 불일치

Read 도구 출력에는 줄 번호 프리픽스가 붙는다. 이걸 복사해서 Edit에 넣으면 들여쓰기가 안 맞아서 실패한다.

```
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

**해결 방법**:

- `timeout` 파라미터를 명시적으로 설정한다. 최대 600초(10분)까지 가능하다.
- 오래 걸리는 명령은 `run_in_background: true`로 백그라운드 실행한다. 완료되면 알림이 온다.
- `sleep`으로 폴링하지 말 것. 백그라운드 실행 후 완료 알림을 기다리는 게 맞다.

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

## 3. MCP 연결 문제

### 서버 연결 끊김

MCP 서버가 갑자기 응답을 멈추거나 프로세스가 죽는 경우가 있다. 특히 장시간 세션에서 자주 발생한다.

**증상**: MCP 도구 호출 시 타임아웃, `EPIPE` 에러, 또는 아무 응답 없이 멈춤

**해결 방법**:

```bash
# MCP 서버 상태 확인
claude mcp list

# 특정 서버 재시작
claude mcp restart <server-name>

# 서버 로그 확인
claude mcp logs <server-name>
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

## 4. 훅(Hooks) 에러

### 훅이 작업을 차단하는 경우

커스텀 훅이 실패하면 Claude Code의 도구 실행이 중단된다. pre-commit 훅이 대표적이다.

```
Error: Hook failed with exit code 1
```

**흔한 원인들**:

- **린터/포매터 훅**: 코드 스타일 위반. Claude Code가 생성한 코드가 프로젝트의 ESLint, Prettier 설정과 안 맞는 경우
- **타입 체크 훅**: TypeScript strict 모드에서 any 타입 사용
- **파일 크기 제한 훅**: 대용량 파일 커밋 시도

**해결 방법**:

Claude Code에게 훅의 피드백을 반영해서 다시 시도하라고 하면 된다. `--no-verify`로 건너뛰는 건 근본 해결이 아니다.

```
# 나쁜 방법: 훅 우회
git commit --no-verify -m "bypass"

# 좋은 방법: 훅 피드백 확인 후 수정
# Claude Code에게 린터 에러를 보여주고 수정 요청
```

### settings.json의 hooks 설정

`settings.json`에서 커스텀 훅을 등록할 수 있다. 여기서 오타나 잘못된 경로를 넣으면 모든 도구 호출이 실패한다.

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

## 5. 권한 설정 꼬임

### 권한 모드 이해

Claude Code에는 세 가지 권한 모드가 있다:

- **Default**: 읽기 전용 도구는 자동 허용, 쓰기 도구는 매번 확인
- **Plan Mode**: 읽기 전용 도구만 허용, 수정 불가
- **YOLO Mode (dangerouslySkipPermissions)**: 모든 도구 자동 허용. 프로덕션 환경에서 절대 쓰지 말 것

### allowedTools 설정 충돌

`settings.json`에서 `allowedTools`를 설정했는데 기대한 대로 동작하지 않는 경우가 있다.

```json
{
  "permissions": {
    "allowedTools": ["Read", "Glob", "Grep"],
    "deniedTools": ["Bash"]
  }
}
```

**주의할 점**:

- `allowedTools`에 넣었어도 MCP 도구는 별도로 허용해야 한다. MCP 도구명은 `mcp__서버명__도구명` 형식이다.
- 글로벌 설정과 프로젝트 설정이 충돌하면, 더 제한적인 쪽이 적용된다.
- `deniedTools`가 `allowedTools`보다 우선한다.

### 파일 시스템 권한 문제

Claude Code가 파일을 수정할 권한이 없을 때 발생한다. Docker 컨테이너 안에서 실행할 때 자주 겪는다.

```bash
# 파일 소유자 확인
ls -la target-file.js

# 현재 사용자 확인
whoami
```

---

## 6. API 키 및 인증 문제

### API 키 인식 실패

```
Error: Invalid API key provided
```

**확인 순서**:

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

## 7. Worktree 문제

### Worktree 충돌

Agent 도구에서 `isolation: "worktree"`를 쓰면 임시 Git worktree를 만든다. 이미 같은 브랜치에 worktree가 존재하면 충돌이 발생한다.

```
fatal: 'path/to/worktree' is already checked out at 'another/path'
```

**해결 방법**:

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

## 8. CI/CD 환경에서의 헤드리스 모드

### 비대화형 모드 설정

CI 환경에서는 사용자 입력을 받을 수 없다. `-p` 플래그로 프롬프트를 전달하고 `--no-input` 또는 비대화형 옵션을 사용해야 한다.

```bash
# CI에서 실행
claude -p "Run tests and report results" --output-format json
```

### CI에서 자주 발생하는 문제들

**1. TTY 없음 에러**

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

**2. Git 설정 누락**

CI 러너에 Git user.name, user.email이 설정되지 않으면 커밋 관련 작업이 실패한다.

```yaml
# GitHub Actions 예시
- name: Configure Git
  run: |
    git config --global user.name "CI Bot"
    git config --global user.email "ci@example.com"
```

**3. 타임아웃**

CI에서 Claude Code가 오래 생각하면 CI 자체 타임아웃에 걸린다. `max_turns` 옵션으로 대화 턴 수를 제한하거나, CI의 타임아웃을 넉넉하게 잡아야 한다.

```bash
# 최대 턴 수 제한
claude -p "Fix lint errors" --max-turns 10
```

---

## 9. 컨텍스트 윈도우 관리

### 컨텍스트 폭발

대용량 파일을 읽거나, 많은 파일을 탐색하면 컨텍스트 윈도우가 빠르게 차버린다. 컨텍스트가 한계에 도달하면 이전 메시지가 자동 압축되고, 중요한 정보가 손실될 수 있다.

**증상**:

- 앞에서 논의한 내용을 갑자기 모르겠다고 하는 경우
- 같은 파일을 반복해서 읽는 경우
- 응답 품질이 갑자기 떨어지는 경우

**대응 방법**:

- Read 도구에서 `offset`과 `limit`을 사용해서 필요한 부분만 읽는다.
- 탐색 작업은 Agent 도구에 위임한다. 서브에이전트는 별도 컨텍스트를 사용한다.
- `/compact` 명령으로 수동 압축하면 핵심 내용만 남길 수 있다.

```bash
# 파일의 특정 부분만 읽기
# Read 도구에서 offset: 100, limit: 50 으로 100~150번 줄만 읽음
```

### CLAUDE.md가 너무 클 때

`CLAUDE.md` 파일은 매 대화 시작 시 컨텍스트에 로드된다. 여기에 너무 많은 내용을 넣으면 실제 작업에 쓸 컨텍스트가 줄어든다.

- `CLAUDE.md`는 간결하게 유지한다. 500줄 이하가 적당하다.
- 상세한 가이드는 별도 파일에 두고, 필요할 때 읽도록 `CLAUDE.md`에 경로만 적는다.
- 여러 `CLAUDE.md` 파일(프로젝트 루트, 하위 디렉토리별)로 분리하면 해당 디렉토리 작업 시에만 로드된다.

---

## 10. 기타 자주 겪는 문제들

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

- `.gitignore`에 `node_modules`, `dist`, `build` 등을 넣어두면 검색에서 제외된다.
- Grep의 `glob` 파라미터로 검색 범위를 좁힌다: `glob: "src/**/*.ts"`
- `git status`에 `-uall` 플래그를 쓰면 대규모 레포에서 메모리 문제가 발생한다. 절대 쓰지 말 것.

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
