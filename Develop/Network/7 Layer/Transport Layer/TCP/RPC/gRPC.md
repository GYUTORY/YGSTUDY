# gRPC

---

# 내용
1. gRPC는 구글이 오픈소스로 공개한 원격 프로시저 호출을 위한 바이너리 프로토콜이다. 
2. 성능과 간편함으로 인기를 얻은 REST의 대안이다. 
3. gRPC는 [Http 2.0](..%2F..%2F..%2FApplication%20Layer%2FHttp%2FHttp%EC%99%80%20Http%202.0.md)에 대한 전이중(full duplex) 연결을 제공한다.
![gRPC.svg](..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FgRPC%2FgRPC.svg)

---

# gRPC 특징 

## 1. 성능
- 네트워크 요청으로 보내기 위해 Protobuf를 직렬화(Serialization) 및 역직렬화(Deserialization)하는 작업은 JSON 형태의 직렬화/역직렬화 보다 빠르다.
- 또한 gRPC의 네트워크 속도가 HTTP POST/GET 속도보다 빠르다. 특히 POST 요청 시 많은 차이를 보인다.
- HTTP/2 기반으로 동작하여 멀티플렉싱, 헤더 압축, 서버 푸시 등의 기능을 지원한다.
- 바이너리 프로토콜을 사용하여 데이터 전송 효율성이 높다.

## 2. REST API 지원
- Protobuf로 정의된 API는 envoyproxy나 grpc-gateway 같은 gateway 를 통해 REST API로 제공 가능하다. 
- gRPC로 정의된 API를 OpenAPI 프로토콜로 변환하여 REST API를 사용하는 클라이언트에도 API-우선 방식을 적용할 수 있다.
- REST API와 gRPC를 동시에 지원하여 점진적인 마이그레이션이 가능하다.

## 3. 통신 패턴
gRPC는 다음과 같은 4가지 통신 패턴을 지원한다:

1. Unary RPC (단일 요청-응답)
   - 클라이언트가 단일 요청을 보내고 서버가 단일 응답을 반환
   - 가장 기본적인 RPC 패턴

2. Server Streaming RPC (서버 스트리밍)
   - 클라이언트가 단일 요청을 보내고 서버가 스트림으로 응답
   - 실시간 데이터 전송에 적합

3. Client Streaming RPC (클라이언트 스트리밍)
   - 클라이언트가 스트림으로 요청을 보내고 서버가 단일 응답을 반환
   - 대용량 데이터 업로드에 적합

4. Bidirectional Streaming RPC (양방향 스트리밍)
   - 클라이언트와 서버가 독립적으로 스트림을 통해 데이터를 주고받음
   - 실시간 양방향 통신에 적합

---

## gRPC와 REST의 차이점 및 특징

![gRPC & Rest.png](..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FgRPC%2FgRPC%20%26%20Rest.png)

1. gRPC는 HTTP2를 사용한다. (REST는 HTTP1.1)
2. gRPC는 protocol buffer data format을 사용한다. REST는 주로 JSON을 사용한다.
3. gRPC를 활용하면 server-side streaming, client-side streaming, bidirectional-streaming과 같은 HTTP/2가 가진 feature를 활용할 수 있다.
4. 내부적으로는 Netty(소켓통신)을 사용하고 있다.
5. 이미 배포한 서비스를 중단할 필요 없이 데이터 구조를 바꿀 수 있다.

---

## 프로토콜 버퍼(Protocol Buffers)

### 1. 프로토콜 버퍼란?
- 프로토콜 버퍼(Protocol Buffers)는 구글에서 개발한 바이너리 직렬화 데이터 형식입니다.
- 이는 다양한 프로그래밍 언어에서 구조화된 데이터를 직렬화하고, 효율적으로 전송하고 저장하기 위한 목적으로 사용됩니다.

![Protocol Buffer.png](..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FgRPC%2FProtocol%20Buffer.png)
```
위 그림은 json과 Protocol buffer를 사용한 직렬화의 용량 차이이다.
json: 82byte
protocol buffer: 33 byte
```

