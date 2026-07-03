---
title: API E2E 테스트 패턴
tags: [framework, node, testing, api, e2e, rest, authentication, express, integration-testing]
updated: 2025-12-13
---

# API E2E 테스트 패턴 가이드

## 배경

### API E2E 테스트란?
API E2E(End-to-End) 테스트는 API의 전체 플로우를 실제 환경과 유사한 조건에서 테스트하는 방법입니다. 데이터베이스, 외부 서비스, 인증 시스템 등 모든 의존성을 포함하여 실제 사용자 시나리오를 검증합니다.

### API E2E 테스트의 필요성
- **전체 플로우 검증**: API 요청부터 응답까지 전체 과정 확인
- **통합 검증**: 데이터베이스, 외부 서비스, 인증 시스템 간 상호작용 확인
- **회귀 테스트**: 새로운 기능 추가 시 기존 API 영향도 확인
- **성능 검증**: 실제 환경에서의 API 성능 측정
- **보안 검증**: 인증/인가 플로우의 보안성 확인

### 기본 개념
- **테스트 격리**: 각 테스트가 독립적으로 실행되도록 보장
- **데이터 정리**: 테스트 후 데이터베이스 상태 복원
- **환경 분리**: 테스트 전용 환경과 프로덕션 환경 분리
- **의존성 관리**: 외부 서비스 의존성 모킹 또는 테스트 더블 사용

## 핵심

### 1. REST API 전체 플로우 테스트

