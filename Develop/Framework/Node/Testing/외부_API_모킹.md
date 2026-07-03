---
title: 외부 API 모킹 가이드
tags: [framework, node, testing, mocking, nock, axios-mock-adapter, external-api, integration-testing]
updated: 2025-09-17
---

# 외부 API 모킹 가이드

## 배경

### 외부 API 모킹이란?
외부 API 모킹은 테스트 환경에서 외부 서비스에 대한 실제 HTTP 요청을 가로채고 미리 정의된 응답을 반환하는 기술입니다. 이를 통해 외부 의존성 없이 안정적이고 빠른 테스트를 수행할 수 있습니다.

### 외부 API 모킹의 필요성
- **테스트 안정성**: 외부 서비스 장애나 변경에 영향받지 않음
- **테스트 속도**: 네트워크 지연 없이 빠른 테스트 실행
- **예측 가능성**: 일관된 응답으로 테스트 결과 보장
- **비용 절약**: 외부 API 호출 비용 및 제한 회피
- **에러 시나리오 테스트**: 다양한 에러 상황 시뮬레이션

### 기본 개념
- **HTTP 인터셉션**: 네트워크 요청을 가로채고 모킹된 응답 반환
- **요청 매칭**: URL, 메서드, 헤더, 바디 등을 기반으로 요청 식별
- **응답 시뮬레이션**: 성공, 실패, 지연 등 다양한 응답 상황 구현
- **상태 관리**: 모킹 상태의 활성화/비활성화 관리

## 핵심

### 1. nock을 사용한 HTTP 요청 모킹

#### nock 설치 및 기본 설정
```bash
npm install --save-dev nock
```

#### 기본 모킹 패턴
```javascript
// tests/mocks/nockSetup.js
const nock = require('nock');

// 기본 설정
const setupNock = () => {
  // 모든 HTTP 요청을 가로채기
  nock.disableNetConnect();
  
  // localhost는 허용 (데이터베이스 연결 등)
  nock.enableNetConnect('127.0.0.1');
  nock.enableNetConnect('localhost');
};

const cleanupNock = () => {
  // 모든 모킹 정리
  nock.cleanAll();
  
  // 네트워크 연결 복원
  nock.enableNetConnect();
};

module.exports = { setupNock, cleanupNock };
```

#### REST API 모킹 예제
```javascript
// tests/mocks/userApiMock.js
const nock = require('nock');

class UserApiMock {
  constructor(baseUrl = 'https://api.example.com') {
    this.baseUrl = baseUrl;
    this.scope = nock(baseUrl);
  }

  // 사용자 조회 모킹
  mockGetUser(userId, response = null) {
    const defaultResponse = {
      id: userId,
      name: 'John Doe',
      email: 'john@example.com',
      status: 'active'
    };

    return this.scope
      .get(`/users/${userId}`)
      .reply(200, response || defaultResponse);
  }

  // 사용자 목록 조회 모킹
  mockGetUsers(query = {}, response = null) {
    const defaultResponse = {
      users: [
        { id: 1, name: 'John Doe', email: 'john@example.com' },
        { id: 2, name: 'Jane Smith', email: 'jane@example.com' }
      ],
      total: 2,
      page: 1,
      limit: 10
    };

    return this.scope
      .get('/users')
      .query(query)
      .reply(200, response || defaultResponse);
  }

  // 사용자 생성 모킹
  mockCreateUser(userData, response = null) {
    const defaultResponse = {
      id: 123,
      ...userData,
      createdAt: '2024-01-01T00:00:00Z'
    };

    return this.scope
      .post('/users', userData)
      .reply(201, response || defaultResponse);
  }

  // 사용자 업데이트 모킹
  mockUpdateUser(userId, userData, response = null) {
    const defaultResponse = {
      id: userId,
      ...userData,
      updatedAt: '2024-01-01T00:00:00Z'
    };

    return this.scope
      .put(`/users/${userId}`, userData)
      .reply(200, response || defaultResponse);
  }

  // 사용자 삭제 모킹
  mockDeleteUser(userId) {
    return this.scope
      .delete(`/users/${userId}`)
      .reply(204);
  }

  // 에러 응답 모킹
  mockErrorResponse(method, path, statusCode = 500, errorMessage = 'Internal Server Error') {
    return this.scope
      [method.toLowerCase()](path)
      .reply(statusCode, {
        error: {
          code: statusCode,
          message: errorMessage
        }
      });
  }

  // 네트워크 지연 모킹
  mockDelayedResponse(method, path, delay = 1000, response = {}) {
    return this.scope
      [method.toLowerCase()](path)
      .delay(delay)
      .reply(200, response);
  }

  // 헤더 검증 모킹
  mockWithHeaderValidation(method, path, expectedHeaders, response = {}) {
    return this.scope
      [method.toLowerCase()](path)
      .matchHeader('authorization', expectedHeaders.authorization)
      .matchHeader('content-type', expectedHeaders['content-type'])
      .reply(200, response);
  }
}

module.exports = UserApiMock;
```

