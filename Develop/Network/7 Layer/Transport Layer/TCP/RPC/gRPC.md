---
title: gRPC Google Remote Procedure Call
tags: [network, 7-layer, transport-layer, tcp, rpc, grpc, protobuf]
updated: 2026-03-31
---

# gRPC (Google Remote Procedure Call)

## 개요

gRPC는 구글이 개발한 원격 프로시저 호출(RPC) 프레임워크다. HTTP/2와 Protocol Buffers를 기반으로 서비스 간 통신에 사용한다.

### RPC란?

RPC(Remote Procedure Call)는 네트워크로 연결된 다른 컴퓨터의 함수를 마치 로컬 함수처럼 호출할 수 있게 해주는 기술이다.

```javascript
// 로컬 함수 호출
const result = localFunction("hello");

// RPC를 통한 원격 함수 호출 (같은 방식으로 호출)
const result = remoteFunction("hello"); // 실제로는 네트워크를 통해 다른 서버의 함수가 실행됨
```

### gRPC의 주요 특징

- HTTP/2 기반 — 멀티플렉싱, 헤더 압축, 바이너리 프레이밍
- Protocol Buffers — 바이너리 직렬화로 JSON 대비 데이터 크기 절반 이하
- 4가지 통신 패턴 — Unary, Server Streaming, Client Streaming, Bidirectional Streaming
- 코드 생성 — .proto 파일에서 클라이언트/서버 스텁 자동 생성
- 다국어 지원 — Java, Go, Python, C++, Node.js 등

![gRPC.svg](..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FgRPC%2FgRPC.svg)

---

## gRPC vs REST API 비교

| 항목 | gRPC | REST API |
|------|------|----------|
| 프로토콜 | HTTP/2 | HTTP/1.1 |
| 데이터 형식 | Protocol Buffers (바이너리) | JSON (텍스트) |
| 속도 | 빠름 | 상대적으로 느림 |
| 크기 | 작음 | 상대적으로 큼 |
| 스트리밍 | 네이티브 지원 | 제한적 |
| 브라우저 지원 | 제한적 (gRPC-Web 필요) | 완전 지원 |

![gRPC & Rest.png](..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FgRPC%2FgRPC%20%26%20Rest.png)

### 데이터 크기 비교

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

## gRPC 통신 패턴

### Unary RPC (단일 요청-응답)

가장 기본적인 패턴으로, 클라이언트가 하나의 요청을 보내면 서버가 하나의 응답을 반환한다.

```javascript
// 클라이언트
const response = await client.getUser({ userId: "123" });
console.log(response.user);

// 서버
function getUser(call, callback) {
  const userId = call.request.userId;
  const user = findUser(userId);
  callback(null, { user });
}
```

### Server Streaming RPC (서버 스트리밍)

클라이언트가 하나의 요청을 보내면 서버가 여러 개의 응답을 스트림으로 전송한다.

```javascript
// 클라이언트
const stream = client.getNotifications({ userId: "123" });
stream.on('data', (notification) => {
  console.log('새 알림:', notification);
});

// 서버
function getNotifications(call) {
  const userId = call.request.userId;
  setInterval(() => {
    const notification = generateNotification(userId);
    call.write(notification);
  }, 1000);
}
```

### Client Streaming RPC (클라이언트 스트리밍)

클라이언트가 여러 개의 요청을 스트림으로 보내면 서버가 하나의 응답을 반환한다.

```javascript
// 클라이언트
const stream = client.uploadFiles((error, response) => {
  console.log('업로드 완료:', response.summary);
});

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

### Bidirectional Streaming RPC (양방향 스트리밍)

클라이언트와 서버가 독립적으로 스트림을 통해 데이터를 주고받는다.

```javascript
// 클라이언트
const stream = client.chat();

stream.on('data', (message) => {
  console.log('받은 메시지:', message.text);
});

stream.write({ text: "안녕하세요!" });
stream.write({ text: "반갑습니다!" });

// 서버
function chat(call) {
  call.on('data', (message) => {
    const { userId, text } = message;
    call.write({ text: `에코: ${text}` });
  });
}
```

---

## Protocol Buffers (Protobuf)

구글이 개발한 바이너리 직렬화 데이터 형식이다. JSON보다 작고 빠르다.

### .proto 파일 기본 구조

```protobuf
syntax = "proto3";

package chat;

service ChatService {
  // Unary
  rpc SendMessage (MessageRequest) returns (MessageResponse) {}
  // Server Streaming
  rpc GetNotifications (UserRequest) returns (stream Notification) {}
  // Client Streaming
  rpc UploadFiles (stream FileData) returns (UploadResponse) {}
  // Bidirectional Streaming
  rpc Chat (stream ChatMessage) returns (stream ChatMessage) {}
}

