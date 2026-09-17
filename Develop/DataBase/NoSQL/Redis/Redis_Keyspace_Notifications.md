---
title: Redis 키스페이스 알림
tags: [redis, nosql, database, backend, java, spring, nodejs]
updated: 2026-09-17
---

# Redis 키스페이스 알림

Redis는 키에 발생한 이벤트(만료, 삭제, 수정 등)를 Pub/Sub 채널로 발행하는 기능을 제공한다. 기본적으로 비활성화 상태다. CPU 오버헤드가 있어 필요할 때만 켜야 한다.

## notify-keyspace-events 설정

`redis.conf`나 런타임에 `CONFIG SET`으로 제어한다.

```bash
# 런타임 설정
CONFIG SET notify-keyspace-events KEx

# 확인
CONFIG GET notify-keyspace-events
```

설정값은 플래그 문자의 조합이다. 빈 문자열("")이면 비활성화다.

| 플래그 | 의미 |
|--------|------|
| K | 키스페이스 이벤트. `__keyspace@<db>__` 채널로 발행 |
| E | 키이벤트 이벤트. `__keyevent@<db>__` 채널로 발행 |
| g | 범용 명령 (DEL, EXPIRE, RENAME 등) |
| $ | 문자열 명령 (SET, GETSET 등) |
| l | 리스트 명령 (LPUSH, RPOP 등) |
| z | 정렬 집합 명령 (ZADD, ZREM 등) |
| x | 만료 이벤트 (키 TTL이 0이 되어 삭제될 때) |
| e | 퇴출 이벤트 (maxmemory 정책으로 삭제될 때) |
| d | 모듈 키 유형 이벤트 |
| t | 스트림 명령 |
| A | `g$lzxe`의 별칭 (모든 이벤트) |

K 또는 E 중 하나는 반드시 포함해야 채널 발행이 된다. 둘 다 없으면 설정이 무시된다.

실무에서 가장 많이 쓰는 조합은 `KEx`(만료 이벤트만)와 `KExg`(만료 + 범용 명령)다.

## __keyspace__ vs __keyevent__ 채널

두 채널은 같은 이벤트를 다른 관점에서 발행한다.

`__keyspace@0__:mykey`는 특정 키에서 발생한 모든 이벤트를 받는다. 메시지 값은 이벤트 종류(`expired`, `set`, `del` 등)다. 특정 키 하나의 생명주기를 추적할 때 쓴다.

`__keyevent@0__:expired`는 특정 이벤트가 발생한 모든 키를 받는다. 메시지 값은 키 이름이다. 세션 만료 감지처럼 특정 이벤트 타입에 반응해야 할 때 더 낫다.

```bash
# __keyspace__ 구독 예시
SUBSCRIBE __keyspace@0__:user:1001

# __keyevent__ 구독 예시
SUBSCRIBE __keyevent@0__:expired
PSUBSCRIBE __keyevent@0__:*  # 모든 이벤트 패턴 구독
```

## lazy expiration 타이밍 지연

만료 이벤트가 TTL 만료 시각에 정확히 오지 않는다. 이 지연의 원인을 모르면 의존하는 로직에서 타이밍 버그가 생긴다.

Redis는 두 가지 만료 처리 방식을 혼용한다.

**lazy expiration**: 만료된 키에 명령이 들어왔을 때 그 시점에 삭제한다. 삭제와 동시에 이벤트가 발행된다. 지연이 없지만, 아무도 접근하지 않으면 삭제가 일어나지 않는다.

**주기적 만료(active expiration)**: Redis의 서버 크론(`hz` 설정, 기본값 10)이 동작하는 주기마다 TTL이 있는 키들 중 20개를 무작위로 샘플링해서 만료된 것을 삭제한다. 20개 중 5개(25%) 이상이 만료됐으면 즉시 한 사이클을 더 돈다. 단, 한 사이클의 최대 처리 시간은 25ms로 제한된다.

