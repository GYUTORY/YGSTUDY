---
title: Claude Code Worktree
tags: [ai, claude-code, git-worktree, parallel-development, isolation]
updated: 2026-04-08
---

# Claude Code Worktree

## 1. git worktree 기본 개념

git worktree는 하나의 저장소에서 여러 작업 디렉토리를 동시에 열 수 있게 해주는 기능이다. 보통은 브랜치를 전환하려면 `git checkout`이나 `git switch`로 현재 작업 디렉토리를 바꿔야 한다. worktree를 쓰면 브랜치마다 별도의 디렉토리가 생기니까, 브랜치 전환 없이 여러 작업을 동시에 진행할 수 있다.

```bash
# feature 브랜치를 별도 디렉토리로 열기
git worktree add ../my-project-feature feature/login

# 현재 worktree 목록 확인
git worktree list

# 작업 끝나면 정리
git worktree remove ../my-project-feature
```

worktree 디렉토리 안에는 `.git` 파일이 하나 있는데, 이건 실제 `.git` 디렉토리가 아니라 원본 저장소의 `.git` 디렉토리를 가리키는 포인터다. 그래서 커밋 히스토리, 리모트 설정, hooks 같은 건 모든 worktree가 공유한다.

한 가지 제약이 있다. **같은 브랜치를 두 개 이상의 worktree에서 동시에 체크아웃할 수 없다.** 이건 브랜치의 HEAD가 꼬이는 걸 방지하기 위한 git의 설계 제약이다.

```bash
# main이 이미 체크아웃되어 있으면 에러 발생
$ git worktree add ../hotfix main
fatal: 'main' is already checked out at '/path/to/original'
```

---

## 2. Claude Code에서 Worktree 사용하기

### 2.1 진입: /enter-worktree

Claude Code 세션에서 `/enter-worktree`를 실행하면 현재 저장소 기반으로 임시 worktree를 생성하고 그 안에서 작업을 시작한다.

```
> /enter-worktree
```

실행하면 다음과 같은 일이 일어난다:

1. 현재 저장소에 `git worktree add`로 임시 디렉토리 생성
2. Claude Code의 작업 디렉토리가 새 worktree로 변경
3. 이후 파일 읽기, 수정, bash 명령 등이 모두 worktree 안에서 실행

새 브랜치 이름을 지정할 수도 있고, 기존 브랜치를 체크아웃할 수도 있다. 원본 작업 디렉토리의 상태는 전혀 건드리지 않으니까, 진행 중인 작업이 있어도 안전하다.

### 2.2 퇴출: /exit-worktree

작업이 끝나면 `/exit-worktree`로 원래 디렉토리로 돌아온다.

```
> /exit-worktree
```

이때 worktree에서 변경사항이 있으면 어떻게 처리할지 물어본다. 커밋하지 않은 변경사항이 남아있으면 경고가 뜨고, 커밋된 변경사항은 원본 저장소에서 merge하거나 cherry-pick으로 가져올 수 있다.

변경사항이 없는 worktree는 자동으로 정리된다. 변경사항이 있으면 worktree 경로와 브랜치 이름이 반환되니까 나중에 수동으로 처리할 수 있다.

---

## 3. Agent 도구의 isolation: worktree 옵션

Claude Code의 Agent 도구(서브에이전트를 생성하는 기능)에는 `isolation: "worktree"` 옵션이 있다. 이걸 쓰면 서브에이전트가 독립된 worktree에서 작업하기 때문에, 메인 작업 디렉토리에 영향을 주지 않는다.

```json
{
  "description": "핫픽스 적용",
  "prompt": "auth 모듈의 토큰 만료 버그를 수정해라",
  "isolation": "worktree"
}
```

서브에이전트가 worktree에서 작업을 마치면:

- **변경사항이 없는 경우**: worktree가 자동으로 삭제된다
- **변경사항이 있는 경우**: worktree 경로와 브랜치 이름이 결과에 포함된다. 메인 에이전트가 이 정보를 받아서 merge하거나 사용자에게 알려줄 수 있다

이 방식의 장점은 서브에이전트가 파일을 마음대로 수정해도 메인 작업에 영향이 없다는 것이다. 실험적인 리팩토링이나 위험한 변경을 시도할 때 유용하다.

### 3.1 일반 서브에이전트와의 차이

