---
title: Git 자주 사용하는 명령어
tags:
  - Git
  - VersionControl
  - CLI
updated: 2026-06-30
---

# Git 자주 사용하는 명령어

매일 쓰는 명령어는 정해져 있다. status, add, commit, push, pull. 문제는 뭔가 꼬였을 때다. 잘못된 브랜치에 커밋하거나, force push로 남의 작업을 날리거나, rebase 도중 충돌이 나서 멈췄을 때 어떻게 빠져나오는지가 실력 차이를 만든다. 이 문서는 일상 명령어부터 사고 수습까지 실제로 쓰는 형태로 정리한다.

## 기본 흐름

### status

작업 디렉토리 상태를 본다. 커밋 전에 뭐가 staged 됐고 뭐가 안 됐는지 확인하는 습관을 들여야 한다.

```bash
git status            # 전체 상태
git status -s         # short 포맷, 한 줄에 파일 하나
```

`-s`로 보면 왼쪽 열이 staging area, 오른쪽 열이 working tree 상태다. `M ` 는 staged된 수정, ` M`은 아직 add 안 된 수정, `??`는 추적 안 되는 새 파일이다. 파일이 많을 때는 `-s`가 훨씬 빨리 읽힌다.

### add

staging area에 올린다. 커밋할 변경을 고르는 단계다.

```bash
git add file.js          # 특정 파일
git add .                # 현재 디렉토리 이하 전부
git add -p               # 변경을 hunk 단위로 골라서 추가
```

`git add -p`는 한 파일 안에서도 일부 변경만 커밋하고 싶을 때 쓴다. 디버깅용 로그를 넣어둔 상태에서 진짜 수정만 커밋하고 로그는 남겨두는 식으로 쓴다. 각 hunk마다 `y/n/s/e`를 묻는데, `s`는 hunk를 더 잘게 쪼개고 `e`는 직접 편집한다.

### commit

```bash
git commit -m "메시지"        # 한 줄 메시지
git commit                    # 에디터 열어서 본문까지 작성
git commit --amend            # 직전 커밋 수정
git commit -am "메시지"       # 추적 중인 파일은 add 생략하고 커밋
```

`--amend`는 직전 커밋의 메시지를 고치거나 빠뜨린 파일을 추가할 때 쓴다. 메시지만 고치려면 그냥 `git commit --amend`, 파일을 추가하려면 `git add` 먼저 하고 `git commit --amend --no-edit`로 메시지는 그대로 둔다.

주의할 점이 있다. 이미 push한 커밋을 `--amend`하면 커밋 해시가 바뀐다. 그러면 다음 push 때 거부당하고, 원격 히스토리를 강제로 덮어써야 한다. 혼자 쓰는 브랜치가 아니면 push한 커밋은 amend하지 않는다.

### log

```bash
git log                              # 전체 로그
git log --oneline                    # 한 줄씩
git log --oneline --graph --all      # 브랜치 그래프까지
git log -p file.js                   # 특정 파일의 변경 내역과 diff
git log --author="이름"              # 특정 작성자
git log --since="2 weeks ago"        # 기간
git log -S "함수명"                  # 해당 문자열이 추가/삭제된 커밋 검색
```

`git log -S`는 "이 함수가 언제 사라졌지"를 추적할 때 쓴다. 코드 문자열이 추가되거나 제거된 커밋만 골라서 보여준다. 버그가 언제 들어왔는지 역추적할 때 `git log -p`로 파일 변경 이력을 따라가는 것보다 훨씬 빠르다.

`--graph --all --oneline`은 묶어서 alias로 등록해두면 편하다.

```bash
git config --global alias.lg "log --oneline --graph --all --decorate"
```

## 브랜치 작업

### branch

```bash
git branch                   # 로컬 브랜치 목록
git branch -a                # 원격 포함 전체
git branch -d feature        # 머지된 브랜치 삭제
git branch -D feature        # 머지 안 됐어도 강제 삭제
git branch -m old new        # 브랜치 이름 변경
git branch -vv               # 각 브랜치의 추적 원격과 ahead/behind 표시
```

