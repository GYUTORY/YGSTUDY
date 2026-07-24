---
title: RDS Multi-AZ
tags: [aws, database, rds, multi-az, failover, high-availability, dns, read-replica]
updated: 2026-07-24
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

## Read Replica와 함께 쓸 때

Multi-AZ와 Read Replica는 별개 개념이다. Multi-AZ는 고가용성(HA)을 위한 구성이고, Read Replica는 읽기 성능 분산을 위한 구성이다.

Multi-AZ 인스턴스를 쓰더라도 읽기 부하 분산이 필요하면 Read Replica를 별도로 만들어야 한다. Standby는 읽기 불가다.

Multi-AZ 클러스터는 내부 Reader 2개가 읽기를 처리하지만, 이 Reader들이 Read Replica는 아니다. 클러스터 외부에 추가로 Read Replica를 붙이는 것도 가능하다.

Read Replica는 비동기 복제다. Primary가 커밋한 데이터가 Replica에 반영되기까지 지연(replication lag)이 발생한다. 보통 수백 밀리초 이내지만, 대량 쓰기가 몰리거나 Replica의 CPU가 높을 때는 수 초에서 수십 초까지 늘어난다.

페일오버가 발생했을 때 Read Replica는 자동으로 새 Primary를 따라가지만, 복제 소스가 바뀌고 재동기화되는 과정에서 복제 지연이 급증한다. 이 시간에 Replica에서 오래된 데이터를 읽으면 사용자에게 잘못된 정보가 노출된다.

대응 방법은 두 가지다. 최신성이 중요한 쿼리는 Primary에서만 읽는다. 읽기 성능이 더 나빠지지만 데이터 정합성이 보장된다. 세밀하게 제어하고 싶다면 `ReplicaLag` CloudWatch 메트릭을 보고 임계치를 넘은 Replica로는 트래픽을 보내지 않는 로직을 앱 쪽에 넣는다.

Cross-Region Read Replica는 지연이 더 크다. 리전 간 네트워크 지연이 기본으로 수십 ms 이상이고, 대량 트랜잭션이 있을 때는 분 단위로 늘어난다. 강한 일관성이 필요한 쿼리는 Primary 리전에서만 처리하도록 설계해야 한다.

## 페일오버 테스트

운영 환경에 올리기 전에 반드시 테스트해봐야 한다. 이론상 60~120초라고 해도 우리 앱이 실제로 얼마나 버티는지는 직접 확인해야 안다.

AWS 콘솔에서 RDS 인스턴스를 선택하고 "Reboot" 옵션에서 "Reboot With Failover"를 선택하면 강제 페일오버가 발생한다. CLI로는 아래처럼 실행한다.

```bash
# Multi-AZ 인스턴스 강제 페일오버
aws rds reboot-db-instance \
  --db-instance-identifier my-db-instance \
  --force-failover

# Multi-AZ 클러스터 Writer 수동 교체
aws rds failover-db-cluster \
  --db-cluster-identifier my-db-cluster
```

테스트할 때 앱 서버에서 DB 연결을 계속 시도하는 스크립트를 같이 돌려두면 어느 시점에 에러가 발생하고 몇 초 후에 복구되는지 정확히 측정할 수 있다.

```bash
# 60초 동안 1초마다 연결 상태 확인 (MySQL)
for i in $(seq 1 60); do
  echo -n "$(date '+%H:%M:%S') - "
  mysql -h mydb.xxxxxxxxx.ap-northeast-2.rds.amazonaws.com \
    -u admin -ppassword \
    --connect-timeout=3 \
    -e "SELECT NOW();" 2>&1 | tail -1
  sleep 1
done
```

RDS 이벤트 로그에서 "Multi-AZ instance failover started" 이후 "Multi-AZ instance failover completed"까지 시간 차이를 기록한다. CloudWatch에서 `DatabaseConnections` 메트릭이 0으로 떨어졌다가 올라오는 구간도 함께 확인한다.

앱 레이어에서 DB 에러가 발생했을 때 재시도 로직이 제대로 동작하는지 검증하는 게 핵심이다. 재시도 없이 바로 에러를 사용자에게 내려보내는 구조라면 페일오버 시간 동안 실제 장애가 된다. 일시적인 DB 연결 오류를 잡아서 N회 재시도하도록 처리하면 다운타임을 크게 줄일 수 있다.

커넥션 풀 설정도 함께 검증한다. HikariCP 기준으로 `connectionTimeout`이 너무 길면 (기본 30초) 페일오버 동안 스레드가 DB 연결 대기에 묶여서 앱 전체가 느려진다. `connectionTimeout`을 5~10초로 줄이고 재시도 로직을 조합해서 빠르게 실패하고 빠르게 재시도하는 패턴이 낫다.

```yaml
# HikariCP 설정 예시 (Spring Boot)
spring:
  datasource:
    hikari:
      connection-timeout: 5000    # 5초 내 연결 못 하면 실패
      validation-timeout: 3000    # 헬스체크 타임아웃
      max-lifetime: 1800000       # 커넥션 30분 후 교체 (페일오버 후 낡은 커넥션 정리)
      keepalive-time: 30000       # 30초마다 keepalive
```
