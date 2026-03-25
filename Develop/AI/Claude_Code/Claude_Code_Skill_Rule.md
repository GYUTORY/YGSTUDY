---
title: Claude Code 스킬과 룰 시스템
tags: [ai, claude-code, anthropic, skill, rule, claude-md, settings]
updated: 2026-03-25
---

# Claude Code 스킬과 룰 시스템

Claude Code에서 반복 작업을 자동화하거나, 프로젝트 전체에 규칙을 강제하는 두 가지 시스템이 있다. **CLAUDE.md 룰**과 **스킬(Skill)**이다. 이 둘을 혼동하면 "왜 안 먹히지?"로 시간을 날린다.

---

## 1. 스킬 파일 구조와 frontmatter

스킬은 마크다운 파일 하나로 정의한다. 위치는 두 곳이다.

| 위치 | 범위 | 용도 |
|------|------|------|
| `~/.claude/skills/` | 전역 (모든 프로젝트) | 개인 워크플로우 |
| `.claude/skills/` | 프로젝트 | 팀 공유 워크플로우 |

프로젝트 레벨 스킬은 git에 커밋해서 팀 전체가 같은 스킬을 쓰게 만든다.

### frontmatter 문법

```markdown
---
description: "PR 올리기 전에 린트, 테스트, 커밋 메시지 형식을 한 번에 점검한다"
user-invocable: true
---

# pr-check

## 수행 단계
1. ...
```

각 필드의 역할:

- **description**: Claude Code가 스킬을 선택할 때 참고하는 설명이다. 이 값이 부실하면 자동 매칭이 안 된다. 구체적으로 써야 한다.
- **user-invocable**: `true`면 `/스킬이름`으로 직접 호출할 수 있다. `false`거나 생략하면 Claude Code가 상황에 맞춰 자동으로 선택한다.

frontmatter가 없어도 스킬 파일로 인식되긴 한다. 다만 `user-invocable`이 빠지면 슬래시 명령이 안 되고, `description`이 빠지면 자동 매칭 정확도가 떨어진다.

---

## 2. 빌트인 스킬과 커스텀 스킬

### 빌트인 스킬

Claude Code에 기본으로 내장된 스킬들이다. 설치 없이 바로 쓸 수 있다.

| 스킬 | 호출 | 하는 일 |
|------|------|---------|
| `/commit` | 슬래시 명령 | 변경사항 분석 → 커밋 메시지 생성 → 커밋 |
| `/review` | 슬래시 명령 | 현재 diff 기반 코드 리뷰 |
| `/simplify` | 자동 매칭 | 변경된 코드의 중복 제거, 품질 개선 |
| `/init` | 슬래시 명령 | CLAUDE.md 초안 생성 |
| `claude-api` | 자동 매칭 | Anthropic SDK import 감지 시 API 사용법 안내 |
| `frontend-design` | 자동 매칭 | 웹 컴포넌트/페이지 빌드 요청 시 디자인 품질 향상 |
| `update-config` | 자동 매칭 | settings.json, 훅, 권한 설정 변경 |
| `schedule` | 슬래시 명령 | 스케줄 기반 원격 에이전트(트리거) 관리 |
| `loop` | 슬래시 명령 | 특정 간격으로 프롬프트 반복 실행 |

빌트인 스킬은 수정할 수 없다. 동작을 바꾸고 싶으면 같은 이름의 커스텀 스킬을 만들지 말고, 다른 이름으로 새로 만들어야 한다.

### 커스텀 스킬

직접 만드는 스킬이다. 마크다운 파일에 Claude가 수행할 단계를 자연어로 적는다.

```markdown
---
description: "TypeORM 마이그레이션 파일 생성 후 검증까지 한 번에 처리한다"
user-invocable: true
---

# migration-check

## 수행 단계

1. `npm run typeorm migration:generate`으로 마이그레이션 파일 생성
2. 생성된 SQL 확인 — DROP TABLE, DROP COLUMN이 있으면 경고
3. `npm run typeorm migration:run`으로 로컬 DB에 적용
4. 적용 후 `npm run test:e2e`로 기존 테스트 통과 확인
5. 실패하면 `migration:revert` 실행하고 실패 원인 분석
```

스킬 파일 이름이 곧 슬래시 명령어가 된다. 위 파일을 `.claude/skills/migration-check.md`로 저장하면 `/migration-check`으로 호출한다.

---

## 3. 스킬이 트리거되는 조건

스킬은 세 가지 방식으로 실행된다.

### 슬래시 명령 (user-invocable)

`user-invocable: true`인 스킬은 `/스킬이름`으로 직접 호출한다.

```
/pr-check
/migration-check
```

`user-invocable: false`이거나 생략된 스킬은 슬래시 명령 목록에 나타나지 않는다.

