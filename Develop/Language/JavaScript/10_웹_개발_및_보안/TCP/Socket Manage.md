---
title: Socket Manage
tags: [language, javascript, 10웹개발및보안, tcp, socket-manage]
updated: 2025-08-10
---

## 배경


네트워크 소켓은 서버와 클라이언트가 데이터를 주고받는 통신 채널입니다. 웹사이트에 접속하거나, 채팅 앱을 사용하거나, 게임을 할 때마다 소켓이 생성되어 데이터를 전송합니다.

하지만 이 소켓들을 제대로 정리하지 않으면 서버에 심각한 문제가 발생할 수 있습니다. 마치 집에서 사용하지 않는 전자제품을 계속 켜두는 것처럼, 불필요한 소켓이 시스템 자원을 계속 차지하게 됩니다.

### 소켓이란?

소켓은 네트워크 통신의 양 끝단을 의미합니다. 쉽게 말해서 전화기의 송화기와 수화기 같은 역할을 합니다.

- **서버 소켓**: 클라이언트의 연결 요청을 기다리는 소켓
- **클라이언트 소켓**: 서버에 연결하여 데이터를 주고받는 소켓

### TCP 연결의 1:1 매핑

TCP 연결은 **1:1 매핑** 관계를 가집니다. 이는 하나의 TCP 연결이 정확히 하나의 소켓 쌍(클라이언트 소켓 + 서버 소켓)에 대응된다는 의미입니다.

**1:1 매핑이란?**
- 하나의 클라이언트가 서버에 연결할 때마다 **새로운 소켓 객체**가 생성됩니다
- 같은 클라이언트가 여러 번 연결하면 **각각 다른 소켓**이 됩니다
- 각 소켓은 고유한 파일 디스크립터를 가지며, 독립적으로 관리됩니다

**실제 예시:**
```javascript
const net = require('net');

const server = net.createServer((socket) => {
    // 매번 새로운 연결마다 새로운 소켓 객체가 생성됨
    console.log('새로운 소켓 생성:', socket.remoteAddress + ':' + socket.remotePort);
    
    // 각 소켓은 고유한 식별자를 가짐
    console.log('소켓 파일 디스크립터:', socket.fd);
    
    socket.on('data', (data) => {
        console.log(`소켓 ${socket.remotePort}에서 데이터 수신:`, data.toString());
    });
    
    socket.on('end', () => {
        console.log(`소켓 ${socket.remotePort} 연결 종료`);
    });
});

server.listen(3000);
```

**브라우저에서 같은 페이지를 여러 번 새로고침하면:**
```
새로운 소켓 생성: 127.0.0.1:54321
소켓 파일 디스크립터: 12
소켓 54321에서 데이터 수신: GET / HTTP/1.1
소켓 54321 연결 종료

새로운 소켓 생성: 127.0.0.1:54322  // 다른 포트 번호
소켓 파일 디스크립터: 13             // 다른 파일 디스크립터
소켓 54322에서 데이터 수신: GET / HTTP/1.1
소켓 54322 연결 종료
```

**1:1 매핑의 장점:**
- 각 연결이 독립적으로 관리되어 안전함
- 한 연결의 문제가 다른 연결에 영향을 주지 않음
- 연결별로 개별적인 설정과 상태 관리 가능

**1:1 매핑의 단점:**
- 연결 수가 많아지면 시스템 자원을 많이 사용
- 각 소켓마다 메모리와 파일 디스크립터를 소모
- 연결 관리의 복잡성 증가

이러한 1:1 매핑 특성 때문에 소켓 관리가 매우 중요합니다. 각 연결이 독립적이므로, 연결이 종료되면 해당 소켓을 반드시 정리해야 시스템 자원이 고갈되지 않습니다.

### 왜 소켓 관리가 중요한가?

실제 서비스에서는 수백, 수천 개의 소켓이 동시에 연결될 수 있습니다. 각 소켓은 시스템의 메모리와 파일 디스크립터를 사용하는데, 이를 제대로 정리하지 않으면 서버가 다운될 수 있습니다.

---


소켓은 네트워크 통신의 양 끝단을 의미합니다. 쉽게 말해서 전화기의 송화기와 수화기 같은 역할을 합니다.

- **서버 소켓**: 클라이언트의 연결 요청을 기다리는 소켓
- **클라이언트 소켓**: 서버에 연결하여 데이터를 주고받는 소켓


실제 서비스에서는 수백, 수천 개의 소켓이 동시에 연결될 수 있습니다. 각 소켓은 시스템의 메모리와 파일 디스크립터를 사용하는데, 이를 제대로 정리하지 않으면 서버가 다운될 수 있습니다.

---


### 시스템 자원 고갈 문제

**파일 디스크립터(File Descriptor)란?**
- 운영체제가 파일이나 네트워크 연결을 추적하기 위해 사용하는 번호표 같은 것입니다
- 각 소켓은 하나의 파일 디스크립터를 사용합니다
- 시스템마다 사용할 수 있는 파일 디스크립터의 개수가 제한되어 있습니다

