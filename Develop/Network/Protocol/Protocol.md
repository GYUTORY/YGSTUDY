---
title: Protocol
tags: [network, protocol]
updated: 2025-08-10
---
# 📡 네트워크 프로토콜(Protocol) 이해하기

## 배경

**프로토콜**은 컴퓨터들이 서로 대화할 때 사용하는 **공통 언어**라고 생각하면 됩니다.

마치 사람들이 대화할 때 문법과 예의가 있듯이, 컴퓨터들도 서로 통신할 때 정해진 규칙을 따라야 합니다.

### 왜 프로토콜이 필요한가?

- **다른 기기끼리도 소통 가능**: 애플 맥과 윈도우 PC가 서로 파일을 주고받을 수 있는 이유
- **데이터가 올바르게 전달**: 메시지가 중간에 깨지지 않고 온전히 전달
- **보안과 안정성**: 중요한 정보를 안전하게 주고받기

---


- **다른 기기끼리도 소통 가능**: 애플 맥과 윈도우 PC가 서로 파일을 주고받을 수 있는 이유
- **데이터가 올바르게 전달**: 메시지가 중간에 깨지지 않고 온전히 전달
- **보안과 안정성**: 중요한 정보를 안전하게 주고받기

---


### HTTP (HyperText Transfer Protocol)

**웹에서 가장 많이 사용하는 프로토콜**입니다. 브라우저가 웹사이트를 볼 때 사용합니다.

```javascript
// 브라우저에서 HTTP 요청 보내기
async function fetchUserData() {
  try {
    const response = await fetch('https://api.example.com/users', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer your-token-here'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP 오류! 상태: ${response.status}`);
    }

    const data = await response.json();
    console.log('받은 데이터:', data);
    return data;
  } catch (error) {
    console.error('요청 실패:', error);
  }
}

// POST 요청으로 데이터 보내기
async function createUser(userData) {
  const response = await fetch('https://api.example.com/users', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(userData)
  });

  return response.json();
}
```

### WebSocket

**실시간 양방향 통신**을 위한 프로토콜입니다. 채팅, 게임, 실시간 알림에 사용됩니다.

```javascript
// WebSocket 클라이언트 예제
class ChatClient {
  constructor(serverUrl) {
    this.serverUrl = serverUrl;
    this.ws = null;
    this.messageQueue = [];
  }

  connect() {
    this.ws = new WebSocket(this.serverUrl);

    this.ws.onopen = () => {
      console.log('채팅 서버에 연결됨');
      // 연결 후 대기 중이던 메시지들 전송
      this.sendQueuedMessages();
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      console.log('연결이 끊어졌습니다');
    };
  }

  sendMessage(text) {
    const message = {
      type: 'chat',
      content: text,
      timestamp: new Date().toISOString()
    };

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // 연결이 안 되어 있으면 대기열에 추가
      this.messageQueue.push(message);
    }
  }

  sendQueuedMessages() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.ws.send(JSON.stringify(message));
    }
  }

  handleMessage(message) {
    switch (message.type) {
      case 'chat':
        console.log(`${message.sender}: ${message.content}`);
        break;
      case 'notification':
        console.log(`알림: ${message.content}`);
        break;
    }
  }
}

// 사용 예시
const chat = new ChatClient('ws://localhost:8080');
chat.connect();
chat.sendMessage('안녕하세요!');
```

### TCP vs UDP 이해하기

#### TCP (Transmission Control Protocol)
**신뢰성이 중요한 데이터**에 사용됩니다. 이메일, 파일 다운로드, 웹페이지 로딩 등

```javascript
// Node.js에서 TCP 서버 만들기
const net = require('net');

const server = net.createServer((socket) => {
  console.log('클라이언트가 연결됨');

  // 데이터 받기
  socket.on('data', (data) => {
    console.log('받은 데이터:', data.toString());
    
    // 응답 보내기
    socket.write('서버에서 응답: 데이터를 받았습니다!');
  });

  socket.on('end', () => {
    console.log('클라이언트 연결 종료');
  });
});

server.listen(3000, () => {
  console.log('TCP 서버가 포트 3000에서 실행 중');
});
```

#### UDP (User Datagram Protocol)
**빠른 전송이 중요한 데이터**에 사용됩니다. 실시간 스트리밍, 온라인 게임 등

```javascript
// Node.js에서 UDP 서버 만들기
const dgram = require('dgram');
const server = dgram.createSocket('udp4');

server.on('message', (msg, rinfo) => {
  console.log(`UDP 메시지 받음: ${msg} from ${rinfo.address}:${rinfo.port}`);
  
  // 응답 보내기
  const response = Buffer.from('UDP 응답 메시지');
  server.send(response, rinfo.port, rinfo.address);
});