message MessageRequest {
  string userId = 1;      // 필드 번호 1
  string message = 2;     // 필드 번호 2
  int64 timestamp = 3;    // 필드 번호 3
}

message MessageResponse {
  bool success = 1;
  string messageId = 2;
}
```

### Proto 파일 관리 — 실무에서 자주 실수하는 부분

#### 필드 번호 삭제/재사용 금지

proto에서 필드 번호는 와이어 포맷에서 식별자 역할을 한다. 한번 배포된 필드 번호를 삭제하고 다른 필드에 재사용하면, 이전 버전 클라이언트가 보낸 데이터를 새 필드로 잘못 파싱하는 문제가 생긴다.

```protobuf
// 잘못된 예 — 필드 번호 2를 삭제 후 재사용
message User {
  string name = 1;
  // string email = 2;  삭제됨
  string phone = 2;     // 이전에 email이던 번호를 phone에 재사용 → 장애 발생
}

// 올바른 예 — reserved로 번호를 예약
message User {
  string name = 1;
  reserved 2;           // 삭제된 email 필드 번호
  reserved "email";     // 필드 이름도 예약해서 실수로 재사용 방지
  string phone = 3;     // 새 번호 사용
}
```

`reserved`를 쓰면 다른 개발자가 해당 번호나 이름을 사용하려 할 때 protoc 컴파일러가 에러를 낸다. 팀 단위로 작업할 때 반드시 써야 한다.

#### oneof — 여러 필드 중 하나만 설정

```protobuf
message PaymentMethod {
  string id = 1;
  oneof method {
    CreditCard credit_card = 2;
    BankTransfer bank_transfer = 3;
    Crypto crypto = 4;
  }
}
```

`oneof` 안의 필드는 동시에 하나만 값을 가진다. 하나를 설정하면 나머지는 자동으로 클리어된다. 주의할 점은 `oneof` 안에 `repeated` 필드를 넣을 수 없다.

#### map — key-value 구조

```protobuf
message Config {
  string service_name = 1;
  map<string, string> env_vars = 2;      // 환경 변수
  map<string, int32> port_mapping = 3;   // 포트 매핑
}
```

`map`의 key 타입은 정수형이나 string만 가능하다. float, bytes, enum은 key로 쓸 수 없다. `map` 필드에는 `repeated`를 붙일 수 없다.

#### 필드 번호 관리 규칙

필드 번호 1~15는 와이어 포맷에서 1바이트만 사용한다. 16~2047은 2바이트를 쓴다. 자주 사용하는 필드를 1~15에 배치하면 메시지 크기를 줄일 수 있다. 19000~19999는 protobuf 내부용으로 예약되어 있어 사용 불가다.

---

## gRPC 상태 코드와 에러 처리

REST가 HTTP 상태 코드를 쓰듯, gRPC는 자체 상태 코드 체계를 사용한다. 실무에서 자주 마주치는 코드와 대응 방법을 정리했다.

### 주요 상태 코드

| 코드 | 이름 | 언제 발생하는가 | 대응 방법 |
|------|------|-----------------|-----------|
| 0 | OK | 정상 처리 | — |
| 1 | CANCELLED | 클라이언트가 요청 취소 | 서버에서 context 취소 감지 후 리소스 정리 |
| 3 | INVALID_ARGUMENT | 잘못된 요청 파라미터 | 재시도 의미 없음. 클라이언트 쪽 수정 필요 |
| 4 | DEADLINE_EXCEEDED | 타임아웃 | 재시도 가능. deadline 값 조정 검토 |
| 5 | NOT_FOUND | 리소스 없음 | 재시도 의미 없음 |
| 7 | PERMISSION_DENIED | 권한 없음 | 인증 토큰 갱신 후 재시도 |
| 8 | RESOURCE_EXHAUSTED | 리소스 한도 초과 (Rate Limit 등) | 백오프 후 재시도 |
| 13 | INTERNAL | 서버 내부 에러 | 재시도 가능하지만, 반복되면 서버 쪽 로그 확인 |
| 14 | UNAVAILABLE | 서버 일시적 사용 불가 | 백오프 후 재시도. 배포 중이거나 서버가 내려간 상태 |
| 16 | UNAUTHENTICATED | 인증 실패 | 토큰 갱신 후 재시도 |

### DEADLINE_EXCEEDED

서비스 체인에서 가장 흔하게 만나는 에러다. A → B → C로 호출이 이어질 때, A의 deadline이 3초인데 B에서 2.5초를 소모하면 C는 0.5초 안에 응답해야 한다. C가 0.5초를 넘기면 A에서 DEADLINE_EXCEEDED가 발생한다.

```java
// Java에서 deadline 설정
ManagedChannel channel = ManagedChannelBuilder
    .forAddress("localhost", 50051)
    .usePlaintext()
    .build();

