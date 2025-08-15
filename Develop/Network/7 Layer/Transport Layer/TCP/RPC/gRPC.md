---
title: gRPC Google Remote Procedure Call
tags: [network, 7-layer, transport-layer, tcp, rpc]
updated: 2025-08-10
---
# gRPC (Google Remote Procedure Call)

## 배경

gRPC는 구글이 개발한 **원격 프로시저 호출(RPC)** 프레임워크입니다. 

### 🤔 RPC란?
**RPC(Remote Procedure Call)**는 네트워크로 연결된 다른 컴퓨터의 함수를 마치 로컬 함수처럼 호출할 수 있게 해주는 기술입니다.

예를 들어:
```javascript
// 로컬 함수 호출
const result = localFunction("hello");

// RPC를 통한 원격 함수 호출 (같은 방식으로 호출)
const result = remoteFunction("hello"); // 실제로는 네트워크를 통해 다른 서버의 함수가 실행됨
```

### 🎯 gRPC의 핵심 특징
- **HTTP/2 기반**: 현대적인 웹 프로토콜 사용
- **Protocol Buffers**: 효율적인 데이터 직렬화
- **다양한 통신 패턴**: 단방향, 양방향, 스트리밍 지원
- **다국어 지원**: JavaScript, Python, Java, Go 등

![gRPC.svg](..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FgRPC%2FgRPC.svg)

---

| 항목 | gRPC | REST API |
|------|------|----------|
| 프로토콜 | HTTP/2 | HTTP/1.1 |
| 데이터 형식 | Protocol Buffers (바이너리) | JSON (텍스트) |
| 속도 | 빠름 | 상대적으로 느림 |
| 크기 | 작음 | 상대적으로 큼 |

![gRPC & Rest.png](..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FgRPC%2FgRPC%20%26%20Rest.png)

```javascript
// JSON 예시 (82바이트)
{
  "name": "John Doe",
  "age": 30,
  "email": "john@example.com",
  "isActive": true
}

// Protocol Buffers (33바이트) - 같은 데이터
// 바이너리 형태로 저장되어 크기가 훨씬 작음
```

![Protocol Buffer.png](..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FgRPC%2FProtocol%20Buffer.png)

---


```bash
npm init -y
npm install @grpc/grpc-js @grpc/proto-loader
```


```
my-grpc-project/
├── proto/
│   └── chat.proto
├── server.js
├── client.js
└── package.json
```


`server.js`:
```javascript
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');

// proto 파일 로드
const PROTO_PATH = path.resolve(__dirname, './proto/chat.proto');
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true
});

const protoDescriptor = grpc.loadPackageDefinition(packageDefinition);
const chatService = protoDescriptor.chat.ChatService;

// 서버 생성
const server = new grpc.Server();

// 서비스 구현
server.addService(chatService.service, {
  // 단일 요청-응답
  sendMessage: (call, callback) => {
    const { userId, message } = call.request;
    
    console.log(`${userId}: ${message}`);
    
    const response = {
      success: true,
      messageId: `msg_${Date.now()}`
    };
    
    callback(null, response);
  },

  // 서버 스트리밍
  getNotifications: (call) => {
    const { userId } = call.request;
    
    console.log(`${userId}의 알림 스트림 시작`);
    
    // 5초 동안 1초마다 알림 전송
    let count = 0;
    const interval = setInterval(() => {
      if (count >= 5) {
        clearInterval(interval);
        call.end();
        return;
      }
      
      const notification = {
        id: `notif_${count}`,
        title: `알림 ${count + 1}`,
        content: `${userId}님에게 새로운 메시지가 있습니다.`
      };
      
      call.write(notification);
      count++;
    }, 1000);
  },

  // 양방향 스트리밍
  chat: (call) => {
    console.log('채팅 세션 시작');
    
    call.on('data', (message) => {
      const { userId, text } = message;
      console.log(`${userId}: ${text}`);
      
      // 에코 응답
      const response = {
        userId: '서버',
        text: `에코: ${text}`
      };
      
      call.write(response);
    });

    call.on('end', () => {
      console.log('채팅 세션 종료');
      call.end();
    });
  }
});

// 서버 시작
server.bindAsync('0.0.0.0:50051', grpc.ServerCredentials.createInsecure(), () => {
  server.start();
  console.log('gRPC 서버가 포트 50051에서 실행 중입니다.');
});
```


