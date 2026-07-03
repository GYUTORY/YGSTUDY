---
title: Worktree, Submodule, LFS 실무
tags:
  - Git
  - Worktree
  - Submodule
  - LFS
updated: 2026-07-03
---

# Worktree, Submodule, LFS 실무

기본 명령어만 알아도 하루 작업은 돌아간다. 그런데 브랜치를 두 개 동시에 붙잡고 있어야 할 때, 남의 저장소를 내 저장소 안에 끼워 넣어야 할 때, 몇백 MB짜리 바이너리를 커밋해야 할 때, clone 한 번에 10분이 걸릴 때가 온다. 이 문서는 그런 상황에서 쓰는 네 가지 기능을 다룬다. 공통점은 하나같이 "몰라도 살지만 알면 반나절을 아끼는" 것들이라는 점이다.

## Worktree — 한 저장소를 여러 디렉토리에 펼치기

### 왜 필요한가

기능 브랜치에서 한창 코드를 뒤엎어 놨는데 운영에서 장애가 터진다. 지금 당장 `main`에서 핫픽스를 내야 한다. 보통은 이렇게 한다.

```bash
$ git stash
$ git checkout main
# 핫픽스 작업
$ git checkout feature/big-refactor
$ git stash pop
```

stash로 밀어 넣고, 브랜치 갈아타고, 고치고, 다시 돌아와서 stash를 꺼낸다. 이 과정에서 자잘한 사고가 난다. stash pop 하다가 충돌이 나거나, 빌드 산출물이 브랜치마다 달라서 IDE가 인덱싱을 처음부터 다시 돌리거나, `node_modules`가 브랜치 간 호환이 안 돼서 재설치를 해야 하는 식이다. 작업 중이던 컨텍스트가 통째로 날아간다.

worktree는 같은 저장소를 여러 디렉토리에 동시에 체크아웃한다. 기존 작업 디렉토리는 그대로 두고, 옆에 새 디렉토리를 만들어서 거기에 `main`을 붙인다.

```bash
$ git worktree add ../hotfix main
Preparing worktree (checking out 'main')
HEAD is now at a1b2c3d ...

$ cd ../hotfix
# 여기서 핫픽스 작업, 커밋, push
```

원래 작업 디렉토리는 손도 안 댔다. stash도 없고 브랜치 전환도 없다. 핫픽스가 끝나면 원래 디렉토리로 돌아가면 그대로 있다.

### 동작 방식

worktree는 `.git` 저장소 하나를 공유한다. 커밋, 브랜치, 스태시, reflog 전부 같은 저장소에 저장된다. 각 worktree는 작업 디렉토리와 HEAD만 따로 가진다. 그래서 디스크를 두 배로 먹지 않는다. 오브젝트는 공유하고 워킹 트리만 복제하는 셈이다.

추가한 worktree 디렉토리를 보면 `.git`이 디렉토리가 아니라 파일이다.

```bash
$ cat ../hotfix/.git
gitdir: /path/to/main-repo/.git/worktrees/hotfix
```

메인 저장소의 `.git/worktrees/` 아래에 각 worktree의 메타데이터가 들어간다.

### 규칙: 같은 브랜치를 두 곳에서 체크아웃 못 한다

worktree의 가장 중요한 제약이다. 한 브랜치는 한 worktree에서만 체크아웃할 수 있다.

```bash
$ git worktree add ../another main
fatal: 'main' is already checked out at '/path/to/hotfix'
```

이게 있어야 하는 이유는 명확하다. 같은 브랜치를 두 디렉토리에서 각각 커밋하면 브랜치 포인터가 어디를 가리켜야 할지 모순이 생긴다. 이 제약 덕분에 실수로 브랜치 상태를 꼬는 일이 막힌다.

특정 커밋만 잠깐 보고 싶으면 detached HEAD로 붙이면 된다.

```bash
$ git worktree add --detach ../inspect a1b2c3d
```

새 브랜치를 바로 만들면서 worktree를 열 수도 있다.

```bash
$ git worktree add -b hotfix/login-500 ../hotfix main
```

