---
title: RDS Storage
tags: [aws, database, encryption, cloud]
updated: 2026-07-25
---

# RDS Storage

## 스토리지 유형

RDS는 EBS 기반 스토리지를 사용한다. 인스턴스 성능보다 스토리지 IOPS가 병목이 되는 경우가 생각보다 많고, 처음에 잘못 고르면 나중에 교체 비용이 크다.

### Magnetic (standard)

가장 오래된 스토리지 유형. 신규 워크로드에서는 선택할 이유가 없다.

- 버스트 기능 없음, IOPS 예측 불가
- 최대 1,000 IOPS 수준이나 실제로는 들쭉날쭉함
- 스토리지 크기 제한도 낮음 (최대 3 TiB)

AWS 공식 문서에서도 레거시 용도라고 명시한다. 구형 인스턴스를 그대로 쓰는 경우가 아니면 gp2나 gp3를 써야 한다.

### gp2

범용 SSD. 스토리지 크기와 IOPS가 연동되는 구조다.

- 1 GiB당 3 IOPS 제공 (최소 100, 최대 16,000 IOPS)
- 100 GiB → 300 IOPS, 5,334 GiB 이상 → 16,000 IOPS 고정
- 버스트 크레딧 방식으로 최대 3,000 IOPS까지 일시적으로 올라갈 수 있음

gp2의 가장 큰 문제는 IOPS를 더 확보하려면 스토리지를 늘려야 한다는 점이다. 실제로 필요한 용량은 200 GiB인데 IOPS 때문에 1 TiB를 할당하는 상황이 생긴다. 이 문제 때문에 신규 워크로드에서는 gp3를 선택하는 게 낫다.

### gp3

gp2의 후속 유형. 스토리지 크기와 IOPS, 처리량이 모두 독립적으로 설정된다.

- 기본 3,000 IOPS, 125 MB/s 처리량을 크기와 무관하게 제공
- IOPS는 최대 16,000까지, 처리량은 최대 1,000 MB/s까지 별도로 조정 가능
- gp2 대비 20% 저렴 (동일 크기 기준)

**IOPS와 처리량은 별개 항목으로 과금된다.** 3,000 IOPS를 초과하는 부분은 IOPS당 $0.02/월이 붙고, 125 MB/s를 초과하는 처리량은 MB/s당 $0.04/월이 붙는다. 예를 들어 6,000 IOPS와 500 MB/s로 설정하면 초과 IOPS 3,000에 대한 비용 $60/월과 초과 처리량 375 MB/s에 대한 비용 $15/월이 스토리지 비용에 추가된다.

처리량 조정이 필요한 경우는 순차 읽기가 많은 분석 쿼리나 대용량 백업 작업이다. OLTP 워크로드에서는 IOPS가 더 중요하고, 125 MB/s 기본값으로 충분한 경우가 대부분이다.

### io1

프로비저닝된 IOPS SSD. 고성능이 필요한 OLTP 워크로드에 쓴다.

- 최대 64,000 IOPS (Nitro 기반 인스턴스 한정)
- IOPS:GiB 비율 최대 50:1 (100 GiB → 최대 5,000 IOPS)
- gp3보다 비싸고, 스토리지와 IOPS를 각각 과금

io1은 실제로 64,000 IOPS에 도달하는 워크로드가 아니면 gp3로도 충분한 경우가 많다.

### io2 Block Express

io1의 후속으로, 고성능과 높은 내구성이 특징이다.

- 최대 256,000 IOPS (Block Express 아키텍처)
- 최대 4,000 MB/s 처리량
- IOPS:GiB 비율 최대 1,000:1
- 내구성 99.999% (io1의 99.9%보다 높음)

**io2 Block Express는 Nitro 기반 인스턴스에서만 동작한다.** 지원 인스턴스는 r5b, x2idn, x2iedn이 대표적이며, 이 외의 인스턴스에서 io2를 선택하면 Block Express 기능 없이 io2로만 동작한다. 실제로 256,000 IOPS를 활용하려면 인스턴스 유형 선택을 먼저 확인해야 한다.

io2 Block Express는 Oracle RAC 같은 극단적인 IOPS 요구 사항이 있을 때 쓴다. 일반적인 웹 서비스 DB에서 쓸 일은 드물다.

### 비용 비교 (us-east-1 기준, 대략적인 수치)

