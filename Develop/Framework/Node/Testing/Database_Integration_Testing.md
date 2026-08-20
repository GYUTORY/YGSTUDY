---
title: 데이터베이스 통합 테스트
tags: [nodejs, testing, database, mysql]
updated: 2025-12-13
---

# 데이터베이스 통합 테스트

## 배경

### 데이터베이스 통합 테스트란?
데이터베이스 통합 테스트는 실제 데이터베이스와 연동해 데이터베이스 관련 로직을 검증하는 테스트다. 단위 테스트와 달리 실제 데이터베이스 연결과 트랜잭션, 쿼리 실행까지 포함해 데이터 흐름 전체를 확인한다.

### 통합 테스트의 필요성
- **실제 환경 검증**: 실제 데이터베이스와 동일한 환경에서 테스트
- **데이터 일관성 보장**: 트랜잭션 처리와 데이터 무결성 검증
- **성능 검증**: 실제 쿼리 성능과 최적화 확인
- **에러 처리 검증**: 데이터베이스 에러 상황 대응 테스트

### 기본 개념
- **테스트 격리**: 각 테스트가 독립적으로 실행되도록 보장
- **데이터 정리**: 테스트 후 데이터베이스 상태 초기화
- **트랜잭션 관리**: 롤백으로 테스트 격리
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

#### `global.sequelize` 는 영원히 `undefined` 다

마지막 두 줄은 겉보기에 같은 일을 하는 것 같지만 결과가 정반대다. **`global.sequelize = sequelize` 는 파일이 로드되는 순간 실행된다.** 그때 `sequelize` 는 아직 `beforeAll` 이 돌기 전이라 `undefined` 이고, 그 `undefined` 가 값으로 복사된다. 나중에 `beforeAll` 이 지역 변수를 채워도 이미 복사된 전역은 안 바뀐다.

```
global.sequelize   = undefined
지역 변수 sequelize = { name: '진짜 커넥션' }
global.getTransaction() = { id: 't1' }
```

바로 아래 `getTransaction` 이 멀쩡한 이유는 **함수라서 호출 시점에 변수를 읽기** 때문이다. 이 차이가 이 파일의 유일한 방어선이다.

그래서 테스트에서 `global.sequelize.query(...)` 를 부르면 `Cannot read properties of undefined` 가 난다. 값을 전역으로 넘길 거면 게터로 넘긴다.

```javascript
global.getSequelize = () => sequelize;   // ✓ 호출 시점에 읽는다
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

#### 팩토리가 트랜잭션을 안 받으면 롤백 격리가 통째로 무너진다

앞 절의 격리 전략은 "모든 쿼리가 같은 트랜잭션 위에서 돈다"를 전제로 한다. 그런데 이 팩토리의 `User.create(userData)` 에는 **`{ transaction }` 이 없다.** 트랜잭션 밖에서 커밋되므로 `afterEach` 의 롤백이 이 데이터를 못 지운다.

증상은 이렇게 나타난다. 아래 테스트를 두 번 돌리면 두 번째부터 다르게 동작한다.

```javascript
const existingUser = await UserFactory.create({ email: 'existing@example.com' });  // ← 트랜잭션 밖
```

첫 실행에서 이 행이 DB 에 영구히 남고, 두 번째 실행에서는 **`UserFactory.create` 자체가 유니크 제약으로 죽는다.** "왜 어제는 통과했는데 오늘은 실패하지" 의 전형이다. 게다가 이건 테스트 순서·개수에 따라 다르게 터져서 재현이 어렵다.

팩토리는 트랜잭션을 받아 넘겨야 한다.

```javascript
static async create(overrides = {}, options = {}) {
  return await User.create({ ...defaultData, ...overrides }, options);
}
// 호출부: await UserFactory.create({ email }, { transaction })
```

트랜잭션을 일일이 넘기기가 번거로우면 Sequelize 의 CLS(`Sequelize.useCLS`)로 자동 전파시키는 방법도 있다. 어느 쪽이든 **"롤백했으니 깨끗하다"는 가정이 실제로 성립하는지**는 한 번 확인해야 한다. 테스트를 연속 두 번 돌려 같은 결과가 나오는지 보는 게 가장 싼 검증이다.

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

이 성능 테스트는 두 가지 이유로 그대로 돌릴 수 없다.

**첫째, `UserFactory.buildMany` 라는 메서드가 없다.** 앞의 팩토리에 정의된 건 `create` / `createMany` / `build` 셋뿐이다.

```
buildMany 타입: undefined
호출 결과: TypeError: UserFactory.buildMany is not a function
```

성능을 재기도 전에 첫 줄에서 죽는다. `build` 를 100번 부르거나 `buildMany` 를 팩토리에 추가해야 한다.

**둘째, 벽시계 시간에 절대 임계값을 거는 단언은 CI 에서 흔들린다.** `toBeLessThan(5000)` 은 개발 머신에서는 늘 통과하다가, 공용 러너가 붐비는 날 갑자기 실패한다. 그러면 사람들은 원인을 찾는 대신 숫자를 10000 으로 올린다. 몇 번 반복되면 이 테스트는 아무것도 검증하지 않으면서 CI 시간만 먹는다.

성능을 테스트로 지키려면 시간이 아니라 **변하지 않는 것**을 건다.

- 쿼리 실행 횟수 — N+1 이 생기면 100번 나가던 게 101번이 된다. 이건 머신 속도와 무관하다.
- 실행 계획 — 인덱스를 타는지 `EXPLAIN` 으로 확인한다.
- 반환 행 수 상한 — 페이지네이션이 빠졌는지 잡힌다.

절대 시간은 테스트가 아니라 부하 테스트 도구와 모니터링의 몫이다.

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

`maxWorkers: 4` 를 켜기 전에 **앞에서 본 트랜잭션 누수부터 잡아야 한다.** 워커 넷이 같은 테스트 DB 하나를 쓰는데 그중 일부 쓰기가 트랜잭션 밖에서 커밋되면, A 워커가 만든 행을 B 워커가 보고 단언이 틀어진다. 순차 실행에서는 안 나던 실패가 병렬에서만, 그것도 매번 다른 테스트에서 나온다.

`globalTeardown` 의 `DROP DATABASE` 도 이때 위험해진다. 로컬에서 개발 DB 이름을 잘못 넣어두면 그대로 날아간다. 이 스크립트에는 **삭제 대상 이름이 테스트용이 맞는지 확인하는 가드**를 넣는 편이 낫다.

```javascript
if (!/_test$/.test(config.test.database)) {
  throw new Error(`테스트 DB 이름이 아님: ${config.test.database}`);
}
```

병렬을 제대로 하려면 워커마다 DB 를 나눠 갖는 쪽이 확실하다. Jest 는 워커 번호를 `process.env.JEST_WORKER_ID` 로 준다.

```javascript
database: `myapp_test_${process.env.JEST_WORKER_ID || 1}`
```

#### 그런데 `maxWorkers: 4` 라고 프로세스가 4개인 건 아니다

Jest 는 조건이 맞으면 **워커를 안 띄우고 전부 한 프로세스(in-band)에서 돌린다.** 테스트 파일 4개에 `--maxWorkers=4` 를 주고 워커 ID 와 PID 를 찍어보면:

```
# 1회차
WORKER_ID=1 pid=29130
WORKER_ID=1 pid=29130
WORKER_ID=1 pid=29130
WORKER_ID=1 pid=29130