`-d`는 머지 안 된 브랜치는 안 지워서 안전장치 역할을 한다. 실수로 작업물을 날리지 않으려면 `-D` 대신 `-d`를 먼저 시도한다. 거부당하면 정말 날려도 되는지 한 번 더 생각한다.

`git branch -vv`로 보면 각 로컬 브랜치가 어느 원격을 추적하는지, 몇 커밋 앞서거나 뒤처졌는지 나온다. push가 안 될 때 원인 파악에 쓴다.

### checkout과 switch

`switch`는 브랜치 전환 전용으로 나중에 나온 명령어다. `checkout`은 브랜치 전환과 파일 복원을 모두 하기 때문에 헷갈린다. 브랜치 작업은 `switch`, 파일 복원은 `restore`로 나눠 쓰는 게 명확하다.

```bash
git switch main              # 브랜치 전환
git switch -c feature        # 새 브랜치 만들고 전환
git switch -                 # 직전 브랜치로

git checkout main            # 위와 동일 (구식)
git checkout -b feature      # 새 브랜치 + 전환 (구식)
```

`git switch -`는 직전에 있던 브랜치로 돌아간다. feature와 main을 왔다 갔다 할 때 이름 안 치고 토글한다.

### merge

```bash
git switch main
git merge feature            # feature를 main에 병합
git merge --no-ff feature    # fast-forward 가능해도 머지 커밋 생성
git merge --squash feature   # 변경을 한 커밋으로 합쳐서 staging
```

기본 머지는 fast-forward가 가능하면 머지 커밋 없이 포인터만 이동한다. 그러면 feature 브랜치가 있었다는 흔적이 히스토리에 안 남는다. 브랜치 단위로 작업을 추적하고 싶으면 `--no-ff`를 쓴다. 팀 정책에 따라 다르니 정해서 통일한다.

`--squash`는 feature의 모든 커밋을 하나로 압축한다. 머지하지 않고 staging만 하므로 직접 commit해야 한다. 잡다한 wip 커밋을 main에 안 남기고 싶을 때 쓴다.

## 원격 동기화

### fetch와 pull

```bash
git fetch origin             # 원격 변경을 받아오되 병합하지 않음
git pull origin main         # fetch + merge
git pull --rebase origin main  # fetch + rebase
```

`fetch`는 원격 상태만 가져오고 내 작업에는 손대지 않는다. `pull`은 fetch한 뒤 자동으로 머지한다. 차이를 모르고 pull만 쓰면 원하지 않는 머지 커밋이 생긴다.

`git pull --rebase`는 머지 커밋 없이 내 커밋을 원격 위로 올린다. 히스토리가 직선으로 유지된다. 단, 이미 push한 커밋을 rebase하면 문제가 되니 아직 push 안 한 로컬 커밋에만 안전하다. 매번 옵션 치기 귀찮으면 기본값으로 설정한다.

```bash
git config --global pull.rebase true
```

### push

```bash
git push origin feature              # feature 브랜치 push
git push -u origin feature           # 추적 설정하며 push (이후 git push만 쳐도 됨)
git push origin --delete feature     # 원격 브랜치 삭제
```

`-u`(`--set-upstream`)는 로컬 브랜치와 원격 브랜치를 연결한다. 한 번 해두면 다음부터 `git push`만 쳐도 된다.

### force push 주의

rebase나 amend로 히스토리를 바꾸면 일반 push가 거부된다. 강제로 덮어써야 하는데 여기서 사고가 난다.

```bash
git push --force origin feature           # 위험
git push --force-with-lease origin feature  # 비교적 안전
```

