---
title: CORS (Cross-Origin Resource Sharing)
tags: [webserver, nginx, cors, cross-origin, security, web-security]
updated: 2025-12-10
---

# CORS (Cross-Origin Resource Sharing)

## CORS의 등장 배경

### Same-Origin Policy

웹 브라우저는 기본적으로 Same-Origin Policy(동일 출처 정책)라는 보안 메커니즘을 가진다. 이 정책은 웹의 보안을 지키는 기본적인 방어선이다.

**실무 팁:**
Same-Origin Policy는 브라우저가 다른 출처의 리소스 접근을 차단한다. CORS는 서버가 명시적으로 허용한 요청만 통과시킨다.

동일 출처 정책이란, 웹 페이지가 오직 같은 출처(Origin)에서만 리소스를 요청할 수 있도록 제한하는 정책이다. 여기서 출처는 다음 세 가지 요소의 조합으로 정의된다:

- 프로토콜 (http, https, ftp 등)
- 호스트 (도메인명 또는 IP 주소)
- 포트 번호 (명시적으로 지정된 경우)

이 세 요소가 모두 일치해야만 "동일 출처"로 인정된다. 하나라도 다르면 "다른 출처(Cross-Origin)"로 간주되어 브라우저가 요청을 차단한다.

### CORS의 등장 이유

현대 웹 개발에서는 이런 제약이 문제가 된다.

**개발 환경**에서는 프론트엔드와 백엔드가 서로 다른 포트에서 실행되는 경우가 많다. 예를 들어 React 개발 서버는 3000번 포트에서, Express API 서버는 8080번 포트에서 실행된다. 이는 브라우저 입장에서는 완전히 다른 출처로 인식된다.

**프로덕션 환경**에서는 마이크로서비스 아키텍처로 인해 여러 서비스가 서로 다른 도메인에서 운영된다. 프론트엔드는 `https://example.com`에서, API 서버는 `https://api.example.com`에서 실행되는 식이다.

이런 상황에서도 안전하게 리소스를 공유할 수 있도록 등장한 것이 CORS(Cross-Origin Resource Sharing)다.

### CORS의 원칙

CORS는 "모든 요청을 허용하자"가 아니라 "서버가 명시적으로 허용한 요청만 통과시키자"는 원칙을 가진다. 이는 보안을 유지하면서도 필요한 경우에만 크로스 오리진 요청을 허용하는 접근법이다.

**실무 팁:**
CORS는 서버에서 설정한다. 클라이언트는 CORS를 우회할 수 없다. 개발 환경에서는 모든 출처를 허용할 수 있지만, 프로덕션에서는 특정 도메인만 허용한다.

## CORS의 작동 원리와 메커니즘

### 브라우저의 CORS 검증 과정

CORS는 브라우저와 서버 간의 협력으로 이루어지는 보안 메커니즘이다. 브라우저는 크로스 오리진 요청을 보낼 때마다 다음과 같은 검증 과정을 거친다:

1. 요청 전 검증: 브라우저가 요청을 보내기 전에 해당 요청이 CORS 정책에 위배되는지 확인
2. 서버 응답 검증: 서버로부터 받은 응답에 적절한 CORS 헤더가 있는지 확인
3. 헤더 분석: `Access-Control-Allow-Origin` 헤더를 통해 현재 출처가 허용되는지 판단

만약 이 과정에서 문제가 발견되면, 브라우저는 요청을 차단하고 개발자 도구에 다음과 같은 오류를 표시한다:

**실무 팁:**
CORS 오류는 브라우저 콘솔에서 확인할 수 있다. 네트워크 탭에서 OPTIONS 요청과 실제 요청을 확인한다.

```
Access to fetch at 'http://api.example.com/data' from origin 'http://localhost:3000' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present 
on the requested resource.
```

### CORS 헤더의 역할과 의미

CORS는 HTTP 헤더를 통해 구현된다. 주요 헤더들은 다음과 같다:

**요청 헤더 (브라우저가 자동으로 추가)**
- `Origin`: 요청을 보내는 페이지의 출처
- `Access-Control-Request-Method`: 실제 요청에서 사용할 HTTP 메서드
- `Access-Control-Request-Headers`: 실제 요청에서 사용할 헤더들

