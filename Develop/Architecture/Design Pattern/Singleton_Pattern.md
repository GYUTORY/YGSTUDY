---
title: Singleton Pattern (싱글톤 패턴)
tags: [design-patterns, javascript, typescript, java, spring, architecture]
updated: 2026-08-27
---

# Singleton Pattern (싱글톤 패턴)

클래스의 인스턴스를 프로세스 전체에서 하나만 만들도록 강제하는 패턴이다. 전역 변수와 다를 게 없지만, 생성 시점을 제어하고 초기화 로직을 캡슐화할 수 있다.

## Eager vs Lazy: 언제 인스턴스를 만드는가

언어마다 구현 방식은 달라도 두 가지 선택지로 귀결된다.

**Eager initialization**은 클래스가 로드될 때 바로 인스턴스를 만든다. 스레드 안전성 문제가 없다. 클래스 로더가 한 번만 초기화를 보장하기 때문이다. 초기화 로직이 단순하고 인스턴스가 항상 쓰인다면 이게 낫다.

```java
// Java — eager initialization
public class Config {
    private static final Config INSTANCE = new Config();

    private Config() {}

    public static Config getInstance() {
        return INSTANCE;
    }
}
```

**Lazy initialization**은 처음 `getInstance()`를 호출할 때 만든다. 초기화 비용이 크거나 쓰이지 않을 수도 있는 경우에 쓴다. 문제는 멀티스레드 환경이다. 두 스레드가 동시에 `null` 체크를 통과하면 인스턴스가 두 개 만들어진다.

```java
// 스레드 안전하지 않은 lazy initialization
public class Config {
    private static Config instance;

    private Config() {}

    public static Config getInstance() {
        if (instance == null) {         // 두 스레드가 동시에 여기 진입 가능
            instance = new Config();    // 인스턴스가 두 개 생길 수 있다
        }
        return instance;
    }
}
```

Java에서 멀티스레드 안전한 lazy initialization은 static inner class로 해결한다. `Holder` 클래스는 `getInstance()`를 처음 호출할 때 로드된다. 클래스 로더가 초기화를 직렬화하므로 `synchronized` 없이도 스레드 안전하다.

```java
// static inner class — lazy, thread-safe, 간결
public class Config {
    private Config() {}

    private static class Holder {
        private static final Config INSTANCE = new Config();
    }

    public static Config getInstance() {
        return Holder.INSTANCE;
    }
}
```

JavaScript(Node.js)는 싱글 스레드라 이 문제가 없다. 비동기 코드에서도 이벤트 루프가 한 번에 하나씩 실행하기 때문에 lazy initialization을 그냥 써도 된다.

## TypeScript 타입 안전한 구현

JavaScript 구현에서 TypeScript로 옮길 때 `private constructor()`가 핵심이다. JavaScript에서는 `new` 직접 호출을 런타임에만 잡지만, TypeScript 컴파일러는 빌드 시점에 막아준다.

```typescript
class Config {
    private static instance: Config;
    private settings: Record<string, unknown>;

    private constructor() {
        this.settings = {
            apiUrl: process.env.API_URL ?? 'http://localhost:3000',
            timeout: 5000,
        };
    }

    static getInstance(): Config {
        if (!Config.instance) {
            Config.instance = new Config();
        }
        return Config.instance;
    }

    get<T>(key: string): T {
        return this.settings[key] as T;
    }

    set<T>(key: string, value: T): void {
        this.settings[key] = value;
    }
}

// new Config() — 컴파일 에러: Constructor of class 'Config' is private
const url = Config.getInstance().get<string>('apiUrl');
const timeout = Config.getInstance().get<number>('timeout');
```

제네릭 싱글톤 베이스 클래스를 만들려는 시도가 있는데, `this: new () => T` 시그니처가 `private constructor`와 충돌해서 실제 사용이 까다롭다. 각 클래스에서 직접 구현하는 편이 낫다.

## 직렬화와 리플렉션이 인스턴스를 깨는 방식

Java에서는 두 가지 경로로 싱글톤이 깨진다.

**직렬화/역직렬화**

`Serializable`을 구현한 싱글톤을 역직렬화하면 새 인스턴스가 만들어진다.

```java
Config c1 = Config.getInstance();

ByteArrayOutputStream baos = new ByteArrayOutputStream();
new ObjectOutputStream(baos).writeObject(c1);

Config c2 = (Config) new ObjectInputStream(
    new ByteArrayInputStream(baos.toByteArray())
).readObject();

System.out.println(c1 == c2); // false — 다른 인스턴스
```

`readResolve()`를 추가하면 막을 수 있다. 역직렬화 시 이 메서드가 호출되어 기존 인스턴스를 반환한다.