### 자동 매칭 (description 기반)

사용자의 요청이 스킬의 `description`과 의미적으로 매칭되면 Claude Code가 알아서 해당 스킬을 가져와 사용한다.

예를 들어 `claude-api` 빌트인 스킬의 description에는 "code imports anthropic" 같은 트리거 조건이 적혀 있다. 코드에서 `import anthropic`을 쓰면 Claude Code가 이 스킬을 자동으로 선택한다.

커스텀 스킬도 마찬가지다. description에 "마이그레이션"이라고 적어두면, "마이그레이션 만들어줘"라는 요청에 해당 스킬이 매칭될 수 있다.

**description 작성 시 주의할 점:**

- 트리거 조건을 구체적으로 써야 한다. "유용한 작업을 한다" 같은 설명은 매칭이 안 된다.
- 어떤 상황에서 이 스킬을 써야 하는지 명확하게 적는다.
- 빌트인 스킬처럼 "TRIGGER when: ..., DO NOT TRIGGER when: ..." 형식으로 적으면 오매칭이 줄어든다.

```markdown
---
description: >
  프로젝트의 API 엔드포인트 목록을 추출하고 문서화한다.
  TRIGGER when: 사용자가 API 문서 생성, 엔드포인트 목록, API 스펙 정리를 요청할 때.
  DO NOT TRIGGER when: 단순 코드 리뷰나 버그 수정 요청.
---
```

### Skill 도구를 통한 호출

Claude Code 내부적으로 `Skill` 도구가 있어서, 다른 스킬이나 에이전트 컨텍스트에서 특정 스킬을 명시적으로 실행할 수 있다. 일반 사용에서는 슬래시 명령이나 자동 매칭으로 충분하다.

---

## 4. CLAUDE.md 룰과 스킬의 역할 분담

이 구분을 못 하면 CLAUDE.md에 스킬 내용을 쓰거나, 스킬에 프로젝트 규칙을 넣는 실수를 한다.

### CLAUDE.md — 항상 적용되는 제약

CLAUDE.md는 **세션 시작 시 자동으로 로드**된다. 여기에 적힌 내용은 모든 요청에 영향을 준다.

```markdown
# CLAUDE.md에 적합한 내용

## 코드 규칙
- any 타입 금지
- console.log 대신 logger 사용
- DB save() 대신 update() 사용

## 테스트
- 단위 테스트: npm run test
- 커밋 전 테스트 통과 필수

## 커밋
- Conventional Commits 형식
- 한글 커밋 메시지
```

CLAUDE.md에 넣으면 안 되는 것: 특정 상황에서만 필요한 절차. "PR 올리기 전에 이것저것 확인해" 같은 건 항상 필요한 게 아니니까 스킬로 빼야 한다. CLAUDE.md가 길어지면 매 요청마다 컨텍스트를 먹는다.

### 스킬 — 특정 작업 시 호출되는 루틴

스킬은 **호출될 때만** 컨텍스트에 올라온다. 평소에는 존재하지 않는 것과 같다.

```
CLAUDE.md: "테스트 실패하면 커밋하지 마" (항상 적용)
스킬:      "/deploy-check" → 배포 전 점검 루틴 (배포할 때만 실행)
```

### 판단 기준

| 질문 | CLAUDE.md | 스킬 |
|------|-----------|------|
| 모든 요청에 적용되나? | O | X |
| 특정 명령으로 실행하나? | X | O |
| 여러 단계의 절차가 있나? | X | O |
| 컨텍스트를 항상 차지해도 되나? | O | X |
| 팀 전체에 강제하고 싶은 규칙인가? | O | 상황에 따라 |

CLAUDE.md가 200줄을 넘어가면 스킬로 분리할 내용이 없는지 점검한다. 컨텍스트 낭비가 심해진다.

### CLAUDE.md 계층 구조

CLAUDE.md는 여러 위치에 놓을 수 있고, 모두 합쳐서 적용된다.

| 위치 | 범위 | 예시 |
|------|------|------|
| `~/.claude/CLAUDE.md` | 전역 | 개인 코딩 습관 |
| 프로젝트 루트 `CLAUDE.md` | 프로젝트 전체 | 팀 코드 규칙 |
| 하위 디렉토리 `CLAUDE.md` | 해당 디렉토리 | 패키지별 규칙 |

하위 디렉토리의 CLAUDE.md는 해당 디렉토리의 파일을 작업할 때만 적용된다. 모노레포에서 패키지별로 규칙을 다르게 가져갈 때 쓴다.

```
project/
├── CLAUDE.md                    # 전체 규칙
├── packages/
│   ├── api/
│   │   └── CLAUDE.md            # API 패키지 규칙
│   └── worker/
│       └── CLAUDE.md            # Worker 패키지 규칙
```

