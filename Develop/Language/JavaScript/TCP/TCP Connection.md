
# 소켓 통신과 Node.js TCP 통신

소켓 통신은 컴퓨터 네트워크에서 데이터를 교환하기 위해 사용하는 기술입니다.
이를 이해하기 위해 클라이언트와 서버, 그리고 소켓의 개념을 하나씩 살펴보겠습니다.

---

## 소켓 통신의 기본 개념

### 1. 소켓(Socket)이란?
소켓은 네트워크 상에서 서로 다른 장치 간 데이터를 주고받기 위한 인터페이스입니다.
프로세스(응용 프로그램)가 네트워크를 통해 통신하기 위해 사용하는 논리적인 접점입니다.

- **역할**: 데이터 송수신
- **형식**: IP 주소와 포트 번호로 구성

### 2. 클라이언트와 서버
- **클라이언트**: 서비스를 요청하는 쪽 (예: 웹 브라우저)
- **서버**: 요청을 처리하고 응답하는 쪽 (예: 웹 서버)

### 3. TCP와 UDP
- **TCP (Transmission Control Protocol)**: 신뢰성 있는 데이터 전송 (순서 보장, 데이터 손실 방지)
- **UDP (User Datagram Protocol)**: 빠르고 단순한 데이터 전송 (신뢰성은 낮음)

---

## Node.js에서의 TCP 통신

Node.js는 기본적으로 `net` 모듈을 사용해 TCP 소켓 서버와 클라이언트를 쉽게 구현할 수 있습니다.

### 1. TCP 서버 구현 예제

```javascript
const net = require('net');

// 서버 생성
const server = net.createServer((socket) => {
    console.log('클라이언트 연결됨');

    // 데이터 수신 처리
    socket.on('data', (data) => {
        console.log('수신 데이터:', data.toString());
        socket.write('서버 응답: ' + data); // 응답 전송
    });

    // 연결 종료 처리
    socket.on('end', () => {
        console.log('클라이언트 연결 종료');
    });

    // 에러 처리
    socket.on('error', (err) => {
        console.error('소켓 에러:', err);
    });
});

// 서버 시작
server.listen(8080, () => {
    console.log('TCP 서버가 8080 포트에서 실행 중입니다.');
});
```

### 2. TCP 클라이언트 구현 예제

```javascript
const net = require('net');

// 클라이언트 생성
const client = net.createConnection({ port: 8080 }, () => {
    console.log('서버에 연결됨');
    client.write('안녕하세요, 서버님!'); // 데이터 전송
});

// 데이터 수신 처리
client.on('data', (data) => {
    console.log('서버 응답:', data.toString());
    client.end(); // 통신 종료
});

// 연결 종료 처리
client.on('end', () => {
    console.log('서버 연결 종료');
});

// 에러 처리
client.on('error', (err) => {
    console.error('클라이언트 에러:', err);
});
```

---

## 소켓 관리

### 1. 소켓이 끊길 때 처리
소켓이 끊기는 상황(예: 클라이언트가 종료하거나 네트워크 문제가 발생했을 때)에는 이를 감지하여 적절히 처리해야 합니다.

- **이벤트 기반 처리**: `end`, `close`, `error` 이벤트를 활용
- **예제**:
```javascript
socket.on('close', () => {
    console.log('소켓이 닫혔습니다.');
    // 필요 시 소켓을 삭제하거나 정리
});
```

### 2. 소켓 관리 팁
- **리소스 정리**: 사용하지 않는 소켓은 명시적으로 닫거나 참조를 해제
- **타임아웃 설정**: 오랫동안 응답이 없는 연결을 자동 종료
```javascript
socket.setTimeout(30000); // 30초 타임아웃
socket.on('timeout', () => {
    console.log('소켓 타임아웃 발생');
    socket.end();
});
```

---

## 소켓 통신을 이해하기 위한 추가 자료

### 1. OSI 7 계층에서 소켓의 위치
소켓은 **전송 계층(TCP, UDP)** 과 **응용 계층(HTTP 등)** 사이에서 동작합니다.

### 2. 소켓 통신의 주요 단계
1. 소켓 생성
2. 서버: 특정 포트에서 대기 (bind & listen)
3. 클라이언트: 서버에 연결 요청 (connect)
4. 데이터 송수신 (send & receive)
5. 연결 종료 (close)

---

## 정리

소켓 통신은 클라이언트와 서버 간의 데이터 교환을 위해 반드시 필요한 기술입니다. Node.js에서는 `net` 모듈을 사용해 간단히 TCP 기반의 소켓 통신을 구현할 수 있으며, 실무에서는 소켓의 상태(열림, 닫힘, 에러 등)를 적절히 관리하는 것이 중요합니다.

---