**응답 헤더 (서버가 명시적으로 설정해야 함)**
- `Access-Control-Allow-Origin`: 허용할 출처 지정
- `Access-Control-Allow-Methods`: 허용할 HTTP 메서드들
- `Access-Control-Allow-Headers`: 허용할 요청 헤더들
- `Access-Control-Allow-Credentials`: 인증 정보 포함 요청 허용 여부

**실무 팁:**
CORS 헤더는 서버에서 설정해야 한다. Nginx에서는 `add_header` 지시어를 사용한다.

### Simple Request vs Preflight Request

CORS 요청은 크게 두 가지 유형으로 나뉩니다:

**Simple Request (단순 요청)**
- GET, HEAD, POST 메서드만 사용
- 특정 헤더만 사용 (Accept, Accept-Language, Content-Language, Content-Type 등)
- Content-Type이 `application/x-www-form-urlencoded`, `multipart/form-data`, `text/plain` 중 하나
- 이런 요청은 브라우저가 바로 보내고, 서버 응답에서 CORS 헤더를 확인

**Preflight Request (사전 요청)**
- PUT, DELETE, PATCH 등 "위험한" 메서드 사용
- 커스텀 헤더 사용 (Authorization, Content-Type: application/json 등)
- 이런 요청은 실제 요청 전에 OPTIONS 메서드로 사전 요청을 보내서 서버의 허용 여부를 확인

**실무 팁:**
Simple Request는 Preflight 없이 바로 전송된다. Preflight는 OPTIONS 요청으로 서버의 허용 여부를 확인한다.

### 현실에서 CORS가 필요한 상황들

**1. 현대 웹 개발 패턴**
- SPA(Single Page Application)에서 API 서버와의 통신
- 프론트엔드와 백엔드의 완전한 분리
- 마이크로서비스 아키텍처에서의 서비스 간 통신

**2. 서드파티 서비스 통합**
- 결제 시스템 (PG사 API)
- 지도 서비스 (Google Maps, Kakao Map)
- 소셜 로그인 (Google, Facebook, Kakao)
- CDN이나 외부 리소스 서비스

**3. 개발 도구와 환경**
- 개발 서버와 API 서버의 포트 분리
- 테스트 환경과 스테이징 환경 간의 통신
- 로컬 개발과 원격 API 서버 연동

## CORS 문제 해결의 실제 접근법

### 문제 상황 인식하기

개발자들이 CORS 문제를 처음 마주할 때의 전형적인 시나리오를 살펴보겠습니다.

**상황**: React 앱(`http://localhost:3000`)에서 Express API 서버(`http://localhost:8080`)로 데이터를 요청하려고 한다. 브라우저 개발자 도구를 열어보니 다음과 같은 오류가 나타난다:

```
Access to fetch at 'http://localhost:8080/api/users' from origin 'http://localhost:3000' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present 
on the requested resource.
```

이 오류의 의미를 정확히 이해하는 것이 중요하다. 브라우저는 "서버가 이 요청을 허용한다고 명시적으로 말하지 않았으니 차단하겠다"는 것이다.

### CORS 오류의 다양한 패턴

**1. 기본적인 Origin 문제**
- 가장 흔한 경우로, 서버에 CORS 설정이 전혀 없는 상황
- 해결: 서버에 `Access-Control-Allow-Origin` 헤더 추가

**2. 메서드 허용 문제**
- 서버가 GET만 허용하는데 POST 요청을 보낸 경우
- 해결: `Access-Control-Allow-Methods`에 필요한 메서드 추가

**3. 헤더 허용 문제**
- Authorization 헤더나 커스텀 헤더를 사용하는데 서버가 허용하지 않는 경우
- 해결: `Access-Control-Allow-Headers`에 해당 헤더 추가

**4. 인증 정보 전송 문제**
- 쿠키나 인증 토큰을 포함한 요청인데 서버가 credentials를 허용하지 않는 경우
- 해결: `Access-Control-Allow-Credentials: true` 설정

### Preflight 요청의 이해

많은 개발자들이 놓치는 부분이 바로 Preflight 요청이다. 

**Preflight가 발생하는 조건**:
- PUT, DELETE, PATCH 메서드 사용
- `Content-Type: application/json` 헤더 사용
- `Authorization` 같은 커스텀 헤더 사용

