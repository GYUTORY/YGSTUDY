---
title: HTTP Status Code
tags: [network, 7-layer, application-layer, http, status-code, rest-api, troubleshooting]
updated: 2026-05-14
---

# HTTP Status Code

## 개요

HTTP 상태 코드는 서버가 클라이언트 요청을 어떻게 처리했는지 알려주는 3자리 숫자다. 첫 자리로 큰 카테고리가 나뉘고, 두 번째·세 번째 자리로 세부 의미가 결정된다. RFC 9110에서 정의한 표준 코드 외에도 IANA 레지스트리에 등록된 확장 코드가 있고, Cloudflare·Nginx 같은 벤더가 자체적으로 쓰는 비표준 코드(520, 522 등)도 실무에서 자주 본다.

운영 중인 API에서 상태 코드를 잘못 쓰면 클라이언트가 재시도 로직을 잘못 짠다든지, 모니터링 대시보드의 5xx 비율이 왜곡된다든지, CDN 캐싱이 의도와 다르게 동작하는 문제가 생긴다. 5년 정도 백엔드를 굴려 보면 "200으로 다 내리고 body에 success 필드 박는" 코드를 한 번씩은 겪게 되는데, 이게 왜 문제인지 본문에서 정리한다.

## 카테고리 5분할

| 범주 | 의미 | 대표 코드 |
|------|------|-----------|
| 1xx | Informational, 처리 중 | 100, 101, 103 |
| 2xx | Success, 성공 | 200, 201, 202, 204, 206 |
| 3xx | Redirection, 추가 작업 필요 | 301, 302, 303, 304, 307, 308 |
| 4xx | Client Error, 클라이언트 잘못 | 400, 401, 403, 404, 405, 409, 422, 429 |
| 5xx | Server Error, 서버 잘못 | 500, 502, 503, 504 |

1xx는 거의 볼 일이 없다. WebSocket 핸드셰이크에서 101 Switching Protocols, Early Hints 기능에서 103을 쓰는 정도다. 100 Continue는 클라이언트가 `Expect: 100-continue` 헤더를 보냈을 때 본문을 보내도 된다고 알려 주는 용도지만, 실제로 브라우저나 라이브러리에서 명시적으로 쓰는 경우는 드물다.

## 2xx 성공

### 200 OK

가장 흔한 코드. GET 요청이 성공했고 body에 결과가 들어 있다는 뜻이다. POST/PUT/PATCH도 결과를 body로 돌려줄 거면 200을 쓴다. body가 없을 거면 204가 맞다.

### 201 Created

리소스가 새로 생성됐을 때 쓴다. POST로 새 글을 만들고 그 글 정보를 돌려줄 때 201이 정석이다. 같이 `Location` 헤더에 새 리소스 URI를 박아 주는 게 관례다.

```http
HTTP/1.1 201 Created
Location: /api/posts/12345
Content-Type: application/json

{"id": 12345, "title": "..."}
```

PUT으로 멱등 생성할 때(존재하지 않는 ID로 PUT을 해서 새로 만들었을 때)도 201이다. 기존 리소스를 갱신했으면 200 또는 204다.

### 202 Accepted

요청은 받았는데 아직 처리 안 끝났다는 뜻. 비동기 작업 큐에 넣고 즉시 응답할 때 쓴다. 응답 body나 `Location` 헤더에 진행 상태를 조회할 URL을 같이 주는 게 일반적이다. 배치 작업, 이메일 발송 큐, 동영상 인코딩 같은 시나리오에서 쓴다.

### 204 No Content

처리는 성공했는데 돌려줄 body가 없다. DELETE가 대표적이다. PUT 갱신 후 굳이 갱신된 리소스를 돌려줄 필요 없을 때도 204를 쓴다. 클라이언트가 PATCH 한 결과를 화면에 다시 그릴 필요가 없는 경우 204로 내려서 트래픽을 아낀다.

