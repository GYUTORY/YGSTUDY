---
title: Claude Code Fable 5 릴리스 정리
tags: [ai, claude-code, fable-5, release, upgrade]
updated: 2026-06-10
---

# Claude Code Fable 5 릴리스 정리

Claude Code는 정기적으로 코드네임이 붙은 릴리스를 낸다. Fable 4까지는 모델 교체와 Skill 시스템 도입이 주된 변화였고, Fable 5는 그 위에서 워크플로 도구들을 한 번에 정리한 릴리스다. 평소처럼 `claude --version`만 보고 마이너 업데이트인 줄 알고 넘어가면 며칠 뒤 `.claude/settings.json`이 깨지거나, 항상 켜두던 hook가 조용히 무시되는 상황을 만난다. 한 번 겪고 나면 릴리스 노트를 안 보고 올리지 못한다.

이 문서는 Fable 5로 올렸을 때 실제로 부딪힌 변화와 마이그레이션 과정에서 챙겨야 할 항목을 정리한다. 릴리스 노트의 전체 항목을 옮기기보다는 백엔드 개발자가 매일 쓰는 영역 — CLI 옵션, 슬래시 커맨드, 모델 설정, hook 호환성, Plan/Auto/Worktree/Skill 상호작용 — 위주로 다룬다.

---

## 1. 코드네임 Fable 5가 가리키는 것

Fable은 Claude Code의 메이저 트랙 코드네임이다. 1부터 5까지 올라오는 동안 트랙의 성격이 조금씩 달라졌다.

- Fable 1~2: 초기 TUI와 기본 도구 셋(Read/Edit/Bash/Glob/Grep) 안정화
- Fable 3: Skill 시스템과 `.claude/skills/` 디렉터리 표준화
- Fable 4: Agent 도구와 Workflow 도구 도입, 모델별 토큰 회계 분리
- Fable 5: 위 도구들을 묶는 세션 단위 동작 정리 — Plan/Auto/Worktree/Skill의 상호 의존 관계 명시, 권한 모델 재정의

릴리스 번호는 단순 버전이라기보다 "어떤 추상화 층을 손봤는지"를 알려주는 신호로 쓰는 게 정확하다. Fable 5는 도구를 새로 추가하지 않는 대신 기존 도구들이 서로를 어떻게 호출하는지를 명시화했다. 그래서 사용자가 직접 만지는 표면은 크게 늘지 않았는데, 그 안쪽 동작 가정이 바뀌어서 기존 설정 파일과 충돌하는 사례가 가장 많다.

설치된 버전과 트랙은 다음으로 확인한다.

```bash
claude --version
# claude 5.0.x  (track: fable-5)

claude config get release.track
# fable-5
```

`release.track` 값이 `fable-4`로 남아 있는데 바이너리가 5.x라면 마이그레이션이 절반만 끝난 상태다. 이 경우 캐시 디렉터리가 옛 스키마로 남아 있어서 슬래시 커맨드 일부가 등록되지 않는다.

---

## 2. Fable 4 대비 바뀐 점

### 2.1 권한 모델 재정의

Fable 4까지의 `permissions.allow`/`permissions.deny`는 평탄한 문자열 리스트였다. Fable 5에서는 도구별 스코프가 명시되어, Bash와 MCP 도구가 같은 키 공간을 공유하지 않는다.

```json
{
  "permissions": {
    "allow": {
      "Bash": ["npm test:*", "git status", "git diff:*"],
      "Mcp": ["mcp__github__*"],
      "WebFetch": ["domain:docs.anthropic.com"]
    },
    "deny": {
      "Bash": ["rm -rf:*", "git push --force:*"]
    }
  }
}
```

Fable 4 스타일의 평탄한 리스트도 한동안 읽히기는 한다. 다만 새 키 형식이 우선하고, 동일 도구에 대해 평탄 리스트와 중첩 리스트가 모두 있으면 중첩 쪽만 적용된다. 이 우선순위를 모르면 "분명히 deny에 넣었는데 왜 통과되지" 같은 상황이 생긴다.

### 2.2 모델 라우팅 분리

Fable 4는 메인 루프와 서브에이전트가 별도 모델 키를 가졌다. Fable 5는 여기에 "phase" 단위가 추가되어, Workflow 스크립트 안의 `phase()`마다 모델을 다르게 지정할 수 있다.

```json
{
  "model": {
    "main": "claude-opus-4-7",
    "subagent": "claude-sonnet-4-6",
    "phases": {
      "Review": "claude-opus-4-7",
      "Verify": "claude-haiku-4-5-20251001"
    }
  }
}
```

phases 키가 정의되지 않으면 subagent 모델을 그대로 쓴다. 비용 관리할 때 verify 단계만 Haiku로 내리는 식으로 쓰면 효과가 크다.

