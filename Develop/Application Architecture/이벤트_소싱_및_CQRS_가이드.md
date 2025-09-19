# 이벤트 소싱 및 CQRS 가이드 (Event Sourcing & CQRS Guide)

## 목차 (Table of Contents)
1. [분산 시스템 개요 (Distributed Systems Overview)](#분산-시스템-개요)
2. [이벤트 소싱 (Event Sourcing) 패턴](#이벤트-소싱-event-sourcing-패턴)
3. [CQRS (Command Query Responsibility Segregation) 구현](#cqrs-command-query-responsibility-segregation-구현)

## 분산 시스템 개요 (Distributed Systems Overview)

분산 시스템은 여러 독립적인 컴퓨터들이 네트워크를 통해 연결되어 하나의 통합된 시스템으로 동작하는 구조입니다.

### 분산 시스템의 핵심 원칙

1. **확장성 (Scalability)**: 시스템의 크기와 복잡성 증가에 대응
2. **가용성 (Availability)**: 시스템의 지속적인 서비스 제공
3. **일관성 (Consistency)**: 데이터의 정확성과 일관성 유지
4. **분할 내성 (Partition Tolerance)**: 네트워크 분할 상황에서도 동작

### CAP 정리 (Consistency, Availability, Partition Tolerance)

```javascript
// 강한 일관성 (Strong Consistency)
class StrongConsistencyService {
  async updateUser(userId, userData) {
    // 모든 복제본에 동시 업데이트
    await Promise.all([
      this.primaryDB.update(userId, userData),
      this.replica1.update(userId, userData),
      this.replica2.update(userId, userData)
    ]);
    
    return userData;
  }
}

// 최종 일관성 (Eventual Consistency)
class EventualConsistencyService {
  async updateUser(userId, userData) {
    // 기본 저장소에만 먼저 업데이트
    await this.primaryDB.update(userId, userData);
    
    // 비동기적으로 복제본 업데이트
    this.eventBus.publish('UserUpdated', { userId, userData });
    
    return userData;
  }
}
```

## 이벤트 소싱 (Event Sourcing) 패턴

이벤트 소싱은 애플리케이션의 상태를 변경하는 이벤트들의 시퀀스로 저장하는 패턴입니다.

### 1. 이벤트 스토어 구현

```javascript
class EventStore {
  constructor(database) {
    this.db = database;
  }
  
  async saveEvents(aggregateId, events, expectedVersion) {
    const stream = await this.getStream(aggregateId);
    
    if (stream.version !== expectedVersion) {
      throw new Error('Concurrency conflict');
    }
    
    const eventRecords = events.map((event, index) => ({
      aggregateId,
      version: expectedVersion + index + 1,
      eventType: event.constructor.name,
      eventData: JSON.stringify(event),
      timestamp: new Date()
    }));
    
    await this.db.query(
      'INSERT INTO events (aggregate_id, version, event_type, event_data, timestamp) VALUES ?',
      [eventRecords.map(record => Object.values(record))]
    );
    
    return eventRecords;
  }
  
  async getEvents(aggregateId) {
    const rows = await this.db.query(
      'SELECT * FROM events WHERE aggregate_id = ? ORDER BY version',
      [aggregateId]
    );
    
    return rows.map(row => ({
      type: row.event_type,
      data: JSON.parse(row.event_data),
      version: row.version,
      timestamp: row.timestamp
    }));
  }
  
  async getStream(aggregateId) {
    const result = await this.db.query(
      'SELECT MAX(version) as version FROM events WHERE aggregate_id = ?',
      [aggregateId]
    );
    
    return {
      aggregateId,
      version: result[0]?.version || 0
    };
  }
}
```

### 2. 애그리게이트 구현

```javascript
class UserAggregate {
  constructor() {
    this.id = null;
    this.name = null;
    this.email = null;
    this.version = 0;
    this.uncommittedEvents = [];
  }
  
  static fromEvents(events) {
    const aggregate = new UserAggregate();
    events.forEach(event => aggregate.apply(event));
    return aggregate;
  }
  
  apply(event) {
    switch (event.type) {
      case 'UserCreated':
        this.id = event.data.userId;
        this.name = event.data.name;
        this.email = event.data.email;
        break;
      case 'UserUpdated':
        this.name = event.data.name;
        this.email = event.data.email;
        break;
      case 'UserDeleted':
        this.deleted = true;
        break;
    }
    this.version++;
  }
  
  createUser(userData) {
    if (this.id) {
      throw new Error('User already exists');
    }
    
    const event = new UserCreatedEvent(userData);
    this.apply(event);
    this.uncommittedEvents.push(event);
    return this;
  }
  
  updateUser(userData) {
    if (!this.id) {
      throw new Error('User does not exist');
    }
    
    const event = new UserUpdatedEvent(this.id, userData);
    this.apply(event);
    this.uncommittedEvents.push(event);
    return this;
  }
  
  deleteUser() {
    if (!this.id) {
      throw new Error('User does not exist');
    }
    
    const event = new UserDeletedEvent(this.id);
    this.apply(event);
    this.uncommittedEvents.push(event);
    return this;
  }
  
  getUncommittedEvents() {
    return this.uncommittedEvents;
  }
  
  markEventsAsCommitted() {
    this.uncommittedEvents = [];
  }
}

// 이벤트 클래스들
class UserCreatedEvent {
  constructor(userData) {
    this.userId = userData.id;
    this.name = userData.name;
    this.email = userData.email;
    this.timestamp = new Date();
  }
}

class UserUpdatedEvent {
  constructor(userId, userData) {
    this.userId = userId;
    this.name = userData.name;
    this.email = userData.email;
    this.timestamp = new Date();
  }
}

class UserDeletedEvent {
  constructor(userId) {
    this.userId = userId;
    this.timestamp = new Date();
  }
}
```

### 3. 이벤트 소싱 서비스

```javascript
class EventSourcingService {
  constructor(eventStore, eventBus) {
    this.eventStore = eventStore;
    this.eventBus = eventBus;
    this.projections = new Map();
  }
  
  async saveAggregate(aggregate) {
    const events = aggregate.getUncommittedEvents();
    if (events.length === 0) {
      return;
    }
    
    const expectedVersion = aggregate.version - events.length;
    await this.eventStore.saveEvents(aggregate.id, events, expectedVersion);
    
    // 이벤트 발행
    for (const event of events) {
      await this.eventBus.publish(event.constructor.name, event);
    }
    
    aggregate.markEventsAsCommitted();
  }
  
  async getAggregate(aggregateId) {
    const events = await this.eventStore.getEvents(aggregateId);
    return UserAggregate.fromEvents(events);
  }
  
  // 프로젝션 등록
  registerProjection(name, projection) {
    this.projections.set(name, projection);
  }
  
  // 프로젝션 업데이트
  async updateProjections(events) {
    for (const event of events) {
      for (const [name, projection] of this.projections) {
        await projection.handle(event);
      }
    }
  }
}
```

## CQRS (Command Query Responsibility Segregation) 구현

CQRS는 명령(Command)과 쿼리(Query)의 책임을 분리하는 패턴입니다.

### 1. 명령 처리 (Command Handling)

```javascript
class CommandBus {
  constructor() {
    this.handlers = new Map();
  }
  
  registerHandler(commandType, handler) {
    this.handlers.set(commandType, handler);
  }
  
  async execute(command) {
    const handler = this.handlers.get(command.constructor.name);
    if (!handler) {
      throw new Error(`No handler found for command: ${command.constructor.name}`);
    }
    
    return await handler.execute(command);
  }
}

// 명령 클래스들
class CreateUserCommand {
  constructor(userData) {
    this.userData = userData;
  }
}

class UpdateUserCommand {
  constructor(userId, userData) {
    this.userId = userId;
    this.userData = userData;
  }
}

// 명령 핸들러들
class CreateUserHandler {
  constructor(eventSourcingService) {
    this.eventSourcingService = eventSourcingService;
  }
  
  async execute(command) {
    const aggregate = new UserAggregate();
    aggregate.createUser(command.userData);
    
    await this.eventSourcingService.saveAggregate(aggregate);
    
    return {
      userId: aggregate.id,
      version: aggregate.version
    };
  }
}

class UpdateUserHandler {
  constructor(eventSourcingService) {
    this.eventSourcingService = eventSourcingService;
  }
  
  async execute(command) {
    const aggregate = await this.eventSourcingService.getAggregate(command.userId);
    aggregate.updateUser(command.userData);
    
    await this.eventSourcingService.saveAggregate(aggregate);
    
    return {
      userId: aggregate.id,
      version: aggregate.version
    };
  }
}
```

### 2. 쿼리 처리 (Query Handling)

```javascript
class QueryBus {
  constructor() {
    this.handlers = new Map();
  }
  
  registerHandler(queryType, handler) {
    this.handlers.set(queryType, handler);
  }
  
  async execute(query) {
    const handler = this.handlers.get(query.constructor.name);
    if (!handler) {
      throw new Error(`No handler found for query: ${query.constructor.name}`);
    }
    
    return await handler.execute(query);
  }
}

// 쿼리 클래스들
class GetUserQuery {
  constructor(userId) {
    this.userId = userId;
  }
}

class GetUsersQuery {
  constructor(filters = {}) {
    this.filters = filters;
  }
}

// 쿼리 핸들러들
class GetUserHandler {
  constructor(readOnlyDB) {
    this.readOnlyDB = readOnlyDB;
  }
  
  async execute(query) {
    const result = await this.readOnlyDB.query(
      'SELECT * FROM user_view WHERE id = ?',
      [query.userId]
    );
    
    return result[0] || null;
  }
}

class GetUsersHandler {
  constructor(readOnlyDB) {
    this.readOnlyDB = readOnlyDB;
  }
  
  async execute(query) {
    let sql = 'SELECT * FROM user_view WHERE 1=1';
    const params = [];
    
    if (query.filters.name) {
      sql += ' AND name LIKE ?';
      params.push(`%${query.filters.name}%`);
    }
    
    if (query.filters.email) {
      sql += ' AND email LIKE ?';
      params.push(`%${query.filters.email}%`);
    }
    
    sql += ' ORDER BY created_at DESC';
    
    if (query.filters.limit) {
      sql += ' LIMIT ?';
      params.push(query.filters.limit);
    }
    
    return await this.readOnlyDB.query(sql, params);
  }
}
```

### 3. 프로젝션 (Projection)

```javascript
class UserProjection {
  constructor(readOnlyDB) {
    this.readOnlyDB = readOnlyDB;
  }
  
  async handle(event) {
    switch (event.constructor.name) {
      case 'UserCreatedEvent':
        await this.handleUserCreated(event);
        break;
      case 'UserUpdatedEvent':
        await this.handleUserUpdated(event);
        break;
      case 'UserDeletedEvent':
        await this.handleUserDeleted(event);
        break;
    }
  }
  
  async handleUserCreated(event) {
    await this.readOnlyDB.query(
      'INSERT INTO user_view (id, name, email, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
      [event.userId, event.name, event.email, event.timestamp, event.timestamp]
    );
  }
  
  async handleUserUpdated(event) {
    await this.readOnlyDB.query(
      'UPDATE user_view SET name = ?, email = ?, updated_at = ? WHERE id = ?',
      [event.name, event.email, event.timestamp, event.userId]
    );
  }
  
  async handleUserDeleted(event) {
    await this.readOnlyDB.query(
      'DELETE FROM user_view WHERE id = ?',
      [event.userId]
    );
  }
}
```

## 4. 실습 프로젝트: 주문 도메인 이벤트 소싱 & CQRS 구현

### 4.1 프로젝트 구조

```
event-sourcing-cqrs-practice/
├── src/
│   ├── core/                    # 핵심 도메인 로직
│   │   ├── events/             # 이벤트 정의
│   │   ├── aggregates/         # 애그리게이트
│   │   ├── commands/           # 명령
│   │   ├── queries/            # 쿼리
│   │   └── handlers/           # 핸들러
│   ├── infrastructure/         # 인프라 계층
│   │   ├── eventstore/         # 이벤트 스토어
│   │   ├── projections/        # 프로젝션
│   │   └── database/           # 데이터베이스
│   ├── application/            # 애플리케이션 계층
│   │   ├── services/           # 서비스
│   │   └── dto/               # 데이터 전송 객체
│   └── api/                   # API 계층
│       ├── controllers/        # 컨트롤러
│       └── middleware/         # 미들웨어
├── tests/                     # 테스트
├── docker-compose.yml         # 개발 환경
└── package.json
```

### 4.2 TypeScript 기반 이벤트 스토어 구현

```typescript
// src/infrastructure/eventstore/PostgreSQLEventStore.ts
import { Pool, PoolClient } from 'pg';
import { Event, EventStore, Snapshot, StreamVersion } from '../interfaces';

export class PostgreSQLEventStore implements EventStore {
  private pool: Pool;

  constructor(connectionString: string) {
    this.pool = new Pool({
      connectionString,
      max: 20,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000,
    });
  }

  async saveEvents(
    streamId: string,
    events: Event[],
    expectedVersion: StreamVersion
  ): Promise<void> {
    const client = await this.pool.connect();
    
    try {
      await client.query('BEGIN');
      
      // 동시성 제어를 위한 버전 확인
      const currentVersion = await this.getStreamVersion(client, streamId);
      
      if (currentVersion !== expectedVersion) {
        throw new ConcurrencyError(
          `Expected version ${expectedVersion}, but current version is ${currentVersion}`
        );
      }

      // 이벤트 저장
      for (let i = 0; i < events.length; i++) {
        const event = events[i];
        const version = expectedVersion + i + 1;
        
        await client.query(
          `INSERT INTO events (stream_id, version, event_type, event_data, metadata, created_at)
           VALUES ($1, $2, $3, $4, $5, $6)`,
          [
            streamId,
            version,
            event.type,
            JSON.stringify(event.data),
            JSON.stringify(event.metadata || {}),
            new Date()
          ]
        );
      }

      await client.query('COMMIT');
      
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getEvents(
    streamId: string,
    fromVersion: number = 0,
    toVersion?: number
  ): Promise<Event[]> {
    const client = await this.pool.connect();
    
    try {
      let query = `
        SELECT version, event_type, event_data, metadata, created_at
        FROM events
        WHERE stream_id = $1 AND version > $2
      `;
      const params: any[] = [streamId, fromVersion];
      
      if (toVersion !== undefined) {
        query += ' AND version <= $3';
        params.push(toVersion);
      }
      
      query += ' ORDER BY version ASC';
      
      const result = await client.query(query, params);
      
      return result.rows.map(row => ({
        type: row.event_type,
        data: JSON.parse(row.event_data),
        metadata: JSON.parse(row.metadata || '{}'),
        version: row.version,
        timestamp: row.created_at
      }));
      
    } finally {
      client.release();
    }
  }

  async saveSnapshot(snapshot: Snapshot): Promise<void> {
    const client = await this.pool.connect();
    
    try {
      await client.query(
        `INSERT INTO snapshots (stream_id, version, snapshot_data, created_at)
         VALUES ($1, $2, $3, $4)
         ON CONFLICT (stream_id) 
         DO UPDATE SET 
           version = EXCLUDED.version,
           snapshot_data = EXCLUDED.snapshot_data,
           created_at = EXCLUDED.created_at`,
        [
          snapshot.streamId,
          snapshot.version,
          JSON.stringify(snapshot.data),
          new Date()
        ]
      );
    } finally {
      client.release();
    }
  }

  async getSnapshot(streamId: string): Promise<Snapshot | null> {
    const client = await this.pool.connect();
    
    try {
      const result = await client.query(
        'SELECT version, snapshot_data FROM snapshots WHERE stream_id = $1',
        [streamId]
      );
      
      if (result.rows.length === 0) {
        return null;
      }
      
      const row = result.rows[0];
      return {
        streamId,
        version: row.version,
        data: JSON.parse(row.snapshot_data),
        timestamp: new Date()
      };
      
    } finally {
      client.release();
    }
  }

  private async getStreamVersion(client: PoolClient, streamId: string): Promise<number> {
    const result = await client.query(
      'SELECT COALESCE(MAX(version), 0) as version FROM events WHERE stream_id = $1',
      [streamId]
    );
    
    return result.rows[0].version;
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}

// 에러 클래스
export class ConcurrencyError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConcurrencyError';
  }
}

// 인터페이스 정의
export interface Event {
  type: string;
  data: any;
  metadata?: any;
  version?: number;
  timestamp?: Date;
}

export interface Snapshot {
  streamId: string;
  version: number;
  data: any;
  timestamp: Date;
}

export interface StreamVersion {
  version: number;
}

export interface EventStore {
  saveEvents(streamId: string, events: Event[], expectedVersion: StreamVersion): Promise<void>;
  getEvents(streamId: string, fromVersion?: number, toVersion?: number): Promise<Event[]>;
  saveSnapshot(snapshot: Snapshot): Promise<void>;
  getSnapshot(streamId: string): Promise<Snapshot | null>;
}
```

### 4.3 애그리게이트 루트 추상 클래스

```typescript
// src/core/aggregates/AggregateRoot.ts
import { Event } from '../../infrastructure/eventstore/PostgreSQLEventStore';

export abstract class AggregateRoot {
  protected id: string;
  protected version: number = 0;
  protected uncommittedEvents: Event[] = [];
  protected snapshotVersion: number = 0;

  constructor(id: string) {
    this.id = id;
  }

  getId(): string {
    return this.id;
  }

  getVersion(): number {
    return this.version;
  }

  getUncommittedEvents(): Event[] {
    return [...this.uncommittedEvents];
  }

  markEventsAsCommitted(): void {
    this.uncommittedEvents = [];
  }

  protected applyEvent(event: Event): void {
    this.handleEvent(event);
    this.version++;
    this.uncommittedEvents.push(event);
  }

  protected abstract handleEvent(event: Event): void;

  // 스냅샷 관련 메서드
  shouldCreateSnapshot(): boolean {
    return this.version - this.snapshotVersion >= 100; // 100개 이벤트마다 스냅샷
  }

  createSnapshot(): any {
    this.snapshotVersion = this.version;
    return this.getSnapshotData();
  }

  protected abstract getSnapshotData(): any;

  loadFromSnapshot(snapshotData: any, version: number): void {
    this.restoreFromSnapshot(snapshotData);
    this.snapshotVersion = version;
    this.version = version;
  }

  protected abstract restoreFromSnapshot(snapshotData: any): void;

  // 이벤트 재생을 통한 상태 복원
  static fromEvents<T extends AggregateRoot>(
    this: new (id: string) => T,
    id: string,
    events: Event[]
  ): T {
    const aggregate = new this(id);
    
    events.forEach(event => {
      aggregate.handleEvent(event);
      aggregate.version++;
    });
    
    return aggregate;
  }
}
```

### 4.4 주문 애그리게이트 구현

```typescript
// src/core/aggregates/OrderAggregate.ts
import { AggregateRoot } from './AggregateRoot';
import { Event } from '../../infrastructure/eventstore/PostgreSQLEventStore';
import {
  OrderCreatedEvent,
  PaymentCompletedEvent,
  ShippingStartedEvent,
  OrderCancelledEvent,
  OrderItemAddedEvent,
  OrderItemRemovedEvent
} from '../events/OrderEvents';

export interface OrderItem {
  productId: string;
  productName: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
}

export interface ShippingAddress {
  street: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
}

export enum OrderStatus {
  PENDING = 'PENDING',
  CONFIRMED = 'CONFIRMED',
  PAID = 'PAID',
  SHIPPED = 'SHIPPED',
  DELIVERED = 'DELIVERED',
  CANCELLED = 'CANCELLED'
}

export class OrderAggregate extends AggregateRoot {
  private userId: string;
  private items: OrderItem[] = [];
  private status: OrderStatus = OrderStatus.PENDING;
  private totalAmount: number = 0;
  private shippingAddress?: ShippingAddress;
  private paymentId?: string;
  private trackingNumber?: string;
  private cancelledAt?: Date;
  private cancellationReason?: string;

  constructor(id: string, userId?: string) {
    super(id);
    if (userId) {
      this.userId = userId;
    }
  }

  // 명령 메서드들
  createOrder(userId: string, items: OrderItem[], shippingAddress: ShippingAddress): void {
    if (this.userId) {
      throw new Error('Order already exists');
    }

    if (items.length === 0) {
      throw new Error('Order must have at least one item');
    }

    const totalAmount = items.reduce((sum, item) => sum + item.totalPrice, 0);

    this.applyEvent(new OrderCreatedEvent({
      orderId: this.id,
      userId,
      items,
      totalAmount,
      shippingAddress,
      timestamp: new Date()
    }));
  }

  addItem(item: OrderItem): void {
    if (this.status !== OrderStatus.PENDING) {
      throw new Error('Cannot add items to non-pending order');
    }

    this.applyEvent(new OrderItemAddedEvent({
      orderId: this.id,
      item,
      newTotalAmount: this.totalAmount + item.totalPrice,
      timestamp: new Date()
    }));
  }

  removeItem(productId: string): void {
    if (this.status !== OrderStatus.PENDING) {
      throw new Error('Cannot remove items from non-pending order');
    }

    const itemIndex = this.items.findIndex(item => item.productId === productId);
    if (itemIndex === -1) {
      throw new Error('Item not found in order');
    }

    const item = this.items[itemIndex];
    const newTotalAmount = this.totalAmount - item.totalPrice;

    this.applyEvent(new OrderItemRemovedEvent({
      orderId: this.id,
      productId,
      newTotalAmount,
      timestamp: new Date()
    }));
  }

  completePayment(paymentId: string): void {
    if (this.status !== OrderStatus.PENDING) {
      throw new Error('Payment can only be completed for pending orders');
    }

    this.applyEvent(new PaymentCompletedEvent({
      orderId: this.id,
      paymentId,
      timestamp: new Date()
    }));
  }

  startShipping(trackingNumber: string): void {
    if (this.status !== OrderStatus.PAID) {
      throw new Error('Shipping can only be started for paid orders');
    }

    this.applyEvent(new ShippingStartedEvent({
      orderId: this.id,
      trackingNumber,
      timestamp: new Date()
    }));
  }

  cancelOrder(reason: string): void {
    if (this.status === OrderStatus.SHIPPED || this.status === OrderStatus.DELIVERED) {
      throw new Error('Cannot cancel shipped or delivered orders');
    }

    if (this.status === OrderStatus.CANCELLED) {
      throw new Error('Order is already cancelled');
    }

    this.applyEvent(new OrderCancelledEvent({
      orderId: this.id,
      reason,
      timestamp: new Date()
    }));
  }

  // 이벤트 핸들러
  protected handleEvent(event: Event): void {
    switch (event.type) {
      case 'OrderCreatedEvent':
        this.handleOrderCreated(event.data);
        break;
      case 'OrderItemAddedEvent':
        this.handleOrderItemAdded(event.data);
        break;
      case 'OrderItemRemovedEvent':
        this.handleOrderItemRemoved(event.data);
        break;
      case 'PaymentCompletedEvent':
        this.handlePaymentCompleted(event.data);
        break;
      case 'ShippingStartedEvent':
        this.handleShippingStarted(event.data);
        break;
      case 'OrderCancelledEvent':
        this.handleOrderCancelled(event.data);
        break;
    }
  }

  private handleOrderCreated(data: any): void {
    this.userId = data.userId;
    this.items = data.items;
    this.totalAmount = data.totalAmount;
    this.shippingAddress = data.shippingAddress;
    this.status = OrderStatus.PENDING;
  }

  private handleOrderItemAdded(data: any): void {
    this.items.push(data.item);
    this.totalAmount = data.newTotalAmount;
  }

  private handleOrderItemRemoved(data: any): void {
    this.items = this.items.filter(item => item.productId !== data.productId);
    this.totalAmount = data.newTotalAmount;
  }

  private handlePaymentCompleted(data: any): void {
    this.paymentId = data.paymentId;
    this.status = OrderStatus.PAID;
  }

  private handleShippingStarted(data: any): void {
    this.trackingNumber = data.trackingNumber;
    this.status = OrderStatus.SHIPPED;
  }

  private handleOrderCancelled(data: any): void {
    this.status = OrderStatus.CANCELLED;
    this.cancelledAt = data.timestamp;
    this.cancellationReason = data.reason;
  }

  // 스냅샷 관련 메서드
  protected getSnapshotData(): any {
    return {
      userId: this.userId,
      items: this.items,
      status: this.status,
      totalAmount: this.totalAmount,
      shippingAddress: this.shippingAddress,
      paymentId: this.paymentId,
      trackingNumber: this.trackingNumber,
      cancelledAt: this.cancelledAt,
      cancellationReason: this.cancellationReason
    };
  }

  protected restoreFromSnapshot(snapshotData: any): void {
    this.userId = snapshotData.userId;
    this.items = snapshotData.items || [];
    this.status = snapshotData.status;
    this.totalAmount = snapshotData.totalAmount || 0;
    this.shippingAddress = snapshotData.shippingAddress;
    this.paymentId = snapshotData.paymentId;
    this.trackingNumber = snapshotData.trackingNumber;
    this.cancelledAt = snapshotData.cancelledAt;
    this.cancellationReason = snapshotData.cancellationReason;
  }

  // 쿼리 메서드들
  getUserId(): string {
    return this.userId;
  }

  getItems(): OrderItem[] {
    return [...this.items];
  }

  getStatus(): OrderStatus {
    return this.status;
  }

  getTotalAmount(): number {
    return this.totalAmount;
  }

  getShippingAddress(): ShippingAddress | undefined {
    return this.shippingAddress;
  }

  getPaymentId(): string | undefined {
    return this.paymentId;
  }

  getTrackingNumber(): string | undefined {
    return this.trackingNumber;
  }

  isCancelled(): boolean {
    return this.status === OrderStatus.CANCELLED;
  }
}
```

### 4.5 이벤트 정의

```typescript
// src/core/events/OrderEvents.ts
export class OrderCreatedEvent {
  public readonly type = 'OrderCreatedEvent';
  
  constructor(public readonly data: {
    orderId: string;
    userId: string;
    items: Array<{
      productId: string;
      productName: string;
      quantity: number;
      unitPrice: number;
      totalPrice: number;
    }>;
    totalAmount: number;
    shippingAddress: {
      street: string;
      city: string;
      state: string;
      zipCode: string;
      country: string;
    };
    timestamp: Date;
  }) {}
}

export class OrderItemAddedEvent {
  public readonly type = 'OrderItemAddedEvent';
  
  constructor(public readonly data: {
    orderId: string;
    item: {
      productId: string;
      productName: string;
      quantity: number;
      unitPrice: number;
      totalPrice: number;
    };
    newTotalAmount: number;
    timestamp: Date;
  }) {}
}

export class OrderItemRemovedEvent {
  public readonly type = 'OrderItemRemovedEvent';
  
  constructor(public readonly data: {
    orderId: string;
    productId: string;
    newTotalAmount: number;
    timestamp: Date;
  }) {}
}

export class PaymentCompletedEvent {
  public readonly type = 'PaymentCompletedEvent';
  
  constructor(public readonly data: {
    orderId: string;
    paymentId: string;
    timestamp: Date;
  }) {}
}

export class ShippingStartedEvent {
  public readonly type = 'ShippingStartedEvent';
  
  constructor(public readonly data: {
    orderId: string;
    trackingNumber: string;
    timestamp: Date;
  }) {}
}

export class OrderCancelledEvent {
  public readonly type = 'OrderCancelledEvent';
  
  constructor(public readonly data: {
    orderId: string;
    reason: string;
    timestamp: Date;
  }) {}
}
```

### 4.6 명령 및 명령 핸들러

```typescript
// src/core/commands/OrderCommands.ts
export class CreateOrderCommand {
  constructor(
    public readonly orderId: string,
    public readonly userId: string,
    public readonly items: Array<{
      productId: string;
      productName: string;
      quantity: number;
      unitPrice: number;
    }>,
    public readonly shippingAddress: {
      street: string;
      city: string;
      state: string;
      zipCode: string;
      country: string;
    }
  ) {}
}

export class AddOrderItemCommand {
  constructor(
    public readonly orderId: string,
    public readonly item: {
      productId: string;
      productName: string;
      quantity: number;
      unitPrice: number;
    }
  ) {}
}

export class RemoveOrderItemCommand {
  constructor(
    public readonly orderId: string,
    public readonly productId: string
  ) {}
}

export class CompletePaymentCommand {
  constructor(
    public readonly orderId: string,
    public readonly paymentId: string
  ) {}
}

export class StartShippingCommand {
  constructor(
    public readonly orderId: string,
    public readonly trackingNumber: string
  ) {}
}

export class CancelOrderCommand {
  constructor(
    public readonly orderId: string,
    public readonly reason: string
  ) {}
}
```

```typescript
// src/core/handlers/OrderCommandHandler.ts
import { CommandHandler } from '../interfaces/CommandHandler';
import { EventStore } from '../../infrastructure/eventstore/PostgreSQLEventStore';
import { OrderAggregate } from '../aggregates/OrderAggregate';
import {
  CreateOrderCommand,
  AddOrderItemCommand,
  RemoveOrderItemCommand,
  CompletePaymentCommand,
  StartShippingCommand,
  CancelOrderCommand
} from '../commands/OrderCommands';

export class OrderCommandHandler implements CommandHandler {
  constructor(private eventStore: EventStore) {}

  async handle(command: any): Promise<void> {
    if (command instanceof CreateOrderCommand) {
      await this.handleCreateOrder(command);
    } else if (command instanceof AddOrderItemCommand) {
      await this.handleAddOrderItem(command);
    } else if (command instanceof RemoveOrderItemCommand) {
      await this.handleRemoveOrderItem(command);
    } else if (command instanceof CompletePaymentCommand) {
      await this.handleCompletePayment(command);
    } else if (command instanceof StartShippingCommand) {
      await this.handleStartShipping(command);
    } else if (command instanceof CancelOrderCommand) {
      await this.handleCancelOrder(command);
    } else {
      throw new Error(`Unknown command: ${command.constructor.name}`);
    }
  }

  private async handleCreateOrder(command: CreateOrderCommand): Promise<void> {
    const order = new OrderAggregate(command.orderId);
    
    // 아이템 총 가격 계산
    const items = command.items.map(item => ({
      ...item,
      totalPrice: item.quantity * item.unitPrice
    }));

    order.createOrder(command.userId, items, command.shippingAddress);
    
    await this.saveAggregate(order);
  }

  private async handleAddOrderItem(command: AddOrderItemCommand): Promise<void> {
    const order = await this.loadAggregate(command.orderId);
    
    const item = {
      ...command.item,
      totalPrice: command.item.quantity * command.item.unitPrice
    };
    
    order.addItem(item);
    
    await this.saveAggregate(order);
  }

  private async handleRemoveOrderItem(command: RemoveOrderItemCommand): Promise<void> {
    const order = await this.loadAggregate(command.orderId);
    order.removeItem(command.productId);
    
    await this.saveAggregate(order);
  }

  private async handleCompletePayment(command: CompletePaymentCommand): Promise<void> {
    const order = await this.loadAggregate(command.orderId);
    order.completePayment(command.paymentId);
    
    await this.saveAggregate(order);
  }

  private async StartShipping(command: StartShippingCommand): Promise<void> {
    const order = await this.loadAggregate(command.orderId);
    order.startShipping(command.trackingNumber);
    
    await this.saveAggregate(order);
  }

  private async handleCancelOrder(command: CancelOrderCommand): Promise<void> {
    const order = await this.loadAggregate(command.orderId);
    order.cancelOrder(command.reason);
    
    await this.saveAggregate(order);
  }

  private async loadAggregate(orderId: string): Promise<OrderAggregate> {
    // 스냅샷 확인
    const snapshot = await this.eventStore.getSnapshot(orderId);
    
    if (snapshot) {
      // 스냅샷에서 복원
      const order = new OrderAggregate(orderId);
      order.loadFromSnapshot(snapshot.data, snapshot.version);
      
      // 스냅샷 이후 이벤트 로드
      const events = await this.eventStore.getEvents(orderId, snapshot.version);
      events.forEach(event => {
        (order as any).handleEvent(event);
        (order as any).version++;
      });
      
      return order;
    } else {
      // 이벤트만으로 복원
      const events = await this.eventStore.getEvents(orderId);
      return OrderAggregate.fromEvents(OrderAggregate, orderId, events);
    }
  }

  private async saveAggregate(order: OrderAggregate): Promise<void> {
    const events = order.getUncommittedEvents();
    if (events.length === 0) {
      return;
    }

    const expectedVersion = order.getVersion() - events.length;
    await this.eventStore.saveEvents(order.getId(), events, expectedVersion);
    
    // 스냅샷 생성 여부 확인
    if (order.shouldCreateSnapshot()) {
      const snapshot = {
        streamId: order.getId(),
        version: order.getVersion(),
        data: order.createSnapshot(),
        timestamp: new Date()
      };
      await this.eventStore.saveSnapshot(snapshot);
    }
    
    order.markEventsAsCommitted();
  }
}
```

### 4.7 쿼리 및 쿼리 핸들러

```typescript
// src/core/queries/OrderQueries.ts
export class GetOrderQuery {
  constructor(public readonly orderId: string) {}
}

export class GetUserOrdersQuery {
  constructor(
    public readonly userId: string,
    public readonly page: number = 1,
    public readonly limit: number = 10,
    public readonly status?: string
  ) {}
}

export class GetOrdersByStatusQuery {
  constructor(
    public readonly status: string,
    public readonly page: number = 1,
    public readonly limit: number = 10
  ) {}
}
```

```typescript
// src/core/handlers/OrderQueryHandler.ts
import { QueryHandler } from '../interfaces/QueryHandler';
import { ReadOnlyDatabase } from '../../infrastructure/database/ReadOnlyDatabase';
import {
  GetOrderQuery,
  GetUserOrdersQuery,
  GetOrdersByStatusQuery
} from '../queries/OrderQueries';

export class OrderQueryHandler implements QueryHandler {
  constructor(private readOnlyDB: ReadOnlyDatabase) {}

  async handle(query: any): Promise<any> {
    if (query instanceof GetOrderQuery) {
      return await this.handleGetOrder(query);
    } else if (query instanceof GetUserOrdersQuery) {
      return await this.handleGetUserOrders(query);
    } else if (query instanceof GetOrdersByStatusQuery) {
      return await this.handleGetOrdersByStatus(query);
    } else {
      throw new Error(`Unknown query: ${query.constructor.name}`);
    }
  }

  private async handleGetOrder(query: GetOrderQuery): Promise<any> {
    const result = await this.readOnlyDB.query(
      'SELECT * FROM order_view WHERE order_id = $1',
      [query.orderId]
    );
    
    return result.rows[0] || null;
  }

  private async handleGetUserOrders(query: GetUserOrdersQuery): Promise<any> {
    let sql = `
      SELECT * FROM order_view 
      WHERE user_id = $1
    `;
    const params: any[] = [query.userId];
    
    if (query.status) {
      sql += ' AND status = $2';
      params.push(query.status);
    }
    
    sql += ' ORDER BY created_at DESC';
    
    const offset = (query.page - 1) * query.limit;
    sql += ' LIMIT $' + (params.length + 1) + ' OFFSET $' + (params.length + 2);
    params.push(query.limit, offset);
    
    const result = await this.readOnlyDB.query(sql, params);
    
    // 총 개수 조회
    let countSql = 'SELECT COUNT(*) as total FROM order_view WHERE user_id = $1';
    const countParams: any[] = [query.userId];
    
    if (query.status) {
      countSql += ' AND status = $2';
      countParams.push(query.status);
    }
    
    const countResult = await this.readOnlyDB.query(countSql, countParams);
    const total = parseInt(countResult.rows[0].total);
    
    return {
      orders: result.rows,
      pagination: {
        page: query.page,
        limit: query.limit,
        total,
        totalPages: Math.ceil(total / query.limit)
      }
    };
  }

  private async handleGetOrdersByStatus(query: GetOrdersByStatusQuery): Promise<any> {
    const offset = (query.page - 1) * query.limit;
    
    const result = await this.readOnlyDB.query(
      `SELECT * FROM order_view 
       WHERE status = $1 
       ORDER BY created_at DESC 
       LIMIT $2 OFFSET $3`,
      [query.status, query.limit, offset]
    );
    
    const countResult = await this.readOnlyDB.query(
      'SELECT COUNT(*) as total FROM order_view WHERE status = $1',
      [query.status]
    );
    
    const total = parseInt(countResult.rows[0].total);
    
    return {
      orders: result.rows,
      pagination: {
        page: query.page,
        limit: query.limit,
        total,
        totalPages: Math.ceil(total / query.limit)
      }
    };
  }
}
```

### 4.8 프로젝션 구현

```typescript
// src/infrastructure/projections/OrderProjection.ts
import { Event } from '../eventstore/PostgreSQLEventStore';
import { ReadOnlyDatabase } from '../database/ReadOnlyDatabase';

export class OrderProjection {
  constructor(private readOnlyDB: ReadOnlyDatabase) {}

  async handle(event: Event): Promise<void> {
    try {
      switch (event.type) {
        case 'OrderCreatedEvent':
          await this.handleOrderCreated(event);
          break;
        case 'OrderItemAddedEvent':
          await this.handleOrderItemAdded(event);
          break;
        case 'OrderItemRemovedEvent':
          await this.handleOrderItemRemoved(event);
          break;
        case 'PaymentCompletedEvent':
          await this.handlePaymentCompleted(event);
          break;
        case 'ShippingStartedEvent':
          await this.handleShippingStarted(event);
          break;
        case 'OrderCancelledEvent':
          await this.handleOrderCancelled(event);
          break;
      }
    } catch (error) {
      console.error(`Error handling event ${event.type}:`, error);
      // 에러 로깅 및 재시도 로직
      await this.logFailedEvent(event, error);
    }
  }

  private async handleOrderCreated(event: Event): Promise<void> {
    const data = event.data;
    
    await this.readOnlyDB.query(
      `INSERT INTO order_view (
        order_id, user_id, status, total_amount, 
        shipping_address, items, created_at, updated_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
      [
        data.orderId,
        data.userId,
        'PENDING',
        data.totalAmount,
        JSON.stringify(data.shippingAddress),
        JSON.stringify(data.items),
        data.timestamp,
        data.timestamp
      ]
    );
  }

  private async handleOrderItemAdded(event: Event): Promise<void> {
    const data = event.data;
    
    // 기존 주문 조회
    const orderResult = await this.readOnlyDB.query(
      'SELECT items FROM order_view WHERE order_id = $1',
      [data.orderId]
    );
    
    if (orderResult.rows.length === 0) {
      throw new Error(`Order not found: ${data.orderId}`);
    }
    
    const currentItems = JSON.parse(orderResult.rows[0].items);
    currentItems.push(data.item);
    
    await this.readOnlyDB.query(
      'UPDATE order_view SET items = $1, total_amount = $2, updated_at = $3 WHERE order_id = $4',
      [JSON.stringify(currentItems), data.newTotalAmount, data.timestamp, data.orderId]
    );
  }

  private async handleOrderItemRemoved(event: Event): Promise<void> {
    const data = event.data;
    
    // 기존 주문 조회
    const orderResult = await this.readOnlyDB.query(
      'SELECT items FROM order_view WHERE order_id = $1',
      [data.orderId]
    );
    
    if (orderResult.rows.length === 0) {
      throw new Error(`Order not found: ${data.orderId}`);
    }
    
    const currentItems = JSON.parse(orderResult.rows[0].items);
    const updatedItems = currentItems.filter((item: any) => item.productId !== data.productId);
    
    await this.readOnlyDB.query(
      'UPDATE order_view SET items = $1, total_amount = $2, updated_at = $3 WHERE order_id = $4',
      [JSON.stringify(updatedItems), data.newTotalAmount, data.timestamp, data.orderId]
    );
  }

  private async handlePaymentCompleted(event: Event): Promise<void> {
    const data = event.data;
    
    await this.readOnlyDB.query(
      'UPDATE order_view SET status = $1, payment_id = $2, updated_at = $3 WHERE order_id = $4',
      ['PAID', data.paymentId, data.timestamp, data.orderId]
    );
  }

  private async handleShippingStarted(event: Event): Promise<void> {
    const data = event.data;
    
    await this.readOnlyDB.query(
      'UPDATE order_view SET status = $1, tracking_number = $2, updated_at = $3 WHERE order_id = $4',
      ['SHIPPED', data.trackingNumber, data.timestamp, data.orderId]
    );
  }

  private async handleOrderCancelled(event: Event): Promise<void> {
    const data = event.data;
    
    await this.readOnlyDB.query(
      'UPDATE order_view SET status = $1, cancelled_at = $2, cancellation_reason = $3, updated_at = $4 WHERE order_id = $5',
      ['CANCELLED', data.timestamp, data.reason, data.timestamp, data.orderId]
    );
  }

  private async logFailedEvent(event: Event, error: Error): Promise<void> {
    await this.readOnlyDB.query(
      `INSERT INTO failed_events (event_type, event_data, error_message, created_at)
       VALUES ($1, $2, $3, $4)`,
      [event.type, JSON.stringify(event.data), error.message, new Date()]
    );
  }
}
```

### 4.9 에러 처리 및 재시도 로직

```typescript
// src/infrastructure/retry/RetryPolicy.ts
export interface RetryPolicy {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  backoffMultiplier: number;
  jitter: boolean;
}

export class ExponentialBackoffRetryPolicy implements RetryPolicy {
  constructor(
    public maxAttempts: number = 3,
    public baseDelay: number = 1000,
    public maxDelay: number = 10000,
    public backoffMultiplier: number = 2,
    public jitter: boolean = true
  ) {}

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    let lastError: Error;
    
    for (let attempt = 1; attempt <= this.maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        
        if (attempt === this.maxAttempts) {
          break;
        }
        
        const delay = this.calculateDelay(attempt);
        await this.sleep(delay);
      }
    }
    
    throw lastError!;
  }

  private calculateDelay(attempt: number): number {
    let delay = this.baseDelay * Math.pow(this.backoffMultiplier, attempt - 1);
    delay = Math.min(delay, this.maxDelay);
    
    if (this.jitter) {
      delay = delay * (0.5 + Math.random() * 0.5);
    }
    
    return delay;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// 에러 분류 및 처리
export class EventSourcingError extends Error {
  constructor(message: string, public readonly retryable: boolean = false) {
    super(message);
    this.name = 'EventSourcingError';
  }
}

export class ConcurrencyError extends EventSourcingError {
  constructor(message: string) {
    super(message, true);
    this.name = 'ConcurrencyError';
  }
}

export class AggregateNotFoundError extends EventSourcingError {
  constructor(aggregateId: string) {
    super(`Aggregate not found: ${aggregateId}`, false);
    this.name = 'AggregateNotFoundError';
  }
}
```

### 4.10 통합 테스트 예제

```typescript
// tests/integration/OrderAggregateTest.ts
import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { PostgreSQLEventStore } from '../../src/infrastructure/eventstore/PostgreSQLEventStore';
import { OrderAggregate } from '../../src/core/aggregates/OrderAggregate';
import { OrderCommandHandler } from '../../src/core/handlers/OrderCommandHandler';
import { CreateOrderCommand, CompletePaymentCommand } from '../../src/core/commands/OrderCommands';

describe('OrderAggregate Integration Tests', () => {
  let eventStore: PostgreSQLEventStore;
  let commandHandler: OrderCommandHandler;

  beforeEach(async () => {
    eventStore = new PostgreSQLEventStore(process.env.DATABASE_URL!);
    commandHandler = new OrderCommandHandler(eventStore);
  });

  afterEach(async () => {
    await eventStore.close();
  });

  it('should create order and complete payment', async () => {
    const orderId = 'order-123';
    const userId = 'user-456';
    
    const items = [
      {
        productId: 'product-1',
        productName: 'Test Product',
        quantity: 2,
        unitPrice: 29.99
      }
    ];
    
    const shippingAddress = {
      street: '123 Main St',
      city: 'Seoul',
      state: 'Seoul',
      zipCode: '12345',
      country: 'South Korea'
    };

    // 주문 생성
    const createCommand = new CreateOrderCommand(orderId, userId, items, shippingAddress);
    await commandHandler.handle(createCommand);

    // 주문 상태 확인
    const events = await eventStore.getEvents(orderId);
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('OrderCreatedEvent');
    expect(events[0].data.totalAmount).toBe(59.98);

    // 결제 완료
    const paymentCommand = new CompletePaymentCommand(orderId, 'payment-789');
    await commandHandler.handle(paymentCommand);

    // 이벤트 확인
    const updatedEvents = await eventStore.getEvents(orderId);
    expect(updatedEvents).toHaveLength(2);
    expect(updatedEvents[1].type).toBe('PaymentCompletedEvent');
    expect(updatedEvents[1].data.paymentId).toBe('payment-789');
  });

  it('should handle concurrency conflicts', async () => {
    const orderId = 'order-concurrent';
    const userId = 'user-456';
    
    const items = [
      {
        productId: 'product-1',
        productName: 'Test Product',
        quantity: 1,
        unitPrice: 10.00
      }
    ];
    
    const shippingAddress = {
      street: '123 Main St',
      city: 'Seoul',
      state: 'Seoul',
      zipCode: '12345',
      country: 'South Korea'
    };

    // 동시에 두 개의 명령 실행
    const createCommand1 = new CreateOrderCommand(orderId, userId, items, shippingAddress);
    const createCommand2 = new CreateOrderCommand(orderId, userId, items, shippingAddress);

    // 첫 번째 명령은 성공해야 함
    await commandHandler.handle(createCommand1);

    // 두 번째 명령은 동시성 오류를 발생시켜야 함
    await expect(commandHandler.handle(createCommand2)).rejects.toThrow('ConcurrencyError');
  });

  it('should create and restore from snapshot', async () => {
    const orderId = 'order-snapshot';
    const userId = 'user-456';
    
    const items = [
      {
        productId: 'product-1',
        productName: 'Test Product',
        quantity: 1,
        unitPrice: 10.00
      }
    ];
    
    const shippingAddress = {
      street: '123 Main St',
      city: 'Seoul',
      state: 'Seoul',
      zipCode: '12345',
      country: 'South Korea'
    };

    // 주문 생성
    const createCommand = new CreateOrderCommand(orderId, userId, items, shippingAddress);
    await commandHandler.handle(createCommand);

    // 스냅샷 생성 (테스트를 위해 강제로)
    const order = await commandHandler.loadAggregate(orderId);
    const snapshot = {
      streamId: orderId,
      version: order.getVersion(),
      data: order.createSnapshot(),
      timestamp: new Date()
    };
    await eventStore.saveSnapshot(snapshot);

    // 스냅샷에서 복원 테스트
    const restoredOrder = await commandHandler.loadAggregate(orderId);
    expect(restoredOrder.getUserId()).toBe(userId);
    expect(restoredOrder.getTotalAmount()).toBe(10.00);
    expect(restoredOrder.getStatus()).toBe('PENDING');
  });
});
```

## 결론

이벤트 소싱과 CQRS는 현대적인 분산 시스템의 핵심 패턴입니다. 이벤트 소싱을 통해 완전한 감사 추적과 상태 재구성이 가능하며, CQRS를 통해 명령과 쿼리의 책임을 분리하여 성능과 확장성을 향상시킬 수 있습니다.

### 핵심 원칙 요약

1. **이벤트 소싱**: 상태 변경을 이벤트로 저장하여 완전한 감사 추적 제공
2. **CQRS**: 명령과 쿼리의 책임 분리로 성능과 확장성 향상
3. **프로젝션**: 이벤트를 읽기 최적화된 뷰로 변환
4. **애그리게이트**: 도메인 로직을 캡슐화하는 일관성 경계
5. **스냅샷**: 성능 최적화를 위한 주기적 상태 저장
6. **재시도 로직**: 장애 상황에서의 안정적인 처리

이러한 패턴들을 적절히 조합하여 안정적이고 확장 가능한 분산 시스템을 구축하세요.
