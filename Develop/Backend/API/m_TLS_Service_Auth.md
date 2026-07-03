---
title: "서비스 간 API 인증 — mTLS"
tags: [API, mTLS, Security, Zero-Trust, Certificate, Service-Mesh]
updated: 2026-04-07
---

# 서비스 간 API 인증 — mTLS

## mTLS가 뭔가

TLS는 클라이언트가 서버의 인증서를 검증하는 단방향 인증이다. mTLS(mutual TLS)는 여기에 서버가 클라이언트의 인증서도 검증하는 과정이 추가된다. 양쪽 다 인증서를 제시하고, 양쪽 다 상대방을 검증한다.

일반적인 HTTPS 통신에서는 브라우저가 서버 인증서만 확인한다. 서버는 클라이언트가 누구인지 모른다. mTLS에서는 서버가 클라이언트에게도 인증서를 요구한다. 클라이언트가 유효한 인증서를 제시하지 못하면 연결 자체가 성립되지 않는다.

핸드셰이크 과정을 정리하면 이렇다:

1. 클라이언트가 서버에 연결 요청
2. 서버가 자신의 인증서를 클라이언트에 전달
3. 클라이언트가 서버 인증서를 CA로 검증
4. **서버가 클라이언트에게 인증서를 요청** (여기가 일반 TLS와 다른 부분)
5. 클라이언트가 자신의 인증서를 서버에 전달
6. 서버가 클라이언트 인증서를 CA로 검증
7. 양쪽 모두 검증 완료 후 암호화 통신 시작

## 내부 API에 JWT 대신 mTLS를 쓰는 경우

마이크로서비스 환경에서 서비스 간 인증을 JWT로 하는 곳이 많다. 잘 동작하지만, 몇 가지 상황에서는 mTLS가 더 맞다.

### JWT의 한계

JWT는 애플리케이션 레이어(L7) 인증이다. 토큰을 HTTP 헤더에 넣어서 보내고, 받는 쪽에서 서명을 검증한다. 문제는:

- **토큰 탈취 가능성**: 네트워크 구간에서 토큰이 노출되면 만료 전까지 재사용할 수 있다. TLS 위에서 보내더라도, 로그에 찍히거나 중간 프록시에서 복호화되는 경우가 있다.
- **각 서비스마다 검증 로직 필요**: 토큰 파싱, 서명 검증, 클레임 확인 코드를 서비스마다 넣어야 한다. 라이브러리가 있어도 설정 실수가 생긴다.
- **토큰 갱신 관리**: 서비스가 수십 개면 토큰 발급/갱신 로직이 복잡해진다. 특히 서비스 간 호출 체인이 길어지면 토큰 전파 방식을 정해야 한다.

### mTLS가 맞는 경우

- **서비스 아이덴티티만 확인하면 될 때**: "이 요청이 order-service에서 온 건가?"만 확인하면 되는 경우. 사용자 정보나 권한 같은 클레임이 필요 없다.
- **네트워크 레벨에서 차단해야 할 때**: 인증서가 없으면 TCP 연결 자체가 안 된다. 애플리케이션 코드에 도달하기 전에 차단된다.
- **서비스 메시를 쓰는 환경**: Istio, Linkerd 같은 서비스 메시는 사이드카 프록시가 mTLS를 자동으로 처리한다. 애플리케이션 코드를 수정할 필요가 없다.

반대로 mTLS만으로 부족한 경우도 있다. 사용자별 권한이 필요하거나, 서비스 간 세분화된 접근 제어가 필요하면 mTLS + JWT를 같이 쓴다. mTLS로 서비스 아이덴티티를 확인하고, JWT로 사용자 컨텍스트를 전달하는 구조다.

## Zero-Trust 통신과 서비스 메시

### Zero-Trust의 핵심

Zero-Trust는 "네트워크 위치를 신뢰하지 않는다"는 원칙이다. 같은 VPC 안에 있어도, 같은 쿠버네티스 클러스터 안에 있어도, 모든 통신을 검증한다.

