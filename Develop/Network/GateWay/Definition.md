---
title: Gateway (게이트웨이)
tags: [network, gateway, definition, api-gateway, network-gateway]
updated: 2025-08-10
---

# Gateway (게이트웨이)

## 배경

**Gateway(게이트웨이)**는 서로 다른 네트워크나 시스템을 연결하는 중간 다리 역할을 하는 장치 또는 소프트웨어입니다. 쉽게 말해서, 집에서 외부로 나가는 대문이라고 생각하면 됩니다. 모든 사람이 이 대문을 통해 들어오고 나가며, 대문에서 출입을 관리하고 보안을 확인합니다.

### 게이트웨이의 필요성
- **네트워크 연결**: 서로 다른 프로토콜이나 네트워크 간 통신 가능
- **보안 강화**: 중앙집중식 보안 정책 적용
- **로드 밸런싱**: 트래픽 분산 및 관리
- **모니터링**: 통합된 로깅 및 모니터링
- **API 통합**: 여러 서비스를 하나의 진입점으로 통합

### 게이트웨이의 종류
- **네트워크 게이트웨이**: 서로 다른 네트워크 간의 통신을 가능하게 하는 장치
- **API 게이트웨이**: 여러 개의 API 서비스를 하나의 진입점으로 통합하는 소프트웨어
- **애플리케이션 게이트웨이**: 특정 애플리케이션 프로토콜을 처리하는 게이트웨이

## 핵심

### 네트워크 게이트웨이

네트워크 게이트웨이는 서로 다른 네트워크 간의 통신을 가능하게 하는 장치입니다. 예를 들어, 집의 인터넷 공유기나 회사의 방화벽이 네트워크 게이트웨이의 역할을 합니다.

#### 네트워크 게이트웨이의 기능
- **프로토콜 변환**: 서로 다른 네트워크 프로토콜 간 변환
- **주소 변환**: NAT(Network Address Translation) 수행
- **라우팅**: 패킷을 적절한 목적지로 전달
- **보안**: 방화벽 기능으로 네트워크 보호

### API 게이트웨이

API 게이트웨이는 여러 개의 API 서비스를 하나의 진입점으로 통합하는 소프트웨어입니다. 예를 들어, 쇼핑몰에서 상품, 주문, 결제 API를 하나의 주소로 관리할 수 있습니다.

#### API 게이트웨이의 기능
- **라우팅**: 요청을 적절한 서비스로 전달
- **인증/인가**: 사용자 인증 및 권한 확인
- **로드 밸런싱**: 트래픽을 여러 서버에 분산
- **모니터링**: API 호출 로깅 및 메트릭 수집
- **캐싱**: 자주 요청되는 데이터 캐싱

## 예시

### Express.js로 API 게이트웨이 만들기

#### 기본 API 게이트웨이 구현
```javascript
const express = require('express');
const axios = require('axios');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');

const app = express();

// 보안 미들웨어
app.use(helmet());
app.use(express.json());

// 속도 제한 설정
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15분
    max: 100, // IP당 최대 100개 요청
    message: '너무 많은 요청이 발생했습니다.'
});
app.use(limiter);

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
    console.log(`${new Date().toISOString()} - ${req.method} ${req.path} - IP: ${req.ip}`);
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
            headers: {
                ...req.headers,
                'x-forwarded-for': req.ip,
                'x-user-id': req.headers['x-user-id']
            },
            timeout: 5000
        });
        
        res.json(response.data);
    } catch (error) {
        console.error('사용자 서비스 오류:', error.message);
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
            headers: {
                ...req.headers,
                'x-forwarded-for': req.ip,
                'x-user-id': req.headers['x-user-id']
            },
            timeout: 5000
        });
        
        res.json(response.data);
    } catch (error) {
        console.error('주문 서비스 오류:', error.message);
        res.status(500).json({ error: '주문 서비스 오류' });
    }
});

// 상품 서비스 라우팅
app.all('/products/*', async (req, res) => {
    try {
        const productServiceUrl = 'http://product-service:3003';
        const targetUrl = `${productServiceUrl}${req.path}`;
        
        const response = await axios({
            method: req.method,
            url: targetUrl,
            data: req.body,
            headers: {
                ...req.headers,
                'x-forwarded-for': req.ip
            },
            timeout: 5000
        });
        
        res.json(response.data);
    } catch (error) {
        console.error('상품 서비스 오류:', error.message);
        res.status(500).json({ error: '상품 서비스 오류' });
    }
});

// 헬스체크 엔드포인트
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`API 게이트웨이가 포트 ${PORT}에서 실행 중입니다.`);
});
```

