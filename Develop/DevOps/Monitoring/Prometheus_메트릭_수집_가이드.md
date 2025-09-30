---
title: Prometheus 메트릭 수집 가이드
tags: [prometheus, metrics, monitoring, nodejs, prom-client, grafana, alerting]
updated: 2025-09-13
---

# Prometheus 메트릭 수집 가이드

## 배경

### Prometheus 메트릭 수집이란?
Prometheus는 오픈소스 모니터링 및 알림 시스템으로, 메트릭 데이터를 수집, 저장, 쿼리하는 기능을 제공합니다. Node.js 애플리케이션에서 prom-client 라이브러리를 사용하여 커스텀 메트릭을 정의하고 수집할 수 있습니다.

### Prometheus 메트릭 수집의 필요성
- **성능 모니터링**: 애플리케이션 성능 지표 실시간 추적
- **리소스 모니터링**: CPU, 메모리, 디스크 사용량 추적
- **비즈니스 메트릭**: 비즈니스 로직에 특화된 메트릭 수집
- **알림 시스템**: 임계값 기반 자동 알림
- **시각화**: Grafana를 통한 메트릭 시각화

### 기본 개념
- **Metric**: 측정 가능한 수치 데이터
- **Label**: 메트릭을 분류하는 키-값 쌍
- **Counter**: 증가만 하는 메트릭 (요청 수, 에러 수)
- **Gauge**: 증가/감소가 가능한 메트릭 (메모리 사용량, 연결 수)
- **Histogram**: 값의 분포를 나타내는 메트릭 (응답 시간)
- **Summary**: 백분위수를 나타내는 메트릭 (응답 시간 분포)

## 핵심

### 1. prom-client 라이브러리 활용

#### 기본 설치 및 설정
```javascript
// package.json
{
  "dependencies": {
    "prom-client": "^15.0.0"
  }
}

// src/metrics/prometheusClient.js
const client = require('prom-client');

class PrometheusClient {
  constructor() {
    // 메트릭 레지스트리 초기화
    this.register = new client.Registry();
    
    // 기본 메트릭 수집 (Node.js 기본 메트릭)
    client.collectDefaultMetrics({
      register: this.register,
      prefix: 'nodejs_',
      gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5],
      eventLoopMonitoringPrecision: 10
    });
    
    // 커스텀 메트릭 초기화
    this.initializeCustomMetrics();
  }
  
  // 커스텀 메트릭 초기화
  initializeCustomMetrics() {
    // HTTP 요청 메트릭
    this.httpRequestDuration = new client.Histogram({
      name: 'http_request_duration_seconds',
      help: 'Duration of HTTP requests in seconds',
      labelNames: ['method', 'route', 'status_code'],
      buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
    });
    
    this.httpRequestTotal = new client.Counter({
      name: 'http_requests_total',
      help: 'Total number of HTTP requests',
      labelNames: ['method', 'route', 'status_code']
    });
    
    // 데이터베이스 메트릭
    this.databaseQueryDuration = new client.Histogram({
      name: 'database_query_duration_seconds',
      help: 'Duration of database queries in seconds',
      labelNames: ['operation', 'table', 'status'],
      buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5]
    });
    
    this.databaseConnections = new client.Gauge({
      name: 'database_connections_active',
      help: 'Number of active database connections',
      labelNames: ['database', 'state']
    });
    
    // 비즈니스 메트릭
    this.userRegistrations = new client.Counter({
      name: 'user_registrations_total',
      help: 'Total number of user registrations',
      labelNames: ['source', 'status']
    });
    
    this.activeUsers = new client.Gauge({
      name: 'active_users_count',
      help: 'Number of active users',
      labelNames: ['period']
    });
    
    // 에러 메트릭
    this.errorsTotal = new client.Counter({
      name: 'errors_total',
      help: 'Total number of errors',
      labelNames: ['type', 'severity', 'component']
    });
    
    // 시스템 메트릭
    this.memoryUsage = new client.Gauge({
      name: 'nodejs_memory_usage_bytes',
      help: 'Node.js memory usage in bytes',
      labelNames: ['type']
    });
    
    this.cpuUsage = new client.Gauge({
      name: 'nodejs_cpu_usage_percent',
      help: 'Node.js CPU usage percentage'
    });
    
    // 모든 메트릭을 레지스트리에 등록
    this.register.registerMetric(this.httpRequestDuration);
    this.register.registerMetric(this.httpRequestTotal);
    this.register.registerMetric(this.databaseQueryDuration);
    this.register.registerMetric(this.databaseConnections);
    this.register.registerMetric(this.userRegistrations);
    this.register.registerMetric(this.activeUsers);
    this.register.registerMetric(this.errorsTotal);
    this.register.registerMetric(this.memoryUsage);
    this.register.registerMetric(this.cpuUsage);
  }
  
  // 메트릭 레지스트리 반환
  getRegister() {
    return this.register;
  }
  
  // 메트릭 데이터 반환
  async getMetrics() {
    return await this.register.metrics();
  }
  
  // 메트릭 초기화
  clearMetrics() {
    this.register.clear();
  }
}

module.exports = PrometheusClient;
```