`--force`는 원격이 어떤 상태든 무조건 덮어쓴다. 내가 마지막으로 본 이후 동료가 push했다면 그 작업이 사라진다. `--force-with-lease`는 내가 알고 있는 원격 상태와 실제 원격이 같을 때만 덮어쓴다. 그 사이 누가 push했으면 거부된다. force push가 필요하면 항상 `--force-with-lease`를 쓴다.

다만 `--force-with-lease`도 만능은 아니다. 직전에 `git fetch`를 했다면 로컬에 기록된 원격 상태가 갱신되어서 동료의 새 커밋을 "내가 아는 상태"로 착각하고 덮어쓸 수 있다. force push 직전에는 fetch하지 않는다.

## 되돌리기

가장 헷갈리는 영역이다. reset, revert, restore가 각각 다른 일을 한다.

### reset

HEAD를 특정 커밋으로 이동시킨다. `--soft`, `--mixed`, `--hard`의 차이가 핵심이다.

```bash
git reset --soft HEAD~1      # 커밋만 취소, 변경은 staged 상태로 유지
git reset --mixed HEAD~1     # 커밋과 staging 취소, 변경은 working tree에 유지 (기본값)
git reset --hard HEAD~1      # 커밋, staging, 변경 전부 삭제
```

세 옵션 모두 HEAD를 한 커밋 뒤로 옮긴다. 차이는 변경 내용을 어디까지 되돌리느냐다.

- `--soft`: 커밋 메시지만 다시 쓰고 싶을 때. 변경은 그대로 staged로 남아서 바로 다시 commit하면 된다.
- `--mixed`: 커밋을 풀고 add도 취소한다. 어떤 파일을 커밋할지 다시 고르고 싶을 때.
- `--hard`: 변경까지 통째로 버린다. 되돌릴 수 없으니 주의한다.

`--hard`로 날린 커밋은 reflog로 복구할 수 있지만, working tree에만 있던 (한 번도 커밋 안 한) 변경은 복구 못 한다. `--hard` 전에는 staged 변경이 있는지 `git status`로 확인한다.

### revert

reset과 달리 히스토리를 지우지 않고, 변경을 취소하는 새 커밋을 만든다.

```bash
git revert HEAD              # 직전 커밋을 취소하는 커밋 생성
git revert abc1234           # 특정 커밋 취소
git revert --no-commit HEAD~3..HEAD  # 여러 커밋 취소를 한 커밋으로
```

이미 push해서 남들이 받아간 커밋을 되돌릴 때는 reset이 아니라 revert를 쓴다. reset으로 히스토리를 바꾸면 force push해야 하고 협업자 모두가 꼬인다. revert는 새 커밋을 추가하는 거라 그냥 push하면 된다.

### restore

파일 단위 복원 전용이다. checkout의 파일 복원 기능을 분리한 명령어다.

```bash
git restore file.js              # working tree 변경 취소 (커밋 상태로)
git restore --staged file.js     # staging만 취소 (변경은 유지)
git restore --source=HEAD~2 file.js  # 특정 커밋 시점으로 복원
```

`git restore file.js`는 수정한 내용을 버리고 마지막 커밋 상태로 되돌린다. 되돌릴 수 없으니 정말 버려도 되는 변경인지 확인한다. `--staged`는 `git add`를 취소하는 용도로, 변경 자체는 남긴다.

### clean

추적되지 않는 파일을 지운다. 빌드 산출물이나 임시 파일이 쌓였을 때 쓴다.

```bash
git clean -n                 # 지워질 파일 미리보기 (실제 삭제 안 함)
git clean -f                 # 추적 안 되는 파일 삭제
git clean -fd                # 디렉토리까지
git clean -fdx               # .gitignore 대상까지 전부
```

`-n`으로 먼저 확인하지 않고 `-f`를 치면 안 된다. `-x`는 .gitignore에 등록된 것까지 다 지우므로 환경설정 파일이나 로컬 캐시가 날아갈 수 있다. 신중하게 쓴다.

## stash

