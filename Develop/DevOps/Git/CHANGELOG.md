---
title: CHANGELOG 작성 규약
tags: [git, devops, ci-cd]
updated: 2026-09-15
---

# CHANGELOG 작성 규약

CHANGELOG는 "무엇이 언제 바뀌었는지"를 사람이 읽을 수 있게 기록한 파일이다. git log와 다른 점은, 커밋 메시지는 개발자가 코드를 보면서 맥락을 떠올릴 때 쓰는 것이고 CHANGELOG는 버전을 선택하거나 업그레이드할 때 사람이 읽는 용도라는 것이다. 같은 정보를 담더라도 독자가 다르다.

[Keep a Changelog](https://keepachangelog.com)가 사실상 표준으로 자리잡은 데는 이유가 있다. 규약을 따르지 않으면 팀마다 날짜 포맷이 제각각이고, 어떤 섹션에 무엇을 넣어야 할지 매번 토론이 생긴다. 규약을 공유하면 그 판단을 생략할 수 있다.

## Keep a Changelog 구조

기본 파일 모양새다.

```markdown
# Changelog

## [Unreleased]

### Added
- 사용자 삭제 API 추가

## [1.3.0] - 2026-08-20

### Added
- 알림 설정 페이지 추가
- 이메일 인증 재전송 기능

### Changed
- 회원 목록 API 응답에 `lastLoginAt` 필드 추가

### Fixed
- 비밀번호 재설정 링크가 만료 후에도 200을 반환하던 문제 수정

## [1.2.1] - 2026-07-15

### Security
- JWT 서명 검증 누락 버그 수정 (CVE-2026-12345)

[Unreleased]: https://github.com/org/repo/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/org/repo/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/org/repo/compare/v1.2.0...v1.2.1
```

버전은 내림차순이다. 최신이 위에 있어야 열었을 때 바로 보인다. 날짜는 반드시 `YYYY-MM-DD` 포맷을 쓴다. `2026.8.20`이나 `Aug 20, 2026` 같은 형식은 파싱이 안 되고 국가마다 다르게 읽힌다.

## 섹션을 나누는 이유

Added / Changed / Deprecated / Removed / Fixed / Security 여섯 가지로 고정된 데는 이유가 있다.

**Added**는 없던 것이 생긴 것이다. 마이그레이션 없이 추가만 되니 기존 사용자에게 영향이 없다.

**Changed**는 기존 동작이 바뀐 것이다. API 응답 필드 이름이 바뀌거나 기본값이 달라지는 것이 여기 들어간다. 업그레이드할 때 코드 수정이 필요할 수 있다.

**Deprecated**는 아직 동작하지만 다음 메이저 버전에서 삭제될 것들이다. 미리 알려서 마이그레이션 시간을 주는 용도다.

**Removed**는 Deprecated였던 것이 실제로 삭제된 것이다. 이것과 Changed를 구분하지 않으면 "삭제된 건지 동작이 바뀐 건지"를 항목만 봐서는 알 수 없다.

**Fixed**는 버그 수정이다. 기존에 잘못 동작하던 것을 바로잡은 것이라 Changed와 다르다. Changed는 의도적인 변경, Fixed는 의도하지 않았던 동작을 고친 것이다.

**Security**는 보안 취약점 수정이다. Fixed와 분리하는 이유는, 보안 팀이나 운영자가 빠르게 찾아야 하기 때문이다. Fixed 안에 섞어두면 보안 패치만 추려내기 어렵다.

이 여섯 가지를 지키면 독자가 항목을 읽기 전에 영향 범위를 예상할 수 있다.

## Unreleased 섹션

아직 릴리즈되지 않은 변경 사항을 모아두는 구역이다. 개발하면서 바로 여기에 기록하면 릴리즈 시점에 CHANGELOG를 새로 쓸 필요가 없다.

릴리즈할 때 과정은 단순하다.

```markdown
## [Unreleased]
↓
## [1.4.0] - 2026-09-15
```

헤더만 바꾸고, 파일 상단에 빈 `[Unreleased]` 섹션을 다시 만들면 된다.

Unreleased를 아예 쓰지 않는 팀도 있다. 이 경우 릴리즈 직전에 커밋 로그를 뒤져서 한꺼번에 정리해야 한다. 작은 팀에서는 이게 가능하지만 배포 직전에 시간이 없을 때 항상 대충 넘어가게 된다. 변경 이력이 중요한 프로젝트라면 개발하면서 Unreleased에 누적하는 편이 낫다.

## git-cliff로 자동 생성

[git-cliff](https://github.com/orhun/git-cliff)는 Conventional Commits 형식의 커밋 메시지를 분석해서 CHANGELOG를 만들어주는 도구다. Rust로 만들어져 있고 단일 바이너리라 설치가 간단하다.

```bash
# 설치 (macOS)
brew install git-cliff

# 설치 (Linux)
curl -sSfL https://raw.githubusercontent.com/orhun/git-cliff/main/install.sh | sh
```

설정 파일 `cliff.toml`을 프로젝트 루트에 만든다.

```toml
[changelog]
header = "# Changelog\n\n"
body = """
{% if version %}
## [{{ version | trim_start_matches(pat="v") }}] - {{ timestamp | date(format="%Y-%m-%d") }}
{% else %}
## [Unreleased]
{% endif %}

{% for group, commits in commits | group_by(attribute="group") %}
### {{ group | upper_first }}
{% for commit in commits %}
- {% if commit.scope %}**{{ commit.scope }}**: {% endif %}{{ commit.message }}\
{% endfor %}
{% endfor %}
"""
trim = true

[git]
conventional_commits = true
filter_unconventional = true
sort_commits = "oldest"

commit_parsers = [
  { message = "^feat", group = "Added" },
  { message = "^fix", group = "Fixed" },
  { message = "^refactor", group = "Changed" },
  { message = "^perf", group = "Changed" },
  { message = "^docs", skip = true },
  { message = "^chore", skip = true },
]
```

```bash
# 전체 CHANGELOG 생성
git cliff -o CHANGELOG.md

# 특정 태그 이후만
git cliff v1.2.0..HEAD -o CHANGELOG.md

# 릴리즈 태그와 함께 최신 섹션만 출력 (CI에서 릴리즈 노트로 쓸 때)
git cliff --latest --strip all
```

한 가지 주의할 점이 있다. `filter_unconventional = true`로 설정하면 `feat:`, `fix:` 같은 접두사가 없는 커밋은 전부 무시된다. 팀 내에 Conventional Commits을 지키지 않는 커밋이 섞여 있으면 CHANGELOG에서 그 변경 사항이 빠진다. 이 설정을 켜기 전에 커밋 히스토리를 한번 확인하는 게 낫다.

## conventional-changelog

Node 기반 프로젝트라면 `conventional-changelog-cli`가 더 자연스럽다.

```bash
npm install -g conventional-changelog-cli

# 마지막 태그 이후 변경 사항 추가
conventional-changelog -p angular -i CHANGELOG.md -s

# 전체 다시 생성
conventional-changelog -p angular -i CHANGELOG.md -s -r 0
```

`-p angular`는 Angular 팀이 쓰는 커밋 형식 파서를 쓴다는 옵션이다. `conventional-changelog-conventionalcommits` 패키지를 쓰면 Conventional Commits 표준에 더 가깝게 동작한다.

```bash
npm install -g conventional-changelog-cli conventional-changelog-conventionalcommits

conventional-changelog -p conventionalcommits -i CHANGELOG.md -s
```

## 수동으로 관리할 때 자주 저지르는 실수들

**날짜 역순 누락.** 습관적으로 파일 아래쪽에 새 항목을 추가하는 경우가 있다. 최신 버전이 가장 아래에 있으면 읽는 사람이 스크롤을 끝까지 내려야 한다. 리뷰에서 잘 안 걸리는 이유는 각자 자기가 추가한 버전만 확인하기 때문이다.

**릴리즈 태그와 불일치.** git tag로 `v1.3.0`을 달았는데 CHANGELOG에는 `[1.3.0]`이 없거나, 반대로 CHANGELOG에는 있는데 태그는 `v1.3.0-rc1`인 경우다. 나중에 "이 변경 사항이 어느 버전에 들어간 건지" 물어보면 누구도 확신하지 못한다.

릴리즈 프로세스를 정할 때 태그 생성과 CHANGELOG 업데이트를 하나의 단계로 묶으면 불일치가 줄어든다.

```bash
# 릴리즈 프로세스 예시
git cliff --tag v1.4.0 -o CHANGELOG.md
git add CHANGELOG.md
git commit -m "chore(release): v1.4.0"
git tag v1.4.0
git push && git push --tags
```

**섹션 혼용.** `Fixed: 불필요한 로그 제거` 같은 항목이 들어간다. 로그 제거는 Fixed가 아니라 Changed다. 버그를 고친 것이 아니기 때문이다. 작성할 때 "이게 의도하지 않았던 동작을 수정한 건가, 아니면 의도적으로 동작을 바꾼 건가"를 물어보면 대부분 구분이 된다.

**Unreleased를 비우지 않고 태그.** 릴리즈 후 `[Unreleased]` 섹션을 빈 채로 두면, 다음 개발 사이클에서 누군가 Unreleased에 항목을 추가했을 때 직전 릴리즈 항목과 뒤섞인다. 릴리즈 직후 빈 `[Unreleased]` 섹션을 만들어두는 걸 루틴으로 만들어야 한다.

## 모노레포에서 패키지별 CHANGELOG 분리

모노레포에서 패키지 A가 바뀌었는데 패키지 B의 CHANGELOG에도 항목이 들어가면 의미가 없다. 각 패키지별로 CHANGELOG를 따로 둔다.

```
packages/
  api-server/
    CHANGELOG.md
    package.json
  auth-service/
    CHANGELOG.md
    package.json
  shared-lib/
    CHANGELOG.md
    package.json
```

git-cliff를 쓰는 경우 커밋 스코프로 필터링할 수 있다.

```toml
# packages/api-server/cliff.toml
[git]
conventional_commits = true
commit_parsers = [
  { message = "^feat\\(api-server\\)", group = "Added" },
  { message = "^fix\\(api-server\\)", group = "Fixed" },
  { message = "^feat\\(shared-lib\\)", group = "Added" },
  { message = ".*", skip = true },
]
```

```bash
# api-server 디렉토리에서 실행
cd packages/api-server
git cliff -o CHANGELOG.md
```

스코프 기반 필터링이 제대로 동작하려면 커밋 메시지에 스코프를 빠짐없이 써야 한다.

```
feat(api-server): 사용자 삭제 API 추가
fix(auth-service): 토큰 갱신 시 race condition 수정
chore(shared-lib): 의존성 버전 업데이트
```

`conventional-changelog`는 패키지별 실행이 더 단순하다.

```bash
cd packages/api-server
conventional-changelog -p conventionalcommits -i CHANGELOG.md -s --commit-path .
```

`--commit-path .`가 현재 디렉토리에 영향을 주는 커밋만 추려준다. 스코프를 쓰지 않아도 파일 경로 기반으로 필터링하기 때문에 기존 커밋 컨벤션을 바꾸지 않아도 된다.

다만 이 방법은 공통 라이브러리 변경이 여러 패키지 CHANGELOG에 중복으로 들어갈 수 있다. `shared-lib`을 수정하는 커밋이 `packages/` 전체에 영향을 주는 것으로 잡히기 때문이다. 이 경우 스코프 기반 필터를 병행해서 공통 라이브러리 변경은 `shared-lib` CHANGELOG에만 들어가게 명시적으로 구분하는 게 낫다.