### 2.3 컨텍스트 윈도우 기본값

Fable 4 기본은 200k였다. Fable 5는 Opus 4.7 모델을 메인 루프에 두면 자동으로 1M 컨텍스트로 시작한다. 사용량이 늘어나니 비용 알림 임계치를 따로 잡지 않으면 한 세션에 평소의 5배가 청구된다. `claude config set context.warn 300000` 정도로 경고선을 잡아두는 게 안전하다.

---

## 3. 새 CLI 옵션과 슬래시 커맨드

### 3.1 CLI 옵션

Fable 5에서 추가된 CLI 옵션 중 실무에서 자주 쓰는 것들이다.

```bash
# 세션 시작 시 특정 스킬만 로드 (큰 .claude/skills/ 디렉터리에서 유용)
claude --skills "code-review,verify"

# 권한 모드를 세션 시작 시점에 잠금
claude --permission-mode acceptEdits

# 특정 워크트리에서 격리된 세션 시작
claude --worktree-base /tmp/cc-worktrees

# 모델을 phase 단위로 오버라이드
claude --phase-model "Verify=claude-haiku-4-5-20251001"
```

`--permission-mode`는 Fable 4의 `--dangerously-skip-permissions`를 일부 대체한다. Fable 5는 이 플래그를 deprecation 경고와 함께 여전히 받아주지만, 다음 메이저에서 사라진다고 명시되어 있다. CI에서 `--dangerously-skip-permissions`로 돌리고 있다면 `--permission-mode bypassPermissions`로 바꿔두는 편이 낫다.

### 3.2 슬래시 커맨드

`/auto`, `/plan`, `/loop`처럼 기존 슬래시 커맨드는 그대로다. Fable 5에서 새로 들어오거나 동작이 바뀐 것들은 다음과 같다.

- `/budget` — 현재 세션의 토큰 사용량과 한도를 보여준다. Workflow 안의 `budget.spent()`와 같은 풀을 본다.
- `/phase-model <name>=<model>` — 세션 진행 중에 특정 phase 모델을 교체한다.
- `/skill list` — 로드된 스킬 목록을 보여준다. Fable 4에선 `/skills`였는데 명사 단수형으로 통일됐다.
- `/worktree status` — 현재 세션이 워크트리 안인지, 어느 베이스 브랜치에서 분기됐는지 표시한다.

`/skills`를 그대로 치면 Fable 5에선 "Unknown command. Did you mean `/skill list`?"가 뜬다. 자동완성에 익숙해진 손가락이 자주 틀린다.

---

## 4. 기본 모델과 컨텍스트 윈도우

Fable 5의 기본 모델 구성은 다음과 같다.

| 슬롯 | Fable 4 기본 | Fable 5 기본 |
|---|---|---|
| Main loop | Sonnet 4.5 | Opus 4.7 (1M) |
| Subagent | Haiku 4.5 | Sonnet 4.6 |
| Plan phase | Sonnet 4.5 | Opus 4.7 |
| Verify phase | Sonnet 4.5 | Haiku 4.5 |

Main loop가 Opus로 올라간 게 가장 큰 비용 변화다. 평소 워크플로가 "메인 루프에서 가볍게 질문 던지기" 위주였다면 Fable 5 기본값은 과하다. `claude config set model.main claude-sonnet-4-6`으로 내려두고 필요할 때만 `/model claude-opus-4-7`로 올려 쓰는 패턴이 비용 관리에 유리하다.

컨텍스트 윈도우 1M은 자동으로 활성화되지만 한 가지 함정이 있다. Anthropic 프롬프트 캐시 TTL은 여전히 5분이다. 1M 윈도우라도 5분 안에 다음 호출이 안 나가면 전체 컨텍스트를 다시 읽기 때문에 호출당 비용이 급증한다. Auto Mode로 길게 돌리는 작업이 아니면 캐시 적중률이 떨어진다는 점을 감안해야 한다.

```bash
# 캐시 적중률 확인
claude metrics cache --since 1h
# cache_creation_input_tokens: 1,200,000
# cache_read_input_tokens:       8,400,000
# hit_rate:                      87.5%
```

적중률이 50% 아래로 떨어지면 윈도우를 200k로 강제로 내리는 쪽이 비용이 낮다.

```bash
claude config set context.window 200000
```

---

## 5. Plan Mode와 Auto Mode 상호작용 변화

Fable 4는 Plan Mode와 Auto Mode를 동시에 켜면 모델이 "Plan을 짤 때 사용자에게 물어보지 않고 합리적으로 결정한다"였다. Fable 5는 여기에 한 단계가 추가됐다. Plan을 짠 뒤 ExitPlanMode로 사용자 승인을 받으면, 그 다음 실행 단계가 자동으로 Auto Mode로 전환된다. 따로 `/auto`를 켜지 않아도 된다.