**파일 디스크립터 제한 확인 방법:**
```bash


네트워크 소켓은 서버와 클라이언트가 데이터를 주고받는 통신 채널입니다. 웹사이트에 접속하거나, 채팅 앱을 사용하거나, 게임을 할 때마다 소켓이 생성되어 데이터를 전송합니다.

하지만 이 소켓들을 제대로 정리하지 않으면 서버에 심각한 문제가 발생할 수 있습니다. 마치 집에서 사용하지 않는 전자제품을 계속 켜두는 것처럼, 불필요한 소켓이 시스템 자원을 계속 차지하게 됩니다.

### 소켓이란?

소켓은 네트워크 통신의 양 끝단을 의미합니다. 쉽게 말해서 전화기의 송화기와 수화기 같은 역할을 합니다.

- **서버 소켓**: 클라이언트의 연결 요청을 기다리는 소켓
- **클라이언트 소켓**: 서버에 연결하여 데이터를 주고받는 소켓

### TCP 연결의 1:1 매핑

TCP 연결은 **1:1 매핑** 관계를 가집니다. 이는 하나의 TCP 연결이 정확히 하나의 소켓 쌍(클라이언트 소켓 + 서버 소켓)에 대응된다는 의미입니다.

**1:1 매핑이란?**
- 하나의 클라이언트가 서버에 연결할 때마다 **새로운 소켓 객체**가 생성됩니다
- 같은 클라이언트가 여러 번 연결하면 **각각 다른 소켓**이 됩니다
- 각 소켓은 고유한 파일 디스크립터를 가지며, 독립적으로 관리됩니다

**실제 예시:**
```javascript
const net = require('net');

const server = net.createServer((socket) => {
    // 매번 새로운 연결마다 새로운 소켓 객체가 생성됨
    console.log('새로운 소켓 생성:', socket.remoteAddress + ':' + socket.remotePort);
    
    // 각 소켓은 고유한 식별자를 가짐
    console.log('소켓 파일 디스크립터:', socket.fd);
    
    socket.on('data', (data) => {
        console.log(`소켓 ${socket.remotePort}에서 데이터 수신:`, data.toString());
    });
    
    socket.on('end', () => {
        console.log(`소켓 ${socket.remotePort} 연결 종료`);
    });
});

server.listen(3000);
```

**브라우저에서 같은 페이지를 여러 번 새로고침하면:**
```
새로운 소켓 생성: 127.0.0.1:54321
소켓 파일 디스크립터: 12
소켓 54321에서 데이터 수신: GET / HTTP/1.1
소켓 54321 연결 종료

새로운 소켓 생성: 127.0.0.1:54322  // 다른 포트 번호
소켓 파일 디스크립터: 13             // 다른 파일 디스크립터
소켓 54322에서 데이터 수신: GET / HTTP/1.1
소켓 54322 연결 종료
```

**1:1 매핑의 장점:**
- 각 연결이 독립적으로 관리되어 안전함
- 한 연결의 문제가 다른 연결에 영향을 주지 않음
- 연결별로 개별적인 설정과 상태 관리 가능

**1:1 매핑의 단점:**
- 연결 수가 많아지면 시스템 자원을 많이 사용
- 각 소켓마다 메모리와 파일 디스크립터를 소모
- 연결 관리의 복잡성 증가

이러한 1:1 매핑 특성 때문에 소켓 관리가 매우 중요합니다. 각 연결이 독립적이므로, 연결이 종료되면 해당 소켓을 반드시 정리해야 시스템 자원이 고갈되지 않습니다.

### 왜 소켓 관리가 중요한가?

실제 서비스에서는 수백, 수천 개의 소켓이 동시에 연결될 수 있습니다. 각 소켓은 시스템의 메모리와 파일 디스크립터를 사용하는데, 이를 제대로 정리하지 않으면 서버가 다운될 수 있습니다.

---


소켓은 네트워크 통신의 양 끝단을 의미합니다. 쉽게 말해서 전화기의 송화기와 수화기 같은 역할을 합니다.

- **서버 소켓**: 클라이언트의 연결 요청을 기다리는 소켓
- **클라이언트 소켓**: 서버에 연결하여 데이터를 주고받는 소켓


실제 서비스에서는 수백, 수천 개의 소켓이 동시에 연결될 수 있습니다. 각 소켓은 시스템의 메모리와 파일 디스크립터를 사용하는데, 이를 제대로 정리하지 않으면 서버가 다운될 수 있습니다.

---


### 시스템 자원 고갈 문제

**파일 디스크립터(File Descriptor)란?**
- 운영체제가 파일이나 네트워크 연결을 추적하기 위해 사용하는 번호표 같은 것입니다
- 각 소켓은 하나의 파일 디스크립터를 사용합니다
- 시스템마다 사용할 수 있는 파일 디스크립터의 개수가 제한되어 있습니다

**파일 디스크립터 제한 확인 방법:**
```bash


