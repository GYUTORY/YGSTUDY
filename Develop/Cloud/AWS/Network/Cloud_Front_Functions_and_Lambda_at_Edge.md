---
title: CloudFront Functions와 Lambda@Edge — 선택과 구현
tags: [aws, cdn, network, javascript, nodejs, security, performance]
updated: 2026-08-27
---

# CloudFront Functions와 Lambda@Edge

CloudFront에서 요청/응답을 중간에 가로채 처리해야 할 때 두 가지 선택지가 있다. CloudFront Functions와 Lambda@Edge다. 이름이 비슷하고 하는 일도 겹치지만, 실행 위치와 제약이 달라서 하나로 해결되는 것을 억지로 다른 걸로 구현하면 사고가 난다.

## 실행 위치

CloudFront Functions는 전 세계 600개 이상의 Edge Location 각각에서 실행된다. 사용자와 물리적으로 가장 가까운 서버에서 돈다. Lambda@Edge는 Regional Edge Cache라고 부르는 13개 리전에서만 실행된다. 사용자가 한국에 있어도 Lambda@Edge 요청은 도쿄나 싱가포르 리전을 거친다.

```
User ─── Edge Location (600+) ─── Regional Edge Cache (13) ─── Origin
               ↑                            ↑
    CloudFront Functions             Lambda@Edge
    viewer-request                   origin-request
    viewer-response                  origin-response
                                     (viewer-request/response도 가능)
```

이 차이가 레이턴시에 직결된다. CloudFront Functions는 사용자 바로 옆에서 실행되니 추가 레이턴시가 거의 없다. Lambda@Edge는 Regional Edge Cache까지 왕복해야 하니 아무리 빨라도 수십 ms가 추가된다.

## 제약 비교

가장 중요한 제약은 CloudFront Functions에서 외부 네트워크 호출이 불가능하다는 점이다. DynamoDB, Redis, 외부 API 어느 것도 호출할 수 없다. 순수하게 요청/응답 객체를 읽고 변환하는 작업만 할 수 있다.

| 항목 | CloudFront Functions | Lambda@Edge |
|------|---------------------|-------------|
| 실행 위치 | Edge Location (600+) | Regional Edge Cache (13) |
| 런타임 | JavaScript (ES5.1 부분 지원) | Node.js 18/20, Python 3.12 |
| 최대 실행 시간 | 1ms | viewer: 5s / origin: 30s |
| 최대 메모리 | 2MB | 128MB ~ 10GB |
| 외부 네트워크 | 불가 | 가능 |
| 이벤트 타입 | viewer-request, viewer-response | 4가지 모두 |
| 가격 | $0.10/백만 요청 | $0.60/백만 요청 + 실행 시간 |

JavaScript 런타임도 다르다. CloudFront Functions는 ECMAScript 5.1 기반인데 완전한 ES5.1도 아니다. `JSON.parse`, `JSON.stringify`, `Date`, `Math`는 된다. `fetch`, `require`, `import`, `Promise`, `async/await` — 전부 안 된다. `console.log`는 되는데 CloudWatch Logs로 바로 안 가고 별도 조회(`aws cloudfront get-function --name ... --stage LIVE`)가 필요하다.

## 이벤트 타입 4가지

```
[사용자 요청]
      ↓
 viewer-request  ← CloudFront Functions 또는 Lambda@Edge
      ↓
 [CloudFront 캐시 확인]
      ↓ (캐시 미스일 때만)
 origin-request  ← Lambda@Edge 전용
      ↓
 [Origin 서버]
      ↓
 origin-response ← Lambda@Edge 전용
      ↓
 [CloudFront 캐시 저장]
      ↓
 viewer-response ← CloudFront Functions 또는 Lambda@Edge
      ↓
 [사용자 응답]
```

캐시 히트가 나면 origin-request와 origin-response는 실행되지 않는다. viewer-request → 캐시 → viewer-response 흐름으로 간다.

**viewer-request**: 사용자 요청이 Edge에 도달한 직후다. 헤더 검사, 리다이렉트, URL 정규화, 간단한 인증을 여기서 처리한다. 응답을 직접 생성해서 Origin까지 요청이 가지 않도록 막을 수도 있다.

**origin-request**: 캐시 미스 시 Origin으로 요청이 나가기 직전이다. 캐시 키에는 없지만 Origin에 전달해야 하는 헤더를 추가하거나, Origin URL을 동적으로 변경하는 데 쓴다.

