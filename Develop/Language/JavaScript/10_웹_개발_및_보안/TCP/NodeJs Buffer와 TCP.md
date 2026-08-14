---
title: Node.js Buffer TCP
tags: [language, javascript, tcp]
updated: 2025-12-21
---
# Node.js Buffer와 TCP 이해하기

## 배경

- [Buffer란?](#buffer란)
- [TCP란?](#tcp란)
- [Buffer와 TCP의 관계](#buffer와-tcp의-관계)
- [실제 사용 예제](#실제-사용-예제)
- [핵심 개념 정리](#핵심-개념-정리)

---


```javascript
// 1. 클라이언트에서 텍스트를 Buffer로 변환
const message = "안녕하세요!";
const buffer = Buffer.from(message, 'utf8');

// 2. Buffer를 네트워크로 전송
socket.write(buffer);

// 3. 서버에서 Buffer를 받아서 텍스트로 변환
socket.on('data', (receivedBuffer) => {
    const receivedMessage = receivedBuffer.toString('utf8');
    console.log('받은 메시지:', receivedMessage);
});
```


```
텍스트 → Buffer → 네트워크 전송 → Buffer → 텍스트
   ↓        ↓           ↓           ↓        ↓
"Hello" → <Buffer> → TCP 패킷 → <Buffer> → "Hello"
```

---


### 🖥 TCP 서버 만들기

```javascript
const net = require('net');

// TCP 서버 생성
const server = net.createServer((socket) => {
    console.log('🟢 새로운 클라이언트가 연결되었습니다!');
    
    // 클라이언트의 IP 주소와 포트 출력
    const clientAddress = socket.remoteAddress;
    const clientPort = socket.remotePort;
    console.log(`📡 연결된 클라이언트: ${clientAddress}:${clientPort}`);

    // 클라이언트로부터 데이터를 받았을 때
    socket.on('data', (receivedData) => {
        // receivedData는 자동으로 Buffer 형태로 제공됩니다
        console.log('📥 받은 데이터 (Buffer):', receivedData);
        console.log('📥 받은 데이터 (문자열):', receivedData.toString());
        
        // 서버에서 응답 만들기
        const responseMessage = `서버가 받은 메시지: "${receivedData.toString()}"`;
        const responseBuffer = Buffer.from(responseMessage, 'utf8');
        
        // 클라이언트에게 응답 보내기
        socket.write(responseBuffer);
        console.log('📤 응답을 보냈습니다:', responseMessage);
    });

    // 클라이언트가 연결을 끊었을 때
    socket.on('end', () => {
        console.log('🔴 클라이언트가 연결을 종료했습니다.');
    });

    // 에러 발생 시
    socket.on('error', (err) => {
        console.error('❌ 소켓 에러:', err.message);
    });
});

// 서버를 8080 포트에서 시작
server.listen(8080, () => {
    console.log('🚀 TCP 서버가 8080 포트에서 실행 중입니다!');
    console.log('📍 서버 주소: localhost:8080');
});

// 서버 에러 처리
server.on('error', (err) => {
    console.error('❌ 서버 에러:', err.message);
});
```

이 서버 코드에는 TCP 로 처음 뭔가를 만들 때 반드시 한 번은 밟는 함정이 들어 있다. **`data` 이벤트 한 번이 `write` 한 번과 짝이 아니다.**

TCP 는 메시지를 주고받는 게 아니라 **바이트 스트림**을 흘려보낸다. 경계라는 개념 자체가 없다. `socket.on('data')` 는 "운영체제 버퍼에 뭔가 도착했다"는 신호일 뿐이고, 그 안에 무엇이 얼마나 들어 있는지는 아무도 약속하지 않는다.

**여러 번 보낸 것이 한 번에 도착한다.**

```javascript
c.write('안녕'); c.write('하세'); c.write('요!');

// 서버가 본 것:
//   data #1: 16바이트 → "안녕하세요!"
//   총 data 이벤트 = 1회   (write 는 3회 했다)
```

**한 번 보낸 것이 여러 번에 나뉘어 도착한다.**

```javascript
const ok = c.write(Buffer.alloc(1024 * 1024));   // 1MB 한 번에

// write() 반환값 = false          ← 커널 버퍼가 찼다는 뜻
// 서버의 data 이벤트 = 16회, 총 1048576바이트
```

여기서 문서 코드의 `receivedData.toString()` 이 무너진다. **한글은 한 글자가 3바이트**라, 조각이 글자 중간에서 잘리면 그 글자가 깨진다.

```javascript
const buf = Buffer.from('안녕하세요');   // 15바이트
c.write(buf.subarray(0, 4));             // 4바이트만 먼저
c.write(buf.subarray(4));                // 나머지 11바이트

// 서버가 본 것:
//   data: 4바이트  → "안�"
//   data: 11바이트 → "��하세요"
```

깨진 글자가 화면에 `�` 로 찍힌다. 그리고 이건 **데이터 크기가 작을 때는 거의 안 나타난다.** 로컬에서 짧은 메시지로 테스트하면 항상 한 번에 오니까 잘 동작하는 것처럼 보이고, 운영에서 메시지가 길어지거나 네트워크가 나빠지면 그때부터 나온다.

고치는 방법은 두 가지다.

**하나, 문자열이면 `StringDecoder` 를 쓴다.** 잘린 바이트를 다음 조각까지 들고 있어 준다.

```javascript
const { StringDecoder } = require('string_decoder');
const decoder = new StringDecoder('utf8');
socket.on('data', chunk => {
  const text = decoder.write(chunk);   // 불완전한 바이트는 내부에 보관
  if (text) console.log(text);
});
```

**둘, 메시지 경계를 직접 정한다.** 구분자를 넣거나(줄바꿈 등) 길이를 앞에 붙인다. 스트림에 없는 경계를 애플리케이션이 만들어야 한다.

```javascript
// 길이 접두사: 앞 4바이트에 본문 길이를 넣는다
const body = Buffer.from(JSON.stringify(payload));
const header = Buffer.alloc(4);
header.writeUInt32BE(body.length);
socket.write(Buffer.concat([header, body]));
```

받는 쪽은 조각을 계속 이어 붙이며 "헤더 4바이트가 모였는가 → 본문이 그 길이만큼 모였는가"를 확인하고 한 메시지씩 잘라 낸다. HTTP 의 `Content-Length`, WebSocket 의 프레임 헤더가 전부 이 문제를 푸는 장치다. **TCP 위에 프로토콜을 얹는다는 말이 곧 경계를 정한다는 뜻이다.**

`write()` 가 `false` 를 돌려주는 것도 그냥 넘길 값이 아니다. 상대가 받아가는 속도보다 빠르게 밀어 넣으면 데이터가 메모리에 쌓인다. `false` 가 나오면 멈췄다가 `drain` 이벤트에서 재개해야 하고, 그게 귀찮으면 `pipe` 나 `pipeline` 에 맡긴다 — 배압 처리를 대신해 준다.

### TCP 클라이언트 만들기

```javascript
const net = require('net');

// TCP 클라이언트 생성
const client = net.createConnection({ 
    port: 8080,           // 연결할 포트
    host: 'localhost'     // 연결할 서버 주소
}, () => {
    console.log('🟢 서버에 성공적으로 연결되었습니다!');
    
    // 서버로 메시지 보내기
    const message = "안녕하세요, 서버님!";
    const messageBuffer = Buffer.from(message, 'utf8');
    
    console.log('📤 보낼 메시지:', message);
    console.log('📤 보낼 데이터 (Buffer):', messageBuffer);
    
    client.write(messageBuffer);
});

// 서버로부터 데이터를 받았을 때
client.on('data', (receivedData) => {
    console.log('📥 서버로부터 받은 데이터 (Buffer):', receivedData);
    console.log('📥 서버로부터 받은 응답:', receivedData.toString());
    
    // 연결 종료
    client.end();
    console.log('🔴 서버와의 연결을 종료합니다.');
});

// 연결이 종료되었을 때
client.on('end', () => {
    console.log('✅ 서버와의 연결이 정상적으로 종료되었습니다.');
});

// 에러 발생 시
client.on('error', (err) => {
    console.error('❌ 클라이언트 에러:', err.message);
});
```

### 테스트 방법

1. **서버 실행**
   ```bash
   node server.js
   ```

2. **클라이언트 실행** (새 터미널에서)
   ```bash
   node client.js
   ```

3. **예상 출력**

   **서버 출력:**
   ```
   🚀 TCP 서버가 8080 포트에서 실행 중입니다!
   📍 서버 주소: localhost:8080
   🟢 새로운 클라이언트가 연결되었습니다!
   📡 연결된 클라이언트: ::1:12345
   📥 받은 데이터 (Buffer): <Buffer ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21>
   📥 받은 데이터 (문자열): 안녕하세요, 서버님!
   📤 응답을 보냈습니다: 서버가 받은 메시지: "안녕하세요, 서버님!"
   🔴 클라이언트가 연결을 종료했습니다.
   ```

   **클라이언트 출력:**
   ```
   🟢 서버에 성공적으로 연결되었습니다!
   📤 보낼 메시지: 안녕하세요, 서버님!
   📤 보낼 데이터 (Buffer): <Buffer ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21>
   📥 서버로부터 받은 데이터 (Buffer): <Buffer ec 84 9c eb b2 84 ea b0 80 20 eb b0 9b ec 9d 80 20 eb a9 94 ec 8b 9c ec a7 80 3a 20 22 ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21 22>
   📥 서버로부터 받은 응답: 서버가 받은 메시지: "안녕하세요, 서버님!"
   🔴 서버와의 연결을 종료합니다.
   ✅ 서버와의 연결이 정상적으로 종료되었습니다.
   ```

### 고급 예제: 파일 전송

```javascript
const net = require('net');
const fs = require('fs');

// 파일 전송 서버
const fileServer = net.createServer((socket) => {
    console.log('🟢 파일 전송 클라이언트가 연결되었습니다!');
    
    let receivedData = Buffer.alloc(0);
    
    socket.on('data', (chunk) => {
        // 받은 데이터를 누적
        receivedData = Buffer.concat([receivedData, chunk]);
    });
    
    socket.on('end', () => {
        // 파일로 저장
        fs.writeFileSync('received_file.txt', receivedData);
        console.log('📁 파일이 성공적으로 저장되었습니다!');
        console.log('📊 파일 크기:', receivedData.length, '바이트');
    });
});

fileServer.listen(8081, () => {
    console.log('🚀 파일 전송 서버가 8081 포트에서 실행 중입니다!');
});
```

---


1. **서버 실행**
   ```bash
   node server.js
   ```

2. **클라이언트 실행** (새 터미널에서)
   ```bash
   node client.js
   ```

3. **예상 출력**

   **서버 출력:**
   ```
   🚀 TCP 서버가 8080 포트에서 실행 중입니다!
   📍 서버 주소: localhost:8080
   🟢 새로운 클라이언트가 연결되었습니다!
   📡 연결된 클라이언트: ::1:12345
   📥 받은 데이터 (Buffer): <Buffer ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21>
   📥 받은 데이터 (문자열): 안녕하세요, 서버님!
   📤 응답을 보냈습니다: 서버가 받은 메시지: "안녕하세요, 서버님!"
   🔴 클라이언트가 연결을 종료했습니다.
   ```

   **클라이언트 출력:**
   ```
   🟢 서버에 성공적으로 연결되었습니다!
   📤 보낼 메시지: 안녕하세요, 서버님!
   📤 보낼 데이터 (Buffer): <Buffer ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21>
   📥 서버로부터 받은 데이터 (Buffer): <Buffer ec 84 9c eb b2 84 ea b0 80 20 eb b0 9b ec 9d 80 20 eb a9 94 ec 8b 9c ec a7 80 3a 20 22 ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21 22>
   📥 서버로부터 받은 응답: 서버가 받은 메시지: "안녕하세요, 서버님!"
   🔴 서버와의 연결을 종료합니다.
   ✅ 서버와의 연결이 정상적으로 종료되었습니다.
   ```


```javascript
const net = require('net');
const fs = require('fs');

// 파일 전송 서버
const fileServer = net.createServer((socket) => {
    console.log('🟢 파일 전송 클라이언트가 연결되었습니다!');
    
    let receivedData = Buffer.alloc(0);
    
    socket.on('data', (chunk) => {
        // 받은 데이터를 누적
        receivedData = Buffer.concat([receivedData, chunk]);
    });
    
    socket.on('end', () => {
        // 파일로 저장
        fs.writeFileSync('received_file.txt', receivedData);
        console.log('📁 파일이 성공적으로 저장되었습니다!');
        console.log('📊 파일 크기:', receivedData.length, '바이트');
    });
});

fileServer.listen(8081, () => {
    console.log('🚀 파일 전송 서버가 8081 포트에서 실행 중입니다!');
});
```

---


### 🔑 Buffer의 핵심

| 개념 | 설명 | 예시 |
|------|------|------|
| **역할** | 텍스트 ↔ 바이너리 변환 | `"Hello"` ↔ `<Buffer 48 65 6c 6c 6f>` |
| **생성** | `Buffer.from()`, `Buffer.alloc()` | `Buffer.from('Hello')` |
| **변환** | `buffer.toString()`, `Buffer.from(string)` | `buffer.toString('utf8')` |

### 🔑 TCP의 핵심

| 개념 | 설명 | 특징 |
|------|------|------|
| **역할** | 안전한 네트워크 통신 | 신뢰성 있는 데이터 전송 |
| **특징** | 연결 설정 → 데이터 전송 → 연결 종료 | 3단계 과정 |
| **장점** | 신뢰성, 순서 보장 | 데이터 손실 방지 |

### 🔑 Buffer + TCP의 시너지

1. **클라이언트**: 텍스트 → Buffer → 네트워크 전송
2. **서버**: 네트워크 수신 → Buffer → 텍스트 처리
3. **응답**: 텍스트 → Buffer → 네트워크 전송
4. **클라이언트**: 네트워크 수신 → Buffer → 텍스트 표시

### 실무에서의 활용

| 분야 | 활용 예시 | 설명 |
|------|-----------|------|
| **채팅 애플리케이션** | 실시간 메시지 전송 | 사용자 간 즉시 메시지 교환 |
| **파일 전송** | 이미지, 문서 등의 바이너리 데이터 전송 | 대용량 파일 안전 전송 |
| **게임 서버** | 실시간 게임 데이터 동기화 | 플레이어 위치, 상태 동기화 |
| **IoT 통신** | 센서 데이터 수집 및 제어 명령 전송 | 온도, 습도 등 센서 데이터 |

---

> 📝 **참고사항**
> 
> - Buffer는 Node.js에서만 사용되는 특별한 객체입니다
> - TCP는 웹 브라우저에서는 직접 사용할 수 없고, Node.js 서버에서만 사용 가능합니다
> - 실제 웹 개발에서는 HTTP/HTTPS를 주로 사용하지만, TCP는 그 기반이 됩니다


| 분야 | 활용 예시 | 설명 |
|------|-----------|------|
| **채팅 애플리케이션** | 실시간 메시지 전송 | 사용자 간 즉시 메시지 교환 |
| **파일 전송** | 이미지, 문서 등의 바이너리 데이터 전송 | 대용량 파일 안전 전송 |
| **게임 서버** | 실시간 게임 데이터 동기화 | 플레이어 위치, 상태 동기화 |
| **IoT 통신** | 센서 데이터 수집 및 제어 명령 전송 | 온도, 습도 등 센서 데이터 |

---

> 📝 **참고사항**
> 
> - Buffer는 Node.js에서만 사용되는 특별한 객체입니다
> - TCP는 웹 브라우저에서는 직접 사용할 수 없고, Node.js 서버에서만 사용 가능합니다
> - 실제 웹 개발에서는 HTTP/HTTPS를 주로 사용하지만, TCP는 그 기반이 됩니다






> 💡 **이 문서는 Node.js에서 Buffer와 TCP를 함께 사용하는 방법을 설명합니다.**

---


1. **서버 실행**
   ```bash
   node server.js
   ```

2. **클라이언트 실행** (새 터미널에서)
   ```bash
   node client.js
   ```

3. **예상 출력**

   **서버 출력:**
   ```
   🚀 TCP 서버가 8080 포트에서 실행 중입니다!
   📍 서버 주소: localhost:8080
   🟢 새로운 클라이언트가 연결되었습니다!
   📡 연결된 클라이언트: ::1:12345
   📥 받은 데이터 (Buffer): <Buffer ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21>
   📥 받은 데이터 (문자열): 안녕하세요, 서버님!
   📤 응답을 보냈습니다: 서버가 받은 메시지: "안녕하세요, 서버님!"
   🔴 클라이언트가 연결을 종료했습니다.
   ```

   **클라이언트 출력:**
   ```
   🟢 서버에 성공적으로 연결되었습니다!
   📤 보낼 메시지: 안녕하세요, 서버님!
   📤 보낼 데이터 (Buffer): <Buffer ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21>
   📥 서버로부터 받은 데이터 (Buffer): <Buffer ec 84 9c eb b2 84 ea b0 80 20 eb b0 9b ec 9d 80 20 eb a9 94 ec 8b 9c ec a7 80 3a 20 22 ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21 22>
   📥 서버로부터 받은 응답: 서버가 받은 메시지: "안녕하세요, 서버님!"
   🔴 서버와의 연결을 종료합니다.
   ✅ 서버와의 연결이 정상적으로 종료되었습니다.
   ```


```javascript
const net = require('net');
const fs = require('fs');

// 파일 전송 서버
const fileServer = net.createServer((socket) => {
    console.log('🟢 파일 전송 클라이언트가 연결되었습니다!');
    
    let receivedData = Buffer.alloc(0);
    
    socket.on('data', (chunk) => {
        // 받은 데이터를 누적
        receivedData = Buffer.concat([receivedData, chunk]);
    });
    
    socket.on('end', () => {
        // 파일로 저장
        fs.writeFileSync('received_file.txt', receivedData);
        console.log('📁 파일이 성공적으로 저장되었습니다!');
        console.log('📊 파일 크기:', receivedData.length, '바이트');
    });
});

fileServer.listen(8081, () => {
    console.log('🚀 파일 전송 서버가 8081 포트에서 실행 중입니다!');
});
```

---


1. **서버 실행**
   ```bash
   node server.js
   ```

2. **클라이언트 실행** (새 터미널에서)
   ```bash
   node client.js
   ```

3. **예상 출력**

   **서버 출력:**
   ```
   🚀 TCP 서버가 8080 포트에서 실행 중입니다!
   📍 서버 주소: localhost:8080
   🟢 새로운 클라이언트가 연결되었습니다!
   📡 연결된 클라이언트: ::1:12345
   📥 받은 데이터 (Buffer): <Buffer ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21>
   📥 받은 데이터 (문자열): 안녕하세요, 서버님!
   📤 응답을 보냈습니다: 서버가 받은 메시지: "안녕하세요, 서버님!"
   🔴 클라이언트가 연결을 종료했습니다.
   ```

   **클라이언트 출력:**
   ```
   🟢 서버에 성공적으로 연결되었습니다!
   📤 보낼 메시지: 안녕하세요, 서버님!
   📤 보낼 데이터 (Buffer): <Buffer ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21>
   📥 서버로부터 받은 데이터 (Buffer): <Buffer ec 84 9c eb b2 84 ea b0 80 20 eb b0 9b ec 9d 80 20 eb a9 94 ec 8b 9c ec a7 80 3a 20 22 ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 2c 20 ec 84 9c eb b2 84 eb 8b 98 21 22>
   📥 서버로부터 받은 응답: 서버가 받은 메시지: "안녕하세요, 서버님!"
   🔴 서버와의 연결을 종료합니다.
   ✅ 서버와의 연결이 정상적으로 종료되었습니다.
   ```


```javascript
const net = require('net');
const fs = require('fs');

// 파일 전송 서버
const fileServer = net.createServer((socket) => {
    console.log('🟢 파일 전송 클라이언트가 연결되었습니다!');
    
    let receivedData = Buffer.alloc(0);
    
    socket.on('data', (chunk) => {
        // 받은 데이터를 누적
        receivedData = Buffer.concat([receivedData, chunk]);
    });
    
    socket.on('end', () => {
        // 파일로 저장
        fs.writeFileSync('received_file.txt', receivedData);
        console.log('📁 파일이 성공적으로 저장되었습니다!');
        console.log('📊 파일 크기:', receivedData.length, '바이트');
    });
});

fileServer.listen(8081, () => {
    console.log('🚀 파일 전송 서버가 8081 포트에서 실행 중입니다!');
});
```

---



| 분야 | 활용 예시 | 설명 |
|------|-----------|------|
| **채팅 애플리케이션** | 실시간 메시지 전송 | 사용자 간 즉시 메시지 교환 |
| **파일 전송** | 이미지, 문서 등의 바이너리 데이터 전송 | 대용량 파일 안전 전송 |
| **게임 서버** | 실시간 게임 데이터 동기화 | 플레이어 위치, 상태 동기화 |
| **IoT 통신** | 센서 데이터 수집 및 제어 명령 전송 | 온도, 습도 등 센서 데이터 |

---

> 📝 **참고사항**
> 
> - Buffer는 Node.js에서만 사용되는 특별한 객체입니다
> - TCP는 웹 브라우저에서는 직접 사용할 수 없고, Node.js 서버에서만 사용 가능합니다
> - 실제 웹 개발에서는 HTTP/HTTPS를 주로 사용하지만, TCP는 그 기반이 됩니다


| 분야 | 활용 예시 | 설명 |
|------|-----------|------|
| **채팅 애플리케이션** | 실시간 메시지 전송 | 사용자 간 즉시 메시지 교환 |
| **파일 전송** | 이미지, 문서 등의 바이너리 데이터 전송 | 대용량 파일 안전 전송 |
| **게임 서버** | 실시간 게임 데이터 동기화 | 플레이어 위치, 상태 동기화 |
| **IoT 통신** | 센서 데이터 수집 및 제어 명령 전송 | 온도, 습도 등 센서 데이터 |

---

> 📝 **참고사항**
> 
> - Buffer는 Node.js에서만 사용되는 특별한 객체입니다
> - TCP는 웹 브라우저에서는 직접 사용할 수 없고, Node.js 서버에서만 사용 가능합니다
> - 실제 웹 개발에서는 HTTP/HTTPS를 주로 사용하지만, TCP는 그 기반이 됩니다






> 💡 **이 문서는 Node.js에서 Buffer와 TCP를 함께 사용하는 방법을 설명합니다.**

---





## Buffer란?

### Buffer의 정의

Buffer는 Node.js에서 **바이너리 데이터(이진 데이터)** 를 다루기 위한 특별한 객체입니다.

> **바이너리 데이터란?**
> 
> 컴퓨터가 이해하는 0과 1로 이루어진 데이터를 의미합니다. 텍스트, 이미지, 음악 파일 등 모든 데이터는 결국 0과 1의 조합으로 저장됩니다.

### Buffer가 필요한 이유

| 상황 | 설명 | 예시 |
|------|------|------|
| **텍스트 vs 바이너리** | 우리가 보는 "Hello"는 컴퓨터에서는 `01001000 01100101 01101100 01101100 01101111`로 저장 | "Hello" → `48 65 6c 6c 6f` |
| **네트워크 통신** | 데이터를 주고받을 때는 항상 바이너리 형태로 전송 | 텍스트 → 바이너리 → 네트워크 |
| **파일 처리** | 이미지, PDF 등은 바이너리 데이터로 처리해야 함 | 이미지 파일의 픽셀 데이터 |

### Buffer 생성 방법

#### 1⃣ 빈 Buffer 생성
```javascript
// 크기가 10인 빈 버퍼 생성 (모든 값이 0으로 초기화)
const emptyBuffer = Buffer.alloc(10);
console.log(emptyBuffer); 
// 출력: <Buffer 00 00 00 00 00 00 00 00 00 00>
```

#### 2⃣ 문자열로 Buffer 생성
```javascript
// 문자열을 바이너리로 변환하여 버퍼 생성
const textBuffer = Buffer.from('Hello, World!');
console.log(textBuffer);
// 출력: <Buffer 48 65 6c 6c 6f 2c 20 57 6f 72 6c 64 21>
```

#### 3⃣ 배열로 Buffer 생성
```javascript
// 숫자 배열로 버퍼 생성
const arrayBuffer = Buffer.from([72, 101, 108, 108, 111]); // 'Hello'의 ASCII 코드
console.log(arrayBuffer.toString()); // 'Hello'
```

### Buffer와 문자열 변환

```javascript
const message = "안녕하세요!";

// 문자열 → Buffer
const buffer = Buffer.from(message, 'utf8');
console.log(buffer);
// 출력: <Buffer ec 95 88 eb 85 95 ed 95 98 ec 84 b8 ec 9a 94 21>

// Buffer → 문자열
const backToString = buffer.toString('utf8');
console.log(backToString); // "안녕하세요!"
```

### Buffer의 다양한 메서드들

```javascript
const buffer = Buffer.from('Hello World');

// Buffer 길이 확인
console.log(buffer.length); // 11

// 특정 위치의 바이트 값 확인
console.log(buffer[0]); // 72 (H의 ASCII 코드)

// Buffer 일부 추출
const slice = buffer.slice(0, 5); // 처음 5바이트
console.log(slice.toString()); // "Hello"

// Buffer 복사
const copy = Buffer.alloc(buffer.length);
buffer.copy(copy);
console.log(copy.toString()); // "Hello World"
```

`buffer.slice()` 를 배열의 `slice` 처럼 생각하면 안 된다. **복사본이 아니라 같은 메모리를 가리키는 창(view)이다.**

```javascript
const b = Buffer.from('Hello World');
const s = b.slice(0, 5);

s[0] = 0x4a;          // 'J'
b.toString();         // 'Jello World'   ← 원본이 바뀌었다
```

잘라낸 조각을 다른 함수에 넘겨 놓고 그쪽에서 고치면 원본이 오염된다. 네트워크에서 받은 버퍼를 헤더와 본문으로 나눠 각각 처리하는 코드에서 실제로 만난다.

이름이 헷갈리는 원인이라 지금은 `subarray` 를 쓰는 것이 권장된다. 동작은 같고 이름이 정직하다. 진짜 복사가 필요하면 `Buffer.from(b.subarray(0, 5))` 처럼 명시한다.

바로 아래 파일 전송 예제의 `Buffer.concat` 도 이 차이와 이어진다. `concat` 은 **새 버퍼를 만들어 전부 복사한다.**

```javascript
socket.on('data', chunk => {
  receivedData = Buffer.concat([receivedData, chunk]);   // 조각마다 전체를 다시 복사
});
```

조각이 올 때마다 지금까지 받은 전부를 새 메모리에 옮긴다. 1MB 를 보내면 서버는 조각을 열 몇 번에 나눠 받는데, 그때마다 누적분 전체가 복사된다. 파일이 커질수록 복사량이 급격히 늘고, 순간적으로 옛 버퍼와 새 버퍼가 둘 다 메모리에 있게 된다.

조각을 배열에 모아 두었다가 마지막에 한 번만 합치면 복사가 한 번으로 끝난다.

```javascript
const chunks = [];
socket.on('data', chunk => chunks.push(chunk));
socket.on('end', () => {
  const data = Buffer.concat(chunks);
});
```

파일이 정말 크면 메모리에 다 담지 말고 `socket.pipe(fs.createWriteStream(path))` 로 흘려보낸다. 예제의 `fs.writeFileSync` 는 이벤트 핸들러 안에서 **이벤트 루프를 멈추기** 때문에, 그동안 다른 클라이언트의 요청이 전부 대기한다. 서버 코드에서 `Sync` 계열은 시작 시점 설정 읽기 정도로만 쓴다.

`Buffer.from(배열)` 이 값을 어떻게 다루는지도 알아 둘 만하다. 범위를 벗어난 수는 에러 없이 **잘린다.**

```javascript
Buffer.from([256, -1, 300, 65.9]);
// <Buffer 00 ff 2c 41>
//   256  → 0     (256 % 256)
//   -1   → 255
//   300  → 44
//   65.9 → 65    (소수점 버림)
```

센서 값이나 계산 결과를 그대로 바이트 배열에 넣으면 조용히 다른 값이 된다.

`Buffer.alloc` 과 `Buffer.allocUnsafe` 의 차이도 이름 그대로다. `alloc` 은 0 으로 채워 주고 `allocUnsafe` 는 **초기화를 건너뛴다.** 실제로 무엇이 들어 있을지는 그때그때 다르다 — 위에서 돌려 봤을 때는 마침 전부 0 이었지만, [Node 문서](https://nodejs.org/api/buffer.html#static-method-bufferallocunsafesize)는 옛 데이터가 남아 있을 수 있으니 **채우기 전에 읽거나 전송하지 말라**고 명시한다. 성능이 문제가 되는 것이 확인된 자리가 아니라면 `alloc` 을 쓴다.

---

## TCP란?

### TCP의 정의

TCP(Transmission Control Protocol)는 **인터넷에서 데이터를 안전하게 전송하기 위한 규칙**입니다.

### 🏗 TCP의 작동 원리

#### 1⃣ 연결 설정 (3-way Handshake)

```
클라이언트 → 서버: "연결하고 싶어요" (SYN)
서버 → 클라이언트: "좋아요, 연결해요" (SYN + ACK)  
클라이언트 → 서버: "알겠어요" (ACK)
```

#### 2⃣ 데이터 전송

- 데이터를 작은 조각(패킷)으로 나누어 전송
- 각 패킷에 번호를 붙여서 순서 보장
- 받은 패킷에 대해 "잘 받았어요" 신호 전송

#### 3⃣ 연결 종료

```
클라이언트 → 서버: "연결 끊을게요" (FIN)
서버 → 클라이언트: "알겠어요" (ACK)
서버 → 클라이언트: "저도 끊을게요" (FIN)
클라이언트 → 서버: "알겠어요" (ACK)
```

### TCP의 특징

| 특징 | 설명 | 장단점 |
|------|------|--------|
| **신뢰성** | 데이터가 손실되지 않도록 보장 | ✅ 안전함 |
| **순서 보장** | 본 순서대로 받음 | ✅ 정확함 |
| **연결 지향** | 전송 전에 연결을 먼저 설정 | ✅ 안정적 |
| **속도** | 안전성을 위해 속도가 상대적으로 느림 | ❌ 느림 |

### TCP vs UDP 비교

| 특징 | TCP | UDP |
|------|-----|-----|
| 연결 방식 | 연결 지향적 | 비연결 지향적 |
| 신뢰성 | 높음 (데이터 손실 방지) | 낮음 (데이터 손실 가능) |
| 순서 보장 | 보장 | 보장하지 않음 |
| 속도 | 상대적으로 느림 | 빠름 |
| 사용 예시 | 웹 브라우징, 이메일 | 실시간 게임, 스트리밍 |

---

## Buffer와 TCP의 관계

### 왜 Buffer와 TCP를 함께 사용할까?

1. **TCP는 바이너리 데이터를 주고받음**
   - 네트워크에서는 모든 데이터가 0과 1로 전송됩니다
   - Buffer가 이 바이너리 데이터를 다루는 도구입니다

2. **데이터 변환의 필요성**
   - 우리는 "Hello"라는 텍스트를 보내고 싶지만
   - 네트워크에서는 바이너리로 전송해야 합니다
   - Buffer가 이 변환을 도와줍니다