### 2. 프로토콜 버퍼의 장점
1) 통신이 빠릅니다.
   - 같은 데이터를 보내더라도 데이터의 크기가 작아 같은 시간에 더 많은 데이터를 보낼 수 있고, 더 빠르게 보내질 수 있습니다.
2) 파싱을 할 필요가 없습니다.
   - json 포맷을 사용하게 되면 받은 데이터를 다시 객체로 파싱해서 사용하는데, protobuf를 사용하면 byte를 받아서 그 byte 그대로 메모리에 써버리고 객체 레퍼런스가 가리키는 형태로 사용하기 때문에 별도의 파싱이 필요가 없어집니다.
3) 강력한 타입 시스템
   - 명시적인 타입 정의로 런타임 에러를 줄일 수 있습니다.
4) 자동 코드 생성
   - .proto 파일로부터 다양한 언어의 코드를 자동 생성할 수 있습니다.

### 3. 프로토콜 버퍼의 단점
1) 인간이 읽기가 어렵습니다.
   - json 포맷은 사람이 읽기 편한 형태로 되어 있는데, .proto 파일이 없으면 의미를 알 수 없을 정도로 protobuf로 쓴 데이터는 사람이 읽기가 어렵습니다. 
   - 즉, .proto 파일이 반드시 있어야지 protobuf로 쓰여진 데이터를 읽을 수가 있다는 단점이 있습니다.
   - 따라서 외부 API 통신에는 보통 사용되지 않고(각 클라이언트마다 .proto 파일이 있어야 합니다), 내부 서비스(Microservice 등)에서 주로 사용됩니다.
2) proto문법을 배워야 합니다.
   - .proto파일은 json과 같이 key, value 쌍으로 단순하게 되어 있지 않고, 작성 방법에 따른 문법을 배워야하기 때문에 난이도가 있습니다.

---

## TypeScript로 구현하는 gRPC

### 1. 프로젝트 설정

먼저 필요한 패키지들을 설치합니다:

```bash
npm init -y
npm install @grpc/grpc-js @grpc/proto-loader typescript ts-node @types/node
```

### 2. Protocol Buffer 정의

`proto/hello.proto` 파일을 생성합니다:

```protobuf
syntax = "proto3";

package hello;

// 서비스 정의
service Greeter {
  // 단일 요청-응답
  rpc SayHello (HelloRequest) returns (HelloResponse) {}
  
  // 서버 스트리밍
  rpc SayHelloServerStream (HelloRequest) returns (stream HelloResponse) {}
  
  // 클라이언트 스트리밍
  rpc SayHelloClientStream (stream HelloRequest) returns (HelloResponse) {}
  
  // 양방향 스트리밍
  rpc SayHelloBidirectional (stream HelloRequest) returns (stream HelloResponse) {}
}

// 요청 메시지 정의
message HelloRequest {
  string name = 1;
}

// 응답 메시지 정의
message HelloResponse {
  string message = 1;
}
```

### 3. 서버 구현

`server.ts` 파일을 생성합니다:

```typescript
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import path from 'path';

// proto 파일 로드
const PROTO_PATH = path.resolve(__dirname, './proto/hello.proto');
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true
});

const protoDescriptor = grpc.loadPackageDefinition(packageDefinition);
const hello = protoDescriptor.hello;

// 서버 구현
const server = new grpc.Server();

// 단일 요청-응답 구현
server.addService(hello.Greeter.service, {
  sayHello: (call: any, callback: any) => {
    const response = {
      message: `Hello ${call.request.name}!`
    };
    callback(null, response);
  },

  // 서버 스트리밍 구현
  sayHelloServerStream: (call: any) => {
    const name = call.request.name;
    for (let i = 0; i < 5; i++) {
      call.write({
        message: `Hello ${name}! Message ${i + 1}`
      });
    }
    call.end();
  },

  // 클라이언트 스트리밍 구현
  sayHelloClientStream: (call: any, callback: any) => {
    let names: string[] = [];
    
    call.on('data', (request: any) => {
      names.push(request.name);
    });

    call.on('end', () => {
      callback(null, {
        message: `Hello ${names.join(', ')}!`
      });
    });
  },

  // 양방향 스트리밍 구현
  sayHelloBidirectional: (call: any) => {
    call.on('data', (request: any) => {
      call.write({
        message: `Hello ${request.name}!`
      });
    });

    call.on('end', () => {
      call.end();
    });
  }
});

// 서버 시작
server.bindAsync('0.0.0.0:50051', grpc.ServerCredentials.createInsecure(), () => {
  server.start();
  console.log('gRPC server running on port 50051');
});
```

