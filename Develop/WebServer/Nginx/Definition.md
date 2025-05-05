# NginX (엔진 엑스)

# Nginx 를 알기 전에 웹서버란?
- HTTP 프로토콜을 이용하여 html 데이터를 클라이언트에게 제공해주는 서버이다. HTTP 프로토콜이란 OSI 7 계층인 application layer에 위치한 프로토콜로서 브라우저(클라이언트)와 서버 사이에 정보를 주고 받기 위한 프로토콜로 사용된다. 즉, 웹(사이트)를 이용한다면, 사이트로 들어갈 때, 어떤 방식을 사용해서, 서버는 어떻게 응답할 것인지를 정해놓은 약속이다.
- 웹서버로는 Nginx 와 Apache 등이 있다.


---

## <span style="color: Brown;">Nginx란 무엇인가?</span>
- HTTP와 HTTPS를 지원하는 웹 서버입니다.
- Web Server : 단순히 정적 파일 응답
- WAS(Web Application Server) : 클라이언트 요청에 대해 동적 처리가 이뤄진 후 응답

![NginX.jpeg](..%2F..%2F..%2Fetc%2Fimage%2FWebServer%2FNginX%2FNginX.jpeg) 

---

## NginX 등장배경
### <span style="color: pink;">Apache의 문제</span>
- 1999년부터는 서버 트래픽량이 높아져서 서버에 동시 연결된 커넥션이 많아졌을 때 더 이상 커넥션을 형성하지 못하는 문제가 생겼다.


1. Connection 10000 Problem
2. 커넥션마다 프로세스를 할당하기에 메모리 부족으로 이어짐.
3. 확장성이라는 장점이 프로세스의 리소스 양을 늘려서 무거운 프로그램이 되었음
4. 많은 커넥션에서 요청이 들어오면 CPU 부하가 높아짐. (컨텍스트 스위칭을 많이함)
> 즉, 수많은 동시 커넥션을 감당하기엔 아파치 서버의 구조가 적합하지 않았다.

### <span style="color: skyblue;">문제점 해결</span>
- 동시 접속에 특화된 Nginx를 쓰자!
- 효율적인 서버 자원(CPU, 메모리 등) 사용 
- Nginx 개요
   세계에서 가장 많이 사용하고 있는 웹서버이다. (웹서버의 TOP2 아파치와 엔진엑스)
  - 웹 서버의 역할 
    - 정적 파일을 처리하는 HTTP 서버
    -  클라이언트가 정적 파일(HTTP, CSS, Javascript, 이미지)만 요청했다면 웹 서버가 직접 응답할 수 있다.

---
## NginX의 구조

![Nginx 구조.png](..%2F..%2F..%2Fetc%2Fimage%2FWebServer%2FNginX%2FNginx%20%EA%B5%AC%EC%A1%B0.png)

> Nginx는 가장 먼저 마스터 프로세스(master process)라는 것을 볼 수 있다.

### Master Process
- 설정 파일을 읽고 워커 프로세스(worker process)를 생성하는 프로세스이다.

### Worker Process
- 실제로 일을 하는 프로세스로, 생성될 때 각자 지정된 listen 소켓을 배정받는다.
- 배정받은 소켓에 새로운 클라이언트 요청이 들어오면 커넥션을 형성하고 처리한다.
- 커넥션은 정해진 Keep Alive 시간만큼 유지되는데, 이렇게 커넥션이 형성되었다고 해서 워커 프로세스가 커넥션 하나만 담당하진 않는다.
- 형성된 커넥션에 아무런 요청이 없으면 새로운 커넥션을 형성하거나 이미 만들어진 다른 커넥션으로부터 들어온 요청을 처리한다.
- Nginx에서는 이런 커넥션 형성과 제거, 새로운 요청을 처리하는 것을 이벤트(event)라고 부른다.


