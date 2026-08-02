---
title: NestJS MongoDB/Mongoose 연동
tags: [nestjs, mongodb, Mongoose, database, Schema, transaction]
updated: 2026-07-10
---

# NestJS MongoDB/Mongoose 연동

## 기본 설정

`@nestjs/mongoose` 패키지가 Mongoose를 NestJS의 DI 컨테이너에 통합해준다. Mongoose 자체를 직접 써도 되지만, 모듈 시스템과 맞물려 커넥션 생명주기 관리가 편하다.

```bash
npm install @nestjs/mongoose mongoose
```

가장 단순한 형태의 루트 모듈 설정이다.

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';

@Module({
  imports: [
    MongooseModule.forRoot('mongodb://localhost:27017/mydb'),
  ],
})
export class AppModule {}
```

`forRoot`는 앱 전체에서 하나의 커넥션을 공유한다. 이 커넥션은 `onApplicationShutdown` 시점에 자동으로 닫힌다.

## Schema 정의

NestJS에서 Mongoose Schema를 정의하는 방법은 두 가지다. 데코레이터 기반과 팩토리 함수 기반인데, 팀 내 타입 안전성을 중요하게 보면 데코레이터 방식이 더 낫다.

```typescript
// schemas/user.schema.ts
import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type UserDocument = HydratedDocument<User>;

@Schema({ timestamps: true })
export class User {
  @Prop({ required: true })
  name: string;

  @Prop({ required: true, unique: true, lowercase: true })
  email: string;

  @Prop({ default: 0 })
  age: number;

  @Prop({ type: [String], default: [] })
  roles: string[];
}

export const UserSchema = SchemaFactory.createForClass(User);
```

`HydratedDocument<User>`는 Mongoose 6.x부터 `Document & User` 대신 쓰는 타입이다. `_id`, `save()`, `populate()` 같은 Mongoose 인스턴스 메서드가 다 포함된다.

스키마를 특정 모듈에서 등록한다.

```typescript
// users/users.module.ts
import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { User, UserSchema } from './schemas/user.schema';
import { UsersService } from './users.service';

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: User.name, schema: UserSchema },
    ]),
  ],
  providers: [UsersService],
  exports: [UsersService],
})
export class UsersModule {}
```

서비스에서는 `@InjectModel`로 모델을 주입받는다.

```typescript
// users/users.service.ts
import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { User, UserDocument } from './schemas/user.schema';

@Injectable()
export class UsersService {
  constructor(
    @InjectModel(User.name) private userModel: Model<UserDocument>,
  ) {}

  async findById(id: string): Promise<UserDocument | null> {
    return this.userModel.findById(id).exec();
  }

  async create(name: string, email: string): Promise<UserDocument> {
    const user = new this.userModel({ name, email });
    return user.save();
  }
}
```

## 멀티 커넥션 구성

단일 DB로 시작했다가 나중에 DB를 분리해야 하는 경우가 생긴다. 처음부터 멀티 커넥션을 고려해야 한다면 `forRootAsync`와 `connectionName`을 쓴다.

```typescript
// app.module.ts
@Module({
  imports: [
    MongooseModule.forRootAsync({
      connectionName: 'users',
      useFactory: (config: ConfigService) => ({
        uri: config.get<string>('MONGO_USERS_URI'),
        maxPoolSize: 10,
        serverSelectionTimeoutMS: 5000,
      }),
      inject: [ConfigService],
    }),
    MongooseModule.forRootAsync({
      connectionName: 'logs',
      useFactory: (config: ConfigService) => ({
        uri: config.get<string>('MONGO_LOGS_URI'),
        maxPoolSize: 5,
      }),
      inject: [ConfigService],
    }),
    ConfigModule.forRoot({ isGlobal: true }),
  ],
})
export class AppModule {}
```

모듈에서 `forFeature`를 쓸 때 `connectionName`을 지정해야 한다.

```typescript
MongooseModule.forFeature(
  [{ name: User.name, schema: UserSchema }],
  'users', // connectionName
)
```

서비스에서 모델 주입 시도 `@InjectModel`에 커넥션 이름을 넘긴다.

```typescript
@InjectModel(User.name, 'users') private userModel: Model<UserDocument>
```

커넥션 이름을 빠뜨리면 기본 커넥션에서 모델을 찾다가 런타임 에러가 난다. `Provider not found` 에러가 아닌 Mongoose 레벨 에러라 추적하기 까다롭다.

## 내장 문서(Subdocument) vs Ref/Populate

MongoDB를 쓰면서 제일 많이 고민하는 부분이다. 잘못 선택하면 나중에 바꾸기 힘들다.

**내장 문서가 맞는 경우**

- 부모 문서 없이 단독으로 조회할 일이 없는 데이터
- 데이터 크기가 예측 가능하고 무한정 늘어나지 않는 경우
- 항상 부모와 함께 읽는 경우

```typescript
@Schema()
export class Address {
  @Prop({ required: true })
  street: string;

  @Prop({ required: true })
  city: string;

  @Prop()
  zipCode: string;
}

export const AddressSchema = SchemaFactory.createForClass(Address);