작업 중인데 다른 브랜치로 급히 가야 할 때, 커밋하기는 애매하고 버리기는 아까운 변경을 잠시 치워둔다.

```bash
git stash                    # 변경을 치워두고 깨끗한 상태로
git stash -u                 # 추적 안 되는 파일까지 포함
git stash list               # 저장된 stash 목록
git stash pop                # 가장 최근 stash 적용하고 목록에서 제거
git stash apply              # 적용하되 목록에 남김
git stash drop stash@{0}     # 특정 stash 삭제
git stash show -p stash@{0}  # stash 내용 diff로 보기
```

`pop`은 적용 후 stash를 지우고, `apply`는 남긴다. 같은 stash를 여러 브랜치에 적용할 거면 `apply`를 쓴다.

자주 하는 실수가 있다. 새로 만든 파일(추적 안 되는 파일)은 그냥 `git stash`로는 안 치워진다. `-u`를 붙여야 한다. 안 붙이면 그 파일은 그대로 남아서 브랜치 전환할 때 따라다닌다.

stash에 메시지를 달면 나중에 찾기 쉽다.

```bash
git stash push -m "로그인 폼 작업 중"
```

## rebase -i로 커밋 정리

push하기 전에 지저분한 커밋을 정리한다. wip 커밋 합치기, 메시지 고치기, 순서 바꾸기를 한다.

```bash
git rebase -i HEAD~4         # 최근 4개 커밋 정리
```

에디터가 열리면 각 커밋 앞에 명령어를 적는다.

```
pick   a1b2c3d 로그인 API 추가
squash e4f5g6h wip
squash h7i8j9k 오타 수정
reword k0l1m2n 비밀번호 검증 추가
```

- `pick`: 그대로 둠
- `squash`(`s`): 위 커밋에 합침, 메시지는 합쳐서 편집
- `fixup`(`f`): 위 커밋에 합침, 메시지는 버림
- `reword`(`r`): 커밋은 두고 메시지만 수정
- `drop`(`d`): 커밋 삭제
- 줄 순서를 바꾸면 커밋 순서가 바뀜

wip 커밋 세 개를 의미 있는 커밋 하나로 합칠 때 `squash`나 `fixup`을 쓴다. 메시지를 버려도 되면 `fixup`이 편하다.

이미 push한 커밋을 rebase하면 히스토리가 바뀌어서 force push해야 한다. 공유 브랜치에서는 하지 않는다. rebase는 아직 push 안 한 로컬 커밋에만 쓴다.

### rebase 충돌 해결

rebase 중 충돌이 나면 멈춘다. 충돌 파일을 고친 다음 진행한다.

```bash
# 충돌 파일 수정 후
git add 충돌파일.js
git rebase --continue        # 계속 진행

git rebase --skip            # 현재 커밋 건너뛰기
git rebase --abort           # rebase 전체 취소, 원래 상태로
```

꼬여서 도저히 모르겠으면 `git rebase --abort`로 시작 전 상태로 완전히 되돌린다. 이게 rebase의 안전장치다. continue를 잘못 눌러서 더 꼬이기 전에 abort하고 처음부터 다시 하는 게 빠를 때가 많다.

## cherry-pick

다른 브랜치의 특정 커밋만 골라서 현재 브랜치에 적용한다.

```bash
git cherry-pick abc1234              # 커밋 하나
git cherry-pick abc1234 def5678      # 여러 개
git cherry-pick abc1234..def5678     # 범위 (abc1234 제외, 이후부터)
git cherry-pick -n abc1234           # 적용만 하고 커밋은 안 함
```

핫픽스를 main에 먼저 커밋했는데 release 브랜치에도 넣어야 할 때 쓴다. 해당 커밋 해시만 골라서 cherry-pick한다. 충돌이 나면 rebase와 똑같이 `--continue`, `--abort`로 처리한다.

남발하면 같은 변경이 여러 브랜치에 다른 해시로 복제돼서 나중에 머지할 때 헷갈린다. 정식 머지로 해결할 수 있으면 그쪽을 우선한다.