`hotfix/login-500` 브랜치를 `main`에서 새로 따면서 `../hotfix`에 체크아웃한다. 핫픽스 대응할 때 이 형태를 제일 많이 쓴다.

### 정리 — remove와 prune

작업이 끝나면 지워야 한다. 디렉토리를 `rm -rf`로 날리면 안 된다. 메타데이터가 남는다.

```bash
$ git worktree remove ../hotfix
```

remove는 워킹 디렉토리와 메타데이터를 같이 지운다. 워킹 트리에 커밋 안 한 변경이 남아 있으면 안전장치로 거부한다. 확실하면 `--force`를 붙인다.

디렉토리를 이미 `rm -rf`로 지워 버렸거나, 외장 드라이브에 있던 worktree가 마운트 해제된 경우엔 메타데이터만 붕 뜬다. 이때 `prune`으로 청소한다.

```bash
$ git worktree list
/path/to/main-repo   a1b2c3d [main]
/path/to/hotfix      e4f5g6h [hotfix/login-500]   # 실제 디렉토리는 이미 없음

$ git worktree prune
$ git worktree list
/path/to/main-repo   a1b2c3d [main]
```

`list`로 현재 등록된 worktree를 확인하고, `prune`으로 실체 없는 항목을 걷어낸다. 습관적으로 remove를 쓰고, 사고로 디렉토리를 날렸을 때만 prune을 쓴다고 기억하면 된다.

### 주의할 점

빌드 산출물이나 `.env` 같은 건 worktree마다 따로 관리된다. gitignore 대상은 공유되지 않으니 새 worktree에서 빌드하려면 의존성 설치를 다시 해야 하는 경우가 있다. 그래도 브랜치 전환 때마다 재설치하는 것보다는 낫다. 각 worktree가 자기 `node_modules`를 유지하니까.

## Submodule — 저장소 안의 저장소

### 언제 쓰나

공용 라이브러리나 사내 SDK를 여러 프로젝트가 공유하는데, 그 라이브러리도 독립된 저장소로 버전 관리되는 경우가 있다. 코드를 복사해 넣으면 원본이 바뀔 때마다 동기화가 지옥이 된다. submodule은 다른 저장소를 특정 커밋에 고정해서 내 저장소 안에 끼워 넣는다.

```bash
$ git submodule add https://github.com/myorg/shared-lib.git libs/shared
```

`.gitmodules` 파일이 생기고, `libs/shared`에 라이브러리가 clone된다.

```ini
# .gitmodules
[submodule "libs/shared"]
	path = libs/shared
	url = https://github.com/myorg/shared-lib.git
```

### 핵심: submodule은 커밋 포인터다

이걸 이해 못 하면 submodule은 계속 사람을 괴롭힌다. 부모 저장소는 submodule의 코드를 저장하지 않는다. "submodule이 어느 커밋을 가리키는지"만 저장한다. `git status`로 보면 submodule은 파일이 아니라 커밋 해시 한 개로 취급된다.

```bash
$ git diff
diff --git a/libs/shared b/libs/shared
index a1b2c3d..e4f5g6h 160000
--- a/libs/shared
+++ b/libs/shared
@@ -1 +1 @@
-Subproject commit a1b2c3d...
+Subproject commit e4f5g6h...
```

`160000`이라는 특이한 모드가 보인다. 이게 submodule을 뜻하는 gitlink다. 부모가 저장하는 건 오직 이 커밋 해시다.

### 함정 1: detached HEAD

submodule 디렉토리에 처음 들어가 보면 브랜치가 아니라 detached HEAD 상태다.

```bash
$ cd libs/shared
$ git status
HEAD detached at a1b2c3d
```

부모 저장소가 "이 커밋"을 가리키라고 지정했기 때문이다. 여기서 아무 생각 없이 코드를 고치고 커밋하면, 그 커밋은 어느 브랜치에도 속하지 않는다. `cd ..`로 나갔다가 나중에 submodule을 업데이트하면 그 커밋은 참조를 잃고 사라진다. 몇 시간 작업한 게 reflog 뒤져야 겨우 찾을 수 있는 상태가 된다.

