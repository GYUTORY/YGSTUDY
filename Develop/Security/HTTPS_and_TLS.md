---
title: HTTPS & TLS
tags: [security, https, tls, ssl, certificate, encryption, handshake, openssl, pem, pkcs12, mtls]
updated: 2026-03-26
---

# HTTPS & TLS

## 개요

**HTTPS**(HTTP over TLS)는 HTTP 통신을 **TLS(Transport Layer Security)** 프로토콜로 암호화한 것이다. 데이터 도청, 변조, 위장을 방지한다. 현대 웹에서 HTTPS는 선택이 아닌 필수다.

### HTTP vs HTTPS

```
HTTP:
  Client ──── "password=1234" ────▶ Server
              (평문, 도청 가능)

HTTPS:
  Client ──── "x7Fk9#@!mZ..." ────▶ Server
              (암호화, 도청 불가)
```

| 항목 | HTTP | HTTPS |
|------|------|-------|
| **포트** | 80 | 443 |
| **암호화** | 없음 | TLS 암호화 |
| **인증** | 없음 | 인증서로 서버 신원 확인 |
| **무결성** | 없음 | 변조 감지 |
| **SEO** | 불이익 | 검색 순위 가산점 |
| **브라우저** | "주의 요함" 경고 | 자물쇠 아이콘 |

### TLS가 제공하는 3가지 보안

| 보안 | 설명 | 위협 방지 |
|------|------|----------|
| **기밀성** | 데이터를 암호화하여 제3자가 읽을 수 없음 | 도청 (Eavesdropping) |
| **무결성** | 데이터가 전송 중 변조되지 않았음을 보장 | 변조 (Tampering) |
| **인증** | 서버가 진짜임을 인증서로 증명 | 위장 (Impersonation) |

## 핵심

### 1. TLS 핸드셰이크

클라이언트와 서버가 암호화 통신을 시작하기 전 **키를 교환하는 과정**이다.

#### TLS 1.3 핸드셰이크 (현재 표준)

```
Client                                          Server
  │                                                │
  │──── ClientHello ──────────────────────────────▶│
  │     (지원 암호 스위트, 키 공유)                    │
  │                                                │
  │◀──── ServerHello + 인증서 + Finished ───────────│
  │     (선택된 암호 스위트, 서버 키, 인증서)           │
  │                                                │
  │──── Finished ─────────────────────────────────▶│
  │                                                │
  │◀═══════════ 암호화된 통신 시작 ═══════════════▶│
```

**TLS 1.3은 1-RTT** (왕복 1회)로 완료. TLS 1.2는 2-RTT 필요.

#### 단계별 설명

| 단계 | 동작 | 목적 |
|------|------|------|
| **ClientHello** | 클라이언트가 지원하는 암호 스위트/키 공유 전송 | 협상 시작 |
| **ServerHello** | 서버가 암호 스위트 선택, 인증서 전송 | 서버 인증 |
| **인증서 검증** | 클라이언트가 CA 체인으로 인증서 검증 | 신뢰 확인 |
| **키 교환** | ECDHE로 공유 비밀 생성 | 대칭키 생성 |
| **Finished** | 양쪽 핸드셰이크 검증 | 무결성 확인 |

### 2. 인증서 (Certificate)

#### 인증서 체인

```
Root CA (최상위 인증기관)
  │  ← 브라우저/OS에 미리 저장됨 (신뢰 앵커)
  ▼
Intermediate CA (중간 인증기관)
  │  ← Root CA가 서명
  ▼
서버 인증서 (End-Entity)
  │  ← Intermediate CA가 서명
  ▼
example.com  ← 이 서버가 진짜 example.com임을 증명
```

| 인증서 유형 | 검증 수준 | 비용 | 용도 |
|-----------|----------|------|------|
| **DV (Domain Validated)** | 도메인 소유 확인 | 무료~저가 | 일반 웹사이트 |
| **OV (Organization Validated)** | 조직 실체 확인 | 중간 | 기업 웹사이트 |
| **EV (Extended Validation)** | 엄격한 신원 확인 | 고가 | 금융, 전자상거래 |

실무에서는 Let's Encrypt(무료 DV)가 대부분의 상황에서 충분하다.

#### Let's Encrypt로 인증서 발급

```bash
# Certbot 설치 (Ubuntu)
sudo apt install certbot python3-certbot-nginx

# 인증서 발급 (Nginx 자동 설정)
sudo certbot --nginx -d example.com -d www.example.com

# 자동 갱신 확인 (90일마다)
sudo certbot renew --dry-run

# 크론탭 자동 갱신
echo "0 0 1 * * certbot renew --quiet" | sudo tee -a /etc/crontab
```

