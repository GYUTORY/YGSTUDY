
# Node.js Buffer와 TCP

## 1. Buffer란?
Buffer는 Node.js에서 바이너리 데이터(이진 데이터)를 다룰 수 있도록 제공되는 클래스입니다.
특히, 네트워크 프로토콜, 파일 I/O, 데이터 스트림 등의 환경에서 자주 사용됩니다.

### Buffer의 주요 특징
- 고정 크기의 메모리 공간을 할당.
- 이진 데이터 처리를 위한 다양한 메서드를 제공.
- `Buffer`는 Node.js의 전역 객체로, 추가적인 `require` 없이 바로 사용 가능.

### Buffer의 생성 예제
```javascript
// 1. Buffer 생성
const buf = Buffer.alloc(10); // 크기가 10인 빈 버퍼 생성
console.log(buf); // <Buffer 00 00 00 00 00 00 00 00 00 00>

// 2. 버퍼에 데이터 저장
const buf2 = Buffer.from('Hello, TCP!');
console.log(buf2); // <Buffer 48 65 6c 6c 6f 2c 20 54 43 50 21>

// 3. 버퍼 데이터를 문자열로 변환
console.log(buf2.toString()); // 'Hello, TCP!'
```

---

## 2. TCP란?
TCP(Transmission Control Protocol)는 인터넷에서 데이터 전송을 담당하는 주요 프로토콜 중 하나로,
신뢰성 있는 데이터 전송을 보장합니다.

### TCP의 주요 특징
- **연결 지향적**: 데이터 전송 전에 송신자와 수신자 간에 연결을 설정.
- **신뢰성 보장**: 데이터가 손실되지 않도록 재전송 및 확인(Acknowledgment) 지원.
- **순서 보장**: 데이터 패킷이 전송된 순서대로 도착.

Node.js에서는 `net` 모듈을 사용하여 TCP 서버 및 클라이언트를 구현할 수 있습니다.

---

## 3. Node.js에서 Buffer와 TCP의 활용
Node.js에서 TCP 소켓 통신 시 데이터를 주고받기 위해 `Buffer`를 자주 사용합니다.
아래는 TCP 서버와 클라이언트를 구현한 예제입니다.

### TCP 서버 예제
```javascript
const net = require('net');

const server = net.createServer((socket) => {
    console.log('클라이언트가 연결되었습니다.');

    // 클라이언트로부터 데이터 수신
    socket.on('data', (data) => {
        console.log('클라이언트로부터 받은 데이터:', data.toString());

        // 클라이언트로 응답 전송
        const response = Buffer.from('서버에서 응답합니다: ' + data.toString());
        socket.write(response);
    });

    socket.on('end', () => {
        console.log('클라이언트가 연결을 종료했습니다.');
    });
});

server.listen(8080, () => {
    console.log('TCP 서버가 8080 포트에서 실행 중입니다.');
});
```

### TCP 클라이언트 예제
```javascript
const net = require('net');

const client = net.createConnection({ port: 8080 }, () => {
    console.log('서버에 연결되었습니다.');

    // 서버로 데이터 전송
    const message = Buffer.from('안녕하세요, 서버님!');
    client.write(message);
});

client.on('data', (data) => {
    console.log('서버로부터 받은 응답:', data.toString());
    client.end(); // 연결 종료
});

client.on('end', () => {
    console.log('서버와의 연결이 종료되었습니다.');
});
```

---

## 4. Buffer와 TCP의 상호작용
- 클라이언트와 서버는 데이터를 `Buffer` 객체로 교환.
- 수신된 데이터는 항상 `Buffer` 형태로 제공되며, 이를 문자열로 변환하거나 추가 처리를 수행 가능.

### 상호작용 과정
1. 클라이언트가 서버에 데이터를 `Buffer` 형태로 전송.
2. 서버가 데이터를 수신하고 처리.
3. 처리 결과를 다시 `Buffer` 형태로 클라이언트에 응답.

---

## 5. 결론
Node.js의 `Buffer`는 이진 데이터를 효율적으로 처리하기 위한 도구이며,
`TCP`는 신뢰성 있는 네트워크 통신을 제공하는 프로토콜입니다.
둘의 결합은 고성능 네트워크 애플리케이션을 개발할 때 강력한 도구가 됩니다.