예전에는 방화벽 안쪽은 안전하다고 봤다. 그래서 내부 서비스 간 통신은 평문 HTTP로 하는 곳이 많았다. 문제는 공격자가 내부 네트워크에 한번 들어오면 lateral movement가 자유롭다는 것이다. 내부 통신에 인증이 없으니까.

mTLS는 Zero-Trust를 구현하는 기본 수단이다. 모든 서비스 간 통신에 상호 인증을 적용하면, 내부 네트워크에 침입하더라도 유효한 인증서 없이는 다른 서비스와 통신할 수 없다.

### 서비스 메시에서의 mTLS

Istio를 예로 들면, 각 Pod에 Envoy 사이드카 프록시가 붙는다. 서비스 간 통신은 실제로 Envoy-to-Envoy 통신이다. Envoy가 mTLS를 알아서 처리하기 때문에 애플리케이션은 평문 HTTP로 통신하면 된다.

```yaml
# Istio PeerAuthentication — 네임스페이스 전체에 mTLS 강제
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT
```

`STRICT` 모드로 설정하면 해당 네임스페이스의 모든 서비스가 mTLS 없이는 통신할 수 없다. `PERMISSIVE` 모드도 있는데, 이건 mTLS와 평문 HTTP를 동시에 허용한다. 마이그레이션 과정에서만 쓰고, 운영에서는 반드시 `STRICT`로 전환해야 한다.

Istio는 내부적으로 SPIFFE(Secure Production Identity Framework For Everyone) 표준을 사용해서 서비스 아이덴티티를 관리한다. 각 서비스에 `spiffe://cluster.local/ns/production/sa/order-service` 같은 형태의 ID가 부여되고, 이걸 기반으로 AuthorizationPolicy를 작성한다:

```yaml
# 특정 서비스만 접근 허용
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: payment-service-policy
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/production/sa/order-service"]
    to:
    - operation:
        methods: ["POST"]
        paths: ["/api/v1/payments"]
```

이렇게 하면 payment-service는 order-service의 POST 요청만 받는다. 다른 서비스가 payment-service에 접근하려 하면 403이 반환된다.

## 인증서 구조와 CA 운영

### 인증서 체인

mTLS를 운영하려면 인증서 체인을 이해해야 한다:

- **Root CA**: 최상위 인증 기관. 자체 서명 인증서를 가진다. 오프라인으로 보관하는 게 원칙이다.
- **Intermediate CA**: Root CA가 서명한 중간 CA. 실제 서비스 인증서 발급에 사용한다.
- **Leaf Certificate**: 각 서비스에 발급되는 인증서. Intermediate CA가 서명한다.

Root CA의 개인키가 유출되면 전체 PKI가 무너진다. 그래서 Root CA는 HSM(Hardware Security Module)에 보관하고, 네트워크에 연결하지 않는다. 일상적인 인증서 발급은 Intermediate CA가 담당한다.

### 인증서에 들어가는 정보

서비스용 인증서에는 최소한 이 정보가 들어간다:

- **CN(Common Name)**: 서비스 식별 이름. 예: `order-service.production.svc.cluster.local`
- **SAN(Subject Alternative Name)**: DNS 이름이나 IP 주소. CN보다 SAN을 우선 검증하는 게 표준이다.
- **유효 기간**: 짧을수록 안전하다. 서비스 인증서는 보통 24시간~90일.
- **Key Usage**: `Digital Signature`, `Key Encipherment` 등. 인증서의 용도를 제한한다.

```bash
# 인증서 내용 확인
openssl x509 -in service.crt -text -noout

# 인증서 체인 검증
openssl verify -CAfile ca-chain.crt service.crt

# mTLS 연결 테스트
openssl s_client -connect payment-service:443 \
  -cert client.crt \
  -key client.key \
  -CAfile ca.crt
```

## 인증서 갱신 자동화