### 3. 키 파일 포맷

HTTPS를 적용하다 보면 `.pem`, `.der`, `.p12`, `.jks` 같은 파일을 자주 만나게 된다. 각 포맷이 뭔지 모르면 인증서 설정에서 삽질하는 시간이 길어진다.

#### PEM (Privacy Enhanced Mail)

가장 흔한 포맷이다. Base64로 인코딩되어 있고 텍스트 에디터로 열 수 있다.

```
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAJC1HiIAZAiUMA0Gcn...
-----END CERTIFICATE-----
```

- 확장자: `.pem`, `.crt`, `.cer`, `.key`
- Nginx, Apache, Let's Encrypt가 기본으로 사용하는 포맷
- 하나의 파일에 인증서, 개인키, 중간 인증서를 모두 넣을 수 있다 (순서대로 이어 붙이면 됨)

#### DER (Distinguished Encoding Rules)

바이너리 포맷이다. 텍스트 에디터로 열면 깨진다.

- 확장자: `.der`, `.cer`
- Java 기본 포맷. Windows에서 `.cer` 파일을 더블클릭하면 DER로 인식하는 경우가 있다
- PEM에서 Base64 인코딩과 헤더/푸터를 제거한 것이 DER이다

#### PKCS#12 (PFX)

개인키 + 인증서 + 중간 인증서를 **하나의 파일**로 묶는 포맷이다. 비밀번호로 보호된다.

- 확장자: `.p12`, `.pfx`
- Spring Boot, Tomcat에서 기본으로 사용
- Windows IIS에서도 `.pfx`로 인증서를 가져온다

#### JKS (Java KeyStore)

Java 전용 키 저장소 포맷이다.

- 확장자: `.jks`
- `keytool` 명령으로 관리
- Java 9부터 기본 keystore 타입이 PKCS12로 바뀌었다. 신규 프로젝트에서는 `.p12`를 쓰는 게 낫다
- 기존 레거시 프로젝트에서 `.jks`를 쓰고 있다면 그대로 유지해도 된다

#### 포맷 비교

| 포맷 | 인코딩 | 개인키 포함 | 비밀번호 보호 | 주 사용처 |
|------|--------|-----------|-------------|----------|
| **PEM** | Base64 (텍스트) | 별도 파일 | 선택 | Nginx, Apache, Linux |
| **DER** | 바이너리 | 별도 파일 | 없음 | Java, Windows |
| **PKCS#12** | 바이너리 | 함께 포함 | 필수 | Spring Boot, Tomcat, IIS |
| **JKS** | 바이너리 | 함께 포함 | 필수 | Java 레거시 |

### 4. openssl 실무 명령어

인증서 관련 작업의 90%는 openssl로 처리한다.

#### 개인키 생성

```bash
# RSA 2048비트 개인키 생성
openssl genrsa -out server.key 2048

# RSA 4096비트 (보안이 더 필요한 경우)
openssl genrsa -out server.key 4096

# 비밀번호로 보호된 개인키 (AES-256 암호화)
openssl genrsa -aes256 -out server.key 2048
# → 비밀번호 입력 프롬프트가 뜬다
# → Nginx에서 쓰려면 시작할 때마다 비밀번호를 입력해야 한다
# → 자동 재시작이 필요한 서버에서는 비밀번호 없는 키를 쓴다

# ECDSA 키 생성 (RSA보다 짧은 키로 동일한 보안 수준)
openssl ecparam -genkey -name prime256v1 -out server-ec.key
```

#### 개인키에서 비밀번호 제거

Nginx나 Apache를 자동 재시작할 때 비밀번호 입력을 못 하면 서비스가 올라오지 않는다. 이 경우 비밀번호를 제거한 키를 따로 만든다.

```bash
openssl rsa -in server.key -out server-nopass.key
```

#### 키 정보 확인

```bash
# RSA 개인키 내용 확인
openssl rsa -in server.key -text -noout

# 인증서 내용 확인 (발급자, 유효기간, SAN 등)
openssl x509 -in server.crt -text -noout

# 인증서 만료일만 확인
openssl x509 -in server.crt -noout -enddate

# 인증서와 개인키가 매칭되는지 확인
# 두 명령의 출력이 같으면 매칭된다
openssl x509 -noout -modulus -in server.crt | openssl md5
openssl rsa -noout -modulus -in server.key | openssl md5

# 원격 서버 인증서 확인
openssl s_client -connect example.com:443 -servername example.com

# 원격 서버 인증서 만료일 확인
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates
```

