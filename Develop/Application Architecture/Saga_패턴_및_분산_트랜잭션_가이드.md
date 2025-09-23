# Saga 패턴 및 분산 트랜잭션 가이드 (Saga Pattern & Distributed Transaction Guide)

## 목차 (Table of Contents)
1. [Saga 패턴을 통한 분산 트랜잭션 관리 (Saga Pattern for Distributed Transaction Management)](#saga-패턴을-통한-분산-트랜잭션-관리-saga-pattern-for-distributed-transaction-management)
2. [분산 트랜잭션 패턴 (Distributed Transaction Patterns)](#분산-트랜잭션-패턴-distributed-transaction-patterns)
3. [보상 트랜잭션 (Compensating Transactions)](#보상-트랜잭션-compensating-transactions)

## Saga 패턴을 통한 분산 트랜잭션 관리 (Saga Pattern for Distributed Transaction Management)

### 1. Choreography Saga

```javascript
class OrderSaga {
  constructor(eventBus) {
    this.eventBus = eventBus;
  }
  
  async startOrderProcess(orderData) {
    // 1. 주문 생성
    const order = await this.createOrder(orderData);
    
    // 2. 결제 요청 이벤트 발행
    await this.eventBus.publish('PaymentRequested', {
      orderId: order.id,
      amount: order.amount,
      userId: order.userId
    });
    
    return order;
  }
  
  async handlePaymentCompleted(event) {
    const { orderId } = event;
    
    try {
      // 3. 재고 차감 요청
      await this.eventBus.publish('InventoryReservationRequested', {
        orderId,
        items: event.items
      });
    } catch (error) {
      // 결제 취소
      await this.eventBus.publish('PaymentCancelled', { orderId });
    }
  }
  
  async handleInventoryReserved(event) {
    const { orderId } = event;
    
    try {
      // 4. 배송 요청
      await this.eventBus.publish('ShippingRequested', {
        orderId,
        address: event.address
      });
    } catch (error) {
      // 재고 복구 및 결제 취소
      await this.eventBus.publish('InventoryReleased', { orderId });
      await this.eventBus.publish('PaymentCancelled', { orderId });
    }
  }
  
  async handleShippingCompleted(event) {
    const { orderId } = event;
    
    // 5. 주문 완료
    await this.eventBus.publish('OrderCompleted', { orderId });
  }
  
  // 보상 트랜잭션들
  async handlePaymentFailed(event) {
    const { orderId } = event;
    await this.cancelOrder(orderId, 'Payment failed');
  }
  
  async handleInventoryInsufficient(event) {
    const { orderId } = event;
    await this.eventBus.publish('PaymentCancelled', { orderId });
    await this.cancelOrder(orderId, 'Insufficient inventory');
  }
}
```

### 2. Orchestration Saga

```javascript
class OrderSagaOrchestrator {
  constructor(services) {
    this.orderService = services.orderService;
    this.paymentService = services.paymentService;
    this.inventoryService = services.inventoryService;
    this.shippingService = services.shippingService;
  }
  
  async executeOrderSaga(orderData) {
    const sagaId = this.generateSagaId();
    const sagaState = {
      sagaId,
      orderId: null,
      paymentId: null,
      inventoryReservationId: null,
      shippingId: null,
      status: 'STARTED',
      steps: []
    };
    
    try {
      // 1. 주문 생성
      sagaState.orderId = await this.orderService.createOrder(orderData);
      sagaState.steps.push({ step: 'ORDER_CREATED', success: true });
      
      // 2. 결제 처리
      sagaState.paymentId = await this.paymentService.processPayment({
        orderId: sagaState.orderId,
        amount: orderData.amount
      });
      sagaState.steps.push({ step: 'PAYMENT_PROCESSED', success: true });
      
      // 3. 재고 차감
      sagaState.inventoryReservationId = await this.inventoryService.reserveInventory({
        orderId: sagaState.orderId,
        items: orderData.items
      });
      sagaState.steps.push({ step: 'INVENTORY_RESERVED', success: true });
      
      // 4. 배송 요청
      sagaState.shippingId = await this.shippingService.createShipping({
        orderId: sagaState.orderId,
        address: orderData.address
      });
      sagaState.steps.push({ step: 'SHIPPING_CREATED', success: true });
      
      sagaState.status = 'COMPLETED';
      return sagaState;
      
    } catch (error) {
      sagaState.status = 'FAILED';
      sagaState.error = error.message;
      
      // 보상 트랜잭션 실행
      await this.compensateSaga(sagaState);
      
      throw error;
    }
  }
  
  async compensateSaga(sagaState) {
    const steps = sagaState.steps.reverse(); // 역순으로 실행
    
    for (const step of steps) {
      if (step.success) {
        try {
          await this.executeCompensation(step.step, sagaState);
        } catch (error) {
          console.error(`Compensation failed for step ${step.step}:`, error);
        }
      }
    }
  }
  
  async executeCompensation(step, sagaState) {
    switch (step) {
      case 'SHIPPING_CREATED':
        await this.shippingService.cancelShipping(sagaState.shippingId);
        break;
      case 'INVENTORY_RESERVED':
        await this.inventoryService.releaseInventory(sagaState.inventoryReservationId);
        break;
      case 'PAYMENT_PROCESSED':
        await this.paymentService.refundPayment(sagaState.paymentId);
        break;
      case 'ORDER_CREATED':
        await this.orderService.cancelOrder(sagaState.orderId);
        break;
    }
  }
  
  generateSagaId() {
    return `saga-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

### 3. Saga 상태 관리

```javascript
class SagaStateManager {
  constructor(database) {
    this.db = database;
  }
  
  async saveSagaState(sagaState) {
    await this.db.query(
      'INSERT INTO saga_states (saga_id, order_id, status, state_data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE status = ?, state_data = ?, updated_at = ?',
      [
        sagaState.sagaId,
        sagaState.orderId,
        sagaState.status,
        JSON.stringify(sagaState),
        new Date(),
        new Date(),
        sagaState.status,
        JSON.stringify(sagaState),
        new Date()
      ]
    );
  }
  
  async getSagaState(sagaId) {
    const result = await this.db.query(
      'SELECT * FROM saga_states WHERE saga_id = ?',
      [sagaId]
    );
    
    if (result.length === 0) {
      return null;
    }
    
    return JSON.parse(result[0].state_data);
  }
  
  async updateSagaState(sagaId, updates) {
    const currentState = await this.getSagaState(sagaId);
    if (!currentState) {
      throw new Error('Saga state not found');
    }
    
    const updatedState = { ...currentState, ...updates };
    await this.saveSagaState(updatedState);
    
    return updatedState;
  }
  
  async getFailedSagas() {
    const result = await this.db.query(
      'SELECT * FROM saga_states WHERE status = ?',
      ['FAILED']
    );
    
    return result.map(row => JSON.parse(row.state_data));
  }
}
```

## 분산 트랜잭션 패턴 (Distributed Transaction Patterns)

### 1. Two-Phase Commit (2PC)

```javascript
class TwoPhaseCommit {
  constructor(participants) {
    this.participants = participants;
  }
  
  async executeTransaction(transactionData) {
    const transactionId = this.generateTransactionId();
    
    try {
      // Phase 1: Prepare
      const prepareResults = await Promise.all(
        this.participants.map(participant => 
          participant.prepare(transactionId, transactionData)
        )
      );
      
      // 모든 참여자가 준비 완료했는지 확인
      const allPrepared = prepareResults.every(result => result.success);
      
      if (!allPrepared) {
        // Abort
        await this.abortTransaction(transactionId);
        throw new Error('Transaction preparation failed');
      }
      
      // Phase 2: Commit
      await this.commitTransaction(transactionId);
      
      return { success: true, transactionId };
      
    } catch (error) {
      await this.abortTransaction(transactionId);
      throw error;
    }
  }
  
  async commitTransaction(transactionId) {
    await Promise.all(
      this.participants.map(participant => 
        participant.commit(transactionId)
      )
    );
  }
  
  async abortTransaction(transactionId) {
    await Promise.all(
      this.participants.map(participant => 
        participant.abort(transactionId)
      )
    );
  }
  
  generateTransactionId() {
    return `tx-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

// 참여자 구현
class TransactionParticipant {
  constructor(serviceName, database) {
    this.serviceName = serviceName;
    this.db = database;
  }
  
  async prepare(transactionId, transactionData) {
    try {
      // 트랜잭션 데이터 검증 및 준비
      await this.validateTransaction(transactionData);
      
      // 준비 상태 저장
      await this.db.query(
        'INSERT INTO transaction_prepare (transaction_id, service_name, status, data) VALUES (?, ?, ?, ?)',
        [transactionId, this.serviceName, 'PREPARED', JSON.stringify(transactionData)]
      );
      
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
  
  async commit(transactionId) {
    const prepareData = await this.db.query(
      'SELECT * FROM transaction_prepare WHERE transaction_id = ? AND service_name = ?',
      [transactionId, this.serviceName]
    );
    
    if (prepareData.length === 0) {
      throw new Error('No prepared transaction found');
    }
    
    const transactionData = JSON.parse(prepareData[0].data);
    
    // 실제 트랜잭션 실행
    await this.executeTransaction(transactionData);
    
    // 준비 데이터 정리
    await this.db.query(
      'DELETE FROM transaction_prepare WHERE transaction_id = ? AND service_name = ?',
      [transactionId, this.serviceName]
    );
  }
  
  async abort(transactionId) {
    // 준비 데이터 정리
    await this.db.query(
      'DELETE FROM transaction_prepare WHERE transaction_id = ? AND service_name = ?',
      [transactionId, this.serviceName]
    );
  }
}
```

### 2. Three-Phase Commit (3PC)

```javascript
class ThreePhaseCommit {
  constructor(participants) {
    this.participants = participants;
  }
  
  async executeTransaction(transactionData) {
    const transactionId = this.generateTransactionId();
    
    try {
      // Phase 1: CanCommit
      const canCommitResults = await Promise.all(
        this.participants.map(participant => 
          participant.canCommit(transactionId, transactionData)
        )
      );
      
      if (!canCommitResults.every(result => result.canCommit)) {
        await this.abortTransaction(transactionId);
        throw new Error('Transaction cannot be committed');
      }
      
      // Phase 2: PreCommit
      await this.preCommitTransaction(transactionId);
      
      // Phase 3: DoCommit
      await this.doCommitTransaction(transactionId);
      
      return { success: true, transactionId };
      
    } catch (error) {
      await this.abortTransaction(transactionId);
      throw error;
    }
  }
  
  async preCommitTransaction(transactionId) {
    await Promise.all(
      this.participants.map(participant => 
        participant.preCommit(transactionId)
      )
    );
  }
  
  async doCommitTransaction(transactionId) {
    await Promise.all(
      this.participants.map(participant => 
        participant.doCommit(transactionId)
      )
    );
  }
  
  async abortTransaction(transactionId) {
    await Promise.all(
      this.participants.map(participant => 
        participant.abort(transactionId)
      )
    );
  }
}
```

## 보상 트랜잭션 (Compensating Transactions)

### 1. 보상 트랜잭션 패턴

```javascript
class CompensatingTransaction {
  constructor(services) {
    this.services = services;
    this.compensationLog = [];
  }
  
  async executeWithCompensation(operations) {
    const transactionId = this.generateTransactionId();
    const executedOperations = [];
    
    try {
      for (const operation of operations) {
        const result = await this.executeOperation(operation);
        executedOperations.push({
          operation,
          result,
          compensation: operation.compensation
        });
        
        // 보상 로그에 기록
        this.compensationLog.push({
          transactionId,
          operation: operation.name,
          compensation: operation.compensation
        });
      }
      
      return { success: true, results: executedOperations };
      
    } catch (error) {
      // 보상 트랜잭션 실행
      await this.executeCompensations(executedOperations.reverse());
      throw error;
    }
  }
  
  async executeOperation(operation) {
    switch (operation.type) {
      case 'CREATE_ORDER':
        return await this.services.orderService.createOrder(operation.data);
      case 'PROCESS_PAYMENT':
        return await this.services.paymentService.processPayment(operation.data);
      case 'RESERVE_INVENTORY':
        return await this.services.inventoryService.reserveInventory(operation.data);
      case 'CREATE_SHIPPING':
        return await this.services.shippingService.createShipping(operation.data);
      default:
        throw new Error(`Unknown operation type: ${operation.type}`);
    }
  }
  
  async executeCompensations(executedOperations) {
    for (const executedOp of executedOperations) {
      try {
        await this.executeCompensation(executedOp.operation, executedOp.result);
      } catch (error) {
        console.error(`Compensation failed for ${executedOp.operation.name}:`, error);
      }
    }
  }
  
  async executeCompensation(operation, result) {
    switch (operation.type) {
      case 'CREATE_ORDER':
        await this.services.orderService.cancelOrder(result.orderId);
        break;
      case 'PROCESS_PAYMENT':
        await this.services.paymentService.refundPayment(result.paymentId);
        break;
      case 'RESERVE_INVENTORY':
        await this.services.inventoryService.releaseInventory(result.reservationId);
        break;
      case 'CREATE_SHIPPING':
        await this.services.shippingService.cancelShipping(result.shippingId);
        break;
    }
  }
  
  generateTransactionId() {
    return `comp-tx-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

### 2. 보상 트랜잭션 서비스

```javascript
class CompensationService {
  constructor(database) {
    this.db = database;
  }
  
  async logCompensation(transactionId, operation, compensationData) {
    await this.db.query(
      'INSERT INTO compensation_log (transaction_id, operation, compensation_data, created_at) VALUES (?, ?, ?, ?)',
      [transactionId, operation, JSON.stringify(compensationData), new Date()]
    );
  }
  
  async getCompensations(transactionId) {
    const result = await this.db.query(
      'SELECT * FROM compensation_log WHERE transaction_id = ? ORDER BY created_at DESC',
      [transactionId]
    );
    
    return result.map(row => ({
      operation: row.operation,
      compensationData: JSON.parse(row.compensation_data),
      createdAt: row.created_at
    }));
  }
  
  async executeCompensation(transactionId, operation, compensationData) {
    try {
      await this.performCompensation(operation, compensationData);
      
      // 보상 완료 로그
      await this.db.query(
        'UPDATE compensation_log SET status = ?, completed_at = ? WHERE transaction_id = ? AND operation = ?',
        ['COMPLETED', new Date(), transactionId, operation]
      );
      
    } catch (error) {
      // 보상 실패 로그
      await this.db.query(
        'UPDATE compensation_log SET status = ?, error_message = ?, failed_at = ? WHERE transaction_id = ? AND operation = ?',
        ['FAILED', error.message, new Date(), transactionId, operation]
      );
      
      throw error;
    }
  }
  
  async performCompensation(operation, compensationData) {
    switch (operation) {
      case 'CANCEL_ORDER':
        await this.orderService.cancelOrder(compensationData.orderId);
        break;
      case 'REFUND_PAYMENT':
        await this.paymentService.refundPayment(compensationData.paymentId);
        break;
      case 'RELEASE_INVENTORY':
        await this.inventoryService.releaseInventory(compensationData.reservationId);
        break;
      case 'CANCEL_SHIPPING':
        await this.shippingService.cancelShipping(compensationData.shippingId);
        break;
      default:
        throw new Error(`Unknown compensation operation: ${operation}`);
    }
  }
}
```

### 3. 분산 트랜잭션 모니터링

```javascript
class DistributedTransactionMonitor {
  constructor(database) {
    this.db = database;
  }
  
  async monitorTransaction(transactionId) {
    const transaction = await this.getTransaction(transactionId);
    const participants = await this.getTransactionParticipants(transactionId);
    const compensations = await this.getCompensations(transactionId);
    
    return {
      transaction,
      participants,
      compensations,
      status: this.determineTransactionStatus(transaction, participants, compensations)
    };
  }
  
  async getTransaction(transactionId) {
    const result = await this.db.query(
      'SELECT * FROM transactions WHERE transaction_id = ?',
      [transactionId]
    );
    
    return result[0] || null;
  }
  
  async getTransactionParticipants(transactionId) {
    const result = await this.db.query(
      'SELECT * FROM transaction_participants WHERE transaction_id = ?',
      [transactionId]
    );
    
    return result;
  }
  
  async getCompensations(transactionId) {
    const result = await this.db.query(
      'SELECT * FROM compensation_log WHERE transaction_id = ?',
      [transactionId]
    );
    
    return result;
  }
  
  determineTransactionStatus(transaction, participants, compensations) {
    if (!transaction) {
      return 'NOT_FOUND';
    }
    
    if (transaction.status === 'COMPLETED') {
      return 'COMPLETED';
    }
    
    if (transaction.status === 'FAILED') {
      return 'FAILED';
    }
    
    // 진행 중인 트랜잭션 상태 확인
    const failedParticipants = participants.filter(p => p.status === 'FAILED');
    const completedParticipants = participants.filter(p => p.status === 'COMPLETED');
    
    if (failedParticipants.length > 0) {
      return 'COMPENSATING';
    }
    
    if (completedParticipants.length === participants.length) {
      return 'READY_TO_COMMIT';
    }
    
    return 'IN_PROGRESS';
  }
  
  async getStuckTransactions(timeoutMinutes = 30) {
    const timeoutDate = new Date(Date.now() - timeoutMinutes * 60 * 1000);
    
    const result = await this.db.query(
      'SELECT * FROM transactions WHERE status = ? AND created_at < ?',
      ['IN_PROGRESS', timeoutDate]
    );
    
    return result;
  }
  
  async retryFailedTransaction(transactionId) {
    const transaction = await this.getTransaction(transactionId);
    if (!transaction || transaction.status !== 'FAILED') {
      throw new Error('Transaction not found or not in failed state');
    }
    
    // 재시도 로직 구현
    const compensations = await this.getCompensations(transactionId);
    
    for (const compensation of compensations) {
      if (compensation.status === 'FAILED') {
        await this.executeCompensation(
          transactionId,
          compensation.operation,
          JSON.parse(compensation.compensation_data)
        );
      }
    }
    
    // 트랜잭션 상태 업데이트
    await this.db.query(
      'UPDATE transactions SET status = ?, retried_at = ? WHERE transaction_id = ?',
      ['RETRIED', new Date(), transactionId]
    );
  }
}
```

## 결론

Saga 패턴과 분산 트랜잭션 관리는 마이크로서비스 아키텍처에서 데이터 일관성을 보장하는 핵심 기술입니다. Choreography와 Orchestration 방식을 적절히 선택하고, 보상 트랜잭션을 통해 실패 시 일관성을 유지할 수 있습니다.

### 핵심 원칙 요약

1. **Saga 패턴**: 분산 트랜잭션을 여러 단계로 나누어 관리
2. **보상 트랜잭션**: 실패 시 이전 작업들을 되돌리는 메커니즘
3. **상태 관리**: 트랜잭션 진행 상황을 추적하고 관리
4. **모니터링**: 분산 트랜잭션의 상태를 실시간으로 모니터링

이러한 패턴들을 적절히 조합하여 안정적이고 일관성 있는 분산 시스템을 구축하세요.
