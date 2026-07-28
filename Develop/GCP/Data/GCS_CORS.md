---
title: GCS CORS 설정
tags: [GCP, Cloud Storage, CORS, 보안, 브라우저 업로드, Terraform, resumable upload]
updated: 2026-07-28
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
- `responseHeader`: GCS가 이 값으로 `Access-Control-Expose-Headers`(JS에서 읽을 수 있는 응답 헤더)와 `Access-Control-Allow-Headers`(preflight에서 허용할 요청 헤더)를 동시에 내려보낸다. 업로드 후 `ETag`를 확인해야 하는 경우 반드시 포함시킨다.
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

## Terraform으로 설정하기

인프라를 Terraform으로 관리하는 경우 `google_storage_bucket` 리소스의 `cors` 블록으로 설정한다.

```hcl
resource "google_storage_bucket" "uploads" {
  name     = "my-bucket"
  location = "ASIA-NORTHEAST3"

  cors {
    origin          = ["https://app.example.com"]
    method          = ["PUT", "GET", "HEAD", "DELETE"]
    response_header = ["Content-Type", "ETag", "x-goog-resumable"]
    max_age_seconds = 3600
  }
}
```

JSON의 `responseHeader`가 Terraform에서는 `response_header`(snake_case)로 바뀐다. 헷갈리기 쉬운 부분이다.

기존 버킷에 CORS를 추가하는 경우 `google_storage_bucket` 리소스에 버킷을 import해야 한다. import 없이 `terraform apply`를 돌리면 버킷이 삭제 후 재생성되므로 기존 데이터가 날아갈 수 있다.

환경별로 origin을 달리 줄 때는 variable로 분리하는 게 낫다.

```hcl
variable "allowed_origins" {
  type    = list(string)
  default = ["https://app.example.com"]
}

resource "google_storage_bucket" "uploads" {
  name     = "my-bucket"
  location = "ASIA-NORTHEAST3"

  cors {
    origin          = var.allowed_origins
    method          = ["PUT", "POST", "GET", "HEAD"]
    response_header = ["Content-Type", "ETag", "x-goog-resumable", "Content-Range", "Location"]
    max_age_seconds = 3600
  }
}
```

## Python/Node.js 클라이언트 라이브러리로 설정하기

### Python

`google-cloud-storage` 라이브러리를 사용하면 `bucket.cors` 속성에 직접 배열을 할당하고 `patch()`를 호출한다.

```python
from google.cloud import storage

client = storage.Client()
bucket = client.bucket("my-bucket")
bucket.reload()  # 최신 메타데이터를 먼저 가져온다

bucket.cors = [
    {
        "origin": ["https://app.example.com"],
        "method": ["PUT", "GET", "HEAD", "DELETE"],
        "responseHeader": ["Content-Type", "ETag", "x-goog-resumable"],
        "maxAgeSeconds": 3600,
    }
]
bucket.patch()
print("CORS 설정 완료:", bucket.cors)
```

`reload()` 없이 `patch()`를 바로 호출하면 다른 메타데이터 필드가 덮어씌워질 수 있다. CI/CD 파이프라인에서 버킷 설정을 코드로 관리할 때 자주 빠뜨리는 부분이다. 설정을 초기화할 때는 빈 리스트를 할당한다.

```python
bucket.cors = []
bucket.patch()
```

### Node.js

`@google-cloud/storage` 패키지는 `bucket.setCorsConfiguration()` 메서드를 제공한다.

```javascript
const { Storage } = require('@google-cloud/storage');

const storage = new Storage();
const bucket = storage.bucket('my-bucket');

await bucket.setCorsConfiguration([
  {
    origin: ['https://app.example.com'],
    method: ['PUT', 'GET', 'HEAD', 'DELETE'],
    responseHeader: ['Content-Type', 'ETag', 'x-goog-resumable'],
    maxAgeSeconds: 3600,
  },
]);

const [metadata] = await bucket.getMetadata();
console.log('CORS 설정:', metadata.cors);
```