**origin-response**: Origin이 응답을 보낸 직후, CloudFront가 캐시에 저장하기 전이다. 응답 헤더를 수정하거나, Origin 오류를 커스텀 응답으로 바꾸는 데 쓴다.

**viewer-response**: CloudFront가 사용자에게 응답을 보내기 직전이다. 보안 헤더 추가, 쿠키 설정 같은 마지막 처리를 한다.

## CloudFront Functions 구현

### SPA 라우팅 리라이트

React, Vue 같은 SPA를 S3에 정적 호스팅하면 `/about`, `/dashboard/settings` 같은 경로가 404로 떨어진다. S3에 그 경로에 해당하는 파일이 없기 때문이다. CloudFront Functions의 viewer-request에서 처리한다.

```javascript
function handler(event) {
    var request = event.request;
    var uri = request.uri;
    var staticExtensions = /\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|json|xml|txt|pdf|mp4|webp|avif|map)$/;
    
    if (!staticExtensions.test(uri) && !uri.startsWith('/api/')) {
        request.uri = '/index.html';
    }
    
    return request;
}
```

`uri.includes('.')` 체크만 하면 `/about/team.section` 같은 경로를 파일로 오해해서 리라이트를 건너뛴다. 확장자 목록을 명시하는 편이 안전하다.

### URL 정규화와 쿼리 스트링 정렬

쿼리 스트링 순서가 달라도 같은 캐시를 써야 하는 경우, CloudFront Cache Policy에서 정렬 옵션을 켜는 것이 기본이지만 CloudFront Functions에서 직접 처리할 수도 있다.

```javascript
function handler(event) {
    var request = event.request;
    var qs = request.querystring;
    
    var keys = Object.keys(qs).sort();
    var sorted = {};
    for (var i = 0; i < keys.length; i++) {
        sorted[keys[i]] = qs[keys[i]];
    }
    request.querystring = sorted;
    
    return request;
}
```

CloudFront Functions의 querystring은 문자열이 아니라 객체 형태다. `{ page: { value: '1' }, limit: { value: '10' } }` 구조다. 다중 값은 `multiValue` 배열로 들어온다.

### 보안 헤더 추가

viewer-response에서 보안 헤더를 일괄 추가한다. Origin이 여러 개거나 Origin 코드를 수정하기 어려울 때 CloudFront 레이어에서 처리하면 편하다.

```javascript
function handler(event) {
    var response = event.response;
    var headers = response.headers;
    
    headers['strict-transport-security'] = { value: 'max-age=63072000; includeSubDomains; preload' };
    headers['x-content-type-options'] = { value: 'nosniff' };
    headers['x-frame-options'] = { value: 'DENY' };
    headers['referrer-policy'] = { value: 'strict-origin-when-cross-origin' };
    headers['permissions-policy'] = { value: 'camera=(), microphone=(), geolocation=()' };
    
    return response;
}
```

헤더 이름은 소문자로 써야 한다. CloudFront Functions는 대소문자를 구분한다. `X-Frame-Options`로 쓰면 안 먹는다.

## Lambda@Edge 구현

### A/B 테스트 — 트래픽 분기

viewer-request에서 쿠키를 확인해 사용자를 A/B 버킷에 할당한다. 같은 사용자가 매번 다른 버킷으로 가면 테스트 결과가 오염되니까 쿠키에 한 번 쓴 버킷을 유지한다.

```javascript
exports.handler = async (event) => {
    const request = event.Records[0].cf.request;
    const headers = request.headers;
    
    // 기존 버킷 쿠키 확인
    let bucket = null;
    const cookieHeader = headers.cookie;
    if (cookieHeader) {
        const match = cookieHeader[0].value.match(/ab-bucket=([ab])/);
        if (match) bucket = match[1];
    }
    
    // 신규 방문자 버킷 할당 (50/50)
    if (!bucket) {
        bucket = Math.random() < 0.5 ? 'a' : 'b';
    }
    
    // 버킷에 따라 Origin 경로 분기
    if (bucket === 'b') {
        request.uri = request.uri.replace('/app/', '/app-v2/');
    }
    
    // 버킷 헤더 추가 (Origin에서 분석에 활용)
    headers['x-ab-bucket'] = [{ key: 'X-AB-Bucket', value: bucket }];
    
    return request;
};
```