---

## 5. settings.json의 permissions/hooks와 스킬의 관계

### settings.json 위치와 역할

```
~/.claude/settings.json          # 전역 설정
.claude/settings.json             # 프로젝트 설정
.claude/settings.local.json       # 로컬 설정 (git에 안 올림)
```

settings.json에서 관리하는 것들:

- **permissions**: 어떤 도구/명령을 자동 허용할지. `npm test`를 매번 승인하기 싫으면 여기에 추가한다.
- **hooks**: 특정 이벤트 발생 시 자동 실행되는 쉘 명령어. "파일 저장할 때마다 린트 돌려" 같은 자동화.
- **env**: 환경 변수 설정

### 룰 적용 우선순위

Claude Code가 동작을 결정할 때 참고하는 설정의 우선순위:

```
1. settings.json의 permissions  → 도구 실행 허용/차단 (가장 먼저 체크)
2. hooks                        → 이벤트 기반 자동 실행
3. CLAUDE.md                    → 세션 전체에 적용되는 규칙
4. 스킬                         → 호출된 스킬의 지시사항
5. 사용자의 현재 요청            → 대화에서 직접 준 지시
```

permissions에서 차단한 동작은 CLAUDE.md나 스킬에서 지시해도 실행되지 않는다. 예를 들어 `rm` 명령을 permissions에서 막아두면, 스킬에서 "임시 파일 삭제"를 지시해도 Claude Code가 실행 전에 사용자에게 확인을 요청한다.

### hooks vs 스킬 — 혼동하기 쉬운 부분

| | hooks | 스킬 |
|---|-------|------|
| 실행 주체 | 시스템 (Claude Code 하네스) | Claude (AI) |
| 정의 위치 | settings.json | .claude/skills/ |
| 트리거 | 이벤트 기반 (도구 호출 전/후 등) | 사용자 요청 또는 자동 매칭 |
| 용도 | 린트, 포맷팅, 알림 같은 기계적 작업 | 판단이 필요한 복합 작업 |

"커밋할 때마다 린트를 돌리고 싶다"는 hooks로 해결한다. "커밋 메시지를 분석해서 적절한 형식인지 판단하고 싶다"는 스킬로 해결한다. hooks는 쉘 명령어를 그대로 실행하는 거고, 스킬은 Claude가 판단하면서 처리하는 거다.

hooks 설정 예시:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(commit)",
        "command": "npm run lint:staged 2>&1 | head -20"
      }
    ]
  }
}
```

"매번 X할 때마다 Y해줘" 같은 자동화 요청은 스킬이 아니라 hooks로 처리해야 한다. Claude가 기억해서 해주는 게 아니라, 시스템이 강제로 실행하는 거다. 메모리나 CLAUDE.md에 적어서는 안 된다.

---

## 6. 실무에서 쓸만한 커스텀 스킬 예제

### 코드 리뷰 — 팀 규칙 기반

```markdown
---
description: >
  팀 코딩 컨벤션 기반으로 현재 변경사항을 리뷰한다.
  TRIGGER when: 코드 리뷰, 컨벤션 체크, PR 전 점검을 요청할 때.
  DO NOT TRIGGER when: 단순 버그 수정이나 기능 구현 요청.
user-invocable: true
---

# team-review

## 수행 단계

1. `git diff --staged` 또는 `git diff`로 변경사항 확인
2. 다음 항목 점검:
   - any 타입 사용 여부
   - console.log 잔존 여부 (logger 대신 쓴 건 아닌지)
   - 에러 처리에서 에러를 삼키는 빈 catch 블록
   - 하드코딩된 문자열 중 환경 변수로 빼야 할 것
   - 함수 길이가 50줄을 넘는 경우
3. 파일별로 발견한 문제를 나열
4. 문제가 없으면 "리뷰 통과"로 끝냄
```

`.claude/skills/team-review.md`로 저장하면 `/team-review`로 호출한다.

### DB 마이그레이션 점검

```markdown
---
description: >
  DB 마이그레이션 파일의 위험 요소를 분석한다.
  TRIGGER when: 마이그레이션 리뷰, 마이그레이션 검증, 스키마 변경 점검을 요청할 때.
user-invocable: true
---

# migration-review

## 수행 단계

1. 아직 적용되지 않은 마이그레이션 파일을 찾는다
2. 각 마이그레이션 파일에서 다음을 확인:
   - DROP TABLE, DROP COLUMN — 데이터 손실 위험
   - ALTER TABLE에 DEFAULT 없는 NOT NULL 추가 — 기존 데이터에서 에러
   - 큰 테이블의 인덱스 추가 — 락 발생 가능성
   - 트랜잭션 안에서 DDL과 DML 혼용 여부