| 유형 | 스토리지 | IOPS | 처리량 |
|------|----------|------|--------|
| Magnetic | $0.10/GiB | 불규칙 | - |
| gp2 | $0.115/GiB | 크기에 연동 | - |
| gp3 | $0.092/GiB | $0.02/IOPS (3,000 초과분) | $0.04/MB/s (125 초과분) |
| io1 | $0.125/GiB | $0.10/IOPS | - |
| io2 | $0.125/GiB | $0.065~0.10/IOPS | - |

io2는 IOPS 사용량에 따라 단가가 다르다. 처음 32,000 IOPS는 $0.10/IOPS, 이후 구간은 단가가 낮아진다.

---

## 엔진별 최대 스토리지 한도

스토리지 크기를 계획할 때 엔진별 상한선을 먼저 확인해야 한다. 오토스케일링 최대값을 엔진 한도 이상으로 설정해도 해당 한도까지만 올라간다.

| 엔진 | 최대 스토리지 |
|------|-------------|
| MySQL | 64 TiB |
| PostgreSQL | 64 TiB |
| MariaDB | 64 TiB |
| Oracle | 64 TiB |
| SQL Server | 16 TiB |

SQL Server는 다른 엔진의 1/4 수준이다. SQL Server 기반 워크로드를 설계할 때 이 제한을 처음부터 고려해야 한다. 16 TiB를 넘어서는 데이터는 파티셔닝이나 아카이브 전략을 별도로 세워야 한다.

Aurora는 RDS 스토리지 제한과 별도로 동작한다. Aurora는 128 TiB까지 자동으로 확장되며, 스토리지 타입 개념이 없다.

---

## gp2 크레딧 버스트 소진 문제

gp2는 버스트 크레딧 잔액이 있을 때 최대 3,000 IOPS까지 올라간다. 크레딧이 고갈되면 기본 IOPS로 떨어진다.

### 버스트 크레딧 계산 방식

- 크레딧 적립: 1초당 (기본 IOPS - 현재 소비 IOPS) × 1 크레딧
- 최대 크레딧 잔액: 스토리지 크기 × 3,600 I/O 크레딧 (초기 잔액 기준으로 환산)
- 100 GiB 볼륨 기준 초기 크레딧 = 540만 크레딧, 3,000 IOPS 버스트로 소진하면 약 50분

실제 문제 상황: 평소에는 문제없다가 배포 후 트래픽이 몰리거나 대용량 쿼리가 실행될 때 갑자기 DB 응답이 느려지는 경우다. CloudWatch의 `BurstBalance` 지표가 0%에 가까워지면 버스트 크레딧 고갈이 원인일 가능성이 높다.

해결 방법은 두 가지다. 스토리지를 늘려 기본 IOPS를 높이거나, gp3로 전환해 크레딧 방식 자체를 없애는 것이다. gp3는 버스트 크레딧 개념이 없고 기본 3,000 IOPS를 항상 제공한다.

---

## 스토리지 오토스케일링

RDS 스토리지 오토스케일링을 활성화하면 용량이 부족할 때 자동으로 늘어난다.

### 확장 조건 (세 가지 모두 충족해야 트리거)

1. 여유 스토리지가 할당 용량의 10% 미만
2. 이 상태가 5분 이상 지속
3. 마지막 스토리지 수정 이후 6시간 경과

확장 크기는 다음 중 가장 큰 값으로 결정된다.

- 현재 크기의 10%
- 7일치 성장 예측량
- 최소 5 GiB

예를 들어 100 GiB 스토리지에서 오토스케일이 트리거되면 최소 10 GiB(10%)가 추가된다. 하루에 2 GiB씩 증가하는 패턴이면 14 GiB를 예측해 적용한다.

### 주의사항

오토스케일링이 트리거된 이후 다시 트리거되려면 6시간을 기다려야 한다. 갑자기 대용량 데이터가 들어오는 상황에서는 이 인터벌이 문제가 된다. 오토스케일링을 믿고 최소 용량으로 운영하기보다는 여유 있게 잡아두는 편이 낫다.

오토스케일링 최대 크기를 설정할 수 있는데, 설정하지 않으면 기본값은 인스턴스 유형에 따라 다르다. 예산 초과를 막으려면 최대 크기를 명시적으로 지정해야 한다.

---

## 스토리지 축소 불가 문제

RDS는 스토리지를 줄이는 기능을 제공하지 않는다. 한 번 늘리면 AWS 콘솔에서 다시 줄일 수 없다.

대용량 데이터를 일시적으로 적재하다가 삭제한 경우, 또는 오토스케일링이 과도하게 확장된 경우에 스토리지 낭비가 생긴다.

### 스냅샷 복원을 통한 우회 방법

