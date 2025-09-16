---
title: HTTP HyperText Transfer Protocol
tags: [network, 7-layer, application-layer, http]
updated: 2025-08-10
---
# HTTP (HyperText Transfer Protocol)

> **📌 통합된 기존 파일들**: 이 가이드는 다음 기존 파일들의 내용을 통합하여 더 체계적으로 정리한 것입니다.
> - TLS & SSL 기본 개념과 보안 프로토콜
> - HTTP vs HTTPS 차이점과 특징
> - TLS 핸드셰이크 과정 상세 설명
> - 암호화 방식 (대칭키, 비대칭키)
> - SSL 인증서 구조와 검증 과정
> - Nginx에서 SSL/TLS 설정 방법

## HTTP 개요
- HTTP는 웹의 기반이 되는 프로토콜로, HTML 문서와 같은 리소스들을 가져올 수 있도록 해주는 프로토콜입니다.
- 클라이언트-서버 모델을 따르는 프로토콜입니다.
- 기본적으로 80번 포트를 사용합니다.
- HTTPS는 HTTP의 보안이 강화된 버전으로, 443번 포트를 사용합니다.

## HTTP 기반 시스템의 구성요소

### 1. 클라이언트 (사용자 에이전트)
- 웹 브라우저가 가장 일반적인 클라이언트입니다.
- 사용자를 대신하여 HTTP 요청을 보내는 모든 도구가 클라이언트가 될 수 있습니다.
- 예시:
  - 웹 브라우저 (Chrome, Firefox, Safari 등)
  - 검색 엔진 크롤러
  - 모바일 앱
  - IoT 기기

### 2. 서버
- 클라이언트의 요청에 대한 응답을 제공하는 시스템
- 일반적으로 다음과 같은 역할을 수행:
  - 정적 파일 제공 (HTML, CSS, JavaScript, 이미지 등)
  - 동적 콘텐츠 생성
  - 데이터베이스 조작
  - 비즈니스 로직 처리

### 3. 프록시
- 클라이언트와 서버 사이에 위치하는 중간 서버
- 주요 기능:
  - 캐싱
  - 필터링
  - 로드 밸런싱
  - 인증
  - 로깅

## HTTP 프로토콜의 특징

### 1. Connectionless (비연결 지향)
- 클라이언트가 서버에 요청을 보내고 서버가 응답을 보내면 연결이 종료됩니다.
- 장점:
  - 서버 리소스의 효율적 사용
  - 동시 접속자 수 증가 가능
- 단점:
  - 매 요청마다 새로운 연결 설정 필요
  - 연결 설정에 따른 지연 발생

### 2. Stateless (무상태)
- 각 요청은 독립적으로 처리되며, 이전 요청과의 연관성이 없습니다.
- 장점:
  - 서버의 복잡도 감소
  - 확장성이 좋음
- 단점:
  - 상태 정보 유지를 위한 추가 작업 필요
  - 매 요청마다 인증 정보 전송 필요

### 3. 앱에서 세션을 사용하지 않는 이유
- HTTP의 Stateless 특성으로 인해 서버에서 세션을 관리해야 합니다.
- 모바일 앱의 특성상 다음과 같은 문제가 발생할 수 있습니다:
  - 네트워크 연결 불안정성
  - 앱 백그라운드 전환 시 세션 유지 어려움
  - 보안 취약점 (세션 하이재킹)
- 대안:
  - JWT (JSON Web Token) 사용
  - OAuth 2.0 인증
  - API 키 기반 인증

## HTTP 통신 흐름

### 1. TCP 연결 설정
- 클라이언트가 서버와 TCP 연결을 수립합니다.
- 연결 방식:
  - 새로운 연결 생성
  - 기존 연결 재사용
  - 여러 TCP 연결 병렬 사용

### 2. HTTP 메시지 전송
- HTTP/1.1: 텍스트 기반의 읽기 쉬운 메시지 형식
- HTTP/2: 바이너리 프로토콜로 변경되어 프레임 단위로 전송
- 메시지 구성:
  - 시작줄 (요청/응답 라인)
  - 헤더
  - 본문

### 3. 서버 응답 처리
- 서버는 요청을 처리하고 적절한 응답을 반환합니다.
- 응답 구성:
  - 상태 코드
  - 응답 헤더
  - 응답 본문

### 4. 연결 종료 또는 재사용
- HTTP/1.0: 각 요청마다 새로운 연결
- HTTP/1.1: Keep-Alive를 통한 연결 재사용
- HTTP/2: 멀티플렉싱을 통한 효율적인 연결 관리

