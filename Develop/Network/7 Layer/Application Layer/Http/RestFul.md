---
title: REST와 RESTful API 완전 가이드
tags: [network, 7-layer, application-layer, http, restful, api, web-service]
updated: 2025-09-20
---

# REST (Representational State Transfer)

## REST란?

REST는 **Representational State Transfer**의 약자로, 웹의 장점을 최대한 활용할 수 있는 아키텍처 스타일입니다.

### 핵심 개념
- **자원(Resource)**: URI로 식별되는 모든 정보
- **표현(Representation)**: 자원의 특정 시점의 상태를 나타내는 방법
- **상태 전달(State Transfer)**: 클라이언트와 서버 간의 자원 표현을 주고받는 것

### REST의 기본 원칙
1. **자원의 식별**: 모든 자원은 고유한 URI로 식별
2. **표현을 통한 자원 조작**: HTTP 메서드를 통한 자원 조작
3. **무상태성(Stateless)**: 각 요청은 독립적이며 서버는 클라이언트 상태를 저장하지 않음
4. **캐시 가능성**: 응답은 캐시 가능해야 함
5. **계층화 시스템**: 클라이언트는 서버와 직접 통신하는지 중간 계층을 거치는지 알 수 없음
6. **코드 온 디맨드**: 서버에서 클라이언트로 실행 가능한 코드를 전송할 수 있음 (선택사항)

# RESTful API

## RESTful이란?

REST의 원칙을 따르는 웹 서비스를 **RESTful**하다고 합니다.

### RESTful API의 특징
- HTTP 프로토콜을 기반으로 함
- JSON, XML 등의 표준 데이터 형식 사용
- URL과 HTTP 메서드를 통한 자원 접근
- 명확하고 일관된 인터페이스 제공

## HTTP 메서드와 REST

### 주요 HTTP 메서드

| 메서드 | 용도 | 설명 | 예시 |
|--------|------|------|------|
| **GET** | 조회 | 자원을 읽어옴 | `GET /users/123` |
| **POST** | 생성 | 새로운 자원을 생성 | `POST /users` |
| **PUT** | 전체 수정 | 자원의 전체를 교체 | `PUT /users/123` |
| **PATCH** | 부분 수정 | 자원의 일부만 수정 | `PATCH /users/123` |
| **DELETE** | 삭제 | 자원을 삭제 | `DELETE /users/123` |

### PUT vs PATCH 상세 비교

#### PUT (전체 업데이트)
```http
PUT /users/123
Content-Type: application/json

{
  "name": "김철수",
  "email": "kim@example.com",
  "age": 30,
  "phone": "010-1234-5678"
}
```
- **특징**: 자원의 **전체**를 교체
- **멱등성**: 있음 (같은 요청을 여러 번 해도 결과가 동일)
- **사용 시기**: 자원의 모든 필드를 알고 있을 때

#### PATCH (부분 업데이트)
```http
PATCH /users/123
Content-Type: application/json

{
  "email": "newemail@example.com"
}
```
- **특징**: 자원의 **일부**만 수정
- **멱등성**: 있음 (같은 요청을 여러 번 해도 결과가 동일)
- **사용 시기**: 특정 필드만 수정하고 싶을 때

## RESTful API 설계 원칙

### 1. URI 설계 규칙

#### 좋은 예시
```
GET    /users              # 사용자 목록 조회
GET    /users/123          # 특정 사용자 조회
POST   /users              # 새 사용자 생성
PUT    /users/123          # 사용자 전체 수정
PATCH  /users/123          # 사용자 부분 수정
DELETE /users/123          # 사용자 삭제

GET    /users/123/posts    # 특정 사용자의 게시글 목록
GET    /users/123/posts/456 # 특정 사용자의 특정 게시글
```

#### 나쁜 예시
```
GET    /getUsers           # 동사 사용 금지
POST   /users/update       # 동사 사용 금지
GET    /users/123/updateName # 동사 사용 금지
POST   /users/123/delete   # 동사 사용 금지
```

### 2. HTTP 상태 코드 활용

| 상태 코드 | 의미 | 사용 예시 |
|-----------|------|-----------|
| 200 | OK | 성공적인 조회 |
| 201 | Created | 성공적인 생성 |
| 204 | No Content | 성공적인 삭제 |
| 400 | Bad Request | 잘못된 요청 |
| 401 | Unauthorized | 인증 실패 |
| 403 | Forbidden | 권한 없음 |
| 404 | Not Found | 자원 없음 |
| 500 | Internal Server Error | 서버 오류 |

