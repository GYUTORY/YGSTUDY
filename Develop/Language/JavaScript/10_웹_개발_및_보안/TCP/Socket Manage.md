---
title: Socket Manage
tags: [language, javascript, 10웹개발및보안, tcp, socket-manage]
updated: 2025-11-01
---

## 소켓 관리의 필요성

네트워크 소켓은 서버와 클라이언트가 데이터를 주고받는 통신 채널입니다. 웹사이트에 접속하거나, 채팅 앱을 사용하거나, 게임을 할 때마다 소켓이 생성되어 데이터를 전송합니다.

하지만 이 소켓들을 제대로 정리하지 않으면 서버에 심각한 문제가 발생할 수 있습니다. 마치 집에서 사용하지 않는 전자제품을 계속 켜두는 것처럼, 불필요한 소켓이 시스템 자원을 계속 차지하게 됩니다.

---

## 소켓의 기본 개념

### 소켓이란?

소켓(Socket)은 네트워크 통신의 종착점(endpoint)입니다. 두 프로그램이 네트워크를 통해 통신하려면 양쪽 끝에 소켓이 필요합니다. 전화 통화를 하려면 양쪽에 전화기가 필요한 것과 같은 원리입니다.

**소켓의 종류:**
- **서버 소켓(Listening Socket)**: 클라이언트의 연결 요청을 기다리는 소켓. 특정 포트에 바인딩되어 여러 클라이언트의 연결을 받아들입니다.
- **클라이언트 소켓(Connected Socket)**: 서버에 연결하여 실제로 데이터를 주고받는 소켓. 각 연결마다 독립적인 소켓이 생성됩니다.

### 소켓의 내부 구조

소켓은 단순한 통신 채널이 아니라, 여러 구성 요소를 가진 복잡한 객체입니다:

**1. 파일 디스크립터(File Descriptor)**
- UNIX 계열 운영체제에서 소켓은 파일처럼 다뤄집니다
- 운영체제가 각 소켓에 고유한 번호를 부여하는데, 이것이 파일 디스크립터입니다
- 0, 1, 2는 표준 입력/출력/에러를 위해 예약되어 있고, 3번부터 소켓이나 파일에 할당됩니다
- 프로세스가 소켓을 읽거나 쓸 때 이 번호를 사용합니다

**2. 송수신 버퍼(Send/Receive Buffer)**
- **송신 버퍼(Send Buffer)**: 애플리케이션이 보낸 데이터를 임시로 저장하는 공간. 네트워크가 느리면 여기에 데이터가 쌓입니다.
- **수신 버퍼(Receive Buffer)**: 네트워크에서 받은 데이터를 애플리케이션이 읽을 때까지 임시로 저장하는 공간
- 각 버퍼의 크기는 보통 수십 KB에서 수백 KB 정도입니다
- 버퍼가 가득 차면 더 이상 데이터를 보내거나 받을 수 없습니다

**3. 연결 상태 정보**
- 로컬 IP 주소 및 포트 번호
- 원격 IP 주소 및 포트 번호
- TCP의 경우 시퀀스 번호, 윈도우 크기 등의 제어 정보
- 연결 상태(ESTABLISHED, CLOSE_WAIT, TIME_WAIT 등)

**4. 소켓 옵션**
- 타임아웃 설정
- Keep-Alive 설정
- Nagle 알고리즘 활성화 여부
- SO_REUSEADDR 등의 운영체제 레벨 옵션

이런 구성 요소들이 각각 메모리를 차지하기 때문에, 소켓 하나당 대략 수 KB에서 수십 KB의 메모리를 사용합니다.

---

## TCP 연결의 1:1 매핑

### 매핑 관계의 의미

TCP 연결은 **1:1 매핑** 관계를 가집니다. 이는 하나의 TCP 연결이 정확히 하나의 소켓 쌍(클라이언트 소켓 + 서버 소켓)에 대응된다는 의미입니다.

**1:1 매핑의 특징:**
- 하나의 클라이언트가 서버에 연결할 때마다 **새로운 소켓 객체**가 서버 측에 생성됩니다
- 같은 클라이언트가 여러 번 연결하면 **각각 독립적인 소켓**이 만들어집니다
- 각 소켓은 고유한 파일 디스크립터를 가지며, 서로 완전히 독립적으로 관리됩니다

### 소켓 식별자

각 TCP 연결은 5-tuple로 고유하게 식별됩니다:

```
(프로토콜, 로컬 IP, 로컬 포트, 원격 IP, 원격 포트)
```

예를 들어:
```
(TCP, 192.168.1.100, 3000, 192.168.1.50, 54321)
(TCP, 192.168.1.100, 3000, 192.168.1.50, 54322) <- 다른 연결
```

이 5-tuple 중 하나라도 다르면 완전히 다른 연결입니다. 같은 클라이언트(IP)에서 두 번 연결해도 클라이언트 포트가 달라지므로 별개의 연결이 됩니다.

### 실제 동작 예시

```javascript
const net = require('net');

const server = net.createServer((socket) => {
    // 매번 새로운 연결마다 이 콜백이 실행되고 새로운 소켓 객체가 전달됨
    console.log('새로운 연결:');
    console.log('  - 로컬: %s:%d', socket.localAddress, socket.localPort);
    console.log('  - 원격: %s:%d', socket.remoteAddress, socket.remotePort);
    console.log('  - 파일 디스크립터:', socket.fd);
    
    socket.on('data', (data) => {
        console.log(`[FD ${socket.fd}] 데이터 수신:`, data.toString());
    });
    
    socket.on('end', () => {
        console.log(`[FD ${socket.fd}] 연결 종료`);
    });
});

server.listen(3000);
```