이런 요청들은 브라우저가 실제 요청 전에 OPTIONS 메서드로 "이런 요청을 보내도 되나요?"라고 먼저 물어본다. 서버가 이 OPTIONS 요청에 적절히 응답해야만 실제 요청이 진행된다.

**Preflight 실패의 전형적인 증상**:
- 네트워크 탭에서 OPTIONS 요청이 404나 405 오류로 실패
- 실제 요청은 아예 보내지지 않음
- 브라우저 콘솔에 "Method OPTIONS is not allowed" 같은 오류

### CORS 해결의 주요 전략

#### 1. 서버 측 설정의 중요성

CORS 문제 해결의 핵심은 서버에서 적절한 헤더를 설정하는 것이다. 클라이언트(브라우저) 측에서는 CORS를 우회할 방법이 없다. 이는 보안상 의도된 설계다.

**실무 팁:**
CORS는 서버에서만 해결할 수 있다. 클라이언트는 CORS를 우회할 수 없다.

**기본 원칙**:
- 모든 크로스 오리진 요청은 서버의 명시적 허용이 필요
- 브라우저는 서버 응답의 CORS 헤더를 신뢰
- 클라이언트는 CORS 정책을 우회할 수 없음

#### 2. Origin 설정의 세밀한 제어

**모든 출처 허용 (`*`)**
- 개발 환경에서만 사용 권장
- 프로덕션에서는 보안상 위험
- `credentials: true`와 함께 사용 불가

**특정 도메인만 허용**
- 가장 안전한 방법
- 프로덕션 환경의 표준
- 도메인을 정확히 지정해야 함

**패턴 기반 허용**
- 정규식을 사용한 도메인 패턴 매칭
- 서브도메인 허용에 유용
- 예: `*.example.com` 패턴

#### 3. 메서드와 헤더의 세심한 관리

**HTTP 메서드 제어**:
- 필요한 메서드만 허용
- GET, POST는 기본적으로 허용
- PUT, DELETE, PATCH는 명시적 허용 필요

**헤더 제어**:
- `Content-Type`, `Authorization` 등 커스텀 헤더 허용
- 불필요한 헤더는 제외하여 보안 강화
- `Access-Control-Expose-Headers`로 클라이언트가 읽을 수 있는 헤더 제한

#### 4. Credentials 처리의 주의사항

**Credentials 설정의 의미**:
- 쿠키, 인증 헤더, 클라이언트 인증서 포함 요청 허용
- `Access-Control-Allow-Origin`에 와일드카드(`*`) 사용 불가
- 보안이 중요한 API에서 신중하게 사용

**보안 고려사항**:
- Credentials를 허용하면 CSRF 공격 위험 증가
- 신뢰할 수 있는 도메인에서만 사용
- 적절한 CSRF 보호 메커니즘 필요

### Preflight Request의 심화 이해

#### Preflight의 목적

Preflight Request는 브라우저의 방어적 프로그래밍 철학을 보여주는 사례다. 브라우저는 "이 요청이 서버에 부담을 줄 수 있으니 미리 확인해보자"는 생각으로 작동한다.

**실무 팁:**
Preflight는 실제 요청 전에 OPTIONS 요청을 보낸다. 서버가 OPTIONS 요청을 처리하지 않으면 실제 요청이 차단된다.

**Preflight가 필요한 이유**:
- 서버에 예상치 못한 부하를 주지 않기 위함
- 서버가 지원하지 않는 메서드나 헤더로 인한 오류 방지
- 보안상 위험할 수 있는 요청에 대한 사전 검증

#### Preflight 트리거 조건의 세부 분석

**1. HTTP 메서드 기준**
- **안전한 메서드**: GET, HEAD, POST (기본적으로 Preflight 불필요)
- **위험한 메서드**: PUT, DELETE, PATCH, OPTIONS (Preflight 필요)
- **이유**: 위험한 메서드는 서버 상태를 변경할 수 있어 사전 확인 필요

**2. 헤더 기준**
- **안전한 헤더**: Accept, Accept-Language, Content-Language, Content-Type (특정 값만)
- **위험한 헤더**: Authorization, X-Requested-With, 커스텀 헤더들
- **이유**: 인증이나 커스텀 로직이 포함된 헤더는 서버에 특별한 처리가 필요할 수 있음

