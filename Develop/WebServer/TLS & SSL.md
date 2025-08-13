---
title: TLS & SSL (Transport Layer Security & Secure Sockets Layer)
tags: [webserver, tls, ssl, security, encryption, https]
updated: 2024-12-19
---

# TLS & SSL (Transport Layer Security & Secure Sockets Layer)

## 배경

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

## 핵심

### SSL/TLS 연결 과정

#### 1. 핸드셰이크 과정
```javascript
// SSL/TLS 핸드셰이크 과정
const tlsHandshake = {
    step1: "Client Hello - 클라이언트가 지원하는 암호화 방식 전송",
    step2: "Server Hello - 서버가 선택한 암호화 방식 응답",
    step3: "Certificate - 서버 인증서 전송",
    step4: "Key Exchange - 암호화 키 교환",
    step5: "Finished - 핸드셰이크 완료 확인"
};
```

#### 2. 실제 연결 과정
1. **클라이언트가 서버에 연결 요청**
2. **서버가 SSL/TLS 인증서 전송**
3. **클라이언트가 인증서 검증**
4. **암호화 키 교환**
5. **암호화된 통신 시작**

### SSL/TLS 인증서 구조

#### 인증서 구성 요소
```javascript
// SSL/TLS 인증서 구조
const sslCertificate = {
    purpose: "웹사이트 신원 확인 및 암호화 키 제공",
    components: {
        publicKey: "암호화에 사용되는 공개키",
        privateKey: "복호화에 사용되는 개인키 (서버에만 보관)",
        domainName: "인증서가 적용되는 도메인",
        issuer: "인증서 발급 기관",
        validityPeriod: "유효기간"
    }
};
```

#### 인증서를 통한 암호화 과정
```javascript
// 인증서를 통한 암호화 과정
const encryptionProcess = {
    step1: "클라이언트가 서버에 연결 요청",
    step2: "서버가 SSL/TLS 인증서 전송",
    step3: "클라이언트가 인증서 검증",
    step4: "공개키로 세션키 암호화하여 전송",
    step5: "서버가 개인키로 세션키 복호화",
    step6: "세션키로 데이터 암호화 통신"
};
```

### SSL vs TLS 비교

#### 보안 취약점
```javascript
// SSL의 알려진 보안 취약점
const sslVulnerabilities = {
    "POODLE": "SSL 3.0 취약점 (2014)",
    "BEAST": "SSL/TLS 1.0 취약점 (2011)",
    "Heartbleed": "OpenSSL 라이브러리 취약점 (2014)",
    "FREAK": "SSL/TLS 취약점 (2015)"
};
```

#### 프로토콜 호환성
```javascript
// 프로토콜 호환성 예시
const protocolCompatibility = {
    modernBrowser: {
        supports: ["TLS 1.2", "TLS 1.3"],
        deprecated: ["SSL 2.0", "SSL 3.0", "TLS 1.0", "TLS 1.1"]
    },
    oldServer: {
        supports: ["SSL 3.0", "TLS 1.0"],
        result: "연결 실패 또는 보안 경고"
    }
};
```

## 예시

### HTTPS 연결 확인

#### 브라우저에서 HTTPS 연결 확인
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

#### Node.js에서 HTTPS 서버 생성
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

### SSL/TLS 인증서 생성

#### OpenSSL을 사용한 자체 서명 인증서 생성
```bash
# 개인키 생성
openssl genrsa -out private-key.pem 2048

# 자체 서명 인증서 생성
openssl req -new -x509 -key private-key.pem -out certificate.pem -days 365

# 인증서 정보 확인
openssl x509 -in certificate.pem -text -noout
```

#### Let's Encrypt를 사용한 무료 인증서 발급
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

### Nginx에서 SSL/TLS 설정

#### 기본 HTTPS 설정
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

### Apache에서 SSL/TLS 설정

#### Virtual Host 설정
```apache
<VirtualHost *:443>
    ServerName example.com
    DocumentRoot /var/www/html
    
    # SSL 설정
    SSLEngine on
    SSLCertificateFile /path/to/certificate.pem
    SSLCertificateKeyFile /path/to/private-key.pem
    SSLCertificateChainFile /path/to/ca-bundle.pem
    
    # 보안 헤더 설정
    Header always set Strict-Transport-Security "max-age=63072000"
    Header always set X-Frame-Options DENY
    Header always set X-Content-Type-Options nosniff
    
    <Directory /var/www/html>
        Require all granted
    </Directory>
</VirtualHost>

# HTTP를 HTTPS로 리다이렉트
<VirtualHost *:80>
    ServerName example.com
    Redirect permanent / https://example.com/
</VirtualHost>
```

