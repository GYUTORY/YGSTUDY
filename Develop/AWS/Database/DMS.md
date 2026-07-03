---
title: AWS DMS (Database Migration Service)
tags: [aws, dms, database, migration, replication, cdc]
updated: 2026-01-18
---

# AWS DMS (Database Migration Service)

## 개요

DMS는 데이터베이스를 마이그레이션하는 서비스다. 소스 데이터베이스에서 타겟 데이터베이스로 데이터를 복사한다. 다운타임을 최소화하면서 마이그레이션할 수 있다. 온프레미스에서 AWS로, AWS 내에서, AWS에서 다른 곳으로 모두 가능하다.

### 왜 필요한가

데이터베이스를 옮겨야 하는 경우가 있다.

**상황 1: 온프레미스에서 AWS로**

**배경:**
회사 데이터센터에서 MySQL을 운영한다. AWS로 이전하고 싶다.

**전통적인 방법:**
1. 서비스를 중단한다
2. mysqldump로 백업한다
3. AWS RDS로 복원한다
4. 서비스를 재개한다

**문제:**
- 다운타임이 몇 시간에서 하루 이상
- 데이터가 많으면 복원이 오래 걸린다
- 고객이 서비스를 사용할 수 없다
- 문제가 생기면 롤백이 어렵다

**DMS의 해결:**
1. DMS 작업을 생성한다
2. 서비스는 계속 실행된다
3. DMS가 데이터를 복사한다
4. 실시간으로 변경사항을 동기화한다
5. 전환 준비가 되면 DNS를 변경한다
6. 다운타임: 몇 분

**상황 2: 데이터베이스 엔진 변경**

**배경:**
Oracle을 사용 중이다. 라이선스 비용이 비싸다. PostgreSQL로 바꾸고 싶다.

**문제:**
- Oracle과 PostgreSQL은 SQL이 다르다
- 데이터 타입이 다르다
- 직접 변환하면 며칠이 걸린다

**DMS의 해결:**
- 자동으로 데이터 타입을 변환한다
- Schema Conversion Tool(SCT)로 스키마 변환
- 다운타임 최소화

**상황 3: 데이터 복제**

**배경:**
프로덕션 데이터베이스의 데이터를 분석용 데이터베이스로 복제하고 싶다.

**문제:**
- 프로덕션에 부하를 주고 싶지 않다
- 실시간으로 동기화되어야 한다
- 읽기 전용 복제본으로는 부족하다 (다른 스키마 필요)

**DMS의 해결:**
- 지속적으로 데이터를 복제한다
- 소스에 최소한의 부하만 발생한다
- 타겟을 자유롭게 설정한다

## 핵심 개념

### Source (소스)

데이터를 가져올 데이터베이스다.

**지원 소스:**
- **관계형 데이터베이스:**
  - Oracle
  - Microsoft SQL Server
  - MySQL
  - MariaDB
  - PostgreSQL
  - SAP ASE
  - MongoDB
  - IBM Db2
- **AWS 데이터베이스:**
  - Amazon RDS (모든 엔진)
  - Amazon Aurora
  - Amazon S3
  - Amazon DocumentDB

### Target (타겟)

데이터를 저장할 데이터베이스다.

**지원 타겟:**
- **관계형 데이터베이스:**
  - MySQL
  - MariaDB
  - PostgreSQL
  - Oracle
  - Microsoft SQL Server
  - SAP ASE
- **AWS 데이터베이스:**
  - Amazon RDS
  - Amazon Aurora
  - Amazon Redshift
  - Amazon DynamoDB
  - Amazon S3
  - Amazon DocumentDB
  - Amazon Kinesis Data Streams
  - Amazon OpenSearch
  - Amazon Neptune

### Replication Instance

마이그레이션을 실행하는 EC2 인스턴스다. DMS가 자동으로 관리한다.

**역할:**
1. 소스에서 데이터를 읽는다
2. 필요하면 변환한다
3. 타겟에 쓴다

**인스턴스 크기:**
- **dms.t3.micro**: 테스트용
- **dms.t3.medium**: 소규모 마이그레이션
- **dms.c5.large**: 중규모 마이그레이션
- **dms.c5.xlarge** 이상: 대규모 마이그레이션

데이터양과 변경 속도에 따라 선택한다.

### Replication Task

실제 마이그레이션 작업이다. 무엇을 어떻게 복사할지 정의한다.

**설정:**
- 어떤 테이블을 복사할지
- 필터링 규칙
- 변환 규칙
- 마이그레이션 타입

## 마이그레이션 타입

### Full Load (전체 로드)

소스의 모든 데이터를 한 번에 복사한다.

**동작:**
1. 테이블 스캔
2. 모든 행 복사
3. 완료

**특징:**
- 시작 시점의 스냅샷
- 복사 중 변경사항은 반영 안 됨
- 가장 단순

