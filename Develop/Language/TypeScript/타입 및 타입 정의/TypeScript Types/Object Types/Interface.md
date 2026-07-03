---
title: TypeScript Interface
tags: [language, typescript, 타입-및-타입-정의, typescript-types, object-types, interface]
updated: 2026-06-05
---

# TypeScript Interface

`interface`는 객체의 모양(shape)을 이름 붙여 두는 도구다. 백엔드 코드에서 매일 쓰게 되는 자리는 보통 정해져 있다. DTO 정의, 엔티티의 컬럼 타입, 외부 API 응답 모양, 그리고 서비스 클래스가 따라야 할 계약. 이 문서는 그 네 가지를 기준으로 기본 문법만 정리한다. 선언 병합, 모듈 보강, 인덱스/호출/생성자 시그니처, variance 같은 심화 주제는 [Interface_Deep_Dive.md](Interface_Deep_Dive.md)에 따로 정리해 두었다.

---

## 1. 기본 정의

`interface` 키워드 뒤에 이름을 적고 중괄호 안에 속성과 메서드 시그니처를 나열한다. 클래스가 아니라 컴파일 타임에만 존재하는 타입 정의라서 런타임 코드로는 한 줄도 남지 않는다.

```typescript
interface Product {
  id: number;
  name: string;
  priceKrw: number;
  inStock: boolean;
}

const sample: Product = {
  id: 1001,
  name: "기계식 키보드",
  priceKrw: 159000,
  inStock: true,
};
```

객체 리터럴을 변수에 직접 할당하면 TypeScript는 잉여 속성(excess property) 검사를 한다. interface에 없는 키를 같이 넣으면 컴파일 에러가 난다. 다만 한 번 변수로 받아서 넘기면 그 검사를 건너뛴다. 이 차이 때문에 의도치 않은 동작을 보게 되는 경우가 있다.

```typescript
function save(p: Product) {}

save({ id: 1, name: "x", priceKrw: 100, inStock: true, vendor: "a" });
// Error: Object literal may only specify known properties

const obj = { id: 1, name: "x", priceKrw: 100, inStock: true, vendor: "a" };
save(obj); // OK. 잉여 속성 검사가 꺼진다.
```

---

## 2. 선택적 속성과 readonly

물음표(`?`)를 붙이면 해당 속성은 없어도 된다. `readonly`를 붙이면 처음 할당한 뒤로는 재할당이 막힌다. 둘 다 컴파일러 수준 약속이라서 `Object.freeze`처럼 런타임을 막아주지는 않는다.

```typescript
interface UpdateUserDto {
  readonly id: number;
  nickname?: string;
  email?: string;
  phone?: string;
}

function update(dto: UpdateUserDto) {
  // dto.id = 2;  Error: readonly
  if (dto.nickname !== undefined) {
    // 부분 업데이트
  }
}
```

DTO에서 PATCH 요청을 받는 자리에 자주 쓰는 형태다. PK는 readonly로 못박고, 본문에서 보내올지 안 보내올지 모르는 필드는 optional로 둔다. 주의할 점이 하나 있다. `name?: string`은 `string | undefined`와 호환되는 것 같지만 미묘하게 다르다. `?`는 키 자체가 빠져도 통과시키고, `string | undefined`는 키가 반드시 있어야 하고 값만 `undefined`일 수 있다. `exactOptionalPropertyTypes` 옵션을 켜 두면 이 차이가 컴파일러 단에서 드러난다.

```typescript
interface A { name?: string }
interface B { name: string | undefined }

const a: A = {};           // OK
const b: B = {};           // Error: name 누락
const b2: B = { name: undefined }; // OK
```

---

## 3. extends — interface 상속

`extends`로 다른 interface의 속성을 그대로 받아온다. 다중 상속도 된다. 클래스 상속과 달리 인터페이스 상속은 단순한 멤버 합집합이라 같은 이름 속성이 충돌하면 컴파일 에러가 난다.

```typescript
interface Timestamped {
  createdAt: Date;
  updatedAt: Date;
}

interface SoftDeletable {
  deletedAt: Date | null;
}

interface UserEntity extends Timestamped, SoftDeletable {
  id: number;
  email: string;
  passwordHash: string;
}
```

TypeORM이나 Prisma로 작업하다 보면 `createdAt`/`updatedAt`/`deletedAt` 같은 공통 컬럼이 거의 모든 테이블에 등장한다. 위처럼 베이스 interface로 빼 두면 엔티티마다 같은 필드를 다시 적지 않아도 된다.

