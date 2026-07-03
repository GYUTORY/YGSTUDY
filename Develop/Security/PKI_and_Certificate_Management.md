---
title: PKI와 인증서 수명주기 관리
tags:
  - Security
  - PKI
  - TLS
  - Certificate
  - mTLS
  - HSM
updated: 2026-06-04
---

# PKI와 인증서 수명주기 관리

운영하다 보면 인증서는 두 가지 순간에만 떠올리게 된다. 처음 발급할 때, 그리고 만료돼서 서비스가 죽었을 때. 사이의 시간은 평화롭지만, 그 평화는 누군가가 자동화를 잘 만들어 뒀거나, 혹은 운이 좋았던 결과다. PKI(Public Key Infrastructure)는 그 평화를 시스템으로 만드는 일이다.

이 문서는 PKI를 처음부터 설명하지 않는다. RSA, AES, HTTPS는 다른 문서에 있다. 여기서는 운영 관점에서 인증서가 어떻게 만들어지고, 어떻게 갱신되고, 어떻게 폐기되는지를 정리한다.

## PKI가 푸는 문제

암호학적으로 공개키 암호는 멋지지만, 실제로는 한 가지 큰 구멍이 있다. "이 공개키가 정말 example.com의 것인가?"를 어떻게 증명하느냐는 문제다.

PKI는 이 문제를 신뢰 사슬(chain of trust)로 푼다. 누군가 신뢰할 수 있는 제3자(CA, Certificate Authority)가 "이 공개키는 example.com의 것이 맞다"는 도장을 찍어 준다. 그 도장이 인증서(certificate)다.

문제는 그 CA를 어떻게 신뢰하느냐다. 운영체제와 브라우저에는 수백 개의 Root CA 공개키가 내장돼 있다. 우리는 이 Root를 무조건 신뢰하고, Root가 신뢰한 것을 신뢰하고, 그 신뢰가 신뢰한 것을 신뢰한다. 이게 사슬이다.

## Root CA와 Intermediate CA

실제 운영에서 Root CA는 거의 쓰이지 않는다. Root는 오프라인 금고에 보관하고, 인증서를 직접 발급하지 않는다. Root가 직접 서비스 인증서를 찍으면 Root 키가 유출됐을 때 모든 신뢰가 무너지기 때문이다.

대신 Root는 Intermediate CA의 인증서만 서명한다. Intermediate CA가 실제 발급 업무를 한다. Intermediate 키가 유출되면 해당 Intermediate만 폐기하면 되고, Root는 살아남는다.

```
Root CA (오프라인, 10~20년 유효)
   └─ Intermediate CA (온라인, 5~10년 유효)
        └─ End Entity Certificate (서비스, 90일~1년 유효)
```

브라우저가 TLS 핸드셰이크에서 인증서를 검증할 때, 서버는 End Entity 인증서와 Intermediate 인증서를 함께 보낸다. 브라우저는 Intermediate를 받아 Root까지 사슬을 만들어 본다. Root는 이미 브라우저에 내장돼 있으므로 추가로 보낼 필요가 없다.

여기서 자주 하는 실수가 Intermediate를 빼먹는 것이다. 서버 인증서만 보내면 Chrome은 어떻게든 캐시에서 Intermediate를 찾아 동작하기도 하지만, 모바일 앱이나 일부 라이브러리는 그대로 실패한다. 같은 도메인이 PC에서는 되는데 앱에서는 안 된다면 십중팔구 Intermediate 누락이다.

`openssl s_client`로 확인할 수 있다.

```bash
openssl s_client -connect example.com:443 -showcerts < /dev/null
```

`Certificate chain` 섹션에 서버 인증서와 Intermediate가 둘 다 보여야 한다. `Verify return code: 0 (ok)`가 나와야 정상이다.

## CSR과 발급 과정

인증서를 받으려면 CSR(Certificate Signing Request)을 만들어 CA에 보낸다. CSR에는 공개키와 신원 정보(Common Name, SAN 등)가 들어가고, 그 전체를 자기 개인키로 서명한다. CA는 서명을 검증해서 "이 공개키의 소유자가 정말 이 요청을 만들었구나"를 확인한다.

