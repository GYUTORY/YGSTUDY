---
title: Nginx SSL 설정 가이드
tags: [webserver, nginx, ssl, security, https, tls]
updated: 2025-08-10
---

# Nginx SSL 설정 가이드

## 배경

SSL(Secure Sockets Layer)과 TLS(Transport Layer Security)는 웹사이트와 사용자 간의 통신을 암호화하여 보안을 강화하는 프로토콜입니다. Nginx에서 SSL을 설정하면 HTTPS를 통해 안전한 웹 서비스를 제공할 수 있습니다.

### SSL/TLS의 필요성
- **데이터 암호화**: 사용자와 서버 간 통신 내용 보호
- **신원 인증**: 서버의 신원을 확인하여 피싱 공격 방지
- **데이터 무결성**: 전송 중 데이터 변조 방지
- **SEO 최적화**: HTTPS는 검색 엔진 최적화에 긍정적 영향
- **사용자 신뢰**: 보안 인증서로 사용자 신뢰도 향상

### SSL 인증서 종류
- **Domain Validated (DV)**: 도메인 소유권만 확인
- **Organization Validated (OV)**: 조직 정보도 확인
- **Extended Validation (EV)**: 가장 엄격한 검증 과정
- **Wildcard**: 서브도메인 모두 포함
- **Multi-Domain**: 여러 도메인을 하나의 인증서로 관리

## 핵심

### SSL 인증서 발급 및 설치

#### Let's Encrypt를 통한 무료 SSL 인증서 발급
```bash
# Certbot 설치
sudo apt update
sudo apt install certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d example.com -d www.example.com

# 인증서 자동 갱신 설정
sudo crontab -e
# 다음 줄 추가: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 수동 SSL 인증서 설치
```bash
# SSL 인증서 디렉토리 생성
sudo mkdir -p /etc/nginx/ssl

# 인증서 파일 복사
sudo cp example.com.crt /etc/nginx/ssl/
sudo cp example.com.key /etc/nginx/ssl/

# 권한 설정
sudo chmod 600 /etc/nginx/ssl/example.com.key
sudo chmod 644 /etc/nginx/ssl/example.com.crt
```

### 기본 Nginx SSL 설정

#### 기본 HTTPS 서버 설정
```nginx
# HTTP를 HTTPS로 리다이렉트
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://$host$request_uri;
}

