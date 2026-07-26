---
title: GCS CORS 설정
tags: [GCP, Cloud Storage, CORS, 보안, 브라우저 업로드]
updated: 2026-07-26
---

# GCS CORS 설정

브라우저에서 GCS에 직접 파일을 올릴 때 CORS 설정이 없으면 preflight 단계에서 막힌다. 서버를 거치지 않는 클라이언트 직접 업로드(presigned URL 패턴)를 쓰는 경우 CORS 설정이 필수다.

## preflight가 실패하는 이유

브라우저는 실제 요청 전에 `OPTIONS` 메서드로 preflight 요청을 보낸다. GCS에 서명된 URL로 `PUT` 요청을 보낼 때 다음 조건이 하나라도 해당하면 preflight가 발생한다.

- `Content-Type` 헤더가 포함된 경우
- 커스텀 헤더(`x-goog-*` 등)가 있는 경우
- `PUT`, `DELETE` 같은 메서드를 쓰는 경우

preflight에서 GCS가 `Access-Control-Allow-Origin` 헤더를 응답에 포함하지 않으면 브라우저는 본 요청을 보내지 않는다. CORS 설정이 없는 버킷에 preflight를 날리면 GCS는 CORS 관련 헤더를 아예 반환하지 않는다.

```
OPTIONS https://storage.googleapis.com/bucket/object?...
Origin: https://app.example.com
Access-Control-Request-Method: PUT
Access-Control-Request-Headers: content-type

→ 응답에 Access-Control-Allow-Origin 없음
→ 브라우저: CORS 정책 위반
```

서버 사이드 업로드(`axios.put`이 Node.js에서 실행되는 경우)는 브라우저가 개입하지 않아 CORS가 필요 없다. CORS는 순수하게 브라우저의 동일 출처 정책에서 비롯되는 문제다.

## cors.json 작성

CORS 설정은 JSON 배열 형태다. 버킷 하나에 최대 100개의 규칙을 넣을 수 있지만 실무에서는 하나로 충분하다.

```json
[
  {
    "origin": ["https://app.example.com"],
    "method": ["PUT", "GET", "HEAD", "DELETE"],
    "responseHeader": ["Content-Type", "ETag", "x-goog-resumable"],
    "maxAgeSeconds": 3600
  }
]
```

각 필드 설명:

- `origin`: 허용할 출처. 배열로 여러 개 지정 가능하다. 프로토콜과 포트까지 정확히 맞춰야 한다. `https://app.example.com:443`과 `https://app.example.com`은 GCS에서 같은 걸로 인식하지만, 포트를 명시하지 않는 쪽이 일반적이다.
- `method`: 허용할 HTTP 메서드. 서명된 URL로 PUT 업로드를 사용한다면 `PUT`은 필수다.
- `responseHeader`: 브라우저가 접근할 수 있는 응답 헤더 목록. 업로드 후 `ETag`를 확인해야 하는 경우 반드시 포함시킨다.
- `maxAgeSeconds`: preflight 결과를 브라우저가 캐시하는 시간(초). 너무 짧으면 매 업로드마다 preflight가 발생한다.

개발 환경과 운영 환경이 다른 경우, 두 origin을 배열에 넣거나 환경별로 별도 버킷을 쓰는 편이 낫다.

```json
[
  {
    "origin": [
      "https://app.example.com",
      "https://dev.example.com"
    ],
    "method": ["PUT", "GET"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
```

## gcloud로 적용하기

```bash
gcloud storage buckets update gs://my-bucket --cors-file=cors.json
```

적용 후 현재 설정을 확인할 때:

```bash
gcloud storage buckets describe gs://my-bucket --format="json(cors)"
```

설정을 완전히 제거할 때는 빈 배열을 담은 파일을 만들어서 적용한다.

```json
[]
```

```bash
gcloud storage buckets update gs://my-bucket --cors-file=empty-cors.json
```

gsutil을 아직 쓰는 경우:

```bash
gsutil cors set cors.json gs://my-bucket
gsutil cors get gs://my-bucket
```

