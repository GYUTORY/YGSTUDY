---
title: RDS Multi-AZ
tags: [aws, database, rds, multi-az, failover, high-availability, dns, read-replica, cloudwatch]
updated: 2026-07-25
---

# RDS Multi-AZ

RDS의 고가용성 구성은 2022년 이후 두 가지 방식이 공존한다. 기존 방식인 Multi-AZ 인스턴스와, 비교적 최근에 나온 Multi-AZ 클러스터다. 이름이 비슷해서 혼동하기 쉬운데 내부 구조가 완전히 다르다.

## Multi-AZ 인스턴스

가장 오래된 고가용성 구성이다. Primary 인스턴스 하나와 Standby 인스턴스 하나, 총 2개 노드가 서로 다른 AZ에 배치된다.

복제 방식은 동기식이다. 애플리케이션이 Primary에 쓰기 요청을 보내면, Primary가 Standby에 데이터를 동기 복제한 뒤에야 완료 응답을 돌려준다. Primary가 죽어도 데이터 유실이 없는 이유다.

Standby는 읽기 요청을 처리하지 않는다. 비용을 내고 인스턴스를 하나 더 운영하는데 평소엔 완전히 놀고 있다. 읽기 부하를 분산하고 싶으면 Read Replica를 별도로 만들어야 한다. Standby는 오직 장애 대비 용도다.

## Multi-AZ 클러스터

Writer 1개와 Reader 2개, 총 3개 노드가 각각 다른 AZ에 위치한다. Reader가 실제로 읽기 요청을 처리할 수 있다는 점에서 Multi-AZ 인스턴스와 구조가 다르다.

복제 방식은 반동기식(semi-synchronous)이다. Writer가 커밋할 때 최소 1개 Reader에서 로컬 스토리지에 기록했다는 확인을 받아야 커밋이 완료된다. 두 Reader 중 하나만 확인해주면 되기 때문에, Reader 한 대가 느리거나 다운되어도 쓰기 성능 영향이 덜하다.

엔드포인트가 3종류다.

| 엔드포인트 | 역할 |
|---|---|
| Cluster endpoint | Writer 인스턴스로 연결 (쓰기 트래픽) |
| Reader endpoint | 2개 Reader에 로드밸런싱 (읽기 트래픽) |
| Instance endpoint | 특정 인스턴스에 직접 연결 (디버깅·유지보수) |

운영 환경에서 Instance endpoint로 직접 연결하는 건 피해야 한다. 페일오버 시 인스턴스가 교체되면 그 연결이 끊긴다.

## 페일오버 발생 조건

자동으로 페일오버가 트리거되는 경우는 몇 가지 패턴이 있다.

- DB 엔진 프로세스 충돌 (MySQL이 OOM으로 죽거나 내부 오류로 재시작하는 경우)
- 네트워크 단절 또는 스토리지 장애
- AZ 수준의 장애
- OS 패치나 마이너 버전 업그레이드 같은 유지보수 작업
- 수동 강제 페일오버 (Reboot with Failover)

유지보수 윈도우 때 패치가 적용되는 경우, Multi-AZ가 켜져 있으면 Standby나 Reader에 먼저 패치를 적용한 뒤 페일오버로 Primary를 교체한다. 다운타임을 줄이는 방식이지만 페일오버 자체는 발생하고 연결이 짧게 끊긴다.

## 페일오버 소요 시간

Multi-AZ 인스턴스는 보통 60~120초다. AWS 문서에는 "60초 이내"라고 나와 있지만, 실제 환경에서는 2분을 넘기는 경우도 있다. Primary 헬스체크 실패를 감지하는 데 시간이 걸리고, DNS CNAME 전환 후 앱 쪽에서 새 Primary로 재연결하는 시간까지 합치면 체감 다운타임은 더 길어진다.