설정 초기화:

```javascript
await bucket.setCorsConfiguration([]);
```

SDK를 쓸 때도 적용 직후 바로 효과가 나타나지 않는 경우가 있다. GCS 내부 전파 지연 때문이며, gcloud CLI와 동일하다.

## resumable upload와 x-goog-* 헤더 처리

파일이 크면 단일 PUT 대신 resumable upload(청크 업로드)를 써야 한다. GCS XML API 기준 resumable upload 흐름은 두 단계로 나뉜다.

**1단계: 세션 시작**

브라우저가 POST로 업로드 세션을 시작한다. 이때 `x-goog-resumable: start` 헤더를 요청에 포함하고, GCS는 응답에 `x-goog-resumable: start`와 업로드 세션 URI가 담긴 `Location`을 돌려준다.

```
POST https://storage.googleapis.com/my-bucket/my-object?uploadType=resumable
Origin: https://app.example.com
x-goog-resumable: start
Content-Type: application/json

← HTTP/2 200
← x-goog-resumable: start
← Location: https://storage.googleapis.com/...?upload_id=xxxxx
```

JS에서 `response.headers.get('Location')`으로 세션 URI를 읽어야 하기 때문에 `responseHeader`에 `Location`이 없으면 `null`을 반환한다. 네트워크 탭에서 응답 헤더에 `Location`이 분명히 있는데 JS에서 읽지 못한다면 이 누락이 원인이다.

**2단계: 청크 업로드**

세션 URI로 PUT을 보내면서 `Content-Range` 헤더로 청크 위치를 명시한다.

```
PUT {세션 URI}
Content-Range: bytes 0-5242879/10485760
```

`Content-Range`는 preflight를 트리거하는 non-simple 헤더다. `responseHeader`에 포함시켜야 preflight에서 허용된다.

resumable upload를 지원하는 최종 cors.json:

```json
[
  {
    "origin": ["https://app.example.com"],
    "method": ["PUT", "POST", "GET", "HEAD", "DELETE"],
    "responseHeader": [
      "Content-Type",
      "Content-Range",
      "ETag",
      "x-goog-resumable",
      "Location"
    ],
    "maxAgeSeconds": 3600
  }
]
```

단순 PUT 업로드만 쓰는 경우 `POST`, `Content-Range`, `Location`은 없어도 된다. resumable upload를 나중에 추가할 때 기존 설정을 덮어쓰지 않도록 주의한다.

## curl로 preflight 검증하기

CORS 설정 적용 후 브라우저 없이 curl로 OPTIONS 요청을 직접 보내서 확인할 수 있다.

```bash
curl -v -X OPTIONS \
  -H "Origin: https://app.example.com" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: content-type" \
  "https://storage.googleapis.com/my-bucket/dummy-object"
```

정상 응답이면 다음 헤더가 내려온다.

```
< HTTP/2 200
< access-control-allow-origin: https://app.example.com
< access-control-allow-methods: PUT
< access-control-allow-headers: content-type
< access-control-max-age: 3600
< vary: Origin
```

`access-control-allow-origin`이 없으면 CORS 설정이 아직 전파 안 된 것이거나 origin이 일치하지 않는 것이다. `-H "Origin: ..."` 값을 cors.json의 origin 배열에 있는 값과 정확히 맞춰야 한다. `https://app.example.com/`처럼 끝에 슬래시를 붙이면 매칭이 안 된다.

resumable upload용 헤더까지 확인할 때:

```bash
curl -v -X OPTIONS \
  -H "Origin: https://app.example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type, x-goog-resumable" \
  "https://storage.googleapis.com/my-bucket/dummy-object"
```

