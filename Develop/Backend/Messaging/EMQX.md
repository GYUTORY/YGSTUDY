---
title: EMQX - 분산 MQTT 브로커 운영
tags: [EMQX, MQTT, IoT, Messaging, Broker, Cluster]
updated: 2026-06-15
---

# EMQX

EMQX는 Erlang/OTP로 만든 분산 MQTT 브로커다. 단일 노드에서 동시 커넥션 수백만 개를 버티는 게 목적이고, 여러 노드를 클러스터로 묶어 수평 확장한다. IoT 디바이스가 수십만~수백만 대 붙는 환경에서 메시지 라우팅, 인증/인가, 외부 시스템 연동까지 한 브로커로 처리하려고 쓴다.

MQTT 프로토콜 자체와 QoS, Retained Message 같은 개념은 [MQTT.md](../../Network/7%20Layer/Transport%20Layer/TCP/Mqtt/MQTT.md)에서 다룬다. 이 문서는 EMQX라는 구현체를 운영하면서 겪는 것들을 정리한다.

## 언제 EMQX를 쓰나

브로커를 고를 때 항상 나오는 후보가 Mosquitto, RabbitMQ MQTT 플러그인, EMQX 세 개다.

Mosquitto는 단일 프로세스 C 구현이라 가볍고 설정이 단순하다. 디바이스가 수천~수만 대고 클러스터링이 필요 없으면 Mosquitto가 운영 부담이 제일 적다. 단점은 기본 빌드가 클러스터링을 지원하지 않는다는 점이다. 브로커 한 대가 죽으면 그걸로 끝이고, 커넥션이 한 노드 용량을 넘으면 답이 없다.

RabbitMQ MQTT 플러그인은 이미 RabbitMQ를 AMQP로 쓰고 있는데 MQTT 디바이스 메시지도 같은 인프라에서 받고 싶을 때 쓴다. AMQP Consumer가 MQTT 메시지를 그대로 소비할 수 있는 게 장점이다. 다만 RabbitMQ는 MQTT 전용으로 설계된 게 아니라서 커넥션 수가 올라가면 메모리를 많이 먹고, MQTT 5.0 기능 지원도 EMQX보다 늦다. 자세한 건 [RabbitMQ_MQTT.md](RabbitMQ_MQTT.md)에 있다.

EMQX는 처음부터 대규모 동시 커넥션과 클러스터링을 목표로 만들었다. Erlang의 경량 프로세스 모델 덕에 커넥션 하나당 메모리 오버헤드가 작고, 노드를 추가하면 커넥션 용량이 선형에 가깝게 늘어난다. Rule Engine으로 메시지를 받아서 Kafka, PostgreSQL, Webhook으로 바로 흘려보내는 기능이 내장돼 있다. 디바이스가 많고, 무중단이 필요하고, 메시지를 외부 시스템으로 가공해서 보내야 하면 EMQX가 맞다.

정리하면 소규모 단일 노드는 Mosquitto, 기존 RabbitMQ 자산 활용은 플러그인, 대규모 분산은 EMQX다.

## 설치와 dashboard 접속

테스트 환경은 Docker 단일 노드로 띄우는 게 제일 빠르다.

```bash
docker run -d --name emqx \
  -p 1883:1883 \
  -p 8883:8883 \
  -p 8083:8083 \
  -p 8084:8084 \
  -p 18083:18083 \
  emqx/emqx:5.8.0
```

포트별 역할을 알아둬야 방화벽 열 때 헷갈리지 않는다.

- 1883: MQTT TCP (평문)
- 8883: MQTT TLS
- 8083: MQTT over WebSocket
- 8084: MQTT over WSS (TLS)
- 18083: 관리 dashboard (HTTP)

dashboard는 `http://localhost:18083`로 접속한다. 초기 계정은 `admin` / `public`이고, 첫 로그인 시 비밀번호를 바꾸라고 강제한다. 프로덕션에서 이 기본 계정을 안 바꾸고 18083을 외부에 노출했다가 사고 나는 경우가 실제로 있다. dashboard 포트는 내부망으로 막거나 reverse proxy 뒤에 둬야 한다.

dashboard에서 Overview를 보면 현재 커넥션 수, 메시지 in/out rate, 노드별 부하를 한눈에 본다. 운영 중에는 이 화면을 제일 자주 본다.