`hz=10`이면 크론이 100ms마다 실행된다. 키가 만료됐는데 아무도 접근하지 않고 샘플링에서 계속 빠진다면 수백 ms가 지나도 이벤트가 오지 않는다. 만료 대상 키가 많아 샘플 중 25% 이상이 계속 걸리면 크론이 연속 실행되면서 다른 작업을 밀어내고, Redis 전체 응답 지연으로 이어진다. 이 상황에서 수 초 단위 지연이 실제로 발생한다.

`hz=100`으로 올리면 10ms 주기로 빨라지지만 CPU 사용률이 올라간다. 만료 이벤트의 정확한 타이밍이 중요하다면 `hz`를 높이되, CPU 여유를 확인하고 결정한다.

TTL 기반 로직에서 "정확히 N초 후 이벤트"를 보장 받으려 하면 안 된다. 지연을 전제로 설계해야 한다.

## 구현 패턴

### Python

```python
import redis
import threading

r = redis.Redis(host='localhost', port=6379, db=0)

def handle_session_expire(message):
    expired_key = message['data'].decode('utf-8')
    if expired_key.startswith('session:'):
        user_id = expired_key.split(':')[1]
        cleanup_user_resources(user_id)

def subscribe_expire_events():
    pubsub = r.pubsub()
    pubsub.subscribe(**{'__keyevent@0__:expired': handle_session_expire})
    for message in pubsub.listen():
        pass  # 핸들러가 처리

threading.Thread(target=subscribe_expire_events, daemon=True).start()
r.setex('session:user123', 1800, 'active')
```

### Java / Spring MessageListenerContainer

Spring Data Redis는 `RedisMessageListenerContainer`로 Pub/Sub 구독을 관리한다. 내부적으로 별도 스레드에서 블로킹 수신을 처리하고, 연결이 끊어지면 자동 재연결을 시도한다.

```java
@Configuration
public class RedisKeyspaceConfig {

    @Bean
    public RedisMessageListenerContainer keyspaceContainer(
            RedisConnectionFactory connectionFactory,
            SessionExpireListener listener) {
        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);
        container.addMessageListener(
            listener,
            new PatternTopic("__keyevent@0__:expired")
        );
        return container;
    }
}
```

```java
@Component
public class SessionExpireListener implements MessageListener {

    @Override
    public void onMessage(Message message, byte[] pattern) {
        String expiredKey = new String(message.getBody(), StandardCharsets.UTF_8);
        if (expiredKey.startsWith("session:")) {
            String userId = expiredKey.split(":")[1];
            cleanupUserResources(userId);
        }
    }
}
```

`MessageListener`를 직접 구현하는 대신 `MessageListenerAdapter`를 쓰면 POJO 메서드를 그대로 연결할 수 있다. 다만 타입 변환 오류가 런타임에 나오니 테스트를 충분히 해야 한다.

`addMessageListener`의 두 번째 인수는 `ChannelTopic`(정확한 채널)과 `PatternTopic`(글로브 패턴) 중 선택한다. 여러 db를 동시에 감시하거나 `__keyevent@*__:expired`처럼 와일드카드가 필요하면 `PatternTopic`을 쓴다.

### NestJS

NestJS에서는 `ioredis`의 `duplicate()`로 전용 구독 커넥션을 분리하는 게 표준 패턴이다. 일반 커맨드 커넥션과 Pub/Sub 커넥션은 프로토콜 상태가 다르기 때문에 같은 커넥션을 공유할 수 없다.

```typescript
import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class KeyspaceNotificationService implements OnModuleInit, OnModuleDestroy {
    private subscriber: Redis;

    constructor(@InjectRedis() private readonly redis: Redis) {}

    async onModuleInit() {
        this.subscriber = this.redis.duplicate();
        await this.subscriber.subscribe('__keyevent@0__:expired');
        this.subscriber.on('message', (_channel: string, key: string) => {
            if (key.startsWith('session:')) {
                this.handleSessionExpire(key);
            }
        });
    }

    async onModuleDestroy() {
        await this.subscriber.unsubscribe();
        this.subscriber.disconnect();
    }

    private handleSessionExpire(key: string) {
        const userId = key.split(':')[1];
        // 처리 로직
    }
}
```

