---
title: URL URI
tags: [network, url과-uri]
updated: 2025-08-10
---
## 📍 URL이란?

**URL(Uniform Resource Locator)**은 인터넷에서 웹페이지, 이미지, 파일 등 각종 자원의 위치를 알려주는 주소입니다.

## 배경
- 집 주소처럼 웹에서 특정 자원을 찾아가는 주소
- 도서관에서 책의 위치를 알려주는 책장 번호와 같은 역할
- 네비게이션에서 목적지까지 가는 경로와 같은 개념

- 브라우저 주소창에 입력하는 것이 바로 URL
- 서버에 있는 파일이나 폴더의 위치를 정확히 가리킴
- 슬래시(/)를 사용해 폴더 구조를 표현 (윈도우 탐색기와 비슷)

---

```
https://www.example.com/index.html
```
- **프로토콜**: `https://`
- **호스트**: `www.example.com`
- **경로**: `/index.html`

```
https://shop.example.com/products/123?color=red&size=L#reviews
```
- **프로토콜**: `https://`
- **호스트**: `shop.example.com`
- **경로**: `/products/123`
- **쿼리**: `color=red&size=L`
- **프래그먼트**: `#reviews`


### 1. **웹 개발**
```javascript
// URL에서 정보 추출
const url = new URL('https://example.com/path?param=value');
console.log(url.hostname);    // example.com
console.log(url.pathname);    // /path
console.log(url.searchParams.get('param')); // value
```

### 2. **API 설계**
```
GET /api/users          ← 사용자 목록
GET /api/users/123      ← 특정 사용자
POST /api/users         ← 새 사용자 생성
PUT /api/users/123      ← 사용자 정보 수정
DELETE /api/users/123   ← 사용자 삭제
```

### 3. **라우팅**
```
/                    ← 홈페이지
/about              ← 회사 소개
/products           ← 상품 목록
/products/123       ← 특정 상품
/contact            ← 문의하기
```

---

1. **프로토콜 확인**: 어떤 방식으로 접속할지
2. **호스트 확인**: 어느 서버에 접속할지
3. **경로 확인**: 서버 내에서 어느 파일/폴더인지
4. **쿼리 확인**: 추가로 전달할 정보가 있는지
5. **프래그먼트 확인**: 페이지 내 특정 부분인지

- URL은 대소문자를 구분할 수 있음
- 특수문자는 인코딩이 필요할 수 있음
- 길이 제한이 있음 (브라우저마다 다름)
- 보안을 위해 민감한 정보는 포함하지 않기






<div align="center">
    <img src="../../etc/image/Network_image/URL.png" alt="URL" width="50%">
</div>





# URL과 URI 

## 🔧 URL의 구성 요소

### 1. **프로토콜 (Scheme)**
웹사이트에 접속하는 방법을 결정하는 규칙

| 프로토콜 | 설명 | 사용 예시 |
|---------|------|-----------|
| `http://` | 일반적인 웹페이지 접속 | `http://www.naver.com` |
| `https://` | 보안이 강화된 웹페이지 접속 | `https://www.google.com` |
| `ftp://` | 파일 전송용 | `ftp://fileserver.com` |
| `mailto:` | 이메일 작성 | `mailto:user@example.com` |

### 2. **호스트 (Host)**
웹사이트가 어느 서버에 있는지 알려주는 부분

```
www.example.com
blog.example.com  ← 서브도메인
192.168.1.1      ← IP 주소
```

### 3. **포트 (Port)**
서버 내에서 실행 중인 특정 서비스를 구분하는 번호

| 서비스 | 기본 포트 | 예시 |
|--------|-----------|------|
| 웹서버 | 80 | `http://example.com:80` |
| 보안웹서버 | 443 | `https://example.com:443` |
| 개발서버 | 3000 | `http://localhost:3000` |

### 4. **경로 (Path)**
서버 내에서 원하는 파일이나 폴더의 위치

```
/images/logo.png     ← 이미지 파일
/api/users          ← API 폴더
/posts/2024/01      ← 연도/월별 폴더
```

### 5. **쿼리 (Query)**
서버에 추가 정보를 전달하는 부분

```
?search=javascript&page=2
?user=kim&age=25&city=seoul
```

**구성 방식:**
- `?`로 시작
- `키=값` 형태로 작성
- 여러 개는 `&`로 연결

### 6. **프래그먼트 (Fragment)**
웹페이지 내에서 특정 부분을 가리키는 앵커

```
#section1
#main-content
#chapter-3
```

---

## 🌐 URI란?

**URI(Uniform Resource Identifier)**는 인터넷 상의 자원을 식별하는 고유한 이름입니다.

### 📚 URL과 URI의 관계

```
URI (자원 식별자)
├── URL (위치 기반 식별)
└── URN (이름 기반 식별)
```

### 🔍 URI의 특징

1. **고유성**: 각 자원마다 다른 URI를 가짐
2. **일관성**: 같은 자원은 항상 같은 URI
3. **지속성**: 자원이 이동해도 URI는 유지 가능

---

## 📝 실제 URL 분석 예시

### API 호출
```
https://api.example.com/users?page=1&limit=10&sort=name
```
- **프로토콜**: `https://`
- **호스트**: `api.example.com`
- **경로**: `/users`
- **쿼리**: `page=1&limit=10&sort=name`

---

## 🎯 URL과 URI의 차이점

| 구분 | URL | URI |
|------|-----|-----|
| **의미** | 자원의 위치 | 자원의 식별자 |
| **범위** | URI의 일부 | 더 넓은 개념 |
| **예시** | `https://example.com` | `urn:isbn:0451450523` |

### 📖 URN 예시
```
urn:isbn:0451450523          ← 책의 ISBN
urn:uuid:6e8bc430-9c3a-11d9-9669-0800200c9a66  ← 고유 식별자
```

---

## 🔍 URL 구조 이해하기