**사용 사례:**
- 한 번만 복사
- 아카이빙
- 초기 데이터 로드

**단점:**
- 복사 중 변경사항 손실
- 다운타임 필요

### CDC (Change Data Capture)

변경사항만 지속적으로 복사한다.

**동작:**
1. 트랜잭션 로그를 읽는다
2. INSERT, UPDATE, DELETE를 파악한다
3. 타겟에 적용한다

**특징:**
- 실시간 동기화
- 다운타임 없음
- 소스 성능 영향 최소

**사용 사례:**
- 지속적인 복제
- 분석용 데이터 복제
- 재해 복구

**요구사항:**
- 소스에 트랜잭션 로그 활성화
- Primary Key 필수

### Full Load + CDC

전체 데이터를 복사한 후 변경사항을 계속 동기화한다.

**동작:**
1. Full Load 시작
2. 동시에 변경사항 캡처 시작
3. Full Load 완료
4. 캡처한 변경사항 적용
5. 이후 변경사항 계속 동기화

**특징:**
- 초기 데이터 + 실시간 동기화
- 다운타임 최소화
- 가장 많이 사용

**사용 사례:**
- 프로덕션 마이그레이션
- 다운타임 최소화 필요
- 전환 시점 유연하게 선택

## 실무 마이그레이션 과정

### 1단계: 준비

**소스 데이터베이스 확인:**
- 버전 지원 여부 확인
- 트랜잭션 로그 활성화
- Binary Logging 활성화 (MySQL)
- 마이그레이션용 계정 생성

**MySQL 예시:**
```sql
-- Binary Logging 확인
SHOW VARIABLES LIKE 'log_bin';

-- Binary Log 활성화 (my.cnf)
[mysqld]
server-id = 1
log-bin = mysql-bin
binlog_format = ROW
binlog_row_image = FULL

-- 계정 생성
CREATE USER 'dms_user'@'%' IDENTIFIED BY 'password';
GRANT SELECT, REPLICATION CLIENT, REPLICATION SLAVE ON *.* TO 'dms_user'@'%';
FLUSH PRIVILEGES;
```

**타겟 데이터베이스 준비:**
- RDS 인스턴스 생성
- 보안 그룹 설정
- 파라미터 그룹 설정

### 2단계: DMS 설정

**Replication Instance 생성:**
```bash
aws dms create-replication-instance \
  --replication-instance-identifier my-replication-instance \
  --replication-instance-class dms.c5.large \
  --vpc-security-group-ids sg-12345678 \
  --allocated-storage 100
```

**Source Endpoint 생성:**
```bash
aws dms create-endpoint \
  --endpoint-identifier source-mysql \
  --endpoint-type source \
  --engine-name mysql \
  --server-name source-db.example.com \
  --port 3306 \
  --username dms_user \
  --password password \
  --database-name mydb
```

**Target Endpoint 생성:**
```bash
aws dms create-endpoint \
  --endpoint-identifier target-aurora \
  --endpoint-type target \
  --engine-name aurora-postgresql \
  --server-name target-db.cluster-abc.us-west-2.rds.amazonaws.com \
  --port 5432 \
  --username admin \
  --password password \
  --database-name mydb
```

**연결 테스트:**
```bash
aws dms test-connection \
  --replication-instance-arn arn:aws:dms:us-west-2:123456789012:rep:ABC123 \
  --endpoint-arn arn:aws:dms:us-west-2:123456789012:endpoint:DEF456
```

모든 연결이 성공해야 한다.

### 3단계: Task 생성

**테이블 선택:**
```json
{
  "rules": [
    {
      "rule-type": "selection",
      "rule-id": "1",
      "rule-name": "include-all-tables",
      "object-locator": {
        "schema-name": "mydb",
        "table-name": "%"
      },
      "rule-action": "include"
    }
  ]
}
```

모든 테이블을 포함한다.

**특정 테이블만:**
```json
{
  "rules": [
    {
      "rule-type": "selection",
      "rule-id": "1",
      "object-locator": {
        "schema-name": "mydb",
        "table-name": "users"
      },
      "rule-action": "include"
    },
    {
      "rule-type": "selection",
      "rule-id": "2",
      "object-locator": {
        "schema-name": "mydb",
        "table-name": "orders"
      },
      "rule-action": "include"
    }
  ]
}
```

**Task 생성:**
```bash
aws dms create-replication-task \
  --replication-task-identifier my-migration-task \
  --source-endpoint-arn arn:aws:dms:us-west-2:123456789012:endpoint:SOURCE \
  --target-endpoint-arn arn:aws:dms:us-west-2:123456789012:endpoint:TARGET \
  --replication-instance-arn arn:aws:dms:us-west-2:123456789012:rep:INSTANCE \
  --migration-type full-load-and-cdc \
  --table-mappings file://table-mappings.json
```

