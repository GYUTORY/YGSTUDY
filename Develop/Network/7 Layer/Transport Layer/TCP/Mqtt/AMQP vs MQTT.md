---
title: AMQP MQTT
tags: [network, 7-layer, transport-layer, tcp, mqtt]
updated: 2025-08-10
---
# AMQP와 MQTT의 차이점

## 배경

MQTT와 AMQP는 모두 메시지 브로커 시스템에서 사용되는 통신 프로토콜입니다. 서로 다른 기기나 프로그램들이 메시지를 주고받을 때 사용하는 규칙이라고 생각하면 됩니다.

### 기본 개념

**메시지 브로커란?**
- 여러 프로그램이나 기기들이 서로 통신할 때 중간에서 메시지를 전달해주는 역할
- 마치 우체부가 편지를 전달하는 것처럼, 메시지를 보내는 쪽에서 받는 쪽으로 전달

**프로토콜이란?**
- 기기들이 서로 통신할 때 따라야 하는 규칙과 형식
- 마치 사람들이 대화할 때 사용하는 언어와 문법 같은 것

**메시지 큐잉이란?**
- 메시지를 일시적으로 저장했다가 적절한 시점에 전달하는 방식
- 발신자와 수신자가 동시에 온라인에 있지 않아도 메시지를 주고받을 수 있음

---


**메시지 브로커란?**
- 여러 프로그램이나 기기들이 서로 통신할 때 중간에서 메시지를 전달해주는 역할
- 마치 우체부가 편지를 전달하는 것처럼, 메시지를 보내는 쪽에서 받는 쪽으로 전달

**프로토콜이란?**
- 기기들이 서로 통신할 때 따라야 하는 규칙과 형식
- 마치 사람들이 대화할 때 사용하는 언어와 문법 같은 것

**메시지 큐잉이란?**
- 메시지를 일시적으로 저장했다가 적절한 시점에 전달하는 방식
- 발신자와 수신자가 동시에 온라인에 있지 않아도 메시지를 주고받을 수 있음

---


1. **Broker (브로커)**
   - 메시지의 중앙 허브 역할
   - 모든 메시지가 거쳐가는 중간 지점
   - 마치 우체국과 같은 역할
   - 클라이언트들이 연결하는 서버

2. **Publisher (발행자)**
   - 메시지를 보내는 쪽
   - 센서, 앱, 기기 등이 될 수 있음
   - 특정 주제(topic)로 메시지를 발행

3. **Subscriber (구독자)**
   - 메시지를 받는 쪽
   - 특정 주제의 메시지를 구독하여 받음
   - 여러 주제를 동시에 구독 가능

4. **Topic (토픽)**
   - 메시지의 주제/카테고리
   - 계층 구조로 구성 (예: `home/livingroom/temperature`)
   - 와일드카드 사용 가능 (`home/+/temperature`)


1. **Exchange (교환소)**
   - 메시지 라우팅을 담당
   - 메시지를 적절한 큐로 전달하는 역할
   - 여러 종류의 라우팅 규칙 제공
   - 메시지의 목적지를 결정하는 중간 처리소

2. **Queue (큐)**
   - 메시지 저장소
   - 메시지가 실제로 저장되는 곳
   - 소비자가 메시지를 가져가는 곳
   - FIFO(First In, First Out) 방식으로 처리

3. **Binding (바인딩)**
   - Exchange와 Queue 간의 연결 규칙
   - 어떤 메시지가 어떤 큐로 가야 하는지 정의
   - 라우팅 키나 패턴으로 연결

4. **Channel (채널)**
   - 논리적 연결
   - 하나의 연결에서 여러 개의 논리적 통신 경로
   - 메모리 효율성을 위해 사용


### MQTT 사용 사례
- **스마트 홈**: 온도 센서, 조명 제어
- **차량 통신**: 실시간 차량 상태 모니터링
- **산업 IoT**: 공장 센서 데이터 수집
- **모바일 앱**: 푸시 알림