상속한 멤버의 타입을 좁히는 것도 허용된다. 단, 호환되는 방향으로만 좁힐 수 있다. 부모가 `string | number`이면 자식에서 `string`으로 좁힐 수 있지만, 부모가 `string`인데 자식에서 `number`로 바꾸면 에러다.

```typescript
interface Notification {
  channel: "email" | "sms" | "push";
  payload: object;
}

interface EmailNotification extends Notification {
  channel: "email";              // 좁히기 OK
  payload: { subject: string; body: string };
}
```

---

## 4. implements — 클래스가 따르는 계약

`implements`는 클래스가 특정 interface의 모양을 만족함을 컴파일러에게 알린다. NestJS의 서비스/리포지토리 자리에서 자주 보인다. 추상 클래스를 굳이 만들지 않아도 "이런 메서드를 가진다"는 약속을 강제할 수 있다.

```typescript
interface PaymentGateway {
  charge(amount: number, idempotencyKey: string): Promise<{ id: string }>;
  refund(chargeId: string): Promise<void>;
}

class TossPayments implements PaymentGateway {
  constructor(private readonly secretKey: string) {}

  async charge(amount: number, idempotencyKey: string) {
    const res = await fetch("https://api.tosspayments.com/v1/payments", {
      method: "POST",
      headers: {
        Authorization: `Basic ${Buffer.from(this.secretKey + ":").toString("base64")}`,
        "Idempotency-Key": idempotencyKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ amount }),
    });
    const json = (await res.json()) as { paymentKey: string };
    return { id: json.paymentKey };
  }

  async refund(chargeId: string) {
    await fetch(`https://api.tosspayments.com/v1/payments/${chargeId}/cancel`, {
      method: "POST",
      headers: {
        Authorization: `Basic ${Buffer.from(this.secretKey + ":").toString("base64")}`,
      },
    });
  }
}
```

`implements`는 단지 모양 검사만 한다. 클래스가 interface보다 더 많은 public 멤버를 가져도 상관없다. 대신 시그니처가 어긋나면 그 자리에서 에러가 난다. 결제 게이트웨이를 토스에서 포트원으로 바꿀 때, 같은 interface를 implements 하도록 강제해 두면 호출부 코드를 건드릴 필요가 없어진다. DI 컨테이너에 어느 구현을 주입하느냐만 바꾸면 된다.

다중 implements도 된다. 한 클래스가 여러 계약을 동시에 만족해야 할 때 쓴다.

```typescript
interface Cacheable {
  cacheKey(): string;
}

interface Serializable {
  toJSON(): object;
}

class Article implements Cacheable, Serializable {
  constructor(private readonly id: number, private readonly title: string) {}

  cacheKey() {
    return `article:${this.id}`;
  }

  toJSON() {
    return { id: this.id, title: this.title };
  }
}
```

---

## 5. 실무에서 자주 쓰는 모양

### NestJS 컨트롤러 DTO

class-validator를 안 쓰고 단순 타입만 잡고 싶을 때 interface로 본문 모양을 정의한다. 검증이 필요한 자리는 `class`로 바꿔야 데코레이터가 붙는다는 점만 기억하면 된다.

```typescript
interface CreateOrderDto {
  userId: number;
  items: Array<{
    productId: number;
    quantity: number;
  }>;
  couponCode?: string;
}

@Controller("orders")
class OrderController {
  constructor(private readonly orderService: OrderService) {}

  @Post()
  create(@Body() dto: CreateOrderDto) {
    return this.orderService.create(dto);
  }
}
```

### TypeORM 엔티티의 생성자 인자 타입

엔티티 클래스 자체는 데코레이터 때문에 `class`로 만들지만, 팩토리 함수의 인자 모양을 interface로 따로 두면 테스트할 때 편하다.

```typescript
interface UserProps {
  email: string;
  passwordHash: string;
  nickname: string;
  emailVerifiedAt?: Date;
}

@Entity()
class User {
  @PrimaryGeneratedColumn() id!: number;
  @Column({ unique: true }) email!: string;
  @Column() passwordHash!: string;
  @Column() nickname!: string;
  @Column({ nullable: true }) emailVerifiedAt?: Date;

