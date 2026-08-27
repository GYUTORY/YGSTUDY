---
title: CDN + Adaptive Thumbnail
tags: [aws, cdn, cloud, performance, backend, architecture]
updated: 2026-08-27
---

## 전체 파이프라인 구조

S3에 원본 이미지를 저장하고, CloudFront가 CDN 레이어를 맡고, Lambda@Edge가 요청 시점에 리사이즈와 포맷 변환을 처리한다. 단순해 보이지만 캐시 키를 잘못 설계하면 Lambda가 매 요청마다 실행되고, 리사이즈 비용이 CDN을 쓰는 이유를 완전히 상쇄한다.

```
브라우저 → CloudFront → origin-request Lambda@Edge → S3 원본
                ↑                                        ↓
         캐시 히트 반환                            Sharp 변환 후 응답
```

Lambda@Edge는 네 가지 이벤트 훅 중 `origin-request`에서만 이 작업을 해야 한다. `viewer-request`에 넣으면 캐시를 우회해 매 요청마다 Lambda가 실행된다. `origin-request`는 캐시 미스일 때만 실행되니 히트율이 곧 비용이다.

## 캐시 키 설계

CloudFront의 기본 캐시 키는 URL 경로만 포함한다. 리사이즈 파라미터를 쿼리 스트링으로 받는다면 `w`, `h`, `fmt`, `q`를 캐시 키에 포함시켜야 한다. 이걸 빠뜨리면 첫 번째 요청의 변환 결과가 다른 크기 요청에 그대로 반환된다.

CloudFront Cache Policy 설정에서 Query Strings를 "Include specified keys"로 지정하고 `w`, `h`, `fmt`, `q`를 나열한다. Headers에는 `Accept`를 추가한다. `Accept` 헤더로 WebP/AVIF를 협상하는 경우 이게 캐시 키에 없으면 WebP를 지원하는 브라우저에 JPEG가 나갈 수 있다.

```
캐시 키 구성 요소:
  경로: /images/product/abc.jpg
  쿼리: w=800&h=600&fmt=webp&q=80
  헤더: Accept (포맷 협상 시)
→ 캐시 키: /images/product/abc.jpg?w=800&h=600&fmt=webp&q=80 + Accept값
```

쿼리 파라미터 조합이 무한정 늘어나면 캐시 히트율이 떨어진다. 클라이언트가 임의의 크기를 요청할 수 있다면 Lambda 호출 횟수가 급격히 증가한다. 실무에서는 허용 크기를 화이트리스트로 제한한다. `w=347`은 받지 않고 `w=360`으로 강제 치환한다.

```javascript
const ALLOWED_WIDTHS = [360, 480, 720, 1080, 1440];
const ALLOWED_HEIGHTS = [360, 480, 720, 1080];

function normalizeWidth(w) {
  const n = parseInt(w, 10);
  if (!n || n <= 0) return 720;
  return ALLOWED_WIDTHS.find(aw => aw >= n) || ALLOWED_WIDTHS[ALLOWED_WIDTHS.length - 1];
}
```

## Accept 헤더 기반 포맷 협상

브라우저가 `Accept: image/avif,image/webp,*/*;q=0.8`을 보내면 Lambda에서 이걸 파싱해 포맷을 결정한다. `fmt` 쿼리 파라미터를 명시한 경우 그게 우선이고, 없으면 Accept 헤더로 폴백한다.

```javascript
function resolveFormat(request) {
  const params = new URLSearchParams(request.querystring);
  const explicit = params.get('fmt');
  if (explicit && ['webp', 'avif', 'jpeg', 'png'].includes(explicit)) {
    return explicit;
  }

  const accept = request.headers['accept']?.[0]?.value || '';
  if (accept.includes('image/avif')) return 'avif';
  if (accept.includes('image/webp')) return 'webp';
  return 'jpeg';
}
```

AVIF는 WebP보다 압축률이 30~50% 높지만 Sharp에서 인코딩 시간이 2~4배 걸린다. 캐시 히트율이 충분하면 문제없지만, 첫 요청이 몰리는 상황(배포 직후, 이벤트 페이지 오픈)에서는 Lambda 타임아웃이 발생할 수 있다. 이 경우 AVIF를 일시적으로 비활성화하거나 사전 워밍업을 별도로 돌린다.

## Sharp 기반 origin-request 핸들러

Lambda@Edge는 Lambda와 다르게 실행 환경 제약이 있다. us-east-1에서만 배포 가능하고, 메모리는 128MB~10GB지만 실행 시간 제한이 `origin-request`에서 30초다. Sharp는 네이티브 바이너리를 포함하므로 Lambda@Edge 배포 패키지 안에 `linux-x64` 바이너리를 함께 묶어야 한다.