### AMQP 사용 사례
- **금융 시스템**: 주식 거래, 결제 처리
- **엔터프라이즈**: 대규모 시스템 통합
- **마이크로서비스**: 서비스 간 통신
- **데이터 파이프라인**: 대용량 데이터 처리

---


### MQTT 보안
```javascript
// MQTT 보안 설정 예시
const client = mqtt.connect('mqtt://broker.example.com', {
    username: 'user',
    password: 'password',
    clientId: 'unique_client_id',
    clean: true,
    reconnectPeriod: 1000,
    connectTimeout: 30 * 1000,
    rejectUnauthorized: false
});
```

### AMQP 보안
```javascript
// AMQP 보안 설정 예시
const connection = await amqp.connect('amqps://localhost', {
    credentials: amqp.credentials.plain('user', 'password'),
    heartbeat: 60,
    connection_timeout: 30000
});
```

---


### MQTT를 선택해야 할 때
- IoT 기기나 센서와의 통신
- 배터리 수명이 중요한 경우
- 네트워크 대역폭이 제한적인 경우
- 실시간 데이터 전송이 필요한 경우
- 간단한 구현이 필요한 경우

### AMQP를 선택해야 할 때
- 기업 환경의 복잡한 시스템
- 메시지 손실이 절대 안 되는 경우
- 고급 라우팅이 필요한 경우
- 보안이 중요한 경우
- 대용량 데이터 처리가 필요한 경우

---


- **Broker/Exchange**: 메시지의 중간 전달자
- **Publisher/Producer**: 메시지를 보내는 쪽
- **Subscriber/Consumer**: 메시지를 받는 쪽
- **Topic/Routing Key**: 메시지의 주제나 경로
- **QoS**: 메시지 전달의 품질 수준
- **Queue**: 메시지가 저장되는 곳
- **Binding**: 메시지 라우팅 규칙
- **Channel**: 논리적 통신 경로







**메시지 브로커란?**
- 여러 프로그램이나 기기들이 서로 통신할 때 중간에서 메시지를 전달해주는 역할
- 마치 우체부가 편지를 전달하는 것처럼, 메시지를 보내는 쪽에서 받는 쪽으로 전달

**프로토콜이란?**
- 기기들이 서로 통신할 때 따라야 하는 규칙과 형식
- 마치 사람들이 대화할 때 사용하는 언어와 문법 같은 것

**메시지 큐잉이란?**
- 메시지를 일시적으로 저장했다가 적절한 시점에 전달하는 방식
- 발신자와 수신자가 동시에 온라인에 있지 않아도 메시지를 주고받을 수 있음

---


**메시지 브로커란?**
- 여러 프로그램이나 기기들이 서로 통신할 때 중간에서 메시지를 전달해주는 역할
- 마치 우체부가 편지를 전달하는 것처럼, 메시지를 보내는 쪽에서 받는 쪽으로 전달

**프로토콜이란?**
- 기기들이 서로 통신할 때 따라야 하는 규칙과 형식
- 마치 사람들이 대화할 때 사용하는 언어와 문법 같은 것

**메시지 큐잉이란?**
- 메시지를 일시적으로 저장했다가 적절한 시점에 전달하는 방식
- 발신자와 수신자가 동시에 온라인에 있지 않아도 메시지를 주고받을 수 있음

---


1. **Broker (브로커)**
   - 메시지의 중앙 허브 역할
   - 모든 메시지가 거쳐가는 중간 지점
   - 마치 우체국과 같은 역할
   - 클라이언트들이 연결하는 서버

2. **Publisher (발행자)**
   - 메시지를 보내는 쪽
   - 센서, 앱, 기기 등이 될 수 있음
   - 특정 주제(topic)로 메시지를 발행

3. **Subscriber (구독자)**
   - 메시지를 받는 쪽
   - 특정 주제의 메시지를 구독하여 받음
   - 여러 주제를 동시에 구독 가능

