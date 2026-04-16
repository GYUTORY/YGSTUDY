---
title: NestJS TypeORM 연동
tags: [nestjs, typeorm, database, orm, repository, migration]
updated: 2026-04-16
---

## 들어가며

NestJS에서 데이터베이스 연동은 대부분 TypeORM 또는 Prisma 둘 중 하나로 귀결된다. 기존 자바 Spring 진영에서 넘어온 개발자라면 TypeORM이 JPA/Hibernate와 유사한 구조라 친숙하고, `@nestjs/typeorm` 패키지가 공식으로 제공되어 모듈 시스템과 궁합이 좋다. 그런데 막상 실무에서 써보면 공식 문서대로만 작성했다가 Connection Pool이 말라서 서비스가 멈추거나, Eager Loading 설정 하나 잘못해서 N+1이 폭발하는 일이 자주 생긴다.

이 문서는 TypeORM을 NestJS에 붙이는 방법부터 실제 운영하면서 마주친 문제들을 정리한다. 단순히 "이렇게 쓰면 된다"가 아니라 "왜 이렇게 써야 하고, 이렇게 안 쓰면 어떤 지뢰를 밟는지"에 초점을 맞췄다.

## TypeORM Module 구성

### 기본 연결

`TypeOrmModule.forRoot()`는 애플리케이션 전체에서 공유되는 DataSource를 등록한다. 루트 모듈에 한 번만 등록하면 되고, 여러 번 호출하면 이름 기반으로 다중 DataSource를 운영할 수 있다.

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ConfigModule, ConfigService } from '@nestjs/config';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    TypeOrmModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        type: 'postgres',
        host: config.get('DB_HOST'),
        port: config.get<number>('DB_PORT'),
        username: config.get('DB_USER'),
        password: config.get('DB_PASSWORD'),
        database: config.get('DB_NAME'),
        entities: [__dirname + '/**/*.entity{.ts,.js}'],
        synchronize: false,
        logging: config.get('NODE_ENV') === 'development',
        extra: {
          max: 20,
          connectionTimeoutMillis: 3000,
          idleTimeoutMillis: 30000,
        },
      }),
    }),
  ],
})
export class AppModule {}
```

`forRoot`와 `forRootAsync`의 차이가 애매한데, 실무에서는 항상 `forRootAsync`를 쓰는 게 맞다. 환경변수를 읽어야 하기 때문이다. 단순히 하드코딩된 값으로 붙이는 경우는 실제로 거의 없다.

`synchronize: true`는 엔티티 정의가 바뀌면 자동으로 DB 스키마를 맞춰준다. 이걸 프로덕션에서 켜두면 어느 날 누군가 엔티티에서 컬럼을 지웠을 때 실제 DB 컬럼이 같이 날아간다. 로컬 개발에서만 쓰고 운영에서는 반드시 Migration으로 관리해야 한다.

### Feature Module 단위 Repository 등록

각 도메인 모듈에서는 `TypeOrmModule.forFeature()`로 해당 모듈이 사용할 엔티티를 등록한다. 이건 Repository 주입을 위한 것이고, DataSource 연결 자체는 루트에서 이미 끝난 상태다.

```typescript
// user.module.ts
@Module({
  imports: [TypeOrmModule.forFeature([User, UserProfile])],
  providers: [UserService],
  exports: [UserService],
})
export class UserModule {}
```

여기서 자주 하는 실수가 있다. 다른 모듈의 엔티티를 Repository로 쓰고 싶어서 해당 엔티티를 `forFeature`에 또 등록하는 경우인데, 이래도 동작은 한다. 하지만 도메인 경계를 무너뜨리는 코드가 되기 쉬우니, 가급적 Service를 export하고 다른 모듈은 Service를 주입받아 쓰는 게 낫다.

## Repository 패턴

### 기본 사용

Repository는 엔티티 단위로 자동 생성된다. `@InjectRepository()` 데코레이터로 주입받는다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from './user.entity';

@Injectable()
export class UserService {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
  ) {}

  async findById(id: number): Promise<User | null> {
    return this.userRepository.findOne({ where: { id } });
  }

  async create(data: Partial<User>): Promise<User> {
    const user = this.userRepository.create(data);
    return this.userRepository.save(user);
  }
}
```

`create()`와 `save()`의 차이를 헷갈려하는 경우가 많다. `create()`는 단순히 엔티티 인스턴스를 생성만 할 뿐 DB에 저장하지 않는다. `save()`가 실제로 INSERT/UPDATE를 수행한다. 그리고 `save()`는 PK가 있으면 UPDATE, 없으면 INSERT로 동작하는데, 이게 편할 때도 있지만 의도치 않은 UPDATE를 유발하기도 한다. 새로 생성한다는 의도가 명확하면 `insert()`를 쓰는 게 안전하다.

