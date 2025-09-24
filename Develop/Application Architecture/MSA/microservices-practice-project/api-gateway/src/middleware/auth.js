const jwt = require('jsonwebtoken');
const logger = require('../utils/logger');

/**
 * JWT 토큰 인증 미들웨어
 */
const authMiddleware = (req, res, next) => {
  try {
    // Authorization 헤더에서 토큰 추출
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        error: 'Access token required',
        message: 'Please provide a valid Bearer token'
      });
    }

    const token = authHeader.substring(7); // 'Bearer ' 제거
    
    if (!token) {
      return res.status(401).json({
        error: 'Access token required',
        message: 'Token cannot be empty'
      });
    }

    // JWT 토큰 검증
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'your-secret-key');
    
    // 요청 객체에 사용자 정보 추가
    req.user = {
      id: decoded.id,
      email: decoded.email,
      role: decoded.role || 'user'
    };

    // 로그 기록
    logger.info('User authenticated', {
      userId: req.user.id,
      email: req.user.email,
      path: req.path,
      method: req.method
    });

    next();
  } catch (error) {
    logger.error('Authentication error:', {
      error: error.message,
      path: req.path,
      method: req.method
    });

    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({
        error: 'Invalid token',
        message: 'The provided token is invalid'
      });
    }

    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({
        error: 'Token expired',
        message: 'The provided token has expired'
      });
    }

    return res.status(401).json({
      error: 'Authentication failed',
      message: 'Unable to authenticate the request'
    });
  }
};

/**
 * 역할 기반 접근 제어 미들웨어
 */
const requireRole = (roles) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        error: 'Authentication required',
        message: 'User must be authenticated'
      });
    }

    const userRole = req.user.role;
    const allowedRoles = Array.isArray(roles) ? roles : [roles];

    if (!allowedRoles.includes(userRole)) {
      logger.warn('Access denied - insufficient role', {
        userId: req.user.id,
        userRole,
        requiredRoles: allowedRoles,
        path: req.path
      });

      return res.status(403).json({
        error: 'Access denied',
        message: `Required role: ${allowedRoles.join(' or ')}`
      });
    }

    next();
  };
};

/**
 * 선택적 인증 미들웨어 (토큰이 있으면 검증, 없으면 통과)
 */
const optionalAuth = (req, res, next) => {
  const authHeader = req.headers.authorization;
  
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return next();
  }

  const token = authHeader.substring(7);
  
  if (!token) {
    return next();
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'your-secret-key');
    req.user = {
      id: decoded.id,
      email: decoded.email,
      role: decoded.role || 'user'
    };
  } catch (error) {
    // 토큰이 유효하지 않아도 계속 진행 (선택적 인증)
    logger.warn('Optional auth failed:', error.message);
  }

  next();
};

module.exports = {
  authMiddleware,
  requireRole,
  optionalAuth
};