### 2. axios-mock-adapter 활용법

#### axios-mock-adapter 설치 및 설정
```bash
npm install --save-dev axios-mock-adapter
```

#### 기본 사용법
```javascript
// tests/mocks/axiosMockSetup.js
const axios = require('axios');
const MockAdapter = require('axios-mock-adapter');

class AxiosMockSetup {
  constructor() {
    this.mock = new MockAdapter(axios);
  }

  // 기본 모킹 설정
  setupBasicMocks() {
    // GET 요청 모킹
    this.mock.onGet('/users/1').reply(200, {
      id: 1,
      name: 'John Doe',
      email: 'john@example.com'
    });

    // POST 요청 모킹
    this.mock.onPost('/users').reply(201, {
      id: 123,
      name: 'New User',
      email: 'new@example.com'
    });

    // PUT 요청 모킹
    this.mock.onPut('/users/1').reply(200, {
      id: 1,
      name: 'Updated User',
      email: 'updated@example.com'
    });

    // DELETE 요청 모킹
    this.mock.onDelete('/users/1').reply(204);
  }

  // 동적 응답 모킹
  setupDynamicMocks() {
    // 요청 데이터에 따른 동적 응답
    this.mock.onPost('/users').reply((config) => {
      const userData = JSON.parse(config.data);
      
      if (userData.email === 'duplicate@example.com') {
        return [409, { error: 'Email already exists' }];
      }
      
      return [201, {
        id: Math.floor(Math.random() * 1000),
        ...userData,
        createdAt: new Date().toISOString()
      }];
    });

    // 쿼리 파라미터에 따른 동적 응답
    this.mock.onGet('/users').reply((config) => {
      const params = new URLSearchParams(config.url.split('?')[1]);
      const page = parseInt(params.get('page')) || 1;
      const limit = parseInt(params.get('limit')) || 10;
      
      const users = Array.from({ length: limit }, (_, i) => ({
        id: (page - 1) * limit + i + 1,
        name: `User ${(page - 1) * limit + i + 1}`,
        email: `user${(page - 1) * limit + i + 1}@example.com`
      }));

      return [200, {
        users,
        pagination: {
          page,
          limit,
          total: 100
        }
      }];
    });
  }

  // 에러 시나리오 모킹
  setupErrorMocks() {
    // 404 에러
    this.mock.onGet('/users/999').reply(404, {
      error: 'User not found'
    });

    // 500 에러
    this.mock.onGet('/users/error').reply(500, {
      error: 'Internal server error'
    });

    // 네트워크 에러
    this.mock.onGet('/users/network-error').networkError();

    // 타임아웃 에러
    this.mock.onGet('/users/timeout').timeout();
  }

  // 정리
  cleanup() {
    this.mock.restore();
  }
}

module.exports = AxiosMockSetup;
```

### 3. 외부 서비스 장애 시뮬레이션

