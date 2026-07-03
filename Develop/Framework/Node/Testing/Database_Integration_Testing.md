---
title: 데이터베이스 통합 테스트
tags: [framework, node, testing, database, integration-testing, jest, mysql, postgresql]
updated: 2025-12-13
---

# 데이터베이스 통합 테스트

## 배경

### 데이터베이스 통합 테스트란?
데이터베이스 통합 테스트는 실제 데이터베이스와 연동하여 데이터베이스 관련 로직을 검증하는 테스트입니다. 단위 테스트와 달리 실제 데이터베이스 연결, 트랜잭션, 쿼리 실행 등을 포함하여 전체적인 데이터 흐름을 테스트합니다.

### 통합 테스트의 필요성
- **실제 환경 검증**: 실제 데이터베이스와 동일한 환경에서 테스트
- **데이터 일관성 보장**: 트랜잭션 처리 및 데이터 무결성 검증
- **성능 검증**: 실제 쿼리 성능 및 최적화 확인
- **에러 처리 검증**: 데이터베이스 에러 상황 대응 테스트

### 기본 개념
- **테스트 격리**: 각 테스트가 독립적으로 실행되도록 보장
- **데이터 정리**: 테스트 후 데이터베이스 상태 초기화
- **트랜잭션 관리**: 롤백을 통한 테스트 격리
- **테스트 데이터**: 일관된 테스트 데이터 관리

## 핵심

### 1. 테스트 전용 데이터베이스 설정

#### 환경별 데이터베이스 분리
```javascript
// config/database.js
const config = {
  development: {
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT || 3306,
    database: process.env.DB_NAME || 'myapp_dev',
    username: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || 'password',
    dialect: 'mysql'
  },
  test: {
    host: process.env.TEST_DB_HOST || 'localhost',
    port: process.env.TEST_DB_PORT || 3306,
    database: process.env.TEST_DB_NAME || 'myapp_test',
    username: process.env.TEST_DB_USER || 'root',
    password: process.env.TEST_DB_PASSWORD || 'password',
    dialect: 'mysql',
    logging: false // 테스트 시 SQL 로그 비활성화
  },
  production: {
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    database: process.env.DB_NAME,
    username: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    dialect: 'mysql'
  }
};

module.exports = config;
```

#### Jest 설정
```javascript
// jest.config.js
module.exports = {
  testEnvironment: 'node',
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  testMatch: ['**/__tests__/**/*.test.js', '**/?(*.)+(spec|test).js'],
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/**/*.test.js',
    '!src/**/*.spec.js'
  ],
  testTimeout: 30000, // 데이터베이스 테스트를 위한 타임아웃 증가
  globalSetup: '<rootDir>/tests/globalSetup.js',
  globalTeardown: '<rootDir>/tests/globalTeardown.js'
};
```

### 2. 트랜잭션 롤백을 통한 테스트 격리

#### Sequelize를 사용한 트랜잭션 관리
```javascript
// tests/setup.js
const { Sequelize } = require('sequelize');
const config = require('../config/database');

let sequelize;
let transaction;

beforeAll(async () => {
  // 테스트용 데이터베이스 연결
  sequelize = new Sequelize(config.test);
  await sequelize.authenticate();
});

beforeEach(async () => {
  // 각 테스트마다 새로운 트랜잭션 시작
  transaction = await sequelize.transaction();
});

afterEach(async () => {
  // 테스트 완료 후 트랜잭션 롤백
  if (transaction) {
    await transaction.rollback();
    transaction = null;
  }
});

afterAll(async () => {
  // 모든 테스트 완료 후 연결 종료
  if (sequelize) {
    await sequelize.close();
  }
});

// 테스트에서 사용할 수 있도록 전역으로 설정
global.sequelize = sequelize;
global.getTransaction = () => transaction;
```

