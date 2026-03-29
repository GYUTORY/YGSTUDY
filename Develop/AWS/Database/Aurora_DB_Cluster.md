---
title: Aurora DB Cluster Failover
tags: [aws, aurora, mysql, rds, failover, global-database, db-proxy]
updated: 2026-03-29
---

# Aurora DB Cluster Failover

Aurora의 장애 전환(Failover) 동작 방식, 커넥션 끊김 대응, Global Database 페일오버, DB Proxy 활용까지 실무에서 필요한 내용을 정리한다.

---

## 1. Aurora 클러스터 기본 구조

- Writer 인스턴스: 1개
- Reader 인스턴스: 0~N개
- 스토리지는 모든 인스턴스가 공유하는 분산 구조 (6개 복사본, 3개 AZ 분산)
- 복제 지연이 거의 없음

```
Application
   ├──> Writer (Read/Write)
   └──> Reader1 (Read-only)
        └──> Shared Storage (6 copies / 3 AZ)
```

---

## 2. 장애 발생 시 내부 처리 흐름

Aurora는 Writer 인스턴스에 장애가 발생하면, 자동으로 Reader 인스턴스 중 하나를 Writer로 승격시킨다.

### 처리 과정

1. Writer 인스턴스 장애 발생
2. 클러스터가 가장 최신 트랜잭션 로그를 가진 Reader를 식별
3. 해당 Reader를 Writer로 승격
4. Writer 엔드포인트가 자동으로 새로운 Writer로 갱신
5. 애플리케이션에서 DNS 갱신 후 새로운 Writer로 재연결

> 데이터 복구는 필요하지 않다. 스토리지는 항상 최신 상태를 유지한다.

---

## 3. 페일오버 우선순위(Tier) 설정

Aurora는 Reader 인스턴스마다 승격 우선순위(promotion tier)를 설정할 수 있다. 0~15까지 지정 가능하고, 숫자가 낮을수록 먼저 승격된다.

### 승격 대상 결정 순서

1. 가장 낮은 tier 번호를 가진 Reader
2. 같은 tier 내에서는 인스턴스 크기가 큰 쪽이 우선
3. 인스턴스 크기도 같으면 Aurora가 임의로 선택

### 설정 방법

```bash
# CLI로 우선순위 변경
aws rds modify-db-instance \
  --db-instance-identifier my-reader-1 \
  --promotion-tier 0

# 확인
aws rds describe-db-instances \
  --db-instance-identifier my-reader-1 \
  --query 'DBInstances[0].PromotionTier'
```

### 실무에서 주의할 점

tier 0으로 설정한 Reader는 Writer와 동일한 인스턴스 클래스를 사용해야 한다. Writer가 `db.r6g.2xlarge`인데 tier 0 Reader가 `db.r6g.large`라면, 승격 후 갑자기 스펙이 절반으로 떨어진다. 장애 상황에서 트래픽까지 몰리면 바로 장애가 연쇄된다.

tier를 명시하지 않으면 기본값은 1이다. Reader가 여러 대인 환경에서는 반드시 tier를 지정해서 예측 가능한 승격이 되게 해야 한다.

---

## 4. Writer 장애 시 연결 재시도 흐름

```plaintext
1. App → Writer: 쓰기 요청
2. Writer 응답 없음 (장애 발생)
3. 클러스터: Reader 중 하나를 Writer로 승격
4. App 재시도 → Writer Endpoint → 새 Writer로 연결
```

> 애플리케이션이 재시도하지 않으면 장애처럼 느껴진다.

---

## 5. Endpoint 구조 및 동작

### Writer Endpoint

- 클러스터 내 현재 Writer 인스턴스를 가리킴
- 장애 발생 시 자동으로 새 Writer로 갱신
- DNS 기반으로 동작 → TTL 반영

### Reader Endpoint

- 모든 Reader 인스턴스 중 하나로 라운드로빈 방식 라우팅
- 읽기 전용 트래픽 분산 처리용

---

## 6. 페일오버 시 커넥션 끊김 대응

페일오버가 발생하면 기존 TCP 커넥션은 전부 끊어진다. 커넥션 풀에 남아 있는 죽은 커넥션으로 쿼리를 날리면 `Communications link failure`나 `Connection refused` 에러가 발생한다.

