---
title: Apache HTTP Server
tags: [webserver, apache, httpd, reverse-proxy, mod_rewrite, virtualhost]
updated: 2026-04-07
---

# Apache HTTP Server

## Apache란

Apache HTTP Server(이하 httpd)는 1995년부터 개발된 웹 서버다. 한때 전 세계 웹 서버 점유율 70%를 넘겼고, 지금도 레거시 시스템이나 공유 호스팅에서는 여전히 많이 쓰인다. Apache Software Foundation에서 관리하며 C로 작성됐다.

Nginx와 가장 큰 차이는 요청 처리 방식이다. Apache는 기본적으로 프로세스/스레드 기반(MPM)으로 동작하고, Nginx는 이벤트 루프 기반이다. 이 차이가 설정 방식, 성능 특성, 모듈 구조 전반에 영향을 준다.

## 설치

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install apache2

# 서비스 시작
sudo systemctl start apache2
sudo systemctl enable apache2

# 버전 확인
apache2 -v
```

### CentOS/RHEL

```bash
sudo yum install httpd

# 서비스 시작
sudo systemctl start httpd
sudo systemctl enable httpd

# 방화벽 허용
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### macOS (Homebrew)

```bash
brew install httpd

# 시작
brew services start httpd
```

macOS에는 시스템 Apache가 기본 설치되어 있는데, Homebrew로 별도 설치하는 게 관리하기 편하다. 시스템 Apache와 포트가 충돌할 수 있으니 `httpd.conf`에서 Listen 포트를 확인해야 한다.

## 설정 파일 구조

배포판마다 설정 파일 위치가 다르다. 이게 처음 접할 때 헷갈리는 부분이다.

| 배포판 | 메인 설정 | 사이트 설정 | 모듈 설정 |
|--------|----------|------------|----------|
| Ubuntu/Debian | `/etc/apache2/apache2.conf` | `/etc/apache2/sites-available/` | `/etc/apache2/mods-available/` |
| CentOS/RHEL | `/etc/httpd/conf/httpd.conf` | `/etc/httpd/conf.d/` | `/etc/httpd/conf.modules.d/` |

Ubuntu 계열은 `a2ensite`, `a2dissite`, `a2enmod`, `a2dismod` 같은 명령어로 사이트와 모듈을 활성화/비활성화한다. CentOS 계열은 설정 파일을 직접 넣고 빼야 한다.

```bash
# Ubuntu: 사이트 활성화/비활성화
sudo a2ensite mysite.conf
sudo a2dissite 000-default.conf

# 모듈 활성화/비활성화
sudo a2enmod rewrite
sudo a2enmod proxy proxy_http

# 설정 테스트
sudo apachectl configtest

# 재시작 (graceful)
sudo apachectl graceful
```

`apachectl configtest`는 반드시 재시작 전에 실행하는 습관을 들여야 한다. 설정 오류로 서비스가 내려가는 사고를 막을 수 있다.

## MPM (Multi-Processing Module)

Apache의 핵심이자 Nginx와 구분되는 부분이다. 요청을 어떤 방식으로 처리할지 결정하는 모듈인데, 세 가지가 있다.

### prefork

요청마다 별도의 프로세스를 fork해서 처리한다. 프로세스 간 메모리를 공유하지 않아서 안정적이지만 메모리를 많이 먹는다.

```apache
<IfModule mpm_prefork_module>
    StartServers             5
    MinSpareServers          5
    MaxSpareServers         10
    MaxRequestWorkers      256
    MaxConnectionsPerChild   0
</IfModule>
```

mod_php를 쓰려면 prefork를 써야 한다. PHP가 thread-safe하지 않은 라이브러리를 쓰는 경우가 많아서다. 레거시 PHP 애플리케이션을 운영한다면 사실상 선택지가 이것뿐이다.

`MaxRequestWorkers`가 256이면 동시에 256개 프로세스가 뜬다. 프로세스 하나당 메모리가 30~50MB 정도 잡히니까 단순 계산으로 8~13GB가 필요하다. 메모리가 부족하면 swap을 타면서 서버가 급격히 느려진다.

### worker

멀티 프로세스 + 멀티 스레드 방식이다. 프로세스 안에서 여러 스레드가 요청을 처리한다. prefork보다 메모리 효율이 좋다.