```java
public class Config implements Serializable {
    private static final Config INSTANCE = new Config();
    private Config() {}
    public static Config getInstance() { return INSTANCE; }

    protected Object readResolve() {
        return INSTANCE;
    }
}
```

**리플렉션**

`private` constructor도 리플렉션으로 우회할 수 있다.

```java
Config c1 = Config.getInstance();

Constructor<Config> ctor = Config.class.getDeclaredConstructor();
ctor.setAccessible(true);
Config c2 = ctor.newInstance();

System.out.println(c1 == c2); // false
```

생성자 안에서 방어할 수 있다.

```java
private Config() {
    if (INSTANCE != null) {
        throw new IllegalStateException("이미 인스턴스가 존재한다");
    }
}
```

직렬화와 리플렉션 공격 둘 다 막는 가장 간단한 방법은 `enum`이다. Joshua Bloch가 Effective Java에서 제안한 방식이고, JVM이 두 공격 경로를 모두 차단한다.

```java
public enum Config {
    INSTANCE;

    private final String apiUrl =
        System.getenv().getOrDefault("API_URL", "http://localhost:3000");

    public String getApiUrl() { return apiUrl; }
}

Config.INSTANCE.getApiUrl();
```

단점은 lazy initialization이 불가능하다는 점이다. 클래스가 로드될 때 바로 초기화된다.

## DI 프레임워크의 싱글톤과 GoF 싱글톤의 차이

Spring의 `@Component`나 NestJS의 Provider는 기본 스코프가 싱글톤이다. GoF 싱글톤과는 다르다.

GoF 싱글톤은 클래스 자체가 인스턴스 수를 통제한다. 어디서 `getInstance()`를 호출해도 같은 인스턴스가 온다. 전역에서 접근 가능하다.

DI 프레임워크의 싱글톤은 컨테이너가 통제한다. 같은 컨테이너 안에서는 하나지만, 컨테이너가 여러 개면 인스턴스도 여러 개다. 클래스 자체는 인스턴스 수를 전혀 신경 쓰지 않는다.

```java
// Spring — 클래스는 일반 POJO다. new UserService()를 여러 번 호출하면 여러 인스턴스가 생긴다
@Service
public class UserService {
    private final UserRepository repo;

    public UserService(UserRepository repo) {
        this.repo = repo;
    }
}
```

```java
// 테스트에서 컨텍스트를 새로 만들면 UserService 인스턴스도 새로 만들어진다
@SpringBootTest
class UserServiceTest {
    @Autowired
    UserService userService;  // 이 컨텍스트 안에서만 하나
}
```

NestJS도 같은 방식이다.

```typescript
@Injectable()
export class ConfigService {
    private readonly config: Record<string, string> = {
        apiUrl: process.env.API_URL ?? 'http://localhost:3000',
    };

    get(key: string): string {
        return this.config[key];
    }
}

// 요청마다 새 인스턴스가 필요하면 스코프를 바꾼다
@Injectable({ scope: Scope.REQUEST })
export class RequestContext { ... }
```

테스트에서 차이가 드러난다. DI 프레임워크를 쓰면 `getInstance()` 없이도 `new`로 직접 인스턴스를 만들 수 있다. GoF 싱글톤은 그게 안 된다.

```java
// GoF 싱글톤 — 테스트에서 새 인스턴스 만들기가 어렵다
Config config = Config.getInstance();

// DI 방식 — 테스트에서 직접 만들 수 있다
ConfigService configService = new ConfigService(mockEnv);
```

Spring에서 주의할 점이 하나 있다. 싱글톤 빈 안에 `@Scope("prototype")` 빈을 주입하면 주입 시점에 한 번만 생성되어 사실상 싱글톤처럼 동작한다. prototype 빈을 매번 새로 받으려면 `ApplicationContext`에서 직접 가져오거나 `@Lookup`을 써야 한다.

## 전역 상태 안티패턴의 실제 사례

싱글톤이 문제가 되는 대부분은 가변 상태 공유 때문이다.

**요청 간 상태 오염**

```javascript
class AuthContext {
    constructor() {
        if (AuthContext._instance) return AuthContext._instance;
        this.currentUser = null;
        AuthContext._instance = this;
    }

    setUser(user) { this.currentUser = user; }
    getUser() { return this.currentUser; }
}

module.exports = new AuthContext();
```

```javascript
// middleware.js
const auth = require('./auth');

app.use(async (req, res, next) => {
    const user = await getUserFromToken(req.headers.authorization);
    auth.setUser(user);  // 모든 요청이 같은 인스턴스를 공유한다
    next();
});

app.get('/profile', (req, res) => {
    const user = auth.getUser();  // 동시 요청이 오면 다른 사용자 정보가 올 수 있다
    res.json(user);
});
```