#### TypeORM을 사용한 트랜잭션 관리
```javascript
// tests/setup.js
const { createConnection, getConnection } = require('typeorm');
const config = require('../config/database');

let connection;

beforeAll(async () => {
  // 테스트용 데이터베이스 연결
  connection = await createConnection({
    type: 'mysql',
    host: config.test.host,
    port: config.test.port,
    username: config.test.username,
    password: config.test.password,
    database: config.test.database,
    entities: ['src/entities/**/*.js'],
    synchronize: true,
    logging: false
  });
});

beforeEach(async () => {
  // 각 테스트마다 트랜잭션 시작
  await connection.query('START TRANSACTION');
});

afterEach(async () => {
  // 테스트 완료 후 트랜잭션 롤백
  await connection.query('ROLLBACK');
});

afterAll(async () => {
  // 모든 테스트 완료 후 연결 종료
  if (connection) {
    await connection.close();
  }
});

global.getConnection = () => connection;
```

### 3. 테스트 데이터 시드 및 정리

#### 테스트 데이터 팩토리
```javascript
// tests/factories/UserFactory.js
const { User } = require('../../src/models');

class UserFactory {
  static async create(overrides = {}) {
    const defaultData = {
      name: 'Test User',
      email: `test${Date.now()}@example.com`,
      password: 'password123',
      role: 'user',
      isActive: true
    };

    const userData = { ...defaultData, ...overrides };
    return await User.create(userData);
  }

  static async createMany(count, overrides = {}) {
    const users = [];
    for (let i = 0; i < count; i++) {
      const userData = {
        name: `Test User ${i + 1}`,
        email: `test${i + 1}${Date.now()}@example.com`,
        ...overrides
      };
      users.push(await this.create(userData));
    }
    return users;
  }

  static build(overrides = {}) {
    const defaultData = {
      name: 'Test User',
      email: `test${Date.now()}@example.com`,
      password: 'password123',
      role: 'user',
      isActive: true
    };

    return { ...defaultData, ...overrides };
  }
}

module.exports = UserFactory;
```

#### 테스트 데이터 시드
```javascript
// tests/seeders/TestDataSeeder.js
const { User, Post, Comment } = require('../../src/models');
const UserFactory = require('../factories/UserFactory');

class TestDataSeeder {
  static async seedUsers(count = 5) {
    const users = [];
    for (let i = 0; i < count; i++) {
      const user = await UserFactory.create({
        name: `Test User ${i + 1}`,
        email: `user${i + 1}@test.com`
      });
      users.push(user);
    }
    return users;
  }

  static async seedPosts(users, count = 10) {
    const posts = [];
    for (let i = 0; i < count; i++) {
      const post = await Post.create({
        title: `Test Post ${i + 1}`,
        content: `This is test post content ${i + 1}`,
        authorId: users[i % users.length].id,
        published: true
      });
      posts.push(post);
    }
    return posts;
  }

  static async seedComments(posts, users, count = 20) {
    const comments = [];
    for (let i = 0; i < count; i++) {
      const comment = await Comment.create({
        content: `Test comment ${i + 1}`,
        postId: posts[i % posts.length].id,
        authorId: users[i % users.length].id
      });
      comments.push(comment);
    }
    return comments;
  }

  static async seedAll() {
    const users = await this.seedUsers();
    const posts = await this.seedPosts(users);
    const comments = await this.seedComments(posts, users);
    
    return { users, posts, comments };
  }
}

module.exports = TestDataSeeder;
```

## 예시

### 1. 실제 사용 사례

