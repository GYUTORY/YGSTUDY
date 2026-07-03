---
title: "CodeSight --wiki"
tags: [ai, codesight, wiki, documentation, cli]
updated: 2026-04-10
---

# CodeSight --wiki

## 1. CodeSight란

코드베이스를 분석해서 문서를 자동 생성하는 CLI 도구다. `--wiki` 플래그를 붙이면 프로젝트 구조, 모듈 의존성, 주요 클래스/함수 설명을 마크다운 위키 형태로 뽑아준다.

신규 입사자 온보딩이나, 문서가 없는 레거시 프로젝트를 빠르게 파악할 때 쓴다. 수동으로 README를 쓰는 것보다 초기 뼈대를 잡는 데 시간이 적게 든다.

---

## 2. 설치

### 2.1 npm

```bash
npm install -g codesight
```

### 2.2 버전 확인

```bash
codesight --version
```

Node.js 18 이상이 필요하다. 16에서 돌리면 `SyntaxError: Unexpected token` 에러가 나니 주의해야 한다.

---

## 3. --wiki 기본 사용법

### 3.1 가장 단순한 형태

프로젝트 루트에서 실행한다.

```bash
codesight --wiki
```

현재 디렉토리를 분석해서 `wiki/` 폴더에 마크다운 파일을 생성한다.

### 3.2 출력 디렉토리 지정

```bash
codesight --wiki --output ./docs/wiki
```

`--output` 없이 실행하면 프로젝트 루트에 `wiki/` 디렉토리가 생긴다. `.gitignore`에 추가할지 말지는 팀 상황에 따라 판단한다.

### 3.3 생성되는 파일 구조

```
wiki/
├── index.md              # 프로젝트 개요, 모듈 목록
├── architecture.md       # 디렉토리 구조, 의존성 그래프
├── modules/
│   ├── auth.md           # auth 모듈 설명
│   ├── api.md            # api 모듈 설명
│   └── database.md       # database 모듈 설명
├── classes/
│   ├── UserService.md    # 클래스별 상세
│   └── OrderRepository.md
└── _sidebar.md           # 네비게이션 사이드바
```

`index.md`에 전체 구조가 요약되고, 각 모듈/클래스별로 개별 파일이 생긴다. 프로젝트 규모에 따라 파일 수가 크게 달라진다. 클래스 200개짜리 프로젝트에서 돌리면 파일이 200개 넘게 나올 수 있다.

---

## 4. 설정 파일 (.codesight.yml)

프로젝트 루트에 `.codesight.yml`을 두면 분석 범위와 출력 형태를 제어할 수 있다.

### 4.1 기본 설정

```yaml
wiki:
  output: ./docs/wiki
  title: "My Project Wiki"
  language: ko           # 생성 언어 (ko, en, ja 등)
  depth: 3               # 디렉토리 탐색 깊이
  
ignore:
  - node_modules
  - dist
  - "**/*.test.ts"
  - "**/*.spec.ts"
  - coverage
  - .git

modules:
  groupBy: directory     # directory | package | custom
```

### 4.2 주요 설정값

**`wiki.depth`**: 기본값 3이다. 모노레포처럼 디렉토리가 깊은 프로젝트에서는 5~6으로 올려야 하위 모듈까지 잡힌다. 너무 높게 잡으면 분석 시간이 급격히 늘어난다.

**`wiki.language`**: `ko`로 설정하면 한국어로 생성하는데, 클래스명이나 함수명은 영문 그대로 유지된다. 설명 문장만 한국어로 바뀐다.

**`ignore`**: glob 패턴을 지원한다. 테스트 코드, 빌드 결과물, 설정 파일 등 위키에 넣을 필요 없는 파일은 여기서 빼야 한다. 빼지 않으면 테스트 헬퍼 클래스까지 전부 문서화되어서 노이즈가 심해진다.

**`modules.groupBy`**: 모듈을 어떤 기준으로 묶을지 결정한다.