### 고급 API 게이트웨이 구현

#### 캐싱 및 로드 밸런싱 기능 추가
```javascript
const express = require('express');
const axios = require('axios');
const Redis = require('ioredis');
const cluster = require('cluster');
const os = require('os');

class AdvancedAPIGateway {
    constructor() {
        this.app = express();
        this.redis = new Redis();
        this.serviceEndpoints = {
            users: ['http://user-service-1:3001', 'http://user-service-2:3001'],
            orders: ['http://order-service-1:3002', 'http://order-service-2:3002'],
            products: ['http://product-service-1:3003', 'http://product-service-2:3003']
        };
        this.currentIndex = {
            users: 0,
            orders: 0,
            products: 0
        };
        
        this.setupMiddleware();
        this.setupRoutes();
    }

    // 미들웨어 설정
    setupMiddleware() {
        this.app.use(express.json());
        this.app.use(this.corsMiddleware());
        this.app.use(this.loggingMiddleware());
        this.app.use(this.rateLimitMiddleware());
        this.app.use(this.authenticationMiddleware());
    }

    // CORS 미들웨어
    corsMiddleware() {
        return (req, res, next) => {
            res.header('Access-Control-Allow-Origin', '*');
            res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
            res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
            
            if (req.method === 'OPTIONS') {
                res.sendStatus(200);
            } else {
                next();
            }
        };
    }

    // 로깅 미들웨어
    loggingMiddleware() {
        return (req, res, next) => {
            const start = Date.now();
            
            res.on('finish', () => {
                const duration = Date.now() - start;
                console.log(`${new Date().toISOString()} - ${req.method} ${req.path} - ${res.statusCode} - ${duration}ms`);
            });
            
            next();
        };
    }

    // 속도 제한 미들웨어
    rateLimitMiddleware() {
        const limits = new Map();
        
        return async (req, res, next) => {
            const key = `rate_limit:${req.ip}`;
            const limit = 100; // 1분당 100개 요청
            const window = 60 * 1000; // 1분
            
            try {
                const current = await this.redis.incr(key);
                
                if (current === 1) {
                    await this.redis.expire(key, window / 1000);
                }
                
                if (current > limit) {
                    return res.status(429).json({ error: '요청 한도를 초과했습니다.' });
                }
                
                res.set('X-RateLimit-Limit', limit);
                res.set('X-RateLimit-Remaining', Math.max(0, limit - current));
                
                next();
            } catch (error) {
                console.error('속도 제한 오류:', error);
                next();
            }
        };
    }

    // 인증 미들웨어
    authenticationMiddleware() {
        return async (req, res, next) => {
            const token = req.headers['authorization'];
            
            if (!token) {
                return res.status(401).json({ error: '인증 토큰이 필요합니다.' });
            }
            
            try {
                // Redis에서 토큰 검증
                const userData = await this.redis.get(`token:${token}`);
                
                if (!userData) {
                    return res.status(403).json({ error: '유효하지 않은 토큰입니다.' });
                }
                
                req.user = JSON.parse(userData);
                next();
            } catch (error) {
                console.error('인증 오류:', error);
                res.status(500).json({ error: '인증 처리 중 오류가 발생했습니다.' });
            }
        };
    }

    // 라우트 설정
    setupRoutes() {
        // 동적 라우팅
        this.app.all('/:service/*', async (req, res) => {
            const service = req.params.service;
            const path = req.params[0];
            
            if (!this.serviceEndpoints[service]) {
                return res.status(404).json({ error: '서비스를 찾을 수 없습니다.' });
            }
            
            // 캐싱 확인 (GET 요청만)
            if (req.method === 'GET') {
                const cacheKey = `cache:${service}:${path}`;
                const cached = await this.redis.get(cacheKey);
                
                if (cached) {
                    return res.json(JSON.parse(cached));
                }
            }
            
            // 로드 밸런싱
            const endpoint = this.getNextEndpoint(service);
            const targetUrl = `${endpoint}/${path}`;
            
            try {
                const response = await axios({
                    method: req.method,
                    url: targetUrl,
                    data: req.body,
                    headers: {
                        ...req.headers,
                        'x-forwarded-for': req.ip,
                        'x-user-id': req.user?.id
                    },
                    timeout: 10000
                });
                
                // 캐싱 (GET 요청만)
                if (req.method === 'GET' && response.status === 200) {
                    const cacheKey = `cache:${service}:${path}`;
                    await this.redis.setex(cacheKey, 300, JSON.stringify(response.data)); // 5분 캐시
                }
                
                res.json(response.data);
            } catch (error) {
                console.error(`${service} 서비스 오류:`, error.message);
                res.status(500).json({ error: `${service} 서비스 오류` });
            }
        });

        // 헬스체크
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                uptime: process.uptime(),
                memory: process.memoryUsage(),
                services: Object.keys(this.serviceEndpoints)
            });
        });
    }

    // 로드 밸런싱 - 라운드 로빈
    getNextEndpoint(service) {
        const endpoints = this.serviceEndpoints[service];
        const index = this.currentIndex[service] % endpoints.length;
        this.currentIndex[service] = (this.currentIndex[service] + 1) % endpoints.length;
        return endpoints[index];
    }

    // 서버 시작
    start(port = 3000) {
        this.app.listen(port, () => {
            console.log(`고급 API 게이트웨이가 포트 ${port}에서 실행 중입니다.`);
        });
    }
}

// 클러스터 모드로 실행
if (cluster.isMaster) {
    const numCPUs = os.cpus().length;
    
    console.log(`마스터 프로세스 ${process.pid} 시작`);
    console.log(`${numCPUs}개의 워커 프로세스 생성 중...`);
    
    for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
    }
    
    cluster.on('exit', (worker, code, signal) => {
        console.log(`워커 ${worker.process.pid} 종료됨`);
        cluster.fork();
    });
} else {
    const gateway = new AdvancedAPIGateway();
    gateway.start();
}
```

