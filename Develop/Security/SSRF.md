---
title: "SSRF (Server-Side Request Forgery)"
tags: [security, ssrf, web, cloud]
updated: 2026-03-25
---

# SSRF (Server-Side Request Forgery)

## SSRF란

서버가 사용자 입력으로 받은 URL에 직접 요청을 보내는 경우, 공격자가 그 URL을 조작해서 서버 내부 네트워크나 로컬 서비스에 접근하는 공격이다. 서버가 대신 요청을 보내주는 셈이라, 외부에서는 접근할 수 없는 리소스에 손이 닿는다.

웹훅 URL 입력, 이미지 URL로 썸네일 생성, PDF 렌더링용 URL 입력 같은 기능이 대표적인 SSRF 진입점이다.

---

## 공격 원리

기본적인 흐름은 단순하다.

```
1. 사용자가 URL을 입력한다 (예: 웹훅 등록, 이미지 미리보기)
2. 서버가 해당 URL로 HTTP 요청을 보낸다
3. 공격자가 URL을 내부 주소로 바꾸면, 서버가 내부 리소스에 요청을 보낸다
4. 응답이 공격자에게 돌아온다 (또는 사이드 채널로 정보가 유출된다)
```

서버는 보통 내부 네트워크에 위치하므로, 방화벽 뒤에 있는 서비스에도 접근할 수 있다. 공격자가 직접 `http://192.168.1.10:8080/admin`에 접근하면 차단되지만, 서버를 경유하면 통과한다.

---

## 내부 네트워크 접근 시나리오

### 내부 서비스 스캔

```
POST /api/webhook
{
  "url": "http://192.168.1.1:8080/health"
}
```

응답 코드나 응답 시간 차이로 내부 네트워크에 어떤 서비스가 살아있는지 파악할 수 있다. 포트 스캔도 가능하다.

### 내부 API 호출

```
POST /api/preview
{
  "url": "http://internal-admin.service:3000/users"
}
```

내부 서비스끼리는 인증 없이 통신하는 경우가 많다. 마이크로서비스 환경에서 서비스 간 통신에 별도 인증이 없으면, SSRF 한 번으로 내부 API를 그대로 호출할 수 있다.

### Redis/Memcached 접근

```
POST /api/fetch
{
  "url": "http://localhost:6379"
}
```

Redis가 인증 없이 로컬에서 돌고 있으면, `gopher://` 프로토콜을 이용해 Redis 명령어를 직접 날릴 수 있다.

```
gopher://127.0.0.1:6379/_SET%20pwned%20true%0D%0A
```

---

## 클라우드 메타데이터 탈취

클라우드 환경에서 SSRF가 특히 위험한 이유다.

### AWS IMDSv1

AWS EC2 인스턴스는 `169.254.169.254`에서 메타데이터 서비스를 제공한다. IMDSv1은 단순 GET 요청으로 접근할 수 있어서, SSRF로 바로 털린다.

```
# IAM Role 크레덴셜 탈취
GET http://169.254.169.254/latest/meta-data/iam/security-credentials/

# Role 이름 확인 후 크레덴셜 획득
GET http://169.254.169.254/latest/meta-data/iam/security-credentials/my-role-name
```

응답에 `AccessKeyId`, `SecretAccessKey`, `Token`이 그대로 들어있다. 이걸로 S3, DynamoDB 등 AWS 리소스에 접근할 수 있다. 2019년 Capital One 사고가 정확히 이 패턴이었다.

### GCP

```
# 서비스 계정 토큰 획득
GET http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
```

GCP는 `Metadata-Flavor: Google` 헤더가 필요하지만, 일부 HTTP 클라이언트 라이브러리가 리다이렉트를 따라갈 때 커스텀 헤더를 유지하는 경우가 있어서 우회 가능한 상황이 존재한다.

### Azure

```
GET http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/
```

`Metadata: true` 헤더가 필요하지만, GCP와 비슷한 우회 가능성이 있다.

---

## URL 파싱 우회 기법

단순히 `127.0.0.1`이나 `localhost`를 차단하는 것만으로는 부족하다. 우회 방법이 많다.

