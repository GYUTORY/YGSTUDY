

# Gateway (게이트웨이)

## 1️⃣ Gateway란?
**Gateway(게이트웨이)**는 **서로 다른 네트워크 또는 시스템을 연결하는 장치 또는 소프트웨어**입니다.  
클라이언트와 서버 사이에서 **트래픽을 관리하고, 요청을 라우팅하며, 보안 및 로드 밸런싱을 수행**할 수 있습니다.

> **👉🏻 게이트웨이는 네트워크, API, 보안 등 다양한 역할을 수행합니다.**

---

## 2️⃣ Gateway의 주요 역할

### ✅ 1. **네트워크 게이트웨이 (Network Gateway)**
- 서로 다른 네트워크(예: IPv4 ↔ IPv6, LAN ↔ WAN) 간의 통신을 가능하게 함
- 방화벽과 함께 보안 기능을 수행

### ✅ 2. **API 게이트웨이 (API Gateway)**
- 여러 개의 API 요청을 **단일 진입점(Single Entry Point)** 으로 통합
- **요청 라우팅, 인증, 로드 밸런싱, 캐싱 등**을 처리

### ✅ 3. **클라우드 및 하이브리드 게이트웨이**
- 온프레미스(On-Premise)와 클라우드 간 **데이터 연동**
- AWS, Azure, Google Cloud에서 제공하는 **API Gateway** 사용 가능

### ✅ 4. **보안 및 인증 기능**
- **DDoS 방어, 인증(Token), 접근 제어(ACL) 등의 보안 기능 제공**

### ✅ 5. **로드 밸런싱 (Load Balancing)**
- 요청을 여러 서버로 분산하여 **성능 및 가용성을 향상**

---

## 3️⃣ Gateway의 종류

### ✅ 1. **네트워크 게이트웨이 (Network Gateway)**
- 서로 다른 네트워크 간 데이터를 전달하는 하드웨어 또는 소프트웨어
- **라우터(Router), 방화벽(Firewall), VPN 게이트웨이 등이 포함**

```plaintext
[클라이언트] → [네트워크 게이트웨이] → [서버]
```

---

### ✅ 2. **API 게이트웨이 (API Gateway)**
- 마이크로서비스 및 클라우드 환경에서 **API 요청을 통합 관리**
- 대표적인 API Gateway 서비스:
    - **AWS API Gateway**
    - **Kong API Gateway**
    - **NGINX API Gateway**

```plaintext
[Client] → [API Gateway] → [Microservices (User, Order, Payment)]
```

---

### ✅ 3. **클라우드 게이트웨이 (Cloud Gateway)**
- **온프레미스 시스템과 클라우드 간 데이터 연동을 지원**
- **클라우드 보안 및 데이터 암호화 적용 가능**

```plaintext
[Local Server] → [Cloud Gateway] → [AWS S3 / Google Cloud Storage]
```

---

## 4️⃣ API Gateway 사용 예제 (Node.js)

### ✅ 1. API Gateway를 사용한 요청 라우팅

#### 📌 Express.js 기반 API Gateway 구현
```javascript
const express = require("express");
const app = express();
const axios = require("axios");

app.use(express.json());

// 사용자 API 요청을 User Service로 라우팅
app.use("/users", async (req, res) => {
    const response = await axios.get("http://user-service.local/api/users");
    res.json(response.data);
});

// 주문 API 요청을 Order Service로 라우팅
app.use("/orders", async (req, res) => {
    const response = await axios.get("http://order-service.local/api/orders");
    res.json(response.data);
});

app.listen(3000, () => console.log("API Gateway 실행 중 (포트: 3000)"));
```

> **👉🏻 API Gateway를 사용하면 마이크로서비스 요청을 단일 진입점으로 관리할 수 있습니다.**

---

### ✅ 2. API Gateway에서 인증 처리
```javascript
app.use((req, res, next) => {
    const token = req.headers["authorization"];
    if (!token || token !== "VALID_TOKEN") {
        return res.status(403).json({ error: "Unauthorized" });
    }
    next();
});
```

> **👉🏻 API Gateway에서 인증을 처리하면 개별 서비스에서 인증을 구현할 필요가 없습니다.**

---

## 5️⃣ Gateway의 장점과 단점

| 장점 | 단점 |
|------|------|
| **네트워크 및 API 요청을 통합 관리 가능** | **단일 장애 지점(Single Point of Failure, SPOF)이 될 수 있음** |
| **보안 및 인증을 중앙에서 처리 가능** | **추가적인 구성 및 유지보수가 필요함** |
| **로드 밸런싱 및 캐싱을 통해 성능 향상** | **잘못된 설정 시 병목 현상 발생 가능** |

> **👉🏻 Gateway는 보안과 성능을 향상시키지만, 구성과 유지보수가 중요합니다.**

---

## 6️⃣ Gateway vs Reverse Proxy vs Load Balancer 비교

| 비교 항목 | Gateway | Reverse Proxy | Load Balancer |
|-----------|--------|--------------|--------------|
| **주요 역할** | API 및 네트워크 요청 관리 | 클라이언트 요청을 내부 서버로 전달 | 트래픽을 여러 서버로 분산 |
| **보안 기능** | 인증, API 보안 | 기본적인 SSL/TLS 암호화 | 없음 |
| **로드 밸런싱** | 가능 | 제한적 | 가능 |
| **마이크로서비스 지원** | ✅ | ❌ | ❌ |
| **사용 사례** | API 요청 라우팅, 보안, 인증 | 웹 서버 보호, 캐싱 | 서버 부하 분산 |

> **👉🏻 API Gateway는 API 관리 중심, Reverse Proxy는 보안, Load Balancer는 부하 분산 역할을 합니다.**

---

## 7️⃣ Gateway 활용 사례

✅ **마이크로서비스 아키텍처**
- 여러 개의 API 서비스를 **하나의 API Gateway를 통해 관리**

✅ **클라우드 및 하이브리드 환경**
- 온프레미스와 클라우드 간의 **데이터 연동**

✅ **IoT 게이트웨이**
- IoT 기기의 데이터를 중앙 서버로 전송하는 역할

✅ **보안 강화 및 인증 처리**
- API 요청을 **인증 및 접근 제어 후 서비스에 전달**

✅ **DDoS 방어 및 속도 최적화**
- API 캐싱을 통해 **응답 속도를 향상**하고 **불필요한 요청 차단**

