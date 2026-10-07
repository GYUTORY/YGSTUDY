---
title: 저장소에 시크릿을 커밋했을 때의 대응
tags: [security, git, devops, iam]
updated: 2026-10-08
---

# 저장소에 시크릿을 커밋했을 때의 대응

`config/secrets.yml`을 커밋했고, 리뷰어가 발견해서 다음 커밋에서 지웠다. PR은 머지됐다. 파일은 `main`의 최신 상태에 없으니 끝난 것처럼 보인다. 그런데 `git log -S`로 찾으면 키가 들어간 커밋이 나오고, 그 커밋의 해시를 URL에 넣으면 파일 내용이 그대로 열린다.

[시크릿 관리](Secrets_Management.md) 문서에 `filter-repo`와 BFG 명령이 짧게 있다. 이 문서는 그 뒤를 잇는다. 히스토리를 정리한 뒤에도 GitHub 쪽에 무엇이 남는지, 그걸 어디까지 지울 수 있는지, 다음에 같은 일이 안 생기게 Push protection과 pre-commit을 어떻게 붙이는지를 다룬다. 이 문서의 git 명령은 전부 임시 저장소에서 실행해 출력을 확인했다. 환경은 git 2.55.0, git-filter-repo 2.47.0, gitleaks 8.30.1, trufflehog 3.99.0이다. `gh api` 호출은 실제 조직이 없어서 실행하지 못했고, GitHub이 공개한 OpenAPI 스펙의 필드명과 값을 대조했다. 가짜 키는 AWS 문서의 `AKIAIOSFODNN7EXAMPLE`을 쓴다.

## 순서는 고정이다

유출을 발견하면 히스토리부터 지우고 싶어진다. 눈에 보이는 문제가 그것이기 때문이다. 순서는 반대다. 키를 죽이는 일이 먼저이고, 히스토리 정리는 그 다음이다.

아래 도식은 발견부터 재발 방지까지의 순서다. 키 폐기와 사용 이력 조회가 히스토리 정리보다 앞에 있고, 이력에서 이미 쓰인 흔적이 나오면 침해 사고 절차로 갈라지는 점을 본다.

```mermaid
flowchart TD
    A["유출 발견"] --> B["키 폐기·회전"]
    B --> C["사용 이력 조회<br/>CloudTrail 등"]
    C --> D{"발견 이전에<br/>쓰인 흔적이 있나"}
    D -->|"있음"| E["침해 사고 절차로 전환<br/>새 IAM 사용자·Role, 데이터 반출 확인"]
    D -->|"없음"| F["히스토리 정리<br/>git filter-repo"]
    E --> F
    F --> G["git push --force --mirror"]
    G --> H["GitHub Support에<br/>캐시 뷰·고아 커밋 제거 요청"]
    H --> I["협업자 재클론<br/>포크 소유자와 협의"]
    I --> J["재발 방지<br/>Push protection, pre-commit"]
```

### 공개 저장소는 몇 분 안에 읽힌다

