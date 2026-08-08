---
title: "Cloud SQL (MySQL / PostgreSQL)"
tags: [gcp, mysql, postgresql, cloud]
updated: 2026-07-03
---

# Cloud SQL (MySQL / PostgreSQL)

GCP의 관리형 관계형 데이터베이스다. MySQL, PostgreSQL, SQL Server 세 엔진을 지원한다. 여기서는 실무에서 대부분 쓰는 MySQL과 PostgreSQL만 다룬다. AWS RDS를 써본 사람이라면 개념은 거의 그대로 옮겨온다. 인스턴스를 만들면 그 안에 DB 엔진이 돌고, 백업·패치·복제·페일오버 같은 운영 작업을 GCP가 대신 해준다. 대신 OS 접근 권한은 없다. SSH로 들어가서 my.cnf를 직접 만지는 식의 작업은 못 하고, 파라미터는 플래그(flag)로만 바꾼다.

직접 관리하는 EC2 위의 MySQL과 가장 크게 다른 점이 이 부분이다. 커널 파라미터를 튜닝하거나, 특정 확장을 소스에서 빌드해 넣거나, 슈퍼유저 권한으로 뭔가를 하려는 순간 막힌다. Cloud SQL은 `root`를 주긴 하지만 실제로는 `SUPER` 권한이 제한된 반쪽짜리 계정이다. PostgreSQL도 `cloudsqlsuperuser` 롤을 주지만 진짜 슈퍼유저는 아니다. 이걸 모르고 온프렘 마이그레이션 스크립트를 그대로 돌리면 권한 에러가 난다.

## 인스턴스 생성

콘솔이나 `gcloud`로 만든다. 만들 때 정하는 값 중에 나중에 못 바꾸거나 바꾸기 어려운 게 몇 개 있어서 처음에 신경 써야 한다.

```bash
gcloud sql instances create prod-mysql \
  --database-version=MYSQL_8_0 \
  --tier=db-custom-4-16384 \
  --region=asia-northeast3 \
  --storage-type=SSD \
  --storage-size=100GB \
  --storage-auto-increase \
  --availability-type=REGIONAL \
  --backup-start-time=17:00 \
  --enable-bin-log
```

`--tier`는 머신 타입이다. `db-custom-4-16384`는 vCPU 4개, 메모리 16GB(16384MB)라는 뜻이다. `db-n1-standard-2` 같은 사전 정의 타입도 있지만 커스텀이 세밀하게 잡힌다. 여기서 주의할 게 vCPU와 메모리 비율에 제약이 있다. vCPU당 메모리가 0.9GB~6.5GB 범위 안에 들어와야 한다. vCPU 4개에 메모리 2GB 같은 건 못 만든다.

`--region`은 만든 뒤 못 바꾼다. 리전을 옮기려면 새로 만들어서 데이터를 옮겨야 한다. 그리고 애플리케이션 서버와 같은 리전에 두는 게 지연 시간 측면에서 중요하다. 서울에 앱을 두고 DB를 도쿄에 두면 쿼리마다 왕복 지연이 붙는다.

`--storage-auto-increase`는 디스크가 차면 자동으로 늘려주는 옵션이다. 켜두는 걸 권한다. 디스크가 꽉 차면 인스턴스가 통째로 멈추는데, 이건 페일오버로도 안 살아난다. 그런데 자동 증가는 한 번 늘어나면 다시 줄일 수 없다. 대량 삭제 배치를 잘못 돌려서 임시로 디스크가 팽창했다가 자동 증가가 물려버리면, 그 늘어난 디스크 요금을 계속 내야 한다. 줄이려면 인스턴스를 새로 만들어 마이그레이션하는 수밖에 없다.

`--storage-type`은 SSD와 HDD가 있는데 프로덕션이면 사실상 SSD다. HDD는 IOPS가 낮아서 트랜잭션이 조금만 몰려도 디스크가 병목이 된다. Cloud SQL은 디스크 IOPS와 처리량이 용량에 비례한다. 100GB짜리와 500GB짜리는 같은 SSD여도 IOPS 상한이 다르다. 그래서 데이터가 적어도 성능이 필요하면 디스크를 일부러 크게 잡기도 한다.

## 고가용성(HA) 구성