#### 사용자 서비스 통합 테스트
```javascript
// tests/integration/UserService.test.js
const { UserService } = require('../../src/services/UserService');
const { User } = require('../../src/models');
const UserFactory = require('../factories/UserFactory');

describe('UserService Integration Tests', () => {
  let userService;
  let transaction;

  beforeEach(async () => {
    userService = new UserService();
    transaction = global.getTransaction();
  });

  describe('createUser', () => {
    it('should create a new user successfully', async () => {
      // Given
      const userData = UserFactory.build({
        name: 'John Doe',
        email: 'john@example.com'
      });

      // When
      const createdUser = await userService.createUser(userData, { transaction });

      // Then
      expect(createdUser).toBeDefined();
      expect(createdUser.id).toBeDefined();
      expect(createdUser.name).toBe(userData.name);
      expect(createdUser.email).toBe(userData.email);
      expect(createdUser.password).not.toBe(userData.password); // 해시된 비밀번호

      // 데이터베이스에서 실제로 생성되었는지 확인
      const dbUser = await User.findByPk(createdUser.id, { transaction });
      expect(dbUser).toBeDefined();
      expect(dbUser.name).toBe(userData.name);
    });

    it('should throw error when email already exists', async () => {
      // Given
      const existingUser = await UserFactory.create({
        email: 'existing@example.com'
      });

      const userData = UserFactory.build({
        email: 'existing@example.com'
      });

      // When & Then
      await expect(
        userService.createUser(userData, { transaction })
      ).rejects.toThrow('Email already exists');
    });
  });

  describe('getUserById', () => {
    it('should return user when user exists', async () => {
      // Given
      const user = await UserFactory.create({
        name: 'Jane Doe',
        email: 'jane@example.com'
      });

      // When
      const foundUser = await userService.getUserById(user.id, { transaction });

      // Then
      expect(foundUser).toBeDefined();
      expect(foundUser.id).toBe(user.id);
      expect(foundUser.name).toBe(user.name);
      expect(foundUser.email).toBe(user.email);
    });

    it('should return null when user does not exist', async () => {
      // Given
      const nonExistentId = 99999;

      // When
      const foundUser = await userService.getUserById(nonExistentId, { transaction });

      // Then
      expect(foundUser).toBeNull();
    });
  });

  describe('updateUser', () => {
    it('should update user successfully', async () => {
      // Given
      const user = await UserFactory.create({
        name: 'Original Name',
        email: 'original@example.com'
      });

      const updateData = {
        name: 'Updated Name',
        email: 'updated@example.com'
      };

      // When
      const updatedUser = await userService.updateUser(user.id, updateData, { transaction });

      // Then
      expect(updatedUser).toBeDefined();
      expect(updatedUser.name).toBe(updateData.name);
      expect(updatedUser.email).toBe(updateData.email);

      // 데이터베이스에서 실제로 업데이트되었는지 확인
      const dbUser = await User.findByPk(user.id, { transaction });
      expect(dbUser.name).toBe(updateData.name);
      expect(dbUser.email).toBe(updateData.email);
    });
  });

  describe('deleteUser', () => {
    it('should delete user successfully', async () => {
      // Given
      const user = await UserFactory.create();

      // When
      await userService.deleteUser(user.id, { transaction });

      // Then
      const deletedUser = await User.findByPk(user.id, { transaction });
      expect(deletedUser).toBeNull();
    });
  });
});
```

#### 게시물 서비스 통합 테스트
```javascript
// tests/integration/PostService.test.js
const { PostService } = require('../../src/services/PostService');
const { Post, User, Comment } = require('../../src/models');
const UserFactory = require('../factories/UserFactory');
const TestDataSeeder = require('../seeders/TestDataSeeder');

describe('PostService Integration Tests', () => {
  let postService;
  let transaction;
  let testData;

  beforeEach(async () => {
    postService = new PostService();
    transaction = global.getTransaction();
    testData = await TestDataSeeder.seedAll();
  });

  describe('getPostsWithComments', () => {
    it('should return posts with comments', async () => {
      // When
      const postsWithComments = await postService.getPostsWithComments({ transaction });

      // Then
      expect(postsWithComments).toBeDefined();
      expect(Array.isArray(postsWithComments)).toBe(true);
      expect(postsWithComments.length).toBeGreaterThan(0);

      // 각 게시물에 댓글이 포함되어 있는지 확인
      postsWithComments.forEach(post => {
        expect(post.Comments).toBeDefined();
        expect(Array.isArray(post.Comments)).toBe(true);
      });
    });

    it('should return posts with pagination', async () => {
      // Given
      const page = 1;
      const limit = 5;

      // When
      const result = await postService.getPostsWithComments({
        page,
        limit,
        transaction
      });

      // Then
      expect(result.posts).toBeDefined();
      expect(result.total).toBeDefined();
      expect(result.page).toBe(page);
      expect(result.limit).toBe(limit);
      expect(result.posts.length).toBeLessThanOrEqual(limit);
    });
  });

  describe('createPost', () => {
    it('should create post with author relationship', async () => {
      // Given
      const author = testData.users[0];
      const postData = {
        title: 'Test Post',
        content: 'This is test content',
        authorId: author.id
      };

      // When
      const createdPost = await postService.createPost(postData, { transaction });

      // Then
      expect(createdPost).toBeDefined();
      expect(createdPost.title).toBe(postData.title);
      expect(createdPost.content).toBe(postData.content);
      expect(createdPost.authorId).toBe(author.id);

      // 작성자 정보가 포함되어 있는지 확인
      expect(createdPost.Author).toBeDefined();
      expect(createdPost.Author.id).toBe(author.id);
      expect(createdPost.Author.name).toBe(author.name);
    });
  });
});
```

