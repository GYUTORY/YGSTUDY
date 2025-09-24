const redis = require('redis');
const logger = require('./logger');

/**
 * 이벤트 기반 통신을 위한 Redis Pub/Sub 구현
 */
class EventBus {
  constructor(redisUrl = 'redis://localhost:6379') {
    this.redisUrl = redisUrl;
    this.publisher = null;
    this.subscriber = null;
    this.subscriptions = new Map();
    this.isConnected = false;
  }

  /**
   * EventBus 연결 초기화
   */
  async connect() {
    try {
      // Publisher 클라이언트 생성
      this.publisher = redis.createClient({
        url: this.redisUrl,
        retry_strategy: (options) => {
          if (options.error && options.error.code === 'ECONNREFUSED') {
            logger.error('Redis connection refused');
            return new Error('Redis connection refused');
          }
          if (options.total_retry_time > 1000 * 60 * 60) {
            logger.error('Redis retry time exhausted');
            return new Error('Retry time exhausted');
          }
          if (options.attempt > 10) {
            logger.error('Redis max retry attempts reached');
            return undefined;
          }
          return Math.min(options.attempt * 100, 3000);
        }
      });

      // Subscriber 클라이언트 생성
      this.subscriber = redis.createClient({
        url: this.redisUrl,
        retry_strategy: (options) => {
          if (options.error && options.error.code === 'ECONNREFUSED') {
            logger.error('Redis connection refused');
            return new Error('Redis connection refused');
          }
          if (options.total_retry_time > 1000 * 60 * 60) {
            logger.error('Redis retry time exhausted');
            return new Error('Retry time exhausted');
          }
          if (options.attempt > 10) {
            logger.error('Redis max retry attempts reached');
            return undefined;
          }
          return Math.min(options.attempt * 100, 3000);
        }
      });

      // 에러 핸들링
      this.publisher.on('error', (err) => {
        logger.error('Redis Publisher Error:', err);
      });

      this.subscriber.on('error', (err) => {
        logger.error('Redis Subscriber Error:', err);
      });

      // 연결 이벤트 핸들링
      this.publisher.on('connect', () => {
        logger.info('Redis Publisher connected');
      });

      this.subscriber.on('connect', () => {
        logger.info('Redis Subscriber connected');
      });

      // 연결
      await this.publisher.connect();
      await this.subscriber.connect();

      this.isConnected = true;
      logger.info('EventBus connected successfully');

    } catch (error) {
      logger.error('Failed to connect to EventBus:', error);
      throw error;
    }
  }

  /**
   * 이벤트 발행
   */
  async publish(eventType, data, options = {}) {
    if (!this.isConnected) {
      throw new Error('EventBus is not connected');
    }

    try {
      const event = {
        id: this.generateEventId(),
        type: eventType,
        data,
        timestamp: new Date().toISOString(),
        source: options.source || 'unknown',
        version: options.version || '1.0',
        metadata: options.metadata || {}
      };

      const channel = this.getChannelName(eventType);
      const message = JSON.stringify(event);

      await this.publisher.publish(channel, message);

      logger.info('Event published', {
        eventType,
        eventId: event.id,
        channel,
        source: event.source
      });

      return event.id;

    } catch (error) {
      logger.error('Failed to publish event:', error);
      throw error;
    }
  }

  /**
   * 이벤트 구독
   */
  async subscribe(eventType, handler, options = {}) {
    if (!this.isConnected) {
      throw new Error('EventBus is not connected');
    }

    try {
      const channel = this.getChannelName(eventType);
      const subscriptionId = this.generateSubscriptionId();

      // 구독 정보 저장
      this.subscriptions.set(subscriptionId, {
        eventType,
        channel,
        handler,
        options
      });

      // Redis 구독
      await this.subscriber.subscribe(channel, (message) => {
        this.handleMessage(eventType, message, handler);
      });

      logger.info('Event subscription created', {
        eventType,
        channel,
        subscriptionId
      });

      return subscriptionId;

    } catch (error) {
      logger.error('Failed to subscribe to event:', error);
      throw error;
    }
  }