# HTTPS 서버 설정
server {
    listen 443 ssl http2;
    server_name example.com www.example.com;

    # SSL 인증서 설정
    ssl_certificate /etc/nginx/ssl/example.com.crt;
    ssl_certificate_key /etc/nginx/ssl/example.com.key;

    # SSL 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

    # SSL 세션 설정
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # HSTS 설정
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 보안 헤더 설정
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 예시

### 고급 SSL 설정

#### 보안 강화된 SSL 설정
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

#### 멀티 도메인 SSL 설정
```nginx
# 메인 도메인
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/nginx/ssl/example.com.crt;
    ssl_certificate_key /etc/nginx/ssl/example.com.key;

    include /etc/nginx/conf.d/ssl.conf;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# 서브도메인
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/nginx/ssl/example.com.crt;
    ssl_certificate_key /etc/nginx/ssl/example.com.key;

    include /etc/nginx/conf.d/ssl.conf;

    location / {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL 자동화 스크립트

#### SSL 인증서 자동 갱신 스크립트
```bash
#!/bin/bash
# /usr/local/bin/ssl-renew.sh

# 로그 파일 설정
LOG_FILE="/var/log/ssl-renew.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] SSL 인증서 갱신 시작" >> $LOG_FILE

# Certbot을 통한 인증서 갱신
if certbot renew --quiet; then
    echo "[$DATE] SSL 인증서 갱신 성공" >> $LOG_FILE
    
    # Nginx 설정 테스트
    if nginx -t; then
        echo "[$DATE] Nginx 설정 테스트 성공" >> $LOG_FILE
        
        # Nginx 재시작
        if systemctl reload nginx; then
            echo "[$DATE] Nginx 재시작 성공" >> $LOG_FILE
        else
            echo "[$DATE] Nginx 재시작 실패" >> $LOG_FILE
        fi
    else
        echo "[$DATE] Nginx 설정 테스트 실패" >> $LOG_FILE
    fi
else
    echo "[$DATE] SSL 인증서 갱신 실패" >> $LOG_FILE
fi
```

#### SSL 상태 모니터링 스크립트
```bash
#!/bin/bash
# /usr/local/bin/ssl-monitor.sh

# 모니터링할 도메인 목록
DOMAINS=("example.com" "api.example.com")

for domain in "${DOMAINS[@]}"; do
    # SSL 인증서 만료일 확인
    expiry_date=$(echo | openssl s_client -servername $domain -connect $domain:443 2>/dev/null | openssl x509 -noout -dates | grep notAfter | cut -d= -f2)
    
    if [ ! -z "$expiry_date" ]; then
        # 만료일을 Unix timestamp로 변환
        expiry_timestamp=$(date -d "$expiry_date" +%s)
        current_timestamp=$(date +%s)
        
        # 30일 이내 만료되는지 확인
        days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
        
        if [ $days_until_expiry -le 30 ]; then
            echo "경고: $domain SSL 인증서가 $days_until_expiry일 후 만료됩니다."
            # 이메일 알림 또는 슬랙 알림 발송
        fi
    else
        echo "오류: $domain SSL 인증서 정보를 가져올 수 없습니다."
    fi
done
```

## 운영 팁

### SSL 성능 최적화

#### SSL 설정 최적화
```nginx
# /etc/nginx/conf.d/ssl-optimization.conf

# SSL 세션 캐시 최적화
ssl_session_cache shared:SSL:50m;
ssl_session_timeout 1d;
ssl_session_tickets off;

# DH 파라미터 생성 (한 번만 실행)
# openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048
ssl_dhparam /etc/nginx/ssl/dhparam.pem;

# OCSP Stapling 활성화
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# HTTP/2 활성화
listen 443 ssl http2;

# SSL 버퍼 크기 최적화
ssl_buffer_size 4k;
```

#### SSL 성능 모니터링
```javascript
// ssl-monitor.js
const https = require('https');
const fs = require('fs');

class SSLMonitor {
    constructor() {
        this.domains = [
            'example.com',
            'api.example.com'
        ];
        this.results = [];
    }

    // SSL 인증서 정보 확인
    checkSSLCertificate(domain) {
        return new Promise((resolve, reject) => {
            const options = {
                hostname: domain,
                port: 443,
                method: 'GET',
                rejectUnauthorized: false
            };

            const req = https.request(options, (res) => {
                const cert = res.socket.getPeerCertificate();
                
                const result = {
                    domain: domain,
                    subject: cert.subject,
                    issuer: cert.issuer,
                    validFrom: new Date(cert.valid_from),
                    validTo: new Date(cert.valid_to),
                    daysUntilExpiry: Math.ceil((new Date(cert.valid_to) - new Date()) / (1000 * 60 * 60 * 24)),
                    protocol: res.socket.getProtocol(),
                    cipher: res.socket.getCipher()
                };

                resolve(result);
            });

            req.on('error', (error) => {
                reject({
                    domain: domain,
                    error: error.message
                });
            });

            req.end();
        });
    }

    // 모든 도메인 SSL 상태 확인
    async checkAllDomains() {
        const promises = this.domains.map(domain => 
            this.checkSSLCertificate(domain).catch(error => error)
        );

        this.results = await Promise.all(promises);
        return this.results;
    }

    // 결과 리포트 생성
    generateReport() {
        const report = {
            timestamp: new Date().toISOString(),
            totalDomains: this.domains.length,
            successfulChecks: this.results.filter(r => !r.error).length,
            failedChecks: this.results.filter(r => r.error).length,
            expiringSoon: this.results.filter(r => !r.error && r.daysUntilExpiry <= 30),
            details: this.results
        };

        return report;
    }

    // 결과를 파일로 저장
    saveReport(filename = 'ssl-report.json') {
        const report = this.generateReport();
        fs.writeFileSync(filename, JSON.stringify(report, null, 2));
        console.log(`SSL 리포트가 ${filename}에 저장되었습니다.`);
    }
}

// 사용 예시
const monitor = new SSLMonitor();

async function runSSLMonitoring() {
    await monitor.checkAllDomains();
    const report = monitor.generateReport();
    
    console.log('SSL 모니터링 리포트:');
    console.log(JSON.stringify(report, null, 2));
    
    monitor.saveReport();
}

runSSLMonitoring();
```

### SSL 보안 강화

#### 보안 헤더 설정
```nginx
# /etc/nginx/conf.d/security-headers.conf

# HSTS (HTTP Strict Transport Security)
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

# X-Frame-Options (클릭재킹 방지)
add_header X-Frame-Options "SAMEORIGIN" always;

# X-XSS-Protection (XSS 방지)
add_header X-XSS-Protection "1; mode=block" always;

# X-Content-Type-Options (MIME 스니핑 방지)
add_header X-Content-Type-Options "nosniff" always;

# Referrer-Policy (리퍼러 정보 제어)
add_header Referrer-Policy "no-referrer-when-downgrade" always;

# Content-Security-Policy (CSP)
add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data: https:;" always;

# Permissions-Policy (기능 정책)
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

#### SSL 취약점 방지
```nginx
# 취약한 SSL 프로토콜 비활성화
ssl_protocols TLSv1.2 TLSv1.3;

# 취약한 암호화 스위트 제외
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

# SSL 압축 비활성화 (CRIME 공격 방지)
ssl_compression off;

# SSL 세션 티켓 비활성화
ssl_session_tickets off;

# 재협상 비활성화
ssl_renegotiation off;
```

## 참고

### SSL 테스트 도구

#### 명령줄 도구
```bash
# SSL 인증서 정보 확인
openssl s_client -connect example.com:443 -servername example.com

# SSL 인증서 만료일 확인
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -dates

# SSL 프로토콜 지원 확인
nmap --script ssl-enum-ciphers -p 443 example.com

# SSL Labs 테스트 (온라인)
curl -s "https://api.ssllabs.com/api/v3/analyze?host=example.com"
```

#### SSL 설정 검증
```bash
# Nginx 설정 문법 검사
nginx -t

# SSL 설정 테스트
openssl s_client -connect example.com:443 -servername example.com -cipher ECDHE-RSA-AES128-GCM-SHA256

# HTTP/2 지원 확인
curl -I --http2 https://example.com
```

### SSL 인증서 관리

#### 인증서 백업 및 복원
```bash
#!/bin/bash
# /usr/local/bin/ssl-backup.sh

BACKUP_DIR="/backup/ssl"
DATE=$(date +%Y%m%d_%H%M%S)

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# SSL 인증서 백업
tar -czf $BACKUP_DIR/ssl_backup_$DATE.tar.gz \
    /etc/nginx/ssl/ \
    /etc/letsencrypt/ \
    /etc/nginx/sites-available/ \
    /etc/nginx/sites-enabled/

echo "SSL 백업 완료: $BACKUP_DIR/ssl_backup_$DATE.tar.gz"
```

### 결론
Nginx SSL 설정은 웹사이트 보안의 핵심 요소입니다.
적절한 SSL 설정으로 데이터 암호화, 신원 인증, 데이터 무결성을 보장할 수 있습니다.
정기적인 인증서 갱신과 모니터링으로 서비스 중단을 방지할 수 있습니다.
보안 헤더와 취약점 방지 설정으로 추가적인 보안을 강화할 수 있습니다.
성능 최적화를 통해 SSL 오버헤드를 최소화할 수 있습니다.