`ioredis`는 연결 끊어짐을 감지하면 자동으로 재연결을 시도하지만, 재연결 후 subscribe는 자동으로 복구되지 않는다. 아래 구독자 장애 복구 절을 참고한다.

## 구독자 장애 복구와 자동 재구독

구독자 프로세스가 재시작되거나 네트워크가 끊어졌다 복구되면 그 사이 이벤트는 영구 소실된다. 이건 막을 수 없다. 다만 복구 후 구독을 자동으로 재개하는 처리가 없으면 이후 이벤트도 계속 놓치게 된다.

Python에서 재연결 루프를 직접 구현해야 하는 경우의 패턴이다:

```python
import redis
import time
import logging

logger = logging.getLogger(__name__)

class ResilientSubscriber:
    def __init__(self, redis_url: str, channel: str, handler):
        self.redis_url = redis_url
        self.channel = channel
        self.handler = handler
        self._stop = False

    def run(self):
        backoff = 1
        while not self._stop:
            try:
                r = redis.from_url(self.redis_url, socket_timeout=5)
                pubsub = r.pubsub()
                pubsub.subscribe(**{self.channel: self.handler})
                logger.info("subscribed: %s", self.channel)
                backoff = 1
                for message in pubsub.listen():
                    if self._stop:
                        break
            except (redis.RedisError, ConnectionError) as e:
                logger.warning("connection lost: %s, retry in %ds", e, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)  # 최대 60초 대기

    def stop(self):
        self._stop = True
```

지수 백오프를 넣지 않으면 Redis 재시작 직후 수백 번의 재연결 시도가 몰린다. 최대 대기 시간(위 예시에서 60초)도 서비스 SLA에 맞게 조정한다.

NestJS에서 `ioredis`의 재연결 후 자동 재구독 처리:

```typescript
async onModuleInit() {
    this.subscriber = this.redis.duplicate();
    
    // 재연결 시 subscribe 재등록
    this.subscriber.on('ready', async () => {
        await this.subscriber.subscribe('__keyevent@0__:expired');
        logger.log('re-subscribed to keyspace notifications');
    });

    this.subscriber.on('message', (_channel: string, key: string) => {
        this.handleExpiredKey(key);
    });
}
```

`ready` 이벤트는 최초 연결과 재연결 모두에서 발행된다. 최초 연결에서 subscribe를 호출하고 `ready`에서 또 호출하면 중복 구독이 된다. 위 패턴처럼 `ready`에서만 subscribe를 처리하거나, 상태 플래그로 최초 연결을 구분한다.

Spring의 `RedisMessageListenerContainer`는 내부적으로 재연결과 재구독을 처리한다. 하지만 Sentinel 환경에서는 별도 주의가 필요하다.

## Redis Sentinel 환경에서의 동작

Sentinel을 쓰는 환경에서 키스페이스 알림을 구독할 때 마스터 페일오버 타이밍에 이벤트 유실이 집중된다.

페일오버 과정을 순서대로 보면:

1. 마스터가 다운되거나 응답하지 않음
2. Sentinel이 이를 감지 (`down-after-milliseconds`, 기본값 30,000ms = 30초)
3. Sentinel들이 쿼럼을 맞춰 페일오버 결정 (수 초)
4. 슬레이브 하나를 마스터로 승격 (수 초)
5. 클라이언트가 구 마스터 연결 실패를 감지하고 Sentinel에 새 마스터 주소 조회
6. 새 마스터로 재연결 완료
7. 구독 채널 재등록

2~7 전체 과정에서 최소 30초 이상, 상황에 따라 60~90초의 갭이 생긴다. 이 시간 동안 발생한 키 만료 이벤트는 전부 사라진다.

Spring의 `RedisMessageListenerContainer`는 Lettuce 드라이버를 통해 재연결 후 자동으로 토픽을 재등록한다. 그러나 아래 상황에서 재등록이 누락되는 경우가 있다:

- `RedisConnectionFactory`를 직접 교체하거나 재초기화한 경우
- 컨테이너 `start()`를 호출했지만 Sentinel 주소 목록이 아직 갱신되지 않은 타이밍에 연결을 시도한 경우

Sentinel 환경에서 키스페이스 알림을 안정적으로 운영하려면 두 가지를 확인한다.

첫째, `RedisMessageListenerContainer`의 `setRecoveryInterval`을 서비스 요건에 맞게 설정한다. 기본값은 5000ms(5초)다.

```java
container.setRecoveryInterval(3000L); // 재연결 시도 간격 3초
```

둘째, 페일오버 기간 이벤트 유실을 보완하는 주기적 검사 로직을 병행한다. 키스페이스 알림을 "빠른 알림"으로 쓰고, 실제 정합성은 스케줄러가 책임지는 구조다.

Python이나 NestJS에서 Sentinel에 직접 연결할 때는 `redis-py`의 `Sentinel` 클래스나 `ioredis`의 Sentinel 옵션으로 마스터 주소를 동적으로 조회하도록 설정해야 한다. 고정 IP로 마스터에 직접 연결하면 페일오버 후 새 주소를 찾지 못한다.

```python
from redis.sentinel import Sentinel

sentinel = Sentinel([('sentinel1', 26379), ('sentinel2', 26379)], socket_timeout=0.1)
master = sentinel.master_for('mymaster', socket_timeout=0.1)

# 구독 전용 커넥션도 Sentinel 경유
subscriber_conn = sentinel.master_for('mymaster')
```

## 이벤트 유실 보장 없음

키스페이스 알림은 Pub/Sub 위에 구현되어 있다. Redis Pub/Sub은 Fire-and-Forget 방식이라 구독자가 연결되어 있지 않으면 이벤트가 사라진다. 메시지 큐가 아니다.

실무에서 겪는 유실 케이스다.

구독자 재시작 중 발생한 이벤트: 배포 중에 만료된 키는 이벤트를 받지 못한다. 무중단 배포를 해도 구 인스턴스가 종료되고 신 인스턴스가 구독하기까지의 갭은 피할 수 없다.

Redis 재시작: Redis가 재시작되면 메모리에 있던 키들의 만료 이벤트가 발행되지 않는다.

네트워크 단절: 클라이언트와 Redis 사이 네트워크가 끊어졌다 복구되면 그 사이 이벤트는 없어진다.

키스페이스 알림만으로 중요한 비즈니스 로직을 처리하면 안 된다. 만료 시 반드시 처리해야 하는 작업이라면 별도 스케줄러로 주기적으로 검사하거나 Redis Streams를 쓰는 편이 낫다.

## AOF 모드에서 동작 차이

AOF를 쓰면 Redis 재시작 시 AOF를 재생하는데, 이 과정에서 과거에 만료됐어야 할 키들의 이벤트가 재생 중 발행되지 않는다. 재시작 후 해당 키에 처음 접근할 때(lazy expiration) 그제야 만료 처리가 일어난다.

RDB 스냅샷 방식도 마찬가지다. 스냅샷에 저장된 키는 Redis 재시작 후 이미 만료됐어도 이벤트 없이 조용히 삭제된다.

## Cluster 모드에서 동작 차이

Redis Cluster에서는 키스페이스 알림이 키가 위치한 노드에서만 발행된다. 슬롯에 따라 키가 여러 노드에 분산되므로, 모든 이벤트를 받으려면 모든 노드에 개별적으로 구독해야 한다.

```python
nodes = [
    redis.Redis(host='node1', port=6379),
    redis.Redis(host='node2', port=6379),
    redis.Redis(host='node3', port=6379),
]

pubsub_list = []
for node in nodes:
    ps = node.pubsub()
    ps.subscribe('__keyevent@0__:expired')
    pubsub_list.append(ps)
```

단일 노드에만 구독하면 그 노드에 없는 키의 이벤트는 아예 받지 못한다. Cluster 환경에서 키스페이스 알림을 쓸 때 가장 많이 빠지는 함정이다.