**브라우저에서 같은 페이지를 여러 번 새로고침하면:**
```
새로운 연결:
  - 로컬: 127.0.0.1:3000
  - 원격: 127.0.0.1:54321
  - 파일 디스크립터: 12
[FD 12] 데이터 수신: GET / HTTP/1.1
[FD 12] 연결 종료

새로운 연결:
  - 로컬: 127.0.0.1:3000
  - 원격: 127.0.0.1:54322  ← 포트가 다름
  - 파일 디스크립터: 13      ← FD도 다름
[FD 13] 데이터 수신: GET / HTTP/1.1
[FD 13] 연결 종료
```

### 1:1 매핑의 장단점

**장점:**
- **격리성**: 각 연결이 독립적으로 관리되어 안전합니다. 한 연결에서 에러가 발생해도 다른 연결에 영향을 주지 않습니다.
- **명확성**: 각 연결의 상태를 명확하게 추적할 수 있습니다.
- **유연성**: 연결별로 개별적인 설정(타임아웃, 버퍼 크기 등)을 다르게 적용할 수 있습니다.

**단점:**
- **자원 소모**: 연결 수가 많아지면 각 소켓마다 메모리와 파일 디스크립터를 소모합니다.
- **C10K 문제**: 1만 개 이상의 동시 연결을 처리하기 어렵습니다.
- **관리 복잡도**: 수천 개의 소켓을 동시에 관리하려면 복잡한 로직이 필요합니다.

이러한 1:1 매핑 특성 때문에 소켓 관리가 매우 중요합니다. 각 연결이 독립적이므로, 연결이 종료되면 해당 소켓을 반드시 정리해야 시스템 자원이 고갈되지 않습니다.

---

## 시스템 자원 고갈 문제

### 파일 디스크립터 제한

**파일 디스크립터(File Descriptor)의 깊은 이해**

UNIX 계열 운영체제에서는 "모든 것이 파일"이라는 철학을 가지고 있습니다. 일반 파일뿐만 아니라 소켓, 파이프, 디바이스까지도 파일처럼 다룹니다. 운영체제는 이런 리소스를 추적하기 위해 각각에 번호를 부여하는데, 이것이 파일 디스크립터입니다.

**파일 디스크립터 테이블:**
- 각 프로세스는 자신만의 파일 디스크립터 테이블을 가집니다
- 테이블의 각 항목은 실제 파일이나 소켓을 가리킵니다
- 테이블의 크기가 제한되어 있어서 무한정 소켓을 열 수 없습니다

```
프로세스 A의 FD 테이블:
[0] -> 표준 입력
[1] -> 표준 출력
[2] -> 표준 에러
[3] -> /var/log/app.log 파일
[4] -> TCP 소켓 (192.168.1.50:54321)
[5] -> TCP 소켓 (192.168.1.51:54322)
...
[1023] -> 마지막 가능한 슬롯
```

**파일 디스크립터 제한 확인:**
```bash
# macOS/Linux에서 확인
ulimit -n

# 소프트 제한과 하드 제한 모두 확인
ulimit -Sn  # 소프트 제한 (변경 가능)
ulimit -Hn  # 하드 제한 (루트만 변경 가능)

# 일반적으로 256~1024개 정도로 제한되어 있음
```

**시스템 전체 제한 확인 (Linux):**
```bash
# 시스템 전체에서 열 수 있는 파일 디스크립터 수
cat /proc/sys/fs/file-max

# 현재 사용 중인 파일 디스크립터 수
cat /proc/sys/fs/file-nr
```

**실제 상황 예시:**

만약 파일 디스크립터 제한이 1024개라면:
- 3개는 표준 입출력에 사용
- 로그 파일, 설정 파일 등에 약 10~20개 사용
- 실제로 소켓에 사용할 수 있는 것은 약 1000개 정도

이것은 동시에 1000명의 사용자만 처리할 수 있다는 의미입니다. 1001번째 사용자가 연결하려고 하면 다음과 같은 에러가 발생합니다:

```
Error: EMFILE: too many open files
```

**문제 상황 코드:**
```javascript
const net = require('net');
const connections = new Set();

const server = net.createServer((socket) => {
    connections.add(socket);
    console.log(`연결 수: ${connections.size}`);
    
    socket.on('data', (data) => {
        console.log('받은 데이터:', data.toString());
    });
    
    // 연결 종료나 에러 처리가 없음 - 문제 발생!
    // 소켓을 닫지 않으면 파일 디스크립터가 계속 차지됨
});

server.on('error', (err) => {
    if (err.code === 'EMFILE') {
        console.error('파일 디스크립터 한계 도달!');
        console.error('현재 연결 수:', connections.size);
    }
});

server.listen(3000);
```

### 메모리 고갈 문제

**소켓 객체의 메모리 구조:**

각 소켓 객체는 다음과 같은 메모리를 사용합니다:

1. **객체 자체의 메모리** (약 1~2 KB)
   - 소켓 객체의 속성들
   - V8 엔진의 히든 클래스 정보
   - 프로토타입 체인 정보

2. **송수신 버퍼** (약 16~64 KB)
   - 기본적으로 각각 64KB 정도 할당됨
   - 설정에 따라 더 클 수 있음