### 2. 고급 패턴

#### 데이터베이스 마이그레이션 테스트
```javascript
// tests/integration/Migration.test.js
const { Sequelize } = require('sequelize');
const config = require('../../config/database');

describe('Database Migration Tests', () => {
  let sequelize;

  beforeAll(async () => {
    sequelize = new Sequelize(config.test);
    await sequelize.authenticate();
  });

  afterAll(async () => {
    await sequelize.close();
  });

  it('should have correct table structure', async () => {
    // Given
    const expectedTables = ['Users', 'Posts', 'Comments', 'Categories'];

    // When
    const tables = await sequelize.getQueryInterface().showAllTables();

    // Then
    expectedTables.forEach(tableName => {
      expect(tables).toContain(tableName);
    });
  });

  it('should have correct column types', async () => {
    // Given
    const tableName = 'Users';
    const expectedColumns = {
      id: 'INTEGER',
      name: 'VARCHAR(255)',
      email: 'VARCHAR(255)',
      password: 'VARCHAR(255)',
      createdAt: 'DATETIME',
      updatedAt: 'DATETIME'
    };

    // When
    const columns = await sequelize.getQueryInterface().describeTable(tableName);

    // Then
    Object.entries(expectedColumns).forEach(([columnName, expectedType]) => {
      expect(columns[columnName]).toBeDefined();
      expect(columns[columnName].type).toContain(expectedType);
    });
  });
});
```

#### 성능 테스트
```javascript
// tests/integration/Performance.test.js
const { UserService } = require('../../src/services/UserService');
const UserFactory = require('../factories/UserFactory');

describe('Performance Tests', () => {
  let userService;
  let transaction;

  beforeEach(async () => {
    userService = new UserService();
    transaction = global.getTransaction();
  });

  it('should handle bulk user creation efficiently', async () => {
    // Given
    const userCount = 100;
    const users = UserFactory.buildMany(userCount);

    // When
    const startTime = Date.now();
    const createdUsers = await userService.createBulkUsers(users, { transaction });
    const endTime = Date.now();

    // Then
    expect(createdUsers).toHaveLength(userCount);
    expect(endTime - startTime).toBeLessThan(5000); // 5초 이내 완료
  });

  it('should handle complex query efficiently', async () => {
    // Given
    await UserFactory.createMany(50);
    const searchTerm = 'test';

    // When
    const startTime = Date.now();
    const results = await userService.searchUsers(searchTerm, { transaction });
    const endTime = Date.now();

    // Then
    expect(results).toBeDefined();
    expect(endTime - startTime).toBeLessThan(1000); // 1초 이내 완료
  });
});
```

## 운영 팁

### 1. 테스트 데이터베이스 관리

#### 자동화된 테스트 환경 설정
```javascript
// tests/globalSetup.js
const { Sequelize } = require('sequelize');
const config = require('../config/database');

module.exports = async () => {
  // 테스트 데이터베이스 생성
  const adminSequelize = new Sequelize({
    host: config.test.host,
    port: config.test.port,
    username: config.test.username,
    password: config.test.password,
    dialect: config.test.dialect,
    logging: false
  });

  try {
    await adminSequelize.query(`CREATE DATABASE IF NOT EXISTS ${config.test.database}`);
    console.log('Test database created successfully');
  } catch (error) {
    console.error('Failed to create test database:', error);
  } finally {
    await adminSequelize.close();
  }
};
```