### 네트워크 게이트웨이 시뮬레이션

#### Node.js로 네트워크 게이트웨이 구현
```javascript
const net = require('net');
const http = require('http');
const https = require('https');

class NetworkGateway {
    constructor() {
        this.routes = new Map();
        this.stats = {
            totalRequests: 0,
            successfulRequests: 0,
            failedRequests: 0,
            startTime: Date.now()
        };
    }

    // 라우팅 규칙 추가
    addRoute(sourcePort, targetHost, targetPort, protocol = 'tcp') {
        this.routes.set(sourcePort, {
            targetHost,
            targetPort,
            protocol
        });
        console.log(`라우팅 규칙 추가: ${sourcePort} -> ${targetHost}:${targetPort} (${protocol})`);
    }

    // TCP 게이트웨이 시작
    startTCPGateway() {
        const server = net.createServer((socket) => {
            this.handleTCPConnection(socket);
        });

        server.listen(8080, () => {
            console.log('TCP 게이트웨이가 포트 8080에서 실행 중입니다.');
        });
    }

    // TCP 연결 처리
    handleTCPConnection(socket) {
        const clientAddress = `${socket.remoteAddress}:${socket.remotePort}`;
        console.log(`새로운 TCP 연결: ${clientAddress}`);

        // 연결 통계 업데이트
        this.stats.totalRequests++;

        // 연결 종료 이벤트
        socket.on('close', () => {
            console.log(`TCP 연결 종료: ${clientAddress}`);
        });

        socket.on('error', (error) => {
            console.error(`TCP 연결 오류: ${clientAddress}`, error.message);
            this.stats.failedRequests++;
        });
    }

    // HTTP 게이트웨이 시작
    startHTTPGateway() {
        const server = http.createServer((req, res) => {
            this.handleHTTPRequest(req, res);
        });

        server.listen(8081, () => {
            console.log('HTTP 게이트웨이가 포트 8081에서 실행 중입니다.');
        });
    }

    // HTTP 요청 처리
    handleHTTPRequest(req, res) {
        const clientAddress = req.socket.remoteAddress;
        console.log(`${new Date().toISOString()} - ${req.method} ${req.url} from ${clientAddress}`);

        this.stats.totalRequests++;

        // 라우팅 규칙 확인
        const route = this.routes.get(req.socket.localPort);
        
        if (route) {
            // 프록시 요청
            this.proxyHTTPRequest(req, res, route);
        } else {
            res.writeHead(404, { 'Content-Type': 'text/plain' });
            res.end('Route not found');
            this.stats.failedRequests++;
        }
    }

    // HTTP 프록시 요청
    proxyHTTPRequest(req, res, route) {
        const options = {
            hostname: route.targetHost,
            port: route.targetPort,
            path: req.url,
            method: req.method,
            headers: req.headers
        };

        const proxyReq = http.request(options, (proxyRes) => {
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res);
            this.stats.successfulRequests++;
        });

        proxyReq.on('error', (error) => {
            console.error('프록시 요청 오류:', error.message);
            res.writeHead(500, { 'Content-Type': 'text/plain' });
            res.end('Proxy error');
            this.stats.failedRequests++;
        });

        req.pipe(proxyReq);
    }

    // 통계 정보 반환
    getStats() {
        const uptime = Date.now() - this.stats.startTime;
        return {
            ...this.stats,
            uptime: Math.floor(uptime / 1000),
            successRate: this.stats.totalRequests > 0 
                ? ((this.stats.successfulRequests / this.stats.totalRequests) * 100).toFixed(2)
                : 0
        };
    }
}

// 사용 예시
const gateway = new NetworkGateway();

// 라우팅 규칙 설정
gateway.addRoute(8080, 'localhost', 3001, 'tcp');
gateway.addRoute(8081, 'localhost', 3002, 'http');

// 게이트웨이 시작
gateway.startTCPGateway();
gateway.startHTTPGateway();

// 통계 모니터링
setInterval(() => {
    const stats = gateway.getStats();
    console.log('게이트웨이 통계:', stats);
}, 30000);
```