### Custom Repository

복잡한 쿼리를 Service에 다 몰아넣으면 Service가 비대해진다. TypeORM 0.3부터 `@EntityRepository`가 deprecated되어서 이제는 Repository를 확장해서 사용한다.

```typescript
import { DataSource, Repository } from 'typeorm';
import { Injectable } from '@nestjs/common';
import { User } from './user.entity';

@Injectable()
export class UserRepository extends Repository<User> {
  constructor(private readonly dataSource: DataSource) {
    super(User, dataSource.createEntityManager());
  }

  async findActiveByEmail(email: string): Promise<User | null> {
    return this.createQueryBuilder('user')
      .where('user.email = :email', { email })
      .andWhere('user.deletedAt IS NULL')
      .getOne();
  }
}
```

이렇게 만든 Custom Repository는 모듈의 `providers`에 등록해서 주입받는다. `@InjectRepository`가 아니라 일반 Provider로 다룬다는 점이 핵심이다.

## Entity 관계 매핑

### 관계 정의

TypeORM의 관계 데코레이터는 네 종류다. `@OneToOne`, `@OneToMany`, `@ManyToOne`, `@ManyToMany`. 이 중 `@OneToMany`는 혼자서는 외래키를 만들지 못한다. 반대편에 반드시 `@ManyToOne`이 있어야 한다.

```typescript
@Entity('users')
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ unique: true })
  email: string;

  @OneToOne(() => UserProfile, (profile) => profile.user, { cascade: true })
  profile: UserProfile;

  @OneToMany(() => Order, (order) => order.user)
  orders: Order[];
}

@Entity('orders')
export class Order {
  @PrimaryGeneratedColumn()
  id: number;

  @ManyToOne(() => User, (user) => user.orders, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'user_id' })
  user: User;
}
```

`@JoinColumn`은 외래키를 가지는 쪽에만 붙인다. `@OneToOne`은 둘 다 외래키를 가질 수 있기 때문에 명시적으로 `@JoinColumn`을 붙인 쪽이 FK를 보유한다.

### Eager vs Lazy Loading

```typescript
@OneToMany(() => Order, (order) => order.user, { eager: true })
orders: Order[];
```

`eager: true`로 설정하면 User를 조회할 때마다 자동으로 Order를 JOIN해서 가져온다. 처음에는 편해 보이지만 이게 전체 서비스에 퍼지면 User 하나만 조회해도 관련 테이블이 전부 딸려 나온다. User 목록 100건 조회하는 API가 JOIN 5개짜리 괴물 쿼리가 되는 건 순식간이다.

실무에서는 대부분의 관계를 Lazy로 두고, 필요한 경우에만 `relations` 옵션이나 QueryBuilder로 명시적으로 로딩한다.

```typescript
await this.userRepository.find({
  relations: { orders: true, profile: true },
});
```

## QueryBuilder 사용

Repository API만으로는 풀어내기 어려운 쿼리가 많다. 서브쿼리, 복잡한 JOIN 조건, 집계 함수, 윈도우 함수 같은 것들이다. 이럴 때 QueryBuilder를 쓴다.

```typescript
async findTopSpenders(limit: number): Promise<Array<{ userId: number; total: number }>> {
  return this.orderRepository
    .createQueryBuilder('order')
    .select('order.user_id', 'userId')
    .addSelect('SUM(order.amount)', 'total')
    .where('order.status = :status', { status: 'COMPLETED' })
    .andWhere('order.created_at >= :from', { from: new Date('2026-01-01') })
    .groupBy('order.user_id')
    .orderBy('total', 'DESC')
    .limit(limit)
    .getRawMany();
}
```

`getMany()`, `getOne()`은 엔티티 인스턴스로 변환해서 반환하고, `getRawMany()`, `getRawOne()`은 가공 없이 row 그대로 반환한다. 집계 쿼리는 엔티티로 매핑되지 않으니 `getRawMany()`를 써야 한다. `getManyAndCount()`는 페이지네이션 구현 시 전체 개수를 함께 가져올 때 쓰는데, 내부적으로 쿼리를 두 번 실행한다는 점을 기억해야 한다.

### JOIN 시 주의사항

