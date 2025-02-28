

# AMQP (Advanced Message Queuing Protocol)

## 1️⃣ AMQP란?
**AMQP (Advanced Message Queuing Protocol)**는 **메시지 브로커를 위한 개방형 표준 프로토콜**입니다.  
메시지의 **신뢰성(Reliability), 상호운용성(Interoperability), 확장성(Scalability)을 보장**하며,  
RabbitMQ 같은 메시지 브로커에서 많이 사용됩니다.

> **👉🏻 AMQP는 메시지를 안정적으로 송수신하기 위한 프로토콜입니다.**

---

## 2️⃣ AMQP의 주요 특징

### ✅ 1. **메시지 지향 프로토콜**
- **메시지 큐(Message Queue)** 기반의 비동기 통신을 지원

### ✅ 2. **신뢰성 보장 (Reliability)**
- 메시지 손실을 방지하기 위해 **확인(Acknowledgment), 재전송(Retry), 영속성(Persistence)** 기능 지원

### ✅ 3. **발행/구독 (Publish/Subscribe) 모델 지원**
- 여러 개의 소비자(Consumer)가 하나의 메시지를 구독할 수 있음

### ✅ 4. **라우팅 기능 제공**
- Exchange를 활용한 **다양한 메시지 라우팅 방식** 지원

### ✅ 5. **다양한 메시지 브로커에서 지원**
- RabbitMQ, Apache Qpid, ActiveMQ 등에서 AMQP를 지원

---

## 3️⃣ AMQP 메시징 구조

### ✨ AMQP의 주요 구성 요소

| 구성 요소 | 설명 |
|----------|------|
| **Producer (생산자)** | 메시지를 생성하여 Exchange로 보냄 |
| **Exchange (교환기)** | 메시지를 적절한 Queue로 라우팅 |
| **Queue (큐)** | 메시지가 저장되는 공간 |
| **Consumer (소비자)** | 큐에서 메시지를 가져와 처리 |

```plaintext
[Producer] → (Exchange) → [Queue] → [Consumer]
```

> **👉🏻 Exchange가 메시지를 적절한 Queue로 분배하는 역할을 합니다.**

---

## 4️⃣ AMQP 메시징 패턴

### ✅ 1. 단순 큐 (Queue)
- 기본적인 메시지 큐
- 한 개의 Consumer가 한 개의 메시지를 소비

```plaintext
[Producer] → [Queue] → [Consumer]
```

---

### ✅ 2. 게시/구독 (Fanout Exchange)
- 여러 Consumer가 동일한 메시지를 받을 수 있음

```plaintext
[Producer] → (Fanout Exchange) → [Queue1] → [Consumer1]
                                    [Queue2] → [Consumer2]
```

```javascript
await channel.assertExchange('logs', 'fanout', { durable: false });
await channel.publish('logs', '', Buffer.from(message));
```

---

### ✅ 3. 라우팅 (Direct Exchange)
- 특정 라우팅 키(Routing Key)에 따라 메시지가 전달됨

```plaintext
[Producer] → (Direct Exchange) → [Queue(error)] → [Consumer1]
                                      [Queue(info)] → [Consumer2]
```

```javascript
await channel.assertExchange('direct_logs', 'direct', { durable: false });
await channel.publish('direct_logs', 'error', Buffer.from("에러 메시지"));
```

---

### ✅ 4. 토픽 (Topic Exchange)
- `*.error`, `app.#` 같은 패턴을 사용하여 메시지를 필터링

```plaintext
[Producer] → (Topic Exchange) → [Queue(app.error)] → [Consumer1]
                                     [Queue(app.info)] → [Consumer2]
```

```javascript
await channel.assertExchange('topic_logs', 'topic', { durable: false });
await channel.publish('topic_logs', 'app.error', Buffer.from("애플리케이션 오류 발생"));
```

---

## 5️⃣ AMQP와 RabbitMQ 사용 예제 (Node.js)

### ✅ 1. RabbitMQ 연결 및 큐 생성
```javascript
const amqp = require('amqplib');

async function setupQueue() {
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();

    const queue = 'task_queue';
    await channel.assertQueue(queue, { durable: true });

    console.log("Queue 생성 완료");
}

setupQueue();
```

---

### ✅ 2. 메시지 발행 (Producer)
```javascript
async function sendMessage() {
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();

    const queue = 'task_queue';
    const message = 'Hello, AMQP!';

    await channel.assertQueue(queue, { durable: true });
    channel.sendToQueue(queue, Buffer.from(message), { persistent: true });

    console.log(`메시지 전송: ${message}`);
    setTimeout(() => { connection.close(); }, 500);
}

sendMessage();
```

---

### ✅ 3. 메시지 소비 (Consumer)
```javascript
async function receiveMessage() {
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();

    const queue = 'task_queue';
    await channel.assertQueue(queue, { durable: true });

    console.log(`[*] 큐에서 메시지를 기다리는 중...`);
    channel.consume(queue, (msg) => {
        console.log(`[x] 받은 메시지: ${msg.content.toString()}`);
    }, { noAck: true });
}

receiveMessage();
```

> **👉🏻 위 코드는 "task_queue"에서 메시지를 주고받는 예제입니다.**

---

## 6️⃣ AMQP의 장점과 단점

| 장점 | 단점 |
|------|------|
| **비동기 메시징 지원** | **초기 설정이 다소 복잡** |
| **다양한 메시징 패턴 지원** | **브로커(RabbitMQ) 설치 필요** |
| **확장성 및 신뢰성 보장** | **TCP 기반이라 네트워크 환경이 제한될 수 있음** |

> **👉🏻 AMQP는 대규모 시스템에서 신뢰성 있는 메시지 처리를 위한 강력한 프로토콜입니다.**

---

## 7️⃣ AMQP vs MQTT 비교

| 비교 항목 | AMQP | MQTT |
|-----------|------|------|
| **사용 목적** | 메시지 큐 및 라우팅 | IoT 및 경량 메시징 |
| **메시징 방식** | Queue & Pub/Sub | Pub/Sub |
| **QoS 지원** | 기본 제공 | QoS 0, 1, 2 |
| **연결 방식** | 단기 연결 가능 | 지속 연결 (Persistent) |
| **적용 사례** | 마이크로서비스, 이벤트 메시징 | IoT, 실시간 데이터 처리 |

> **👉🏻 AMQP는 복잡한 메시징 구조를 지원하고, MQTT는 IoT에 최적화되어 있습니다.**

---

## 8️⃣ AMQP 활용 사례

✅ **마이크로서비스 간 메시지 전달**
- 서비스 간 이벤트를 안전하게 전달하여 비동기 아키텍처 구축

✅ **이벤트 드리븐 아키텍처**
- 특정 이벤트 발생 시 여러 서비스가 동작하도록 설계

✅ **분산 시스템 메시징**
- 대규모 시스템에서 **비동기 메시지 큐를 활용하여 확장성 보장**

✅ **IoT 데이터 처리**
- 수많은 IoT 기기에서 발생하는 데이터를 안정적으로 수집 및 처리

---

## 마무리

- **AMQP는 메시지 브로커를 위한 개방형 표준 프로토콜**
- **RabbitMQ와 같은 메시지 브로커에서 널리 사용됨**
- **비동기 메시지 큐, 라우팅, 토픽 기반 메시징 등을 지원**
- **마이크로서비스 및 이벤트 기반 아키텍처에 적합**

> **✨ AMQP를 활용하여 확장성 높은 메시징 시스템을 구축하세요!**  

