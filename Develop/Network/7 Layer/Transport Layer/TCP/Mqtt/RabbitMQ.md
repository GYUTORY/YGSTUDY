

# RabbitMQ (Message Broker)

## 1️⃣ RabbitMQ란?
**RabbitMQ**는 **메시지 브로커(Message Broker) 서비스**로,  
서로 다른 애플리케이션 간 **비동기 메시지 전달을 관리하는 역할**을 합니다.

> **👉🏻 RabbitMQ는 메시지를 안전하고 신뢰성 있게 전달하기 위해 큐(Queue) 기반의 시스템을 사용합니다.**

---

## 2️⃣ RabbitMQ의 주요 특징

### ✅ 1. **메시지 큐(Message Queue) 기반**
- 메시지를 큐에 저장하고, 필요할 때 **소비자(Consumer)** 가 가져감
- **생산자(Producer)** 와 **소비자(Consumer)** 가 직접 연결되지 않아도 됨

### ✅ 2. **비동기 메시지 처리 지원**
- 요청을 즉시 처리하지 않고, **큐에 저장했다가 나중에 처리 가능**
- **트래픽이 많아도 안정적인 메시지 처리 가능**

### ✅ 3. **여러 가지 메시징 패턴 지원**
- **단순 큐(Queue)**
- **게시/구독 (Pub/Sub)**
- **라우팅 (Routing)**
- **토픽 (Topic) 기반 메시징** 등 다양한 패턴 지원

### ✅ 4. **확장성 및 성능 최적화**
- 여러 개의 **Consumer를 통해 병렬 처리 가능**
- **클러스터링 및 고가용성(HA) 구성 가능**

### ✅ 5. **보안 및 인증 지원**
- TLS/SSL을 통한 **보안 메시지 전송 가능**
- **사용자 인증 및 권한 관리 기능 제공**

---

## 3️⃣ RabbitMQ 아키텍처

### ✨ RabbitMQ의 주요 구성 요소

| 구성 요소 | 설명 |
|----------|------|
| **Producer (생산자)** | 메시지를 생성하고 큐(Queue)에 보냄 |
| **Exchange (교환기)** | 메시지를 올바른 큐로 라우팅 |
| **Queue (큐)** | 메시지가 저장되는 공간 |
| **Consumer (소비자)** | 큐에서 메시지를 가져와 처리 |

> **👉🏻 Producer → Exchange → Queue → Consumer 순으로 메시지가 전달됩니다.**

---

## 4️⃣ RabbitMQ 설치 및 실행

### ✅ 1. RabbitMQ 설치 (Docker 사용)
```bash
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:management
```

### ✅ 2. RabbitMQ 관리 콘솔 접속
- 웹 브라우저에서 `http://localhost:15672` 접속
- 기본 로그인 정보:
    - **ID**: `guest`
    - **PW**: `guest`

> **👉🏻 RabbitMQ 웹 관리 콘솔을 통해 메시지 큐 상태를 확인할 수 있습니다.**

---

## 5️⃣ Node.js에서 RabbitMQ 사용하기

### ✅ 1. `amqplib` 라이브러리 설치
```bash
npm install amqplib
```

### ✅ 2. 메시지 발행 (Producer)

```javascript
const amqp = require('amqplib');

async function sendMessage() {
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();

    const queue = 'hello';
    const message = 'Hello, RabbitMQ!';

    await channel.assertQueue(queue, { durable: false });
    channel.sendToQueue(queue, Buffer.from(message));

    console.log(`메시지 전송: ${message}`);
    
    setTimeout(() => {
        connection.close();
    }, 500);
}

sendMessage();
```

> **👉🏻 위 코드는 "hello" 큐에 "Hello, RabbitMQ!" 메시지를 전송하는 예제입니다.**

---

### ✅ 3. 메시지 소비 (Consumer)

```javascript
const amqp = require('amqplib');

async function receiveMessage() {
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();

    const queue = 'hello';

    await channel.assertQueue(queue, { durable: false });

    console.log(`[*] 큐에서 메시지를 기다리는 중...`);
    channel.consume(queue, (msg) => {
        console.log(`[x] 받은 메시지: ${msg.content.toString()}`);
    }, { noAck: true });
}

receiveMessage();
```

> **👉🏻 위 코드는 "hello" 큐에서 메시지를 받아서 출력하는 예제입니다.**

---

## 6️⃣ RabbitMQ 메시징 패턴

### ✅ 1. 기본 큐(Queue)
- **Producer → Queue → Consumer** 구조
- 메시지를 **한 개의 Consumer가 가져감**

### ✅ 2. 게시/구독 (Fanout Exchange)
- **여러 개의 Consumer가 같은 메시지를 받을 수 있음**

```javascript
await channel.assertExchange('logs', 'fanout', { durable: false });
await channel.publish('logs', '', Buffer.from(message));
```

### ✅ 3. 라우팅 (Direct Exchange)
- 특정 키를 가진 Consumer만 메시지를 수신
```javascript
await channel.assertExchange('direct_logs', 'direct', { durable: false });
await channel.publish('direct_logs', 'error', Buffer.from("에러 메시지"));
```

> **👉🏻 다양한 패턴을 활용하여 메시지를 효율적으로 라우팅할 수 있습니다.**

---

## 7️⃣ RabbitMQ vs MQTT 비교

| 비교 항목 | RabbitMQ | MQTT |
|-----------|---------|------|
| **주요 용도** | 일반적인 메시지 브로커 | IoT 및 실시간 메시징 |
| **프로토콜** | AMQP (Advanced Message Queuing Protocol) | MQTT |
| **메시징 패턴** | 큐(Queue), Pub/Sub, Direct Exchange 등 | Pub/Sub |
| **QoS 지원** | 기본적으로 제공 | QoS 0, 1, 2 지원 |
| **지속 연결** | 필요 없음 | **연결 유지 필요** |
| **사용 사례** | 마이크로서비스, 이벤트 드리븐 아키텍처 | IoT, 실시간 데이터 전송 |

> **👉🏻 RabbitMQ는 범용적인 메시지 브로커이고, MQTT는 IoT에 최적화된 프로토콜입니다.**

---

## 8️⃣ RabbitMQ의 활용 사례

✅ **마이크로서비스 간 메시지 전달**
- 서로 다른 서비스 간 메시지를 비동기적으로 전달

✅ **이메일 및 알림 시스템**
- 이메일, SMS, 푸시 알림 등의 **비동기 작업 처리**

✅ **이벤트 드리븐 아키텍처**
- 여러 서비스가 특정 이벤트를 구독하고 비즈니스 로직을 실행

✅ **IoT 데이터 처리**
- 센서 데이터 수집 및 분석