3. **이벤트 리스너** (약 수백 바이트)
   - 등록된 각 이벤트 핸들러가 메모리 차지
   - 핸들러의 클로저가 참조하는 변수들도 포함

4. **운영체제 레벨 구조** (약 1~2 KB)
   - TCP 제어 블록 (TCB)
   - 송수신 큐
   - 라우팅 정보

**총 메모리 사용량:**
소켓 하나당 약 20~70 KB 정도 사용합니다. 만약 10,000개의 소켓이 정리되지 않고 남아있다면:

```
10,000개 × 50 KB = 500 MB
```

**메모리 누수가 발생하는 이유:**

JavaScript는 가비지 컬렉션을 사용하는 언어입니다. 더 이상 참조되지 않는 객체를 자동으로 메모리에서 제거합니다. 하지만:

1. **참조가 남아있으면 해제되지 않습니다**
   - 소켓 객체를 배열이나 맵에 저장해두면 참조가 유지됨
   - 연결이 끊어져도 배열에서 제거하지 않으면 메모리에 계속 남음

2. **이벤트 리스너가 참조를 만듭니다**
   - 이벤트 핸들러가 등록되어 있으면 소켓 객체에 대한 참조가 생김
   - 이벤트 리스너를 제거하지 않으면 가비지 컬렉션되지 않음

3. **클로저가 의도치 않은 참조를 만듭니다**
   - 이벤트 핸들러 내부에서 외부 변수를 참조하면 클로저가 생성됨
   - 클로저가 살아있는 한 참조된 모든 변수가 메모리에 남음

**메모리 누수 예시:**
```javascript
// 문제가 있는 코드
const activeConnections = [];
const userData = new Map();

const server = net.createServer((socket) => {
    // 1. 배열에 추가 - 참조 생성
    activeConnections.push(socket);
    
    // 2. 사용자 데이터 저장 - 또 다른 참조 생성
    const userId = Date.now();
    userData.set(socket, { userId, data: new Array(1000000) }); // 큰 데이터
    
    socket.on('data', (data) => {
        // 3. 클로저가 socket과 userData를 참조
        console.log('사용자', userData.get(socket).userId);
    });
    
    socket.on('end', () => {
        console.log('연결 종료');
        // 문제: 배열과 Map에서 제거하지 않음!
        // activeConnections와 userData에 계속 남아있음
    });
});

server.listen(3000);

// 시간이 지나면서 activeConnections와 userData가 계속 커짐
// 각 항목마다 수 MB의 메모리를 사용한다면 급격히 메모리 고갈
```

**메모리 사용량 모니터링:**
```javascript
setInterval(() => {
    const used = process.memoryUsage();
    console.log('메모리 사용량:');
    console.log('  RSS:', Math.round(used.rss / 1024 / 1024), 'MB'); // 전체 메모리
    console.log('  Heap Used:', Math.round(used.heapUsed / 1024 / 1024), 'MB'); // 힙 사용량
    console.log('  External:', Math.round(used.external / 1024 / 1024), 'MB'); // 외부 메모리 (버퍼 등)
    console.log('현재 연결 수:', activeConnections.length);
}, 5000);
```

### 성능 저하

정리되지 않은 소켓들이 많아지면:

1. **이벤트 루프 지연**
   - Node.js는 단일 스레드 이벤트 루프를 사용합니다
   - 수천 개의 소켓이 있으면 각 소켓의 이벤트를 처리하는데 시간이 걸립니다
   - 새로운 요청 처리가 지연됩니다

2. **가비지 컬렉션 부담**
   - 메모리가 많이 사용되면 가비지 컬렉션이 자주 실행됩니다
   - GC가 실행되는 동안 애플리케이션이 멈춥니다 (Stop-the-world)
   - 사용자 요청이 느려집니다

3. **시스템 전체 불안정**
   - 운영체제가 메모리 부족 상태에 도달하면 스왑을 사용합니다
   - 스왑은 디스크를 사용하므로 매우 느립니다
   - 최악의 경우 OOM Killer가 프로세스를 강제 종료합니다

---

## 소켓 관리 방법

### 1. 연결 종료 감지 및 정리

소켓의 생명주기를 이해하고 적절한 시점에 정리하는 것이 핵심입니다.

**TCP 연결의 생명주기:**

```
클라이언트                              서버
    |                                    |
    |---- SYN ----------------------->|
    |<--- SYN-ACK -------------------|    [connection 이벤트]
    |---- ACK ----------------------->|
    |                                    |
    |     [ESTABLISHED 상태]             |
    |                                    |
    |<--- 데이터 송수신 --------------->|    [data 이벤트]
    |                                    |
    |---- FIN ----------------------->|    [end 이벤트]
    |<--- ACK -----------------------|
    |<--- FIN -----------------------|
    |---- ACK ----------------------->|    [close 이벤트]
    |                                    |
    |     [CLOSED 상태]                 |
```

**주요 이벤트의 의미:**

- **`connection` 이벤트**: 새로운 클라이언트가 연결되었을 때 발생. 서버 측에서만 발생합니다.

- **`data` 이벤트**: 데이터를 받았을 때 발생. 데이터는 Buffer 형태로 전달됩니다.

- **`end` 이벤트**: 상대방이 FIN 패킷을 보내서 더 이상 데이터를 보내지 않겠다고 알렸을 때 발생. 하지만 아직 소켓은 완전히 닫히지 않았습니다. 이 시점에는 우리 쪽에서 데이터를 보낼 수는 있습니다 (half-closed 상태).