## 리스너 설정

EMQX 5.x는 `emqx.conf`를 HOCON 포맷으로 쓴다. 리스너를 직접 손볼 일이 많다.

```hocon
listeners.tcp.default {
  bind = "0.0.0.0:1883"
  max_connections = 1024000
  acceptors = 16
}

listeners.ssl.default {
  bind = "0.0.0.0:8883"
  max_connections = 512000
  ssl_options {
    keyfile = "/opt/emqx/etc/certs/key.pem"
    certfile = "/opt/emqx/etc/certs/cert.pem"
    cacertfile = "/opt/emqx/etc/certs/cacert.pem"
    verify = verify_none
  }
}
```

`max_connections`는 리스너별 커넥션 상한이다. 기본값이 무한대(`infinity`)인데, 실제로는 OS의 file descriptor 한계에 먼저 걸리니까 의미 있는 값으로 막아두는 게 낫다. 한 리스너가 노드 전체 리소스를 다 먹는 걸 방지한다.

`acceptors`는 새 커넥션을 받는 acceptor 프로세스 수다. 커넥션이 한꺼번에 몰리는 환경(디바이스가 동시에 재부팅돼서 재접속하는 상황)에서 이 값이 작으면 accept 큐가 밀린다. CPU 코어 수에 맞춰 늘린다.

TLS에서 `verify = verify_none`은 서버 인증서만 쓰고 클라이언트 인증서는 검증하지 않는다는 뜻이다. 디바이스에 클라이언트 인증서를 심는 mutual TLS를 하려면 `verify_peer`로 바꾸고 `fail_if_no_peer_cert = true`를 추가한다. 디바이스 펌웨어에 인증서 갱신 로직이 없으면 인증서 만료될 때 전 디바이스가 한꺼번에 접속 실패하니까, mutual TLS 도입 전에 갱신 운영을 먼저 설계해야 한다.

## 인증과 인가

인증(Authentication)은 "누가 접속할 수 있나", 인가(Authorization, ACL)는 "어떤 토픽에 publish/subscribe할 수 있나"를 정한다. EMQX는 둘을 별도 설정으로 관리한다.

### Built-in DB 인증

가장 간단한 건 내장 데이터베이스에 username/password를 저장하는 방식이다. dashboard의 Access Control > Authentication에서 추가하거나 HOCON으로 설정한다.

```hocon
authentication = [
  {
    mechanism = password_based
    backend = built_in_database
    password_hash_algorithm {
      name = sha256
      salt_position = suffix
    }
  }
]
```

사용자는 dashboard나 REST API로 등록한다.

```bash
curl -u admin:public -X POST 'http://localhost:18083/api/v5/authentication/password_based:built_in_database/users' \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "device001", "password": "secret"}'
```

디바이스가 수만 대면 built-in DB에 일일이 넣기 힘들다. 그땐 외부 DB나 JWT를 쓴다.

### MySQL/PostgreSQL 연동

디바이스 계정 정보가 이미 RDB에 있으면 거기서 바로 조회하게 한다.

```hocon
authentication = [
  {
    mechanism = password_based
    backend = postgresql
    server = "pg.internal:5432"
    database = "iot"
    username = "emqx"
    password = "emqx_pw"
    query = "SELECT password_hash, salt FROM devices WHERE username = ${username} LIMIT 1"
    password_hash_algorithm {
      name = sha256
      salt_position = suffix
    }
  }
]
```

`${username}`은 접속 시 클라이언트가 보낸 값으로 치환된다. 여기서 자주 실수하는 게 쿼리에 인덱스 안 걸린 컬럼을 쓰는 것이다. 디바이스가 동시에 수만 개 재접속하면 이 쿼리가 초당 수만 번 날아간다. `username` 컬럼에 인덱스가 없으면 DB가 먼저 죽는다. 인증 쿼리는 반드시 인덱스 탄 단일 row 조회여야 한다.

### JWT 인증

디바이스가 별도 인증 서버에서 토큰을 받아오는 구조면 JWT가 깔끔하다. EMQX는 토큰 서명만 검증하고 DB 조회를 안 하니까 부하가 제일 적다.