```apache
<IfModule mpm_worker_module>
    StartServers             3
    MinSpareThreads         75
    MaxSpareThreads        250
    ThreadsPerChild         25
    MaxRequestWorkers      400
    MaxConnectionsPerChild   0
</IfModule>
```

총 동시 처리 가능 수는 `StartServers × ThreadsPerChild`가 초기값이고, 최대 `MaxRequestWorkers`까지 늘어난다. mod_php를 쓸 수 없다는 제약이 있어서 PHP-FPM과 조합해야 한다.

### event

worker를 개선한 방식이다. Keep-Alive 연결을 별도 스레드가 관리해서 worker보다 동시 연결 처리가 낫다. Apache 2.4부터 기본 MPM이 됐고, 신규 구축이라면 event를 쓰는 게 맞다.

```apache
<IfModule mpm_event_module>
    StartServers             3
    MinSpareThreads         75
    MaxSpareThreads        250
    ThreadsPerChild         25
    MaxRequestWorkers      400
    MaxConnectionsPerChild   0
</IfModule>
```

설정 형태는 worker와 같다. 내부적으로 Keep-Alive 연결 처리 방식만 다르다.

### 현재 MPM 확인과 변경

```bash
# 현재 사용 중인 MPM 확인
apachectl -V | grep MPM

# Ubuntu에서 MPM 변경
sudo a2dismod mpm_prefork
sudo a2enmod mpm_event
sudo systemctl restart apache2
```

### Nginx와의 비교

Nginx는 단일 프로세스(worker process) 안에서 이벤트 루프로 수천 개 연결을 처리한다. Apache event MPM도 비슷한 방향이지만 구조적으로 Nginx만큼 가볍지는 않다.

정적 파일 서빙이나 리버스 프록시 용도로는 Nginx가 메모리, 동시 연결 처리 면에서 확실히 유리하다. Apache가 나은 경우는 .htaccess가 필요한 레거시 환경이거나, mod_php 같은 Apache 전용 모듈에 의존하는 경우다.

요즘 신규 프로젝트에서 Apache를 선택하는 경우는 거의 없다. 다만 기존 시스템 유지보수나 특정 모듈 의존성 때문에 써야 하는 상황은 자주 만난다.

## VirtualHost 설정

한 서버에서 여러 도메인을 운영할 때 쓴다. Nginx의 server 블록에 해당한다.

### 기본 VirtualHost

```apache
# /etc/apache2/sites-available/mysite.conf

<VirtualHost *:80>
    ServerName mysite.com
    ServerAlias www.mysite.com
    DocumentRoot /var/www/mysite

    <Directory /var/www/mysite>
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/mysite-error.log
    CustomLog ${APACHE_LOG_DIR}/mysite-access.log combined
</VirtualHost>
```

`AllowOverride All`은 .htaccess를 허용하겠다는 뜻이다. 성능에 영향을 주니까 뒤에서 따로 설명한다.

### HTTPS VirtualHost

```apache
<VirtualHost *:443>
    ServerName mysite.com
    DocumentRoot /var/www/mysite

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/mysite.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/mysite.com/privkey.pem

    # HTTP/2 활성화
    Protocols h2 http/1.1

    # 보안 헤더
    Header always set Strict-Transport-Security "max-age=63072000"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "DENY"

    <Directory /var/www/mysite>
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
```

### HTTP → HTTPS 리다이렉트

```apache
<VirtualHost *:80>
    ServerName mysite.com
    ServerAlias www.mysite.com
    Redirect permanent / https://mysite.com/
</VirtualHost>
```

`Redirect permanent`은 301 리다이렉트다. `mod_rewrite`로도 할 수 있는데 단순 리다이렉트는 `Redirect` 지시자가 더 깔끔하다.

## 주요 모듈

Apache의 기능 대부분은 모듈로 구현된다. 자주 쓰는 모듈을 정리한다.

### mod_rewrite

URL 재작성 모듈이다. 가장 많이 쓰이면서 동시에 디버깅이 까다로운 모듈이다.

```apache
# mod_rewrite 활성화
sudo a2enmod rewrite
```