### 3. 응답 형식 표준화

#### 성공 응답
```json
{
  "status": "success",
  "data": {
    "id": 123,
    "name": "김철수",
    "email": "kim@example.com"
  }
}
```

#### 에러 응답
```json
{
  "status": "error",
  "message": "사용자를 찾을 수 없습니다",
  "code": "USER_NOT_FOUND"
}
```

## RESTful하지 않은 API의 문제점

### 1. 모든 작업을 POST로 처리
```http
POST /api/getUsers     # ❌ 잘못된 예시
POST /api/updateUser   # ❌ 잘못된 예시
POST /api/deleteUser   # ❌ 잘못된 예시
```

### 2. URI에 동사 사용
```http
GET /api/getUserById/123    # ❌ 잘못된 예시
POST /api/createUser        # ❌ 잘못된 예시
POST /api/updateUserName    # ❌ 잘못된 예시
```

### 3. 일관성 없는 응답 형식
```json
// API A의 응답
{
  "user": { "name": "김철수" }
}

// API B의 응답  
{
  "data": { "name": "김철수" }
}
```

## RESTful API의 장점

### 1. **단순성**
- HTTP 표준을 활용하여 이해하기 쉬움
- URL만으로도 API의 기능을 파악 가능

### 2. **확장성**
- 무상태성으로 인한 높은 확장성
- 캐싱을 통한 성능 향상

### 3. **플랫폼 독립성**
- HTTP 기반으로 모든 플랫폼에서 사용 가능
- 다양한 클라이언트 지원

### 4. **표준화**
- HTTP 메서드와 상태 코드의 표준 사용
- 일관된 인터페이스 제공

## 실제 구현 예시

### Node.js + Express 예시
```javascript
// 사용자 관련 API
app.get('/users', (req, res) => {
  // 사용자 목록 조회
  res.json({ users: userList });
});

app.get('/users/:id', (req, res) => {
  // 특정 사용자 조회
  const user = findUserById(req.params.id);
  if (user) {
    res.json({ user });
  } else {
    res.status(404).json({ error: 'User not found' });
  }
});

app.post('/users', (req, res) => {
  // 새 사용자 생성
  const newUser = createUser(req.body);
  res.status(201).json({ user: newUser });
});

app.put('/users/:id', (req, res) => {
  // 사용자 전체 수정
  const updatedUser = updateUser(req.params.id, req.body);
  res.json({ user: updatedUser });
});

app.patch('/users/:id', (req, res) => {
  // 사용자 부분 수정
  const updatedUser = partialUpdateUser(req.params.id, req.body);
  res.json({ user: updatedUser });
});

app.delete('/users/:id', (req, res) => {
  // 사용자 삭제
  deleteUser(req.params.id);
  res.status(204).send();
});
```

## RESTful API 모범 사례

### 1. **버전 관리**
```
GET /api/v1/users
GET /api/v2/users
```

### 2. **페이지네이션**
```
GET /users?page=1&limit=10
GET /users?offset=0&limit=10
```

### 3. **필터링 및 정렬**
```
GET /users?status=active&sort=name&order=asc
GET /users?age_min=18&age_max=65
```

### 4. **에러 처리**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력 데이터가 올바르지 않습니다",
    "details": [
      {
        "field": "email",
        "message": "올바른 이메일 형식이 아닙니다"
      }
    ]
  }
}
```

## 결론

RESTful API는 웹 서비스 개발의 표준이 되었으며, 다음과 같은 이유로 널리 사용됩니다:

- **직관적**: URL과 HTTP 메서드만으로도 API의 기능을 이해할 수 있음
- **표준화**: HTTP 표준을 활용하여 일관된 인터페이스 제공
- **확장성**: 무상태성과 캐싱을 통한 높은 성능과 확장성
- **호환성**: 다양한 클라이언트와 플랫폼에서 사용 가능

올바른 RESTful API 설계를 통해 더 나은 웹 서비스를 구축할 수 있습니다.

---

## 참고 자료
- [AWS RESTful API 가이드](https://aws.amazon.com/ko/what-is/restful-api/)
- [REST API 설계 가이드](https://restfulapi.net/)
- [HTTP 상태 코드](https://developer.mozilla.org/ko/docs/Web/HTTP/Status)