키와 인증서가 매칭되지 않으면 Nginx가 `SSL_CTX_use_PrivateKey_file ... error` 로그를 남기면서 시작에 실패한다. 인증서를 갱신한 뒤 키 파일을 안 바꾸거나, 여러 도메인 인증서를 섞어 쓸 때 자주 발생한다.

#### 포맷 변환

실무에서 가장 자주 하게 되는 변환이다. Nginx에서 쓰던 PEM을 Spring Boot용 PKCS12로 바꾸거나, 그 반대가 필요한 경우가 많다.

```bash
# PEM → DER
openssl x509 -in server.crt -outform DER -out server.der

# DER → PEM
openssl x509 -in server.der -inform DER -outform PEM -out server.pem

# PEM(인증서 + 개인키) → PKCS12
openssl pkcs12 -export -in server.crt -inkey server.key \
  -out server.p12 -name myapp \
  -certfile intermediate.crt
# -name: keystore 안에서 이 키를 식별하는 alias
# -certfile: 중간 인증서가 있으면 함께 넣는다

# PKCS12 → PEM (인증서 추출)
openssl pkcs12 -in server.p12 -clcerts -nokeys -out server.crt

# PKCS12 → PEM (개인키 추출)
openssl pkcs12 -in server.p12 -nocerts -nodes -out server.key
# -nodes: 개인키에 비밀번호를 걸지 않는다

# PKCS12 내용 확인
openssl pkcs12 -in server.p12 -info -noout
```

#### JKS 관련 변환 (keytool 사용)

```bash
# PKCS12 → JKS
keytool -importkeystore \
  -srckeystore server.p12 -srcstoretype PKCS12 \
  -destkeystore server.jks -deststoretype JKS

# JKS → PKCS12
keytool -importkeystore \
  -srckeystore server.jks -srcstoretype JKS \
  -destkeystore server.p12 -deststoretype PKCS12

# JKS 내용 확인
keytool -list -v -keystore server.jks
```

### 5. CSR 생성과 인증서 발급 과정

**CSR(Certificate Signing Request)**은 CA에 인증서를 요청할 때 보내는 파일이다. 개인키로 서명한 공개키와 도메인 정보가 들어 있다.

#### CSR 발급 흐름

```
1. 개인키 생성 (server.key)
       │
2. CSR 생성 (server.csr) ← 개인키로 서명
       │
3. CA에 CSR 제출
       │
4. CA가 도메인 소유 확인 (DV의 경우)
       │
5. CA가 인증서 발급 (server.crt)
       │
6. 서버에 인증서 + 개인키 설정
```

#### CSR 생성

```bash
# 개인키 + CSR을 한번에 생성
openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr \
  -subj "/C=KR/ST=Seoul/L=Gangnam/O=MyCompany/CN=example.com"

# 이미 개인키가 있는 경우 CSR만 생성
openssl req -new -key server.key -out server.csr \
  -subj "/C=KR/ST=Seoul/L=Gangnam/O=MyCompany/CN=example.com"
```

`-subj` 필드 설명:

| 필드 | 의미 | 예시 |
|------|------|------|
| `C` | 국가 코드 (2자리) | KR |
| `ST` | 시/도 | Seoul |
| `L` | 구/군 | Gangnam |
| `O` | 조직명 | MyCompany |
| `CN` | 도메인 (Common Name) | example.com |

**CN은 HTTPS에서 가장 중요한 필드다.** 여기에 적은 도메인과 실제 접속 도메인이 다르면 브라우저가 인증서 오류를 띄운다.

#### SAN(Subject Alternative Name)이 있는 CSR

하나의 인증서로 여러 도메인을 커버하려면 SAN을 써야 한다. 요즘 브라우저는 CN보다 SAN을 우선으로 본다.

```bash
# san.cnf 파일 생성
cat > san.cnf << 'EOF'
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = KR
ST = Seoul
L = Gangnam
O = MyCompany
CN = example.com

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = example.com
DNS.2 = www.example.com
DNS.3 = api.example.com
EOF

# SAN이 포함된 CSR 생성
openssl req -new -key server.key -out server.csr -config san.cnf
```

#### CSR 내용 확인

```bash
openssl req -in server.csr -text -noout
```

