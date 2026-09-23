---
title: Cloudflare vs CloudFront
tags: [cloud, cdn, performance, network, aws, security]
updated: 2026-09-23
---

# Cloudflare vs CloudFront

둘 다 CDN이지만 출발점이 다르다. Cloudflare는 원래 DNS 리졸버와 보안 프록시로 시작했고, CloudFront는 S3·EC2 앞에 캐시 레이어를 붙이기 위해 만들어졌다. 그 차이가 지금도 각 제품의 강점과 약점을 가른다.

## 네트워크 규모

Cloudflare는 2026년 기준 330개 이상의 PoP를 운영한다. 단순 개수보다 중요한 건 배치 방식이다. Cloudflare는 IXP(인터넷 교환점)에 직접 들어가는 방식을 택했다. 사용자 ISP와 피어링을 맺으면 트래픽이 퍼블릭 인터넷을 덜 거친다. 국내에서 테스트해보면 서울 PoP까지 RTT가 3~7ms 수준으로 나온다.

CloudFront는 AWS 리전 기반으로 엣지 로케이션을 배치한다. 서울 리전(ap-northeast-2) 덕분에 국내 레이턴시는 비슷한 수준이지만, 동남아·아프리카·남미 일부 지역은 Cloudflare보다 PoP 밀도가 낮다. AWS는 정확한 PoP 수를 공개하지 않지만 600개 이상이라고 한다 — 단, 이 숫자에는 리전 엣지 캐시(Regional Edge Cache)까지 포함된다.

실무에서 체감 차이가 나는 경우는 ISP 다양성이 높은 지역이다. 한국처럼 주요 ISP가 몇 개 안 되는 환경에서는 거의 차이가 없다.

## 캐싱 동작

### TTL 정책

CloudFront는 origin에서 내려주는 `Cache-Control`, `Expires` 헤더를 따른다. 헤더가 없으면 기본 TTL 86,400초(24시간)를 쓴다. 최소 TTL(기본 0)과 최대 TTL(기본 31,536,000초)을 캐시 정책으로 별도 설정하는데, 이 세 값의 우선순위가 헷갈린다.

origin이 `max-age=300`을 보내도 CloudFront 캐시 정책의 최소 TTL이 600이면 600초 동안 캐시한다. 반대로 최대 TTL이 60이면 origin이 `max-age=3600`을 보내도 60초에 만료된다. 이걸 모르고 origin 헤더만 맞춰놨다가 캐시가 예상보다 길게 살아있는 경우가 있다.

Cloudflare는 기본적으로 origin 헤더를 따르되, `Cache-Control: no-store` / `no-cache`가 없으면 정적 파일 확장자(css, js, png 등)는 자동으로 엣지 캐시에 올린다. 무료 플랜에서도 이 동작은 켜져 있다. 반면 HTML은 기본적으로 캐시하지 않는다 — 쿠키나 쿼리스트링 기반 동적 콘텐츠를 잘못 캐시하지 않기 위해서다.

### Invalidation 비용

CloudFront는 한 달에 1,000개 경로까지 무료로 무효화(invalidation)할 수 있다. 초과분은 경로당 $0.005다. 와일드카드(`/images/*`)도 1개로 카운트되지만, `/*` 하나로 전체를 날리는 건 일반적으로 권장하지 않는다 — 캐시 히트율이 급격히 떨어져 origin 부하가 치솟는다.

Cloudflare는 무료 플랜에서도 API로 캐시 퍼지(purge)가 가능하고, URL 단위 퍼지는 무제한이다. 다만 무료 플랜의 캐시 퍼지는 약간의 전파 지연이 있다. 태그 기반 퍼지(Cache-Tag)는 Enterprise 플랜에서만 쓸 수 있다.

배포할 때마다 캐시를 퍼지해야 하는 SPA 구조라면 CloudFront의 invalidation 비용이 실제로 쌓인다. 파일명에 해시를 박는 방식(`main.8f2a1c.js`)을 쓰면 퍼지 없이도 되는데, 그렇게 못 하는 환경이 있다.

## 엣지 컴퓨팅

### CloudFront Functions vs Lambda@Edge vs Workers