  /**
   * 이벤트 구독 해제
   */
  async unsubscribe(subscriptionId) {
    try {
      const subscription = this.subscriptions.get(subscriptionId);
      if (!subscription) {
        logger.warn('Subscription not found:', subscriptionId);
        return;
      }

      await this.subscriber.unsubscribe(subscription.channel);
      this.subscriptions.delete(subscriptionId);

      logger.info('Event subscription removed', {
        subscriptionId,
        eventType: subscription.eventType
      });

    } catch (error) {
      logger.error('Failed to unsubscribe:', error);
      throw error;
    }
  }

  /**
   * 메시지 처리
   */
  async handleMessage(eventType, message, handler) {
    try {
      const event = JSON.parse(message);
      
      // 이벤트 검증
      if (!this.validateEvent(event)) {
        logger.warn('Invalid event received:', event);
        return;
      }

      // 핸들러 실행
      await handler(event);

      logger.debug('Event handled successfully', {
        eventType,
        eventId: event.id
      });

    } catch (error) {
      logger.error('Failed to handle event:', error);
    }
  }

  /**
   * 이벤트 검증
   */
  validateEvent(event) {
    return event &&
           event.id &&
           event.type &&
           event.data !== undefined &&
           event.timestamp &&
           event.source;
  }

  /**
   * 채널 이름 생성
   */
  getChannelName(eventType) {
    return `events:${eventType}`;
  }

  /**
   * 이벤트 ID 생성
   */
  generateEventId() {
    return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 구독 ID 생성
   */
  generateSubscriptionId() {
    return `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 연결 종료
   */
  async disconnect() {
    try {
      if (this.publisher) {
        await this.publisher.quit();
      }
      if (this.subscriber) {
        await this.subscriber.quit();
      }
      
      this.isConnected = false;
      this.subscriptions.clear();
      
      logger.info('EventBus disconnected');

    } catch (error) {
      logger.error('Failed to disconnect EventBus:', error);
      throw error;
    }
  }

  /**
   * 상태 확인
   */
  getStatus() {
    return {
      isConnected: this.isConnected,
      subscriptions: this.subscriptions.size,
      publisherConnected: this.publisher?.isReady || false,
      subscriberConnected: this.subscriber?.isReady || false
    };
  }
}

/**
 * 이벤트 타입 상수
 */
const EventTypes = {
  // 사용자 관련 이벤트
  USER_CREATED: 'user.created',
  USER_UPDATED: 'user.updated',
  USER_DELETED: 'user.deleted',
  USER_LOGIN: 'user.login',
  USER_LOGOUT: 'user.logout',

  // 주문 관련 이벤트
  ORDER_CREATED: 'order.created',
  ORDER_UPDATED: 'order.updated',
  ORDER_CANCELLED: 'order.cancelled',
  ORDER_SHIPPED: 'order.shipped',
  ORDER_DELIVERED: 'order.delivered',

  // 결제 관련 이벤트
  PAYMENT_INITIATED: 'payment.initiated',
  PAYMENT_COMPLETED: 'payment.completed',
  PAYMENT_FAILED: 'payment.failed',
  PAYMENT_REFUNDED: 'payment.refunded',

  // 시스템 이벤트
  SERVICE_STARTED: 'service.started',
  SERVICE_STOPPED: 'service.stopped',
  HEALTH_CHECK: 'health.check'
};

/**
 * 이벤트 핸들러 데코레이터
 */
function eventHandler(eventType, options = {}) {
  return function(target, propertyName, descriptor) {
    const originalMethod = descriptor.value;
    
    descriptor.value = async function(...args) {
      try {
        const result = await originalMethod.apply(this, args);
        
        // 이벤트 발행
        if (this.eventBus) {
          await this.eventBus.publish(eventType, result, {
            source: this.constructor.name,
            ...options
          });
        }
        
        return result;
      } catch (error) {
        logger.error(`Error in event handler ${eventType}:`, error);
        throw error;
      }
    };
    
    return descriptor;
  };
}

module.exports = {
  EventBus,
  EventTypes,
  eventHandler
};