## reflog로 잃어버린 커밋 복구

reset --hard로 커밋을 날렸거나, 브랜치를 삭제했거나, rebase가 꼬여서 커밋이 사라진 것처럼 보일 때, reflog가 살린다. HEAD가 움직인 모든 기록이 남아있다.

```bash
git reflog                   # HEAD 이동 기록 전체
```

출력이 이렇게 나온다.

```
a1b2c3d HEAD@{0}: reset: moving to HEAD~1
e4f5g6h HEAD@{1}: commit: 중요한 작업
...
```

날린 커밋의 해시(`e4f5g6h`)를 찾았으면 복구한다.

```bash
git reset --hard e4f5g6h         # 그 커밋으로 HEAD 이동
# 또는 새 브랜치로 안전하게 살리기
git branch recovered e4f5g6h
```

reflog 기록은 기본 90일간 유지된다. 커밋한 적이 있는 작업이라면 거의 다 복구할 수 있다. "커밋 날렸다"고 당황하기 전에 reflog부터 본다.

## 잘못 푸시한 경우 수습

### 비밀번호나 키를 커밋해서 push했을 때

가장 급한 상황이다. 단순히 다음 커밋에서 지우는 걸로는 안 된다. 히스토리에 남아있으면 누구나 과거 커밋에서 꺼낼 수 있다.

먼저 노출된 키를 즉시 폐기하고 재발급한다. 이게 1순위다. 히스토리 정리는 그다음이다. 키는 이미 노출됐다고 가정하고 무효화부터 한다.

히스토리에서 제거하려면 `git filter-repo`(권장)나 BFG를 쓴다. `filter-branch`는 느리고 권장되지 않는다.

```bash
git filter-repo --path config/secret.yml --invert-paths
```

이건 전체 히스토리를 다시 써서 force push해야 하고, 그 리포를 clone한 모든 사람이 다시 받아야 한다. 협업 중이면 팀에 먼저 공지한다.

### 잘못된 메시지로 push했을 때

혼자 쓰는 브랜치면 amend 후 force push한다.

```bash
git commit --amend -m "올바른 메시지"
git push --force-with-lease origin feature
```

공유 브랜치면 히스토리를 바꾸지 말고 그냥 둔다. 메시지 하나 때문에 모두를 꼬이게 할 가치는 없다.

### 잘못된 파일을 push했을 때

이미 공유된 상태면 revert로 취소 커밋을 만든다.

```bash
git revert <커밋해시>
git push origin main
```

## .gitignore 이미 추적된 파일 제거

.gitignore에 추가했는데도 계속 변경이 잡히는 경우가 있다. 이미 git이 추적 중인 파일은 .gitignore가 무시하지 않기 때문이다. .gitignore는 추적 안 되는 파일에만 적용된다.

추적을 멈춰야 한다. `--cached`로 working tree의 파일은 두고 git의 추적에서만 뺀다.

```bash
git rm --cached config/local.env       # 파일 하나
git rm -r --cached node_modules        # 디렉토리
git commit -m "추적에서 제외"
```

`--cached` 없이 `git rm`을 하면 실제 파일도 지워진다. 환경설정 파일이라면 로컬 파일까지 날아가니 반드시 `--cached`를 붙인다.

이미 여러 파일이 추적 중이고 .gitignore를 새로 정리했다면, 전체를 한 번에 다시 적용한다.

```bash
git rm -r --cached .
git add .
git commit -m ".gitignore 재적용"
```

이건 추적 목록을 비웠다가 .gitignore를 반영해서 다시 채우는 방식이다. 실제 파일은 안 지워진다.

## 자주 겪는 실수와 해결

### detached HEAD

`git checkout <커밋해시>`나 태그 체크아웃을 하면 detached HEAD 상태가 된다. 특정 브랜치가 아니라 커밋을 직접 가리키는 상태다. 여기서 커밋하면 어느 브랜치에도 속하지 않아서, 브랜치를 옮기는 순간 그 커밋을 잃기 쉽다.

