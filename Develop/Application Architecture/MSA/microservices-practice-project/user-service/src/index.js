const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const mongoose = require('mongoose');
const redis = require('redis');
require('dotenv').config();

const authRoutes = require('./routes/auth');
const userRoutes = require('./routes/users');
const logger = require('./utils/logger');
const { startGrpcServer } = require('./grpc/server');

const app = express();
const PORT = process.env.PORT || 3001;

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
  }
});

app.use(limiter);

// MongoDB 연결
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/user-service', {
  useNewUrlParser: true,
  useUnifiedTopology: true,
});

mongoose.connection.on('connected', () => {
  logger.info('MongoDB connected successfully');
});

mongoose.connection.on('error', (err) => {
  logger.error('MongoDB connection error:', err);
});

// 헬스체크 엔드포인트
app.get('/health', async (req, res) => {
  const health = {
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    service: 'user-service',
    version: '1.0.0',
    dependencies: {
      mongodb: mongoose.connection.readyState === 1 ? 'UP' : 'DOWN',
      redis: redisClient.isReady ? 'UP' : 'DOWN'
    }
  };

  const allDependenciesUp = Object.values(health.dependencies).every(
    status => status === 'UP'
  );

  res.status(allDependenciesUp ? 200 : 503).json(health);
});

// API 라우트
app.use('/api/users', authRoutes);
app.use('/api/users', userRoutes);

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
    
    // HTTP 서버 시작
    app.listen(PORT, () => {
      logger.info(`🚀 User Service running on port ${PORT}`);
      logger.info(`📊 Health check: http://localhost:${PORT}/health`);
    });

    // gRPC 서버 시작
    await startGrpcServer();
    logger.info(`🔗 gRPC server started on port ${process.env.GRPC_PORT || 50051}`);
    
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully');
  await mongoose.connection.close();
  await redisClient.quit();
  process.exit(0);
});

process.on('SIGINT', async () => {
  logger.info('SIGINT received, shutting down gracefully');
  await mongoose.connection.close();
  await redisClient.quit();
  process.exit(0);
});

startServer();

module.exports = app;