viewer-response에서 `Set-Cookie`로 버킷 쿠키를 설정하면 다음 요청부터 버킷이 유지된다. 두 함수를 같은 Behavior에 연결해서 쓴다.

Lambda@Edge는 CloudFront 이벤트를 `event.Records[0].cf` 구조로 받는다. CloudFront Functions의 `event.request` 구조와 다르다. 두 서비스 간에 코드를 복붙하면 반드시 터진다.

### JWT 인증 검증

viewer-request에서 Authorization 헤더의 JWT를 검증하고 유효하지 않으면 바로 401을 반환한다. Origin까지 요청이 가지 않으므로 Origin 서버 부담을 줄인다.

```javascript
const crypto = require('crypto');

exports.handler = async (event) => {
    const request = event.Records[0].cf.request;
    const headers = request.headers;
    
    const authHeader = headers.authorization;
    if (!authHeader || !authHeader[0].value.startsWith('Bearer ')) {
        return {
            status: '401',
            statusDescription: 'Unauthorized',
            headers: {
                'www-authenticate': [{ key: 'WWW-Authenticate', value: 'Bearer' }],
                'content-type': [{ key: 'Content-Type', value: 'application/json' }]
            },
            body: JSON.stringify({ error: 'Missing or invalid authorization header' })
        };
    }
    
    const token = authHeader[0].value.slice(7);
    
    try {
        const [headerB64, payloadB64, signatureB64] = token.split('.');
        if (!headerB64 || !payloadB64 || !signatureB64) throw new Error('Invalid structure');
        
        const secret = process.env.JWT_SECRET;
        const signingInput = `${headerB64}.${payloadB64}`;
        const expectedSig = crypto
            .createHmac('sha256', secret)
            .update(signingInput)
            .digest('base64url');
        
        if (signatureB64 !== expectedSig) throw new Error('Invalid signature');
        
        const payload = JSON.parse(Buffer.from(payloadB64, 'base64url').toString());
        
        if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) {
            throw new Error('Token expired');
        }
        
        // 페이로드를 헤더로 전달 (Origin에서 사용자 ID 추출 가능)
        headers['x-user-id'] = [{ key: 'X-User-Id', value: String(payload.sub) }];
        
        return request;
    } catch (err) {
        return {
            status: '401',
            statusDescription: 'Unauthorized',
            headers: {
                'content-type': [{ key: 'Content-Type', value: 'application/json' }]
            },
            body: JSON.stringify({ error: 'Invalid token' })
        };
    }
};
```

Lambda@Edge에서 환경변수는 일반 Lambda처럼 `process.env`로 읽는다. 단, Lambda@Edge 환경변수는 함수 코드에 포함되어 배포된다 — 시크릿을 환경변수로 직접 넣으면 CloudFormation/Terraform 스택에 평문으로 남는다. Secrets Manager를 호출해서 런타임에 가져오는 편이 안전하다. 콜드 스타트나 첫 요청에서 수십 ms가 추가된다.

### 지역 기반 콘텐츠 분기

CloudFront는 `CloudFront-Viewer-Country` 헤더를 자동으로 붙여준다. Lambda@Edge의 origin-request에서 이걸 읽어 다른 Origin으로 라우팅한다.

```javascript
exports.handler = async (event) => {
    const request = event.Records[0].cf.request;
    const headers = request.headers;
    
    const viewerCountry = headers['cloudfront-viewer-country']
        ? headers['cloudfront-viewer-country'][0].value
        : 'US';
    
    const originMap = {
        KR: 'api-kr.example.com',
        JP: 'api-jp.example.com',
        DE: 'api-eu.example.com',
        FR: 'api-eu.example.com',
    };
    
    const originHost = originMap[viewerCountry] || 'api.example.com';
    
    request.origin = {
        custom: {
            domainName: originHost,
            port: 443,
            protocol: 'https',
            path: '',
            sslProtocols: ['TLSv1.2'],
            readTimeout: 10,
            keepaliveTimeout: 5,
            customHeaders: {}
        }
    };
    
    // Host 헤더도 변경 — 안 바꾸면 Origin에서 도메인 불일치 오류
    headers.host = [{ key: 'Host', value: originHost }];
    
    return request;
};
```

`CloudFront-Viewer-Country` 헤더가 origin-request에서 사용 가능하려면 Origin Request Policy에 해당 헤더를 추가해야 한다. viewer-request에서는 CloudFront가 자동으로 붙여주므로 별도 설정 없이 읽을 수 있다.

