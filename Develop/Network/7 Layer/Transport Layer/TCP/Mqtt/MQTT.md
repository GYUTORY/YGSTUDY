

# MQTT (Message Queuing Telemetry Transport)

## 1️⃣ MQTT란?
**MQTT (Message Queuing Telemetry Transport)**는 **가벼운 메시지 프로토콜**로,  
제한된 네트워크 환경에서도 **IoT(사물인터넷) 기기 간 통신을 효율적으로 수행**할 수 있도록 설계되었습니다.

> **👉🏻 MQTT는 메시지 기반의 **"발행/구독 (Publish/Subscribe)"** 방식으로 동작합니다.**

---

## 2️⃣ MQTT의 주요 특징

### ✅ 1. **경량 프로토콜 (Lightweight Protocol)**
- 최소한의 네트워크 대역폭을 사용하여 **저전력 및 저성능 기기에서도 사용 가능**
- 패킷 크기가 작아서 **배터리 소모가 적음**

### ✅ 2. **발행/구독 (Publish/Subscribe) 방식**
- **브로커(Broker)**가 메시지를 중개하며, 클라이언트는 **주제(Topic)**를 통해 메시지를 송수신
- **클라이언트 간 직접 연결이 필요 없음**

### ✅ 3. **QoS (Quality of Service) 지원**
- MQTT는 **3가지 QoS 레벨**을 제공하여 메시지 전달 신뢰성을 보장
    - `QoS 0`: **최선 전송 (At most once)** – 메시지가 한 번만 전송됨 (손실 가능)
    - `QoS 1`: **최소 1회 전송 (At least once)** – 중복 전송 가능하지만 반드시 도착
    - `QoS 2`: **정확히 1회 전송 (Exactly once)** – 중복 없이 한 번만 도착

### ✅ 4. **지속적 연결 (Persistent Connection)**
- MQTT 클라이언트는 **항상 연결을 유지**하여 실시간 통신 가능
- `Will Message` 기능을 통해 **비정상 종료 시 메시지를 전송 가능**

### ✅ 5. **보안 (Security)**
- **TLS/SSL**을 지원하여 **암호화된 통신 가능**
- **인증(Authentication) 및 권한 관리** 기능 제공

---

## 3️⃣ MQTT 기본 개념 및 구조

### ✨ MQTT 시스템 구성 요소
| 구성 요소 | 설명 |
|----------|------|
| **Broker (브로커)** | 메시지를 중개하는 중앙 서버 |
| **Publisher (발행자)** | 메시지를 특정 주제(Topic)로 발행 |
| **Subscriber (구독자)** | 특정 주제(Topic)의 메시지를 수신 |

> **👉🏻 브로커가 메시지를 받아서 적절한 구독자에게 전달하는 구조입니다.**

### ✅ MQTT 메시지 흐름
1. **Publisher**가 **Topic(주제)**를 설정하여 메시지를 발행
2. **Broker**가 해당 Topic을 구독한 **Subscriber**에게 메시지를 전달
3. Subscriber는 **필요한 메시지만 수신**

```plaintext
[Publisher] → (Topic: "home/temperature") → [Broker] → [Subscriber]
```

---

## 4️⃣ MQTT 설치 및 사용법

### ✅ MQTT 브로커 설치 (Mosquitto 사용)
```bash
# Mosquitto 설치 (Ubuntu/Debian)
sudo apt update && sudo apt install -y mosquitto mosquitto-clients
```

### ✅ MQTT 브로커 실행
```bash
# Mosquitto 실행
mosquitto -v
```

> **👉🏻 위 명령어를 실행하면 MQTT 브로커가 실행됩니다.**

---

### ✅ MQTT 메시지 발행 및 구독 (CLI)

#### 📌 메시지 발행 (Publisher)
```bash
mosquitto_pub -h localhost -t "home/temperature" -m "25°C"
```
> **👉🏻 "home/temperature" 주제로 "25°C" 메시지 발행**

#### 📌 메시지 구독 (Subscriber)
```bash
mosquitto_sub -h localhost -t "home/temperature"
```
> **👉🏻 "home/temperature" 주제를 구독하여 메시지 수신**

---

## 5️⃣ Node.js에서 MQTT 사용하기

### ✅ 1. `mqtt` 라이브러리 설치
```bash
npm install mqtt
```

### ✅ 2. MQTT 클라이언트 설정 (Publisher & Subscriber)

#### 📌 MQTT 메시지 발행 (Publisher)
```javascript
const mqtt = require("mqtt");
const client = mqtt.connect("mqtt://localhost");

client.on("connect", () => {
    console.log("MQTT 연결 성공");
    client.publish("home/temperature", "25°C"); // 메시지 발행
    client.end(); // 연결 종료
});
```

#### 📌 MQTT 메시지 구독 (Subscriber)
```javascript
const mqtt = require("mqtt");
const client = mqtt.connect("mqtt://localhost");

client.on("connect", () => {
    console.log("MQTT 연결 성공");
    client.subscribe("home/temperature"); // 주제 구독
});

client.on("message", (topic, message) => {
    console.log(`수신된 메시지: ${message.toString()}`);
});
```

> **👉🏻 위 코드는 "home/temperature" 주제를 구독하여 메시지를 수신하는 예제입니다.**

---

## 6️⃣ MQTT QoS (Quality of Service) 설정

### ✅ QoS 설정 예제
```javascript
client.publish("home/temperature", "25°C", { qos: 1 });
client.subscribe("home/temperature", { qos: 2 });
```

> **👉🏻 QoS 1과 2를 설정하면 메시지 전송 신뢰성을 높일 수 있습니다.**

---

## 7️⃣ MQTT 보안 설정 (TLS/SSL)

### ✅ TLS/SSL을 사용한 보안 연결
```javascript
const client = mqtt.connect("mqtts://broker.example.com", {
    port: 8883,
    username: "user",
    password: "password"
});
```

> **👉🏻 MQTT는 기본적으로 보안이 취약할 수 있으므로, TLS/SSL을 적용하는 것이 중요합니다.**

---

## 8️⃣ MQTT와 HTTP 비교

| 비교 항목 | MQTT | HTTP |
|-----------|------|------|
| **통신 방식** | 발행/구독 (Pub/Sub) | 요청/응답 (Request/Response) |
| **속도** | 빠름 (실시간) | 상대적으로 느림 |
| **데이터 크기** | 작음 | 큼 |
| **연결 방식** | 지속적 연결 (Persistent) | 요청 시 연결 |
| **IoT 최적화** | ✅ 가능 | ❌ 비효율적 |

> **👉🏻 MQTT는 **IoT, 실시간 데이터 송수신, 저전력 기기**에 최적화된 프로토콜입니다.**

---

## 9️⃣ MQTT의 활용 사례

✅ **스마트 홈 (Smart Home)**
- 온도 센서에서 데이터를 발행하고, 스마트폰 앱에서 실시간으로 구독

✅ **IoT 기기 통신**
- 공장 내 센서가 데이터 전송 → MQTT 브로커 → 서버에서 분석

✅ **실시간 채팅**
- 채팅 메시지를 MQTT를 통해 빠르게 전송

✅ **실시간 위치 추적**
- GPS 데이터를 지속적으로 발행하고, 구독자가 실시간 추적 가능

