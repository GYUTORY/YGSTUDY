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