server.bind(3001, () => {
  console.log('UDP 서버가 포트 3001에서 실행 중');
});
```

---


### REST API 설계

```javascript
// Express.js로 REST API 서버 만들기
const express = require('express');
const app = express();

app.use(express.json());

// GET - 데이터 조회
app.get('/api/users', (req, res) => {
  const users = [
    { id: 1, name: '김철수', email: 'kim@example.com' },
    { id: 2, name: '이영희', email: 'lee@example.com' }
  ];
  res.json(users);
});

// POST - 데이터 생성
app.post('/api/users', (req, res) => {
  const { name, email } = req.body;
  const newUser = { id: Date.now(), name, email };
  
  // 실제로는 데이터베이스에 저장
  console.log('새 사용자 생성:', newUser);
  
  res.status(201).json(newUser);
});

// PUT - 데이터 수정
app.put('/api/users/:id', (req, res) => {
  const { id } = req.params;
  const { name, email } = req.body;
  
  console.log(`사용자 ${id} 정보 수정:`, { name, email });
  res.json({ id, name, email });
});

// DELETE - 데이터 삭제
app.delete('/api/users/:id', (req, res) => {
  const { id } = req.params;
  
  console.log(`사용자 ${id} 삭제`);
  res.status(204).send();
});

app.listen(3000, () => {
  console.log('서버가 포트 3000에서 실행 중');
});
```

### 실시간 통신 구현

```javascript
// Socket.IO로 실시간 채팅 구현
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = socketIo(server);

// 연결된 사용자들 관리
const connectedUsers = new Map();

io.on('connection', (socket) => {
  console.log('새로운 사용자 연결:', socket.id);

  // 사용자 입장
  socket.on('join', (username) => {
    connectedUsers.set(socket.id, username);
    socket.broadcast.emit('userJoined', username);
    console.log(`${username}님이 입장했습니다`);
  });

  // 메시지 전송
  socket.on('message', (message) => {
    const username = connectedUsers.get(socket.id);
    const messageData = {
      user: username,
      content: message,
      timestamp: new Date().toISOString()
    };
    
    io.emit('message', messageData);
  });

  // 연결 해제
  socket.on('disconnect', () => {
    const username = connectedUsers.get(socket.id);
    connectedUsers.delete(socket.id);
    socket.broadcast.emit('userLeft', username);
    console.log(`${username}님이 퇴장했습니다`);
  });
});

server.listen(3000, () => {
  console.log('실시간 채팅 서버 실행 중');
});
```

---


```javascript
// Socket.IO로 실시간 채팅 구현
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = socketIo(server);

// 연결된 사용자들 관리
const connectedUsers = new Map();

io.on('connection', (socket) => {
  console.log('새로운 사용자 연결:', socket.id);

  // 사용자 입장
  socket.on('join', (username) => {
    connectedUsers.set(socket.id, username);
    socket.broadcast.emit('userJoined', username);
    console.log(`${username}님이 입장했습니다`);
  });

  // 메시지 전송
  socket.on('message', (message) => {
    const username = connectedUsers.get(socket.id);
    const messageData = {
      user: username,
      content: message,
      timestamp: new Date().toISOString()
    };
    
    io.emit('message', messageData);
  });

  // 연결 해제
  socket.on('disconnect', () => {
    const username = connectedUsers.get(socket.id);
    connectedUsers.delete(socket.id);
    socket.broadcast.emit('userLeft', username);
    console.log(`${username}님이 퇴장했습니다`);
  });
});

server.listen(3000, () => {
  console.log('실시간 채팅 서버 실행 중');
});
```

---


### 언제 HTTP를 사용할까?
- ✅ 웹페이지 로딩
- ✅ API 호출
- ✅ 파일 업로드/다운로드
- ✅ 폼 제출

### 언제 WebSocket을 사용할까?
- ✅ 실시간 채팅
- ✅ 실시간 알림
- ✅ 온라인 게임
- ✅ 실시간 대시보드

### 언제 TCP를 사용할까?
- ✅ 중요한 데이터 전송
- ✅ 파일 전송
- ✅ 이메일 전송
- ✅ 데이터베이스 연결

### 언제 UDP를 사용할까?
- ✅ 실시간 스트리밍
- ✅ 온라인 게임
- ✅ VoIP (음성 통화)
- ✅ 빠른 응답이 필요한 경우






---


- **다른 기기끼리도 소통 가능**: 애플 맥과 윈도우 PC가 서로 파일을 주고받을 수 있는 이유
- **데이터가 올바르게 전달**: 메시지가 중간에 깨지지 않고 온전히 전달
- **보안과 안정성**: 중요한 정보를 안전하게 주고받기

---


- **다른 기기끼리도 소통 가능**: 애플 맥과 윈도우 PC가 서로 파일을 주고받을 수 있는 이유
- **데이터가 올바르게 전달**: 메시지가 중간에 깨지지 않고 온전히 전달
- **보안과 안정성**: 중요한 정보를 안전하게 주고받기

---



```javascript
// Socket.IO로 실시간 채팅 구현
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = socketIo(server);