- **`close` 이벤트**: 소켓이 완전히 닫혔을 때 발생. 양방향 모두 닫힌 상태입니다. 이 이벤트가 발생하면 더 이상 소켓을 사용할 수 없습니다.

- **`error` 이벤트**: 소켓에서 에러가 발생했을 때 (네트워크 문제, 연결 끊김 등). 에러 이벤트 후에는 자동으로 `close` 이벤트가 발생합니다.

- **`timeout` 이벤트**: 설정한 시간 동안 활동이 없을 때 발생. 이 이벤트 자체는 소켓을 닫지 않으므로 명시적으로 닫아야 합니다.

**올바른 정리 코드:**

```javascript
const net = require('net');
const activeSockets = new Set();

const server = net.createServer((socket) => {
    console.log('새로운 클라이언트 연결됨');
    
    // 소켓 추적 시작
    activeSockets.add(socket);
    console.log(`활성 소켓 수: ${activeSockets.size}`);
    
    // 데이터 수신
    socket.on('data', (data) => {
        console.log('받은 데이터:', data.toString());
        socket.write(`서버 응답: ${data.toString()}`);
    });
    
    // 정상 종료: 클라이언트가 연결을 끊었을 때
    socket.on('end', () => {
        console.log('클라이언트가 연결을 종료했습니다');
        // 아직 소켓은 완전히 닫히지 않음
        // close 이벤트에서 정리하므로 여기서는 로깅만
    });
    
    // 에러 발생: 네트워크 문제나 예기치 않은 종료
    socket.on('error', (err) => {
        console.error('소켓 에러:', err.message);
        // error 후 자동으로 close 발생하므로 여기서 제거하지 않음
    });
    
    // 완전 종료: 소켓이 완전히 닫혔을 때
    // 이것이 가장 중요한 정리 시점
    socket.on('close', (hadError) => {
        console.log('소켓 닫힘', hadError ? '(에러로 인해)' : '(정상)');
        
        // Set에서 제거 - 가비지 컬렉션 가능하게 함
        activeSockets.delete(socket);
        console.log(`활성 소켓 수: ${activeSockets.size}`);
        
        // 추가 정리 작업이 필요하다면 여기서 수행
        // 예: 데이터베이스 업데이트, 로그 기록 등
    });
});

server.listen(3000, () => {
    console.log('서버가 포트 3000에서 실행 중입니다');
});

// 모니터링
setInterval(() => {
    console.log(`[모니터링] 현재 활성 연결: ${activeSockets.size}`);
}, 10000);

// 우아한 종료 (Graceful Shutdown)
process.on('SIGTERM', () => {
    console.log('SIGTERM 신호 받음 - 서버 종료 시작');
    
    server.close(() => {
        console.log('더 이상 새로운 연결을 받지 않음');
    });
    
    // 기존 연결들을 정리
    activeSockets.forEach(socket => {
        socket.end(); // 정상적으로 연결 종료
    });
    
    // 타임아웃 설정 - 10초 안에 종료되지 않으면 강제 종료
    setTimeout(() => {
        console.error('타임아웃 - 강제 종료');
        activeSockets.forEach(socket => {
            socket.destroy(); // 강제 종료
        });
        process.exit(1);
    }, 10000);
});
```

**Set vs Array vs Map 선택:**

소켓을 추적할 때 어떤 자료구조를 사용할지는 요구사항에 따라 다릅니다:

- **Set 사용**: 단순히 소켓 목록만 관리하고 싶을 때. 중복 제거와 빠른 검색/삭제가 장점입니다.
```javascript
const activeSockets = new Set();
activeSockets.add(socket);      // O(1)
activeSockets.delete(socket);   // O(1)
```

- **Map 사용**: 소켓과 연관된 데이터를 함께 저장하고 싶을 때
```javascript
const socketData = new Map();
socketData.set(socket, { userId: 123, loginTime: Date.now() });
const userInfo = socketData.get(socket);
```

- **WeakMap 사용**: 소켓이 정리되면 자동으로 연관 데이터도 제거하고 싶을 때
```javascript
const socketData = new WeakMap();
socketData.set(socket, { data: 'some data' });
// socket이 가비지 컬렉션되면 연관 데이터도 자동 제거됨
```

### 2. 타임아웃 설정

타임아웃은 비정상적인 상황에서 소켓을 자동으로 정리하는 안전장치입니다.

**타임아웃이 필요한 상황:**

1. **좀비 연결 (Zombie Connection)**
   - 클라이언트가 비정상 종료되었지만 TCP 연결은 ESTABLISHED 상태로 남아있는 경우
   - 네트워크 장비 재시작 등으로 연결이 끊어졌지만 양쪽 모두 모르는 경우

2. **느린 클라이언트 (Slow Client)**
   - 의도적이든 아니든 매우 느리게 데이터를 보내거나 받는 클라이언트
   - Slowloris 공격: 연결은 유지하면서 매우 느리게 요청을 보내 서버 자원 고갈

3. **유휴 연결 (Idle Connection)**
   - 연결은 되어 있지만 오랜 시간 아무 활동이 없는 경우
   - 자원 낭비를 방지하기 위해 정리 필요

**타임아웃 구현:**