제출 전에 CN과 SAN이 맞는지 반드시 확인한다. CA에 제출한 뒤에 수정하려면 CSR을 새로 만들어야 한다.

### 6. 자체 서명 인증서 (Self-Signed Certificate)

개발 환경이나 내부 시스템에서 CA 없이 직접 서명한 인증서를 쓰는 경우가 있다. 브라우저에서는 경고가 뜨지만, 내부 API 서버 간 통신이나 로컬 개발에서는 문제없다.

#### 한 줄로 생성 (개인키 + 인증서 동시)

```bash
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout server.key -out server.crt \
  -days 365 \
  -subj "/C=KR/ST=Seoul/O=Dev/CN=localhost"
```

#### 단계별 생성 (개인키 → CSR → 자체 서명)

개별 단계가 필요한 경우다. CA 역할을 직접 하는 것과 같다.

```bash
# 1. 개인키 생성
openssl genrsa -out server.key 2048

# 2. CSR 생성
openssl req -new -key server.key -out server.csr \
  -subj "/C=KR/ST=Seoul/O=Dev/CN=localhost"

# 3. 자체 서명 (365일 유효)
openssl x509 -req -in server.csr -signkey server.key \
  -out server.crt -days 365
```

#### SAN 포함 자체 서명 인증서

localhost에서 개발할 때 Chrome이 SAN 없는 인증서를 거부하는 경우가 있다. SAN을 넣어야 한다.

```bash
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout server.key -out server.crt \
  -days 365 \
  -subj "/C=KR/ST=Seoul/O=Dev/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

#### 내부 CA 구성 (여러 서비스에 인증서를 발급할 때)

마이크로서비스가 여러 개인 환경에서 각각 자체 서명 인증서를 만들면 관리가 안 된다. 내부 CA를 하나 만들고, 거기서 인증서를 발급하는 방식이 낫다.

```bash
# 1. CA 개인키 생성
openssl genrsa -aes256 -out ca.key 4096

# 2. CA 인증서 생성 (10년)
openssl req -x509 -new -key ca.key -out ca.crt -days 3650 \
  -subj "/C=KR/ST=Seoul/O=MyCompany/CN=MyCompany Internal CA"

# 3. 서비스용 개인키 + CSR 생성
openssl genrsa -out service.key 2048
openssl req -new -key service.key -out service.csr \
  -subj "/C=KR/ST=Seoul/O=MyCompany/CN=api.internal"

# 4. CA로 서비스 인증서 서명
openssl x509 -req -in service.csr \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out service.crt -days 365

# 5. 각 서비스/클라이언트에 ca.crt를 신뢰 인증서로 등록
```

이렇게 하면 클라이언트 쪽에서 `ca.crt`만 신뢰하면 CA가 서명한 모든 서비스 인증서를 신뢰한다.

### 7. TLS 버전 비교

| 항목 | TLS 1.2 | TLS 1.3 |
|------|---------|---------|
| **핸드셰이크** | 2-RTT | 1-RTT (빠름) |
| **0-RTT 재연결** | 미지원 | 지원 (재방문 시 즉시 연결) |
| **암호 스위트** | 다수 (일부 취약) | AEAD만 (안전한 것만) |
| **키 교환** | RSA 또는 ECDHE | ECDHE만 (전방 비밀성 보장) |
| **상태** | 점진적 폐지 | **현재 표준** |

설정에서는 `ssl_protocols TLSv1.2 TLSv1.3;`으로 TLS 1.2 이상만 허용한다. TLS 1.0/1.1은 반드시 비활성화해야 한다.

### 8. 암호 스위트 (Cipher Suite)

TLS 통신에 사용할 알고리즘 조합이다.

```
TLS_AES_256_GCM_SHA384
 │    │       │    │
 │    │       │    └── 무결성 확인 (해시)
 │    │       └─────── 인증된 암호화 모드
 │    └─────────────── 대칭키 암호화 알고리즘
 └──────────────────── TLS 프로토콜
```

**TLS 1.3 지원 암호 스위트 (3개만):**
- `TLS_AES_256_GCM_SHA384` — 가장 강력
- `TLS_AES_128_GCM_SHA256` — 성능/보안 균형
- `TLS_CHACHA20_POLY1305_SHA256` — 모바일 최적화

### 9. 전방 비밀성 (Forward Secrecy)

서버의 개인키가 유출되더라도 **과거 통신 내용을 복호화할 수 없는** 성질이다.

```
RSA 키 교환 (전방 비밀성 없음):
  개인키 유출 → 과거 모든 통신 복호화 가능