### 4. 클라이언트 구현

`client.ts` 파일을 생성합니다:

```typescript
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import path from 'path';

// proto 파일 로드
const PROTO_PATH = path.resolve(__dirname, './proto/hello.proto');
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true
});

const protoDescriptor = grpc.loadPackageDefinition(packageDefinition);
const hello = protoDescriptor.hello;

// 클라이언트 생성
const client = new hello.Greeter(
  'localhost:50051',
  grpc.credentials.createInsecure()
);

// 단일 요청-응답 호출
client.sayHello({ name: 'World' }, (error: any, response: any) => {
  if (error) {
    console.error(error);
    return;
  }
  console.log('SayHello Response:', response.message);
});

// 서버 스트리밍 호출
const serverStream = client.sayHelloServerStream({ name: 'World' });
serverStream.on('data', (response: any) => {
  console.log('ServerStream Response:', response.message);
});
serverStream.on('end', () => {
  console.log('ServerStream ended');
});

// 클라이언트 스트리밍 호출
const clientStream = client.sayHelloClientStream((error: any, response: any) => {
  if (error) {
    console.error(error);
    return;
  }
  console.log('ClientStream Response:', response.message);
});

// 여러 요청 전송
['Alice', 'Bob', 'Charlie'].forEach(name => {
  clientStream.write({ name });
});
clientStream.end();

// 양방향 스트리밍 호출
const bidirectionalStream = client.sayHelloBidirectional();

bidirectionalStream.on('data', (response: any) => {
  console.log('Bidirectional Response:', response.message);
});

bidirectionalStream.on('end', () => {
  console.log('Bidirectional stream ended');
});

// 여러 요청 전송
['Alice', 'Bob', 'Charlie'].forEach(name => {
  bidirectionalStream.write({ name });
});
bidirectionalStream.end();
```

### 5. 실행 방법

1. 서버 실행:
```bash
ts-node server.ts
```

2. 클라이언트 실행:
```bash
ts-node client.ts
```

---

## gRPC 사용 시 주의사항

1. 보안
   - TLS/SSL을 사용하여 통신을 암호화해야 합니다.
   - 인증 메커니즘을 구현하여 클라이언트 인증을 수행해야 합니다.

2. 에러 처리
   - gRPC는 상세한 에러 코드와 메시지를 제공합니다.
   - 클라이언트와 서버 모두 적절한 에러 처리를 구현해야 합니다.

3. 성능 최적화
   - 스트리밍을 적절히 활용하여 네트워크 효율성을 높일 수 있습니다.
   - 메시지 크기와 빈도를 고려하여 설계해야 합니다.

4. 버전 관리
   - .proto 파일의 변경 시 하위 호환성을 유지해야 합니다.
   - 필드 번호는 재사용하지 않아야 합니다.

---

## 실제 사용 사례

1. 마이크로서비스 아키텍처
   - 서비스 간 통신에 gRPC를 사용하여 효율적인 통신 구현
   - Polyglot 환경에서의 일관된 API 정의

2. 모바일 앱 백엔드
   - 모바일 앱과 서버 간의 효율적인 통신
   - 배터리 사용량 최적화

3. IoT 디바이스 통신
   - 제한된 리소스 환경에서의 효율적인 통신
   - 실시간 데이터 전송

4. 실시간 애플리케이션
   - 양방향 스트리밍을 활용한 실시간 기능 구현
   - 채팅, 게임, 실시간 모니터링 등