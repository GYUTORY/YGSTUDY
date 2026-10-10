---
title: GitHub Actions 워크플로 인젝션
tags: [security, ci-cd, devops, git]
updated: 2026-10-10
---

# GitHub Actions 워크플로 인젝션

## 왜 YAML 한 줄이 명령 실행이 되는가

GitHub Actions의 워크플로는 실행 전에 `${{ }}` 표현식을 **문자열 치환**으로 먼저 펼친다. 쉘 스크립트를 실행하는 `run:` 블록 안에 `${{ }}`를 쓰면, 러너는 그 자리에 값을 그대로 끼워 넣은 뒤 셸에 넘긴다. 즉 표현식 치환은 셸이 변수를 읽는 것보다 **한 단계 앞**에서 일어난다. 이 순서가 인젝션의 전부다.

```yaml
# 취약 — PR 제목이 셸 스크립트에 직접 치환된다
- run: echo "PR 제목: ${{ github.event.pull_request.title }}"
```

러너가 보기 전에 치환이 끝나므로, 제목이 `$(…)`나 백틱이나 `; rm -rf …` 를 담고 있으면 그건 데이터가 아니라 **스크립트의 일부**가 되어 실행된다. 공격자는 코드를 커밋할 필요도 없다. PR 제목·브랜치명·이슈 본문처럼 외부인이 자유롭게 채우는 필드 하나면 된다.

공격자가 조종할 수 있는 입력은 많다.

- `github.event.pull_request.title`, `.body`, `.head.ref`(브랜치명)
- `github.event.issue.title`, `.body`, `.comment.body`
- `github.event.review.body`, `.commits[*].message`, `.commits[*].author.email`

이들의 공통점은 **코드 리뷰를 거치지 않고 저장소에 도달한다**는 것이다.

## pull_request 와 pull_request_target 의 차이가 피해 규모를 가른다

인젝션 자체는 두 트리거에서 다 일어나지만, 손에 들어오는 권한이 다르다.

| 트리거 | 실행 컨텍스트 | GITHUB_TOKEN | 시크릿 접근 |
|---|---|---|---|
| `pull_request` | 포크(PR) 쪽 | 읽기 전용(기본) | 없음 |
| `pull_request_target` | base(대상 저장소) 쪽 | 쓰기 가능 | 있음 |

`pull_request_target`은 포크에서 온 PR을 **대상 저장소의 권한으로** 돌린다. 포크 PR에 대해 라벨을 달거나 코멘트를 남기는 자동화를 만들려고 쓰는데, 바로 그 권한 때문에 여기서 인젝션이 터지면 외부인이 저장소 시크릿과 쓰기 토큰을 그대로 쥔다. 실제 Ultralytics·Nx 공급망 사고가 이 경로였다 — 사례는 [GitHub를 입구로 터진 보안사고](Git_Hub_Security_Incidents.md)에 정리돼 있다.

여기에 더해, `pull_request_target`에서 포크의 코드를 `actions/checkout`으로 받아 빌드·테스트까지 하면 **외부 코드를 특권 컨텍스트에서 실행**하는 것이 되어, 인젝션이 없어도 그 자체로 위험하다.

## 막는 법 — 입력을 셸에 직접 넣지 않는다

### 1. 환경변수를 거친다

가장 확실한 한 가지. `${{ }}`를 `run:`에 직접 쓰지 말고 `env:`로 옮긴 뒤 셸 변수로 참조한다.

```yaml
# 안전 — 치환은 env 값으로만, 셸은 변수를 데이터로 읽는다
- env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: echo "PR 제목: $PR_TITLE"
```

차이는 이렇다. `env:`에 들어간 값은 셸 스크립트 텍스트에 끼워지는 게 아니라 **환경변수로 전달**되고, `"$PR_TITLE"`는 셸이 변수로 읽을 뿐 다시 파싱하지 않는다. 따옴표로 감싸는 것을 잊지 않는다.

### 2. pull_request_target 에서 포크 코드를 체크아웃하지 않는다