ECDHE 키 교환 (전방 비밀성 있음):
  개인키 유출 → 과거 통신 복호화 불가
  (매 세션마다 임시 키를 생성하므로)
```

TLS 1.3은 ECDHE만 사용하므로 자동으로 전방 비밀성이 보장된다.

### 10. HSTS (HTTP Strict Transport Security)

브라우저에게 **항상 HTTPS를 사용하라**고 지시하는 보안 헤더다.

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

| 파라미터 | 의미 |
|---------|------|
| `max-age=31536000` | 1년간 HTTPS만 사용 |
| `includeSubDomains` | 서브도메인도 적용 |
| `preload` | 브라우저 사전 로드 목록에 등록 |

```
HSTS 없이:
  사용자 → http://example.com → 301 리다이렉트 → https://example.com
  (첫 요청이 HTTP로 가서 중간자 공격 가능)

HSTS 있으면:
  사용자 → 브라우저가 자동으로 https://example.com 접속
  (HTTP 요청 자체가 발생하지 않음)
```

### 11. mTLS (Mutual TLS)

일반 TLS에서는 클라이언트가 서버의 인증서만 검증한다. mTLS는 **서버도 클라이언트의 인증서를 검증**하는 양방향 인증이다.

#### 일반 TLS vs mTLS

```
일반 TLS:
  Client ──── "너 진짜 서버 맞아?" ────▶ Server
  Client ◀──── 인증서 제시 ──────────── Server
  → 서버만 인증

mTLS:
  Client ──── "너 진짜 서버 맞아?" ────▶ Server
  Client ◀──── 서버 인증서 제시 ──────── Server
  Client ──── 클라이언트 인증서 제시 ──▶ Server
  Client ◀──── "너도 확인됐어" ──────── Server
  → 양쪽 모두 인증
```

#### 사용하는 경우

- 마이크로서비스 간 내부 통신 (서비스 메시에서 기본으로 사용)
- 금융 API, 정부 시스템 같이 클라이언트 신원 확인이 필요한 경우
- IoT 디바이스 인증
- 제로 트러스트 네트워크 구현

#### mTLS 인증서 준비

내부 CA를 만들고, 서버와 클라이언트에 각각 인증서를 발급한다.

```bash
# CA 키 + 인증서 (이미 만들었다면 재사용)
openssl genrsa -out ca.key 4096
openssl req -x509 -new -key ca.key -out ca.crt -days 3650 \
  -subj "/CN=Internal CA"

# 서버 인증서
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=api.internal"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365

# 클라이언트 인증서
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr -subj "/CN=service-a"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out client.crt -days 365
```

#### Nginx mTLS 설정

```nginx
server {
    listen 443 ssl;
    server_name api.internal;

    # 서버 인증서 (일반 TLS와 동일)
    ssl_certificate     /etc/ssl/server.crt;
    ssl_certificate_key /etc/ssl/server.key;

    # 클라이언트 인증서 검증 (mTLS 핵심)
    ssl_client_certificate /etc/ssl/ca.crt;
    ssl_verify_client on;
    # ssl_verify_client optional; 로 하면 인증서 없어도 접속은 가능하다

    # 클라이언트 CN을 백엔드로 전달
    proxy_set_header X-Client-CN $ssl_client_s_dn_cn;
}
```

#### curl로 mTLS 테스트

```bash
# 클라이언트 인증서를 포함하여 요청
curl --cert client.crt --key client.key --cacert ca.crt \
  https://api.internal/health

# 인증서 없이 요청하면 400 에러가 발생한다
curl --cacert ca.crt https://api.internal/health
# → 400 No required SSL certificate was sent
```

#### Spring Boot mTLS 설정

```yaml
# application.yml
server:
  ssl:
    enabled: true
    key-store: classpath:server.p12
    key-store-type: PKCS12
    key-store-password: ${SSL_PASSWORD}
    # 클라이언트 인증서 검증
    client-auth: need  # need: 필수, want: 선택
    trust-store: classpath:truststore.p12
    trust-store-type: PKCS12
    trust-store-password: ${TRUST_PASSWORD}
```

truststore에는 CA 인증서를 넣는다:

```bash
# CA 인증서를 truststore로 변환
keytool -import -alias internal-ca -file ca.crt \
  -keystore truststore.p12 -storetype PKCS12 \
  -storepass changeit -noprompt
