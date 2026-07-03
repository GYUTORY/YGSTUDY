---
title: Cursor Rules - 프로젝트별 AI 규칙 설정
tags: [cursor, rules, cursor-rules, ai-context, project-config]
updated: 2026-04-10
---

# Cursor Rules

## 1. Rules란

Cursor에서 AI에게 프로젝트 맥락을 주입하는 방법이다. `.cursor/rules` 디렉토리에 `.mdc` 확장자 파일을 만들어서, AI가 코드를 생성하거나 수정할 때 참고할 규칙을 정의한다.

예를 들어 "이 프로젝트는 Spring Boot 3.x + Java 21을 쓴다", "API 응답은 반드시 `ApiResponse<T>` 래퍼를 쓴다" 같은 규칙을 넣으면 AI가 코드를 생성할 때 이 규칙을 따른다.

Rules가 없으면 AI는 프로젝트 컨벤션을 모른 채 일반적인 코드를 생성한다. 팀에서 쓰는 패턴, 라이브러리, 네이밍 규칙 등을 Rules로 정의하면 AI 출력의 일관성이 크게 달라진다.

## 2. 디렉토리 구조

```
project-root/
├── .cursor/
│   └── rules/
│       ├── general.mdc          # 프로젝트 전역 규칙
│       ├── api-conventions.mdc  # API 작성 규칙
│       ├── testing.mdc          # 테스트 작성 규칙
│       └── database.mdc        # DB 관련 규칙
├── .cursorrules                 # (레거시) 단일 파일 방식
└── src/
```

`.cursor/rules/` 디렉토리 안에 `.mdc` 파일을 만든다. 파일 이름은 자유지만, 역할이 드러나는 이름을 쓰는 게 좋다.

`.mdc` 파일은 YAML frontmatter + Markdown 본문으로 구성된다.

```
---
description: API 컨트롤러 작성 시 적용할 규칙
globs: src/main/java/**/controller/**/*.java
alwaysApply: false
---

- API 응답은 `ApiResponse<T>`로 감싼다
- 예외 처리는 `@RestControllerAdvice`에서 한다
- Controller에 비즈니스 로직을 넣지 않는다
```

## 3. Rule 타입

Rule은 frontmatter 설정에 따라 4가지 타입으로 나뉜다. 어떤 상황에서 AI 컨텍스트에 포함되느냐가 다르다.

### 3.1 Always Apply

```yaml
---
description: 프로젝트 전역 규칙
alwaysApply: true
---
```

모든 AI 요청에 항상 포함된다. 프로젝트 전체에 걸치는 규칙을 넣는다.

적합한 내용:
- 프로젝트에서 쓰는 언어 버전, 프레임워크 버전
- 전역 네이밍 규칙
- 금지 패턴 (특정 라이브러리 사용 금지 등)

주의: 항상 컨텍스트에 포함되므로 내용이 길면 토큰을 낭비한다. 간결하게 작성해야 한다.

### 3.2 Auto Attached

```yaml
---
description: React 컴포넌트 작성 규칙
globs: src/components/**/*.tsx
alwaysApply: false
---
```

`globs` 패턴에 매칭되는 파일을 편집할 때 자동으로 포함된다. 특정 디렉토리나 파일 타입에만 적용할 규칙에 쓴다.

glob 패턴 예시:
- `src/**/*.test.ts` — 테스트 파일 편집 시
- `**/migrations/*.sql` — 마이그레이션 파일 편집 시
- `docker-compose*.yml` — Docker 설정 편집 시

`alwaysApply: false`이고 `globs`가 있으면 Auto Attached가 된다. `alwaysApply: true`면 globs를 무시하고 항상 포함되니까 둘을 동시에 쓸 이유가 없다.

### 3.3 Agent Requested

```yaml
---
description: 데이터베이스 마이그레이션 작성 시 참고할 규칙. Flyway 기반이며 V{번호}__{설명}.sql 형식을 따른다.
alwaysApply: false
---
```

`alwaysApply: false`이고 `globs`도 없는 경우다. AI 에이전트가 `description`을 보고 관련 있다고 판단하면 스스로 가져다 쓴다.

이 타입은 description이 중요하다. 에이전트가 description만 보고 이 규칙이 현재 작업에 필요한지 판단하기 때문이다. description이 모호하면 필요할 때 못 찾거나, 불필요할 때 가져오는 경우가 생긴다.