### 4단계: 실행 및 모니터링

**Task 시작:**
```bash
aws dms start-replication-task \
  --replication-task-arn arn:aws:dms:us-west-2:123456789012:task:TASK123 \
  --start-replication-task-type start-replication
```

**진행 상황 확인:**
```bash
aws dms describe-replication-tasks \
  --filters Name=replication-task-arn,Values=arn:aws:dms:...:task:TASK123
```

**CloudWatch 모니터링:**
- FullLoadThroughputRowsTarget: 초당 복사 행 수
- CDCLatencySource: 소스 지연 시간
- CDCLatencyTarget: 타겟 지연 시간

### 5단계: 검증

**데이터 검증:**
Task 설정에서 Validation을 활성화한다.

```json
{
  "ValidationSettings": {
    "EnableValidation": true,
    "ThreadCount": 5
  }
}
```

DMS가 자동으로 데이터를 비교한다. 불일치가 있으면 CloudWatch에 기록된다.

**수동 검증:**
```sql
-- 소스
SELECT COUNT(*) FROM users;

-- 타겟
SELECT COUNT(*) FROM users;
```

행 수가 같은지 확인한다.

**샘플 데이터 확인:**
```sql
-- 소스
SELECT * FROM users WHERE id = 123;

-- 타겟
SELECT * FROM users WHERE id = 123;
```

값이 같은지 확인한다.

### 6단계: 전환

**지연 시간 확인:**
CloudWatch에서 `CDCLatencySource`를 확인한다. 1초 미만이면 거의 실시간이다.

**전환 준비:**
1. 애플리케이션 트래픽 줄이기
2. 지연 시간이 0에 가까워질 때까지 대기
3. 소스를 읽기 전용으로 전환 (선택)

**DNS 변경:**
```bash
# Route 53에서 데이터베이스 엔드포인트 변경
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch file://change-batch.json
```

**애플리케이션 재시작:**
새로운 데이터베이스로 연결한다.

**확인:**
- 애플리케이션이 정상 동작하는지
- 에러가 없는지
- 성능이 괜찮은지

### 7단계: 정리

**Task 중지:**
```bash
aws dms stop-replication-task \
  --replication-task-arn arn:aws:dms:...:task:TASK123
```

**리소스 삭제:**
```bash
# Task 삭제
aws dms delete-replication-task --replication-task-arn ...

# Endpoint 삭제
aws dms delete-endpoint --endpoint-arn ...

# Replication Instance 삭제
aws dms delete-replication-instance --replication-instance-arn ...
```

**소스 데이터베이스:**
- 백업 후 종료
- 또는 일정 기간 보관

## 스키마 변환

### AWS SCT (Schema Conversion Tool)

소스와 타겟의 데이터베이스 엔진이 다르면 스키마를 변환해야 한다.

**예시: Oracle → PostgreSQL**

**Oracle:**
```sql
CREATE TABLE employees (
  emp_id NUMBER PRIMARY KEY,
  emp_name VARCHAR2(100),
  hire_date DATE,
  salary NUMBER(10,2)
);
```

**PostgreSQL (SCT 변환):**
```sql
CREATE TABLE employees (
  emp_id INTEGER PRIMARY KEY,
  emp_name VARCHAR(100),
  hire_date DATE,
  salary NUMERIC(10,2)
);
```

**사용 방법:**
1. SCT 다운로드 및 설치
2. 소스와 타겟 연결
3. 스키마 분석
4. 변환 수행
5. 검토 및 수정
6. 타겟에 적용

**변환 리포트:**
SCT가 변환 가능 여부를 리포트한다.
- 자동 변환 가능: 초록색
- 수동 수정 필요: 노란색
- 변환 불가능: 빨간색

수동 수정이 필요한 부분을 확인하고 코드를 수정한다.

## 트러블슈팅

### Task가 실패한다

**로그 확인:**
```bash
aws dms describe-replication-tasks \
  --filters Name=replication-task-arn,Values=arn:aws:dms:...:task:TASK123
```

`LastFailureMessage`를 확인한다.

**흔한 원인:**

**1. 연결 실패:**
- 보안 그룹 설정 확인
- 네트워크 ACL 확인
- 데이터베이스 방화벽 확인

**2. 권한 부족:**
- 소스 계정 권한 확인
- 타겟 계정 권한 확인

**3. Primary Key 없음:**
CDC는 Primary Key가 필수다. 없으면 실패한다.

```sql
-- Primary Key 추가
ALTER TABLE users ADD PRIMARY KEY (id);
```

**4. 디스크 부족:**
Replication Instance의 디스크가 부족하다. 스토리지를 늘린다.

### 복사 속도가 느리다

**병목 지점 확인:**