#### 고급 메트릭 설정
```javascript
// src/metrics/advancedPrometheusClient.js
const client = require('prom-client');

class AdvancedPrometheusClient {
  constructor() {
    this.register = new client.Registry();
    
    // 고급 기본 메트릭 설정
    client.collectDefaultMetrics({
      register: this.register,
      prefix: 'app_',
      gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5, 10],
      eventLoopMonitoringPrecision: 10,
      // 커스텀 메트릭 수집기 추가
      customMetricPrefix: 'custom_'
    });
    
    this.initializeAdvancedMetrics();
  }
  
  // 고급 메트릭 초기화
  initializeAdvancedMetrics() {
    // 분산 추적 메트릭
    this.distributedTraceDuration = new client.Histogram({
      name: 'distributed_trace_duration_seconds',
      help: 'Duration of distributed traces in seconds',
      labelNames: ['service', 'operation', 'status'],
      buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30]
    });
    
    // 큐 메트릭
    this.queueSize = new client.Gauge({
      name: 'queue_size',
      help: 'Current size of the queue',
      labelNames: ['queue_name', 'priority']
    });
    
    this.queueProcessingDuration = new client.Histogram({
      name: 'queue_processing_duration_seconds',
      help: 'Duration of queue processing in seconds',
      labelNames: ['queue_name', 'job_type', 'status'],
      buckets: [0.1, 0.5, 1, 2, 5, 10, 30, 60, 300]
    });
    
    // 캐시 메트릭
    this.cacheHits = new client.Counter({
      name: 'cache_hits_total',
      help: 'Total number of cache hits',
      labelNames: ['cache_name', 'key_pattern']
    });
    
    this.cacheMisses = new client.Counter({
      name: 'cache_misses_total',
      help: 'Total number of cache misses',
      labelNames: ['cache_name', 'key_pattern']
    });
    
    this.cacheSize = new client.Gauge({
      name: 'cache_size_bytes',
      help: 'Current size of the cache in bytes',
      labelNames: ['cache_name']
    });
    
    // 외부 API 메트릭
    this.externalAPIDuration = new client.Histogram({
      name: 'external_api_duration_seconds',
      help: 'Duration of external API calls in seconds',
      labelNames: ['service', 'endpoint', 'status_code'],
      buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
    });
    
    this.externalAPIRate = new client.Gauge({
      name: 'external_api_rate_limit_remaining',
      help: 'Remaining rate limit for external API',
      labelNames: ['service', 'endpoint']
    });
    
    // 비즈니스 KPI 메트릭
    this.revenue = new client.Counter({
      name: 'revenue_total',
      help: 'Total revenue in currency units',
      labelNames: ['currency', 'source', 'product']
    });
    
    this.conversionRate = new client.Gauge({
      name: 'conversion_rate',
      help: 'Conversion rate percentage',
      labelNames: ['funnel_stage', 'segment']
    });
    
    // 모든 메트릭을 레지스트리에 등록
    this.register.registerMetric(this.distributedTraceDuration);
    this.register.registerMetric(this.queueSize);
    this.register.registerMetric(this.queueProcessingDuration);
    this.register.registerMetric(this.cacheHits);
    this.register.registerMetric(this.cacheMisses);
    this.register.registerMetric(this.cacheSize);
    this.register.registerMetric(this.externalAPIDuration);
    this.register.registerMetric(this.externalAPIRate);
    this.register.registerMetric(this.revenue);
    this.register.registerMetric(this.conversionRate);
  }
  
  // 메트릭 레지스트리 반환
  getRegister() {
    return this.register;
  }
  
  // 메트릭 데이터 반환
  async getMetrics() {
    return await this.register.metrics();
  }
}

module.exports = AdvancedPrometheusClient;
```

