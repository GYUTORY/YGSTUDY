---
title: Node.js TDD (Test-Driven Development)
tags: [framework, node, tdd, test-driven-development, nodejs]
updated: 2024-12-19
---

# Node.js TDD (Test-Driven Development)

## 배경

### TDD란?
TDD(Test-Driven Development, 테스트 주도 개발)는 테스트를 먼저 작성하고, 이후에 실제 코드를 구현하는 방식입니다. 즉, 기능을 개발하기 전에 먼저 테스트를 작성한 후, 테스트를 통과할 수 있도록 코드를 작성하는 개발 방법론입니다.

### TDD의 핵심 원칙
- **테스트 우선**: 기능 구현 전에 테스트를 먼저 작성
- **작은 단위**: 작은 기능 단위로 테스트와 구현을 반복
- **지속적 리팩토링**: 코드 개선을 통한 품질 향상

### TDD의 장점
- 코드의 품질과 신뢰성 향상
- 설계 개선 및 리팩토링 용이
- 문서화 효과
- 버그 조기 발견

## 핵심

### TDD 개발 프로세스
TDD는 **Red → Green → Refactor** 3단계를 반복합니다.

1. **Red(실패)**: 먼저 테스트를 작성하고 실행 → 당연히 처음에는 실패
2. **Green(성공)**: 테스트를 통과할 수 있도록 최소한의 코드를 작성
3. **Refactor(리팩토링)**: 중복 제거 및 코드 개선 (테스트는 계속 통과해야 함)

```plaintext
1. 테스트 코드 작성 (실패)  🔴 Red
2. 기능 코드 작성 (성공)  🟢 Green
3. 리팩토링 (성능 개선)  ♻️ Refactor
4. 반복...
```

### Node.js에서 TDD를 위한 필수 패키지
TDD를 수행하려면 테스트 프레임워크가 필요합니다. Node.js 환경에서는 아래 패키지들이 많이 사용됩니다.

| 패키지 | 설명 |
|--------|----------------------|
| `Jest` | 가장 인기 있는 JavaScript 테스트 프레임워크 |
| `Mocha` | 유연한 테스트 러너 |
| `Chai` | 가독성이 좋은 assertion 라이브러리 |
| `Supertest` | HTTP 요청 테스트를 위한 라이브러리 (Express API 테스트에 유용) |

## 예시

### TDD 예제: 간단한 API 테스트 및 개발

#### 프로젝트 설정
```bash
mkdir node-tdd-example  # 프로젝트 폴더 생성
cd node-tdd-example

npm init -y             # package.json 생성

npm install express     # Express 설치
npm install jest supertest --save-dev  # Jest, Supertest 설치
```

#### Jest 설정 (package.json 수정)
`package.json` 파일에서 `"scripts"` 부분을 아래처럼 수정합니다.

```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch"
  }
}
```

#### 1단계: Red - 테스트 작성 (실패)
새로운 API 엔드포인트를 위한 테스트를 먼저 작성합니다.

```javascript
// tests/app.test.js
const request = require('supertest');
const app = require('../app');

describe("GET /api/greet", () => {
    it("200 상태코드와 함께 'Welcome to TDD!' 메시지를 반환해야 한다", async () => {
        const response = await request(app).get("/api/greet");
        expect(response.status).toBe(200);
        expect(response.body.message).toBe("Welcome to TDD!");
    });
});
```

이 테스트는 당연히 실패합니다. 아직 해당 엔드포인트가 구현되지 않았기 때문입니다.

#### 2단계: Green - 최소한의 코드 작성 (성공)
테스트를 통과할 수 있도록 최소한의 코드를 작성합니다.

```javascript
// app.js
const express = require('express');
const app = express();

app.use(express.json());

app.get('/api/greet', (req, res) => {
    res.status(200).json({ message: "Welcome to TDD!" });
});

module.exports = app;
```

이제 테스트를 실행하면 통과합니다.

#### 3단계: Refactor - 코드 개선
코드를 개선하고 중복을 제거합니다.

```javascript
// routes/api.js
const express = require('express');
const router = express.Router();

router.get("/greet", (req, res) => {
    res.status(200).json({ message: "Welcome to TDD!" });
});

module.exports = router;

// app.js
const express = require('express');
const apiRoutes = require('./routes/api');

const app = express();
app.use(express.json());
app.use('/api', apiRoutes);

module.exports = app;
```

### TDD를 활용한 사용자 관리 API 개발