## 운영 팁

### 게이트웨이 성능 최적화

#### 성능 모니터링 및 최적화
```javascript
const os = require('os');
const cluster = require('cluster');

class GatewayPerformanceMonitor {
    constructor() {
        this.metrics = {
            requests: 0,
            errors: 0,
            responseTimes: [],
            memoryUsage: [],
            cpuUsage: []
        };
        this.startTime = Date.now();
    }

    // 요청 처리 시간 측정
    measureResponseTime(req, res, next) {
        const start = Date.now();
        
        res.on('finish', () => {
            const duration = Date.now() - start;
            this.metrics.requests++;
            this.metrics.responseTimes.push(duration);
            
            // 최근 1000개 응답 시간만 유지
            if (this.metrics.responseTimes.length > 1000) {
                this.metrics.responseTimes.shift();
            }
            
            if (res.statusCode >= 400) {
                this.metrics.errors++;
            }
        });
        
        next();
    }

    // 시스템 리소스 모니터링
    monitorSystemResources() {
        setInterval(() => {
            const memUsage = process.memoryUsage();
            const cpuUsage = process.cpuUsage();
            
            this.metrics.memoryUsage.push({
                timestamp: Date.now(),
                rss: memUsage.rss,
                heapUsed: memUsage.heapUsed,
                heapTotal: memUsage.heapTotal
            });
            
            this.metrics.cpuUsage.push({
                timestamp: Date.now(),
                user: cpuUsage.user,
                system: cpuUsage.system
            });
            
            // 최근 100개 메트릭만 유지
            if (this.metrics.memoryUsage.length > 100) {
                this.metrics.memoryUsage.shift();
                this.metrics.cpuUsage.shift();
            }
        }, 5000);
    }

    // 성능 리포트 생성
    generateReport() {
        const uptime = Date.now() - this.startTime;
        const avgResponseTime = this.metrics.responseTimes.length > 0
            ? this.metrics.responseTimes.reduce((sum, time) => sum + time, 0) / this.metrics.responseTimes.length
            : 0;
            
        const errorRate = this.metrics.requests > 0
            ? (this.metrics.errors / this.metrics.requests * 100).toFixed(2)
            : 0;
            
        const latestMemory = this.metrics.memoryUsage[this.metrics.memoryUsage.length - 1];
        const latestCPU = this.metrics.cpuUsage[this.metrics.cpuUsage.length - 1];
        
        return {
            uptime: Math.floor(uptime / 1000),
            totalRequests: this.metrics.requests,
            totalErrors: this.metrics.errors,
            errorRate: `${errorRate}%`,
            averageResponseTime: `${avgResponseTime.toFixed(2)}ms`,
            memoryUsage: latestMemory ? {
                rss: `${Math.round(latestMemory.rss / 1024 / 1024)}MB`,
                heapUsed: `${Math.round(latestMemory.heapUsed / 1024 / 1024)}MB`,
                heapTotal: `${Math.round(latestMemory.heapTotal / 1024 / 1024)}MB`
            } : null,
            cpuUsage: latestCPU ? {
                user: `${Math.round(latestCPU.user / 1000)}ms`,
                system: `${Math.round(latestCPU.system / 1000)}ms`
            } : null,
            systemInfo: {
                platform: os.platform(),
                arch: os.arch(),
                cpus: os.cpus().length,
                totalMemory: `${Math.round(os.totalmem() / 1024 / 1024 / 1024)}GB`,
                freeMemory: `${Math.round(os.freemem() / 1024 / 1024 / 1024)}GB`
            }
        };
    }
}

// 사용 예시
const monitor = new GatewayPerformanceMonitor();
monitor.monitorSystemResources();

// 성능 리포트 출력
setInterval(() => {
    const report = monitor.generateReport();
    console.log('성능 리포트:', JSON.stringify(report, null, 2));
}, 30000);
```

### 게이트웨이 보안 강화