  static create(props: UserProps): User {
    const u = new User();
    u.email = props.email;
    u.passwordHash = props.passwordHash;
    u.nickname = props.nickname;
    u.emailVerifiedAt = props.emailVerifiedAt;
    return u;
  }
}
```

### 외부 API 응답 모양

서드파티 API를 호출해서 받은 JSON을 그대로 다루지 않고, 응답 모양을 interface로 박아 두는 편이 안전하다. 응답에 새 필드가 추가돼도 기존 코드는 영향을 받지 않고, 필요한 필드만 골라 쓰게 된다.

```typescript
interface GithubUserResponse {
  id: number;
  login: string;
  avatar_url: string;
  name: string | null;
  company: string | null;
  email: string | null;
  public_repos: number;
  followers: number;
  created_at: string;
}

async function fetchGithubUser(login: string): Promise<GithubUserResponse> {
  const res = await fetch(`https://api.github.com/users/${login}`);
  if (!res.ok) throw new Error(`GitHub API ${res.status}`);
  return (await res.json()) as GithubUserResponse;
}
```

`as` 단언이 부담스러우면 zod 같은 런타임 검증 라이브러리로 한 번 더 검사한다. 다만 검증 비용을 항상 치를 필요는 없다. 외부에서 들어오는 자료의 첫 진입점 한 곳에서만 검증하고, 그 뒤로는 interface로 흘려보내는 패턴을 자주 쓴다.

### 페이지네이션 응답 같은 제네릭 모양

목록 API 응답은 거의 같은 모양이라 제네릭 interface로 한 번만 만들어 둔다.

```typescript
interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

interface OrderSummary {
  id: number;
  userId: number;
  totalKrw: number;
  status: "pending" | "paid" | "shipped" | "cancelled";
}

async function listOrders(page: number): Promise<Page<OrderSummary>> {
  const res = await fetch(`/api/orders?page=${page}`);
  return (await res.json()) as Page<OrderSummary>;
}
```

---

## 6. interface와 type alias, 어느 쪽을 쓸까

문법으로 가능한 자리는 거의 겹친다. 실무에서 갈리는 기준은 단순하다.

- 객체/클래스의 모양을 묘사하고, 나중에 같은 이름으로 멤버를 더할 가능성이 있다면 `interface`.
- 유니온/교차/조건부 타입, 튜플, 매핑 타입처럼 객체 모양을 벗어나는 정의라면 `type`.
- 라이브러리 사용자에게 모양을 노출할 때는 `interface`. 외부에서 선언 병합으로 확장할 여지를 남길 수 있다.

비교는 다음과 같다.

| 항목 | interface | type alias |
|---|---|---|
| 객체 모양 정의 | 가능 | 가능 |
| 확장 방식 | `extends` | `&` (교차 타입) |
| 동일 이름 재선언 | 멤버가 병합됨 | 중복 식별자 에러 |
| 유니온 타입 정의 | 직접 불가 | 가능 |
| 튜플·매핑·조건부 타입 | 불가 | 가능 |
| 외부 코드의 보강 | `declare module`로 가능 | 불가 |

성능 면에서는 큰 차이가 없지만, 매우 복잡한 교차 타입을 type alias로 누적하면 컴파일러가 풀어내야 할 일이 많아져서 IDE 응답이 느려질 때가 있다. 한 모양에 이름을 붙이는 거라면 interface가 무난하다.

---

## 7. 자주 마주치는 실수

- **메서드 시그니처와 메서드 프로퍼티의 차이**: `do(x: A): void` 형태와 `do: (x: A) => void` 형태는 비슷해 보이지만 variance가 다르다. 후자는 strict function types 옵션 아래에서 인자의 반공변 검사가 엄격해진다. 라이브러리를 만든다면 메서드 시그니처 형태로 적는 편이 사용자 코드를 덜 깨뜨린다.
- **클래스 implements + private 필드**: `private` 필드는 interface로 표현할 수 없다. `implements`로는 public 모양만 강제된다. private까지 강제하고 싶으면 추상 클래스를 쓴다.
- **JSON.parse 결과를 곧바로 interface로 단언**: 타입 시스템이 진실이라고 믿어 버리니, 외부 입력은 최소 한 번 검증한다.
- **`{}` 빈 interface**: TypeScript에서 `{}`는 "null/undefined가 아닌 모든 값"을 뜻한다. 의도와 다르게 동작하므로 빈 interface로 가드를 시도하지 않는다.

---

## 참고

- [TypeScript Interface 심화 (선언 병합·모듈 보강·시그니처)](Interface_Deep_Dive.md)
- [고급 타입 기법](../../고급%20타입%20기법.md)
