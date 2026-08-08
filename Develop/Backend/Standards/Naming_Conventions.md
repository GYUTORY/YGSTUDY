---
title: 케밥같은 용어들 — 개발 명명 규칙
tags: [backend]
updated: 2026-07-27
---

# 케밥같은 용어들 — 개발 명명 규칙

케밥 케이스, 스네이크 케이스, 카멜 케이스. 처음 들으면 음식 이야기처럼 들리는데, 실제 프로젝트에서 이것들을 혼용하다가 버그가 생기는 경우는 생각보다 많다.

## 기본 표기

| 표기 방식 | 예시 | 특징 |
|---|---|---|
| kebab-case | `user-profile-image` | 단어 사이를 하이픈으로 연결 |
| snake_case | `user_profile_image` | 단어 사이를 언더스코어로 연결 |
| camelCase | `userProfileImage` | 첫 단어 소문자, 이후 단어 첫 글자 대문자 |
| PascalCase | `UserProfileImage` | 모든 단어 첫 글자 대문자 |
| SCREAMING_SNAKE_CASE | `USER_PROFILE_IMAGE` | 전부 대문자 + 언더스코어 |

## 어디에 무엇을 쓰는가

### URL

URL 경로는 kebab-case가 표준이다. `/user-profile`, `/order-history`, `/payment-method` 처럼 단어 사이를 하이픈으로 연결한다.

언더스코어는 검색 엔진이 단어 구분자로 인식하지 못하는 경우가 있어서 `/user_profile` 같은 형태는 SEO에서 불리하다. 실제로 구글 문서에서 하이픈을 단어 구분자로 사용하길 권장한다고 명시되어 있다.

쿼리 파라미터는 관례가 조금 다르다. `?sort_by=created_at`처럼 snake_case를 쓰는 곳도 많고, `?sortBy=createdAt`처럼 camelCase를 쓰는 곳도 많다. 팀 내에서 통일만 되면 둘 다 문제없다. 문제가 생기는 건 같은 API에서 두 방식이 섞일 때다.

### JSON

공개 API를 만들 때는 camelCase가 지배적이다. JavaScript 생태계와 자연스럽게 맞아 떨어지기 때문이다.

```json
{
  "userId": 123,
  "profileImageUrl": "https://...",
  "createdAt": "2026-07-27T00:00:00Z"
}
```

snake_case JSON도 흔하다. Python, Ruby, PostgreSQL 생태계에서는 snake_case가 더 자연스러워서 그쪽 백엔드 팀은 대부분 snake_case로 응답한다.

```json
{
  "user_id": 123,
  "profile_image_url": "https://...",
  "created_at": "2026-07-27T00:00:00Z"
}
```

어느 쪽이 맞다고 할 수는 없다. 단 프론트엔드 팀과 협의하지 않고 중간에 바꾸면 그날 밤이 바빠진다.

### 데이터베이스

PostgreSQL, MySQL 모두 컬럼명은 snake_case가 관례다.

```sql
CREATE TABLE user_profiles (
  user_id         BIGINT PRIMARY KEY,
  profile_image   TEXT,
  created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
  is_deleted      BOOLEAN NOT NULL DEFAULT FALSE
);
```

대소문자 구분 문제가 있어서 `userProfileImage` 같은 camelCase 컬럼명을 쓰면 쿼리할 때마다 따옴표를 붙여야 한다.

```sql
-- 이렇게 해야 인식된다
SELECT "userProfileImage" FROM user_profiles;
```

처음에 대충 camelCase로 컬럼 만들고 나중에 이 상황을 마주치면 마이그레이션 하기도 애매하고 그냥 따옴표 붙이며 살게 된다.

### 코드

언어마다 컨벤션이 명확하게 정해져 있다.

**Go**
- 함수, 변수: camelCase (`getUserProfile`)
- 공개 함수, 타입: PascalCase (`UserProfile`, `GetUserProfile`)
- 상수: 관례적으로 PascalCase 또는 camelCase (SCREAMING_SNAKE_CASE는 거의 안 씀)

**Python**
- 함수, 변수: snake_case (`get_user_profile`)
- 클래스: PascalCase (`UserProfile`)
- 상수: SCREAMING_SNAKE_CASE (`MAX_RETRY_COUNT`)

**Java / Kotlin**
- 메서드, 변수: camelCase (`getUserProfile`)
- 클래스: PascalCase (`UserProfile`)
- 상수: SCREAMING_SNAKE_CASE (`MAX_RETRY_COUNT`)

**JavaScript / TypeScript**
- 함수, 변수: camelCase (`getUserProfile`)
- 클래스, 컴포넌트: PascalCase (`UserProfile`)
- 상수: 팀마다 다르지만 SCREAMING_SNAKE_CASE 많이 씀

## 혼용할 때 생기는 문제

### DB snake_case → JSON camelCase 변환

Go에서 `database/sql`이나 `sqlx`를 쓸 때 구조체 필드명과 DB 컬럼명을 매핑해야 한다.