| 구분 | 일반 서브에이전트 | isolation: worktree |
|------|------------------|---------------------|
| 작업 디렉토리 | 메인과 동일 | 별도 worktree |
| 파일 수정 영향 | 메인에 즉시 반영 | 메인에 영향 없음 |
| git 상태 | 메인과 공유 | 독립된 브랜치 |
| 정리 | 수동 | 변경 없으면 자동 정리 |

---

## 4. 실전 시나리오

### 4.1 핫픽스 처리

피처 개발 중에 프로덕션 버그가 발견된 경우다. 기존에는 stash하고 브랜치 전환하고 수정하고 다시 돌아와야 했다.

```
# 피처 개발 중인 상태에서
> /enter-worktree

# worktree 안에서 핫픽스 브랜치 생성
> hotfix/auth-token-expire 브랜치를 만들고 토큰 만료 시간 계산 버그를 수정해줘

# 수정 완료 후 커밋, 푸시
> 커밋하고 푸시해줘

# 원래 작업으로 복귀
> /exit-worktree

# 피처 개발 이어서 진행
```

stash를 쓸 필요가 없다. 피처 브랜치의 staged/unstaged 변경사항이 그대로 보존되니까 컨텍스트 스위칭 비용이 줄어든다.

### 4.2 병렬 피처 개발

여러 피처를 동시에 진행할 때, Agent 도구의 worktree isolation을 활용할 수 있다.

```
> feature/user-profile은 내가 직접 작업할 테니까,
  feature/notification 브랜치에서 알림 API 스켈레톤 코드를 만들어줘.
  worktree로 격리해서 작업해.
```

이렇게 하면 Claude Code가 서브에이전트를 worktree isolation으로 실행해서 알림 API 작업을 별도 디렉토리에서 처리한다. 메인 세션에서는 user-profile 작업을 계속할 수 있다.

### 4.3 PR 리뷰 중 수정

PR 리뷰를 하다가 직접 코드를 수정해야 하는 상황이다.

```
# 현재 main 브랜치에서 작업 중
> /enter-worktree

# PR의 브랜치를 체크아웃
> feature/payment 브랜치를 체크아웃하고, 
  결제 금액 반올림 로직에서 소수점 셋째 자리까지 처리하도록 수정해줘

# 수정 후 커밋, 푸시
> 수정 커밋하고 푸시해줘

# 원래 작업으로 복귀
> /exit-worktree
```

리뷰 코멘트만 달지 않고 직접 수정까지 처리할 수 있으니까 PR 처리 속도가 빨라진다.

---

## 5. Worktree 디스크 관리와 정리

### 5.1 worktree가 쌓이는 문제

worktree를 만들고 제대로 정리하지 않으면 디스크에 계속 쌓인다. 특히 Claude Code에서 서브에이전트가 생성한 worktree는 변경사항이 있으면 자동 삭제되지 않기 때문에, 의식적으로 관리해야 한다.

```bash
# 현재 worktree 목록 확인
git worktree list

# 출력 예시
# /Users/dev/my-project           abc1234 [main]
# /Users/dev/my-project-hotfix    def5678 [hotfix/auth]
# /tmp/.claude/worktree-a8f3e2    (detached HEAD)
```

`/tmp/` 아래에 생성된 worktree는 Claude Code가 만든 임시 worktree일 가능성이 높다. 작업이 끝났는데 남아있다면 수동으로 정리해야 한다.

### 5.2 정리 방법

```bash
# 특정 worktree 삭제 (변경사항 없는 경우)
git worktree remove /path/to/worktree

# 변경사항이 있으면 --force 필요
git worktree remove --force /path/to/worktree

# 이미 디렉토리가 삭제된 worktree 참조 정리
git worktree prune
```

`git worktree prune`은 디렉토리는 이미 삭제됐는데 git 내부 참조만 남아있는 경우를 정리한다. 시스템 재부팅이나 `/tmp` 정리로 worktree 디렉토리가 사라진 경우에 필요하다.

### 5.3 디스크 사용량 확인

worktree는 원본 저장소의 `.git` 객체를 공유하니까 전체 저장소를 복제하는 것보다는 디스크를 적게 쓴다. 하지만 작업 디렉토리에 있는 파일들(체크아웃된 파일, node_modules, 빌드 결과물 등)은 worktree마다 별도로 존재한다.

```bash
# worktree별 디스크 사용량 확인
du -sh $(git worktree list --porcelain | grep worktree | cut -d' ' -f2)
```