### 2. 커스텀 메트릭 정의 및 수집

#### 메트릭 수집 서비스
```javascript
// src/services/metricsCollectionService.js
const PrometheusClient = require('../metrics/prometheusClient');

class MetricsCollectionService {
  constructor() {
    this.prometheusClient = new PrometheusClient();
    this.metrics = new Map();
    this.timers = new Map();
  }
  
  // HTTP 요청 메트릭 수집
  recordHTTPRequest(method, route, statusCode, duration) {
    try {
      // Histogram 메트릭 기록
      this.prometheusClient.httpRequestDuration
        .labels(method, route, statusCode.toString())
        .observe(duration);
      
      // Counter 메트릭 기록
      this.prometheusClient.httpRequestTotal
        .labels(method, route, statusCode.toString())
        .inc();
      
    } catch (error) {
      console.error('Failed to record HTTP request metric:', error);
    }
  }
  
  // 데이터베이스 쿼리 메트릭 수집
  recordDatabaseQuery(operation, table, status, duration) {
    try {
      this.prometheusClient.databaseQueryDuration
        .labels(operation, table, status)
        .observe(duration);
      
    } catch (error) {
      console.error('Failed to record database query metric:', error);
    }
  }
  
  // 데이터베이스 연결 메트릭 수집
  recordDatabaseConnection(database, state, count) {
    try {
      this.prometheusClient.databaseConnections
        .labels(database, state)
        .set(count);
      
    } catch (error) {
      console.error('Failed to record database connection metric:', error);
    }
  }
  
  // 사용자 등록 메트릭 수집
  recordUserRegistration(source, status) {
    try {
      this.prometheusClient.userRegistrations
        .labels(source, status)
        .inc();
      
    } catch (error) {
      console.error('Failed to record user registration metric:', error);
    }
  }
  
  // 활성 사용자 메트릭 수집
  recordActiveUsers(period, count) {
    try {
      this.prometheusClient.activeUsers
        .labels(period)
        .set(count);
      
    } catch (error) {
      console.error('Failed to record active users metric:', error);
    }
  }
  
  // 에러 메트릭 수집
  recordError(type, severity, component) {
    try {
      this.prometheusClient.errorsTotal
        .labels(type, severity, component)
        .inc();
      
    } catch (error) {
      console.error('Failed to record error metric:', error);
    }
  }
  
  // 시스템 메트릭 수집
  recordSystemMetrics() {
    try {
      const memUsage = process.memoryUsage();
      
      // 메모리 사용량 메트릭
      this.prometheusClient.memoryUsage
        .labels('rss')
        .set(memUsage.rss);
      
      this.prometheusClient.memoryUsage
        .labels('heapTotal')
        .set(memUsage.heapTotal);
      
      this.prometheusClient.memoryUsage
        .labels('heapUsed')
        .set(memUsage.heapUsed);
      
      this.prometheusClient.memoryUsage
        .labels('external')
        .set(memUsage.external);
      
      // CPU 사용량 메트릭 (간단한 구현)
      const cpuUsage = process.cpuUsage();
      const totalCpuUsage = (cpuUsage.user + cpuUsage.system) / 1000000; // 마이크로초를 초로 변환
      
      this.prometheusClient.cpuUsage.set(totalCpuUsage);
      
    } catch (error) {
      console.error('Failed to record system metrics:', error);
    }
  }
  
  // 타이머 시작
  startTimer(name) {
    this.timers.set(name, Date.now());
  }
  
  // 타이머 종료 및 메트릭 기록
  endTimer(name, labels = {}) {
    try {
      const startTime = this.timers.get(name);
      if (!startTime) {
        console.warn(`Timer ${name} was not started`);
        return 0;
      }
      
      const duration = (Date.now() - startTime) / 1000; // 초 단위로 변환
      this.timers.delete(name);
      
      // 커스텀 타이머 메트릭 기록
      if (labels.operation && labels.table) {
        this.recordDatabaseQuery(labels.operation, labels.table, 'success', duration);
      }
      
      return duration;
    } catch (error) {
      console.error('Failed to end timer:', error);
      return 0;
    }
  }
  
  // 커스텀 메트릭 기록
  recordCustomMetric(name, value, labels = {}) {
    try {
      if (!this.metrics.has(name)) {
        // 새로운 Gauge 메트릭 생성
        const client = require('prom-client');
        const metric = new client.Gauge({
          name: name,
          help: `Custom metric: ${name}`,
          labelNames: Object.keys(labels)
        });
        
        this.prometheusClient.register.registerMetric(metric);
        this.metrics.set(name, metric);
      }
      
      const metric = this.metrics.get(name);
      metric.labels(...Object.values(labels)).set(value);
      
    } catch (error) {
      console.error('Failed to record custom metric:', error);
    }
  }
  
  // 메트릭 데이터 반환
  async getMetrics() {
    try {
      return await this.prometheusClient.getMetrics();
    } catch (error) {
      console.error('Failed to get metrics:', error);
      return '';
    }
  }
  
  // 메트릭 레지스트리 반환
  getRegister() {
    return this.prometheusClient.getRegister();
  }
}

module.exports = MetricsCollectionService;
```