인증서 만료는 운영 사고의 단골 원인이다. 수동 갱신은 반드시 실수가 생긴다. 자동화는 선택이 아니다.

### cert-manager (쿠버네티스 환경)

쿠버네티스에서는 cert-manager가 표준이다. 인증서 발급, 갱신, 시크릿 저장을 자동으로 처리한다.

```yaml
# Issuer 정의 — 내부 CA 사용
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: internal-ca-issuer
spec:
  ca:
    secretName: internal-ca-keypair

---
# 서비스별 인증서 요청
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: order-service-cert
  namespace: production
spec:
  secretName: order-service-tls
  duration: 720h        # 30일
  renewBefore: 168h     # 만료 7일 전에 갱신
  issuerRef:
    name: internal-ca-issuer
    kind: ClusterIssuer
  commonName: order-service.production.svc.cluster.local
  dnsNames:
  - order-service.production.svc.cluster.local
  - order-service.production.svc
  - order-service
  privateKey:
    algorithm: ECDSA
    size: 256
```

`renewBefore` 설정이 핵심이다. 만료 7일 전에 갱신을 시작하면, 갱신에 실패하더라도 대응할 시간이 있다. 인증서 만료까지 갱신 재시도를 반복한다.

### Vault PKI (비쿠버네티스 환경)

HashiCorp Vault의 PKI 시크릿 엔진을 사용하면 온프레미스 환경에서도 자동화가 가능하다.

```bash
# PKI 엔진 활성화
vault secrets enable pki
vault secrets tune -max-lease-ttl=87600h pki

# Root CA 생성
vault write pki/root/generate/internal \
  common_name="Internal Root CA" \
  ttl=87600h

# Intermediate CA 설정
vault secrets enable -path=pki_int pki
vault write pki_int/intermediate/generate/internal \
  common_name="Internal Intermediate CA"

# Role 생성 — 서비스별 인증서 발급 정책
vault write pki_int/roles/service-cert \
  allowed_domains="production.svc.cluster.local" \
  allow_subdomains=true \
  max_ttl=720h

# 인증서 발급
vault write pki_int/issue/service-cert \
  common_name="order-service.production.svc.cluster.local" \
  ttl=720h
```

Vault Agent를 서비스와 함께 실행하면 인증서 만료 전 자동 갱신이 가능하다. Agent가 Vault에서 새 인증서를 받아오고, 파일을 교체한 뒤 서비스에 reload 시그널을 보낸다.

### 만료 모니터링

자동화를 했어도 모니터링은 반드시 해야 한다. 자동화가 실패할 수 있기 때문이다.

```bash
# 인증서 만료일 확인
openssl x509 -in service.crt -enddate -noout

# 만료까지 남은 일수 계산
expiry=$(openssl x509 -in service.crt -enddate -noout | cut -d= -f2)
expiry_epoch=$(date -d "$expiry" +%s)
now_epoch=$(date +%s)
days_left=$(( (expiry_epoch - now_epoch) / 86400 ))
echo "Days until expiry: $days_left"
```

Prometheus를 쓴다면 `x509_cert_not_after` 메트릭으로 인증서 만료를 추적하고, 7일 이내면 알림을 보내는 규칙을 설정한다.

## Spring Boot mTLS 설정

### 서버 측 설정

```yaml
# application.yml
server:
  port: 8443
  ssl:
    enabled: true
    key-store: classpath:keystore.p12
    key-store-password: ${KEYSTORE_PASSWORD}
    key-store-type: PKCS12
    key-alias: order-service
    # mTLS 핵심 설정
    client-auth: need        # 클라이언트 인증서 필수 (want: 선택, need: 필수)
    trust-store: classpath:truststore.p12
    trust-store-password: ${TRUSTSTORE_PASSWORD}
    trust-store-type: PKCS12
    protocol: TLS
    enabled-protocols: TLSv1.3
```

`client-auth: need`가 mTLS를 활성화하는 설정이다. `want`로 설정하면 인증서가 있으면 검증하고, 없어도 연결을 허용한다. 운영 환경에서는 `need`를 써야 한다.