```yaml
# 나쁜 예 - 너무 모호함
description: DB 관련

# 좋은 예 - 구체적
description: PostgreSQL 마이그레이션 작성 규칙. Flyway 기반, 롤백 스크립트 필수 포함
```

### 3.4 Manual

Cursor 설정(Settings > Rules)에서 직접 추가하는 User Rules다. 파일로 관리되지 않고 Cursor 앱 내부에 저장된다.

User Rules는 모든 프로젝트에 걸쳐서 적용된다. "응답은 한국어로 해줘", "주석은 영어로 작성해" 같은 개인 선호를 넣기에 적합하다.

프로젝트 규칙과 User Rules가 충돌하면 프로젝트 규칙이 우선한다.

## 4. 프로젝트별 Rule 예제

### 4.1 Spring Boot 프로젝트

```
# .cursor/rules/general.mdc
---
description: Spring Boot 프로젝트 전역 규칙
alwaysApply: true
---

- Java 21, Spring Boot 3.3, Gradle 사용
- 패키지 구조는 도메인별로 나눈다 (com.example.order, com.example.user)
- Lombok @RequiredArgsConstructor로 의존성 주입한다
- 필드 주입(@Autowired) 금지
```

```
# .cursor/rules/api.mdc
---
description: REST API 컨트롤러 작성 규칙
globs: src/main/java/**/controller/**/*.java
alwaysApply: false
---

- 응답은 ResponseEntity<ApiResponse<T>> 형태로 반환한다
- @Valid로 요청 DTO 검증한다
- Controller에 비즈니스 로직 넣지 않는다. Service 계층에 위임한다
- API 경로는 복수형 명사를 쓴다 (/api/v1/orders)
```

```
# .cursor/rules/jpa.mdc
---
description: JPA Entity 및 Repository 작성 규칙. Querydsl 커스텀 리포지토리 포함
globs: src/main/java/**/entity/**/*.java, src/main/java/**/repository/**/*.java
alwaysApply: false
---

- Entity에 @Setter 금지. 변경은 도메인 메서드로 한다
- 양방향 연관관계는 편의 메서드를 만든다
- N+1 문제 방지를 위해 fetch join이나 @EntityGraph를 기본으로 쓴다
- Querydsl 커스텀 리포지토리는 {Entity}RepositoryCustom 인터페이스 + {Entity}RepositoryImpl 구현체
```

```
# .cursor/rules/test.mdc
---
description: 테스트 코드 작성 규칙
globs: src/test/**/*.java
alwaysApply: false
---

- 테스트 메서드 이름은 한글로 작성한다 (@DisplayName 대신 메서드명)
- given-when-then 패턴으로 구성한다
- 단위 테스트는 Mockito, 통합 테스트는 @SpringBootTest + TestContainers
- 테스트용 데이터는 Fixture 클래스에 모아둔다
```

### 4.2 NestJS 프로젝트

```
# .cursor/rules/general.mdc
---
description: NestJS 프로젝트 전역 규칙
alwaysApply: true
---

- TypeScript strict mode
- NestJS 10, Node.js 20 LTS
- pnpm 패키지 매니저
- 모듈 단위로 디렉토리를 나눈다 (src/modules/user, src/modules/order)
```

```
# .cursor/rules/api.mdc
---
description: NestJS 컨트롤러 및 DTO 작성 규칙
globs: src/modules/**/controllers/**/*.ts, src/modules/**/*.dto.ts
alwaysApply: false
---

- DTO에 class-validator 데코레이터를 쓴다
- 응답은 class-transformer의 @Exclude, @Expose로 직렬화 제어한다
- Controller 메서드에 @ApiOperation, @ApiResponse Swagger 데코레이터를 붙인다
- 에러 응답은 HttpException을 상속한 커스텀 예외로 던진다
```

```
# .cursor/rules/prisma.mdc
---
description: Prisma ORM 사용 규칙. 스키마 변경 및 마이그레이션 포함
globs: prisma/**
alwaysApply: false
---

- 마이그레이션 이름은 YYYYMMDD_설명 형식 (예: 20260410_add_user_email_index)
- 스키마 변경 후 prisma generate를 반드시 실행한다
- 프로덕션 마이그레이션은 prisma migrate deploy만 쓴다 (prisma migrate dev는 로컬 전용)
- 소프트 삭제가 필요한 테이블은 deletedAt 컬럼을 추가한다
```