```apache
<VirtualHost *:80>
    ServerName mysite.com
    DocumentRoot /var/www/mysite

    RewriteEngine On

    # www 제거
    RewriteCond %{HTTP_HOST} ^www\.mysite\.com$ [NC]
    RewriteRule ^(.*)$ http://mysite.com$1 [R=301,L]

    # 트레일링 슬래시 추가
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_URI} !(.*)/$
    RewriteRule ^(.*)$ $1/ [R=301,L]

    # 프론트 컨트롤러 패턴 (Laravel, WordPress 등)
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule ^(.*)$ /index.php [L,QSA]
</VirtualHost>
```

RewriteRule 디버깅이 어려울 때는 로그 레벨을 올려서 확인한다.

```apache
# 개발 환경에서만 사용. 프로덕션에서는 로그가 폭증한다.
LogLevel alert rewrite:trace6
```

RewriteCond와 RewriteRule의 실행 순서를 잘못 이해하면 무한 루프가 생긴다. `[L]` 플래그가 "이 규칙에서 멈춰라"가 아니라 "이번 회차에서 멈춰라"라는 의미라서, 재작성된 URL이 다시 RewriteRule을 타는 경우가 있다. `[END]` 플래그(Apache 2.3.9+)를 쓰면 완전히 멈출 수 있다.

### mod_proxy / mod_proxy_http

리버스 프록시 모듈이다. 백엔드 애플리케이션 서버(Tomcat, Node.js, Spring Boot 등) 앞에 Apache를 두는 구성에서 쓴다.

```bash
sudo a2enmod proxy proxy_http proxy_balancer lbmethod_byrequests
```

```apache
<VirtualHost *:80>
    ServerName api.mysite.com

    ProxyPreserveHost On
    ProxyPass / http://localhost:8080/
    ProxyPassReverse / http://localhost:8080/

    # 타임아웃 설정
    ProxyTimeout 60

    # 특정 경로만 프록시
    ProxyPass /api http://localhost:8080/api
    ProxyPassReverse /api http://localhost:8080/api

    # 정적 파일은 Apache가 직접 서빙
    ProxyPass /static !
    Alias /static /var/www/mysite/static
</VirtualHost>
```

`ProxyPreserveHost On`은 원본 Host 헤더를 백엔드로 전달한다. Spring Boot처럼 Host 헤더를 보고 동작하는 애플리케이션에서는 이 설정이 빠지면 문제가 생긴다.

### 로드 밸런싱

```apache
<Proxy balancer://backend>
    BalancerMember http://localhost:8080 route=node1
    BalancerMember http://localhost:8081 route=node2
    ProxySet stickysession=JSESSIONID
</Proxy>

<VirtualHost *:80>
    ServerName mysite.com
    ProxyPass / balancer://backend/
    ProxyPassReverse / balancer://backend/
</VirtualHost>
```

`stickysession`은 세션 기반 애플리케이션에서 같은 사용자를 같은 백엔드로 보내는 설정이다. JSESSIONID는 Tomcat/Spring에서 쓰는 세션 쿠키 이름이다.

### mod_ssl

SSL/TLS 처리 모듈이다. Let's Encrypt + certbot 조합이 가장 일반적이다.

```bash
sudo a2enmod ssl headers
sudo apt install certbot python3-certbot-apache

# 인증서 발급 (Apache 설정까지 자동으로 잡아준다)
sudo certbot --apache -d mysite.com -d www.mysite.com

# 갱신 테스트
sudo certbot renew --dry-run
```

certbot이 자동으로 VirtualHost를 수정하지만, 수동으로 SSL 설정을 튜닝하고 싶다면 아래처럼 한다.

```apache
# /etc/apache2/conf-available/ssl-params.conf

SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1
SSLCipherSuite ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
SSLHonorCipherOrder off
SSLSessionTickets off

SSLUseStapling On
SSLStaplingCache "shmcb:logs/ssl_stapling(32768)"
```

TLS 1.0과 1.1은 이미 대부분의 브라우저에서 지원이 끊겼다. TLS 1.2 이상만 허용하는 게 맞다. SSLv3는 POODLE 취약점 때문에 반드시 비활성화해야 한다.

### mod_security

웹 방화벽(WAF) 모듈이다. OWASP Core Rule Set과 함께 쓴다.

```bash
sudo apt install libapache2-mod-security2
sudo a2enmod security2
```