```javascript
const AWS = require('aws-sdk');
const Sharp = require('sharp');

const S3 = new AWS.S3({ region: 'ap-northeast-2' });
const BUCKET = 'my-image-bucket';

exports.handler = async (event) => {
  const request = event.Records[0].cf.request;
  const params = new URLSearchParams(request.querystring);

  const w = normalizeWidth(params.get('w'));
  const h = params.get('h') ? normalizeHeight(params.get('h')) : null;
  const fmt = resolveFormat(request);
  const quality = Math.min(Math.max(parseInt(params.get('q') || '85', 10), 10), 100);

  // 파라미터 없으면 원본 반환
  if (!params.get('w') && !params.get('h') && !params.get('fmt')) {
    return request;
  }

  const key = decodeURIComponent(request.uri.replace(/^\//, ''));

  let s3Object;
  try {
    s3Object = await S3.getObject({ Bucket: BUCKET, Key: key }).promise();
  } catch (e) {
    return { status: '404', body: 'Not Found' };
  }

  let pipeline = Sharp(s3Object.Body).resize({
    width: w,
    height: h || undefined,
    fit: h ? 'cover' : 'inside',
    withoutEnlargement: true,
  });

  if (fmt === 'webp') pipeline = pipeline.webp({ quality });
  else if (fmt === 'avif') pipeline = pipeline.avif({ quality });
  else pipeline = pipeline.jpeg({ quality, progressive: true });

  const buffer = await pipeline.toBuffer();

  const contentTypeMap = { webp: 'image/webp', avif: 'image/avif', jpeg: 'image/jpeg', png: 'image/png' };

  return {
    status: '200',
    headers: {
      'content-type': [{ key: 'Content-Type', value: contentTypeMap[fmt] }],
      'cache-control': [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }],
    },
    bodyEncoding: 'base64',
    body: buffer.toString('base64'),
  };
};
```

Lambda@Edge 응답 바디는 base64 인코딩이고 최대 1MB다. 리사이즈 후에도 1MB를 초과하는 경우가 있다. PNG나 고해상도 JPEG가 대표적이다. 이 경우 Lambda가 예외 없이 조용히 실패하거나 CloudFront가 502를 반환한다. 응답 전 `buffer.length`를 체크해서 초과 시 품질을 낮추거나 원본으로 리다이렉트하는 로직이 필요하다.

## 기존 URL을 깨지 않는 마이그레이션

이미 배포된 상태에서 리사이즈 파라미터 방식을 추가하는 경우, 기존 `/images/product/abc.jpg` 형태 URL은 그대로 동작해야 한다. 파라미터 없는 요청은 Lambda를 거치지 않고 S3 원본을 그대로 반환하면 된다.

문제는 기존에 CloudFront에 캐시된 원본 응답이 있다면 Lambda를 추가해도 해당 캐시가 살아있는 동안 Lambda가 실행되지 않는다는 점이다. 캐시 무효화 없이 Lambda를 붙이면 일부 요청은 새 동작, 일부는 기존 캐시가 섞이는 상황이 생긴다.

마이그레이션 순서:

1. Lambda@Edge 함수를 배포하되 아직 CloudFront 동작(Behavior)에 연결하지 않는다.
2. 기존 캐시를 일괄 무효화한다 (`/*`).
3. CloudFront Behavior에 Lambda@Edge를 origin-request로 연결한다.
4. 파라미터 없는 요청이 원본을 그대로 반환하는지 확인한다.

단계적으로 특정 경로(`/images/*`)에만 먼저 적용하고 이상 없으면 전체로 확장하는 방식이 안전하다.

## 히트율 vs Lambda 호출 횟수

캐시 히트율이 낮으면 Lambda가 자주 실행되고, 변환 비용과 응답 지연이 증가한다. 히트율에 영향을 주는 요소는 크게 두 가지다.

**파라미터 조합 수**: 클라이언트가 `w=347`, `w=350`, `w=360`을 각각 요청하면 세 가지 캐시 엔트리가 생긴다. 화이트리스트로 정규화하면 모두 `w=360`으로 모인다.

**캐시 TTL**: `Cache-Control: public, max-age=31536000`으로 1년을 지정해도 CloudFront의 최소 TTL 설정이 이를 무시하면 짧게 만료된다. Behavior의 Minimum TTL을 0으로 두면 Lambda 응답의 Cache-Control을 그대로 따른다.

CloudFront 콘솔의 Cache Statistics에서 `CacheHitRate`를 확인한다. 70% 미만이면 파라미터 정규화를 먼저 점검한다. 90% 이상이면 Lambda 호출 횟수보다 S3 GET 비용과 데이터 전송 비용이 더 크다.

## 사전 생성 vs 온디맨드

온디맨드 리사이즈의 약점은 첫 요청 응답이 느리다는 점이다. Lambda 콜드 스타트(200~500ms) + Sharp 변환(100~800ms) + S3 GET 시간이 합산된다. 첫 방문자가 로딩 지연을 체감한다.

사전 생성은 원본 업로드 시점에 필요한 크기를 미리 만들어 S3에 저장한다. Lambda@Edge 없이 순수 S3 + CloudFront로 서빙 가능하고, 첫 요청부터 S3 원본을 반환하니 지연이 없다.