```go
type UserProfile struct {
    UserID          int64  `db:"user_id"   json:"userId"`
    ProfileImage    string `db:"profile_image" json:"profileImage"`
    CreatedAt       time.Time `db:"created_at" json:"createdAt"`
}
```

태그를 일일이 달아야 한다. 누군가 `db` 태그를 빠뜨리면 컬럼 매핑이 조용히 실패하거나 제로값이 들어온다.

Python에서 Pydantic을 쓸 때는 설정 한 줄로 해결할 수 있다.

```python
from pydantic import BaseModel

class UserProfile(BaseModel):
    user_id: int
    profile_image: str
    created_at: datetime

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```

`alias_generator=to_camel`을 쓰면 snake_case 필드를 직렬화할 때 camelCase로 자동 변환한다. 다만 `populate_by_name=True`를 같이 써야 역직렬화할 때 원래 snake_case 이름으로도 받을 수 있다.

### 프레임워크 자동 변환

Spring Boot는 Jackson이 기본으로 camelCase로 직렬화한다.

```java
public class UserProfile {
    private Long userId;
    private String profileImage;
    private LocalDateTime createdAt;
    // getter/setter 생략
}
```

이걸 그대로 응답으로 보내면 JSON에서 `userId`, `profileImage`, `createdAt`이 나온다. snake_case로 보내고 싶으면 `application.properties`에 한 줄 추가한다.

```properties
spring.jackson.property-naming-strategy=SNAKE_CASE
```

또는 클래스 레벨에서만 적용할 수도 있다.

```java
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class UserProfile {
    private Long userId;
    // ...
}
```

Django REST Framework는 기본이 camelCase가 아니다. `djangorestframework-camel-case` 패키지를 추가해야 JSON 응답을 camelCase로 보낼 수 있다.

NestJS는 `class-transformer`의 `@Transform`이나 글로벌 인터셉터로 변환을 처리한다.

## URL 경로의 케밥 케이스와 파일시스템

Next.js나 Nuxt 같은 파일 기반 라우팅에서는 파일명이 곧 URL 경로가 된다. `user-profile.tsx` 파일을 만들면 `/user-profile` 경로가 생긴다. 이 경우 파일명도 kebab-case로 맞춰야 URL 경로와 일관성이 유지된다.

React 컴포넌트 파일은 PascalCase(`UserProfile.tsx`)를 쓰고 페이지 파일은 kebab-case를 쓰는 팀도 있다. 처음에 규칙을 못 박아두지 않으면 나중에 파일 탐색할 때 피로해진다.

## 환경 변수

환경 변수는 SCREAMING_SNAKE_CASE가 사실상 표준이다.

```bash
DATABASE_URL=postgres://localhost:5432/mydb
JWT_SECRET=your-secret-key
MAX_RETRY_COUNT=3
REDIS_HOST=localhost
```

이걸 camelCase나 kebab-case로 쓰면 쉘 스크립트에서 읽을 때 문제가 생기고, 일부 OS에서 kebab-case 환경 변수는 설정 자체가 안 된다.

## 실제로 가장 많이 발생하는 실수

### 1. JSON 키 케이스를 API 클라이언트에서 추측

백엔드가 `created_at`으로 보내는데 프론트엔드에서 `createdAt`으로 읽으려다 `undefined`가 나오는 상황. 문서가 없거나 계약이 명확하지 않을 때 생긴다.

### 2. ORM이 컬럼명을 마음대로 변환

TypeORM은 기본적으로 camelCase 엔티티 필드를 snake_case 컬럼으로 매핑한다. `profileImage` 필드가 DB에서 `profile_image` 컬럼으로 저장된다. 이 동작을 모르면 DB를 직접 보면서 왜 컬럼명이 다른지 한참 헤맨다.

```typescript
@Entity()
export class UserProfile {
    @Column()
    profileImage: string; // DB 컬럼명은 profile_image
}
```

명시적으로 지정하고 싶으면 `@Column({ name: 'profile_image' })`처럼 옵션을 준다.

### 3. API 명세와 실제 구현 불일치

Swagger/OpenAPI 스펙에서 `user_id`로 정의했는데 코드에서 `userId`로 구현된 경우. 자동 생성 클라이언트를 쓰는 팀에서는 이 차이 때문에 빌드가 깨진다.

## 정리

어떤 케이스를 쓸지보다 중요한 건 레이어별로 관례를 고정하고 변환 지점을 명확히 하는 것이다. DB는 snake_case, API 응답은 camelCase, 환경 변수는 SCREAMING_SNAKE_CASE로 각 레이어 관례를 정하고, 그 사이에서 프레임워크 자동 변환이 어떻게 동작하는지 파악해두면 혼용으로 인한 문제는 대부분 예방된다.

새 프로젝트를 시작할 때 README나 ADR(Architecture Decision Record)에 명명 규칙을 한 줄이라도 적어두는 게 낫다. 나중에 "우리 팀은 어떻게 하기로 했었지?" 라는 질문이 나올 때 Slack 히스토리를 뒤질 필요가 없어진다.