```hocon
authentication = [
  {
    mechanism = jwt
    use_jwks = false
    algorithm = "hmac-based"
    secret = "my-jwt-secret"
    verify_claims {
      username = "${username}"
    }
  }
]
```

JWT의 `exp` 클레임이 만료되면 EMQX가 커넥션을 끊는다. 디바이스가 토큰 갱신을 안 하면 만료 시점에 끊기니까, 토큰 수명과 디바이스의 재인증 주기를 맞춰야 한다. 토큰을 너무 짧게 잡으면 재접속 폭주가 주기적으로 발생한다.

### ACL 규칙

인증을 통과해도 아무 토픽이나 만지게 두면 안 된다. 디바이스 A가 디바이스 B의 토픽을 구독하는 걸 막아야 한다. ACL로 토픽 패턴을 제한한다.

```hocon
authorization {
  sources = [
    {
      type = built_in_database
    }
  ]
  no_match = deny
  deny_action = disconnect
}
```

`no_match = deny`는 어떤 ACL 규칙에도 안 걸리면 거부한다는 뜻이다. 기본값이 `allow`라서 모르고 두면 ACL을 걸어도 규칙 밖 토픽은 다 통과한다. 화이트리스트로 운영하려면 반드시 `deny`로 바꾼다.

규칙 예시는 디바이스가 자기 ID 하위 토픽만 쓰게 하는 형태다.

```
# device001은 device/device001/up 에만 publish, device/device001/down 만 subscribe
{allow, {username, "device001"}, publish, ["device/device001/up"]}.
{allow, {username, "device001"}, subscribe, ["device/device001/down"]}.
```

`${username}` 같은 치환자를 ACL에 쓰면 디바이스마다 규칙을 만들 필요 없이 한 줄로 끝난다.

```
{allow, all, publish, ["device/${username}/up"]}.
{allow, all, subscribe, ["device/${username}/down"]}.
```

## 클러스터 구성

노드 한 대로 부족하면 클러스터로 묶는다. 노드들이 서로를 찾는 방법(디스커버리)을 먼저 정해야 한다.

### 디스커버리 방식

`manual`은 노드를 띄운 뒤 `emqx_ctl cluster join`으로 직접 붙인다. 노드가 몇 개 안 되고 IP가 고정이면 쓴다.

`static`은 설정 파일에 노드 목록을 박아둔다. 노드 집합이 거의 안 바뀌는 온프레미스 환경에 맞다.

```hocon
cluster {
  discovery_strategy = static
  static {
    seeds = ["emqx@node1.internal", "emqx@node2.internal", "emqx@node3.internal"]
  }
}
```

`dns`는 DNS A 레코드나 SRV 레코드로 노드를 찾는다. Kubernetes의 headless service와 조합하면 Pod가 늘고 줄 때 자동으로 클러스터에 붙고 빠진다. 오토스케일 환경이면 사실상 이걸 쓴다.

```hocon
cluster {
  discovery_strategy = dns
  dns {
    name = "emqx-headless.default.svc.cluster.local"
    record_type = srv
  }
}
```

### core-replicant 아키텍처

EMQX 5.x는 노드를 core와 replicant 두 역할로 나눈다. core 노드는 클러스터 메타데이터(라우팅 테이블, 세션 정보)를 들고 합의에 참여한다. replicant 노드는 메타데이터를 읽기 전용으로 복제만 받고 합의에는 안 낀다.

core를 3~5대 정도 두고 디바이스 커넥션은 대부분 replicant가 받게 한다. 커넥션을 늘리려면 replicant만 추가하면 되니까 합의 비용 없이 커넥션 용량을 키울 수 있다. core는 홀수로 두는 게 좋다(분할 시 과반 판단). core가 전부 죽으면 replicant는 메타데이터를 못 받아서 정상 동작을 못 하니까, core 가용성을 우선 챙겨야 한다.

```hocon
node {
  role = replicant   # core 또는 replicant
}
```

### 쿠키 불일치 문제

클러스터가 안 붙을 때 십중팔구는 Erlang 쿠키 불일치다. Erlang 노드끼리 통신하려면 같은 쿠키 값을 공유해야 하는데, 노드마다 쿠키가 다르면 connection refused만 나고 원인 메시지가 친절하지 않다.