```javascript
const server = net.createServer((socket) => {
    // 30초 유휴 타임아웃 설정
    socket.setTimeout(30000);
    
    let lastActivity = Date.now();
    
    socket.on('data', (data) => {
        // 활동 감지 - 타임아웃 리셋
        lastActivity = Date.now();
        socket.setTimeout(30000); // 타임아웃 갱신
        
        console.log('데이터 수신:', data.toString());
        socket.write('OK');
    });
    
    socket.on('timeout', () => {
        const idleTime = Date.now() - lastActivity;
        console.log(`타임아웃 발생 - ${idleTime}ms 동안 유휴 상태`);
        
        // 정상적인 종료 시도
        socket.end('타임아웃으로 연결을 종료합니다\n');
        
        // 만약 end()가 실패하면 강제 종료
        setTimeout(() => {
            if (!socket.destroyed) {
                socket.destroy();
            }
        }, 1000);
    });
    
    socket.on('error', (err) => {
        console.error('소켓 에러:', err.message);
    });
    
    socket.on('close', () => {
        console.log('소켓 정리 완료');
    });
});

server.listen(3000);
```

**다양한 타임아웃 전략:**

```javascript
// 1. 연결 타임아웃 (Connection Timeout)
// 연결 수립 후 첫 데이터를 받을 때까지의 시간 제한
const server = net.createServer((socket) => {
    let firstDataReceived = false;
    socket.setTimeout(5000); // 5초 안에 데이터가 와야 함
    
    socket.on('data', (data) => {
        if (!firstDataReceived) {
            firstDataReceived = true;
            socket.setTimeout(30000); // 이후에는 30초로 변경
        }
        // 처리...
    });
    
    socket.on('timeout', () => {
        if (!firstDataReceived) {
            console.log('초기 데이터 수신 타임아웃');
        } else {
            console.log('유휴 타임아웃');
        }
        socket.end();
    });
});

// 2. 요청 타임아웃 (Request Timeout)
// HTTP 요청 전체를 받는데 걸리는 시간 제한
const http = require('http');
const server = http.createServer((req, res) => {
    req.setTimeout(10000); // 요청 전체를 10초 안에 받아야 함
    
    req.on('timeout', () => {
        res.writeHead(408, { 'Content-Type': 'text/plain' });
        res.end('요청 타임아웃');
    });
    
    // 요청 처리...
});

// 3. 응답 타임아웃 (Response Timeout)
// 응답을 보내는데 걸리는 시간 제한
const server = http.createServer((req, res) => {
    res.setTimeout(60000); // 응답을 60초 안에 완료해야 함
    
    res.on('timeout', () => {
        console.error('응답 전송 타임아웃');
        res.end();
    });
    
    // 느린 처리 시뮬레이션
    setTimeout(() => {
        res.end('처리 완료');
    }, 5000);
});
```

### 3. 명시적 참조 해제

JavaScript의 가비지 컬렉터가 제대로 작동하도록 참조를 정리해야 합니다.

**가비지 컬렉션의 작동 원리:**

V8 엔진(Node.js가 사용)은 **도달 가능성(Reachability)** 기반의 가비지 컬렉션을 사용합니다:

1. **루트(Root)에서 시작**: 전역 객체, 현재 실행 중인 함수의 로컬 변수 등
2. **참조 추적**: 루트에서 참조로 도달할 수 있는 모든 객체를 표시
3. **미도달 객체 제거**: 표시되지 않은 객체는 도달 불가능하므로 메모리에서 제거

**문제 상황:**

```javascript
// 문제가 있는 코드
const globalConnections = []; // 전역 변수 - 루트에서 도달 가능

function handleConnection(socket) {
    globalConnections.push(socket); // 참조 추가
    
    socket.on('data', (data) => {
        // 클로저가 socket을 참조
        console.log('데이터:', data.toString());
    });
    
    socket.on('close', () => {
        console.log('연결 종료');
        // 배열에서 제거하지 않음 - 여전히 참조가 남아있음!
    });
}

// globalConnections 배열에 계속 쌓임
// 루트(전역) -> globalConnections -> socket 참조 경로가 유지됨
// 가비지 컬렉션 불가능
```

**올바른 참조 관리:**

```javascript
const activeConnections = new Map(); // 연결 ID로 관리
let connectionId = 0;

function handleConnection(socket) {
    const id = ++connectionId;
    activeConnections.set(id, socket);
    
    console.log(`연결 ${id} 생성`);
    console.log(`활성 연결 수: ${activeConnections.size}`);
    
    socket.on('data', (data) => {
        console.log(`[${id}] 데이터:`, data.toString());
    });
    
    socket.on('close', () => {
        console.log(`연결 ${id} 종료`);
        
        // 1. Map에서 제거 - 참조 해제
        activeConnections.delete(id);
        
        // 2. 이벤트 리스너 명시적 제거 (선택사항, close 후에는 자동 제거됨)
        socket.removeAllListeners();
        
        console.log(`활성 연결 수: ${activeConnections.size}`);
    });
}

const server = net.createServer(handleConnection);
server.listen(3000);
```

**이벤트 리스너 누수 방지:**

이벤트 리스너는 객체에 대한 강한 참조를 만듭니다. 많은 리스너가 등록되면 메모리 누수가 발생할 수 있습니다.

```javascript
// 문제 상황
socket.on('data', function handler(data) {
    // 처리...
});

// 같은 이벤트에 리스너를 계속 추가하면
socket.on('data', anotherHandler);
socket.on('data', yetAnotherHandler);
// EventEmitter가 경고를 출력함:
// (node:12345) MaxListenersExceededWarning: Possible EventEmitter memory leak

// 해결 방법 1: 리스너 제거
const handler = (data) => {
    console.log(data);
};
socket.on('data', handler);
// 나중에
socket.removeListener('data', handler);

// 해결 방법 2: once 사용 (한 번만 실행)
socket.once('data', (data) => {
    console.log('첫 데이터:', data);
    // 자동으로 리스너가 제거됨
});

// 해결 방법 3: 최대 리스너 수 조정
socket.setMaxListeners(20); // 기본값은 10
```