3. 위험도를 높음/중간/낮음으로 분류
4. 롤백 마이그레이션(down)이 있는지 확인
5. 롤백이 없으면 경고
```

### 배포 전 검증

```markdown
---
description: >
  배포 전 필수 체크 항목을 순서대로 실행한다.
  TRIGGER when: 배포 전 점검, deploy check, 릴리스 준비를 요청할 때.
user-invocable: true
---

# deploy-check

## 수행 단계

1. 현재 브랜치가 main인지 확인. main이 아니면 경고
2. `git status`로 커밋 안 된 변경사항 확인. 있으면 중단
3. `npm run build` 실행. 빌드 실패하면 중단
4. `npm run test` 실행. 테스트 실패하면 중단
5. 환경 변수 확인 — .env.example과 .env 비교해서 빠진 변수 있는지 확인
6. package.json의 version이 이전 태그보다 올라갔는지 확인
7. 모든 항목 통과하면 결과 요약 출력
```

### API 스펙 변경 감지

```markdown
---
description: >
  API 엔드포인트의 요청/응답 스펙 변경을 감지하고 하위 호환성을 확인한다.
  TRIGGER when: API 변경 확인, breaking change 체크, API 호환성 점검을 요청할 때.
user-invocable: true
---

# api-compat

## 수행 단계

1. 변경된 컨트롤러/라우터 파일 목록 추출
2. 각 엔드포인트에서 다음을 확인:
   - 응답 필드 삭제 또는 타입 변경 — breaking change
   - 필수 요청 파라미터 추가 — 기존 클라이언트에서 에러
   - URL 경로 변경 — 기존 클라이언트 호출 실패
   - HTTP 메서드 변경
3. breaking change가 있으면 목록으로 정리
4. 하위 호환성을 유지하면서 변경하는 방법 제안
```

---

## 7. 스킬이 안 먹힐 때 디버깅

### 슬래시 명령이 안 나온다

`/스킬이름`을 쳤는데 목록에 안 뜨는 경우:

- **frontmatter에 `user-invocable: true`가 있는지 확인한다.** 이게 빠지면 슬래시 명령으로 호출이 안 된다.
- **파일 위치가 맞는지 확인한다.** `~/.claude/skills/` 또는 `.claude/skills/` 안에 있어야 한다. `.claude/skill/`처럼 오타가 나면 인식이 안 된다.
- **파일 확장자가 `.md`인지 확인한다.** `.txt`나 `.yaml`은 스킬 파일로 인식되지 않는다.

### 자동 매칭이 안 된다

"마이그레이션 검증해줘"라고 했는데 해당 스킬이 선택되지 않는 경우:

- **description이 너무 모호하다.** "유용한 작업을 수행한다"는 아무것도 매칭하지 않는다. 구체적인 키워드와 상황을 적어야 한다.
- **description에 트리거 조건이 없다.** `TRIGGER when:` 형식으로 어떤 요청에 반응해야 하는지 명시한다.
- **비슷한 description의 스킬이 여러 개다.** Claude Code가 어떤 걸 써야 할지 판단하지 못한다. description을 서로 겹치지 않게 분리한다.

### 스킬이 실행은 되는데 기대와 다르게 동작한다

- **단계 설명이 애매하다.** "적절히 처리한다" 같은 표현은 Claude가 재량껏 해석한다. 구체적인 명령어와 판단 기준을 적는다.
- **CLAUDE.md와 스킬이 충돌한다.** CLAUDE.md에 "테스트 파일은 건드리지 마"라고 써두고, 스킬에서 "테스트 실행 후 수정"을 지시하면 Claude가 혼란스러워한다. CLAUDE.md의 규칙이 우선하는 경우가 많다.
- **permissions에서 막혀 있다.** 스킬에서 `rm`, `docker` 같은 명령을 쓰는데 permissions에 허용이 안 되어 있으면 실행 전에 매번 승인을 요청한다. settings.json에서 해당 명령을 허용해야 한다.

### 디버깅 순서

스킬이 안 먹히면 이 순서로 확인한다:

1. 파일 위치: `.claude/skills/` 안에 `.md` 파일로 존재하는가
2. frontmatter: `user-invocable`, `description`이 제대로 적혀 있는가
3. 이름 충돌: 빌트인 스킬과 같은 이름을 쓰고 있지 않은가
4. description: 트리거 조건이 충분히 구체적인가
5. CLAUDE.md 충돌: 스킬의 지시와 CLAUDE.md의 규칙이 모순되지 않는가
6. permissions: 스킬에서 쓰는 명령어가 허용되어 있는가

`--verbose` 플래그로 Claude Code를 실행하면 스킬 매칭 과정을 볼 수 있어서 원인 파악이 빨라진다.