### IP 표현 변환

```
# 전부 127.0.0.1을 가리킨다
http://127.0.0.1
http://0x7f000001          # hex
http://2130706433           # decimal
http://0177.0.0.1           # octal
http://127.1                # 축약형
http://0                    # 0.0.0.0 → 일부 시스템에서 localhost로 동작
http://[::1]                # IPv6 loopback
http://[0:0:0:0:0:ffff:127.0.0.1]  # IPv6 mapped IPv4
```

### DNS를 이용한 우회

```
# 127.0.0.1로 resolve되는 도메인
http://localtest.me
http://spoofed.burpcollaborator.net   # 공격자가 DNS를 제어하는 도메인
http://your-domain.com                # A 레코드를 127.0.0.1로 설정
```

### URL 파서 혼동

```
# @ 앞은 userinfo로 해석
http://allowed.com@evil.com

# fragment나 쿼리로 파서 혼동
http://allowed.com#@127.0.0.1
http://127.0.0.1\t.allowed.com    # 일부 파서에서 탭 무시

# URL 인코딩
http://127.0.0.%31
```

### 리다이렉트 이용

allowlist에 있는 외부 URL이 내부 주소로 리다이렉트하게 만든다.

```python
# 공격자 서버
@app.route('/redirect')
def redirect():
    return redirect('http://169.254.169.254/latest/meta-data/', code=302)
```

서버가 리다이렉트를 자동으로 따라가면, 최종 목적지는 메타데이터 서비스다.

---

## 방어 방법

### 1. Allowlist 기반 필터링

가장 확실한 방법은 허용된 도메인/IP만 요청을 보내는 것이다. Denylist는 우회 기법이 너무 많아서 신뢰하기 어렵다.

```java
// Spring - 허용 도메인 검증
public class UrlValidator {

    private static final Set<String> ALLOWED_HOSTS = Set.of(
        "api.github.com",
        "hooks.slack.com"
    );

    public boolean isAllowed(String urlString) {
        try {
            URI uri = new URI(urlString);
            String host = uri.getHost();
            String scheme = uri.getScheme();

            // HTTP/HTTPS만 허용. gopher, file, ftp 등 차단
            if (!"https".equals(scheme)) {
                return false;
            }

            return host != null && ALLOWED_HOSTS.contains(host.toLowerCase());
        } catch (URISyntaxException e) {
            return false;
        }
    }
}
```

allowlist를 쓸 수 없는 경우(사용자가 임의 URL을 입력해야 하는 기능)에는 아래 방법들을 조합한다.

### 2. DNS Resolution 후 IP 검증

URL의 호스트를 먼저 DNS resolve하고, resolve된 IP가 내부 대역인지 확인한다. 단, DNS rebinding 공격에 취약하다.

```java
// Spring - IP 대역 검증
import java.net.InetAddress;

public class SsrfProtection {

    public boolean isInternalIp(String host) throws Exception {
        InetAddress[] addresses = InetAddress.getAllByName(host);

        for (InetAddress addr : addresses) {
            if (addr.isLoopbackAddress()
                || addr.isLinkLocalAddress()
                || addr.isSiteLocalAddress()
                || addr.isAnyLocalAddress()) {
                return true;
            }

            // 169.254.169.254 (클라우드 메타데이터) 명시적 차단
            byte[] bytes = addr.getAddress();
            if (bytes.length == 4
                && (bytes[0] & 0xFF) == 169
                && (bytes[1] & 0xFF) == 254) {
                return true;
            }
        }
        return false;
    }

    public boolean isSafeUrl(String urlString) throws Exception {
        URI uri = new URI(urlString);
        String scheme = uri.getScheme();

        if (!"https".equals(scheme) && !"http".equals(scheme)) {
            return false;
        }

        String host = uri.getHost();
        if (host == null || isInternalIp(host)) {
            return false;
        }

        int port = uri.getPort();
        if (port != -1 && port != 80 && port != 443) {
            return false;
        }

        return true;
    }
}
```

### 3. DNS Rebinding 대응