4. **Topic (토픽)**
   - 메시지의 주제/카테고리
   - 계층 구조로 구성 (예: `home/livingroom/temperature`)
   - 와일드카드 사용 가능 (`home/+/temperature`)


1. **Exchange (교환소)**
   - 메시지 라우팅을 담당
   - 메시지를 적절한 큐로 전달하는 역할
   - 여러 종류의 라우팅 규칙 제공
   - 메시지의 목적지를 결정하는 중간 처리소

2. **Queue (큐)**
   - 메시지 저장소
   - 메시지가 실제로 저장되는 곳
   - 소비자가 메시지를 가져가는 곳
   - FIFO(First In, First Out) 방식으로 처리

3. **Binding (바인딩)**
   - Exchange와 Queue 간의 연결 규칙
   - 어떤 메시지가 어떤 큐로 가야 하는지 정의
   - 라우팅 키나 패턴으로 연결

4. **Channel (채널)**
   - 논리적 연결
   - 하나의 연결에서 여러 개의 논리적 통신 경로
   - 메모리 효율성을 위해 사용






## MQTT (Message Queuing Telemetry Transport)

### MQTT란?

MQTT는 IoT 기기들을 위한 가벼운 메시지 전송 프로토콜입니다. 배터리 수명이 짧고 네트워크 연결이 불안정한 센서나 스마트 기기들이 효율적으로 통신할 수 있도록 설계되었습니다.

**Telemetry란?**
- 원격 측정을 의미하는 용어
- 멀리 떨어진 곳에서 데이터를 수집하고 전송하는 기술

### MQTT 구조

#### JavaScript 예시

```javascript
// MQTT 클라이언트 예시 (mqtt.js 라이브러리 사용)
const mqtt = require('mqtt');

// 브로커에 연결
const client = mqtt.connect('mqtt://broker.example.com');

// 메시지 발행 (Publisher)
client.publish('home/temperature', '23.5', { qos: 1 }, (err) => {
    if (!err) {
        console.log('온도 데이터 전송 완료');
    }
});

// 메시지 구독 (Subscriber)
client.subscribe('home/temperature', (err) => {
    if (!err) {
        console.log('온도 토픽 구독 완료');
    }
});

// 메시지 수신
client.on('message', (topic, message) => {
    console.log(`토픽: ${topic}, 메시지: ${message.toString()}`);
});
```

### QoS (Quality of Service) 레벨

MQTT는 메시지 전달의 신뢰성을 3단계로 나누어 제공합니다:

1. **QoS 0 - 최대 한 번 전달 (At most once)**
   - 가장 빠르지만 메시지 손실 가능성 있음
   - 실시간 게임, 스트리밍 등에 적합
   - 확인 응답 없이 한 번만 전송

2. **QoS 1 - 최소 한 번 전달 (At least once)**
   - 메시지가 최소 한 번은 도착함을 보장
   - 중복 전달 가능성 있음
   - 발신자가 확인 응답을 받을 때까지 재전송

3. **QoS 2 - 정확히 한 번 전달 (Exactly once)**
   - 가장 안전하지만 느림
   - 중요한 데이터 전송에 사용
   - 4단계 핸드셰이크로 중복 방지

```javascript
// QoS 레벨별 메시지 발행 예시
client.publish('sensor/data', 'critical_data', { qos: 2 }, (err) => {
    console.log('중요 데이터 전송 (QoS 2)');
});

client.publish('game/position', 'player_pos', { qos: 0 }, (err) => {
    console.log('실시간 게임 데이터 전송 (QoS 0)');
});
```

### MQTT 장점
- **매우 가벼움**: 헤더가 2바이트로 최소
- **빠른 전송**: 낮은 오버헤드로 빠른 메시지 전달
- **배터리 효율적**: IoT 기기에 최적화
- **간단한 구현**: 복잡하지 않은 구조