1. 현재 DB 인스턴스의 스냅샷 생성
2. 스냅샷에서 새 인스턴스 생성 시 더 작은 스토리지 크기 지정
3. 애플리케이션을 새 인스턴스로 전환
4. 기존 인스턴스 삭제

단, 스냅샷 복원 시 실제 데이터 크기보다 작은 스토리지를 지정하면 실패한다. 현재 실제 사용 중인 데이터 크기를 먼저 확인해야 한다.

```sql
-- MySQL/MariaDB에서 실제 데이터 크기 확인
SELECT 
    table_schema AS 'Database',
    ROUND(SUM(data_length + index_length) / 1024 / 1024 / 1024, 2) AS 'Size (GB)'
FROM information_schema.tables
GROUP BY table_schema;
```

PostgreSQL은 `pg_database_size()` 또는 `pg_size_pretty(pg_database_size('dbname'))`로 확인한다.

스냅샷 복원 방법의 단점은 다운타임이 발생한다는 점이다. Multi-AZ나 Read Replica를 사용하는 경우 전환 절차가 복잡해진다. 실제로 스토리지 비용 절감 효과가 이 작업 비용보다 클 때만 진행하는 게 맞다.

---

## 스토리지 유형 변경 시 동작

### 소요 시간과 성능 저하

스토리지 유형 변경(gp2→gp3 등)이나 크기 확장은 다운타임 없이 진행된다. 하지만 백그라운드에서 데이터 마이그레이션이 진행되는 동안 성능 저하가 발생한다.

- 100 GiB 미만: 수십 분 내
- 500 GiB ~ 1 TiB: 1~3시간
- 수 TiB 이상: 몇 시간에서 반나절까지 걸리기도 함

변경 진행 중 IOPS 성능이 기존 대비 50~70% 수준으로 떨어지는 경우가 있다. `WriteLatency`와 `DiskQueueDepth`를 변경 전후로 CloudWatch에서 모니터링해야 한다.

변경 완료 후에도 `optimizing` 상태가 한동안 유지된다. 이 상태에서는 추가 스토리지 변경을 할 수 없고, 6시간 쿨다운이 적용된다.

### Multi-AZ 환경에서의 변경

Multi-AZ 환경에서 스토리지를 변경하면 처리 순서가 다르다.

1. Standby 인스턴스에 먼저 변경 적용
2. Standby 변경 완료 후 Failover 수행 (Standby가 Primary로 승격)
3. 기존 Primary에 변경 적용

이 방식 덕분에 실제 서비스 영향 시간은 Failover에 걸리는 몇 초 수준으로 줄어든다. 하지만 전체 변경 작업이 완료되는 데는 Single-AZ보다 오래 걸린다. 두 인스턴스에 순차적으로 적용되기 때문이다.

Multi-AZ 환경에서 스토리지 변경 중 Failover가 발생하면 기존 Primary가 Standby 역할을 맡아 변경 작업을 이어받는다. 변경 작업이 완전히 끝날 때까지 추가 변경 요청은 블록된다.

---

## 스토리지 암호화

### 암호화 설정 규칙

스토리지 암호화는 인스턴스 생성 시점에 결정한다. **생성 이후에는 암호화 여부를 변경할 수 없다.** 암호화되지 않은 인스턴스를 나중에 암호화하려면 스냅샷→복원 과정이 필요하다.

암호화를 활성화하면 스토리지, 자동 백업, Read Replica, 스냅샷 모두 동일한 KMS 키로 암호화된다. KMS 키는 AWS 관리형 키(`aws/rds`)나 고객 관리형 키(CMK) 중 선택한다.

스냅샷 복원 시 암호화 키를 교체하거나 암호화되지 않은 스냅샷을 암호화된 인스턴스로 복원하는 것은 가능하다.

### 스토리지 타입과 암호화의 관계

gp2, gp3, io1, io2 모두 암호화를 지원한다. 스토리지 타입을 변경해도 암호화 설정은 유지된다. gp2에서 gp3로 바꿔도 이미 설정된 KMS 키가 그대로 적용된다.

Cross-region 스냅샷 복사 시 대상 리전의 KMS 키를 별도로 지정해야 한다. 원본 키가 다른 리전에서 자동으로 사용되지 않는다.

```bash
# 암호화되지 않은 스냅샷을 암호화된 스냅샷으로 복사
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:ap-northeast-2:123456789:snapshot:my-snapshot \
  --target-db-snapshot-identifier my-encrypted-snapshot \
  --kms-key-id arn:aws:kms:ap-northeast-2:123456789:key/my-key-id \
  --region ap-northeast-2
```

