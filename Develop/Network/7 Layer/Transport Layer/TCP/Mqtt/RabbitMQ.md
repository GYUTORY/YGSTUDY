# RabbitMQ (Message Broker)

## 📋 목차
- [RabbitMQ란?](#rabbitmq란)
- [메시지 브로커란?](#메시지-브로커란)
- [RabbitMQ의 주요 특징](#rabbitmq의-주요-특징)
- [RabbitMQ 아키텍처](#rabbitmq-아키텍처)
- [설치 및 실행](#설치-및-실행)
- [JavaScript로 RabbitMQ 사용하기](#javascript로-rabbitmq-사용하기)
- [메시징 패턴](#메시징-패턴)
- [RabbitMQ vs MQTT](#rabbitmq-vs-mqtt)
- [실제 활용 사례](#실제-활용-사례)

---

## 🐰 RabbitMQ란?

**RabbitMQ**는 **메시지 브로커(Message Broker) 서비스**입니다.

쉽게 말해서, 서로 다른 애플리케이션들이 **메시지를 주고받을 수 있도록 중간에서 연결해주는 역할**을 하는 소프트웨어입니다.

### 💡 메시지 브로커란?

메시지 브로커는 **메시지 큐(Message Queue) 시스템**의 핵심 구성 요소입니다.

**메시지 큐**란?
- 데이터를 **임시로 저장하는 공간**
- 마치 **우체국**처럼 메시지를 받아서 보관하고, 받는 사람이 준비되면 전달
- **비동기 처리**를 가능하게 함

**왜 메시지 브로커가 필요한가?**
```
❌ 브로커 없이 직접 연결
앱 A ────────────────→ 앱 B
(앱 B가 다운되면 메시지 손실)

✅ 브로커 사용
앱 A ──→ RabbitMQ ──→ 앱 B
(메시지가 큐에 안전하게 보관됨)
```

---

## ✨ RabbitMQ의 주요 특징

### 1. **메시지 큐 기반 시스템**
- 메시지를 **큐에 저장**하고, 필요할 때 **소비자가 가져감**
- **생산자(Producer)**와 **소비자(Consumer)**가 직접 연결되지 않아도 됨

### 2. **비동기 메시지 처리**
- 요청을 **즉시 처리하지 않고**, 큐에 저장했다가 나중에 처리
- **트래픽이 많아도 안정적인 메시지 처리** 가능

### 3. **다양한 메시징 패턴 지원**
- **단순 큐(Queue)**: 기본적인 메시지 전송
- **게시/구독 (Pub/Sub)**: 하나의 메시지를 여러 곳에 전송
- **라우팅 (Routing)**: 조건에 따라 특정 큐로 메시지 전송
- **토픽 (Topic)**: 주제별로 메시지 분류

### 4. **확장성 및 성능**
- 여러 개의 **Consumer를 통한 병렬 처리**
- **클러스터링 및 고가용성(HA)** 구성 가능

### 5. **보안 및 인증**
- **TLS/SSL**을 통한 보안 메시지 전송
- **사용자 인증 및 권한 관리** 기능

---

## 🏗️ RabbitMQ 아키텍처

### 핵심 구성 요소

| 구성 요소 | 설명 | 역할 |
|----------|------|------|
| **Producer (생산자)** | 메시지를 생성하는 애플리케이션 | 메시지를 큐에 보내는 역할 |
| **Exchange (교환기)** | 메시지를 올바른 큐로 라우팅 | 우체국의 분류 센터 같은 역할 |
| **Queue (큐)** | 메시지가 저장되는 공간 | 우체국의 사서함 같은 역할 |
| **Consumer (소비자)** | 메시지를 처리하는 애플리케이션 | 큐에서 메시지를 가져와 처리 |

### 메시지 흐름
```
Producer → Exchange → Queue → Consumer
   ↓         ↓         ↓        ↓
  메시지    라우팅    저장     처리
  생성      규칙      공간
```

**Exchange의 종류:**
- **Direct Exchange**: 정확한 라우팅 키 매칭
- **Fanout Exchange**: 모든 큐에 브로드캐스트
- **Topic Exchange**: 패턴 기반 라우팅
- **Headers Exchange**: 헤더 값 기반 라우팅

---

## 🚀 설치 및 실행

### Docker로 RabbitMQ 설치

```bash
# RabbitMQ 컨테이너 실행
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:management
```

**포트 설명:**
- **5672**: AMQP 프로토콜 포트 (메시지 전송용)
- **15672**: 웹 관리 콘솔 포트

### 웹 관리 콘솔 접속

1. 웹 브라우저에서 `http://localhost:15672` 접속
2. 기본 로그인 정보:
   - **사용자명**: `guest`
   - **비밀번호**: `guest`

**관리 콘솔에서 확인할 수 있는 것:**
- 큐 상태 및 메시지 개수
- Exchange 설정
- 연결된 Producer/Consumer 정보
- 시스템 성능 지표

---

## 💻 JavaScript로 RabbitMQ 사용하기

### 1. 라이브러리 설치

```bash
npm install amqplib
```

### 2. 메시지 발행 (Producer)

```javascript
const amqp = require('amqplib');

async function sendMessage() {
    try {
        // RabbitMQ 서버에 연결
        const connection = await amqp.connect('amqp://localhost');
        const channel = await connection.createChannel();

        const queue = 'hello';
        const message = 'Hello, RabbitMQ!';

        // 큐가 존재하는지 확인하고, 없으면 생성
        await channel.assertQueue(queue, { 
            durable: false  // 서버 재시작 시 큐 유지 여부
        });

        // 메시지를 큐에 전송
        channel.sendToQueue(queue, Buffer.from(message));

        console.log(`✅ 메시지 전송 완료: ${message}`);
        
        // 연결 종료
        setTimeout(() => {
            connection.close();
        }, 500);
    } catch (error) {
        console.error('❌ 메시지 전송 실패:', error);
    }
}

sendMessage();
```

### 3. 메시지 소비 (Consumer)

```javascript
const amqp = require('amqplib');

async function receiveMessage() {
    try {
        // RabbitMQ 서버에 연결
        const connection = await amqp.connect('amqp://localhost');
        const channel = await connection.createChannel();

        const queue = 'hello';

        // 큐가 존재하는지 확인
        await channel.assertQueue(queue, { durable: false });

        console.log('⏳ 큐에서 메시지를 기다리는 중...');
        
        // 큐에서 메시지를 소비
        channel.consume(queue, (msg) => {
            if (msg) {
                console.log(`📨 받은 메시지: ${msg.content.toString()}`);
                
                // 메시지 처리 완료 확인 (ACK)
                channel.ack(msg);
            }
        }, { 
            noAck: false  // 수동으로 ACK 처리
        });
    } catch (error) {
        console.error('❌ 메시지 수신 실패:', error);
    }
}

receiveMessage();
```

### 4. 게시/구독 패턴 (Fanout Exchange)

```javascript
// Producer (게시자)
async function publishMessage() {
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();

    const exchange = 'logs';
    const message = '로그 메시지입니다!';

    // Fanout Exchange 생성
    await channel.assertExchange(exchange, 'fanout', { durable: false });
    
    // Exchange로 메시지 발행 (라우팅 키는 빈 문자열)
    channel.publish(exchange, '', Buffer.from(message));
    
    console.log(`📢 메시지 발행: ${message}`);
    
    setTimeout(() => connection.close(), 500);
}

// Consumer (구독자)
async function subscribeToLogs() {
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();

    const exchange = 'logs';

    // Exchange 생성
    await channel.assertExchange(exchange, 'fanout', { durable: false });
    
    // 임시 큐 생성 (서버가 자동으로 이름 생성)
    const result = await channel.assertQueue('', { exclusive: true });
    const queueName = result.queue;

    // 큐를 Exchange에 바인딩
    await channel.bindQueue(queueName, exchange, '');

    console.log('📡 로그 메시지를 구독 중...');
    
    channel.consume(queueName, (msg) => {
        if (msg) {
            console.log(`📋 로그: ${msg.content.toString()}`);
            channel.ack(msg);
        }
    });
}
```

---

## 🔄 메시징 패턴

### 1. 기본 큐 (Simple Queue)
가장 기본적인 패턴으로, **하나의 Producer가 하나의 Consumer에게 메시지 전송**

```javascript
// Producer
channel.sendToQueue('simple_queue', Buffer.from('Hello'));

// Consumer
channel.consume('simple_queue', (msg) => {
    console.log(msg.content.toString());
    channel.ack(msg);
});
```

### 2. 게시/구독 (Fanout Exchange)
**하나의 메시지를 여러 Consumer가 동시에 받는 패턴**

```javascript
// Producer
await channel.assertExchange('broadcast', 'fanout');
channel.publish('broadcast', '', Buffer.from('공지사항'));

// Consumer 1
const q1 = await channel.assertQueue('', { exclusive: true });
await channel.bindQueue(q1.queue, 'broadcast', '');

// Consumer 2
const q2 = await channel.assertQueue('', { exclusive: true });
await channel.bindQueue(q2.queue, 'broadcast', '');
```

### 3. 라우팅 (Direct Exchange)
**특정 조건에 따라 메시지를 다른 큐로 라우팅**

```javascript
// Producer
await channel.assertExchange('direct_logs', 'direct');
channel.publish('direct_logs', 'error', Buffer.from('에러 발생'));
channel.publish('direct_logs', 'info', Buffer.from('정보 메시지'));

// Error Consumer
const errorQueue = await channel.assertQueue('error_queue');
await channel.bindQueue(errorQueue.queue, 'direct_logs', 'error');

// Info Consumer
const infoQueue = await channel.assertQueue('info_queue');
await channel.bindQueue(infoQueue.queue, 'direct_logs', 'info');
```

### 4. 토픽 (Topic Exchange)
**패턴 매칭을 통한 유연한 라우팅**

```javascript
// Producer
await channel.assertExchange('topic_logs', 'topic');
channel.publish('topic_logs', 'user.login', Buffer.from('로그인'));
channel.publish('topic_logs', 'user.logout', Buffer.from('로그아웃'));
channel.publish('topic_logs', 'system.error', Buffer.from('시스템 에러'));

// Consumer (user.* 패턴 구독)
const userQueue = await channel.assertQueue('user_queue');
await channel.bindQueue(userQueue.queue, 'topic_logs', 'user.*');

// Consumer (*.error 패턴 구독)
const errorQueue = await channel.assertQueue('error_queue');
await channel.bindQueue(errorQueue.queue, 'topic_logs', '*.error');
```

---

## 🔍 RabbitMQ vs MQTT 비교

| 비교 항목 | RabbitMQ | MQTT |
|-----------|---------|------|
| **주요 용도** | 일반적인 메시지 브로커 | IoT 및 실시간 메시징 |
| **프로토콜** | AMQP (Advanced Message Queuing Protocol) | MQTT |
| **메시징 패턴** | 큐, Pub/Sub, Direct, Topic Exchange | Pub/Sub |
| **QoS 지원** | 기본적으로 제공 | QoS 0, 1, 2 지원 |
| **연결 방식** | 필요 시 연결 | 지속 연결 필요 |
| **메시지 크기** | 큰 메시지 처리 가능 | 작은 메시지에 최적화 |
| **사용 사례** | 마이크로서비스, 이벤트 드리븐 | IoT, 실시간 데이터 |

---

## 🎯 실제 활용 사례

### 1. **마이크로서비스 간 통신**
```javascript
// 주문 서비스 → 결제 서비스
async function processOrder(orderData) {
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();
    
    await channel.assertQueue('payment_queue');
    channel.sendToQueue('payment_queue', Buffer.from(JSON.stringify(orderData)));
    
    console.log('결제 요청 전송 완료');
}
```

### 2. **이메일 발송 시스템**
```javascript
// 사용자 가입 시 이메일 발송
async function sendWelcomeEmail(userData) {
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();
    
    await channel.assertQueue('email_queue');
    channel.sendToQueue('email_queue', Buffer.from(JSON.stringify({
        type: 'welcome',
        email: userData.email,
        name: userData.name
    })));
}
```

### 3. **로그 수집 시스템**
```javascript
// 애플리케이션 로그 수집
async function logMessage(level, message) {
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();
    
    await channel.assertExchange('logs', 'topic');
    channel.publish('logs', `app.${level}`, Buffer.from(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: level,
        message: message
    })));
}
```

### 4. **실시간 알림 시스템**
```javascript
// 푸시 알림 발송
async function sendNotification(userId, message) {
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();
    
    await channel.assertQueue('notification_queue');
    channel.sendToQueue('notification_queue', Buffer.from(JSON.stringify({
        userId: userId,
        message: message,
        timestamp: new Date().toISOString()
    })));
}
```

---

## 📚 주요 용어 정리

| 용어 | 설명 |
|------|------|
| **AMQP** | Advanced Message Queuing Protocol, RabbitMQ가 사용하는 메시징 프로토콜 |
| **Producer** | 메시지를 생성하고 큐에 전송하는 애플리케이션 |
| **Consumer** | 큐에서 메시지를 가져와 처리하는 애플리케이션 |
| **Exchange** | 메시지를 큐로 라우팅하는 구성 요소 |
| **Queue** | 메시지가 저장되는 공간 |
| **Binding** | Exchange와 Queue를 연결하는 규칙 |
| **Routing Key** | 메시지를 특정 큐로 라우팅하기 위한 키 |
| **ACK** | Acknowledgment, 메시지 처리 완료 확인 |
| **Durable** | 서버 재시작 시에도 큐/Exchange가 유지되는지 여부 |
| **Exclusive** | 하나의 연결에서만 사용할 수 있는 큐 |