#### 다양한 장애 시나리오
```javascript
// tests/mocks/failureSimulation.js
const nock = require('nock');

class FailureSimulation {
  constructor(baseUrl = 'https://api.example.com') {
    this.baseUrl = baseUrl;
    this.scope = nock(baseUrl);
  }

  // 서버 에러 시뮬레이션
  simulateServerError(path, statusCode = 500) {
    return this.scope
      .get(path)
      .reply(statusCode, {
        error: {
          code: statusCode,
          message: 'Internal Server Error'
        }
      });
  }

  // 네트워크 타임아웃 시뮬레이션
  simulateTimeout(path, timeout = 5000) {
    return this.scope
      .get(path)
      .delay(timeout)
      .reply(200, { message: 'This should timeout' });
  }

  // 네트워크 연결 실패 시뮬레이션
  simulateNetworkError(path) {
    return this.scope
      .get(path)
      .replyWithError('ECONNREFUSED');
  }

  // 일시적 장애 시뮬레이션 (재시도 후 성공)
  simulateTemporaryFailure(path, failureCount = 2) {
    let callCount = 0;
    
    return this.scope
      .get(path)
      .reply(() => {
        callCount++;
        if (callCount <= failureCount) {
          return [500, { error: 'Temporary failure' }];
        }
        return [200, { message: 'Success after retry' }];
      });
  }

  // 느린 응답 시뮬레이션
  simulateSlowResponse(path, delay = 3000) {
    return this.scope
      .get(path)
      .delay(delay)
      .reply(200, { message: 'Slow response' });
  }

  // 부분적 실패 시뮬레이션
  simulatePartialFailure(path, failureRate = 0.5) {
    return this.scope
      .get(path)
      .reply(() => {
        if (Math.random() < failureRate) {
          return [500, { error: 'Random failure' }];
        }
        return [200, { message: 'Success' }];
      });
  }

  // 인증 실패 시뮬레이션
  simulateAuthFailure(path) {
    return this.scope
      .get(path)
      .reply(401, {
        error: {
          code: 401,
          message: 'Unauthorized'
        }
      });
  }

  // 할당량 초과 시뮬레이션
  simulateRateLimit(path, retryAfter = 60) {
    return this.scope
      .get(path)
      .reply(429, {
        error: {
          code: 429,
          message: 'Rate limit exceeded'
        }
      }, {
        'Retry-After': retryAfter
      });
  }
}

module.exports = FailureSimulation;
```

### 4. 모킹 데이터 관리

#### 모킹 데이터 팩토리
```javascript
// tests/mocks/mockDataFactory.js
class MockDataFactory {
  // 사용자 데이터 생성
  static createUser(overrides = {}) {
    const defaultUser = {
      id: Math.floor(Math.random() * 1000),
      name: 'John Doe',
      email: 'john@example.com',
      status: 'active',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z'
    };

    return { ...defaultUser, ...overrides };
  }

  // 사용자 목록 생성
  static createUserList(count = 5, overrides = {}) {
    return Array.from({ length: count }, (_, index) => 
      this.createUser({
        id: index + 1,
        name: `User ${index + 1}`,
        email: `user${index + 1}@example.com`,
        ...overrides
      })
    );
  }

  // API 응답 생성
  static createApiResponse(data, meta = {}) {
    return {
      data,
      meta: {
        timestamp: new Date().toISOString(),
        version: '1.0',
        ...meta
      }
    };
  }

  // 페이지네이션 응답 생성
  static createPaginatedResponse(data, page = 1, limit = 10, total = null) {
    const totalCount = total || data.length;
    
    return {
      data,
      pagination: {
        page,
        limit,
        total: totalCount,
        totalPages: Math.ceil(totalCount / limit),
        hasNext: page < Math.ceil(totalCount / limit),
        hasPrev: page > 1
      }
    };
  }

  // 에러 응답 생성
  static createErrorResponse(code = 500, message = 'Internal Server Error', details = {}) {
    return {
      error: {
        code,
        message,
        details,
        timestamp: new Date().toISOString()
      }
    };
  }
}

module.exports = MockDataFactory;
```