`client.js`:
```javascript
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');

// proto 파일 로드
const PROTO_PATH = path.resolve(__dirname, './proto/chat.proto');
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true
});

const protoDescriptor = grpc.loadPackageDefinition(packageDefinition);
const chatService = protoDescriptor.chat.ChatService;

// 클라이언트 생성
const client = new chatService.ChatService(
  'localhost:50051',
  grpc.credentials.createInsecure()
);

// 1. 단일 요청-응답 테스트
console.log('=== 단일 요청-응답 테스트 ===');
client.sendMessage({ userId: '사용자1', message: '안녕하세요!' }, (error, response) => {
  if (error) {
    console.error('에러:', error);
    return;
  }
  console.log('응답:', response);
});

// 2. 서버 스트리밍 테스트
console.log('\n=== 서버 스트리밍 테스트 ===');
const notificationStream = client.getNotifications({ userId: '사용자1' });

notificationStream.on('data', (notification) => {
  console.log('알림:', notification);
});

notificationStream.on('end', () => {
  console.log('알림 스트림 종료');
});

// 3. 양방향 스트리밍 테스트
setTimeout(() => {
  console.log('\n=== 양방향 스트리밍 테스트 ===');
  const chatStream = client.chat();

  chatStream.on('data', (message) => {
    console.log(`${message.userId}: ${message.text}`);
  });

  chatStream.on('end', () => {
    console.log('채팅 스트림 종료');
  });

  // 메시지 전송
  chatStream.write({ userId: '사용자1', text: '안녕하세요!' });
  chatStream.write({ userId: '사용자1', text: '반갑습니다!' });

  // 3초 후 스트림 종료
  setTimeout(() => {
    chatStream.end();
  }, 3000);
}, 6000);
```


1. **서버 실행**:
```bash
node server.js
```

2. **클라이언트 실행** (새 터미널에서):
```bash
node client.js
```

---


### 🔐 TLS/SSL 설정

```javascript
// 서버 (TLS 사용)
const fs = require('fs');

const serverCredentials = grpc.ServerCredentials.createSsl(
  fs.readFileSync('server.crt'),
  [{
    private_key: fs.readFileSync('server.key'),
    cert_chain: fs.readFileSync('server.crt')
  }],
  true
);

server.bindAsync('0.0.0.0:50051', serverCredentials, () => {
  server.start();
});

// 클라이언트 (TLS 사용)
const clientCredentials = grpc.credentials.createSsl(
  fs.readFileSync('ca.crt')
);

const client = new chatService.ChatService(
  'localhost:50051',
  clientCredentials
);
```

### 🔑 인증 구현

```javascript
// 서버에서 인증 미들웨어
const authenticate = (call, callback) => {
  const metadata = call.metadata;
  const token = metadata.get('authorization')[0];
  
  if (!token || token !== 'valid-token') {
    callback({
      code: grpc.status.UNAUTHENTICATED,
      message: '인증 실패'
    });
    return false;
  }
  
  return true;
};

// 서비스에서 인증 사용
sendMessage: (call, callback) => {
  if (!authenticate(call, callback)) return;
  
  // 비즈니스 로직...
}
```

---


```javascript
// 서버에서 인증 미들웨어
const authenticate = (call, callback) => {
  const metadata = call.metadata;
  const token = metadata.get('authorization')[0];
  
  if (!token || token !== 'valid-token') {
    callback({
      code: grpc.status.UNAUTHENTICATED,
      message: '인증 실패'
    });
    return false;
  }
  
  return true;
};

// 서비스에서 인증 사용
sendMessage: (call, callback) => {
  if (!authenticate(call, callback)) return;
  
  // 비즈니스 로직...
}
```

---


### 1. 마이크로서비스 통신
```javascript
// 사용자 서비스
const userClient = new UserService('user-service:50051', credentials);

// 주문 서비스에서 사용자 정보 조회
const getUserInfo = async (userId) => {
  return new Promise((resolve, reject) => {
    userClient.getUser({ userId }, (error, response) => {
      if (error) reject(error);
      else resolve(response.user);
    });
  });
};
```

