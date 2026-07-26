---
title: Nginx FastCGI & PHP-FPM
tags: [nginx, fastcgi, php-fpm, uwsgi, fastcgi_cache, fastcgi_params, PATH_INFO, socket, tcp]
updated: 2026-07-26
---

# Nginx FastCGI & PHP-FPM

Nginx는 PHP를 직접 실행하지 못한다. FastCGI 프로토콜로 PHP-FPM에 요청을 위임하고, PHP-FPM이 처리한 결과를 받아 클라이언트에 돌려준다. 이 위임 과정에서 설정을 잘못 잡으면 퍼포먼스 문제나 `502 Bad Gateway`가 반복적으로 발생한다.

## 소켓 방식 vs TCP 방식

PHP-FPM과 Nginx를 연결하는 방법은 Unix 도메인 소켓과 TCP 소켓 두 가지다.

**Unix 도메인 소켓 (`fastcgi_pass unix:/run/php/php8.2-fpm.sock`)**

파일 시스템 소켓 파일을 통해 통신한다. 같은 서버에서 Nginx와 PHP-FPM이 함께 돌아갈 때 쓴다. 네트워크 스택을 거치지 않으므로 레이턴시가 낮고 컨텍스트 스위치 비용도 작다. 초당 요청 수가 많을수록 TCP 대비 차이가 벌어진다.

단점은 소켓 파일 권한 문제가 자주 생긴다는 점이다. Nginx 프로세스(보통 `www-data` 또는 `nginx` 유저)가 소켓 파일에 읽기/쓰기 권한이 없으면 바로 `502`가 난다. PHP-FPM pool 설정의 `listen.owner`, `listen.group`, `listen.mode`를 Nginx 유저에 맞춰야 한다.

**TCP 소켓 (`fastcgi_pass 127.0.0.1:9000`)**

PHP-FPM이 다른 서버에 있거나 컨테이너로 분리된 경우에 쓴다. Docker 환경에서 Nginx 컨테이너와 PHP-FPM 컨테이너를 분리하면 Unix 소켓을 공유할 수 없으므로 TCP로 연결한다. 오버헤드가 있지만 확장할 때 편하다.

```nginx
# Unix 소켓
location ~ \.php$ {
    fastcgi_pass unix:/run/php/php8.2-fpm.sock;
}

# TCP 소켓
location ~ \.php$ {
    fastcgi_pass 127.0.0.1:9000;
}

# 컨테이너 환경 (서비스명 사용)
location ~ \.php$ {
    fastcgi_pass php-fpm:9000;
}
```

성능 우선이면 Unix 소켓, 구조적 분리나 확장이 필요하면 TCP다. 같은 호스트에서 돌리면서 TCP를 쓸 이유는 없다.

## fastcgi_pass 기본 설정

PHP 파일 요청을 처리하는 기본 블록이다.

```nginx
server {
    listen 80;
    server_name example.com;
    root /var/www/html;
    index index.php index.html;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        try_files $uri =404;
        fastcgi_pass unix:/run/php/php8.2-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }
}
```

`try_files $uri =404` 부분이 중요하다. 실제로 존재하는 PHP 파일만 FastCGI로 넘기기 위한 장치다. 이 줄이 없으면 `/non-existent-path`로 요청이 들어와도 PHP-FPM에 전달되어 처리되거나 오류가 생긴다. 보안 취약점으로 이어질 수 있다.

`SCRIPT_FILENAME`은 PHP-FPM이 어떤 파일을 실행할지 알려주는 파라미터다. `$document_root$fastcgi_script_name`으로 조합하거나 `$realpath_root$fastcgi_script_name`을 쓰는 경우도 있다. 심볼릭 링크를 쓰는 환경이라면 `$realpath_root`가 실제 경로를 해석해서 더 정확하다.

## fastcgi_params와 SCRIPT_FILENAME

