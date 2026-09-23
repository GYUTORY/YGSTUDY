---
title: Cloudflare R2
tags: [cloud, backend, api, performance, security]
updated: 2026-09-23
---

# Cloudflare R2

R2는 Cloudflare가 운영하는 오브젝트 스토리지다. S3와 API가 호환되고, 저장 용량 요금은 S3와 비슷한 수준이지만 egress(다운로드) 비용이 0원이다. 트래픽이 많은 정적 자산이나 미디어 파일을 다룰 때 S3 대비 비용 차이가 꽤 크게 벌어진다.

## egress 비용이 0인 이유와 실제 비용 계산

S3의 egress 요금은 인터넷으로 나가는 데이터에 부과된다. 서울 리전 기준 월 10TB 이상부터 GB당 $0.08이다. 100GB짜리 영상 파일을 1000번 다운로드하면 100TB로 $8,192가 청구된다.

R2는 인터넷 egress 요금이 없다. Workers나 공개 버킷 도메인으로 나가는 데이터 모두 해당한다.

R2 요금 구조는 세 항목이다:

| 항목 | 무료 구간 | 초과 요금 |
|---|---|---|
| 저장 용량 | 월 10GB | $0.015/GB |
| Class A 작업 (PUT, POST, LIST 등) | 월 100만 건 | $4.50/백만 건 |
| Class B 작업 (GET, HEAD 등) | 월 1000만 건 | $0.36/백만 건 |

월 50GB 저장, 다운로드 500만 건, 업로드 50만 건 규모라면 요금 계산은 이렇다:

```
저장: (50 - 10) × $0.015 = $0.60
Class A: 무료 구간 초과 없음 (50만 건)
Class B: 무료 구간 초과 없음 (500만 건)
합계: $0.60/월
```

같은 규모를 S3 서울 리전에서 운용하면 저장 $1.15 + egress $3.20 = $4.35다. egress가 없는 것만으로 차이가 난다.

단, R2는 S3의 Transfer Acceleration, 리전 간 복제, S3 Glacier 같은 스토리지 클래스가 없다. 요구사항이 단순한 정적 파일 서빙이라면 R2가 맞지만, 복잡한 수명 주기 정책이나 다중 리전 복제가 필요하면 S3를 써야 한다.

## 버킷 생성과 접근 정책

대시보드에서 생성하거나 Wrangler CLI로 만든다.

```bash
wrangler r2 bucket create my-bucket
```

버킷 공개 여부는 두 가지로 나뉜다.

**비공개(기본값)**: Workers 바인딩이나 API 토큰으로만 접근 가능하다. presigned URL을 발급해서 외부에 일시적 접근권을 줄 수 있다.

**공개**: 대시보드에서 "Public Access"를 활성화하면 `https://<버킷명>.<계정ID>.r2.cloudflarestorage.com/<키>` 형태의 URL로 누구나 읽을 수 있다. Custom Domain을 연결하면 `https://assets.example.com/<키>`로도 노출된다.

공개 버킷이라도 쓰기는 허용되지 않는다. 읽기만 공개, 쓰기는 인증된 요청만 가능한 구조다.

CORS 설정이 필요한 경우 버킷 단위로 JSON을 등록한다:

```bash
wrangler r2 bucket cors put my-bucket --rules '[
  {
    "allowedOrigins": ["https://example.com"],
    "allowedMethods": ["GET", "PUT"],
    "allowedHeaders": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]'
```

S3의 버킷 정책(Bucket Policy)에 해당하는 세밀한 IAM 규칙은 R2에 없다. 접근 제어는 API 토큰 범위로만 한다. 토큰마다 "Object Read", "Object Read & Write", "Admin Read & Write" 중 하나를 부여한다.

## S3 SDK로 전환

S3 호환 API 엔드포인트는 `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`이다. 기존 S3 클라이언트 코드에서 엔드포인트와 자격증명만 교체하면 된다.

```typescript
import { S3Client, PutObjectCommand, GetObjectCommand } from "@aws-sdk/client-s3";

const r2 = new S3Client({
  region: "auto",  // R2는 리전 개념이 없어서 "auto"로 고정
  endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
  },
});
```

`region: "auto"`가 중요하다. `us-east-1`이나 다른 AWS 리전 값을 넣으면 서명 오류가 난다. R2는 실제로 Cloudflare 네트워크 안에서 가장 가까운 곳에 저장하기 때문에 리전 개념이 없다.

업로드와 다운로드는 일반 S3 SDK 사용법과 동일하다:

```typescript
// 업로드
await r2.send(new PutObjectCommand({
  Bucket: "my-bucket",
  Key: "images/profile/user-123.jpg",
  Body: fileBuffer,
  ContentType: "image/jpeg",
}));

// 다운로드
const response = await r2.send(new GetObjectCommand({
  Bucket: "my-bucket",
  Key: "images/profile/user-123.jpg",
}));
const body = await response.Body?.transformToByteArray();
```

Python boto3도 동일한 방식으로 엔드포인트만 교체한다:

```python
import boto3

r2 = boto3.client(
    "s3",
    region_name="auto",
    endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
    aws_access_key_id=access_key_id,
    aws_secret_access_key=secret_access_key,
)
```

