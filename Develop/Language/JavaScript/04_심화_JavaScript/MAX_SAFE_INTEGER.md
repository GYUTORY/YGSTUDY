---
title: MAX_SAFE_INTEGER
tags: [javascript, Number, IEEE754, BigInt, 정밀도, prisma, typeorm]
updated: 2026-07-29
---

# Number.MAX_SAFE_INTEGER

`Number.MAX_SAFE_INTEGER`는 2^53 - 1, 즉 9007199254740991이다. JavaScript에서 정수를 안전하게 표현할 수 있는 최댓값이다. 이 값을 넘어서면 정수 연산 결과를 보장할 수 없다.

## IEEE 754 double에서 53비트 한계가 생기는 이유

JavaScript의 `Number`는 IEEE 754 배정밀도 부동소수점을 따른다. 64비트 구성은 아래와 같다.

- 부호: 1비트
- 지수: 11비트
- 가수(mantissa/significand): 52비트

가수부 52비트에 암묵적으로 선행하는 1비트(hidden bit)가 더해져 사실상 53비트의 정수 정밀도를 갖는다. 이 hidden bit는 정규화된 부동소수점 수에서 항상 1이기 때문에 저장하지 않고 암묵적으로 붙는다.

2^53 이하의 정수는 가수부 53비트에 정확하게 표현된다. 2^53을 넘어서면 두 개의 연속된 부동소수점 수 사이 간격이 1보다 커지면서 모든 정수를 표현할 수 없게 된다.

```javascript
2 ** 53      // 9007199254740992
2 ** 53 + 1  // 9007199254740992  — 같은 값이 나옴
2 ** 53 + 2  // 9007199254740994
```

2^53과 2^54 사이에서 표현 가능한 수는 짝수뿐이다. 2^54와 2^55 사이에서는 4의 배수만 표현된다. 가수부 비트 수가 고정되어 있기 때문에 지수가 커질수록 정수 간격이 넓어진다.

## 실무에서 정밀도 손실이 발생하는 패턴

### DB BIGINT

PostgreSQL, MySQL의 BIGINT는 64비트 부호 정수다. 최대값이 9223372036854775807(2^63 - 1)로 MAX_SAFE_INTEGER보다 훨씬 크다. ORM이나 raw query로 BIGINT 컬럼을 읽어서 JSON으로 내려줄 때 손실이 생긴다.

pg 라이브러리는 BIGINT를 기본적으로 문자열로 반환한다. 이걸 Number로 파싱하면 정밀도가 날아간다.

```javascript
const result = await client.query('SELECT id FROM users WHERE id = 9007199254740993');
console.log(result.rows[0].id); // "9007199254740993" — pg는 BIGINT를 문자열로 반환

const id = Number(result.rows[0].id); // 9007199254740992 — 이미 손상됨
```

#### Prisma

Prisma schema에서 BigInt 컬럼을 선언하면 JavaScript `bigint` 타입으로 매핑된다.

```prisma
model User {
  id   BigInt @id @default(autoincrement())
  name String
}
```

쿼리 결과의 `id`는 `bigint` 타입이다. `res.json(user)`를 바로 호출하면 `TypeError: Do not know how to serialize a BigInt`가 발생한다. Express, Fastify, NestJS 모두 내부적으로 `JSON.stringify`를 쓰기 때문이다.

```typescript
// 문제 상황
const user = await prisma.user.findUnique({ where: { id: 1n } });
res.json(user); // TypeError 발생

// 해결 1: replacer로 일괄 변환
const serialized = JSON.stringify(user, (_, v) =>
  typeof v === 'bigint' ? v.toString() : v
);
res.setHeader('Content-Type', 'application/json').send(serialized);
```

매번 replacer를 붙이기 번거롭다면 Prisma Client Extensions(v5+)로 쿼리 결과에서 BigInt를 string으로 변환하는 방법이 있다.

```typescript
const prisma = new PrismaClient().$extends({
  result: {
    user: {
      id: {
        needs: { id: true },
        compute(user) {
          return user.id.toString();
        },
      },
    },
  },
});

// where 절은 여전히 bigint를 받음
const user = await prisma.user.findUnique({ where: { id: 1n } });
console.log(typeof user?.id); // "string" — 결과는 string으로 변환됨
```

