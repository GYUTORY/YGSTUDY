---
title: Apache Thrift
tags: [network, tcp, backend, api, java]
updated: 2026-09-07
---

# Apache Thrift

Facebook이 2007년 내부 서비스 연동을 위해 만들어 오픈소스로 공개한 RPC 프레임워크다. 핵심 아이디어는 하나다. 인터페이스 정의 파일(`.thrift`)을 작성하면, 지원하는 언어별로 클라이언트와 서버 코드를 자동 생성해준다.

Facebook 초기 아키텍처가 C++, PHP, Python, Java로 구성되어 있었다. 각 언어 사이에서 데이터를 주고받는 직렬화 방식이 제각각이었고, 이를 통일하기 위해 Thrift가 나왔다. 2008년 Apache 재단에 기증됐고, 지금도 일부 대형 서비스의 내부 RPC 레이어로 쓰인다.

## IDL 정의

Thrift IDL은 Proto3와 비슷해 보이지만 타입 시스템이 더 풍부하다.

```thrift
namespace java com.example.user
namespace go user
namespace py user

const i32 MAX_RESULTS = 100

exception UserNotFoundException {
  1: i32 code,
  2: string message
}

exception ValidationException {
  1: string field,
  2: string reason
}

enum UserStatus {
  ACTIVE = 1,
  INACTIVE = 2,
  SUSPENDED = 3
}

struct User {
  1: required string id,
  2: required string name,
  3: optional string email,
  4: UserStatus status = UserStatus.ACTIVE,
  5: map<string, string> metadata = {}
}

service UserService {
  User getUser(1: string userId) throws (1: UserNotFoundException notFound),
  list<User> listUsers(1: i32 limit = 20, 2: i32 offset = 0),
  void createUser(1: User user) throws (1: ValidationException validationError),
  oneway void deleteUser(1: string userId)
}
```

Proto3와 다른 점이 몇 가지 있다. `required`/`optional` 한정자를 명시적으로 쓴다. 기본값을 필드 수준에서 설정할 수 있다. 서비스 메서드에 예외 타입을 직접 선언한다는 것도 Thrift만의 특징이다. `oneway`는 응답을 기다리지 않는 fire-and-forget 호출이다.

## 타입 시스템

기본 타입:

| 타입 | 설명 | Java 매핑 |
|------|------|-----------|
| `bool` | 불리언 | boolean |
| `byte` | 8비트 정수 | byte |
| `i16` | 16비트 정수 | short |
| `i32` | 32비트 정수 | int |
| `i64` | 64비트 정수 | long |
| `double` | 64비트 부동소수점 | double |
| `string` | UTF-8 문자열 | String |
| `binary` | 바이트 시퀀스 | ByteBuffer |

컨테이너 타입: `list<T>`는 순서 있는 컬렉션(중복 허용), `set<T>`는 순서 없는 컬렉션(중복 불허), `map<K, V>`는 키-값 쌍이다.

`required` 필드는 직렬화 시 반드시 값이 있어야 하고, 없으면 예외가 발생한다. `optional` 필드는 값이 없으면 와이어에 포함되지 않는다.

문제는 `required`로 정의된 필드를 나중에 삭제하거나 `optional`로 바꾸려면 클라이언트와 서버를 동시에 배포해야 한다는 점이다. 그렇지 않으면 구버전이 해당 필드 없는 메시지를 받았을 때 예외를 던진다. Facebook 내부에서도 나중에는 `optional`을 쓰고 애플리케이션 레벨에서 필드 존재 여부를 체크하는 패턴으로 전환했다.

## 전송 레이어와 프로토콜 레이어

Thrift의 아키텍처는 전송 레이어와 프로토콜 레이어가 분리되어 있다. 둘을 독립적으로 선택해서 조합한다.

### 전송 레이어

**TSocket** — 기본 TCP 소켓. 개발 환경 테스트에 쓴다.

**TFramedTransport** — 메시지 앞에 4바이트 길이 헤더를 붙여서 프레임 단위로 처리한다. 비동기 서버(`TNonblockingServer`, `THsHaServer`)를 쓰려면 반드시 필요하다. 비동기 서버에서 TFramedTransport를 빠뜨리면 연결 자체가 안 되는데 오류 메시지가 불친절해서 찾기 어렵다.

**TBufferedTransport** — 쓰기를 버퍼에 모아뒀다가 한 번에 보낸다. 시스템 콜 횟수를 줄인다.

**TMemoryBuffer** — 메모리에만 쓰는 전송 레이어. 직렬화 결과를 바이트로 뽑거나 테스트할 때 유용하다.

### 프로토콜 레이어

**TBinaryProtocol** — 기본 바이너리 직렬화. 단순하고 빠르다.