---

## gp2 → gp3 마이그레이션

gp3 전환은 다운타임 없이 진행되고, 전환 후 비용이 줄어드는 경우가 대부분이다. 특히 gp2에서 IOPS 확보를 위해 과도하게 스토리지를 늘린 경우 효과가 크다.

전환 전에 확인해야 할 것은 현재 IOPS와 처리량 사용 패턴이다. gp2에서 16,000 IOPS를 쓰고 있었다면 gp3에서 동일한 IOPS를 명시적으로 설정해야 한다. 기본 3,000 IOPS로 전환하면 성능이 크게 떨어진다.

### 콘솔

1. RDS 콘솔 → 해당 인스턴스 선택 → [수정]
2. 스토리지 섹션에서 스토리지 유형을 `gp3`로 변경
3. IOPS와 처리량 값 확인 및 조정
4. [계속] → [즉시 적용] 또는 [다음 유지 관리 기간에 적용] 선택

즉시 적용을 선택하면 변경이 바로 시작된다. 피크 타임에는 다음 유지 관리 기간을 선택하는 게 낫다.

### CLI

```bash
# gp2 → gp3 전환, IOPS와 처리량 명시 설정
aws rds modify-db-instance \
  --db-instance-identifier my-db-instance \
  --storage-type gp3 \
  --iops 6000 \
  --storage-throughput 500 \
  --apply-immediately \
  --region ap-northeast-2

# 변경 상태 확인
aws rds describe-db-instances \
  --db-instance-identifier my-db-instance \
  --query 'DBInstances[0].PendingModifiedValues' \
  --region ap-northeast-2
```

`--apply-immediately`를 빼면 다음 유지 관리 기간에 적용된다. 운영 환경에서는 유지 관리 기간을 지정하고 변경하는 편이 안전하다.

### Terraform

```hcl
resource "aws_db_instance" "main" {
  identifier        = "my-db-instance"
  engine            = "mysql"
  instance_class    = "db.r6g.large"

  storage_type          = "gp3"
  allocated_storage     = 200
  iops                  = 6000
  storage_throughput    = 500

  # 기존 gp2에서 전환 시 apply_immediately = true 권장
  apply_immediately = false
}
```

기존 gp2 인스턴스를 Terraform으로 관리하고 있었다면 `storage_type`을 `"gp3"`로 바꾸고, `iops`와 `storage_throughput` 필드를 추가하면 된다. `terraform plan`으로 변경 사항을 확인한 뒤 적용한다.

---

## IOPS 병목 진단

DB가 느려질 때 CPU나 메모리보다 먼저 스토리지 IOPS를 의심해야 하는 경우가 있다. 특히 쓰기 집약적인 워크로드에서 자주 나타난다.

### CloudWatch 지표

| 지표 | 설명 |
|------|------|
| `ReadIOPS` | 초당 읽기 작업 수 |
| `WriteIOPS` | 초당 쓰기 작업 수 |
| `ReadLatency` | 읽기 지연 시간 (초) |
| `WriteLatency` | 쓰기 지연 시간 (초) |
| `DiskQueueDepth` | 대기 중인 I/O 요청 수 |
| `BurstBalance` | gp2 크레딧 잔량 (%) |
| `ReadThroughput` | 초당 읽기 처리량 (bytes) |
| `WriteThroughput` | 초당 쓰기 처리량 (bytes) |

`DiskQueueDepth`가 1을 넘어가면 I/O 요청이 쌓이고 있다는 신호다. 지속적으로 1 이상이면 프로비저닝된 IOPS가 부족한 상태다.

`WriteLatency`가 1ms 이하면 정상, 10ms 이상으로 올라가면 스토리지가 병목인 경우가 많다.

### Performance Insights로 확인

Performance Insights의 `db load` 그래프에서 대기 이벤트를 확인할 수 있다. `wait/io/file/innodb/innodb_data_file` (MySQL) 또는 `io` 관련 대기 이벤트 비중이 높으면 스토리지 I/O가 병목이다.

```bash
# AWS CLI로 CloudWatch 지표 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DiskQueueDepth \
  --dimensions Name=DBInstanceIdentifier,Value=my-db-instance \
  --start-time 2026-07-25T00:00:00Z \
  --end-time 2026-07-25T01:00:00Z \
  --period 60 \
  --statistics Average \
  --region ap-northeast-2
```

운영 중에 IOPS 조정이 필요하면 피크 시간대를 피해서 진행하고, 변경 중에도 CloudWatch로 지연 시간을 모니터링한다.