### 4.3 React 프로젝트

```
# .cursor/rules/general.mdc
---
description: React 프로젝트 전역 규칙
alwaysApply: true
---

- React 19, TypeScript, Vite
- 상태 관리는 Zustand
- 스타일은 Tailwind CSS v4
- import 순서: react > 라이브러리 > 내부 모듈 > 상대 경로
```

```
# .cursor/rules/components.mdc
---
description: React 컴포넌트 작성 규칙
globs: src/components/**/*.tsx
alwaysApply: false
---

- 컴포넌트는 named export만 쓴다 (default export 금지)
- Props 타입은 컴포넌트명 + Props (예: UserCardProps)
- children을 받는 컴포넌트는 PropsWithChildren 사용
- 이벤트 핸들러 prop 이름은 on + 동사 (예: onSubmit, onClick)
- 컴포넌트 파일당 하나의 export 컴포넌트만 둔다
```

```
# .cursor/rules/hooks.mdc
---
description: 커스텀 훅 작성 규칙
globs: src/hooks/**/*.ts
alwaysApply: false
---

- 훅 이름은 use로 시작한다
- API 호출 훅은 TanStack Query를 감싸서 만든다
- 반환값이 2개 이하면 배열, 3개 이상이면 객체로 반환한다
- 훅 내부에서 다른 훅을 조합할 때 의존성 배열 관리를 신경 쓴다
```

## 5. .cursorrules 레거시 마이그레이션

프로젝트 루트에 `.cursorrules` 파일을 쓰던 방식은 레거시다. 아직 동작하지만, `.cursor/rules/` 디렉토리 방식으로 옮기는 것을 권장한다.

### 마이그레이션 절차

1. `.cursor/rules/` 디렉토리를 만든다
2. `.cursorrules` 내용을 역할별로 쪼갠다
3. 각 내용을 `.mdc` 파일로 만들고 frontmatter를 붙인다
4. 동작을 확인한 뒤 `.cursorrules` 파일을 삭제한다

기존 `.cursorrules` 내용이 이런 형태였다면:

```
# .cursorrules (레거시)
You are a Java 21 / Spring Boot 3.3 expert.

Always use constructor injection.
Use ResponseEntity<ApiResponse<T>> for all API responses.
Write tests in Korean method names.
Use Querydsl for complex queries.
```

이렇게 분리한다:

```
# .cursor/rules/general.mdc
---
description: 프로젝트 전역 규칙
alwaysApply: true
---

- Java 21, Spring Boot 3.3
- 생성자 주입만 사용 (필드 주입 금지)
```

```
# .cursor/rules/api.mdc
---
description: API 응답 형식 규칙
globs: src/main/java/**/controller/**/*.java
alwaysApply: false
---

- ResponseEntity<ApiResponse<T>> 형태로 반환
```

```
# .cursor/rules/test.mdc
---
description: 테스트 작성 규칙
globs: src/test/**/*.java
alwaysApply: false
---

- 메서드 이름은 한글로 작성
```

단일 파일에 다 넣으면 항상 전체 내용이 컨텍스트에 들어가서 토큰 낭비가 생기고, 파일별로 분리하면 관련된 규칙만 선택적으로 로딩된다. 이게 마이그레이션하는 실질적인 이유다.

### 주의사항

`.cursorrules`와 `.cursor/rules/`가 동시에 존재하면 둘 다 적용된다. 마이그레이션 중에 규칙이 중복 적용되는 경우가 생길 수 있으니, 마이그레이션이 끝나면 `.cursorrules`를 반드시 삭제한다.

## 6. Rule 우선순위와 충돌

같은 주제에 대해 여러 Rule이 서로 다른 내용을 담고 있으면 어떻게 되는가.

### 우선순위 순서

1. **User Rules** (Settings에서 설정한 전역 규칙) — 가장 낮은 우선순위
2. **Always Apply** 규칙
3. **Auto Attached** 규칙 (globs 매칭)
4. **Agent Requested** 규칙 (에이전트가 선택)