### JVM DNS 캐시 설정

JVM은 기본적으로 DNS 조회 결과를 영구 캐시한다. 페일오버 후 Writer Endpoint의 DNS가 바뀌어도 JVM이 이전 IP를 계속 들고 있으면 새 Writer에 연결되지 않는다.

```java
// JVM 시작 옵션 또는 코드에서 설정
java.security.Security.setProperty("networkaddress.cache.ttl", "5");
java.security.Security.setProperty("networkaddress.cache.negative.ttl", "3");
```

또는 JVM 옵션:

```bash
-Dsun.net.inetaddr.ttl=5
```

5초 정도가 적당하다. 너무 짧으면 DNS 조회가 빈번해지고, 너무 길면 페일오버 반영이 늦어진다.

### HikariCP 설정

```yaml
spring:
  datasource:
    hikari:
      connection-timeout: 3000        # 커넥션 획득 대기 최대 3초
      validation-timeout: 2000        # validation 쿼리 타임아웃 2초
      max-lifetime: 1800000           # 커넥션 최대 수명 30분
      keepalive-time: 30000           # 30초마다 커넥션 유효성 확인
      connection-test-query: "SELECT 1"
      # 아래 설정이 핵심
      exception-override-class-name: ""  # HikariCP 4.x
```

`max-lifetime`은 DB의 `wait_timeout`보다 짧게 잡아야 한다. Aurora MySQL 기본 `wait_timeout`은 28800초(8시간)인데, HikariCP `max-lifetime`을 이보다 길게 설정하면 DB 쪽에서 먼저 끊은 커넥션을 풀이 계속 들고 있게 된다.

`keepalive-time`을 설정하면 HikariCP가 주기적으로 idle 커넥션에 validation 쿼리를 날린다. 이 과정에서 죽은 커넥션이 감지되어 제거된다.

### JDBC URL에서 할 수 있는 것

```
jdbc:mysql://my-cluster.cluster-xxx.ap-northeast-2.rds.amazonaws.com:3306/mydb
  ?connectTimeout=3000
  &socketTimeout=10000
  &autoReconnect=false
```

`autoReconnect=true`는 사용하면 안 된다. 트랜잭션 중간에 재연결이 되면 커밋되지 않은 상태에서 새 커넥션으로 붙는다. 데이터 정합성이 깨질 수 있다.

### AWS JDBC Driver (권장)

AWS에서 Aurora용으로 만든 JDBC 드라이버가 있다. 페일오버 감지를 DNS가 아닌 Aurora API로 하기 때문에 DNS TTL에 의존하지 않고 빠르게 전환된다.

```xml
<dependency>
    <groupId>software.amazon.jdbc</groupId>
    <artifactId>aws-advanced-jdbc-wrapper</artifactId>
    <version>2.5.4</version>
</dependency>
```

```
jdbc:aws-wrapper:mysql://my-cluster.cluster-xxx.ap-northeast-2.rds.amazonaws.com:3306/mydb
  ?wrapperPlugins=failover
```

이 드라이버를 쓰면 페일오버 감지 시간이 DNS 기반 대비 절반 이하로 줄어드는 경우가 많다.

---

## 7. 페일오버 테스트 방법

### CLI로 강제 페일오버 트리거

```bash
# 특정 인스턴스를 새 Writer로 지정하면서 페일오버
aws rds failover-db-cluster \
  --db-cluster-identifier my-aurora-cluster \
  --target-db-instance-identifier my-reader-1
```

`--target-db-instance-identifier`를 생략하면 Aurora가 우선순위 기반으로 승격 대상을 자동 선택한다.

### 테스트 시 확인 사항

페일오버 CLI를 실행한 뒤 확인해야 할 것:

1. 애플리케이션 로그에서 커넥션 에러 발생 후 자동 복구되는지
2. 복구까지 걸린 시간 (보통 5~30초)
3. 진행 중이던 트랜잭션이 롤백되었는지
4. Writer Endpoint의 DNS가 새 인스턴스 IP를 반환하는지

```bash
# DNS 변경 확인
watch -n 1 "nslookup my-cluster.cluster-xxx.ap-northeast-2.rds.amazonaws.com"
```

### Fault Injection Query (FIQ)