`--availability-type=REGIONAL`이 HA 구성이다. 기본값은 `ZONAL`이고, 이건 인스턴스가 한 존(zone)에만 있어서 그 존이 죽으면 DB도 같이 죽는다. REGIONAL로 만들면 다른 존에 대기(standby) 인스턴스가 하나 더 서고, 두 인스턴스 사이를 동기 복제한다.

여기서 오해하기 쉬운 게 이 standby는 읽기용이 아니다. RDS의 Multi-AZ와 똑같이, standby는 평소엔 아무 트래픽도 안 받고 그냥 대기만 한다. 읽기 부하를 나누고 싶으면 뒤에 나오는 읽기 복제본을 따로 만들어야 한다. HA는 오로지 가용성을 위한 것이지 성능을 위한 게 아니다.

```mermaid
graph LR
    App[애플리케이션] -->|쓰기/읽기| Primary[Primary 인스턴스<br/>zone-a]
    Primary -->|동기 복제| Standby[Standby 인스턴스<br/>zone-b]
    Primary -.->|장애 시 승격| Standby
    Standby -.->|페일오버 후| App
```

페일오버가 일어나면 GCP가 standby를 자동으로 승격시킨다. 이때 연결 IP는 그대로 유지된다. 그래서 애플리케이션 입장에서는 같은 주소로 계속 붙으면 되는데, 문제는 페일오버 순간에 기존 연결이 전부 끊긴다는 점이다. 대략 30초에서 2분 정도 쓰기가 안 되는 구간이 생긴다. 이 시간 동안 커넥션 풀이 죽은 커넥션을 붙잡고 있으면 앱이 계속 에러를 뱉는다. 그래서 커넥션 풀에 `validation query`나 짧은 `maxLifetime`을 걸어서 죽은 커넥션을 빨리 버리게 해야 한다.

HA를 켜면 비용은 대략 두 배가 된다. standby 인스턴스도 같은 스펙으로 계속 떠 있기 때문이다. 개발이나 스테이징 환경까지 REGIONAL로 잡을 필요는 없다. 프로덕션과 그에 준하는 환경만 HA로 두고 나머지는 ZONAL로 두면 비용이 절반이다.

동기 복제라서 쓰기 지연에 영향이 있다. 커밋이 standby까지 기록돼야 완료되기 때문에, ZONAL보다 쓰기 응답이 조금 느리다. 대부분 무시할 수준이지만, 초당 쓰기가 아주 많은 워크로드라면 이 차이가 보인다.

## 연결 방식: 퍼블릭 IP vs 프라이빗 IP

Cloud SQL에 붙는 방법이 크게 두 갈래다. 이걸 처음에 잘못 정하면 나중에 통째로 바꿔야 해서 번거롭다.

퍼블릭 IP는 인스턴스에 공인 IP가 붙는 방식이다. 이름과 달리 아무나 붙을 수 있는 건 아니고, 붙으려면 `Authorized networks`에 소스 IP를 등록하거나 Auth Proxy를 써야 한다. 등록된 IP 대역만 접속을 허용한다. 사무실이나 특정 서버에서만 붙는 소규모 환경이면 간단하다.

프라이빗 IP는 인스턴스가 VPC 내부 사설 IP만 갖는 방식이다. 공인 경로가 아예 없어서 외부에서 직접 못 붙는다. 같은 VPC(또는 VPC 피어링된 네트워크) 안의 리소스만 접속한다. 프로덕션이면 프라이빗 IP를 권한다. 인터넷에 DB 포트가 노출될 여지 자체가 없어진다.

프라이빗 IP를 쓰려면 처음에 `Private Service Access`를 설정해야 한다. VPC 안에서 Google이 관리하는 서비스용 IP 대역을 미리 할당(allocated range)하고 피어링을 맺는 작업이다. 이게 인스턴스 생성 전에 되어 있어야 프라이빗 IP로 만들 수 있다. 순서를 놓치면 인스턴스를 만들 때 프라이빗 IP 옵션이 안 잡힌다.

```bash
# Private Service Access용 IP 대역 예약
gcloud compute addresses create google-managed-services-default \
  --global --purpose=VPC_PEERING --prefix-length=16 \
  --network=default

# 서비스 네트워킹 연결(피어링) 생성
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-default \
  --network=default
```

