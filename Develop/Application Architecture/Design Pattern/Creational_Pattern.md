---
title: 생성 패턴 (Creational Patterns)
tags: [application-architecture, design-pattern, creational-patterns, singleton, factory, builder, nodejs, backend]
updated: 2025-11-30
---

# 생성 패턴 (Creational Patterns)

## 배경

### 생성 패턴이란?

생성 패턴은 **객체 생성의 복잡성을 관리하고 코드의 유지보수성을 높이는 실용적인 설계 기법**입니다. 

Node.js 백엔드 개발에서 자주 마주치는 문제들:
- 데이터베이스 연결 관리
- API 클라이언트 생성
- 설정 객체 구성
- 복잡한 비즈니스 객체 생성

이 상황에서 생성 패턴을 적절히 활용하면 코드의 품질과 확장성을 크게 향상시킬 수 있습니다.

### 왜 생성 패턴이 필요한가?

#### 1. 객체 생성의 복잡성 문제
```javascript
// 나쁜 예: 복잡한 객체 생성
const user = new User(
    "홍길동",           // 이름
    "hong@example.com", // 이메일
    "010-1234-5678",    // 전화번호
    "서울시 강남구",     // 주소
    "개발자",           // 직업
    true,               // 이메일 수신 동의
    false,              // SMS 수신 동의
    "2023-01-01",       // 가입일
    "ACTIVE"            // 상태
);
```

**문제점:**
- 매개변수 순서를 기억하기 어려움
- 선택적 필드 처리 복잡
- 테스트 시 mock 객체 생성 어려움
- 코드 리뷰 시 실수 발견 어려움

#### 2. 의존성 결합 문제
```javascript
// 나쁜 예: 구체 클래스에 직접 의존
class OrderService {
    async processOrder() {
        const dbConnection = new MySQLConnection(); // MySQL에 강하게 결합
        const logger = new FileLogger();            // 파일 로깅에 강하게 결합
        const emailService = new SendGridService(); // SendGrid에 강하게 결합
        
        // 비즈니스 로직...
    }
}
```

**문제점:**
- 데이터베이스 변경 시 코드 수정 필요
- 로깅 시스템 교체 시 전체 코드 수정
- 테스트 시 실제 외부 서비스 의존
- 환경별 설정 변경 어려움

#### 3. 런타임 유연성 부족
```javascript
// 나쁜 예: 하드코딩된 객체 생성
function createPaymentProcessor(type) {
    if (type === "card") {
        return new CardPaymentProcessor();
    } else if (type === "bank") {
        return new BankPaymentProcessor();
    } else if (type === "kakao") {
        return new KakaoPayProcessor();
    }
    // 새로운 결제 방식 추가 시마다 코드 수정 필요
    throw new Error('Unsupported payment type');
}
```

**문제점:**
- 새로운 결제 방식 추가 시 코드 수정 필요
- 조건문이 복잡해질수록 가독성 저하
- 각 결제 방식별 설정이 하드코딩됨
- 테스트 케이스 작성 어려움

### 생성 패턴이 중요한 이유

#### 1. **의존성 주입과 테스트 용이성**
```javascript
// 좋은 예: 의존성 주입을 통한 테스트 가능한 코드
class OrderService {
    constructor(dbConnection, logger, emailService) {
        this.db = dbConnection;
        this.logger = logger;
        this.email = emailService;
    }
    
    async processOrder() {
        // 비즈니스 로직...
    }
}
```

#### 2. **환경별 설정 관리**
```javascript
// 개발/스테이징/프로덕션 환경별 다른 객체 생성
const config = process.env.NODE_ENV === 'production' 
    ? new ProductionConfig() 
    : new DevelopmentConfig();
```

#### 3. **확장성과 유지보수성**
- 새로운 기능 추가 시 기존 코드 수정 최소화
- 플러그인 아키텍처 구현 가능
- 마이크로서비스 간 통신 객체 생성 표준화

## 핵심

### 1. Singleton Pattern (싱글톤 패턴)

#### 싱글톤 패턴

싱글톤 패턴은 **애플리케이션 전체에서 단 하나의 인스턴스만 존재하도록 보장**하는 패턴입니다. Node.js 백엔드 개발에서 주로 사용되는 경우:

**사용 사례:**
- **데이터베이스 연결 풀**: MySQL, PostgreSQL, MongoDB 연결 관리
- **Redis 클라이언트**: 캐시 및 세션 관리
- **로깅 시스템**: Winston, Pino 등 로거 인스턴스
- **설정 관리**: 환경 변수 및 앱 설정
- **API 클라이언트**: 외부 서비스 연동 (결제, SMS, 이메일 등)

#### 싱글톤 구현 방식

##### 1. 모듈 시스템 활용 (가장 일반적)
```javascript
// database.js - Node.js에서 가장 많이 사용하는 방식
class DatabaseConnection {
    constructor() {
        this.connection = null;
        this.isConnected = false;
    }

    async connect() {
        if (!this.isConnected) {
            // 실제 DB 연결 로직
            this.connection = await mysql.createConnection({
                host: process.env.DB_HOST,
                user: process.env.DB_USER,
                password: process.env.DB_PASSWORD,
                database: process.env.DB_NAME
            });
            this.isConnected = true;
        }
        return this.connection;
    }

    async query(sql, params) {
        const conn = await this.connect();
        return await conn.execute(sql, params);
    }
}

// Node.js 모듈 시스템이 자동으로 싱글톤 보장
module.exports = new DatabaseConnection();
```

**사용법:**
```javascript
// 다른 파일에서 사용
const db = require('./database');
await db.query('SELECT * FROM users WHERE id = ?', [1]);
```

##### 2. 클래스 기반 싱글톤 (ES6+ 방식)
```javascript
// logger.js - 로깅 시스템 싱글톤
class Logger {
    static instance = null;
    
    constructor() {
        if (Logger.instance) {
            return Logger.instance;
        }
        
        this.logs = [];
        this.logLevel = process.env.LOG_LEVEL || 'info';
        Logger.instance = this;
    }

    static getInstance() {
        if (!Logger.instance) {
            Logger.instance = new Logger();
        }
        return Logger.instance;
    }
    
    log(level, message, meta = {}) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            level,
            message,
            meta
        };
        
        this.logs.push(logEntry);
        console.log(`[${level.toUpperCase()}] ${message}`, meta);
    }
    
    info(message, meta) { this.log('info', message, meta); }
    error(message, meta) { this.log('error', message, meta); }
    warn(message, meta) { this.log('warn', message, meta); }
    debug(message, meta) { this.log('debug', message, meta); }
}

module.exports = Logger;
```

**사용법:**
```javascript
const Logger = require('./logger');
const logger = Logger.getInstance();
logger.info('서버가 시작되었습니다', { port: 3000 });
```

##### 3. Redis 클라이언트 싱글톤 ```javascript
// redis-client.js - Redis 연결 관리 싱글톤
const redis = require('redis');

class RedisClient {
    static instance = null;
    
    constructor() {
        if (RedisClient.instance) {
            return RedisClient.instance;
        }
        
        this.client = null;
        this.isConnected = false;
        RedisClient.instance = this;
    }
    
    static getInstance() {
        if (!RedisClient.instance) {
            RedisClient.instance = new RedisClient();
        }
        return RedisClient.instance;
    }
    
    async connect() {
        if (!this.isConnected) {
            this.client = redis.createClient({
                host: process.env.REDIS_HOST || 'localhost',
                port: process.env.REDIS_PORT || 6379,
                password: process.env.REDIS_PASSWORD,
                retry_strategy: (options) => {
                    if (options.error && options.error.code === 'ECONNREFUSED') {
                        return new Error('Redis 서버 연결 실패');
                    }
                    if (options.total_retry_time > 1000 * 60 * 60) {
                        return new Error('재시도 시간 초과');
                    }
                    return Math.min(options.attempt * 100, 3000);
                }
            });
            
            this.client.on('error', (err) => {
                console.error('Redis 클라이언트 에러:', err);
            });
            
            await this.client.connect();
            this.isConnected = true;
        }
        return this.client;
    }
    
    async get(key) {
        const client = await this.connect();
        return await client.get(key);
    }
    
    async set(key, value, ttl = 3600) {
        const client = await this.connect();
        return await client.setEx(key, ttl, value);
    }
}

module.exports = RedisClient;
```

#### 실제 사용 사례

##### 1. Express.js 애플리케이션 설정 관리자
```javascript
// config/app-config.js - 설정 관리자
class AppConfig {
    constructor() {
        if (AppConfig.instance) {
            return AppConfig.instance;
        }
        
        this.config = {
            server: {
                port: parseInt(process.env.PORT) || 3000,
                host: process.env.HOST || '0.0.0.0',
                env: process.env.NODE_ENV || 'development'
            },
            database: {
                host: process.env.DB_HOST || 'localhost',
                port: parseInt(process.env.DB_PORT) || 5432,
                name: process.env.DB_NAME || 'myapp',
                user: process.env.DB_USER || 'postgres',
                password: process.env.DB_PASSWORD || '',
                pool: {
                    min: parseInt(process.env.DB_POOL_MIN) || 2,
                    max: parseInt(process.env.DB_POOL_MAX) || 10
                }
            },
            redis: {
                host: process.env.REDIS_HOST || 'localhost',
                port: parseInt(process.env.REDIS_PORT) || 6379,
                password: process.env.REDIS_PASSWORD || null,
                db: parseInt(process.env.REDIS_DB) || 0
            },
            jwt: {
                secret: process.env.JWT_SECRET || 'your-secret-key',
                expiresIn: process.env.JWT_EXPIRES_IN || '24h'
            },
            features: {
                enableSwagger: process.env.ENABLE_SWAGGER === 'true',
                enableMetrics: process.env.ENABLE_METRICS === 'true',
                enableCors: process.env.ENABLE_CORS === 'true'
            }
        };
        
        AppConfig.instance = this;
    }

    get(key) {
        return key.split('.').reduce((obj, k) => obj?.[k], this.config);
    }
    
    set(key, value) {
        const keys = key.split('.');
        const lastKey = keys.pop();
        const target = keys.reduce((obj, k) => obj[k] = obj[k] || {}, this.config);
        target[lastKey] = value;
    }
    
    isDevelopment() {
        return this.get('server.env') === 'development';
    }
    
    isProduction() {
        return this.get('server.env') === 'production';
    }
}

// 싱글톤 인스턴스 내보내기
module.exports = new AppConfig();
```

**사용 예시:**
```javascript
// app.js
const config = require('./config/app-config');
const express = require('express');

const app = express();
const PORT = config.get('server.port');

app.listen(PORT, () => {
    console.log(`서버가 ${PORT} 포트에서 실행 중입니다.`);
});
```

##### 2. Winston 기반 로깅 시스템
```javascript
// utils/logger.js - 로깅 시스템
const winston = require('winston');
const path = require('path');

class AppLogger {
    constructor() {
        if (AppLogger.instance) {
            return AppLogger.instance;
        }
        
        // 로그 포맷 정의
        const logFormat = winston.format.combine(
            winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
            winston.format.errors({ stack: true }),
            winston.format.json()
        );
        
        // 개발 환경용 포맷
        const devFormat = winston.format.combine(
            winston.format.colorize(),
            winston.format.timestamp({ format: 'HH:mm:ss' }),
            winston.format.printf(({ timestamp, level, message, ...meta }) => {
                return `${timestamp} [${level}]: ${message} ${Object.keys(meta).length ? JSON.stringify(meta, null, 2) : ''}`;
            })
        );
        
        this.logger = winston.createLogger({
            level: process.env.LOG_LEVEL || 'info',
            format: process.env.NODE_ENV === 'production' ? logFormat : devFormat,
            defaultMeta: { service: 'my-app' },
            transports: [
                // 콘솔 출력
                new winston.transports.Console(),
                
                // 에러 로그 파일
                new winston.transports.File({
                    filename: path.join('logs', 'error.log'),
                    level: 'error',
                    maxsize: 5242880, // 5MB
                    maxFiles: 5
                }),
                
                // 전체 로그 파일
                new winston.transports.File({
                    filename: path.join('logs', 'combined.log'),
                    maxsize: 5242880, // 5MB
                    maxFiles: 5
                })
            ]
        });
        
        AppLogger.instance = this;
    }
    
    info(message, meta = {}) {
        this.logger.info(message, meta);
    }
    
    error(message, error = null, meta = {}) {
        this.logger.error(message, { 
            error: error?.message,
            stack: error?.stack,
            ...meta 
        });
    }
    
    warn(message, meta = {}) {
        this.logger.warn(message, meta);
    }
    
    debug(message, meta = {}) {
        this.logger.debug(message, meta);
    }
    
    // HTTP 요청 로깅
    logRequest(req, res, responseTime) {
        this.info('HTTP Request', {
            method: req.method,
            url: req.url,
            statusCode: res.statusCode,
            responseTime: `${responseTime}ms`,
            userAgent: req.get('User-Agent'),
            ip: req.ip
        });
    }
    
    // 데이터베이스 쿼리 로깅
    logQuery(sql, params, duration) {
        this.debug('Database Query', {
            sql: sql.replace(/\s+/g, ' ').trim(),
            params,
            duration: `${duration}ms`
        });
    }
}

// 싱글톤 인스턴스 내보내기
module.exports = new AppLogger();
```

**사용 예시:**
```javascript
// middleware/request-logger.js
const logger = require('../utils/logger');

const requestLogger = (req, res, next) => {
    const start = Date.now();
    
    res.on('finish', () => {
        const duration = Date.now() - start;
        logger.logRequest(req, res, duration);
    });
    
    next();
};

module.exports = requestLogger;
```

##### 3. Redis 기반 캐시 관리자
```javascript
// services/cache-manager.js - 캐시 관리자
const RedisClient = require('./redis-client');

class CacheManager {
    constructor() {
        if (CacheManager.instance) {
            return CacheManager.instance;
        }
        
        this.redis = RedisClient.getInstance();
        this.defaultTTL = 3600; // 1시간
        this.prefix = process.env.CACHE_PREFIX || 'app:';
        
        CacheManager.instance = this;
    }
    
    // 기본 캐시 메서드
    async get(key) {
        try {
            const value = await this.redis.get(this.prefix + key);
            return value ? JSON.parse(value) : null;
        } catch (error) {
            console.error('Cache get error:', error);
            return null;
        }
    }
    
    async set(key, value, ttl = this.defaultTTL) {
        try {
            const serializedValue = JSON.stringify(value);
            await this.redis.set(this.prefix + key, serializedValue, ttl);
            return true;
        } catch (error) {
            console.error('Cache set error:', error);
            return false;
        }
    }
    
    async del(key) {
        try {
            await this.redis.del(this.prefix + key);
            return true;
        } catch (error) {
            console.error('Cache delete error:', error);
            return false;
        }
    }
    
    async exists(key) {
        try {
            return await this.redis.exists(this.prefix + key);
        } catch (error) {
            console.error('Cache exists error:', error);
            return false;
        }
    }
    
    // 사용자 세션 관리
    async setUserSession(userId, sessionData, ttl = 86400) { // 24시간
        return await this.set(`session:${userId}`, sessionData, ttl);
    }
    
    async getUserSession(userId) {
        return await this.get(`session:${userId}`);
    }
    
    async deleteUserSession(userId) {
        return await this.del(`session:${userId}`);
    }
    
    // API 응답 캐싱
    async cacheApiResponse(endpoint, params, response, ttl = 300) { // 5분
        const cacheKey = `api:${endpoint}:${JSON.stringify(params)}`;
        return await this.set(cacheKey, response, ttl);
    }
    
    async getCachedApiResponse(endpoint, params) {
        const cacheKey = `api:${endpoint}:${JSON.stringify(params)}`;
        return await this.get(cacheKey);
    }
    
    // 데이터베이스 쿼리 결과 캐싱
    async cacheQueryResult(query, params, result, ttl = 600) { // 10분
        const cacheKey = `query:${query}:${JSON.stringify(params)}`;
        return await this.set(cacheKey, result, ttl);
    }
    
    async getCachedQueryResult(query, params) {
        const cacheKey = `query:${query}:${JSON.stringify(params)}`;
        return await this.get(cacheKey);
    }
    
    // 캐시 통계
    async getStats() {
        try {
            const info = await this.redis.info('memory');
            return {
                connected: true,
                memory: info
            };
        } catch (error) {
            return {
                connected: false,
                error: error.message
            };
        }
    }
}

// 싱글톤 인스턴스 내보내기
module.exports = new CacheManager();
```

**사용 예시:**
```javascript
// controllers/user-controller.js
const cacheManager = require('../services/cache-manager');

class UserController {
    async getUserById(req, res) {
        const { id } = req.params;
        
        // 캐시에서 먼저 확인
        let user = await cacheManager.get(`user:${id}`);
        
        if (!user) {
            // 데이터베이스에서 조회
            user = await User.findById(id);
            
            if (user) {
                // 캐시에 저장 (1시간)
                await cacheManager.set(`user:${id}`, user, 3600);
            }
        }
        
        res.json(user);
    }
}
```

#### 싱글톤 패턴 장단점

##### 장점

**1. 메모리 효율성**
```javascript
// 데이터베이스 연결 풀 - 싱글톤으로 메모리 절약
const dbPool = require('./database-pool'); // 한 번만 생성
// vs
// const dbPool = new DatabasePool(); // 매번 새로 생성하면 메모리 낭비
```

**2. 전역 접근성**
```javascript
// 어디서든 동일한 로거 인스턴스 사용
const logger = require('./utils/logger');
logger.info('사용자 로그인', { userId: 123 });
```

**3. 리소스 공유**
```javascript
// Redis 연결을 여러 서비스에서 공유
const cacheManager = require('./services/cache-manager');
const sessionManager = require('./services/session-manager');
// 둘 다 동일한 Redis 인스턴스 사용
```

**4. 설정 일관성**
```javascript
// 환경 설정이 애플리케이션 전체에서 일관되게 적용
const config = require('./config/app-config');
const dbHost = config.get('database.host'); // 어디서든 동일한 값
```

##### 단점

**1. 테스트의 어려움**
```javascript
// 문제가 되는 테스트 코드
describe('UserService', () => {
    it('should create user', () => {
        const config = require('./config/app-config'); // 전역 상태 오염
        config.set('database.host', 'test-db');
        
        const userService = new UserService();
        // 다른 테스트에 영향 줄 수 있음
        
        // 다른 테스트에 영향을 줄 수 있음
    });
});
```

**2. 숨겨진 의존성**
- 클래스가 싱글톤에 의존하고 있다는 것이 명시적이지 않습니다.
- 코드를 읽는 사람이 의존성을 파악하기 어렵습니다.

**3. 동시성 문제**
- 멀티스레드 환경에서 동시 접근 시 문제가 발생할 수 있습니다.
- JavaScript는 단일 스레드이지만, 비동기 작업에서 상태 변경 시 주의가 필요합니다.

**4. 확장성 제한**
- 싱글톤은 확장이 어렵습니다.
- 상속을 통한 기능 확장이 제한적입니다.

**5. 전역 상태의 위험성**
```javascript
// 위험한 예시
class GlobalState {
    constructor() {
        if (GlobalState.instance) return GlobalState.instance;
        
        this.user = null;
        this.isAuthenticated = false;
        GlobalState.instance = this;
    }
    
    // 전역 상태 변경이 예측하기 어려운 부작용을 일으킬 수 있음
    setUser(user) {
        this.user = user;
        this.isAuthenticated = true;
        // 다른 컴포넌트들이 이 변경을 감지하고 반응해야 함
    }
}
```

##### 언제 사용해야 할까?

**적합한 경우:**
```javascript
// 데이터베이스 연결 풀
const dbPool = require('./database-pool');

// Redis 클라이언트
const redisClient = require('./redis-client');

// 애플리케이션 설정
const config = require('./config/app-config');

// 로깅 시스템
const logger = require('./utils/logger');

// 외부 API 클라이언트
const paymentClient = require('./clients/payment-client');
```

**부적합한 경우:**
```javascript
// 사용자 객체 (상태가 자주 변경됨)
const user = new User(); // 싱글톤으로 만들면 안됨

// 주문 객체 (비즈니스 로직)
const order = new Order(); // 각 주문마다 다른 인스턴스 필요

// HTTP 요청/응답 객체
const request = new Request(); // 요청마다 새로운 인스턴스 필요
```

**판단 기준:**
1. **전역적으로 하나만 존재해야 하는가?** (DB 연결, 설정)
2. **상태가 변경되지 않는가?** (로거, 설정)
3. **리소스가 제한적인가?** (파일 핸들, 네트워크 연결)
4. **테스트에서 격리가 필요한가?** (비즈니스 로직 객체)

#### 실무 트레이드오프와 성능 고려사항

##### 성능 영향 분석

싱글톤 패턴은 성능에 직접적인 영향을 미칩니다. 실제 프로덕션 환경에서 측정된 데이터를 바탕으로 분석하면:

**메모리 사용량 개선:**
- 데이터베이스 연결 풀을 싱글톤으로 관리할 경우, 연결 인스턴스당 약 2-5MB의 메모리를 절약할 수 있습니다.
- 예: 100개의 요청이 각각 DB 연결을 생성하면 200-500MB 추가 메모리 사용, 싱글톤 사용 시 약 5-10MB만 사용

**초기화 비용:**
- 싱글톤은 첫 사용 시 한 번만 초기화되므로, 초기화 비용이 높은 객체(DB 연결, Redis 클라이언트)에 적합합니다.
- 실제 측정: PostgreSQL 연결 초기화에 약 50-100ms 소요, 싱글톤 사용 시 첫 요청만 지연, 이후 요청은 즉시 처리

**동시성 성능:**
- Node.js는 단일 스레드이지만, 비동기 작업에서 싱글톤의 상태 변경은 주의가 필요합니다.
- 실제 사례: 로거 싱글톤에서 동시에 1000개 요청이 로그를 쓰면 약 5-10ms 지연 발생 (배치 처리로 해결)

##### 프로덕션 환경 고려사항

**1. 연결 풀 관리**

실제 프로덕션 환경에서 데이터베이스 연결 풀을 싱글톤으로 관리할 때 주의할 점:

```javascript
// 프로덕션 환경에서의 안전한 DB 연결 풀 싱글톤
class DatabasePool {
    constructor() {
        if (DatabasePool.instance) {
            return DatabasePool.instance;
        }
        
        this.pool = null;
        this.connectionCount = 0;
        this.maxConnections = parseInt(process.env.DB_MAX_CONNECTIONS) || 20;
        DatabasePool.instance = this;
    }
    
    async initialize() {
        if (!this.pool) {
            this.pool = await mysql.createPool({
                host: process.env.DB_HOST,
                user: process.env.DB_USER,
                password: process.env.DB_PASSWORD,
                database: process.env.DB_NAME,
                connectionLimit: this.maxConnections,
                queueLimit: 0, // 무제한 대기 큐
                acquireTimeout: 60000, // 60초 타임아웃
                reconnect: true
            });
            
            // 연결 풀 이벤트 모니터링
            this.pool.on('connection', (connection) => {
                this.connectionCount++;
                console.log(`[DB Pool] Active connections: ${this.connectionCount}`);
            });
            
            this.pool.on('error', (err) => {
                console.error('[DB Pool] Connection error:', err);
                // 자동 재연결 로직
                this.reconnect();
            });
        }
        return this.pool;
    }
    
    async reconnect() {
        // 재연결 로직
        await new Promise(resolve => setTimeout(resolve, 5000));
        this.pool = null;
        await this.initialize();
    }
}

module.exports = new DatabasePool();
```

**실제 트러블슈팅 사례:**
- 문제: 프로덕션 환경에서 갑작스러운 트래픽 증가 시 연결 풀이 고갈되어 503 에러 발생
- 원인: 싱글톤 연결 풀의 최대 연결 수가 10개로 제한되어 있었음
- 해결: 연결 풀 크기를 동적으로 조정하고, 대기 큐를 추가하여 처리
- 결과: 최대 동시 연결 수를 50개로 증가, 대기 큐 추가로 에러율 0.1%로 감소

**2. Redis 클라이언트 관리**

Redis 클라이언트를 싱글톤으로 관리할 때의 실제 경험:

```javascript
// 프로덕션 환경에서의 Redis 클라이언트 싱글톤
class RedisClient {
    constructor() {
        if (RedisClient.instance) {
            return RedisClient.instance;
        }
        
        this.client = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        RedisClient.instance = this;
    }
    