## HTTP 메서드
- GET: 리소스 조회
- POST: 리소스 생성
- PUT: 리소스 수정
- DELETE: 리소스 삭제
- PATCH: 리소스 부분 수정
- HEAD: 리소스 헤더만 조회
- OPTIONS: 지원하는 메서드 조회
- TRACE: 요청/응답 추적
- CONNECT: 프록시 서버 연결

## HTTP 상태 코드
### 1xx (정보)
- 100 Continue
- 101 Switching Protocols

### 2xx (성공)
- 200 OK
- 201 Created
- 204 No Content

### 3xx (리다이렉션)
- 301 Moved Permanently
- 302 Found
- 304 Not Modified

### 4xx (클라이언트 오류)
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found

### 5xx (서버 오류)
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable

## HTTP 헤더

## 배경
- Date
- Connection
- Cache-Control

- Host
- User-Agent
- Accept
- Authorization

- Server
- Set-Cookie
- Content-Type
- Content-Length

## HTTPS (HTTP Secure)

### HTTPS란?
- HyperText Transfer Protocol over Secure Socket Layer, HTTP over TLS, HTTP over SSL, HTTP Secure 등으로 불리는 HTTPS는 HTTP에 데이터 암호화가 추가된 프로토콜입니다.
- HTTPS는 HTTP와 다르게 443번 포트를 사용하며, 네트워크 상에서 중간에 제3자가 정보를 볼 수 없도록 암호화를 지원하고 있습니다.
- SSL/TLS 프로토콜을 통해 데이터를 암호화하여 전송합니다.

### HTTP와 HTTPS의 주요 차이점

| 측면 | HTTP | HTTPS |
|------|------|-------|
| **보안성** | 데이터가 암호화되지 않은 평문으로 전송되어 보안에 취약 | SSL/TLS를 통해 데이터를 암호화하여 전송하여 보안성 강화 |
| **포트** | 80번 포트 사용 | 443번 포트 사용 |
| **인증서** | 인증서 불필요 | SSL 인증서 필요 (CA에서 발급) |
| **연산 속도** | 암호화 과정이 없어 상대적으로 빠름 | 암호화/복호화 과정으로 인해 상대적으로 느림 |
| **URL 형식** | `http://example.com` | `https://example.com` |

## TLS/SSL (Transport Layer Security & Secure Sockets Layer)

### SSL과 TLS란?
웹에서 데이터를 안전하게 전송하기 위한 보안 프로토콜입니다.

- **SSL (Secure Sockets Layer)**: 1995년 Netscape에서 처음 개발한 보안 프로토콜
- **TLS (Transport Layer Security)**: SSL의 개선된 버전으로, 현재 웹에서 사용되는 표준 보안 프로토콜

### 보안 프로토콜의 필요성
- 개인정보나 금융정보 같은 민감한 데이터를 해커로부터 보호
- 데이터 전송 중 중간자 공격 방지
- 웹사이트의 신원 확인 및 인증

### SSL/TLS의 발전 과정
- **SSL 1.0**: 개발되었지만 공개되지 않음
- **SSL 2.0**: 1995년 발표, 보안 취약점 발견으로 사용 중단
- **SSL 3.0**: 1996년 발표, POODLE 공격으로 인해 사용 중단
- **TLS 1.0**: 1999년 발표, SSL 3.0의 개선 버전
- **TLS 1.1**: 2006년 발표, BEAST 공격 대응
- **TLS 1.2**: 2008년 발표, 현재 널리 사용됨
- **TLS 1.3**: 2018년 발표, 최신 보안 기능 포함

### SSL/TLS 프로토콜 버전 비교

| 버전 | 발표년도 | 보안 수준 | 브라우저 지원 | 권장사항 |
|------|----------|-----------|---------------|----------|
| **SSL 2.0** | 1995 | 취약 | 지원 안함 | 사용 금지 |
| **SSL 3.0** | 1996 | 취약 | 지원 안함 | 사용 금지 |
| **TLS 1.0** | 1999 | 취약 | 제한적 지원 | 사용 금지 |
| **TLS 1.1** | 2006 | 취약 | 제한적 지원 | 사용 금지 |
| **TLS 1.2** | 2008 | 안전 | 널리 지원 | 권장 |
| **TLS 1.3** | 2018 | 매우 안전 | 최신 브라우저 | 최우선 권장 |

## 암호화 방식

### 대칭키 암호화 (Symmetric Encryption)
- 클라이언트와 서버가 동일한 키를 사용해 암호화/복호화를 진행함
- 키가 노출되면 매우 위험하지만 연산 속도가 빠름
- AES, DES, 3DES 등이 대표적인 대칭키 암호화 알고리즘
- 키 교환 문제가 있음 (키를 안전하게 전달하기 어려움)