`notify-keyspace-events`를 `CONFIG SET`으로 런타임에 바꿔도 해당 노드에만 적용된다. 각 노드 설정 파일에 개별적으로 넣거나, 노드 전체에 루프로 적용해야 한다.

## 이벤트 폭풍 방지

트래픽이 많은 서비스에서 키스페이스 알림을 켜면 이벤트 폭풍이 생길 수 있다.

이벤트 범위부터 좁힌다. 모든 이벤트(`A`)를 구독하지 말고 필요한 것만 켠다.

```bash
# 만료 이벤트만 필요한 경우
CONFIG SET notify-keyspace-events KEx
```

`PSUBSCRIBE`의 패턴 기능으로 관심 있는 키만 구독한다.

```python
pubsub = r.pubsub()
pubsub.psubscribe('__keyevent@0__:expired')
# 또는 키 패턴으로
pubsub.psubscribe('__keyspace@0__:session:*')
```

이벤트 처리가 느리면 Pub/Sub 버퍼가 쌓인다. Redis 클라이언트 라이브러리마다 내부 버퍼 한계가 있고, 넘어서면 메시지를 버린다. 이벤트를 받는 즉시 무거운 작업을 하지 말고, 큐에 넣고 별도 워커가 처리하는 구조가 낫다.

```python
from queue import Queue

job_queue = Queue()

def handle_expire(message):
    key = message['data'].decode('utf-8')
    job_queue.put(key)  # 즉시 반환

def worker():
    while True:
        key = job_queue.get()
        process_expired_key(key)  # 실제 처리는 여기서
```

키스페이스 알림 활성화 자체가 Redis CPU를 올린다. `INFO stats`의 `keyspace_hits`, `keyspace_misses`로 키 접근 빈도를 확인하고, `redis-cli --latency`로 지연이 늘지 않는지 확인한다.

## 디버깅

이벤트가 오지 않을 때 확인할 것들이다.

**설정 먼저 확인한다**

```bash
redis-cli CONFIG GET notify-keyspace-events
```

빈 문자열이면 비활성화 상태다. `K` 또는 `E` 플래그가 없어도 이벤트가 발행되지 않는다.

**redis-cli로 직접 구독 테스트**

애플리케이션 로직 없이 채널 자체에 이벤트가 오는지 먼저 확인한다.

```bash
# 터미널 1: 구독 대기
redis-cli subscribe __keyevent@0__:expired

# 터미널 2: 만료 키 생성
redis-cli setex debug:test:key 3 value
# 3초 후 터미널 1에 이벤트가 오면 설정과 채널은 정상
```

이 테스트에서 이벤트가 오는데 애플리케이션에서 못 받는다면, 구독 코드나 핸들러 쪽 문제다.

**채널 이름 오타 확인**

db 번호가 틀리거나 언더스코어 개수가 다른 경우가 많다. `__keyevent@0__:expired`에서 `@0__`을 `@0_`으로 쓰면 아무것도 오지 않는다.

```bash
# MONITOR로 실제 Pub/Sub 발행 여부 확인 (운영에서는 짧게만)
redis-cli MONITOR | grep -i "publish"
```

`MONITOR`는 모든 커맨드를 출력해서 Redis 성능에 영향을 준다. 운영 중이라면 수 초 이내로만 쓴다.

**만료 지연인지 유실인지 구분**

이벤트가 예상 시각보다 늦게 오면 지연이고, 아예 오지 않으면 유실이다. 테스트 키에 짧은 TTL을 걸고 `redis-cli subscribe`로 수신 시각을 기록해서 지연 폭을 측정한다.

**Spring MessageListenerContainer 연결 상태 확인**

`RedisMessageListenerContainer`가 실제로 구독 중인지 확인할 때:

```java
// 컨테이너가 실행 중인지
boolean running = container.isRunning();

// 등록된 리스너 목록 (디버그 로그 레벨에서 출력됨)
// logging.level.org.springframework.data.redis=DEBUG
```

`isRunning()`이 true여도 내부 연결이 끊어진 상태일 수 있다. `DEBUG` 로그로 재연결 시도 메시지를 확인한다.
