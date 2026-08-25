---
title: Factory Method Pattern (팩토리 메서드 패턴)
tags: [design-patterns, javascript, architecture, language]
updated: 2026-08-24
---

# Factory Method Pattern

객체를 생성하는 책임을 서브클래스에 위임하는 패턴이다. 클라이언트는 어떤 클래스가 만들어지는지 알 필요가 없다.

GoF 정의 기준으로 팩토리 메서드는 **인스턴스 메서드 오버라이드**다. `Creator` 가 `createProduct()` 를 선언하고, `ConcreteCreator` 가 그걸 구현한다. `static create(type)` 처럼 타입 파라미터로 분기하는 건 Simple Factory 로 따로 부른다. 실무에서 두 형태를 혼용하면서 이름만 같아 "팩토리를 썼으니 OCP 를 지킨다"고 착각하는 경우가 있다.

## 구조

네 가지 역할로 나뉜다.

- **Product**: 생성될 객체의 공통 인터페이스
- **ConcreteProduct**: Product 를 구현한 실제 클래스
- **Creator**: `createProduct()` 를 선언하는 추상 클래스. 공통 로직도 여기 담는다
- **ConcreteCreator**: `createProduct()` 를 오버라이드해서 구체 타입을 반환

```javascript
// Product
class Notifier {
  send(message) { throw new Error('구현 필요'); }
}

// ConcreteProducts
class EmailNotifier extends Notifier {
  send(message) {
    // 실제로는 SMTP 클라이언트 호출
    console.log(`[Email] ${message}`);
  }
}

class SlackNotifier extends Notifier {
  constructor(webhookUrl) {
    super();
    this.webhookUrl = webhookUrl;
  }

  send(message) {
    // 실제로는 Slack Incoming Webhook POST
    console.log(`[Slack → ${this.webhookUrl}] ${message}`);
  }
}

// Creator
class NotificationService {
  // 서브클래스가 오버라이드해야 할 팩토리 메서드
  createNotifier() {
    throw new Error('서브클래스에서 구현');
  }

  // 공통 로직 — 팩토리 메서드를 내부에서 호출한다
  alert(message) {
    const notifier = this.createNotifier();
    notifier.send(`[ALERT] ${message}`);
  }
}

// ConcreteCreators
class EmailNotificationService extends NotificationService {
  createNotifier() {
    return new EmailNotifier();
  }
}

class SlackNotificationService extends NotificationService {
  constructor(webhookUrl) {
    super();
    this.webhookUrl = webhookUrl;
  }

  createNotifier() {
    return new SlackNotifier(this.webhookUrl);
  }
}
```

클라이언트는 `EmailNotificationService` 나 `SlackNotificationService` 를 선택하면 된다. `EmailNotifier` 나 `SlackNotifier` 를 직접 참조하지 않는다.

```javascript
function sendAlert(service, message) {
  service.alert(message);
}

const emailSvc = new EmailNotificationService();
const slackSvc = new SlackNotificationService('https://hooks.slack.com/...');

sendAlert(emailSvc, '서버 응답 지연');
sendAlert(slackSvc, '서버 응답 지연');
```

`sendAlert` 는 `NotificationService` 타입만 알면 된다. 나중에 PagerDutyNotificationService 를 추가해도 이 함수를 건드리지 않는다.

## Simple Factory 와 OCP

위 GoF 형태 외에 실무에서 더 자주 보이는 건 이쪽이다.

```javascript
class NotifierFactory {
  static create(type, config = {}) {
    switch (type) {
      case 'email': return new EmailNotifier(config);
      case 'slack': return new SlackNotifier(config.webhookUrl);
      default:      throw new Error(`지원하지 않는 채널: ${type}`);
    }
  }
}
```

이 형태를 두고 "OCP 를 지킨다"고 설명하는 자료가 많은데 그렇지 않다. 새 채널을 추가하려면 이 함수를 열어야 한다. 달라진 것은 흩어져 있던 `new` 분기가 한 곳으로 모였다는 점이고, 그것만으로도 충분히 가치가 있다. 다만 그건 OCP 가 아니라 **분기의 국소화**다.

수정 없이 확장하려면 등록표를 쓴다.

```javascript
class NotifierFactory {
  static #registry = new Map();

  static register(type, Ctor) {
    this.#registry.set(type, Ctor);
  }

  static create(type, ...args) {
    const Ctor = this.#registry.get(type);
    if (!Ctor) throw new Error(`지원하지 않는 채널: ${type}`);
    return new Ctor(...args);
  }
}

// 팩토리 파일을 건드리지 않고 확장
NotifierFactory.register('email', EmailNotifier);
NotifierFactory.register('slack', SlackNotifier);

// 서드파티 알림 채널을 외부에서 등록
import { PagerDutyNotifier } from './pagerduty-notifier';
NotifierFactory.register('pagerduty', PagerDutyNotifier);
```