```apache
<IfModule security2_module>
    SecRuleEngine On
    SecRequestBodyAccess On
    SecResponseBodyAccess Off
    SecRequestBodyLimit 13107200

    # OWASP CRS 포함
    IncludeOptional /etc/modsecurity/crs/*.conf
</IfModule>
```

mod_security를 켜면 오탐(false positive)이 많다. 특히 파일 업로드, JSON API 호출에서 자주 걸린다. 처음에는 `SecRuleEngine DetectionOnly`로 감지 모드로 두고 로그를 보면서 예외 규칙을 만들어가는 게 현실적이다.

## .htaccess 성능 이슈

.htaccess는 디렉토리별 설정 파일이다. 파일 업로드 없이 설정을 변경할 수 있어서 공유 호스팅에서 많이 쓰인다. 문제는 성능이다.

Apache는 요청이 들어올 때마다 해당 경로의 모든 상위 디렉토리에서 .htaccess 파일을 찾는다. `/var/www/mysite/blog/2024/post.html` 요청이 들어오면 `/var/www/`, `/var/www/mysite/`, `/var/www/mysite/blog/`, `/var/www/mysite/blog/2024/` 순서로 .htaccess를 읽는다.

디스크 I/O가 매 요청마다 발생한다는 뜻이다. 트래픽이 많은 서비스에서는 체감할 수 있는 차이가 난다.

```apache
# .htaccess를 완전히 비활성화
<Directory /var/www>
    AllowOverride None
</Directory>
```

`AllowOverride None`으로 .htaccess를 비활성화하고, .htaccess에 있던 설정을 VirtualHost 설정 파일로 옮기는 게 낫다. 서버 설정 파일은 Apache 시작 시 한 번만 읽히니까 성능 차이가 없다.

WordPress나 Laravel처럼 .htaccess에 의존하는 프레임워크를 쓴다면, 해당 설정을 VirtualHost로 옮긴 뒤 .htaccess를 비활성화한다.

```apache
# WordPress의 .htaccess 내용을 VirtualHost로 옮긴 예시
<VirtualHost *:80>
    ServerName blog.mysite.com
    DocumentRoot /var/www/wordpress

    <Directory /var/www/wordpress>
        AllowOverride None
        Require all granted

        # WordPress 퍼머링크 (.htaccess에서 옮긴 것)
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.php$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.php [L]
    </Directory>
</VirtualHost>
```

## 리버스 프록시 설정

Spring Boot, Node.js 같은 애플리케이션 서버 앞에 Apache를 두는 구성이다.

### Spring Boot + Apache

```apache
<VirtualHost *:443>
    ServerName api.mysite.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/api.mysite.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/api.mysite.com/privkey.pem

    ProxyPreserveHost On

    # WebSocket 지원
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) ws://localhost:8080/$1 [P,L]

    ProxyPass / http://localhost:8080/
    ProxyPassReverse / http://localhost:8080/

    # 백엔드가 죽었을 때 사용자에게 보여줄 에러 페이지
    ProxyErrorOverride On
    ErrorDocument 503 /maintenance.html
</VirtualHost>
```

### 헤더 전달

리버스 프록시 뒤의 애플리케이션은 클라이언트 IP를 알 수 없다. 헤더로 전달해야 한다.

```apache
RequestHeader set X-Forwarded-For "%{REMOTE_ADDR}s"
RequestHeader set X-Forwarded-Proto "https"
RequestHeader set X-Real-IP "%{REMOTE_ADDR}s"
```

Spring Boot에서는 `application.yml`에 아래 설정을 추가해야 한다.

```yaml
server:
  forward-headers-strategy: framework
```

이 설정이 빠지면 `request.getRemoteAddr()`가 항상 `127.0.0.1`을 반환한다. 로그에서 클라이언트 IP를 추적할 수 없게 되니 반드시 확인해야 한다.

## 로그 분석과 트러블슈팅

### 로그 위치와 형식

```bash
# Ubuntu
/var/log/apache2/access.log
/var/log/apache2/error.log

# CentOS
/var/log/httpd/access_log
/var/log/httpd/error_log
```

### 커스텀 로그 형식