keystore와 truststore의 차이:
- **keystore**: 자기 자신의 인증서와 개인키를 저장
- **truststore**: 신뢰할 CA 인증서를 저장. 상대방 인증서를 검증할 때 사용

```bash
# keystore 생성 (서비스 인증서 + 개인키)
openssl pkcs12 -export \
  -in service.crt \
  -inkey service.key \
  -certfile ca-chain.crt \
  -out keystore.p12 \
  -name order-service \
  -password pass:${KEYSTORE_PASSWORD}

# truststore 생성 (CA 인증서)
keytool -importcert \
  -file ca.crt \
  -alias internal-ca \
  -keystore truststore.p12 \
  -storetype PKCS12 \
  -storepass ${TRUSTSTORE_PASSWORD} \
  -noprompt
```

### 클라이언트 측 설정 (RestTemplate)

다른 서비스를 호출할 때도 클라이언트 인증서를 제시해야 한다.

```java
@Configuration
public class MtlsRestTemplateConfig {

    @Value("${client.ssl.key-store}")
    private Resource keyStore;

    @Value("${client.ssl.key-store-password}")
    private String keyStorePassword;

    @Value("${client.ssl.trust-store}")
    private Resource trustStore;

    @Value("${client.ssl.trust-store-password}")
    private String trustStorePassword;

    @Bean
    public RestTemplate mtlsRestTemplate() throws Exception {
        SSLContext sslContext = SSLContextBuilder.create()
            .loadKeyMaterial(
                keyStore.getURL(),
                keyStorePassword.toCharArray(),
                keyStorePassword.toCharArray()
            )
            .loadTrustMaterial(
                trustStore.getURL(),
                trustStorePassword.toCharArray()
            )
            .build();

        HttpClient httpClient = HttpClients.custom()
            .setSSLContext(sslContext)
            .build();

        HttpComponentsClientHttpRequestFactory factory =
            new HttpComponentsClientHttpRequestFactory(httpClient);

        return new RestTemplate(factory);
    }
}
```

Spring Boot 3.1부터는 `spring.ssl.bundle`로 SSL 설정을 묶어서 관리할 수 있다:

```yaml
spring:
  ssl:
    bundle:
      jks:
        mtls-bundle:
          key:
            alias: order-service
          keystore:
            location: classpath:keystore.p12
            password: ${KEYSTORE_PASSWORD}
            type: PKCS12
          truststore:
            location: classpath:truststore.p12
            password: ${TRUSTSTORE_PASSWORD}
            type: PKCS12
```

## Nginx mTLS 설정

Nginx를 리버스 프록시로 쓰는 경우, Nginx에서 mTLS를 처리하고 백엔드에는 평문으로 전달하는 구조가 일반적이다.

```nginx
server {
    listen 443 ssl;
    server_name api.internal.example.com;

    # 서버 인증서
    ssl_certificate     /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;

    # mTLS 설정
    ssl_client_certificate /etc/nginx/ssl/ca.crt;    # 클라이언트 인증서를 검증할 CA
    ssl_verify_client on;                             # 클라이언트 인증서 검증 활성화
    ssl_verify_depth 2;                               # 인증서 체인 검증 깊이

    # TLS 프로토콜/암호화 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;

    # 클라이언트 인증서 정보를 백엔드에 전달
    location / {
        proxy_pass http://backend:8080;
        proxy_set_header X-SSL-Client-DN $ssl_client_s_dn;
        proxy_set_header X-SSL-Client-Verify $ssl_client_verify;
        proxy_set_header X-SSL-Client-Serial $ssl_client_serial;
    }
}
```

주의할 점:

- `ssl_verify_depth`는 인증서 체인의 깊이다. Root CA → Intermediate CA → Leaf Certificate 구조면 2로 설정한다.
- `ssl_client_certificate`에는 클라이언트 인증서를 발급한 CA의 인증서를 넣는다. 클라이언트 인증서 자체가 아니다. 여러 CA를 신뢰해야 하면 인증서를 하나의 파일에 이어 붙인다.
- `$ssl_client_s_dn`으로 클라이언트의 DN(Distinguished Name)을 백엔드에 전달한다. 백엔드에서 이 값으로 서비스를 식별할 수 있다.

### CRL/OCSP 설정

인증서가 유출되면 폐기(revoke)해야 한다. Nginx에서 CRL(Certificate Revocation List)을 설정하는 방법:

```nginx
# CRL 파일 지정
ssl_crl /etc/nginx/ssl/crl.pem;
```

CRL 파일은 주기적으로 업데이트해야 한다. 파일이 오래되면 새로 폐기된 인증서를 차단하지 못한다. cron으로 CA에서 최신 CRL을 가져오는 스크립트를 돌리는 방식이 일반적이다.

## 운영에서 겪는 문제들

### 인증서 만료 사고

가장 흔한 사고다. 인증서가 만료되면 서비스 간 통신이 전부 끊어진다. 새벽에 만료되면 아침에 출근했을 때 장애 상태인 걸 발견하게 된다.

대응:
- 인증서 유효 기간을 짧게 설정하고 자동 갱신을 붙인다. 유효 기간이 짧으면 갱신 주기가 빨라지고, 자동화가 정상 동작하는지 빠르게 확인된다.
- 만료 7일 전, 3일 전, 1일 전에 알림을 보낸다.

### 인증서 체인 불일치

서버 인증서는 있는데 중간 CA 인증서를 빠뜨리는 경우가 있다. 서버 쪽에서 테스트하면 잘 되는데(로컬에 CA 인증서가 설치되어 있으니까), 다른 서비스에서 연결하면 `unable to verify the first certificate` 에러가 난다.

```bash
# 인증서 체인이 올바른지 확인
openssl s_client -connect service:443 -showcerts
```

출력에서 인증서 체인이 Root CA까지 이어지는지 확인한다. 중간에 빠진 인증서가 있으면 서버 인증서 파일에 중간 CA 인증서를 추가해야 한다.

### 시간 동기화 문제

인증서 검증에는 시간이 중요하다. 서버 시간이 틀어져 있으면 유효한 인증서도 만료되었다고 판단하거나, 아직 유효하지 않다고 판단할 수 있다. NTP 동기화가 되어 있는지 확인해야 한다.

### 키 알고리즘 선택

RSA 2048은 아직 안전하지만, 새로 구축한다면 ECDSA P-256을 쓰는 게 낫다. 키 크기가 작아서 핸드셰이크가 빠르고, 같은 보안 수준에서 성능이 좋다.

```bash
# ECDSA 키 생성
openssl ecparam -name prime256v1 -genkey -noout -out service.key

# CSR 생성
openssl req -new -key service.key -out service.csr \
  -subj "/CN=order-service.production.svc.cluster.local"

# 인증서 발급 (CA의 키로 서명)
openssl x509 -req -in service.csr \
  -CA intermediate-ca.crt -CAkey intermediate-ca.key \
  -CAcreateserial \
  -out service.crt \
  -days 30 \
  -sha256 \
  -extfile <(printf "subjectAltName=DNS:order-service.production.svc.cluster.local")
```

### mTLS 디버깅

mTLS 관련 문제가 생기면 OpenSSL로 직접 연결해보는 게 가장 빠르다.

```bash
# 상세 핸드셰이크 로그 확인
openssl s_client -connect service:443 \
  -cert client.crt \
  -key client.key \
  -CAfile ca.crt \
  -state -debug

# 서버가 요구하는 CA 목록 확인
openssl s_client -connect service:443 2>&1 | grep -A5 "Acceptable client certificate CA names"
```

서버가 요구하는 CA 목록에 클라이언트 인증서를 발급한 CA가 포함되어 있는지 확인한다. 여기에 없으면 클라이언트가 아무리 인증서를 보내도 거부된다.
