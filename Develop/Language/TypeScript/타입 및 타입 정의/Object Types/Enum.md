---
title: TypeScript Enum
tags: [language, typescript, 타입-및-타입-정의, typescript-types, object-types, enum]
updated: 2026-04-20
---

# TypeScript Enum

## 배경

Enum은 관련된 상수 묶음에 이름을 붙여 쓰는 문법이다. 다른 언어에서 넘어온 사람이 TypeScript에서 가장 먼저 찾게 되는 기능이기도 하다. 문제는 TypeScript의 Enum이 단순한 타입 레벨 개념이 아니라, **런타임에 실제 객체로 존재하는 독특한 구조**라는 점이다. 이 특성 때문에 번들 크기, 트리 셰이킹, 라이브러리 호환성에서 생각지 못한 이슈가 생긴다.

실무에서는 팀 컨벤션으로 "Enum 대신 union literal을 써라"고 못 박아 둔 곳이 많다. 이유는 뒤에서 컴파일 결과를 비교하며 설명한다.

## 숫자 Enum (Numeric Enum)

### 동작

```typescript
enum Direction {
    Up,      // 0
    Down,    // 1
    Left,    // 2
    Right,   // 3
}

enum HttpStatus {
    OK = 200,
    Created = 201,
    BadRequest = 400,
}
```

값을 생략하면 0부터 시작해 자동 증가한다. 중간에 값을 지정하면 그 뒤부터 이어서 증가한다.

### 컴파일 결과

```typescript
// 원본
enum Direction { Up, Down, Left, Right }

// 컴파일 후 (JavaScript)
var Direction;
(function (Direction) {
    Direction[Direction["Up"] = 0] = "Up";
    Direction[Direction["Down"] = 1] = "Down";
    Direction[Direction["Left"] = 2] = "Left";
    Direction[Direction["Right"] = 3] = "Right";
})(Direction || (Direction = {}));
```

`Direction[0] === "Up"`과 `Direction.Up === 0`이 둘 다 성립하는 역매핑 구조가 만들어진다. 숫자 키로도, 문자 키로도 조회 가능한 양방향 맵이다.

### 숫자 Enum의 위험

숫자 Enum은 타입 안전성이 생각보다 약하다. 정의되지 않은 숫자를 그대로 받아들인다.

```typescript
enum Direction { Up, Down, Left, Right }

function move(dir: Direction) {
    console.log(dir);
}

move(Direction.Up); // OK
move(999);          // OK (컴파일 에러 안 남)
```

API에서 받은 숫자를 그대로 Enum 타입 파라미터로 넘기는 코드가 꽤 많은데, 위처럼 아무 숫자나 통과시켜 버린다. 5년 전에 이걸로 결제 상태 코드가 엉뚱한 값으로 DB에 들어간 적이 있다. 숫자 Enum을 쓸 거면 경계값 검증을 따로 해야 한다.

## 문자열 Enum (String Enum)

### 동작

```typescript
enum OrderStatus {
    Pending = 'PENDING',
    Paid = 'PAID',
    Shipped = 'SHIPPED',
    Cancelled = 'CANCELLED',
}
```

문자열 Enum은 모든 멤버에 값을 명시해야 한다. 자동 증가가 없다.

### 컴파일 결과

```typescript
// 컴파일 후
var OrderStatus;
(function (OrderStatus) {
    OrderStatus["Pending"] = "PENDING";
    OrderStatus["Paid"] = "PAID";
    OrderStatus["Shipped"] = "SHIPPED";
    OrderStatus["Cancelled"] = "CANCELLED";
})(OrderStatus || (OrderStatus = {}));
```

숫자 Enum과 달리 **역매핑이 없다**. `OrderStatus["Pending"] === "PENDING"` 한 방향만 성립한다. `OrderStatus["PAID"]`로 이름을 얻을 수 없다.

### 실무 관점에서의 차이

숫자 Enum과 달리 문자열 Enum은 타입 체크가 엄격하다.

```typescript
enum OrderStatus { Pending = 'PENDING', Paid = 'PAID' }

function updateStatus(status: OrderStatus) {}

updateStatus(OrderStatus.Pending);  // OK
updateStatus('PENDING');            // 에러 (Type '"PENDING"' is not assignable to OrderStatus)
```