# 2회차 (같은 명령, 같은 파일)
WORKER_ID=1 pid=31454
WORKER_ID=2 pid=31455
WORKER_ID=3 pid=31456
WORKER_ID=4 pid=31457
```

같은 명령인데 결과가 다르다. 판단 근거는 `@jest/core` 안에 그대로 있다.

```javascript
const SLOW_TEST_TIME = 1000;
const areFastTests = timings.every(timing => timing < SLOW_TEST_TIME);
return workerIdleMemoryLimit === undefined &&
  (oneWorkerOrLess || oneTestOrLess ||
   tests.length <= 20 && timings.length > 0 && areFastTests);
```

(Jest 30.4.1 — `node_modules/@jest/core/build/index.js` 의 `shouldRunInBand`)

**직전 실행의 소요 시간을 캐시해 두고, 파일이 20개 이하이면서 전부 1초 미만이면 워커를 안 띄운다.** 위 1회차가 in-band 였던 건 그 전에 돌린 빠른 버전의 타이밍이 캐시에 남아 있었기 때문이고, 2회차는 느려진 타이밍이 반영돼 워커로 갈렸다.

DB 통합 테스트에서 이게 왜 중요하냐면, **격리 방식이 프로세스 수에 따라 달라지기 때문**이다.

- in-band 면 모든 스위트가 커넥션 풀 하나와 전역 하나를 공유한다. 위의 `myapp_test_${JEST_WORKER_ID}` 도 전부 `..._1` 로 같은 DB 를 가리킨다.
- 워커로 갈리면 프로세스마다 풀이 따로 뜨고, DB 도 갈린다.

그래서 "로컬에서는 되는데 CI 에서만 깨진다"가 나온다. CI 는 캐시가 비어 있는 상태로 시작하니 첫 실행의 경로가 로컬과 다르다. **캐시 상태에 따라 실행 방식이 바뀌는 걸 피하려면 `--runInBand` 나 `--maxWorkers=1` 로 못 박는다.** 느려지는 대신 재현이 된다.

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
1. 각 테스트는 독립적이어야 한다
2. 테스트 순서에 의존하지 않는다
3. 테스트가 끝나면 상태를 초기화한다
4. 실제 데이터베이스를 쓴다

#### 성능 고려사항
1. 테스트 데이터베이스 최적화
2. 인덱스 설정 확인
3. 쿼리 성능 모니터링
4. 병렬 테스트 실행

### 결론
데이터베이스 통합 테스트는 실제 데이터베이스와 연동해 데이터 관련 로직을 검증하는 중요한 테스트다.
트랜잭션 롤백으로 테스트를 격리하고 테스트 데이터를 체계적으로 관리하면 안정적이고 믿을 만한 테스트를 만들 수 있다.
실제 프로덕션 환경과 비슷한 조건에서 테스트를 돌리면 검증이 그만큼 정확해진다.