UserServiceGrpc.UserServiceBlockingStub stub = UserServiceGrpc.newBlockingStub(channel);

try {
    GetUserResponse response = stub
        .withDeadlineAfter(3, TimeUnit.SECONDS)  // 3초 deadline
        .getUser(GetUserRequest.newBuilder().setUserId("123").build());
} catch (StatusRuntimeException e) {
    if (e.getStatus().getCode() == Status.Code.DEADLINE_EXCEEDED) {
        // 타임아웃 — 재시도 또는 폴백 로직
        log.warn("getUser 타임아웃 발생. userId={}", "123");
    }
}
```

### UNAVAILABLE

서버가 내려가 있거나, 배포 중이거나, 네트워크 문제일 때 발생한다. 일시적인 상태이므로 exponential backoff로 재시도하는 게 맞다.

```java
// gRPC 클라이언트에서 재시도 설정 (서비스 설정 JSON)
// retryPolicy를 channel에 설정하면 클라이언트가 자동으로 재시도한다
String retryPolicy = "{\n"
    + "  \"methodConfig\": [{\n"
    + "    \"name\": [{\"service\": \"user.UserService\"}],\n"
    + "    \"retryPolicy\": {\n"
    + "      \"maxAttempts\": 3,\n"
    + "      \"initialBackoff\": \"0.5s\",\n"
    + "      \"maxBackoff\": \"10s\",\n"
    + "      \"backoffMultiplier\": 2.0,\n"
    + "      \"retryableStatusCodes\": [\"UNAVAILABLE\", \"DEADLINE_EXCEEDED\"]\n"
    + "    }\n"
    + "  }]\n"
    + "}";

ManagedChannel channel = ManagedChannelBuilder
    .forAddress("localhost", 50051)
    .defaultServiceConfig(new Gson().fromJson(retryPolicy, Map.class))
    .enableRetry()
    .usePlaintext()
    .build();
```

주의할 점 — INVALID_ARGUMENT, NOT_FOUND 같은 코드는 재시도해도 결과가 같다. retryableStatusCodes에 넣으면 불필요한 요청만 늘어난다.

---

## Deadline/Timeout 전파

gRPC에서 deadline은 "이 시각까지 응답을 받겠다"는 절대 시각이다. timeout은 "지금부터 N초"라는 상대 시간이고, 클라이언트가 보낼 때 절대 시각으로 변환된다.

### 서비스 체인에서의 전파

```
Client (deadline: 5초 남음)
  → Service A (2초 소모, 3초 남은 채로 전파)
    → Service B (1초 소모, 2초 남은 채로 전파)
      → Service C (2초 안에 응답해야 함)
```

gRPC는 deadline을 메타데이터로 자동 전파한다. Service A가 Service B를 호출할 때, 남은 deadline이 함께 전달된다. 별도 설정 없이 동작하지만, 각 서비스에서 `Context`를 확인해야 한다.

```java
// Java — 현재 남은 deadline 확인
@Override
public void processOrder(ProcessOrderRequest request,
                          StreamObserver<ProcessOrderResponse> responseObserver) {

    // 현재 컨텍스트의 deadline 확인
    Deadline deadline = Context.current().getDeadline();
    if (deadline != null) {
        long remaining = deadline.timeRemaining(TimeUnit.MILLISECONDS);
        log.info("남은 deadline: {}ms", remaining);

        if (remaining < 500) {
            // 남은 시간이 너무 적으면 빠르게 실패
            responseObserver.onError(Status.DEADLINE_EXCEEDED
                .withDescription("남은 deadline 부족: " + remaining + "ms")
                .asRuntimeException());
            return;
        }
    }

    // 하위 서비스 호출 시 현재 컨텍스트의 deadline이 자동 전파됨
    PaymentResponse paymentResp = paymentStub.charge(chargeRequest);
    // ...
}
```

### deadline을 설정 안 하면 생기는 문제

deadline을 설정하지 않으면 서버가 응답할 때까지 무한정 대기한다. 서버가 hang 걸리면 클라이언트도 같이 멈춘다. 마이크로서비스 환경에서는 하나의 hang이 전체 서비스 체인을 멈추는 cascading failure로 이어진다.

모든 gRPC 호출에는 반드시 deadline을 설정해야 한다. 서비스별로 적절한 값이 다르므로, 각 RPC 메서드의 예상 응답 시간을 기준으로 여유분을 더해서 설정한다. 보통 P99 응답 시간의 2~3배를 기준으로 잡는다.

---

## Interceptor

gRPC의 Interceptor는 서블릿 필터나 Spring의 HandlerInterceptor와 같은 역할이다. 모든 RPC 호출 전후에 공통 로직을 끼워넣는다. 인증, 로깅, 메트릭 수집에 쓴다.

### 서버 Interceptor

```java
// 인증 Interceptor
public class AuthInterceptor implements ServerInterceptor {