```

## 예시

### Nginx HTTPS 보안 설정 (프로덕션)

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    # 인증서
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # TLS 버전
    ssl_protocols TLSv1.2 TLSv1.3;

    # 암호 스위트
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # OCSP Stapling (인증서 상태 확인 가속)
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;

    # 세션 캐시 (핸드셰이크 재사용)
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # 보안 헤더
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
}
```

### Spring Boot HTTPS 설정

#### keystore 생성 과정

Let's Encrypt 같은 CA에서 받은 PEM 파일을 Spring Boot가 읽을 수 있는 PKCS12로 변환한다.

```bash
# Let's Encrypt 인증서 파일 확인
ls /etc/letsencrypt/live/example.com/
# fullchain.pem  — 서버 인증서 + 중간 인증서
# privkey.pem    — 개인키
# cert.pem       — 서버 인증서만
# chain.pem      — 중간 인증서만

# PEM → PKCS12 변환
openssl pkcs12 -export \
  -in /etc/letsencrypt/live/example.com/fullchain.pem \
  -inkey /etc/letsencrypt/live/example.com/privkey.pem \
  -out keystore.p12 \
  -name myapp \
  -passout pass:changeit

# keystore 내용 확인
keytool -list -v -keystore keystore.p12 -storetype PKCS12 -storepass changeit
```

자체 서명 인증서로 keystore를 만드는 경우 (개발 환경):

```bash
# keytool로 한번에 생성 (개인키 + 자체 서명 인증서)
keytool -genkeypair -alias myapp \
  -keyalg RSA -keysize 2048 \
  -storetype PKCS12 \
  -keystore keystore.p12 \
  -validity 365 \
  -storepass changeit \
  -dname "CN=localhost, O=Dev, L=Seoul, C=KR" \
  -ext "SAN=dns:localhost,ip:127.0.0.1"
```

#### application.yml

```yaml
server:
  ssl:
    enabled: true
    key-store: classpath:keystore.p12
    key-store-type: PKCS12
    key-store-password: ${SSL_PASSWORD}
    key-alias: myapp
  port: 8443
```

실무에서는 Spring Boot에 직접 SSL을 설정하기보다 **Nginx에서 SSL을 처리**(SSL Termination)하고, Spring Boot는 HTTP로 통신하는 것이 일반적이다. 다만 mTLS가 필요하거나, Nginx 없이 단독 실행하는 경우에는 직접 설정한다.

## 운영 시 주의사항

### 흔한 실수

| 실수 | 결과 | 해결 |
|------|------|------|
| Mixed Content | HTTPS 페이지에서 HTTP 리소스 로드 시 경고 | 모든 리소스를 HTTPS로 |
| 인증서 만료 | 사이트 접근 불가 | 자동 갱신 크론 설정 |
| 자체 서명 인증서 | 브라우저 경고 | Let's Encrypt 사용 |
| TLS 1.0 허용 | 보안 취약 | `ssl_protocols TLSv1.2 TLSv1.3;` |
| 키-인증서 불일치 | Nginx/Apache 시작 실패 | modulus 비교로 확인 |
| 중간 인증서 누락 | 일부 클라이언트에서 검증 실패 | fullchain.pem 사용 |

### 인증서 갱신 시 주의점

Let's Encrypt 인증서는 90일마다 갱신해야 한다. 갱신 자체는 `certbot renew`가 자동으로 처리하지만, Spring Boot처럼 PKCS12로 변환해서 쓰는 경우 갱신 후 변환 스크립트까지 돌려야 한다.

```bash
#!/bin/bash
# renew-and-convert.sh
certbot renew --quiet

# 갱신됐으면 PKCS12로 변환
openssl pkcs12 -export \
  -in /etc/letsencrypt/live/example.com/fullchain.pem \
  -inkey /etc/letsencrypt/live/example.com/privkey.pem \
  -out /opt/app/keystore.p12 \
  -name myapp \
  -passout pass:${SSL_PASSWORD}

# Spring Boot 재시작
systemctl restart myapp
```

## 참고

- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/) — Nginx/Apache SSL 설정 자동 생성
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/) — SSL 보안 점검
- [Let's Encrypt](https://letsencrypt.org/)
- [AES 암호화](AES.md) — TLS에서 사용하는 대칭키 암호화
- [RSA 암호화](RSA.md) — 인증서 서명에 사용
- [Nginx 리버스 프록시](../WebServer/Nginx/Reverse_Proxy_and_Load_Balancing.md) — SSL Termination 설정