`Content-Length: 0`이거나 헤더 자체가 없어야 한다. body를 뭐라도 채워서 보내면 일부 클라이언트가 파싱 에러를 낸다.

### 206 Partial Content

`Range` 헤더로 일부만 요청했을 때의 응답. 동영상 스트리밍, 큰 파일 다운로드 재개 기능에서 쓴다. `Content-Range: bytes 0-1023/146515`처럼 어느 구간을 보냈는지 알려 줘야 한다. S3 presigned URL로 큰 파일 다운받을 때 보면 이걸로 동작한다.

## 3xx 리다이렉션

여기가 헷갈리는 구간이다. 301/302/303/307/308 다섯 개의 미묘한 차이를 정리해 둬야 한다.

| 코드 | 영구/임시 | 메서드 변경 | 캐시 | SEO 영향 |
|------|-----------|-------------|------|----------|
| 301 Moved Permanently | 영구 | 허용(역사적) | 강하게 캐시 | PageRank 이전 |
| 302 Found | 임시 | 허용(역사적) | 약하게 캐시 | 이전 안 됨 |
| 303 See Other | 임시 | 강제로 GET | 캐시 안 됨 | 이전 안 됨 |
| 307 Temporary Redirect | 임시 | 메서드 보존 | 약하게 캐시 | 이전 안 됨 |
| 308 Permanent Redirect | 영구 | 메서드 보존 | 강하게 캐시 | PageRank 이전 |

### 301 vs 308

원래 301은 RFC 상으로는 메서드를 바꾸지 말아야 했지만, 역사적으로 브라우저들이 POST를 GET으로 바꿔 버렸다. 이걸 명확히 하려고 308이 추가됐다. 308은 "영구 이동이고, 메서드도 그대로 유지하라"는 강한 보장이다.

API 엔드포인트를 영구 이동시킬 거면 308을 쓰는 게 맞다. POST `/api/v1/users`를 `/api/v2/users`로 옮겼는데 301로 응답하면 일부 클라이언트가 GET으로 재요청해서 405 Method Not Allowed로 깨진다.

### 302 vs 303 vs 307

302도 역사적 모호함이 있어서 303과 307이 나왔다.

- 303 See Other: POST 처리 후 결과 페이지로 보낼 때. PRG(Post-Redirect-Get) 패턴에서 쓴다. 폼 제출 후 새로고침 시 중복 제출 방지용.
- 307: 메서드 그대로 유지하면서 임시로 다른 위치로. 예를 들어 메인 서버 점검 중에 백업 서버로 POST 그대로 흘려보낼 때.

대부분의 실무 코드는 302를 그냥 쓴다. 브라우저 동작이 사실상 303과 같게 굳어져 있어서다.

### 304 Not Modified

조건부 GET의 응답. 클라이언트가 `If-None-Match`(ETag) 또는 `If-Modified-Since`를 보냈는데 변경된 게 없으면 304를 돌려준다. body는 보내지 않는다. CDN, 브라우저 캐시 검증에 쓴다.

```http
GET /api/posts/12345 HTTP/1.1
If-None-Match: "abc123"

HTTP/1.1 304 Not Modified
ETag: "abc123"
Cache-Control: max-age=3600
```

304는 클라이언트가 캐시한 버전을 그대로 쓰라는 의미다. body 없이도 ETag, Cache-Control 같은 메타 헤더는 보내야 한다.

### 캐싱·SEO 영향

301/308은 브라우저가 영구 캐시한다. 한 번 잘못 박으면 사용자 브라우저에서 캐시가 풀릴 때까지 잘못된 곳으로 계속 간다. 운영 사이트에서 301을 쓸 때는 정말 영구 이동인지 확인하고 써야 한다. 임시 점검 페이지로 보내는데 301을 박았다가 점검 끝나도 사용자가 점검 페이지로 가는 사고를 본 적이 있다.