    @Override
    public <ReqT, RespT> ServerCall.Listener<ReqT> interceptCall(
            ServerCall<ReqT, RespT> call,
            Metadata headers,
            ServerCallHandler<ReqT, RespT> next) {

        String token = headers.get(
            Metadata.Key.of("authorization", Metadata.ASCII_STRING_MARSHALLER));

        if (token == null || !validateToken(token)) {
            call.close(Status.UNAUTHENTICATED
                .withDescription("유효하지 않은 인증 토큰"), new Metadata());
            return new ServerCall.Listener<>() {};  // 빈 리스너 반환
        }

        // 인증 성공 시 사용자 정보를 Context에 저장
        Context ctx = Context.current()
            .withValue(USER_ID_KEY, extractUserId(token));

        return Contexts.interceptCall(ctx, call, headers, next);
    }

    // Context Key 정의
    public static final Context.Key<String> USER_ID_KEY = Context.key("userId");
}
```

```java
// 로깅 Interceptor
public class LoggingInterceptor implements ServerInterceptor {

    @Override
    public <ReqT, RespT> ServerCall.Listener<ReqT> interceptCall(
            ServerCall<ReqT, RespT> call,
            Metadata headers,
            ServerCallHandler<ReqT, RespT> next) {

        String method = call.getMethodDescriptor().getFullMethodName();
        long startTime = System.currentTimeMillis();
        log.info("gRPC 호출 시작: {}", method);

        // 응답 시 로깅을 위해 ServerCall을 래핑
        ServerCall<ReqT, RespT> wrappedCall = new ForwardingServerCall
                .SimpleForwardingServerCall<>(call) {
            @Override
            public void close(Status status, Metadata trailers) {
                long elapsed = System.currentTimeMillis() - startTime;
                log.info("gRPC 호출 완료: {} | status={} | {}ms",
                    method, status.getCode(), elapsed);
                super.close(status, trailers);
            }
        };

        return next.startCall(wrappedCall, headers);
    }
}
```

```java
// 메트릭 수집 Interceptor
public class MetricsInterceptor implements ServerInterceptor {

    private final MeterRegistry meterRegistry;

    @Override
    public <ReqT, RespT> ServerCall.Listener<ReqT> interceptCall(
            ServerCall<ReqT, RespT> call,
            Metadata headers,
            ServerCallHandler<ReqT, RespT> next) {

        String method = call.getMethodDescriptor().getFullMethodName();
        Timer.Sample sample = Timer.start(meterRegistry);

        ServerCall<ReqT, RespT> wrappedCall = new ForwardingServerCall
                .SimpleForwardingServerCall<>(call) {
            @Override
            public void close(Status status, Metadata trailers) {
                sample.stop(Timer.builder("grpc.server.calls")
                    .tag("method", method)
                    .tag("status", status.getCode().name())
                    .register(meterRegistry));
                meterRegistry.counter("grpc.server.calls.total",
                    "method", method,
                    "status", status.getCode().name()).increment();
                super.close(status, trailers);
            }
        };

        return next.startCall(wrappedCall, headers);
    }
}
```

### 클라이언트 Interceptor

```java
// 클라이언트에서 요청에 인증 헤더 자동 추가
public class AuthClientInterceptor implements ClientInterceptor {

    private final TokenProvider tokenProvider;

    @Override
    public <ReqT, RespT> ClientCall<ReqT, RespT> interceptCall(
            MethodDescriptor<ReqT, RespT> method,
            CallOptions callOptions,
            Channel next) {

        return new ForwardingClientCall
                .SimpleForwardingClientCall<>(next.newCall(method, callOptions)) {
            @Override
            public void start(Listener<RespT> responseListener, Metadata headers) {
                headers.put(
                    Metadata.Key.of("authorization", Metadata.ASCII_STRING_MARSHALLER),
                    "Bearer " + tokenProvider.getToken());
                super.start(responseListener, headers);
            }
        };
    }
}
```

### Interceptor 등록 순서

Interceptor는 등록 순서대로 실행된다. 인증 → 로깅 → 메트릭 순서가 일반적이다. 인증이 실패하면 뒤의 Interceptor는 실행되지 않는다.

```java
Server server = ServerBuilder.forPort(50051)
    .addService(new UserServiceImpl())
    .intercept(new MetricsInterceptor(meterRegistry))  // 3번째 실행
    .intercept(new LoggingInterceptor())                // 2번째 실행
    .intercept(new AuthInterceptor())                   // 1번째 실행 (마지막에 추가한 게 먼저 실행)
    .build();