### MQTT 단점
- **제한된 메시지 크기**: 큰 데이터 전송에 부적합
- **기본적인 라우팅**: 복잡한 메시지 라우팅 불가
- **제한된 보안**: 기본적인 보안 기능만 제공

---

## AMQP (Advanced Message Queuing Protocol)

### AMQP란?

AMQP는 기업 환경을 위한 고급 메시지 큐잉 프로토콜입니다. 복잡한 분산 시스템에서 안정적이고 안전한 메시지 전달이 필요한 경우에 사용됩니다.

**Advanced란?**
- 고급 기능들을 제공한다는 의미
- 복잡한 라우팅, 트랜잭션, 보안 기능 등 포함

### AMQP 구조

#### JavaScript 예시

```javascript
// AMQP 클라이언트 예시 (amqplib 라이브러리 사용)
const amqp = require('amqplib');

async function setupAMQP() {
    // 연결 생성
    const connection = await amqp.connect('amqp://localhost');
    const channel = await connection.createChannel();
    
    // Exchange 생성
    await channel.assertExchange('order_exchange', 'direct', { durable: true });
    
    // Queue 생성
    await channel.assertQueue('order_queue', { durable: true });
    
    // Binding 설정
    await channel.bindQueue('order_queue', 'order_exchange', 'order.created');
    
    // 메시지 발행
    channel.publish('order_exchange', 'order.created', Buffer.from('새 주문이 생성되었습니다'), {
        persistent: true,
        priority: 1
    });
    
    // 메시지 소비
    channel.consume('order_queue', (msg) => {
        console.log('받은 메시지:', msg.content.toString());
        channel.ack(msg); // 메시지 확인
    });
}
```

### Exchange 타입

AMQP는 다양한 라우팅 방식을 제공합니다:

1. **Direct Exchange**
   - 정확한 라우팅 키와 매칭되는 큐로 전달
   - 예: `order.created` → 주문 큐
   - 가장 단순한 라우팅 방식

2. **Topic Exchange**
   - 패턴 기반 라우팅
   - 와일드카드 사용 가능 (`*`, `#`)
   - 예: `user.*.notification` → 모든 사용자 알림

3. **Fanout Exchange**
   - 모든 바인딩된 큐에 브로드캐스트
   - 라우팅 키 무시
   - 예: 시스템 공지사항

4. **Headers Exchange**
   - 메시지 속성 기반 라우팅
   - 복잡한 조건부 라우팅에 사용
   - 헤더 값으로 라우팅 결정

```javascript
// Exchange 타입별 예시
// Direct Exchange
channel.publish('order_exchange', 'order.created', Buffer.from('주문 생성'));

// Topic Exchange
channel.publish('notification_exchange', 'user.123.notification', Buffer.from('사용자 알림'));

// Fanout Exchange
channel.publish('broadcast_exchange', '', Buffer.from('시스템 공지'));
```

### AMQP 장점
- **고급 라우팅**: 복잡한 메시지 라우팅 가능
- **강력한 보안**: TLS, SASL 등 고급 보안 기능
- **메시지 지속성**: 메시지 손실 방지
- **트랜잭션 지원**: 안전한 메시지 처리

### AMQP 단점
- **높은 오버헤드**: 복잡한 구조로 인한 성능 저하
- **복잡한 구현**: 설정과 관리가 복잡
- **리소스 사용량**: 더 많은 메모리와 CPU 사용

---

## MQTT vs AMQP 비교

| 구분 | MQTT | AMQP |
|------|------|------|
| **목적** | IoT 기기 통신 | 기업 메시징 |
| **복잡도** | 간단함 | 복잡함 |
| **오버헤드** | 매우 낮음 (2바이트) | 높음 |
| **메시지 크기** | 제한적 | 대용량 지원 |
| **라우팅** | 토픽 기반 (단순) | 고급 라우팅 |
| **보안** | 기본적 | 고급 |
| **성능** | 빠름 | 상대적으로 느림 |
| **배터리 효율** | 매우 좋음 | 보통 |

---