v4 이하에서는 `$use` 미들웨어로 처리했지만 v5에서 deprecated됐다. `$extends` result 방식이 현재 권장 방법이다.

NestJS에서는 전역 interceptor나 `FastifyInstance`의 `addContentTypeParser`로 직렬화 처리를 한 곳에 모아두는 편이 낫다. 컨트롤러마다 replacer를 붙이면 누락이 생긴다.

#### TypeORM

TypeORM에서 `@Column('bigint')`은 컬럼 값을 string으로 반환한다. mysql2 드라이버가 BIGINT를 string으로 전달하기 때문이다.

```typescript
@Entity()
class User {
  @PrimaryGeneratedColumn('increment', { type: 'bigint' })
  id: string; // bigint 컬럼은 string으로 반환

  @Column({ type: 'bigint' })
  score: string;
}

const user = await userRepository.findOne({ where: { id: '9007199254740993' } });
console.log(typeof user.id); // "string"
```

흔한 실수는 엔티티 프로퍼티를 `number`로 선언하는 것이다. TypeScript 타입을 `number`로 써도 런타임 값은 string으로 오기 때문에 타입과 실제 값이 어긋난다. BigInt 연산이 필요한 경우 `BigInt(user.id)`로 변환해서 쓴다.

PostgreSQL은 드라이버 동작이 다르다. `pg` 라이브러리는 BIGINT를 string으로 주지만 TypeORM이 엔티티 타입에 맞게 변환을 시도한다. 컬럼 타입을 `bigint`로 선언하면 string이 유지되고, `number`로 선언하면 Number 변환을 시도해서 손실이 생긴다.

### Snowflake ID

트위터가 개발한 Snowflake ID는 64비트 정수다. 타임스탬프(41비트) + 워커 ID(10비트) + 시퀀스(12비트)로 구성된다. 현재 발급되는 Snowflake ID는 이미 2^53을 넘었다.

트위터 API v1에서 실제로 이 문제가 발생했다. JSON 응답에서 tweet id가 숫자로 내려오면 JavaScript 클라이언트가 파싱할 때 손실이 생겨서, 트위터는 `id`와 `id_str` 두 필드를 동시에 내려줬다.

```json
{
  "id": 1234567890123456789,
  "id_str": "1234567890123456789"
}
```

`response.id`를 쓰면 값이 다를 수 있다. JavaScript 클라이언트는 반드시 `id_str`을 써야 한다.

### 타임스탬프 나노초

Unix 타임스탬프를 나노초 단위로 표현하면 2^53을 넘는다. 현재 시각의 나노초 타임스탬프는 약 1.7 × 10^18 수준이다.

```javascript
const nanoTs = 1706789012345678901; // JSON.parse 후 이미 손상
```

밀리초(13자리)는 안전하고, 마이크로초(16자리)는 일부 값에서 손실이 생기기 시작하며, 나노초(19자리)는 거의 항상 손실된다. gRPC나 protobuf로 타임스탬프를 받을 때 나노초 필드를 Number로 파싱하는 실수가 자주 나온다.

### API 응답의 큰 정수

외부 API(결제, 물류, 금융 도메인)에서 고유 ID나 금액을 큰 정수로 내려주는 경우가 있다. `JSON.parse`는 숫자 필드를 Number로 파싱하기 때문에 파싱 시점에 이미 손실이 생긴다.

```javascript
const data = JSON.parse('{"amount": 9007199254740993}');
console.log(data.amount); // 9007199254740992
console.log(data.amount === 9007199254740993); // false
```

응답 스펙을 보면 숫자처럼 생겼는데 실제로는 손실이 생겨 있는 상태다. 겉으로는 드러나지 않기 때문에 데이터 정합성 문제로 한참 지나서 발견된다.

## json-bigint 라이브러리

`JSON.parse`의 정밀도 손실 문제는 파서 자체를 교체해서 해결한다. `json-bigint` 라이브러리는 JavaScript 숫자 범위를 벗어나는 정수를 `bigint` 또는 string으로 파싱한다.

```bash
npm install json-bigint
```