대신 대가가 있다. **등록 코드가 실행돼야 그 타입이 존재한다.** 등록 모듈을 import 하지 않으면 런타임에야 "지원하지 않는 채널" 에러가 나온다. 번들러가 부수효과뿐인 import 를 tree-shaking 으로 제거하면 로컬에서는 멀쩡한데 배포 환경에서만 터지기도 한다. TypeScript 라면 `switch` 쪽이 유니온 타입으로 누락을 컴파일 시점에 잡을 수 있다.

| | switch | 등록표 |
|---|---|---|
| 새 타입 추가 | 팩토리 파일 수정 | 등록 한 줄 |
| 누락 감지 시점 | 컴파일·리뷰 | 런타임 |
| 타입 좁히기 | TS 유니온으로 가능 | 대체로 문자열 키 |
| 적합한 상황 | 타입이 유한하고 한 팀이 관리 | 플러그인처럼 외부에서 타입이 들어옴 |

타입이 자주 늘지 않는다면 switch 쪽이 낫다. 등록표는 "팩토리를 고칠 수 없는 사람이 타입을 추가해야 할 때" 값을 한다.

## 캐싱 팩토리의 함정

객체 생성 비용을 아끼려고 팩토리에 캐시를 붙이는 경우가 있다.

```javascript
class NotifierFactory {
  static #cache = new Map();
  static #maxSize = 50;

  static create(type, config) {
    const key = `${type}:${JSON.stringify(config)}`;

    if (this.#cache.has(key)) {
      return this.#cache.get(key);  // 캐시 히트
    }

    const notifier = this.#createNew(type, config);

    if (this.#cache.size >= this.#maxSize) {
      // 첫 키를 지운다
      const oldest = this.#cache.keys().next().value;
      this.#cache.delete(oldest);
    }

    this.#cache.set(key, notifier);
    return notifier;
  }
}
```

같은 키로 두 번 부르면 **같은 객체**가 돌아온다.

```javascript
const a = NotifierFactory.create('slack', { webhookUrl: 'https://...' });
const b = NotifierFactory.create('slack', { webhookUrl: 'https://...' });
a === b  // true

a.rateLimitRemaining = 10;
b.rateLimitRemaining  // 10 — b 는 건드린 적이 없다
```

"캐시"라는 이름 때문에 생성 비용만 아끼는 것처럼 읽히지만, 실제로는 모든 호출자가 하나의 가변 객체를 나눠 쓰는 구조다. **팩토리에 캐시를 붙이려면 생성되는 객체가 불변이거나 무상태여야 한다.** 연결 상태나 rate limit 카운터를 갖는 Notifier 는 그 조건에 맞지 않는다.

축출 정책도 이름과 다르다. `Map.keys().next().value` 는 삽입 순서 기준으로 가장 먼저 넣은 항목을 지운다. `get` 은 Map 의 삽입 순서를 바꾸지 않으므로 아무리 자주 읽어도 오래된 항목부터 나간다 — LRU 가 아니라 **FIFO** 다.

```
용량 3에서 A B C 를 넣고 → A 를 다시 읽고 → D 를 넣으면
남는 키: B C D   (A 를 방금 읽었는데도 축출된다)
```

LRU 로 만들려면 히트 시 `delete` 후 `set` 으로 다시 넣어 순서를 갱신해야 한다.

정적 필드를 상속과 함께 쓸 때도 문제가 생긴다. `class SubFactory extends NotifierFactory {}` 는 자기 Map 을 갖지 않고 부모의 Map 에 쓴다. 서브 팩토리마다 캐시를 분리하려면 각 클래스에 `static #cache = new Map()` 을 따로 선언해야 한다. 이 공유는 조용해서, 서브 팩토리를 여러 개 만든 뒤에야 "왜 남의 객체가 반환되지"로 드러난다.

## 실무 사례: 데이터베이스 연결

환경 변수나 설정 파일로 DB 종류를 바꿔야 할 때 팩토리가 값을 한다.

```javascript
class DatabaseConnection {
  async connect() { throw new Error('구현 필요'); }
  async disconnect() { throw new Error('구현 필요'); }
  async query(sql, params = []) { throw new Error('구현 필요'); }
}

class MySQLConnection extends DatabaseConnection {
  constructor(config) {
    super();
    this.config = config;
    this.client = null;
  }

  async connect() {
    // mysql2/promise 사용
    this.client = await mysql.createConnection(this.config);
  }

  async query(sql, params = []) {
    const [rows] = await this.client.execute(sql, params);
    return rows;
  }

  async disconnect() {
    await this.client.end();
  }
}

class PostgreSQLConnection extends DatabaseConnection {
  constructor(config) {
    super();
    this.config = config;
    this.client = null;
  }

  async connect() {
    this.client = new pg.Client(this.config);
    await this.client.connect();
  }

  async query(sql, params = []) {
    const result = await this.client.query(sql, params);
    return result.rows;
  }

  async disconnect() {
    await this.client.end();
  }
}

class DatabaseFactory {
  static create(type, config) {
    switch (type) {
      case 'mysql':
        return new MySQLConnection(config);
      case 'postgresql':
      case 'postgres':
        return new PostgreSQLConnection(config);
      default:
        throw new Error(`지원하지 않는 DB 타입: ${type}`);
    }
  }
}
```