```bash
docker run -d --name emqx1 \
  -e EMQX_NODE__COOKIE="my-shared-cookie" \
  -e EMQX_CLUSTER__DISCOVERY_STRATEGY=static \
  ...
```

모든 노드에 `EMQX_NODE__COOKIE`를 같은 값으로 넣어야 한다. Docker Compose로 여러 노드 띄울 때 한 노드만 환경변수 오타가 나도 그 노드만 클러스터에서 빠진다. 클러스터가 안 붙으면 제일 먼저 `emqx_ctl cluster status`로 확인하고, 쿠키부터 의심한다. 노드 이름(`EMQX_NODE__NAME`)도 노드별로 유일해야 하고 hostname이 서로 resolve돼야 한다. 컨테이너 환경에서 hostname resolve가 안 돼서 안 붙는 경우도 흔하다.

## Rule Engine과 Data Bridge

EMQX의 진짜 쓸모는 메시지를 받아서 외부 시스템으로 흘려보내는 데 있다. Rule Engine이 SQL 비슷한 문법으로 메시지를 필터링/가공하고, Data Bridge가 목적지로 보낸다.

규칙은 SQL로 작성한다. 토픽에서 메시지를 뽑아 필요한 필드만 추린다.

```sql
SELECT
  payload.temperature as temp,
  payload.device_id as device_id,
  clientid,
  timestamp
FROM
  "device/+/up"
WHERE
  payload.temperature > 80
```

`device/+/up` 토픽으로 들어온 메시지 중 온도가 80을 넘는 것만 골라낸다. 이 결과를 Data Bridge로 연결한다.

### Kafka 연동

센서 데이터를 Kafka로 흘려서 다운스트림에서 스트림 처리하는 구조가 흔하다.

```hocon
bridges.kafka_producer.to_analytics {
  bootstrap_hosts = "kafka1:9092,kafka2:9092"
  topic = "iot-telemetry"
  message {
    key = "${clientid}"
    value = "${payload}"
  }
  buffer {
    mode = disk
    per_partition_limit = "2GB"
  }
}
```

`buffer.mode = disk`로 두면 Kafka가 잠깐 죽어도 메시지를 디스크에 버퍼링했다가 복구되면 보낸다. memory로 두면 Kafka 장애 시 버퍼가 차서 메시지를 버린다. 데이터 유실이 곤란하면 disk로 둔다. 다만 디스크 버퍼가 무한정 쌓이면 디스크가 꽉 차니까 `per_partition_limit`을 반드시 건다.

### PostgreSQL 연동

```hocon
bridges.pgsql.to_db {
  server = "pg.internal:5432"
  database = "iot"
  username = "emqx"
  sql = "INSERT INTO telemetry(device_id, temp, ts) VALUES (${device_id}, ${temp}, ${timestamp})"
}
```

여기서 자주 터지는 게 INSERT 부하다. 디바이스가 초당 수만 건 보내면 매 메시지마다 INSERT가 날아가서 DB가 못 버틴다. EMQX의 batch 설정으로 여러 메시지를 묶어 한 번에 INSERT하거나, 애초에 Kafka로 받아서 컨슈머가 배치 적재하는 구조로 가야 한다. 고빈도 텔레메트리를 RDB에 직접 꽂는 건 거의 항상 후회한다.

### Webhook 연동

```hocon
bridges.webhook.to_alert {
  url = "http://alert-service.internal/api/alert"
  method = post
  body = "${payload}"
  pool_size = 16
}
```

Webhook 대상 서비스가 느리면 EMQX 쪽 요청 큐가 밀린다. `pool_size`로 동시 요청 수를 조절하고, 대상 서비스에 타임아웃과 재시도 정책을 명확히 해둔다. 온도 임계 초과 같은 알림성 이벤트에만 Webhook을 쓰고, 전체 텔레메트리를 Webhook으로 보내려는 시도는 하지 않는다.

## Shared Subscription으로 부하 분산

일반 구독은 한 토픽을 구독한 모든 컨슈머가 같은 메시지를 다 받는다. 백엔드 컨슈머를 여러 개 띄워 메시지를 나눠 처리하고 싶으면 Shared Subscription을 쓴다. `$share/<group>/` 접두사를 붙인다.