Host 헤더를 안 바꾸면 Origin 서버에서 "Unknown host" 오류가 난다. ALB 뒤에 다중 도메인을 호스팅하는 경우에 특히 그렇다.

## 두 서비스 선택 기준

외부 네트워크 호출이 필요하다면 Lambda@Edge다. 인증 토큰을 Redis나 DynamoDB로 검증하거나, 설정을 DB에서 읽어야 한다면 Lambda@Edge만 가능하다.

Origin 이벤트(origin-request, origin-response)가 필요하다면 Lambda@Edge다. Origin URL 동적 변경, 다중 Origin 라우팅은 origin-request에서만 처리할 수 있다.

나머지는 CloudFront Functions가 낫다. 빠르고 싸다. 실행 위치가 모든 Edge Location이라 레이턴시 추가가 거의 없다.

비용을 수치로 보면: 월 1억 요청 기준으로 CloudFront Functions는 $10, Lambda@Edge는 $60 + 실행 시간이다. 실행 시간이 평균 1ms면 1억 × 1ms × $0.00000625/128MB-second ≈ $4.9 추가. 합산하면 약 6배 차이다.

CloudFront Functions의 1ms 실행 제한은 실제로 빠듯하다. URL 파싱, 헤더 읽기, 응답 생성 정도는 1ms 안에 들어오지만, 정규표현식이 복잡하거나 대용량 쿠키를 파싱하면 초과할 수 있다. CloudFront Functions 콘솔의 테스트 탭에서 실행 시간을 확인하고 배포한다.

## 배포 시 자주 겪는 문제

**Lambda@Edge는 us-east-1에서만 배포 가능하다.** 함수 자체는 us-east-1에 두고 CloudFront Behavior에 연결하면 AWS가 다른 리전으로 복제한다. ap-northeast-2에서 Lambda를 만들고 연결하려 하면 거부된다.

**Lambda@Edge 수정 후 반영이 느리다.** CloudFront Behavior를 저장하면 전파에 수 분이 걸린다. 이 구간에서 두 버전의 동작이 섞여 간헐적 오류처럼 보인다.

**Lambda@Edge 버전 관리.** `$LATEST` 버전은 CloudFront에 연결할 수 없다. 게시된 버전(버전 번호 있는 ARN)만 연결된다. 코드를 수정하면 새 버전을 게시하고 CloudFront Behavior의 ARN을 업데이트해야 한다. Terraform을 쓴다면 `aws_lambda_function`의 `publish = true`를 설정하고 `qualified_arn`을 참조한다.

**이벤트 객체 구조 혼동.** CloudFront Functions와 Lambda@Edge는 이벤트 구조가 다르다.

CloudFront Functions:
```json
{
    "version": "1.0",
    "context": { "eventType": "viewer-request" },
    "request": {
        "method": "GET",
        "uri": "/test",
        "headers": {
            "host": { "value": "example.com" }
        },
        "querystring": {},
        "cookies": {}
    }
}
```

Lambda@Edge:
```json
{
    "Records": [{
        "cf": {
            "config": { "distributionId": "EDFDVBD6EXAMPLE" },
            "request": {
                "method": "GET",
                "uri": "/test",
                "headers": {
                    "host": [{ "key": "Host", "value": "example.com" }]
                }
            }
        }
    }]
}
```

CloudFront Functions에서는 헤더가 `{ value: '...' }` 형태고, Lambda@Edge에서는 `[{ key: '...', value: '...' }]` 배열 형태다. 두 서비스 간에 코드를 그대로 복붙하면 로컬 테스트는 통과하는데 실제 CloudFront에서 터진다.

**CloudFront Functions에서 `console.log` 확인 방법.** CloudWatch Logs에 바로 안 쌓인다. AWS 콘솔에서 CloudFront → Functions → 함수 선택 → Monitoring 탭에서 확인하거나, CLI로 조회한다.

```bash
aws cloudfront get-function \
    --name my-function \
    --stage LIVE \
    --query 'FunctionCode' \
    --output text | base64 -d
```

로그는 `aws cloudfront describe-function`의 `FunctionExecutionLogs`로 확인한다. 디버깅이 불편해서 복잡한 로직은 로컬에서 단위 테스트를 먼저 작성한다.