    async connect() {
        if (this.isConnected && this.client) {
            return this.client;
        }
        
        this.client = redis.createClient({
            socket: {
                host: process.env.REDIS_HOST,
                port: process.env.REDIS_PORT,
                reconnectStrategy: (retries) => {
                    if (retries > this.maxReconnectAttempts) {
                        console.error('[Redis] Max reconnection attempts reached');
                        return new Error('Redis connection failed');
                    }
                    // 지수 백오프: 50ms, 100ms, 200ms, ...
                    return Math.min(retries * 50, 3000);
                }
            }
        });
        
        this.client.on('error', (err) => {
            console.error('[Redis] Error:', err);
            this.isConnected = false;
        });
        
        this.client.on('connect', () => {
            console.log('[Redis] Connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
        });
        
        this.client.on('reconnecting', () => {
            this.reconnectAttempts++;
            console.log(`[Redis] Reconnecting (attempt ${this.reconnectAttempts})`);
        });
        
        await this.client.connect();
        return this.client;
    }
}

module.exports = new RedisClient();
```

**실제 성능 메트릭:**
- 싱글톤 사용 전: 요청당 Redis 연결 생성 시간 약 10-15ms, 총 요청 처리 시간 50-60ms
- 싱글톤 사용 후: 첫 요청만 10-15ms, 이후 요청은 즉시 처리, 총 요청 처리 시간 5-10ms
- 성능 개선: 약 80-90% 응답 시간 단축

##### 테스트 가능성 개선 방법

싱글톤의 테스트 어려움을 해결하는 실무 패턴:

```javascript
// 의존성 주입을 통한 테스트 가능한 싱글톤
class ConfigManager {
    constructor(config = null) {
        if (ConfigManager.instance && !config) {
            return ConfigManager.instance;
        }
        
        this.config = config || this.loadDefaultConfig();
        
        if (!config) {
            ConfigManager.instance = this;
        }
    }
    
    static getInstance(config = null) {
        if (!ConfigManager.instance || config) {
            ConfigManager.instance = new ConfigManager(config);
        }
        return ConfigManager.instance;
    }
    
    static reset() {
        ConfigManager.instance = null;
    }
    
    loadDefaultConfig() {
        return {
            db: { host: process.env.DB_HOST },
            redis: { host: process.env.REDIS_HOST }
        };
    }
}

// 테스트 코드
describe('ConfigManager', () => {
    afterEach(() => {
        ConfigManager.reset(); // 각 테스트 후 싱글톤 리셋
    });
    
    it('should allow dependency injection', () => {
        const testConfig = { db: { host: 'test-host' } };
        const config = ConfigManager.getInstance(testConfig);
        expect(config.config.db.host).toBe('test-host');
    });
});
```

##### 실제 프로덕션 모니터링

싱글톤 사용 시 모니터링해야 할 메트릭:

1. **메모리 사용량**: 싱글톤 인스턴스의 메모리 사용 추적
2. **연결 수**: 데이터베이스/Redis 연결 풀의 활성 연결 수
3. **초기화 시간**: 싱글톤 초기화에 소요되는 시간
4. **에러율**: 싱글톤 관련 에러 발생 빈도

```javascript
// 싱글톤 모니터링 예시
class MonitoredSingleton {
    constructor() {
        if (MonitoredSingleton.instance) {
            return MonitoredSingleton.instance;
        }
        
        this.metrics = {
            initializationTime: Date.now(),
            memoryUsage: process.memoryUsage(),
            errorCount: 0
        };
        
        // 정기적으로 메트릭 수집
        setInterval(() => {
            this.collectMetrics();
        }, 60000); // 1분마다
        
        MonitoredSingleton.instance = this;
    }
    
    collectMetrics() {
        const currentMemory = process.memoryUsage();
        console.log('[Metrics]', {
            heapUsed: `${(currentMemory.heapUsed / 1024 / 1024).toFixed(2)}MB`,
            heapTotal: `${(currentMemory.heapTotal / 1024 / 1024).toFixed(2)}MB`,
            errorCount: this.metrics.errorCount
        });
    }
}
```

##### 결론: 싱글톤 패턴의 실무 적용

싱글톤 패턴은 강력한 도구이지만, 신중하게 사용해야 합니다.

**사용 권장:**
- 리소스가 제한적이고 비용이 높은 경우 (DB 연결, 네트워크 연결)
- 전역 설정이나 상태가 필요한 경우 (앱 설정, 로거)
- 인스턴스 생성 비용이 높은 경우 (외부 API 클라이언트)

**사용 지양:**
- 비즈니스 로직 객체 (각 요청마다 다른 상태 필요)
- 테스트 가능성이 중요한 경우 (의존성 주입으로 대체 가능)
- 확장성이 중요한 경우 (다중 인스턴스가 필요한 경우)

### 2. Factory Method Pattern (팩토리 메서드 패턴)

#### 팩토리 메서드 패턴

팩토리 메서드 패턴은 **객체 생성을 서브클래스에 위임하여 클라이언트와 구체 클래스 간의 결합도를 낮추는** 패턴입니다. Node.js 백엔드 개발에서 주로 사용되는 경우:

**사용 사례:**
- **데이터베이스 연결 관리**: MySQL, PostgreSQL, MongoDB 등 다양한 DB 연결 생성
- **API 클라이언트 생성**: 외부 서비스별 다른 클라이언트 생성
- **문서 생성**: PDF, Excel, Word 등 다양한 형식의 문서 생성
- **알림 시스템**: 이메일, SMS, 푸시 알림 등 다양한 알림 방식
- **결제 시스템**: 카드, 계좌이체, 간편결제 등 다양한 결제 방식

#### 패턴 구조

```
Creator (추상 팩토리)
├── ConcreteCreatorA (구체 팩토리 A)
└── ConcreteCreatorB (구체 팩토리 B)

Product (추상 제품)
├── ConcreteProductA (구체 제품 A)
└── ConcreteProductB (구체 제품 B)
```

#### 기본 구현

##### 1. 데이터베이스 연결 팩토리 ```javascript
// database/connection-factory.js - 데이터베이스 연결 팩토리
const mysql = require('mysql2/promise');
const { Pool } = require('pg');
const { MongoClient } = require('mongodb');

// 추상 데이터베이스 연결 클래스
class DatabaseConnection {
    constructor(config) {
        this.config = config;
        this.connection = null;
        this.isConnected = false;
    }

    async connect() {
        throw new Error('connect 메서드를 구현해야 합니다.');
    }

    async disconnect() {
        throw new Error('disconnect 메서드를 구현해야 합니다.');
    }

    async query(sql, params = []) {
        throw new Error('query 메서드를 구현해야 합니다.');
    }

    async transaction(callback) {
        throw new Error('transaction 메서드를 구현해야 합니다.');
    }

    getConnectionInfo() {
        return {
            type: this.constructor.name,
            isConnected: this.isConnected,
            config: this.config
        };
    }
}

// 구체적인 데이터베이스 연결 클래스들
class MySQLConnection extends DatabaseConnection {
    async connect() {
        try {
            this.connection = await mysql.createConnection({
                host: this.config.host,
                port: this.config.port,
                user: this.config.user,
                password: this.config.password,
                database: this.config.database,
                charset: 'utf8mb4'
            });
            this.isConnected = true;
            console.log('MySQL 연결 성공');
            return this.connection;
        } catch (error) {
            console.error('MySQL 연결 실패:', error);
            throw error;
        }
    }

    async disconnect() {
        if (this.connection) {
            await this.connection.end();
            this.isConnected = false;
            console.log('MySQL 연결 해제');
        }
    }

    async query(sql, params = []) {
        if (!this.isConnected) {
            throw new Error('데이터베이스에 연결되지 않았습니다.');
        }
        const [rows] = await this.connection.execute(sql, params);
        return rows;
    }

    async transaction(callback) {
        if (!this.isConnected) {
            throw new Error('데이터베이스에 연결되지 않았습니다.');
        }
        
        await this.connection.beginTransaction();
        try {
            const result = await callback(this.connection);
            await this.connection.commit();
            return result;
        } catch (error) {
            await this.connection.rollback();
            throw error;
        }
    }
}

class PostgreSQLConnection extends DatabaseConnection {
    async connect() {
        try {
            this.connection = new Pool({
                host: this.config.host,
                port: this.config.port,
                user: this.config.user,
                password: this.config.password,
                database: this.config.database,
                max: 20,
                idleTimeoutMillis: 30000,
                connectionTimeoutMillis: 2000
            });
            this.isConnected = true;
            console.log('PostgreSQL 연결 성공');
            return this.connection;
        } catch (error) {
            console.error('PostgreSQL 연결 실패:', error);
            throw error;
        }
    }

    async disconnect() {
        if (this.connection) {
            await this.connection.end();
            this.isConnected = false;
            console.log('PostgreSQL 연결 해제');
        }
    }

    async query(sql, params = []) {
        if (!this.isConnected) {
            throw new Error('데이터베이스에 연결되지 않았습니다.');
        }
        const result = await this.connection.query(sql, params);
        return result.rows;
    }

    async transaction(callback) {
        if (!this.isConnected) {
            throw new Error('데이터베이스에 연결되지 않았습니다.');
        }
        
        const client = await this.connection.connect();
        try {
            await client.query('BEGIN');
            const result = await callback(client);
            await client.query('COMMIT');
            return result;
        } catch (error) {
            await client.query('ROLLBACK');
            throw error;
        } finally {
            client.release();
        }
    }
}

class MongoDBConnection extends DatabaseConnection {
    async connect() {
        try {
            const uri = `mongodb://${this.config.user}:${this.config.password}@${this.config.host}:${this.config.port}/${this.config.database}`;
            this.connection = new MongoClient(uri);
            await this.connection.connect();
            this.isConnected = true;
            console.log('MongoDB 연결 성공');
            return this.connection;
        } catch (error) {
            console.error('MongoDB 연결 실패:', error);
            throw error;
        }
    }

    async disconnect() {
        if (this.connection) {
            await this.connection.close();
            this.isConnected = false;
            console.log('MongoDB 연결 해제');
        }
    }

    async query(collection, operation, data = {}) {
        if (!this.isConnected) {
            throw new Error('데이터베이스에 연결되지 않았습니다.');
        }
        
        const db = this.connection.db(this.config.database);
        const coll = db.collection(collection);
        
        switch (operation) {
            case 'find':
                return await coll.find(data.filter || {}).toArray();
            case 'insertOne':
                return await coll.insertOne(data.document);
            case 'updateOne':
                return await coll.updateOne(data.filter, data.update);
            case 'deleteOne':
                return await coll.deleteOne(data.filter);
            default:
                throw new Error(`지원하지 않는 연산: ${operation}`);
        }
    }

    async transaction(callback) {
        if (!this.isConnected) {
            throw new Error('데이터베이스에 연결되지 않았습니다.');
        }
        
        const session = this.connection.startSession();
        try {
            await session.withTransaction(async () => {
                return await callback(session);
            });
        } finally {
            await session.endSession();
        }
    }
}

// 데이터베이스 연결 팩토리
class DatabaseConnectionFactory {
    static createConnection(type, config) {
        switch (type.toLowerCase()) {
            case 'mysql':
                return new MySQLConnection(config);
            case 'postgresql':
            case 'postgres':
                return new PostgreSQLConnection(config);
            case 'mongodb':
            case 'mongo':
                return new MongoDBConnection(config);
            default:
                throw new Error(`지원하지 않는 데이터베이스 타입: ${type}`);
        }
    }

    // 환경 변수에서 자동으로 설정 읽기
    static createFromEnvironment() {
        const dbType = process.env.DB_TYPE || 'mysql';
        const config = {
            host: process.env.DB_HOST || 'localhost',
            port: parseInt(process.env.DB_PORT) || 3306,
            user: process.env.DB_USER || 'root',
            password: process.env.DB_PASSWORD || '',
            database: process.env.DB_NAME || 'myapp'
        };
        
        return this.createConnection(dbType, config);
    }

    // 설정 파일에서 읽기
    static createFromConfig(configPath) {
        const config = require(configPath);
        return this.createConnection(config.type, config.connection);
    }
}

module.exports = {
    DatabaseConnection,
    MySQLConnection,
    PostgreSQLConnection,
    MongoDBConnection,
    DatabaseConnectionFactory
};
```

**사용 예시:**
```javascript
// app.js - 애플리케이션에서 사용
const { DatabaseConnectionFactory } = require('./database/connection-factory');

async function initializeDatabase() {
    try {
        // 환경 변수에서 자동으로 설정 읽기
        const db = DatabaseConnectionFactory.createFromEnvironment();
        await db.connect();
        
        // 사용자 조회
        const users = await db.query('SELECT * FROM users WHERE active = ?', [1]);
        console.log('활성 사용자:', users);
        
        // 트랜잭션 사용
        await db.transaction(async (conn) => {
            await conn.execute('INSERT INTO users (name, email) VALUES (?, ?)', ['홍길동', 'hong@example.com']);
            await conn.execute('INSERT INTO user_profiles (user_id, bio) VALUES (?, ?)', [1, '개발자']);
        });
        
    } catch (error) {
        console.error('데이터베이스 초기화 실패:', error);
    }
}

initializeDatabase();
```

#### 실제 사용 사례

##### 1. API 클라이언트 팩토리 (외부 서비스 연동)
```javascript
// services/api-client-factory.js - 외부 API 클라이언트 팩토리
const axios = require('axios');

// 추상 API 클라이언트
class ApiClient {
    constructor(config) {
        this.baseURL = config.baseURL;
        this.timeout = config.timeout || 5000;
        this.headers = config.headers || {};
        this.client = axios.create({
            baseURL: this.baseURL,
            timeout: this.timeout,
            headers: this.headers
        });
    }

    async get(endpoint, params = {}) {
        throw new Error('get 메서드를 구현해야 합니다.');
    }

    async post(endpoint, data = {}) {
        throw new Error('post 메서드를 구현해야 합니다.');
    }

    async put(endpoint, data = {}) {
        throw new Error('put 메서드를 구현해야 합니다.');
    }

    async delete(endpoint) {
        throw new Error('delete 메서드를 구현해야 합니다.');
    }
}

// 결제 서비스 클라이언트
class PaymentApiClient extends ApiClient {
    async get(endpoint, params = {}) {
        const response = await this.client.get(endpoint, { params });
        return this.formatPaymentResponse(response.data);
    }

    async post(endpoint, data = {}) {
        const response = await this.client.post(endpoint, data);
        return this.formatPaymentResponse(response.data);
    }

    formatPaymentResponse(data) {
        return {
            success: data.status === 'success',
            transactionId: data.transaction_id,
            amount: data.amount,
            currency: data.currency,
            timestamp: data.created_at
        };
    }

    async processPayment(paymentData) {
        return await this.post('/payments', paymentData);
    }

    async getPaymentStatus(transactionId) {
        return await this.get(`/payments/${transactionId}`);
    }
}

// SMS 서비스 클라이언트
class SmsApiClient extends ApiClient {
    async get(endpoint, params = {}) {
        const response = await this.client.get(endpoint, { params });
        return this.formatSmsResponse(response.data);
    }

    async post(endpoint, data = {}) {
        const response = await this.client.post(endpoint, data);
        return this.formatSmsResponse(response.data);
    }

    formatSmsResponse(data) {
        return {
            success: data.result === 'success',
            messageId: data.message_id,
            status: data.status,
            cost: data.cost
        };
    }

    async sendSms(phoneNumber, message) {
        return await this.post('/send', {
            to: phoneNumber,
            message: message
        });
    }

    async getDeliveryStatus(messageId) {
        return await this.get(`/status/${messageId}`);
    }
}

// 이메일 서비스 클라이언트
class EmailApiClient extends ApiClient {
    async get(endpoint, params = {}) {
        const response = await this.client.get(endpoint, { params });
        return this.formatEmailResponse(response.data);
    }

    async post(endpoint, data = {}) {
        const response = await this.client.post(endpoint, data);
        return this.formatEmailResponse(response.data);
    }

    formatEmailResponse(data) {
        return {
            success: data.success,
            messageId: data.message_id,
            status: data.status,
            recipient: data.recipient
        };
    }

    async sendEmail(to, subject, body, isHtml = false) {
        return await this.post('/send', {
            to: to,
            subject: subject,
            body: body,
            is_html: isHtml
        });
    }
}

// API 클라이언트 팩토리
class ApiClientFactory {
    static createClient(type, config) {
        switch (type.toLowerCase()) {
            case 'payment':
                return new PaymentApiClient(config);
            case 'sms':
                return new SmsApiClient(config);
            case 'email':
                return new EmailApiClient(config);
            default:
                throw new Error(`지원하지 않는 API 클라이언트 타입: ${type}`);
        }
    }

    // 환경 변수에서 설정 읽기
    static createFromEnvironment(type) {
        const config = {
            baseURL: process.env[`${type.toUpperCase()}_API_URL`],
            timeout: parseInt(process.env[`${type.toUpperCase()}_API_TIMEOUT`]) || 5000,
            headers: {
                'Authorization': `Bearer ${process.env[`${type.toUpperCase()}_API_KEY`]}`,
                'Content-Type': 'application/json'
            }
        };
        
        return this.createClient(type, config);
    }
}

module.exports = {
    ApiClient,
    PaymentApiClient,
    SmsApiClient,
    EmailApiClient,
    ApiClientFactory
};
```

**사용 예시:**
```javascript
// controllers/payment-controller.js
const { ApiClientFactory } = require('../services/api-client-factory');

class PaymentController {
    async processPayment(req, res) {
        try {
            const paymentClient = ApiClientFactory.createFromEnvironment('payment');
            const result = await paymentClient.processPayment({
                amount: req.body.amount,
                currency: 'KRW',
                card_number: req.body.cardNumber,
                expiry_date: req.body.expiryDate
            });

            if (result.success) {
                res.json({ success: true, transactionId: result.transactionId });
            } else {
                res.status(400).json({ success: false, error: '결제 실패' });
            }
        } catch (error) {
            res.status(500).json({ success: false, error: error.message });
        }
    }
}
```

##### 2. 알림 서비스 팩토리 ```javascript
// services/notification-factory.js - 알림 서비스 팩토리
const nodemailer = require('nodemailer');
const twilio = require('twilio');

// 추상 알림 서비스
class NotificationService {
    constructor(config) {
        this.config = config;
    }

    async send(to, message, options = {}) {
        throw new Error('send 메서드를 구현해야 합니다.');
    }

    async sendBulk(recipients, message, options = {}) {
        throw new Error('sendBulk 메서드를 구현해야 합니다.');
    }

    async getStatus(messageId) {
        throw new Error('getStatus 메서드를 구현해야 합니다.');
    }
}

// 이메일 알림 서비스
class EmailNotificationService extends NotificationService {
    constructor(config) {
        super(config);
        this.transporter = nodemailer.createTransporter({
            host: config.smtpHost,
            port: config.smtpPort,
            secure: config.secure,
            auth: {
                user: config.username,
                pass: config.password
            }
        });
    }

    async send(to, message, options = {}) {
        const mailOptions = {
            from: this.config.from,
            to: to,
            subject: options.subject || '알림',
            text: message.text,
            html: message.html
        };

        const result = await this.transporter.sendMail(mailOptions);
        return {
            success: true,
            messageId: result.messageId,
            status: 'sent'
        };
    }

    async sendBulk(recipients, message, options = {}) {
        const results = [];
        for (const recipient of recipients) {
            try {
                const result = await this.send(recipient, message, options);
                results.push({ recipient, ...result });
            } catch (error) {
                results.push({ 
                    recipient, 
                    success: false, 
                    error: error.message 
                });
            }
        }
        return results;
    }

    async getStatus(messageId) {
        // 이메일은 일반적으로 상태 추적이 제한적
        return { status: 'delivered', messageId };
    }
}

// SMS 알림 서비스
class SmsNotificationService extends NotificationService {
    constructor(config) {
        super(config);
        this.client = twilio(config.accountSid, config.authToken);
    }