```

주의 — `intercept()`를 여러 번 호출하면 **나중에 추가한 것이 먼저 실행**된다. 스택처럼 동작한다.

---

## Java/Spring Boot gRPC 구현

### 의존성 설정

`build.gradle`:

```groovy
plugins {
    id 'org.springframework.boot' version '3.2.0'
    id 'io.spring.dependency-management' version '1.1.4'
    id 'com.google.protobuf' version '0.9.4'
    id 'java'
}

dependencies {
    implementation 'net.devh:grpc-spring-boot-starter:3.0.0.RELEASE'
    implementation 'io.grpc:grpc-netty-shaded:1.60.0'
    implementation 'io.grpc:grpc-protobuf:1.60.0'
    implementation 'io.grpc:grpc-stub:1.60.0'
    compileOnly 'org.apache.tomcat:annotations-api:6.0.53'
}

protobuf {
    protoc {
        artifact = 'com.google.protobuf:protoc:3.25.1'
    }
    plugins {
        grpc {
            artifact = 'io.grpc:protoc-gen-grpc-java:1.60.0'
        }
    }
    generateProtoTasks {
        all()*.plugins {
            grpc {}
        }
    }
}
```

### Proto 파일 정의

`src/main/proto/user.proto`:

```protobuf
syntax = "proto3";

option java_multiple_files = true;
option java_package = "com.example.grpc.user";

package user;

service UserService {
  rpc GetUser (GetUserRequest) returns (GetUserResponse) {}
  rpc ListUsers (ListUsersRequest) returns (stream GetUserResponse) {}
  rpc CreateUser (CreateUserRequest) returns (GetUserResponse) {}
}

message GetUserRequest {
  string user_id = 1;
}

message ListUsersRequest {
  int32 page = 1;
  int32 size = 2;
}

message CreateUserRequest {
  string name = 1;
  string email = 2;
  UserRole role = 3;
}

message GetUserResponse {
  string user_id = 1;
  string name = 2;
  string email = 3;
  UserRole role = 4;
}

enum UserRole {
  USER_ROLE_UNSPECIFIED = 0;
  USER = 1;
  ADMIN = 2;
}
```

### 서버 구현

`grpc-spring-boot-starter`를 쓰면 `@GrpcService` 어노테이션 하나로 gRPC 서비스를 Spring Bean으로 등록한다.

```java
@GrpcService
public class UserGrpcService extends UserServiceGrpc.UserServiceImplBase {

    private final UserRepository userRepository;

    public UserGrpcService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @Override
    public void getUser(GetUserRequest request,
                        StreamObserver<GetUserResponse> responseObserver) {
        User user = userRepository.findById(request.getUserId())
            .orElse(null);

        if (user == null) {
            responseObserver.onError(Status.NOT_FOUND
                .withDescription("사용자를 찾을 수 없음: " + request.getUserId())
                .asRuntimeException());
            return;
        }

        GetUserResponse response = GetUserResponse.newBuilder()
            .setUserId(user.getId())
            .setName(user.getName())
            .setEmail(user.getEmail())
            .setRole(UserRole.valueOf(user.getRole()))
            .build();

        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void listUsers(ListUsersRequest request,
                          StreamObserver<GetUserResponse> responseObserver) {
        Page<User> users = userRepository.findAll(
            PageRequest.of(request.getPage(), request.getSize()));

        for (User user : users.getContent()) {
            GetUserResponse response = GetUserResponse.newBuilder()
                .setUserId(user.getId())
                .setName(user.getName())
                .setEmail(user.getEmail())
                .build();
            responseObserver.onNext(response);
        }
        responseObserver.onCompleted();
    }

    @Override
    public void createUser(CreateUserRequest request,
                           StreamObserver<GetUserResponse> responseObserver) {
        // 입력 검증
        if (request.getName().isBlank()) {
            responseObserver.onError(Status.INVALID_ARGUMENT
                .withDescription("name은 비어있을 수 없음")
                .asRuntimeException());
            return;
        }

        User user = new User();
        user.setName(request.getName());
        user.setEmail(request.getEmail());
        user.setRole(request.getRole().name());
        userRepository.save(user);

        GetUserResponse response = GetUserResponse.newBuilder()
            .setUserId(user.getId())
            .setName(user.getName())
            .setEmail(user.getEmail())
            .setRole(request.getRole())
            .build();

        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }
}
```

### 클라이언트 구현

```java
@Service
public class UserGrpcClient {

    private final UserServiceGrpc.UserServiceBlockingStub userStub;

    public UserGrpcClient(@GrpcClient("user-service") Channel channel) {
        this.userStub = UserServiceGrpc.newBlockingStub(channel);
    }