검색 엔진은 301/308을 받으면 새 URL로 인덱스를 옮기고 PageRank를 이전한다. 302/307은 원래 URL을 유지한다. 사이트 도메인 이전, URL 구조 변경 같은 SEO가 중요한 작업에서는 반드시 301을 써야 한다.

## 4xx 클라이언트 에러

### 400 Bad Request

요청 자체가 문법적으로 깨졌을 때. JSON 파싱 실패, 필수 헤더 누락, Content-Length가 음수 같은 경우다. 검증 실패와는 구분해서 써야 한다.

### 401 Unauthorized vs 403 Forbidden

이름이 헷갈리는 대표 사례다.

- 401: 인증 안 됨. 너 누군지 모르겠으니 자격 증명을 보내라. `WWW-Authenticate` 헤더를 같이 보내야 표준이다.
- 403: 인증은 됐지만 권한 없음. 누군지는 알겠는데 이 리소스에 접근할 권한이 없다.

토큰 만료, 토큰 미첨부 → 401. 일반 사용자가 관리자 API 호출 → 403. JWT가 위조됐거나 서명 검증 실패 → 401. 본인 글이 아닌데 수정 시도 → 403.

실무에서는 보안상 일부러 둘을 구분 안 하고 둘 다 404로 내리는 경우도 있다. 리소스 존재 여부 자체를 노출하고 싶지 않을 때(예: 비공개 저장소 URL)다. GitHub가 그렇게 한다.

### 404 Not Found

리소스가 없다. URL이 잘못됐거나 ID가 존재하지 않을 때다. 라우팅 자체가 매칭 안 되는 경우와, 라우팅은 됐지만 DB에 데이터 없는 경우 둘 다 404로 묶는 게 일반적이다.

### 405 Method Not Allowed

URL은 맞는데 메서드를 잘못 썼다. `/api/posts/12345`에 POST를 보냈는데 그 엔드포인트가 GET/PUT/DELETE만 받을 때 405다. `Allow` 헤더에 허용 메서드 목록을 같이 줘야 한다.

```http
HTTP/1.1 405 Method Not Allowed
Allow: GET, PUT, DELETE
```

### 409 Conflict

리소스 상태가 충돌한다. 같은 이메일로 회원가입 시도(unique 제약 위반), 낙관적 락 버전 불일치, 이미 삭제된 리소스에 대한 작업 등에 쓴다. body에 충돌 사유를 구체적으로 적어 줘야 클라이언트가 대응할 수 있다.

### 422 Unprocessable Entity vs 400

이게 또 자주 헷갈린다.

- 400: 요청 자체가 깨짐. JSON 파싱 실패, 형식 오류.
- 422: 요청 형식은 맞는데 의미적 검증 실패. 이메일 포맷 잘못됨, 비밀번호 길이 부족, 필수 필드 누락.

JSON은 잘 파싱되는데 비즈니스 룰을 위반한 경우가 422다. Spring Validation, Pydantic, Joi 같은 검증 라이브러리에서 걸리는 에러는 거의 다 422로 내리는 게 맞다.

```json
{
  "error": "validation_failed",
  "details": [
    {"field": "email", "message": "유효하지 않은 이메일 형식"},
    {"field": "password", "message": "최소 8자 이상"}
  ]
}
```

다만 Rails나 일부 프레임워크는 검증 실패도 그냥 400으로 내리는 컨벤션이 있어서, 팀 내 합의로 한쪽으로 통일하는 게 낫다. 양쪽을 섞어 쓰면 클라이언트 에러 핸들링이 지저분해진다.

### 429 Too Many Requests

레이트 리밋 초과. `Retry-After` 헤더에 언제 다시 시도할 수 있는지 알려 줘야 한다. 두 가지 형식이 있다.

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60