Node.js는 싱글 스레드지만 비동기 코드에서 이 패턴은 무너진다. A 요청 처리 중 `await`로 멈춘 사이 B 요청이 `setUser`를 호출하면, A가 다시 실행될 때 `getUser()`는 B의 사용자를 반환한다.

`AsyncLocalStorage`가 정확한 해결책이다.

```javascript
const { AsyncLocalStorage } = require('async_hooks');
const storage = new AsyncLocalStorage();

app.use(async (req, res, next) => {
    const user = await getUserFromToken(req.headers.authorization);
    storage.run({ user }, next);
});

app.get('/profile', (req, res) => {
    const { user } = storage.getStore();
    res.json(user);
});
```

**테스트 간 설정 오염**

```typescript
const config = Config.getInstance();

describe('타임아웃이 긴 경우', () => {
    beforeAll(() => {
        config.set('timeout', 30000);  // 전역 상태 변경
    });

    // 이 다음에 실행되는 테스트들도 timeout: 30000을 본다
});
```

`afterEach`에서 원래 값으로 되돌리는 것으로 임시 해결할 수 있지만, 테스트가 쌓일수록 관리가 어려워진다. 설정 값을 함수 인자로 넘기는 방식이 근본 해결이다.

**캐시 상태 추적 불가**

여러 모듈이 같은 캐시 싱글톤을 공유하면 누가 언제 무효화했는지 추적하기 어려워진다. A 모듈이 `cache.set('user:1', data)`를 하고 B 모듈이 `cache.invalidate('user:1')`를 하면, C 모듈이 캐시를 읽을 때 무효화된 상태인지 알 방법이 없다. 캐시에 싱글톤을 쓴다면 invalidation 이벤트를 pub/sub으로 명시적으로 알리거나, TTL을 강제해서 시간이 지나면 자동으로 갱신되게 해야 한다.

## 기본 구현

```javascript
class Config {
    constructor() {
        if (Config._instance) {
            return Config._instance;
        }
        this.settings = {
            apiUrl: process.env.API_URL || 'http://localhost:3000',
            timeout: 5000,
        };
        Config._instance = this;
    }

    static getInstance() {
        if (!Config._instance) {
            new Config();
        }
        return Config._instance;
    }

    get(key) { return this.settings[key]; }
    set(key, value) { this.settings[key] = value; }
}
```

생성자에서 `Config._instance`를 확인하는 이유는 `new Config()`를 직접 호출해도 기존 인스턴스가 반환되게 하기 위해서다. `getInstance()`만 제공해서는 `new`를 통한 우회를 막을 수 없다.

## Node.js에서 실제로 쓰는 방법

Node.js의 `require`는 같은 모듈을 캐시한다. 클래스 없이도 자연스럽게 싱글톤이 된다.

```javascript
// config.js
const config = {
    apiUrl: process.env.API_URL || 'http://localhost:3000',
    timeout: 5000,
};

module.exports = config;
```

```javascript
// 어디서 require해도 같은 객체를 참조한다
const config1 = require('./config');
const config2 = require('./config');

console.log(config1 === config2); // true
```

`require.cache`를 삭제하면 캐시가 풀린다. 테스트 코드에서 `jest.resetModules()`나 `delete require.cache[...]`를 쓰면 다음 `require` 때 새 인스턴스가 만들어진다. 모듈 캐시에만 의존하는 싱글톤은 테스트 환경에서 기대대로 동작하지 않을 수 있다.

## 테스트에서 상태가 오염되는 상황

싱글톤 때문에 가장 자주 겪는 문제다.

```javascript
// counter.js
class Counter {
    constructor() {
        if (Counter._instance) return Counter._instance;
        this.count = 0;
        Counter._instance = this;
    }
    increment() { this.count++; }
    getCount() { return this.count; }
}
module.exports = new Counter();
```

```javascript
// counter.test.js
const counter = require('./counter');

test('처음에는 0이다', () => {
    expect(counter.getCount()).toBe(0); // 단독 실행 시 통과
});

test('increment 후 1이다', () => {
    counter.increment();
    expect(counter.getCount()).toBe(1); // 통과
});

test('다시 0이다', () => {
    // 앞 테스트 실행 순서에 따라 결과가 달라진다
    expect(counter.getCount()).toBe(0); // 실패
});
```

테스트 파일 하나만 실행하면 통과하다가, 전체 실행하면 실패하는 케이스다. 앞 테스트에서 바꾼 싱글톤 상태가 다음 테스트로 넘어오기 때문이다.

가장 흔한 해결책은 인스턴스를 재설정하는 메서드를 만드는 것이다.

