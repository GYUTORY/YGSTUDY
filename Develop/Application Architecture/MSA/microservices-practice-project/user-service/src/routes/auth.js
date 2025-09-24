const express = require('express');
const jwt = require('jsonwebtoken');
const { body, validationResult } = require('express-validator');
const User = require('../models/User');
const logger = require('../utils/logger');
const authMiddleware = require('../middleware/auth');

const router = express.Router();

/**
 * 사용자 등록
 * POST /api/users/register
 */
router.post('/register', [
  body('email')
    .isEmail()
    .normalizeEmail()
    .withMessage('Please provide a valid email'),
  body('password')
    .isLength({ min: 6 })
    .withMessage('Password must be at least 6 characters long'),
  body('name')
    .trim()
    .isLength({ min: 2, max: 100 })
    .withMessage('Name must be between 2 and 100 characters')
], async (req, res) => {
  try {
    // 입력 검증
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      });
    }

    const { email, password, name } = req.body;

    // 이메일 중복 확인
    const existingUser = await User.findByEmail(email);
    if (existingUser) {
      return res.status(409).json({
        error: 'User already exists',
        message: 'A user with this email already exists'
      });
    }

    // 새 사용자 생성
    const user = new User({
      email,
      password,
      name,
      emailVerificationToken: jwt.sign(
        { email },
        process.env.JWT_SECRET || 'your-secret-key',
        { expiresIn: '24h' }
      )
    });

    await user.save();

    // JWT 토큰 생성
    const token = jwt.sign(
      {
        id: user._id,
        email: user.email,
        role: user.role
      },
      process.env.JWT_SECRET || 'your-secret-key',
      { expiresIn: process.env.JWT_EXPIRES_IN || '24h' }
    );

    logger.auth('register', user._id, user.email, true);

    res.status(201).json({
      message: 'User registered successfully',
      user: user.toSafeJSON(),
      token
    });

  } catch (error) {
    logger.error('Registration error:', error);
    res.status(500).json({
      error: 'Registration failed',
      message: 'Unable to register user'
    });
  }
});

/**
 * 사용자 로그인
 * POST /api/users/login
 */
router.post('/login', [
  body('email')
    .isEmail()
    .normalizeEmail()
    .withMessage('Please provide a valid email'),
  body('password')
    .notEmpty()
    .withMessage('Password is required')
], async (req, res) => {
  try {
    // 입력 검증
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      });
    }

    const { email, password } = req.body;

    // 사용자 찾기
    const user = await User.findByEmail(email);
    if (!user) {
      logger.auth('login', null, email, false, new Error('User not found'));
      return res.status(401).json({
        error: 'Authentication failed',
        message: 'Invalid email or password'
      });
    }

    // 계정 잠금 확인
    if (user.isLocked) {
      logger.auth('login', user._id, email, false, new Error('Account locked'));
      return res.status(423).json({
        error: 'Account locked',
        message: 'Account is temporarily locked due to too many failed login attempts'
      });
    }

    // 비밀번호 확인
    const isPasswordValid = await user.comparePassword(password);
    if (!isPasswordValid) {
      await user.incLoginAttempts();
      logger.auth('login', user._id, email, false, new Error('Invalid password'));
      return res.status(401).json({
        error: 'Authentication failed',
        message: 'Invalid email or password'
      });
    }

    // 계정 상태 확인
    if (user.status !== 'active') {
      logger.auth('login', user._id, email, false, new Error('Account inactive'));
      return res.status(403).json({
        error: 'Account inactive',
        message: 'Your account is not active'
      });
    }

    // 로그인 성공 처리
    await user.resetLoginAttempts();
    user.lastLogin = new Date();
    await user.save();

    // JWT 토큰 생성
    const token = jwt.sign(
      {
        id: user._id,
        email: user.email,
        role: user.role
      },
      process.env.JWT_SECRET || 'your-secret-key',
      { expiresIn: process.env.JWT_EXPIRES_IN || '24h' }
    );

    logger.auth('login', user._id, user.email, true);

    res.json({
      message: 'Login successful',
      user: user.toSafeJSON(),
      token
    });

  } catch (error) {
    logger.error('Login error:', error);
    res.status(500).json({
      error: 'Login failed',
      message: 'Unable to process login request'
    });
  }
});

/**
 * 토큰 새로고침
 * POST /api/users/refresh
 */
router.post('/refresh', authMiddleware, async (req, res) => {
  try {
    const user = await User.findById(req.user.id);
    if (!user || user.status !== 'active') {
      return res.status(401).json({
        error: 'Invalid user',
        message: 'User not found or inactive'
      });
    }

    // 새 토큰 생성
    const token = jwt.sign(
      {
        id: user._id,
        email: user.email,
        role: user.role
      },
      process.env.JWT_SECRET || 'your-secret-key',
      { expiresIn: process.env.JWT_EXPIRES_IN || '24h' }
    );

    res.json({
      message: 'Token refreshed successfully',
      token
    });

  } catch (error) {
    logger.error('Token refresh error:', error);
    res.status(500).json({
      error: 'Token refresh failed',
      message: 'Unable to refresh token'
    });
  }
});

/**
 * 로그아웃
 * POST /api/users/logout
 */
router.post('/logout', authMiddleware, async (req, res) => {
  try {
    // 실제 구현에서는 토큰을 블랙리스트에 추가하거나
    // Redis에서 토큰을 무효화할 수 있습니다.
    
    logger.auth('logout', req.user.id, req.user.email, true);

    res.json({
      message: 'Logout successful'
    });

  } catch (error) {
    logger.error('Logout error:', error);
    res.status(500).json({
      error: 'Logout failed',
      message: 'Unable to process logout request'
    });
  }
});

/**
 * 비밀번호 변경
 * PUT /api/users/change-password
 */
router.put('/change-password', [
  authMiddleware,
  body('currentPassword')
    .notEmpty()
    .withMessage('Current password is required'),
  body('newPassword')
    .isLength({ min: 6 })
    .withMessage('New password must be at least 6 characters long')
], async (req, res) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      });
    }

    const { currentPassword, newPassword } = req.body;
    const user = await User.findById(req.user.id);

    if (!user) {
      return res.status(404).json({
        error: 'User not found'
      });
    }

    // 현재 비밀번호 확인
    const isCurrentPasswordValid = await user.comparePassword(currentPassword);
    if (!isCurrentPasswordValid) {
      return res.status(401).json({
        error: 'Invalid current password'
      });
    }

    // 새 비밀번호 설정
    user.password = newPassword;
    await user.save();

    logger.auth('password_change', user._id, user.email, true);

    res.json({
      message: 'Password changed successfully'
    });

  } catch (error) {
    logger.error('Password change error:', error);
    res.status(500).json({
      error: 'Password change failed',
      message: 'Unable to change password'
    });
  }
});

module.exports = router;