    public GetUserResponse getUser(String userId) {
        try {
            return userStub
                .withDeadlineAfter(3, TimeUnit.SECONDS)
                .getUser(GetUserRequest.newBuilder()
                    .setUserId(userId)
                    .build());
        } catch (StatusRuntimeException e) {
            switch (e.getStatus().getCode()) {
                case NOT_FOUND:
                    throw new UserNotFoundException(userId);
                case DEADLINE_EXCEEDED:
                    throw new ServiceTimeoutException("user-service", 3);
                case UNAVAILABLE:
                    throw new ServiceUnavailableException("user-service");
                default:
                    throw new GrpcCallException(e);
            }
        }
    }
}
```

### application.yml 설정

```yaml
grpc:
  server:
    port: 9090
  client:
    user-service:
      address: 'static://localhost:9090'
      negotiation-type: plaintext
      # 프로덕션에서는 TLS 사용
      # negotiation-type: tls
```

`grpc-spring-boot-starter`는 기본적으로 Spring Boot의 포트(8080)와 별도로 gRPC 포트를 연다. REST API와 gRPC를 같은 애플리케이션에서 동시에 서비스할 수 있다.

---

## 커넥션 관리와 Keepalive

gRPC는 HTTP/2 기반이라 하나의 TCP 커넥션 위에 여러 스트림을 멀티플렉싱한다. 커넥션 하나로 수백 개의 동시 요청을 처리할 수 있다는 뜻이지만, 커넥션 관리를 제대로 하지 않으면 문제가 생긴다.

### Keepalive가 필요한 이유

로드밸런서, 프록시, 방화벽은 유휴 커넥션을 끊어버린다. AWS의 NLB는 기본 350초, 일부 방화벽은 60초 만에 끊는 경우가 있다. gRPC 클라이언트는 커넥션이 끊겼다는 걸 모르고 해당 커넥션으로 요청을 보내다가 타임아웃이 발생한다.

keepalive ping을 주기적으로 보내면 중간 장비가 커넥션을 유휴 상태로 판단하지 않는다. 서버가 응답하지 않으면 커넥션이 죽었다는 걸 빠르게 감지할 수 있다.

### 클라이언트 Keepalive 설정

```java
ManagedChannel channel = ManagedChannelBuilder
    .forAddress("localhost", 50051)
    .keepAliveTime(30, TimeUnit.SECONDS)        // 30초마다 keepalive ping
    .keepAliveTimeout(5, TimeUnit.SECONDS)      // ping 응답 5초 대기
    .keepAliveWithoutCalls(true)                // 활성 RPC 없어도 ping 전송
    .idleTimeout(5, TimeUnit.MINUTES)           // 5분 유휴 시 커넥션 해제
    .usePlaintext()
    .build();
```

- `keepAliveTime` — ping 전송 간격. 너무 짧으면 서버 부하가 늘고, 너무 길면 끊긴 커넥션을 늦게 감지한다. 30~60초가 적절하다.
- `keepAliveTimeout` — ping 응답 대기 시간. 이 시간 안에 응답이 없으면 커넥션을 닫고 재연결한다.
- `keepAliveWithoutCalls` — false면 활성 RPC가 없을 때 ping을 보내지 않는다. true로 설정해야 유휴 커넥션이 끊기는 걸 방지한다.

### 서버 Keepalive 설정

```java
Server server = ServerBuilder.forPort(50051)
    .addService(new UserServiceImpl())
    .permitKeepAliveTime(10, TimeUnit.SECONDS)     // 클라이언트 ping 최소 간격
    .permitKeepAliveWithoutCalls(true)              // 활성 RPC 없이도 ping 허용
    .maxConnectionIdle(15, TimeUnit.MINUTES)        // 유휴 커넥션 최대 유지 시간
    .maxConnectionAge(30, TimeUnit.MINUTES)         // 커넥션 최대 수명
    .maxConnectionAgeGrace(5, TimeUnit.SECONDS)     // 종료 유예 시간
    .build();
```

- `permitKeepAliveTime` — 클라이언트가 이 간격보다 짧게 ping을 보내면 GOAWAY로 커넥션을 끊는다. 클라이언트의 `keepAliveTime`보다 같거나 작아야 한다.
- `maxConnectionAge` — 커넥션이 이 시간을 넘기면 서버가 GOAWAY를 보낸다. 롤링 배포 시 오래된 커넥션이 이전 서버에 붙어있는 문제를 방지한다.
- `maxConnectionAgeGrace` — GOAWAY를 보낸 후 진행 중인 RPC가 완료될 때까지 기다리는 시간.

### 커넥션 관리 주의사항

gRPC 채널(ManagedChannel)은 애플리케이션 시작 시 한 번 생성하고 재사용해야 한다. 호출마다 새 채널을 만들면 TCP 커넥션이 계속 열리고 닫히면서 성능이 급격히 떨어진다. 채널 내부에 커넥션 풀이 있으므로 직접 풀을 구현할 필요 없다.

```java
// 잘못된 사용 — 매 호출마다 채널 생성
public GetUserResponse getUser(String userId) {
    ManagedChannel channel = ManagedChannelBuilder.forAddress("localhost", 50051).build();
    try {
        return UserServiceGrpc.newBlockingStub(channel).getUser(request);
    } finally {
        channel.shutdown();  // 매번 커넥션 생성/종료 → 느림
    }
}

// 올바른 사용 — 채널 재사용
@Bean
public ManagedChannel userServiceChannel() {
    return ManagedChannelBuilder.forAddress("localhost", 50051)
        .keepAliveTime(30, TimeUnit.SECONDS)
        .keepAliveTimeout(5, TimeUnit.SECONDS)
        .usePlaintext()
        .build();
}
```

---

## 로드밸런싱

gRPC는 HTTP/2의 멀티플렉싱 때문에 로드밸런싱이 REST와 다르게 동작한다. HTTP/1.1에서는 요청마다 커넥션을 맺거나, 커넥션을 재사용하더라도 한 커넥션에 한 요청씩 처리한다. L4 로드밸런서가 커넥션 단위로 분배하면 자연스럽게 요청이 분산된다.

gRPC는 하나의 커넥션으로 모든 요청을 보낸다. L4 로드밸런서는 커넥션이 맺어질 때 한 번만 백엔드를 선택하므로, 모든 요청이 한 서버로 몰린다.

### 프록시 기반 로드밸런싱 (L7)

Envoy, nginx(gRPC 지원 버전), Istio 같은 L7 프록시를 사용한다. 프록시가 HTTP/2 프레임 단위로 요청을 파싱해서 개별 RPC 호출을 다른 백엔드로 분배한다.

```
Client → L7 Proxy (Envoy) → Backend A
                           → Backend B
                           → Backend C
```

클라이언트는 프록시 주소만 알면 된다. 백엔드 추가/제거를 프록시에서 처리하므로 클라이언트 변경이 없다. 다만 프록시가 병목이 될 수 있고, 추가 hop으로 지연이 생긴다.

### 클라이언트 사이드 로드밸런싱

클라이언트가 직접 여러 서버 주소를 알고, 요청마다 다른 서버를 선택한다. 프록시 없이 직접 통신하므로 지연이 적다.

gRPC는 `round_robin`, `pick_first` 같은 내장 정책을 제공한다.

```java
// 클라이언트 사이드 round-robin
ManagedChannel channel = ManagedChannelBuilder
    .forTarget("dns:///my-grpc-service.default.svc.cluster.local:50051")
    .defaultLoadBalancingPolicy("round_robin")
    .usePlaintext()
    .build();
```

`dns:///` 형식을 쓰면 DNS에서 A 레코드를 조회해서 여러 IP를 가져오고, round-robin으로 분배한다.

### Kubernetes 환경에서 주의할 점

K8s의 기본 Service는 ClusterIP 타입으로, kube-proxy가 L4 로드밸런싱을 한다. gRPC와 L4 조합은 위에서 설명한 대로 트래픽 쏠림이 발생한다.

해결 방법은 크게 세 가지다:

**1. Headless Service + 클라이언트 사이드 로드밸런싱**

```yaml
# K8s Headless Service
apiVersion: v1
kind: Service
metadata:
  name: user-service
spec:
  clusterIP: None    # Headless — DNS가 모든 Pod IP를 반환
  selector:
    app: user-service
  ports:
    - port: 50051
```

Headless Service는 DNS 조회 시 모든 Pod의 IP를 반환한다. 클라이언트가 round-robin으로 요청을 분배한다.

문제는 DNS 캐싱이다. Pod가 추가/삭제되어도 DNS 캐시 만료 전까지는 이전 목록을 사용한다. `maxConnectionAge`를 설정해서 주기적으로 커넥션을 갱신하면 새 Pod 목록을 반영할 수 있다.

**2. Istio/Envoy 사이드카**

서비스 메시를 사용하면 각 Pod 옆에 Envoy 프록시가 붙어서 L7 로드밸런싱을 자동으로 처리한다. 애플리케이션 코드 변경 없이 동작한다.

**3. gRPC용 L7 Ingress**

`grpc-web` 프로토콜이나 nginx ingress의 gRPC 백엔드 설정을 사용한다.

실무에서는 이미 Istio 같은 서비스 메시를 사용 중이면 사이드카 방식이 편하고, 그렇지 않으면 Headless Service + 클라이언트 사이드 로드밸런싱이 가장 단순하다.

---

## 디버깅 도구

gRPC는 바이너리 프로토콜이라 curl로 테스트할 수 없다. 전용 CLI 도구가 필요하다.

### grpcurl

REST에서 curl이 하는 역할을 gRPC에서 한다. 서버의 리플렉션 API를 통해 서비스 목록과 메서드를 조회하고, 요청을 보낼 수 있다.

```bash
# 설치 (macOS)
brew install grpcurl

# 서비스 목록 조회 (서버에 리플렉션 활성화 필요)
grpcurl -plaintext localhost:50051 list

# 서비스의 메서드 목록
grpcurl -plaintext localhost:50051 list user.UserService

# 메서드의 요청/응답 타입 확인
grpcurl -plaintext localhost:50051 describe user.UserService.GetUser

# Unary 호출
grpcurl -plaintext -d '{"user_id": "123"}' \
  localhost:50051 user.UserService/GetUser

# 메타데이터(헤더) 포함 호출
grpcurl -plaintext \
  -H 'authorization: Bearer eyJhbGci...' \
  -d '{"user_id": "123"}' \
  localhost:50051 user.UserService/GetUser
```

서버에서 리플렉션을 활성화해야 grpcurl이 서비스 목록을 조회할 수 있다.

```java
// Spring Boot에서 리플렉션 활성화
// grpc-spring-boot-starter 사용 시 application.yml에 추가
// grpc:
//   server:
//     reflection-service-enabled: true

// 또는 직접 서버 빌드 시
Server server = ServerBuilder.forPort(50051)
    .addService(new UserServiceImpl())
    .addService(ProtoReflectionService.newInstance())  // 리플렉션 서비스 추가
    .build();
```

프로덕션에서는 리플렉션을 끄는 게 좋다. 서비스 구조가 외부에 노출된다.

### Evans

인터랙티브 gRPC 클라이언트다. REPL 모드에서 탭 완성을 지원해서 proto 구조를 탐색하면서 요청을 보내기 편하다.

```bash
# 설치 (macOS)
brew install evans

# REPL 모드로 시작
evans -r repl -p 50051

# REPL 안에서
> show service
> show message
> service UserService
> call GetUser
# 필드를 하나씩 입력하라는 프롬프트가 나옴
user_id (TYPE_STRING) => 123
```

Evans는 proto 파일 없이 리플렉션만으로 동작한다. 개발 중에 서버가 정상 동작하는지 빠르게 확인할 때 유용하다.

### proto 파일 기반 호출 (리플렉션 없이)

리플렉션이 꺼진 서버에는 proto 파일을 직접 지정해야 한다.

```bash
# grpcurl — proto 파일 지정
grpcurl -plaintext \
  -proto src/main/proto/user.proto \
  -d '{"user_id": "123"}' \
  localhost:50051 user.UserService/GetUser

# evans — proto 파일 지정
evans --proto src/main/proto/user.proto -p 50051 repl
```

---

## 보안 및 인증

### TLS/SSL 설정

```java
// 서버 TLS
Server server = ServerBuilder.forPort(50051)
    .useTransportSecurity(
        new File("server.crt"),
        new File("server.key"))
    .addService(new UserServiceImpl())
    .build();

// 클라이언트 TLS
ManagedChannel channel = ManagedChannelBuilder
    .forAddress("localhost", 50051)
    .sslContext(GrpcSslContexts.forClient()
        .trustManager(new File("ca.crt"))
        .build())
    .build();
```

### 인증 토큰 처리

인증은 Interceptor 섹션에서 설명한 패턴을 사용한다. 메타데이터에 `authorization` 헤더를 넣고, 서버 Interceptor에서 검증하는 방식이다.

---

## 요약

gRPC는 마이크로서비스 간 내부 통신에 적합하다. HTTP/2 멀티플렉싱으로 하나의 커넥션에 여러 요청을 처리하고, Protocol Buffers로 데이터 크기를 줄인다.

실무에서 신경 써야 할 것들:

- **deadline은 반드시 설정한다** — 안 하면 cascading failure 위험
- **proto 필드 번호는 삭제/재사용하지 않는다** — `reserved` 사용
- **L4 로드밸런서로는 트래픽이 분산되지 않는다** — L7 프록시 또는 클라이언트 사이드 로드밸런싱 필요
- **keepalive를 설정한다** — 중간 장비가 유휴 커넥션을 끊는다
- **ManagedChannel은 재사용한다** — 호출마다 생성하면 성능 저하

### gRPC를 쓰기 적합한 경우

- 마이크로서비스 간 내부 통신
- 실시간 데이터 스트리밍
- 양방향 통신이 필요한 시스템
- 여러 언어로 작성된 서비스 간 연동

### gRPC가 맞지 않는 경우

- 브라우저에서 직접 호출해야 하는 API (gRPC-Web으로 우회 가능하지만 복잡도 증가)
- 단순한 CRUD API — REST가 더 단순하고 도구 생태계가 넓다
- 디버깅 편의성이 중요한 초기 프로토타이핑