DNS rebinding은 이렇게 동작한다:

1. 서버가 `evil.com`을 resolve한다 → 외부 IP 반환 (검증 통과)
2. 서버가 실제 요청을 보낸다 → 이때 다시 resolve하면 `127.0.0.1` 반환
3. 결과적으로 내부 주소에 요청이 간다

대응 방법은 **resolve한 IP를 직접 사용**하는 것이다. 호스트명으로 다시 요청하지 않는다.

```javascript
// Node.js - DNS resolve 결과를 직접 사용
const dns = require('dns').promises;
const http = require('http');
const { URL } = require('url');
const net = require('net');

function isPrivateIp(ip) {
    // IPv4 내부 대역 확인
    const parts = ip.split('.').map(Number);
    if (parts.length !== 4) return true; // IPv6 등은 일단 차단

    return (
        parts[0] === 127 ||                          // loopback
        parts[0] === 10 ||                            // 10.0.0.0/8
        (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) || // 172.16.0.0/12
        (parts[0] === 192 && parts[1] === 168) ||     // 192.168.0.0/16
        (parts[0] === 169 && parts[1] === 254) ||     // link-local, 메타데이터
        parts[0] === 0                                 // 0.0.0.0
    );
}

async function safeFetch(urlString) {
    const parsed = new URL(urlString);

    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
        throw new Error('HTTP(S)만 허용');
    }

    // DNS resolve
    const { address } = await dns.lookup(parsed.hostname);

    if (isPrivateIp(address)) {
        throw new Error(`내부 IP 차단: ${address}`);
    }

    // resolve된 IP로 직접 연결 (DNS rebinding 방지)
    return new Promise((resolve, reject) => {
        const options = {
            hostname: address,  // IP 직접 사용
            port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
            path: parsed.pathname + parsed.search,
            method: 'GET',
            headers: {
                'Host': parsed.hostname  // 원래 호스트명은 Host 헤더로
            },
            timeout: 5000
        };

        const req = http.request(options, (res) => {
            // 리다이렉트 따라가지 않음
            if (res.statusCode >= 300 && res.statusCode < 400) {
                reject(new Error('리다이렉트 차단'));
                return;
            }

            let data = '';
            res.on('data', chunk => { data += chunk; });
            res.on('end', () => resolve(data));
        });

        req.on('timeout', () => {
            req.destroy();
            reject(new Error('타임아웃'));
        });
        req.on('error', reject);
        req.end();
    });
}
```

핵심은 두 가지다:

- DNS resolve 결과(IP)로 직접 연결한다. 호스트명으로 다시 요청하면 rebinding에 당한다.
- 리다이렉트를 자동으로 따라가지 않는다. 따라가야 한다면, 리다이렉트 대상 URL도 같은 검증을 거쳐야 한다.

### 4. IMDSv2 강제 (AWS)

AWS를 쓴다면 IMDSv2를 강제하는 게 SSRF의 클라우드 메타데이터 탈취를 막는 가장 직접적인 방법이다.

IMDSv1은 단순 GET 요청이라 SSRF로 바로 접근된다. IMDSv2는 먼저 PUT 요청으로 토큰을 발급받고, 그 토큰을 헤더에 넣어야 메타데이터에 접근할 수 있다.

```bash
# IMDSv2 강제 설정 (인스턴스별)
aws ec2 modify-instance-metadata-options \
    --instance-id i-1234567890abcdef0 \
    --http-tokens required \
    --http-put-response-hop-limit 1

# 새 인스턴스 생성 시
aws ec2 run-instances \
    --metadata-options "HttpTokens=required,HttpPutResponseHopLimit=1" \
    ...
```

`http-put-response-hop-limit 1`은 컨테이너 환경에서 중요하다. hop limit이 2 이상이면 컨테이너 안에서 호스트의 메타데이터에 접근할 수 있다.

Terraform으로 설정하는 경우:

```hcl
resource "aws_instance" "web" {
  # ...

  metadata_options {
    http_tokens                 = "required"  # IMDSv2 강제
    http_put_response_hop_limit = 1
    http_endpoint               = "enabled"
  }
}
```