### 비대칭키 암호화 (Asymmetric Encryption)
- 1개의 쌍으로 구성된 공개키와 개인키를 암호화/복호화 하는데 사용함
- 공개키로 암호화하면 개인키로만 복호화 가능
- 개인키로 암호화하면 공개키로만 복호화 가능
- 키가 노출되어도 비교적 안전하지만 연산 속도가 느림
- RSA가 대표적인 비대칭키 암호화 알고리즘

### 하이브리드 암호화 방식
- 공개키 암호화 방식과 공개키의 느리다는 단점을 보완한 대칭키 암호화 방식을 함께 사용
- 공개키 방식으로 대칭키를 전달하고, 서로 공유된 대칭키를 가지고 통신

## TLS 핸드셰이크 과정

### TLS 핸드셰이크란?
- TLS 핸드셰이크는 TLS 암호화를 사용하는 통신 세션을 실행하는 프로세스입니다.
- TLS 핸드셰이크 중에, 통신하는 양측에서는 메시지를 교환하여 서로를 인식하고 서로를 검증하며 사용할 암호화 알고리즘을 구성하고 세션 키에 합의합니다.
- TLS 핸드셰이크는 HTTPS 작동 원리의 근간을 이룹니다.

### TLS 핸드셰이크 단계

#### 1. Client Hello
- 클라이언트가 서버에 연결을 시도
- 클라이언트가 지원하는 암호화 방식 전송
- 클라이언트가 생성한 랜덤 데이터 전송

#### 2. Server Hello
- 서버가 클라이언트의 인사에 응답하며, 필요한 정보를 제공
- 서버가 선택한 암호화 방식 응답
- 서버가 생성한 랜덤 데이터 전송

#### 3. Certificate
- 서버가 자신의 SSL 인증서를 클라이언트에 전송
- 클라이언트가 서버의 SSL 인증서를 인증서 발행 기관을 통해 검증
- 이를 통해 서버가 인증서에 명시된 서버인지, 그리고 클라이언트가 상호작용 중인 서버가 실제 해당 도메인의 소유자인지를 확인

#### 4. Key Exchange
- 클라이언트가 "예비 마스터 암호"라고 하는 무작위 바이트 문자열을 하나 더 전송
- 예비 마스터 암호는 공개 키로 암호화되어 있으며, 서버가 개인 키로만 해독할 수 있음
- 클라이언트는 서버의 SSL 인증서를 통해 공개 키를 받음

#### 5. Server Key Exchange & Server Hello Done
- 서버가 예비 마스터 암호를 해독하여, master key를 저장하고 연결에 고유한 값을 부여하기 위한 session key를 생성
- 서버가 핸드셰이크 완료를 알림

#### 6. Client Key Exchange & Change Cipher Spec & Finished
- 클라이언트가 세션 키를 사용하여 암호화된 통신 준비 완료를 알림
- 클라이언트가 핸드셰이크 완료를 알림

#### 7. Change Cipher Spec & Finished
- 서버가 세션 키를 사용하여 암호화된 통신 준비 완료를 알림
- 서버가 핸드셰이크 완료를 알림

#### 8. 암호화된 통신 시작
- SSL/TLS 핸드셰이크를 종료하고, HTTPS 통신을 시작

## SSL/TLS 인증서

### 인증서 구성 요소
- **Public Key**: 암호화에 사용되는 공개키
- **Private Key**: 복호화에 사용되는 개인키 (서버에만 보관)
- **Domain Name**: 인증서가 적용되는 도메인
- **Issuer**: 인증서 발급 기관
- **Validity Period**: 유효기간

### 인증서 종류