#### 모킹 데이터 관리자
```javascript
// tests/mocks/mockDataManager.js
const MockDataFactory = require('./mockDataFactory');

class MockDataManager {
  constructor() {
    this.dataStore = new Map();
    this.setupDefaultData();
  }

  // 기본 데이터 설정
  setupDefaultData() {
    this.dataStore.set('users', MockDataFactory.createUserList(10));
    this.dataStore.set('posts', this.generatePosts(20));
    this.dataStore.set('comments', this.generateComments(50));
  }

  // 게시물 데이터 생성
  generatePosts(count) {
    return Array.from({ length: count }, (_, index) => ({
      id: index + 1,
      title: `Post ${index + 1}`,
      content: `This is the content of post ${index + 1}`,
      authorId: (index % 10) + 1,
      published: true,
      createdAt: new Date(Date.now() - index * 86400000).toISOString()
    }));
  }

  // 댓글 데이터 생성
  generateComments(count) {
    return Array.from({ length: count }, (_, index) => ({
      id: index + 1,
      content: `Comment ${index + 1}`,
      postId: (index % 20) + 1,
      authorId: (index % 10) + 1,
      createdAt: new Date(Date.now() - index * 3600000).toISOString()
    }));
  }

  // 데이터 조회
  getData(key) {
    return this.dataStore.get(key) || [];
  }

  // 데이터 추가
  addData(key, item) {
    const data = this.getData(key);
    data.push(item);
    this.dataStore.set(key, data);
    return item;
  }

  // 데이터 업데이트
  updateData(key, id, updates) {
    const data = this.getData(key);
    const index = data.findIndex(item => item.id === id);
    if (index !== -1) {
      data[index] = { ...data[index], ...updates };
      this.dataStore.set(key, data);
      return data[index];
    }
    return null;
  }

  // 데이터 삭제
  deleteData(key, id) {
    const data = this.getData(key);
    const filteredData = data.filter(item => item.id !== id);
    this.dataStore.set(key, filteredData);
    return filteredData.length < data.length;
  }

  // 데이터 초기화
  resetData() {
    this.dataStore.clear();
    this.setupDefaultData();
  }

  // 특정 데이터 초기화
  resetDataByKey(key) {
    this.dataStore.delete(key);
    if (key === 'users') {
      this.dataStore.set('users', MockDataFactory.createUserList(10));
    } else if (key === 'posts') {
      this.dataStore.set('posts', this.generatePosts(20));
    } else if (key === 'comments') {
      this.dataStore.set('comments', this.generateComments(50));
    }
  }
}

module.exports = MockDataManager;
```

## 예시

### 1. 실제 사용 사례

#### 사용자 서비스 통합 테스트
```javascript
// tests/integration/UserService.test.js
const { UserService } = require('../../src/services/UserService');
const UserApiMock = require('../mocks/userApiMock');
const MockDataFactory = require('../mocks/mockDataFactory');
const { setupNock, cleanupNock } = require('../mocks/nockSetup');

describe('UserService Integration Tests', () => {
  let userService;
  let userApiMock;

  beforeAll(() => {
    setupNock();
  });

  afterAll(() => {
    cleanupNock();
  });

  beforeEach(() => {
    userService = new UserService();
    userApiMock = new UserApiMock();
  });

  afterEach(() => {
    nock.cleanAll();
  });

  describe('fetchUserFromExternalApi', () => {
    it('should fetch user successfully', async () => {
      // Given
      const userId = 123;
      const mockUser = MockDataFactory.createUser({ id: userId });
      
      userApiMock.mockGetUser(userId, mockUser);

      // When
      const result = await userService.fetchUserFromExternalApi(userId);

      // Then
      expect(result).toBeDefined();
      expect(result.id).toBe(userId);
      expect(result.name).toBe(mockUser.name);
      expect(result.email).toBe(mockUser.email);
    });

    it('should handle API error gracefully', async () => {
      // Given
      const userId = 999;
      userApiMock.mockErrorResponse('GET', `/users/${userId}`, 404, 'User not found');

      // When & Then
      await expect(
        userService.fetchUserFromExternalApi(userId)
      ).rejects.toThrow('User not found');
    });

    it('should handle network timeout', async () => {
      // Given
      const userId = 123;
      userApiMock.mockDelayedResponse('GET', `/users/${userId}`, 5000);

      // When & Then
      await expect(
        userService.fetchUserFromExternalApi(userId)
      ).rejects.toThrow('timeout');
    });
  });

  describe('syncUsersFromExternalApi', () => {
    it('should sync multiple users successfully', async () => {
      // Given
      const mockUsers = MockDataFactory.createUserList(5);
      const mockResponse = MockDataFactory.createPaginatedResponse(mockUsers);
      
      userApiMock.mockGetUsers({}, mockResponse);

      // When
      const result = await userService.syncUsersFromExternalApi();

      // Then
      expect(result).toBeDefined();
      expect(result.length).toBe(5);
      expect(result[0].name).toBe('User 1');
    });

    it('should handle partial failure during sync', async () => {
      // Given
      const failureSimulation = new (require('../mocks/failureSimulation'))();
      failureSimulation.simulatePartialFailure('/users', 0.3);

      // When
      const result = await userService.syncUsersFromExternalApi();

      // Then
      expect(result).toBeDefined();
      // 일부 실패가 있어도 성공한 데이터는 반환되어야 함
    });
  });
});
```