- `directory`: 디렉토리 기준 (기본값)
- `package`: package.json 또는 build.gradle 단위
- `custom`: `.codesight.yml`에서 직접 그룹 정의

### 4.3 커스텀 모듈 그룹 정의

```yaml
modules:
  groupBy: custom
  groups:
    - name: "인증/인가"
      paths:
        - src/auth
        - src/middleware/auth
    - name: "주문 처리"
      paths:
        - src/order
        - src/payment
        - src/shipping
```

비즈니스 도메인 기준으로 묶고 싶을 때 쓴다. 디렉토리 구조가 도메인과 안 맞는 레거시 프로젝트에서 유용하다.

---

## 5. 모노레포 / 멀티모듈 프로젝트

### 5.1 모노레포에서 실행

모노레포 루트에서 그냥 실행하면 모든 패키지를 하나의 위키로 합쳐버린다. 패키지별로 분리하려면 `--scope` 플래그를 쓴다.

```bash
# 특정 패키지만 위키 생성
codesight --wiki --scope packages/api

# 여러 패키지 동시 지정
codesight --wiki --scope packages/api --scope packages/web
```

### 5.2 멀티모듈 Gradle/Maven 프로젝트

```bash
# 루트에서 실행하면 전체 모듈 대상
codesight --wiki

# 특정 모듈만
codesight --wiki --scope modules/core
```

설정 파일로 모듈 간 의존성 표시를 제어할 수 있다.

```yaml
wiki:
  showDependencyGraph: true
  dependencyDepth: 2        # 의존성 몇 단계까지 표시할지
```

### 5.3 모노레포에서 자주 겪는 문제

**분석 시간이 오래 걸리는 경우**: 패키지가 20개 넘는 모노레포에서 전체를 한 번에 돌리면 수십 분 걸릴 수 있다. `--scope`로 범위를 좁히거나, CI에서 병렬로 각 패키지별 위키를 생성하는 방식이 현실적이다.

**공유 모듈 참조 문제**: `packages/shared`를 여러 패키지에서 참조하는 구조일 때, scope를 하나만 지정하면 shared 모듈의 타입이나 유틸이 "외부 의존성"으로 표시된다. 이 경우 shared를 scope에 같이 포함시켜야 한다.

```bash
codesight --wiki --scope packages/api --scope packages/shared
```

---

## 6. 생성된 위키의 한계점

### 6.1 비즈니스 로직 설명이 부정확한 경우

코드 구조와 시그니처 기반으로 설명을 생성하기 때문에, "왜 이렇게 구현했는지"는 모른다. 예를 들어 `calculateDiscount()` 메서드의 할인 정책이 어떤 비즈니스 규칙에서 나온 건지는 코드만 봐서 알 수 없다.

이런 부분은 생성 후 수동으로 보정해야 한다.

### 6.2 주석이 없는 코드

JSDoc이나 Javadoc 같은 주석이 있으면 그걸 참고해서 설명을 만든다. 주석이 없는 코드는 메서드명과 파라미터명만으로 추론하는데, 약어가 많거나 네이밍이 불분명한 코드에서는 엉뚱한 설명이 나온다.

```java
// 이런 코드는 설명이 제대로 나옴
public User findUserByEmail(String email) { ... }

// 이런 코드는 추론이 틀릴 가능성이 높음
public List<Map<String, Object>> proc(int t, boolean f) { ... }
```

### 6.3 동적 타입 언어의 한계

TypeScript처럼 타입 정보가 있으면 분석 정확도가 높다. Python이나 JavaScript(바닐라)는 타입 추론이 안 되는 부분에서 "unknown type" 같은 표시가 생기거나, 실제와 다른 타입으로 문서화되는 경우가 있다.

### 6.4 수동 보정이 필요한 케이스 정리

