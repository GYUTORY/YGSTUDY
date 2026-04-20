---
title: TypeScript Class
tags: [language, typescript, 타입-및-타입-정의, typescript-types, object-types, class]
updated: 2026-04-20
---

# TypeScript Class

## 배경

TypeScript의 `class`는 ES2015 클래스 문법 위에 타입 시스템을 얹은 구조다. 런타임에는 그냥 JavaScript 클래스로 컴파일되고, 타입스크립트가 추가로 하는 일은 두 가지다. 첫째, 필드와 메서드의 타입을 체크한다. 둘째, 클래스를 선언하는 순간 두 종류의 타입이 자동으로 만들어진다 — 인스턴스 타입과 생성자 타입(정적 면, static side).

실무에서 클래스를 쓸 때 가장 자주 헷갈리는 지점이 바로 이 두 타입의 구분이다. `class User {}` 한 줄을 쓰면 `User`라는 이름이 두 곳에 등록된다. 값 공간에는 생성자 함수(정적 멤버를 가진 함수)가, 타입 공간에는 인스턴스 타입이 들어간다. 그래서 `const u: User = new User()`는 인스턴스 타입이고, `const C: typeof User = User`는 생성자 타입이다. 이 구분이 안 되면 DI 컨테이너나 팩토리를 타입으로 안전하게 엮을 수 없다.

또 하나 주의할 점. 런타임 객체지향에 익숙한 사람은 클래스 타입이 nominal(명목적)일 거라고 기대하지만 TypeScript의 클래스 타입은 여전히 구조적(structural)이다. 즉 `class A { x: number }`와 `class B { x: number }`는 private 필드가 없는 한 서로 할당 가능하다. 이 차이 때문에 Java/C# 출신이 처음에 많이 당황한다.

## 클래스에서 만들어지는 두 가지 타입

### 인스턴스 타입

클래스 이름을 타입 자리에서 쓰면 그건 인스턴스 타입이다. `new` 키워드로 만든 객체가 이 타입에 해당한다.

```typescript
class User {
    constructor(public id: number, public name: string) {}
    greet(): string {
        return `hi, ${this.name}`;
    }
}

const u: User = new User(1, "kim");
```

여기서 `User`는 타입이고, `{ id: number; name: string; greet(): string }` 구조와 동등하다.

### 생성자 타입 (typeof Class)

클래스 자체 — `new`가 붙기 전의 함수 — 를 가리키는 타입은 `typeof ClassName`으로 얻는다. 이게 있어야 팩토리나 DI에서 "클래스를 인자로 받아서 나중에 생성한다" 같은 패턴을 타입 안전하게 짤 수 있다.

```typescript
class User {
    constructor(public id: number) {}
}

function createOne(Ctor: typeof User, id: number): User {
    return new Ctor(id);
}
```

`typeof User`는 생성자 시그니처(`new (id: number) => User`)와 정적 멤버를 모두 포함한다. 둘을 분리해서 일반화하고 싶을 때는 아래에서 다룰 `new (...args: any[]) => T` 형태의 constructor signature를 직접 쓴다.

## 인터페이스 구현 (implements)

클래스가 특정 구조를 따라야 한다는 계약을 표현할 때 `implements`를 쓴다. `extends`와 혼동하기 쉬운데, `implements`는 구현 상속이 아니라 "타입 체크만" 한다. 즉 인터페이스의 필드·메서드가 클래스에 존재하는지 검사할 뿐 런타임에는 아무것도 남지 않는다.

```typescript
interface Repository<T> {
    findById(id: number): Promise<T | null>;
    save(entity: T): Promise<T>;
}

interface User {
    id: number;
    name: string;
}

class UserRepository implements Repository<User> {
    async findById(id: number): Promise<User | null> {
        // ...
        return null;
    }

    async save(entity: User): Promise<User> {
        return entity;
    }
}
```

### implements를 쓸 때 자주 실수하는 지점

`implements`는 파라미터 타입에 contextual typing을 적용하지 않는다. 무슨 말이냐면, 인터페이스에 `save(entity: User)`라고 적혀 있어도 클래스 메서드 쪽에서 파라미터 타입을 생략하면 `any`가 된다.

```typescript
class UserRepository implements Repository<User> {
    async save(entity): Promise<User> {  // entity는 any — 컴파일러가 안 막아준다
        return entity;
    }
}
```

이런 케이스를 잡으려면 `tsconfig`에서 `noImplicitAny`를 켜거나 파라미터 타입을 직접 명시해야 한다. 실무에서는 대부분 명시적으로 적는 쪽을 권장한다 — 리뷰에서 놓치기 쉽다.

여러 인터페이스를 구현하는 것도 가능하다. 클래스 상속은 단일 상속만 되지만 `implements`는 여러 개를 콤마로 나열한다.

```typescript
interface Loggable { log(): void; }
interface Serializable { toJSON(): string; }

class Event implements Loggable, Serializable {
    constructor(private name: string) {}
    log(): void { console.log(this.name); }
    toJSON(): string { return JSON.stringify({ name: this.name }); }
}
```