`/etc/nginx/fastcgi_params` 파일에는 CGI 표준에서 정의하는 기본 환경 변수들이 들어있다. 이 파일을 `include`하면 `QUERY_STRING`, `REQUEST_METHOD`, `CONTENT_TYPE`, `CONTENT_LENGTH`, `SCRIPT_NAME`, `REQUEST_URI`, `DOCUMENT_URI`, `SERVER_NAME`, `SERVER_PORT` 등이 PHP-FPM으로 넘어간다.

눈여겨볼 점은 `SCRIPT_FILENAME`이 `fastcgi_params`에 없다는 것이다. PHP가 실행할 파일 경로를 직접 지정해줘야 한다.

```nginx
include fastcgi_params;
fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
```

`/etc/nginx/fastcgi.conf`라는 파일도 있다. 이 파일은 `fastcgi_params`에 `SCRIPT_FILENAME`까지 포함한 버전이다. 두 파일 중 하나만 쓰면 된다. `fastcgi_params`를 `include`하고 `SCRIPT_FILENAME`을 따로 추가하거나, `fastcgi.conf`를 `include`하거나, 둘 중 하나다. 둘 다 include하면 `SCRIPT_FILENAME`이 중복 선언된다.

## fastcgi_split_path_info와 PATH_INFO 처리

`PATH_INFO`는 PHP 스크립트 파일명 뒤에 붙는 경로 정보다. `/index.php/api/users`처럼 요청이 들어오면 `/index.php`가 스크립트, `/api/users`가 PATH_INFO가 된다. CodeIgniter, Slim 같은 프레임워크가 URL 라우팅에 이 방식을 쓰기도 한다.

```nginx
location ~ ^(.+\.php)(/.*)$ {
    fastcgi_pass unix:/run/php/php8.2-fpm.sock;
    fastcgi_split_path_info ^(.+\.php)(/.+)$;

    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    fastcgi_param PATH_INFO $fastcgi_path_info;
    fastcgi_param PATH_TRANSLATED $document_root$fastcgi_path_info;
}
```

`fastcgi_split_path_info`에 지정한 정규식의 첫 번째 캡처 그룹이 `$fastcgi_script_name`에, 두 번째 캡처 그룹이 `$fastcgi_path_info`에 들어간다. location 정규식도 `.php` 이후 경로를 허용하도록 `^(.+\.php)(/.*)?$` 형태로 잡아야 한다.

이 설정에서 흔히 생기는 문제가 있다. `/images/photo.jpg/index.php` 같은 요청이 들어오면 `photo.jpg`가 실제로 존재하더라도 `index.php`가 `SCRIPT_FILENAME`으로 설정되어 PHP-FPM에 전달된다. Nginx가 `.php`를 찾을 때 경로 전체를 탐색하기 때문이다. 이걸 막으려면 `cgi.fix_pathinfo=0`을 `php.ini`에 설정하고, location에서 파일 존재 여부를 먼저 확인해야 한다.

## uWSGI 연동

Python 애플리케이션을 배포할 때 uWSGI를 FastCGI 대신 쓰는 경우가 많다. Nginx는 `uwsgi_pass`를 별도로 지원한다.

```nginx
location / {
    uwsgi_pass unix:/run/uwsgi/app.sock;
    include uwsgi_params;
}
```

`uwsgi_params` 파일은 `/etc/nginx/uwsgi_params`에 있다. FastCGI와 마찬가지로 include해서 쓴다.

uWSGI를 TCP로 연결할 경우에는 다음처럼 쓴다.

```nginx
location / {
    uwsgi_pass 127.0.0.1:8001;
    include uwsgi_params;
}
```

uWSGI는 HTTP 모드와 uwsgi 프로토콜 모드 두 가지로 실행할 수 있다. HTTP 모드로 띄웠다면 `uwsgi_pass` 대신 `proxy_pass`를 써야 한다. 혼용하면 Nginx가 응답을 파싱하지 못해 502가 반복된다.

```ini
# uWSGI ini 설정
[uwsgi]
socket = /run/uwsgi/app.sock
chmod-socket = 660
module = myapp:application
processes = 4
threads = 2
```