퍼블릭 IP와 프라이빗 IP를 동시에 켤 수도 있다. 마이그레이션 과도기에 잠깐 둘 다 열어두는 경우가 있다. 하지만 프라이빗으로 다 옮겼으면 퍼블릭은 꺼야 한다. 켜둔 채로 잊으면 `Authorized networks`를 `0.0.0.0/0`으로 열어놓은 실수와 겹쳐서 사고가 난다.

## Cloud SQL Auth Proxy

Auth Proxy는 애플리케이션과 Cloud SQL 사이에 끼는 로컬 프록시다. 앱은 로컬호스트의 프록시에 붙고, 프록시가 IAM 인증으로 Cloud SQL까지 암호화된 터널을 뚫어준다. IP 화이트리스트를 관리하거나 SSL 인증서를 직접 다룰 필요가 없어진다는 게 핵심이다.

동작 방식은 이렇다. 프록시가 뜰 때 서비스 계정 자격증명으로 Cloud SQL Admin API에 인증하고, 인스턴스의 접속 정보를 받아 TLS 터널을 만든다. 앱은 그냥 `127.0.0.1:3306`에 평문으로 붙는데, 실제 네트워크 구간은 프록시가 TLS로 감싼다. 그래서 앱 코드에서 SSL 설정을 안 해도 통신은 암호화된다.

```bash
# 프록시 실행 (v2 기준)
./cloud-sql-proxy \
  --port 3306 \
  my-project:asia-northeast3:prod-mysql

# 애플리케이션은 로컬호스트로 붙는다
mysql -u app_user -p --host=127.0.0.1 --port=3306
```

GKE에서는 사이드카(sidecar) 컨테이너로 띄우는 게 정석이다. 애플리케이션 파드 안에 Auth Proxy 컨테이너를 같이 넣고, 앱은 같은 파드의 `localhost`로 붙는다. 파드마다 프록시가 하나씩 뜨니까 네트워크 홉이 짧고, 프록시가 죽으면 파드 단위로 재시작된다.

```yaml
# GKE 사이드카 예시 (일부)
containers:
  - name: app
    image: my-app:latest
    env:
      - name: DB_HOST
        value: "127.0.0.1"
      - name: DB_PORT
        value: "3306"
  - name: cloud-sql-proxy
    image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.11.0
    args:
      - "--port=3306"
      - "my-project:asia-northeast3:prod-mysql"
    securityContext:
      runAsNonRoot: true
```

Auth Proxy를 쓸 때 자주 막히는 게 서비스 계정 권한이다. 프록시가 쓰는 서비스 계정에 `Cloud SQL Client`(roles/cloudsql.client) 역할이 있어야 한다. 이게 없으면 프록시는 뜨는데 실제 연결에서 인증 실패가 난다. 에러 메시지가 권한 문제라고 친절하게 안 알려주고 그냥 연결이 안 되는 것처럼 보여서 한참 헤맨다.

또 하나, 프록시는 IAM 인증까지만 해준다. DB 사용자와 비밀번호는 별개다. 프록시가 터널을 뚫어줘도 그 안에서 `app_user`로 로그인하는 건 여전히 앱이 해야 한다. IAM 데이터베이스 인증을 따로 켜면 DB 비밀번호 없이 IAM 토큰으로 로그인할 수도 있지만, 기본은 프록시(네트워크 인증) + DB 계정(DB 인증)의 이중 구조다.

프라이빗 IP 인스턴스에도 Auth Proxy를 쓸 수 있다. `--private-ip` 플래그를 주면 퍼블릭 경로 대신 프라이빗 IP로 터널을 맺는다. VPC 안에서 도는 GKE 워크로드가 프라이빗 IP Cloud SQL에 붙을 때 이 조합을 많이 쓴다.

## 자동 백업과 PITR

`--backup-start-time`으로 매일 자동 백업 시각을 잡는다. 백업은 지정한 시각 근처에 시작하는 자동 백업과, 필요할 때 직접 뜨는 온디맨드 백업이 있다. 자동 백업은 기본 7개까지 보관하고 개수를 조정할 수 있다.

