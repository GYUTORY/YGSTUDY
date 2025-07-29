# Gateway (게이트웨이)

## 📖 개요

**Gateway(게이트웨이)**는 서로 다른 네트워크나 시스템을 연결하는 중간 다리 역할을 하는 장치 또는 소프트웨어입니다.

쉽게 말해서, **집에서 외부로 나가는 대문**이라고 생각하면 됩니다. 모든 사람이 이 대문을 통해 들어오고 나가며, 대문에서 출입을 관리하고 보안을 확인합니다.

---

## 🔍 핵심 개념 이해하기

### 네트워크 게이트웨이란?
- **서로 다른 네트워크 간의 통신을 가능하게 하는 장치**
- 예: 집의 인터넷 공유기, 회사의 방화벽

### API 게이트웨이란?
- **여러 개의 API 서비스를 하나의 진입점으로 통합하는 소프트웨어**
- 예: 쇼핑몰에서 상품, 주문, 결제 API를 하나의 주소로 관리

---

## 🎯 Gateway의 주요 기능

### 1. 네트워크 연결
- **IPv4 ↔ IPv6 변환**: 서로 다른 인터넷 주소 체계 간 통신
- **LAN ↔ WAN 연결**: 내부 네트워크와 외부 네트워크 연결

### 2. API 통합 관리
- **단일 진입점**: 여러 API를 하나의 주소로 접근 가능
- **요청 라우팅**: 요청을 적절한 서비스로 전달

### 3. 보안 기능
- **인증(Authentication)**: 사용자 신원 확인
- **인가(Authorization)**: 접근 권한 확인
- **DDoS 방어**: 악의적인 공격 차단

### 4. 성능 최적화
- **로드 밸런싱**: 요청을 여러 서버로 분산
- **캐싱**: 자주 요청되는 데이터를 임시 저장

---

## 🏗️ Gateway의 종류

### 1. 네트워크 게이트웨이
**하드웨어 또는 소프트웨어로 구현되는 네트워크 연결 장치**

```javascript
// 네트워크 게이트웨이 예시 (라우터 역할)
const networkGateway = {
    // IPv4 주소를 IPv6로 변환
    convertIPv4ToIPv6: (ipv4Address) => {
        return `2001:db8::${ipv4Address.replace(/\./g, ':')}`;
    },
    
    // 네트워크 패킷 라우팅
    routePacket: (packet, destination) => {
        console.log(`패킷을 ${destination}으로 라우팅합니다.`);
        return packet;
    }
};
```

### 2. API 게이트웨이
**마이크로서비스 환경에서 API 요청을 통합 관리하는 소프트웨어**

```javascript
// API 게이트웨이 기본 구조
const apiGateway = {
    // 서비스별 엔드포인트 매핑
    services: {
        user: 'http://user-service:3001',
        order: 'http://order-service:3002',
        payment: 'http://payment-service:3003'
    },
    
    // 요청 라우팅
    routeRequest: (path, method, data) => {
        const service = path.split('/')[1]; // /user/profile -> user
        const targetUrl = apiGateway.services[service];
        
        if (!targetUrl) {
            throw new Error('서비스를 찾을 수 없습니다.');
        }
        
        return `${targetUrl}${path}`;
    }
};
```

### 3. 클라우드 게이트웨이
**온프레미스 시스템과 클라우드 서비스 간의 연결**

```javascript
// 클라우드 게이트웨이 예시
const cloudGateway = {
    // 로컬 파일을 클라우드에 업로드
    uploadToCloud: async (localFile, cloudStorage) => {
        console.log(`${localFile}을 ${cloudStorage}에 업로드합니다.`);
        // 실제 구현에서는 AWS S3, Google Cloud Storage 등 사용
    },
    
    // 클라우드에서 로컬로 다운로드
    downloadFromCloud: async (cloudFile, localPath) => {
        console.log(`${cloudFile}을 ${localPath}로 다운로드합니다.`);
    }
};
```

---

## 💻 실제 구현 예제

### Express.js로 API 게이트웨이 만들기

```javascript
const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json());

// 인증 미들웨어
const authenticateToken = (req, res, next) => {
    const token = req.headers['authorization'];
    
    if (!token) {
        return res.status(401).json({ error: '토큰이 필요합니다.' });
    }
    
    // 실제로는 JWT 토큰 검증 로직이 들어갑니다
    if (token !== 'valid-token') {
        return res.status(403).json({ error: '유효하지 않은 토큰입니다.' });
    }
    
    next();
};

// 로깅 미들웨어
const logRequest = (req, res, next) => {
    console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
    next();
};

app.use(logRequest);
app.use(authenticateToken);

// 사용자 서비스 라우팅
app.all('/users/*', async (req, res) => {
    try {
        const userServiceUrl = 'http://user-service:3001';
        const targetUrl = `${userServiceUrl}${req.path}`;
        
        const response = await axios({
            method: req.method,
            url: targetUrl,
            data: req.body,
            headers: req.headers
        });
        
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: '사용자 서비스 오류' });
    }
});

// 주문 서비스 라우팅
app.all('/orders/*', async (req, res) => {
    try {
        const orderServiceUrl = 'http://order-service:3002';
        const targetUrl = `${orderServiceUrl}${req.path}`;
        
        const response = await axios({
            method: req.method,
            url: targetUrl,
            data: req.body,
            headers: req.headers
        });
        
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: '주문 서비스 오류' });
    }
});

// 결제 서비스 라우팅
app.all('/payments/*', async (req, res) => {
    try {
        const paymentServiceUrl = 'http://payment-service:3003';
        const targetUrl = `${paymentServiceUrl}${req.path}`;
        
        const response = await axios({
            method: req.method,
            url: targetUrl,
            data: req.body,
            headers: req.headers
        });
        
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: '결제 서비스 오류' });
    }
});

app.listen(3000, () => {
    console.log('API 게이트웨이가 포트 3000에서 실행 중입니다.');
});
```