```nginx
# socket 모드 → uwsgi_pass
location / {
    uwsgi_pass unix:/run/uwsgi/app.sock;
    include uwsgi_params;
}
```

```ini
# HTTP 모드
[uwsgi]
http = :8001
module = myapp:application
```

```nginx
# http 모드 → proxy_pass
location / {
    proxy_pass http://127.0.0.1:8001;
}
```

## fastcgi_cache 설정

PHP-FPM의 응답을 Nginx에서 캐시할 수 있다. 동적 페이지지만 내용이 자주 바뀌지 않는 경우, DB 부하를 줄이기 위해 쓴다.

캐시 저장소를 먼저 `http` 블록에 정의한다.

```nginx
http {
    fastcgi_cache_path /var/cache/nginx/fastcgi
        levels=1:2
        keys_zone=php_cache:10m
        max_size=1g
        inactive=60m
        use_temp_path=off;

    fastcgi_cache_key "$scheme$request_method$host$request_uri";
}
```

`levels=1:2`는 캐시 파일을 디렉토리 계층으로 분산 저장하는 설정이다. 파일이 많아지면 한 디렉토리에 몰리는 것보다 성능이 낫다. `keys_zone=php_cache:10m`에서 `10m`은 캐시 키 인덱스를 저장하는 공유 메모리 크기다. 캐시 파일 자체의 크기가 아니라 키 목록 크기다. `max_size`가 실제 캐시 용량 상한이다.

```nginx
location ~ \.php$ {
    fastcgi_pass unix:/run/php/php8.2-fpm.sock;
    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;

    fastcgi_cache php_cache;
    fastcgi_cache_valid 200 301 302 10m;
    fastcgi_cache_valid 404 1m;
    fastcgi_cache_use_stale error timeout updating invalid_header http_500;
    fastcgi_cache_lock on;

    add_header X-FastCGI-Cache $upstream_cache_status;
}
```

`fastcgi_cache_use_stale`에 `updating`을 추가하면 캐시가 만료되어 재생성 중일 때 구 버전 캐시를 돌려준다. 캐시 갱신 중 트래픽이 몰리면 동시에 여러 요청이 PHP-FPM을 때릴 수 있는데, `fastcgi_cache_lock on`이 이를 막는다. 첫 번째 요청만 PHP-FPM에 보내고 나머지는 그 결과를 기다린다.

`X-FastCGI-Cache` 헤더를 응답에 추가하면 `HIT`, `MISS`, `BYPASS`, `EXPIRED` 중 어떤 상태인지 확인할 수 있어서 디버깅에 유용하다.

로그인한 사용자나 쿠키가 있는 요청은 캐시에서 제외해야 할 때가 있다.

```nginx
# http 블록
map $http_cookie $no_cache {
    default 0;
    ~PHPSESSID 1;
    ~wordpress_logged_in 1;
}

# server 블록
location ~ \.php$ {
    fastcgi_pass unix:/run/php/php8.2-fpm.sock;
    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;

    fastcgi_cache php_cache;
    fastcgi_cache_valid 200 10m;
    fastcgi_no_cache $no_cache;
    fastcgi_cache_bypass $no_cache;
}
```

POST 요청도 자동으로 캐시에서 제외된다. `fastcgi_cache_methods`를 명시하지 않으면 기본값이 `GET HEAD`다.

## PHP-FPM 프로세스 수와 Nginx 설정의 관계

PHP-FPM 프로세스 관리 방식은 `static`, `dynamic`, `ondemand` 세 가지다.

`pm = dynamic`일 때 핵심 파라미터는 `pm.max_children`이다. PHP-FPM이 동시에 처리할 수 있는 최대 요청 수가 이 값으로 결정된다. Nginx의 `worker_connections`와 `worker_processes`로 계산되는 최대 동시 연결 수가 아무리 커도, PHP-FPM의 `pm.max_children`을 넘는 PHP 요청은 큐에서 대기한다.