같은 값의 문자열 리터럴이라도 Enum 멤버로 대체할 수 없다. 이 동작이 보안적으로 유리하지만, 외부 JSON에서 파싱한 문자열을 바로 넘기지 못하는 불편함이 있다. 파싱 단계에서 명시적으로 Enum 멤버로 변환해 줘야 한다.

```typescript
const raw = 'PAID';

// 이렇게는 안 됨
// updateStatus(raw);

// 이렇게 해야 함
if (Object.values(OrderStatus).includes(raw as OrderStatus)) {
    updateStatus(raw as OrderStatus);
}
```

## const enum

### 동작과 컴파일 결과

`const`를 붙이면 컴파일 결과가 완전히 달라진다.

```typescript
const enum LogLevel {
    Debug = 0,
    Info = 1,
    Warn = 2,
    Error = 3,
}

function log(level: LogLevel, msg: string) {
    if (level >= LogLevel.Warn) console.error(msg);
}

log(LogLevel.Error, 'boom');
```

컴파일 후:

```javascript
// const enum은 아예 사라지고, 사용처가 값으로 치환된다
function log(level, msg) {
    if (level >= 2 /* LogLevel.Warn */) console.error(msg);
}

log(3 /* LogLevel.Error */, 'boom');
```

`LogLevel` 객체 자체가 번들에 포함되지 않는다. 리터럴만 남아 번들 크기가 줄고 런타임 객체 접근 비용도 없어진다.

### const enum의 함정

성능상 이점만 보면 무조건 쓰고 싶지만, 실무에서 권장되지 않는 경우가 많다.

**1. `isolatedModules`에서 에러가 난다**

Babel, esbuild, swc 같은 single-file transpiler는 const enum을 제대로 처리하지 못한다. 한 파일만 보고 컴파일하는 구조라 다른 파일의 const enum 값을 알 수 없기 때문이다.

```
// tsconfig에 isolatedModules: true 설정 시
// Cannot re-export a type when 'isolatedModules' is enabled.
// 'const' enums ... cannot be used in single-file transpilation.
```

Next.js, Vite 같은 도구들이 기본적으로 isolatedModules를 켜 두기 때문에 실질적으로 const enum을 못 쓴다.

**2. 라이브러리로 배포할 때 문제가 된다**

라이브러리가 const enum을 export하면 소비자 쪽 코드가 `preserveConstEnums`나 컴파일 설정에 따라 깨진다. 그래서 공개 패키지에서는 const enum을 거의 쓰지 않는다.

**3. 어차피 대안이 더 낫다**

아래 설명할 union literal 패턴이 const enum보다 번들 크기가 더 작고(0바이트) 이런 함정도 없다.

## enum 대신 union literal 패턴

실무에서 가장 많이 쓰는 대안이다. 일반 객체 + `as const` + `typeof`/`keyof` 조합.

### 기본 패턴

```typescript
// Enum 대신
const OrderStatus = {
    Pending: 'PENDING',
    Paid: 'PAID',
    Shipped: 'SHIPPED',
    Cancelled: 'CANCELLED',
} as const;

type OrderStatus = typeof OrderStatus[keyof typeof OrderStatus];
// type OrderStatus = 'PENDING' | 'PAID' | 'SHIPPED' | 'CANCELLED'

function updateStatus(status: OrderStatus) {
    console.log(status);
}

updateStatus(OrderStatus.Pending); // OK
updateStatus('PAID');              // OK (문자열 Enum과 다르게 리터럴도 허용)
updateStatus('UNKNOWN');           // 에러
```

타입과 값이 같은 이름을 공유하는 TypeScript의 네임스페이스 분리 덕분에 Enum 같은 사용감을 낸다.

### 컴파일 결과 비교

| 작성 방식 | 번들에 남는 코드 |
|----------|----------------|
| 숫자 Enum | 역매핑 포함된 IIFE 객체 전체 |
| 문자열 Enum | 단방향 객체 |
| const enum | 없음 (리터럴로 인라인) |
| `as const` 객체 + union | `{ Pending: 'PENDING', ... }` 객체만 (트리 셰이킹 가능) |
| 순수 union literal | 없음 (타입만) |

순수 union literal은 아예 런타임 값이 없다.

```typescript
type OrderStatus = 'PENDING' | 'PAID' | 'SHIPPED' | 'CANCELLED';

function updateStatus(status: OrderStatus) {}
updateStatus('PAID'); // OK
```