# 또는 절대 시각
Retry-After: Wed, 14 May 2026 10:00:00 GMT
```

대부분 초 단위 정수로 보낸다. 클라이언트는 이 값을 보고 재시도 백오프를 정한다. `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` 같은 비표준 헤더로 현재 한도 정보도 같이 주면 클라이언트가 미리 대응하기 좋다.

429를 무시하고 그냥 재시도하는 클라이언트가 많은데, 운영하는 입장에서는 `Retry-After`를 지키지 않는 IP를 일시 차단하거나 429를 더 길게 유지하는 식으로 방어한다.

## 5xx 서버 에러

### 500 Internal Server Error

서버 코드에서 예외가 터졌다. NPE, DB 커넥션 실패, 디스크 풀 같은 거. 클라이언트가 잘못한 게 없는 모든 경우에 쓰는 fallback이다. 운영 중에 500 비율이 늘면 알람이 울려야 한다.

500의 응답 body에 스택 트레이스를 그대로 담으면 안 된다. 정보 노출이고 보안 사고로 이어진다. `error_id`만 주고 실제 로그는 서버에서 찾는 식으로 처리한다.

### 502 Bad Gateway

게이트웨이(보통 리버스 프록시)가 백엔드로부터 잘못된 응답을 받았다. Nginx 뒤의 애플리케이션이 죽었거나, 응답 형식이 깨졌을 때 502가 난다. ALB 뒤의 ECS 태스크가 헬스체크 실패로 빠졌을 때, ALB는 일단 요청을 넘기다가 다른 태스크에서도 실패하면 502를 돌려준다.

### 503 Service Unavailable

서버가 일시적으로 처리할 수 없는 상태. 점검 중, 과부하, 큐 가득 참 같은 경우다. `Retry-After` 헤더를 같이 주는 게 표준이다.

502와의 차이: 503은 "내가(이 서버가) 지금 못 한다"이고, 502는 "내가 호출한 다음 단의 서버가 이상하다"이다. 운영 중에 503이 보이면 자기 자신의 용량 문제, 502가 보이면 백엔드 문제로 1차 분류한다.

### 504 Gateway Timeout

게이트웨이가 백엔드 응답을 기다리다가 타임아웃났다. ALB의 idle timeout이 60초인데 백엔드가 90초 걸리면 504가 난다. Nginx의 `proxy_read_timeout` 초과도 504다.

504가 나오면 일단 의심해야 할 것:
- 백엔드 처리 시간이 길어졌나 (DB 슬로우 쿼리, 외부 API 지연)
- 게이트웨이 타임아웃 설정이 짧은가
- 백엔드 스레드/커넥션 풀이 고갈됐나

### 502 vs 503 vs 504 트러블슈팅

| 코드 | 1차 의심 | 확인 방법 |
|------|----------|-----------|
| 502 | 백엔드 프로세스 죽음, 응답 깨짐 | 백엔드 로그, 컨테이너 상태 |
| 503 | 자체 과부하, 점검 모드 | 자기 서버 CPU/메모리, 큐 길이 |
| 504 | 백엔드 처리 지연 | 백엔드 응답 시간, DB 슬로우 쿼리 |

Nginx 액세스 로그에서 5xx만 추적할 때:

```bash
# 5xx 응답만 카운트
awk '$9 ~ /^5/' /var/log/nginx/access.log | wc -l

