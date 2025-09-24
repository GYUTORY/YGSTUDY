const winston = require('winston');

// 로그 포맷 정의
const logFormat = winston.format.combine(
  winston.format.timestamp({
    format: 'YYYY-MM-DD HH:mm:ss'
  }),
  winston.format.errors({ stack: true }),
  winston.format.json(),
  winston.format.prettyPrint()
);

// 콘솔 포맷 (개발 환경용)
const consoleFormat = winston.format.combine(
  winston.format.colorize(),
  winston.format.timestamp({
    format: 'HH:mm:ss'
  }),
  winston.format.printf(({ timestamp, level, message, ...meta }) => {
    let log = `${timestamp} [${level}]: ${message}`;
    
    if (Object.keys(meta).length > 0) {
      log += `\n${JSON.stringify(meta, null, 2)}`;
    }
    
    return log;
  })
);

// 로거 인스턴스 생성
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: logFormat,
  defaultMeta: {
    service: 'api-gateway',
    version: '1.0.0'
  },
  transports: [
    // 콘솔 출력
    new winston.transports.Console({
      format: process.env.NODE_ENV === 'production' ? logFormat : consoleFormat
    }),
    
    // 파일 출력 (에러)
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5
    }),
    
    // 파일 출력 (전체)
    new winston.transports.File({
      filename: 'logs/combined.log',
      maxsize: 5242880, // 5MB
      maxFiles: 5
    })
  ],
  
  // 예외 처리
  exceptionHandlers: [
    new winston.transports.File({ filename: 'logs/exceptions.log' })
  ],
  
  // Promise rejection 처리
  rejectionHandlers: [
    new winston.transports.File({ filename: 'logs/rejections.log' })
  ]
});

// 개발 환경에서는 더 자세한 로그
if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: consoleFormat
  }));
}

// 로그 디렉토리 생성 (없는 경우)
const fs = require('fs');
const path = require('path');

const logDir = 'logs';
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir);
}

// 구조화된 로깅을 위한 헬퍼 메서드들
logger.request = (req, res, responseTime) => {
  logger.info('HTTP Request', {
    method: req.method,
    url: req.originalUrl,
    statusCode: res.statusCode,
    responseTime: `${responseTime}ms`,
    userAgent: req.get('User-Agent'),
    ip: req.ip,
    userId: req.user?.id
  });
};

logger.auth = (action, userId, email, success, error = null) => {
  logger.info('Authentication Event', {
    action,
    userId,
    email,
    success,
    error: error?.message
  });
};

logger.serviceCall = (serviceName, method, url, statusCode, responseTime, error = null) => {
  const level = error ? 'error' : 'info';
  logger[level]('Service Call', {
    service: serviceName,
    method,
    url,
    statusCode,
    responseTime: `${responseTime}ms`,
    error: error?.message
  });
};

logger.circuitBreaker = (serviceName, state, failureCount, successCount) => {
  logger.info('Circuit Breaker State Change', {
    service: serviceName,
    state,
    failureCount,
    successCount
  });
};

logger.security = (event, details) => {
  logger.warn('Security Event', {
    event,
    ...details,
    timestamp: new Date().toISOString()
  });
};

logger.performance = (operation, duration, metadata = {}) => {
  logger.info('Performance Metric', {
    operation,
    duration: `${duration}ms`,
    ...metadata
  });
};

// 에러 로깅 헬퍼
logger.errorWithContext = (error, context = {}) => {
  logger.error('Error with Context', {
    message: error.message,
    stack: error.stack,
    ...context
  });
};

module.exports = logger;
