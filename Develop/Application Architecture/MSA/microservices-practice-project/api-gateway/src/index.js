const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { createProxyMiddleware } = require('http-proxy-middleware');
const jwt = require('jsonwebtoken');
const redis = require('redis');
const winston = require('winston');
require('dotenv').config();

const CircuitBreaker = require('./middleware/circuitBreaker');
const authMiddleware = require('./middleware/auth');
const logger = require('./utils/logger');

const app = express();
const PORT = process.env.PORT || 3000;

// Redis 클라이언트 설정
const redisClient = redis.createClient({
  url: process.env.REDIS_URL || 'redis://localhost:6379'
});

redisClient.on('error', (err) => {
  logger.error('Redis Client Error:', err);
});

redisClient.on('connect', () => {
  logger.info('Redis Client Connected');
});

// 미들웨어 설정
app.use(helmet());
app.use(compression());
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// 로깅 미들웨어
app.use(morgan('combined', {
  stream: {
    write: (message) => logger.info(message.trim())
  }
}));

// Rate Limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15분
  max: 100, // 최대 100 요청
  message: {
    error: 'Too many requests from this IP, please try again later.'
  },
  standardHeaders: true,
  legacyHeaders: false,
});

app.use(limiter);

// 서비스 URL 설정
const services = {
  user: process.env.USER_SERVICE_URL || 'http://localhost:3001',
  order: process.env.ORDER_SERVICE_URL || 'http://localhost:3002',
  payment: process.env.PAYMENT_SERVICE_URL || 'http://localhost:3003'
};

// 서킷 브레이커 설정
const circuitBreakers = {
  user: new CircuitBreaker(services.user, { timeout: 5000, threshold: 5 }),
  order: new CircuitBreaker(services.order, { timeout: 5000, threshold: 5 }),
  payment: new CircuitBreaker(services.payment, { timeout: 5000, threshold: 5 })
};

// 헬스체크 엔드포인트
app.get('/health', async (req, res) => {
  const health = {
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    services: {}
  };

  // 각 서비스 헬스체크
  for (const [serviceName, circuitBreaker] of Object.entries(circuitBreakers)) {
    try {
      const response = await fetch(`${services[serviceName]}/health`);
      health.services[serviceName] = {
        status: response.ok ? 'UP' : 'DOWN',
        circuitBreaker: circuitBreaker.getState()
      };
    } catch (error) {
      health.services[serviceName] = {
        status: 'DOWN',
        circuitBreaker: circuitBreaker.getState(),
        error: error.message
      };
    }
  }

  const allServicesUp = Object.values(health.services).every(
    service => service.status === 'UP'
  );

  res.status(allServicesUp ? 200 : 503).json(health);
});

// 인증이 필요하지 않은 라우트
app.use('/api/users/register', createProxyMiddleware({
  target: services.user,
  changeOrigin: true,
  pathRewrite: {
    '^/api/users/register': '/api/users/register'
  },
  onError: (err, req, res) => {
    logger.error('User Service Proxy Error:', err);
    res.status(503).json({ error: 'User service is temporarily unavailable' });
  }
}));

app.use('/api/users/login', createProxyMiddleware({
  target: services.user,
  changeOrigin: true,
  pathRewrite: {
    '^/api/users/login': '/api/users/login'
  },
  onError: (err, req, res) => {
    logger.error('User Service Proxy Error:', err);
    res.status(503).json({ error: 'User service is temporarily unavailable' });
  }
}));

// 인증 미들웨어 적용
app.use('/api', authMiddleware);

// 사용자 서비스 프록시
app.use('/api/users', createProxyMiddleware({
  target: services.user,
  changeOrigin: true,
  pathRewrite: {
    '^/api/users': '/api/users'
  },
  onError: (err, req, res) => {
    logger.error('User Service Proxy Error:', err);
    res.status(503).json({ error: 'User service is temporarily unavailable' });
  }
}));

// 주문 서비스 프록시
app.use('/api/orders', createProxyMiddleware({
  target: services.order,
  changeOrigin: true,
  pathRewrite: {
    '^/api/orders': '/api/orders'
  },
  onError: (err, req, res) => {
    logger.error('Order Service Proxy Error:', err);
    res.status(503).json({ error: 'Order service is temporarily unavailable' });
  }
}));

// 결제 서비스 프록시
app.use('/api/payments', createProxyMiddleware({
  target: services.payment,
  changeOrigin: true,
  pathRewrite: {
    '^/api/payments': '/api/payments'
  },
  onError: (err, req, res) => {
    logger.error('Payment Service Proxy Error:', err);
    res.status(503).json({ error: 'Payment service is temporarily unavailable' });
  }
}));

// 404 핸들러
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Route not found',
    path: req.originalUrl,
    method: req.method
  });
});

// 글로벌 에러 핸들러
app.use((err, req, res, next) => {
  logger.error('Global Error Handler:', err);
  
  res.status(err.status || 500).json({
    error: process.env.NODE_ENV === 'production' 
      ? 'Internal server error' 
      : err.message,
    ...(process.env.NODE_ENV !== 'production' && { stack: err.stack })
  });
});

// 서버 시작
async function startServer() {
  try {
    await redisClient.connect();
    
    app.listen(PORT, () => {
      logger.info(`🚀 API Gateway running on port ${PORT}`);
      logger.info(`📊 Health check: http://localhost:${PORT}/health`);
      logger.info(`🔗 Services configured:`, services);
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully');
  await redisClient.quit();
  process.exit(0);
});

process.on('SIGINT', async () => {
  logger.info('SIGINT received, shutting down gracefully');
  await redisClient.quit();
  process.exit(0);
});

startServer();

module.exports = app;