`leftJoinAndSelect`와 `leftJoin`의 차이를 모르고 쓰다가 관계 데이터가 안 나온다고 헤매는 경우가 많다. `leftJoinAndSelect`는 JOIN과 함께 SELECT 대상에 포함시키는 것이고, `leftJoin`은 JOIN만 걸고 조건에만 쓴다는 의미다.

```typescript
// 잘못된 사용: Orders는 조회되지 않는다
await this.userRepository
  .createQueryBuilder('user')
  .leftJoin('user.orders', 'order')
  .where('order.amount > :min', { min: 10000 })
  .getMany();

// Orders도 함께 조회
await this.userRepository
  .createQueryBuilder('user')
  .leftJoinAndSelect('user.orders', 'order')
  .where('order.amount > :min', { min: 10000 })
  .getMany();
```

## 트랜잭션 처리

### QueryRunner 방식

가장 제어가 명확한 방식이다. Connection Pool에서 하나의 Connection을 점유하고 그 안에서 모든 쿼리를 실행한다.

```typescript
import { DataSource } from 'typeorm';

@Injectable()
export class OrderService {
  constructor(private readonly dataSource: DataSource) {}

  async createOrderWithPayment(orderData: CreateOrderDto): Promise<Order> {
    const queryRunner = this.dataSource.createQueryRunner();
    await queryRunner.connect();
    await queryRunner.startTransaction();

    try {
      const order = await queryRunner.manager.save(Order, orderData);
      await queryRunner.manager.save(Payment, {
        orderId: order.id,
        amount: order.amount,
      });
      await queryRunner.manager.decrement(
        Product,
        { id: orderData.productId },
        'stock',
        orderData.quantity,
      );

      await queryRunner.commitTransaction();
      return order;
    } catch (err) {
      await queryRunner.rollbackTransaction();
      throw err;
    } finally {
      await queryRunner.release();
    }
  }
}
```

`release()`를 finally에서 반드시 호출해야 한다. 이걸 빠뜨리면 Connection이 Pool로 돌아가지 않아서 서서히 고갈된다. 운영 환경에서 "갑자기 DB 연결이 안 돼요"라는 장애의 대부분이 이 패턴이다.

### DataSource.transaction() 방식

콜백 기반으로 트랜잭션을 관리한다. QueryRunner를 직접 다루지 않아도 되므로 release 누락 실수를 줄일 수 있다.

```typescript
await this.dataSource.transaction(async (manager) => {
  const order = await manager.save(Order, orderData);
  await manager.save(Payment, { orderId: order.id, amount: order.amount });
  return order;
});
```

격리 수준을 지정하려면 첫 인자로 넘긴다.

```typescript
await this.dataSource.transaction('SERIALIZABLE', async (manager) => {
  // ...
});
```

### 트랜잭션 안에서 Repository를 쓰면 안 되는 이유

초보자가 가장 자주 실수하는 부분이다. 트랜잭션 블록 안에서 외부에서 주입받은 Repository를 그대로 쓰면 해당 쿼리는 트랜잭션 밖에서 실행된다. Repository는 전역 DataSource에 묶여 있기 때문이다.

```typescript
// 트랜잭션 밖에서 실행되는 잘못된 코드
await this.dataSource.transaction(async (manager) => {
  await manager.save(Order, orderData);
  await this.paymentRepository.save(payment);  // 이게 트랜잭션 밖에서 실행됨
});

// 올바른 코드
await this.dataSource.transaction(async (manager) => {
  await manager.save(Order, orderData);
  await manager.save(Payment, payment);
});
```

커밋 전에 롤백이 발생해도 외부 Repository로 저장한 데이터는 그대로 남는다. 부분 저장 상태가 되어서 데이터 정합성이 깨진다.

## N+1 문제

N+1은 TypeORM을 포함한 모든 ORM의 고질병이다. 관계된 엔티티를 반복문에서 각각 접근할 때 발생한다.

```typescript
// 문제 상황
const users = await this.userRepository.find(); // 쿼리 1회
for (const user of users) {
  const orders = await user.orders; // Lazy 관계라면 user 수만큼 쿼리 발생
  console.log(orders.length);
}
```

User가 100명이면 쿼리가 101번 나간다. 로컬에서는 체감이 안 되는데 프로덕션 데이터 양으로 돌리면 응답시간이 수 초 단위로 늘어난다.

해결 방법은 세 가지다.

**첫째, relations 옵션으로 한 번에 가져오기.**

```typescript
const users = await this.userRepository.find({
  relations: { orders: true },
});
```

**둘째, QueryBuilder의 leftJoinAndSelect 사용.** relations 옵션보다 세밀한 조건을 걸 수 있다.