```javascript
const JSONbig = require('json-bigint');

const raw = '{"id": 9007199254740993, "name": "Alice"}';

// 기본 JSON.parse
const parsed = JSON.parse(raw);
console.log(parsed.id); // 9007199254740992 — 손실

// json-bigint
const parsed2 = JSONbig.parse(raw);
console.log(parsed2.id);        // 9007199254740993n
console.log(typeof parsed2.id); // "bigint"

// 직렬화도 지원
const str = JSONbig.stringify(parsed2);
console.log(str); // '{"id":9007199254740993,"name":"Alice"}'
```

`storeAsString` 옵션을 주면 BigInt 대신 string으로 저장한다. DB에 저장하거나 API 응답으로 다시 내려줄 때 변환 단계가 줄어서 실무에서 더 자주 쓰는 방식이다.

```javascript
const JSONbig = require('json-bigint')({ storeAsString: true });

const parsed = JSONbig.parse('{"id": 9007199254740993}');
console.log(parsed.id);        // "9007199254740993"
console.log(typeof parsed.id); // "string"
```

axios로 외부 API를 호출할 때 `transformResponse`에 적용하면 응답 전체에 일괄 적용된다.

```javascript
const JSONbig = require('json-bigint')({ storeAsString: true });

const instance = axios.create({
  transformResponse: [data => JSONbig.parse(data)],
});

const res = await instance.get('/api/payment/123');
console.log(res.data.transactionId); // 손실 없는 string
```

fetch API는 `response.json()` 대신 `response.text()`로 raw 문자열을 받아서 `JSONbig.parse()`를 직접 호출한다.

## 손실 여부 확인과 디버깅

특정 숫자가 안전 범위 안에 있는지 확인한다.

```javascript
Number.isSafeInteger(9007199254740991);  // true
Number.isSafeInteger(9007199254740992);  // false

const value = 9007199254740993;
value > Number.MAX_SAFE_INTEGER; // true — 손실 가능 범위
```

손실된 값에서 원래 값을 복원할 수 없다. 이미 손상된 Number에 역산을 해봐야 원본을 알 수 없기 때문에, 데이터가 어디서 손상됐는지 추적하는 게 먼저다.

디버깅할 때 콘솔에 숫자를 찍으면 이미 손상된 값이 나온다. 원본 데이터가 문자열로 넘어오는지 먼저 확인해야 한다. `res.json()` 대신 `res.text()`로 raw 응답을 먼저 확인한다.

```javascript
// 잘못된 디버깅
const res = await fetch('/api/user/1234567890123456789');
const data = await res.json(); // 이 시점에 이미 손실
console.log(data.id);          // 손상된 값

// 올바른 디버깅
const res = await fetch('/api/user/1234567890123456789');
const text = await res.text(); // 먼저 텍스트로 읽음
console.log(text);             // 원본 JSON 문자열 확인
const data = JSON.parse(text);
```

## TypeScript에서 bigint 타입

TypeScript는 `bigint` 타입을 기본 지원한다. `tsconfig.json`의 `target`이 `ES2020` 이상이어야 하고, `ES2019` 이하로 설정하면 컴파일 에러가 난다.

```json
{
  "compilerOptions": {
    "target": "ES2020"
  }
}
```

```typescript
const id: bigint = 9007199254740993n;
const doubled: bigint = id * 2n;

// Number와 혼합 연산 불가 — 컴파일 에러
const wrong = id + 1;  // error: Operator '+' cannot be applied to types 'bigint' and 'number'
const right = id + 1n; // 정상

// 변환
const asString: string = id.toString();
const asNumber: number = Number(id); // MAX_SAFE_INTEGER 초과 시 손실
const fromString: bigint = BigInt('9007199254740993');
const fromNumber: bigint = BigInt(42); // 안전 범위 정수에서만 사용
```

API 경계에서는 `string`, 내부 비즈니스 로직에서는 `bigint`를 쓰는 패턴이 관리하기 편하다.

```typescript
// HTTP 응답 DTO — string으로 직렬화
interface UserResponse {
  id: string;
  name: string;
}

// 내부 도메인 모델 — bigint 그대로
interface UserEntity {
  id: bigint;
  name: string;
}

function toResponse(entity: UserEntity): UserResponse {
  return {
    id: entity.id.toString(),
    name: entity.name,
  };
}
```

NestJS에서 class-transformer와 `bigint`를 함께 쓸 때 주의가 필요하다. HTTP body로 받은 값은 항상 string이기 때문에 `@Transform`으로 명시적 변환을 해야 한다.