Go의 aws-sdk-go-v2도 `EndpointResolverWithOptions`를 커스텀하거나 `BaseEndpoint`를 설정해서 쓸 수 있다.

## presigned URL 발급

외부 클라이언트가 서버를 거치지 않고 R2에 직접 업로드하거나 다운로드할 때 쓴다. 서버가 서명된 URL을 발급하면 클라이언트는 그 URL로 직접 R2에 요청한다.

```typescript
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

// 업로드용 presigned URL (PUT)
const uploadUrl = await getSignedUrl(
  r2,
  new PutObjectCommand({
    Bucket: "my-bucket",
    Key: `uploads/${userId}/${filename}`,
    ContentType: "image/jpeg",
    ContentLength: fileSizeBytes,  // 크기 제한을 걸 때 명시
  }),
  { expiresIn: 300 }  // 초 단위, 5분
);

// 다운로드용 presigned URL (GET)
const downloadUrl = await getSignedUrl(
  r2,
  new GetObjectCommand({
    Bucket: "my-bucket",
    Key: `uploads/${userId}/${filename}`,
  }),
  { expiresIn: 3600 }
);
```

presigned URL로 업로드받을 때 주의할 점이 있다. `ContentLength`를 명시하지 않으면 클라이언트가 원하는 크기로 올릴 수 있다. 파일 크기 제한이 필요하면 발급 시 `ContentLength`와 `ContentType`을 고정하고, 클라이언트가 다른 값을 보내면 R2가 서명 불일치로 거부한다.

presigned URL의 유효기간은 최대 7일(604,800초)이다. 이보다 긴 접근이 필요하면 공개 버킷이나 Workers로 다른 방식을 써야 한다.

## Workers 바인딩으로 직접 접근

Workers에서 R2를 쓸 때는 S3 SDK 없이 바인딩으로 직접 접근한다. `wrangler.toml`에 바인딩을 선언하면 Workers 런타임이 `env` 객체에 R2 버킷 인스턴스를 주입한다.

```toml
[[r2_buckets]]
binding = "MY_BUCKET"
bucket_name = "my-bucket"
```

```typescript
export interface Env {
  MY_BUCKET: R2Bucket;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const key = url.pathname.slice(1);

    if (request.method === "GET") {
      const object = await env.MY_BUCKET.get(key);
      if (!object) {
        return new Response("Not Found", { status: 404 });
      }

      const headers = new Headers();
      object.writeHttpMetadata(headers);
      headers.set("etag", object.httpEtag);

      return new Response(object.body, { headers });
    }

    if (request.method === "PUT") {
      await env.MY_BUCKET.put(key, request.body, {
        httpMetadata: {
          contentType: request.headers.get("content-type") ?? "application/octet-stream",
        },
      });
      return new Response("OK");
    }

    return new Response("Method Not Allowed", { status: 405 });
  },
};
```

바인딩 방식의 장점은 R2에 대한 요청이 Workers 내부 네트워크를 타기 때문에 API 토큰이나 서명 처리가 필요 없고, 레이턴시도 외부 HTTP 호출보다 낮다.

객체 목록 조회는 `list()` 메서드를 쓴다:

```typescript
const listed = await env.MY_BUCKET.list({
  prefix: `users/${userId}/`,
  limit: 100,
  cursor: nextCursor,  // 페이지네이션
});

for (const object of listed.objects) {
  console.log(object.key, object.size, object.uploaded);
}

if (listed.truncated) {
  // listed.cursor로 다음 페이지 요청
}
```

`list()`는 기본 최대 1000개까지 반환한다. `limit`으로 줄일 수 있고, `truncated`가 `true`이면 다음 페이지가 있다는 뜻이다.

## 마이그레이션 시 실제로 마주치는 문제

**Multipart Upload**: S3의 멀티파트 업로드 API는 R2에서도 동작한다. 다만 최소 파트 크기가 5MB(마지막 파트 제외)라는 S3 규칙이 그대로 적용된다. 이보다 작은 파트를 올리면 `EntityTooSmall` 오류가 난다.

**객체 태깅**: S3의 `PutObjectTagging`, `GetObjectTagging`은 R2가 아직 지원하지 않는다(2026년 기준). 태그 정보를 다른 방식으로 관리해야 한다. 메타데이터(`x-amz-meta-*` 헤더)는 지원된다.

**버전 관리**: S3 버킷 버저닝은 R2에 없다. 이전 버전을 보관해야 하는 경우 키에 버전 정보를 직접 포함하는 방식으로 우회해야 한다.

**체크섬 검증**: `PutObject` 요청에 `x-amz-checksum-sha256` 같은 체크섬 헤더를 넣어 보내면 R2가 검증한다. SDK v3가 기본적으로 체크섬을 붙이는 경우가 있어서 기존 코드가 예상 못한 오류를 낼 수 있다. `requestChecksumCalculation: "when_required"`로 설정해서 끌 수 있다.

```typescript
const r2 = new S3Client({
  // ...
  requestChecksumCalculation: "when_required",
  responseChecksumValidation: "when_required",
});
```