#### 1단계: 사용자 생성 API 테스트
```javascript
// tests/user.test.js
const request = require('supertest');
const app = require('../app');

describe("POST /api/users", () => {
    it("새로운 사용자를 생성하고 201 상태코드를 반환해야 한다", async () => {
        const userData = {
            name: "김철수",
            email: "kim@example.com"
        };

        const response = await request(app)
            .post("/api/users")
            .send(userData);

        expect(response.status).toBe(201);
        expect(response.body).toHaveProperty('id');
        expect(response.body.name).toBe(userData.name);
        expect(response.body.email).toBe(userData.email);
    });

    it("이메일이 중복되면 400 상태코드를 반환해야 한다", async () => {
        const userData = {
            name: "김철수",
            email: "kim@example.com"
        };

        // 첫 번째 사용자 생성
        await request(app).post("/api/users").send(userData);

        // 중복 이메일로 두 번째 사용자 생성 시도
        const response = await request(app)
            .post("/api/users")
            .send(userData);

        expect(response.status).toBe(400);
        expect(response.body.error).toBe("이메일이 이미 존재합니다");
    });
});
```

#### 2단계: 사용자 생성 API 구현
```javascript
// models/user.js
class User {
    constructor(name, email) {
        this.id = Date.now().toString();
        this.name = name;
        this.email = email;
    }
}

// services/userService.js
class UserService {
    constructor() {
        this.users = [];
    }

    createUser(name, email) {
        // 이메일 중복 확인
        const existingUser = this.users.find(user => user.email === email);
        if (existingUser) {
            throw new Error("이메일이 이미 존재합니다");
        }

        const user = new User(name, email);
        this.users.push(user);
        return user;
    }

    getAllUsers() {
        return this.users;
    }

    getUserById(id) {
        return this.users.find(user => user.id === id);
    }
}

module.exports = UserService;

// routes/users.js
const express = require('express');
const UserService = require('../services/userService');

const router = express.Router();
const userService = new UserService();

router.post('/', (req, res) => {
    try {
        const { name, email } = req.body;
        const user = userService.createUser(name, email);
        res.status(201).json(user);
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});

router.get('/', (req, res) => {
    const users = userService.getAllUsers();
    res.status(200).json(users);
});

router.get('/:id', (req, res) => {
    const user = userService.getUserById(req.params.id);
    if (!user) {
        return res.status(404).json({ error: "사용자를 찾을 수 없습니다" });
    }
    res.status(200).json(user);
});

module.exports = router;
```

#### 3단계: 통합 테스트
```javascript
// tests/integration.test.js
const request = require('supertest');
const app = require('../app');

describe("사용자 관리 API 통합 테스트", () => {
    beforeEach(() => {
        // 각 테스트 전에 데이터 초기화
        // 실제로는 데이터베이스를 초기화하거나 모킹을 사용
    });

    it("사용자 생성 후 조회가 가능해야 한다", async () => {
        // 1. 사용자 생성
        const userData = {
            name: "이영희",
            email: "lee@example.com"
        };

        const createResponse = await request(app)
            .post("/api/users")
            .send(userData);

        expect(createResponse.status).toBe(201);
        const createdUser = createResponse.body;

        // 2. 생성된 사용자 조회
        const getResponse = await request(app)
            .get(`/api/users/${createdUser.id}`);

        expect(getResponse.status).toBe(200);
        expect(getResponse.body.name).toBe(userData.name);
        expect(getResponse.body.email).toBe(userData.email);
    });
});
```

### 비동기 함수 TDD 예제

#### 1단계: 비동기 함수 테스트
```javascript
// tests/async.test.js
const { fetchUserData, processUserData } = require('../services/asyncService');

describe("비동기 함수 테스트", () => {
    it("사용자 데이터를 성공적으로 가져와야 한다", async () => {
        const userId = "123";
        const userData = await fetchUserData(userId);
        
        expect(userData).toHaveProperty('id');
        expect(userData).toHaveProperty('name');
        expect(userData).toHaveProperty('email');
    });

    it("사용자 데이터 처리가 성공적으로 완료되어야 한다", async () => {
        const rawData = { id: "123", name: "김철수", email: "kim@example.com" };
        const processedData = await processUserData(rawData);
        
        expect(processedData).toHaveProperty('formattedName');
        expect(processedData.formattedName).toBe("김철수 (ID: 123)");
    });
});
```

