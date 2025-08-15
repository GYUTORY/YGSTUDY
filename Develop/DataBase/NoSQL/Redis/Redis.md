---
title: Redis Remote Dictionary Server
tags: [database, nosql, redis]
updated: 2025-08-10
---
# Redis (Remote Dictionary Server)

## 1. Redis 소개
Redis는 오픈소스 인메모리 데이터 구조 저장소로, 다음과 같은 핵심 특징을 가집니다:

- **인메모리 데이터베이스**: 모든 데이터를 메모리에 저장하여 초고속 데이터 접근 가능
- **Key-Value 저장소**: 단순한 키-값 구조를 기반으로 다양한 데이터 타입 지원
- **고성능**: 초당 100,000+ 작업 처리, 마이크로초 단위의 응답 시간 제공
- **영속성**: RDB와 AOF를 통한 데이터 지속성 보장
- **분산 시스템**: 클러스터링과 샤딩을 통한 수평적 확장성

### 1.1 Redis의 역사와 발전
- 2009년 Salvatore Sanfilippo에 의해 개발
- 2015년 Redis Labs의 인수로 기업 지원 강화
- 현재 7.x 버전까지 발전하며 지속적인 기능 개선

### 1.2 Redis의 장점
1. **빠른 성능**
   - 인메모리 처리로 마이크로초 단위 응답
   - 단일 스레드 모델로 레이턴시 최소화
   - 비동기 I/O로 높은 처리량 달성

2. **다양한 데이터 타입**
   - String, Hash, List, Set, Sorted Set 등
   - 각 데이터 타입별 최적화된 명령어 제공
   - 복잡한 데이터 구조도 효율적으로 처리

3. **풍부한 기능**
   - Pub/Sub 메시징
   - Lua 스크립팅
   - 트랜잭션 지원
   - 키 만료 기능

![Redis.png](..%2F..%2F..%2F..%2Fetc%2Fimage%2FDataBase%2FNoSQL%2FRedis%2FRedis.png)

## 2. 데이터 타입

Redis는 5가지 주요 데이터 타입을 지원합니다:

### 2.1 String
- **특징**
  - 가장 기본적인 데이터 타입
  - 최대 512MB까지 저장 가능
  - 바이너리 안전 (binary-safe)
  - 정수형, 실수형, 문자열 모두 저장 가능

- **주요 명령어**
  ```redis
  SET key value [EX seconds] [PX milliseconds] [NX|XX]
  GET key
  INCR key
  DECR key
  MSET key1 value1 key2 value2
  MGET key1 key2
  ```

- **실제 사용 예시**
  ```redis

## 배경
  SET user:session:123 "user_data" EX 3600
  
  INCR page:views:homepage
  
  HSET user:1000 name "John" email "john@example.com" age "30"
  
  HSET product:123 name "iPhone" price "999" stock "50"
  
  HSET config:app theme "dark" language "ko" notifications "on"
  ```

### 2.3 List
- **특징**
  - 순서가 있는 문자열 목록
  - 양쪽 끝에서 O(1) 시간으로 삽입/삭제
  - 최대 2^32 - 1개의 요소 저장 가능
  - 블로킹 연산 지원

- **주요 명령어**
  ```redis
  LPUSH key value
  RPUSH key value
  LPOP key
  RPOP key
  LRANGE key start stop
  BLPOP key timeout
  ```

- **실제 사용 예시**
  ```redis

  LPUSH user:1000:activity "Logged in" "Viewed profile" "Posted comment"
  
  LPUSH job:queue "process_image_123"
  RPOP job:queue
  
  LPUSH user:1000:timeline "New post: Hello World!"
  ```

### 2.4 Set
- **특징**
  - 중복되지 않는 문자열 집합
  - O(1) 시간으로 멤버 추가/삭제/확인
  - 최대 2^32 - 1개의 멤버 저장 가능
  - 집합 연산 지원 (합집합, 교집합, 차집합)

- **주요 명령어**
  ```redis
  SADD key member
  SREM key member
  SISMEMBER key member
  SINTER key1 key2
  SUNION key1 key2
  ```

- **실제 사용 예시**
  ```redis

  SADD user:1000:tags "redis" "database" "nosql"
  
  SADD user:1000:friends "user:2000" "user:3000"
  
  SADD daily:visitors:2024-03-20 "192.168.1.1"
  ```

### 2.5 Sorted Set
- **특징**
  - 점수(score)와 연결된 문자열 집합
  - 점수로 정렬된 데이터 조회
  - O(log(N)) 시간으로 멤버 추가/삭제
  - 범위 기반 쿼리 지원

- **주요 명령어**
  ```redis
  ZADD key score member
  ZRANGE key start stop [WITHSCORES]
  ZREVRANGE key start stop [WITHSCORES]
  ZRANGEBYSCORE key min max
  ```