#### 결제 서비스 통합 테스트
```javascript
// tests/integration/PaymentService.test.js
const { PaymentService } = require('../../src/services/PaymentService');
const nock = require('nock');

describe('PaymentService Integration Tests', () => {
  let paymentService;

  beforeEach(() => {
    paymentService = new PaymentService();
  });

  afterEach(() => {
    nock.cleanAll();
  });

  describe('processPayment', () => {
    it('should process payment successfully', async () => {
      // Given
      const paymentData = {
        amount: 10000,
        currency: 'KRW',
        cardNumber: '4111111111111111',
        expiryDate: '12/25',
        cvv: '123'
      };

      const mockResponse = {
        transactionId: 'txn_123456789',
        status: 'succeeded',
        amount: 10000,
        currency: 'KRW'
      };

      nock('https://api.payment.com')
        .post('/payments', paymentData)
        .reply(201, mockResponse);

      // When
      const result = await paymentService.processPayment(paymentData);

      // Then
      expect(result).toBeDefined();
      expect(result.transactionId).toBe('txn_123456789');
      expect(result.status).toBe('succeeded');
    });

    it('should handle payment failure', async () => {
      // Given
      const paymentData = {
        amount: 10000,
        currency: 'KRW',
        cardNumber: '4000000000000002', // 실패 카드 번호
        expiryDate: '12/25',
        cvv: '123'
      };

      nock('https://api.payment.com')
        .post('/payments', paymentData)
        .reply(402, {
          error: {
            code: 'card_declined',
            message: 'Your card was declined'
          }
        });

      // When & Then
      await expect(
        paymentService.processPayment(paymentData)
      ).rejects.toThrow('Your card was declined');
    });

    it('should retry on temporary failure', async () => {
      // Given
      const paymentData = {
        amount: 10000,
        currency: 'KRW',
        cardNumber: '4111111111111111',
        expiryDate: '12/25',
        cvv: '123'
      };

      const successResponse = {
        transactionId: 'txn_123456789',
        status: 'succeeded',
        amount: 10000,
        currency: 'KRW'
      };

      // 첫 번째 요청은 실패, 두 번째 요청은 성공
      nock('https://api.payment.com')
        .post('/payments', paymentData)
        .reply(500, { error: 'Temporary failure' });

      nock('https://api.payment.com')
        .post('/payments', paymentData)
        .reply(201, successResponse);

      // When
      const result = await paymentService.processPayment(paymentData);

      // Then
      expect(result).toBeDefined();
      expect(result.status).toBe('succeeded');
    });
  });
});
```

### 2. 고급 패턴

