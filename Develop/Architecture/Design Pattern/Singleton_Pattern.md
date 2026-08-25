---
title: Singleton Pattern (싱글톤 패턴)
tags: [design-patterns, javascript, architecture]
updated: 2026-08-24
---

# Singleton Pattern (싱글톤 패턴)

클래스의 인스턴스를 프로세스 전체에서 하나만 만들도록 강제하는 패턴이다. 전역 변수와 다를 게 없지만, 생성 시점을 제어하고 초기화 로직을 캡슐화할 수 있다.

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

주의할 점은 `require.cache`를 삭제하면 캐시가 풀린다는 것이다. 테스트 코드에서 `jest.resetModules()`나 `delete require.cache[...]`를 쓰면 다음 `require` 때 새 인스턴스가 만들어진다. 모듈 캐시에만 의존하는 싱글톤은 테스트 환경에서 기대대로 동작하지 않을 수 있다.

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

`_reset`이 프로덕션 코드에 노출된다는 단점이 있다. 이게 마음에 걸린다면 아예 의존성 주입 방식으로 바꾸는 것이 낫다. 싱글톤 대신 한 곳에서 인스턴스를 만들어 필요한 모듈에 넘기면 테스트에서 새 인스턴스를 만드는 게 간단해진다.

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
// main.js
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