**Replication Instance:**
CloudWatch에서 CPU, 메모리, 네트워크를 확인한다. 80% 이상이면 인스턴스를 크게 한다.

**소스 데이터베이스:**
쿼리가 느릴 수 있다. 인덱스를 확인한다.

```sql
-- MySQL: Slow Query Log 확인
SHOW VARIABLES LIKE 'slow_query_log';
SET GLOBAL slow_query_log = 'ON';
```

**타겟 데이터베이스:**
쓰기 성능이 부족할 수 있다. IOPS를 늘리거나 인스턴스를 크게 한다.

**최적화:**

**병렬 처리:**
Task 설정에서 병렬 로드를 활성화한다.

```json
{
  "ParallelLoadSettings": {
    "MaxFullLoadSubTasks": 8
  }
}
```

**배치 크기 조정:**
```json
{
  "BatchApplyEnabled": true,
  "BatchApplyTimeoutMin": 1,
  "BatchApplyTimeoutMax": 30,
  "BatchSplitSize": 0
}
```

### CDC 지연이 크다

**지연 시간 확인:**
CloudWatch에서 `CDCLatencySource`를 확인한다. 10초 이상이면 문제다.

**원인:**

**1. Replication Instance 성능:**
CPU나 네트워크가 부족하다. 더 큰 인스턴스로 변경한다.

**2. 타겟 쓰기 느림:**
타겟 데이터베이스의 IOPS를 확인한다. 부족하면 늘린다.

**3. 트랜잭션 로그 많음:**
소스의 쓰기 트래픽이 너무 많다. Replication Instance를 확장한다.

### 데이터 불일치

**Validation 확인:**
```bash
aws dms describe-table-statistics \
  --replication-task-arn arn:aws:dms:...:task:TASK123
```

`ValidationState`가 `Failed`인 테이블을 확인한다.

**재로드:**
문제가 있는 테이블을 다시 로드한다.

```bash
aws dms reload-tables \
  --replication-task-arn arn:aws:dms:...:task:TASK123 \
  --tables-to-reload SchemaName=mydb,TableName=users
```

## 주의사항

### LOB (Large Object) 처리

큰 텍스트나 바이너리 데이터는 특별히 처리해야 한다.

**설정:**
- **Limited LOB Mode**: 크기 제한 설정 (예: 32KB)
- **Full LOB Mode**: 전체 LOB 복사 (느림)

**권장:**
대부분의 LOB이 작으면 Limited LOB Mode를 사용한다. 크기를 적절히 설정한다.

### 트리거와 외래 키

타겟에서 트리거와 외래 키를 비활성화한다. Full Load 중에는 순서가 맞지 않을 수 있다.

**MySQL:**
```sql
SET FOREIGN_KEY_CHECKS = 0;
```

Full Load 완료 후 다시 활성화한다.

```sql
SET FOREIGN_KEY_CHECKS = 1;
```

### 다운타임 최소화

**테스트 마이그레이션:**
프로덕션 전에 테스트 환경에서 먼저 마이그레이션한다. 시간을 측정한다.

**Low Traffic 시간대:**
새벽이나 주말처럼 트래픽이 적은 시간에 전환한다.

**점진적 전환:**
- 읽기 트래픽부터 전환
- 쓰기 트래픽은 나중에
- 문제가 생기면 빠르게 롤백

### 비용 관리

**Replication Instance 크기:**
필요 이상으로 크게 만들지 않는다. 모니터링하면서 조정한다.

**Task 중지:**
마이그레이션이 끝나면 Task를 중지한다. 실행 중에는 비용이 발생한다.

**리소스 삭제:**
더 이상 필요 없으면 모든 리소스를 삭제한다.

## 비용

**Replication Instance:**
- dms.t3.medium: $0.219/시간 (약 $160/월)
- dms.c5.large: $0.346/시간 (약 $250/월)
- dms.c5.xlarge: $0.692/시간 (약 $500/월)

**스토리지:**
- $0.115/GB-월

**데이터 전송:**
- AWS 내 전송: 무료
- 인터넷 송신: 유료

**예시:**
- Replication Instance: dms.c5.large
- 스토리지: 100GB
- 기간: 7일

**비용:**
- Instance: $0.346 × 24시간 × 7일 = $58
- Storage: $0.115 × 100GB = $11.50
- 합계: 약 $70

마이그레이션이 끝나면 리소스를 삭제한다. 추가 비용이 발생하지 않는다.

## 참고

- AWS DMS 개발자 가이드: https://docs.aws.amazon.com/dms/
- DMS 요금: https://aws.amazon.com/dms/pricing/
- AWS SCT: https://aws.amazon.com/dms/schema-conversion-tool/
- 마이그레이션 모범 사례: https://docs.aws.amazon.com/dms/latest/userguide/CHAP_BestPractices.html