# 5xx 코드별 분포
awk '$9 ~ /^5/ {print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# 5xx 발생한 URL 상위
awk '$9 ~ /^5/ {print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20
```

ALB의 경우 CloudWatch 메트릭으로 `HTTPCode_ELB_5XX_Count`(ALB 자체가 낸 5xx)와 `HTTPCode_Target_5XX_Count`(타깃이 낸 5xx)를 분리해서 본다. 전자가 늘면 ALB-타깃 사이 문제, 후자가 늘면 애플리케이션 문제다.

## 멱등성과 상태 코드

HTTP 메서드의 멱등성 정의:

- GET, HEAD, PUT, DELETE: 멱등 (몇 번을 호출해도 결과 동일)
- POST, PATCH: 비멱등

멱등 메서드가 5xx로 실패하면 클라이언트가 안전하게 재시도할 수 있다. 비멱등 메서드는 재시도하면 중복 처리될 위험이 있다. 그래서 결제 같은 POST 요청은 별도의 idempotency key를 헤더로 받아서 서버가 중복을 걸러 낸다.

상태 코드와 메서드의 조합으로 클라이언트의 재시도 전략이 달라진다:

| 메서드 | 응답 | 재시도 가능? |
|--------|------|--------------|
| GET | 5xx, 429 | 안전, 백오프로 재시도 |
| POST | 500, 502, 503, 504 | 위험, idempotency key 없으면 금지 |
| PUT/DELETE | 5xx | 안전, 결과 동일 |
| 모든 | 4xx (429 제외) | 재시도 의미 없음, 요청 자체 수정 필요 |

## REST API 설계 시 상태 코드 선택 기준

### 흔히 잘못 쓰는 케이스

1. 모든 응답을 200으로 내리고 body의 `success: true/false`로 분기
   - 클라이언트 라이브러리(axios, fetch)의 에러 인터셉터가 동작 안 한다. 4xx/5xx 모니터링이 무의미해진다.

2. 검증 실패에 500 사용
   - 서버 잘못이 아니라 클라이언트 입력이 잘못된 거다. 422 또는 400이 맞다. 500이 늘어나면 진짜 서버 장애가 묻힌다.

3. 인증 실패에 200 + body에 에러 메시지
   - 401을 안 쓰면 인증 실패가 모니터링 대시보드에서 안 보인다. 토큰 만료 비율 추적이 불가능하다.

4. 리소스 없을 때 200 + 빈 배열·null
   - 단일 리소스 조회는 404가 맞다. 컬렉션 조회의 경우 빈 배열은 200이 맞다. 둘을 헷갈리면 안 된다.

5. POST 생성 후 200
   - 새로 만들었으면 201이다. 이게 모니터링 대시보드에서 "새 가입 수" 같은 메트릭을 뽑을 때 차이를 만든다.

### 결정 흐름

```
요청 받음
├─ JSON 파싱 실패, 헤더 깨짐 → 400
├─ 인증 토큰 없음/만료 → 401
├─ 인증은 됐는데 권한 없음 → 403
├─ URL 매칭 안 됨, 리소스 없음 → 404
├─ 메서드 잘못 → 405
├─ 입력 검증 실패 → 422
├─ 상태 충돌(중복 등) → 409
├─ 레이트 리밋 → 429
├─ 처리 성공
│   ├─ 새 리소스 생성 → 201
│   ├─ 비동기 처리 시작 → 202
│   ├─ 결과 body 있음 → 200
│   └─ 결과 body 없음 → 204
└─ 서버 에러
    ├─ 백엔드 응답 이상 → 502
    ├─ 자체 과부하/점검 → 503
    ├─ 백엔드 타임아웃 → 504
    └─ 그 외 예외 → 500
```

## curl/Postman 실제 응답 예제

### 200 OK 정상 응답

```bash
$ curl -i https://httpbin.org/get
HTTP/2 200
date: Wed, 14 May 2026 10:00:00 GMT
content-type: application/json
content-length: 312

{
  "args": {},
  "headers": {...},
  "url": "https://httpbin.org/get"
}
```

### 201 Created 응답 확인

```bash
$ curl -i -X POST https://httpbin.org/anything \
  -H "Content-Type: application/json" \
  -d '{"name":"test"}'
HTTP/2 200
content-type: application/json
...
```

(httpbin은 항상 200을 돌려주지만, 실제 API라면 다음과 같은 응답을 본다)

```http
HTTP/1.1 201 Created
Location: /api/users/12345
Content-Type: application/json

{"id": 12345, "name": "test"}
```

### 401 인증 실패

```bash
$ curl -i https://api.example.com/private
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="api"
Content-Type: application/json