### 2. 실시간 채팅
```javascript
// 채팅 클라이언트
const chatStream = chatClient.joinRoom({ roomId: 'room1' });

chatStream.on('data', (message) => {
  displayMessage(message);
});

// 메시지 전송
const sendMessage = (text) => {
  chatStream.write({
    userId: currentUser.id,
    text: text,
    timestamp: Date.now()
  });
};
```

### 3. 파일 업로드
```javascript
// 파일 업로드 클라이언트
const uploadStream = fileClient.uploadFile((error, response) => {
  if (error) {
    console.error('업로드 실패:', error);
  } else {
    console.log('업로드 완료:', response.fileId);
  }
});

// 파일 청크 전송
const uploadFile = (file) => {
  const chunkSize = 1024 * 1024; // 1MB
  let offset = 0;
  
  while (offset < file.size) {
    const chunk = file.slice(offset, offset + chunkSize);
    uploadStream.write({ data: chunk });
    offset += chunkSize;
  }
  
  uploadStream.end();
};
```

---


### 🔧 gRPC 구성 요소
- **Service**: 제공할 서비스 정의
- **Message**: 데이터 구조 정의
- **RPC Method**: 실제 함수 정의
- **Stream**: 데이터 스트림 처리

### 🌐 HTTP/2 특징
- **멀티플렉싱**: 하나의 연결로 여러 요청/응답 처리
- **헤더 압축**: HPACK을 통한 헤더 크기 최적화
- **서버 푸시**: 서버가 클라이언트에게 데이터를 미리 전송

### 📦 Protocol Buffers 특징
- **바이너리 형식**: 텍스트가 아닌 바이너리로 저장
- **스키마 기반**: .proto 파일로 데이터 구조 정의
- **버전 관리**: 필드 번호를 통한 하위 호환성 유지






---


```javascript
// 서버에서 인증 미들웨어
const authenticate = (call, callback) => {
  const metadata = call.metadata;
  const token = metadata.get('authorization')[0];
  
  if (!token || token !== 'valid-token') {
    callback({
      code: grpc.status.UNAUTHENTICATED,
      message: '인증 실패'
    });
    return false;
  }
  
  return true;
};

// 서비스에서 인증 사용
sendMessage: (call, callback) => {
  if (!authenticate(call, callback)) return;
  
  // 비즈니스 로직...
}
```

---


```javascript
// 서버에서 인증 미들웨어
const authenticate = (call, callback) => {
  const metadata = call.metadata;
  const token = metadata.get('authorization')[0];
  
  if (!token || token !== 'valid-token') {
    callback({
      code: grpc.status.UNAUTHENTICATED,
      message: '인증 실패'
    });
    return false;
  }
  
  return true;
};

// 서비스에서 인증 사용
sendMessage: (call, callback) => {
  if (!authenticate(call, callback)) return;
  
  // 비즈니스 로직...
}
```

---






## 🚀 gRPC vs REST API 비교

## 🔄 gRPC 통신 패턴

### 1️⃣ Unary RPC (단일 요청-응답)
가장 기본적인 패턴으로, 클라이언트가 하나의 요청을 보내면 서버가 하나의 응답을 반환합니다.

```javascript
// 클라이언트
const response = await client.getUser({ userId: "123" });
console.log(response.user); // 사용자 정보

// 서버
function getUser(call, callback) {
  const userId = call.request.userId;
  const user = findUser(userId);
  callback(null, { user });
}
```

### 2️⃣ Server Streaming RPC (서버 스트리밍)
클라이언트가 하나의 요청을 보내면 서버가 여러 개의 응답을 스트림으로 전송합니다.

```javascript
// 클라이언트
const stream = client.getNotifications({ userId: "123" });
stream.on('data', (notification) => {
  console.log('새 알림:', notification);
});

// 서버
function getNotifications(call) {
  const userId = call.request.userId;
  
  // 실시간으로 알림 전송
  setInterval(() => {
    const notification = generateNotification(userId);
    call.write(notification);
  }, 1000);
}
```

### 3️⃣ Client Streaming RPC (클라이언트 스트리밍)
클라이언트가 여러 개의 요청을 스트림으로 보내면 서버가 하나의 응답을 반환합니다.