이 동작은 편한 반면 의도하지 않은 자동 실행을 만든다. 짧은 Plan을 승인했는데 실행 단계에서 모델이 계속 redirect 없이 진행해버려서, 평소라면 확인받았을 파일 삭제가 그대로 일어나는 사례가 있다. 이 동작을 끄려면 다음을 설정한다.

```json
{
  "planMode": {
    "autoModeAfterApproval": false
  }
}
```

기본값이 `true`로 바뀌었다는 점이 Fable 4와 가장 큰 차이다.

### 5.1 Plan에서 ExitPlanMode 이후 동작

Plan을 짜고 ExitPlanMode를 호출하면 Fable 4는 단순히 Plan 모드를 빠져나오기만 했다. Fable 5는 빠져나오면서 다음을 확인한다.

- Plan 안에 언급된 파일이 실제로 존재하는지
- 언급된 명령어가 권한 모델에 등록돼 있는지
- 새로 만들 파일 경로가 기존 파일을 덮어쓰는지

존재하지 않는 파일이나 권한 없는 명령어가 있으면 ExitPlanMode 단계에서 경고를 띄우고 사용자 확인을 한 번 더 받는다. 이 검증은 끌 수 없다. Fable 4에서 자주 발생하던 "Plan대로 진행했는데 파일 경로가 틀려서 엉뚱한 데 만들어진" 문제를 잡으려고 들어간 동작이다.

---

## 6. Worktree와 Skill 시스템 변화

### 6.1 Worktree

Fable 5는 워크트리 생성을 명시적 API로 끌어올렸다. Workflow 안의 `agent(..., {isolation: 'worktree'})`는 그대로 동작하고, CLI에서도 `EnterWorktree`/`ExitWorktree` 도구가 도구 목록에 노출된다. 워크트리가 만들어지는 위치는 `--worktree-base`로 지정하거나 설정으로 잡는다.

```json
{
  "worktree": {
    "base": "/tmp/cc-worktrees",
    "autoCleanup": true,
    "maxAgeHours": 24
  }
}
```

`autoCleanup`이 `true`면 세션이 종료될 때 변경이 없는 워크트리는 삭제된다. 변경이 있으면 `maxAgeHours`가 지난 뒤 삭제된다. Fable 4는 사용자가 직접 정리해야 했고, `/tmp`가 가득 차서 디스크 알림이 울리는 일이 잦았다.

Fable 4 시절 만들어둔 워크트리는 자동 정리 대상이 아니다. 업그레이드 후에는 다음 명령으로 한 번 청소하는 게 깔끔하다.

```bash
claude worktree prune --older-than 7d
```

### 6.2 Skill 시스템

Skill 자체의 포맷은 Fable 3 이후 그대로지만, Fable 5는 스킬 로딩 시점에 차이가 있다. Fable 4는 세션 시작 시점에 모든 스킬을 메모리에 로드했다. Fable 5는 lazy loading으로 바뀌어서, 사용자가 `/skill <name>`이나 자연어로 호출했을 때 처음 디스크에서 읽는다.

장점은 세션 시작이 빨라진다는 점이다. 단점은 스킬 파일에 syntax 오류가 있어도 호출 전까지 알 수 없다는 점이다. 이걸 시작 시점에 검증하고 싶으면 다음 옵션을 켠다.

```json
{
  "skills": {
    "eagerLoad": true,
    "validateOnStart": true
  }
}
```

기존에 `~/.claude/skills/` 아래에 자작 스킬이 많다면 `validateOnStart`만 켜두는 편이 안전하다. `eagerLoad`까지 켜면 세션 시작이 다시 느려진다.

---

## 7. 업그레이드 시 주의사항

### 7.1 설정 파일 마이그레이션

Fable 5 첫 실행 시 마이그레이터가 돌면서 `settings.json`을 새 스키마로 변환한다. 변환 전 파일은 `settings.json.fable4.bak`로 백업된다. 변환 자체는 안전하지만 다음 두 경우는 수동으로 손봐야 한다.

- `permissions.allow`에 같은 키가 여러 번 들어 있는 경우: 마이그레이터가 첫 항목만 살린다
- 커스텀 hook의 `matcher`가 정규식인 경우: Fable 5는 glob만 지원하므로 변환에 실패한다

마이그레이터 로그는 `~/.claude/logs/migration-fable5.log`에 남는다. 변환 실패 항목은 이 로그에 `SKIPPED:` 접두어로 출력된다.

### 7.2 캐시 무효화