- **실제 사용 예시**
  ```redis

  ZADD leaderboard 100 "player1" 200 "player2" 150 "player3"
  
  ZADD game:ranking 1000 "user:1" 2000 "user:2"
  
  ZADD events 1647830400 "event1" 1647834000 "event2"
  ```

![Redis-DataType.png](..%2F..%2F..%2F..%2Fetc%2Fimage%2FDataBase%2FNoSQL%2FRedis%2FRedis-DataType.png)















## 3. 주요 기능

### 3.1 데이터 지속성
#### RDB (Redis Database)
- **특징**
  - 특정 시점의 메모리 데이터를 이진 파일로 저장
  - 포크를 사용한 비차단 백업
  - 압축된 단일 파일로 저장
  - 빠른 재시작과 복구

- **설정 예시**
  ```conf
  save 900 1      # 15분 동안 1개 이상 변경
  save 300 10     # 5분 동안 10개 이상 변경
  save 60 10000   # 1분 동안 10000개 이상 변경
  ```

#### AOF (Append Only File)
- **특징**
  - 모든 쓰기 작업을 로그 파일에 기록
  - 실시간 데이터 보호
  - 재실행을 통한 복구
  - 주기적인 파일 재작성

- **설정 예시**
  ```conf
  appendonly yes
  appendfsync everysec
  auto-aof-rewrite-percentage 100
  auto-aof-rewrite-min-size 64mb
  ```

### 3.2 고가용성
#### Redis Sentinel
- **기능**
  - 자동 장애 감지
  - 자동 페일오버
  - 구성 관리
  - 모니터링

- **설정 예시**
  ```conf
  sentinel monitor mymaster 127.0.0.1 6379 2
  sentinel down-after-milliseconds mymaster 5000
  sentinel failover-timeout mymaster 60000
  ```

#### Redis Cluster
- **특징**
  - 자동 샤딩
  - 마스터-슬레이브 복제
  - 자동 페일오버
  - 분산 데이터 저장

- **설정 예시**
  ```conf
  cluster-enabled yes
  cluster-config-file nodes.conf
  cluster-node-timeout 15000
  ```

### 3.3 확장성
- **수평적 확장**
  - 클러스터 모드에서 최대 1000개 노드
  - 자동 샤딩으로 데이터 분산
  - 동적 노드 추가/제거

- **성능 최적화**
  - 파이프라이닝
  - Lua 스크립팅
  - 트랜잭션
  - 키 만료

## 4. 주요 사용 사례

### 4.1 캐싱
- **웹 페이지 캐싱**
  ```redis

  SET query:users:active '["user1","user2"]' EX 600
  
  SET stats:daily:2024-03-20 '{"visits":1000}' EX 86400
  ```

### 4.2 세션 관리
- **사용자 세션**
  ```redis

  HSET session:123 user_id "1000" last_access "2024-03-20"
  EXPIRE session:123 3600
  
  EXISTS session:123
  ```

- **분산 세션**
  ```redis

  SET session:123:data '{"user_id":1000,"preferences":{}}' EX 3600
  
  EXPIRE session:123 3600
  ```

### 4.3 실시간 분석
- **페이지뷰 추적**
  ```redis

  INCR stats:visitors:2024-03-20
  
  INCR page:views:homepage
  ```

- **사용자 행동 분석**
  ```redis

  LPUSH user:1000:activity "viewed_product:123"
  
  ZINCRBY realtime:stats 1 "product:123"
  ```

### 4.4 메시지 큐
- **작업 큐**
  ```redis

  LPUSH job:queue "process_image_123"
  
  RPOP job:queue
  ```

- **이벤트 발행/구독**
  ```redis

  PUBLISH notifications "New message from user:1000"
  
  SUBSCRIBE notifications
  ```

### 4.5 게임 서비스
- **리더보드**
  ```redis

  ZADD leaderboard 1000 "player1"
  
  ZREVRANGE leaderboard 0 9 WITHSCORES
  ```

- **실시간 매칭**
  ```redis

  LPUSH matchmaking:queue "player1"
  
  RPOPLPUSH matchmaking:queue matchmaking:active
  ```

## 5. 운영 시 고려사항

### 5.1 메모리 관리
- **모니터링**
  ```redis

  INFO memory
  
  DBSIZE
  ```

- **메모리 정책**
  ```conf
  maxmemory 2gb
  maxmemory-policy allkeys-lru
  ```

- **TTL 설정**
  ```redis

  EXPIRE key 3600
  
  TTL key
  ```

### 5.2 성능 최적화
- **파이프라이닝**
  ```redis

  MULTI
  SET key1 value1
  SET key2 value2
  EXEC
  ```

