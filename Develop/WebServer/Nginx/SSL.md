# Nginx SSL 설정 가이드

## 목차
1. [SSL이란?](#ssl이란)
2. [SSL 인증서 종류](#ssl-인증서-종류)
3. [무료 SSL 인증서 발급 (Let's Encrypt)](#무료-ssl-인증서-발급)
4. [Nginx SSL 설정](#nginx-ssl-설정)
5. [SSL 설정 최적화](#ssl-설정-최적화)
6. [문제 해결](#문제-해결)

## SSL이란?
SSL(Secure Sockets Layer)은 웹 서버와 브라우저 사이의 통신을 암호화하는 보안 프로토콜입니다. TLS(Transport Layer Security)라고도 불리며, 데이터 전송 시 제3자가 정보를 탈취하거나 변조하는 것을 방지합니다.

### SSL의 주요 기능
- 데이터 암호화: 전송되는 모든 데이터를 암호화
- 인증: 서버와 클라이언트의 신원 확인
- 데이터 무결성: 전송 중 데이터가 변조되지 않았음을 보장

## SSL 인증서 종류

### 1. 도메인 검증형 (DV, Domain Validation)
- 가장 기본적인 인증서
- 도메인 소유권만 확인
- 발급이 빠르고 비용이 저렴
- 적합한 경우: 개인 블로그, 소규모 웹사이트

### 2. 조직 검증형 (OV, Organization Validation)
- 도메인 소유권 + 조직 정보 검증
- 기업용 웹사이트에 적합
- 발급에 1-3일 소요

### 3. 확장 검증형 (EV, Extended Validation)
- 가장 엄격한 검증 절차
- 금융기관, 전자상거래 사이트에 적합
- 브라우저 주소창에 기업명 표시
- 발급에 1-2주 소요

## 무료 SSL 인증서 발급

### Let's Encrypt 사용하기
Let's Encrypt는 무료로 SSL 인증서를 발급해주는 인증 기관입니다.

1. Certbot 설치
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# CentOS
sudo yum install certbot python3-certbot-nginx

# macOS
brew install certbot
```

2. 인증서 발급
```bash
sudo certbot --nginx -d example.com -d www.example.com
```

3. 자동 갱신 설정
```bash
sudo certbot renew --dry-run
```

## Nginx SSL 설정

### 기본 설정
```nginx
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name example.com www.example.com;

    # SSL 인증서 설정
    ssl_certificate /etc/nginx/ssl/example.com.crt;
    ssl_certificate_key /etc/nginx/ssl/example.com.key;

    # SSL 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

    # HSTS 설정
    add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## SSL 설정 최적화

### 1. SSL 세션 캐시
```nginx
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

### 2. OCSP Stapling
```nginx
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
```

### 3. DH 파라미터 생성
```bash
openssl dhparam -out /etc/nginx/dhparam.pem 2048
```
```nginx
ssl_dhparam /etc/nginx/dhparam.pem;
```

## 문제 해결

### 1. SSL 인증서 오류
- 인증서 경로 확인
- 인증서 권한 설정
- 인증서 만료 여부 확인

### 2. 연결 오류
- 방화벽 설정 확인
- 포트(443) 개방 확인
- SSL 프로토콜 버전 확인

### 3. 성능 이슈
- SSL 세션 캐시 확인
- DH 파라미터 최적화
- SSL 설정 최적화 확인

### 4. 일반적인 문제 해결 명령어
```bash
# Nginx 설정 문법 검사
nginx -t

# Nginx 재시작
sudo systemctl restart nginx

# SSL 인증서 정보 확인
openssl x509 -in /path/to/certificate.crt -text -noout

# SSL 연결 테스트
openssl s_client -connect example.com:443 -servername example.com
```

## 보안 모범 사례

1. 강력한 암호화 설정 사용
2. 정기적인 인증서 갱신
3. 취약한 SSL/TLS 버전 비활성화
4. HSTS 헤더 설정
5. 보안 관련 HTTP 헤더 추가

```nginx
# 추가 보안 헤더
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
```

---

> 참고 자료
> 1. [Nginx 공식 문서](https://nginx.org/en/docs/)
> 2. [Let's Encrypt 공식 문서](https://letsencrypt.org/docs/)
> 3. [SSL Labs](https://www.ssllabs.com/ssltest/)
> 4. [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)