업그레이드 직후 첫 세션은 캐시가 비어 있다. 평소 적중률이 90%대라도 첫 1~2시간은 30%대까지 떨어진다. 큰 워크플로를 업그레이드 직후에 돌리면 청구가 평소 두 배 가까이 나온다. 한가한 시간대에 가벼운 세션 한두 개로 캐시를 데우고 본 작업을 돌리는 게 낫다.

`~/.claude/cache/` 디렉터리는 Fable 5에서 스키마가 바뀌었다. 옛 캐시는 자동으로 무시되지만 디스크 용량은 잡고 있다. 다음으로 정리한다.

```bash
claude cache prune --schema-version fable-4
```

### 7.3 기존 hook과 권한 호환성

PostToolUse, PreToolUse hook 시그니처는 그대로다. 다만 hook 안에서 `$CLAUDE_TOOL_NAME` 같은 환경 변수를 읽고 있다면 새 도구 이름과 매칭되는지 확인해야 한다. Fable 5에서 추가된 `EnterWorktree`, `ExitWorktree` 도구는 Fable 4 hook에는 매칭되지 않는다. 이 도구를 가로채려면 matcher에 명시적으로 추가한다.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|EnterWorktree|ExitWorktree",
        "hooks": [
          {"type": "command", "command": "/usr/local/bin/cc-audit"}
        ]
      }
    ]
  }
}
```

권한 deny 규칙은 새 중첩 형식으로 다시 작성하는 게 안전하다. 마이그레이터가 평탄 리스트를 변환할 때 `Bash` 스코프로만 옮기는데, 실제로는 MCP 도구에 걸어야 할 deny가 있었다면 누락된다.

---

## 8. 실사용에서 만난 동작 변화와 트러블슈팅

### 8.1 "Plan을 승인했는데 모델이 갑자기 멈춘다"

Fable 5의 ExitPlanMode 검증이 권한 없는 명령어를 감지한 경우다. 로그에 `plan.validation: pending` 메시지가 남는다. 권한 모델에 해당 명령어를 추가하거나, Plan을 다시 짜서 권한 있는 명령어로 바꾼다.

### 8.2 "Skill이 분명히 있는데 호출되지 않는다"

lazy loading 때문에 스킬 파일이 처음 읽히는 시점에 syntax 오류가 발견되어 로딩이 실패한 경우다. `~/.claude/logs/skills.log`를 확인하면 어느 파일의 어느 줄에서 실패했는지 나온다.

```bash
tail -n 50 ~/.claude/logs/skills.log
# 2026-06-10T09:12:33Z [error] failed to load skill 'my-deploy':
#   ~/.claude/skills/my-deploy.md: invalid frontmatter at line 4
```

`validateOnStart`를 켜두면 세션 시작 시점에 한 번에 다 잡힌다.

### 8.3 "워크트리가 안 지워진다"

`autoCleanup`이 켜져 있어도 변경 사항이 남아 있는 워크트리는 보존된다. 변경 사항이 의도하지 않은 결과물이라면 다음으로 강제 정리한다.

```bash
claude worktree prune --force --older-than 1h
```

`--force`는 변경 사항이 있어도 삭제하므로 작업물이 남아 있는지 확인하고 써야 한다. 한 번 날리면 복구할 수 없다.

### 8.4 "캐시 적중률이 떨어졌다"

세 가지를 확인한다. 첫째로 시스템 프롬프트가 매번 달라지지 않는지 — Auto Mode를 켰다 껐다 하면 시스템 프롬프트가 바뀌어서 캐시가 무효화된다. 둘째로 메인 모델을 자주 바꾸지 않는지 — 모델별로 캐시가 분리된다. 셋째로 1M 윈도우에서 컨텍스트가 5분 안에 재사용되는지 — 재사용 간격이 길면 캐시가 만료된 뒤 다시 만들어지므로 적중률이 떨어진다.

### 8.5 "권한 deny에 넣었는데 명령이 통과된다"

중첩 형식과 평탄 형식이 같은 settings.json에 공존하는 경우다. 같은 도구에 대해 두 형식이 있으면 중첩 형식이 이긴다. 평탄 리스트는 삭제하고 중첩 형식으로 통일한다.

```json
{
  "permissions": {
    "deny": {
      "Bash": ["git push --force:*", "rm -rf:*"]
    }
  }
}
```

마이그레이터가 변환한 결과를 확인하지 않고 settings.json에 옛 형식을 손으로 더 넣으면 이 충돌이 생긴다. 마이그레이션 후 한 번은 `claude config validate`로 확인하는 게 습관이 되어야 한다.

```bash
claude config validate
# OK: 12 permission rules, 3 hooks, 5 skills
# WARNING: legacy flat list found in permissions.allow, ignored
```

WARNING이 뜨면 그 자리에서 정리한다. 미루면 다음에 디버깅할 때 같은 자리에서 다시 잡고 있게 된다.