타입 전용으로 쓸 수 있으면 이게 가장 가볍다. 값 목록을 런타임에서 순회할 필요가 있을 때만 `as const` 객체 패턴으로 넘어가면 된다.

### 객체 패턴이 Enum보다 나은 이유

**1. 트리 셰이킹이 된다**

Enum은 IIFE로 감싸져 있어 번들러가 사용되지 않는 멤버를 제거하지 못한다. `as const` 객체는 단순 객체 리터럴이라 미사용 필드를 제거할 여지가 있다.

**2. 외부 문자열과 자연스럽게 호환된다**

```typescript
// 문자열 Enum
enum Role { Admin = 'ADMIN' }
function setRole(r: Role) {}
setRole('ADMIN'); // 에러

// union literal
type Role = 'ADMIN' | 'USER';
function setRole(r: Role) {}
setRole('ADMIN'); // OK
```

API 응답 JSON을 파싱한 문자열을 바로 함수에 넘길 수 있다. 백엔드 응답을 다루는 코드에서 훨씬 편하다.

**3. 선언 병합 같은 Enum 특유의 함정이 없다**

같은 이름의 Enum이 두 군데에서 선언되면 조용히 병합된다. 의도치 않은 충돌이 생길 수 있는데 union literal은 이런 동작이 없다.

### 값 순회가 필요한 경우

`as const` 객체 패턴을 쓰면 값 목록 순회도 된다.

```typescript
const OrderStatus = {
    Pending: 'PENDING',
    Paid: 'PAID',
    Shipped: 'SHIPPED',
    Cancelled: 'CANCELLED',
} as const;

type OrderStatus = typeof OrderStatus[keyof typeof OrderStatus];

const allStatuses = Object.values(OrderStatus);
// ['PENDING', 'PAID', 'SHIPPED', 'CANCELLED']

function isOrderStatus(v: string): v is OrderStatus {
    return allStatuses.includes(v as OrderStatus);
}
```

타입 가드까지 자연스럽게 엮인다. Enum의 역매핑이나 `Object.values` 필터링 같은 복잡한 처리가 필요 없다.

## 실무 판단 기준

어떤 걸 쓸지 고를 때 기준은 대략 이렇다.

- **순수하게 타입 체크만 필요** → union literal (`'A' | 'B' | 'C'`)
- **값 목록을 런타임에서 쓸 일이 있음** → `as const` 객체 + `typeof`/`keyof`
- **기존 코드와의 일관성 때문에 Enum을 유지해야 함** → 문자열 Enum 선택 (숫자 Enum 피하기)
- **내부 번들만 관리하고 번들 크기가 크리티컬** → const enum (단, isolatedModules와 충돌 없는 환경만)

새 프로젝트에서 Enum을 도입할 이유는 거의 없다고 본다. 기존 코드에서 Enum을 걷어낼 때는 문자열 Enum을 동일한 문자열 값의 union literal로 치환하는 게 가장 안전하다. 값이 동일해 API 호환성이 유지된다.

## 비트 플래그에 대해

과거 C 스타일 비트 플래그를 Enum으로 흉내 내는 패턴이 유명하다.

```typescript
enum Permission {
    None = 0,
    Read = 1 << 0,
    Write = 1 << 1,
    Execute = 1 << 2,
}

const perm = Permission.Read | Permission.Write;
if (perm & Permission.Read) { /* ... */ }
```

TypeScript 타입 시스템은 비트 연산 결과를 정확히 추적하지 못한다. `Permission.Read | Permission.Write`의 결과 타입이 `Permission`으로 좁혀지는데 실제로는 정의되지 않은 3이라는 값이다. 권한 시스템은 `Set<string>`이나 `readonly string[]`로 표현하는 편이 타입 안전성과 가독성 둘 다 유리하다.

```typescript
type Permission = 'read' | 'write' | 'execute';

function hasPermission(perms: ReadonlySet<Permission>, required: Permission) {
    return perms.has(required);
}
```

디스크 용량 절감이 목적인 시스템이 아니면 비트 플래그를 쓸 이유가 별로 없다.

## 참고

- TypeScript Handbook — Enums: https://www.typescriptlang.org/docs/handbook/enums.html
- tsconfig `isolatedModules` 관련: https://www.typescriptlang.org/tsconfig#isolatedModules
- `preserveConstEnums`: https://www.typescriptlang.org/tsconfig#preserveConstEnums