**파일 디스크립터(File Descriptor)란?**
- 운영체제가 파일이나 네트워크 연결을 추적하기 위해 사용하는 번호표 같은 것입니다
- 각 소켓은 하나의 파일 디스크립터를 사용합니다
- 시스템마다 사용할 수 있는 파일 디스크립터의 개수가 제한되어 있습니다

**파일 디스크립터 제한 확인 방법:**
```bash


소켓 객체는 내부적으로 데이터를 저장하는 버퍼와 상태 정보를 가지고 있습니다. 이 객체들이 제대로 정리되지 않으면 메모리에 계속 쌓이게 됩니다.

**메모리 누수가 발생하는 이유:**
- JavaScript의 가비지 컬렉터는 참조가 남아있는 객체를 메모리에서 해제하지 않습니다
- 소켓 객체에 대한 참조가 남아있으면, 연결이 끊어져도 메모리에서 제거되지 않습니다
- 시간이 지날수록 사용하지 않는 소켓 객체들이 메모리를 계속 차지하게 됩니다

**메모리 누수 예시:**
```javascript
// 문제가 있는 코드
const activeConnections = [];

const server = net.createServer((socket) => {
    activeConnections.push(socket); // 소켓을 배열에 추가
    
    socket.on('data', (data) => {
        // 데이터 처리
    });
    
    // 연결이 끊어져도 배열에서 제거하지 않음
    // 이렇게 되면 activeConnections 배열이 계속 커짐
});
```


정리되지 않은 소켓들이 많아지면:
- 새로운 연결 요청을 처리할 수 없게 됩니다
- 서버 응답 속도가 느려집니다
- 전체 시스템이 불안정해집니다

---


### 연결 종료 감지 및 정리

소켓의 생명주기 이벤트를 활용하여 연결이 종료될 때 자동으로 정리하는 방법입니다.

**주요 이벤트들:**
- `'end'`: 클라이언트가 연결을 정상적으로 종료할 때
- `'error'`: 소켓에서 에러가 발생했을 때  
- `'close'`: 소켓이 완전히 닫혔을 때 (에러로 인한 종료인지 확인 가능)

```javascript
const net = require('net');

// 활성 소켓들을 추적하는 Set 사용
// Set을 사용하는 이유: 중복 제거, 빠른 검색/삭제
const activeSockets = new Set();

const server = net.createServer((socket) => {
    console.log('새로운 클라이언트 연결됨');
    
    // 새 소켓을 추적 목록에 추가
    activeSockets.add(socket);
    
    // 클라이언트로부터 데이터 수신
    socket.on('data', (data) => {
        console.log('받은 데이터:', data.toString());
        
        // 에코 서버처럼 데이터를 다시 보내기
        socket.write(`서버 응답: ${data.toString()}`);
    });
    
    // 클라이언트가 연결을 종료할 때
    socket.on('end', () => {
        console.log('클라이언트가 연결을 종료했습니다');
        activeSockets.delete(socket);
    });
    
    // 소켓에서 에러가 발생했을 때
    socket.on('error', (err) => {
        console.error('소켓 에러:', err.message);
        activeSockets.delete(socket);
    });
    
    // 소켓이 완전히 닫혔을 때
    socket.on('close', (hadError) => {
        console.log('소켓이 닫혔습니다', hadError ? '(에러로 인해)' : '');
        activeSockets.delete(socket);
    });
});

server.listen(3000, () => {
    console.log('서버가 포트 3000에서 실행 중입니다');
});

// 현재 활성 연결 수 확인 (모니터링용)
setInterval(() => {
    console.log(`현재 활성 연결 수: ${activeSockets.size}`);
}, 5000);
```

### 타임아웃 설정으로 오래된 연결 자동 정리

클라이언트가 연결을 끊지 않고 그대로 두는 경우를 대비해 일정 시간 후 자동으로 연결을 종료하는 방법입니다.

**타임아웃이 필요한 이유:**
- 클라이언트가 비정상적으로 종료된 경우
- 네트워크 문제로 연결이 끊어진 경우
- 악의적인 클라이언트가 연결을 계속 유지하는 경우

```javascript
const server = net.createServer((socket) => {
    // 30초 타임아웃 설정 (밀리초 단위)
    socket.setTimeout(30000);
    
    socket.on('data', (data) => {
        // 데이터를 받으면 타임아웃을 리셋
        // 이렇게 하면 활발히 통신하는 연결은 종료되지 않음
        socket.setTimeout(30000);
        console.log('데이터 수신:', data.toString());
    });
    
    // 타임아웃 발생 시 연결 종료
    socket.on('timeout', () => {
        console.log('타임아웃 발생 - 연결 종료');
        socket.end(); // 연결 종료
    });
    
    // 기타 이벤트 처리...
    socket.on('end', () => {
        console.log('연결 종료');
    });
    
    socket.on('error', (err) => {
        console.error('소켓 에러:', err.message);
    });
});
```

### 명시적 참조 해제

JavaScript의 가비지 컬렉터가 메모리를 회수할 수 있도록 객체 참조를 명시적으로 해제하는 방법입니다.

**가비지 컬렉션이란?**
- JavaScript 엔진이 더 이상 사용되지 않는 객체를 자동으로 메모리에서 제거하는 기능
- 하지만 참조가 남아있으면 객체가 사용 중이라고 판단하여 제거하지 않음

```javascript
let clientSocket = null;