여기서 중요한 게 PITR(Point-In-Time Recovery)이다. 자동 백업만으로는 백업 시각 단위로만 복구된다. 새벽 5시 백업이 마지막이고 오후 3시에 사고가 났으면, 백업만으로는 새벽 5시로밖에 못 돌아간다. 그 사이 10시간의 데이터가 날아간다. PITR을 켜면 바이너리 로그(MySQL) 또는 WAL(PostgreSQL)을 계속 쌓아서, 특정 초 단위 시점으로 복구할 수 있다. 오후 2시 59분처럼 사고 직전으로 되돌린다.

MySQL이면 PITR을 쓰려면 `--enable-bin-log`가 켜져 있어야 한다. 바이너리 로그가 있어야 시점 복구가 되기 때문이다. PostgreSQL은 WAL 아카이빙이 자동 백업과 함께 관리된다.

```bash
# 특정 시점으로 새 인스턴스에 복구 (기존 인스턴스는 건드리지 않는다)
gcloud sql instances clone prod-mysql prod-mysql-recovered \
  --point-in-time '2026-07-03T05:59:00.000Z'
```

PITR 복구는 기존 인스턴스를 덮어쓰는 게 아니라 새 인스턴스로 복원한다. 이게 중요한데, 사고 난 원본을 그대로 두고 복구본을 따로 세운 다음, 필요한 데이터만 뽑아서 원본에 반영하는 식으로 쓰는 경우가 많다. 통째로 롤백하면 사고 이후에 정상적으로 들어온 데이터까지 날아가기 때문이다. 실무에서 "특정 테이블만 실수로 지웠다" 같은 상황이 대부분이라, 복구본에서 그 테이블만 덤프해서 옮기는 게 안전하다.

주의할 점은 PITR 복구 시점 범위다. 바이너리 로그 보관 기간(기본 7일 정도)을 벗어난 시점으로는 못 돌아간다. 그리고 인스턴스를 재시작하거나 특정 설정을 바꾸면 복구 가능한 시작점이 바뀔 수 있다. 오래된 사고를 뒤늦게 발견하면 이미 복구 범위를 벗어나 있는 경우가 있다.

## 읽기 복제본(Read Replica)

읽기 부하를 나누려면 읽기 복제본을 만든다. Primary의 데이터를 비동기로 복제받는 읽기 전용 인스턴스다. 쓰기는 안 되고 읽기만 된다. 리포팅 쿼리나 통계 집계처럼 무거운 읽기를 복제본으로 몰아서 Primary 부하를 던다.

```bash
gcloud sql instances create prod-mysql-replica \
  --master-instance-name=prod-mysql \
  --region=asia-northeast3 \
  --tier=db-custom-2-8192
```

복제본은 비동기라서 복제 지연(replication lag)이 있다. Primary에 방금 쓴 데이터가 복제본에는 몇 밀리초에서, 부하가 크면 몇 초까지 늦게 반영된다. 그래서 "방금 쓴 걸 바로 읽어야 하는" 로직을 복제본으로 보내면 데이터가 없다고 나온다. 회원가입 직후 그 회원 정보를 조회하는 흐름을 읽기 복제본으로 라우팅했다가, 가끔 "없는 회원"으로 처리되는 버그를 겪은 적이 있다. 읽기 일관성이 필요한 쿼리는 Primary로 보내야 한다.

복제 지연은 모니터링해야 한다. Cloud Monitoring에서 `replica_lag` 지표를 본다. 복제본 스펙이 Primary보다 너무 낮으면 쓰기를 따라가지 못해 지연이 계속 벌어진다. 복제본을 Primary보다 한참 작게 잡는 실수를 자주 하는데, 최소한 쓰기를 소화할 만큼은 줘야 한다.

읽기 복제본은 페일오버 대상이 아니다. HA의 standby와 헷갈리면 안 된다. Primary가 죽어도 읽기 복제본이 자동으로 승격되지 않는다. 다만 복제본을 수동으로 독립 인스턴스로 승격(promote)시킬 수는 있다. 이건 리전 재해 복구 용도나, 복제본을 새 Primary로 분리하는 마이그레이션에 쓴다. 승격하면 복제 관계가 끊기고 되돌릴 수 없다.

## 커넥션 풀 고갈과 max_connections 튜닝

Cloud SQL 운영에서 제일 자주 터지는 게 커넥션 고갈이다. 어느 순간 앱이 `Too many connections` 또는 `remaining connection slots are reserved` 에러를 뱉으면서 DB에 못 붙는다.