Multi-AZ 클러스터는 AWS가 35초 이내라고 명시한다. Writer가 죽으면 두 Reader 중 데이터가 더 최신인 쪽이 Writer로 승격된다. 승격 대상 Reader는 이미 최신 데이터를 갖고 있어서 복구 시간이 줄어든다. 실제 테스트에서는 20~40초 수준이 나오는 경우가 많다.

## DNS 전환 방식

RDS는 CNAME 방식으로 페일오버를 처리한다. `mydb.cluster-xxxxxxxxx.ap-northeast-2.rds.amazonaws.com` 같은 엔드포인트 주소는 CNAME이고, 이 CNAME이 실제 인스턴스 IP를 가리키는 A 레코드로 이어진다. 페일오버가 발생하면 CNAME이 새 Primary(또는 Writer)를 가리키도록 바뀐다. DNS TTL은 5초로 설정되어 있다.

여기서 자주 겪는 문제가 두 가지다.

**JVM 애플리케이션의 DNS 캐시**

Java는 기본 설정에 따라 DNS 조회 결과를 무기한 캐시하는 경우가 있다. `networkaddress.cache.ttl`이 `-1`이거나 설정 자체가 없으면 JVM이 처음 기동할 때 조회한 IP를 계속 쓴다. 페일오버 후 새 Primary의 IP가 달라져도 앱이 계속 죽은 인스턴스 IP로 연결을 시도하는 상황이 생긴다. JVM 실행 옵션에 `-Dsun.net.inetaddr.ttl=5` 또는 `security.properties`에 `networkaddress.cache.ttl=5`를 넣어야 한다.

**커넥션 풀이 유지하는 기존 TCP 연결**

DNS가 바뀌어도 이미 맺어진 TCP 커넥션은 그대로 남아 있다. 이 커넥션들은 Primary가 죽을 때 TCP 레벨에서 끊기기 전까지 앱은 연결이 살아있다고 판단한다. 커넥션 풀 설정에서 `testOnBorrow`나 `validationQuery`를 켜두면 커넥션을 빌릴 때마다 상태를 확인해서 빨리 감지할 수 있다. JDBC URL에 `connectTimeout`과 `socketTimeout`을 짧게 잡아두는 것도 같은 목적이다.

## Read Replica와 복제 지연 대응

Multi-AZ와 Read Replica는 별개 개념이다. Multi-AZ는 고가용성(HA)을 위한 구성이고, Read Replica는 읽기 성능 분산을 위한 구성이다.

Multi-AZ 인스턴스를 쓰더라도 읽기 부하 분산이 필요하면 Read Replica를 별도로 만들어야 한다. Standby는 읽기 불가다.

Multi-AZ 클러스터는 내부 Reader 2개가 읽기를 처리하지만, 이 Reader들이 Read Replica는 아니다. 클러스터 외부에 추가로 Read Replica를 붙이는 것도 가능하다.

Read Replica는 비동기 복제다. Primary가 커밋한 데이터가 Replica에 반영되기까지 지연(replication lag)이 발생한다. 보통 수백 밀리초 이내지만, 대량 쓰기가 몰리거나 Replica의 CPU가 높을 때는 수 초에서 수십 초까지 늘어난다.

페일오버가 발생했을 때 Read Replica는 자동으로 새 Primary를 따라가지만, 복제 소스가 바뀌고 재동기화되는 과정에서 복제 지연이 급증한다. 이 시간에 Replica에서 오래된 데이터를 읽으면 사용자에게 잘못된 정보가 노출된다.

### ReplicaLag 기반 라우팅

`ReplicaLag` CloudWatch 메트릭을 주기적으로 조회해서 임계치를 넘은 Replica로는 트래픽을 보내지 않는 방법이다. 앱 안에서 DataSource를 동적으로 전환하는 구조로 구현한다.