function connectToServer() {
    clientSocket = net.createConnection({ port: 3000 }, () => {
        console.log('서버에 연결되었습니다');
    });
    
    clientSocket.on('data', (data) => {
        console.log('서버로부터 받은 데이터:', data.toString());
    });
    
    clientSocket.on('end', () => {
        console.log('서버 연결이 종료되었습니다');
        // 참조 해제로 가비지 컬렉션이 메모리를 회수할 수 있도록 함
        clientSocket = null;
    });
    
    clientSocket.on('error', (err) => {
        console.error('연결 에러:', err.message);
        clientSocket = null;
    });
}

// 연결 종료 함수
function disconnectFromServer() {
    if (clientSocket) {
        clientSocket.end(); // 소켓 종료
        clientSocket = null; // 참조 해제
    }
}
```

---


소켓의 생명주기 이벤트를 활용하여 연결이 종료될 때 자동으로 정리하는 방법입니다.

**주요 이벤트들:**
- `'end'`: 클라이언트가 연결을 정상적으로 종료할 때
- `'error'`: 소켓에서 에러가 발생했을 때  
- `'close'`: 소켓이 완전히 닫혔을 때 (에러로 인한 종료인지 확인 가능)

```javascript
const net = require('net');

// 활성 소켓들을 추적하는 Set 사용
// Set을 사용하는 이유: 중복 제거, 빠른 검색/삭제
const activeSockets = new Set();

const server = net.createServer((socket) => {
    console.log('새로운 클라이언트 연결됨');
    
    // 새 소켓을 추적 목록에 추가
    activeSockets.add(socket);
    
    // 클라이언트로부터 데이터 수신
    socket.on('data', (data) => {
        console.log('받은 데이터:', data.toString());
        
        // 에코 서버처럼 데이터를 다시 보내기
        socket.write(`서버 응답: ${data.toString()}`);
    });
    
    // 클라이언트가 연결을 종료할 때
    socket.on('end', () => {
        console.log('클라이언트가 연결을 종료했습니다');
        activeSockets.delete(socket);
    });
    
    // 소켓에서 에러가 발생했을 때
    socket.on('error', (err) => {
        console.error('소켓 에러:', err.message);
        activeSockets.delete(socket);
    });
    
    // 소켓이 완전히 닫혔을 때
    socket.on('close', (hadError) => {
        console.log('소켓이 닫혔습니다', hadError ? '(에러로 인해)' : '');
        activeSockets.delete(socket);
    });
});

server.listen(3000, () => {
    console.log('서버가 포트 3000에서 실행 중입니다');
});

// 현재 활성 연결 수 확인 (모니터링용)
setInterval(() => {
    console.log(`현재 활성 연결 수: ${activeSockets.size}`);
}, 5000);
```


클라이언트가 연결을 끊지 않고 그대로 두는 경우를 대비해 일정 시간 후 자동으로 연결을 종료하는 방법입니다.

**타임아웃이 필요한 이유:**
- 클라이언트가 비정상적으로 종료된 경우
- 네트워크 문제로 연결이 끊어진 경우
- 악의적인 클라이언트가 연결을 계속 유지하는 경우

```javascript
const server = net.createServer((socket) => {
    // 30초 타임아웃 설정 (밀리초 단위)
    socket.setTimeout(30000);
    
    socket.on('data', (data) => {
        // 데이터를 받으면 타임아웃을 리셋
        // 이렇게 하면 활발히 통신하는 연결은 종료되지 않음
        socket.setTimeout(30000);
        console.log('데이터 수신:', data.toString());
    });
    
    // 타임아웃 발생 시 연결 종료
    socket.on('timeout', () => {
        console.log('타임아웃 발생 - 연결 종료');
        socket.end(); // 연결 종료
    });
    
    // 기타 이벤트 처리...
    socket.on('end', () => {
        console.log('연결 종료');
    });
    
    socket.on('error', (err) => {
        console.error('소켓 에러:', err.message);
    });
});
```


JavaScript의 가비지 컬렉터가 메모리를 회수할 수 있도록 객체 참조를 명시적으로 해제하는 방법입니다.

**가비지 컬렉션이란?**
- JavaScript 엔진이 더 이상 사용되지 않는 객체를 자동으로 메모리에서 제거하는 기능
- 하지만 참조가 남아있으면 객체가 사용 중이라고 판단하여 제거하지 않음

```javascript
let clientSocket = null;