히스토리 정리를 먼저 하면 안 되는 이유는 작업하는 동안에도 키가 살아 있기 때문이다. 공개 저장소에 AWS 키를 올린 허니팟 실험에서 공격자가 키를 찾아 쓰기 시작하기까지 1분이 걸렸다는 보고가 있다([Comparitech, 2022](https://www.comparitech.com/blog/information-security/github-honeypot/)). Palo Alto Unit 42는 공개 GitHub에 노출한 IAM 자격증명을 공격자가 5분 안에 찾아 썼다고 적었다([Unit 42, 2023](https://unit42.paloaltonetworks.com/malicious-operations-of-exposed-iam-keys-cryptojacking/)). 같은 글에서 AWS가 격리 정책을 붙인 시각 이후 4분이 지나 공격자가 정찰을 시작했다. 자동 격리가 걸렸다고 해서 키가 안전해진 것은 아니다.

두 실험 모두 공개 저장소다. 비공개 저장소는 이 속도로 읽히지 않는다. 하지만 비공개 저장소의 키도 퇴사자의 clone, CI 캐시, 나중에 공개로 바뀌는 경우를 생각하면 폐기 대상이다. 공개/비공개를 따져서 순서를 바꾸지 않는다.

폐기할 때는 "새 키 발급, 서비스에 반영, 옛 키 비활성화" 순으로 한다. 옛 키를 먼저 끄면 서비스가 멈추고, 그러면 사람이 서두르다가 옛 키를 다시 켜는 일이 생긴다. 회전 절차 자체는 [시크릿 관리](Secrets_Management.md)의 로테이션 절을 본다.

### 사용 이력은 폐기 직후에 본다

키를 죽인 다음 그 키로 호출된 기록을 조회한다. AWS면 CloudTrail에서 Access Key ID로 이벤트를 찾는다. 조회 명령과 새 IAM 사용자·Role 확인 명령은 [시크릿 관리](Secrets_Management.md)의 "즉시 해야 할 일" 절에 있다. 유출 시각부터 폐기 시각까지의 구간에서 `ConsoleLogin`, `CreateUser`, `CreateAccessKey`, `AttachUserPolicy`가 보이면 단순 유출이 아니라 침해다. 이 경우 히스토리 정리는 증거 보존이 끝난 뒤로 미룬다. force push로 옛 커밋이 고아가 되면 어떤 파일이 노출됐는지 다시 확인하기 번거로워지기 때문이다.

## 지운 커밋은 어디에 남는가

커밋 하나는 여러 곳에 복제된다. 한 곳에서 지워도 나머지는 그대로다.

```mermaid
flowchart LR
    subgraph LOCAL["내 로컬"]
        L1["작업 저장소<br/>.git/objects"]
        L2["reflog"]
    end
    subgraph TEAM["협업자 로컬"]
        T1["옛 clone"]
    end
    subgraph GH["GitHub"]
        R["원격 저장소<br/>main은 새 히스토리를 가리킴"]
        O["고아 커밋<br/>브랜치는 없지만 해시로 열림"]
        PR["PR 참조<br/>refs/pull/N/head"]
        F["포크<br/>fork 쪽 객체"]
        C["캐시 뷰"]
    end
    L1 -->|"force push --mirror"| R
    R -.->|"옛 객체가 남음"| O
    PR -.->|"force push로 안 바뀜"| O
    F -.->|"원본과 객체 공유"| O
    C -.-> O
    T1 -->|"pull 후 push하면 되살아남"| R
    L2 -.-> L1
```

점선은 "지워지지 않고 남는 경로"다. 실선 중 `force push --mirror`만이 원격의 브랜치를 새 히스토리로 옮긴다. 이 화살표가 고아 커밋(`O`)을 지우지 않는다는 것이 다음 절의 주제다.

### force push는 브랜치를 옮길 뿐 객체를 지우지 않는다

git 저장소에서 참조(ref)와 객체(object)는 분리되어 있다. force push는 `refs/heads/main`이 가리키는 곳을 바꾼다. 옛 커밋 객체는 어떤 ref도 가리키지 않게 될 뿐 디스크에 남아 있다. 임시 저장소로 확인했다. 베어 저장소 `origin.git`을 만들어 5개 커밋을 push하고, 키가 든 커밋(`20b9dd6`)을 filter-repo로 걷어낸 히스토리를 `git push --force --mirror`로 덮어썼다.

```bash
# 서버 쪽(origin.git)에서 옛 커밋이 여전히 있는지 본다
$ git --git-dir=origin.git cat-file -t 20b9dd682e4aada6c0045d9dd98828ec04255598
commit

# 어떤 브랜치에도 속하지 않는다
$ git --git-dir=origin.git branch --contains 20b9dd682e4aada6c0045d9dd98828ec04255598
$

# 그런데 내용은 읽힌다
$ git --git-dir=origin.git show 20b9dd682e4a:config/secrets.yml
aws:
  access_key_id: AKIAIOSFODNN7EXAMPLE
  secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

`branch --contains`가 아무것도 안 내놓는 것이 고아 커밋이다. 브랜치 목록, `git log`, 웹 UI의 커밋 이력에는 나오지 않는다. 해시를 알면 열린다. 이 저장소에서 `git gc --prune=now`를 돌리자 `cat-file`이 `could not get object info`를 냈다. 즉 직접 운영하는 서버라면 gc로 지울 수 있다. GitHub은 그 gc를 우리가 돌릴 수 없고, 그래서 Support에 요청해야 한다.

아래 도식은 force push 전후의 ref와 객체 관계다. `main`은 새 커밋으로 옮겨 가지만 옛 커밋은 어떤 ref에도 안 붙은 채 객체로 남는 점을 본다.

```mermaid
flowchart LR
    subgraph BEFORE["push 전"]
        M1["refs/heads/main"] --> K2["키 제거 커밋"]
        K2 --> K1["키 추가 커밋<br/>20b9dd6"]
        K1 --> K0["초기 커밋"]
    end
    subgraph AFTER["force push 후"]
        M2["refs/heads/main"] --> N1["새 커밋"]
        N1 --> K0N["초기 커밋"]
        O1["고아 커밋 20b9dd6<br/>ref 없음, 객체는 남음"]
    end
    BEFORE -->|"git push --force --mirror"| AFTER
```

같은 시점에 만들어 둔 미러 사본(`fork.git`)은 origin을 gc해도 그대로 `commit`을 반환했다. 포크가 별도의 객체 저장소 사본이라는 비유로 쓰기 좋은 결과다. GitHub 포크의 내부 구현은 이 실험과 다르다. 아래 CFOR 절에서 GitHub이 실제로 어떻게 동작하는지는 Truffle Security의 보고를 따른다.

### 포크와 비공개 전환 (Cross Fork Object Reference)

Truffle Security는 2024년 7월 24일 보고서에서 Cross Fork Object Reference(CFOR)라는 이름을 붙였다. 한 포크가 같은 포크 네트워크의 다른 저장소(비공개나 삭제된 포크 포함)의 데이터에 접근할 수 있는 취약점 부류다. 보고서가 든 세 가지 상황은 이렇다.

| 상황 | 일어나는 일 |
|---|---|
| 포크를 만들어 커밋하고 포크를 삭제 | 삭제한 포크의 커밋이 원본 저장소에서 계속 접근된다 |
| 공개 저장소를 삭제했는데 포크가 있음 | 삭제 전 커밋이 포크에서 계속 접근된다. GitHub이 루트 노드를 하위 포크로 옮긴다 |
| 공개 저장소의 비공개 포크를 두고 운영하다가 공개 | 비공개 포크에만 있던 커밋이 공개 저장소 쪽에서 해시로 열린다 |

커밋 접근은 SHA-1 해시를 아는 경우에 열린다. 짧은 해시는 최소 4자리부터 받아주므로, 보고서는 4자리 SHA-1의 공간이 65,536(16^4)이라 무차별 대입이 가능하다고 적었다. 출처는 [Truffle Security의 보고](https://trufflesecurity.com/blog/anyone-can-access-deleted-and-private-repo-data-github)다. 같은 글은 GitHub이 이를 의도된 설계로 문서화했다고 쓴다.

여기서 실무에 걸리는 결론이 둘이다. 첫째, 저장소를 삭제하거나 비공개로 돌려도 키가 있던 커밋이 사라진다는 보장이 없다. 둘째, 사내에서 공개용과 비공개용을 포크 관계로 운영했다면 비공개 쪽에만 있던 시크릿이 공개 쪽 해시로 읽힐 수 있다. 저장소 삭제를 유출 대응의 마침표로 쓰지 않는다. 키를 폐기한 상태여야 삭제가 의미를 갖는다.

### GitHub Support에 제거를 요청할 때

GitHub 문서는 시크릿이 포함된 커밋이 한 번 푸시되면 침해된 것으로 보라고 한다. 포크가 있으면 거기서 계속 접근되고, 캐시 뷰에서 SHA-1로도 접근된다고 적는다. 정리 순서도 문서에 있다. 로컬에서 `git filter-repo`로 재작성, force push, Support에 캐시 뷰 제거 요청, 협업자 clone 정리, 재발 방지 장치 순이다. 맨 위 순서도와 같은 흐름이다.

Support 요청서에 넣을 정보는 네 가지다.

- 저장소 식별자 (`USERNAME/REPOSITORY`)
- 영향받은 PR 개수
- filter-repo 출력의 `First Changed Commit(s)`
- 고아 LFS 객체가 있으면 그 파일명

`First Changed Commit(s)`는 filter-repo가 `.git/filter-repo/first-changed-commits` 파일에도 적어 둔다. 한 줄에 해시가 둘 있고 앞쪽이 처음으로 바뀐 옛 커밋이다. 이 파일은 filter-repo를 다시 돌리거나 clone을 지우면 없어진다. 요청서를 쓰기 전에 다른 곳에 복사해 둔다.

주의할 점은 GitHub Support가 해 주는 범위다. 문서의 문장은 이렇다. 민감하지 않은 데이터는 지워 주지 않고, 영향받은 자격증명을 회전해서 위험이 해소되는 경우에는 시크릿 제거를 돕지 않을 수 있다고 한다. 키를 폐기하지 않은 채 "지워 달라"고 요청하면 거절당하는 경우가 있다. 폐기 먼저가 순서일 뿐 아니라 요청의 전제 조건이기도 하다.

포크는 Support가 대신 정리해 주지 않는다. 외부 포크 소유자의 저장소를 우리가 강제로 바꿀 수 없다. 포크한 사람에게 연락해서 시크릿이 든 포크를 삭제하거나 정리해 달라고 부탁해야 하고, 응답이 없으면 방법이 없다. 이 지점이 "키 폐기가 유일한 확실한 해결"이라는 말의 근거다. 출처는 [GitHub 문서, Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)다.

아래 도식은 위 설명을 키 폐기 여부로 나눈 것이다. 폐기하지 않은 쪽은 Support 요청이 거절될 수 있고, 포크는 어느 쪽이든 소유자에게 부탁하는 길뿐이다.

```mermaid
flowchart TD
    A["Support에 제거 요청"] --> B{"키를 이미<br/>폐기했나"}
    B -->|"아니오"| C["거절될 수 있음<br/>폐기 먼저"]
    B -->|"예"| D["캐시 뷰·고아 커밋 제거 가능"]
    D --> E{"외부 포크가 있나"}
    E -->|"없음"| F["정리 완료"]
    E -->|"있음"| G["포크 소유자에게 삭제·정리 요청<br/>응답 없으면 방법 없음"]
```

## git filter-repo로 히스토리 정리

아래 도식은 이 절의 전체 흐름이다. 새 clone에서 시작해, 키가 파일 전체인지 한 줄인지에 따라 옵션이 갈리고, 어느 쪽이든 `git log -S`로 확인한 뒤 push하는 순서를 본다.

```mermaid
flowchart TD
    A["정리용 fresh clone"] --> B{"시크릿이<br/>파일 전체인가"}
    B -->|"파일 통째로"| C["--path 파일 --invert-paths"]
    B -->|"소스 속 문자열"| D["--replace-text replacements.txt"]
    C --> E["git log -S --all<br/>키 문자열마다 확인"]
    D --> E
    E --> F{"출력이 비었나"}
    F -->|"아니오"| B
    F -->|"예"| G["git remote -v 확인<br/>git push --force --mirror"]
```

### 실행 전에 걸린 두 가지

`pip install git-filter-repo`로 2.47.0을 설치하고 바로 돌렸을 때 두 번 막혔다.

먼저 작업 중인 저장소에서 돌리면 거부한다.

```text
$ git filter-repo --path config/secrets.yml --invert-paths
Aborting: Refusing to destructively overwrite repo history since
this does not look like a fresh clone.
  (expected at most one entry in the reflog for HEAD)
Note: when cloning local repositories, you need to pass
      --no-local to git clone to avoid this issue.
Please operate on a fresh clone instead.  If you want to proceed
anyway, use --force.
```

`--force`로 뚫을 수 있지만 쓰지 않는다. 작업 디렉터리를 망가뜨리지 않으려고 만든 안전장치이고, 어차피 정리용 clone을 따로 하나 만드는 편이 협업자에게 안내하기도 쉽다. 로컬 경로로 clone 연습을 할 때는 메시지대로 `--no-local`을 붙인다.

두 번째는 git 버전이다. git 2.34.1에서는 filter-repo가 파이썬 예외로 죽었다.

```text
  File "/usr/local/lib/python3.10/dist-packages/git_filter_repo.py", line 3353, in _setup_lfs_orphaning_checks
    a = self._file_info_value.get_contents_by_identifier(b"HEAD:.gitattributes")
  File "/usr/local/lib/python3.10/dist-packages/git_filter_repo.py", line 2939, in get_contents_by_identifier
    assert(line == blobhash+b" missing\n")
AssertionError
```

메시지만 보면 저장소가 망가진 것처럼 읽힌다. git을 2.55.0으로 올리자 같은 저장소에서 같은 명령이 통과했다. Ubuntu 22.04 기본 git이 2.34.1이라 CI 러너나 오래된 개발 서버에서 만나기 쉽다. `AssertionError`가 나오면 저장소를 의심하기 전에 `git --version`부터 본다.

### 파일을 통째로 지울 때

GitHub 문서는 2.47 이상에서 `--sensitive-data-removal` 플래그를 쓰라고 한다. 이 플래그가 있으면 filter-repo가 origin의 모든 ref를 먼저 가져와서 재작성 대상에 넣는다. 실행 로그에 `NOTICE: Fetching all refs from origin to make sure we rewrite`가 찍힌다.

```bash
git clone git@github.com:myorg/myrepo.git cleanup && cd cleanup

# 실행 전
git rev-list --all | wc -l                      # 5
git log -S AKIAIOSFODNN7EXAMPLE --oneline --all
# 4db31eb remove secrets
# 20b9dd6 add config

git filter-repo --sensitive-data-removal \
  --path config/secrets.yml --invert-paths

# 실행 후
git rev-list --all | wc -l                      # 3
git log -S AKIAIOSFODNN7EXAMPLE --oneline --all # 출력 없음
```

커밋이 5개에서 3개로 줄었다. `config/secrets.yml`만 건드린 커밋 두 개(추가한 커밋과 지운 커밋)가 비어서 filter-repo가 버렸기 때문이다. 이 숫자 차이를 이상하게 보지 않으면 된다. 반대로 개수가 그대로인데 `git log -S`가 비었다면 키가 파일 한 곳에만 있었던 것이 아니라 다른 변경과 같은 커밋에 섞여 있었다는 뜻이다.

`git log -S`는 문자열이 추가되거나 제거된 커밋을 찾는다. 그래서 키를 넣은 커밋과 지운 커밋이 둘 다 나온다. 지운 커밋만 보고 "이미 지웠네" 하고 넘어가지 않는다. `--all`을 빼면 현재 체크아웃한 브랜치만 본다. 태그와 다른 브랜치에 키가 남는 경우가 있어서 항상 붙인다.

파일이 이전에 이름이 바뀐 적이 있으면 옛 경로도 `--path`로 따로 넣어야 한다. GitHub 문서의 경고다. `git log --follow --name-only -- config/secrets.yml`로 옛 이름을 먼저 확인한다.

### 소스에 박혀 있는 문자열을 치환할 때

파일 전체를 지울 수 없고 한 줄만 문제인 경우다. 하드코딩한 키가 `src/client.py`에 있고 이후 커밋에서 환경변수로 바꿨다고 하자.

```bash
cat > replacements.txt <<'EOF'
AKIAIOSFODNN7EXAMPLE==>***REMOVED***
wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY==>***REMOVED***
regex:AKIA[0-9A-Z]{16}==>***REMOVED***
EOF

git filter-repo --sensitive-data-removal --replace-text replacements.txt
```

한 줄이 `원문==>대체문` 형식이고, `regex:`로 시작하면 정규식이다. 실행 전 `git log -S AKIAIOSFODNN7EXAMPLE`와 `git log -S wJalrXUtnFEMI`가 둘 다 두 커밋(`use env`와 `s3 client`)을 냈고, 실행 후에는 둘 다 비었다. `git log --all -p -- src/client.py`로 보면 옛 커밋과 새 커밋 모두 `aws_access_key_id="***REMOVED***"`로 바뀌어 있다.

실제 사고에서는 `regex:` 줄을 믿지 말고 리터럴 줄도 같이 넣는다. 정규식이 키 형식 일부만 잡으면(예: 시크릿 키는 `AKIA` 접두어가 없다) 짝이 되는 값이 남는다. 위 예제에서 `regex:AKIA...` 줄만 있었다면 `wJalr...` 시크릿 키 쪽은 그대로 남았을 것이다. 치환 후에는 반드시 시크릿 두 개를 각각 `git log -S`로 확인한다.

### push와 그 뒤

```bash
git push --force --mirror origin
```

브랜치 보호가 걸린 저장소는 이 push가 거부되므로 정리 시간 동안 보호 규칙을 풀어야 한다. `refs/pull/*` 참조는 서버가 갱신을 거부한다. 문서에 따르면 이건 정상이다. 다른 ref가 거부되면 보호 규칙 문제다. PR 참조에 옛 커밋이 붙어 있다는 뜻이므로, 열었던 PR이 있으면 앞의 Support 요청서에 PR 개수를 적는다.

filter-repo는 `--sensitive-data-removal`을 쓰면 origin 설정을 그대로 두고, 플래그 없이 쓰면 origin을 지운다. 플래그 없이 돌린 별도 clone에서 `git remote -v`가 빈 출력이었다. [시크릿 관리](Secrets_Management.md) 문서의 "filter-repo 실행 후 origin이 자동 제거된다"는 설명은 플래그 없이 쓸 때 맞는 말이다. 어느 쪽인지 확인하고 push 하라고 `git remote -v`를 먼저 본다.

### 협업자 재클론

force push가 끝나면 협업자에게 공지가 나가야 한다. 이때 "다시 pull 받으세요"라고 하면 안 된다. 옛 clone에서 `git pull`을 하면 옛 히스토리가 새 히스토리로 합쳐진다. 재현했다. 다른 협업자 역할의 clone에서 로컬 커밋을 하나 만든 뒤 force push 이후 `git pull origin main --no-edit`을 실행했다.

```text
Merge made by the 'ort' strategy.

$ git log -S AKIAIOSFODNN7EXAMPLE --oneline --all
4db31eb remove secrets
20b9dd6 add config

$ git push origin main
   6a50072..4effb99  main -> main
```

push가 fast-forward로 받아들여졌고, 서버에서 `git log -S`를 돌리자 키 커밋 두 개가 다시 나왔다. 몇 시간 들여 정리한 히스토리가 한 명의 `git pull`로 원상복구되는 것이다. 서버는 merge 커밋의 부모에 옛 커밋이 들어 있어도 fast-forward면 그대로 받는다. force push로 서버를 덮어쓴 것과 별개로, 협업자 쪽 push가 되살리는 길은 열려 있다.

아래 도식은 위 재현의 순서다. 정리가 끝난 뒤 협업자의 `git pull`과 `git push`가 옛 커밋을 서버로 되돌려 보내는 부분을 본다.

```mermaid
sequenceDiagram
    participant Cl as 정리 담당
    participant Sv as origin 서버
    participant Co as 협업자 옛 clone
    Cl->>Sv: git push --force --mirror
    Note over Sv: main이 새 히스토리를 가리킴
    Co->>Sv: git pull origin main
    Sv-->>Co: 새 히스토리
    Note over Co: 로컬 옛 커밋과 merge<br/>부모에 키 커밋이 포함됨
    Co->>Sv: git push origin main
    Sv-->>Co: fast-forward로 수락
    Note over Sv: git log -S 에 키 커밋이 다시 나옴
```

가장 단순한 안내는 이렇다.

1. 작업 중이던 로컬 브랜치의 커밋 해시를 따로 적어 둔다(`git log origin/main..HEAD --oneline`).
2. 기존 clone을 지우고 새로 clone한다.
3. 적어 둔 커밋을 `git cherry-pick`으로 옮긴다.

새로 clone하기 어려운 사람은 아래도 된다.

```bash
git fetch origin
git reset --hard origin/main         # 로컬 변경은 먼저 stash나 별도 브랜치로 옮긴다
git reflog expire --expire=now --all
git gc --prune=now
```

`reset --hard`만 하면 옛 객체가 reflog에 남는다. 이 clone에서 `git cat-file -t <옛 해시>`가 `reset` 직후에는 `commit`을 반환했고, `reflog expire`와 `gc --prune=now`를 돌린 뒤에는 `could not get object info`가 나왔다. 디스크 위의 사본을 지우는 것까지 안내해야 한다. 사본이 남아 있으면 어느 날 누군가 `git push origin <옛 브랜치>`나 `git push --all`로 되살린다.

## Secret scanning과 Push protection

사고 이후에 할 일은 같은 일이 반복되지 않게 막는 것이다. GitHub은 이를 두 단계로 제공한다. Secret scanning은 저장소에 이미 들어간 시크릿을 찾아 알림을 만들고, Push protection은 push 시점에 시크릿이 든 커밋을 서버가 거절한다. 사고 이후에는 후자가 더 중요하다. 알림은 이미 들어간 뒤에 오지만 거절은 들어가기 전에 막는다.

### 조직 단위로 켜기

저장소마다 설정 화면에서 켜면 새 저장소가 빠진다. 조직의 code security configuration을 만들어 모든 저장소에 붙이는 방식이 낫다. OpenAPI 스펙에서 `POST /orgs/{org}/code-security/configurations`의 필수 필드는 `name` 하나이고, 시크릿 관련 필드는 각각 `enabled`, `disabled`, `not_set` 중 하나를 받는다.

```bash
gh api -X POST /orgs/myorg/code-security/configurations --input - <<'EOF'
{
  "name": "secrets-baseline",
  "description": "Secret scanning과 Push protection",
  "secret_scanning": "enabled",
  "secret_scanning_push_protection": "enabled",
  "secret_scanning_validity_checks": "enabled",
  "secret_scanning_non_provider_patterns": "enabled",
  "enforcement": "enforced"
}
EOF
```

응답에 `id`가 있다. 이 값으로 기존 저장소에 붙이고, 새 저장소의 기본값도 정한다.

```bash
CONFIG_ID=123456

# 기존 저장소 전부에 적용. scope: all | all_without_configurations | public | private_or_internal | selected
gh api -X POST /orgs/myorg/code-security/configurations/$CONFIG_ID/attach -f scope=all

# 앞으로 만드는 저장소의 기본값. all | none | private_and_internal | public
gh api -X PUT /orgs/myorg/code-security/configurations/$CONFIG_ID/defaults -f default_for_new_repos=all
```

`all_without_configurations`는 이미 다른 설정을 붙인 저장소를 건드리지 않는다. 처음 적용할 때는 이 값이 안전하다. 이 호출들을 실제 조직에서 실행하지 못했다. 플랜별로 어떤 기능이 열리는지(특히 비공개 저장소)는 조직 설정 화면에서 확인해야 한다.

아래 도식은 위 세 호출의 관계다. 설정 하나를 만들고, 같은 `id`로 기존 저장소(`attach`)와 새 저장소(`defaults`)에 따로 붙이는 점을 본다.

```mermaid
flowchart LR
    A["POST configurations<br/>name, secret_scanning,<br/>push_protection"] --> B["응답의 id<br/>CONFIG_ID"]
    B --> C["POST attach<br/>scope"]
    B --> D["PUT defaults<br/>default_for_new_repos"]
    C --> E["기존 저장소"]
    D --> F["앞으로 만드는 저장소"]
```

`secret_scanning_non_provider_patterns`는 서비스 제공사 형식이 아닌 일반 패턴(비밀번호 문자열 같은 것)을 잡는다. 오탐이 늘어서 팀이 불평하는 것이 이 항목이다. 처음에는 `disabled`로 두고 `secret_scanning`과 `push_protection`부터 켠 뒤 늘리는 쪽이 낫다.

### 커스텀 패턴

GitHub이 알아보는 것은 파트너 서비스의 토큰 형식이다. 사내 API 키, 데이터 서버 접속 문자열 같은 것은 직접 정규식을 써서 등록해야 한다. [GitHub를 입구로 터진 보안사고](Git_Hub_Security_Incidents.md)의 Toyota 사례가 이 경우다.

조직 단위 API는 `POST /orgs/{org}/secret-scanning/custom-patterns`이고 한 번에 100개까지 만든다. 필드는 `name`, `pattern`(필수), `start_delimiter`, `end_delimiter`, `must_match`, `must_not_match`다. 구분자 기본값은 앞이 `\A|[^0-9A-Za-z]`, 뒤가 `\z|[^0-9A-Za-z]`다.

```bash
gh api -X POST /orgs/myorg/secret-scanning/custom-patterns --input - <<'EOF'
{
  "patterns": [
    {
      "name": "myorg internal api key",
      "pattern": "int_(live|test)_[0-9a-zA-Z]{32}",
      "must_not_match": ["0{8,}", "x{8,}", "X{8,}", "(?i)example"]
    }
  ]
}
EOF
```

`must_not_match`가 오탐 줄이는 장치다. 위 정규식을 파이썬 `re`로 확인했다(GitHub의 정규식 엔진과 문법 차이가 있을 수 있어서 `(?i)` 같은 플래그는 실제 등록 전에 dry run으로 본다).

| 입력 | 패턴 매치 | must_not_match에 걸림 |
|---|---|---|
| `int_live_aB3dE5gH7jK9mN1pQ3sT5vX7zA9cE1gH` | 예 | 아니오 (탐지) |
| `int_live_00000000000000000000000000000000` | 예 | 예 (제외) |
| `int_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | 예 | 예 (제외) |
| `int_live_abc` | 아니오 | |

UI에서 만들 때는 등록 전에 dry run을 돌려야 한다. dry run은 알림을 만들지 않고 저장소에서 매치되는 것을 최대 1,000건까지 보여 준다. 정규식을 쓰자마자 push protection까지 켜지 말고 dry run으로 오탐을 본다. GitHub 문서도 흔히 발견되는 커스텀 패턴에 push protection을 켜면 기여자에게 방해가 될 수 있다고 경고한다([Defining custom patterns](https://docs.github.com/en/code-security/secret-scanning/using-advanced-secret-scanning-and-push-protection-features/custom-patterns/defining-custom-patterns-for-secret-scanning)).

### 우회 요청과 승인 흐름

push가 거절되면 터미널에 시크릿 종류, 커밋 해시, 파일 경로와 줄 번호가 출력되고 우회용 URL이 나온다. 이 URL은 push를 시도한 본인만 열 수 있다(다른 사람은 404). 사유는 세 가지 중에서 고른다.

- It's used in tests
- It's a false positive
- I'll fix it later

사유를 고르면 3시간 동안 같은 push를 다시 시도할 수 있다. 세 번째 사유("나중에 고치겠다")를 쉽게 고를 수 있게 두면 우회 버튼이 습관이 된다. 조직 설정에서 위임 우회(delegated bypass)를 켜면 개발자가 직접 푸는 대신 승인자에게 요청하는 흐름이 된다. 설정 필드는 `secret_scanning_delegated_bypass: "enabled"`와 `secret_scanning_delegated_bypass_options.reviewers`다. 승인자는 팀(`TEAM`) 또는 역할(`ROLE`)의 ID로 지정한다.

```mermaid
sequenceDiagram
    participant Dev as 개발자
    participant GH as GitHub
    participant Rev as 승인자
    Dev->>GH: git push
    GH-->>Dev: 거절(시크릿 종류, 커밋, 줄, 요청 URL)
    Dev->>GH: 우회 요청(왜 안전한지 코멘트)
    GH->>Rev: 검토 요청
    Rev->>GH: 승인 또는 거부
    GH-->>Dev: 이메일로 결과 통지
    alt 승인
        Dev->>GH: git push 재시도(해당 커밋과 같은 시크릿은 통과)
    else 거부
        Dev->>Dev: 시크릿 제거 후 다시 커밋
    end
```

승인된 요청은 해당 커밋과 같은 시크릿이 이후 다시 나와도 통과한다. 거부되면 시크릿을 지우고 다시 커밋해야 한다. 승인자가 보는 것은 "왜 안전한가"에 대한 개발자의 코멘트뿐이라서, 코멘트가 "테스트용"처럼 한 줄이면 승인 담당자가 키를 직접 열어 확인하는 수고를 진다. 승인 팀은 보안팀 한 곳으로 몰지 말고 서비스 오너 팀에도 나눠 둔다. 모든 요청이 한 곳에 몰리면 며칠씩 걸리고, 그러면 개발자는 "나중에 고치겠다"를 고르고 만다. 출처는 [GitHub 문서, Working with push protection from the command line](https://docs.github.com/en/code-security/secret-scanning/working-with-secret-scanning-and-push-protection/working-with-push-protection-from-the-command-line)이다.

우회 사유를 API로 기록하는 엔드포인트(`POST /repos/{owner}/{repo}/secret-scanning/push-protection-bypasses`)도 있다. 필수 필드는 `reason`과 `placeholder_id`다. 직접 만든 도구에서 쓰지 않을 거면 신경 쓰지 않아도 된다.

## 커밋 전에 막기

Push protection은 서버에서 막는다. 로컬에서 먼저 막으면 개발자가 거절당하기 전에 알고, 커밋 히스토리에 키가 남을 일이 없다. 이 절은 gitleaks와 trufflehog를 같은 임시 저장소에서 돌려 본 결과다.

### gitleaks 훅

`.pre-commit-config.yaml`에 gitleaks 저장소를 `repo`로 지정하면 pre-commit이 gitleaks를 Go로 빌드한다. Go 툴체인이 없는 장비에서는 실패한다. 바이너리를 미리 설치해 두고 로컬 훅으로 부르는 방식이 설치 문제를 줄인다.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: gitleaks
        name: gitleaks (staged)
        entry: gitleaks git --pre-commit --staged --redact --no-banner -v
        language: system
        pass_filenames: false
```

[시크릿 관리](Secrets_Management.md)에 있는 `gitleaks protect --staged`는 8.30.1의 도움말 명령 목록에 없다. 현재 명령은 `gitleaks git --pre-commit --staged`다. 이 훅으로 키가 든 파일을 커밋하자 이렇게 막혔다.

```text
gitleaks (staged)........................................................Failed
- hook id: gitleaks
- exit code: 1
Finding:     ...ws_access_key_id = "REDACTED
Secret:      REDACTED
RuleID:      aws-access-token
File:        a.py
Line:        1
Fingerprint: a.py:aws-access-token:1
```

`--redact`를 붙이면 터미널에 시크릿 원문이 안 찍힌다. CI 로그에 평문 시크릿이 남는 사고가 의외로 많아서 CI에서도 붙인다.

여기서 두 가지를 겪었다.

**AWS 문서의 예시 키는 탐지되지 않는다.** `AKIAIOSFODNN7EXAMPLE`을 커밋한 저장소에 `gitleaks git .`을 돌리면 `3 commits scanned. no leaks found`가 나온다. 기본 규칙이 `EXAMPLE`이 들어간 값을 걸러낸다. 이 문서의 예제 키를 가지고 스캐너 테스트를 하면 "정상 동작"이 아니라 "탐지 실패"로 오해하기 쉽다. 마지막 글자를 바꾼 `AKIAIOSFODNN7EXAMPL3`으로 바꾸자 `aws-access-token` 규칙으로 탐지됐다. 스캐너가 제대로 도는지 보려면 `EXAMPLE`을 피한 가짜 값을 따로 둔다.

**`SKIP=gitleaks`와 `--no-verify`는 흔적 없이 우회된다.** 위 훅은 `SKIP=gitleaks git commit`으로 한 줄에 건너뛴다(`gitleaks (staged)....Skipped`). 로컬 훅은 개발자가 끄면 끝이다. 그래서 로컬 훅만으로는 안 되고, 서버의 Push protection과 CI 스캔이 뒤에 있어야 한다. 로컬 훅의 목적은 "서버에서 거절당하기 전에 알리는 것"이다.

아래 도식은 커밋 하나가 거치는 세 겹의 방어선이다. 로컬 훅은 `SKIP`이나 `--no-verify`로 건너뛸 수 있고, 그 경우 서버의 Push protection과 CI 스캔이 남는 점을 본다.

```mermaid
flowchart LR
    A["git commit"] --> B{"pre-commit<br/>gitleaks 훅"}
    B -->|"탐지"| X1["커밋 차단"]
    B -->|"통과"| C["git push"]
    B -.->|"SKIP, --no-verify"| C
    C --> D{"Push protection<br/>서버"}
    D -->|"탐지"| X2["push 거절<br/>우회 요청 흐름"]
    D -->|"통과"| E["저장소 반영"]
    E --> F{"CI 스캔<br/>gitleaks, trufflehog"}
    F -->|"탐지"| X3["빌드 실패"]
    F -->|"통과"| G["머지 가능"]
```

속도도 쟀다. 이 샌드박스(4코어)에서는 파일이 한 줄이어도 `gitleaks git`과 `gitleaks dir`이 17~18초 걸렸고 user 시간이 같은 값이었다. 규칙을 `--enable-rule aws-access-token` 하나로 줄여도 16.9초였다. 시작 비용이 큰 환경이라는 뜻인데 원인은 확인하지 못했다. `gitleaks version`은 0.3초다. 팀 장비에서 `time gitleaks git --pre-commit --staged`를 재 보고, 커밋마다 몇 초 이상 걸리면 훅 대신 CI로 옮기는 것을 고려한다. 느린 훅은 `SKIP`으로 제일 먼저 꺼진다.

### trufflehog

trufflehog는 탐지 후 서비스에 실제로 키를 보내 유효한지 검증하는 점이 gitleaks와 다르다. 가짜 키는 검증이 실패하므로 `--only-verified`로는 안 나온다.

```bash
# 검증 없이 모든 탐지를 본다
trufflehog git file://. --no-verification --since-commit HEAD~1

# 검증된 것만. 가짜 키는 0건이고 종료 코드도 0이다
trufflehog git file://. --only-verified --fail
```

가짜 GitHub 토큰(`ghp_` 뒤 36자)을 커밋한 저장소에서 `--no-verification`으로 `Detector Type: Github`, 파일, 줄 번호가 나왔다. `--only-verified --fail`은 같은 저장소에서 아무 출력 없이 종료 코드 0이었다. `--no-verification --fail`은 183을 반환했다. CI에서 `--only-verified`만 쓰면 이미 폐기된 키는 영원히 통과한다. 유출된 뒤 폐기한 키가 히스토리에 남아 있어도 CI는 조용하다. 히스토리 청소가 끝났는지 확인하는 용도라면 `--no-verification`으로 돌려야 한다.

같은 임시 저장소에서 `AKIA...EXAMPL3` 키는 `--no-verification`으로도 trufflehog가 내놓지 않았다. 탐지기마다 검증 없이 보고하는 규칙이 다른 것으로 보이는데, 원인을 파지는 않았다. gitleaks와 trufflehog 중 하나만 쓰면 놓치는 형식이 있을 수 있다.

### 오탐 때문에 팀이 꺼버릴 때

훅이나 CI 스캔이 꺼지는 가장 흔한 계기는 오탐 한두 건이다. 테스트 픽스처에 든 가짜 토큰이 걸려서 PR이 막히고, 누군가 임시로 `|| true`를 붙이고, 그 상태가 몇 달 간다. 막지 말고 오탐을 줄이는 쪽으로 간다. gitleaks로 확인한 방법 세 가지다.

아래 도식은 오탐의 성격에 따라 어느 방법을 고르는지다. 범위가 넓을수록 진짜 유출까지 가리기 쉬워서 아래로 갈수록 좁은 방법이다.

```mermaid
flowchart TD
    A["오탐 발생"] --> B{"어디까지<br/>허용할 것인가"}
    B -->|"경로·값 전체"| C["설정 파일 allowlists<br/>paths, targetRules, regexes"]
    B -->|"코드 한 줄"| D["줄 끝 주석<br/>gitleaks:allow"]
    B -->|"이미 있는 히스토리"| E["baseline.json<br/>새로 생긴 탐지만 보고"]
    C --> F["규칙 약화<br/>CODEOWNERS 승인 필수"]
    D --> F
    E --> F
```

**설정 파일에서 경로와 값을 제외한다.** 8.30.1에서 `[[allowlists]]`(복수형) 테이블이 동작했다. 기본 규칙을 유지하고 커스텀 규칙을 더하는 `[extend] useDefault = true`와 같이 쓴다.

```toml
# .gitleaks.toml
title = "myorg gitleaks"

[extend]
useDefault = true

[[rules]]
id = "myorg-internal-api-key"
description = "사내 API 키"
regex = '''int_(live|test)_[0-9a-zA-Z]{32}'''
keywords = ["int_live_", "int_test_"]

[[allowlists]]
description = "테스트 픽스처와 문서"
paths = ['''(^|/)testdata/''', '''^docs/''', '''\.md$''']

[[allowlists]]
description = "문서용 예시 키"
targetRules = ["aws-access-token"]
regexes = ['''AKIAIOSFODNN7EXAMPL3''']
```

이 설정으로 사내 키 문자열이 든 `b.py`는 `myorg-internal-api-key`로 탐지됐고, `testdata/t.py`, `docs/x.md`, 예시 키가 든 `a.py`는 걸리지 않았다. `targetRules`를 쓰면 "이 값은 이 규칙에서만 제외"가 되어 다른 규칙의 탐지까지 가리지 않는다. 경로 제외는 넓게 잡을수록 진짜 유출도 가린다. `docs/` 아래에 실수로 넣은 진짜 키는 이 설정으로 영원히 통과한다.

**줄 단위로 허용한다.** 코드 줄 끝에 `# gitleaks:allow`를 붙이면 그 줄만 제외된다. 위 설정에서 `c.py`에 사내 키 형식 값과 이 주석을 같이 넣었더니 탐지되지 않았다. 코드 리뷰에서 눈에 띄는 형태라서 경로 제외보다 낫다.

**기존 히스토리는 baseline으로 묻는다.** 이미 있는 탐지 때문에 새 스캔이 매번 실패하면 아무도 안 본다. 현재 상태를 리포트로 저장하고 다음부터는 새로 생긴 것만 본다.

```bash
gitleaks git . -r baseline.json            # 현재 탐지를 저장
gitleaks git . -b baseline.json            # baseline에 없는 것만 보고
```

baseline을 만든 뒤 새 커밋에 키를 하나 넣었더니 `-b baseline.json`에서 그 커밋의 `n.py`만 보고됐고, 기존 탐지는 `no leaks found`로 가려졌다. baseline은 "나중에 청소할 빚의 목록"이다. 파일로 저장소에 두고, 폐기·정리가 끝난 항목을 주기적으로 빼야 의미가 있다.

세 방법 모두 규칙을 약하게 하는 변경이다. 규칙 파일(`.gitleaks.toml`)과 baseline은 코드 리뷰 대상에 넣고, CODEOWNERS로 보안 담당이 승인하게 해 둔다. 개발자가 자기 PR에서 자기 오탐을 자기가 허용하게 두면 규칙이 서서히 구멍이 난다.

## 출처

- [Comparitech, GitHub honeypot 실험 (2022-07-10)](https://www.comparitech.com/blog/information-security/github-honeypot/) 공개 저장소에 올린 AWS 키가 1분 만에 발견되어 쓰이기 시작했다.
- [Palo Alto Unit 42, CloudKeys in the Air (2023-10-30)](https://unit42.paloaltonetworks.com/malicious-operations-of-exposed-iam-keys-cryptojacking/) 노출된 IAM 자격증명을 5분 안에 공격자가 찾아 사용했다.
- [Truffle Security, Anyone can access deleted and private repo data on GitHub (2024-07-24)](https://trufflesecurity.com/blog/anyone-can-access-deleted-and-private-repo-data-github) Cross Fork Object Reference.
- [GitHub Docs, Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [GitHub Docs, Working with push protection from the command line](https://docs.github.com/en/code-security/secret-scanning/working-with-secret-scanning-and-push-protection/working-with-push-protection-from-the-command-line)
- [GitHub Docs, Defining custom patterns for secret scanning](https://docs.github.com/en/code-security/secret-scanning/using-advanced-secret-scanning-and-push-protection-features/custom-patterns/defining-custom-patterns-for-secret-scanning)
- [GitHub REST API OpenAPI 설명](https://github.com/github/rest-api-description) `code-security/configurations`와 `secret-scanning/custom-patterns` 필드 대조에 썼다.

관련 문서는 [시크릿 관리](Secrets_Management.md), [보안 사고 대응 절차](Incident_Response.md), [GitHub를 입구로 터진 보안사고](Git_Hub_Security_Incidents.md), [SSH 키 라이프사이클 관리](SSH_Key_Management.md)다.