### 간단한 로드 밸런싱 구현

```javascript
// 라운드 로빈 방식의 로드 밸런서
class LoadBalancer {
    constructor(servers) {
        this.servers = servers;
        this.currentIndex = 0;
    }
    
    getNextServer() {
        const server = this.servers[this.currentIndex];
        this.currentIndex = (this.currentIndex + 1) % this.servers.length;
        return server;
    }
    
    async routeRequest(path, method, data) {
        const server = this.getNextServer();
        console.log(`요청을 ${server}로 라우팅합니다.`);
        
        // 실제로는 axios로 요청을 전달합니다
        return `${server}${path}`;
    }
}

// 사용 예시
const loadBalancer = new LoadBalancer([
    'http://server1:3001',
    'http://server2:3001',
    'http://server3:3001'
]);
```

---

## 🔄 Gateway vs 다른 기술들

### Gateway vs Reverse Proxy

| 구분 | Gateway | Reverse Proxy |
|------|---------|---------------|
| **주요 목적** | API 관리 및 통합 | 웹 서버 보호 및 캐싱 |
| **보안 기능** | 인증, 인가, API 보안 | SSL/TLS 암호화 |
| **마이크로서비스** | ✅ 지원 | ❌ 지원 안함 |
| **사용 예시** | API 요청 통합 관리 | Nginx로 웹 서버 보호 |

### Gateway vs Load Balancer

| 구분 | Gateway | Load Balancer |
|------|---------|---------------|
| **주요 목적** | API 요청 관리 및 보안 | 서버 부하 분산 |
| **기능** | 라우팅, 인증, 캐싱 | 트래픽 분산 |
| **복잡도** | 높음 | 낮음 |
| **사용 예시** | 마이크로서비스 API 관리 | 웹 서버 부하 분산 |

---

## ⚖️ 장단점

### 장점
- **중앙 집중식 관리**: 모든 API 요청을 한 곳에서 관리
- **보안 강화**: 인증과 인가를 중앙에서 처리
- **성능 최적화**: 캐싱과 로드 밸런싱으로 성능 향상
- **개발 편의성**: 클라이언트는 하나의 주소만 알면 됨

### 단점
- **단일 장애점**: 게이트웨이가 다운되면 모든 서비스 접근 불가
- **복잡성 증가**: 추가적인 구성과 유지보수 필요
- **성능 오버헤드**: 요청이 게이트웨이를 거쳐야 함
- **설정 복잡**: 잘못된 설정 시 전체 시스템에 영향

---

## 🏢 실제 사용 사례

### 1. 마이크로서비스 아키텍처
```javascript
// 쇼핑몰 마이크로서비스 예시
const shoppingMallGateway = {
    routes: {
        '/products': 'product-service',
        '/orders': 'order-service', 
        '/payments': 'payment-service',
        '/users': 'user-service'
    }
};
```

### 2. 클라우드 하이브리드 환경
```javascript
// 온프레미스와 클라우드 연결
const hybridGateway = {
    localServices: ['http://local-db:5432', 'http://local-cache:6379'],
    cloudServices: ['https://aws-s3.amazonaws.com', 'https://api.cloudflare.com']
};
```

### 3. IoT 게이트웨이
```javascript
// IoT 기기 데이터 수집
const iotGateway = {
    collectData: (deviceId, sensorData) => {
        console.log(`기기 ${deviceId}에서 데이터 수집:`, sensorData);
        // 중앙 서버로 데이터 전송
    }
};
```

---

## 📚 주요 용어 정리

- **API (Application Programming Interface)**: 애플리케이션 간 통신을 위한 인터페이스
- **마이크로서비스**: 하나의 큰 애플리케이션을 작은 서비스들로 분리한 아키텍처
- **로드 밸런싱**: 요청을 여러 서버로 분산하여 부하를 나누는 기술
- **캐싱**: 자주 사용되는 데이터를 임시로 저장하여 성능을 향상시키는 기술
- **인증(Authentication)**: 사용자가 누구인지 확인하는 과정
- **인가(Authorization)**: 사용자가 특정 리소스에 접근할 권한이 있는지 확인하는 과정
- **DDoS**: 분산 서비스 거부 공격으로, 많은 요청을 보내 서비스를 마비시키는 공격
- **온프레미스(On-Premise)**: 회사 내부에 직접 구축한 IT 인프라
- **클라우드**: 인터넷을 통해 제공되는 IT 서비스

