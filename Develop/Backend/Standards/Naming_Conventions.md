---
title: 케밥같은 용어들 — 개발 명명 규칙
tags: [backend, engineering]
updated: 2026-09-24
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

### 약어 처리 — ID, URL, API, HTTP

팀에서 규칙 충돌이 가장 자주 나는 지점이다. `getUserId`가 맞는지 `getUserID`가 맞는지 PR마다 논쟁이 붙는다. 언어마다 공식 입장이 다르기 때문이다.

**Go**: 약어는 전부 대문자로 쓴다. Go 공식 스타일 가이드([Effective Go](https://go.dev/doc/effective_go))에 명시되어 있다.

```go
// 맞다
func getUserID(userID int64) {}
var httpClient *http.Client
type URLParser struct{}
type APIResponse struct{}

// 틀렸다 — Go 코드리뷰에서 지적받는다
func getUserId(userId int64) {}
var httpClient *http.Client  // 이건 우연히 맞아 보이지만
type UrlParser struct{}      // 이건 틀렸다
```

**Java / Kotlin**: 약어도 camelCase 규칙을 따른다. 첫 글자만 대문자, 이후는 소문자다.

```java
// 맞다
public User getUserById(Long userId) {}
private String apiUrl;
class HttpClient {}
class ApiResponse {}

// 틀렸다 — Java 팀에서 이상하게 본다
public User getUserByID(Long userID) {}
class HTTPClient {}
```

**JavaScript / TypeScript**: Java와 같다. `userId`, `apiUrl`, `httpMethod`.

이 차이가 실제 문제로 번지는 경우가 있다. Go 백엔드 팀이 만든 코드에서 `UserID`, `APIURL` 같은 필드명이 JSON 직렬화 시 `UserID`, `APIURL`로 나와서 프론트엔드에서 `userId`, `apiUrl`로 매핑하다 undefined가 나오는 상황이다. JSON 태그를 명시적으로 달아두지 않으면 struct 필드명이 그대로 키가 된다.

```go
type User struct {
    UserID  int64  `json:"userId"`  // 명시적으로 달아야 한다
    APIURL  string `json:"apiUrl"`
}
```

SQL에서도 마찬가지다. sqlx를 쓸 때 `db:"user_id"` 태그를 빠뜨리면 `UserID` 필드를 `UserID` 컬럼으로 찾으려 해서 매핑이 실패한다.

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

## CSS/SCSS 클래스명

CSS 클래스명은 kebab-case가 사실상 표준이다. camelCase로 쓰면 일부 CSS 선택자에서 의도치 않게 동작할 수 있고, HTML 속성값과 일관성도 떨어진다.

BEM(Block Element Modifier) 방법론은 컴포넌트 단위로 클래스명 충돌을 막는 방법이다.

```css
/* Block: 독립적인 컴포넌트 단위 */
.user-card {}

/* Element: 블록 안의 구성 요소, 블록__요소 형식 */
.user-card__avatar {}
.user-card__name {}
.user-card__action-button {}

/* Modifier: 상태나 변형, 블록--변형 형식 */
.user-card--active {}
.user-card--loading {}
.user-card__avatar--large {}
```

실제로 쓰다 보면 요소가 깊어질수록 클래스명이 길어지는 문제가 생긴다. `.navigation__list__item__link--active` 같은 형태가 나오면 BEM 구조를 다시 검토해야 한다. BEM은 깊이 2단계(블록, 요소)까지만 쓰고, 그 이상은 새로운 블록으로 쪼개는 게 낫다.

SCSS를 쓴다면 `&` 연산자로 중첩해서 쓸 수 있다.

```scss
.user-card {
  padding: 16px;

  &__avatar {
    width: 48px;
    border-radius: 50%;
  }

  &__name {
    font-weight: 600;
  }

  &--loading {
    opacity: 0.5;
    pointer-events: none;
  }
}
```

React나 Vue에서 CSS Modules를 쓰면 BEM 없이도 충돌을 막을 수 있다. 클래스명이 빌드 시 해시로 변환되기 때문이다. 이 경우 camelCase 클래스명을 쓰는 경우도 있다(`styles.userCard`처럼 JS 객체 프로퍼티로 접근하니까). Tailwind를 도입한 팀이라면 커스텀 클래스명 자체를 거의 안 쓰게 된다.

## Git 브랜치와 커밋

### 브랜치 명명

`타입/설명` 형식이 가장 흔하다. 설명 부분은 kebab-case로 쓴다.

```
feature/add-user-authentication
feature/payment-v2
fix/login-redirect-bug
fix/null-pointer-in-order-service
hotfix/prod-payment-timeout
chore/update-dependencies
refactor/extract-auth-middleware
docs/add-api-reference
```

팀마다 이슈 번호를 붙이는 경우도 많다.

```
feature/PROJ-123-add-user-authentication
fix/PROJ-456-login-redirect-bug
```

브랜치명에 공백이나 슬래시 두 개 이상이 들어가면 일부 Git GUI 도구에서 폴더 구조로 인식해 계층이 생긴다. `feature/login/add-oauth`처럼 슬래시를 두 개 쓰면 `feature` 아래 `login` 폴더가 생긴 것처럼 보인다. 의도한 게 아니라면 하이픈으로 연결하는 게 낫다.

### 커밋 메시지

Conventional Commits 형식이 널리 쓰인다.

```
feat: add OAuth2 login with Google
fix: resolve null pointer in OrderService when cart is empty
chore: upgrade Spring Boot to 3.3.0
refactor: extract email validation into UserValidator
docs: add API authentication guide
test: add unit tests for PaymentService retry logic
```

`feat`과 `fix`는 CHANGELOG 자동 생성 도구가 읽는 타입이기도 해서, 의미에 맞게 구분해 쓰는 게 중요하다. 기능 추가인데 `chore`로 쓰거나 버그 수정인데 `feat`으로 쓰면 자동 생성된 릴리즈 노트가 엉킨다.

`!`를 붙이면 breaking change를 표시한다.

```
feat!: change user ID from integer to UUID
refactor!: remove deprecated /v1 API endpoints
```

body에 `BREAKING CHANGE:` 주석을 달아도 된다.

```
feat: change user ID type to UUID

BREAKING CHANGE: user_id field is now a UUID string instead of integer.
Clients must update their ID parsing logic.
```

커밋 메시지 subject는 50자 이내, body는 72자 줄바꿈이 권장값이다. GitHub PR 목록에서 잘리지 않고 보이는 길이 기준이다.

## Protobuf/gRPC

proto 파일 안에서는 케이스 규칙이 영역마다 다르다.

```proto
syntax = "proto3";

package user.v1;

// 메시지명: PascalCase
message GetUserRequest {
  // 필드명: snake_case
  int64 user_id = 1;
  string profile_image_url = 2;
  repeated string tag_ids = 3;
}

message GetUserResponse {
  int64 user_id = 1;
  string display_name = 2;
}

// 서비스명: PascalCase
service UserService {
  // RPC 메서드명: PascalCase
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
  rpc ListUsers(ListUsersRequest) returns (ListUsersResponse);
}

// enum명: PascalCase, 값: SCREAMING_SNAKE_CASE + enum명 접두사
enum UserStatus {
  USER_STATUS_UNSPECIFIED = 0;
  USER_STATUS_ACTIVE = 1;
  USER_STATUS_SUSPENDED = 2;
}
```

enum 값에 enum명을 접두사로 붙이는 이유는 proto3가 enum 값을 패키지 레벨에서 관리하기 때문이다. 두 enum에 같은 값 이름이 있으면 컴파일 에러가 난다.

```proto
// 이렇게 하면 안 된다 — ACTIVE가 충돌한다
enum UserStatus {
  ACTIVE = 1;
}
enum OrderStatus {
  ACTIVE = 1;  // 에러
}
```

proto 파일의 snake_case 필드명은 각 언어 protoc 플러그인이 자동으로 변환한다. Go에서는 `UserId`, Java에서는 `userId`, Python에서는 `user_id`로 생성된다. 이 변환이 자동으로 이루어지기 때문에 proto 파일에서 camelCase를 직접 쓰면 안 된다. `userId = 1`로 쓰면 Go 생성 코드에서 `UserId`가 나와서 Go 스타일 가이드(`UserID`)와 맞지 않게 된다.

파일명은 snake_case, 패키지명은 소문자 도메인 계층 구조를 쓴다.

```
user/v1/user_service.proto       # 파일명: snake_case
package user.v1;                 # 패키지명: 소문자 + 버전
```

## Kubernetes와 Docker

### Kubernetes 리소스명

쿠버네티스 리소스명은 RFC 1123을 따른다. 소문자 + 숫자 + 하이픈만 허용하고, 알파벳으로 시작해야 한다. 대문자나 언더스코어를 쓰면 `kubectl apply` 시 validation error가 난다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service          # kebab-case 강제
  namespace: production
  labels:
    app.kubernetes.io/name: user-service
    app.kubernetes.io/version: "1.2.3"
    app.kubernetes.io/component: backend
```

레이블 키는 `prefix/name` 형식이다. 쿠버네티스 공식 레이블은 `app.kubernetes.io/` 접두사를 쓴다. 팀 커스텀 레이블은 회사 도메인을 접두사로 쓰는 게 권장값이다(`team.mycompany.com/owner: backend`).

ConfigMap이나 Secret의 키는 kebab-case와 `.` 조합을 흔히 쓴다. 환경 변수로 마운트할 때는 SCREAMING_SNAKE_CASE를 쓴다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-service-config
data:
  database.host: "postgres-primary.production.svc.cluster.local"
  database.port: "5432"
```

```yaml
# 환경 변수로 주입할 때
env:
  - name: DATABASE_HOST
    valueFrom:
      configMapKeyRef:
        name: user-service-config
        key: database.host
```

### Docker 이미지 태그

`latest`는 CI/CD에서 쓰지 않는 게 낫다. 언제 빌드된 이미지인지 추적이 안 되고, 배포 롤백도 어렵다.

```bash
# 권장하지 않는다
docker push registry.io/user-service:latest

# semver: 릴리즈 배포에 적합
docker push registry.io/user-service:1.2.3

# 브랜치 + 커밋 해시: 개발 환경, 스테이징에서 흔히 씀
docker push registry.io/user-service:main-a3f92c1

# PR 번호: PR별 환경을 띄울 때
docker push registry.io/user-service:pr-456
```

이미지 이름은 레지스트리 도메인과 경로를 포함한다. Docker Hub 외에 AWS ECR, GCR, GHCR을 쓸 때는 경로 형식이 다르다.

```bash
# Docker Hub
docker.io/myorg/user-service:1.2.3

# AWS ECR
123456789.dkr.ecr.ap-northeast-2.amazonaws.com/user-service:1.2.3

# GitHub Container Registry
ghcr.io/myorg/user-service:1.2.3

# Google Artifact Registry
asia-northeast3-docker.pkg.dev/my-project/my-repo/user-service:1.2.3
```

Dockerfile 내부에서 `ARG`와 `ENV` 변수는 SCREAMING_SNAKE_CASE를 쓴다.

```dockerfile
ARG APP_VERSION=latest
ARG BUILD_DATE

ENV APP_HOME=/app \
    PORT=8080 \
    LOG_LEVEL=info
```

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

### JSON 키 케이스를 API 클라이언트에서 추측

백엔드가 `created_at`으로 보내는데 프론트엔드에서 `createdAt`으로 읽으려다 `undefined`가 나오는 상황. 문서가 없거나 계약이 명확하지 않을 때 생긴다.

### ORM이 컬럼명을 마음대로 변환

TypeORM은 기본적으로 camelCase 엔티티 필드를 snake_case 컬럼으로 매핑한다. `profileImage` 필드가 DB에서 `profile_image` 컬럼으로 저장된다. 이 동작을 모르면 DB를 직접 보면서 왜 컬럼명이 다른지 한참 헤맨다.

```typescript
@Entity()
export class UserProfile {
    @Column()
    profileImage: string; // DB 컬럼명은 profile_image
}
```

명시적으로 지정하고 싶으면 `@Column({ name: 'profile_image' })`처럼 옵션을 준다.

### API 명세와 실제 구현 불일치

Swagger/OpenAPI 스펙에서 `user_id`로 정의했는데 코드에서 `userId`로 구현된 경우. 자동 생성 클라이언트를 쓰는 팀에서는 이 차이 때문에 빌드가 깨진다.

### proto 필드명에 camelCase 사용

proto3 파일에서 `userId = 1`처럼 camelCase로 쓰면 각 언어 생성 코드에서 의도치 않은 이름이 나온다. Go 생성 코드에서 `UserId`가 되어 Go 스타일 가이드(`UserID`)와 맞지 않고, `protoc-gen-go`가 이를 경고로 잡는다. proto 파일은 항상 snake_case로 쓴다.

어떤 케이스를 쓸지보다 중요한 건 레이어별로 관례를 고정하고 변환 지점을 명확히 하는 것이다. DB는 snake_case, API 응답은 camelCase, 환경 변수는 SCREAMING_SNAKE_CASE, 쿠버네티스 리소스명은 kebab-case로 각 레이어 관례를 정하고, 그 사이에서 프레임워크 자동 변환이 어떻게 동작하는지 파악해두면 혼용으로 인한 문제는 대부분 예방된다.

새 프로젝트를 시작할 때 README나 ADR(Architecture Decision Record)에 명명 규칙을 한 줄이라도 적어두는 게 낫다. 나중에 "우리 팀은 어떻게 하기로 했었지?" 라는 질문이 나올 때 Slack 히스토리를 뒤질 필요가 없어진다.