- **Lua 스크립팅**
  ```lua
  -- 원자적 연산 수행
  redis.call('SET', KEYS[1], ARGV[1])
  redis.call('EXPIRE', KEYS[1], ARGV[2])
  ```

### 5.3 보안
- **인증 설정**
  ```conf
  requirepass your_strong_password
  ```

- **네트워크 보안**
  ```conf
  bind 127.0.0.1
  protected-mode yes
  ```

- **SSL/TLS 설정**
  ```conf
  tls-port 6379
  tls-cert-file /path/to/cert.pem
  tls-key-file /path/to/key.pem
  ```

### 5.4 모니터링
- **성능 지표**
  ```redis

  INFO
  
  INFO commandstats
  
  CLIENT LIST
  ```

- **로그 설정**
  ```conf
  loglevel notice
  logfile /var/log/redis/redis.log
  ```

## 6. 백업 전략

### 6.1 RDB 백업
- **장점**
  - 빠른 백업/복구
  - 작은 파일 크기
  - 단일 파일 관리 용이

- **단점**
  - 마지막 백업 이후 데이터 손실 가능
  - 포크로 인한 메모리 사용량 증가

### 6.2 AOF 백업
- **장점**
  - 데이터 손실 최소화
  - 실시간 데이터 보호
  - 재실행을 통한 복구

- **단점**
  - 큰 파일 크기
  - 긴 복구 시간
  - 디스크 I/O 부하

### 6.3 권장 사항
- **하이브리드 백업**
  ```conf

  0 0 * * * /path/to/backup.sh
  ```

- **재해 복구 계획**
  1. 정기적인 백업 테스트
  2. 복구 절차 문서화
  3. 모니터링 및 알림 설정

## 7. Redis 클라이언트

### 7.1 주요 클라이언트
- **Python**: redis-py
  ```python
  import redis
  r = redis.Redis(host='localhost', port=6379, db=0)
  r.set('key', 'value')
  ```

- **Node.js**: ioredis
  ```javascript
  const Redis = require('ioredis');
  const redis = new Redis();
  redis.set('key', 'value');
  ```

- **Java**: Jedis
  ```java
  Jedis jedis = new Jedis("localhost");
  jedis.set("key", "value");
  ```

### 7.2 클라이언트 모범 사례
- **연결 풀링**
- **재시도 로직**
- **에러 처리**
- **성능 최적화**

## 8. Redis 모니터링 도구

### 8.1 Redis CLI
- **기본 모니터링**
  ```bash
  redis-cli info
  redis-cli monitor
  ```

- **성능 분석**
  ```bash
  redis-cli --latency
  redis-cli --bigkeys
  ```

### 8.2 외부 모니터링 도구
- **RedisInsight**
- **Grafana + Prometheus**
- **Datadog**
- **New Relic**

## 9. Redis 클라우드 서비스

### 9.1 주요 제공업체
- **AWS ElastiCache**
- **Azure Cache for Redis**
- **Google Cloud Memorystore**
- **Redis Enterprise Cloud**

### 9.2 클라우드 서비스 선택 기준
- **가용성**
- **성능**
- **보안**
- **비용**
- **지원**

## 10. Redis 최신 트렌드

### 10.1 Redis Stack
- **RedisJSON**
- **RedisSearch**
- **RedisGraph**
- **RedisTimeSeries**

### 10.2 Redis 7.x 신기능
- **FUNCTION LOAD**
- **ACL 개선**
- **Sharded Pub/Sub**
- **Multi-part AOF**

```
출처
https://redis.io/documentation
https://aws.amazon.com/ko/elasticache/redis/
https://redis.com/redis-enterprise/redis-enterprise-cloud/overview/
https://redis.io/topics/clients

  # 캐시된 API 응답
  SET api:users:123 '{"name":"John","age":30}' EX 300
  ```

### 2.2 Hash
- **특징**
  - 필드와 값으로 구성된 객체 저장
  - 최대 2^32 - 1개의 필드-값 쌍 저장 가능
  - 메모리 효율적인 저장 방식
  - 부분 업데이트 가능

- **주요 명령어**
  ```redis
  HSET key field value
  HGET key field
  HGETALL key
  HMSET key field1 value1 field2 value2
  HDEL key field
  ```

- **실제 사용 예시**
  ```redis
  # HTML 페이지 캐싱
  SET page:home "<html>...</html>" EX 3600
  
  # API 응답 캐싱
  SET api:users:123 '{"name":"John"}' EX 300
  ```

- **데이터베이스 쿼리 캐싱**
  ```redis
  # RDB + AOF 조합
  save 900 1
  appendonly yes
  appendfsync everysec
  ```

- **백업 스케줄링**
  ```bash