#### 메트릭 수집 미들웨어
```javascript
// src/middleware/metricsMiddleware.js
const MetricsCollectionService = require('../services/metricsCollectionService');

class MetricsMiddleware {
  constructor() {
    this.metricsService = new MetricsCollectionService();
    
    // 정기적인 시스템 메트릭 수집
    setInterval(() => {
      this.metricsService.recordSystemMetrics();
    }, 5000); // 5초마다
  }
  
  // HTTP 요청 메트릭 수집 미들웨어
  collectHTTPMetrics() {
    return (req, res, next) => {
      const startTime = Date.now();
      const originalSend = res.send;
      
      // 응답 시간 측정
      res.send = function(data) {
        const duration = (Date.now() - startTime) / 1000; // 초 단위
        
        // 메트릭 기록
        this.metricsService.recordHTTPRequest(
          req.method,
          req.route?.path || req.path,
          res.statusCode.toString(),
          duration
        );
        
        originalSend.call(this, data);
      }.bind(this);
      
      next();
    };
  }
  
  // 데이터베이스 메트릭 수집 미들웨어
  collectDatabaseMetrics() {
    return (req, res, next) => {
      const originalQuery = req.db?.query;
      
      if (originalQuery) {
        req.db.query = function(sql, params, callback) {
          const startTime = Date.now();
          
          const wrappedCallback = function(error, results) {
            const duration = (Date.now() - startTime) / 1000;
            const status = error ? 'error' : 'success';
            
            // 메트릭 기록
            this.metricsService.recordDatabaseQuery(
              'query',
              'unknown',
              status,
              duration
            );
            
            if (callback) callback(error, results);
          }.bind(this);
          
          originalQuery.call(this, sql, params, wrappedCallback);
        }.bind(this);
      }
      
      next();
    };
  }
  
  // 에러 메트릭 수집 미들웨어
  collectErrorMetrics() {
    return (err, req, res, next) => {
      // 에러 메트릭 기록
      this.metricsService.recordError(
        err.name || 'UnknownError',
        err.statusCode >= 500 ? 'high' : 'medium',
        'http'
      );
      
      next(err);
    };
  }
  
  // 사용자 행동 메트릭 수집 미들웨어
  collectUserBehaviorMetrics() {
    return (req, res, next) => {
      if (req.user) {
        // 사용자 행동 메트릭 기록
        this.metricsService.recordCustomMetric(
          'user_action_total',
          1,
          {
            action: req.method,
            endpoint: req.path,
            userId: req.user.id
          }
        );
      }
      
      next();
    };
  }
  
  // 메트릭 서비스 반환
  getMetricsService() {
    return this.metricsService;
  }
}

module.exports = MetricsMiddleware;
```

