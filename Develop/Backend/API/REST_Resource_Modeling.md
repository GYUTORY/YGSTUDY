---
title: REST 리소스 모델링 심화
tags: [backend, api, rest]
updated: 2026-07-26
---

# REST 리소스 모델링 심화

REST 설계에서 URL과 HTTP 메서드를 어떻게 매핑하느냐보다 리소스 간의 관계를 어떻게 표현하느냐가 실제로 더 많은 논쟁을 만들어낸다. 팀마다 다르게 쓰고, 잘못 설계하면 클라이언트 쪽 코드가 지저분해지거나 N+1 요청이 생긴다.

## 관계 표현 패턴

### Embedded vs Linked vs Sideloaded

관련 리소스를 응답에 담는 방식은 세 가지로 나뉜다.

**Embedded**: 부모 응답 안에 자식 리소스를 직접 포함한다.

```json
// GET /orders/123
{
  "id": 123,
  "status": "PAID",
  "items": [
    { "productId": 10, "name": "노트북 거치대", "quantity": 2, "price": 35000 },
    { "productId": 11, "name": "USB 허브", "quantity": 1, "price": 28000 }
  ]
}
```

`items`가 `orders` 없이 독립적으로 존재하지 않는 경우에 맞다. 항상 같이 조회하고, 자식의 개수가 제한적이며, 별도 캐싱이 필요 없을 때 쓴다. 반면 `user` 같은 독립 리소스를 여기 담으면 같은 사용자 정보가 여러 응답에 중복되고 업데이트가 어려워진다.

**Linked**: 자식의 ID나 URL만 포함한다.

```json
// GET /posts/55
{
  "id": 55,
  "title": "Spring Boot 배포 삽질기",
  "authorId": 7,
  "tagIds": [12, 34, 89]
}
```

자식 리소스가 독립적으로 자주 접근되거나, 클라이언트가 항상 자식이 필요하지 않을 때 적합하다. 단점은 클라이언트가 `authorId`로 `/users/7`을 별도 호출해야 한다는 것이다. 목록 API에서 linked 방식으로 설계하면 아이템 수만큼 추가 요청이 생기는 N+1 문제가 그대로 발생한다.

**Sideloaded**: 메인 리소스와 연관 리소스를 별도 키로 함께 묶어 응답한다. JSON:API 스펙이 이 방식을 표준화했다.

```json
// GET /posts/55?include=author,tags
{
  "data": {
    "id": 55,
    "type": "posts",
    "attributes": {
      "title": "Spring Boot 배포 삽질기"
    },
    "relationships": {
      "author": { "data": { "type": "users", "id": "7" } },
      "tags": { "data": [{ "type": "tags", "id": "12" }, { "type": "tags", "id": "34" }] }
    }
  },
  "included": [
    { "id": "7", "type": "users", "attributes": { "name": "홍길동" } },
    { "id": "12", "type": "tags", "attributes": { "name": "spring" } },
    { "id": "34", "type": "tags", "attributes": { "name": "devops" } }
  ]
}
```

중복 없이 모든 데이터를 한 번에 전달한다. 여러 포스트에서 같은 작성자가 있어도 `included`에 한 번만 들어간다. 클라이언트가 `id`로 조립해야 하므로 클라이언트 코드가 복잡해진다. 정형화된 API를 여러 클라이언트에 제공할 때 유리하다.

### 어떤 패턴을 선택하나

세 패턴을 선택하는 기준은 주로 이 세 가지다.

- 자식 리소스가 부모 없이 독립적으로 존재하는가 → linked 또는 sideloaded
- 목록 API에서 자식이 항상 필요한가 → embedded (단, 크기 제한)
- 여러 클라이언트(웹, 앱, 외부)에 공개하는 API인가 → sideloaded나 `?include=` 쿼리 파라미터 지원

실무에서는 세 방식을 혼용한다. `items` 같은 값 객체는 embedded, `author` 같은 독립 엔티티는 linked로 두고 `?include=author` 옵션으로 필요할 때 sideloaded 형태로 제공하는 방식이 많다.

## 컨트롤러 리소스 패턴

CRUD로 표현하기 어려운 동작이 있다. 계정 활성화, 이메일 재발송, 주문 취소, 비밀번호 리셋 같은 행위다. 이걸 POST `/users/7/activate`나 PUT `/users/7/status`로 처리하는데, 팀마다 의견이 갈린다.

컨트롤러 리소스는 행위 자체를 리소스로 모델링한다.