더 구체적인 규칙이 더 일반적인 규칙보다 우선한다. 하지만 Cursor가 명시적으로 "이 규칙이 저 규칙을 덮어썼다"고 알려주지는 않는다.

### 충돌이 실제로 일어나는 경우

```
# general.mdc (alwaysApply: true)
- 에러는 RuntimeException을 상속한 커스텀 예외로 던진다

# api.mdc (globs: **/controller/**/*.java)
- 에러는 ResponseStatusException으로 던진다
```

컨트롤러 파일을 편집하면 두 규칙이 동시에 컨텍스트에 들어간다. AI는 두 규칙을 모두 보고 나름대로 판단하는데, 결과가 일관되지 않을 수 있다.

### 충돌 방지 방법

- 같은 주제는 한 파일에서만 다룬다
- 전역 규칙에는 모든 상황에 적용되는 것만 넣고, 특정 영역 규칙은 해당 파일에 넣는다
- 규칙 간 모순이 없는지 주기적으로 점검한다

## 7. 팀에서 Rules 공유하기

### Git에 커밋할 것과 말 것

`.cursor/rules/` 디렉토리는 Git에 커밋한다. 팀 전체가 같은 규칙을 공유할 수 있다.

`.gitignore`에 넣으면 안 되는 것:
```
# 이렇게 하면 안 된다
.cursor/rules/
```

반대로 `.gitignore`에 넣어야 하는 것:
```
# Cursor 캐시와 개인 설정은 제외
.cursor/*
!.cursor/rules/
```

이렇게 하면 `.cursor/` 내 다른 파일(캐시, 세션 정보 등)은 무시하면서 `rules/` 디렉토리만 추적한다.

### 팀 공유 시 주의사항

**개인 규칙과 팀 규칙을 분리한다.**
개인적인 선호(응답 언어, 코드 스타일 등)는 User Rules(Settings)에 넣고, 프로젝트 규칙만 `.cursor/rules/`에 넣는다. "나는 탭 들여쓰기를 선호한다" 같은 건 User Rules에 들어가야지, 팀 전체에 강제할 내용이 아니다.

**Rule 파일이 너무 많아지면 관리가 어렵다.**
파일 수를 10개 이하로 유지하는 게 현실적이다. 규칙이 많아지면 AI가 참고할 컨텍스트도 늘어나서 토큰 비용이 올라가고, 규칙 간 충돌 가능성도 높아진다.

**새 멤버가 합류했을 때 Rules의 존재를 알려줘야 한다.**
Cursor를 처음 쓰는 사람은 `.cursor/rules/`가 뭔지 모른다. 프로젝트 README나 온보딩 문서에 "이 프로젝트는 Cursor Rules를 사용한다"는 내용을 추가한다.

**팀원 간 Rules 수정 충돌을 조심한다.**
`.mdc` 파일도 일반 텍스트이기 때문에 Git merge conflict가 발생할 수 있다. 한 사람이 규칙을 수정하고 다른 사람도 같은 파일을 수정하면 충돌이 생긴다. 규칙 변경은 PR을 통해 리뷰하는 것이 좋다.

## 8. Rule 작성 시 실수하기 쉬운 부분

**description을 빈 값으로 두는 경우.**
Agent Requested 타입에서 description이 비어 있으면 에이전트가 이 규칙을 찾을 수 없다. 아무 효과도 없는 규칙이 된다.

**globs 패턴이 잘못된 경우.**
`src/main/**/*.java`라고 써야 하는데 `src/main/*.java`라고 쓰면 하위 디렉토리의 파일을 매칭하지 못한다. glob 패턴에서 `**`는 여러 단계 디렉토리를 의미하고 `*`는 한 단계만 의미한다.

**규칙이 너무 길거나 모호한 경우.**
"코드를 잘 작성해줘" 같은 모호한 규칙은 아무 의미가 없다. "Controller에서 Service를 직접 호출하고, Repository는 Service에서만 접근한다"처럼 구체적이어야 AI가 따를 수 있다.

**프롬프트처럼 작성하는 경우.**
"You are an expert Java developer..." 같은 역할 지정은 Rules에서 효과가 거의 없다. AI에게 역할을 부여하는 것보다 구체적인 코딩 규칙을 나열하는 게 낫다.