![NginX - Worker Process.jpeg](..%2F..%2F..%2Fetc%2Fimage%2FWebServer%2FNginX%2FNginX%20-%20Worker%20Process.jpeg)
- 이벤트들은 OS 커널이 큐 형식으로 워커 프로세스에게 전달해준다.
- 이벤트는 큐에 담긴 상태에서 워커 프로세스가 처리할 때까지 비동기 방식으로 대기한다.
- 그리고 워커 프로세스는 하나의 스레드로 이벤트를 꺼내서 처리해 나간다.
- 아파치 서버는 커넥션 연결 후 요청이 없다면 방치되는 반면, NGINX는 커넥션 연결 후 요청이 없으면 다른 커넥션의 요청을 처리하거나 새로운 커넥션을 형성하므로 아파치 서버에 비해 서버 자원을 효율적으로 쓰는 것을 알 수 있다.


---

## NginX의 활용

### 프록시
- '대리'라는 의미로, 네트워크 기술에서는 프로토콜에 있어서 대리 응답 등에서 친숙한 개념입니다. 보안 분야에서는 주로 보안상의 이유로 직접 통시할 수 없는 두 점 사이에서 통신을 할 경우 그 사이에 있어서 중게기로서 대리로 통신을 수행하는 기능을 가리켜 '프록시', 그 중계 기능을 하는 것을 프록시 서버라고 부릅니다.
  
### 로드 밸런싱(load balancing)
- 로드 밸런서는 직역하면 부하 분산으로, 서버에 가해지는 부하를 분산해주는 역할을 하는 것이다.
- 이용자가 많아서 발생하는 요청이 많을 때, 하나의 서버에서 이를 모두 처리하는 것이 아니라 여러
  대의 서버를 이용하여 요청을 처리하게 한다.

### HTTP Server로서 정적 파일을 Serve
- 클라이언트(유저)로부터 요청을 받았을 때 WAS를 거치지 않고 요청에 맞는 정적 파일을 응답해주는 HTTP server로서 활용할 수 있다.
- HTML, CSS 같은 정적인 리소스에 대한 요청을 Nginx가 처리해준다.
- React의 build 된 파일들도 정적인 리소스라고 볼 수 있고 따라서 Nginx가 index.html 같은 메인 페이지를 랜더링 해줄 수 있다.

### Reverse Proxy Server로서 Client와 Server를 중개
- Reverse Proxy Server로서 Client의 Request와 Server의 Response를 중개하는 서버로 동작하게 할 수 있다.
- 이 과정에서 nginx는 로드밸런서로서의 역할을 수행할 수 있다.
- 동적으로 계산되거나 전달되어야 하는 사항들은 WAS에게 맡긴다.

### WAS (Web Application Server)
- 웹 서버로부터 오는 동적인 요청들을 처리하는 서버이다. 흔히 사용하는 웹 프레임워크를 사용해 구축하는 백엔드를 WAS라고 생각하면 될듯하다. 주로 데이터베이스 서버와 같이 관리된다.

--- 

```
출처 
https://ssdragon.tistory.com/60
```

# 웹서버란?
- HTTP 프로토콜을 이용하여 html 데이터를 클라이언트에게 제공해주는 서버이다. HTTP 프로토콜이란 OSI 7 계층인 application layer에 위치한 프로토콜로서 브라우저(클라이언트)와 서버 사이에 정보를 주고 받기 위한 프로토콜로 사용된다.
- 웹서버의 주요 기능:
  1. 정적 컨텐츠 제공 (HTML, CSS, JavaScript, 이미지 등)
  2. 동적 컨텐츠 처리 (PHP, Python, Node.js 등과 연동)
  3. 보안 기능 (SSL/TLS, 인증 등)
  4. 로드 밸런싱
  5. 캐싱
  6. 리버스 프록시

---

## <span style="color: Brown;">Nginx란 무엇인가?</span>
- 2004년 Igor Sysoev가 개발한 고성능 웹 서버
- 현재 전 세계 웹사이트의 약 33%가 사용 중 (Apache는 약 31%)
- 주요 특징:
  1. 이벤트 기반 비동기 처리 방식
  2. 높은 동시 접속 처리 능력
  3. 낮은 메모리 사용량
  4. 모듈식 아키텍처
  5. 리버스 프록시 및 로드 밸런싱 기능

### Web Server vs WAS
- Web Server (Nginx, Apache)
  - 정적 컨텐츠 처리
  - HTTP 요청 처리
  - SSL/TLS 처리
  - 캐싱
  - 리버스 프록시