function connectToServer() {
    clientSocket = net.createConnection({ port: 3000 }, () => {
        console.log('서버에 연결되었습니다');
    });
    
    clientSocket.on('data', (data) => {
        console.log('서버로부터 받은 데이터:', data.toString());
    });
    
    clientSocket.on('end', () => {
        console.log('서버 연결이 종료되었습니다');
        // 참조 해제로 가비지 컬렉션이 메모리를 회수할 수 있도록 함
        clientSocket = null;
    });
    
    clientSocket.on('error', (err) => {
        console.error('연결 에러:', err.message);
        clientSocket = null;
    });
}

// 연결 종료 함수
function disconnectFromServer() {
    if (clientSocket) {
        clientSocket.end(); // 소켓 종료
        clientSocket = null; // 참조 해제
    }
}
```

---


### 시스템 자원 부족
- 새로운 클라이언트 연결을 받을 수 없음
- 서버가 응답하지 않게 됨

### 메모리 부족으로 인한 서버 중단
- 운영체제가 메모리 부족으로 프로세스를 강제 종료
- 서비스 중단 발생

### 디버깅의 어려움
- 어떤 소켓이 문제인지 파악하기 어려움
- 서버 동작 예측이 불가능

---

- 새로운 클라이언트 연결을 받을 수 없음
- 서버가 응답하지 않게 됨

- 운영체제가 메모리 부족으로 프로세스를 강제 종료
- 서비스 중단 발생

- 어떤 소켓이 문제인지 파악하기 어려움
- 서버 동작 예측이 불가능

---


### 핵심 포인트
1. **소켓은 반드시 정리해야 한다** - 사용이 끝나면 명시적으로 닫기
2. **이벤트 리스너 활용** - 'end', 'error', 'close' 이벤트로 정리 시점 감지
3. **타임아웃 설정** - 오래된 연결은 자동으로 종료
4. **참조 해제** - JavaScript 객체 참조를 null로 설정

### 실무에서 주의할 점
- 소켓 정리는 서버 안정성의 핵심
- 개발 단계에서부터 소켓 관리 패턴 적용
- 정기적인 모니터링으로 소켓 상태 확인

### 추가로 알아두면 좋은 것들

**소켓 상태 확인 명령어:**
```bash

1. **소켓은 반드시 정리해야 한다** - 사용이 끝나면 명시적으로 닫기
2. **이벤트 리스너 활용** - 'end', 'error', 'close' 이벤트로 정리 시점 감지
3. **타임아웃 설정** - 오래된 연결은 자동으로 종료
4. **참조 해제** - JavaScript 객체 참조를 null로 설정

- 소켓 정리는 서버 안정성의 핵심
- 개발 단계에서부터 소켓 관리 패턴 적용
- 정기적인 모니터링으로 소켓 상태 확인


**소켓 상태 확인 명령어:**
```bash

lsof -i :3000

ls -l /proc/[PID]/fd | wc -l
```

**Node.js에서 소켓 정보 확인:**
```javascript
// 서버의 연결 정보 확인
server.getConnections((err, count) => {
    console.log(`현재 연결 수: ${count}`);
});
```

소켓 관리는 처음에는 복잡해 보일 수 있지만, 일관된 패턴을 적용하면 안정적인 네트워크 서버를 구축할 수 있습니다.

---


**파일 디스크립터(File Descriptor)란?**
- 운영체제가 파일이나 네트워크 연결을 추적하기 위해 사용하는 번호표 같은 것입니다
- 각 소켓은 하나의 파일 디스크립터를 사용합니다
- 시스템마다 사용할 수 있는 파일 디스크립터의 개수가 제한되어 있습니다

**파일 디스크립터 제한 확인 방법:**
```bash


네트워크 소켓은 서버와 클라이언트가 데이터를 주고받는 통신 채널입니다. 웹사이트에 접속하거나, 채팅 앱을 사용하거나, 게임을 할 때마다 소켓이 생성되어 데이터를 전송합니다.

하지만 이 소켓들을 제대로 정리하지 않으면 서버에 심각한 문제가 발생할 수 있습니다. 마치 집에서 사용하지 않는 전자제품을 계속 켜두는 것처럼, 불필요한 소켓이 시스템 자원을 계속 차지하게 됩니다.


소켓은 네트워크 통신의 양 끝단을 의미합니다. 쉽게 말해서 전화기의 송화기와 수화기 같은 역할을 합니다.

- **서버 소켓**: 클라이언트의 연결 요청을 기다리는 소켓
- **클라이언트 소켓**: 서버에 연결하여 데이터를 주고받는 소켓


실제 서비스에서는 수백, 수천 개의 소켓이 동시에 연결될 수 있습니다. 각 소켓은 시스템의 메모리와 파일 디스크립터를 사용하는데, 이를 제대로 정리하지 않으면 서버가 다운될 수 있습니다.

---


소켓은 네트워크 통신의 양 끝단을 의미합니다. 쉽게 말해서 전화기의 송화기와 수화기 같은 역할을 합니다.

- **서버 소켓**: 클라이언트의 연결 요청을 기다리는 소켓
- **클라이언트 소켓**: 서버에 연결하여 데이터를 주고받는 소켓


실제 서비스에서는 수백, 수천 개의 소켓이 동시에 연결될 수 있습니다. 각 소켓은 시스템의 메모리와 파일 디스크립터를 사용하는데, 이를 제대로 정리하지 않으면 서버가 다운될 수 있습니다.

---



**파일 디스크립터(File Descriptor)란?**
- 운영체제가 파일이나 네트워크 연결을 추적하기 위해 사용하는 번호표 같은 것입니다
- 각 소켓은 하나의 파일 디스크립터를 사용합니다
- 시스템마다 사용할 수 있는 파일 디스크립터의 개수가 제한되어 있습니다

**파일 디스크립터 제한 확인 방법:**
```bash