조직 전체에 IMDSv1을 비활성화하려면 SCP(Service Control Policy)를 건다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": "ec2:RunInstances",
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "StringNotEquals": {
          "ec2:MetadataHttpTokens": "required"
        }
      }
    }
  ]
}
```

### 5. 네트워크 레벨 격리

애플리케이션 서버에서 내부 서비스로의 아웃바운드를 제한한다.

- 웹훅 발송 등 외부 요청이 필요한 서비스는 별도 네트워크 세그먼트에 둔다
- 아웃바운드 방화벽 규칙으로 내부 대역(`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`)으로의 요청을 차단한다
- 프록시 서버를 통해 외부 요청을 중계하고, 프록시에서 목적지를 검증한다

---

## Spring에서 SSRF 방어 적용

실제 웹훅 기능에 SSRF 방어를 적용하는 예시다.

```java
@Service
public class WebhookService {

    private final SsrfProtection ssrfProtection;
    private final RestTemplate restTemplate;

    public WebhookService(SsrfProtection ssrfProtection) {
        this.ssrfProtection = ssrfProtection;

        // 리다이렉트 비활성화
        HttpComponentsClientHttpRequestFactory factory =
            new HttpComponentsClientHttpRequestFactory();
        CloseableHttpClient httpClient = HttpClients.custom()
            .disableRedirectHandling()
            .build();
        factory.setHttpClient(httpClient);
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(5000);

        this.restTemplate = new RestTemplate(factory);
    }

    public void sendWebhook(String url, Object payload) {
        try {
            if (!ssrfProtection.isSafeUrl(url)) {
                throw new IllegalArgumentException("허용되지 않는 URL: " + url);
            }
        } catch (Exception e) {
            throw new IllegalArgumentException("URL 검증 실패", e);
        }

        restTemplate.postForEntity(url, payload, String.class);
    }
}
```

주의할 점:

- `RestTemplate`의 기본 설정은 리다이렉트를 따라간다. 반드시 비활성화한다.
- 타임아웃을 설정하지 않으면, 내부 서비스가 응답하지 않을 때 스레드가 묶인다.
- URL 검증과 실제 요청 사이에 시간 차가 있으면 DNS rebinding에 취약할 수 있다. resolve된 IP로 직접 요청하는 방식이 더 안전하다.

---

## 놓치기 쉬운 SSRF 진입점

URL을 직접 받는 경우만 SSRF가 아니다.

- **XML 파싱 (XXE → SSRF)**: XML의 외부 엔티티(`<!ENTITY>`)가 URL을 가져올 수 있다. XML 파서의 외부 엔티티 처리를 비활성화해야 한다.
- **SVG 업로드**: SVG 안에 `<image href="http://internal/...">` 같은 참조가 들어갈 수 있다. 서버 사이드에서 SVG를 렌더링하면 SSRF가 된다.
- **PDF 생성**: HTML → PDF 변환 시 HTML 안의 리소스 URL을 서버가 가져온다. `<img src="http://169.254.169.254/...">`가 가능하다.
- **Git clone**: 사용자가 입력한 레포 URL로 `git clone`을 실행하면, `git://` 프로토콜이나 내부 주소로 요청이 갈 수 있다.
- **데이터베이스 연결**: JDBC URL 같은 연결 문자열을 사용자가 입력하는 경우, 내부 서비스에 연결을 시도할 수 있다.

---

## 정리

SSRF 방어는 한 가지만으로 되지 않는다. 조합해서 쓴다.

| 계층 | 방법 |
|------|------|
| 입력 검증 | allowlist 기반 URL 필터링, 프로토콜 제한(HTTP/HTTPS만) |
| DNS 레벨 | resolve 후 IP 검증, resolve된 IP로 직접 연결 |
| HTTP 클라이언트 | 리다이렉트 비활성화, 타임아웃 설정 |
| 클라우드 인프라 | IMDSv2 강제, hop limit 1 |
| 네트워크 | 아웃바운드 방화벽, 내부 대역 차단, 프록시 경유 |