### 3. Node.js 애플리케이션 메트릭 노출

#### 메트릭 엔드포인트 설정
```javascript
// src/routes/metricsRoutes.js
const express = require('express');
const MetricsCollectionService = require('../services/metricsCollectionService');

class MetricsRoutes {
  constructor() {
    this.router = express.Router();
    this.metricsService = new MetricsCollectionService();
    this.setupRoutes();
  }
  
  setupRoutes() {
    // Prometheus 메트릭 엔드포인트
    this.router.get('/metrics', async (req, res) => {
      try {
        const metrics = await this.metricsService.getMetrics();
        
        res.set('Content-Type', 'text/plain; version=0.0.4; charset=utf-8');
        res.send(metrics);
      } catch (error) {
        res.status(500).json({ error: 'Failed to get metrics' });
      }
    });
    
    // 메트릭 상태 확인 엔드포인트
    this.router.get('/metrics/health', (req, res) => {
      try {
        const register = this.metricsService.getRegister();
        const metrics = register.getMetricsAsJSON();
        
        res.json({
          status: 'healthy',
          metricsCount: metrics.length,
          timestamp: new Date().toISOString()
        });
      } catch (error) {
        res.status(500).json({ 
          status: 'unhealthy',
          error: error.message 
        });
      }
    });
    
    // 특정 메트릭 조회 엔드포인트
    this.router.get('/metrics/:metricName', (req, res) => {
      try {
        const { metricName } = req.params;
        const register = this.metricsService.getRegister();
        const metrics = register.getMetricsAsJSON();
        
        const metric = metrics.find(m => m.name === metricName);
        
        if (!metric) {
          return res.status(404).json({ error: 'Metric not found' });
        }
        
        res.json(metric);
      } catch (error) {
        res.status(500).json({ error: 'Failed to get metric' });
      }
    });
    
    // 메트릭 통계 엔드포인트
    this.router.get('/metrics/stats', (req, res) => {
      try {
        const register = this.metricsService.getRegister();
        const metrics = register.getMetricsAsJSON();
        
        const stats = {
          totalMetrics: metrics.length,
          metricTypes: {},
          timestamp: new Date().toISOString()
        };
        
        // 메트릭 타입별 통계
        metrics.forEach(metric => {
          const type = metric.type;
          stats.metricTypes[type] = (stats.metricTypes[type] || 0) + 1;
        });
        
        res.json(stats);
      } catch (error) {
        res.status(500).json({ error: 'Failed to get metrics stats' });
      }
    });
    
    // 메트릭 리셋 엔드포인트 (개발 환경에서만)
    this.router.post('/metrics/reset', (req, res) => {
      if (process.env.NODE_ENV === 'production') {
        return res.status(403).json({ error: 'Not allowed in production' });
      }
      
      try {
        this.metricsService.prometheusClient.clearMetrics();
        res.json({ message: 'Metrics reset successfully' });
      } catch (error) {
        res.status(500).json({ error: 'Failed to reset metrics' });
      }
    });
  }
  
  getRouter() {
    return this.router;
  }
}

module.exports = MetricsRoutes;
```