**WeakMap 활용:**

WeakMap은 키가 가비지 컬렉션되면 자동으로 해당 항목도 제거되는 특별한 Map입니다.

```javascript
// 일반 Map - 명시적으로 제거해야 함
const socketData = new Map();
socketData.set(socket, { userId: 123 });
// socket이 필요없어도 Map에서 제거하지 않으면 메모리에 남음

// WeakMap - 자동 정리
const socketData = new WeakMap();
socketData.set(socket, { userId: 123, largeData: new Array(1000000) });

socket.on('close', () => {
    // WeakMap에서 명시적으로 제거하지 않아도 됨
    // socket이 가비지 컬렉션되면 연관 데이터도 자동 제거
});

// 주의: WeakMap은 키를 순회할 수 없음
// socketData.forEach() // 불가능
// 따라서 "모든 활성 소켓" 같은 것을 추적하려면 일반 Map 사용
```

---

## 소켓 관리 실패 시 발생하는 문제

### 1. 시스템 자원 부족

**증상:**
```
Error: EMFILE: too many open files
Error: ENFILE: file table overflow
Error: ENOMEM: out of memory
```

**영향:**
- 새로운 클라이언트 연결을 받을 수 없음
- 파일을 열 수 없음 (로그 파일, 설정 파일 등)
- 데이터베이스 연결 불가
- 서버가 완전히 응답 불가 상태가 됨

**실제 사례:**
어떤 회사의 채팅 서버에서 클라이언트가 연결을 끊어도 서버에서 소켓을 정리하지 않았습니다. 평소에는 문제가 없었지만, 마케팅 이벤트로 사용자가 급증하자 파일 디스크립터가 고갈되어 서버가 다운되었습니다. 신규 사용자는 연결조차 할 수 없었고, 기존 사용자도 메시지를 보낼 수 없게 되었습니다.

### 2. 메모리 부족으로 인한 서버 중단

**메모리 고갈 프로세스:**

```
초기 상태: 메모리 사용량 200MB
  ↓
1시간 후: 500MB (소켓 300개 누적)
  ↓
6시간 후: 2GB (소켓 2000개 누적)
  ↓
12시간 후: 4GB (시스템 메모리 한계)
  ↓
시스템이 스왑 사용 시작 (성능 급격히 저하)
  ↓
OOM Killer가 프로세스 강제 종료
  ↓
서비스 완전 중단
```

**실제 사례:**
게임 서버에서 플레이어가 로그아웃해도 소켓과 플레이어 데이터가 메모리에 남아있었습니다. 플레이어 한 명당 약 5MB의 데이터가 있었는데, 하루에 수천 명이 접속하다 보니 매일 밤마다 메모리가 고갈되어 서버가 재시작되는 문제가 발생했습니다.

### 3. 성능 저하

**증상:**
- 응답 시간이 점점 느려짐 (처음 100ms → 나중에 5초)
- CPU 사용률이 높지 않은데도 느림
- 간헐적인 멈춤 현상

**원인:**
1. **많은 소켓 감시**: epoll/kqueue/select 같은 시스템 콜이 많은 소켓을 감시하느라 느려짐
2. **잦은 GC**: 메모리가 많이 사용되면 가비지 컬렉션이 자주 발생하고, 그 동안 애플리케이션이 멈춤
3. **캐시 미스**: 메모리가 부족하면 CPU 캐시 효율이 떨어짐

### 4. 디버깅의 어려움

소켓 관리 문제는 발견하기 어렵습니다:

- **점진적 악화**: 갑자기 문제가 생기지 않고 천천히 악화됨
- **재현 어려움**: 개발 환경에서는 연결 수가 적어서 문제가 안 나타남
- **타이밍 문제**: 특정 상황(많은 동시 접속, 네트워크 불안정 등)에서만 발생
- **복합적 원인**: 여러 요인이 겹쳐서 발생하므로 원인 파악이 어려움

---

## 모니터링 및 디버깅

### 소켓 상태 확인

**운영체제 레벨 확인:**

```bash
# 특정 포트의 연결 상태 확인 (Linux/macOS)
lsof -i :3000

# 출력 예시:
# COMMAND   PID USER   FD   TYPE     DEVICE SIZE/OFF NODE NAME
# node    12345 user   12u  IPv4   12345678      0t0  TCP *:3000 (LISTEN)
# node    12345 user   13u  IPv4   12345679      0t0  TCP localhost:3000->localhost:54321 (ESTABLISHED)
# node    12345 user   14u  IPv4   12345680      0t0  TCP localhost:3000->localhost:54322 (ESTABLISHED)

# 프로세스가 열고 있는 파일 디스크립터 수 확인
ls -l /proc/[PID]/fd | wc -l

# 모든 TCP 연결 상태별 통계
netstat -an | awk '/tcp/ {print $6}' | sort | uniq -c | sort -rn

# 출력 예시:
#     150 ESTABLISHED
#      50 TIME_WAIT
#      20 CLOSE_WAIT  <- 이게 많으면 소켓 정리 문제
#      10 FIN_WAIT1
#       5 LISTEN
```