이 상태에서 작업한 게 있으면 브랜치를 만들어서 살린다.

```bash
git switch -c new-branch     # 현재 위치를 새 브랜치로 저장
```

작업한 게 없으면 그냥 원래 브랜치로 돌아가면 된다.

```bash
git switch main
```

detached 상태에서 커밋하고 나서 그냥 브랜치를 옮겨버렸다면, reflog로 그 커밋 해시를 찾아 복구한다.

### 잘못된 브랜치에 커밋했을 때

feature에서 작업해야 하는데 main에서 커밋한 경우다. 아직 push 안 했으면 간단하다. 커밋을 옮긴다.

```bash
# main에 잘못 커밋한 상태
git switch -c feature        # 현재 커밋을 가진 채 새 브랜치 생성
git switch main
git reset --hard origin/main # main을 원격 상태로 되돌림
```

`git switch -c feature`로 커밋을 feature에 복사해두고, main은 원격 상태로 reset해서 잘못 들어간 커밋을 뺀다. main에서 reset --hard 하기 전에 feature 브랜치가 그 커밋을 갖고 있는지 `git log`로 꼭 확인한다.

커밋이 여러 개고 일부만 옮겨야 하면 cherry-pick으로 골라서 옮긴 뒤 main에서 reset한다.

### 머지 충돌

merge나 pull, rebase 중 같은 부분을 양쪽이 고쳤으면 충돌이 난다. git이 멈추고 충돌 파일에 마커를 넣는다.

```
<<<<<<< HEAD
현재 브랜치의 내용
=======
들어오는 브랜치의 내용
>>>>>>> feature
```

`<<<<<<<`, `=======`, `>>>>>>>` 마커 사이를 보고 최종 내용으로 직접 고친다. 마커 세 줄을 전부 지우고 올바른 코드만 남긴다. 그다음 진행한다.

```bash
git add 충돌파일.js          # 해결 표시
git commit                   # merge면 커밋으로 마무리
git rebase --continue        # rebase 중이면 continue
```

어느 쪽 내용을 통째로 채택할지 정해졌으면 마커를 일일이 안 지우고 한쪽을 고를 수 있다.

```bash
git checkout --ours file.js      # 현재 브랜치 쪽 채택
git checkout --theirs file.js    # 들어오는 브랜치 쪽 채택
git add file.js
```

merge에서 `--ours`는 현재 브랜치, `--theirs`는 머지하려는 브랜치다. 단 rebase 중에는 ours와 theirs의 의미가 반대가 된다. rebase는 내 커밋을 상대 위에 다시 올리는 거라 기준이 뒤집힌다. 헷갈리면 마커를 직접 보고 고치는 게 안전하다.

충돌이 너무 많아 감당이 안 되면 멈추고 처음 상태로 돌아간다.

```bash
git merge --abort            # merge 취소
git rebase --abort           # rebase 취소
```

## 알아두면 덜 고생하는 설정

```bash
# 커밋 작성자 정보
git config --global user.name "이름"
git config --global user.email "메일"

# 한글 파일명 깨짐 방지 (macOS에서 자주 필요)
git config --global core.quotepath false

# 자동 줄바꿈 처리 (협업 시 OS 차이 문제 예방)
git config --global core.autocrlf input   # macOS, Linux

# 충돌 시 양쪽뿐 아니라 공통 조상까지 표시 (해결이 쉬워짐)
git config --global merge.conflictstyle zdiff3
```

`merge.conflictstyle`을 `zdiff3`로 바꾸면 충돌 마커에 원래 공통 내용까지 같이 나온다. 양쪽이 각각 뭘 바꿨는지 비교하기 쉬워져서 충돌 해결 시간이 줄어든다. 충돌 자주 겪는다면 이거 하나만 바꿔도 체감이 다르다.