#### 메트릭 노출 서버
```javascript
// src/servers/metricsServer.js
const express = require('express');
const MetricsRoutes = require('../routes/metricsRoutes');

class MetricsServer {
  constructor(port = 9090) {
    this.app = express();
    this.port = port;
    this.metricsRoutes = new MetricsRoutes();
    
    this.setupMiddleware();
    this.setupRoutes();
  }
  
  setupMiddleware() {
    // 기본 미들웨어
    this.app.use(express.json());
    this.app.use(express.urlencoded({ extended: true }));
    
    // CORS 설정
    this.app.use((req, res, next) => {
      res.header('Access-Control-Allow-Origin', '*');
      res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
      next();
    });
    
    // 요청 로깅
    this.app.use((req, res, next) => {
      console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
      next();
    });
  }
  
  setupRoutes() {
    // 메트릭 라우트
    this.app.use('/metrics', this.metricsRoutes.getRouter());
    
    // 헬스 체크
    this.app.get('/health', (req, res) => {
      res.json({ 
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
      });
    });
    
    // 루트 경로
    this.app.get('/', (req, res) => {
      res.json({
        message: 'Prometheus Metrics Server',
        endpoints: {
          metrics: '/metrics',
          health: '/health',
          stats: '/metrics/stats'
        }
      });
    });
  }
  
  start() {
    this.server = this.app.listen(this.port, () => {
      console.log(`Metrics server running on port ${this.port}`);
      console.log(`Metrics endpoint: http://localhost:${this.port}/metrics`);
    });
    
    // Graceful shutdown
    process.on('SIGTERM', () => {
      console.log('SIGTERM received, shutting down gracefully');
      this.server.close(() => {
        console.log('Metrics server closed');
        process.exit(0);
      });
    });
  }
  
  stop() {
    if (this.server) {
      this.server.close();
    }
  }
}

module.exports = MetricsServer;
```

### 4. 메트릭 엔드포인트 설정

#### 통합 메트릭 설정
```javascript
// src/config/metricsConfig.js
const metricsConfig = {
  // 기본 메트릭 설정
  default: {
    prefix: 'app_',
    gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5],
    eventLoopMonitoringPrecision: 10
  },
  
  // HTTP 메트릭 설정
  http: {
    durationBuckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10],
    labelNames: ['method', 'route', 'status_code']
  },
  
  // 데이터베이스 메트릭 설정
  database: {
    durationBuckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5],
    labelNames: ['operation', 'table', 'status']
  },
  
  // 비즈니스 메트릭 설정
  business: {
    userRegistration: {
      labelNames: ['source', 'status']
    },
    activeUsers: {
      labelNames: ['period']
    }
  },
  
  // 에러 메트릭 설정
  errors: {
    labelNames: ['type', 'severity', 'component']
  },
  
  // 시스템 메트릭 설정
  system: {
    memoryTypes: ['rss', 'heapTotal', 'heapUsed', 'external'],
    collectionInterval: 5000 // 5초
  }
};

// 환경별 설정
const environmentConfigs = {
  development: {
    ...metricsConfig,
    default: {
      ...metricsConfig.default,
      prefix: 'dev_'
    }
  },
  
  staging: {
    ...metricsConfig,
    default: {
      ...metricsConfig.default,
      prefix: 'staging_'
    }
  },
  
  production: {
    ...metricsConfig,
    default: {
      ...metricsConfig.default,
      prefix: 'prod_'
    },
    system: {
      ...metricsConfig.system,
      collectionInterval: 10000 // 10초
    }
  }
};

