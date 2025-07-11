# RPC (Remote Procedure Call)

## 📋 개요

RPC는 **Remote Procedure Call**의 약자로, **원격 프로시저 호출**을 의미합니다. 

간단히 말해서, 다른 컴퓨터에 있는 함수를 마치 내 컴퓨터에 있는 함수처럼 호출할 수 있게 해주는 기술입니다.

### 🎯 핵심 개념
- **로컬 함수 호출**: 같은 컴퓨터 내에서 함수를 호출하는 것
- **원격 함수 호출**: 다른 컴퓨터에 있는 함수를 네트워크를 통해 호출하는 것
- **투명성**: 원격 호출이지만 로컬 호출처럼 사용할 수 있는 것

---

## 🔍 RPC란 무엇인가?

### 기본 개념
RPC는 분산 시스템에서 프로그램 간 통신을 위한 프로토콜입니다. 이를 통해 클라이언트 애플리케이션은 서버에 있는 함수를 원격으로 호출할 수 있습니다.

### 🤔 왜 RPC가 필요한가?

**전통적인 방식 (RPC 없이)**
```javascript
// 클라이언트에서 직접 HTTP 요청을 보내야 함
fetch('http://server.com/api/calculate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ a: 5, b: 3 })
})
.then(response => response.json())
.then(result => console.log(result));
```

**RPC 방식**
```javascript
// 마치 로컬 함수를 호출하는 것처럼 사용
const result = await remoteCalculator.add(5, 3);
console.log(result); // 8
```

---

## ⚙️ RPC의 작동 원리

### 1️⃣ 클라이언트 호출 단계
클라이언트가 원격 함수를 호출합니다.

```javascript
// 클라이언트 코드
const userService = new RPCClient('user-service');
const user = await userService.getUserById(123);
```

### 2️⃣ 매개변수 직렬화 (Serialization)
함수 호출 정보를 네트워크로 전송할 수 있는 형태로 변환합니다.

```javascript
// 내부적으로 이런 과정이 일어남
const callData = {
  method: 'getUserById',
  params: [123],
  id: 'call-001'
};
const serializedData = JSON.stringify(callData);
```

### 3️⃣ 네트워크 전송
직렬화된 데이터를 서버로 전송합니다.

### 4️⃣ 서버에서 실행
서버가 받은 호출을 처리하고 함수를 실행합니다.

```javascript
// 서버 코드
class UserService {
  async getUserById(id) {
    // 데이터베이스에서 사용자 조회
    return await database.findUser(id);
  }
}
```

### 5️⃣ 결과 반환
실행 결과를 클라이언트로 되돌려줍니다.

---

## 🏗️ RPC의 구성 요소

### 📝 인터페이스 정의 (Interface Definition)
RPC 서비스가 제공하는 함수들의 명세를 정의합니다.

```javascript
// 인터페이스 정의 예시
interface UserService {
  getUserById(id: number): Promise<User>;
  createUser(userData: UserData): Promise<User>;
  updateUser(id: number, userData: Partial<User>): Promise<User>;
  deleteUser(id: number): Promise<boolean>;
}
```

### 🔧 클라이언트 스텁 (Client Stub)
클라이언트가 원격 함수를 로컬 함수처럼 호출할 수 있게 해주는 인터페이스입니다.

```javascript
// 클라이언트 스텁 예시
class UserServiceClient {
  constructor(serverUrl) {
    this.serverUrl = serverUrl;
  }

  async getUserById(id) {
    // 내부적으로 네트워크 요청을 처리
    const response = await fetch(`${this.serverUrl}/rpc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        method: 'getUserById',
        params: [id]
      })
    });
    
    return await response.json();
  }
}
```

### 🖥️ 서버 스텁 (Server Stub)
서버에서 클라이언트의 호출을 받아 실제 함수를 실행하는 인터페이스입니다.

```javascript
// 서버 스텁 예시
class UserServiceServer {
  constructor() {
    this.userService = new UserService();
  }

  async handleRPC(request) {
    const { method, params } = request;
    
    switch (method) {
      case 'getUserById':
        return await this.userService.getUserById(params[0]);
      case 'createUser':
        return await this.userService.createUser(params[0]);
      // ... 다른 메서드들
    }
  }
}
```

### 🔄 직렬화/역직렬화 (Serialization/Deserialization)
데이터를 네트워크로 전송 가능한 형태로 변환하는 과정입니다.

```javascript
// 직렬화 예시
function serialize(data) {
  return JSON.stringify(data);
}