### implements vs 구조적 타입

사실 `implements` 없이도 "구조만 맞추면" 그 인터페이스를 만족하는 값으로 쓸 수 있다. TypeScript가 구조적 타입 시스템이기 때문이다.

```typescript
class UserRepository {
    async findById(id: number): Promise<User | null> { return null; }
    async save(entity: User): Promise<User> { return entity; }
}

const repo: Repository<User> = new UserRepository();  // implements 안 붙여도 OK
```

그래도 `implements`를 붙이는 이유는 "이 클래스의 의도가 인터페이스를 만족시키는 것"이라는 걸 명시적으로 드러내기 위해서다. 인터페이스가 바뀌면 구현 클래스에서 바로 컴파일 에러가 나므로 리팩토링할 때 누락된 구현을 빨리 잡을 수 있다.

## 추상 클래스와의 차이

`abstract class`는 인터페이스와 일반 클래스의 중간 성격이다. 필드 초기화나 메서드 구현을 일부 제공하면서도, 몇몇 메서드는 자식 클래스가 반드시 구현하도록 강제한다.

```typescript
abstract class HttpHandler {
    async handle(req: Request): Promise<Response> {
        const user = await this.authenticate(req);
        return this.process(req, user);
    }

    protected abstract authenticate(req: Request): Promise<User>;
    protected abstract process(req: Request, user: User): Promise<Response>;
}

class LoginHandler extends HttpHandler {
    protected async authenticate(req: Request): Promise<User> { /* ... */ }
    protected async process(req: Request, user: User): Promise<Response> { /* ... */ }
}
```

### 인터페이스 vs 추상 클래스 — 언제 뭘 쓰나

인터페이스는 타입 전용 계약이다. 런타임에 아무것도 남지 않고, 여러 개를 동시에 구현할 수 있고, 공통 로직을 담을 수 없다. 상태 없는 순수한 "shape"을 정의할 때 적합하다.

추상 클래스는 런타임에 실제 JavaScript 클래스로 존재한다. `new`는 못 하지만 공통 필드·메서드를 자식에게 상속시킬 수 있다. 템플릿 메서드 패턴처럼 "골격은 부모가, 세부 구현은 자식이" 같은 구조가 필요할 때 쓴다.

실무 감각으로는, "이 계약을 만족하는 객체가 필요할 뿐이다" 싶으면 인터페이스, "공통 구현을 재사용하면서 일부만 다르게 하고 싶다" 싶으면 추상 클래스를 쓴다. 추상 클래스는 상속 계층을 만들기 때문에 남발하면 수정 비용이 커진다 — 필요한 공통 로직이 진짜로 공통인지, 아니면 잠깐 겹쳐 보이는 건지 한 번 더 의심해야 한다.

### 추상 클래스는 생성자 타입에도 영향을 준다

`abstract class Foo`의 생성자 타입 `typeof Foo`는 `new`를 허용하지 않는다. 그래서 팩토리 함수가 구체 클래스만 받도록 제약할 때 유용하다.

```typescript
abstract class Animal {
    abstract makeSound(): void;
}

class Dog extends Animal {
    makeSound(): void { console.log("왈"); }
}

function instantiate<T extends Animal>(Ctor: new () => T): T {
    return new Ctor();
}

instantiate(Dog);     // OK
instantiate(Animal);  // 컴파일 에러 — abstract는 new 못 함
```

`new () => T` 시그니처가 "실제로 인스턴스화 가능한 생성자"를 의미하기 때문에 추상 클래스가 걸러진다. 이런 타입 제약이 필요 없을 때는 `abstract new () => T`를 쓰면 추상 클래스까지 받을 수 있다 (TypeScript 4.2+).

## 클래스를 타입으로 사용하는 패턴

### 생성자 시그니처로 DI 받기

의존성 주입이나 팩토리에서 "클래스 자체"를 파라미터로 받고 싶을 때, `new (...args) => T` 형태의 시그니처가 핵심이다.

```typescript
type Constructor<T = {}> = new (...args: any[]) => T;

function createLogger<T extends Constructor>(Base: T) {
    return class extends Base {
        log(message: string): void {
            console.log(`[${new Date().toISOString()}] ${message}`);
        }
    };
}

class Service {
    run(): void { /* ... */ }
}

const LoggingService = createLogger(Service);
const svc = new LoggingService();
svc.log("started");
svc.run();
```

이게 바로 믹스인(mixin) 패턴이다. `Constructor<T>` 제네릭 제약 덕에 `Base`가 반드시 생성 가능한 클래스여야 한다는 걸 타입으로 강제할 수 있다.

### InstanceType / ConstructorParameters 유틸리티

클래스 타입에서 인스턴스 타입이나 생성자 인자 타입을 뽑아내는 유틸리티 타입이 표준 라이브러리에 들어있다.