```
$share/workers/device/+/up
```

`workers` 그룹에 컨슈머 3개가 같은 토픽을 구독하면, 메시지가 셋 중 하나로만 간다. 컨슈머를 늘리면 처리량이 늘어난다.

분배 방식은 `shared_subscription_strategy`로 정한다.

```hocon
mqtt {
  shared_subscription_strategy = round_robin
}
```

기본값 `random`은 메시지마다 랜덤 컨슈머를 고른다. `round_robin`은 순서대로 돌린다. `sticky`는 한 클라이언트의 메시지를 같은 컨슈머에 계속 보낸다. 주의할 점은 컨슈머가 죽었는데 EMQX가 아직 죽은 걸 모르는 짧은 순간에 그 컨슈머로 배정된 메시지가 유실될 수 있다는 것이다. QoS 1 이상으로 두고, 컨슈머가 처리 후 ACK하는 구조여야 죽은 컨슈머로 간 메시지가 재전송된다.

## Retained Message와 세션 영속성

Retained Message는 토픽에 마지막 메시지를 저장해두고, 나중에 그 토픽을 구독하는 클라이언트에게 즉시 한 번 보내는 기능이다. 디바이스의 마지막 상태(online/offline, 마지막 센서 값)를 새로 붙는 구독자에게 바로 알려줄 때 쓴다. publish할 때 retain 플래그를 켠다.

retained 메시지는 토픽당 하나만 유지된다. 새 메시지가 오면 덮어쓴다. 빈 페이로드로 retain publish하면 저장된 retained 메시지가 지워진다. 디바이스가 매번 retain으로 보내면 retained 저장소가 토픽 수만큼 커지니까, 토픽 설계를 잘못하면 retained 저장소가 메모리를 많이 먹는다.

세션 영속성은 클라이언트가 끊겼다 다시 붙을 때 구독 정보와 미전송 메시지를 유지하는 기능이다. MQTT 3.1.1에서는 `clean_session = false`, MQTT 5.0에서는 `Clean Start = false` + `Session Expiry Interval`로 제어한다.

```hocon
mqtt {
  session_expiry_interval = 2h
}
```

세션을 유지하면 디바이스가 잠깐 끊겨도 그동안 온 QoS 1/2 메시지를 재접속 시 받는다. 문제는 디바이스가 오래 안 붙으면 그 세션의 미전송 메시지가 큐에 계속 쌓인다는 것이다. 디바이스 수만 대가 일제히 오프라인되는 상황(네트워크 장애)에서 세션 만료 시간을 길게 잡으면 브로커 메모리가 폭발한다. 영구 오프라인 가능성이 있는 디바이스는 만료 시간을 현실적으로 잡아야 한다.

## MQTT 5.0 지원

EMQX는 MQTT 5.0을 완전히 지원한다. 5.0에서 실무적으로 유용한 것들이 몇 개 있다.

Reason Code가 생겨서 연결이 왜 끊겼는지(인증 실패인지, 서버 종료인지) 클라이언트가 안다. 3.1.1에서는 그냥 끊겼다는 것만 알 수 있어서 디버깅이 힘들었다.

Session Expiry Interval로 세션 수명을 초 단위로 지정한다. 3.1.1의 `clean_session`은 켜고 끄는 것만 됐다.

Topic Alias로 긴 토픽 이름을 숫자로 매핑해서 대역폭을 아낀다. 토픽 이름이 긴 환경에서 패킷 크기가 줄어든다.

Shared Subscription이 표준에 들어왔다(3.1.1에서는 브로커 확장 기능이었다).

디바이스 펌웨어가 MQTT 5.0 클라이언트를 지원하면 5.0으로 가는 게 낫다. 단 EMQX는 3.1.1과 5.0 클라이언트를 한 브로커에서 동시에 받으니까, 디바이스 전환을 점진적으로 할 수 있다.

## 운영하며 겪는 문제들

### file descriptor 한계

커넥션 하나가 file descriptor 하나를 쓴다. 디바이스가 늘어 커넥션이 폭증하면 OS의 fd 한계(`ulimit -n` 기본 1024)에 걸려서 `Too many open files`가 뜨고 새 커넥션을 못 받는다. 커넥션은 안정적인데 어느 순간 더 안 붙으면 거의 fd 문제다.