submodule 안에서 실제로 작업하려면 반드시 브랜치를 먼저 잡는다.

```bash
$ cd libs/shared
$ git checkout main
$ git pull
# 이제 여기서 작업하고 커밋, push
```

### 함정 2: 포인터 커밋 잊고 push

submodule에서 코드를 고치고 submodule 저장소에 push까지 했다. 여기서 끝난 게 아니다. 부모 저장소는 아직 옛날 커밋을 가리키고 있다. 부모에서 새 포인터를 커밋해야 한다.

```bash
$ cd ..            # 부모 저장소로
$ git add libs/shared
$ git commit -m "shared-lib 업데이트: 로그인 버그 수정 반영"
$ git push
```

이걸 빼먹으면 동료가 부모를 pull 했을 때 submodule은 여전히 옛날 커밋을 가리킨다. "내 로컬에선 되는데" 상황의 단골 원인이다. 반대로 submodule에서 push는 안 하고 부모 포인터만 push하는 실수도 흔하다. 이러면 동료가 submodule을 업데이트하려는 순간 "그런 커밋 없다"며 터진다. submodule 먼저 push, 그다음 부모 포인터 push. 순서를 몸에 익혀야 한다.

### 함정 3: clone할 때 submodule이 비어 있다

submodule이 있는 저장소를 그냥 clone하면 submodule 디렉토리는 텅 빈다. 포인터만 있고 실제 코드는 안 받아진다.

```bash
$ git clone https://github.com/myorg/app.git
$ ls app/libs/shared
# 아무것도 없음
```

clone 시점에 같이 받으려면 `--recurse-submodules`를 붙인다.

```bash
$ git clone --recurse-submodules https://github.com/myorg/app.git
```

이미 clone을 받은 뒤라면 초기화하고 업데이트한다.

```bash
$ git submodule update --init --recursive
```

부모를 pull 할 때 submodule 포인터가 바뀌었을 수 있다. pull 뒤에 submodule도 맞춰 줘야 한다.

```bash
$ git pull
$ git submodule update --init --recursive
```

이걸 매번 두 줄로 치기 귀찮으면 설정으로 자동화한다.

```bash
$ git config submodule.recurse true
```

이 설정을 켜면 `git pull`, `git checkout`이 submodule을 알아서 따라간다. 팀 전체가 submodule을 쓴다면 이 설정을 각자 켜 두는 게 사고를 줄인다.

### submodule이 애물단지가 될 때

submodule은 강제되는 규칙이 많고 실수 지점이 많다. 라이브러리를 자주 같이 수정하는 구조라면 submodule보다 모노레포나 패키지 레지스트리(사내 npm, Maven 등)가 나은 경우가 많다. submodule은 "가끔 버전만 올리는, 명확히 분리된 의존성"에 적합하다. 하루에도 몇 번씩 부모와 함께 고쳐야 한다면 도구 선택이 틀린 것이다.

## Git LFS — 대용량 바이너리 다루기

### 문제 상황

디자인 시안 PSD, 게임 리소스, 학습된 모델 가중치, 동영상 같은 걸 커밋하기 시작하면 저장소가 순식간에 비대해진다. Git은 파일이 조금만 바뀌어도 그 버전 전체를 저장한다. 100MB짜리 바이너리를 열 번 수정하면 저장소에 1GB가 쌓인다. 텍스트는 diff가 작지만 바이너리는 압축도 잘 안 되고 delta도 안 먹는다. clone 한 번에 수 GB를 받아야 하는 저장소가 이렇게 만들어진다.

Git LFS(Large File Storage)는 큰 파일의 실체를 별도 서버에 두고, Git 저장소에는 포인터만 남긴다. 포인터는 몇백 바이트짜리 텍스트다.

### 도입

LFS를 설치하고 어떤 파일을 LFS로 관리할지 지정한다.

```bash
$ git lfs install
$ git lfs track "*.psd"
$ git lfs track "*.mp4"
$ git lfs track "assets/models/*.bin"
```

`track`을 실행하면 `.gitattributes`에 규칙이 쌓인다.