```java
@Component
public class ReplicaHealthChecker {
    private static final long LAG_THRESHOLD_SECONDS = 30L;
    private final AmazonCloudWatch cloudWatch;
    private volatile boolean replicaHealthy = true;

    @Scheduled(fixedRate = 5000)
    public void checkReplicaLag() {
        GetMetricStatisticsRequest request = new GetMetricStatisticsRequest()
            .withNamespace("AWS/RDS")
            .withMetricName("ReplicaLag")
            .withDimensions(new Dimension()
                .withName("DBInstanceIdentifier")
                .withValue("my-read-replica"))
            .withStartTime(new Date(System.currentTimeMillis() - 120_000))
            .withEndTime(new Date())
            .withPeriod(60)
            .withStatistics("Average");

        GetMetricStatisticsResult result = cloudWatch.getMetricStatistics(request);
        result.getDatapoints().stream()
            .max(Comparator.comparing(Datapoint::getTimestamp))
            .ifPresent(dp -> replicaHealthy = dp.getAverage() < LAG_THRESHOLD_SECONDS);
    }

    public boolean isReplicaHealthy() {
        return replicaHealthy;
    }
}
```

이 체커를 DataSource 라우터에 연결하면, Replica 지연이 30초를 넘는 순간 자동으로 Primary로 우회한다.

```java
public class RoutingDataSource extends AbstractRoutingDataSource {
    private final ReplicaHealthChecker healthChecker;

    @Override
    protected Object determineCurrentLookupKey() {
        boolean isReadOperation = TransactionSynchronizationManager.isCurrentTransactionReadOnly();
        if (isReadOperation && healthChecker.isReplicaHealthy()) {
            return "replica";
        }
        return "primary";
    }
}
```

### Sticky Primary 패턴

쓰기 직후 바로 같은 데이터를 읽어야 하는 경우(주문 생성 후 주문 상세 조회 등)가 있다. 이 경우 Replica 지연 때문에 방금 쓴 데이터가 안 보이는 상황이 생긴다. 세션 단위로 일정 시간 Primary에서 읽도록 강제하면 해결된다.

```java
@Component
public class StickyPrimaryContext {
    private static final long STICKY_DURATION_MS = 10_000L; // 쓰기 후 10초
    private final ThreadLocal<Long> primaryUntil = new ThreadLocal<>();

    public void markWriteOccurred() {
        primaryUntil.set(System.currentTimeMillis() + STICKY_DURATION_MS);
    }

    public boolean shouldUsePrimary() {
        Long until = primaryUntil.get();
        return until != null && System.currentTimeMillis() < until;
    }

    public void clear() {
        primaryUntil.remove();
    }
}
```

AOP로 `@Transactional` 쓰기 트랜잭션 완료 시점에 `markWriteOccurred()`를 호출하도록 묶어두면, 서비스 레이어에서 별도 처리 없이 동작한다.

### Cross-Region Replica 주의사항

Cross-Region Read Replica는 지연이 더 크다. 리전 간 네트워크 지연이 기본으로 수십 ms 이상이고, 대량 트랜잭션이 있을 때는 분 단위로 늘어난다. 강한 일관성이 필요한 쿼리는 Primary 리전에서만 처리해야 한다.

## 페일오버 테스트

운영 환경에 올리기 전에 반드시 테스트해봐야 한다. 이론상 60~120초라고 해도 실제 앱이 얼마나 버티는지는 직접 확인해야 안다.

### 강제 페일오버 실행

```bash
# Multi-AZ 인스턴스 강제 페일오버
aws rds reboot-db-instance \
  --db-instance-identifier my-db-instance \
  --force-failover

# Multi-AZ 클러스터 Writer 수동 교체
aws rds failover-db-cluster \
  --db-cluster-identifier my-db-cluster
```

### 연결 상태 측정 스크립트

페일오버를 트리거하면서 동시에 아래 스크립트를 실행하면, 정확히 어느 시점에 연결이 끊기고 몇 초 후에 복구되는지 기록된다. `@@hostname`을 조회하기 때문에 인스턴스가 교체되는 순간도 로그에 찍힌다.