**3. Content-Type 기준**
- **안전한 타입**: `text/plain`, `application/x-www-form-urlencoded`, `multipart/form-data`
- **위험한 타입**: `application/json`, `application/xml`
- **이유**: 복잡한 데이터 형식은 서버의 특별한 파싱 로직이 필요할 수 있음

#### Preflight 과정의 상세 분석

**1단계: 브라우저의 판단**
브라우저가 요청을 분석하여 Preflight가 필요한지 결정한다. 위의 조건 중 하나라도 해당되면 Preflight를 시작한다.

**2단계: OPTIONS 요청 전송**
실제 요청 대신 OPTIONS 메서드로 사전 요청을 보낸다. 이 요청에는 다음 정보가 포함된다:
- `Access-Control-Request-Method`: 실제 요청에서 사용할 메서드
- `Access-Control-Request-Headers`: 실제 요청에서 사용할 헤더들
- `Origin`: 요청을 보내는 출처

**3단계: 서버의 응답**
서버는 OPTIONS 요청에 대해 허용 여부를 응답한다:
- `Access-Control-Allow-Methods`: 허용할 메서드들
- `Access-Control-Allow-Headers`: 허용할 헤더들
- `Access-Control-Max-Age`: 이 정보를 캐시할 시간

**4단계: 실제 요청 진행**
서버가 허용한다고 응답하면, 브라우저는 실제 요청을 보낸다. 거부한다면 요청을 차단한다.

#### Preflight 최적화 전략

**캐싱 활용**:
- `Access-Control-Max-Age` 헤더로 Preflight 결과를 캐시
- 동일한 요청에 대해서는 캐시된 정보 사용
- 불필요한 OPTIONS 요청 감소

**Simple Request로 전환**:
- 가능한 경우 Simple Request 조건을 만족하도록 요청 구조 변경
- GET 요청 활용, 안전한 헤더만 사용
- Preflight 오버헤드 제거

## 실무에서의 CORS 관리 전략

### 개발 단계별 CORS 접근법

#### 개발 환경 (Development)
**목표**: 빠른 개발과 디버깅
- 모든 출처 허용 (`*`)으로 설정
- 모든 메서드와 헤더 허용
- Preflight 캐싱 시간을 짧게 설정
- 상세한 CORS 오류 로깅

#### 스테이징 환경 (Staging)
**목표**: 프로덕션과 유사한 환경에서 테스트
- 실제 도메인과 유사한 설정
- 제한된 출처만 허용
- 프로덕션과 동일한 보안 정책 적용
- CORS 오류 모니터링 강화

#### 프로덕션 환경 (Production)
**목표**: 최대 보안과 안정성
- 최소한의 출처만 허용
- 필요한 메서드와 헤더만 허용
- 상세한 CORS 정책 로깅
- 보안 위반 시도 모니터링

### CORS 오류 진단의 체계적 접근

#### 1단계: 오류 메시지 분석
브라우저 콘솔의 CORS 오류 메시지는 매우 구체적이다. 메시지를 정확히 읽으면 문제의 원인을 파악할 수 있다.

**일반적인 오류 패턴**:
- `No 'Access-Control-Allow-Origin' header`: 서버에 CORS 설정이 전혀 없음
- `Request header field X is not allowed`: 특정 헤더가 허용되지 않음
- `Method Y is not allowed`: 특정 HTTP 메서드가 허용되지 않음
- `Credentials are not supported`: 인증 정보 전송이 허용되지 않음

#### 2단계: 네트워크 탭 분석
개발자 도구의 네트워크 탭에서 실제 HTTP 요청과 응답을 확인한다.

**확인 포인트**:
- OPTIONS 요청이 있는가? (Preflight 확인)
- OPTIONS 요청의 응답 상태 코드는?
- 응답 헤더에 적절한 CORS 헤더가 있는가?
- 실제 요청이 전송되었는가?

#### 3단계: 서버 로그 확인
서버 측에서 CORS 관련 요청과 응답을 로깅하여 문제를 추적한다.

### CORS 보안의 주요 원칙

#### 최소 권한 원칙 (Principle of Least Privilege)
**기본 철학**: 필요한 최소한의 권한만 부여

**실제 적용**:
- 필요한 출처만 허용 (와일드카드 사용 금지)
- 필요한 메서드만 허용 (불필요한 메서드 제외)
- 필요한 헤더만 허용 (민감한 헤더 제외)
- 필요한 시간만 캐시 (보안 정책 변경에 유연하게 대응)