```bash
# 1. 개인키 생성 (RSA 2048 또는 ECDSA P-256)
openssl genrsa -out service.key 2048

# 2. CSR 생성
openssl req -new -key service.key -out service.csr \
  -subj "/C=KR/O=YourCompany/CN=api.example.com" \
  -addext "subjectAltName=DNS:api.example.com,DNS:www.api.example.com"

# 3. CSR 내용 확인
openssl req -in service.csr -text -noout
```

여기서 가장 자주 틀리는 게 SAN(Subject Alternative Name)이다. 요즘 브라우저는 CN을 거의 보지 않고 SAN만 본다. SAN에 도메인이 없으면 인증서가 유효해도 "NET::ERR_CERT_COMMON_NAME_INVALID"가 뜬다.

여러 도메인을 한 인증서로 묶을 때도 모두 SAN에 넣는다. 예전 OpenSSL은 `-addext` 옵션이 없어서 별도 설정 파일을 만들어야 했다.

```ini
# csr.cnf
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = KR
O = YourCompany
CN = api.example.com

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = api.example.com
DNS.2 = www.api.example.com
DNS.3 = admin.example.com
```

```bash
openssl req -new -key service.key -out service.csr -config csr.cnf
```

CA는 이 CSR을 받아 신원을 확인한 뒤 자기 개인키로 서명해서 인증서를 만들어 돌려준다. 공개 CA는 도메인 소유 검증(DV)을 자동으로 한다. Let's Encrypt가 대표적이다.

## Let's Encrypt와 ACME

Let's Encrypt는 ACME(Automatic Certificate Management Environment) 프로토콜로 인증서를 자동 발급한다. 무료, 90일 유효, 자동 갱신이 표준이다.

도메인 소유 검증은 두 가지가 흔하다.

- **HTTP-01**: `http://example.com/.well-known/acme-challenge/<token>` 경로에 특정 문자열을 두면 검증 통과
- **DNS-01**: `_acme-challenge.example.com` TXT 레코드에 특정 값을 두면 검증 통과

와일드카드(`*.example.com`)는 DNS-01만 가능하다. HTTP-01은 단일 도메인용이다.

certbot이 가장 흔하지만, 운영 환경에서는 acme.sh를 더 많이 쓴다. 의존성이 없고 셸 스크립트라 어디서든 돈다.

```bash
# DNS-01 발급 (Cloudflare API 사용 예)
acme.sh --issue --dns dns_cf \
  -d example.com -d '*.example.com' \
  --keylength ec-256

# nginx 설정 경로로 배포
acme.sh --install-cert -d example.com \
  --key-file       /etc/nginx/certs/example.com.key \
  --fullchain-file /etc/nginx/certs/example.com.crt \
  --reloadcmd      "systemctl reload nginx"
```

`--install-cert`로 등록해 두면 acme.sh가 cron에 들어가 자동 갱신한다. 60일째에 갱신을 시도하고, 30일치 여유를 둔다. 갱신 후 `reloadcmd`로 웹서버를 reload한다.

운영 팁 하나. `reloadcmd`가 실패해도 acme.sh는 성공으로 처리한다. 갱신은 됐는데 nginx가 리로드 안 돼서 만료 사고가 나는 경우가 있다. reloadcmd 마지막에 `&& nginx -t`나 헬스체크를 붙여서 실패 시 알람이 오게 해야 한다.

## cert-manager — 쿠버네티스에서

쿠버네티스에서는 cert-manager가 사실상 표준이다. Issuer/ClusterIssuer 리소스로 CA를 정의하고, Certificate 리소스를 만들면 알아서 발급·갱신·Secret 저장까지 해 준다.

```yaml
# Let's Encrypt Production Issuer
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-account
    solvers:
      - dns01:
          cloudflare:
            apiTokenSecretRef:
              name: cloudflare-api-token
              key: api-token
```