```javascript
const db = DatabaseFactory.create(process.env.DB_TYPE, {
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT),
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
});

await db.connect();
const rows = await db.query('SELECT * FROM users WHERE active = ?', [true]);
await db.disconnect();
```

테스트에서는 `process.env.DB_TYPE` 을 `'sqlite'` 같은 인메모리 DB 로 바꾸면 된다. DB 마이그레이션 기간에 두 연결을 동시에 유지하는 것도 팩토리 하나로 처리할 수 있다.

주의할 점이 있다. 위 예제에서 `MySQLConnection` 과 `PostgreSQLConnection` 의 `query` 파라미터 바인딩 방식이 다르다. MySQL 은 `?`, PostgreSQL 은 `$1 $2 ...` 를 쓴다. 인터페이스가 같아 보여도 실제로 교환 가능하지 않다. 이 차이를 숨기고 싶다면 추상 계층에서 파라미터 변환을 처리해야 한다.

## 언제 쓰고 언제 쓰지 않는지

쓰면 좋은 경우:
- 런타임에 타입이 결정된다. 설정 파일, 환경 변수, 사용자 입력이 그 예다
- 같은 생성 로직이 여러 곳에 흩어져 있고, 나중에 그 로직이 달라질 여지가 있다
- 테스트에서 구현체를 교체해야 한다. Mock 이나 인메모리 구현을 주입해야 할 때

쓰지 않는 게 나은 경우:
- 항상 같은 타입만 생성한다. `new User()` 를 팩토리로 감쌀 이유가 없다
- 생성 로직이 단순하다. 추상화를 더하면 코드 추적이 어려워진다. `new` 가 사라지면 스택 트레이스에 팩토리만 찍히고 어떤 구체 타입인지는 디버거를 붙여야 안다
- 타입이 하나뿐이다. 확장 계획이 없는데 인터페이스를 만들면 코드 읽기가 복잡해진다

## 다른 패턴과의 관계

**Abstract Factory** 는 연관된 객체군을 함께 만드는 패턴이다. Factory Method 가 단일 객체를 담당한다면, Abstract Factory 는 `createButton()` / `createInput()` / `createModal()` 처럼 테마나 플랫폼에 따라 묶음으로 생성한다.

**Builder** 는 생성 과정 자체가 복잡할 때 쓴다. Factory Method 가 "무엇을" 만들지 결정하면, Builder 는 "어떻게" 단계별로 조립할지 관리한다. 선택적 파라미터가 많아서 생성자 인자가 7개를 넘어가기 시작하면 Builder 를 검토한다.

**Singleton** 과 조합하는 경우도 있다. 팩토리 자체가 내부 상태(캐시, 커넥션 풀)를 갖는다면 전역에서 하나의 인스턴스를 쓰는 게 합리적이다. 상태가 없는 팩토리라면 `static` 메서드로 충분하다.

## 성능 측정 착각

직접 생성과 팩토리 생성을 비교하는 벤치마크가 자주 등장하는데, 대부분 결과를 신뢰할 수 없다.

```javascript
const ITER = 100_000;

console.time('직접 생성');
for (let i = 0; i < ITER; i++) {
  new EmailNotifier();  // 결과를 아무 데도 쓰지 않는다
}
console.timeEnd('직접 생성');

console.time('팩토리');
for (let i = 0; i < ITER; i++) {
  NotifierFactory.create('email');
}
console.timeEnd('팩토리');
```

결과를 쓰지 않으면 JIT 이 할당 자체를 제거할 수 있다. 두 루프를 같은 프로세스에서 순서대로 돌리면 앞 루프가 JIT 워밍업을 마친 뒤 뒤 루프가 돈다. 순서만 바꿔 돌리면 승자가 뒤집힌다.

```
direct-first : 직접 1.51ms / 팩토리 1.17ms
factory-first: 직접 0.82ms / 팩토리 1.67ms
direct-first : 직접 1.14ms / 팩토리 1.17ms
factory-first: 직접 0.63ms / 팩토리 1.32ms
```

먼저 도는 쪽이 손해를 보는 것뿐이다.

팩토리 도입 여부를 이런 미시 측정으로 정하지 않는다. 함수 호출 하나와 `switch` 한 번이 실제 병목인 경우는 드물다. 이 패턴의 실제 비용은 **`new` 가 코드에서 사라져 어떤 구현이 만들어졌는지 추적하기 어려워지는 것**이다. 스택 트레이스에 팩토리만 찍히고 어떤 구체 타입인지는 디버거를 붙여야 아는 상황이 그 대가다.