#### 기본 API 테스트 구조
```javascript
// tests/e2e/api/user-management.test.js
const request = require('supertest');
const app = require('../../src/app');
const { setupTestDB, cleanupTestDB } = require('../helpers/database');
const { createTestUser, deleteTestUser } = require('../helpers/userHelpers');

describe('User Management API E2E', () => {
  let testUser;
  let authToken;

  beforeAll(async () => {
    await setupTestDB();
  });

  afterAll(async () => {
    await cleanupTestDB();
  });

  beforeEach(async () => {
    testUser = await createTestUser({
      name: 'Test User',
      email: 'test@example.com',
      password: 'password123'
    });
  });

  afterEach(async () => {
    if (testUser) {
      await deleteTestUser(testUser.id);
    }
  });

  describe('POST /api/users', () => {
    it('should create a new user successfully', async () => {
      const newUser = {
        name: 'New User',
        email: 'newuser@example.com',
        password: 'password123'
      };

      const response = await request(app)
        .post('/api/users')
        .send(newUser)
        .expect(201);

      expect(response.body).toMatchObject({
        id: expect.any(String),
        name: newUser.name,
        email: newUser.email,
        createdAt: expect.any(String)
      });
      expect(response.body.password).toBeUndefined();
    });

    it('should return 400 for invalid user data', async () => {
      const invalidUser = {
        name: '',
        email: 'invalid-email',
        password: '123'
      };

      const response = await request(app)
        .post('/api/users')
        .send(invalidUser)
        .expect(400);

      expect(response.body).toMatchObject({
        error: 'Validation failed',
        details: expect.arrayContaining([
          expect.objectContaining({
            field: 'name',
            message: expect.any(String)
          }),
          expect.objectContaining({
            field: 'email',
            message: expect.any(String)
          }),
          expect.objectContaining({
            field: 'password',
            message: expect.any(String)
          })
        ])
      });
    });

    it('should return 409 for duplicate email', async () => {
      const duplicateUser = {
        name: 'Duplicate User',
        email: testUser.email, // 이미 존재하는 이메일
        password: 'password123'
      };

      const response = await request(app)
        .post('/api/users')
        .send(duplicateUser)
        .expect(409);

      expect(response.body).toMatchObject({
        error: 'Email already exists'
      });
    });
  });

  describe('GET /api/users', () => {
    beforeEach(async () => {
      // 인증 토큰 획득
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          password: 'password123'
        });
      
      authToken = loginResponse.body.token;
    });

    it('should get all users with pagination', async () => {
      const response = await request(app)
        .get('/api/users?page=1&limit=10')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body).toMatchObject({
        users: expect.arrayContaining([
          expect.objectContaining({
            id: expect.any(String),
            name: expect.any(String),
            email: expect.any(String)
          })
        ]),
        pagination: {
          page: 1,
          limit: 10,
          total: expect.any(Number),
          totalPages: expect.any(Number)
        }
      });
    });

    it('should filter users by name', async () => {
      const response = await request(app)
        .get('/api/users?name=Test')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.users).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            name: expect.stringContaining('Test')
          })
        ])
      );
    });
  });

  describe('PUT /api/users/:id', () => {
    beforeEach(async () => {
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          password: 'password123'
        });
      
      authToken = loginResponse.body.token;
    });

    it('should update user successfully', async () => {
      const updateData = {
        name: 'Updated User',
        email: 'updated@example.com'
      };

      const response = await request(app)
        .put(`/api/users/${testUser.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send(updateData)
        .expect(200);

      expect(response.body).toMatchObject({
        id: testUser.id,
        name: updateData.name,
        email: updateData.email,
        updatedAt: expect.any(String)
      });
    });

    it('should return 403 for unauthorized update', async () => {
      const otherUser = await createTestUser({
        name: 'Other User',
        email: 'other@example.com',
        password: 'password123'
      });

      const updateData = {
        name: 'Unauthorized Update'
      };

      await request(app)
        .put(`/api/users/${otherUser.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send(updateData)
        .expect(403);

      await deleteTestUser(otherUser.id);
    });
  });

  describe('DELETE /api/users/:id', () => {
    beforeEach(async () => {
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          password: 'password123'
        });
      
      authToken = loginResponse.body.token;
    });

    it('should delete user successfully', async () => {
      await request(app)
        .delete(`/api/users/${testUser.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(204);

      // 삭제 확인
      await request(app)
        .get(`/api/users/${testUser.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(404);
    });
  });
});
```

### 2. 인증/인가 플로우 테스트

#### JWT 인증 플로우 테스트
```javascript
// tests/e2e/api/authentication.test.js
const request = require('supertest');
const app = require('../../src/app');
const jwt = require('jsonwebtoken');
const { setupTestDB, cleanupTestDB } = require('../helpers/database');
const { createTestUser, deleteTestUser } = require('../helpers/userHelpers');

describe('Authentication API E2E', () => {
  let testUser;

  beforeAll(async () => {
    await setupTestDB();
  });

  afterAll(async () => {
    await cleanupTestDB();
  });

  beforeEach(async () => {
    testUser = await createTestUser({
      name: 'Test User',
      email: 'test@example.com',
      password: 'password123'
    });
  });

  afterEach(async () => {
    if (testUser) {
      await deleteTestUser(testUser.id);
    }
  });

  describe('POST /api/auth/login', () => {
    it('should login successfully with valid credentials', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          password: 'password123'
        })
        .expect(200);

      expect(response.body).toMatchObject({
        token: expect.any(String),
        user: {
          id: testUser.id,
          name: testUser.name,
          email: testUser.email
        },
        expiresIn: expect.any(String)
      });

      // JWT 토큰 검증
      const decoded = jwt.verify(response.body.token, process.env.JWT_SECRET);
      expect(decoded.userId).toBe(testUser.id);
    });

    it('should return 401 for invalid credentials', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          password: 'wrongpassword'
        })
        .expect(401);

      expect(response.body).toMatchObject({
        error: 'Invalid credentials'
      });
    });

    it('should return 401 for non-existent user', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'nonexistent@example.com',
          password: 'password123'
        })
        .expect(401);

      expect(response.body).toMatchObject({
        error: 'Invalid credentials'
      });
    });

    it('should return 429 for too many login attempts', async () => {
      // 5번의 실패한 로그인 시도
      for (let i = 0; i < 5; i++) {
        await request(app)
          .post('/api/auth/login')
          .send({
            email: testUser.email,
            password: 'wrongpassword'
          });
      }

      // 6번째 시도에서 429 에러
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          password: 'wrongpassword'
        })
        .expect(429);

      expect(response.body).toMatchObject({
        error: 'Too many login attempts',
        retryAfter: expect.any(Number)
      });
    });
  });

  describe('POST /api/auth/refresh', () => {
    let refreshToken;

    beforeEach(async () => {
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          password: 'password123'
        });
      
      refreshToken = loginResponse.body.refreshToken;
    });

    it('should refresh token successfully', async () => {
      const response = await request(app)
        .post('/api/auth/refresh')
        .send({ refreshToken })
        .expect(200);

      expect(response.body).toMatchObject({
        token: expect.any(String),
        expiresIn: expect.any(String)
      });

      // 새 토큰이 이전 토큰과 다른지 확인
      const newDecoded = jwt.verify(response.body.token, process.env.JWT_SECRET);
      expect(newDecoded.userId).toBe(testUser.id);
    });

    it('should return 401 for invalid refresh token', async () => {
      const response = await request(app)
        .post('/api/auth/refresh')
        .send({ refreshToken: 'invalid-token' })
        .expect(401);

      expect(response.body).toMatchObject({
        error: 'Invalid refresh token'
      });
    });
  });

  describe('POST /api/auth/logout', () => {
    let authToken;

    beforeEach(async () => {
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          password: 'password123'
        });
      
      authToken = loginResponse.body.token;
    });

    it('should logout successfully', async () => {
      const response = await request(app)
        .post('/api/auth/logout')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body).toMatchObject({
        message: 'Logged out successfully'
      });

      // 로그아웃 후 토큰이 무효화되었는지 확인
      await request(app)
        .get('/api/users/me')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(401);
    });
  });

  describe('Authorization Middleware', () => {
    let authToken;

    beforeEach(async () => {
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          password: 'password123'
        });
      
      authToken = loginResponse.body.token;
    });

    it('should allow access with valid token', async () => {
      const response = await request(app)
        .get('/api/users/me')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body).toMatchObject({
        id: testUser.id,
        name: testUser.name,
        email: testUser.email
      });
    });

    it('should deny access without token', async () => {
      const response = await request(app)
        .get('/api/users/me')
        .expect(401);

      expect(response.body).toMatchObject({
        error: 'Access token required'
      });
    });

    it('should deny access with invalid token', async () => {
      const response = await request(app)
        .get('/api/users/me')
        .set('Authorization', 'Bearer invalid-token')
        .expect(401);

      expect(response.body).toMatchObject({
        error: 'Invalid token'
      });
    });

    it('should deny access with expired token', async () => {
      // 만료된 토큰 생성
      const expiredToken = jwt.sign(
        { userId: testUser.id },
        process.env.JWT_SECRET,
        { expiresIn: '-1h' }
      );

      const response = await request(app)
        .get('/api/users/me')
        .set('Authorization', `Bearer ${expiredToken}`)
        .expect(401);

      expect(response.body).toMatchObject({
        error: 'Token expired'
      });
    });
  });
});
```

### 3. 에러 케이스 테스트

#### 에러 핸들링 테스트
```javascript
// tests/e2e/api/error-handling.test.js
const request = require('supertest');
const app = require('../../src/app');
const { setupTestDB, cleanupTestDB } = require('../helpers/database');

describe('Error Handling API E2E', () => {
  beforeAll(async () => {
    await setupTestDB();
  });

  afterAll(async () => {
    await cleanupTestDB();
  });

  describe('Validation Errors', () => {
    it('should return 400 for missing required fields', async () => {
      const response = await request(app)
        .post('/api/users')
        .send({})
        .expect(400);

      expect(response.body).toMatchObject({
        error: 'Validation failed',
        details: expect.arrayContaining([
          expect.objectContaining({
            field: 'name',
            message: expect.stringContaining('required')
          }),
          expect.objectContaining({
            field: 'email',
            message: expect.stringContaining('required')
          }),
          expect.objectContaining({
            field: 'password',
            message: expect.stringContaining('required')
          })
        ])
      });
    });

    it('should return 400 for invalid data types', async () => {
      const response = await request(app)
        .post('/api/users')
        .send({
          name: 123,
          email: 'invalid-email',
          password: 'short'
        })
        .expect(400);

      expect(response.body).toMatchObject({
        error: 'Validation failed',
        details: expect.arrayContaining([
          expect.objectContaining({
            field: 'name',
            message: expect.stringContaining('string')
          }),
          expect.objectContaining({
            field: 'email',
            message: expect.stringContaining('email')
          }),
          expect.objectContaining({
            field: 'password',
            message: expect.stringContaining('length')
          })
        ])
      });
    });
  });

  describe('Not Found Errors', () => {
    it('should return 404 for non-existent user', async () => {
      const response = await request(app)
        .get('/api/users/non-existent-id')
        .expect(404);

      expect(response.body).toMatchObject({
        error: 'User not found'
      });
    });

    it('should return 404 for non-existent endpoint', async () => {
      const response = await request(app)
        .get('/api/non-existent-endpoint')
        .expect(404);

      expect(response.body).toMatchObject({
        error: 'Endpoint not found'
      });
    });
  });

  describe('Rate Limiting', () => {
    it('should return 429 for too many requests', async () => {
      // 100번의 요청을 빠르게 보내기
      const requests = Array(100).fill().map(() =>
        request(app).get('/api/users')
      );

      const responses = await Promise.all(requests);
      const rateLimitedResponses = responses.filter(r => r.status === 429);

      expect(rateLimitedResponses.length).toBeGreaterThan(0);
      expect(rateLimitedResponses[0].body).toMatchObject({
        error: 'Too many requests',
        retryAfter: expect.any(Number)
      });
    });
  });

  describe('Database Errors', () => {
    it('should handle database connection errors gracefully', async () => {
      // 데이터베이스 연결을 일시적으로 끊기
      const originalQuery = require('../../src/database').query;
      require('../../src/database').query = jest.fn().mockRejectedValue(
        new Error('Database connection failed')
      );

      const response = await request(app)
        .get('/api/users')
        .expect(500);

      expect(response.body).toMatchObject({
        error: 'Internal server error'
      });

      // 원래 함수 복원
      require('../../src/database').query = originalQuery;
    });
  });

  describe('External Service Errors', () => {
    it('should handle external API failures gracefully', async () => {
      // 외부 API 모킹
      const nock = require('nock');
      nock('https://external-api.com')
        .get('/data')
        .reply(500, { error: 'External service unavailable' });

      const response = await request(app)
        .get('/api/external-data')
        .expect(503);

      expect(response.body).toMatchObject({
        error: 'External service unavailable'
      });
    });
  });
});
```

## 예시

### 1. 실제 Express.js API 예제

#### Express.js 애플리케이션 구조
```javascript
// src/app.js
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { errorHandler, notFoundHandler } = require('./middleware/errorHandler');
const { authMiddleware } = require('./middleware/auth');
const userRoutes = require('./routes/users');
const authRoutes = require('./routes/auth');

const app = express();

// 보안 미들웨어
app.use(helmet());
app.use(cors());

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15분
  max: 100, // 최대 100 요청
  message: {
    error: 'Too many requests',
    retryAfter: 15 * 60
  }
});
app.use('/api/', limiter);

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// 라우트
app.use('/api/auth', authRoutes);
app.use('/api/users', authMiddleware, userRoutes);

// 에러 핸들링
app.use(notFoundHandler);
app.use(errorHandler);

module.exports = app;
```

#### 사용자 라우트
```javascript
// src/routes/users.js
const express = require('express');
const { body, param, query, validationResult } = require('express-validator');
const UserService = require('../services/UserService');
const { authorize } = require('../middleware/authorization');

const router = express.Router();

// 사용자 생성
router.post('/', [
  body('name').notEmpty().withMessage('Name is required'),
  body('email').isEmail().withMessage('Valid email is required'),
  body('password').isLength({ min: 6 }).withMessage('Password must be at least 6 characters')
], async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      });
    }

    const user = await UserService.createUser(req.body);
    res.status(201).json(user);
  } catch (error) {
    if (error.code === 'DUPLICATE_EMAIL') {
      return res.status(409).json({ error: 'Email already exists' });
    }
    next(error);
  }
});

// 사용자 목록 조회
router.get('/', [
  query('page').optional().isInt({ min: 1 }).withMessage('Page must be a positive integer'),
  query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
  query('name').optional().isString().withMessage('Name must be a string')
], async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      });
    }

    const { page = 1, limit = 10, name } = req.query;
    const result = await UserService.getUsers({ page, limit, name });
    res.json(result);
  } catch (error) {
    next(error);
  }
});

// 특정 사용자 조회
router.get('/:id', [
  param('id').isUUID().withMessage('Invalid user ID')
], async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      });
    }

    const user = await UserService.getUserById(req.params.id);
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    res.json(user);
  } catch (error) {
    next(error);
  }
});

// 사용자 정보 수정
router.put('/:id', [
  param('id').isUUID().withMessage('Invalid user ID'),
  body('name').optional().notEmpty().withMessage('Name cannot be empty'),
  body('email').optional().isEmail().withMessage('Valid email is required')
], authorize('update', 'user'), async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      });
    }

    const user = await UserService.updateUser(req.params.id, req.body, req.user);
    res.json(user);
  } catch (error) {
    if (error.code === 'NOT_FOUND') {
      return res.status(404).json({ error: 'User not found' });
    }
    if (error.code === 'UNAUTHORIZED') {
      return res.status(403).json({ error: 'Unauthorized to update this user' });
    }
    next(error);
  }
});

// 사용자 삭제
router.delete('/:id', [
  param('id').isUUID().withMessage('Invalid user ID')
], authorize('delete', 'user'), async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      });
    }

    await UserService.deleteUser(req.params.id, req.user);
    res.status(204).send();
  } catch (error) {
    if (error.code === 'NOT_FOUND') {
      return res.status(404).json({ error: 'User not found' });
    }
    if (error.code === 'UNAUTHORIZED') {
      return res.status(403).json({ error: 'Unauthorized to delete this user' });
    }
    next(error);
  }
});

module.exports = router;
```

#### 인증 라우트
```javascript
// src/routes/auth.js
const express = require('express');
const { body, validationResult } = require('express-validator');
const AuthService = require('../services/AuthService');
const { loginRateLimit } = require('../middleware/rateLimiting');

const router = express.Router();

// 로그인
router.post('/login', loginRateLimit, [
  body('email').isEmail().withMessage('Valid email is required'),
  body('password').notEmpty().withMessage('Password is required')
], async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      });
    }

    const result = await AuthService.login(req.body);
    res.json(result);
  } catch (error) {
    if (error.code === 'INVALID_CREDENTIALS') {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    if (error.code === 'TOO_MANY_ATTEMPTS') {
      return res.status(429).json({
        error: 'Too many login attempts',
        retryAfter: error.retryAfter
      });
    }
    next(error);
  }
});

// 토큰 갱신
router.post('/refresh', [
  body('refreshToken').notEmpty().withMessage('Refresh token is required')
], async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      });
    }

    const result = await AuthService.refreshToken(req.body.refreshToken);
    res.json(result);
  } catch (error) {
    if (error.code === 'INVALID_REFRESH_TOKEN') {
      return res.status(401).json({ error: 'Invalid refresh token' });
    }
    next(error);
  }
});

// 로그아웃
router.post('/logout', async (req, res, next) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    if (token) {
      await AuthService.logout(token);
    }
    res.json({ message: 'Logged out successfully' });
  } catch (error) {
    next(error);
  }
});

module.exports = router;
```

### 2. 테스트 헬퍼 함수

#### 데이터베이스 헬퍼
```javascript
// tests/helpers/database.js
const { Pool } = require('pg');
const { v4: uuidv4 } = require('uuid');

let testPool;

const setupTestDB = async () => {
  testPool = new Pool({
    host: process.env.TEST_DB_HOST || 'localhost',
    port: process.env.TEST_DB_PORT || 5432,
    database: process.env.TEST_DB_NAME || 'test_db',
    user: process.env.TEST_DB_USER || 'test_user',
    password: process.env.TEST_DB_PASSWORD || 'test_password'
  });

  // 테스트 데이터베이스 초기화
  await testPool.query('BEGIN');
};

const cleanupTestDB = async () => {
  if (testPool) {
    await testPool.query('ROLLBACK');
    await testPool.end();
  }
};

const query = async (text, params) => {
  return await testPool.query(text, params);
};

module.exports = {
  setupTestDB,
  cleanupTestDB,
  query
};
```

#### 사용자 헬퍼
```javascript
// tests/helpers/userHelpers.js
const bcrypt = require('bcrypt');
const { query } = require('./database');
const { v4: uuidv4 } = require('uuid');

const createTestUser = async (userData) => {
  const id = uuidv4();
  const hashedPassword = await bcrypt.hash(userData.password, 10);
  
  const result = await query(
    'INSERT INTO users (id, name, email, password, created_at) VALUES ($1, $2, $3, $4, NOW()) RETURNING *',
    [id, userData.name, userData.email, hashedPassword]
  );
  
  return result.rows[0];
};

const deleteTestUser = async (userId) => {
  await query('DELETE FROM users WHERE id = $1', [userId]);
};

const createTestUsers = async (count) => {
  const users = [];
  for (let i = 0; i < count; i++) {
    const user = await createTestUser({
      name: `Test User ${i}`,
      email: `test${i}@example.com`,
      password: 'password123'
    });
    users.push(user);
  }
  return users;
};

const cleanupTestUsers = async (userIds) => {
  if (userIds.length === 0) return;
  
  const placeholders = userIds.map((_, index) => `$${index + 1}`).join(',');
  await query(`DELETE FROM users WHERE id IN (${placeholders})`, userIds);
};

module.exports = {
  createTestUser,
  deleteTestUser,
  createTestUsers,
  cleanupTestUsers
};
```

### 3. 고급 테스트 패턴

#### 테스트 픽스처 관리
```javascript
// tests/fixtures/userFixtures.js
const { createTestUser, deleteTestUser } = require('../helpers/userHelpers');

class UserFixtures {
  constructor() {
    this.users = [];
  }

  async createUser(userData = {}) {
    const defaultData = {
      name: 'Test User',
      email: `test${Date.now()}@example.com`,
      password: 'password123',
      ...userData
    };

    const user = await createTestUser(defaultData);
    this.users.push(user);
    return user;
  }

  async createUsers(count, baseData = {}) {
    const users = [];
    for (let i = 0; i < count; i++) {
      const userData = {
        name: `Test User ${i}`,
        email: `test${i}${Date.now()}@example.com`,
        password: 'password123',
        ...baseData
      };
      const user = await this.createUser(userData);
      users.push(user);
    }
    return users;
  }

  async cleanup() {
    for (const user of this.users) {
      await deleteTestUser(user.id);
    }
    this.users = [];
  }
}

module.exports = UserFixtures;
```

#### 테스트 시나리오 빌더
```javascript
// tests/builders/testScenarioBuilder.js
class TestScenarioBuilder {
  constructor() {
    this.scenario = {
      setup: [],
      test: null,
      teardown: []
    };
  }

  withUser(userData = {}) {
    this.scenario.setup.push({
      type: 'createUser',
      data: userData
    });
    return this;
  }

  withUsers(count, baseData = {}) {
    this.scenario.setup.push({
      type: 'createUsers',
      data: { count, baseData }
    });
    return this;
  }

  withAuth(userData = {}) {
    this.scenario.setup.push({
      type: 'authenticate',
      data: userData
    });
    return this;
  }

  test(testFunction) {
    this.scenario.test = testFunction;
    return this;
  }

  build() {
    return this.scenario;
  }
}

module.exports = TestScenarioBuilder;
```

## 운영 팁

### 1. 테스트 환경 설정

#### 환경 변수 설정
```bash
# .env.test
NODE_ENV=test
PORT=3001
DB_HOST=localhost
DB_PORT=5432
DB_NAME=test_db
DB_USER=test_user
DB_PASSWORD=test_password
JWT_SECRET=test-secret-key
REDIS_URL=redis://localhost:6379/1
```

#### Jest 설정
```javascript
// jest.config.js
module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/tests/e2e/**/*.test.js'],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  testTimeout: 30000,
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/**/*.test.js',
    '!src/**/*.spec.js'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html']
};
```

### 2. 성능 최적화

#### 병렬 테스트 실행
```javascript
// tests/e2e/parallel/api-tests.test.js
const request = require('supertest');
const app = require('../../src/app');

describe('Parallel API Tests', () => {
  test('should handle concurrent user creation', async () => {
    const users = Array(10).fill().map((_, i) => ({
      name: `User ${i}`,
      email: `user${i}@example.com`,
      password: 'password123'
    }));

    const requests = users.map(user =>
      request(app)
        .post('/api/users')
        .send(user)
        .expect(201)
    );

    const responses = await Promise.all(requests);
    expect(responses).toHaveLength(10);
  });
});
```

### 3. 모니터링 및 리포팅

#### 테스트 결과 리포팅
```javascript
// tests/reporters/customReporter.js
class CustomReporter {
  constructor(globalConfig, options) {
    this.globalConfig = globalConfig;
    this.options = options;
  }

  onRunComplete(contexts, results) {
    const report = {
      timestamp: new Date().toISOString(),
      totalTests: results.numTotalTests,
      passed: results.numPassedTests,
      failed: results.numFailedTests,
      skipped: results.numPendingTests,
      duration: results.startTime ? Date.now() - results.startTime : 0,
      testResults: results.testResults.map(result => ({
        file: result.testFilePath,
        status: result.status,
        duration: result.perfStats.end - result.perfStats.start,
        failures: result.failureMessages
      }))
    };

    // 리포트 저장
    const fs = require('fs');
    fs.writeFileSync('test-report.json', JSON.stringify(report, null, 2));
  }
}

module.exports = CustomReporter;
```

## 참고

### 주의사항

#### 테스트 설계 원칙
1. **테스트 격리**: 각 테스트가 독립적으로 실행되도록 보장
2. **데이터 정리**: 테스트 후 데이터베이스 상태 복원
3. **명확한 어설션**: 예상 결과를 명확하게 검증
4. **에러 케이스 포함**: 정상 케이스와 에러 케이스 모두 테스트
5. **실제 시나리오**: 실제 사용자 시나리오를 반영한 테스트

#### 성능 고려사항
1. **병렬 실행**: 가능한 한 병렬로 테스트 실행
2. **데이터 최적화**: 필요한 최소한의 테스트 데이터만 생성
3. **캐싱 활용**: 반복적인 데이터 생성 최소화
4. **타임아웃 설정**: 적절한 타임아웃으로 테스트 안정성 확보
5. **리소스 관리**: 데이터베이스 연결 및 메모리 사용량 모니터링

### 결론
API E2E 테스트는 전체 시스템의 안정성을 보장하는 중요한 요소입니다.
테스트 격리, 데이터 정리, 에러 핸들링을 통해 안정적이고 신뢰할 수 있는 테스트를 구축하세요.
실제 사용자 시나리오를 반영한 테스트로 프로덕션 환경에서의 문제를 사전에 발견하고 해결할 수 있습니다.


