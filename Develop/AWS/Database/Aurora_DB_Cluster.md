---
title: Aurora MySQL Writer Failover & Endpoint Routing
tags: [aws, aurora, mysql, rds, failover]
updated: 2026-01-04
---

# Aurora MySQL Writer 장애 전환과 엔드포인트 라우팅

이 문서는 Aurora MySQL의 Writer 인스턴스 장애 시 처리 방식과 엔드포인트 라우팅 전환 흐름을 실무 중심으로 정리합니다.  
복제/백업보다는 **연결 전환 관점**에 초점을 둡니다.

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

Aurora는 Writer 인스턴스에 장애가 발생하면, 자동으로 Reader 인스턴스 중 하나를 Writer로 승격시킵니다.

### 처리 과정 요약

1. Writer 인스턴스 장애 발생
2. 클러스터가 가장 최신 트랜잭션 로그를 가진 Reader를 식별
3. 해당 Reader를 Writer로 승격
4. **Writer 엔드포인트가 자동으로 새로운 Writer로 갱신됨**
5. 애플리케이션에서 DNS 갱신 후 새로운 Writer로 재연결

> 데이터 복구는 필요하지 않음. 스토리지는 항상 최신 상태 유지.

---

## 3. Writer 장애 시 연결 재시도 흐름

```plaintext
1. App → Writer: 쓰기 요청
2. Writer 응답 없음 (장애 발생)
3. 클러스터: Reader 중 하나를 Writer로 승격
4. App 재시도 → Writer Endpoint → 새 Writer로 연결
```

> **애플리케이션이 재시도하지 않으면 장애처럼 느껴질 수 있음**

---

## 4. Endpoint 구조 및 동작

### Writer Endpoint

- 클러스터 내 **현재 Writer 인스턴스**를 가리킴
- 장애 발생 시 자동으로 새 Writer로 갱신
- DNS 기반으로 동작 → TTL 반영됨

### Reader Endpoint

- 모든 Reader 인스턴스 중 하나로 라운드로빈 방식 라우팅
- 읽기 전용 트래픽 분산 처리용
- Reader 수가 많을수록 분산 효과 증가

---

## 5. 장애 시 자주 발생하는 문제

### 문제 1: Writer Endpoint 사용 중인데도 장애처럼 느껴짐

**원인**
- 기존 Writer로의 TCP 커넥션이 남아 있음 (커넥션 풀 미정리)
- DB 연결 실패 시 재시도 로직 부재

**대응**
- 커넥션 풀에서 장애 시 연결 정리
- 쓰기 실패 시 재시도 로직 구현

---

### 문제 2: 일부 애플리케이션만 장애 발생

**원인**
- DNS 캐시 TTL이 만료되지 않아 엔드포인트 갱신이 안됨
- 각 프로세스 또는 런타임마다 DNS 해석 방식 다름

**대응**
- 애플리케이션 DNS TTL 설정 명시 (예: JVM, Node.js)
- 전체 프로세스 재시작 또는 커넥션 풀 초기화 고려

---

## 6. 승격 대상 결정 기준

Aurora는 다음 기준에 따라 승격할 Reader를 결정합니다:

- 가장 최신 트랜잭션 로그 위치 (Log Sequence Number)
- 인스턴스 상태 (CPU, 네트워크, 헬스체크)
- 가용영역 분산 고려
- 수동 설정된 우선순위 값 (기본 미사용)

---

## 7. Aurora vs. RDS MySQL

| 항목 | Aurora MySQL | RDS MySQL |
|------|--------------|-----------|
| 스토리지 | 공유 분산 스토리지 | 인스턴스마다 물리적 스토리지 |
| 장애 처리 방식 | Reader 승격 | Standby 인스턴스로 전환 |
| 데이터 복구 필요 | 없음 | 필요 (복제 및 리플레이) |
| 체감 장애 시간 | 수 초 내 회복 | 수십 초 ~ 수 분 |
| 엔드포인트 | Writer/Reader 논리 엔드포인트 | 인스턴스 주소 기반 |

---

## 8. 실무 팁

- **Writer Endpoint 사용은 필수**  
  → Writer 장애 시에도 자동으로 갱신되는 논리 엔드포인트

- **DB 연결 풀 관리 중요**  
  → 장애 시 커넥션 풀 초기화 없으면 회복되지 않음

- **DNS TTL 명시 설정**  
  → Java: `networkaddress.cache.ttl=30`  
  → Node.js: DNS cache 라이브러리 사용

- **실패 재시도 로직 구성**  
  → 쓰기 실패 시 짧은 지연 후 재시도. 영구 실패 시 알림

---

## 9. 정리

- Aurora는 장애 발생 시 **스토리지 복구가 아닌 연결 대상 전환**
- 장애 복구는 빠르지만, 애플리케이션이 준비되지 않으면 서비스 중단 체감 발생
- Writer Endpoint + 재시도 로직 + 커넥션 풀 관리가 핵심

---

## 참고

- [Aurora MySQL Failover Mechanism](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.html#Aurora.Managing.FaultTolerance)
- [Best Practices for Aurora Connections](https://aws.amazon.com/premiumsupport/knowledge-center/aurora-failover-reconnect/)
- [DNS TTL 설정 예시 (Java)](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/java-dg-jvm-ttl.html)