{"error": "missing_token"}
```

### 429 레이트 리밋

```bash
$ curl -i https://api.github.com/rate_limit_test
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1715680800

{"message": "API rate limit exceeded"}
```

### 상태 코드만 빠르게 확인

```bash
# 코드만 출력
$ curl -o /dev/null -s -w "%{http_code}\n" https://example.com
200

# 응답 시간까지
$ curl -o /dev/null -s -w "code=%{http_code} time=%{time_total}s\n" https://example.com
code=200 time=0.342s

# 리다이렉트 따라가기
$ curl -L -o /dev/null -s -w "%{http_code} %{url_effective}\n" http://github.com
200 https://github.com/

# 리다이렉트 체인 모두 보기
$ curl -L -o /dev/null -s -w "%{http_code}\n" -D - http://github.com 2>&1 | grep -E "^HTTP|^Location"
HTTP/1.1 301 Moved Permanently
Location: https://github.com/
HTTP/2 200
```

### 304 캐시 검증

```bash
# 첫 요청으로 ETag 받기
$ curl -i https://api.example.com/posts/1
HTTP/1.1 200 OK
ETag: "abc123"

# 같은 ETag로 조건부 요청
$ curl -i -H 'If-None-Match: "abc123"' https://api.example.com/posts/1
HTTP/1.1 304 Not Modified
ETag: "abc123"
```

## 실무에서 자주 만나는 문제

### Nginx에서 백엔드가 죽었을 때

업스트림 전부 죽으면 502, 일부만 죽고 응답이 느려지면 504, Nginx 자체가 점검 페이지 서빙 중이면 503이 난다. `error_log`에 `connect() failed`, `upstream timed out` 같은 메시지가 같이 찍히니까 그걸로 1차 진단한다.

### CDN과 304

CloudFront, CloudFlare 같은 CDN 뒤에 API를 두면 304를 잘못 다뤄서 stale 응답이 가는 경우가 있다. CDN이 자체적으로 ETag를 생성하는 경우와 origin의 ETag를 그대로 패스하는 경우가 다르고, 캐시 무효화 시점도 다르다. API 응답에 `Cache-Control: no-store`를 명시해서 CDN이 캐시 안 하게 하는 게 안전한 경우가 많다.

### 401 무한 리프레시 루프

토큰 만료 → 401 → 리프레시 토큰으로 갱신 → 다시 요청 → 또 401 패턴이 무한 반복되는 버그. 리프레시 토큰도 만료됐는데 클라이언트가 그걸 감지 못 하고 계속 시도하는 경우다. 리프레시 엔드포인트가 401을 돌려주면 강제 로그아웃 처리해야 한다.

### 502 짧은 스파이크

배포 중에 잠깐 502가 튀는 경우가 있다. 새 컨테이너가 뜨면서 ALB가 헬스체크 통과 전에 트래픽을 보내거나, 구 컨테이너가 graceful shutdown 안 해서 in-flight 요청이 끊기는 경우다. graceful shutdown 타임아웃 설정과 ALB target group의 deregistration delay를 맞춰 줘야 한다.

### 504 vs 클라이언트 타임아웃

서버는 정상 응답했는데 클라이언트가 먼저 타임아웃 끊으면 클라이언트 입장에선 에러지만 서버 로그에는 200으로 찍힌다. 504는 게이트웨이가 명시적으로 돌려주는 코드라서, 클라이언트-서버 사이에 게이트웨이가 없다면 504 자체가 발생할 수 없다. 클라이언트가 "504 났다"고 하면 정말 504인지 클라이언트 측 타임아웃인지 먼저 구분해야 한다.

## 참고 표준

- RFC 9110: HTTP Semantics (상태 코드 정의)
- RFC 7231~7235: 구 HTTP/1.1 명세 (RFC 9110으로 통합됨)
- IANA HTTP Status Code Registry: https://www.iana.org/assignments/http-status-codes/