```
사전 생성 파이프라인 (S3 이벤트 기반):
원본 업로드 → S3 Event → SQS → Lambda 리사이즈 워커
  → S3에 /images/product/abc_w360.webp, abc_w720.webp ... 저장
```

사전 생성의 문제는 조합 폭발이다. 해상도 5개 × 포맷 3개 = 원본 1개당 파일 15개. 이미지 100만 장이면 1,500만 파일이 된다. S3 스토리지 비용보다 운영 복잡도가 문제다. 이미지를 삭제하거나 교체할 때 파생 파일을 전부 정리해야 한다.

실무에서 흔한 선택은 **혼합 방식**이다. 주요 크기(360, 720, 1080)만 업로드 시점에 사전 생성해두고, 그 외 요청은 온디맨드로 처리한다.

```javascript
// 업로드 후 사전 워밍업
async function preheat(key) {
  const sizes = [360, 720, 1080];
  const formats = ['webp', 'jpeg'];
  const cdnBase = 'https://cdn.example.com';

  const requests = sizes.flatMap(w =>
    formats.map(fmt =>
      fetch(`${cdnBase}/${key}?w=${w}&fmt=${fmt}`)
    )
  );
  await Promise.all(requests);
}
```

CDN에 요청을 보내는 방식으로 캐시를 미리 채운다. Lambda가 실행되고 그 결과가 CloudFront에 캐싱되니, 이후 실제 사용자 요청은 캐시 히트로 처리된다.

## srcset 연동

HTML `srcset`과 `sizes`로 브라우저가 화면 해상도에 맞는 크기를 선택하게 한다.

```html
<img
  src="/images/product/abc.jpg?w=720&fmt=jpeg"
  srcset="
    /images/product/abc.jpg?w=360&fmt=webp 360w,
    /images/product/abc.jpg?w=720&fmt=webp 720w,
    /images/product/abc.jpg?w=1080&fmt=webp 1080w
  "
  sizes="(max-width: 480px) 360px, (max-width: 1024px) 720px, 1080px"
  width="720"
  height="480"
  loading="lazy"
  decoding="async"
  alt="상품 이미지"
>
```

`src`는 WebP를 지원하지 않는 구형 브라우저 폴백이다. `srcset`에 `fmt=webp`를 지정했을 때 Accept 헤더로 포맷을 결정하면 캐시 키가 Accept 헤더 값에 따라 달라진다. `fmt` 쿼리를 명시하는 방식이 캐시 키를 단순하게 유지한다.

Retina 디스플레이(2x)를 지원하려면 각 크기의 2배 너비 이미지가 필요하다. 360px로 표시하는 자리에 720px 이미지를 쓴다. `srcset`에 `1x`, `2x` 디스크립터를 쓰거나 `w` 디스크립터로 처리한다.

```html
srcset="
  /images/product/abc.jpg?w=360&fmt=webp 360w,
  /images/product/abc.jpg?w=720&fmt=webp 720w,
  /images/product/abc.jpg?w=1440&fmt=webp 1440w
"
sizes="(max-width: 480px) 360px, 720px"
```

360px 화면에서 2x 기기는 720w를 선택하고, 720px 화면에서 2x 기기는 1440w를 선택한다.

## 운영 중 자주 터지는 문제

**Lambda@Edge 함수 교체 반영 지연**: Lambda@Edge를 새 버전으로 교체해도 CloudFront 엣지 로케이션에 전파되는 데 10~20분 걸린다. 버그를 고쳐 배포했는데 일부 엣지에서 여전히 구 버전이 실행되는 경우가 있다. 급하면 캐시 무효화와 함께 처리한다.

**Sharp 네이티브 바이너리 아키텍처 불일치**: 맥에서 `npm install`로 설치한 Sharp를 그대로 배포하면 Lambda(linux-x64) 환경에서 실행되지 않는다. 배포 패키지 빌드를 Docker(amazonlinux 이미지)에서 하거나 `npm install --platform=linux --arch=x64` 옵션으로 설치한다.

**1MB 응답 한도 무음 실패**: Lambda@Edge가 1MB를 초과하는 응답을 반환하면 CloudFront가 502 Bad Gateway를 반환한다. Lambda 로그에는 아무것도 남지 않는다. CloudWatch Logs에서 `us-east-1` 리전의 Lambda@Edge 로그 그룹을 확인해야 한다 (`/aws/lambda/us-east-1.함수이름`).

**캐시 무효화 비용**: 파일을 교체할 때 CloudFront 무효화는 월 1,000건 무료, 초과 시 건당 $0.005다. 전체 무효화(`/*`)는 1건으로 처리되지만 무효화 완료까지 5~10분 걸린다. 이미지 교체가 잦다면 파일명에 버전(해시)을 넣어 무효화 없이 처리하는 게 낫다.
