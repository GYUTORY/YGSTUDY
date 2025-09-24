const logger = require('../utils/logger');

/**
 * 서킷 브레이커 패턴 구현
 * 장애가 발생한 서비스를 일시적으로 차단하여 시스템 안정성 확보
 */
class CircuitBreaker {
  constructor(serviceUrl, options = {}) {
    this.serviceUrl = serviceUrl;
    this.timeout = options.timeout || 5000;
    this.threshold = options.threshold || 5;
    this.resetTimeout = options.resetTimeout || 30000;
    this.monitoringPeriod = options.monitoringPeriod || 10000;
    
    // 서킷 브레이커 상태
    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
    this.failureCount = 0;
    this.successCount = 0;
    this.lastFailureTime = null;
    this.nextAttemptTime = null;
    
    // 메트릭
    this.metrics = {
      totalRequests: 0,
      failedRequests: 0,
      successfulRequests: 0,
      circuitOpenCount: 0
    };

    // 주기적 상태 체크
    this.startMonitoring();
  }

  /**
   * 서비스 호출 실행
   */
  async execute(operation, fallback = null) {
    this.metrics.totalRequests++;

    // 서킷이 열려있는 경우
    if (this.state === 'OPEN') {
      if (this.shouldAttemptReset()) {
        this.state = 'HALF_OPEN';
        this.successCount = 0;
        logger.info(`Circuit breaker transitioning to HALF_OPEN for ${this.serviceUrl}`);
      } else {
        this.metrics.failedRequests++;
        this.metrics.circuitOpenCount++;
        
        if (fallback) {
          logger.warn(`Circuit breaker OPEN, using fallback for ${this.serviceUrl}`);
          return await fallback();
        }
        
        throw new Error(`Circuit breaker is OPEN for ${this.serviceUrl}`);
      }
    }

    try {
      // 타임아웃과 함께 작업 실행
      const result = await this.withTimeout(operation, this.timeout);
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      
      // 서킷이 열린 상태에서 폴백이 있으면 사용
      if (this.state === 'OPEN' && fallback) {
        logger.warn(`Operation failed, using fallback for ${this.serviceUrl}:`, error.message);
        return await fallback();
      }
      
      throw error;
    }
  }

  /**
   * 성공 처리
   */
  onSuccess() {
    this.successCount++;
    this.metrics.successfulRequests++;
    
    if (this.state === 'HALF_OPEN') {
      // HALF_OPEN 상태에서 성공하면 CLOSED로 전환
      this.state = 'CLOSED';
      this.failureCount = 0;
      this.lastFailureTime = null;
      this.nextAttemptTime = null;
      logger.info(`Circuit breaker transitioning to CLOSED for ${this.serviceUrl}`);
    }
  }

  /**
   * 실패 처리
   */
  onFailure() {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    this.metrics.failedRequests++;
    
    if (this.failureCount >= this.threshold) {
      this.state = 'OPEN';
      this.nextAttemptTime = Date.now() + this.resetTimeout;
      logger.error(`Circuit breaker transitioning to OPEN for ${this.serviceUrl} after ${this.failureCount} failures`);
    }
  }

  /**
   * 리셋 시도 여부 확인
   */
  shouldAttemptReset() {
    return this.nextAttemptTime && Date.now() >= this.nextAttemptTime;
  }

  /**
   * 타임아웃과 함께 작업 실행
   */
  async withTimeout(operation, timeout) {
    return Promise.race([
      operation(),
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error(`Operation timeout after ${timeout}ms`)), timeout)
      )
    ]);
  }

  /**
   * 서킷 브레이커 상태 반환
   */
  getState() {
    return {
      state: this.state,
      failureCount: this.failureCount,
      successCount: this.successCount,
      lastFailureTime: this.lastFailureTime,
      nextAttemptTime: this.nextAttemptTime,
      metrics: { ...this.metrics }
    };
  }

  /**
   * 서킷 브레이커 리셋
   */
  reset() {
    this.state = 'CLOSED';
    this.failureCount = 0;
    this.successCount = 0;
    this.lastFailureTime = null;
    this.nextAttemptTime = null;
    logger.info(`Circuit breaker manually reset for ${this.serviceUrl}`);
  }

  /**
   * 주기적 모니터링 시작
   */
  startMonitoring() {
    setInterval(() => {
      this.logMetrics();
    }, this.monitoringPeriod);
  }

  /**
   * 메트릭 로깅
   */
  logMetrics() {
    const state = this.getState();
    const failureRate = this.metrics.totalRequests > 0 
      ? (this.metrics.failedRequests / this.metrics.totalRequests * 100).toFixed(2)
      : 0;

    logger.info(`Circuit Breaker Metrics for ${this.serviceUrl}`, {
      state: state.state,
      failureRate: `${failureRate}%`,
      totalRequests: this.metrics.totalRequests,
      failedRequests: this.metrics.failedRequests,
      successfulRequests: this.metrics.successfulRequests,
      circuitOpenCount: this.metrics.circuitOpenCount
    });
  }
}

/**
 * 서킷 브레이커 팩토리
 */
class CircuitBreakerFactory {
  constructor() {
    this.breakers = new Map();
  }

  /**
   * 서킷 브레이커 생성 또는 반환
   */
  getBreaker(serviceUrl, options = {}) {
    if (!this.breakers.has(serviceUrl)) {
      this.breakers.set(serviceUrl, new CircuitBreaker(serviceUrl, options));
    }
    return this.breakers.get(serviceUrl);
  }

  /**
   * 모든 서킷 브레이커 상태 반환
   */
  getAllStates() {
    const states = {};
    for (const [url, breaker] of this.breakers) {
      states[url] = breaker.getState();
    }
    return states;
  }

  /**
   * 모든 서킷 브레이커 리셋
   */
  resetAll() {
    for (const breaker of this.breakers.values()) {
      breaker.reset();
    }
  }
}

module.exports = CircuitBreaker;
module.exports.CircuitBreakerFactory = CircuitBreakerFactory;