```typescript
await this.userRepository
  .createQueryBuilder('user')
  .leftJoinAndSelect('user.orders', 'order', 'order.status = :status', {
    status: 'COMPLETED',
  })
  .getMany();
```

**셋째, DataLoader 패턴.** GraphQL 환경에서 특히 유용하다. 여러 요청을 배치로 묶어서 한 번에 조회한다.

JOIN 방식은 편하지만 카티션 곱 문제가 생길 수 있다. User 1명이 Order 10개, Item 20개를 가지면 JOIN 결과가 200 row가 된다. 이 경우는 관계별로 쿼리를 분리하는 게 낫다. TypeORM은 `relationLoadStrategy: 'query'` 옵션으로 JOIN 대신 별도 쿼리로 관계를 로딩하는 모드를 지원한다.

## Migration 운영

### Migration 파일 생성

`synchronize: false`로 운영하는 환경에서는 Migration이 필수다. 스키마 변경 이력을 코드로 관리할 수 있고, 여러 환경(dev/staging/prod)에 동일한 변경을 적용할 수 있다.

```typescript
// data-source.ts
import { DataSource } from 'typeorm';
import 'dotenv/config';

export const AppDataSource = new DataSource({
  type: 'postgres',
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT),
  username: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  entities: ['src/**/*.entity.ts'],
  migrations: ['src/migrations/*.ts'],
});
```

package.json에 스크립트를 등록해두고 CLI를 쓴다.

```json
{
  "scripts": {
    "typeorm": "typeorm-ts-node-commonjs -d src/data-source.ts",
    "migration:generate": "npm run typeorm -- migration:generate",
    "migration:run": "npm run typeorm -- migration:run",
    "migration:revert": "npm run typeorm -- migration:revert"
  }
}
```

`migration:generate`는 엔티티와 현재 DB 스키마 차이를 비교해서 Migration을 자동 생성한다. 편하지만 생성된 쿼리를 반드시 검토해야 한다. 컬럼 타입 변경이나 이름 변경 같은 경우 TypeORM이 의도와 다르게 DROP+CREATE로 생성하는 경우가 있는데, 이러면 프로덕션 데이터가 날아간다.

### 운영에서 조심해야 할 것

컬럼 추가는 기본값 없이 NOT NULL로 바로 추가하면 기존 row에 대해 에러가 난다. 단계를 나눠야 한다.

1. NULL 허용으로 컬럼 추가
2. 기존 데이터 백필
3. NOT NULL 제약 추가

대용량 테이블에서 인덱스 추가는 DB를 락 걸 수 있다. PostgreSQL이라면 `CREATE INDEX CONCURRENTLY`, MySQL이라면 `ALGORITHM=INPLACE, LOCK=NONE` 같은 옵션을 Migration 쿼리에 직접 작성해야 한다. TypeORM이 자동 생성한 DDL은 이런 옵션을 붙여주지 않으니 수동으로 수정해야 한다.

Migration은 롤백 스크립트도 반드시 작성한다. `down()` 메서드를 빈 채로 두는 경우를 자주 보는데, 배포 직후 문제가 생겨서 급하게 되돌려야 할 때 없으면 수동으로 복구해야 한다.

## Connection Pool 이슈

### Pool 설정

TypeORM은 내부적으로 node-postgres나 mysql2 같은 드라이버의 Pool을 사용한다. `extra` 옵션으로 Pool 파라미터를 전달한다.

```typescript
{
  extra: {
    max: 20,
    min: 2,
    connectionTimeoutMillis: 3000,
    idleTimeoutMillis: 30000,
    statement_timeout: 5000,
  },
}
```

`max`는 동시에 열 수 있는 Connection 최대 개수다. 흔한 오해가 "클수록 좋다"인데, 실제로는 DB 서버의 max_connections를 고려해야 한다. 인스턴스가 4개인데 각각 max 100으로 설정하면 총 400개의 Connection을 요구한다. PostgreSQL의 기본 max_connections가 100 수준이니 이러면 DB가 터진다.

### Pool 고갈 증상

운영 중 자주 마주치는 증상이다.

- `TimeoutError: ResourceRequest timed out` 에러가 대량 발생
- DB 쿼리가 아닌 Connection을 기다리는 구간에서 느려짐
- APM에서 보면 "DB 쿼리는 빠른데 응답시간이 길다"는 이상한 패턴

원인은 거의 정해져 있다.

**첫 번째, QueryRunner를 release하지 않는 코드.** 위에서 말한 finally 누락이다.

