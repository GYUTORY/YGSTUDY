# NginX (엔진 엑스) 완벽 가이드

## 목차
1. [웹서버의 이해](#웹서버의-이해)
2. [Nginx 소개](#nginx-소개)
3. [Nginx의 등장 배경](#nginx의-등장-배경)
4. [Nginx의 구조와 작동 방식](#nginx의-구조와-작동-방식)
5. [Nginx의 주요 기능](#nginx의-주요-기능)
6. [Nginx vs Apache 상세 비교](#nginx-vs-apache-상세-비교)
7. [Nginx 설정 가이드](#nginx-설정-가이드)
8. [실제 사용 사례](#실제-사용-사례)

## 웹서버의 이해

### 웹서버란?
웹서버는 HTTP 프로토콜을 통해 클라이언트의 요청을 처리하고 응답을 제공하는 서버입니다. 웹서버의 주요 역할은 다음과 같습니다:

1. **정적 컨텐츠 제공**
   - HTML, CSS, JavaScript 파일
   - 이미지, 비디오 등 미디어 파일
   - 문서 파일 (PDF, DOC 등)

2. **동적 컨텐츠 처리**
   - PHP, Python, Node.js 등과 연동
   - 데이터베이스 연동
   - API 요청 처리

3. **보안 기능**
   - SSL/TLS 암호화
   - 접근 제어
   - 인증 및 인가

4. **성능 최적화**
   - 캐싱
   - 압축
   - 로드 밸런싱

### 주요 웹서버 종류
1. **Apache**
   - 가장 오래된 웹서버
   - 모듈식 구조
   - .htaccess 지원
   - 전 세계 웹사이트의 약 31% 사용

2. **Nginx**
   - 고성능 웹서버
   - 이벤트 기반 구조
   - 전 세계 웹사이트의 약 33% 사용

3. **Microsoft IIS**
   - Windows 서버용 웹서버
   - ASP.NET 지원
   - Windows 환경에 최적화

## Nginx 소개

### Nginx란?
Nginx는 2004년 Igor Sysoev가 개발한 고성능 웹서버입니다. 현재 전 세계 웹사이트의 약 33%가 Nginx를 사용하고 있으며, 특히 대규모 트래픽을 처리해야 하는 사이트에서 선호됩니다.

### Nginx의 주요 특징
1. **이벤트 기반 비동기 처리**
   - 단일 프로세스로 수천 개의 동시 연결 처리
   - 낮은 메모리 사용량
   - 높은 처리량

2. **모듈식 아키텍처**
   - 필요한 기능만 선택적 사용
   - 확장성 우수
   - 유지보수 용이

3. **다양한 기능**
   - 리버스 프록시
   - 로드 밸런싱
   - 캐싱
   - SSL/TLS 지원

### Web Server vs WAS
1. **Web Server (Nginx, Apache)**
   - 정적 컨텐츠 처리
   - HTTP 요청 처리
   - SSL/TLS 처리
   - 캐싱
   - 리버스 프록시

2. **WAS (Web Application Server)**
   - 동적 컨텐츠 처리
   - 비즈니스 로직 실행
   - 데이터베이스 연동
   - 세션 관리
   - 트랜잭션 처리

## Nginx의 등장 배경

### Apache의 한계
1. **Connection 10000 Problem**
   - 동시 접속자 수 증가로 인한 성능 저하
   - 프로세스/스레드 기반 구조의 한계
   - 메모리 사용량 증가

2. **리소스 관리 문제**
   - 각 연결마다 프로세스/스레드 생성
   - 높은 메모리 사용량
   - CPU 부하 증가

3. **확장성 문제**
   - 수직적 확장에 의존
   - 하드웨어 리소스 증가 필요
   - 비용 증가

### Nginx의 해결책
1. **이벤트 기반 아키텍처**
   - 비동기 처리
   - 효율적인 리소스 사용
   - 높은 동시성 지원

2. **경량화된 구조**
   - 낮은 메모리 사용량
   - 빠른 처리 속도
   - 효율적인 CPU 사용

## Nginx의 구조와 작동 방식

### 프로세스 구조
1. **Master Process**
   - 설정 파일 읽기
   - Worker Process 관리
   - 로그 관리
   - 설정 리로드

2. **Worker Process**
   - 실제 요청 처리
   - 이벤트 처리
   - CPU 코어 수에 맞춰 생성

### 이벤트 처리 방식
1. **이벤트 루프**
   - 비동기 이벤트 처리
   - 효율적인 리소스 사용
   - 높은 처리량

2. **연결 처리**
   - Keep-Alive 연결 관리
   - 효율적인 연결 재사용
   - 낮은 오버헤드

## Nginx의 주요 기능

### 1. 리버스 프록시
- 클라이언트와 백엔드 서버 사이 중개자 역할
- 보안 강화
- 로드 밸런싱
- SSL/TLS 종료
- 캐싱

### 2. 로드 밸런싱
- 라운드 로빈
- 최소 연결
- IP 해시
- 가중치 기반
- 상태 확인

### 3. 캐싱
- 정적 컨텐츠 캐싱
- 프록시 캐싱
- FastCGI 캐싱
- 메모리 캐싱

### 4. 보안 기능
- SSL/TLS 지원
- 접근 제어
- 요청 필터링
- DDoS 방어

## Nginx vs Apache 상세 비교

### 1. 아키텍처 비교
#### Apache
- MPM (Multi-Processing Module) 기반
- 프로세스/스레드 기반 처리
- 모듈식 구조
- .htaccess 지원

#### Nginx
- 이벤트 기반 비동기 처리
- 단일 프로세스로 다중 연결 처리
- 모듈식 구조
- 중앙 집중식 설정

### 2. 성능 비교
#### 동시 접속 처리
- Apache: 프로세스/스레드 기반으로 제한적
- Nginx: 이벤트 기반으로 높은 동시성

#### 리소스 사용
- Apache: 높은 메모리 사용량
- Nginx: 낮은 메모리 사용량

### 3. 사용 사례
#### Apache가 적합한 경우
- .htaccess 사용 필요
- 다양한 모듈 필요
- PHP 애플리케이션
- 공유 호스팅

#### Nginx가 적합한 경우
- 높은 동시 접속
- 정적 컨텐츠 서빙
- 리버스 프록시
- 마이크로서비스

## Nginx 설정 가이드

### 기본 설정 예시
```nginx
# 워커 프로세스 설정
worker_processes auto;
worker_connections 1024;

# 이벤트 설정
events {
    use epoll;
    multi_accept on;
}

# HTTP 설정
http {
    include mime.types;
    
    # 로드 밸런싱
    upstream backend {
        server backend1.example.com;
        server backend2.example.com;
    }
    
    # 서버 설정
    server {
        listen 80;
        server_name example.com;
        
        # 정적 파일
        location /static/ {
            root /var/www/html;
            expires 30d;
        }
        
        # 리버스 프록시
        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

### 주요 설정 항목
1. **워커 프로세스**
   - worker_processes
   - worker_connections
   - worker_rlimit_nofile

2. **이벤트 설정**
   - use
   - multi_accept
   - worker_connections

3. **HTTP 설정**
   - include
   - default_type
   - sendfile
   - tcp_nopush
   - tcp_nodelay

4. **서버 설정**
   - listen
   - server_name
   - location
   - root
   - index

## 실제 사용 사례

### 1. 정적 파일 서빙
- 이미지, CSS, JavaScript 파일
- 효율적인 캐싱
- 빠른 응답 시간

### 2. 리버스 프록시
- 백엔드 서버 보호
- 로드 밸런싱
- SSL 종료

### 3. 로드 밸런싱
- 여러 백엔드 서버 분산
- 고가용성 확보
- 확장성 향상

### 4. API 게이트웨이
- 마이크로서비스 아키텍처
- 라우팅
- 인증/인가

## 결론
Nginx는 현대 웹 인프라에서 필수적인 요소가 되었습니다. 높은 성능, 낮은 리소스 사용량, 다양한 기능을 제공하며, 특히 대규모 트래픽을 처리해야 하는 환경에서 그 진가를 발휘합니다. 웹 개발자와 시스템 관리자는 Nginx의 특성을 잘 이해하고 적절히 활용하여 효율적인 웹 서비스를 구축할 수 있습니다.

```
출처
- https://www.nginx.com/blog/nginx-vs-apache-our-view/
- https://www.digitalocean.com/community/tutorials/apache-vs-nginx-practical-considerations
- https://www.nginx.com/resources/wiki/
```