`access-control-allow-headers`에 `x-goog-resumable`이 포함되어 있으면 정상이다. 버킷이나 오브젝트가 존재하지 않아도 OPTIONS 요청은 CORS 응답을 정상적으로 내려주기 때문에 테스트할 때 실제 오브젝트가 없어도 된다.

## 설정 전파 지연

gcloud CLI, SDK, Terraform 모두 CORS를 적용해도 GCS 내부적으로 설정이 전파되는 데 시간이 걸린다. 짧으면 수 분, 길면 20~30분까지 걸리는 경우도 있다. 적용 직후 curl로 OPTIONS를 날려도 CORS 헤더가 없다면 전파가 아직 진행 중인 것이다.

이 상태에서 계속 설정을 바꿔보거나 재적용해도 결과가 달라지지 않는다. `gcloud storage buckets describe`로 설정값이 맞게 들어갔는지 먼저 확인하고, 몇 분 기다린 뒤 다시 curl로 검증하는 게 낫다.

```bash
# 설정 확인
gcloud storage buckets describe gs://my-bucket --format="json(cors)"

# 몇 분 후 preflight 재검증
curl -v -X OPTIONS \
  -H "Origin: https://app.example.com" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: content-type" \
  "https://storage.googleapis.com/my-bucket/test"
```

전파 지연은 GCS SLA 범위 밖이라 강제로 당길 방법이 없다. 실무에서는 CORS 설정 변경을 배포 전날 먼저 적용해두는 편이다.

## 설정 후 캐시 문제

CORS 설정을 적용해도 브라우저에서 즉시 반영되지 않는 경우가 있다. 두 가지 캐시가 영향을 미친다.

**브라우저 preflight 캐시**: `maxAgeSeconds`에 지정한 시간 동안 preflight 결과가 캐시된다. 이전에 성공한 preflight 결과가 캐시되어 있으면 변경된 설정이 즉시 적용되지 않는다. Chrome 기준으로 실패한 preflight는 캐시하지 않지만, Firefox는 일정 시간 캐시하는 경우가 있다.

캐시를 강제로 무효화하려면 브라우저 개발자 도구에서 "Disable cache" 옵션을 켜고 새로고침하거나, 시크릿 창에서 테스트한다.

**Cloud CDN 캐시**: Cloud CDN을 버킷 앞에 두는 경우, CORS 헤더가 CDN에 캐시될 수 있다. CDN 캐시는 `gcloud compute url-maps invalidate-cdn-cache` 명령으로 제거해야 한다. CORS 설정 변경 후 CDN 캐시까지 날리지 않으면 CDN이 이전 CORS 헤더를 반환한다.

실무에서 CORS 설정을 변경한 후 "여전히 안 된다"는 상황이 나오면 대부분 이 캐시 문제다. 개발자 도구 Network 탭에서 preflight 응답 헤더를 직접 확인해서 `Access-Control-Allow-Origin`이 있는지 보는 게 가장 빠른 확인 방법이다.

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

## 자주 실수하는 지점

**Content-Type mismatch**: 서명된 URL 생성 시 `content_type`을 지정했는데, 클라이언트에서 실제 PUT 요청의 `Content-Type`이 다르면 서명 검증이 실패한다. CORS 문제가 아니라 서명 문제인데 CORS 문제로 오인하는 경우가 있다. 브라우저 개발자 도구에서 실제 오류 메시지를 읽어야 구분할 수 있다.

**responseHeader 누락**: 업로드 후 응답에서 `ETag`를 읽으려는데 `responseHeader`에 `ETag`를 빠뜨리면 자바스크립트에서 해당 헤더에 접근할 수 없다. 응답 헤더가 있더라도 CORS 설정에서 노출을 허용하지 않으면 브라우저가 차단한다.

**origin 대소문자**: origin은 대소문자를 구분한다. `https://App.example.com`과 `https://app.example.com`은 다르다. 실제 브라우저가 보내는 `Origin` 요청 헤더 값을 Network 탭에서 확인해서 그대로 맞춰야 한다.
