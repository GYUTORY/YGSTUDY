---
title: AMQP Advanced Message Queuing Protocol
tags: [network, 7-layer, transport-layer, tcp, mqtt]
updated: 2025-08-10
---
# AMQP (Advanced Message Queuing Protocol)

## 배경
- [AMQP란?](#amqp란)
- [메시지 큐의 기본 개념](#메시지-큐의-기본-개념)
- [AMQP의 핵심 구성 요소](#amqp의-핵심-구성-요소)
- [메시징 패턴 이해하기](#메시징-패턴-이해하기)
- [실제 사용 예제](#실제-사용-예제)
- [AMQP vs MQTT](#amqp-vs-mqtt)
- [활용 사례](#활용-사례)

---

메시지 브로커는 **메시지를 중간에서 받아서 적절한 곳으로 전달해주는 중개자**입니다. 마치 우체부가 편지를 받아서 각 집으로 배달하는 것과 같습니다.


### 🔄 동기 vs 비동기 통신

**동기 통신 (Synchronous)**
```javascript
// 동기 방식 - 응답을 기다림
function sendMessageSync(message) {
    const response = server.processMessage(message); // 여기서 멈춤
    return response; // 응답이 올 때까지 대기
}
```

**비동기 통신 (Asynchronous)**
```javascript
// 비동기 방식 - 응답을 기다리지 않음
function sendMessageAsync(message) {
    messageQueue.send(message); // 바로 다음으로 넘어감
    return "메시지가 큐에 저장되었습니다";
}
```

### 📋 메시지 큐의 장점
- **시스템 부하 분산**: 메시지를 즉시 처리하지 않고 큐에 저장
- **신뢰성**: 메시지 손실 방지
- **확장성**: 여러 소비자가 동시에 메시지 처리 가능

---

- **시스템 부하 분산**: 메시지를 즉시 처리하지 않고 큐에 저장
- **신뢰성**: 메시지 손실 방지
- **확장성**: 여러 소비자가 동시에 메시지 처리 가능

---


#### 1️⃣ Producer (생산자)
메시지를 생성하고 보내는 역할
```javascript
// Producer 예시
const producer = {
    sendMessage: function(message) {
        // Exchange로 메시지 전송
        exchange.receive(message);
    }
};
```

#### 2️⃣ Exchange (교환기)
메시지를 받아서 적절한 큐로 분배하는 역할
```javascript
// Exchange의 기본 동작
const exchange = {
    receive: function(message) {
        const targetQueue = this.routeMessage(message);
        targetQueue.add(message);
    },
    
    routeMessage: function(message) {
        // 메시지 타입에 따라 적절한 큐 선택
        if (message.type === 'error') {
            return errorQueue;
        } else if (message.type === 'info') {
            return infoQueue;
        }
    }
};
```

#### 3️⃣ Queue (큐)
메시지가 저장되는 공간
```javascript
// Queue의 기본 구조
const queue = {
    messages: [],
    
    add: function(message) {
        this.messages.push(message);
        console.log(`메시지 추가됨: ${message.content}`);
    },
    
    get: function() {
        return this.messages.shift(); // 가장 오래된 메시지 반환
    }
};
```

#### 4️⃣ Consumer (소비자)
큐에서 메시지를 가져와서 처리하는 역할
```javascript
// Consumer 예시
const consumer = {
    processMessage: function() {
        const message = queue.get();
        if (message) {
            console.log(`메시지 처리 중: ${message.content}`);
            // 실제 비즈니스 로직 처리
        }
    }
};
```

---


### 1️⃣ 단순 큐 (Simple Queue)
가장 기본적인 패턴 - 하나의 생산자가 하나의 소비자에게 메시지 전달

```javascript
// 단순 큐 예시
const simpleQueue = {
    producer: function() {
        const message = "안녕하세요!";
        queue.add(message);
    },
    
    consumer: function() {
        const message = queue.get();
        console.log(`받은 메시지: ${message}`);
    }
};
```

### 2️⃣ 게시/구독 (Publish/Subscribe)
하나의 메시지를 여러 소비자가 받는 패턴

```javascript
// Fanout Exchange 예시
const fanoutExchange = {
    subscribers: [], // 구독자 목록
    
    subscribe: function(consumer) {
        this.subscribers.push(consumer);
    },
    
    publish: function(message) {
        // 모든 구독자에게 메시지 전달
        this.subscribers.forEach(subscriber => {
            subscriber.receive(message);
        });
    }
};

// 사용 예시
fanoutExchange.subscribe(consumer1);
fanoutExchange.subscribe(consumer2);
fanoutExchange.publish("공지사항: 시스템 점검 예정");
```

### 3️⃣ 라우팅 (Routing)
메시지 타입에 따라 다른 큐로 전달하는 패턴

```javascript
// Direct Exchange 예시
const directExchange = {
    routes: {
        'error': errorQueue,
        'info': infoQueue,
        'warning': warningQueue
    },
    
    route: function(message) {
        const queue = this.routes[message.type];
        if (queue) {
            queue.add(message);
        }
    }
};

// 사용 예시
directExchange.route({ type: 'error', content: '데이터베이스 연결 실패' });
directExchange.route({ type: 'info', content: '사용자 로그인 성공' });
```

### 4️⃣ 토픽 (Topic)
패턴 매칭을 통한 메시지 필터링

```javascript
// Topic Exchange 예시
const topicExchange = {
    patterns: {
        'user.*': userQueue,      // user.login, user.logout 등
        'system.#': systemQueue,  // system.start, system.stop 등
        '*.error': errorQueue     // user.error, system.error 등
    },
    
    matchPattern: function(topic, pattern) {
        // 간단한 패턴 매칭 (실제로는 더 복잡한 로직 필요)
        const regex = pattern.replace('*', '[^.]+').replace('#', '.*');
        return new RegExp(`^${regex}$`).test(topic);
    },
    
    route: function(topic, message) {
        for (const [pattern, queue] of Object.entries(this.patterns)) {
            if (this.matchPattern(topic, pattern)) {
                queue.add(message);
                break;
            }
        }
    }
};
```

---


### 🚀 RabbitMQ와 Node.js 연동

#### 1️⃣ 기본 설정
```javascript
const amqp = require('amqplib');

// RabbitMQ 연결
async function connectToRabbitMQ() {
    try {
        const connection = await amqp.connect('amqp://localhost');
        const channel = await connection.createChannel();
        
        console.log('RabbitMQ에 연결되었습니다!');
        return { connection, channel };
    } catch (error) {
        console.error('RabbitMQ 연결 실패:', error);
        throw error;
    }
}
```

#### 2️⃣ 큐 생성
```javascript
async function createQueue(channel, queueName) {
    try {
        // 큐가 없으면 생성, 있으면 기존 큐 사용
        await channel.assertQueue(queueName, {
            durable: true  // 서버 재시작 후에도 큐 유지
        });
        
        console.log(`큐 '${queueName}' 생성/확인 완료`);
    } catch (error) {
        console.error('큐 생성 실패:', error);
        throw error;
    }
}
```

#### 3️⃣ 메시지 발행 (Producer)
```javascript
async function sendMessage(queueName, message) {
    const { connection, channel } = await connectToRabbitMQ();
    
    try {
        await createQueue(channel, queueName);
        
        // 메시지 전송
        channel.sendToQueue(queueName, Buffer.from(message), {
            persistent: true  // 메시지를 디스크에 저장
        });
        
        console.log(`메시지 전송 완료: ${message}`);
    } catch (error) {
        console.error('메시지 전송 실패:', error);
    } finally {
        setTimeout(() => connection.close(), 500);
    }
}

// 사용 예시
sendMessage('task_queue', '안녕하세요, AMQP!');
```

#### 4️⃣ 메시지 소비 (Consumer)
```javascript
async function receiveMessage(queueName) {
    const { connection, channel } = await connectToRabbitMQ();
    
    try {
        await createQueue(channel, queueName);
        
        console.log(`[*] 큐 '${queueName}'에서 메시지를 기다리는 중...`);
        
        // 메시지 소비
        channel.consume(queueName, (msg) => {
            if (msg) {
                const message = msg.content.toString();
                console.log(`[x] 받은 메시지: ${message}`);
                
                // 메시지 처리 완료 알림
                channel.ack(msg);
            }
        });
        
    } catch (error) {
        console.error('메시지 수신 실패:', error);
    }
}

// 사용 예시
receiveMessage('task_queue');
```

#### 5️⃣ Exchange 사용 예제
```javascript
async function setupExchange() {
    const { connection, channel } = await connectToRabbitMQ();
    
    try {
        // Direct Exchange 생성
        await channel.assertExchange('direct_logs', 'direct', { durable: false });
        
        // 큐 생성
        await channel.assertQueue('error_queue');
        await channel.assertQueue('info_queue');
        
        // 큐를 Exchange에 바인딩
        await channel.bindQueue('error_queue', 'direct_logs', 'error');
        await channel.bindQueue('info_queue', 'direct_logs', 'info');
        
        console.log('Exchange 설정 완료');
        
        // 메시지 발행
        channel.publish('direct_logs', 'error', Buffer.from('에러가 발생했습니다!'));
        channel.publish('direct_logs', 'info', Buffer.from('정보 메시지입니다.'));
        
    } catch (error) {
        console.error('Exchange 설정 실패:', error);
    } finally {
        setTimeout(() => connection.close(), 500);
    }
}
```

---


| 특징 | AMQP | MQTT |
|------|------|------|
| **주요 용도** | 메시지 큐, 마이크로서비스 | IoT, 실시간 데이터 |
| **메시지 크기** | 큰 메시지 지원 | 작은 메시지에 최적화 |
| **연결 방식** | 단기/장기 연결 모두 가능 | 주로 장기 연결 |
| **라우팅** | 복잡한 라우팅 지원 | 단순한 토픽 기반 |
| **QoS** | 기본 제공 | QoS 0, 1, 2 레벨 |


**AMQP 사용 시기:**
- 복잡한 메시지 라우팅이 필요할 때
- 마이크로서비스 간 통신
- 대용량 메시지 처리

**MQTT 사용 시기:**
- IoT 기기와의 통신
- 실시간 데이터 스트리밍
- 네트워크 대역폭이 제한적인 환경

---


### 🏪 온라인 쇼핑몰 시스템
```javascript
// 주문 처리 시스템 예시
const orderSystem = {
    // 주문 생성
    createOrder: async function(orderData) {
        await sendMessage('order_queue', JSON.stringify(orderData));
        console.log('주문이 큐에 등록되었습니다.');
    },
    
    // 재고 확인
    checkInventory: async function(orderData) {
        await sendMessage('inventory_queue', JSON.stringify(orderData));
    },
    
    // 결제 처리
    processPayment: async function(orderData) {
        await sendMessage('payment_queue', JSON.stringify(orderData));
    }
};
```

### 📧 이메일 발송 시스템
```javascript
// 이메일 발송 시스템 예시
const emailSystem = {
    // 이메일 발송 요청
    sendEmail: async function(emailData) {
        await sendMessage('email_queue', JSON.stringify(emailData));
    },
    
    // 이메일 템플릿별 라우팅
    sendWelcomeEmail: async function(userData) {
        const emailData = {
            type: 'welcome',
            to: userData.email,
            template: 'welcome',
            data: userData
        };
        await sendMessage('email_queue', JSON.stringify(emailData));
    }
};
```

### 📊 로그 처리 시스템
```javascript
// 로그 처리 시스템 예시
const logSystem = {
    // 로그 레벨별 처리
    logError: async function(error) {
        await sendMessage('error_log_queue', JSON.stringify(error));
    },
    
    logInfo: async function(info) {
        await sendMessage('info_log_queue', JSON.stringify(info));
    },
    
    logWarning: async function(warning) {
        await sendMessage('warning_log_queue', JSON.stringify(warning));
    }
};
```

---

```javascript
// 주문 처리 시스템 예시
const orderSystem = {
    // 주문 생성
    createOrder: async function(orderData) {
        await sendMessage('order_queue', JSON.stringify(orderData));
        console.log('주문이 큐에 등록되었습니다.');
    },
    
    // 재고 확인
    checkInventory: async function(orderData) {
        await sendMessage('inventory_queue', JSON.stringify(orderData));
    },
    
    // 결제 처리
    processPayment: async function(orderData) {
        await sendMessage('payment_queue', JSON.stringify(orderData));
    }
};
```

```javascript
// 이메일 발송 시스템 예시
const emailSystem = {
    // 이메일 발송 요청
    sendEmail: async function(emailData) {
        await sendMessage('email_queue', JSON.stringify(emailData));
    },
    
    // 이메일 템플릿별 라우팅
    sendWelcomeEmail: async function(userData) {
        const emailData = {
            type: 'welcome',
            to: userData.email,
            template: 'welcome',
            data: userData
        };
        await sendMessage('email_queue', JSON.stringify(emailData));
    }
};
```

```javascript
// 로그 처리 시스템 예시
const logSystem = {
    // 로그 레벨별 처리
    logError: async function(error) {
        await sendMessage('error_log_queue', JSON.stringify(error));
    },
    
    logInfo: async function(info) {
        await sendMessage('info_log_queue', JSON.stringify(info));
    },
    
    logWarning: async function(warning) {
        await sendMessage('warning_log_queue', JSON.stringify(warning));
    }
};
```

---


### ✅ AMQP의 핵심 포인트
- **메시지 브로커를 위한 표준 프로토콜**
- **비동기 메시징으로 시스템 부하 분산**
- **다양한 메시징 패턴 지원**
- **신뢰성 있는 메시지 전달 보장**

### 🎯 실제 개발에서의 활용
- **마이크로서비스 간 통신**
- **이벤트 기반 아키텍처**
- **대용량 데이터 처리**
- **시스템 간 느슨한 결합**


- **마이크로서비스 간 통신**
- **이벤트 기반 아키텍처**
- **대용량 데이터 처리**
- **시스템 간 느슨한 결합**







- **시스템 부하 분산**: 메시지를 즉시 처리하지 않고 큐에 저장
- **신뢰성**: 메시지 손실 방지
- **확장성**: 여러 소비자가 동시에 메시지 처리 가능

---

- **시스템 부하 분산**: 메시지를 즉시 처리하지 않고 큐에 저장
- **신뢰성**: 메시지 손실 방지
- **확장성**: 여러 소비자가 동시에 메시지 처리 가능

---


#### 1️⃣ Producer (생산자)
메시지를 생성하고 보내는 역할
```javascript
// Producer 예시
const producer = {
    sendMessage: function(message) {
        // Exchange로 메시지 전송
        exchange.receive(message);
    }
};
```

#### 2️⃣ Exchange (교환기)
메시지를 받아서 적절한 큐로 분배하는 역할
```javascript
// Exchange의 기본 동작
const exchange = {
    receive: function(message) {
        const targetQueue = this.routeMessage(message);
        targetQueue.add(message);
    },
    
    routeMessage: function(message) {
        // 메시지 타입에 따라 적절한 큐 선택
        if (message.type === 'error') {
            return errorQueue;
        } else if (message.type === 'info') {
            return infoQueue;
        }
    }
};
```

#### 3️⃣ Queue (큐)
메시지가 저장되는 공간
```javascript
// Queue의 기본 구조
const queue = {
    messages: [],
    
    add: function(message) {
        this.messages.push(message);
        console.log(`메시지 추가됨: ${message.content}`);
    },
    
    get: function() {
        return this.messages.shift(); // 가장 오래된 메시지 반환
    }
};
```

#### 4️⃣ Consumer (소비자)
큐에서 메시지를 가져와서 처리하는 역할
```javascript
// Consumer 예시
const consumer = {
    processMessage: function() {
        const message = queue.get();
        if (message) {
            console.log(`메시지 처리 중: ${message.content}`);
            // 실제 비즈니스 로직 처리
        }
    }
};
```

---


```javascript
// 주문 처리 시스템 예시
const orderSystem = {
    // 주문 생성
    createOrder: async function(orderData) {
        await sendMessage('order_queue', JSON.stringify(orderData));
        console.log('주문이 큐에 등록되었습니다.');
    },
    
    // 재고 확인
    checkInventory: async function(orderData) {
        await sendMessage('inventory_queue', JSON.stringify(orderData));
    },
    
    // 결제 처리
    processPayment: async function(orderData) {
        await sendMessage('payment_queue', JSON.stringify(orderData));
    }
};
```

```javascript
// 이메일 발송 시스템 예시
const emailSystem = {
    // 이메일 발송 요청
    sendEmail: async function(emailData) {
        await sendMessage('email_queue', JSON.stringify(emailData));
    },
    
    // 이메일 템플릿별 라우팅
    sendWelcomeEmail: async function(userData) {
        const emailData = {
            type: 'welcome',
            to: userData.email,
            template: 'welcome',
            data: userData
        };
        await sendMessage('email_queue', JSON.stringify(emailData));
    }
};
```

```javascript
// 로그 처리 시스템 예시
const logSystem = {
    // 로그 레벨별 처리
    logError: async function(error) {
        await sendMessage('error_log_queue', JSON.stringify(error));
    },
    
    logInfo: async function(info) {
        await sendMessage('info_log_queue', JSON.stringify(info));
    },
    
    logWarning: async function(warning) {
        await sendMessage('warning_log_queue', JSON.stringify(warning));
    }
};
```

---

```javascript
// 주문 처리 시스템 예시
const orderSystem = {
    // 주문 생성
    createOrder: async function(orderData) {
        await sendMessage('order_queue', JSON.stringify(orderData));
        console.log('주문이 큐에 등록되었습니다.');
    },
    
    // 재고 확인
    checkInventory: async function(orderData) {
        await sendMessage('inventory_queue', JSON.stringify(orderData));
    },
    
    // 결제 처리
    processPayment: async function(orderData) {
        await sendMessage('payment_queue', JSON.stringify(orderData));
    }
};
```

```javascript
// 이메일 발송 시스템 예시
const emailSystem = {
    // 이메일 발송 요청
    sendEmail: async function(emailData) {
        await sendMessage('email_queue', JSON.stringify(emailData));
    },
    
    // 이메일 템플릿별 라우팅
    sendWelcomeEmail: async function(userData) {
        const emailData = {
            type: 'welcome',
            to: userData.email,
            template: 'welcome',
            data: userData
        };
        await sendMessage('email_queue', JSON.stringify(emailData));
    }
};
```

```javascript
// 로그 처리 시스템 예시
const logSystem = {
    // 로그 레벨별 처리
    logError: async function(error) {
        await sendMessage('error_log_queue', JSON.stringify(error));
    },
    
    logInfo: async function(info) {
        await sendMessage('info_log_queue', JSON.stringify(info));
    },
    
    logWarning: async function(warning) {
        await sendMessage('warning_log_queue', JSON.stringify(warning));
    }
};
```

---


- **마이크로서비스 간 통신**
- **이벤트 기반 아키텍처**
- **대용량 데이터 처리**
- **시스템 간 느슨한 결합**


- **마이크로서비스 간 통신**
- **이벤트 기반 아키텍처**
- **대용량 데이터 처리**
- **시스템 간 느슨한 결합**











## 🤔 AMQP란?

**AMQP (Advanced Message Queuing Protocol)**는 **메시지 브로커를 위한 개방형 표준 프로토콜**입니다.

### 🎯 AMQP의 역할
- **메시지의 안전한 전달** 보장
- **여러 시스템 간의 비동기 통신** 지원
- **메시지의 우선순위와 라우팅** 관리

---

## 🏗️ AMQP의 핵심 구성 요소

### 📊 AMQP 아키텍처

```plaintext
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Producer   │───▶│   Exchange  │───▶│    Queue    │───▶│  Consumer   │
│ (생산자)     │    │  (교환기)    │    │   (큐)      │    │ (소비자)     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## ⚖️ AMQP vs MQTT