```typescript
class User {
    constructor(public id: number, public name: string) {}
}

type UserInstance = InstanceType<typeof User>;           // User
type UserCtorArgs = ConstructorParameters<typeof User>;  // [number, string]

function createFromArgs<T extends new (...args: any[]) => any>(
    Ctor: T,
    args: ConstructorParameters<T>
): InstanceType<T> {
    return new Ctor(...args);
}

const u = createFromArgs(User, [1, "kim"]);  // u: User
```

`createFromArgs` 같은 함수는 라이브러리 경계에서 제네릭 팩토리를 짤 때 종종 등장한다. 인자 배열을 그대로 전달하면서도 타입을 잃지 않게 해준다.

### private 필드와 nominal 흉내

앞에서 TypeScript 클래스는 구조적이라고 했다. 그런데 ECMAScript private 필드 (`#field`)나 TypeScript `private` 제어자는 타입 호환성에 영향을 준다. 특히 `#field`는 런타임에도 진짜 private이고, 브랜딩 효과가 있어 "같은 구조지만 다른 클래스"를 컴파일러가 구분하게 만든다.

```typescript
class UserId {
    #brand!: never;
    constructor(public readonly value: number) {}
}

class OrderId {
    #brand!: never;
    constructor(public readonly value: number) {}
}

function loadUser(id: UserId) { /* ... */ }

loadUser(new UserId(1));          // OK
loadUser(new OrderId(1) as any);  // 런타임에는 돌지만 의도적으로 캐스팅 안 하면 타입 에러
```

ID 타입을 섞어 쓰는 사고를 막을 때 이 트릭을 쓰기도 한다. 다만 과용하면 코드가 복잡해지니까 도메인 모델에서 정말 중요한 ID에만 제한적으로 적용하는 게 좋다.

### 메서드 오버로드와 `this` 타입

메서드 반환 타입으로 `this`를 쓰면 체이닝 API에서 상속된 서브클래스도 자기 타입을 유지한다.

```typescript
class QueryBuilder {
    where(cond: string): this {
        // ...
        return this;
    }
}

class UserQuery extends QueryBuilder {
    activeOnly(): this {
        return this;
    }
}

new UserQuery().where("age > 18").activeOnly();  // this 덕에 UserQuery로 유지됨
```

반환 타입을 `QueryBuilder`로 박아두면 `.activeOnly()`에서 체인이 끊긴다. 빌더 패턴이나 fluent API를 클래스로 짤 때 이 차이를 꼭 의식해야 한다.

## 실무에서 마주치는 문제들

### 생성자 오버로드의 불편함

TypeScript의 클래스 생성자는 함수 오버로드를 지원하긴 하지만 구현 시그니처가 하나로 통합돼야 해서 분기 로직이 지저분해진다. 인자 조합이 여러 개라면 정적 팩토리 메서드로 나누는 쪽이 훨씬 읽기 좋다.

```typescript
class User {
    private constructor(public id: number, public name: string) {}

    static fromId(id: number): User {
        return new User(id, `user_${id}`);
    }

    static fromPayload(payload: { id: number; name: string }): User {
        return new User(payload.id, payload.name);
    }
}
```

생성자를 `private`로 막고 정적 메서드만 노출하면 호출자가 항상 의도된 경로를 타도록 강제할 수 있다.

### 상속 남용의 함정

5년쯤 굴리다 보면 상속 계층이 3단 이상으로 쌓인 코드는 거의 예외 없이 리팩토링 대상이 된다. 공통 로직을 뽑으려고 쓴 부모 클래스가, 요구사항이 갈라지면서 자식 간의 균열을 억지로 덮는 용도로 변질되기 때문이다. 가능하면 상속 대신 조합(composition)으로 풀고, 꼭 상속이 필요할 때도 단일 계층으로 유지하는 편이 유지보수에 유리하다.

### 클래스로 감싼 DTO 안티패턴

요청·응답 DTO를 클래스로 정의하면 편해 보이지만, JSON 직렬화·역직렬화를 거치면서 인스턴스가 아닌 순수 객체가 된다. `dto instanceof UserDto`는 네트워크 경계를 넘은 뒤에는 항상 `false`다. DTO 수준에서는 `interface`나 `type`으로 충분한 경우가 많고, 굳이 클래스로 묶으려면 `class-transformer` 같은 라이브러리로 변환 경계를 명확히 잡아야 한다.

## 참고

### 클래스 vs 인터페이스 vs 추상 클래스

| 구분 | 인터페이스 | 추상 클래스 | 일반 클래스 |
|------|-----------|------------|------------|
| 런타임 존재 | 없음 | 있음 | 있음 |
| 구현 포함 | 불가 | 일부 가능 | 가능 |
| 인스턴스화 | 불가 | 불가 | 가능 |
| 다중 구현 | 가능 (implements 여러 개) | 불가 | 불가 |
| 상태(필드) | 없음 (선언만) | 있음 | 있음 |
| 생성자 | 없음 | 있음 (protected) | 있음 |

### 관련 문서

- [Interface.md](./Interface.md)
- [추상 클래스.md](./추상%20클래스.md)
- [접근 제어자.md](./접근%20제어자.md)