`max_connections`는 DB가 동시에 받을 수 있는 커넥션 상한이다. Cloud SQL은 이 값을 인스턴스 메모리에 비례해 자동으로 잡는데, 생각보다 낮게 잡힐 때가 있다. 플래그로 직접 올릴 수 있다.

```bash
gcloud sql instances patch prod-mysql \
  --database-flags=max_connections=500
```

그런데 max_connections를 무작정 올리는 게 답이 아니다. 커넥션 하나가 메모리를 잡아먹는다. 특히 PostgreSQL은 커넥션마다 프로세스를 하나씩 띄우기 때문에, 커넥션 수를 크게 늘리면 메모리가 감당을 못 한다. MySQL은 스레드 기반이라 조금 낫지만 그래도 무한하지 않다. max_connections를 2000으로 올려놓고 실제로 2000개가 붙으면 인스턴스가 메모리 부족으로 불안정해진다.

진짜 원인은 대부분 애플리케이션 쪽 커넥션 풀 설정이다. 앱 인스턴스 하나가 커넥션 풀을 20개씩 물고 있고, 오토스케일로 앱이 30개까지 뜨면 그것만으로 600개가 필요하다. 여기에 배치 서버, 관리 도구까지 붙으면 순식간에 상한을 넘는다. 계산이 안 맞으면 max_connections를 올리기 전에 앱 풀 크기부터 다시 본다.

경험상 이렇게 접근한다. 먼저 앱 인스턴스당 커넥션 풀 크기(HikariCP면 `maximumPoolSize`)를 필요한 만큼만 잡는다. CPU 코어 수 기준으로 10~20개 정도면 대부분 충분하다. 풀을 크게 잡는다고 처리량이 늘지 않는다. 오히려 DB가 동시에 처리할 수 있는 것보다 많은 쿼리를 던지면 락 경합만 늘어난다.

```properties
# HikariCP 설정 예시
spring.datasource.hikari.maximum-pool-size=15
spring.datasource.hikari.minimum-idle=5
spring.datasource.hikari.max-lifetime=280000
spring.datasource.hikari.connection-timeout=3000
```

`max-lifetime`을 Cloud SQL의 `wait_timeout`보다 짧게 잡는 게 중요하다. Cloud SQL은 일정 시간 유휴 커넥션을 서버 쪽에서 끊는데(`wait_timeout`), 앱 풀이 이미 끊긴 커넥션을 살아있다고 믿고 재사용하려다 `Communications link failure`가 난다. `max-lifetime`을 서버 타임아웃보다 짧게 둬서 앱이 먼저 커넥션을 폐기하게 만든다. 앞서 HA 페일오버 때 죽은 커넥션을 빨리 버려야 한다고 한 것과 같은 맥락이다.

커넥션이 정말 많이 필요한 구조라면 앱과 DB 사이에 커넥션 풀러를 따로 둔다. PostgreSQL이면 PgBouncer가 표준이다. 앱은 PgBouncer에 붙고, PgBouncer가 실제 DB 커넥션을 적은 수로 재사용한다. 앱 인스턴스가 수백 개여도 DB 실제 커넥션은 수십 개로 유지된다. Cloud SQL 자체에는 이런 풀러가 내장돼 있지 않아서(엔진에 따라 다르지만) 직접 세우거나 사이드카로 붙인다.

고갈 상황을 진단할 때는 현재 붙어 있는 커넥션을 직접 본다.

```sql
-- MySQL: 현재 커넥션 수와 상태
SHOW STATUS LIKE 'Threads_connected';
SHOW PROCESSLIST;

-- PostgreSQL: 상태별 커넥션 집계
SELECT state, count(*)
FROM pg_stat_activity
GROUP BY state;
```

PostgreSQL에서 `idle in transaction` 상태가 많이 쌓여 있으면 이게 범인인 경우가 많다. 트랜잭션을 열어놓고 커밋도 롤백도 안 한 채 커넥션만 붙잡고 있는 상태다. 애플리케이션에서 트랜잭션 경계를 잘못 잡았거나, 예외 처리 중에 커넥션을 안 닫는 코드가 있으면 이렇게 쌓인다. 커넥션 수를 늘리기 전에 이 상태부터 없애야 한다. 그냥 max_connections만 올리면 새는 커넥션이 그만큼 더 새는 것뿐이다.