// 역직렬화 예시
function deserialize(data) {
  return JSON.parse(data);
}
```

---

## ✅ RPC의 장점

### 🔄 모듈성과 재사용성
- 함수 단위로 기능을 분리하여 개발
- 다른 애플리케이션에서 쉽게 재사용 가능

### 👁️ 투명성
- 원격 호출이지만 로컬 호출처럼 사용
- 복잡한 네트워크 통신을 숨겨줌

### 🌐 분산 시스템 관리
- 여러 서버에 분산된 서비스를 통합 관리
- 마이크로서비스 아키텍처에 적합

### 🔧 다양한 언어/플랫폼 지원
- JavaScript, Python, Java 등 다양한 언어 지원
- 서로 다른 언어로 작성된 서비스 간 통신 가능

---

## 🎯 실제 사용 사례

### 🏢 마이크로서비스 아키텍처
여러 개의 작은 서비스로 나누어진 시스템에서 서비스 간 통신에 사용됩니다.

```javascript
// 사용자 서비스
const userService = new RPCClient('user-service:3001');

// 주문 서비스
const orderService = new RPCClient('order-service:3002');

// 주문 생성 시 사용자 정보 조회
async function createOrder(userId, orderData) {
  const user = await userService.getUserById(userId);
  const order = await orderService.createOrder({
    userId,
    userInfo: user,
    ...orderData
  });
  return order;
}
```

### 💾 원격 데이터 접근
분산 데이터베이스나 원격 서비스에 접근할 때 사용됩니다.

```javascript
// 원격 데이터베이스 서비스
const dbService = new RPCClient('database-service:3003');

async function getUserData(userId) {
  const user = await dbService.query('SELECT * FROM users WHERE id = ?', [userId]);
  const orders = await dbService.query('SELECT * FROM orders WHERE user_id = ?', [userId]);
  
  return { user, orders };
}
```

---

## 🔧 JavaScript에서 RPC 구현 예시

### 간단한 RPC 클라이언트 구현

```javascript
class SimpleRPCClient {
  constructor(serverUrl) {
    this.serverUrl = serverUrl;
    this.callId = 0;
  }

  async call(method, ...params) {
    const callId = ++this.callId;
    
    const request = {
      id: callId,
      method: method,
      params: params
    };

    try {
      const response = await fetch(this.serverUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });

      const result = await response.json();
      
      if (result.error) {
        throw new Error(result.error);
      }
      
      return result.result;
    } catch (error) {
      throw new Error(`RPC 호출 실패: ${error.message}`);
    }
  }
}

// 사용 예시
const client = new SimpleRPCClient('http://localhost:3000/rpc');

// 원격 함수 호출
const user = await client.call('getUserById', 123);
const result = await client.call('calculate', 10, 20, '+');
```

### 간단한 RPC 서버 구현

```javascript
class SimpleRPCServer {
  constructor() {
    this.methods = new Map();
  }

  // 메서드 등록
  register(methodName, handler) {
    this.methods.set(methodName, handler);
  }

  // RPC 요청 처리
  async handleRequest(request) {
    const { id, method, params } = request;
    
    if (!this.methods.has(method)) {
      return {
        id,
        error: `메서드 '${method}'를 찾을 수 없습니다.`
      };
    }

    try {
      const handler = this.methods.get(method);
      const result = await handler(...params);
      
      return {
        id,
        result: result
      };
    } catch (error) {
      return {
        id,
        error: error.message
      };
    }
  }
}

// 서버 설정 예시
const server = new SimpleRPCServer();

// 메서드 등록
server.register('add', (a, b) => a + b);
server.register('getUserById', async (id) => {
  // 데이터베이스에서 사용자 조회 로직
  return { id, name: '홍길동', email: 'hong@example.com' };
});

// Express.js와 함께 사용
app.post('/rpc', async (req, res) => {
  const response = await server.handleRequest(req.body);
  res.json(response);
});
```

---

## 📚 관련 기술들

### gRPC
Google에서 개발한 고성능 RPC 프레임워크
- Protocol Buffers를 사용한 효율적인 직렬화
- HTTP/2 기반의 양방향 스트리밍 지원

### JSON-RPC
JSON을 사용하는 경량 RPC 프로토콜
- 간단하고 가독성이 좋음
- 웹 브라우저에서도 사용 가능

### GraphQL
Facebook에서 개발한 쿼리 언어 및 런타임
- RPC와 유사하지만 더 유연한 데이터 요청 가능
- 단일 엔드포인트로 다양한 데이터 조회

---

## 💡 결론

RPC는 분산 시스템에서 프로그램 간 통신을 위한 강력한 기술입니다. 복잡한 네트워크 통신을 추상화하여 개발자가 원격 함수를 로컬 함수처럼 쉽게 호출할 수 있게 해줍니다.

### 핵심 포인트
- **투명성**: 원격 호출을 로컬 호출처럼 사용
- **모듈성**: 함수 단위로 서비스를 분리
- **재사용성**: 다양한 애플리케이션에서 공통 기능 재사용
- **확장성**: 마이크로서비스 아키텍처에 적합

RPC를 이해하고 활용하면 분산 시스템을 더 효율적으로 구축하고 관리할 수 있습니다.