#### 조건부 모킹
```javascript
// tests/mocks/conditionalMocking.js
const nock = require('nock');

class ConditionalMocking {
  constructor(baseUrl = 'https://api.example.com') {
    this.baseUrl = baseUrl;
    this.scope = nock(baseUrl);
  }

  // 요청 횟수에 따른 다른 응답
  mockWithCallCount(path, responses) {
    let callCount = 0;
    
    return this.scope
      .get(path)
      .reply(() => {
        const response = responses[callCount] || responses[responses.length - 1];
        callCount++;
        return [response.status, response.data];
      });
  }

  // 요청 데이터에 따른 조건부 응답
  mockWithConditionalResponse(method, path, condition, successResponse, errorResponse) {
    return this.scope
      [method.toLowerCase()](path)
      .reply((uri, requestBody) => {
        if (condition(requestBody)) {
          return [200, successResponse];
        } else {
          return [400, errorResponse];
        }
      });
  }

  // 헤더 기반 조건부 응답
  mockWithHeaderCondition(path, headerName, expectedValue, successResponse, errorResponse) {
    return this.scope
      .get(path)
      .matchHeader(headerName, expectedValue)
      .reply(200, successResponse)
      .get(path)
      .reply(401, errorResponse);
  }
}

module.exports = ConditionalMocking;
```

#### 모킹 상태 관리
```javascript
// tests/mocks/mockStateManager.js
class MockStateManager {
  constructor() {
    this.states = new Map();
    this.currentState = 'default';
  }

  // 상태 설정
  setState(stateName) {
    this.currentState = stateName;
  }

  // 상태별 모킹 설정
  setupStateMocks() {
    // 기본 상태
    this.states.set('default', {
      userApi: { status: 'healthy', responseTime: 100 },
      paymentApi: { status: 'healthy', responseTime: 200 },
      notificationApi: { status: 'healthy', responseTime: 150 }
    });

    // 장애 상태
    this.states.set('degraded', {
      userApi: { status: 'healthy', responseTime: 100 },
      paymentApi: { status: 'slow', responseTime: 5000 },
      notificationApi: { status: 'error', responseTime: 0 }
    });

    // 완전 장애 상태
    this.states.set('down', {
      userApi: { status: 'error', responseTime: 0 },
      paymentApi: { status: 'error', responseTime: 0 },
      notificationApi: { status: 'error', responseTime: 0 }
    });
  }

  // 현재 상태에 따른 모킹 적용
  applyCurrentState() {
    const state = this.states.get(this.currentState);
    if (!state) return;

    Object.entries(state).forEach(([apiName, config]) => {
      this.applyApiMock(apiName, config);
    });
  }

  // API별 모킹 적용
  applyApiMock(apiName, config) {
    const nock = require('nock');
    const baseUrl = this.getApiBaseUrl(apiName);
    const scope = nock(baseUrl);

    switch (config.status) {
      case 'healthy':
        this.setupHealthyMock(scope, apiName);
        break;
      case 'slow':
        this.setupSlowMock(scope, apiName, config.responseTime);
        break;
      case 'error':
        this.setupErrorMock(scope, apiName);
        break;
    }
  }

  // API 기본 URL 반환
  getApiBaseUrl(apiName) {
    const urls = {
      userApi: 'https://api.users.com',
      paymentApi: 'https://api.payments.com',
      notificationApi: 'https://api.notifications.com'
    };
    return urls[apiName];
  }

  // 정상 모킹 설정
  setupHealthyMock(scope, apiName) {
    scope.get('/health').reply(200, { status: 'healthy' });
    // API별 기본 엔드포인트 모킹
  }

  // 느린 응답 모킹 설정
  setupSlowMock(scope, apiName, responseTime) {
    scope.get('/health').delay(responseTime).reply(200, { status: 'slow' });
  }

  // 에러 모킹 설정
  setupErrorMock(scope, apiName) {
    scope.get('/health').reply(500, { status: 'error' });
  }
}

module.exports = MockStateManager;
```

## 운영 팁

### 1. 모킹 최적화