```javascript
class Counter {
    constructor() {
        if (Counter._instance) return Counter._instance;
        this.count = 0;
        Counter._instance = this;
    }

    static _reset() {
        Counter._instance = null;
    }

    increment() { this.count++; }
    getCount() { return this.count; }
}
```

```javascript
describe('Counter', () => {
    beforeEach(() => {
        Counter._reset();
    });

    test('항상 0에서 시작한다', () => {
        expect(new Counter().getCount()).toBe(0);
    });
});
```

`_reset`이 프로덕션 코드에 노출된다는 단점이 있다. 의존성 주입 방식으로 바꾸는 것이 낫다. 싱글톤 대신 한 곳에서 인스턴스를 만들어 필요한 모듈에 넘기면 테스트에서 새 인스턴스를 만드는 게 간단해진다.

`jest.resetModules()`를 쓰는 방법도 있다.

```javascript
describe('Counter', () => {
    let counter;

    beforeEach(() => {
        jest.resetModules();
        counter = require('./counter');
    });

    test('항상 0에서 시작한다', () => {
        expect(counter.getCount()).toBe(0);
    });
});
```

관련 모듈 전체가 다시 로드되므로, 무거운 초기화가 있는 모듈(DB 연결 등)이 포함되면 테스트 속도가 눈에 띄게 느려진다.

## Worker Threads에서 싱글톤은 공유되지 않는다

Node.js의 Worker Threads는 메모리를 공유하지 않는다. 각 워커는 별도의 V8 인스턴스를 갖고, 싱글톤 인스턴스도 각자 만든다.

```javascript
const { Worker, isMainThread, parentPort } = require('worker_threads');

class Counter {
    constructor() {
        if (Counter._instance) return Counter._instance;
        this.count = 0;
        Counter._instance = this;
    }
    increment() { this.count++; }
    getCount() { return this.count; }
}
const counter = new Counter();

if (isMainThread) {
    counter.increment(); // 메인 스레드에서 1로 증가

    const worker = new Worker(__filename);
    worker.on('message', (msg) => {
        console.log('메인 카운터:', counter.getCount()); // 1
        console.log('워커 카운터:', msg);               // 0 — 별개의 인스턴스
    });
} else {
    // 워커는 자체 Counter 인스턴스를 갖는다. 메인 스레드 상태를 모른다.
    parentPort.postMessage(counter.getCount());
}
```

워커 스레드 간에 상태를 공유해야 한다면 싱글톤으로는 해결이 안 된다. `SharedArrayBuffer`와 `Atomics`로 단순한 수치는 공유할 수 있지만, 복잡한 상태는 Redis 같은 외부 저장소로 빼는 것이 현실적이다.

## pm2 클러스터 모드에서 싱글톤이 무의미해지는 지점

pm2의 클러스터 모드는 Node.js 프로세스를 CPU 코어 수만큼 포크한다. 각 프로세스는 완전히 독립적이어서 메모리를 공유하지 않는다.

```bash
pm2 start app.js -i max  # CPU 코어 수만큼 프로세스 생성
```

프로세스가 4개라면 싱글톤 인스턴스도 4개가 생긴다.

```
프로세스 0: counter.count = 5
프로세스 1: counter.count = 3
프로세스 2: counter.count = 8
프로세스 3: counter.count = 1
```

로드밸런서가 요청을 어느 프로세스로 보내느냐에 따라 같은 엔드포인트가 다른 값을 반환하게 된다.

실제로 겪었던 케이스는 rate limiter를 싱글톤으로 구현한 경우다. 프로세스 4개에서 각자 카운터를 관리하니 설정한 제한의 4배까지 요청이 통과되고 있었다. 단일 프로세스 테스트에서는 정상 동작했기 때문에 배포 후에야 발견됐다.

pm2 클러스터 환경에서 상태를 공유해야 한다면 Redis를 써야 한다. 싱글톤은 단일 프로세스 안에서만 인스턴스가 하나임을 보장한다.

## 싱글톤이 적합한 경우와 그렇지 않은 경우

싱글톤이 잘 맞는 경우는 프로세스 전체에서 하나만 있어야 하고, 상태 공유보다 초기화 비용 절감이 목적인 경우다. 설정 값 읽기, 로거 인스턴스, DB 연결 풀 객체가 여기 해당한다.

문제가 생기는 패턴은 대부분 두 가지다. 싱글톤에 가변 상태를 넣어 테스트 사이에 오염이 생기는 경우, 그리고 pm2 클러스터나 Worker Threads처럼 멀티 프로세스/스레드 환경에서 싱글톤이 공유된다고 가정하는 경우다. 두 번째는 단일 인스턴스에서 잘 돌다가 스케일 아웃하는 순간 조용히 깨지는 유형이라 특히 늦게 발견된다.
