
# Event Loop

<div align="center">
    <img src="../../../etc/image/Framework/Node/Event Loop.jpeg" alt="Domain" width="50%">
</div>

## 1. 이벤트루프가 왜 중요한가?
- 이벤트루프는 메인스레드 겸 싱글스레드로서, 비즈니스 로직을 수행한다. 
- 수행도중에 블로킹 IO작업을 만나면 커널 비동기 또는 자신의 워커쓰레드풀에게 넘겨주는 역할까지 한다. 
- 보통 웹어플리케이션에서 쓰니, 웹으로 예를 들자면 request 가 들어오면 라우터태우기, if문분기, 반복문돌며 필터링, 콜백내부로직 등은 이벤트루프가 수행하지만 DB에서 데이터를 읽어오거나 외부 API콜을 하는 것은 커널 비동기 또는 자신의 워커쓰레드가 수행한다. 
- 동시에 많은 요청이 들어온다해도 1개의 이벤트루프에서 처리한다. 
- 따라서 JS로직(if분기, 반복문 등)이 무겁다면 많은 요청을 처리해내기 힘들 것이다.

## 2. libuv는 어떻게 동작하는가?
- libuv는 윈도우 커널, 리눅스 커널을 추상화해서 wrapping하고 있다.
- nodejs는 기본적으로 libuv 위에서 동작하며, node 인스턴스가 뜰 때, libuv에는 워커 쓰레드풀(default 4개)이 생성된다.
- 위에서 블로킹 작업(api콜, DB Read/Write 등)들이 들어오면 이벤트루프가 uv_io에게 내려준다고 하였다.


---

> 출처
> https://akasai.space/node-js/about_node_js_3/