@Schema()
export class User {
  @Prop({ type: AddressSchema })
  address: Address;

  // 배열 내장: 항목 수가 제한적일 때만 사용
  @Prop({ type: [AddressSchema], default: [] })
  shippingAddresses: Address[];
}
```

배열 내장은 항목이 무한정 늘어나는 구조에 쓰면 안 된다. MongoDB 도큐먼트 크기 제한이 16MB이고, 배열이 커질수록 쓰기 성능이 떨어진다.

**Ref/Populate가 맞는 경우**

- 참조 대상이 독립적으로 조회·수정되는 경우
- 여러 곳에서 같은 도큐먼트를 참조하는 경우
- 참조 배열이 커질 수 있는 경우

```typescript
import { Types } from 'mongoose';

@Schema()
export class Post {
  @Prop({ required: true })
  title: string;

  @Prop({ type: Types.ObjectId, ref: 'User', required: true })
  author: Types.ObjectId | User;

  @Prop({ type: [{ type: Types.ObjectId, ref: 'Tag' }] })
  tags: Types.ObjectId[] | Tag[];
}

export const PostSchema = SchemaFactory.createForClass(Post);
```

Populate 쿼리 예시다.

```typescript
async findPostWithAuthor(id: string): Promise<PostDocument> {
  return this.postModel
    .findById(id)
    .populate('author', 'name email') // 필드 선택
    .populate('tags', 'name')
    .exec();
}
```

Populate는 편하지만 N+1 문제가 있다. 목록 조회에서 무분별하게 쓰면 쿼리가 폭발한다. 목록에서는 필요한 필드만 프로젝션하거나, `$lookup` 집계를 쓰는 게 낫다.

## 트랜잭션 (세션 기반)

MongoDB 트랜잭션은 레플리카셋 환경에서만 동작한다. 로컬 개발 환경에서 단일 인스턴스로 쓰면 트랜잭션이 에러를 낸다. 로컬에서도 레플리카셋을 구성하거나, MongoDB Atlas를 쓰면 된다.

커넥션 객체를 주입받아 세션을 직접 관리한다.

```typescript
import { InjectConnection } from '@nestjs/mongoose';
import { Connection, ClientSession } from 'mongoose';

@Injectable()
export class OrdersService {
  constructor(
    @InjectConnection() private readonly connection: Connection,
    @InjectModel(Order.name) private orderModel: Model<OrderDocument>,
    @InjectModel(Inventory.name) private inventoryModel: Model<InventoryDocument>,
  ) {}

  async createOrder(userId: string, items: OrderItem[]): Promise<OrderDocument> {
    const session: ClientSession = await this.connection.startSession();
    
    try {
      session.startTransaction();

      // 재고 차감
      for (const item of items) {
        const result = await this.inventoryModel.findOneAndUpdate(
          { productId: item.productId, quantity: { $gte: item.quantity } },
          { $inc: { quantity: -item.quantity } },
          { session, new: true },
        );

        if (!result) {
          throw new Error(`재고 부족: ${item.productId}`);
        }
      }

      // 주문 생성
      const [order] = await this.orderModel.create(
        [{ userId, items, status: 'pending' }],
        { session },
      );

      await session.commitTransaction();
      return order;
    } catch (error) {
      await session.abortTransaction();
      throw error;
    } finally {
      await session.endSession();
    }
  }
}
```

`create()`에 세션을 넘길 때 배열 형태로 넘겨야 한다. `create([doc], { session })`이 맞다. `create(doc, { session })`은 세션이 적용되지 않는다.

멀티 커넥션 환경에서는 커넥션 이름을 지정해서 주입받는다.

```typescript
@InjectConnection('users') private readonly usersConnection: Connection,
```

## 인덱스 선언

스키마에서 `@Prop`의 옵션으로 단일 인덱스를 선언하거나, `@Schema` 데코레이터 아래에 `SchemaFactory`로 복합 인덱스를 추가한다.

```typescript
@Schema({ timestamps: true })
export class User {
  @Prop({ required: true, unique: true, index: true })
  email: string;

  @Prop({ index: true })
  createdAt: Date;

  // TTL 인덱스 (90일 후 자동 삭제)
  @Prop({ type: Date })
  expireAt: Date;
}

export const UserSchema = SchemaFactory.createForClass(User);

// 복합 인덱스
UserSchema.index({ email: 1, createdAt: -1 });

// TTL 인덱스
UserSchema.index({ expireAt: 1 }, { expireAfterSeconds: 0 });