gsutil은 deprecated 상태라 새 프로젝트에서는 `gcloud storage`를 쓰는 게 낫다.

## 와일드카드 origin의 보안 위험

```json
{
  "origin": ["*"]
}
```

와일드카드를 쓰면 어떤 사이트에서도 해당 버킷으로 요청을 보낼 수 있다. 공개 버킷에서 GET만 허용하는 경우라면 크게 문제가 없다. 하지만 다음 상황에서는 실제 위험이 된다.

**서명된 URL과 함께 쓸 때**: 와일드카드 origin이 설정된 버킷에 서명된 URL을 발급하면, 해당 URL을 탈취한 사람이 어떤 도메인에서도 업로드·다운로드할 수 있다. 서명된 URL 자체가 토큰이라 CORS만으로는 막을 수 없고, origin을 특정 도메인으로 제한해도 URL이 탈취되면 소용없다. 최소한 악의적인 사이트에서 유저 브라우저로 요청하는 CSRF 형태의 시나리오는 차단된다.

**`credentials: include`와 함께 쓸 때**: `XMLHttpRequest`나 `fetch`에서 `credentials: include`를 사용하면 와일드카드 origin은 동작하지 않는다. 브라우저가 `Access-Control-Allow-Origin: *`와 `Access-Control-Allow-Credentials: true`를 동시에 받으면 CORS 오류를 낸다. 와일드카드와 credentials를 같이 쓰는 건 브라우저 명세상 금지다.

운영 버킷에서는 와일드카드 대신 실제 도메인을 명시한다.

## 설정 후 캐시 문제

CORS 설정을 적용해도 브라우저에서 즉시 반영되지 않는 경우가 있다. 두 가지 캐시가 영향을 미친다.

**브라우저 preflight 캐시**: `maxAgeSeconds`에 지정한 시간 동안 preflight 결과가 캐시된다. 이전에 성공한 preflight 결과가 캐시되어 있으면 변경된 설정이 즉시 적용되지 않는다. Chrome 기준으로 실패한 preflight는 캐시하지 않지만, Firefox는 일정 시간 캐시하는 경우가 있다.

캐시를 강제로 무효화하려면 브라우저 개발자 도구에서 "Disable cache" 옵션을 켜고 새로고침하거나, 시크릿 창에서 테스트한다.

**Cloud CDN 캐시**: Cloud CDN을 버킷 앞에 두는 경우, CORS 헤더가 CDN에 캐시될 수 있다. CDN 캐시는 `gcloud compute url-maps invalidate-cdn-cache` 명령으로 제거해야 한다. CORS 설정 변경 후 CDN 캐시까지 날리지 않으면 CDN이 이전 CORS 헤더를 반환한다.

실무에서 CORS 설정을 변경한 후 "여전히 안 된다"는 상황이 나오면 대부분 이 캐시 문제다. 개발자 도구 Network 탭에서 preflight 응답 헤더를 직접 확인해서 `Access-Control-Allow-Origin`이 있는지 보는 게 가장 빠른 확인 방법이다.

## 자주 실수하는 지점

**Content-Type mismatch**: 서명된 URL 생성 시 `content_type`을 지정했는데, 클라이언트에서 실제 PUT 요청의 `Content-Type`이 다르면 서명 검증이 실패한다. CORS 문제가 아니라 서명 문제인데 CORS 문제로 오인하는 경우가 있다. 브라우저 개발자 도구에서 실제 오류 메시지를 읽어야 구분할 수 있다.

**responseHeader 누락**: 업로드 후 응답에서 `ETag`를 읽으려는데 `responseHeader`에 `ETag`를 빠뜨리면 자바스크립트에서 해당 헤더에 접근할 수 없다. 응답 헤더가 있더라도 CORS 설정에서 노출을 허용하지 않으면 브라우저가 차단한다.

**origin 대소문자**: origin은 대소문자를 구분한다. `https://App.example.com`과 `https://app.example.com`은 다르다. 실제 브라우저가 보내는 `Origin` 요청 헤더 값을 Network 탭에서 확인해서 그대로 맞춰야 한다.