Aurora MySQL은 장애 시뮬레이션용 쿼리를 제공한다.

```sql
-- Writer 크래시 시뮬레이션
ALTER SYSTEM CRASH;

-- 특정 시간(초) 동안 Writer 블로킹
ALTER SYSTEM SIMULATE POINT OF FAILURE FOR 60;
```

`ALTER SYSTEM CRASH`는 실제로 인스턴스를 크래시시킨다. 운영 환경에서 절대 실행하면 안 된다. 스테이징 환경에서만 사용해야 한다.

---

## 8. DB Proxy를 활용한 페일오버 다운타임 최소화

RDS Proxy를 Writer 앞에 두면 페일오버 시 다운타임을 크게 줄일 수 있다.

### 동작 방식

```
Application → RDS Proxy → Aurora Writer
                              ↓ (페일오버)
Application → RDS Proxy → 새 Aurora Writer
```

Proxy가 Aurora 내부 API를 통해 새 Writer를 감지한다. 애플리케이션은 Proxy 엔드포인트에만 연결하면 되고, DNS 변경을 신경 쓸 필요가 없다.

### 페일오버 시 차이

| 항목 | Proxy 없이 | Proxy 사용 |
|------|-----------|-----------|
| 다운타임 | 5~30초 | 1~5초 수준 |
| DNS 캐시 문제 | 있음 | 없음 |
| 커넥션 풀 관리 | 애플리케이션에서 처리 | Proxy가 처리 |
| 커넥션 멀티플렉싱 | 불가 | 가능 |

### Proxy 설정 시 주의사항

- Proxy는 VPC 내에서만 접근 가능하다. 퍼블릭 액세스가 필요한 경우 사용할 수 없다.
- Proxy는 Secrets Manager에 저장된 DB 자격 증명을 사용한다. IAM 인증도 지원한다.
- `idle-client-timeout` 기본값은 1800초(30분)이다. Lambda 같은 서버리스 환경에서는 이 값을 짧게 조정해야 커넥션이 쌓이지 않는다.
- Proxy를 쓰더라도 진행 중이던 트랜잭션은 롤백된다. 커넥션이 끊기지 않을 뿐이지, 트랜잭션 보장은 별개 문제다.

```bash
# Proxy 엔드포인트 확인
aws rds describe-db-proxies \
  --db-proxy-name my-proxy \
  --query 'DBProxies[0].Endpoint'
```

---

## 9. Global Database 페일오버

Aurora Global Database는 하나의 Primary 리전과 최대 5개의 Secondary 리전으로 구성된다. 리전 단위 장애에 대응하기 위한 구성이다.

### Managed Planned Failover

계획된 리전 전환이다. Primary 리전을 다른 리전으로 옮길 때 사용한다. 리전 마이그레이션이나 DR 훈련 시 쓴다.

```bash
aws rds switchover-global-cluster \
  --global-cluster-identifier my-global-cluster \
  --target-db-cluster-identifier arn:aws:rds:ap-southeast-1:123456789012:cluster:my-secondary-cluster
```

동작 순서:

1. Primary 리전의 Writer가 새로운 쓰기를 차단
2. Secondary 리전이 Primary의 미반영 변경사항을 모두 적용할 때까지 대기
3. Secondary가 새 Primary로 승격
4. 기존 Primary가 Secondary로 전환

데이터 손실이 없다. 다만 전환 중(보통 1~2분) 쓰기가 차단되므로, 트래픽이 적은 시간대에 진행해야 한다.

### Unplanned Failover (Detach & Promote)

Primary 리전 자체가 불능 상태일 때 사용한다. Secondary 클러스터를 Global Database에서 분리(detach)하고 독립된 클러스터로 승격시킨다.

```bash
# Secondary 클러스터를 Global Database에서 분리
aws rds remove-from-global-cluster \
  --global-cluster-identifier my-global-cluster \
  --db-cluster-identifier arn:aws:rds:ap-southeast-1:123456789012:cluster:my-secondary-cluster
```

이 작업은 되돌릴 수 없다. 분리된 클러스터는 독립된 Aurora 클러스터가 되고, 이후 애플리케이션의 엔드포인트를 이 클러스터로 변경해야 한다.

### Unplanned Failover에서 데이터 손실 가능성