function getMetricsConfig(environment = 'development') {
  return environmentConfigs[environment] || environmentConfigs.development;
}

module.exports = { metricsConfig, getMetricsConfig };
```

## 예시

### 1. 완전한 Prometheus 통합 예제

#### Express.js 애플리케이션 통합
```javascript
// app.js
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');

// 메트릭 관련 import
const MetricsMiddleware = require('./src/middleware/metricsMiddleware');
const MetricsServer = require('./src/servers/metricsServer');

const app = express();

// 메트릭 미들웨어 초기화
const metricsMiddleware = new MetricsMiddleware();

// 기본 미들웨어
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Rate Limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15분
  max: 100, // 최대 100 요청
  message: {
    error: 'Too many requests from this IP',
    retryAfter: 15 * 60
  }
});
app.use('/api/', limiter);

// 메트릭 수집 미들웨어
app.use(metricsMiddleware.collectHTTPMetrics());
app.use(metricsMiddleware.collectDatabaseMetrics());
app.use(metricsMiddleware.collectUserBehaviorMetrics());

// 라우트 설정
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

app.get('/api/users', async (req, res) => {
  try {
    // 타이머 시작
    metricsMiddleware.getMetricsService().startTimer('userQuery');
    
    // 사용자 조회 로직
    const users = await User.findAll();
    
    // 타이머 종료
    const duration = metricsMiddleware.getMetricsService().endTimer('userQuery', {
      operation: 'SELECT',
      table: 'users'
    });
    
    // 비즈니스 메트릭 기록
    metricsMiddleware.getMetricsService().recordCustomMetric(
      'user_query_total',
      1,
      { operation: 'SELECT', table: 'users' }
    );
    
    res.json(users);
  } catch (error) {
    // 에러 메트릭 기록
    metricsMiddleware.getMetricsService().recordError(
      'DatabaseError',
      'high',
      'userService'
    );
    
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.post('/api/users', async (req, res) => {
  try {
    // 타이머 시작
    metricsMiddleware.getMetricsService().startTimer('userCreate');
    
    // 사용자 생성 로직
    const user = await User.create(req.body);
    
    // 타이머 종료
    const duration = metricsMiddleware.getMetricsService().endTimer('userCreate', {
      operation: 'INSERT',
      table: 'users'
    });
    
    // 사용자 등록 메트릭 기록
    metricsMiddleware.getMetricsService().recordUserRegistration(
      'api',
      'success'
    );
    
    res.status(201).json(user);
  } catch (error) {
    // 에러 메트릭 기록
    metricsMiddleware.getMetricsService().recordError(
      'ValidationError',
      'medium',
      'userService'
    );
    
    res.status(500).json({ error: 'Internal server error' });
  }
});

// 에러 처리 미들웨어
app.use(metricsMiddleware.collectErrorMetrics());

// 404 처리
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// 메인 서버 시작
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Main server running on port ${PORT}`);
});

// 메트릭 서버 시작
const metricsServer = new MetricsServer(9090);
metricsServer.start();
```

### 2. Prometheus 설정 파일

#### prometheus.yml 설정
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # Node.js 애플리케이션 메트릭
  - job_name: 'nodejs-app'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 5s
    scrape_timeout: 5s
    
  # Node.js 기본 메트릭
  - job_name: 'nodejs-default'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 15s
    
  # 시스템 메트릭 (node_exporter)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 15s
```

#### 알림 규칙 설정
```yaml
# alert_rules.yml
groups:
  - name: nodejs-app
    rules:
      # 높은 에러율 알림
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"
      
      # 높은 응답 시간 알림
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }} seconds"
      
      # 높은 메모리 사용률 알림
      - alert: HighMemoryUsage
        expr: nodejs_memory_usage_bytes{type="heapUsed"} > 1000000000
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value }} bytes"
      
      # 데이터베이스 연결 문제 알림
      - alert: DatabaseConnectionIssue
        expr: database_connections_active{state="active"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection issue"
          description: "No active database connections"
```

## 운영 팁

### 1. Prometheus 메트릭 최적화

#### 메트릭 최적화 가이드
```javascript
// scripts/optimizeMetrics.js
const optimizationTips = {
  performance: [
    '메트릭 수집 빈도 최적화',
    '불필요한 메트릭 제거',
    '메트릭 레이블 수 최소화',
    '메트릭 버킷 크기 조정'
  ],
  
  storage: [
    '메트릭 보존 기간 설정',
    '불필요한 메트릭 삭제',
    '메트릭 압축 설정',
    '스토리지 최적화'
  ],
  
  monitoring: [
    '핵심 메트릭 우선순위 설정',
    '알림 임계값 최적화',
    '대시보드 성능 최적화',
    '메트릭 쿼리 최적화'
  ],
  
  maintenance: [
    '정기적인 메트릭 검토',
    '메트릭 설정 업데이트',
    '성능 지표 분석',
    '비용 최적화'
  ]
};

function getOptimizationTips() {
  return optimizationTips;
}

module.exports = { getOptimizationTips };
```

### 2. Prometheus 모니터링 체크리스트

#### 모니터링 설정 검증
```javascript
// scripts/validatePrometheusSetup.js
const validationChecklist = {
  installation: [
    'Prometheus 서버 설치 확인',
    'Node.js 애플리케이션 메트릭 노출 확인',
    '메트릭 엔드포인트 접근 가능 확인',
    '기본 메트릭 수집 확인'
  ],
  
  configuration: [
    'prometheus.yml 설정 확인',
    '스크래핑 설정 확인',
    '알림 규칙 설정 확인',
    '메트릭 레이블 설정 확인'
  ],
  
  monitoring: [
    '핵심 메트릭 모니터링 확인',
    '알림 설정 확인',
    '대시보드 구성 확인',
    '메트릭 쿼리 테스트'
  ],
  
  maintenance: [
    '정기적인 메트릭 검토',
    '알림 임계값 조정',
    '성능 지표 분석',
    '스토리지 관리'
  ]
};

function validatePrometheusSetup() {
  const results = {};
  
  Object.keys(validationChecklist).forEach(category => {
    results[category] = {
      total: validationChecklist[category].length,
      implemented: 0,
      missing: []
    };
    
    validationChecklist[category].forEach(item => {
      if (isImplemented(item)) {
        results[category].implemented++;
      } else {
        results[category].missing.push(item);
      }
    });
  });
  
  return results;
}

module.exports = { validationChecklist, validatePrometheusSetup };
```

## 참고

### 모범 사례

#### Prometheus 메트릭 설계 원칙
1. **명확한 네이밍**: 메트릭 이름이 목적을 명확히 나타내도록
2. **적절한 레이블**: 메트릭을 분류하는 데 필요한 레이블만 사용
3. **일관된 형식**: 메트릭 이름과 레이블 형식의 일관성 유지
4. **성능 고려**: 메트릭 수집이 애플리케이션 성능에 미치는 영향 최소화
5. **보안 고려**: 민감한 정보가 메트릭에 노출되지 않도록 주의

#### 모니터링 전략
1. **다층 모니터링**: 시스템, 애플리케이션, 비즈니스 레벨 모니터링
2. **실시간 추적**: 실시간 성능 및 에러 추적
3. **트렌드 분석**: 장기적인 트렌드 분석
4. **비교 분석**: 과거 데이터와의 비교 분석
5. **자동화**: 모니터링 및 알림 자동화

### 결론
Prometheus는 Node.js 애플리케이션의 성능 모니터링과 최적화를 위한 강력한 도구입니다.
적절한 메트릭 정의와 수집으로 애플리케이션의 성능을 지속적으로 개선하세요.
지속적인 모니터링과 분석을 통해 안정적이고 성능이 우수한 애플리케이션을 유지하세요.