#### 보안 미들웨어 구현
```javascript
const crypto = require('crypto');

class GatewaySecurity {
    constructor() {
        this.blockedIPs = new Set();
        this.suspiciousPatterns = [
            /\.\.\//, // 경로 순회 공격
            /<script/i, // XSS 공격
            /union\s+select/i, // SQL 인젝션
            /eval\s*\(/i, // 코드 인젝션
            /document\.cookie/i // 쿠키 탈취
        ];
    }

    // IP 차단 미들웨어
    blockIPMiddleware() {
        return (req, res, next) => {
            const clientIP = req.ip || req.connection.remoteAddress;
            
            if (this.blockedIPs.has(clientIP)) {
                return res.status(403).json({ error: '접근이 차단된 IP입니다.' });
            }
            
            next();
        };
    }

    // 요청 검증 미들웨어
    validateRequestMiddleware() {
        return (req, res, next) => {
            const url = req.url;
            const body = JSON.stringify(req.body);
            
            // 의심스러운 패턴 검사
            for (const pattern of this.suspiciousPatterns) {
                if (pattern.test(url) || pattern.test(body)) {
                    console.warn(`의심스러운 요청 감지: ${req.ip} - ${req.method} ${req.url}`);
                    return res.status(400).json({ error: '잘못된 요청입니다.' });
                }
            }
            
            next();
        };
    }

    // 요청 서명 검증 미들웨어
    verifySignatureMiddleware(secretKey) {
        return (req, res, next) => {
            const signature = req.headers['x-signature'];
            const timestamp = req.headers['x-timestamp'];
            
            if (!signature || !timestamp) {
                return res.status(401).json({ error: '서명이 필요합니다.' });
            }
            
            // 타임스탬프 검증 (5분 이내)
            const now = Date.now();
            const requestTime = parseInt(timestamp);
            
            if (Math.abs(now - requestTime) > 5 * 60 * 1000) {
                return res.status(401).json({ error: '요청 시간이 만료되었습니다.' });
            }
            
            // 서명 검증
            const expectedSignature = this.generateSignature(req.body, timestamp, secretKey);
            
            if (signature !== expectedSignature) {
                return res.status(401).json({ error: '유효하지 않은 서명입니다.' });
            }
            
            next();
        };
    }

    // 서명 생성
    generateSignature(data, timestamp, secretKey) {
        const message = JSON.stringify(data) + timestamp + secretKey;
        return crypto.createHash('sha256').update(message).digest('hex');
    }

    // IP 차단
    blockIP(ip) {
        this.blockedIPs.add(ip);
        console.log(`IP 차단: ${ip}`);
    }

    // IP 차단 해제
    unblockIP(ip) {
        this.blockedIPs.delete(ip);
        console.log(`IP 차단 해제: ${ip}`);
    }
}

// 사용 예시
const security = new GatewaySecurity();

// 보안 미들웨어 적용
app.use(security.blockIPMiddleware());
app.use(security.validateRequestMiddleware());
app.use(security.verifySignatureMiddleware('your-secret-key'));
```

## 참고

### 게이트웨이 도구 및 프레임워크

#### 인기 있는 API 게이트웨이 도구
```javascript
const gatewayTools = {
    'Kong': {
        description: '오픈소스 API 게이트웨이',
        features: ['인증', '로드 밸런싱', '모니터링', '플러그인'],
        language: 'Lua',
        database: 'PostgreSQL'
    },
    'AWS API Gateway': {
        description: 'AWS 관리형 API 게이트웨이',
        features: ['서버리스', '자동 스케일링', 'AWS 통합'],
        language: 'JavaScript',
        database: 'DynamoDB'
    },
    'Zuul': {
        description: 'Netflix 오픈소스 게이트웨이',
        features: ['동적 라우팅', '필터링', '모니터링'],
        language: 'Java',
        database: 'Eureka'
    },
    'Express Gateway': {
        description: 'Node.js 기반 API 게이트웨이',
        features: ['플러그인', 'REST API', '웹 대시보드'],
        language: 'JavaScript',
        database: 'Redis'
    }
};
```

### 결론
게이트웨이는 네트워크와 시스템 간의 중요한 연결점 역할을 합니다.
API 게이트웨이는 마이크로서비스 아키텍처에서 중앙집중식 관리와 보안을 제공합니다.
적절한 게이트웨이 설정으로 성능 최적화와 보안 강화를 동시에 달성할 수 있습니다.
모니터링과 로깅을 통해 게이트웨이의 상태를 지속적으로 관리할 수 있습니다.
게이트웨이는 확장 가능한 시스템 구축에 필수적인 구성 요소입니다.