Global Database의 복제는 비동기 방식이다. Primary→Secondary 복제 지연(RPO)은 보통 1초 미만이지만, 장애 시점에 아직 Secondary에 반영되지 않은 트랜잭션은 유실된다.

`ReplicationLag` CloudWatch 메트릭으로 복제 지연을 모니터링할 수 있다. 이 값이 평소에 수백ms 이상이면 네트워크 병목이나 Secondary 리전의 부하를 확인해야 한다.

---

## 10. 장애 시나리오별 대응

### 시나리오 1: Writer 인스턴스 장애

가장 흔한 경우다. 하드웨어 문제나 인스턴스 레벨 장애.

- Aurora가 자동으로 Reader를 승격 (30초 이내)
- 애플리케이션은 커넥션 에러를 감지하고 재연결해야 함
- DB Proxy 사용 시 1~5초 내 자동 전환

대응: tier 0 Reader를 미리 지정하고, 커넥션 풀의 validation 설정을 확인한다.

### 시나리오 2: 특정 AZ 장애

하나의 가용영역이 전체적으로 불능 상태.

- Writer가 해당 AZ에 있었다면 다른 AZ의 Reader로 승격
- Reader가 해당 AZ에 있었다면 Reader Endpoint에서 자동 제외
- 스토리지는 3개 AZ에 분산되어 있으므로 데이터는 안전함

대응: Writer와 tier 0 Reader를 서로 다른 AZ에 배치해야 한다. 같은 AZ에 있으면 AZ 장애 시 둘 다 날아간다.

```bash
# 인스턴스별 AZ 확인
aws rds describe-db-instances \
  --filters Name=db-cluster-id,Values=my-aurora-cluster \
  --query 'DBInstances[*].[DBInstanceIdentifier,AvailabilityZone,PromotionTier]' \
  --output table
```

### 시나리오 3: 리전 장애

리전 전체가 불능 상태. Global Database가 구성되어 있어야 대응 가능하다.

- Global Database가 없으면 해당 리전이 복구될 때까지 대기할 수밖에 없다
- Global Database가 있으면 Secondary 리전에서 Unplanned Failover를 실행한다
- 애플리케이션의 DB 엔드포인트를 Secondary 리전의 클러스터 엔드포인트로 변경해야 한다
- Route 53 헬스체크와 연동해서 자동 DNS 전환을 구성해 둘 수 있다

대응: Global Database를 구성하고, 평소에 Managed Planned Failover로 훈련해 둬야 한다. 실제 리전 장애 때 처음 해보면 실수가 나올 수밖에 없다.

---

## 11. Aurora vs. RDS MySQL

| 항목 | Aurora MySQL | RDS MySQL |
|------|--------------|-----------|
| 스토리지 | 공유 분산 스토리지 | 인스턴스마다 물리적 스토리지 |
| 장애 처리 방식 | Reader 승격 | Standby 인스턴스로 전환 |
| 데이터 복구 필요 | 없음 | 필요 (복제 및 리플레이) |
| 체감 장애 시간 | 수 초 내 회복 | 수십 초 ~ 수 분 |
| 엔드포인트 | Writer/Reader 논리 엔드포인트 | 인스턴스 주소 기반 |

---

## 12. 정리

- Aurora 페일오버는 빠르지만, 애플리케이션이 준비되지 않으면 다운타임이 길어진다
- JVM DNS 캐시를 5초 이하로 설정하고, HikariCP의 `keepalive-time`과 `validation-timeout`을 잡아야 한다
- DB Proxy를 쓰면 커넥션 관리 부담이 줄고 페일오버 다운타임도 짧아진다
- tier 0 Reader는 Writer와 같은 인스턴스 클래스, 다른 AZ에 배치한다
- Global Database는 리전 장애 대비용이며, Planned Failover로 주기적으로 훈련해야 한다
- 페일오버 테스트는 `failover-db-cluster` CLI로 할 수 있고, 스테이징에서 먼저 검증한다

---

## 참고

- [Aurora Failover](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html)
- [Aurora Global Database Failover](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)
- [RDS Proxy](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy.html)
- [AWS JDBC Driver](https://github.com/aws/aws-advanced-jdbc-wrapper)
- [DNS TTL 설정 (Java)](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/java-dg-jvm-ttl.html)