**CLOSE_WAIT 상태가 많다는 것의 의미:**
- 상대방이 연결을 끊었지만 우리 쪽에서 아직 close()를 호출하지 않은 상태
- 소켓 정리가 제대로 되지 않는다는 신호
- 이 상태의 소켓이 계속 쌓이면 심각한 문제

**Node.js 레벨 확인:**

```javascript
const net = require('net');
const activeSockets = new Set();

const server = net.createServer((socket) => {
    activeSockets.add(socket);
    
    // 소켓 정보 로깅
    console.log('새 연결:');
    console.log('  Local:', socket.localAddress, socket.localPort);
    console.log('  Remote:', socket.remoteAddress, socket.remotePort);
    console.log('  FD:', socket._handle ? socket._handle.fd : 'N/A');
    
    socket.on('close', () => {
        activeSockets.delete(socket);
    });
});

server.listen(3000);

// 상세 모니터링 엔드포인트
const http = require('http');
const monitorServer = http.createServer((req, res) => {
    if (req.url === '/status') {
        const status = {
            activeConnections: activeSockets.size,
            memory: process.memoryUsage(),
            uptime: process.uptime(),
            connections: []
        };
        
        // 각 소켓의 상세 정보
        activeSockets.forEach(socket => {
            status.connections.push({
                remote: `${socket.remoteAddress}:${socket.remotePort}`,
                bytesRead: socket.bytesRead,
                bytesWritten: socket.bytesWritten,
                bufferSize: socket.bufferSize
            });
        });
        
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(status, null, 2));
    } else {
        res.writeHead(404);
        res.end();
    }
});

monitorServer.listen(9000);
console.log('모니터링 서버: http://localhost:9000/status');
```

### 메모리 프로파일링

```javascript
// 정기적인 힙 스냅샷
const v8 = require('v8');
const fs = require('fs');

function takeHeapSnapshot() {
    const filename = `heap-${Date.now()}.heapsnapshot`;
    const snapshot = v8.writeHeapSnapshot(filename);
    console.log(`힙 스냅샷 저장됨: ${snapshot}`);
}

// 1시간마다 스냅샷 저장
setInterval(takeHeapSnapshot, 3600000);

// Chrome DevTools에서 열어서 분석 가능
// 메모리 누수가 있는지, 어떤 객체가 메모리를 많이 차지하는지 확인
```

---

## 실전 예제: 안정적인 TCP 서버

```javascript
const net = require('net');
const EventEmitter = require('events');

class ConnectionManager extends EventEmitter {
    constructor(options = {}) {
        super();
        this.connections = new Map();
        this.connectionId = 0;
        
        // 설정
        this.maxConnections = options.maxConnections || 1000;
        this.idleTimeout = options.idleTimeout || 60000; // 60초
        this.connectionTimeout = options.connectionTimeout || 5000; // 5초
    }
    
    add(socket) {
        // 연결 수 제한 확인
        if (this.connections.size >= this.maxConnections) {
            console.warn('최대 연결 수 도달');
            socket.end('서버가 현재 최대 용량입니다. 나중에 다시 시도해주세요.\n');
            return null;
        }
        
        const id = ++this.connectionId;
        const conn = {
            id,
            socket,
            createdAt: Date.now(),
            lastActivity: Date.now(),
            bytesRead: 0,
            bytesWritten: 0
        };
        
        this.connections.set(id, conn);
        this.setupSocket(conn);
        
        this.emit('connection', conn);
        console.log(`[${id}] 연결됨 (총 ${this.connections.size}개)`);
        
        return id;
    }
    
    setupSocket(conn) {
        const { id, socket } = conn;
        let firstDataReceived = false;
        
        // 초기 타임아웃: 연결 후 첫 데이터를 받을 때까지
        socket.setTimeout(this.connectionTimeout);
        
        socket.on('data', (data) => {
            conn.lastActivity = Date.now();
            conn.bytesRead += data.length;
            
            // 첫 데이터를 받으면 타임아웃을 유휴 타임아웃으로 변경
            if (!firstDataReceived) {
                firstDataReceived = true;
                socket.setTimeout(this.idleTimeout);
            }
            
            this.emit('data', conn, data);
        });
        
        socket.on('timeout', () => {
            const idleTime = Date.now() - conn.lastActivity;
            console.log(`[${id}] 타임아웃 (유휴 시간: ${idleTime}ms)`);
            
            this.emit('timeout', conn);
            
            // 정상 종료 시도
            socket.end();
            
            // 1초 후에도 안 닫히면 강제 종료
            setTimeout(() => {
                if (!socket.destroyed) {
                    console.log(`[${id}] 강제 종료`);
                    socket.destroy();
                }
            }, 1000);
        });
        
        socket.on('error', (err) => {
            console.error(`[${id}] 에러:`, err.message);
            this.emit('error', conn, err);
        });
        
        socket.on('close', (hadError) => {
            const duration = Date.now() - conn.createdAt;
            console.log(`[${id}] 닫힘 (지속시간: ${duration}ms, 읽음: ${conn.bytesRead}B, 쓰기: ${conn.bytesWritten}B)`);
            
            this.connections.delete(id);
            this.emit('close', conn, hadError);
            
            console.log(`활성 연결: ${this.connections.size}개`);
        });
    }
    
    write(id, data) {
        const conn = this.connections.get(id);
        if (conn) {
            conn.socket.write(data);
            conn.bytesWritten += data.length;
            conn.lastActivity = Date.now();
            return true;
        }
        return false;
    }
    
    close(id) {
        const conn = this.connections.get(id);
        if (conn) {
            conn.socket.end();
            return true;
        }
        return false;
    }
    
    closeAll() {
        console.log(`모든 연결 종료 (${this.connections.size}개)`);
        this.connections.forEach(conn => {
            conn.socket.end();
        });
    }
    
    getStats() {
        const stats = {
            total: this.connections.size,
            bytesSent: 0,
            bytesReceived: 0,
            avgAge: 0
        };
        
        const now = Date.now();
        this.connections.forEach(conn => {
            stats.bytesSent += conn.bytesWritten;
            stats.bytesReceived += conn.bytesRead;
            stats.avgAge += (now - conn.createdAt);
        });
        
        if (stats.total > 0) {
            stats.avgAge /= stats.total;
        }
        
        return stats;
    }
}

// 사용 예시
const manager = new ConnectionManager({
    maxConnections: 1000,
    idleTimeout: 60000,
    connectionTimeout: 5000
});

const server = net.createServer((socket) => {
    const id = manager.add(socket);
    if (id === null) return; // 연결 거부됨
    
    // 환영 메시지
    manager.write(id, 'TCP 서버에 오신 것을 환영합니다!\n');
});

// 이벤트 처리
manager.on('data', (conn, data) => {
    const message = data.toString().trim();
    console.log(`[${conn.id}] 받음:`, message);
    
    // 에코 서버
    manager.write(conn.id, `에코: ${message}\n`);
});

manager.on('error', (conn, err) => {
    console.error(`[${conn.id}] 에러 처리`);
});

// 모니터링
setInterval(() => {
    const stats = manager.getStats();
    console.log('=== 서버 통계 ===');
    console.log('활성 연결:', stats.total);
    console.log('송신:', Math.round(stats.bytesSent / 1024), 'KB');
    console.log('수신:', Math.round(stats.bytesReceived / 1024), 'KB');
    console.log('평균 연결 시간:', Math.round(stats.avgAge / 1000), '초');
    console.log('메모리:', Math.round(process.memoryUsage().heapUsed / 1024 / 1024), 'MB');
}, 10000);

// 우아한 종료
process.on('SIGTERM', () => {
    console.log('종료 신호 받음');
    server.close(() => {
        console.log('더 이상 새로운 연결을 받지 않음');
    });
    
    manager.closeAll();
    
    setTimeout(() => {
        console.log('강제 종료');
        process.exit(0);
    }, 10000);
});

server.listen(3000, () => {
    console.log('서버 시작: 포트 3000');
});
```