CloudFront는 엣지 로직 실행을 두 계층으로 나눈다.

**CloudFront Functions**는 엣지 로케이션에서 실행된다. URL 재작성, 헤더 조작, 단순 리다이렉트 용도로만 쓸 수 있다. JavaScript 런타임이지만 `fetch`가 없다 — 외부 API를 부를 수 없다. 실행 시간 한도가 1ms다. 무료 티어는 월 2백만 호출까지다.

**Lambda@Edge**는 리전 엣지(Regional Edge Cache)에서 돌아간다. 진짜 Lambda 함수가 실행되는 것이라 Node.js나 Python을 쓸 수 있고 외부 API 호출도 된다. 대신 콜드스타트가 있고, 함수 배포가 전체 엣지에 전파되는 데 수 분이 걸린다. 요청 당 과금이 일반 Lambda보다 비싸다.

**Cloudflare Workers**는 모든 PoP에서 실행된다. V8 Isolate 방식이라 콜드스타트가 없다. `fetch`로 외부 API를 부를 수 있고, KV Store·Durable Objects·R2·D1 같은 Cloudflare 자체 스토리지와 연결된다. CPU 시간 제한(유료 30ms)이 있지만 대부분 요청 가공 로직은 여기서 끝난다.

A/B 테스트나 인증 토큰 검증처럼 "요청을 가로채서 뭔가를 보고 분기"하는 패턴은 Workers 쪽이 구현하기 편하다. CloudFront로 같은 걸 만들려면 Lambda@Edge를 써야 하는데, 배포 복잡도가 높고 전파 시간도 신경 써야 한다.

```javascript
// Cloudflare Workers: 국가 코드 기반 리다이렉트
export default {
  async fetch(request) {
    const country = request.cf?.country;
    if (country === 'KR') {
      return Response.redirect('https://kr.example.com' + new URL(request.url).pathname, 301);
    }
    return fetch(request);
  }
};
```

```javascript
// CloudFront Functions: 헤더 조작 (fetch 불가)
function handler(event) {
  var request = event.request;
  request.headers['x-forwarded-host'] = { value: request.headers['host'].value };
  return request;
}
```

## WAF·DDoS 보호

Cloudflare WAF는 무료 플랜에도 기본 규칙셋이 포함된다. Pro 이상에서는 OWASP 코어 룰셋과 Cloudflare 관리 규칙셋이 활성화된다. L3/L4 DDoS 보호는 모든 플랜에서 무제한으로 적용된다 — Cloudflare 입장에서 DDoS를 흡수하는 게 자사 네트워크를 지키는 일이기도 해서다.

실제로 3.8 Tbps 규모의 공격을 막은 사례가 있는데, 이 정도 용량은 단순 서비스 약관이 아니라 네트워크 구조의 문제다. Cloudflare 네트워크 자체 용량이 100 Tbps 이상이라 웬만한 볼류메트릭 공격은 그냥 흡수한다.

AWS Shield Standard는 CloudFront를 통해 자동 적용된다. L3/L4 보호는 무료지만, L7 공격(HTTP flood, slowloris 등)은 AWS WAF가 따로 필요하고 유료다. WAF 웹 ACL당 월 $5, 규칙당 $1, 백만 요청당 $0.6이 기본 과금이다. 관리 규칙셋(AWS Managed Rules)을 쓰면 거기에 추가 요금이 붙는다.

Bot 관리도 차이가 난다. Cloudflare Bot Management는 Pro 이상에서 기본 봇 차단이 가능하고, 크리덴셜 스터핑이나 스크레이핑을 막는 기능은 상위 플랜에 있다. AWS WAF도 Bot Control 관리 규칙이 있는데, Common 모드는 월 $10, Targeted 모드는 월 $40에 요청량 과금이 더해진다.

## 가격 구조

가격 비교는 트래픽 패턴에 따라 결과가 달라진다.

**Cloudflare**는 Pro 플랜이 월 $20으로 고정이고, 대역폭 과금이 없다. 엣지에서 내보내는 바이트 수에 돈을 내지 않는다. Workers도 무료 플랜 기준 일 10만 요청까지 무료, 유료($5/월)는 천만 요청까지다.

