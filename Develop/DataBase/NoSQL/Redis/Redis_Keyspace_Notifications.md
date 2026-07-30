---
title: Redis 키스페이스 알림
tags: [Redis, Keyspace, Pub/Sub, 만료 이벤트, NoSQL]
updated: 2026-07-30
---

# Redis 키스페이스 알림

Redis는 키에 발생한 이벤트(만료, 삭제, 수정 등)를 Pub/Sub 채널로 발행하는 기능을 제공한다. 이 기능이 키스페이스 알림(Keyspace Notifications)이다.

기본적으로 비활성화 상태다. CPU 오버헤드가 있어 필요할 때만 켜야 한다.

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

**__keyspace@0__:mykey**
- 특정 키에서 발생한 모든 이벤트를 받는다
- 메시지 값은 이벤트 종류 (예: `expired`, `set`, `del`)
- "이 키가 어떻게 바뀌었나"가 필요할 때 사용

**__keyevent@0__:expired**
- 특정 이벤트가 발생한 모든 키를 받는다
- 메시지 값은 키 이름 (예: `session:abc123`)
- "만료된 키가 뭔가"가 필요할 때 사용

세션 만료 감지처럼 특정 이벤트 타입에 반응해야 할 때는 `__keyevent__` 채널이 더 낫다. 특정 키 하나의 생명주기를 추적할 때는 `__keyspace__` 채널이 맞다.

```
# __keyspace__ 구독 예시
SUBSCRIBE __keyspace@0__:user:1001

# __keyevent__ 구독 예시
SUBSCRIBE __keyevent@0__:expired
PSUBSCRIBE __keyevent@0__:*  # 모든 이벤트 패턴 구독
```

## 만료 이벤트 구독 실용 패턴

### 세션 만료 감지

사용자 세션 만료 시 정리 작업이 필요한 경우다. 예를 들어 세션이 만료될 때 해당 사용자의 락을 해제하거나 로그를 남겨야 하는 상황.

```python
import redis
import threading

r = redis.Redis(host='localhost', port=6379, db=0)

def handle_session_expire(message):
    expired_key = message['data'].decode('utf-8')
    if expired_key.startswith('session:'):
        user_id = expired_key.split(':')[1]
        # 세션 만료 처리 로직
        cleanup_user_resources(user_id)

def subscribe_expire_events():
    pubsub = r.pubsub()
    pubsub.subscribe(**{'__keyevent@0__:expired': handle_session_expire})
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            pass  # 핸들러가 처리

# 세션 설정 (TTL 30분)
r.setex('session:user123', 1800, 'active')
```

주의할 점이 있다. Redis의 만료는 지연 방식(lazy expiration)과 주기적 방식(periodic expiration)을 혼용한다. 키가 만료되어도 즉시 이벤트가 발행되지 않을 수 있다. 정확히 30분 후 이벤트가 온다고 보장하지 않는다. 수 초에서 수십 초 지연이 생길 수 있다.

### 캐시 무효화 트리거

캐시 키가 만료될 때 워커가 새 데이터를 미리 채워두는 패턴이다.

```python
def handle_cache_expire(message):
    expired_key = message['data'].decode('utf-8')
    if expired_key.startswith('cache:product:'):
        product_id = expired_key.split(':')[2]
        # 비동기로 캐시 재생성 요청
        task_queue.enqueue('refresh_product_cache', product_id)

pubsub = r.pubsub()
pubsub.subscribe(**{'__keyevent@0__:expired': handle_cache_expire})
```

이 패턴은 캐시 stampede(쏠림) 문제를 완화하는 데 쓸 수 있다. 만료 이벤트를 받아 하나의 워커만 캐시를 갱신하고, 나머지 요청은 기다리게 한다.

## 이벤트 유실 보장 없음

키스페이스 알림은 Pub/Sub 위에 구현되어 있다. Redis Pub/Sub은 Fire-and-Forget 방식이라 구독자가 연결되어 있지 않으면 이벤트가 사라진다. 메시지 큐가 아니다.

실무에서 겪는 문제 상황들이다.