**TCompactProtocol** — 가변 길이 인코딩을 써서 TBinaryProtocol보다 메시지 크기가 30~40% 작다. 성능이 중요한 환경에서는 이걸 쓴다.

**TJSONProtocol** — JSON으로 직렬화한다. 디버깅할 때 메시지를 눈으로 읽을 수 있지만 크기와 속도 면에서 바이너리보다 불리하다. 프로덕션에서는 쓰지 않는다.

조합 예:

| 전송 | 프로토콜 | 용도 |
|------|----------|------|
| TFramedTransport | TCompactProtocol | 프로덕션 내부 RPC |
| TFramedTransport | TBinaryProtocol | 구버전 호환이 필요한 경우 |
| TMemoryBuffer | TBinaryProtocol | 테스트 / 직렬화 결과 검사 |
| TSocket | TJSONProtocol | 개발 중 디버깅 |

주의할 점은 같은 IDL이라도 프로토콜이 다르면 와이어 포맷이 달라서 상호 통신이 안 된다. 클라이언트와 서버가 같은 전송+프로토콜 조합을 써야 하는데, 이게 설정으로 관리되다 보니 조합이 맞지 않아 연결이 안 되는 상황이 생긴다. 이미 TBinaryProtocol로 운영 중인 서비스에 TCompactProtocol을 붙이면 클라이언트 쪽도 동시에 변경해야 한다.

## 코드 생성 흐름

`.thrift` 파일을 작성하면 `thrift` 컴파일러로 타겟 언어 코드를 생성한다.

```bash
# 설치 (macOS)
brew install thrift

# Java 코드 생성
thrift --gen java -out src/main/java user.thrift

# 여러 언어 동시 생성
thrift --gen java -out java/src user.thrift
thrift --gen go  -out go/src  user.thrift
thrift --gen py  -out py/src  user.thrift
```

생성된 Java 코드 구조:

```
com/example/user/
  UserService.java            — 클라이언트 스텁과 서버 인터페이스
  UserService.Iface           — 서버 구현 인터페이스
  UserService.Client          — 클라이언트
  UserService.Processor       — 서버 요청 처리기
  User.java                   — User 구조체
  UserStatus.java             — enum
  UserNotFoundException.java  — 예외 타입
  ValidationException.java    — 예외 타입
```

서버 구현은 `UserService.Iface`를 구현하면 된다:

```java
public class UserServiceImpl implements UserService.Iface {

    @Override
    public User getUser(String userId) throws UserNotFoundException, TException {
        User user = userRepository.findById(userId);
        if (user == null) {
            throw new UserNotFoundException(404, "사용자를 찾을 수 없음: " + userId);
        }
        return user;
    }

    @Override
    public List<User> listUsers(int limit, int offset) throws TException {
        return userRepository.findAll(limit, offset);
    }

    @Override
    public void createUser(User user) throws ValidationException, TException {
        if (user.getName() == null || user.getName().isBlank()) {
            throw new ValidationException("name", "비어있을 수 없음");
        }
        userRepository.save(user);
    }

    @Override
    public void deleteUser(String userId) throws TException {
        userRepository.delete(userId);
        // oneway — 응답 없음
    }
}
```

서버 시작:

```java
UserServiceImpl handler = new UserServiceImpl();
UserService.Processor<UserServiceImpl> processor = new UserService.Processor<>(handler);

// 비동기 서버 — 높은 동시성 처리
TNonblockingServerTransport serverTransport = new TNonblockingServerSocket(9090);
TServer server = new THsHaServer(
    new THsHaServer.Args(serverTransport)
        .processor(processor)
        .transportFactory(new TFramedTransport.Factory())
        .protocolFactory(new TCompactProtocol.Factory())
);
server.serve();
```

클라이언트:

```java
TTransport transport = new TFramedTransport(new TSocket("localhost", 9090));
transport.open();

TProtocol protocol = new TCompactProtocol(transport);
UserService.Client client = new UserService.Client(protocol);

try {
    User user = client.getUser("user-123");
} catch (UserNotFoundException e) {
    log.warn("사용자 없음: code={}, message={}", e.getCode(), e.getMessage());
} catch (TException e) {
    log.error("Thrift 전송 오류", e);
} finally {
    transport.close();
}
```

## gRPC와의 실제 차이

스펙 비교보다 실제 운영에서 어디서 다르게 느껴지는지가 더 중요하다.

**스트리밍**

gRPC는 HTTP/2 기반이라 서버 스트리밍, 클라이언트 스트리밍, 양방향 스트리밍을 네이티브로 지원한다. Thrift는 기본적으로 요청-응답 구조다. 스트리밍이 필요하면 `list<T>`를 반환하거나 애플리케이션 레벨에서 직접 구현해야 한다. 실시간 스트리밍이 필요한 서비스에는 gRPC가 맞다.