**파일 디스크립터(File Descriptor)란?**
- 운영체제가 파일이나 네트워크 연결을 추적하기 위해 사용하는 번호표 같은 것입니다
- 각 소켓은 하나의 파일 디스크립터를 사용합니다
- 시스템마다 사용할 수 있는 파일 디스크립터의 개수가 제한되어 있습니다

**파일 디스크립터 제한 확인 방법:**
```bash


소켓 객체는 내부적으로 데이터를 저장하는 버퍼와 상태 정보를 가지고 있습니다. 이 객체들이 제대로 정리되지 않으면 메모리에 계속 쌓이게 됩니다.

**메모리 누수가 발생하는 이유:**
- JavaScript의 가비지 컬렉터는 참조가 남아있는 객체를 메모리에서 해제하지 않습니다
- 소켓 객체에 대한 참조가 남아있으면, 연결이 끊어져도 메모리에서 제거되지 않습니다
- 시간이 지날수록 사용하지 않는 소켓 객체들이 메모리를 계속 차지하게 됩니다

**메모리 누수 예시:**
```javascript
// 문제가 있는 코드
const activeConnections = [];

const server = net.createServer((socket) => {
    activeConnections.push(socket); // 소켓을 배열에 추가
    
    socket.on('data', (data) => {
        // 데이터 처리
    });
    
    // 연결이 끊어져도 배열에서 제거하지 않음
    // 이렇게 되면 activeConnections 배열이 계속 커짐
});
```


정리되지 않은 소켓들이 많아지면:
- 새로운 연결 요청을 처리할 수 없게 됩니다
- 서버 응답 속도가 느려집니다
- 전체 시스템이 불안정해집니다

---



소켓의 생명주기 이벤트를 활용하여 연결이 종료될 때 자동으로 정리하는 방법입니다.

**주요 이벤트들:**
- `'end'`: 클라이언트가 연결을 정상적으로 종료할 때
- `'error'`: 소켓에서 에러가 발생했을 때  
- `'close'`: 소켓이 완전히 닫혔을 때 (에러로 인한 종료인지 확인 가능)

```javascript
const net = require('net');

// 활성 소켓들을 추적하는 Set 사용
// Set을 사용하는 이유: 중복 제거, 빠른 검색/삭제
const activeSockets = new Set();

const server = net.createServer((socket) => {
    console.log('새로운 클라이언트 연결됨');
    
    // 새 소켓을 추적 목록에 추가
    activeSockets.add(socket);
    
    // 클라이언트로부터 데이터 수신
    socket.on('data', (data) => {
        console.log('받은 데이터:', data.toString());
        
        // 에코 서버처럼 데이터를 다시 보내기
        socket.write(`서버 응답: ${data.toString()}`);
    });
    
    // 클라이언트가 연결을 종료할 때
    socket.on('end', () => {
        console.log('클라이언트가 연결을 종료했습니다');
        activeSockets.delete(socket);
    });
    
    // 소켓에서 에러가 발생했을 때
    socket.on('error', (err) => {
        console.error('소켓 에러:', err.message);
        activeSockets.delete(socket);
    });
    
    // 소켓이 완전히 닫혔을 때
    socket.on('close', (hadError) => {
        console.log('소켓이 닫혔습니다', hadError ? '(에러로 인해)' : '');
        activeSockets.delete(socket);
    });
});

server.listen(3000, () => {
    console.log('서버가 포트 3000에서 실행 중입니다');
});