```yaml
# 인증서 요청
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: api-example-com
  namespace: prod
spec:
  secretName: api-example-com-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - api.example.com
    - admin.example.com
  duration: 2160h   # 90일
  renewBefore: 720h # 30일 전 갱신
```

이 Certificate를 만들면 cert-manager가 ACME 발급을 진행하고, 결과를 `api-example-com-tls`라는 Secret에 `tls.crt`, `tls.key`로 저장한다. Ingress가 이 Secret을 참조하면 끝이다.

운영하면서 가장 자주 만나는 cert-manager 사고는 발급 한도(rate limit) 초과다. Let's Encrypt는 같은 도메인에 주당 50회 발급 한도가 있다. 잘못된 설정으로 CertificateRequest가 무한 재시도되면 한 시간 만에 한도를 다 써 버린다. 그러면 일주일간 새 인증서를 못 받는다.

이런 사고를 막으려면 처음에는 반드시 staging 환경(`https://acme-staging-v02.api.letsencrypt.org/directory`)으로 테스트해야 한다. 스테이징은 한도가 훨씬 넉넉하고, 발급된 인증서는 브라우저가 신뢰하지 않을 뿐 형식은 동일하다.

## CRL과 OCSP — 인증서 폐기

발급된 인증서를 만료 전에 무효화해야 할 때가 있다. 개인키가 유출됐다거나, 직원이 퇴사했다거나. 이때 쓰는 게 인증서 폐기 메커니즘이다.

**CRL(Certificate Revocation List)**은 폐기된 인증서 시리얼 번호 목록을 CA가 정기 발행하는 방식이다. 클라이언트는 이 목록을 다운로드해서 검증한다. 문제는 목록이 점점 커진다는 것. 큰 CA의 CRL은 수 메가가 넘는다. 모바일에서 매번 다운로드하기 어렵다.

**OCSP(Online Certificate Status Protocol)**는 개별 인증서 하나의 상태만 묻는 방식이다. CA가 운영하는 OCSP responder에 시리얼 번호로 질의하면 "good", "revoked", "unknown" 중 하나를 돌려준다. 작고 빠르지만, 매 TLS 연결마다 외부 OCSP 서버에 묻는 건 부담이다. 그리고 OCSP 서버가 죽으면 인증서 검증이 늦어진다.

**OCSP Stapling**은 그 부담을 서버가 대신 진다. 웹서버가 주기적으로 OCSP responder에 묻고, 그 응답을 캐시해서 TLS 핸드셰이크에 끼워(staple) 보낸다. 클라이언트는 외부에 묻지 않고도 폐기 상태를 안다.

nginx 설정 예다.

```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/nginx/certs/chain.pem;
resolver 1.1.1.1 8.8.8.8 valid=300s;
resolver_timeout 5s;
```

`resolver` 지시어가 빠지면 nginx가 OCSP responder의 도메인을 못 풀어서 stapling이 동작하지 않는다. 로그에 조용히 실패가 찍힌다. 시작 후 `openssl s_client -connect host:443 -status`로 OCSP Response가 붙는지 확인해야 한다.