```bash
#!/bin/bash
DB_HOST="mydb.xxxxxxxxx.ap-northeast-2.rds.amazonaws.com"
DB_USER="admin"
DB_PASS="password"
LOG_FILE="failover_$(date +%Y%m%d_%H%M%S).log"

echo "시작: $(date)" | tee -a "$LOG_FILE"

for i in $(seq 1 120); do
  TS=$(date '+%H:%M:%S.%3N')
  RESULT=$(mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" \
    --connect-timeout=3 \
    -e "SELECT @@hostname, NOW();" 2>&1)

  if [ $? -eq 0 ]; then
    HOST=$(echo "$RESULT" | awk 'NR==2 {print $1}')
    echo "$TS OK host=$HOST" | tee -a "$LOG_FILE"
  else
    ERR=$(echo "$RESULT" | head -1)
    echo "$TS ERROR: $ERR" | tee -a "$LOG_FILE"
  fi

  sleep 1
done
```

페일오버 전후로 hostname이 달라지는 시점이 찍히고, ERROR 로그가 연속으로 나온 구간의 초 수가 실제 앱 다운타임이다.

### 시나리오별 검증 포인트

**앱 재시도 로직 검증**

페일오버 중 발생하는 예외가 `CommunicationsException`, `MySQLNonTransientConnectionException` 같은 재시도 가능한 타입인지 확인한다. 이 예외를 잡아서 재시도하는 로직이 없으면 페일오버 시간 동안 전체가 에러다. 재시도 횟수는 3회, 재시도 간격은 지수 백오프(1초 → 2초 → 4초)로 잡는 게 일반적이다.

**트랜잭션 도중 페일오버**

긴 트랜잭션이 실행되는 도중 페일오버가 발생하면 트랜잭션은 롤백된다. 앱이 이 상황에서 재시도하면 동일 요청이 두 번 처리되는 중복 문제가 생긴다. 결제나 재고 차감처럼 멱등성이 중요한 작업은 재시도 전에 이미 처리됐는지 먼저 확인하는 로직이 있어야 한다.

**커넥션 풀 소진 확인**

페일오버 직후 새 연결을 맺으려는 요청이 몰리면서 커넥션 풀이 가득 차는 상황이 자주 나온다. HikariCP의 `connectionTimeout`을 5초로 잡아두면, 풀이 가득 찬 상태에서 5초 후 `SQLTransientConnectionException`이 발생한다. 이 예외를 재시도 대상으로 잡아야 한다. `maximum-pool-size`를 너무 작게 잡으면 병목이 되고, 너무 크게 잡으면 DB 쪽 `max_connections`를 초과한다. 인스턴스 타입별 `max_connections` 기본값은 RDS 파라미터 그룹에서 확인한다.

```yaml
spring:
  datasource:
    hikari:
      connection-timeout: 5000     # 5초 내 연결 못 하면 예외
      validation-timeout: 3000     # 헬스체크 타임아웃
      max-lifetime: 1800000        # 커넥션 30분 후 교체 (낡은 커넥션 정리)
      keepalive-time: 30000        # 30초마다 keepalive 전송
      minimum-idle: 5
      maximum-pool-size: 20
```

`max-lifetime`을 1800초(30분)로 설정하면, 페일오버 후 낡은 커넥션이 30분 안에 자연스럽게 교체된다. `keepalive-time`은 DB 쪽 `wait_timeout`보다 짧게 잡아야 유휴 커넥션이 서버 쪽에서 끊기는 걸 방지한다.

## CloudWatch 모니터링

페일오버 감지와 복제 지연 추적에 쓰는 핵심 메트릭들이다.