```typescript
import { Transform } from 'class-transformer';
import { IsString } from 'class-validator';

class CreateItemDto {
  @Transform(({ value }) => BigInt(value))
  ownerId: bigint;
}
```

`class-validator`의 `@IsString()`, `@IsNumber()` 같은 데코레이터는 `bigint`를 인식하지 못한다. validation 전에 변환하면 검증 자체가 꼬이기 때문에, DTO 레벨에서는 string으로 받고 서비스 레이어에서 `BigInt()`로 변환하는 방식이 더 안전하다.

## BigInt 전환 시 주의사항

`BigInt`는 임의 정밀도 정수를 표현한다. MAX_SAFE_INTEGER 범위를 넘는 정수 연산이 필요하면 BigInt를 써야 한다.

```javascript
const big = BigInt("9007199254740993");
const result = big + 1n; // 9007199254740994n
```

### JSON 직렬화 예외

BigInt는 `JSON.stringify`에서 예외를 던진다.

```javascript
JSON.stringify({ id: 9007199254740993n });
// TypeError: Do not know how to serialize a BigInt
```

API 응답에 BigInt를 그대로 담으면 직렬화 단계에서 서버가 500을 반환한다. BigInt를 내려줄 때는 문자열로 변환해야 한다.

```javascript
JSON.stringify({ id: 9007199254740993n.toString() }); // {"id":"9007199254740993"}

// replacer 함수로 일괄 처리
JSON.stringify(data, (key, value) =>
  typeof value === 'bigint' ? value.toString() : value
);
```

Express나 Fastify에서 BigInt가 포함된 객체를 `res.json()`으로 내리려 할 때도 같은 에러가 난다. 별도 직렬화 처리가 필요하다.

### 비트 연산자 32비트 제한

JavaScript의 비트 연산자(`&`, `|`, `^`, `~`, `<<`, `>>`, `>>>`)는 피연산자를 32비트 정수로 변환한 뒤 연산한다. 32비트를 넘는 값에 비트 연산을 적용하면 상위 비트가 잘린다.

```javascript
const id = 9007199254740993;
id & 0xFF; // 상위 비트 잘림, 의도하지 않은 값

// BigInt의 비트 연산은 제대로 동작함
const bigId = 9007199254740993n;
bigId & 0xFFn; // 올바른 하위 8비트
```

Snowflake ID에서 타임스탬프나 워커 ID를 비트 마스킹으로 추출할 때 Number 대신 BigInt를 써야 한다. Number로 비트 연산을 하면 32비트 이상의 정보가 소실된다.

```javascript
// Snowflake ID에서 타임스탬프 추출
const snowflake = 1234567890123456789n;
const EPOCH = 1420070400000n;
const timestamp = (snowflake >> 22n) + EPOCH;
```

## 백엔드가 ID를 문자열로 내려야 하는 이유

API를 설계할 때 BIGINT 식별자를 숫자 타입 JSON 필드로 내리는 건 클라이언트에게 손실 가능성을 전가하는 것이다. JavaScript 클라이언트가 아니더라도 Python, Go의 기본 JSON 파서가 큰 정수를 float64로 파싱하면 같은 문제가 생긴다.

문자열로 내리면 모든 클라이언트에서 정밀도 손실 없이 원본 값을 유지한다.

```json
// 숫자로 내릴 때
{"id": 9007199254740993}   // JavaScript에서 9007199254740992로 파싱됨

// 문자열로 내릴 때
{"id": "9007199254740993"} // 모든 클라이언트에서 원본 유지
```

ID 필드 타입을 바꾸는 일은 API 버전 변경이 필요한 breaking change다. 처음 설계할 때부터 문자열로 내리는 게 낫다. 기존 API에서 숫자로 내리고 있었다면 트위터처럼 `id`와 `id_str` 두 필드를 병행 제공하는 방법으로 마이그레이션한다.

금액처럼 연산이 필요한 값도 마찬가지다. 클라이언트에서 금액 연산을 할 필요가 없으면 문자열로 내리고, 연산이 필요하면 Decimal 라이브러리를 쓰도록 안내한다. 서버에서 최소 단위(센트, 원)로 정수 변환 후 내리는 방법도 있다.