```javascript
// 클라이언트
const stream = client.uploadFiles((error, response) => {
  console.log('업로드 완료:', response.summary);
});

// 여러 파일을 순차적으로 전송
files.forEach(file => {
  stream.write({ fileData: file });
});
stream.end();

// 서버
function uploadFiles(call, callback) {
  let totalSize = 0;
  let fileCount = 0;
  
  call.on('data', (request) => {
    totalSize += request.fileData.length;
    fileCount++;
  });
  
  call.on('end', () => {
    callback(null, { 
      summary: `${fileCount}개 파일, 총 ${totalSize}바이트 업로드 완료` 
    });
  });
}
```

### 4️⃣ Bidirectional Streaming RPC (양방향 스트리밍)
클라이언트와 서버가 독립적으로 스트림을 통해 데이터를 주고받습니다.

```javascript
// 클라이언트
const stream = client.chat();

stream.on('data', (message) => {
  console.log('받은 메시지:', message.text);
});

// 메시지 전송
stream.write({ text: "안녕하세요!" });
stream.write({ text: "반갑습니다!" });

// 서버
function chat(call) {
  call.on('data', (message) => {
    console.log('클라이언트 메시지:', message.text);
    
    // 에코 응답
    call.write({ text: `에코: ${message.text}` });
  });
}
```

---

## 📝 Protocol Buffers (Protobuf)

### 🔍 Protocol Buffers란?
구글이 개발한 **바이너리 직렬화 데이터 형식**입니다. JSON보다 효율적이고 빠른 데이터 전송이 가능합니다.

### 📄 .proto 파일 작성법

```protobuf
syntax = "proto3";  // Protocol Buffers 버전 3 사용

package chat;  // 패키지명

// 서비스 정의
service ChatService {
  // 단일 요청-응답
  rpc SendMessage (MessageRequest) returns (MessageResponse) {}
  
  // 서버 스트리밍
  rpc GetNotifications (UserRequest) returns (stream Notification) {}
  
  // 클라이언트 스트리밍
  rpc UploadFiles (stream FileData) returns (UploadResponse) {}
  
  // 양방향 스트리밍
  rpc Chat (stream ChatMessage) returns (stream ChatMessage) {}
}

// 메시지 정의
message MessageRequest {
  string userId = 1;      // 필드 번호 1
  string message = 2;     // 필드 번호 2
  int64 timestamp = 3;    // 필드 번호 3
}

message MessageResponse {
  bool success = 1;
  string messageId = 2;
}

message UserRequest {
  string userId = 1;
}

message Notification {
  string id = 1;
  string title = 2;
  string content = 3;
}

message FileData {
  bytes data = 1;
  string filename = 2;
}

message UploadResponse {
  int32 fileCount = 1;
  int64 totalSize = 2;
}

message ChatMessage {
  string userId = 1;
  string text = 2;
}
```

### ⚡ Protobuf의 장점

1. **빠른 통신**
   - JSON 대비 2-3배 작은 데이터 크기
   - 파싱 속도가 빠름

2. **타입 안전성**
   - 컴파일 타임에 타입 검사
   - 런타임 에러 감소

3. **자동 코드 생성**
   - .proto 파일로부터 JavaScript 코드 자동 생성

### ⚠️ Protobuf의 단점

1. **가독성 부족**
   - 바이너리 형태로 사람이 읽기 어려움
   - .proto 파일이 필요

2. **학습 곡선**
   - 새로운 문법 학습 필요

---

## 🛠️ JavaScript로 gRPC 구현하기

### 📄 Protocol Buffer 정의

`proto/chat.proto`:
```protobuf
syntax = "proto3";

package chat;

service ChatService {
  rpc SendMessage (MessageRequest) returns (MessageResponse) {}
  rpc GetNotifications (UserRequest) returns (stream Notification) {}
  rpc Chat (stream ChatMessage) returns (stream ChatMessage) {}
}

message MessageRequest {
  string userId = 1;
  string message = 2;
}

message MessageResponse {
  bool success = 1;
  string messageId = 2;
}

message UserRequest {
  string userId = 1;
}

message Notification {
  string id = 1;
  string title = 2;
  string content = 3;
}

message ChatMessage {
  string userId = 1;
  string text = 2;
}
```