**CloudFront**는 대역폭과 요청 모두 과금한다. 서울 리전 기준 HTTP 요청 1만 건당 $0.0090, 대역폭은 월 10TB까지 GB당 $0.114다. 대용량 파일을 많이 서빙하는 서비스는 대역폭 비용이 지배적이다. 반면 API 응답처럼 작은 크기의 요청이 많은 패턴은 요청 과금이 더 크다.

실제로 정적 자산을 월 50TB 서빙하면 CloudFront 대역폭 비용만 약 $3,500이 나온다. Cloudflare Pro($20)나 Business($200)와 비교하면 규모가 다른 숫자다. 단, CloudFront는 AWS 서비스 간 트래픽(S3 → CloudFront)은 무료다.

Workers 유사 기능(Lambda@Edge)은 호출 당 $0.0000006, GB-초당 $0.00000625125다. Cloudflare Workers 유료 플랜($5)과 직접 비교하기 어렵지만, 트래픽이 많아질수록 Lambda@Edge 비용이 가파르게 오른다.

## AWS 생태계 통합

CloudFront가 분명히 앞서는 영역이다.

S3 오리진을 CloudFront에 붙이면 OAC(Origin Access Control)로 S3 버킷을 퍼블릭으로 열지 않아도 된다. S3 정적 호스팅을 직접 노출하지 않고 CloudFront만 뚫어두는 구성이 자연스럽다.

ALB를 오리진으로 쓸 때도 CloudFront ↔ ALB 사이에 커스텀 헤더를 심어서 ALB로 직접 들어오는 요청을 막는다. API Gateway도 마찬가지다. IAM 정책으로 접근을 제한하는 것보다 훨씬 단순하다.

WAF 규칙, CloudWatch 메트릭, ACM 인증서, Route 53 — 전부 AWS 콘솔에서 관리한다. 별도 서비스를 배울 필요가 없다.

Cloudflare를 AWS 앞에 붙이는 건 가능하지만, 이 경우 Cloudflare와 AWS 두 곳에서 TLS를 끊어야 하고, 실제 클라이언트 IP를 origin에 전달하는 설정(`CF-Connecting-IP` 헤더 처리)도 직접 해야 한다. Cloudflare에서 AWS WAF로 이중 WAF를 운영하면 정책 충돌 디버깅도 복잡해진다.

## 실무 선택 기준

**Cloudflare가 맞는 경우:**

AWS를 쓰지 않거나, 멀티 클라우드로 운영하는 경우. DNS를 Cloudflare로 옮기면 CDN과 WAF가 자동으로 붙어 오는 구조라 초기 설정이 단순하다.

대역폭이 많이 나가는 서비스. 이미지·동영상 스트리밍처럼 바이트 단위 과금이 부담스러울 때 Cloudflare의 정액제가 유리하다.

Workers로 엣지 로직을 많이 써야 할 때. A/B 테스트, 지역별 콘텐츠 분기, 엣지 캐시 커스터마이징을 코드로 제어하고 싶은 경우.

**CloudFront가 맞는 경우:**

이미 S3, ALB, API Gateway를 쓰고 있고, 이것들을 CDN 뒤에 놓는 게 주목적인 경우. OAC로 S3 버킷을 닫아두는 패턴이 잘 맞는다.

AWS 비용을 한 곳에서 관리하고 싶을 때. CloudFront + WAF + Shield 조합을 AWS 콘솔에서 통합 관리하는 편이 Cloudflare 대시보드를 추가로 운영하는 것보다 편하다.

Lambda@Edge가 아니라 리전 Lambda로 처리하면 되는 수준의 로직이라면 CloudFront Functions로 헤더 조작 정도만 쓰면 충분하다.

둘을 섞는 구성은 권장하지 않는다. Cloudflare를 앞에 두고 CloudFront를 오리진으로 쓰면 캐시가 두 겹이 되고, TTL 불일치로 예상치 못한 캐시가 살아있는 문제가 생긴다. 어느 쪽에서 WAF가 막은 건지도 추적이 어려워진다.