대기 큐가 가득 차면 PHP-FPM은 새 연결을 거부한다. Nginx가 `fastcgi_pass`로 요청을 보낼 때 연결이 안 되면 `502 Bad Gateway`가 발생한다.

```ini
; PHP-FPM pool 설정 (/etc/php/8.2/fpm/pool.d/www.conf)
pm = dynamic
pm.max_children = 50
pm.start_servers = 10
pm.min_spare_servers = 5
pm.max_spare_servers = 20
pm.max_requests = 500
```

`pm.max_requests = 500`은 각 워커가 500개 요청을 처리한 뒤 재시작하도록 한다. PHP 프로세스에 메모리 누수가 있는 경우 이 값으로 누수 영향을 제한한다.

`pm.max_children`을 적정 값으로 잡는 기준은 서버 메모리다. PHP 프로세스 하나가 평균 몇 MB를 쓰는지 실측한 뒤 가용 메모리를 나누면 된다.

```bash
# PHP-FPM 프로세스 메모리 사용량 확인
ps --no-headers -o "rss,cmd" -C php-fpm8.2 | awk '{sum+=$1} END {print sum/NR/1024 " MB per process"}'
```

예를 들어 프로세스 하나가 평균 40MB를 쓰고 서버 가용 메모리가 2GB라면 `pm.max_children`을 40~45 정도로 잡는다. 실제로는 다른 프로세스도 메모리를 쓰므로 여유를 두는 것이 좋다.

Nginx 쪽에서는 `fastcgi_read_timeout`과 `fastcgi_connect_timeout`을 조정하는 경우가 있다.

```nginx
location ~ \.php$ {
    fastcgi_pass unix:/run/php/php8.2-fpm.sock;
    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;

    fastcgi_connect_timeout 60s;
    fastcgi_send_timeout 60s;
    fastcgi_read_timeout 120s;

    fastcgi_buffer_size 128k;
    fastcgi_buffers 4 256k;
    fastcgi_busy_buffers_size 256k;
}
```

`fastcgi_read_timeout`은 PHP-FPM으로부터 응답이 오기까지 Nginx가 기다리는 시간이다. 기본값은 60초다. PHP에서 오래 걸리는 작업(보고서 생성, 대용량 파일 처리 등)을 처리한다면 이 값을 늘려야 한다. 늘리지 않으면 PHP가 아직 처리 중인데 Nginx가 먼저 포기하고 `504 Gateway Timeout`을 낸다.

`fastcgi_buffers`는 PHP-FPM 응답을 Nginx가 메모리에 버퍼링하는 크기다. 응답이 버퍼보다 크면 디스크에 임시 파일로 쓴다. 응답 크기가 일정하다면 버퍼를 응답 크기에 맞게 조정하는 것이 낫다.

## 트러블슈팅 포인트

**502 Bad Gateway**가 반복된다면 PHP-FPM이 살아있는지, 소켓 파일이 존재하는지, 권한 문제는 없는지 순서대로 확인한다.

```bash
# PHP-FPM 상태 확인
systemctl status php8.2-fpm

# 소켓 파일 확인
ls -la /run/php/php8.2-fpm.sock

# Nginx 에러 로그
tail -f /var/log/nginx/error.log
```

**PHP-FPM 상태 페이지**를 활성화하면 현재 워커 상태를 실시간으로 볼 수 있다.

```ini
; PHP-FPM pool 설정
pm.status_path = /status
pm.status_listen = /run/php/php8.2-fpm-status.sock
```

```nginx
location ~ ^/(status|ping)$ {
    allow 127.0.0.1;
    deny all;
    fastcgi_pass unix:/run/php/php8.2-fpm.sock;
    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $fastcgi_script_name;
}
```

`/status?full`로 요청하면 현재 처리 중인 요청과 각 워커가 무엇을 하는지까지 보인다. 503이 반복되거나 응답이 느려질 때 `pm.max_children`을 늘려야 하는지 판단하는 데 쓴다.