```
# .gitattributes
*.psd filter=lfs diff=lfs merge=lfs -text
*.mp4 filter=lfs diff=lfs merge=lfs -text
```

`.gitattributes`는 반드시 커밋해야 한다. 이 파일이 없으면 동료의 환경에서는 LFS가 동작하지 않고 큰 파일이 그냥 Git에 들어간다.

이후로는 평소처럼 add, commit하면 된다. LFS가 필터로 끼어들어서 실제 파일은 LFS 스토리지로 보내고 저장소에는 포인터를 커밋한다.

```bash
$ git add design.psd
$ git commit -m "메인 배너 시안 추가"
```

포인터 파일의 실제 내용을 보면 이렇게 생겼다.

```
version https://git-lfs.github.com/spec/v1
oid sha256:4d7a...
size 104857600
```

### 이미 커밋된 큰 파일 처리

여기가 제일 골치 아프다. LFS를 나중에 도입하면 과거 커밋에 이미 박힌 큰 파일은 저절로 사라지지 않는다. `.gitattributes`에 track을 걸어도 그건 "앞으로 커밋될 파일"에만 적용된다. 이미 히스토리에 들어간 파일은 여전히 저장소를 무겁게 만든다.

과거 히스토리에서 큰 파일을 LFS로 옮기려면 히스토리를 다시 쓴다. `git lfs migrate`를 쓴다.

```bash
$ git lfs migrate import --include="*.psd" --everything
```

`--everything`은 모든 브랜치와 태그의 히스토리를 대상으로 한다. 이 명령은 커밋 해시를 전부 바꾼다. 히스토리 재작성이라 협업 중인 저장소에서는 신중해야 한다. 다른 사람이 이미 pull 받은 히스토리를 갈아엎는 것이라, 실행 전에 팀 전체에 공지하고 각자 작업을 정리하게 해야 한다. force push가 필요하고, 그 뒤에 모든 팀원이 저장소를 다시 clone하거나 강제로 히스토리를 맞춰야 한다.

혼자 쓰는 저장소가 아니라면 히스토리 재작성보다, 큰 파일을 아예 걷어내고 새로 시작하는 게 나을 때도 있다. 판단 기준은 "이 저장소의 과거 히스토리가 얼마나 중요한가"다.

### LFS 쓸 때 겪는 것들

clone하거나 pull할 때 LFS가 설치돼 있지 않으면 포인터 파일만 받아진다. 큰 파일을 열려는 순간 "이게 왜 텍스트지" 하고 당황한다. 이럴 땐 LFS를 설치하고 실제 파일을 당겨온다.

```bash
$ git lfs install
$ git lfs pull
```

GitHub 같은 호스팅은 LFS 스토리지와 대역폭에 용량 제한이 걸려 있다. 무료 한도를 넘기면 결제하거나 파일을 정리해야 한다. 팀에서 수십 GB짜리 리소스를 LFS로 관리하면 이 한도를 금방 넘기니 미리 확인하는 게 좋다.

한 가지 더. LFS로 관리되는 파일은 일반 diff가 안 된다. 바이너리라 당연하지만, 코드 리뷰에서 "이 시안 뭐가 바뀐 거야"를 Git으로 확인할 수 없다. 이건 LFS의 한계가 아니라 바이너리의 한계다.

## Partial clone과 sparse-checkout — 거대 저장소 다루기

### clone이 느린 두 가지 원인

모노레포가 커지면 clone 한 번에 몇 분에서 몇십 분이 걸린다. 원인은 두 가지로 나뉜다. 하나는 히스토리가 너무 길고 무거워서(오래된 커밋의 오브젝트를 전부 받아야 함), 다른 하나는 지금 당장 필요 없는 디렉토리까지 전부 워킹 트리에 펼쳐야 해서다. 이 둘은 해법이 다르다.

### Partial clone — 오브젝트를 필요할 때 받기

partial clone은 히스토리의 오브젝트를 clone 시점에 다 받지 않는다. 커밋 그래프와 트리는 받되, 파일 내용(blob)은 실제로 필요할 때 서버에서 당겨온다.

