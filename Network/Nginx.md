
# Nginx
- HTTP와 HTTPS를 지원하는 웹 서버입니다.
- Web Server : 단순히 정적 파일 응답
- WAS(Web Application Server) : 클라이언트 요청에 대해 동적 처리가 이뤄진 후 응답

![NginX.jpeg](..%2Fetc%2Fimage%2FNetwork_image%2FNginX.jpeg)

### Apache와의 차이를 알기 위해, Apache에 대해 먼저 알아보자.

- 아파치 서버는 요청이 들어오면 커넥션을 형성하기 위해 프로세스를 생성한다.
- 즉, 새로운 요청이 들어올 때마다 프로세스를 새로 만든다.
- 그래서 새로운 클라이언트 요청이 들어오면 미리 만들어 놓은 프로세스를 가져다 사용했다.
- 만약 만들어 놓은 프로세스가 모두 할당되면 추가로 프로세스를 만들었다.

![Apache HTTP SERVER 확장성.jpeg](..%2Fetc%2Fimage%2FNetwork_image%2FApache%20HTTP%20SERVER%20%ED%99%95%EC%9E%A5%EC%84%B1.jpeg)

- 덕분에 개발자는 다양한 모듈을 만들어서 서버에 빠르게 기능을 추가할 수 있었다.
- 이런 식으로 아파치 서버는 동적 컨텐츠를 처리할수 있게 되었다. 

![10K문제.jpeg](..%2Fetc%2Fimage%2FNetwork_image%2F10K%EB%AC%B8%EC%A0%9C.jpeg)

## Apache의 문제
- 1999년부터는 서버 트래픽량이 높아져서 서버에 동시 연결된 커넥션이 많아졌을 때 더 이상 커넥션을 형성하지 못하는 문제가 생겼다.


1. Connection 10000 Problem
2. 커넥션마다 프로세스를 할당하기에 메모리 부족으로 이어짐.
3. 확장성이라는 장점이 프로세스의 리소스 양을 늘려서 무거운 프로그램이 되었음
4. 많은 커넥션에서 요청이 들어오면 CPU 부하가 높아짐. (컨텍스트 스위칭을 많이함)
> 즉, 수많은 동시 커넥션을 감당하기엔 아파치 서버의 구조가 적합하지 않았다.

## 다시 Nginx로 돌아가자 

### NginX의 구조 

![Nginx 구조.png](..%2Fetc%2Fimage%2FNetwork_image%2FNginx%20%EA%B5%AC%EC%A1%B0.png)

> Nginx는 가장 먼저 마스터 프로세스(master process)라는 것을 볼 수 있다.

#### Master Process
- 설정 파일을 읽고 워커 프로세스(worker process)를 생성하는 프로세스이다.

#### Worker Process
- 실제로 일을 하는 프로세스로, 생성될 때 각자 지정된 listen 소켓을 배정받는다.
- 배정받은 소켓에 새로운 클라이언트 요청이 들어오면 커넥션을 형성하고 처리한다.
- 커넥션은 정해진 Keep Alive 시간만큼 유지되는데, 이렇게 커넥션이 형성되었다고 해서 워커 프로세스가 커넥션 하나만 담당하진 않는다. 
- 형성된 커넥션에 아무런 요청이 없으면 새로운 커넥션을 형성하거나 이미 만들어진 다른 커넥션으로부터 들어온 요청을 처리한다.
- Nginx에서는 이런 커넥션 형성과 제거, 새로운 요청을 처리하는 것을 이벤트(event)라고 부른다.

![NginX - Worker Process.jpeg](..%2Fetc%2Fimage%2FNetwork_image%2FNginX%20-%20Worker%20Process.jpeg)
- 이벤트들은 OS 커널이 큐 형식으로 워커 프로세스에게 전달해준다.
- 이벤트는 큐에 담긴 상태에서 워커 프로세스가 처리할 때까지 비동기 방식으로 대기한다.
- 그리고 워커 프로세스는 하나의 스레드로 이벤트를 꺼내서 처리해 나간다.
- 아파치 서버는 커넥션 연결 후 요청이 없다면 방치되는 반면, NGINX는 커넥션 연결 후 요청이 없으면 다른 커넥션의 요청을 처리하거나 새로운 커넥션을 형성하므로 아파치 서버에 비해 서버 자원을 효율적으로 쓰는 것을 알 수 있다.

# Nginx의 특징
1. HTTP Server로서 정적 파일을 Serve 해준다
- 클라이언트(유저)로부터 요청을 받았을 때 WAS를 거치지 않고 요청에 맞는 정적 파일을 응답해주는 HTTP server로서 활용할 수 있다.
- HTML, CSS 같은 정적인 리소스에 대한 요청을 Nginx가 처리해준다.
- React의 build 된 파일들도 정적인 리소스라고 볼 수 있고 따라서 Nginx가 index.html 같은 메인 페이지를 랜더링 해줄 수 있다.

2. Reverse Proxy Server로서 Client와 Server를 중개해 준다.
- Reverse Proxy Server로서 Client의 Request와 Server의 Response를 중개하는 서버로 동작하게 할 수 있다. 
- 이 과정에서 nginx는 로드밸런서로서의 역할을 수행할 수 있다.
- 동적으로 계산되거나 전달되어야 하는 사항들은 WAS에게 맡긴다.

3. WAS (Web Application Server)
- 웹 서버로부터 오는 동적인 요청들을 처리하는 서버이다. 흔히 사용하는 웹 프레임워크를 사용해 구축하는 백엔드를 WAS라고 생각하면 될듯하다. 주로 데이터베이스 서버와 같이 관리된다.


```
출처 
https://ssdragon.tistory.com/60

```