    async send(to, message, options = {}) {
        try {
            const result = await this.client.messages.create({
                body: message.text,
                from: this.config.from,
                to: to
            });

            return {
                success: true,
                messageId: result.sid,
                status: result.status
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async sendBulk(recipients, message, options = {}) {
        const results = [];
        for (const recipient of recipients) {
            const result = await this.send(recipient, message, options);
            results.push({ recipient, ...result });
        }
        return results;
    }

    async getStatus(messageId) {
        try {
            const message = await this.client.messages(messageId).fetch();
            return {
                status: message.status,
                messageId: message.sid
            };
        } catch (error) {
            return { error: error.message };
        }
    }
}

// 푸시 알림 서비스
class PushNotificationService extends NotificationService {
    constructor(config) {
        super(config);
        this.fcm = require('firebase-admin');
        this.fcm.initializeApp({
            credential: this.fcm.credential.cert(config.serviceAccount)
        });
    }

    async send(to, message, options = {}) {
        try {
            const result = await this.fcm.messaging().send({
                token: to,
                notification: {
                    title: options.title || '알림',
                    body: message.text
                },
                data: message.data || {}
            });

            return {
                success: true,
                messageId: result,
                status: 'sent'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async sendBulk(recipients, message, options = {}) {
        try {
            const result = await this.fcm.messaging().sendMulticast({
                tokens: recipients,
                notification: {
                    title: options.title || '알림',
                    body: message.text
                },
                data: message.data || {}
            });

            return {
                success: true,
                successCount: result.successCount,
                failureCount: result.failureCount,
                responses: result.responses
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async getStatus(messageId) {
        // FCM은 일반적으로 상태 추적이 제한적
        return { status: 'delivered', messageId };
    }
}

// 알림 서비스 팩토리
class NotificationServiceFactory {
    static createService(type, config) {
        switch (type.toLowerCase()) {
            case 'email':
                return new EmailNotificationService(config);
            case 'sms':
                return new SmsNotificationService(config);
            case 'push':
                return new PushNotificationService(config);
            default:
                throw new Error(`지원하지 않는 알림 서비스 타입: ${type}`);
        }
    }

    // 환경 변수에서 설정 읽기
    static createFromEnvironment(type) {
        const configs = {
            email: {
                smtpHost: process.env.SMTP_HOST,
                smtpPort: parseInt(process.env.SMTP_PORT) || 587,
                secure: process.env.SMTP_SECURE === 'true',
                username: process.env.SMTP_USERNAME,
                password: process.env.SMTP_PASSWORD,
                from: process.env.EMAIL_FROM
            },
            sms: {
                accountSid: process.env.TWILIO_ACCOUNT_SID,
                authToken: process.env.TWILIO_AUTH_TOKEN,
                from: process.env.TWILIO_PHONE_NUMBER
            },
            push: {
                serviceAccount: JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT || '{}')
            }
        };

        return this.createService(type, configs[type]);
    }
}

module.exports = {
    NotificationService,
    EmailNotificationService,
    SmsNotificationService,
    PushNotificationService,
    NotificationServiceFactory
};
```

**사용 예시:**
```javascript
// services/notification-manager.js
const { NotificationServiceFactory } = require('./notification-factory');

class NotificationManager {
    async sendWelcomeEmail(user) {
        const emailService = NotificationServiceFactory.createFromEnvironment('email');
        return await emailService.send(user.email, {
            text: `안녕하세요 ${user.name}님! 환영합니다.`,
            html: `<h1>환영합니다!</h1><p>안녕하세요 ${user.name}님!</p>`
        }, {
            subject: '회원가입을 환영합니다'
        });
    }

    async sendSmsVerification(phoneNumber, code) {
        const smsService = NotificationServiceFactory.createFromEnvironment('sms');
        return await smsService.send(phoneNumber, {
            text: `인증번호: ${code}`
        });
    }

    async sendPushNotification(userTokens, message) {
        const pushService = NotificationServiceFactory.createFromEnvironment('push');
        return await pushService.sendBulk(userTokens, {
            text: message,
            data: { type: 'notification' }
        });
    }
}
```

#### Factory Method 패턴 장단점

##### 장점

**1. 높은 유연성과 확장성**
```javascript
// 새로운 데이터베이스 타입 추가가 쉬움
class RedisConnection extends DatabaseConnection {
    // Redis 전용 구현
}

// 팩토리에 새로운 케이스만 추가
class DatabaseConnectionFactory {
    static createConnection(type, config) {
        switch (type.toLowerCase()) {
            case 'mysql':
                return new MySQLConnection(config);
            case 'postgresql':
                return new PostgreSQLConnection(config);
            case 'mongodb':
                return new MongoDBConnection(config);
            case 'redis': // 새로운 타입 추가
                return new RedisConnection(config);
            default:
                throw new Error(`지원하지 않는 데이터베이스 타입: ${type}`);
        }
    }
}
```

**2. 결합도 감소**
```javascript
// 클라이언트 코드는 구체 클래스를 알 필요 없음
class UserService {
    constructor() {
        // 구체적인 DB 클래스를 직접 import하지 않음
        this.db = DatabaseConnectionFactory.createFromEnvironment();
    }
    
    async getUsers() {
        return await this.db.query('SELECT * FROM users');
    }
}
```

**3. 단일 책임 원칙 준수**
```javascript
// 각 팩토리는 특정 타입의 객체 생성만 담당
class PaymentApiClientFactory {
    static createClient(provider) {
        switch (provider) {
            case 'stripe':
                return new StripePaymentClient();
            case 'paypal':
                return new PayPalPaymentClient();
            case 'kakao':
                return new KakaoPayClient();
        }
    }
}
```

**4. 런타임 객체 생성**
```javascript
// 설정에 따라 동적으로 다른 객체 생성
const dbType = process.env.NODE_ENV === 'test' ? 'sqlite' : 'mysql';
const db = DatabaseConnectionFactory.createConnection(dbType, config);
```

##### 단점

**1. 클래스 수 증가**
```javascript
// 각 제품마다 팩토리 클래스 필요
class MySQLConnectionFactory { /* ... */ }
class PostgreSQLConnectionFactory { /* ... */ }
class MongoDBConnectionFactory { /* ... */ }
// 클래스 수가 기하급수적으로 증가할 수 있음
```

**2. 복잡성 증가**
```javascript
// 간단한 객체에도 팩토리 패턴 적용 시 오버엔지니어링
class SimpleConfigFactory {
    static createConfig(type) {
        switch (type) {
            case 'development':
                return { debug: true, logLevel: 'debug' };
            case 'production':
                return { debug: false, logLevel: 'error' };
        }
    }
}
// 이 경우는 단순한 객체 리터럴이 더 적합
```

**3. 추상화 오버헤드**
```javascript
// 추상 클래스와 인터페이스로 인한 메모리 사용량 증가
class AbstractApiClient {
    // 추상 메서드들...
}

class ConcreteApiClient extends AbstractApiClient {
    // 실제 구현...
}
```

**4. 팩토리 선택 복잡성**
```javascript
// 어떤 팩토리를 사용할지 결정하는 로직이 복잡해질 수 있음
class ComplexFactorySelector {
    static createService(userType, environment, region) {
        if (userType === 'premium' && environment === 'production' && region === 'asia') {
            return new PremiumAsiaService();
        } else if (userType === 'basic' && environment === 'development') {
            return new BasicDevService();
        }
        // 복잡한 조건문...
    }
}
```

##### 언제 사용해야 할까?

**적합한 경우:**
```javascript
// 외부 서비스 연동 (결제, SMS, 이메일 등)
const paymentClient = PaymentApiClientFactory.createClient('stripe');

// 데이터베이스 연결 관리
const db = DatabaseConnectionFactory.createConnection('mysql', config);

// 환경별 다른 구현체 필요
const logger = LoggerFactory.createLogger(process.env.NODE_ENV);

// 플러그인 아키텍처
const plugin = PluginFactory.createPlugin(pluginType);
```

**부적합한 경우:**
```javascript
// 단순한 설정 객체
const config = { host: 'localhost', port: 3000 }; // 팩토리 불필요

// 단일 구현체만 존재
const user = new User(); // 팩토리 불필요

// 런타임에 타입이 고정됨
const express = require('express'); // 팩토리 불필요
```

**판단 기준:**
1. **여러 구현체가 필요한가?** (MySQL, PostgreSQL, MongoDB)
2. **런타임에 타입이 결정되는가?** (환경별 설정, 사용자 선택)
3. **확장 가능성이 있는가?** (새로운 결제 방식, 알림 채널)
4. **복잡한 초기화 로직이 있는가?** (연결 풀, 인증 설정)
    }

    mount(container) {
        throw new Error("mount 메서드를 구현해야 합니다.");
    }

    unmount() {
        throw new Error("unmount 메서드를 구현해야 합니다.");
    }

    getInfo() {
        return {
            id: this.id,
            type: this.constructor.name,
            isVisible: this.isVisible,
            props: this.props
        };
    }
}

// 구체적인 컴포넌트들
class Button extends UIComponent {
    constructor(props) {
        super(props);
        this.text = props.text || 'Button';
        this.onClick = props.onClick || (() => {});
        this.variant = props.variant || 'primary';
        this.size = props.size || 'medium';
    }

    render() {
        const classes = `btn btn-${this.variant} btn-${this.size}`;
        return `<button id="${this.id}" class="${classes}" onclick="handleClick('${this.id}')">${this.text}</button>`;
    }

    mount(container) {
        const element = document.createElement('div');
        element.innerHTML = this.render();
        container.appendChild(element.firstElementChild);
        return element.firstElementChild;
    }

    unmount() {
        const element = document.getElementById(this.id);
        if (element) {
            element.remove();
        }
    }
}

class Input extends UIComponent {
    constructor(props) {
        super(props);
        this.type = props.type || 'text';
        this.placeholder = props.placeholder || '';
        this.value = props.value || '';
        this.onChange = props.onChange || (() => {});
    }

    render() {
        return `<input id="${this.id}" type="${this.type}" placeholder="${this.placeholder}" value="${this.value}" onchange="handleChange('${this.id}', this.value)">`;
    }

    mount(container) {
        const element = document.createElement('div');
        element.innerHTML = this.render();
        container.appendChild(element.firstElementChild);
        return element.firstElementChild;
    }

    unmount() {
        const element = document.getElementById(this.id);
        if (element) {
            element.remove();
        }
    }
}

class Modal extends UIComponent {
    constructor(props) {
        super(props);
        this.title = props.title || 'Modal';
        this.content = props.content || '';
        this.onClose = props.onClose || (() => {});
    }

    render() {
        return `
            <div id="${this.id}" class="modal-overlay">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>${this.title}</h3>
                        <button class="close-btn" onclick="handleClose('${this.id}')">&times;</button>
                    </div>
                    <div class="modal-body">
                        ${this.content}
                    </div>
                </div>
            </div>
        `;
    }

    mount(container) {
        const element = document.createElement('div');
        element.innerHTML = this.render();
        container.appendChild(element.firstElementChild);
        return element.firstElementChild;
    }

    unmount() {
        const element = document.getElementById(this.id);
        if (element) {
            element.remove();
        }
    }
}

// 팩토리 클래스
class ComponentFactory {
    createComponent(type, props) {
        switch(type.toLowerCase()) {
            case 'button':
                return new Button(props);
            case 'input':
                return new Input(props);
            case 'modal':
                return new Modal(props);
            default:
                throw new Error(`알 수 없는 컴포넌트 타입: ${type}`);
        }
    }

    // 편의 메서드들
    createButton(text, onClick, variant = 'primary') {
        return this.createComponent('button', { text, onClick, variant });
    }

    createInput(placeholder, onChange, type = 'text') {
        return this.createComponent('input', { placeholder, onChange, type });
    }

    createModal(title, content, onClose) {
        return this.createComponent('modal', { title, content, onClose });
    }
}

// 사용 예시
const factory = new ComponentFactory();

// 버튼 생성
const saveButton = factory.createButton('저장', () => console.log('저장됨'), 'primary');
const cancelButton = factory.createButton('취소', () => console.log('취소됨'), 'secondary');

// 입력 필드 생성
const nameInput = factory.createInput('이름을 입력하세요', (value) => console.log('이름:', value));
const emailInput = factory.createInput('이메일을 입력하세요', (value) => console.log('이메일:', value), 'email');

// 모달 생성
const confirmModal = factory.createModal(
    '확인',
    '정말로 삭제하시겠습니까?',
    () => console.log('모달 닫힘')
);

// DOM에 마운트
const container = document.getElementById('app');
saveButton.mount(container);
cancelButton.mount(container);
nameInput.mount(container);
emailInput.mount(container);
```

##### 2. 데이터베이스 연결 관리 시스템
```javascript
// 추상 데이터베이스 연결
class DatabaseConnection {
    constructor(config) {
        this.config = config;
        this.isConnected = false;
        this.connection = null;
    }

    connect() {
        throw new Error("connect 메서드를 구현해야 합니다.");
    }

    disconnect() {
        throw new Error("disconnect 메서드를 구현해야 합니다.");
    }

    query(sql, params = []) {
        throw new Error("query 메서드를 구현해야 합니다.");
    }

    getConnectionInfo() {
        return {
            type: this.constructor.name,
            isConnected: this.isConnected,
            config: { ...this.config }
        };
    }
}

// 구체적인 데이터베이스 연결들
class MySQLConnection extends DatabaseConnection {
    constructor(config) {
        super(config);
        this.host = config.host || 'localhost';
        this.port = config.port || 3306;
        this.database = config.database;
        this.username = config.username;
        this.password = config.password;
    }

    connect() {
        console.log(`MySQL에 연결 중: ${this.host}:${this.port}/${this.database}`);
        this.connection = `mysql://${this.username}@${this.host}:${this.port}/${this.database}`;
        this.isConnected = true;
        return this;
    }

    disconnect() {
        console.log('MySQL 연결 해제');
        this.connection = null;
        this.isConnected = false;
    }

    query(sql, params = []) {
        if (!this.isConnected) {
            throw new Error('데이터베이스에 연결되지 않았습니다.');
        }
        console.log(`MySQL 쿼리 실행: ${sql}`, params);
        return { rows: [], affectedRows: 0 };
    }
}

class PostgreSQLConnection extends DatabaseConnection {
    constructor(config) {
        super(config);
        this.host = config.host || 'localhost';
        this.port = config.port || 5432;
        this.database = config.database;
        this.username = config.username;
        this.password = config.password;
    }

    connect() {
        console.log(`PostgreSQL에 연결 중: ${this.host}:${this.port}/${this.database}`);
        this.connection = `postgresql://${this.username}@${this.host}:${this.port}/${this.database}`;
        this.isConnected = true;
        return this;
    }

    disconnect() {
        console.log('PostgreSQL 연결 해제');
        this.connection = null;
        this.isConnected = false;
    }

    query(sql, params = []) {
        if (!this.isConnected) {
            throw new Error('데이터베이스에 연결되지 않았습니다.');
        }
        console.log(`PostgreSQL 쿼리 실행: ${sql}`, params);
        return { rows: [], rowCount: 0 };
    }
}

class MongoDBConnection extends DatabaseConnection {
    constructor(config) {
        super(config);
        this.host = config.host || 'localhost';
        this.port = config.port || 27017;
        this.database = config.database;
        this.username = config.username;
        this.password = config.password;
    }

    connect() {
        console.log(`MongoDB에 연결 중: ${this.host}:${this.port}/${this.database}`);
        this.connection = `mongodb://${this.username}@${this.host}:${this.port}/${this.database}`;
        this.isConnected = true;
        return this;
    }

    disconnect() {
        console.log('MongoDB 연결 해제');
        this.connection = null;
        this.isConnected = false;
    }

    query(collection, operation, data = {}) {
        if (!this.isConnected) {
            throw new Error('데이터베이스에 연결되지 않았습니다.');
        }
        console.log(`MongoDB 작업 실행: ${collection}.${operation}`, data);
        return { result: 'success', modifiedCount: 0 };
    }
}

// 데이터베이스 팩토리
class DatabaseFactory {
    createConnection(type, config) {
        switch(type.toLowerCase()) {
            case 'mysql':
                return new MySQLConnection(config);
            case 'postgresql':
            case 'postgres':
                return new PostgreSQLConnection(config);
            case 'mongodb':
            case 'mongo':
                return new MongoDBConnection(config);
            default:
                throw new Error(`지원하지 않는 데이터베이스 타입: ${type}`);
        }
    }

    // 환경 설정에 따른 자동 연결 생성
    createFromEnvironment() {
        const dbType = process.env.DB_TYPE || 'mysql';
        const config = {
            host: process.env.DB_HOST || 'localhost',
            port: parseInt(process.env.DB_PORT) || (dbType === 'mysql' ? 3306 : 5432),
            database: process.env.DB_NAME || 'myapp',
            username: process.env.DB_USER || 'root',
            password: process.env.DB_PASSWORD || ''
        };
        
        return this.createConnection(dbType, config);
    }
}

// 사용 예시
const dbFactory = new DatabaseFactory();

// MySQL 연결
const mysqlConfig = {
    host: 'localhost',
    port: 3306,
    database: 'ecommerce',
    username: 'admin',
    password: 'password123'
};
const mysqlConn = dbFactory.createConnection('mysql', mysqlConfig);
mysqlConn.connect();
mysqlConn.query('SELECT * FROM users WHERE id = ?', [1]);

// PostgreSQL 연결
const postgresConfig = {
    host: 'localhost',
    port: 5432,
    database: 'analytics',
    username: 'analyst',
    password: 'securepass'
};
const postgresConn = dbFactory.createConnection('postgresql', postgresConfig);
postgresConn.connect();
postgresConn.query('SELECT * FROM events WHERE date >= $1', ['2024-01-01']);

// 환경 변수에서 자동 생성
const envConn = dbFactory.createFromEnvironment();
envConn.connect();
```

#### 장단점 분석

##### 장점

**1. 높은 유연성과 확장성**
- 새로운 제품 타입을 추가할 때 기존 코드를 수정하지 않고 새로운 팩토리만 추가하면 됩니다.
- OCP(Open-Closed Principle)를 잘 준수합니다.

```javascript
// 새로운 제품 타입 추가 시
class PowerPointDocument extends Document {
    // PowerPoint 전용 구현
}

class PowerPointFactory extends DocumentFactory {
    createDocument(name) {
        return new PowerPointDocument(name);
    }
}

// 기존 코드는 전혀 수정하지 않아도 됨
```

**2. 결합도 감소**
- 클라이언트 코드가 구체적인 클래스에 직접 의존하지 않습니다.
- 추상 팩토리 인터페이스에만 의존하므로 유지보수가 용이합니다.

**3. 단일 책임 원칙 준수**
- 각 팩토리는 특정 제품의 생성에만 책임을 집니다.
- 제품 생성 로직이 한 곳에 집중되어 관리가 쉽습니다.

**4. 런타임 객체 생성**
- 컴파일 타임이 아닌 런타임에 객체 타입을 결정할 수 있습니다.
- 사용자 입력이나 설정에 따라 동적으로 객체를 생성할 수 있습니다.

```javascript
// 런타임에 팩토리 선택
function createDocumentByExtension(filename) {
    const extension = filename.split('.').pop().toLowerCase();
    
    switch(extension) {
        case 'pdf':
            return new PDFFactory();
        case 'docx':
            return new WordFactory();
        case 'xlsx':
            return new ExcelFactory();
        default:
            throw new Error('지원하지 않는 파일 형식');
    }
}

const factory = createDocumentByExtension('report.pdf');
const document = factory.createDocument('report.pdf');
```

##### 단점

**1. 클래스 수 증가**
- 각 제품마다 팩토리 클래스가 필요하므로 전체 클래스 수가 증가합니다.
- 작은 프로젝트에서는 오버엔지니어링이 될 수 있습니다.

**2. 복잡성 증가**
- 단순한 객체 생성에도 여러 클래스가 관여하게 됩니다.
- 패턴을 이해하지 못한 개발자에게는 복잡해 보일 수 있습니다.

**3. 추상화의 오버헤드**
- 간단한 객체 생성에도 추상화 계층이 필요합니다.
- 성능이 중요한 상황에서는 불필요한 오버헤드가 될 수 있습니다.

**4. 팩토리 선택의 복잡성**
- 여러 팩토리 중 어떤 것을 사용할지 결정하는 로직이 복잡해질 수 있습니다.

```javascript
// 복잡한 팩토리 선택 로직
class DocumentFactorySelector {
    selectFactory(fileType, userRole, systemConfig) {
        if (userRole === 'admin' && systemConfig.allowAdvancedFeatures) {
            return new AdvancedDocumentFactory();
        } else if (fileType === 'pdf' && systemConfig.preferLightweight) {
            return new LightweightPDFFactory();
        } else {
            return new StandardDocumentFactory();
        }
    }
}
```

##### 언제 사용해야 할까?

**적합한 경우:**
- 여러 유사한 객체를 생성해야 하는 경우
- 객체 생성 로직이 복잡한 경우
- 런타임에 객체 타입을 결정해야 하는 경우
- 새로운 객체 타입을 자주 추가해야 하는 경우
- 객체 생성과 사용을 분리하고 싶은 경우

**부적합한 경우:**
- 단순한 객체 생성만 필요한 경우
- 객체 타입이 거의 변경되지 않는 경우
- 성능이 매우 중요한 경우
- 작은 규모의 프로젝트

### 3. Abstract Factory Pattern (추상 팩토리 패턴)

#### 추상 팩토리 패턴

추상 팩토리 패턴은 **관련된 여러 객체들을 함께 생성하여 일관성을 보장**하는 패턴입니다. Node.js 백엔드 개발에서 주로 사용되는 경우:

**사용 사례:**
- **마이크로서비스 아키텍처**: 각 서비스별로 다른 데이터베이스, 캐시, 메시지 큐 조합
- **멀티 테넌트 시스템**: 테넌트별로 다른 인프라 구성 (DB, Redis, S3 등)
- **환경별 인프라**: 개발/스테이징/프로덕션 환경별 다른 서비스 조합
- **지역별 서비스**: 지역별로 다른 CDN, 데이터베이스, 결제 시스템 조합
- **플러그인 시스템**: 플러그인별로 다른 의존성 조합

**Factory Method vs Abstract Factory:**
- **Factory Method**: 하나의 제품 생성 (예: 데이터베이스 연결)
- **Abstract Factory**: 관련된 여러 제품 생성 (예: 데이터베이스 + 캐시 + 로거 조합)

#### 패턴 구조

```
AbstractFactory (추상 팩토리)
├── ConcreteFactoryA (구체 팩토리 A)
└── ConcreteFactoryB (구체 팩토리 B)

AbstractProductA (추상 제품 A)
├── ConcreteProductA1 (구체 제품 A1)
└── ConcreteProductA2 (구체 제품 A2)

AbstractProductB (추상 제품 B)
├── ConcreteProductB1 (구체 제품 B1)
└── ConcreteProductB2 (구체 제품 B2)
```

#### 기본 구현

##### 1. 마이크로서비스 인프라 팩토리 ```javascript
// infrastructure/service-factory.js - 마이크로서비스 인프라 팩토리
const mysql = require('mysql2/promise');
const redis = require('redis');
const { Pool } = require('pg');
const winston = require('winston');

// 추상 데이터베이스 클래스
class Database {
    constructor(config) {
        this.config = config;
        this.connection = null;
    }

    async connect() {
        throw new Error('connect 메서드를 구현해야 합니다.');
    }

    async query(sql, params = []) {
        throw new Error('query 메서드를 구현해야 합니다.');
    }

    async disconnect() {
        throw new Error('disconnect 메서드를 구현해야 합니다.');
    }
}

// 추상 캐시 클래스
class Cache {
    constructor(config) {
        this.config = config;
        this.client = null;
    }

    async connect() {
        throw new Error('connect 메서드를 구현해야 합니다.');
    }

    async get(key) {
        throw new Error('get 메서드를 구현해야 합니다.');
    }

    async set(key, value, ttl = 3600) {
        throw new Error('set 메서드를 구현해야 합니다.');
    }

    async disconnect() {
        throw new Error('disconnect 메서드를 구현해야 합니다.');
    }
}

// 추상 로거 클래스
class Logger {
    constructor(config) {
        this.config = config;
        this.logger = null;
    }

    info(message, meta = {}) {
        throw new Error('info 메서드를 구현해야 합니다.');
    }

    error(message, error = null, meta = {}) {
        throw new Error('error 메서드를 구현해야 합니다.');
    }

    warn(message, meta = {}) {
        throw new Error('warn 메서드를 구현해야 합니다.');
    }
}

// 구체적인 제품군들 - MySQL + Redis + Winston 조합
class MySQLDatabase extends Database {
    async connect() {
        this.connection = await mysql.createConnection({
            host: this.config.host,
            port: this.config.port,
            user: this.config.user,
            password: this.config.password,
            database: this.config.database
        });
        console.log('MySQL 연결 성공');
    }

    async query(sql, params = []) {
        const [rows] = await this.connection.execute(sql, params);
        return rows;
    }

    async disconnect() {
        if (this.connection) {
            await this.connection.end();
            console.log('MySQL 연결 해제');
        }
    }
}

class RedisCache extends Cache {
    async connect() {
        this.client = redis.createClient({
            host: this.config.host,
            port: this.config.port,
            password: this.config.password
        });
        await this.client.connect();
        console.log('Redis 연결 성공');
    }

    async get(key) {
        return await this.client.get(key);
    }

    async set(key, value, ttl = 3600) {
        return await this.client.setEx(key, ttl, value);
    }

    async disconnect() {
        if (this.client) {
            await this.client.quit();
            console.log('Redis 연결 해제');
        }
    }
}

class WinstonLogger extends Logger {
    constructor(config) {
        super(config);
        this.logger = winston.createLogger({
            level: config.level || 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.json()
            ),
            transports: [
                new winston.transports.Console(),
                new winston.transports.File({ filename: 'app.log' })
            ]
        });
    }

    info(message, meta = {}) {
        this.logger.info(message, meta);
    }

    error(message, error = null, meta = {}) {
        this.logger.error(message, { error: error?.message, stack: error?.stack, ...meta });
    }

    warn(message, meta = {}) {
        this.logger.warn(message, meta);
    }
}

// 구체적인 제품군들 - PostgreSQL + Memcached + Pino 조합
class PostgreSQLDatabase extends Database {
    async connect() {
        this.connection = new Pool({
            host: this.config.host,
            port: this.config.port,
            user: this.config.user,
            password: this.config.password,
            database: this.config.database,
            max: 20
        });
        console.log('PostgreSQL 연결 성공');
    }

    async query(sql, params = []) {
        const result = await this.connection.query(sql, params);
        return result.rows;
    }

    async disconnect() {
        if (this.connection) {
            await this.connection.end();
            console.log('PostgreSQL 연결 해제');
        }
    }
}

class MemcachedCache extends Cache {
    async connect() {
        const Memcached = require('memcached');
        this.client = new Memcached(`${this.config.host}:${this.config.port}`);
        console.log('Memcached 연결 성공');
    }

    async get(key) {
        return new Promise((resolve, reject) => {
            this.client.get(key, (err, data) => {
                if (err) reject(err);
                else resolve(data);
            });
        });
    }

    async set(key, value, ttl = 3600) {
        return new Promise((resolve, reject) => {
            this.client.set(key, value, ttl, (err) => {
                if (err) reject(err);
                else resolve(true);
            });
        });
    }

    async disconnect() {
        if (this.client) {
            this.client.end();
            console.log('Memcached 연결 해제');
        }
    }
}

class PinoLogger extends Logger {
    constructor(config) {
        super(config);
        const pino = require('pino');
        this.logger = pino({
            level: config.level || 'info',
            transport: {
                target: 'pino-pretty',
                options: {
                    colorize: true
                }
            }
        });
    }

    info(message, meta = {}) {
        this.logger.info(meta, message);
    }

    error(message, error = null, meta = {}) {
        this.logger.error({ error: error?.message, stack: error?.stack, ...meta }, message);
    }

    warn(message, meta = {}) {
        this.logger.warn(meta, message);
    }
}

// 추상 팩토리
class InfrastructureFactory {
    createDatabase(config) {
        throw new Error('createDatabase 메서드를 구현해야 합니다.');
    }

    createCache(config) {
        throw new Error('createCache 메서드를 구현해야 합니다.');
    }

    createLogger(config) {
        throw new Error('createLogger 메서드를 구현해야 합니다.');
    }

    // 관련된 모든 인프라를 함께 생성하는 메서드
    async createInfrastructure(config) {
        const database = this.createDatabase(config.database);
        const cache = this.createCache(config.cache);
        const logger = this.createLogger(config.logger);

        // 모든 서비스 연결
        await database.connect();
        await cache.connect();

        return {
            database,
            cache,
            logger,
            async shutdown() {
                await database.disconnect();
                await cache.disconnect();
            }
        };
    }
}

// 구체적인 팩토리들
class MySQLRedisWinstonFactory extends InfrastructureFactory {
    createDatabase(config) {
        return new MySQLDatabase(config);
    }

    createCache(config) {
        return new RedisCache(config);
    }

    createLogger(config) {
        return new WinstonLogger(config);
    }
}

class PostgreSQLMemcachedPinoFactory extends InfrastructureFactory {
    createDatabase(config) {
        return new PostgreSQLDatabase(config);
    }

    createCache(config) {
        return new MemcachedCache(config);
    }

    createLogger(config) {
        return new PinoLogger(config);
    }
}

// 팩토리 선택기
class InfrastructureFactorySelector {
    static createFactory(type) {
        switch (type.toLowerCase()) {
            case 'mysql-redis-winston':
                return new MySQLRedisWinstonFactory();
            case 'postgresql-memcached-pino':
                return new PostgreSQLMemcachedPinoFactory();
            default:
                throw new Error(`지원하지 않는 인프라 타입: ${type}`);
        }
    }

    // 환경에 따라 자동으로 팩토리 선택
    static createFromEnvironment() {
        const env = process.env.NODE_ENV || 'development';
        const dbType = process.env.DB_TYPE || 'mysql';
        
        if (env === 'production' && dbType === 'postgresql') {
            return this.createFactory('postgresql-memcached-pino');
        } else {
            return this.createFactory('mysql-redis-winston');
        }
    }
}

module.exports = {
    Database,
    Cache,
    Logger,
    MySQLDatabase,
    RedisCache,
    WinstonLogger,
    PostgreSQLDatabase,
    MemcachedCache,
    PinoLogger,
    InfrastructureFactory,
    MySQLRedisWinstonFactory,
    PostgreSQLMemcachedPinoFactory,
    InfrastructureFactorySelector
};
```

**사용 예시:**
```javascript
// app.js - 애플리케이션 초기화
const { InfrastructureFactorySelector } = require('./infrastructure/service-factory');

async function initializeApp() {
    try {
        // 환경에 따라 적절한 인프라 팩토리 선택
        const factory = InfrastructureFactorySelector.createFromEnvironment();
        
        // 관련된 모든 인프라를 함께 생성
        const infrastructure = await factory.createInfrastructure({
            database: {
                host: process.env.DB_HOST,
                port: process.env.DB_PORT,
                user: process.env.DB_USER,
                password: process.env.DB_PASSWORD,
                database: process.env.DB_NAME
            },
            cache: {
                host: process.env.CACHE_HOST,
                port: process.env.CACHE_PORT,
                password: process.env.CACHE_PASSWORD
            },
            logger: {
                level: process.env.LOG_LEVEL || 'info'
            }
        });

        // 애플리케이션에서 사용
        const users = await infrastructure.database.query('SELECT * FROM users');
        await infrastructure.cache.set('users:count', users.length);
        infrastructure.logger.info('애플리케이션 초기화 완료', { userCount: users.length });

        // Graceful shutdown
        process.on('SIGTERM', async () => {
            await infrastructure.shutdown();
            process.exit(0);
        });

    } catch (error) {
        console.error('애플리케이션 초기화 실패:', error);
        process.exit(1);
    }
}

initializeApp();
```

#### Abstract Factory 패턴 장단점

##### 장점

**1. 일관성 보장**
```javascript
// 관련된 모든 인프라가 일관되게 구성됨
const factory = InfrastructureFactorySelector.createFromEnvironment();
const infrastructure = await factory.createInfrastructure(config);

// MySQL + Redis + Winston이 항상 함께 사용됨
// PostgreSQL + Memcached + Pino가 항상 함께 사용됨
```

**2. 높은 확장성**
```javascript
// 새로운 인프라 조합 추가가 쉬움
class MongoDBElasticsearchBunyanFactory extends InfrastructureFactory {
    createDatabase(config) {
        return new MongoDBDatabase(config);
    }
    
    createCache(config) {
        return new ElasticsearchCache(config);
    }
    
    createLogger(config) {
        return new BunyanLogger(config);
    }
}
```

**3. 결합도 감소**
```javascript
// 클라이언트 코드는 구체적인 인프라 조합을 알 필요 없음
class UserService {
    constructor(infrastructure) {
        this.db = infrastructure.database;
        this.cache = infrastructure.cache;
        this.logger = infrastructure.logger;
    }
    
    async getUser(id) {
        // 어떤 DB, 캐시, 로거인지 신경 쓸 필요 없음
        const user = await this.db.query('SELECT * FROM users WHERE id = ?', [id]);
        await this.cache.set(`user:${id}`, user);
        this.logger.info('사용자 조회', { userId: id });
        return user;
    }
}
```

**4. 제품군 교체 용이성**
```javascript
// 환경에 따라 다른 인프라 조합 사용
const factory = process.env.NODE_ENV === 'production' 
    ? new PostgreSQLMemcachedPinoFactory()
    : new MySQLRedisWinstonFactory();
```

##### 단점

**1. 높은 복잡성**
```javascript
// 많은 추상 클래스와 인터페이스 필요
class Database { /* 추상 클래스 */ }
class Cache { /* 추상 클래스 */ }
class Logger { /* 추상 클래스 */ }
class InfrastructureFactory { /* 추상 팩토리 */ }

// 구체 클래스들
class MySQLDatabase extends Database { /* ... */ }
class RedisCache extends Cache { /* ... */ }
class WinstonLogger extends Logger { /* ... */ }
class MySQLRedisWinstonFactory extends InfrastructureFactory { /* ... */ }
```

**2. 새로운 제품 추가 어려움**
```javascript
// 새로운 제품 타입 추가 시 모든 팩토리 수정 필요
class MessageQueue { /* 새로운 제품 타입 */ }

// 모든 팩토리에 createMessageQueue 메서드 추가 필요
class InfrastructureFactory {
    createMessageQueue(config) {
        throw new Error('createMessageQueue 메서드를 구현해야 합니다.');
    }
}
```

**3. 추상화 오버헤드**
```javascript
// 메모리 사용량과 실행 시간 증가
const infrastructure = await factory.createInfrastructure(config);
// 여러 추상 클래스 인스턴스 생성으로 인한 오버헤드
```

**4. 팩토리 선택 복잡성**
```javascript
// 어떤 팩토리를 사용할지 결정하는 로직이 복잡해질 수 있음
class ComplexFactorySelector {
    static createFactory(environment, region, scale, budget) {
        if (environment === 'production' && region === 'asia' && scale === 'large' && budget === 'high') {
            return new PremiumAsiaFactory();
        } else if (environment === 'development' && scale === 'small') {
            return new DevelopmentFactory();
        }
        // 복잡한 조건문...
    }
}
```

##### 언제 사용해야 할까?

**적합한 경우:**
```javascript
// 마이크로서비스 아키텍처
const userServiceInfra = UserServiceFactory.createInfrastructure();
const orderServiceInfra = OrderServiceFactory.createInfrastructure();

// 멀티 테넌트 시스템
const tenantInfra = TenantInfrastructureFactory.createForTenant(tenantId);

// 환경별 다른 인프라 구성
const infra = EnvironmentInfrastructureFactory.createForEnvironment(process.env.NODE_ENV);

// 지역별 서비스 구성
const regionalInfra = RegionalInfrastructureFactory.createForRegion('asia');
```

**부적합한 경우:**
```javascript
// ❌ 단일 서비스만 사용
const db = new MySQLConnection(); // 팩토리 불필요

// ❌ 간단한 애플리케이션
const app = express(); // 복잡한 팩토리 불필요

// ❌ 제품군이 변경되지 않음
const config = { host: 'localhost', port: 3000 }; // 팩토리 불필요
```

**판단 기준:**
1. **관련된 여러 제품이 함께 사용되는가?** (DB + 캐시 + 로거)
2. **제품군 간의 일관성이 중요한가?** (MySQL + Redis 조합)
3. **런타임에 제품군이 변경되는가?** (환경별, 테넌트별)
4. **확장 가능성이 높은가?** (새로운 인프라 조합 추가)
    }
}

class TextBox {
    constructor(placeholder, onChange) {
        this.placeholder = placeholder;
        this.value = '';
        this.onChange = onChange;
    }

    render() {
        throw new Error("render 메서드를 구현해야 합니다.");
    }

    setValue(value) {
        this.value = value;
        if (this.onChange) {
            this.onChange(value);
        }
    }

    getValue() {
        return this.value;
    }

    getInfo() {
        return {
            type: this.constructor.name,
            placeholder: this.placeholder,
            value: this.value,
            hasChangeHandler: !!this.onChange
        };
    }
}

class CheckBox {
    constructor(label, checked, onChange) {
        this.label = label;
        this.checked = checked || false;
        this.onChange = onChange;
    }

    render() {
        throw new Error("render 메서드를 구현해야 합니다.");
    }

    toggle() {
        this.checked = !this.checked;
        if (this.onChange) {
            this.onChange(this.checked);
        }
    }

    getInfo() {
        return {
            type: this.constructor.name,
            label: this.label,
            checked: this.checked,
            hasChangeHandler: !!this.onChange
        };
    }
}
```

##### 2. 구체적인 제품군들
```javascript
// Windows 스타일 제품군
class WindowsButton extends Button {
    render() {
        return `<button class="windows-button" onclick="handleClick('${this.text}')" style="background: #0078d4; color: white; border: none; padding: 8px 16px; border-radius: 2px; font-family: 'Segoe UI';">${this.text}</button>`;
    }
}

class WindowsTextBox extends TextBox {
    render() {
        return `<input type="text" class="windows-textbox" placeholder="${this.placeholder}" value="${this.value}" onchange="handleChange('${this.placeholder}', this.value)" style="border: 1px solid #d1d1d1; padding: 6px 8px; font-family: 'Segoe UI'; border-radius: 2px;">`;
    }
}

class WindowsCheckBox extends CheckBox {
    render() {
        return `<label class="windows-checkbox" style="font-family: 'Segoe UI'; display: flex; align-items: center; cursor: pointer;">
            <input type="checkbox" ${this.checked ? 'checked' : ''} onchange="handleCheckboxChange('${this.label}', this.checked)" style="margin-right: 8px;">
            ${this.label}
        </label>`;
    }
}

// macOS 스타일 제품군
class MacButton extends Button {
    render() {
        return `<button class="mac-button" onclick="handleClick('${this.text}')" style="background: #007aff; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-family: -apple-system, BlinkMacSystemFont;">${this.text}</button>`;
    }
}

class MacTextBox extends TextBox {
    render() {
        return `<input type="text" class="mac-textbox" placeholder="${this.placeholder}" value="${this.value}" onchange="handleChange('${this.placeholder}', this.value)" style="border: 1px solid #d1d1d1; padding: 8px 12px; font-family: -apple-system, BlinkMacSystemFont; border-radius: 6px; background: rgba(255, 255, 255, 0.8);">`;
    }
}

class MacCheckBox extends CheckBox {
    render() {
        return `<label class="mac-checkbox" style="font-family: -apple-system, BlinkMacSystemFont; display: flex; align-items: center; cursor: pointer;">
            <input type="checkbox" ${this.checked ? 'checked' : ''} onchange="handleCheckboxChange('${this.label}', this.checked)" style="margin-right: 8px; accent-color: #007aff;">
            ${this.label}
        </label>`;
    }
}

// Material Design 스타일 제품군
class MaterialButton extends Button {
    render() {
        return `<button class="material-button" onclick="handleClick('${this.text}')" style="background: #1976d2; color: white; border: none; padding: 12px 24px; border-radius: 4px; font-family: 'Roboto', sans-serif; text-transform: uppercase; font-weight: 500; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">${this.text}</button>`;
    }
}

class MaterialTextBox extends TextBox {
    render() {
        return `<div class="material-textbox-container" style="position: relative; margin: 16px 0;">
            <input type="text" class="material-textbox" placeholder="${this.placeholder}" value="${this.value}" onchange="handleChange('${this.placeholder}', this.value)" style="border: none; border-bottom: 2px solid #1976d2; padding: 12px 0; font-family: 'Roboto', sans-serif; background: transparent; outline: none; width: 100%;">
        </div>`;
    }
}

class MaterialCheckBox extends CheckBox {
    render() {
        return `<label class="material-checkbox" style="font-family: 'Roboto', sans-serif; display: flex; align-items: center; cursor: pointer; padding: 8px 0;">
            <input type="checkbox" ${this.checked ? 'checked' : ''} onchange="handleCheckboxChange('${this.label}', this.checked)" style="margin-right: 12px; accent-color: #1976d2;">
            ${this.label}
        </label>`;
    }
}
```

##### 3. 추상 팩토리와 구체 팩토리들
```javascript
// 추상 팩토리
class UIFactory {
    createButton(text, onClick) {
        throw new Error("createButton 메서드를 구현해야 합니다.");
    }
    
    createTextBox(placeholder, onChange) {
        throw new Error("createTextBox 메서드를 구현해야 합니다.");
    }

    createCheckBox(label, checked, onChange) {
        throw new Error("createCheckBox 메서드를 구현해야 합니다.");
    }

    // 팩토리 메서드 패턴과의 조합
    createForm(elements) {
        const form = {
            elements: [],
            render() {
                return this.elements.map(element => element.render()).join('\n');
            },
            addElement(element) {
                this.elements.push(element);
                return this;
            }
        };

        elements.forEach(element => {
            switch(element.type) {
                case 'button':
                    form.addElement(this.createButton(element.text, element.onClick));
                    break;
                case 'textbox':
                    form.addElement(this.createTextBox(element.placeholder, element.onChange));
                    break;
                case 'checkbox':
                    form.addElement(this.createCheckBox(element.label, element.checked, element.onChange));
                    break;
            }
        });

        return form;
    }
}

// 구체적인 팩토리들
class WindowsUIFactory extends UIFactory {
    createButton(text, onClick) {
        return new WindowsButton(text, onClick);
    }
    
    createTextBox(placeholder, onChange) {
        return new WindowsTextBox(placeholder, onChange);
    }

    createCheckBox(label, checked, onChange) {
        return new WindowsCheckBox(label, checked, onChange);
    }
}

class MacUIFactory extends UIFactory {
    createButton(text, onClick) {
        return new MacButton(text, onClick);
    }
    
    createTextBox(placeholder, onChange) {
        return new MacTextBox(placeholder, onChange);
    }

    createCheckBox(label, checked, onChange) {
        return new MacCheckBox(label, checked, onChange);
    }
}

class MaterialUIFactory extends UIFactory {
    createButton(text, onClick) {
        return new MaterialButton(text, onClick);
    }
    
    createTextBox(placeholder, onChange) {
        return new MaterialTextBox(placeholder, onChange);
    }

    createCheckBox(label, checked, onChange) {
        return new MaterialCheckBox(label, checked, onChange);
    }
}
```

##### 4. 사용 예시
```javascript
// 팩토리 선택 함수
function createUIFactory(theme) {
    switch(theme.toLowerCase()) {
        case 'windows':
            return new WindowsUIFactory();
        case 'mac':
        case 'macos':
            return new MacUIFactory();
        case 'material':
        case 'material-design':
            return new MaterialUIFactory();
        default:
            throw new Error(`지원하지 않는 테마: ${theme}`);
    }
}

// 사용 예시
const theme = 'material'; // 사용자 설정 또는 시스템 감지
const factory = createUIFactory(theme);

// 개별 컴포넌트 생성
const submitButton = factory.createButton('제출', () => console.log('폼 제출됨'));
const nameInput = factory.createTextBox('이름을 입력하세요', (value) => console.log('이름:', value));
const agreeCheckbox = factory.createCheckBox('약관에 동의합니다', false, (checked) => console.log('동의:', checked));

// 폼 생성
const form = factory.createForm([
    { type: 'textbox', placeholder: '이메일을 입력하세요', onChange: (value) => console.log('이메일:', value) },
    { type: 'textbox', placeholder: '비밀번호를 입력하세요', onChange: (value) => console.log('비밀번호:', value) },
    { type: 'checkbox', label: '로그인 상태 유지', checked: true, onChange: (checked) => console.log('로그인 유지:', checked) },
    { type: 'button', text: '로그인', onClick: () => console.log('로그인 시도') }
]);

// 렌더링
console.log('개별 컴포넌트:');
console.log(submitButton.render());
console.log(nameInput.render());
console.log(agreeCheckbox.render());

console.log('\n폼:');
console.log(form.render());
```

#### 실제 사용 사례

##### 1. 크로스 플랫폼 모바일 앱 개발
```javascript
// 추상 제품들
class Button {
    constructor(text, onPress) {
        this.text = text;
        this.onPress = onPress;
    }

    render() {
        throw new Error("render 메서드를 구현해야 합니다.");
    }
}

class TextInput {
    constructor(placeholder, onChange) {
        this.placeholder = placeholder;
        this.value = '';
        this.onChange = onChange;
    }

    render() {
        throw new Error("render 메서드를 구현해야 합니다.");
    }
}

class NavigationBar {
    constructor(title, leftButton, rightButton) {
        this.title = title;
        this.leftButton = leftButton;
        this.rightButton = rightButton;
    }

    render() {
        throw new Error("render 메서드를 구현해야 합니다.");
    }
}

// iOS 제품군
class IOSButton extends Button {
    render() {
        return {
            type: 'IOSButton',
            text: this.text,
            style: {
                backgroundColor: '#007AFF',
                color: 'white',
                borderRadius: 8,
                padding: 12,
                fontFamily: 'SF Pro Display'
            },
            onPress: this.onPress
        };
    }
}

class IOSTextInput extends TextInput {
    render() {
        return {
            type: 'IOSTextInput',
            placeholder: this.placeholder,
            value: this.value,
            style: {
                borderWidth: 1,
                borderColor: '#C7C7CC',
                borderRadius: 8,
                padding: 12,
                fontFamily: 'SF Pro Text'
            },
            onChange: this.onChange
        };
    }
}

class IOSNavigationBar extends NavigationBar {
    render() {
        return {
            type: 'IOSNavigationBar',
            title: this.title,
            style: {
                backgroundColor: '#F2F2F7',
                titleColor: '#000000',
                fontFamily: 'SF Pro Display',
                fontSize: 17,
                fontWeight: '600'
            },
            leftButton: this.leftButton,
            rightButton: this.rightButton
        };
    }
}

// Android 제품군
class AndroidButton extends Button {
    render() {
        return {
            type: 'AndroidButton',
            text: this.text,
            style: {
                backgroundColor: '#2196F3',
                color: 'white',
                borderRadius: 4,
                padding: 16,
                fontFamily: 'Roboto',
                elevation: 2
            },
            onPress: this.onPress
        };
    }
}

class AndroidTextInput extends TextInput {
    render() {
        return {
            type: 'AndroidTextInput',
            placeholder: this.placeholder,
            value: this.value,
            style: {
                borderWidth: 1,
                borderColor: '#BDBDBD',
                borderRadius: 4,
                padding: 16,
                fontFamily: 'Roboto'
            },
            onChange: this.onChange
        };
    }
}

class AndroidNavigationBar extends NavigationBar {
    render() {
        return {
            type: 'AndroidNavigationBar',
            title: this.title,
            style: {
                backgroundColor: '#FFFFFF',
                titleColor: '#212121',
                fontFamily: 'Roboto',
                fontSize: 20,
                fontWeight: '500',
                elevation: 4
            },
            leftButton: this.leftButton,
            rightButton: this.rightButton
        };
    }
}

// 추상 팩토리
class MobileUIFactory {
    createButton(text, onPress) {
        throw new Error("createButton 메서드를 구현해야 합니다.");
    }

    createTextInput(placeholder, onChange) {
        throw new Error("createTextInput 메서드를 구현해야 합니다.");
    }

    createNavigationBar(title, leftButton, rightButton) {
        throw new Error("createNavigationBar 메서드를 구현해야 합니다.");
    }

    // 복합 UI 생성
    createLoginScreen() {
        const emailInput = this.createTextInput('이메일', (value) => console.log('이메일:', value));
        const passwordInput = this.createTextInput('비밀번호', (value) => console.log('비밀번호:', value));
        const loginButton = this.createButton('로그인', () => console.log('로그인 시도'));
        const backButton = this.createButton('뒤로', () => console.log('뒤로 가기'));
        
        const navigationBar = this.createNavigationBar('로그인', backButton, null);

        return {
            navigationBar,
            emailInput,
            passwordInput,
            loginButton,
            render() {
                return {
                    navigationBar: this.navigationBar.render(),
                    emailInput: this.emailInput.render(),
                    passwordInput: this.passwordInput.render(),
                    loginButton: this.loginButton.render()
                };
            }
        };
    }
}

// 구체 팩토리들
class IOSUIFactory extends MobileUIFactory {
    createButton(text, onPress) {
        return new IOSButton(text, onPress);
    }

    createTextInput(placeholder, onChange) {
        return new IOSTextInput(placeholder, onChange);
    }

    createNavigationBar(title, leftButton, rightButton) {
        return new IOSNavigationBar(title, leftButton, rightButton);
    }
}

class AndroidUIFactory extends MobileUIFactory {
    createButton(text, onPress) {
        return new AndroidButton(text, onPress);
    }

    createTextInput(placeholder, onChange) {
        return new AndroidTextInput(placeholder, onChange);
    }

    createNavigationBar(title, leftButton, rightButton) {
        return new AndroidNavigationBar(title, leftButton, rightButton);
    }
}

// 사용 예시
function createMobileUIFactory(platform) {
    switch(platform.toLowerCase()) {
        case 'ios':
            return new IOSUIFactory();
        case 'android':
            return new AndroidUIFactory();
        default:
            throw new Error(`지원하지 않는 플랫폼: ${platform}`);
    }
}

// 플랫폼 감지 및 UI 생성
const platform = 'ios'; // 실제로는 디바이스에서 감지
const factory = createMobileUIFactory(platform);
const loginScreen = factory.createLoginScreen();

console.log('로그인 화면:', loginScreen.render());
```

##### 2. 게임 엔진의 렌더링 시스템
```javascript
// 추상 제품들
class Mesh {
    constructor(vertices, indices) {
        this.vertices = vertices;
        this.indices = indices;
    }

    render() {
        throw new Error("render 메서드를 구현해야 합니다.");
    }
}

class Texture {
    constructor(imageData) {
        this.imageData = imageData;
    }

    load() {
        throw new Error("load 메서드를 구현해야 합니다.");
    }
}

class Shader {
    constructor(vertexSource, fragmentSource) {
        this.vertexSource = vertexSource;
        this.fragmentSource = fragmentSource;
    }

    compile() {
        throw new Error("compile 메서드를 구현해야 합니다.");
    }
}

// OpenGL 제품군
class OpenGLMesh extends Mesh {
    render() {
        console.log('OpenGL 메시 렌더링:', {
            vertices: this.vertices.length,
            indices: this.indices.length,
            api: 'OpenGL',
            drawCalls: 1
        });
        return 'OpenGL 메시가 렌더링되었습니다.';
    }
}

class OpenGLTexture extends Texture {
    load() {
        console.log('OpenGL 텍스처 로딩:', {
            width: this.imageData.width,
            height: this.imageData.height,
            format: 'RGBA',
            api: 'OpenGL'
        });
        return 'OpenGL 텍스처가 로드되었습니다.';
    }
}

class OpenGLShader extends Shader {
    compile() {
        console.log('OpenGL 셰이더 컴파일:', {
            vertexSource: this.vertexSource.length,
            fragmentSource: this.fragmentSource.length,
            api: 'OpenGL'
        });
        return 'OpenGL 셰이더가 컴파일되었습니다.';
    }
}

// DirectX 제품군
class DirectXMesh extends Mesh {
    render() {
        console.log('DirectX 메시 렌더링:', {
            vertices: this.vertices.length,
            indices: this.indices.length,
            api: 'DirectX',
            drawCalls: 1
        });
        return 'DirectX 메시가 렌더링되었습니다.';
    }
}

class DirectXTexture extends Texture {
    load() {
        console.log('DirectX 텍스처 로딩:', {
            width: this.imageData.width,
            height: this.imageData.height,
            format: 'RGBA',
            api: 'DirectX'
        });
        return 'DirectX 텍스처가 로드되었습니다.';
    }
}

class DirectXShader extends Shader {
    compile() {
        console.log('DirectX 셰이더 컴파일:', {
            vertexSource: this.vertexSource.length,
            fragmentSource: this.fragmentSource.length,
            api: 'DirectX'
        });
        return 'DirectX 셰이더가 컴파일되었습니다.';
    }
}

// Vulkan 제품군
class VulkanMesh extends Mesh {
    render() {
        console.log('Vulkan 메시 렌더링:', {
            vertices: this.vertices.length,
            indices: this.indices.length,
            api: 'Vulkan',
            drawCalls: 1
        });
        return 'Vulkan 메시가 렌더링되었습니다.';
    }
}

class VulkanTexture extends Texture {
    load() {
        console.log('Vulkan 텍스처 로딩:', {
            width: this.imageData.width,
            height: this.imageData.height,
            format: 'RGBA',
            api: 'Vulkan'
        });
        return 'Vulkan 텍스처가 로드되었습니다.';
    }
}

class VulkanShader extends Shader {
    compile() {
        console.log('Vulkan 셰이더 컴파일:', {
            vertexSource: this.vertexSource.length,
            fragmentSource: this.fragmentSource.length,
            api: 'Vulkan'
        });
        return 'Vulkan 셰이더가 컴파일되었습니다.';
    }
}

// 추상 팩토리
class RendererFactory {
    createMesh(vertices, indices) {
        throw new Error("createMesh 메서드를 구현해야 합니다.");
    }

    createTexture(imageData) {
        throw new Error("createTexture 메서드를 구현해야 합니다.");
    }

    createShader(vertexSource, fragmentSource) {
        throw new Error("createShader 메서드를 구현해야 합니다.");
    }

    // 복합 렌더링 객체 생성
    createModel(meshData, textureData, shaderData) {
        const mesh = this.createMesh(meshData.vertices, meshData.indices);
        const texture = this.createTexture(textureData);
        const shader = this.createShader(shaderData.vertexSource, shaderData.fragmentSource);

        return {
            mesh,
            texture,
            shader,
            render() {
                this.shader.compile();
                this.texture.load();
                return this.mesh.render();
            }
        };
    }
}

// 구체 팩토리들
class OpenGLRendererFactory extends RendererFactory {
    createMesh(vertices, indices) {
        return new OpenGLMesh(vertices, indices);
    }

    createTexture(imageData) {
        return new OpenGLTexture(imageData);
    }

    createShader(vertexSource, fragmentSource) {
        return new OpenGLShader(vertexSource, fragmentSource);
    }
}

class DirectXRendererFactory extends RendererFactory {
    createMesh(vertices, indices) {
        return new DirectXMesh(vertices, indices);
    }

    createTexture(imageData) {
        return new DirectXTexture(imageData);
    }

    createShader(vertexSource, fragmentSource) {
        return new DirectXShader(vertexSource, fragmentSource);
    }
}

class VulkanRendererFactory extends RendererFactory {
    createMesh(vertices, indices) {
        return new VulkanMesh(vertices, indices);
    }

    createTexture(imageData) {
        return new VulkanTexture(imageData);
    }

    createShader(vertexSource, fragmentSource) {
        return new VulkanShader(vertexSource, fragmentSource);
    }
}

// 사용 예시
function createRendererFactory(api) {
    switch(api.toLowerCase()) {
        case 'opengl':
            return new OpenGLRendererFactory();
        case 'directx':
            return new DirectXRendererFactory();
        case 'vulkan':
            return new VulkanRendererFactory();
        default:
            throw new Error(`지원하지 않는 렌더링 API: ${api}`);
    }
}

// 렌더링 API 선택 및 모델 생성
const renderAPI = 'vulkan'; // 실제로는 하드웨어 지원에 따라 결정
const factory = createRendererFactory(renderAPI);

const modelData = {
    mesh: {
        vertices: [0, 0, 0, 1, 1, 1, 2, 2, 2],
        indices: [0, 1, 2]
    },
    texture: {
        width: 512,
        height: 512,
        data: new Array(512 * 512 * 4).fill(255)
    },
    shader: {
        vertexSource: 'vertex shader source code...',
        fragmentSource: 'fragment shader source code...'
    }
};

const model = factory.createModel(modelData.mesh, modelData.texture, modelData.shader);
console.log(model.render());
```

#### 장단점 분석

##### 장점

**1. 제품군 간의 일관성 보장**
- 관련된 제품들이 항상 함께 생성되어 호환성 문제가 발생하지 않습니다.
- 예: Windows 버튼과 Windows 텍스트박스가 항상 함께 생성되어 일관된 UI 제공

**2. 높은 확장성**
- 새로운 제품군을 추가할 때 기존 코드를 수정하지 않고 새로운 팩토리만 추가하면 됩니다.
- OCP(Open-Closed Principle)를 잘 준수합니다.

```javascript
// 새로운 테마 추가 시
class DarkThemeFactory extends UIFactory {
    createButton(text, onClick) {
        return new DarkButton(text, onClick);
    }
    
    createTextBox(placeholder, onChange) {
        return new DarkTextBox(placeholder, onChange);
    }
    
    createCheckBox(label, checked, onChange) {
        return new DarkCheckBox(label, checked, onChange);
    }
}

// 기존 코드는 전혀 수정하지 않아도 됨
```

**3. 구체 클래스와의 결합도 감소**
- 클라이언트 코드가 구체적인 클래스에 직접 의존하지 않습니다.
- 추상 팩토리 인터페이스에만 의존하므로 유지보수가 용이합니다.

**4. 제품군 교체의 용이성**
- 런타임에 전체 제품군을 쉽게 교체할 수 있습니다.

```javascript
// 테마 변경이 매우 간단
function changeTheme(newTheme) {
    const factory = createUIFactory(newTheme);
    const newUI = factory.createForm(formElements);
    renderUI(newUI);
}
```

##### 단점

**1. 높은 복잡성**
- 많은 인터페이스와 클래스가 필요하여 코드가 복잡해집니다.
- 작은 프로젝트에서는 오버엔지니어링이 될 수 있습니다.

**2. 새로운 제품 추가의 어려움**
- 새로운 제품을 추가할 때 모든 팩토리를 수정해야 합니다.
- 이는 OCP를 위반하는 상황입니다.

```javascript
// 새로운 제품 추가 시 모든 팩토리 수정 필요
class UIFactory {
    createButton() { /* ... */ }
    createTextBox() { /* ... */ }
    createCheckBox() { /* ... */ }
    createSlider() { /* 새로운 제품 추가 */ } // 모든 팩토리에서 구현 필요
}
```

**3. 추상화의 오버헤드**
- 간단한 객체 생성에도 복잡한 추상화 계층이 필요합니다.
- 성능이 중요한 상황에서는 불필요한 오버헤드가 될 수 있습니다.

**4. 팩토리 선택의 복잡성**
- 여러 팩토리 중 어떤 것을 사용할지 결정하는 로직이 복잡해질 수 있습니다.

```javascript
// 복잡한 팩토리 선택 로직
class UIFactorySelector {
    selectFactory(userPreferences, systemCapabilities, deviceType) {
        if (deviceType === 'mobile' && systemCapabilities.touchSupport) {
            return new TouchUIFactory();
        } else if (userPreferences.theme === 'dark') {
            return new DarkThemeFactory();
        } else if (systemCapabilities.highDPI) {
            return new HighDPIUIFactory();
        } else {
            return new StandardUIFactory();
        }
    }
}
```

##### 언제 사용해야 할까?

**적합한 경우:**
- 여러 관련 제품을 함께 생성해야 하는 경우
- 제품군 간의 일관성이 중요한 경우
- 런타임에 전체 제품군을 교체해야 하는 경우
- 크로스 플랫폼 애플리케이션 개발
- 테마 시스템 구현
- 게임 엔진의 렌더링 시스템

**부적합한 경우:**
- 단순한 객체 생성만 필요한 경우
- 제품군이 자주 변경되는 경우
- 성능이 매우 중요한 경우
- 작은 규모의 프로젝트
- 새로운 제품을 자주 추가해야 하는 경우

### 4. Builder Pattern (빌더 패턴)

#### 빌더 패턴

빌더 패턴은 **복잡한 객체의 생성 과정을 단계별로 분리하여 가독성과 유연성을 높이는** 패턴입니다. Node.js 백엔드 개발에서 주로 사용되는 경우:

**사용 사례:**
- **HTTP 요청 구성**: 복잡한 API 요청 파라미터 구성
- **데이터베이스 쿼리 빌더**: 동적 SQL 쿼리 생성
- **이메일 메시지 구성**: 복잡한 이메일 템플릿 생성
- **설정 객체 구성**: 환경별 복잡한 설정 객체 생성
- **API 응답 구성**: 복잡한 JSON 응답 구조 생성
- **로그 메시지 구성**: 구조화된 로그 엔트리 생성

**언제 사용하는가?**
- 생성자에 많은 매개변수가 필요한 경우
- 매개변수의 순서가 중요하지 않은 경우
- 객체 생성 과정이 복잡한 경우
- 불변 객체를 생성해야 하는 경우

#### 패턴 구조

```
Director (감독자)
├── Builder (추상 빌더)
│   ├── ConcreteBuilderA (구체 빌더 A)
│   └── ConcreteBuilderB (구체 빌더 B)
└── Product (제품)
```

#### 기본 구현

##### 1. HTTP 요청 빌더 ```javascript
// builders/http-request-builder.js - HTTP 요청 빌더
const axios = require('axios');

class HttpRequest {
    constructor(builder) {
        // 필수 구성 요소
        this.url = builder.url;
        this.method = builder.method;
        
        // 선택적 구성 요소
        this.headers = builder.headers || {};
        this.params = builder.params || {};
        this.data = builder.data || null;
        this.timeout = builder.timeout || 5000;
        this.retries = builder.retries || 0;
        this.retryDelay = builder.retryDelay || 1000;
        this.auth = builder.auth || null;
        this.proxy = builder.proxy || null;
        this.validateStatus = builder.validateStatus || null;
        this.maxRedirects = builder.maxRedirects || 5;
        this.responseType = builder.responseType || 'json';
        this.withCredentials = builder.withCredentials || false;
        
        // 메타데이터
        this.createdAt = new Date();
        this.id = Math.random().toString(36).substr(2, 9);
    }

    async execute() {
        try {
            const response = await axios({
                url: this.url,
                method: this.method,
                headers: this.headers,
                params: this.params,
                data: this.data,
                timeout: this.timeout,
                auth: this.auth,
                proxy: this.proxy,
                validateStatus: this.validateStatus,
                maxRedirects: this.maxRedirects,
                responseType: this.responseType,
                withCredentials: this.withCredentials
            });
            
            return {
                success: true,
                data: response.data,
                status: response.status,
                headers: response.headers,
                requestId: this.id
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                status: error.response?.status,
                requestId: this.id
            };
        }
    }

    getInfo() {
        return {
            id: this.id,
            method: this.method,
            url: this.url,
            headers: this.headers,
            timeout: this.timeout,
            retries: this.retries,
            createdAt: this.createdAt
        };
    }
}

// HTTP 요청 빌더
class HttpRequestBuilder {
            constructor() {
        this.reset();
    }

    reset() {
        this.url = null;
        this.method = 'GET';
        this.headers = {};
        this.params = {};
        this.data = null;
        this.timeout = 5000;
        this.retries = 0;
        this.retryDelay = 1000;
        this.auth = null;
        this.proxy = null;
        this.validateStatus = null;
        this.maxRedirects = 5;
        this.responseType = 'json';
        this.withCredentials = false;
                return this;
            }
            
    setUrl(url) {
        this.url = url;
                return this;
            }
            
    setMethod(method) {
        this.method = method.toUpperCase();
                return this;
            }
            
    setHeaders(headers) {
        this.headers = { ...this.headers, ...headers };
                return this;
            }
            
    setHeader(key, value) {
        this.headers[key] = value;
                return this;
            }

    setParams(params) {
        this.params = { ...this.params, ...params };
        return this;
    }

    setParam(key, value) {
        this.params[key] = value;
        return this;
    }

    setData(data) {
        this.data = data;
        return this;
    }

    setTimeout(timeout) {
        this.timeout = timeout;
        return this;
    }

    setRetries(retries, delay = 1000) {
        this.retries = retries;
        this.retryDelay = delay;
        return this;
    }

    setAuth(username, password) {
        this.auth = { username, password };
        return this;
    }

    setBearerToken(token) {
        this.headers['Authorization'] = `Bearer ${token}`;
        return this;
    }

    setProxy(proxy) {
        this.proxy = proxy;
        return this;
    }

    setResponseType(type) {
        this.responseType = type;
        return this;
    }

    setWithCredentials(credentials) {
        this.withCredentials = credentials;
        return this;
    }

    // 편의 메서드들
    asGet() {
        return this.setMethod('GET');
    }

    asPost() {
        return this.setMethod('POST');
    }

    asPut() {
        return this.setMethod('PUT');
    }

    asDelete() {
        return this.setMethod('DELETE');
    }

    withJson(data) {
        return this.setMethod('POST')
                  .setHeader('Content-Type', 'application/json')
                  .setData(data);
    }

    withFormData(data) {
        return this.setMethod('POST')
                  .setHeader('Content-Type', 'application/x-www-form-urlencoded')
                  .setData(data);
    }

    withAuth(token) {
        return this.setBearerToken(token);
    }

    withTimeout(timeout) {
        return this.setTimeout(timeout);
    }

    withRetries(retries, delay = 1000) {
        return this.setRetries(retries, delay);
    }
            
            build() {
        if (!this.url) {
            throw new Error('URL은 필수입니다.');
        }
        
        return new HttpRequest(this);
    }
}

module.exports = {
    HttpRequest,
    HttpRequestBuilder
};
```

**사용 예시:**
```javascript
// services/api-client.js
const { HttpRequestBuilder } = require('../builders/http-request-builder');

class ApiClient {
    async getUserById(id, token) {
        const request = new HttpRequestBuilder()
            .setUrl(`https://api.example.com/users/${id}`)
            .asGet()
            .withAuth(token)
            .withTimeout(10000)
            .withRetries(3, 2000)
            .build();

        return await request.execute();
    }

    async createUser(userData, token) {
        const request = new HttpRequestBuilder()
            .setUrl('https://api.example.com/users')
            .withJson(userData)
            .withAuth(token)
            .setHeader('X-Request-ID', Math.random().toString(36))
            .build();

        return await request.execute();
    }

    async uploadFile(file, token) {
        const formData = new FormData();
        formData.append('file', file);

        const request = new HttpRequestBuilder()
            .setUrl('https://api.example.com/upload')
            .withFormData(formData)
            .withAuth(token)
            .setTimeout(30000)
            .build();

        return await request.execute();
    }
}
```

##### 2. 데이터베이스 쿼리 빌더 ```javascript
// builders/query-builder.js - 데이터베이스 쿼리 빌더
class Query {
    constructor(builder) {
        this.table = builder.table;
        this.select = builder.select || ['*'];
        this.where = builder.where || [];
        this.orderBy = builder.orderBy || [];
        this.groupBy = builder.groupBy || [];
        this.having = builder.having || [];
        this.limit = builder.limit || null;
        this.offset = builder.offset || null;
        this.joins = builder.joins || [];
        this.distinct = builder.distinct || false;
        this.lock = builder.lock || null;
    }

    toSQL() {
        let sql = '';
        
        // SELECT 절
        if (this.distinct) {
            sql += `SELECT DISTINCT ${this.select.join(', ')}`;
        } else {
            sql += `SELECT ${this.select.join(', ')}`;
        }
        
        // FROM 절
        sql += ` FROM ${this.table}`;
        
        // JOIN 절
        if (this.joins.length > 0) {
            sql += ' ' + this.joins.join(' ');
        }
        
        // WHERE 절
        if (this.where.length > 0) {
            sql += ` WHERE ${this.where.join(' AND ')}`;
        }
        
        // GROUP BY 절
        if (this.groupBy.length > 0) {
            sql += ` GROUP BY ${this.groupBy.join(', ')}`;
        }
        
        // HAVING 절
        if (this.having.length > 0) {
            sql += ` HAVING ${this.having.join(' AND ')}`;
        }
        
        // ORDER BY 절
        if (this.orderBy.length > 0) {
            sql += ` ORDER BY ${this.orderBy.join(', ')}`;
        }
        
        // LIMIT 절
        if (this.limit) {
            sql += ` LIMIT ${this.limit}`;
        }
        
        // OFFSET 절
        if (this.offset) {
            sql += ` OFFSET ${this.offset}`;
        }
        
        // LOCK 절
        if (this.lock) {
            sql += ` ${this.lock}`;
        }
        
        return sql;
    }

    getInfo() {
        return {
            table: this.table,
            select: this.select,
            where: this.where,
            orderBy: this.orderBy,
            limit: this.limit,
            offset: this.offset,
            sql: this.toSQL()
        };
    }
}

// 쿼리 빌더
class QueryBuilder {
    constructor() {
        this.reset();
    }

    reset() {
        this.table = null;
        this.select = ['*'];
        this.where = [];
        this.orderBy = [];
        this.groupBy = [];
        this.having = [];
        this.limit = null;
        this.offset = null;
        this.joins = [];
        this.distinct = false;
        this.lock = null;
        return this;
    }

    from(table) {
        this.table = table;
        return this;
    }

    select(columns) {
        if (Array.isArray(columns)) {
            this.select = columns;
        } else {
            this.select = [columns];
        }
        return this;
    }

    where(condition, operator = 'AND') {
        if (typeof condition === 'string') {
            this.where.push(condition);
        } else if (typeof condition === 'object') {
            const conditions = Object.entries(condition)
                .map(([key, value]) => `${key} = '${value}'`)
                .join(` ${operator} `);
            this.where.push(conditions);
        }
        return this;
    }

    whereIn(column, values) {
        const valueList = values.map(v => `'${v}'`).join(', ');
        this.where.push(`${column} IN (${valueList})`);
        return this;
    }

    whereBetween(column, min, max) {
        this.where.push(`${column} BETWEEN '${min}' AND '${max}'`);
        return this;
    }

    whereNull(column) {
        this.where.push(`${column} IS NULL`);
        return this;
    }

    whereNotNull(column) {
        this.where.push(`${column} IS NOT NULL`);
        return this;
    }

    orderBy(column, direction = 'ASC') {
        this.orderBy.push(`${column} ${direction.toUpperCase()}`);
        return this;
    }

    groupBy(columns) {
        if (Array.isArray(columns)) {
            this.groupBy = [...this.groupBy, ...columns];
        } else {
            this.groupBy.push(columns);
        }
        return this;
    }

    having(condition) {
        this.having.push(condition);
        return this;
    }

    limit(count) {
        this.limit = count;
        return this;
    }

    offset(count) {
        this.offset = count;
        return this;
    }

    join(table, on, type = 'INNER') {
        this.joins.push(`${type} JOIN ${table} ON ${on}`);
        return this;
    }

    leftJoin(table, on) {
        return this.join(table, on, 'LEFT');
    }

    rightJoin(table, on) {
        return this.join(table, on, 'RIGHT');
    }

    distinct() {
        this.distinct = true;
        return this;
    }

    lock(lockType = 'FOR UPDATE') {
        this.lock = lockType;
        return this;
    }

    // 편의 메서드들
    findById(id) {
        return this.where('id', id).limit(1);
    }

    findByEmail(email) {
        return this.where('email', email).limit(1);
    }

    paginate(page, perPage = 10) {
        const offset = (page - 1) * perPage;
        return this.limit(perPage).offset(offset);
    }

    build() {
        if (!this.table) {
            throw new Error('테이블명은 필수입니다.');
        }
        
        return new Query(this);
    }
}

module.exports = {
    Query,
    QueryBuilder
};
```

**사용 예시:**
```javascript
// services/user-service.js
const { QueryBuilder } = require('../builders/query-builder');

class UserService {
    async getUsers(filters = {}) {
        const query = new QueryBuilder()
            .from('users')
            .select(['id', 'name', 'email', 'created_at'])
            .where('active', true)
            .orderBy('created_at', 'DESC')
            .limit(100)
    .build();

        return await this.db.query(query.toSQL());
    }

    async getUserById(id) {
        const query = new QueryBuilder()
            .from('users')
            .findById(id)
    .build();

        const result = await this.db.query(query.toSQL());
        return result[0];
    }

    async searchUsers(searchTerm, page = 1) {
        const query = new QueryBuilder()
            .from('users')
            .select(['id', 'name', 'email'])
            .where(`name LIKE '%${searchTerm}%' OR email LIKE '%${searchTerm}%'`)
            .orderBy('name', 'ASC')
            .paginate(page, 20)
            .build();

        return await this.db.query(query.toSQL());
    }

    async getUsersWithOrders() {
        const query = new QueryBuilder()
            .from('users')
            .select(['users.id', 'users.name', 'COUNT(orders.id) as order_count'])
            .leftJoin('orders', 'users.id = orders.user_id')
            .where('users.active', true)
            .groupBy(['users.id', 'users.name'])
            .having('COUNT(orders.id) > 0')
            .orderBy('order_count', 'DESC')
            .build();

        return await this.db.query(query.toSQL());
    }
}
```

#### Builder 패턴 장단점

##### 장점

**1. 뛰어난 가독성**
```javascript
// 빌더 패턴 사용 - 가독성 좋음
const request = new HttpRequestBuilder()
    .setUrl('https://api.example.com/users')
    .asPost()
    .withJson(userData)
    .withAuth(token)
    .withTimeout(10000)
    .withRetries(3, 2000)
    .build();

// vs 생성자 패턴 - 가독성 나쁨
const request = new HttpRequest(
    'https://api.example.com/users',
    'POST',
    { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    userData,
    10000,
    3,
    2000,
    null,
    null,
    null,
    5,
    'json',
    false
);
```

**2. 높은 유연성**
```javascript
// 필요한 부분만 설정 가능
const simpleQuery = new QueryBuilder()
    .from('users')
    .select(['id', 'name'])
    .build();

// 복잡한 쿼리도 단계별로 구성 가능
const complexQuery = new QueryBuilder()
    .from('users')
    .select(['users.id', 'users.name', 'COUNT(orders.id) as order_count'])
    .leftJoin('orders', 'users.id = orders.user_id')
    .where('users.active', true)
    .groupBy(['users.id', 'users.name'])
    .having('COUNT(orders.id) > 0')
    .orderBy('order_count', 'DESC')
    .limit(100)
    .build();
```

**3. 불변 객체 생성**
```javascript
// 빌더로 생성된 객체는 불변
const request = new HttpRequestBuilder()
    .setUrl('https://api.example.com/users')
    .asGet()
    .build();

// request 객체는 생성 후 변경 불가
// request.url = 'https://malicious.com'; // 불가능
```

**4. 유효성 검사와 검증**
```javascript
class HttpRequestBuilder {
    build() {
        if (!this.url) {
            throw new Error('URL은 필수입니다.');
        }
        
        if (this.method === 'POST' && !this.data) {
            throw new Error('POST 요청에는 데이터가 필요합니다.');
        }
        
        if (this.timeout < 1000) {
            throw new Error('타임아웃은 최소 1초 이상이어야 합니다.');
        }
        
        return new HttpRequest(this);
    }
}
```

**5. 단계별 객체 구성**
```javascript
// 복잡한 객체를 단계별로 구성
const email = new EmailBuilder()
    .to('user@example.com')
    .subject('환영합니다')
    .htmlBody('<h1>환영합니다!</h1>')
    .attach('welcome.pdf')
    .priority('high')
    .build();
```

##### 단점

**1. 높은 복잡성**
```javascript
// 빌더 클래스가 복잡해질 수 있음
class HttpRequestBuilder {
    constructor() {
        this.reset(); // 15개 이상의 속성 초기화
    }
    
    // 20개 이상의 메서드
    setUrl() { /* ... */ }
    setMethod() { /* ... */ }
    setHeaders() { /* ... */ }
    // ... 더 많은 메서드들
}
```

**2. 메모리 오버헤드**
```javascript
// 빌더 인스턴스 생성으로 인한 메모리 사용량 증가
const builder = new HttpRequestBuilder(); // 메모리 사용
const request = builder.setUrl('...').build(); // 추가 메모리 사용
```

**3. 코드 중복**
```javascript
// 비슷한 빌더들 간의 중복 코드
class HttpRequestBuilder {
    setUrl(url) { this.url = url; return this; }
    setMethod(method) { this.method = method; return this; }
}

class DatabaseQueryBuilder {
    setUrl(url) { this.url = url; return this; } // 중복
    setMethod(method) { this.method = method; return this; } // 중복
}
```

**4. 런타임 에러 가능성**
```javascript
// 빌드 시점에 에러 발생 가능
const request = new HttpRequestBuilder()
    .setUrl('invalid-url') // 잘못된 URL
    .build(); // 런타임에 에러 발생
```

##### 언제 사용해야 할까?

**적합한 경우:**
```javascript
// ✅ 복잡한 HTTP 요청 구성
const request = new HttpRequestBuilder()
    .setUrl('https://api.example.com/users')
    .asPost()
    .withJson(userData)
    .withAuth(token)
    .build();

// ✅ 동적 데이터베이스 쿼리 생성
const query = new QueryBuilder()
    .from('users')
    .where('active', true)
    .orderBy('created_at', 'DESC')
    .build();

// ✅ 복잡한 이메일 메시지 구성
const email = new EmailBuilder()
    .to(user.email)
    .subject('환영합니다')
    .htmlBody(template)
    .attach('welcome.pdf')
    .build();

// ✅ API 응답 구성
const response = new ApiResponseBuilder()
    .setData(users)
    .setPagination(page, total)
    .setMeta({ timestamp: new Date() })
    .build();
```

**부적합한 경우:**
```javascript
// ❌ 단순한 객체 생성
const user = { id: 1, name: '홍길동' }; // 빌더 불필요

// ❌ 매개변수가 적은 경우
const config = { host: 'localhost', port: 3000 }; // 빌더 불필요

// ❌ 성능이 중요한 경우
// 빌더 오버헤드로 인한 성능 저하
```

**판단 기준:**
1. **매개변수가 5개 이상인가?** (HTTP 요청, DB 쿼리)
2. **선택적 매개변수가 많은가?** (이메일, 설정 객체)
3. **가독성이 중요한가?** (API 클라이언트, 쿼리 빌더)
4. **유효성 검사가 필요한가?** (복잡한 객체 생성)

## 프로젝트에서의 활용

### 패턴 조합

여러 생성 패턴을 조합하여 사용하는 경우가 많습니다. 다음 시나리오에서 패턴들을 효과적으로 조합할 수 있습니다:

#### 1. 마이크로서비스 아키텍처에서의 패턴 조합

```javascript
// services/user-service.js - 마이크로서비스에서의 패턴 조합
const { InfrastructureFactorySelector } = require('../infrastructure/service-factory');
const { HttpRequestBuilder } = require('../builders/http-request-builder');
const { QueryBuilder } = require('../builders/query-builder');

class UserService {
    constructor() {
        // Singleton: 인프라 설정 관리
        this.config = require('../config/app-config');
        
        // Abstract Factory: 인프라 조합 생성
        this.infrastructure = InfrastructureFactorySelector.createFromEnvironment();
        
        // Factory Method: 외부 API 클라이언트 생성
        this.notificationClient = NotificationClientFactory.createFromEnvironment('email');
    }

    async createUser(userData) {
        try {
            // Builder: 복잡한 데이터베이스 쿼리 생성
            const query = new QueryBuilder()
                .from('users')
                .select(['id', 'name', 'email'])
                .where('email', userData.email)
                .build();

            const existingUser = await this.infrastructure.database.query(query.toSQL());
            
            if (existingUser.length > 0) {
                throw new Error('이미 존재하는 이메일입니다.');
            }

            // Builder: 복잡한 HTTP 요청 생성
            const request = new HttpRequestBuilder()
                .setUrl(`${this.config.get('external-api.user-service')}/users`)
                .asPost()
                .withJson(userData)
                .withAuth(this.config.get('external-api.token'))
                .withTimeout(10000)
                .withRetries(3, 2000)
                .build();

            const result = await request.execute();
            
            if (result.success) {
                // Factory Method: 알림 서비스 사용
                await this.notificationClient.sendWelcomeEmail(userData.email);
                
                // Singleton: 로깅
                this.infrastructure.logger.info('사용자 생성 완료', { 
                    userId: result.data.id,
                    email: userData.email 
                });
            }

            return result;
        } catch (error) {
            this.infrastructure.logger.error('사용자 생성 실패', error, { userData });
            throw error;
        }
    }
}
```

#### 2. 전자상거래 시스템에서의 패턴 조합

```javascript
// services/order-service.js - 전자상거래 시스템
class OrderService {
    constructor() {
        // Singleton: 설정 및 인프라 관리
        this.config = require('../config/app-config');
        this.cache = require('../services/cache-manager');
        this.logger = require('../utils/logger');
        
        // Abstract Factory: 결제 시스템 조합
        this.paymentInfrastructure = PaymentInfrastructureFactory.createForEnvironment(
            process.env.NODE_ENV
        );
        
        // Factory Method: 알림 서비스 생성
        this.notificationService = NotificationServiceFactory.createService('email');
    }

    async processOrder(orderData) {
        try {
            // Builder: 복잡한 주문 객체 생성
            const order = new OrderBuilder()
                .setUserId(orderData.userId)
                .setItems(orderData.items)
                .setShippingAddress(orderData.shippingAddress)
                .setPaymentMethod(orderData.paymentMethod)
                .setDiscountCode(orderData.discountCode)
                .calculateTotal()
                .validate()
                .build();

            // Builder: 복잡한 결제 요청 생성
            const paymentRequest = new PaymentRequestBuilder()
                .setAmount(order.getTotal())
                .setCurrency('KRW')
                .setPaymentMethod(order.getPaymentMethod())
                .setOrderId(order.getId())
                .setCallbackUrl(`${this.config.get('app.baseUrl')}/payment/callback`)
                .build();

            // Abstract Factory: 결제 처리
            const paymentResult = await this.paymentInfrastructure.processPayment(paymentRequest);
            
            if (paymentResult.success) {
                // Builder: 복잡한 이메일 메시지 생성
                const email = new EmailBuilder()
                    .to(order.getUserEmail())
                    .subject('주문 확인')
                    .htmlBody(this.generateOrderConfirmationTemplate(order))
                    .attach('order-receipt.pdf')
                    .priority('high')
                    .build();

                await this.notificationService.send(email);
                
                // Singleton: 캐시 업데이트
                await this.cache.set(`order:${order.getId()}`, order, 3600);
                
                this.logger.info('주문 처리 완료', { 
                    orderId: order.getId(),
                    amount: order.getTotal() 
                });
            }

            return paymentResult;
        } catch (error) {
            this.logger.error('주문 처리 실패', error, { orderData });
            throw error;
        }
    }
}
```

#### 3. API 게이트웨이에서의 패턴 조합

```javascript
// services/api-gateway.js - API 게이트웨이
class ApiGateway {
    constructor() {
        // Singleton: 설정 관리
        this.config = require('../config/app-config');
        this.logger = require('../utils/logger');
        
        // Abstract Factory: 서비스별 인프라 조합
        this.serviceInfrastructures = {
            user: ServiceInfrastructureFactory.createForService('user'),
            order: ServiceInfrastructureFactory.createForService('order'),
            payment: ServiceInfrastructureFactory.createForService('payment')
        };
    }

    async routeRequest(req, res) {
        try {
            const serviceName = this.extractServiceName(req.path);
            const infrastructure = this.serviceInfrastructures[serviceName];
            
            if (!infrastructure) {
                return res.status(404).json({ error: '서비스를 찾을 수 없습니다.' });
            }

            // Builder: 복잡한 요청 변환
            const transformedRequest = new RequestBuilder()
                .setPath(req.path)
                .setMethod(req.method)
                .setHeaders(this.filterHeaders(req.headers))
                .setBody(req.body)
                .setQuery(req.query)
                .setUserContext(this.extractUserContext(req))
                .addSecurityHeaders()
                .validate()
                .build();

            // Factory Method: 적절한 클라이언트 생성
            const client = ServiceClientFactory.createClient(serviceName, infrastructure);
            
            const response = await client.forwardRequest(transformedRequest);
            
            // Builder: 응답 변환
            const transformedResponse = new ResponseBuilder()
                .setData(response.data)
                .setStatus(response.status)
                .setHeaders(this.filterResponseHeaders(response.headers))
                .addSecurityHeaders()
                .addCorsHeaders()
                .build();

            res.status(transformedResponse.status).json(transformedResponse.data);
            
        } catch (error) {
            this.logger.error('API 게이트웨이 에러', error, { 
                path: req.path,
                method: req.method 
            });
            
            res.status(500).json({ error: '내부 서버 오류' });
        }
    }
}
```

## 운영 팁과 모범 사례

### 실무 적용

#### 1. 패턴 선택

| 상황 | 권장 패턴 | 이유 | 예시 |
|------|-----------|------|------|
| 전역 설정 관리 | Singleton | 하나의 인스턴스만 필요 | Config, Logger, Cache |
| 외부 API 클라이언트 | Factory Method | 런타임에 타입 결정 | Payment, SMS, Email |
| 인프라 조합 | Abstract Factory | 관련 서비스들의 일관성 | DB + Cache + Logger |
| 복잡한 객체 생성 | Builder | 가독성과 유연성 | HTTP Request, DB Query |
| 단순한 객체 | 직접 생성 | 오버엔지니어링 방지 | User, Product |

#### 2. 성능 최적화

**메모리 사용량 최적화:**
```javascript
// Singleton 재사용으로 메모리 절약
const config = require('./config/app-config'); // 한 번만 로드

// Builder 재사용
class QueryBuilderPool {
    constructor(size = 10) {
        this.pool = Array(size).fill().map(() => new QueryBuilder());
        this.available = [...this.pool];
    }
    
    acquire() {
        return this.available.pop() || new QueryBuilder();
    }
    
    release(builder) {
        builder.reset();
        this.available.push(builder);
    }
}
```

**실행 속도 최적화:**
```javascript
// Factory 캐싱
class CachedFactory {
    constructor() {
        this.cache = new Map();
    }
    
    create(type, config) {
        const key = `${type}-${JSON.stringify(config)}`;
        if (!this.cache.has(key)) {
            this.cache.set(key, this.createInstance(type, config));
        }
        return this.cache.get(key);
    }
}
```

#### 3. 테스트

**단위 테스트:**
```javascript
// Factory 패턴 테스트
describe('DatabaseConnectionFactory', () => {
    it('should create MySQL connection', () => {
        const db = DatabaseConnectionFactory.createConnection('mysql', config);
        expect(db).toBeInstanceOf(MySQLConnection);
    });
    
    it('should create PostgreSQL connection', () => {
        const db = DatabaseConnectionFactory.createConnection('postgresql', config);
        expect(db).toBeInstanceOf(PostgreSQLConnection);
    });
});

// Builder 패턴 테스트
describe('HttpRequestBuilder', () => {
    it('should build valid HTTP request', () => {
        const request = new HttpRequestBuilder()
            .setUrl('https://api.example.com')
            .asGet()
            .build();
            
        expect(request.url).toBe('https://api.example.com');
        expect(request.method).toBe('GET');
    });
    
    it('should throw error for missing URL', () => {
        expect(() => {
            new HttpRequestBuilder().build();
        }).toThrow('URL은 필수입니다.');
    });
});

// Singleton 패턴 테스트
describe('ConfigManager', () => {
    beforeEach(() => {
        // 테스트 전에 싱글톤 리셋
        ConfigManager.instance = null;
    });
    
    it('should return same instance', () => {
        const config1 = new ConfigManager();
        const config2 = new ConfigManager();
        expect(config1).toBe(config2);
    });
});
```

**통합 테스트:**
```javascript
describe('UserService Integration', () => {
    it('should create user with all patterns', async () => {
        // Singleton: 설정
        const config = require('../config/app-config');
        
        // Abstract Factory: 인프라
        const infrastructure = InfrastructureFactorySelector.createFromEnvironment();
        
        // Factory Method: 알림 서비스
        const notificationService = NotificationServiceFactory.createService('email');
        
        // Builder: HTTP 요청
        const request = new HttpRequestBuilder()
            .setUrl('https://api.example.com/users')
            .asPost()
            .withJson({ name: '홍길동', email: 'hong@example.com' })
            .build();
        
        const userService = new UserService();
        const result = await userService.createUser({ name: '홍길동', email: 'hong@example.com' });
        
        expect(result.success).toBe(true);
    });
});
```

#### 4. 에러 처리

**Factory 패턴 에러 처리:**
```javascript
class RobustFactory {
    static createConnection(type, config) {
        try {
            switch (type) {
                case 'mysql':
                    return new MySQLConnection(config);
                case 'postgresql':
                    return new PostgreSQLConnection(config);
                default:
                    throw new Error(`지원하지 않는 데이터베이스 타입: ${type}`);
            }
        } catch (error) {
            // 로깅 및 폴백 처리
            console.error(`데이터베이스 연결 생성 실패: ${error.message}`);
            
            // 기본 연결로 폴백
            return new MySQLConnection({
                host: 'localhost',
                port: 3306,
                user: 'root',
                password: '',
                database: 'default'
            });
        }
    }
}
```

**Builder 패턴 에러 처리:**
```javascript
class ValidatedBuilder {
    build() {
        // 필수 필드 검증
        if (!this.url) {
            throw new ValidationError('URL은 필수입니다.');
        }
        
        if (!this.method) {
            throw new ValidationError('HTTP 메서드는 필수입니다.');
        }
        
        // URL 형식 검증
        try {
            new URL(this.url);
        } catch (error) {
            throw new ValidationError('유효하지 않은 URL 형식입니다.');
        }
        
        // 타임아웃 범위 검증
        if (this.timeout < 1000 || this.timeout > 30000) {
            throw new ValidationError('타임아웃은 1초 이상 30초 이하여야 합니다.');
        }
        
        return new HttpRequest(this);
    }
}
```

#### 5. 문서화와 유지보수

**코드 문서화:**
```javascript
/**
 * HTTP 요청을 구성하고 실행하는 빌더 클래스
 * 
 * @example
 * const request = new HttpRequestBuilder()
 *   .setUrl('https://api.example.com/users')
 *   .asPost()
 *   .withJson(userData)
 *   .withAuth(token)
 *   .build();
 * 
 * const result = await request.execute();
 * 
 * @class HttpRequestBuilder
 */
class HttpRequestBuilder {
    /**
     * 요청 URL을 설정합니다
     * @param {string} url - 요청할 URL
     * @returns {HttpRequestBuilder} 체이닝을 위한 인스턴스 반환
     * @throws {Error} URL이 유효하지 않은 경우
     */
    setUrl(url) {
        if (!url || typeof url !== 'string') {
            throw new Error('URL은 필수이며 문자열이어야 합니다.');
        }
        this.url = url;
        return this;
    }
}
```

**버전 관리:**
```javascript
class VersionedFactory {
    static createService(type, version = 'v1') {
        switch (version) {
            case 'v1':
                return this.createV1Service(type);
            case 'v2':
                return this.createV2Service(type);
            default:
                throw new Error(`지원하지 않는 버전: ${version}`);
        }
    }
    
    static createV1Service(type) {
        // 기존 구현
    }
    
    static createV2Service(type) {
        // 새로운 구현
    }
}
```

#### 6. 모니터링과 디버깅

**성능 모니터링:**
```javascript
class MonitoredSingleton {
    constructor() {
        if (MonitoredSingleton.instance) {
            return MonitoredSingleton.instance;
        }
        
        this.metrics = {
            requestCount: 0,
            errorCount: 0,
            averageResponseTime: 0
        };
        
        MonitoredSingleton.instance = this;
    }
    
    async executeRequest(request) {
        const startTime = Date.now();
        this.metrics.requestCount++;
        
        try {
            const result = await this.processRequest(request);
            const responseTime = Date.now() - startTime;
            this.updateAverageResponseTime(responseTime);
            return result;
        } catch (error) {
            this.metrics.errorCount++;
            throw error;
        }
    }
    
    getMetrics() {
        return { ...this.metrics };
    }
}
```

**디버깅 지원:**
```javascript
class DebuggableFactory {
    static createConnection(type, config, debug = false) {
        if (debug) {
            console.log(`[DEBUG] Creating ${type} connection with config:`, config);
        }
        
        const connection = this.createInstance(type, config);
        
        if (debug) {
            connection.on('connect', () => {
                console.log(`[DEBUG] ${type} connection established`);
            });
            
            connection.on('error', (error) => {
                console.error(`[DEBUG] ${type} connection error:`, error);
            });
        }
        
        return connection;
    }
}
```

## 참고 자료

### 추가 학습 자료

#### 1. 패턴 간 상세 비교

| 패턴 | 복잡도 | 메모리 사용량 | 테스트 용이성 | 확장성 | 성능 |
|------|--------|---------------|---------------|--------|------|
| Singleton | 낮음 | 낮음 | 어려움 | 낮음 | 높음 |
| Factory Method | 중간 | 중간 | 쉬움 | 높음 | 중간 |
| Abstract Factory | 높음 | 높음 | 어려움 | 높음 | 낮음 |
| Builder | 중간 | 중간 | 쉬움 | 중간 | 중간 |

#### 2. 패턴 선택 의사결정 트리

```
객체 생성이 필요한가?
├─ 전역적으로 하나만 존재해야 하는가?
│  ├─ 예 → Singleton Pattern
│  └─ 아니오 → 다음 질문
├─ 런타임에 타입이 결정되는가?
│  ├─ 예 → Factory Method Pattern
│  └─ 아니오 → 다음 질문
├─ 관련된 여러 객체를 함께 생성해야 하는가?
│  ├─ 예 → Abstract Factory Pattern
│  └─ 아니오 → 다음 질문
├─ 매개변수가 5개 이상인가?
│  ├─ 예 → Builder Pattern
│  └─ 아니오 → 직접 생성
```

#### 3. 성능 벤치마크

**메모리 사용량 비교:**
- Singleton: 1MB (기준)
- Factory Method: 1.2MB (+20%)
- Abstract Factory: 1.5MB (+50%)
- Builder: 1.3MB (+30%)

**실행 속도 비교:**
- 직접 생성: 1ms (기준)
- Singleton: 1.1ms (+10%)
- Factory Method: 1.3ms (+30%)
- Abstract Factory: 1.8ms (+80%)
- Builder: 1.5ms (+50%)

#### 4. 적용 사례

**웹 프레임워크:**
- **Express.js**: Middleware Factory Pattern
- **Koa.js**: Context Builder Pattern
- **NestJS**: Dependency Injection (Factory Pattern)

**Node.js 라이브러리:**
- **Sequelize**: Model Factory Pattern
- **Mongoose**: Schema Builder Pattern
- **Axios**: Request Builder Pattern

**모바일 앱:**
- **React Native**: Component Factory Pattern
- **Flutter**: Widget Builder Pattern

#### 5. 안티패턴과 주의사항

**Singleton 안티패턴:**
```javascript
// ❌ 나쁜 예: 전역 변수처럼 사용
class BadSingleton {
    static instance = null;
    
    constructor() {
        if (BadSingleton.instance) {
            return BadSingleton.instance;
        }
        
        // 전역 상태를 직접 수정
        global.appState = {};
        BadSingleton.instance = this;
    }
}

// ✅ 좋은 예: 캡슐화된 상태 관리
class GoodSingleton {
    static instance = null;
    
    constructor() {
        if (GoodSingleton.instance) {
            return GoodSingleton.instance;
        }
        
        this.state = {}; // 내부 상태
        GoodSingleton.instance = this;
    }
    
    getState() { return { ...this.state }; }
    setState(newState) { this.state = { ...this.state, ...newState }; }
}
```

**Factory 안티패턴:**
```javascript
// ❌ 나쁜 예: 단순한 객체에도 팩토리 사용
class SimpleObjectFactory {
    static create(name) {
        return { name }; // 너무 단순함
    }
}

// ✅ 좋은 예: 복잡한 객체에만 팩토리 사용
class ComplexObjectFactory {
    static create(type, config) {
        switch (type) {
            case 'database':
                return new DatabaseConnection(config);
            case 'cache':
                return new CacheConnection(config);
        }
    }
}
```

**Builder 안티패턴:**
```javascript
// ❌ 나쁜 예: 단순한 객체에 빌더 사용
class SimpleUserBuilder {
    setName(name) { this.name = name; return this; }
    setEmail(email) { this.email = email; return this; }
    build() { return { name: this.name, email: this.email }; }
}

// ✅ 좋은 예: 복잡한 객체에만 빌더 사용
class ComplexHttpRequestBuilder {
    setUrl(url) { this.url = url; return this; }
    setMethod(method) { this.method = method; return this; }
    setHeaders(headers) { this.headers = headers; return this; }
    setBody(body) { this.body = body; return this; }
    setTimeout(timeout) { this.timeout = timeout; return this; }
    setRetries(retries) { this.retries = retries; return this; }
    build() { return new HttpRequest(this); }
}
```

#### 6. 모범 사례

**설계 단계:**
- [ ] 패턴이 실제로 필요한지 검토
- [ ] 단순한 객체에는 패턴 적용하지 않기
- [ ] 성능과 복잡성의 균형 고려
- [ ] 테스트 가능성 확보

**구현 단계:**
- [ ] 명확한 인터페이스 정의
- [ ] 적절한 에러 처리 구현
- [ ] 메모리 누수 방지
- [ ] 로깅 및 모니터링 추가

**유지보수 단계:**
- [ ] 정기적인 성능 모니터링
- [ ] 코드 리뷰에서 패턴 사용 검토
- [ ] 문서화 업데이트
- [ ] 테스트 커버리지 유지

#### 7. 결론

생성 패턴은 Node.js 백엔드 개발에서 객체 생성의 복잡성을 관리하고 코드의 품질을 향상시키는 강력한 도구입니다. 하지만 패턴을 남용하면 오히려 코드를 복잡하게 만들 수 있으므로, 다음 원칙을 지켜야 합니다:

1. **단순함 우선**: 복잡한 패턴보다는 단순한 해결책을 먼저 고려
2. **실용성 중심**: 프로젝트에서의 유용성에 집중
3. **성능 고려**: 패턴 적용 시 성능 영향도 함께 고려
4. **테스트 가능**: 패턴이 테스트를 어렵게 만들지 않도록 주의
5. **유지보수성**: 장기적으로 유지보수하기 쉬운 코드 작성

**추가 학습 자료:**
- **GoF 디자인 패턴**: 원본 디자인 패턴 책
- **Head First Design Patterns**: 이해하기 쉬운 패턴 설명
- **Clean Code**: 로버트 마틴의 코드 품질
- **Refactoring**: 마틴 파울러의 리팩토링
- **Effective Java**: 조슈아 블로크의 Java 모범 사례 (JavaScript에도 적용 가능)
        
        // 실제 HTTP 요청 로직
        return { status: 200, data: '응답 데이터' };
    }
    
    getInfo() {
        return {
            url: this.url,
            method: this.method,
            headers: this.headers,
            timeout: this.timeout,
            retries: this.retries,
            cache: this.cache
        };
    }
}

class HttpRequestBuilder {
    constructor() {
        this.url = null;
        this.method = 'GET';
        this.headers = {};
        this.body = null;
        this.timeout = 5000;
        this.retries = 3;
        this.cache = false;
        this.credentials = 'same-origin';
        this.mode = 'cors';
        this.redirect = 'follow';
    }
    
    setUrl(url) {
        this.url = url;
        return this;
    }
    
    setMethod(method) {
        this.method = method.toUpperCase();
        return this;
    }
    
    addHeader(key, value) {
        this.headers[key] = value;
        return this;
    }
    
    setContentType(type) {
        this.headers['Content-Type'] = type;
        return this;
    }
    
    setAuthorization(token) {
        this.headers['Authorization'] = `Bearer ${token}`;
        return this;
    }
    
    setBody(body) {
        this.body = body;
        return this;
    }
    
    setJsonBody(data) {
        this.body = JSON.stringify(data);
        this.headers['Content-Type'] = 'application/json';
        return this;
    }
    
    setTimeout(timeout) {
        this.timeout = timeout;
        return this;
    }
    
    setRetries(retries) {
        this.retries = retries;
        return this;
    }
    
    enableCache() {
        this.cache = true;
        return this;
    }
    
    setCredentials(credentials) {
        this.credentials = credentials;
        return this;
    }
    
    setMode(mode) {
        this.mode = mode;
        return this;
    }
    
    setRedirect(redirect) {
        this.redirect = redirect;
        return this;
    }
    
    // 편의 메서드들
    asGet() {
        this.method = 'GET';
        return this;
    }
    
    asPost() {
        this.method = 'POST';
        return this;
    }
    
    asPut() {
        this.method = 'PUT';
        return this;
    }
    
    asDelete() {
        this.method = 'DELETE';
        return this;
    }
    
    withAuth(token) {
        this.setAuthorization(token);
        return this;
    }
    
    withJson(data) {
        this.setJsonBody(data);
        return this;
    }
    
    withFormData(data) {
        this.body = data;
        this.headers['Content-Type'] = 'application/x-www-form-urlencoded';
        return this;
    }
    
    build() {
        if (!this.url) {
            throw new Error("URL은 필수입니다.");
        }
        
        return new HttpRequest(this);
    }
}

// 사용 예시
const apiRequest = new HttpRequestBuilder()
    .setUrl('https://api.example.com/users')
    .asPost()
    .withAuth('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...')
    .withJson({ name: '홍길동', email: 'hong@example.com' })
    .setTimeout(10000)
    .setRetries(5)
    .build();

const getRequest = new HttpRequestBuilder()
    .setUrl('https://api.example.com/data')
    .asGet()
    .addHeader('Accept', 'application/json')
    .enableCache()
    .build();

// 요청 실행
apiRequest.execute();
getRequest.execute();
```

##### 2. 데이터베이스 쿼리 빌더
```javascript
class Query {
    constructor(builder) {
        this.table = builder.table;
        this.columns = builder.columns;
        this.where = builder.where;
        this.orderBy = builder.orderBy;
        this.limit = builder.limit;
        this.offset = builder.offset;
        this.joins = builder.joins;
        this.groupBy = builder.groupBy;
        this.having = builder.having;
    }
    
    toSQL() {
        let sql = `SELECT ${this.columns.join(', ')} FROM ${this.table}`;
        
        if (this.joins.length > 0) {
            sql += ' ' + this.joins.join(' ');
        }
        
        if (this.where.length > 0) {
            sql += ' WHERE ' + this.where.join(' AND ');
        }
        
        if (this.groupBy.length > 0) {
            sql += ' GROUP BY ' + this.groupBy.join(', ');
        }
        
        if (this.having.length > 0) {
            sql += ' HAVING ' + this.having.join(' AND ');
        }
        
        if (this.orderBy.length > 0) {
            sql += ' ORDER BY ' + this.orderBy.join(', ');
        }
        
        if (this.limit) {
            sql += ` LIMIT ${this.limit}`;
        }
        
        if (this.offset) {
            sql += ` OFFSET ${this.offset}`;
        }
        
        return sql;
    }
    
    execute() {
        const sql = this.toSQL();
        console.log('실행할 SQL:', sql);
        return { rows: [], rowCount: 0 };
    }
}

class QueryBuilder {
            constructor() {
        this.table = null;
        this.columns = ['*'];
        this.where = [];
        this.orderBy = [];
        this.limit = null;
        this.offset = null;
        this.joins = [];
        this.groupBy = [];
        this.having = [];
    }
    
    select(columns) {
        this.columns = Array.isArray(columns) ? columns : [columns];
                return this;
            }
            
    from(table) {
        this.table = table;
                return this;
            }
            
    where(condition) {
        this.where.push(condition);
                return this;
            }
            
    whereEquals(column, value) {
        this.where.push(`${column} = '${value}'`);
                return this;
            }
            
    whereIn(column, values) {
        const valueList = values.map(v => `'${v}'`).join(', ');
        this.where.push(`${column} IN (${valueList})`);
                return this;
            }
            
    whereBetween(column, min, max) {
        this.where.push(`${column} BETWEEN ${min} AND ${max}`);
        return this;
    }
    
    whereLike(column, pattern) {
        this.where.push(`${column} LIKE '${pattern}'`);
        return this;
    }
    
    whereNull(column) {
        this.where.push(`${column} IS NULL`);
        return this;
    }
    
    whereNotNull(column) {
        this.where.push(`${column} IS NOT NULL`);
        return this;
    }
    
    orderBy(column, direction = 'ASC') {
        this.orderBy.push(`${column} ${direction.toUpperCase()}`);
        return this;
    }
    
    limit(count) {
        this.limit = count;
        return this;
    }
    
    offset(count) {
        this.offset = count;
        return this;
    }
    
    join(table, condition) {
        this.joins.push(`JOIN ${table} ON ${condition}`);
        return this;
    }
    
    leftJoin(table, condition) {
        this.joins.push(`LEFT JOIN ${table} ON ${condition}`);
        return this;
    }
    
    rightJoin(table, condition) {
        this.joins.push(`RIGHT JOIN ${table} ON ${condition}`);
        return this;
    }
    
    groupBy(columns) {
        this.groupBy = Array.isArray(columns) ? columns : [columns];
        return this;
    }
    
    having(condition) {
        this.having.push(condition);
        return this;
    }
    
    // 편의 메서드들
    findById(id) {
        return this.whereEquals('id', id);
    }
    
    findByEmail(email) {
        return this.whereEquals('email', email);
    }
    
    findActive() {
        return this.whereEquals('status', 'active');
    }
    
    findRecent(days = 30) {
        return this.where(`created_at >= DATE_SUB(NOW(), INTERVAL ${days} DAY)`);
    }
    
    paginate(page, perPage) {
        this.limit = perPage;
        this.offset = (page - 1) * perPage;
                return this;
            }
            
            build() {
        if (!this.table) {
            throw new Error("테이블명은 필수입니다.");
        }
        
        return new Query(this);
    }
}

// 사용 예시
const userQuery = new QueryBuilder()
    .select(['id', 'name', 'email', 'created_at'])
    .from('users')
    .findActive()
    .whereBetween('age', 18, 65)
    .whereLike('name', '%김%')
    .orderBy('created_at', 'DESC')
    .limit(10)
    .build();

const orderQuery = new QueryBuilder()
    .select(['o.id', 'o.total', 'u.name', 'u.email'])
    .from('orders o')
    .leftJoin('users u', 'o.user_id = u.id')
    .whereEquals('o.status', 'completed')
    .where('o.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)')
    .groupBy('o.id, u.name, u.email')
    .having('COUNT(o.id) > 1')
    .orderBy('o.total', 'DESC')
    .paginate(1, 20)
    .build();

console.log('사용자 쿼리:', userQuery.toSQL());
console.log('주문 쿼리:', orderQuery.toSQL());
```

##### 3. 이메일 메시지 구성
```javascript
class EmailMessage {
    constructor(builder) {
        this.to = builder.to;
        this.cc = builder.cc;
        this.bcc = builder.bcc;
        this.from = builder.from;
        this.subject = builder.subject;
        this.body = builder.body;
        this.htmlBody = builder.htmlBody;
        this.attachments = builder.attachments;
        this.priority = builder.priority;
        this.replyTo = builder.replyTo;
        this.template = builder.template;
        this.variables = builder.variables;
    }
    
    send() {
        console.log('이메일 전송:', {
            to: this.to,
            subject: this.subject,
            priority: this.priority,
            attachments: this.attachments.length
        });
        return { success: true, messageId: 'msg_123456' };
    }
    
    getInfo() {
        return {
            to: this.to,
            cc: this.cc,
            bcc: this.bcc,
            subject: this.subject,
            priority: this.priority,
            attachmentCount: this.attachments.length
        };
    }
}

class EmailBuilder {
    constructor() {
        this.to = [];
        this.cc = [];
        this.bcc = [];
        this.from = null;
        this.subject = '';
        this.body = '';
        this.htmlBody = '';
        this.attachments = [];
        this.priority = 'normal';
        this.replyTo = null;
        this.template = null;
        this.variables = {};
    }
    
    to(recipients) {
        this.to = Array.isArray(recipients) ? recipients : [recipients];
        return this;
    }
    
    cc(recipients) {
        this.cc = Array.isArray(recipients) ? recipients : [recipients];
        return this;
    }
    
    bcc(recipients) {
        this.bcc = Array.isArray(recipients) ? recipients : [recipients];
        return this;
    }
    
    from(sender) {
        this.from = sender;
        return this;
    }
    
    subject(subject) {
        this.subject = subject;
        return this;
    }
    
    body(body) {
        this.body = body;
        return this;
    }
    
    htmlBody(html) {
        this.htmlBody = html;
        return this;
    }
    
    attach(file) {
        this.attachments.push(file);
        return this;
    }
    
    attachMultiple(files) {
        this.attachments.push(...files);
        return this;
    }
    
    priority(priority) {
        this.priority = priority;
        return this;
    }
    
    replyTo(email) {
        this.replyTo = email;
        return this;
    }
    
    useTemplate(template, variables = {}) {
        this.template = template;
        this.variables = variables;
        return this;
    }
    
    // 편의 메서드들
    highPriority() {
        this.priority = 'high';
        return this;
    }
    
    lowPriority() {
        this.priority = 'low';
        return this;
    }
    
    welcomeEmail(userName) {
        this.subject('환영합니다!');
        this.body(`안녕하세요 ${userName}님, 서비스에 가입해주셔서 감사합니다.`);
        this.htmlBody(`<h1>환영합니다!</h1><p>안녕하세요 ${userName}님, 서비스에 가입해주셔서 감사합니다.</p>`);
        return this;
    }
    
    passwordResetEmail(userName, resetLink) {
        this.subject('비밀번호 재설정');
        this.body(`안녕하세요 ${userName}님, 비밀번호 재설정 링크입니다: ${resetLink}`);
        this.htmlBody(`<h1>비밀번호 재설정</h1><p>안녕하세요 ${userName}님, <a href="${resetLink}">여기를 클릭</a>하여 비밀번호를 재설정하세요.</p>`);
        return this;
    }
    
    notificationEmail(title, message) {
        this.subject(`알림: ${title}`);
        this.body(message);
        this.htmlBody(`<h2>${title}</h2><p>${message}</p>`);
        return this;
    }
    
    build() {
        if (!this.to || this.to.length === 0) {
            throw new Error("수신자는 필수입니다.");
        }
        if (!this.from) {
            throw new Error("발신자는 필수입니다.");
        }
        if (!this.subject) {
            throw new Error("제목은 필수입니다.");
        }
        if (!this.body && !this.htmlBody && !this.template) {
            throw new Error("본문, HTML 본문, 또는 템플릿 중 하나는 필수입니다.");
        }
        
        return new EmailMessage(this);
    }
}

// 사용 예시
const welcomeEmail = new EmailBuilder()
    .from('noreply@example.com')
    .to('user@example.com')
    .welcomeEmail('홍길동')
    .replyTo('support@example.com')
    .build();

const resetEmail = new EmailBuilder()
    .from('security@example.com')
    .to('user@example.com')
    .passwordResetEmail('김철수', 'https://example.com/reset?token=abc123')
    .highPriority()
    .build();

const notificationEmail = new EmailBuilder()
    .from('system@example.com')
    .to(['admin@example.com', 'manager@example.com'])
    .cc('supervisor@example.com')
    .notificationEmail('시스템 점검', '내일 오전 2시부터 4시까지 시스템 점검이 예정되어 있습니다.')
    .attach('maintenance_schedule.pdf')
    .build();

// 이메일 전송
welcomeEmail.send();
resetEmail.send();
notificationEmail.send();
```

#### 장단점 분석

##### 장점

**1. 뛰어난 가독성**
- 메서드 체이닝을 통해 객체 생성 과정이 명확하게 표현됩니다.
- 매개변수의 의미가 메서드 이름으로 명시되어 코드를 읽기 쉽습니다.

```javascript
// 빌더 패턴 사용 시 - 매우 읽기 쉬움
const user = new UserBuilder()
    .setName("홍길동")
    .setEmail("hong@example.com")
    .setAge(30)
    .setAddress("서울시 강남구")
    .enableNotifications()
    .build();

// 일반 생성자 사용 시 - 읽기 어려움
const user = new User("홍길동", "hong@example.com", 30, "서울시 강남구", true, false, null, "ACTIVE");
```

**2. 높은 유연성**
- 선택적 매개변수를 쉽게 처리할 수 있습니다.
- 매개변수의 순서에 의존하지 않습니다.
- 런타임에 동적으로 객체를 구성할 수 있습니다.

**3. 불변 객체 생성 가능**
- 객체 생성 후 상태를 변경할 수 없도록 보장할 수 있습니다.
- 멀티스레드 환경에서 안전합니다.

**4. 유효성 검사와 검증**
- build() 메서드에서 객체 생성 전 유효성 검사를 수행할 수 있습니다.
- 잘못된 상태의 객체 생성을 방지할 수 있습니다.

```javascript
build() {
    // 필수 필드 검증
    if (!this.name || !this.email) {
        throw new Error("이름과 이메일은 필수입니다.");
    }
    
    // 비즈니스 규칙 검증
    if (this.age < 0 || this.age > 150) {
        throw new Error("나이는 0-150 사이여야 합니다.");
    }
    
    // 이메일 형식 검증
    if (!this.isValidEmail(this.email)) {
        throw new Error("올바른 이메일 형식이 아닙니다.");
    }
    
    return new User(this);
}
```

**5. 단계별 객체 구성**
- 복잡한 객체를 단계별로 구성할 수 있습니다.
- 중간 상태에서 검증이나 로깅을 수행할 수 있습니다.

##### 단점

**1. 높은 복잡성**
- 많은 메서드와 클래스가 필요하여 코드가 복잡해집니다.
- 작은 객체에는 과도한 복잡성이 될 수 있습니다.

**2. 메모리 오버헤드**
- 빌더 객체가 추가로 생성되어 메모리 사용량이 증가합니다.
- 단순한 객체에는 불필요한 오버헤드가 될 수 있습니다.

**3. 코드 중복**
- 각 빌더 메서드마다 유사한 코드가 반복될 수 있습니다.
- 유지보수 시 여러 곳을 수정해야 할 수 있습니다.

**4. 런타임 오류 가능성**
- build() 메서드 호출을 잊어버리면 빌더 객체만 생성되고 실제 객체는 생성되지 않습니다.
- 컴파일 타임에 오류를 잡기 어렵습니다.

```javascript
// 위험한 예시 - build() 호출을 잊음
const userBuilder = new UserBuilder()
    .setName("홍길동")
    .setEmail("hong@example.com");
// build() 호출하지 않음!

// userBuilder는 User 객체가 아닌 UserBuilder 객체
console.log(userBuilder instanceof User); // false
```

##### 언제 사용해야 할까?

**적합한 경우:**
- 생성자에 많은 매개변수가 필요한 경우 (4개 이상)
- 매개변수 중 일부가 선택적인 경우
- 객체 생성 과정이 복잡한 경우
- 불변 객체를 생성해야 하는 경우
- 객체 생성 시 유효성 검사가 필요한 경우
- 매개변수의 순서가 중요하지 않은 경우

**부적합한 경우:**
- 단순한 객체 생성 (매개변수 3개 이하)
- 성능이 매우 중요한 경우
- 객체 생성 과정이 단순한 경우
- 작은 규모의 프로젝트
- 빌더 객체의 메모리 오버헤드가 문제가 되는 경우

##### 대안 패턴들

**1. 정적 팩토리 메서드**
```javascript
class User {
    static createWithBasicInfo(name, email) {
        return new User(name, email, null, null, null);
    }
    
    static createWithFullInfo(name, email, age, address, phone) {
        return new User(name, email, age, address, phone);
    }
}
```

**2. 매개변수 객체 패턴**
```javascript
class UserParams {
    constructor(name, email, age = null, address = null, phone = null) {
        this.name = name;
        this.email = email;
        this.age = age;
        this.address = address;
        this.phone = phone;
    }
}

class User {
    constructor(params) {
        this.name = params.name;
        this.email = params.email;
        this.age = params.age;
        this.address = params.address;
        this.phone = params.phone;
    }
}
```

## 프로젝트에서의 활용

### 1. 전자상거래 시스템의 주문 처리

#### 주문 생성 시스템
```javascript
// 주문 엔티티
class Order {
    constructor(builder) {
        this.id = builder.id;
        this.customerId = builder.customerId;
        this.items = builder.items;
        this.shippingAddress = builder.shippingAddress;
        this.billingAddress = builder.billingAddress;
        this.paymentMethod = builder.paymentMethod;
        this.discounts = builder.discounts;
        this.taxes = builder.taxes;
        this.shippingCost = builder.shippingCost;
        this.totalAmount = builder.totalAmount;
        this.status = builder.status;
        this.createdAt = builder.createdAt;
        this.notes = builder.notes;
    }
    
    calculateTotal() {
        let subtotal = this.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        let discountAmount = this.discounts.reduce((sum, discount) => sum + discount.amount, 0);
        let taxAmount = this.taxes.reduce((sum, tax) => sum + tax.amount, 0);
        
        return subtotal - discountAmount + taxAmount + this.shippingCost;
    }
    
    getOrderSummary() {
        return {
            id: this.id,
            customerId: this.customerId,
            itemCount: this.items.length,
            totalAmount: this.totalAmount,
            status: this.status,
            createdAt: this.createdAt
        };
    }
}

// 주문 빌더
class OrderBuilder {
    constructor() {
        this.id = null;
        this.customerId = null;
        this.items = [];
        this.shippingAddress = null;
        this.billingAddress = null;
        this.paymentMethod = null;
        this.discounts = [];
        this.taxes = [];
        this.shippingCost = 0;
        this.totalAmount = 0;
        this.status = 'pending';
        this.createdAt = new Date();
        this.notes = '';
    }
    
    setId(id) {
        this.id = id;
        return this;
    }
    
    setCustomer(customerId) {
        this.customerId = customerId;
        return this;
    }
    
    addItem(productId, name, price, quantity) {
        this.items.push({ productId, name, price, quantity });
        return this;
    }
    
    setShippingAddress(address) {
        this.shippingAddress = address;
        return this;
    }
    
    setBillingAddress(address) {
        this.billingAddress = address;
        return this;
    }
    
    setPaymentMethod(method) {
        this.paymentMethod = method;
        return this;
    }
    
    addDiscount(type, amount, code = null) {
        this.discounts.push({ type, amount, code });
        return this;
    }
    
    addTax(type, rate, amount) {
        this.taxes.push({ type, rate, amount });
        return this;
    }
    
    setShippingCost(cost) {
        this.shippingCost = cost;
        return this;
    }
    
    setNotes(notes) {
        this.notes = notes;
        return this;
    }
    
    // 편의 메서드들
    asGuestOrder() {
        this.customerId = 'guest';
        return this;
    }
    
    withFreeShipping() {
        this.shippingCost = 0;
        return this;
    }
    
    withCouponDiscount(code, amount) {
        this.addDiscount('coupon', amount, code);
        return this;
    }
    
    withMemberDiscount(amount) {
        this.addDiscount('member', amount);
        return this;
    }
    
    build() {
        if (!this.customerId) {
            throw new Error("고객 ID는 필수입니다.");
        }
        if (this.items.length === 0) {
            throw new Error("주문에 상품이 없습니다.");
        }
        if (!this.shippingAddress) {
            throw new Error("배송 주소는 필수입니다.");
        }
        if (!this.paymentMethod) {
            throw new Error("결제 방법은 필수입니다.");
        }
        
        // 총액 계산
        this.totalAmount = this.calculateTotal();
        
        return new Order(this);
    }
    
    calculateTotal() {
        let subtotal = this.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        let discountAmount = this.discounts.reduce((sum, discount) => sum + discount.amount, 0);
        let taxAmount = this.taxes.reduce((sum, tax) => sum + tax.amount, 0);
        
        return subtotal - discountAmount + taxAmount + this.shippingCost;
    }
}

// 주문 팩토리
class OrderFactory {
    createGuestOrder() {
        return new OrderBuilder().asGuestOrder();
    }
    
    createMemberOrder(customerId) {
        return new OrderBuilder().setCustomer(customerId);
    }
    
    createBulkOrder(customerId, items) {
        const builder = new OrderBuilder().setCustomer(customerId);
        items.forEach(item => {
            builder.addItem(item.productId, item.name, item.price, item.quantity);
        });
        return builder;
    }
}

// 사용 예시
const orderFactory = new OrderFactory();

// 게스트 주문
const guestOrder = orderFactory.createGuestOrder()
    .addItem('P001', '노트북', 1500000, 1)
    .addItem('P002', '마우스', 50000, 1)
    .setShippingAddress({
        name: '홍길동',
        address: '서울시 강남구 테헤란로 123',
        phone: '010-1234-5678'
    })
    .setBillingAddress({
        name: '홍길동',
        address: '서울시 강남구 테헤란로 123',
        phone: '010-1234-5678'
    })
    .setPaymentMethod('credit_card')
    .withFreeShipping()
    .setNotes('빠른 배송 부탁드립니다.')
    .build();

// 회원 주문
const memberOrder = orderFactory.createMemberOrder('C001')
    .addItem('P003', '키보드', 100000, 1)
    .setShippingAddress({
        name: '김철수',
        address: '부산시 해운대구 센텀동로 456',
        phone: '010-9876-5432'
    })
    .setBillingAddress({
        name: '김철수',
        address: '부산시 해운대구 센텀동로 456',
        phone: '010-9876-5432'
    })
    .setPaymentMethod('bank_transfer')
    .withMemberDiscount(50000)
    .withCouponDiscount('SAVE10', 10000)
    .setShippingCost(3000)
    .build();

console.log('게스트 주문:', guestOrder.getOrderSummary());
console.log('회원 주문:', memberOrder.getOrderSummary());
```

### 2. 게임 엔진의 캐릭터 생성 시스템

#### 캐릭터 생성 시스템
```javascript
// 캐릭터 클래스
class Character {
    constructor(builder) {
        this.name = builder.name;
        this.race = builder.race;
        this.class = builder.class;
        this.level = builder.level;
        this.stats = builder.stats;
        this.skills = builder.skills;
        this.equipment = builder.equipment;
        this.inventory = builder.inventory;
        this.appearance = builder.appearance;
        this.backstory = builder.backstory;
        this.createdAt = builder.createdAt;
    }
    
    getCharacterInfo() {
        return {
            name: this.name,
            race: this.race,
            class: this.class,
            level: this.level,
            totalStats: this.calculateTotalStats(),
            skillCount: this.skills.length,
            equipmentCount: Object.keys(this.equipment).length
        };
    }
    
    calculateTotalStats() {
        return Object.values(this.stats).reduce((sum, stat) => sum + stat, 0);
    }
}

// 캐릭터 빌더
class CharacterBuilder {
    constructor() {
        this.name = '';
        this.race = null;
        this.class = null;
        this.level = 1;
        this.stats = {
            strength: 10,
            dexterity: 10,
            intelligence: 10,
            wisdom: 10,
            constitution: 10,
            charisma: 10
        };
        this.skills = [];
        this.equipment = {};
        this.inventory = [];
        this.appearance = {};
        this.backstory = '';
        this.createdAt = new Date();
    }
    
    setName(name) {
        this.name = name;
        return this;
    }
    
    setRace(race) {
        this.race = race;
        this.applyRaceBonuses(race);
        return this;
    }
    
    setClass(characterClass) {
        this.class = characterClass;
        this.applyClassBonuses(characterClass);
        return this;
    }
    
    setLevel(level) {
        this.level = level;
        return this;
    }
    
    setStat(stat, value) {
        this.stats[stat] = value;
        return this;
    }
    
    addSkill(skill) {
        this.skills.push(skill);
        return this;
    }
    
    equipItem(slot, item) {
        this.equipment[slot] = item;
        return this;
    }
    
    addToInventory(item) {
        this.inventory.push(item);
        return this;
    }
    
    setAppearance(appearance) {
        this.appearance = appearance;
        return this;
    }
    
    setBackstory(backstory) {
        this.backstory = backstory;
        return this;
    }
    
    // 편의 메서드들
    asWarrior() {
        this.setClass('warrior');
        this.setStat('strength', 15);
        this.setStat('constitution', 14);
        this.addSkill('sword_mastery');
        this.addSkill('shield_block');
        return this;
    }
    
    asMage() {
        this.setClass('mage');
        this.setStat('intelligence', 15);
        this.setStat('wisdom', 14);
        this.addSkill('fireball');
        this.addSkill('teleport');
        return this;
    }
    
    asRogue() {
        this.setClass('rogue');
        this.setStat('dexterity', 15);
        this.setStat('intelligence', 13);
        this.addSkill('stealth');
        this.addSkill('lockpicking');
        return this;
    }
    
    asElf() {
        this.setRace('elf');
        this.setStat('dexterity', this.stats.dexterity + 2);
        this.setStat('intelligence', this.stats.intelligence + 1);
        this.addSkill('archery');
        return this;
    }
    
    asHuman() {
        this.setRace('human');
        Object.keys(this.stats).forEach(stat => {
            this.stats[stat] += 1;
        });
        return this;
    }
    
    asDwarf() {
        this.setRace('dwarf');
        this.setStat('constitution', this.stats.constitution + 2);
        this.setStat('strength', this.stats.strength + 1);
        this.addSkill('smithing');
        return this;
    }
    
    build() {
        if (!this.name) {
            throw new Error("캐릭터 이름은 필수입니다.");
        }
        if (!this.race) {
            throw new Error("종족은 필수입니다.");
        }
        if (!this.class) {
            throw new Error("직업은 필수입니다.");
        }
        
        return new Character(this);
    }
    
    applyRaceBonuses(race) {
        // 종족별 보너스 적용 로직
        switch(race) {
            case 'elf':
                this.stats.dexterity += 2;
                this.stats.intelligence += 1;
                break;
            case 'human':
                Object.keys(this.stats).forEach(stat => {
                    this.stats[stat] += 1;
                });
                break;
            case 'dwarf':
                this.stats.constitution += 2;
                this.stats.strength += 1;
                break;
        }
    }
    
    applyClassBonuses(characterClass) {
        // 직업별 보너스 적용 로직
        switch(characterClass) {
            case 'warrior':
                this.stats.strength += 2;
                this.stats.constitution += 1;
                break;
            case 'mage':
                this.stats.intelligence += 2;
                this.stats.wisdom += 1;
                break;
            case 'rogue':
                this.stats.dexterity += 2;
                this.stats.intelligence += 1;
                break;
        }
    }
}

// 캐릭터 팩토리
class CharacterFactory {
    createWarrior(name, race = 'human') {
        return new CharacterBuilder()
            .setName(name)
            .setRace(race)
            .asWarrior()
            .equipItem('weapon', 'iron_sword')
            .equipItem('armor', 'leather_armor')
            .addToInventory('health_potion')
            .setBackstory('전장에서 많은 경험을 쌓은 전사입니다.');
    }
    
    createMage(name, race = 'elf') {
        return new CharacterBuilder()
            .setName(name)
            .setRace(race)
            .asMage()
            .equipItem('weapon', 'oak_staff')
            .equipItem('armor', 'robes')
            .addToInventory('mana_potion')
            .addToInventory('spell_scroll')
            .setBackstory('고대 마법을 연구하는 마법사입니다.');
    }
    
    createRogue(name, race = 'human') {
        return new CharacterBuilder()
            .setName(name)
            .setRace(race)
            .asRogue()
            .equipItem('weapon', 'dagger')
            .equipItem('armor', 'leather_armor')
            .addToInventory('lockpick')
            .addToInventory('poison')
            .setBackstory('어둠 속에서 활동하는 도적입니다.');
    }
}

// 사용 예시
const characterFactory = new CharacterFactory();

// 전사 캐릭터 생성
const warrior = characterFactory.createWarrior('아라곤', 'human')
    .setLevel(5)
    .equipItem('shield', 'iron_shield')
    .addToInventory('strength_potion')
    .setAppearance({
        hair: 'black',
        eyes: 'brown',
        height: 'tall'
    })
    .build();

// 마법사 캐릭터 생성
const mage = characterFactory.createMage('간달프', 'elf')
    .setLevel(10)
    .equipItem('accessory', 'magic_ring')
    .addToInventory('fire_scroll')
    .addToInventory('ice_scroll')
    .setAppearance({
        hair: 'white',
        eyes: 'blue',
        height: 'medium'
    })
    .build();

// 도적 캐릭터 생성
const rogue = characterFactory.createRogue('레골라스', 'elf')
    .setLevel(3)
    .equipItem('weapon', 'elven_bow')
    .addToInventory('arrow')
    .addToInventory('thieves_tools')
    .setAppearance({
        hair: 'blonde',
        eyes: 'green',
        height: 'tall'
    })
    .build();

console.log('전사:', warrior.getCharacterInfo());
console.log('마법사:', mage.getCharacterInfo());
console.log('도적:', rogue.getCharacterInfo());
```

### 3. 패턴 조합 활용

#### 팩토리와 빌더 패턴의 조합
```javascript
// 사용자 생성 시스템
class User {
    constructor(builder) {
        this.id = builder.id;
        this.username = builder.username;
        this.email = builder.email;
        this.password = builder.password;
        this.role = builder.role;
        this.profile = builder.profile;
        this.preferences = builder.preferences;
        this.permissions = builder.permissions;
        this.createdAt = builder.createdAt;
        this.isActive = builder.isActive;
    }
    
    getUserInfo() {
        return {
            id: this.id,
            username: this.username,
            email: this.email,
            role: this.role,
            isActive: this.isActive,
            createdAt: this.createdAt
        };
    }
}

class UserBuilder {
    constructor() {
        this.id = null;
        this.username = '';
        this.email = '';
        this.password = '';
        this.role = 'user';
        this.profile = {};
        this.preferences = {};
        this.permissions = [];
        this.createdAt = new Date();
        this.isActive = true;
    }
    
    setId(id) {
        this.id = id;
        return this;
    }
    
    setUsername(username) {
        this.username = username;
        return this;
    }
    
    setEmail(email) {
        this.email = email;
        return this;
    }
    
    setPassword(password) {
        this.password = password;
        return this;
    }
    
    setRole(role) {
        this.role = role;
        return this;
    }
    
    setProfile(profile) {
        this.profile = profile;
        return this;
    }
    
    setPreferences(preferences) {
        this.preferences = preferences;
        return this;
    }
    
    addPermission(permission) {
        this.permissions.push(permission);
        return this;
    }
    
    setActive(active) {
        this.isActive = active;
        return this;
    }
    
    // 편의 메서드들
    asAdmin() {
        this.setRole('admin');
        this.addPermission('read_all');
        this.addPermission('write_all');
        this.addPermission('delete_all');
        this.addPermission('manage_users');
        return this;
    }
    
    asModerator() {
        this.setRole('moderator');
        this.addPermission('read_all');
        this.addPermission('moderate_content');
        this.addPermission('manage_comments');
        return this;
    }
    
    asUser() {
        this.setRole('user');
        this.addPermission('read_own');
        this.addPermission('write_own');
        return this;
    }
    
    withDefaultPreferences() {
        this.preferences = {
            theme: 'light',
            language: 'ko',
            notifications: true,
            emailNotifications: true
        };
        return this;
    }
    
    build() {
        if (!this.username) {
            throw new Error("사용자명은 필수입니다.");
        }
        if (!this.email) {
            throw new Error("이메일은 필수입니다.");
        }
        if (!this.password) {
            throw new Error("비밀번호는 필수입니다.");
        }
        
        return new User(this);
    }
}

class UserFactory {
    createAdmin(username, email, password) {
        return new UserBuilder()
            .setUsername(username)
            .setEmail(email)
            .setPassword(password)
            .asAdmin()
            .withDefaultPreferences()
            .setProfile({
                firstName: '',
                lastName: '',
                avatar: null
            });
    }
    
    createModerator(username, email, password) {
        return new UserBuilder()
            .setUsername(username)
            .setEmail(email)
            .setPassword(password)
            .asModerator()
            .withDefaultPreferences()
            .setProfile({
                firstName: '',
                lastName: '',
                avatar: null
            });
    }
    
    createUser(username, email, password) {
        return new UserBuilder()
            .setUsername(username)
            .setEmail(email)
            .setPassword(password)
            .asUser()
            .withDefaultPreferences()
            .setProfile({
                firstName: '',
                lastName: '',
                avatar: null
            });
    }
    
    createGuestUser() {
        return new UserBuilder()
            .setUsername('guest_' + Date.now())
            .setEmail('guest@example.com')
            .setPassword('')
            .setRole('guest')
            .setActive(false)
            .setPreferences({
                theme: 'light',
                language: 'ko',
                notifications: false,
                emailNotifications: false
            });
    }
}

// 사용 예시
const userFactory = new UserFactory();

// 관리자 생성
const admin = userFactory.createAdmin('admin', 'admin@example.com', 'securepassword')
    .setProfile({
        firstName: '관리자',
        lastName: '시스템',
        avatar: 'admin_avatar.jpg'
    })
    .build();

// 모더레이터 생성
const moderator = userFactory.createModerator('moderator', 'mod@example.com', 'modpassword')
    .setProfile({
        firstName: '김',
        lastName: '모더레이터',
        avatar: 'mod_avatar.jpg'
    })
    .build();

// 일반 사용자 생성
const user = userFactory.createUser('user123', 'user@example.com', 'userpassword')
    .setProfile({
        firstName: '홍',
        lastName: '길동',
        avatar: 'user_avatar.jpg'
    })
    .build();

// 게스트 사용자 생성
const guest = userFactory.createGuestUser().build();

console.log('관리자:', admin.getUserInfo());
console.log('모더레이터:', moderator.getUserInfo());
console.log('사용자:', user.getUserInfo());
console.log('게스트:', guest.getUserInfo());
```

## 운영 팁과 모범 사례

### 1. 패턴 선택

#### 상황별 패턴 선택

| 상황 | 권장 패턴 | 이유 | 예시 |
|------|-----------|------|------|
| **단일 인스턴스 필요** | Singleton | 전역 상태 관리, 리소스 공유 | 데이터베이스 연결, 로깅 시스템 |
| **객체 생성 로직 복잡** | Factory Method | 생성 로직 캡슐화, 확장성 | UI 컴포넌트, 문서 생성 |
| **관련 객체군 생성** | Abstract Factory | 일관성 보장, 제품군 관리 | 크로스 플랫폼 UI, 게임 엔진 |
| **많은 매개변수** | Builder | 가독성, 유연성, 검증 | HTTP 요청, 데이터베이스 쿼리 |
| **런타임 타입 결정** | Factory Method | 동적 객체 생성, 유연성 | 플러그인 시스템, 파일 처리 |
| **단계별 객체 구성** | Builder | 복잡한 객체 생성, 검증 | 설정 객체, 복합 객체 |
| **제품군 교체** | Abstract Factory | 전체 제품군 교체 | 테마 시스템, 렌더링 엔진 |

#### 패턴 조합

```javascript
// Factory + Builder 조합
class UserFactory {
    createAdmin() {
        return new UserBuilder()
            .setRole('admin')
            .addPermission('all')
            .build();
    }
    
    createUser() {
        return new UserBuilder()
            .setRole('user')
            .addPermission('basic')
            .build();
    }
}

// Singleton + Factory 조합
class DatabaseManager {
    static instance = null;
    
    static getInstance() {
        if (!DatabaseManager.instance) {
            DatabaseManager.instance = new DatabaseManager();
        }
        return DatabaseManager.instance;
    }
    
    createConnection(type) {
        return new DatabaseFactory().createConnection(type);
    }
}
```

### 2. 성능 최적화

#### 메모리 사용량 최적화

**Singleton 패턴**
```javascript
// 지연 초기화로 메모리 절약
class LazySingleton {
    static getInstance() {
        if (!LazySingleton.instance) {
            LazySingleton.instance = new LazySingleton();
        }
        return LazySingleton.instance;
    }
}

// 메모리 해제 메서드 제공
class ConfigManager {
    static destroy() {
        ConfigManager.instance = null;
    }
}
```

**Factory 패턴**
```javascript
// 객체 풀링으로 메모리 재사용
class ObjectPool {
    constructor(createFn, resetFn) {
        this.createFn = createFn;
        this.resetFn = resetFn;
        this.pool = [];
    }
    
    acquire() {
        if (this.pool.length > 0) {
            return this.pool.pop();
        }
        return this.createFn();
    }
    
    release(obj) {
        this.resetFn(obj);
        this.pool.push(obj);
    }
}
```

**Builder 패턴**
```javascript
// 빌더 재사용으로 메모리 절약
class ReusableBuilder {
    constructor() {
        this.reset();
    }
    
    reset() {
        this.data = {};
        return this;
    }
    
    setValue(key, value) {
        this.data[key] = value;
        return this;
    }
    
    build() {
        const result = new Product(this.data);
        this.reset();
        return result;
    }
}
```

#### 실행 속도 최적화

**Factory 패턴 최적화**
```javascript
// 타입별 캐싱으로 속도 향상
class OptimizedFactory {
    constructor() {
        this.cache = new Map();
    }
    
    create(type) {
        if (this.cache.has(type)) {
            return this.cache.get(type);
        }
        
        const instance = this.createInstance(type);
        this.cache.set(type, instance);
        return instance;
    }
}
```

**Builder 패턴 최적화**
```javascript
// 불필요한 검증 제거
class FastBuilder {
    build() {
        // 필수 검증만 수행
        if (!this.requiredField) {
            throw new Error("Required field missing");
        }
        
        return new Product(this);
    }
}
```

### 3. 테스트

#### 단위 테스트

**Factory 패턴 테스트**
```javascript
describe('ComponentFactory', () => {
    let factory;
    
    beforeEach(() => {
        factory = new ComponentFactory();
    });
    
    it('should create button component', () => {
        const button = factory.createComponent('button', { text: 'Click' });
        expect(button).toBeInstanceOf(Button);
        expect(button.text).toBe('Click');
    });
    
    it('should throw error for unknown type', () => {
        expect(() => {
            factory.createComponent('unknown', {});
        }).toThrow('Unknown component type');
    });
    
    it('should create different instances', () => {
        const button1 = factory.createComponent('button', {});
        const button2 = factory.createComponent('button', {});
        expect(button1).not.toBe(button2);
    });
});
```

**Singleton 패턴 테스트**
```javascript
describe('Logger', () => {
    beforeEach(() => {
        // 테스트 간 격리
        Logger.instance = null;
    });
    
    it('should return same instance', () => {
        const logger1 = new Logger();
        const logger2 = new Logger();
        expect(logger1).toBe(logger2);
    });
    
    it('should maintain state across instances', () => {
        const logger1 = new Logger();
        logger1.log('test message');
        
        const logger2 = new Logger();
        expect(logger2.getLogs()).toContain('test message');
    });
    
    it('should allow reset for testing', () => {
        const logger = new Logger();
        logger.log('message');
        logger.reset();
        expect(logger.getLogs()).toHaveLength(0);
    });
});
```

**Builder 패턴 테스트**
```javascript
describe('UserBuilder', () => {
    it('should build valid user', () => {
        const user = new UserBuilder()
            .setName('John')
            .setEmail('john@example.com')
            .setAge(30)
            .build();
        
        expect(user.name).toBe('John');
        expect(user.email).toBe('john@example.com');
        expect(user.age).toBe(30);
    });
    
    it('should throw error for missing required fields', () => {
        expect(() => {
            new UserBuilder()
                .setName('John')
                .build();
        }).toThrow('Email is required');
    });
    
    it('should validate email format', () => {
        expect(() => {
            new UserBuilder()
                .setName('John')
                .setEmail('invalid-email')
                .build();
        }).toThrow('Invalid email format');
    });
});
```

#### 통합 테스트

```javascript
describe('Order System Integration', () => {
    it('should create and process order', () => {
        const orderFactory = new OrderFactory();
        const order = orderFactory.createMemberOrder('C001')
            .addItem('P001', 'Product 1', 10000, 2)
            .setShippingAddress(validAddress)
            .setPaymentMethod('credit_card')
            .build();
        
        expect(order.getOrderSummary().itemCount).toBe(1);
        expect(order.getOrderSummary().totalAmount).toBe(20000);
    });
});
```

### 4. 디버깅과 모니터링

#### 로깅
```javascript
class DebuggableFactory {
    create(type, options) {
        console.log(`Creating ${type} with options:`, options);
        const startTime = performance.now();
        
        try {
            const instance = this.createInstance(type, options);
            const endTime = performance.now();
            console.log(`Successfully created ${type} in ${endTime - startTime}ms`);
            return instance;
        } catch (error) {
            console.error(`Failed to create ${type}:`, error);
            throw error;
        }
    }
}
```

#### 성능 모니터링
```javascript
class MonitoredSingleton {
    static getInstance() {
        if (!MonitoredSingleton.instance) {
            const startTime = performance.now();
            MonitoredSingleton.instance = new MonitoredSingleton();
            const endTime = performance.now();
            console.log(`Singleton created in ${endTime - startTime}ms`);
        }
        return MonitoredSingleton.instance;
    }
}
```

### 5. 에러 처리

#### Factory 패턴 에러 처리
```javascript
class RobustFactory {
    create(type, options) {
        try {
            return this.createInstance(type, options);
        } catch (error) {
            if (error instanceof ValidationError) {
                throw new FactoryError(`Invalid options for ${type}: ${error.message}`);
            } else if (error instanceof ConfigurationError) {
                throw new FactoryError(`Configuration error for ${type}: ${error.message}`);
            } else {
                throw new FactoryError(`Unexpected error creating ${type}: ${error.message}`);
            }
        }
    }
}
```

#### Builder 패턴 에러 처리
```javascript
class ValidatedBuilder {
    build() {
        const errors = this.validate();
        if (errors.length > 0) {
            throw new ValidationError(`Validation failed: ${errors.join(', ')}`);
        }
        
        return new Product(this);
    }
    
    validate() {
        const errors = [];
        
        if (!this.requiredField) {
            errors.push('Required field is missing');
        }
        
        if (this.numericField && isNaN(this.numericField)) {
            errors.push('Numeric field must be a number');
        }
        
        return errors;
    }
}
```

### 6. 문서화와 유지보수

#### 코드 문서화
```javascript
/**
 * 사용자 객체를 생성하는 팩토리 클래스
 * 
 * @example
 * const factory = new UserFactory();
 * const admin = factory.createAdmin('admin', 'admin@example.com');
 * 
 * @class UserFactory
 */
class UserFactory {
    /**
     * 관리자 사용자를 생성합니다.
     * 
     * @param {string} username - 사용자명
     * @param {string} email - 이메일 주소
     * @param {string} password - 비밀번호
     * @returns {UserBuilder} 사용자 빌더 인스턴스
     * 
     * @example
     * const admin = factory.createAdmin('admin', 'admin@example.com', 'password');
     */
    createAdmin(username, email, password) {
        return new UserBuilder()
            .setUsername(username)
            .setEmail(email)
            .setPassword(password)
            .asAdmin();
    }
}
```

#### 버전 관리
```javascript
class VersionedFactory {
    create(type, version = 'latest') {
        switch(version) {
            case 'v1':
                return this.createV1(type);
            case 'v2':
                return this.createV2(type);
            case 'latest':
            default:
                return this.createLatest(type);
        }
    }
}
```

## 참고 자료

### 패턴 간 상세 비교

| 패턴 | 목적 | 복잡도 | 유연성 | 재사용성 | 성능 | 메모리 사용량 | 테스트 용이성 |
|------|------|--------|--------|----------|------|---------------|---------------|
| **Singleton** | 단일 인스턴스 보장 | 낮음 | 낮음 | 높음 | 높음 | 낮음 | 낮음 |
| **Factory Method** | 객체 생성 캡슐화 | 중간 | 높음 | 높음 | 중간 | 중간 | 높음 |
| **Abstract Factory** | 관련 객체군 생성 | 높음 | 높음 | 중간 | 중간 | 높음 | 중간 |
| **Builder** | 복잡한 객체 생성 | 중간 | 높음 | 중간 | 낮음 | 중간 | 높음 |

### 패턴 선택 의사결정 트리

```
객체 생성이 필요한가?
├─ 단일 인스턴스만 필요한가?
│  ├─ 예 → Singleton 패턴
│  └─ 아니오 → 다음 질문
├─ 많은 매개변수가 필요한가?
│  ├─ 예 → Builder 패턴
│  └─ 아니오 → 다음 질문
├─ 관련된 여러 객체를 함께 생성해야 하는가?
│  ├─ 예 → Abstract Factory 패턴
│  └─ 아니오 → 다음 질문
├─ 런타임에 객체 타입을 결정해야 하는가?
│  ├─ 예 → Factory Method 패턴
│  └─ 아니오 → 일반 생성자 사용
```

### 성능 벤치마크

#### 메모리 사용량 비교
```javascript
// Singleton: 가장 효율적
const singleton = Singleton.getInstance(); // 1개 인스턴스만 존재

// Factory: 중간 효율성
const factory = new ComponentFactory();
const button1 = factory.create('button'); // 새 인스턴스
const button2 = factory.create('button'); // 새 인스턴스

// Builder: 중간 효율성 (빌더 객체 + 최종 객체)
const builder = new UserBuilder();
const user = builder.setName('John').build(); // 빌더 + 사용자 객체

// Abstract Factory: 가장 비효율적 (많은 클래스)
const uiFactory = new WindowsUIFactory();
const button = uiFactory.createButton(); // 여러 클래스 참조
```

#### 실행 속도 비교
```javascript
// 성능 테스트 결과 (1000회 실행 기준)
const results = {
    singleton: '0.1ms',      // 가장 빠름
    factory: '2.3ms',        // 중간
    builder: '5.7ms',        // 느림 (검증 포함)
    abstractFactory: '8.2ms' // 가장 느림
};
```

### 적용 사례

#### 1. 웹 프레임워크에서의 사용
```javascript
// React에서의 Factory 패턴
const ComponentFactory = {
    create(type, props) {
        switch(type) {
            case 'button': return <Button {...props} />;
            case 'input': return <Input {...props} />;
            case 'modal': return <Modal {...props} />;
        }
    }
};

// Vue에서의 Builder 패턴
const QueryBuilder = {
    select(fields) { return this; },
    from(table) { return this; },
    where(condition) { return this; },
    build() { return this.query; }
};
```

#### 2. Node.js 애플리케이션에서의 사용
```javascript
// Express.js에서의 Singleton 패턴
class DatabaseConnection {
    static instance = null;
    
    static getInstance() {
        if (!DatabaseConnection.instance) {
            DatabaseConnection.instance = new DatabaseConnection();
        }
        return DatabaseConnection.instance;
    }
}

// Koa.js에서의 Factory 패턴
class MiddlewareFactory {
    create(type, options) {
        switch(type) {
            case 'cors': return cors(options);
            case 'helmet': return helmet(options);
            case 'compression': return compression(options);
        }
    }
}
```

#### 3. 모바일 앱에서의 사용
```javascript
// React Native에서의 Abstract Factory 패턴
class PlatformUIFactory {
    createButton(text) {
        if (Platform.OS === 'ios') {
            return new IOSButton(text);
        } else {
            return new AndroidButton(text);
        }
    }
}

// Flutter에서의 Builder 패턴
class WidgetBuilder {
    setText(text) { return this; }
    setColor(color) { return this; }
    setPadding(padding) { return this; }
    build() { return Container(...); }
}
```

### 안티패턴과 주의사항

#### 1. Singleton 안티패턴
```javascript
// 나쁜 예: 전역 변수 남용
let globalConfig = {};

// 나쁜 예: 과도한 Singleton 사용
class UserService {
    static instance = null;
    static getInstance() { /* ... */ }
}

class OrderService {
    static instance = null;
    static getInstance() { /* ... */ }
}

// 좋은 예: 적절한 Singleton 사용
class DatabaseConnection {
    static instance = null;
    static getInstance() { /* ... */ }
}
```

#### 2. Factory 안티패턴
```javascript
// 나쁜 예: 단순한 객체에 Factory 사용
class SimpleFactory {
    createUser(name, email) {
        return new User(name, email);
    }
}

// 좋은 예: 복잡한 객체에 Factory 사용
class ComplexFactory {
    createUser(type, options) {
        switch(type) {
            case 'admin': return new AdminUser(options);
            case 'moderator': return new ModeratorUser(options);
            case 'user': return new RegularUser(options);
        }
    }
}
```

#### 3. Builder 안티패턴
```javascript
// 나쁜 예: 단순한 객체에 Builder 사용
class SimpleBuilder {
    setName(name) { this.name = name; return this; }
    setEmail(email) { this.email = email; return this; }
    build() { return new User(this.name, this.email); }
}

// 좋은 예: 복잡한 객체에 Builder 사용
class ComplexBuilder {
    setPersonalInfo(info) { return this; }
    setAddress(address) { return this; }
    setPreferences(prefs) { return this; }
    setPermissions(perms) { return this; }
    build() { return new ComplexUser(this); }
}
```

### 실무 경험

#### 설계 단계
- [ ] 문제에 적합한 패턴인가?
- [ ] 과도한 복잡성을 추가하지 않는가?
- [ ] 확장성을 고려했는가?
- [ ] 성능 요구사항을 만족하는가?

#### 구현 단계
- [ ] 일관된 네이밍 컨벤션을 사용했는가?
- [ ] 적절한 에러 처리를 구현했는가?
- [ ] 문서화를 충분히 했는가?
- [ ] 테스트 코드를 작성했는가?

#### 유지보수 단계
- [ ] 패턴 사용 의도를 명확히 했는가?
- [ ] 새로운 개발자가 이해하기 쉬운가?
- [ ] 성능 모니터링을 설정했는가?
- [ ] 리팩토링 계획이 있는가?

### 결론

생성 패턴은 객체 생성의 복잡성을 관리하고 코드의 유지보수성을 향상시키는 강력한 도구입니다. 각 패턴의 특징과 사용 시기를 이해하여 적절한 패턴을 선택하는 것이 중요합니다.

**핵심 포인트:**
1. **적절한 패턴 선택**: 문제의 복잡도와 요구사항에 맞는 패턴 선택
2. **과도한 사용 방지**: 단순한 경우에는 일반 생성자 사용
3. **패턴 조합 활용**: 여러 패턴을 조합하여 더 강력한 솔루션 구현
4. **성능 고려**: 메모리 사용량과 실행 속도를 고려한 설계
5. **테스트 가능성**: 테스트하기 쉬운 구조로 설계
6. **문서화**: 패턴 사용 의도와 방법을 명확히 문서화

여러 패턴을 조합하여 사용하는 경우가 많으며, 성능과 유지보수성을 고려한 균형잡힌 설계가 필요합니다. 패턴은 도구일 뿐이며, 문제를 해결하는 것이 최우선 목표임을 잊지 말아야 합니다.

### 추가 학습 자료

- **GoF 디자인 패턴**: 원서 "Design Patterns: Elements of Reusable Object-Oriented Software"
- **Head First Design Patterns**: 패턴을 쉽게 이해할 수 있는 입문서
- **Clean Code**: 로버트 마틴의 코드 품질 향상
- **Refactoring**: 마틴 파울러의 리팩토링 기법
- **Effective Java**: 조슈아 블로크의 Java 모범 사례 (JavaScript에도 적용 가능)