현실적으로 폐기 메커니즘은 완벽하지 않다. Chrome은 일반 CRL/OCSP를 거의 보지 않고, 자체적으로 CRLSet이라는 축약 목록만 본다. 짧은 유효기간(Let's Encrypt 90일)이 사실상 가장 현실적인 폐기 전략이 된 이유다. 키가 유출되면 새 키로 재발급하고 90일만 버티면 자연 만료된다.

## 사설 CA 운영

내부 서비스나 mTLS용으로 사설 CA를 굴리는 경우가 많다. 공개 CA로 사설 도메인(`*.internal`)에 인증서를 받을 수 없고, 받을 필요도 없다. 사설 CA의 Root만 클라이언트에 신뢰 추가해 두면 된다.

가장 단순한 사설 CA는 OpenSSL로 만들 수 있다.

```bash
# Root CA 개인키와 인증서
openssl genrsa -aes256 -out rootCA.key 4096
openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 3650 \
  -out rootCA.crt -subj "/C=KR/O=YourCompany/CN=YourCompany Root CA"

# Intermediate CA
openssl genrsa -out intermediate.key 4096
openssl req -new -key intermediate.key -out intermediate.csr \
  -subj "/C=KR/O=YourCompany/CN=YourCompany Intermediate CA"
openssl x509 -req -in intermediate.csr \
  -CA rootCA.crt -CAkey rootCA.key -CAcreateserial \
  -out intermediate.crt -days 1825 -sha256 \
  -extfile <(printf "basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign")
```

이렇게 만든 Root와 Intermediate로 서비스 인증서를 찍을 수 있다. 하지만 손으로 굴리는 사설 CA는 6개월만 지나도 누가 무엇을 발급했는지 추적이 안 된다. 폐기 기능도 없다. 운영 규모가 커지면 전용 도구를 써야 한다.

대표적인 게 HashiCorp Vault의 PKI Secret Engine과 step-ca다. Vault PKI는 짧은 수명(예: 24시간)의 인증서를 API로 즉시 발급한다. 폐기 대신 자연 만료에 의존한다. 마이크로서비스 mTLS에 잘 맞는다.

```bash
# Vault PKI 마운트와 Root 생성
vault secrets enable -path=pki_root pki
vault secrets tune -max-lease-ttl=87600h pki_root
vault write -field=certificate pki_root/root/generate/internal \
  common_name="YourCompany Root CA" ttl=87600h > root.crt

# Intermediate를 별도 마운트로
vault secrets enable -path=pki_int pki
vault write -format=json pki_int/intermediate/generate/internal \
  common_name="YourCompany Intermediate CA" \
  | jq -r '.data.csr' > int.csr

vault write -format=json pki_root/root/sign-intermediate \
  csr=@int.csr format=pem_bundle ttl="43800h" \
  | jq -r '.data.certificate' > int.crt

vault write pki_int/intermediate/set-signed certificate=@int.crt

# 발급 role 정의
vault write pki_int/roles/api-server \
  allowed_domains=internal.example.com \
  allow_subdomains=true \
  max_ttl=24h

# 실제 발급
vault write pki_int/issue/api-server \
  common_name=svc1.internal.example.com ttl=24h
```

24시간 인증서를 매일 갱신하면 폐기 메커니즘 자체가 필요 없어진다. 키가 유출돼도 하루면 끝난다. 대신 클라이언트가 이 갱신을 잘 따라가야 한다.

## mTLS용 클라이언트 인증서

서버 인증서는 "이 서버가 진짜 example.com이다"를 증명한다. mTLS는 클라이언트도 인증서를 보내서 "이 클라이언트가 진짜 service-A다"를 증명한다. 자세한 내용은 [Mutual_TLS.md](Mutual_TLS.md) 문서에 있고, 여기서는 인증서 관리 관점만 다룬다.

mTLS에서 클라이언트 인증서는 보통 사설 CA로 발급한다. 공개 CA는 클라이언트 인증서를 거의 발급하지 않는다.

```bash
# 클라이언트용 CSR
openssl req -new -key client.key -out client.csr \
  -subj "/C=KR/O=YourCompany/OU=Services/CN=service-a"

# 사설 CA로 서명, Extended Key Usage에 clientAuth를 명시
openssl x509 -req -in client.csr \
  -CA intermediate.crt -CAkey intermediate.key -CAcreateserial \
  -out client.crt -days 365 -sha256 \
  -extfile <(printf "extendedKeyUsage=clientAuth")
```

`extendedKeyUsage=clientAuth`가 핵심이다. 이게 없으면 nginx 같은 서버가 클라이언트 인증서로 인정하지 않는다.

서비스 식별은 CN이나 SAN에 넣는다. nginx에서는 `$ssl_client_s_dn` 변수로 받을 수 있다.

```nginx
location /api {
    proxy_set_header X-Client-DN $ssl_client_s_dn;
    proxy_pass http://upstream;
}
```

업스트림 애플리케이션은 `X-Client-DN` 헤더의 CN을 보고 서비스를 식별한다. 단, 이 헤더는 mTLS 통과 후에만 신뢰할 수 있다. mTLS 없는 경로로 같은 헤더가 들어오면 위조다. 외부에서 오는 동일 헤더는 nginx에서 무조건 덮어써야 한다.

mTLS 클라이언트 인증서는 갱신이 까다롭다. 서버 인증서는 nginx reload면 끝이지만, 클라이언트 인증서는 수십, 수백 개의 워크로드에 분산돼 있다. 짧은 수명을 쓰고 자동 갱신을 만들어 두는 게 답이다. SPIFFE/SPIRE 같은 워크로드 ID 시스템이 이걸 자동화한다.

## HSM 연동

HSM(Hardware Security Module)은 개인키를 하드웨어 안에서만 다루는 장비다. 키가 절대로 메모리나 디스크에 평문으로 나오지 않는다. 서명 작업은 HSM 내부에서 일어나고, 외부로는 결과만 나온다.

PKI에서 HSM이 가장 흔히 쓰이는 곳은 Root CA와 Intermediate CA의 개인키 보호다. Root 키 유출은 회복 불가능한 사고다. HSM에 보관하면 키 자체를 훔칠 수 없다.

PKCS#11이 표준 인터페이스다. OpenSSL의 `pkcs11` engine으로 HSM 키를 쓸 수 있다.

```bash
# HSM에 저장된 키로 인증서 서명 (libsofthsm2 예)
openssl req -engine pkcs11 -keyform engine \
  -new -key "pkcs11:object=root-ca-key;type=private;pin-value=1234" \
  -x509 -days 3650 -out rootCA.crt \
  -subj "/CN=Root CA"
```

운영 환경에서는 AWS CloudHSM, Azure Dedicated HSM, Google Cloud HSM 같은 매니지드 서비스를 많이 쓴다. 물리 HSM(Thales, Utimaco 등)은 비싸고 관리 부담이 크다.

규모가 작거나 시작 단계라면 HSM 대신 AWS KMS나 Vault의 Transit Engine으로도 비슷한 효과를 낸다. 키가 격리된 환경에 있고, 평문 키를 직접 다루지 않는다는 원칙만 지키면 된다.

다만 PKI Root에 KMS를 쓸 때 주의할 점이 있다. KMS 키 정책을 잘못 설정하면 IAM 관리자가 그 키로 임의의 인증서를 서명할 수 있다. CA 서명용 KMS 키는 별도 정책으로 격리하고, 사용 로그를 CloudTrail에 남기고, 감사해야 한다.

## 인증서 만료 사고 트러블슈팅

운영하다 보면 만료 사고는 반드시 한 번은 만난다. 패턴이 몇 가지 있다.

**증상 1: 갑자기 모든 요청이 실패한다**

가장 흔한 시나리오다. 어제까지 잘 되던 서비스가 자정 넘어 죽는다. `openssl s_client -connect host:443`로 확인하면 `notAfter` 날짜가 어제다.

```bash
# 인증서 만료일 빠르게 확인
echo | openssl s_client -connect api.example.com:443 2>/dev/null \
  | openssl x509 -noout -dates
```

응급 처치는 새 인증서 발급이다. Let's Encrypt면 ACME 발급, 사설 CA면 수동 서명. 발급 후 웹서버 reload.

근본 원인은 거의 자동화 실패다. 자동 갱신은 도는데 reload가 빠졌거나, cron이 죽었거나, 권한이 바뀌었거나. 사고 후에는 자동 갱신 자체를 모니터링해야 한다.

**증상 2: 일부 클라이언트만 실패한다**

PC 브라우저에서는 되는데 iOS 앱이나 옛 Android에서만 실패한다면 Intermediate 누락이 1순위 의심이다. 또는 신뢰 스토어가 오래된 단말에서 새 Root를 모르는 경우다.

Let's Encrypt가 2021년 9월에 IdenTrust 교차 서명에서 자체 Root(ISRG Root X1)로 전환할 때 옛 Android에서 대량 실패가 났다. 비슷한 이슈는 앞으로도 반복된다. 사용자 단말의 OS 버전 분포를 알고, 신뢰 사슬을 미리 검증하는 게 답이다.

`ssllabs.com/ssltest`를 돌리면 다양한 클라이언트의 신뢰 사슬을 한 번에 본다. 운영 도메인은 분기마다 한 번씩 돌려 봐도 된다.

**증상 3: Intermediate가 만료됐다**

End Entity 인증서는 멀쩡한데 Intermediate가 만료되면 전체 사슬이 깨진다. CA 측에서 Intermediate를 갱신하면 우리는 새 Intermediate가 포함된 fullchain을 다시 받아서 배포해야 한다.

acme.sh나 cert-manager는 이걸 자동으로 처리하지만, 옛날에 발급받은 인증서를 그대로 쓰는 경우 잡지 못한다. 인증서 갱신 주기를 정해 둬야 하는 이유다.

**증상 4: 클럭이 안 맞는다**

서버 시간이 미래나 과거로 크게 어긋나면 멀쩡한 인증서도 만료 또는 미래 인증서로 판정된다. 컨테이너 호스트가 NTP 동기화 안 된 상태에서 부팅된 경우 자주 본다. `date` 명령으로 먼저 확인한다.

## 모니터링과 알람

인증서 사고를 막는 유일한 방법은 만료 전에 사람이 안다는 것이다. 자동 갱신을 믿더라도 모니터링은 별도로 둔다.

가장 단순한 건 외부에서 만료일을 긁어 알람을 보내는 방식이다.

```bash
#!/bin/bash
# cert-check.sh
DOMAIN=$1
THRESHOLD_DAYS=14

EXPIRY=$(echo | openssl s_client -connect "$DOMAIN":443 -servername "$DOMAIN" 2>/dev/null \
  | openssl x509 -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

if [ $DAYS_LEFT -lt $THRESHOLD_DAYS ]; then
  echo "ALERT: $DOMAIN expires in $DAYS_LEFT days"
  exit 1
fi
```

Prometheus blackbox_exporter의 `probe_ssl_earliest_cert_expiry` 메트릭이 표준이다.

```yaml
# alert rule
- alert: CertExpiringSoon
  expr: probe_ssl_earliest_cert_expiry - time() < 86400 * 14
  for: 1h
  annotations:
    summary: "{{ $labels.instance }} 인증서 14일 이내 만료"
```

내부 사설 CA로 발급한 인증서까지 포함하려면 도메인 목록을 별도로 관리해야 한다. mTLS 워크로드 인증서는 보통 짧은 수명이라 만료 알람을 거는 대신 갱신 성공률 메트릭을 본다.

## 실무 정리

PKI 운영의 핵심은 인증서 만료라는 시한폭탄을 폭발 전에 처리하는 자동화다. 자동화의 핵심은 발급, 배포, 검증이 한 사이클로 묶여 있어야 한다는 것이다. 발급은 됐는데 배포가 안 됐거나, 배포는 됐는데 검증이 빠지면 결국 사고로 이어진다.

규모가 작을 때는 Let's Encrypt + acme.sh + cron이면 충분하다. 쿠버네티스로 가면 cert-manager가 사실상 표준이다. 내부 mTLS가 본격적으로 들어오면 Vault PKI나 SPIFFE/SPIRE를 검토할 시점이다. Root CA 보호가 중요한 단계가 되면 HSM이나 KMS로 격리한다.

각 단계의 전환은 사고가 한 번 나야 결정되는 경우가 많다. 그 사고를 피하려면 인증서 인벤토리를 평소에 유지하는 게 가장 좋다. 어떤 도메인이 언제 만료되는지, 누가 발급했는지, 어디에 배포돼 있는지. 이 표가 있는 조직은 사고를 거의 만나지 않는다.

관련 문서로 [HTTPS_and_TLS.md](HTTPS_and_TLS.md)에 TLS 핸드셰이크 동작이, [Mutual_TLS.md](Mutual_TLS.md)에 mTLS 구성 상세가 있다. 키 보관과 관련해서는 [Secrets_Management.md](Secrets_Management.md)도 함께 보면 좋다.