#### 방어적 프로그래밍
**기본 철학**: 예상치 못한 상황에 대비

**실제 적용**:
- CORS 정책 변경 시 점진적 적용
- 다양한 환경에서의 CORS 설정 검증
- CORS 오류에 대한 적절한 에러 핸들링
- 정기적인 CORS 정책 검토

#### 투명성과 모니터링
**기본 철학**: CORS 관련 활동을 투명하게 관리

**실제 적용**:
- CORS 요청과 응답에 대한 상세 로깅
- CORS 정책 위반 시도 모니터링
- 정기적인 CORS 설정 검토
- CORS 관련 보안 이벤트 알림

## CORS의 미래와 발전 방향

### 웹 표준의 진화

CORS는 웹 보안의 기본이 되는 Same-Origin Policy를 유지하면서도 현대적인 웹 개발 요구사항을 충족시키기 위해 등장했습니다. 하지만 웹 생태계가 계속 발전하면서 CORS도 함께 진화하고 있습니다.

**최근의 변화**:
- **CORS와 CSP(Content Security Policy)의 통합**: 더 세밀한 보안 제어
- **CORS와 Service Worker의 상호작용**: 오프라인 환경에서의 CORS 처리
- **CORS와 HTTP/3의 호환성**: 새로운 프로토콜에서의 CORS 동작

### 대안 기술들의 등장

CORS가 모든 상황의 해답은 아닙니다. 특정 상황에서는 다른 접근법이 더 적합할 수 있습니다.

**프록시 서버 활용**:
- 클라이언트와 API 서버 사이에 프록시 서버 배치
- 프록시 서버에서 CORS 헤더 추가
- 클라이언트는 같은 출처로 인식

**JSONP (JSON with Padding)**:
- GET 요청만 지원하는 레거시 방법
- 보안상 취약점이 있어 권장되지 않음
- 최신 브라우저에서는 대부분 지원 중단

**서버 사이드 렌더링 (SSR)**:
- 서버에서 API 호출 후 HTML 생성
- 브라우저는 정적 리소스만 요청
- CORS 문제 자체를 회피

### CORS 이해하기

CORS를 이해하려면 다음 사항들을 숙지해야 한다:

**실무 팁:**
CORS는 서버에서 설정하는 보안 메커니즘이다. 개발 환경에서는 모든 출처를 허용할 수 있지만, 프로덕션에서는 특정 도메인만 허용한다.

**기술적 이해**:
- HTTP 헤더의 역할과 의미
- 브라우저의 보안 모델
- 네트워크 프로토콜의 동작 원리

**실무적 경험**:
- 다양한 환경에서의 CORS 설정 경험
- CORS 오류 진단과 해결 경험
- 보안과 개발 편의성의 균형점 찾기

**지속적 학습**:
- 웹 표준의 변화 추적
- 새로운 보안 위협에 대한 대응
- 최적화 기법의 지속적 개선

## 참조

### 공식 문서 및 표준
- [MDN Web Docs - CORS](https://developer.mozilla.org/ko/docs/Web/HTTP/CORS)
- [W3C CORS Specification](https://www.w3.org/TR/cors/)
- [Fetch Living Standard](https://fetch.spec.whatwg.org/)

### 추가 학습 자료
- [OWASP CORS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html#cross-origin-resource-sharing)
- [CORS in Action](https://www.manning.com/books/cors-in-action) - Manning Publications
- [Web Security Academy - CORS](https://portswigger.net/web-security/cors)

### 도구 및 유틸리티
- [CORS Tester](https://www.test-cors.org/) - 온라인 CORS 테스트 도구
- [CORS Anywhere](https://github.com/Rob--W/cors-anywhere) - 개발용 CORS 프록시
- [Browser Developer Tools](https://developer.chrome.com/docs/devtools/) - CORS 디버깅

### 관련 기술
- [Content Security Policy (CSP)](https://developer.mozilla.org/ko/docs/Web/HTTP/CSP)
- [Same-Origin Policy](https://developer.mozilla.org/ko/docs/Web/Security/Same-origin_policy)
- [Cross-Site Request Forgery (CSRF)](https://owasp.org/www-community/attacks/csrf)