꼭 받아야 하면 빌드·실행 없이 데이터로만 다루고, 특권이 필요한 작업과 포크 코드를 만지는 작업을 **별도 워크플로로 분리**한다. GitHub의 권장 패턴은 라벨 승인 후에만 특권 작업을 돌리는 2단계 구성이다.

### 3. 토큰 권한을 최소화한다

워크플로 상단에 기본을 읽기 전용으로 내리고, 필요한 잡에만 필요한 권한을 올린다. 인젝션이 나도 손에 쥐어지는 권한이 작으면 피해가 작다.

```yaml
permissions:
  contents: read   # 기본값을 좁힌다
```

### 4. 발행 토큰을 워크플로 시크릿에 두지 않는다

npm·PyPI 발행 토큰이 워크플로 시크릿에 있으면 인젝션 한 번에 공급망 전체가 넘어간다. OIDC로 클라우드·레지스트리에 단기 자격증명을 받아 쓰고, 장기 토큰을 저장소에 두지 않는다. 이 구조는 [CI/CD 파이프라인 공격](CI_CD_Pipeline_Attacks.md)에서 자세히 다룬다.

### 5. 서드파티 액션을 SHA로 고정한다

`uses: some/action@v3`는 태그라 언제든 내용이 바뀐다. 전체 커밋 SHA로 고정하면 공격자가 태그를 옮겨 악성 코드를 밀어 넣는 경로를 막는다.

```yaml
- uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8  # v4.1.0
```

## 탐지 — 이미 들어온 것을 찾는다

새로 막는 것과 별개로, 지금 저장소에 깔린 워크플로에서 위험 패턴을 뽑아낸다.

- `run:` 블록 안에 `${{ github.event.*.title }}`·`.body`·`.head.ref`·`.comment.body`가 직접 치환되는 곳
- `pull_request_target` 트리거와 `actions/checkout`이 같은 워크플로에 함께 있는 곳
- 태그로만 참조된(`@v1`, `@main`) 서드파티 액션

CI에서 이걸 상시로 잡으려면 전용 린터를 붙인다.

- **actionlint**: 워크플로 문법·표현식 린터. 셸 인젝션 위험 표현식을 경고한다.
- **zizmor**: Actions 보안 전용 정적 분석기. `template-injection`, `dangerous-triggers` 등을 룰로 잡는다.
- **CodeQL**: Actions 워크플로용 쿼리로 인젝션 경로를 추적한다.

이들을 PR 게이트로 걸어두면 새 워크플로가 같은 실수를 들고 들어오는 것을 사람 리뷰 전에 막는다. 탐지 도구 운용은 [SAST / DAST / IAST](Security_Testing_SAST_DAST_IAST.md)와 묶어 두면 관리가 쉽다.

## 정리

표현식 인젝션은 커널 버그나 제로데이가 아니라 **치환 순서에 대한 오해**에서 나온다. `${{ }}`는 러너가 셸을 부르기 전에 텍스트로 펼쳐지고, 그 텍스트에 외부인이 쓸 수 있는 필드가 들어가는 순간 데이터가 코드가 된다. 방어의 핵심 한 줄은 "외부 입력을 `run:`에 직접 치환하지 말고 `env:`를 거쳐 따옴표로 읽어라"다. 나머지(토큰 최소화, SHA 고정, OIDC, 린터)는 그 한 줄이 어쩌다 뚫렸을 때 피해를 줄이는 층이다.

## 참고

- [CI/CD 파이프라인 공격](CI_CD_Pipeline_Attacks.md)
- [GitHub를 입구로 터진 보안사고](Git_Hub_Security_Incidents.md)
- [SAST / DAST / IAST](Security_Testing_SAST_DAST_IAST.md)
- [GitHub Docs — Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [GitHub Security Lab — Keeping your GitHub Actions and workflows secure: Untrusted input](https://securitylab.github.com/resources/github-actions-untrusted-input/)
- [actionlint](https://github.com/rhysd/actionlint) · [zizmor](https://github.com/woodruffw/zizmor)