---

## 정리

### 핵심 원칙

1. **소켓은 반드시 정리해야 합니다**
   - 소켓은 유한한 시스템 자원입니다
   - 사용이 끝나면 명시적으로 닫아야 합니다
   - `close` 이벤트에서 참조를 제거해야 가비지 컬렉션이 됩니다

2. **생명주기 이벤트를 활용하세요**
   - `end`: 상대방이 연결을 끊기 시작
   - `error`: 에러 발생
   - `close`: 완전히 닫힘 - 여기서 정리!

3. **타임아웃을 설정하세요**
   - 비정상 상황에 대비한 안전장치
   - 좀비 연결을 자동으로 정리
   - 서비스 거부 공격(DoS) 방어

4. **참조를 명시적으로 해제하세요**
   - 배열, Map, Set에서 소켓 제거
   - 이벤트 리스너 정리 (필요시)
   - 가비지 컬렉션이 작동할 수 있도록

5. **모니터링하세요**
   - 활성 연결 수 추적
   - 메모리 사용량 모니터링
   - 비정상 패턴 감지

### 실무에서의 고려사항

**개발 단계:**
- 처음부터 소켓 관리 패턴을 적용하세요
- 연결 수를 인위적으로 늘려서 테스트하세요
- 메모리 프로파일링을 정기적으로 수행하세요

**운영 단계:**
- 연결 수, 메모리, 파일 디스크립터를 모니터링하세요
- 알람을 설정하여 임계값 초과 시 알림을 받으세요
- 로그를 통해 비정상 패턴을 감지하세요

**문제 발생 시:**
- `netstat`, `lsof` 명령으로 현재 상태 확인
- 힙 스냅샷을 떠서 메모리 누수 분석
- 연결이 많이 쌓이는 패턴을 찾으세요

### 참고 명령어

```bash
# 현재 파일 디스크립터 제한 확인
ulimit -n

# 특정 포트의 연결 확인
lsof -i :3000
netstat -an | grep :3000

# 프로세스의 파일 디스크립터 수
ls -l /proc/[PID]/fd | wc -l

# TCP 연결 상태별 통계
netstat -an | awk '/tcp/ {print $6}' | sort | uniq -c
```

### Node.js에서 소켓 정보 확인

```javascript
// 서버의 연결 수 확인
server.getConnections((err, count) => {
    console.log(`현재 연결 수: ${count}`);
});

// 메모리 사용량 확인
const used = process.memoryUsage();
console.log('RSS:', Math.round(used.rss / 1024 / 1024), 'MB');
console.log('Heap:', Math.round(used.heapUsed / 1024 / 1024), 'MB');
```

소켓 관리는 처음에는 복잡해 보일 수 있지만, 일관된 패턴을 적용하면 안정적인 네트워크 서버를 구축할 수 있습니다. 특히 대규모 서비스에서는 소켓 관리가 서버 안정성의 핵심입니다.