#### 모킹 범위 관리
```javascript
// tests/helpers/mockScopeManager.js
class MockScopeManager {
  constructor() {
    this.scopes = new Map();
  }

  // 특정 도메인만 모킹
  mockSpecificDomain(domain) {
    const nock = require('nock');
    const scope = nock(domain);
    this.scopes.set(domain, scope);
    return scope;
  }

  // 모든 외부 요청 모킹 (localhost 제외)
  mockAllExternal() {
    const nock = require('nock');
    nock.disableNetConnect();
    nock.enableNetConnect('127.0.0.1');
    nock.enableNetConnect('localhost');
  }

  // 특정 경로만 모킹
  mockSpecificPath(baseUrl, path) {
    const nock = require('nock');
    return nock(baseUrl).get(path);
  }

  // 정리
  cleanup() {
    this.scopes.forEach(scope => scope.cleanAll());
    this.scopes.clear();
  }
}

module.exports = MockScopeManager;
```

### 2. 테스트 성능 최적화

#### 모킹 캐싱
```javascript
// tests/helpers/mockCache.js
class MockCache {
  constructor() {
    this.cache = new Map();
  }

  // 모킹 설정 캐싱
  cacheMock(key, mockSetup) {
    if (!this.cache.has(key)) {
      this.cache.set(key, mockSetup());
    }
    return this.cache.get(key);
  }

  // 캐시된 모킹 사용
  useCachedMock(key) {
    const cachedMock = this.cache.get(key);
    if (cachedMock) {
      return cachedMock;
    }
    throw new Error(`No cached mock found for key: ${key}`);
  }

  // 캐시 정리
  clearCache() {
    this.cache.clear();
  }
}

module.exports = new MockCache();
```

### 3. 디버깅 및 모니터링

#### 모킹 로깅
```javascript
// tests/helpers/mockLogger.js
class MockLogger {
  constructor() {
    this.logs = [];
  }

  // 모킹 요청 로깅
  logRequest(method, url, body, headers) {
    const log = {
      timestamp: new Date().toISOString(),
      type: 'request',
      method,
      url,
      body,
      headers
    };
    this.logs.push(log);
    console.log(`[MOCK REQUEST] ${method} ${url}`);
  }

  // 모킹 응답 로깅
  logResponse(status, data, headers) {
    const log = {
      timestamp: new Date().toISOString(),
      type: 'response',
      status,
      data,
      headers
    };
    this.logs.push(log);
    console.log(`[MOCK RESPONSE] ${status}`);
  }

  // 로그 조회
  getLogs() {
    return this.logs;
  }

  // 로그 정리
  clearLogs() {
    this.logs = [];
  }
}

module.exports = new MockLogger();
```

## 참고

### 모킹 도구 비교

| 도구 | 장점 | 단점 | 사용 사례 |
|------|------|------|-----------|
| **nock** | 강력한 매칭, 유연한 설정 | 설정 복잡성 | 복잡한 API 모킹 |
| **axios-mock-adapter** | 간단한 설정, axios 전용 | axios에만 특화 | axios 기반 프로젝트 |
| **MSW** | 브라우저/Node.js 지원 | 상대적으로 새로운 도구 | 풀스택 애플리케이션 |

### 참고

#### 모킹 원칙
1. **실제 API와 유사한 응답** 구조 유지
2. **에러 시나리오** 포함한 테스트
3. **모킹 범위** 최소화
4. **테스트 격리** 보장

#### 성능 고려사항
1. **모킹 설정 최적화**
2. **불필요한 모킹 제거**
3. **캐싱 활용**
4. **병렬 테스트 실행**

### 결론
외부 API 모킹은 안정적이고 빠른 테스트를 위한 필수 기술입니다.
nock과 axios-mock-adapter를 적절히 활용하여 외부 의존성 없이 완전한 테스트를 구축할 수 있습니다.
다양한 장애 시나리오를 시뮬레이션하여 견고한 애플리케이션을 개발하세요.
모킹 데이터 관리를 통해 일관되고 유지보수하기 쉬운 테스트를 작성하세요.