// 연결된 사용자들 관리
const connectedUsers = new Map();

io.on('connection', (socket) => {
  console.log('새로운 사용자 연결:', socket.id);

  // 사용자 입장
  socket.on('join', (username) => {
    connectedUsers.set(socket.id, username);
    socket.broadcast.emit('userJoined', username);
    console.log(`${username}님이 입장했습니다`);
  });

  // 메시지 전송
  socket.on('message', (message) => {
    const username = connectedUsers.get(socket.id);
    const messageData = {
      user: username,
      content: message,
      timestamp: new Date().toISOString()
    };
    
    io.emit('message', messageData);
  });

  // 연결 해제
  socket.on('disconnect', () => {
    const username = connectedUsers.get(socket.id);
    connectedUsers.delete(socket.id);
    socket.broadcast.emit('userLeft', username);
    console.log(`${username}님이 퇴장했습니다`);
  });
});

server.listen(3000, () => {
  console.log('실시간 채팅 서버 실행 중');
});
```

---


```javascript
// Socket.IO로 실시간 채팅 구현
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = socketIo(server);

// 연결된 사용자들 관리
const connectedUsers = new Map();

io.on('connection', (socket) => {
  console.log('새로운 사용자 연결:', socket.id);

  // 사용자 입장
  socket.on('join', (username) => {
    connectedUsers.set(socket.id, username);
    socket.broadcast.emit('userJoined', username);
    console.log(`${username}님이 입장했습니다`);
  });

  // 메시지 전송
  socket.on('message', (message) => {
    const username = connectedUsers.get(socket.id);
    const messageData = {
      user: username,
      content: message,
      timestamp: new Date().toISOString()
    };
    
    io.emit('message', messageData);
  });

  // 연결 해제
  socket.on('disconnect', () => {
    const username = connectedUsers.get(socket.id);
    connectedUsers.delete(socket.id);
    socket.broadcast.emit('userLeft', username);
    console.log(`${username}님이 퇴장했습니다`);
  });
});

server.listen(3000, () => {
  console.log('실시간 채팅 서버 실행 중');
});
```

---






## 🏗️ 프로토콜의 3가지 핵심 요소

### 1️⃣ 구문(Syntax) - "어떻게 말할까?"

**데이터를 어떤 형태로 만들지 정하는 규칙**입니다.

예를 들어, HTTP 요청을 보낼 때는 이런 형식을 따라야 합니다:

```javascript
// 올바른 HTTP 요청 형식
const httpRequest = {
  method: 'GET',
  url: '/api/users',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer token123'
  },
  body: null
};

// 실제 HTTP 메시지 형태
const rawHttpMessage = 
`GET /api/users HTTP/1.1
Host: example.com
Content-Type: application/json
Authorization: Bearer token123

`;
```

### 2️⃣ 의미론(Semantics) - "무엇을 말할까?"

**데이터가 어떤 뜻을 가지고 있는지, 어떻게 해석해야 하는지**를 정의합니다.

```javascript
// HTTP 상태 코드의 의미
const httpStatusCodes = {
  200: '성공 - 요청이 정상적으로 처리됨',
  404: '실패 - 요청한 리소스를 찾을 수 없음',
  500: '오류 - 서버 내부 오류가 발생함'
};

// API 응답의 의미
const apiResponse = {
  status: 200,           // 성공을 의미
  data: {                // 실제 데이터
    users: [
      { id: 1, name: '김철수' },
      { id: 2, name: '이영희' }
    ]
  },
  message: '사용자 목록을 성공적으로 가져왔습니다'
};
```

### 3️⃣ 타이밍(Timing) - "언제 말할까?"

**데이터를 언제, 얼마나 빠르게 보낼지**를 결정합니다.

```javascript
// 웹소켓 연결에서의 타이밍 제어
class WebSocketClient {
  constructor(url) {
    this.url = url;
    this.reconnectInterval = 1000; // 1초마다 재연결 시도
    this.heartbeatInterval = 30000; // 30초마다 연결 상태 확인
  }

  connect() {
    this.ws = new WebSocket(this.url);
    
    // 연결 성공 시
    this.ws.onopen = () => {
      console.log('연결됨!');
      this.startHeartbeat();
    };

    // 연결 끊어짐 시
    this.ws.onclose = () => {
      console.log('연결 끊어짐, 재연결 시도...');
      setTimeout(() => this.connect(), this.reconnectInterval);
    };
  }

  startHeartbeat() {
    // 주기적으로 연결 상태 확인
    setInterval(() => {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, this.heartbeatInterval);
  }
}
```

---