- WAS (Web Application Server)
  - 동적 컨텐츠 처리
  - 비즈니스 로직 실행
  - 데이터베이스 연동
  - 세션 관리
  - 트랜잭션 처리

---

## NginX vs Apache 상세 비교

### 1. 아키텍처 비교
#### Apache
- MPM (Multi-Processing Module) 기반 아키텍처
- 주요 MPM 모드:
  1. Prefork MPM
     - 각 요청마다 새로운 프로세스 생성
     - PHP와 같은 스레드-안전하지 않은 모듈과 호환성 좋음
     - 메모리 사용량 높음
  2. Worker MPM
     - 멀티 프로세스 + 멀티 스레드
     - 각 프로세스가 여러 스레드 생성
     - 메모리 효율적 사용
  3. Event MPM
     - 비동기 이벤트 처리
     - 높은 동시성 지원

#### Nginx
- 이벤트 기반 비동기 아키텍처
- 구성 요소:
  1. Master Process
     - 설정 파일 읽기
     - Worker Process 관리
     - 로그 관리
  2. Worker Process
     - 실제 요청 처리
     - 비동기 이벤트 처리
     - CPU 코어 수에 맞춰 생성

### 2. 성능 비교
#### 동시 접속 처리
- Apache
  - 각 연결마다 프로세스/스레드 생성
  - 많은 동시 접속 시 메모리 부족 가능성
  - 컨텍스트 스위칭 오버헤드

- Nginx
  - 비동기 이벤트 처리
  - 단일 프로세스로 수천 개 연결 처리 가능
  - 낮은 메모리 사용량
  - 높은 처리량

#### 정적 컨텐츠 처리
- Apache
  - 파일 시스템 직접 접근
  - sendfile() 시스템 콜 사용 가능
  - 모듈에 따른 성능 차이

- Nginx
  - 효율적인 파일 전송
  - sendfile() 최적화
  - 캐싱 메커니즘 우수

### 3. 설정 및 관리
#### Apache
- .htaccess 파일 지원
- 모듈 동적 로드 가능
- 설정 변경 시 서버 재시작 필요
- 더 많은 모듈과 기능

#### Nginx
- 중앙 집중식 설정
- 설정 변경 시 서버 재시작 불필요
- 더 간단한 설정 문법
- 높은 보안성

### 4. 사용 사례
#### Apache가 더 적합한 경우
- .htaccess 사용이 필요한 경우
- 다양한 모듈이 필요한 경우
- PHP 애플리케이션 호스팅
- 공유 호스팅 환경

#### Nginx가 더 적합한 경우
- 높은 동시 접속 처리
- 정적 컨텐츠 서빙
- 리버스 프록시
- 로드 밸런싱
- 마이크로서비스 아키텍처

---

## NginX의 주요 기능

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

---

## NginX 설정 예시

```nginx
# 워커 프로세스 설정
worker_processes auto;  # CPU 코어 수에 맞춰 자동 설정
worker_connections 1024;  # 각 워커의 최대 연결 수

# 이벤트 설정
events {
    use epoll;  # Linux에서 효율적인 이벤트 처리
    multi_accept on;  # 여러 연결 동시 수락
}

# HTTP 설정
http {
    # MIME 타입 설정
    include mime.types;
    
    # 로드 밸런싱 설정
    upstream backend {
        server backend1.example.com;
        server backend2.example.com;
    }
    
    # 서버 설정
    server {
        listen 80;
        server_name example.com;
        
        # 정적 파일 서빙
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

---

## 결론
- Nginx는 높은 성능과 낮은 리소스 사용량이 필요한 경우에 적합
- Apache는 다양한 기능과 모듈이 필요한 경우에 적합
- 현대 웹 아키텍처에서는 Nginx를 프론트엔드, Apache를 백엔드로 사용하는 하이브리드 구성도 일반적
- 마이크로서비스 아키텍처에서는 Nginx가 더 적합한 선택

```
출처 
https://ssdragon.tistory.com/60
https://www.nginx.com/blog/nginx-vs-apache-our-view/
https://www.digitalocean.com/community/tutorials/apache-vs-nginx-practical-considerations
```