node_modules가 큰 프로젝트에서는 worktree마다 `npm install`을 해야 하니까 디스크 사용량이 빠르게 늘어날 수 있다. 작업이 끝나면 바로 정리하는 습관이 필요하다.

---

## 6. 멀티 세션 충돌 방지

### 6.1 같은 저장소에서 여러 Claude Code 세션

터미널 여러 개를 열고 같은 저장소에서 Claude Code를 동시에 실행하는 경우가 있다. worktree 없이 이렇게 하면 파일 수정이 충돌할 수 있다.

각 세션이 worktree를 사용하면 파일 시스템 레벨에서 격리되니까 충돌이 발생하지 않는다. 단, git의 내부 lock에 의한 충돌은 있을 수 있다.

### 6.2 git index.lock 충돌

여러 worktree에서 동시에 git 작업(commit, checkout 등)을 하면 `.git/index.lock` 관련 에러가 날 수 있다.

```
fatal: Unable to create '/path/to/repo/.git/index.lock': File exists.
```

worktree마다 자체 index 파일이 있지만, 일부 git 작업은 공유되는 메인 `.git` 디렉토리의 lock을 잡는다. refs 업데이트(브랜치 생성, 태그 생성 등)가 대표적이다.

이런 상황은 드물지만, 동시에 여러 worktree에서 브랜치를 만들거나 push하면 발생할 수 있다. 잠시 후 재시도하면 보통 해결된다. lock 파일이 오래 남아있다면(해당 프로세스가 비정상 종료된 경우) 수동으로 삭제해도 된다.

```bash
# lock 파일이 stale한 경우에만 삭제
rm .git/index.lock
```

---

## 7. 주의사항

### 7.1 브랜치 중복 체크아웃 에러

앞서 말한 것처럼, 같은 브랜치를 두 개 이상의 worktree에서 체크아웃하면 에러가 난다.

```
fatal: 'feature/login' is already checked out at '/path/to/other-worktree'
```

이 제약은 git의 설계상 의도적인 것이다. 같은 브랜치를 두 곳에서 수정하면 어느 쪽의 HEAD가 맞는지 결정할 수 없기 때문이다.

해결 방법:
- 새 브랜치를 만들어서 체크아웃한다
- 기존 worktree를 먼저 정리한다
- detached HEAD로 체크아웃한다 (`git checkout --detach`)

Claude Code에서 `/enter-worktree`를 실행할 때 현재 브랜치와 같은 브랜치를 지정하면 이 에러를 만날 수 있다. 다른 브랜치 이름을 지정하거나, 새 브랜치를 생성하도록 해야 한다.

### 7.2 lock 파일 관련 문제

Claude Code 세션이 비정상 종료되면 worktree 관련 lock 파일이 남을 수 있다.

```bash
# worktree lock 상태 확인
git worktree list

# lock 해제
git worktree unlock /path/to/worktree
```

worktree를 수동으로 `git worktree lock`으로 잠그면 `git worktree remove`로 삭제가 안 된다. 의도적으로 잠근 게 아니라면 `unlock`으로 풀어야 한다.

### 7.3 .gitignore와 worktree

worktree는 `.gitignore`를 원본 저장소와 공유한다. 하지만 worktree 디렉토리 안에서 별도의 `.gitignore` 규칙이 필요한 경우는 거의 없다. IDE 설정 파일이나 로컬 환경 파일이 worktree마다 다르게 필요한 경우, `.git/info/exclude`를 사용하면 된다. 이 파일은 worktree마다 독립적이다.

### 7.4 hooks 공유

git hooks는 `.git/hooks` 디렉토리에 있는데, 이건 모든 worktree가 공유한다. pre-commit hook이 설정되어 있으면 어떤 worktree에서 커밋하든 동일하게 실행된다. 이 점은 보통 원하는 동작이지만, worktree별로 다른 hook 동작이 필요한 경우는 hook 스크립트 안에서 `$GIT_WORK_TREE` 환경변수를 확인해서 분기 처리해야 한다.

### 7.5 서브모듈이 있는 저장소

서브모듈을 사용하는 저장소에서 worktree를 만들면, 서브모듈이 자동으로 초기화되지 않는다. worktree 디렉토리에서 직접 `git submodule update --init`을 실행해야 한다. 이걸 빼먹으면 빌드가 실패하는 경우가 많다.