## 운영 팁

### SSL/TLS 보안 설정

#### 1. 강력한 암호화 설정
```nginx
# Nginx에서 강력한 암호화 설정
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

#### 2. 보안 헤더 설정
```javascript
// 보안 헤더 설정 예시
const securityHeaders = {
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'"
};
```

#### 3. 인증서 모니터링
```javascript
// 인증서 만료일 모니터링
class CertificateMonitor {
    constructor() {
        this.certificates = new Map();
    }
    
    addCertificate(domain, expiryDate) {
        this.certificates.set(domain, new Date(expiryDate));
    }
    
    checkExpiry() {
        const now = new Date();
        const warnings = [];
        
        for (const [domain, expiry] of this.certificates) {
            const daysUntilExpiry = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
            
            if (daysUntilExpiry <= 30) {
                warnings.push({
                    domain: domain,
                    daysUntilExpiry: daysUntilExpiry,
                    severity: daysUntilExpiry <= 7 ? 'critical' : 'warning'
                });
            }
        }
        
        return warnings;
    }
}

// 사용 예시
const monitor = new CertificateMonitor();
monitor.addCertificate('example.com', '2024-12-31');
const warnings = monitor.checkExpiry();
console.log('인증서 만료 경고:', warnings);
```

### 성능 최적화

#### 1. SSL 세션 재사용
```nginx
# Nginx에서 SSL 세션 재사용 설정
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_session_tickets off;
```

#### 2. OCSP Stapling
```nginx
# OCSP Stapling 설정
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /path/to/ca-bundle.pem;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
```

#### 3. HTTP/2 활성화
```nginx
# HTTP/2 활성화
listen 443 ssl http2;
```

### 인증서 관리

#### 1. 자동 갱신 스크립트
```bash
#!/bin/bash
# 인증서 자동 갱신 스크립트

DOMAIN="example.com"
EMAIL="admin@example.com"

# Let's Encrypt 인증서 갱신
certbot renew --quiet

# Nginx 설정 테스트
nginx -t

if [ $? -eq 0 ]; then
    # Nginx 재시작
    systemctl reload nginx
    echo "인증서 갱신 완료: $(date)"
else
    echo "Nginx 설정 오류: $(date)"
    exit 1
fi
```

#### 2. 인증서 백업
```bash
#!/bin/bash
# 인증서 백업 스크립트

BACKUP_DIR="/backup/ssl"
DATE=$(date +%Y%m%d_%H%M%S)

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# 인증서 파일 백업
cp /etc/letsencrypt/live/example.com/fullchain.pem $BACKUP_DIR/fullchain_$DATE.pem
cp /etc/letsencrypt/live/example.com/privkey.pem $BACKUP_DIR/privkey_$DATE.pem

# 30일 이상 된 백업 파일 삭제
find $BACKUP_DIR -name "*.pem" -mtime +30 -delete

echo "인증서 백업 완료: $DATE"
```

## 참고

### SSL/TLS 프로토콜 버전 비교

| 버전 | 발표년도 | 보안 수준 | 브라우저 지원 | 권장사항 |
|------|----------|-----------|---------------|----------|
| **SSL 2.0** | 1995 | 취약 | 지원 안함 | 사용 금지 |
| **SSL 3.0** | 1996 | 취약 | 지원 안함 | 사용 금지 |
| **TLS 1.0** | 1999 | 취약 | 제한적 지원 | 사용 금지 |
| **TLS 1.1** | 2006 | 취약 | 제한적 지원 | 사용 금지 |
| **TLS 1.2** | 2008 | 안전 | 널리 지원 | 권장 |
| **TLS 1.3** | 2018 | 매우 안전 | 최신 브라우저 | 최우선 권장 |

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

### SSL/TLS 테스트 도구

#### 1. 온라인 테스트 도구
- **SSL Labs**: https://www.ssllabs.com/ssltest/
- **Mozilla Observatory**: https://observatory.mozilla.org/
- **Security Headers**: https://securityheaders.com/

#### 2. 명령줄 도구
```bash
# OpenSSL을 사용한 연결 테스트
openssl s_client -connect example.com:443 -servername example.com

# nmap을 사용한 SSL 스캔
nmap --script ssl-enum-ciphers -p 443 example.com
```

### 결론
SSL/TLS는 웹 보안의 핵심 프로토콜로, HTTPS 통신을 통해 데이터를 안전하게 전송할 수 있게 해줍니다.
최신 TLS 1.3 프로토콜 사용과 적절한 보안 설정을 통해 안전한 웹 서비스를 제공할 수 있습니다.
정기적인 인증서 관리와 모니터링을 통해 지속적인 보안을 유지하는 것이 중요합니다.