```bash
# 현재 한계 확인
ulimit -n

# EMQX 프로세스 실제 사용량
cat /proc/$(pgrep -f emqx)/limits | grep "open files"
```

systemd로 띄우면 unit 파일에 `LimitNOFILE`을 올리고, Docker면 `--ulimit nofile=1048576:1048576`을 준다. 수십만 커넥션을 받을 노드는 fd를 백만 단위로 올려놔야 한다. 커널의 `fs.file-max`도 같이 확인한다.

```bash
docker run -d --name emqx \
  --ulimit nofile=2097152:2097152 \
  ...
```

### QoS 2 메시지 적체

QoS 2는 정확히 한 번 전달(exactly once)을 보장하려고 4-way 핸드셰이크(PUBLISH/PUBREC/PUBREL/PUBCOMP)를 한다. 메시지 한 건에 패킷이 네 번 오가니까 QoS 0/1보다 오버헤드가 훨씬 크다. 디바이스가 ACK를 제때 안 보내면 in-flight 메시지가 쌓이고, 브로커는 그걸 들고 있어야 해서 메모리가 찬다.

대부분의 텔레메트리는 QoS 1이면 충분하다. 같은 메시지가 두 번 와도 멱등하게 처리하면 되니까 QoS 2를 굳이 쓸 필요가 없다. 결제나 명령처럼 중복이 진짜 곤란한 것만 QoS 2로 두고, 그것도 in-flight 윈도우(`max_inflight`)를 제한해서 한 클라이언트가 브로커 메모리를 독점하지 못하게 막는다.

### 메모리 사용량 모니터링

EMQX의 메모리는 커넥션 수, retained 메시지, 세션 큐, in-flight 메시지에 비례해서 늘어난다. 평소엔 안정적이다가 위 요인 중 하나가 튀면 갑자기 오른다.

```bash
emqx_ctl broker metrics | grep memory
emqx_ctl listeners   # 리스너별 커넥션 수
```

Prometheus 엔드포인트(`/api/v5/prometheus/stats`)를 켜서 Grafana로 보는 게 정석이다. 봐야 할 지표는 커넥션 수, 메시지 in/out rate, 큐 길이, 노드별 메모리/CPU다. 메모리가 우상향하면 retained나 세션 큐가 안 비워지고 쌓이는 건 아닌지 의심한다. 디바이스가 대량 오프라인된 뒤 세션이 안 만료돼서 메모리가 천천히 차오르는 패턴을 실제로 자주 본다.

## emqx_ctl CLI

운영 중 가장 많이 쓰는 명령들이다. dashboard가 안 뜨거나 SSH만 되는 상황에서 결국 이걸 쓴다.

```bash
# 노드 상태
emqx_ctl status

# 클러스터 상태 (클러스터 안 붙을 때 제일 먼저)
emqx_ctl cluster status

# 노드 클러스터에 붙이기 (manual 디스커버리)
emqx_ctl cluster join emqx@node1.internal

# 노드 클러스터에서 빼기
emqx_ctl cluster leave

# 현재 커넥션 목록
emqx_ctl clients list

# 특정 클라이언트 강제 종료
emqx_ctl clients kick device001

# 구독 현황
emqx_ctl subscriptions list

# 브로커 메트릭
emqx_ctl broker metrics

# 리스너 상태와 커넥션 수
emqx_ctl listeners

# 토픽 라우팅 테이블
emqx_ctl topics list
```

장애 대응 순서는 대체로 이렇다. 커넥션이 안 붙으면 `listeners`로 리스너가 살아있는지, `status`로 노드가 정상인지 본다. 클러스터가 깨졌으면 `cluster status`로 어느 노드가 빠졌는지 확인하고 쿠키와 hostname을 의심한다. 특정 디바이스가 이상하게 동작하면 `clients list`로 찾아 `clients kick`으로 끊고 재접속을 유도한다.

emqx_ctl은 노드 로컬 명령이라 클러스터 전체가 아니라 접속한 그 노드 기준으로 동작하는 경우가 있다(`clients list` 같은 건 클러스터 전체를 본다). 노드별로 확인이 필요하면 각 노드에 들어가서 실행한다.