| 상황 | 증상 | 보정 방법 |
|------|------|-----------|
| 비즈니스 로직 | 기술적 설명만 있고 비즈니스 맥락 없음 | 도메인 설명 직접 추가 |
| 약어 변수명 | 잘못된 설명 생성 | 해당 클래스/메서드 설명 수정 |
| 동적 타입 | 타입 정보 누락 또는 오류 | 타입 정보 수동 명시 |
| 내부 컨벤션 | 팀 고유 패턴을 일반적으로 해석 | 컨벤션 관련 설명 추가 |
| 인프라 코드 | Terraform/k8s 매니페스트 분석 부정확 | 인프라 구성 별도 문서화 |

---

## 7. CI 파이프라인 연동

### 7.1 GitHub Actions 예시

```yaml
name: Generate Wiki
on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - '.codesight.yml'

jobs:
  wiki:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - run: npm install -g codesight
      
      - run: codesight --wiki --output ./wiki
      
      - name: Commit wiki
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add wiki/
          git diff --cached --quiet || git commit -m "docs: update wiki"
          git push
```

### 7.2 CI 연동 시 주의사항

**실행 시간 관리**: 대규모 프로젝트에서 매 푸시마다 위키를 재생성하면 CI 시간이 늘어난다. `paths` 필터로 소스 코드 변경이 있을 때만 트리거하는 게 맞다. 문서만 수정했는데 위키가 재생성될 필요는 없다.

**diff 체크 필수**: `git diff --cached --quiet` 없이 커밋하면, 변경 사항이 없는데도 빈 커밋이 생긴다. 워크플로우에서 항상 변경 여부를 체크해야 한다.

**브랜치 분리**: 위키 결과물을 main에 직접 커밋하면 PR 리뷰 히스토리가 지저분해진다. `docs/wiki` 같은 별도 브랜치에 위키를 관리하거나, GitHub Wiki 기능에 직접 푸시하는 방법도 있다.

```yaml
# GitHub Wiki 리포지토리에 직접 푸시하는 방식
- name: Push to wiki
  run: |
    git clone https://github.com/${{ github.repository }}.wiki.git wiki-repo
    cp -r wiki/* wiki-repo/
    cd wiki-repo
    git add .
    git diff --cached --quiet || git commit -m "docs: update wiki"
    git push
```

**API 키 관리**: CodeSight가 LLM API를 호출해서 설명을 생성하는 구조이므로, CI 환경에서 API 키를 시크릿으로 관리해야 한다. 환경변수 `CODESIGHT_API_KEY`로 전달한다.

```yaml
- run: codesight --wiki
  env:
    CODESIGHT_API_KEY: ${{ secrets.CODESIGHT_API_KEY }}
```

**캐시 활용**: `.codesight-cache/` 디렉토리를 CI 캐시에 포함시키면 변경되지 않은 파일의 재분석을 건너뛴다.

```yaml
- uses: actions/cache@v4
  with:
    path: .codesight-cache
    key: codesight-${{ hashFiles('src/**') }}
    restore-keys: codesight-
```

---

## 8. 자주 쓰는 옵션 조합

```bash
# 한국어로 위키 생성, 테스트 제외
codesight --wiki --language ko --ignore "**/*.test.*"

# 특정 디렉토리만 대상으로 위키 생성
codesight --wiki --scope src/domain --output docs/domain-wiki

# 기존 위키를 업데이트 (변경된 파일만 재분석)
codesight --wiki --incremental

# 의존성 그래프 포함
codesight --wiki --dependency-graph

# dry-run으로 생성될 파일 목록만 확인
codesight --wiki --dry-run
```

`--incremental`은 이전 분석 결과를 캐시해두고 변경된 파일만 다시 처리한다. 대규모 프로젝트에서 매번 전체를 돌리는 건 비효율적이니, 로컬 개발 중에는 이 옵션을 쓰는 게 낫다.

`--dry-run`은 실제 파일을 생성하지 않고 어떤 파일이 만들어질지만 보여준다. 설정을 바꾼 후 결과를 미리 확인할 때 쓴다.