```apache
# JSON 형태 로그 (ELK 스택 연동 시 파싱이 편하다)
LogFormat "{\"time\":\"%{%Y-%m-%dT%H:%M:%S}t\",\"remote_ip\":\"%a\",\"method\":\"%m\",\"uri\":\"%U\",\"status\":%>s,\"size\":%B,\"referer\":\"%{Referer}i\",\"user_agent\":\"%{User-Agent}i\",\"duration\":%D}" json_log

CustomLog ${APACHE_LOG_DIR}/access.json json_log
```

`%D`는 마이크로초 단위 응답 시간이다. 느린 요청을 추적할 때 유용하다. `%T`는 초 단위인데, 밀리초 이하 응답은 0으로 찍혀서 `%D`를 쓰는 게 낫다.

### 자주 겪는 문제들

**403 Forbidden**

가장 흔한 원인은 디렉토리 권한이다.

```bash
# 디렉토리 권한 확인
namei -l /var/www/mysite/index.html

# 일반적인 권한 설정
sudo chown -R www-data:www-data /var/www/mysite
sudo find /var/www/mysite -type d -exec chmod 755 {} \;
sudo find /var/www/mysite -type f -exec chmod 644 {} \;
```

`<Directory>` 블록에 `Require all granted`가 빠져 있어도 403이 뜬다. Apache 2.4에서 권한 체계가 바뀌었는데, 2.2 시절 설정을 그대로 쓰면 이 문제가 생긴다.

```apache
# Apache 2.2 (이제 안 된다)
Order allow,deny
Allow from all

# Apache 2.4
Require all granted
```

**502 Bad Gateway (리버스 프록시)**

백엔드가 응답하지 않을 때 발생한다. 확인 순서:

1. 백엔드 서비스가 실행 중인지 확인: `curl -v http://localhost:8080`
2. SELinux가 켜져 있으면 네트워크 연결을 차단할 수 있다: `sudo setsebool -P httpd_can_network_connect 1`
3. 방화벽 규칙 확인
4. ProxyPass 경로에 슬래시가 맞는지 확인 — `/api`와 `/api/`는 다르다

SELinux 관련 문제는 CentOS/RHEL에서 자주 만난다. `audit.log`를 확인하면 SELinux가 차단한 로그를 볼 수 있다.

```bash
sudo ausearch -m avc -ts recent
```

**AH00558: Could not reliably determine the server's fully qualified domain name**

Apache 시작 시 나오는 경고다. 동작에는 문제없지만 없애려면 `ServerName`을 설정한다.

```apache
# /etc/apache2/conf-available/servername.conf
ServerName localhost
```

```bash
sudo a2enconf servername
sudo apachectl graceful
```

### 상태 모니터링

```apache
<Location /server-status>
    SetHandler server-status
    Require ip 10.0.0.0/8
    Require ip 127.0.0.1
</Location>

# 확장 상태 정보 (CPU 사용량, 요청별 상세 정보)
ExtendedStatus On
```

`/server-status`는 현재 연결 수, 각 워커의 상태, 요청 처리 현황을 보여준다. 프로덕션에서는 반드시 접근 제한을 걸어야 한다. Prometheus의 `apache_exporter`와 연동하면 모니터링 대시보드를 만들 수 있다.

## 성능 튜닝 참고사항

Apache 성능이 문제가 되는 경우 확인할 것들이다.

```apache
# KeepAlive 설정
KeepAlive On
MaxKeepAliveRequests 100
KeepAliveTimeout 5
```

`KeepAliveTimeout`을 너무 높게 잡으면 유휴 연결이 워커를 점유한다. 기본값 5초 정도가 적당하고, API 서버라면 2~3초로 줄여도 된다.

MPM 설정에서 `MaxRequestWorkers`는 서버 메모리를 기준으로 계산한다. 프로세스당 메모리 사용량을 확인하고 나서 조정해야 한다.

```bash
# Apache 프로세스별 메모리 확인
ps aux | grep apache2 | awk '{sum+=$6; n++} END {print "Average:", sum/n/1024, "MB"}'
```

평균 프로세스 메모리가 40MB이고 서버에 4GB 여유가 있다면, `MaxRequestWorkers`는 100 정도가 상한선이다. OS와 다른 프로세스가 쓸 메모리를 남겨둬야 한다.

`.htaccess` 비활성화, 불필요한 모듈 비활성화, `Options -Indexes`(디렉토리 리스팅 비활성화)는 기본으로 해두는 것이 좋다.