// 현재 활성 연결 수 확인 (모니터링용)
setInterval(() => {
    console.log(`현재 활성 연결 수: ${activeSockets.size}`);
}, 5000);
```


클라이언트가 연결을 끊지 않고 그대로 두는 경우를 대비해 일정 시간 후 자동으로 연결을 종료하는 방법입니다.

**타임아웃이 필요한 이유:**
- 클라이언트가 비정상적으로 종료된 경우
- 네트워크 문제로 연결이 끊어진 경우
- 악의적인 클라이언트가 연결을 계속 유지하는 경우

```javascript
const server = net.createServer((socket) => {
    // 30초 타임아웃 설정 (밀리초 단위)
    socket.setTimeout(30000);
    
    socket.on('data', (data) => {
        // 데이터를 받으면 타임아웃을 리셋
        // 이렇게 하면 활발히 통신하는 연결은 종료되지 않음
        socket.setTimeout(30000);
        console.log('데이터 수신:', data.toString());
    });
    
    // 타임아웃 발생 시 연결 종료
    socket.on('timeout', () => {
        console.log('타임아웃 발생 - 연결 종료');
        socket.end(); // 연결 종료
    });
    
    // 기타 이벤트 처리...
    socket.on('end', () => {
        console.log('연결 종료');
    });
    
    socket.on('error', (err) => {
        console.error('소켓 에러:', err.message);
    });
});
```


JavaScript의 가비지 컬렉터가 메모리를 회수할 수 있도록 객체 참조를 명시적으로 해제하는 방법입니다.

**가비지 컬렉션이란?**
- JavaScript 엔진이 더 이상 사용되지 않는 객체를 자동으로 메모리에서 제거하는 기능
- 하지만 참조가 남아있으면 객체가 사용 중이라고 판단하여 제거하지 않음

```javascript
let clientSocket = null;

function connectToServer() {
    clientSocket = net.createConnection({ port: 3000 }, () => {
        console.log('서버에 연결되었습니다');
    });
    
    clientSocket.on('data', (data) => {
        console.log('서버로부터 받은 데이터:', data.toString());
    });
    
    clientSocket.on('end', () => {
        console.log('서버 연결이 종료되었습니다');
        // 참조 해제로 가비지 컬렉션이 메모리를 회수할 수 있도록 함
        clientSocket = null;
    });
    
    clientSocket.on('error', (err) => {
        console.error('연결 에러:', err.message);
        clientSocket = null;
    });
}

// 연결 종료 함수
function disconnectFromServer() {
    if (clientSocket) {
        clientSocket.end(); // 소켓 종료
        clientSocket = null; // 참조 해제
    }
}
```

---


소켓의 생명주기 이벤트를 활용하여 연결이 종료될 때 자동으로 정리하는 방법입니다.

**주요 이벤트들:**
- `'end'`: 클라이언트가 연결을 정상적으로 종료할 때
- `'error'`: 소켓에서 에러가 발생했을 때  
- `'close'`: 소켓이 완전히 닫혔을 때 (에러로 인한 종료인지 확인 가능)

```javascript
const net = require('net');

// 활성 소켓들을 추적하는 Set 사용
// Set을 사용하는 이유: 중복 제거, 빠른 검색/삭제
const activeSockets = new Set();

const server = net.createServer((socket) => {
    console.log('새로운 클라이언트 연결됨');
    
    // 새 소켓을 추적 목록에 추가
    activeSockets.add(socket);
    
    // 클라이언트로부터 데이터 수신
    socket.on('data', (data) => {
        console.log('받은 데이터:', data.toString());
        
        // 에코 서버처럼 데이터를 다시 보내기
        socket.write(`서버 응답: ${data.toString()}`);
    });
    
    // 클라이언트가 연결을 종료할 때
    socket.on('end', () => {
        console.log('클라이언트가 연결을 종료했습니다');
        activeSockets.delete(socket);
    });
    
    // 소켓에서 에러가 발생했을 때
    socket.on('error', (err) => {
        console.error('소켓 에러:', err.message);
        activeSockets.delete(socket);
    });
    
    // 소켓이 완전히 닫혔을 때
    socket.on('close', (hadError) => {
        console.log('소켓이 닫혔습니다', hadError ? '(에러로 인해)' : '');
        activeSockets.delete(socket);
    });
});

server.listen(3000, () => {
    console.log('서버가 포트 3000에서 실행 중입니다');
});

// 현재 활성 연결 수 확인 (모니터링용)
setInterval(() => {
    console.log(`현재 활성 연결 수: ${activeSockets.size}`);
}, 5000);
```


클라이언트가 연결을 끊지 않고 그대로 두는 경우를 대비해 일정 시간 후 자동으로 연결을 종료하는 방법입니다.

**타임아웃이 필요한 이유:**
- 클라이언트가 비정상적으로 종료된 경우
- 네트워크 문제로 연결이 끊어진 경우
- 악의적인 클라이언트가 연결을 계속 유지하는 경우

```javascript
const server = net.createServer((socket) => {
    // 30초 타임아웃 설정 (밀리초 단위)
    socket.setTimeout(30000);
    
    socket.on('data', (data) => {
        // 데이터를 받으면 타임아웃을 리셋
        // 이렇게 하면 활발히 통신하는 연결은 종료되지 않음
        socket.setTimeout(30000);
        console.log('데이터 수신:', data.toString());
    });
    
    // 타임아웃 발생 시 연결 종료
    socket.on('timeout', () => {
        console.log('타임아웃 발생 - 연결 종료');
        socket.end(); // 연결 종료
    });
    
    // 기타 이벤트 처리...
    socket.on('end', () => {
        console.log('연결 종료');
    });
    
    socket.on('error', (err) => {
        console.error('소켓 에러:', err.message);
    });
});
```


JavaScript의 가비지 컬렉터가 메모리를 회수할 수 있도록 객체 참조를 명시적으로 해제하는 방법입니다.

**가비지 컬렉션이란?**
- JavaScript 엔진이 더 이상 사용되지 않는 객체를 자동으로 메모리에서 제거하는 기능
- 하지만 참조가 남아있으면 객체가 사용 중이라고 판단하여 제거하지 않음

```javascript
let clientSocket = null;