#### 테스트 후 정리
```javascript
// tests/globalTeardown.js
const { Sequelize } = require('sequelize');
const config = require('../config/database');

module.exports = async () => {
  // 테스트 데이터베이스 삭제
  const adminSequelize = new Sequelize({
    host: config.test.host,
    port: config.test.port,
    username: config.test.username,
    password: config.test.password,
    dialect: config.test.dialect,
    logging: false
  });

  try {
    await adminSequelize.query(`DROP DATABASE IF EXISTS ${config.test.database}`);
    console.log('Test database cleaned up successfully');
  } catch (error) {
    console.error('Failed to clean up test database:', error);
  } finally {
    await adminSequelize.close();
  }
};
```

### 2. 에러 처리 및 디버깅

#### 데이터베이스 에러 테스트
```javascript
// tests/integration/ErrorHandling.test.js
const { UserService } = require('../../src/services/UserService');
const { User } = require('../../src/models');

describe('Database Error Handling', () => {
  let userService;
  let transaction;

  beforeEach(async () => {
    userService = new UserService();
    transaction = global.getTransaction();
  });

  it('should handle database connection errors', async () => {
    // Given
    const invalidUserData = {
      name: null, // NOT NULL 제약 조건 위반
      email: 'test@example.com'
    };

    // When & Then
    await expect(
      userService.createUser(invalidUserData, { transaction })
    ).rejects.toThrow();
  });

  it('should handle foreign key constraint errors', async () => {
    // Given
    const postData = {
      title: 'Test Post',
      content: 'Test content',
      authorId: 99999 // 존재하지 않는 사용자 ID
    };

    // When & Then
    await expect(
      userService.createPost(postData, { transaction })
    ).rejects.toThrow();
  });
});
```

### 3. 테스트 최적화

#### 병렬 테스트 실행
```javascript
// jest.config.js
module.exports = {
  testEnvironment: 'node',
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  testMatch: ['**/__tests__/**/*.test.js', '**/?(*.)+(spec|test).js'],
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/**/*.test.js',
    '!src/**/*.spec.js'
  ],
  testTimeout: 30000,
  maxWorkers: 4, // 병렬 테스트 실행
  globalSetup: '<rootDir>/tests/globalSetup.js',
  globalTeardown: '<rootDir>/tests/globalTeardown.js'
};
```

#### 테스트 데이터 캐싱
```javascript
// tests/helpers/TestDataCache.js
class TestDataCache {
  constructor() {
    this.cache = new Map();
  }

  async get(key, factory) {
    if (!this.cache.has(key)) {
      const data = await factory();
      this.cache.set(key, data);
    }
    return this.cache.get(key);
  }

  clear() {
    this.cache.clear();
  }
}

module.exports = new TestDataCache();
```

## 참고

### 데이터베이스별 특성

#### MySQL vs PostgreSQL
| 특성 | MySQL | PostgreSQL |
|------|-------|------------|
| **트랜잭션 격리** | 기본 지원 | 고급 격리 수준 |
| **JSON 지원** | 5.7+ | 네이티브 지원 |
| **성능** | 읽기 최적화 | 복잡한 쿼리 최적화 |
| **확장성** | 수평 확장 | 수직 확장 |

### 주의사항

#### 테스트 격리 원칙
1. **각 테스트는 독립적**이어야 함
2. **테스트 순서에 의존하지 않음**
3. **테스트 후 상태 초기화**
4. **실제 데이터베이스 사용**

#### 성능 고려사항
1. **테스트 데이터베이스 최적화**
2. **인덱스 설정 확인**
3. **쿼리 성능 모니터링**
4. **병렬 테스트 실행**

### 결론
데이터베이스 통합 테스트는 실제 데이터베이스와 연동하여 데이터 관련 로직을 검증하는 중요한 테스트입니다.
트랜잭션 롤백을 통한 테스트 격리와 체계적인 테스트 데이터 관리를 통해 안정적이고 신뢰할 수 있는 테스트를 구축할 수 있습니다.
실제 프로덕션 환경과 유사한 조건에서 테스트를 수행하여 더욱 정확한 검증이 가능합니다.