| 메트릭 | 설명 | 알람 기준 |
|---|---|---|
| `ReplicaLag` | 복제 지연 시간 (초) | 30초 초과 |
| `DatabaseConnections` | 현재 연결 수 | max_connections의 80% 초과 |
| `FreeableMemory` | 사용 가능한 메모리 (bytes) | 전체의 10% 미만 |
| `CPUUtilization` | CPU 사용률 (%) | 80% 초과 5분 지속 |
| `WriteLatency` | 쓰기 응답시간 (초) | 0.1초 초과 |
| `ReadLatency` | 읽기 응답시간 (초) | 0.05초 초과 |

### CloudWatch Alarm 설정

```bash
# ReplicaLag 알람 (30초 초과 시 SNS 알림)
aws cloudwatch put-metric-alarm \
  --alarm-name "rds-replica-lag-high" \
  --alarm-description "RDS Read Replica lag exceeds 30 seconds" \
  --namespace "AWS/RDS" \
  --metric-name "ReplicaLag" \
  --dimensions Name=DBInstanceIdentifier,Value=my-read-replica \
  --statistic Average \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 30 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:rds-alerts \
  --ok-actions arn:aws:sns:ap-northeast-2:123456789012:rds-alerts

# DatabaseConnections 알람 (db.t3.medium 기준 max_connections ≈ 170, 80% = 136)
aws cloudwatch put-metric-alarm \
  --alarm-name "rds-connections-high" \
  --alarm-description "RDS connections exceed 80 percent of max" \
  --namespace "AWS/RDS" \
  --metric-name "DatabaseConnections" \
  --dimensions Name=DBInstanceIdentifier,Value=my-db-instance \
  --statistic Average \
  --period 60 \
  --evaluation-periods 3 \
  --threshold 136 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:rds-alerts
```

### 페일오버 이벤트 감지

EventBridge로 RDS 페일오버 이벤트를 실시간으로 받을 수 있다. RDS 콘솔의 이벤트 탭보다 빠르게 Lambda나 SNS로 전달된다.

```bash
# 페일오버 이벤트를 SNS로 전달하는 EventBridge 룰
aws events put-rule \
  --name "rds-failover-events" \
  --event-pattern '{
    "source": ["aws.rds"],
    "detail-type": ["RDS DB Instance Event"],
    "detail": {
      "EventCategories": ["failover"]
    }
  }' \
  --state ENABLED

aws events put-targets \
  --rule "rds-failover-events" \
  --targets Id=sns-target,Arn=arn:aws:sns:ap-northeast-2:123456789012:rds-alerts
```

RDS 이벤트 로그에서 `Multi-AZ instance failover started`와 `Multi-AZ instance failover completed` 사이 시간 차이를 기록한다. `DatabaseConnections` 메트릭이 0으로 떨어졌다가 올라오는 구간과 비교하면 AWS 내부 복구 시간과 앱 레이어 복구 시간을 분리해서 볼 수 있다.

### 대시보드 구성

페일오버 대응 시 한 화면에서 상태를 확인하려면 CloudWatch 대시보드에 아래 위젯을 묶어두는 게 편하다.

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", "my-db-instance"],
          ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", "my-read-replica"]
        ],
        "period": 60,
        "stat": "Average",
        "title": "DB Connections"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/RDS", "ReplicaLag", "DBInstanceIdentifier", "my-read-replica"]
        ],
        "period": 60,
        "stat": "Maximum",
        "title": "Replica Lag (seconds)"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/RDS", "WriteLatency", "DBInstanceIdentifier", "my-db-instance"],
          ["AWS/RDS", "ReadLatency", "DBInstanceIdentifier", "my-read-replica"]
        ],
        "period": 60,
        "stat": "p99",
        "title": "Query Latency p99"
      }
    }
  ]
}
```

`WriteLatency`와 `ReadLatency`는 p99 기준으로 보는 게 맞다. Average는 스파이크를 숨기는 경우가 있어서 페일오버 직후 실제 영향 범위를 과소평가하게 된다.