function connectToServer() {
    clientSocket = net.createConnection({ port: 3000 }, () => {
        console.log('서버에 연결되었습니다');
    });
    
    clientSocket.on('data', (data) => {
        console.log('서버로부터 받은 데이터:', data.toString());
    });
    
    clientSocket.on('end', () => {
        console.log('서버 연결이 종료되었습니다');
        // 참조 해제로 가비지 컬렉션이 메모리를 회수할 수 있도록 함
        clientSocket = null;
    });
    
    clientSocket.on('error', (err) => {
        console.error('연결 에러:', err.message);
        clientSocket = null;
    });
}

// 연결 종료 함수
function disconnectFromServer() {
    if (clientSocket) {
        clientSocket.end(); // 소켓 종료
        clientSocket = null; // 참조 해제
    }
}
```

---


- 새로운 클라이언트 연결을 받을 수 없음
- 서버가 응답하지 않게 됨

- 운영체제가 메모리 부족으로 프로세스를 강제 종료
- 서비스 중단 발생

- 어떤 소켓이 문제인지 파악하기 어려움
- 서버 동작 예측이 불가능

---

- 새로운 클라이언트 연결을 받을 수 없음
- 서버가 응답하지 않게 됨

- 운영체제가 메모리 부족으로 프로세스를 강제 종료
- 서비스 중단 발생

- 어떤 소켓이 문제인지 파악하기 어려움
- 서버 동작 예측이 불가능

---


1. **소켓은 반드시 정리해야 한다** - 사용이 끝나면 명시적으로 닫기
2. **이벤트 리스너 활용** - 'end', 'error', 'close' 이벤트로 정리 시점 감지
3. **타임아웃 설정** - 오래된 연결은 자동으로 종료
4. **참조 해제** - JavaScript 객체 참조를 null로 설정

- 소켓 정리는 서버 안정성의 핵심
- 개발 단계에서부터 소켓 관리 패턴 적용
- 정기적인 모니터링으로 소켓 상태 확인


**소켓 상태 확인 명령어:**
```bash

1. **소켓은 반드시 정리해야 한다** - 사용이 끝나면 명시적으로 닫기
2. **이벤트 리스너 활용** - 'end', 'error', 'close' 이벤트로 정리 시점 감지
3. **타임아웃 설정** - 오래된 연결은 자동으로 종료
4. **참조 해제** - JavaScript 객체 참조를 null로 설정

- 소켓 정리는 서버 안정성의 핵심
- 개발 단계에서부터 소켓 관리 패턴 적용
- 정기적인 모니터링으로 소켓 상태 확인


**소켓 상태 확인 명령어:**
```bash

lsof -i :3000

ls -l /proc/[PID]/fd | wc -l
```

**Node.js에서 소켓 정보 확인:**
```javascript
// 서버의 연결 정보 확인
server.getConnections((err, count) => {
    console.log(`현재 연결 수: ${count}`);
});
```

소켓 관리는 처음에는 복잡해 보일 수 있지만, 일관된 패턴을 적용하면 안정적인 네트워크 서버를 구축할 수 있습니다.

---















# macOS/Linux에서 확인
ulimit -n

# 일반적으로 256~1024개 정도로 제한되어 있음
```

**실제 상황 예시:**
만약 파일 디스크립터 제한이 256개라면, 256개의 소켓 연결만 동시에 처리할 수 있습니다. 그 이상 연결되면 "too many open files" 에러가 발생합니다.

**문제 상황:**
```javascript
// 잘못된 예시 - 소켓을 정리하지 않는 경우
const net = require('net');

const server = net.createServer((socket) => {
    // 클라이언트 연결 처리
    socket.on('data', (data) => {
        console.log('받은 데이터:', data.toString());
        // 소켓을 닫지 않고 그대로 둠
    });
    
    // 연결 종료나 에러 처리가 없음
});

server.listen(3000);
```

이렇게 하면 클라이언트가 연결을 끊어도 소켓이 계속 남아있어서, 결국 다음과 같은 에러가 발생합니다:

```
Error: EMFILE: too many open files
```