**예외 처리**

Thrift IDL에서 서비스 메서드에 예외 타입을 선언한다. 선언된 예외는 IDL에서 정의한 구조체로 전달되고, 클라이언트에서 타입 있는 예외로 잡을 수 있다. gRPC는 상태 코드와 메시지 문자열로 오류를 전달하고, 구조화된 오류 본문을 전달하려면 `google.rpc.Status`의 `details` 필드를 따로 처리해야 한다. 예외 구조가 명확해야 하는 서비스 간 계약에서는 Thrift가 더 직관적이다.

**생태계**

gRPC는 Envoy, Istio, Kubernetes 생태계와 통합이 자연스럽다. grpcurl, Evans 같은 CLI 도구도 있고, Prometheus 메트릭 수집도 된다. Thrift는 그쪽이 취약하다. Thrift 서버를 L7 로드밸런서로 분산하려면 커스텀 구성이 필요하다.

**전송/프로토콜 유연성**

Thrift의 레이어 분리 구조는 장점이기도 단점이기도 하다. TTransport 인터페이스를 구현하면 커스텀 전송 레이어를 붙일 수 있다. gRPC는 HTTP/2가 고정이라 이런 커스터마이징이 어렵다. 다만 클라이언트와 서버가 조합을 맞춰야 하므로 설정 관리가 추가된다.

**브라우저 지원**

gRPC는 gRPC-Web 없이는 브라우저에서 직접 호출이 안 된다. Thrift는 TJSONProtocol을 HTTP 위에서 쓰면 브라우저에서도 호출할 수 있지만, 실무에서 이렇게 쓰는 경우는 드물다.

## 아직 Thrift를 쓰는 이유

gRPC가 나온 이후로 신규 서비스에서 Thrift를 선택하는 경우는 거의 없다. 살아남아 있는 이유는 대부분 레거시다.

2010년대 초중반에 대규모 마이크로서비스를 구축한 회사들이 Thrift로 내부 RPC를 구성했다. 수백 개 서비스의 IDL과 생성 코드, 그 위의 비즈니스 로직을 gRPC로 한 번에 마이그레이션하는 건 현실적으로 어렵다. 마이그레이션 비용이 얻을 수 있는 이익보다 크면 그냥 유지한다.

또 다른 이유는 언어 지원이다. Thrift는 gRPC보다 지원 언어 목록이 길다. C, Haskell, Erlang, OCaml, Delphi 같은 언어에서 Thrift를 써야 하는 상황이 있다. gRPC의 공식 지원이 닿지 않는 영역이다.

## 운영 시 주의사항

**IDL 변경 시 필드 번호를 재사용하지 않는다.** 삭제된 필드 번호에 새 필드를 정의하면 구버전 클라이언트가 그 필드를 구버전 타입으로 파싱하려 한다.

```thrift
// 잘못된 예
struct User {
  1: required string id,
  // 2: string oldEmail  — 삭제됨
  2: string phone        // 구버전은 이걸 oldEmail로 읽으려 한다
}

// 올바른 예
struct User {
  1: required string id,
  3: string phone        // 새 번호 사용
}
```

Thrift는 Proto3의 `reserved`에 해당하는 문법이 없다. 팀 내 관례로 삭제된 번호를 주석으로 표시해두는 수밖에 없다.

**`required` 필드는 가능하면 쓰지 않는다.** 처음부터 `optional`로 쓰고 애플리케이션 레벨에서 null 체크를 하는 게 낫다. 나중에 필드를 제거하거나 `optional`로 바꿀 때 양쪽을 동시에 배포해야 하는 제약을 피할 수 있다.

**Thrift 클라이언트는 스레드 안전하지 않다.** 하나의 클라이언트 인스턴스를 여러 스레드에서 동시에 쓰면 데이터가 섞인다. 스레드마다 별도 클라이언트를 만들거나 커넥션 풀을 써야 한다.

```java
// ThreadLocal로 클라이언트 관리
private static final ThreadLocal<UserService.Client> CLIENT = ThreadLocal.withInitial(() -> {
    try {
        TTransport transport = new TFramedTransport(new TSocket("localhost", 9090));
        transport.open();
        return new UserService.Client(new TCompactProtocol(transport));
    } catch (TException e) {
        throw new RuntimeException("Thrift 클라이언트 생성 실패", e);
    }
});
```

커넥션 풀은 Apache Commons Pool2와 조합해서 쓰는 경우가 많다. Pool에서 꺼낸 클라이언트가 커넥션이 끊긴 상태일 수 있으므로, 호출 실패 시 해당 클라이언트를 풀에서 폐기하고 새로 만드는 로직이 필요하다.