```bash
$ git clone --filter=blob:none https://github.com/myorg/huge-repo.git
```

`--filter=blob:none`은 blob을 아예 안 받는다. checkout할 때 필요한 blob만 그때그때 가져온다. 최근 커밋 위주로 작업하고 오래된 파일 내용을 볼 일이 거의 없다면 clone이 극적으로 빨라진다.

일정 크기 이상만 걸러낼 수도 있다.

```bash
$ git clone --filter=blob:limit=1m https://github.com/myorg/huge-repo.git
```

1MB 넘는 blob은 지연 로딩하고 작은 파일은 다 받는다. 대부분의 작업이 소스 코드고 가끔 대용량 파일만 문제라면 이 형태가 균형이 좋다.

대가는 있다. blob이 로컬에 없으니 오프라인에서 과거 파일을 열려고 하면 서버에 요청이 나간다. 인터넷이 끊긴 상태에서 오래된 커밋을 뒤지면 실패한다. `git log -p`처럼 히스토리 전체의 내용을 훑는 명령은 그만큼 blob을 대량으로 당겨오느라 느려질 수 있다.

### Sparse-checkout — 필요한 디렉토리만 펼치기

partial clone이 "히스토리를 덜 받는" 거라면, sparse-checkout은 "워킹 트리를 덜 펼치는" 것이다. 모노레포에서 나는 `services/payment`만 만지는데 저장소 전체 디렉토리가 워킹 트리에 다 펼쳐질 이유가 없다.

```bash
$ git clone --filter=blob:none --sparse https://github.com/myorg/monorepo.git
$ cd monorepo
$ git sparse-checkout set services/payment libs/common
```

`--sparse`로 clone하면 처음엔 루트의 파일만 체크아웃된다. `sparse-checkout set`으로 실제로 작업할 디렉토리만 지정하면 그것들만 워킹 트리에 나타난다. 나머지 수백 개 디렉토리는 디스크에 펼쳐지지 않는다. IDE 인덱싱도 빨라지고, 파일 검색도 관심 있는 범위로 좁혀진다.

작업 범위가 바뀌면 다시 지정하면 된다.

```bash
$ git sparse-checkout add services/notification
```

partial clone과 sparse-checkout은 같이 쓸 때 효과가 크다. partial clone으로 히스토리 오브젝트를 줄이고, sparse-checkout으로 워킹 트리를 줄인다. 수 GB짜리 모노레포를 몇백 MB 수준의 로컬 작업 환경으로 만들 수 있다.

### 주의할 점

sparse-checkout으로 디렉토리를 숨겨도 그 디렉토리의 파일들은 여전히 Git이 추적한다. 브랜치를 옮기거나 pull할 때 숨긴 영역의 변경도 반영된다. 워킹 트리에서 안 보일 뿐 없어진 게 아니다. 이걸 착각해서 "이 디렉토리 지워도 되겠지" 하고 실수하는 경우가 있다.

빌드 시스템이 저장소 전체 구조를 전제로 동작하면 sparse-checkout이 오히려 발목을 잡는다. 없는 디렉토리를 참조하다 빌드가 깨진다. 도입 전에 빌드가 어느 경로에 의존하는지 확인하고, 그 경로를 sparse 범위에 포함시켜야 한다.

## 정리

네 기능 모두 "평소엔 필요 없다가 특정 순간에 반나절을 아끼는" 도구다. worktree는 브랜치 전환 비용이 클 때, submodule은 분리된 저장소를 버전 고정해서 끼워 넣을 때, LFS는 바이너리로 저장소가 비대해질 때, partial clone과 sparse-checkout은 저장소가 너무 커서 clone과 작업이 느릴 때 꺼내 쓴다. 공통적으로 함정이 있다. worktree는 메타데이터 정리, submodule은 포인터 커밋 순서와 detached HEAD, LFS는 이미 커밋된 파일과 히스토리 재작성, sparse-checkout은 숨겨진 디렉토리의 추적 상태다. 도구 자체보다 이 함정들을 아는 게 실무에서 더 중요하다.
