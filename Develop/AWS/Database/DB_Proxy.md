---
title: AWS DB Proxy
tags: [aws, database, dbproxy]
updated: 2026-01-06
---

# AWS DB Proxy

## 1. 개요

AWS DB Proxy는 애플리케이션과 RDS/Aurora 데이터베이스 사이에 위치하여 연결을 풀링하고, 연결 수를 효율적으로 관리해주는 완전관리형 프록시 서비스입니다.

## 2. 사용 목적

- 데이터베이스 연결 수 제한 해결
- Lambda 등 서버리스 환경에서의 연결 성능 개선
- 연결 재사용으로 데이터베이스 부하 감소
- IAM 인증 및 Secrets Manager와 연동된 보안 강화
- 장애 복구 자동화 (failover 자동 전환)

---

## 3. 주요 기능

### 3.1 연결 풀링 (Connection Pooling)

- 애플리케이션에서 DB 연결 요청 시, 새 연결 생성 없이 기존 연결 재사용
- 커넥션 생성/종료에 따른 DB 리소스 소비 최소화
- 실시간 트래픽 변화에 따라 자동 조정되는 연결 풀

### 3.2 장애 자동 복구 (Automatic Failover)

- RDS 또는 Aurora 장애 시 자동으로 프록시가 정상 인스턴스로 연결 전환
- 애플리케이션 코드를 변경하지 않아도 무중단 처리 가능

### 3.3 보안 기능

- **IAM 인증 지원**: DB 사용자명/비밀번호 없이 IAM 권한으로 접근 가능
- **Secrets Manager 연동**: 자격 증명 자동 로테이션
- **SSL/TLS 암호화**: 데이터 전송 보안
- **VPC 내부 통신**: 퍼블릭 노출 없이 격리된 환경에서 사용 가능

### 3.4 읽기/쓰기 분리

- Aurora 기반에서 읽기 전용 복제본으로 자동 분산 처리 가능
- 쓰기 부하와 읽기 부하를 분리하여 성능 향상

---

## 4. 지원 데이터베이스 엔진

### RDS

- MySQL 5.7, 8.0
- PostgreSQL 10 이상
- MariaDB 10.3 이상
- SQL Server 2016 이상

### Aurora

- Aurora MySQL
- Aurora PostgreSQL

---

## 5. 아키텍처 구성 예시

```
[Application Layer]
        ↓
[DB Proxy Endpoint]
        ↓
[Connection Pool Manager]
        ↓
[RDS / Aurora DB Cluster]
```

### 구성 방식

- 프록시 엔드포인트는 VPC 내부에서 운영
- 읽기/쓰기 연결을 분리하여 설정 가능
- 보안 그룹 및 서브넷 설정 필요

---

## 6. 서버리스 연동 예시 (Lambda)

- Lambda 실행 시 매번 새 DB 연결 생성은 비효율적
- DB Proxy와 연결하면 기존 연결을 재사용
- 콜드 스타트 시간 단축 및 커넥션 누수 방지
- 동시에 수천 개의 Lambda 함수가 실행되어도 효율적으로 DB 연결 처리

---

## 7. 모니터링 및 로깅

### CloudWatch 메트릭

- `DatabaseConnections`: 현재 연결 수
- `ClientConnections`: 애플리케이션에서 프록시로의 연결 수
- `ActiveConnections`: 현재 활성 연결 수
- `DatabaseResponseTime`: DB 응답 지연 시간
- `QueryResponseTime`: 쿼리 응답 시간

### CloudWatch Logs (옵션)

- SQL 실행 및 오류 로그를 기록 가능 (옵션)
- 성능 이슈 또는 장애 원인 분석 가능

---

## 8. 비용

- **시간당 요금**: 실행 중인 DB Proxy 인스턴스 수에 따라 과금
- **요금 기준**: vCPU 개수와 연결 수량
- **기본 요금**: 지역별 상이. 예: 서울 리전 기준 약 $0.048/hour

**비용 최적화 전략**
- DB Proxy 사용 대상을 필요한 워크로드에만 제한
- 연결 풀 사이즈 조정
- DB Proxy 인스턴스 공유 전략

---

## 9. 제한사항 및 주의점

| 항목 | 제한 |
|------|------|
| 연결 수 | 엔진/인스턴스 유형에 따라 제한 |
| 지원 DB 버전 | 일부 구버전 지원 불가 |
| 쓰기/읽기 분리 | Aurora 에서만 지원 |
| 연결 유지 | 장기 유휴 연결은 종료될 수 있음 |
| RDS Multi-AZ | 장애 조치 전환에 약간의 지연 발생 가능 |

---

## 10. 보안 구성 팁

- DB Proxy는 퍼블릭 액세스를 차단하고 VPC 내부에서만 접근 가능하도록 구성
- 보안 그룹: 애플리케이션 → DB Proxy만 허용
- DB Proxy → RDS: 내부 통신 허용
- IAM 역할을 애플리케이션에 부여하여 인증
- Secrets Manager 사용 시 수동으로 자격 증명을 관리하지 않아도 됨

---

## 11. 실무 적용 시나리오

### Lambda + RDS

- Lambda → DB Proxy → RDS 구성
- 커넥션 풀로 Lambda cold start 문제 완화

### ECS / EC2 → Aurora

- 다수의 ECS task 또는 EC2 인스턴스에서 동일 DB로 접근 시 연결 관리 간소화

### MSA 환경

- 마이크로서비스 별로 DB Proxy endpoint 분리
- 트래픽 패턴에 따라 개별적으로 최적화 가능

---

## 12. 구성 요약

| 항목 | 설정 |
|------|------|
| VPC 배포 필수 여부 | ✅ 필수 |
| IAM 인증 | ✅ 지원 |
| Secrets Manager 연동 | ✅ 지원 |
| CloudWatch 연동 | ✅ 지원 |
| 장애 자동 전환 | ✅ 지원 (Multi-AZ 환경) |
| SSL 암호화 | ✅ 가능 |
| 연결 풀 설정 | ✅ 자동 조정 |
| Aurora 읽기 분산 | ✅ 지원 (Aurora만) |

---

## 13. 참고 링크

- [AWS 공식 문서 - DB Proxy](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy.html)
- [DB Proxy Best Practices](https://aws.amazon.com/blogs/database/best-practices-for-working-with-amazon-rds-proxy/)
- [Pricing](https://aws.amazon.com/rds/proxy/pricing/)
- [CloudWatch Metrics](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy.monitoring.html)