**두 번째, 트랜잭션이 너무 길어지는 경우.** 트랜잭션 안에서 외부 API 호출을 하거나 복잡한 비즈니스 로직을 처리하면 그 시간 동안 Connection이 점유된다. 외부 API가 느려지면 Connection이 다 묶여버린다. 원칙적으로 트랜잭션은 DB 작업만 포함해야 한다.

```typescript
// 좋지 않은 패턴
await this.dataSource.transaction(async (manager) => {
  const order = await manager.save(Order, data);
  await this.paymentGateway.charge(order); // 외부 API 호출
  await manager.save(PaymentLog, { orderId: order.id });
});

// 개선: 외부 호출은 트랜잭션 밖으로
const order = await this.dataSource.transaction(async (manager) => {
  return manager.save(Order, data);
});
const result = await this.paymentGateway.charge(order);
await this.dataSource.transaction(async (manager) => {
  await manager.save(PaymentLog, { orderId: order.id, result });
});
```

**세 번째, Read Replica를 쓰지 않는 경우.** 조회 트래픽이 많은 서비스에서 Master만 바라보면 Pool이 빨리 찬다. TypeORM은 `replication` 옵션으로 Master/Slave 구성을 지원한다.

```typescript
{
  type: 'postgres',
  replication: {
    master: { host: 'master.db', /* ... */ },
    slaves: [
      { host: 'slave1.db', /* ... */ },
      { host: 'slave2.db', /* ... */ },
    ],
  },
}
```

기본적으로 SELECT는 Slave로, 그 외는 Master로 라우팅된다. 트랜잭션 내부의 SELECT는 항상 Master로 간다.

### Serverless 환경에서의 고민

AWS Lambda 같은 Serverless에서 TypeORM을 쓰면 Connection Pool이 오히려 독이 된다. Lambda는 인스턴스가 수백 개씩 뜰 수 있는데, 각 인스턴스가 Pool을 유지하면 DB가 감당을 못한다. RDS Proxy나 pgBouncer 같은 중간 계층을 두거나, Pool 없이 요청마다 Connection을 새로 여는 방식이 필요하다.

## 운영 중 자주 보는 주의사항

### Soft Delete

TypeORM은 `@DeleteDateColumn`으로 Soft Delete를 지원한다. `softDelete()`는 `deletedAt`을 현재 시각으로 채우고, 이후 `find()` 같은 메서드는 자동으로 deletedAt IS NULL 조건을 붙인다.

그런데 QueryBuilder를 쓰면 이 자동 필터링이 적용되지 않는다. 직접 `WHERE ... IS NULL` 조건을 추가해야 한다. 이걸 놓쳐서 삭제된 레코드가 검색에 노출되는 버그가 자주 나온다.

```typescript
.createQueryBuilder('user')
.withDeleted()  // 삭제된 것도 포함
.getMany();

.createQueryBuilder('user')
.andWhere('user.deleted_at IS NULL')  // 명시적 필터
.getMany();
```

### 시간 컬럼의 타임존

`@CreateDateColumn`, `@UpdateDateColumn`은 DB의 현재 시각을 자동으로 채운다. DB 서버 타임존이 UTC면 UTC로 저장되고, Asia/Seoul이면 KST로 저장된다. 운영 환경과 개발 환경의 DB 타임존이 다르면 시간값이 9시간씩 어긋나는 문제가 생긴다. DB 타임존은 반드시 UTC로 통일하고, 애플리케이션 단에서 표시 시점에만 로컬 타임존으로 변환하는 게 낫다.

### 데코레이터 실행 순서와 Circular Dependency

엔티티끼리 서로 참조할 때 TypeScript의 모듈 로딩 순서 때문에 `Cannot read property of undefined` 같은 에러가 발생한다. 화살표 함수로 타입을 지연 평가하는 것이 기본 패턴이다.

```typescript
@ManyToOne(() => User, (user) => user.orders)  // 화살표 함수 필수
user: User;
```

`@ManyToOne(User, ...)`처럼 직접 클래스를 참조하면 로딩 시점에 User가 아직 정의되지 않았을 수 있다.

## 마무리

TypeORM은 손에 익으면 빠르게 개발할 수 있는 ORM이지만, 기본 설정대로만 쓰면 운영에서 반드시 문제가 생긴다. 가장 중요한 세 가지를 꼽자면 `synchronize: false`로 두고 Migration으로 관리하기, 트랜잭션 범위를 DB 작업으로만 한정하기, Connection Pool 크기와 DB max_connections의 균형 맞추기다. 이 세 가지만 제대로 잡혀 있어도 운영 중 장애의 대부분은 예방할 수 있다.