```
# 행위를 동사형 URL로
POST /accounts/7/activate
POST /orders/123/cancel
POST /emails/resend
POST /passwords/reset

# 상태 변경을 리소스로 표현
POST /users/7/sessions         # 로그인
DELETE /users/7/sessions/abc   # 로그아웃
POST /orders/123/cancellations # 주문 취소 (취소 이력을 리소스로)
```

`POST /orders/123/cancellations`처럼 명사형으로 만들면 취소 자체가 리소스가 되어 취소 사유, 취소 시각 같은 속성을 자연스럽게 붙일 수 있다. 취소 이력을 `GET /orders/123/cancellations`로 조회하는 것도 된다.

단순히 상태만 바꾸는 경우라면 PATCH도 쓴다.

```
# 상태 필드만 변경
PATCH /orders/123
{ "status": "CANCELLED" }
```

문제는 `status`에 허용 가능한 전이가 비즈니스 규칙으로 존재할 때다. `PAID` 상태에서 `SHIPPED`로 직접 바꾸는 게 가능한지를 PATCH 하나로 표현하면 서버가 유효성 검증을 해야 하고, 클라이언트는 어떤 전이가 가능한지 알기 어렵다. 이 경우 전이마다 별도 액션 엔드포인트를 두는 게 더 명확하다.

## 서브리소스 설계 기준

서브리소스 URL(`/parents/{id}/children`)을 쓸 기준이 모호한 경우가 많다.

**서브리소스를 쓰는 경우:**

- 자식 리소스가 부모 없이는 의미가 없을 때 (`/orders/123/items`)
- 부모 컨텍스트로 자식을 필터링하는 게 핵심 동작일 때 (`/users/7/posts`)
- 자식 생성 시 부모 ID가 반드시 필요할 때

**플랫 URL을 쓰는 경우:**

- 자식 리소스가 여러 부모 컨텍스트에서 독립적으로 접근될 때
- 자식 ID만으로 리소스를 특정할 수 있을 때 (`/posts/55`, `/comments/99`)

서브리소스를 남용하면 URL 중첩이 깊어진다. `/users/7/posts/55/comments/99/likes`까지 가면 관리가 힘들어진다. 관례적으로 2단계(`/parents/{id}/children`) 이상은 플랫 URL로 대체한다.

```
# 2단계까지
GET /posts/55/comments

# 3단계 이상은 플랫으로
GET /comments/99/likes       # /posts/55/comments/99/likes 대신
GET /likes?commentId=99      # 또는 쿼리 파라미터
```

## 다대다 관계 표현

사용자-역할, 포스트-태그, 학생-수업 같은 다대다 관계는 중간 연결 테이블이 있다. 이 관계 자체를 리소스로 모델링할지, 아니면 한쪽 서브리소스로 처리할지 결정해야 한다.

**관계에 속성이 없는 경우**: 한쪽 서브리소스로 처리한다.

```
# 사용자에게 태그 추가/제거
PUT    /users/7/tags/12     # 태그 연결
DELETE /users/7/tags/12     # 태그 연결 해제
GET    /users/7/tags        # 연결된 태그 목록
```

**관계 자체에 속성이 있는 경우**: 관계를 별도 리소스로 모델링한다.

```
# 수강 등록 (enrollment에 속성 있음: 등록일, 성적, 수료 여부)
POST /enrollments
{
  "studentId": 7,
  "courseId": 42,
  "enrolledAt": "2026-07-01"
}

GET  /enrollments?studentId=7     # 학생의 수강 목록
GET  /enrollments?courseId=42     # 수업의 수강생 목록
GET  /enrollments/enrollment_id   # 특정 수강 정보
PATCH /enrollments/enrollment_id  # 성적 업데이트 등
```

관계에 고유한 속성이나 상태가 붙는 순간 그 관계는 독립 리소스다. 억지로 서브리소스로 표현하려 하면 설계가 복잡해진다.

## 비동기 작업 리소스 패턴

파일 업로드 처리, 대용량 리포트 생성, 외부 시스템 연동처럼 즉시 완료되지 않는 작업을 HTTP로 표현할 때 202 Accepted 패턴을 쓴다.

```
# 1. 작업 요청
POST /reports
{
  "type": "MONTHLY_SALES",
  "month": "2026-06"
}

# 2. 즉시 202 반환, 작업 리소스 생성
HTTP/1.1 202 Accepted
Location: /jobs/job_abc123
{
  "jobId": "job_abc123",
  "status": "PENDING",
  "createdAt": "2026-07-26T10:00:00Z"
}
```