#### 2단계: 비동기 함수 구현
```javascript
// services/asyncService.js
const axios = require('axios');

async function fetchUserData(userId) {
    try {
        const response = await axios.get(`https://api.example.com/users/${userId}`);
        return response.data;
    } catch (error) {
        throw new Error(`사용자 데이터 조회 실패: ${error.message}`);
    }
}

async function processUserData(userData) {
    return new Promise((resolve) => {
        setTimeout(() => {
            const processed = {
                ...userData,
                formattedName: `${userData.name} (ID: ${userData.id})`,
                processedAt: new Date().toISOString()
            };
            resolve(processed);
        }, 100);
    });
}

module.exports = {
    fetchUserData,
    processUserData
};
```

## 운영 팁

### TDD 모범 사례

#### 1. 테스트 작성 원칙
- **명확한 테스트 이름**: 테스트가 무엇을 검증하는지 명확히 표현
- **하나의 개념만 테스트**: 각 테스트는 하나의 개념만 검증
- **독립적인 테스트**: 테스트 간 의존성 없이 독립적으로 실행 가능

```javascript
// 좋은 예시
it("이메일이 유효한 형식이면 사용자를 생성해야 한다", async () => {
    // 테스트 구현
});

// 나쁜 예시
it("사용자 생성 테스트", async () => {
    // 여러 개념을 한 번에 테스트
});
```

#### 2. 테스트 구조화
```javascript
describe("사용자 관리", () => {
    describe("사용자 생성", () => {
        it("유효한 데이터로 사용자를 생성할 수 있어야 한다", () => {
            // 테스트 구현
        });

        it("중복 이메일로는 사용자를 생성할 수 없어야 한다", () => {
            // 테스트 구현
        });
    });

    describe("사용자 조회", () => {
        it("존재하는 사용자 ID로 조회할 수 있어야 한다", () => {
            // 테스트 구현
        });

        it("존재하지 않는 사용자 ID로 조회하면 404를 반환해야 한다", () => {
            // 테스트 구현
        });
    });
});
```

#### 3. 테스트 데이터 관리
```javascript
// test/fixtures/users.js
const testUsers = [
    {
        id: "1",
        name: "김철수",
        email: "kim@example.com"
    },
    {
        id: "2",
        name: "이영희",
        email: "lee@example.com"
    }
];

module.exports = testUsers;

// 테스트에서 사용
const testUsers = require('../fixtures/users');

describe("사용자 API", () => {
    beforeEach(() => {
        // 테스트 데이터 설정
        userService.users = [...testUsers];
    });

    afterEach(() => {
        // 테스트 데이터 정리
        userService.users = [];
    });
});
```

### 성능 최적화
```javascript
// 테스트 실행 최적화
const { performance } = require('perf_hooks');

describe("성능 테스트", () => {
    it("대량의 사용자 데이터를 처리할 수 있어야 한다", async () => {
        const startTime = performance.now();
        
        // 대량 데이터 처리 로직
        const users = Array.from({ length: 1000 }, (_, i) => ({
            name: `User${i}`,
            email: `user${i}@example.com`
        }));

        for (const user of users) {
            await userService.createUser(user.name, user.email);
        }

        const endTime = performance.now();
        const duration = endTime - startTime;

        expect(duration).toBeLessThan(5000); // 5초 이내 완료
        expect(userService.getAllUsers()).toHaveLength(1000);
    });
});
```

## 참고

### TDD vs BDD (Behavior-Driven Development)

| 특징 | TDD | BDD |
|------|-----|-----|
| **초점** | 테스트 우선 개발 | 행동 중심 개발 |
| **언어** | 기술적 용어 | 비즈니스 용어 |
| **대상** | 개발자 | 개발자 + 비즈니스 관계자 |
| **도구** | Jest, Mocha | Cucumber, Jasmine |

### TDD 도구 및 라이브러리
- **Jest**: Facebook에서 개발한 테스트 프레임워크
- **Mocha**: 유연한 테스트 러너
- **Chai**: Assertion 라이브러리
- **Supertest**: HTTP API 테스트
- **Sinon**: 스파이, 스텁, 모킹 라이브러리

### 결론
TDD는 코드의 품질과 신뢰성을 크게 향상시키는 개발 방법론입니다.
테스트를 먼저 작성함으로써 명확한 요구사항을 정의하고,
지속적인 리팩토링을 통해 깔끔하고 유지보수하기 쉬운 코드를 작성할 수 있습니다.
특히 Node.js 환경에서는 Jest와 Supertest 같은 강력한 도구들을 활용하여
효과적인 TDD를 실천할 수 있습니다.