// 텍스트 인덱스
UserSchema.index({ name: 'text', bio: 'text' });
```

### 인덱스 마이그레이션 전략

Mongoose의 `autoIndex` 옵션이 기본적으로 `true`다. 앱 시작 시 스키마에 선언된 인덱스가 없으면 자동으로 생성한다. 개발 환경에서는 편하지만 운영에서는 문제가 된다.

- 대용량 컬렉션에서 인덱스 빌드는 오래 걸리고 I/O를 많이 먹는다
- 앱 시작과 동시에 인덱스 빌드가 시작되면 서비스 응답이 느려진다

운영에서는 `autoIndex: false`로 꺼야 한다.

```typescript
MongooseModule.forRootAsync({
  useFactory: (config: ConfigService) => ({
    uri: config.get<string>('MONGO_URI'),
    autoIndex: config.get<string>('NODE_ENV') !== 'production',
  }),
  inject: [ConfigService],
})
```

인덱스는 MongoDB Shell이나 별도 마이그레이션 스크립트로 관리한다.

```javascript
// 운영 배포 전 별도 실행하는 인덱스 마이그레이션
db.users.createIndex(
  { email: 1 },
  { unique: true, background: true } // background: true로 빌드 중 서비스 유지
);
```

MongoDB 4.2부터 `background` 옵션이 deprecated됐고, 인덱스 빌드가 기본적으로 온라인 방식으로 동작한다. `background` 옵션을 명시해도 동작은 하지만 무시된다.

인덱스를 삭제할 때는 더 조심해야 한다. 인덱스를 스키마에서 지운다고 해서 DB에서 삭제되지 않는다. `autoIndex: true`여도 기존 인덱스는 건드리지 않는다. DB에서 직접 `dropIndex`를 실행해야 한다.

## 커넥션 풀 튜닝

기본 `maxPoolSize`는 5다. 트래픽이 어느 정도 있는 서비스에서는 부족하다. 반대로 람다나 서버리스 환경에서는 커넥션이 쌓일 수 있어서 줄여야 한다.

```typescript
MongooseModule.forRootAsync({
  useFactory: (config: ConfigService) => ({
    uri: config.get<string>('MONGO_URI'),
    maxPoolSize: 20,           // 최대 커넥션 수
    minPoolSize: 5,            // 최소 유지 커넥션 수
    maxIdleTimeMS: 30000,      // 유휴 커넥션 유지 시간 (30초)
    serverSelectionTimeoutMS: 5000,  // 서버 선택 타임아웃
    socketTimeoutMS: 45000,    // 소켓 타임아웃
    connectTimeoutMS: 10000,   // 초기 연결 타임아웃
    heartbeatFrequencyMS: 10000,     // 헬스체크 주기
  }),
  inject: [ConfigService],
})
```

커넥션 풀 크기는 애플리케이션 인스턴스 수와 MongoDB가 허용하는 최대 커넥션 수를 고려해야 한다. 인스턴스 10개에 풀 크기 20이면 MongoDB는 최대 200개 커넥션을 받는다. MongoDB Atlas M10 기준 최대 커넥션이 1500개 정도라 인스턴스 수가 늘어날수록 풀 크기를 줄여야 한다.

커넥션 상태를 모니터링할 때는 Mongoose 이벤트를 활용한다.

```typescript
// database/database.module.ts
import { Module, OnModuleInit } from '@nestjs/common';
import { InjectConnection } from '@nestjs/mongoose';
import { Connection } from 'mongoose';

@Injectable()
export class DatabaseHealthService implements OnModuleInit {
  constructor(
    @InjectConnection() private readonly connection: Connection,
  ) {}

  onModuleInit() {
    this.connection.on('connected', () => {
      console.log('MongoDB connected');
    });

    this.connection.on('disconnected', () => {
      console.warn('MongoDB disconnected');
    });

    this.connection.on('error', (error) => {
      console.error('MongoDB error:', error);
    });
  }
}
```

운영에서는 커넥션 수를 Prometheus 메트릭으로 노출하고, `connection.pool`에서 active/idle 커넥션 수를 추적하는 게 좋다.

## 자주 겪는 문제

**`E11000 duplicate key error` 처리**

unique 인덱스 위반은 Mongoose가 `MongoServerError`로 던진다. NestJS의 exception filter에서 처리하지 않으면 500 에러로 올라간다.

```typescript
import { MongoServerError } from 'mongodb';

async createUser(dto: CreateUserDto): Promise<UserDocument> {
  try {
    return await this.userModel.create(dto);
  } catch (error) {
    if (error instanceof MongoServerError && error.code === 11000) {
      throw new ConflictException('이미 존재하는 이메일입니다.');
    }
    throw error;
  }
}
```

**Populate 후 타입 문제**

`populate()` 후에 타입이 `Types.ObjectId | User`로 남아있어서 참조 필드 접근 시 타입 에러가 난다.

```typescript
// 타입 단언이 필요한 경우
const post = await this.postModel.findById(id).populate('author').exec();
const author = post.author as UserDocument; // 단언
console.log(author.email); // 이제 접근 가능
```

아니면 제네릭을 활용한 헬퍼 타입을 만들어 관리하는 방법도 있다.

**`lean()` 사용 시 주의**

`lean()`을 쓰면 Mongoose 인스턴스 대신 순수 JS 객체를 반환해서 성능이 낫다. 단, `save()`, `populate()` 같은 메서드를 쓸 수 없다. 읽기 전용 조회에만 쓴다.

```typescript
// 목록 조회에 lean() 적용
async findAll(): Promise<User[]> {
  return this.userModel.find().lean<User[]>().exec();
}
```

`lean<User[]>()`처럼 제네릭을 명시하면 반환 타입이 맞게 추론된다.