**구독자 재시작 중 발생한 이벤트**: 애플리케이션 배포 중에 만료된 키는 이벤트를 받지 못한다. 이 사이에 세션이 만료된 사용자는 정리 작업이 누락된다.

**Redis 재시작**: Redis가 재시작되면 메모리에 있던 키들의 만료 이벤트가 발행되지 않는다.

**네트워크 단절**: 클라이언트와 Redis 사이 네트워크가 끊어졌다 복구되면 그 사이 이벤트는 없어진다.

키스페이스 알림만으로 중요한 비즈니스 로직을 처리하면 안 된다. 보완책이 필요하다. 만료 시 반드시 처리해야 하는 작업이라면 별도의 스케줄러로 주기적으로 검사하는 방식을 병행하거나, Redis Streams를 쓰는 편이 낫다.

## AOF 모드에서 동작 차이

AOF(Append Only File)가 활성화된 경우, 만료 이벤트 타이밍에 차이가 생긴다.

AOF 없이 운영할 때는 키 만료가 메모리에서만 추적되므로 이벤트 발행이 상대적으로 빠르다. AOF를 쓰면 Redis가 재시작 시 AOF를 재생하는데, 이 과정에서 과거에 만료됐어야 할 키들의 이벤트가 재생 중 발행되지 않는다. 재시작 후 처음 해당 키에 접근할 때(lazy expiration) 그제야 만료 처리가 일어난다.

RDB 스냅샷 방식도 마찬가지다. 스냅샷에 저장된 키는 Redis 재시작 후 이미 만료됐어도 이벤트 없이 조용히 삭제된다.

## Cluster 모드에서 동작 차이

Redis Cluster에서는 키스페이스 알림이 키가 위치한 노드에서만 발행된다. 슬롯에 따라 키가 여러 노드에 분산되므로, 모든 이벤트를 받으려면 모든 노드에 개별적으로 구독해야 한다.

```python
# Cluster 모드: 각 노드에 개별 구독 필요
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

Cluster 모드에서는 `notify-keyspace-events`를 각 노드 설정 파일에 개별적으로 설정해야 한다. `CONFIG SET`으로 런타임에 바꿔도 해당 노드에만 적용된다.

## 이벤트 폭풍 방지

트래픽이 많은 서비스에서 키스페이스 알림을 켜면 이벤트 폭풍이 생길 수 있다. 수천 개의 키가 동시에 만료되거나, SET 명령이 초당 수만 건 발생하는 상황이다.

**이벤트 범위 좁히기**

모든 이벤트(`A`)를 구독하지 말고 필요한 것만 켠다.

```bash
# 나쁜 설정 (모든 이벤트)
CONFIG SET notify-keyspace-events KEA

# 만료 이벤트만 필요한 경우
CONFIG SET notify-keyspace-events KEx
```

**키 네이밍으로 필터링**

`PSUBSCRIBE`의 패턴 기능으로 관심 있는 키만 구독한다.

```python
pubsub = r.pubsub()
# session: 으로 시작하는 키의 만료만
pubsub.psubscribe('__keyspace@0__:session:*')
```

**구독자 처리 속도 유지**

이벤트 처리가 느리면 Pub/Sub 버퍼가 쌓인다. Redis 클라이언트 라이브러리마다 내부 버퍼 한계가 있고, 넘어서면 메시지를 버린다. 이벤트를 받는 즉시 무거운 작업을 하지 말고, 큐에 넣고 별도 워커가 처리하는 구조가 낫다.

```python
def handle_expire(message):
    key = message['data'].decode('utf-8')
    # 직접 DB 조회하지 말고 큐에만 넣기
    job_queue.put(key)

# 별도 스레드에서 큐를 소비
def worker():
    while True:
        key = job_queue.get()
        process_expired_key(key)
```

**CPU 모니터링**

키스페이스 알림 활성화 자체가 Redis CPU를 올린다. `INFO stats`의 `keyspace_hits`, `keyspace_misses`로 키 접근 빈도를 확인하고, `redis-cli --latency`로 지연이 늘지 않는지 확인한다. 이벤트 폭풍이 의심되면 `MONITOR` 명령으로 실제 트래픽을 직접 확인하는 게 빠르다.