#### 1. 도메인 검증 (DV) 인증서
- 가장 기본적인 인증서
- 도메인 소유권만 확인
- 무료로 발급 가능 (Let's Encrypt)
- 개인 웹사이트, 블로그에 적합

#### 2. 조직 검증 (OV) 인증서
- 조직 정보도 함께 확인
- 비용 발생
- 기업 웹사이트에 적합

#### 3. 확장 검증 (EV) 인증서
- 가장 엄격한 검증 과정
- 브라우저 주소창에 조직명 표시
- 금융, 전자상거래 사이트에 적합

### 인증서를 통한 암호화 과정
1. 클라이언트가 서버에 연결 요청
2. 서버가 SSL/TLS 인증서 전송
3. 클라이언트가 인증서 검증
4. 공개키로 세션키 암호화하여 전송
5. 서버가 개인키로 세션키 복호화
6. 세션키로 데이터 암호화 통신

## 실제 구현 예제

### Node.js에서 HTTPS 서버 생성
```javascript
const https = require('https');
const fs = require('fs');

// SSL 인증서 로드
const options = {
    key: fs.readFileSync('private-key.pem'),
    cert: fs.readFileSync('certificate.pem'),
    ca: fs.readFileSync('ca-bundle.pem')
};

// HTTPS 서버 생성
const server = https.createServer(options, (req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('안전한 HTTPS 연결입니다!\n');
});

server.listen(443, () => {
    console.log('HTTPS 서버가 포트 443에서 실행 중입니다.');
});
```

### 브라우저에서 HTTPS 연결 확인
```javascript
// 브라우저에서 HTTPS 연결 확인
const checkHttpsConnection = () => {
    const protocol = window.location.protocol;
    const isSecure = protocol === 'https:';
    
    if (isSecure) {
        console.log('안전한 HTTPS 연결입니다.');
        
        // 인증서 정보 확인
        if ('connection' in navigator) {
            const connection = navigator.connection;
            console.log('보안 프로토콜:', connection.effectiveType);
        }
    } else {
        console.log('HTTP 연결입니다. 보안에 주의하세요.');
    }
    
    return isSecure;
};

// 사용 예시
checkHttpsConnection();
```

### SSL/TLS 인증서 생성
```bash
# 개인키 생성
openssl genrsa -out private-key.pem 2048

# 자체 서명 인증서 생성
openssl req -new -x509 -key private-key.pem -out certificate.pem -days 365

# 인증서 정보 확인
openssl x509 -in certificate.pem -text -noout
```

### Let's Encrypt를 사용한 무료 인증서 발급
```bash
# Certbot 설치 (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install certbot

# 웹 서버용 인증서 발급
sudo certbot --nginx -d example.com -d www.example.com

# 인증서 자동 갱신 설정
sudo crontab -e
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## Nginx에서 SSL/TLS 설정

### 기본 HTTPS 설정
```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    
    # SSL 인증서 설정
    ssl_certificate /path/to/certificate.pem;
    ssl_certificate_key /path/to/private-key.pem;
    
    # SSL 프로토콜 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # HSTS 설정
    add_header Strict-Transport-Security "max-age=63072000" always;
    
    location / {
        root /var/www/html;
        index index.html;
    }
}

# HTTP를 HTTPS로 리다이렉트
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

### 보안 강화된 SSL 설정
```nginx
# SSL 설정 파일 분리
# /etc/nginx/conf.d/ssl.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

# DH 파라미터 (성능 최적화)
ssl_dhparam /etc/nginx/ssl/dhparam.pem;

# SSL 세션 설정
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# 보안 헤더
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
```

## 보안 헤더

### HSTS (HTTP Strict Transport Security)
- 브라우저가 HTTP 대신 HTTPS만 사용하도록 강제
- `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`

### CSP (Content Security Policy)
- XSS 공격을 방지하기 위한 정책
- `Content-Security-Policy: default-src 'self'`

### X-Frame-Options
- 클릭재킹 공격 방지
- `X-Frame-Options: SAMEORIGIN`

### X-XSS-Protection
- 브라우저의 XSS 필터 활성화
- `X-XSS-Protection: 1; mode=block`

### X-Content-Type-Options
- MIME 타입 스니핑 방지
- `X-Content-Type-Options: nosniff`

## SSL/TLS 테스트 도구

### 온라인 테스트 도구
- **SSL Labs**: https://www.ssllabs.com/ssltest/
- **Mozilla Observatory**: https://observatory.mozilla.org/
- **Security Headers**: https://securityheaders.com/

### 명령줄 도구
```bash
# OpenSSL을 사용한 연결 테스트
openssl s_client -connect example.com:443 -servername example.com

# nmap을 사용한 SSL 스캔
nmap --script ssl-enum-ciphers -p 443 example.com

# SSL 인증서 만료일 확인
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -dates
```

## 결론

HTTP/HTTPS/TLS는 웹 통신의 핵심 프로토콜입니다.
- HTTP는 웹의 기본 프로토콜로, 클라이언트-서버 간 통신을 담당합니다.
- HTTPS는 HTTP에 SSL/TLS 암호화를 추가하여 보안을 강화한 프로토콜입니다.
- TLS 핸드셰이크를 통해 안전한 암호화 통신을 설정합니다.
- 적절한 SSL 인증서와 보안 설정으로 안전한 웹 서비스를 제공할 수 있습니다.
- 정기적인 인증서 관리와 모니터링으로 지속적인 보안을 유지하는 것이 중요합니다.

> 출처: 
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Overview
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Methods
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Status

- HSTS
- CSP
- X-Frame-Options
- X-XSS-Protection

> 출처: 
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Overview
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Methods
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Status






- HSTS
- CSP
- X-Frame-Options
- X-XSS-Protection

> 출처: 
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Overview
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Methods
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Status

- HSTS
- CSP
- X-Frame-Options
- X-XSS-Protection

> 출처: 
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Overview
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Methods
> - https://developer.mozilla.org/ko/docs/Web/HTTP/Status