`Location` 헤더로 작업 상태를 폴링할 URL을 알려준다.

```
# 3. 폴링
GET /jobs/job_abc123

# 진행 중
{
  "jobId": "job_abc123",
  "status": "PROCESSING",
  "progress": 45,
  "estimatedCompleteAt": "2026-07-26T10:05:00Z"
}

# 완료
{
  "jobId": "job_abc123",
  "status": "COMPLETED",
  "result": {
    "reportId": "report_xyz",
    "downloadUrl": "/reports/report_xyz",
    "expiresAt": "2026-08-26T10:05:00Z"
  }
}

# 실패
{
  "jobId": "job_abc123",
  "status": "FAILED",
  "error": {
    "code": "DATA_NOT_FOUND",
    "message": "2026-06 판매 데이터가 존재하지 않습니다"
  }
}
```

폴링 응답에 `Retry-After` 헤더를 붙이면 클라이언트가 적절한 간격으로 재요청한다.

```
HTTP/1.1 200 OK
Retry-After: 5
{
  "status": "PROCESSING",
  "progress": 45
}
```

작업 리소스는 완료 후에도 일정 기간 보존한다. 클라이언트가 완료 시점을 놓쳤을 때 재조회가 가능해야 한다. 완료된 작업을 TTL 기반으로 삭제하거나 클라이언트가 `DELETE /jobs/job_abc123`으로 명시적 삭제를 지원하는 방식을 함께 제공한다.

웹훅이 가능한 환경이면 폴링 대신 콜백 URL을 받아 완료 시 POST로 알려주는 방식이 낫다. 폴링은 클라이언트가 직접 제어하는 환경(모바일 앱, CLI 도구 등)에서 더 적합하다.

## 복합 키 리소스 처리

DB 테이블에 복합 기본 키가 있을 때 URL 설계가 까다롭다. 예를 들어 `(userId, productId)` 조합으로 식별되는 위시리스트 항목이 있다.

**방법 1: 서브리소스로 표현**

```
GET    /users/7/wishlist/products/42
DELETE /users/7/wishlist/products/42
PUT    /users/7/wishlist/products/42
```

자연스럽지만 양쪽 ID가 URL에 다 들어가야 한다.

**방법 2: 인조 키 부여**

```
POST /wishlist-items
{ "userId": 7, "productId": 42 }
→ { "id": "wi_abc", "userId": 7, "productId": 42 }

GET    /wishlist-items/wi_abc
DELETE /wishlist-items/wi_abc
```

UUID나 surrogate key를 발급하면 URL이 단순해지고, 나중에 위시리스트 항목에 추가 속성(메모, 추가일 등)이 생겨도 자연스럽게 확장된다.

**방법 3: 복합 키를 URL에 인코딩**

```
GET    /user-product-preferences/7,42
DELETE /user-product-preferences/7,42
```

일부 API에서 쓰지만 쉼표나 특수문자를 URL에 쓰면 라우터 파싱이나 로그 분석에서 문제가 생기는 경우가 있다. URL 인코딩하면 `/user-product-preferences/7%2C42`가 되어 읽기 불편해진다.

**방법 4: 쿼리 파라미터로 조회, 서브리소스로 변경**

```
GET    /wishlist-items?userId=7&productId=42   # 조회
PUT    /users/7/wishlist/products/42           # 생성/수정
DELETE /users/7/wishlist/products/42           # 삭제
```

읽기와 쓰기 경로를 다르게 두는 방식이다. CQRS 관점에서는 자연스럽지만 일관성이 없어서 API 문서화가 복잡해진다.

실무에서는 관계 자체에 속성이 생길 가능성이 조금이라도 있으면 인조 키를 발급해서 독립 리소스로 만드는 편이 낫다. 속성 없는 순수 연결이 확실할 때만 서브리소스 방식을 쓴다.

## 정리

| 상황 | 선택 |
|------|------|
| 자식이 부모 없이 존재 불가 + 항상 같이 조회 | embedded |
| 자식이 독립 리소스, 항상 필요하지 않음 | linked + `?include` |
| 복잡한 관계, 중복 없이 전달 필요 | sideloaded |
| 상태 전이 행위 표현 | 컨트롤러 리소스 (`/resource/{id}/action`) |
| 다대다 관계에 속성 없음 | 서브리소스 PUT/DELETE |
| 다대다 관계에 속성 있음 | 독립 리소스 (인조 키) |
| 장시간 작업 | 202 + 작업 리소스 폴링 |
| 복합 키 + 속성 확장 가능성 | 인조 키 발급 |
