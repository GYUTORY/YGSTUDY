---
title: RDS Backup & Snapshot
tags: [aws, database, rds, backup, snapshot, PITR, point-in-time-recovery, dr, disaster-recovery, cross-region]
updated: 2026-07-24
---

# RDS Backup & Snapshot

RDS 백업은 자동 백업과 수동 스냅샷 두 가지로 나뉜다. 이름이 비슷해서 혼동하기 쉽지만, 보존 기간과 삭제 동작, PITR 지원 여부가 다르다. DR 구성이나 규정 준수 요건을 맞추려면 이 차이를 정확히 알아야 한다.

## 자동 백업과 수동 스냅샷 차이

### 자동 백업

RDS 인스턴스를 만들 때 기본으로 활성화된다. 보존 기간은 1~35일 사이에서 지정한다. 보존 기간을 0으로 설정하면 자동 백업이 비활성화된다.

자동 백업은 두 가지 요소로 구성된다. 첫째는 매일 백업 창(backup window) 동안 생성되는 일별 스냅샷이고, 둘째는 트랜잭션 로그(transaction log)다. 이 두 가지가 함께 있어야 PITR이 가능하다. 스냅샷만 있고 트랜잭션 로그가 없으면 특정 시점 복원이 불가능하고, 스냅샷 생성 시점으로만 복원된다.

인스턴스를 삭제할 때 자동 백업은 같이 삭제된다. 이게 가장 흔한 실수다. 개발 환경 인스턴스를 삭제할 때 "나중에 복원할 수도 있으니"라고 생각했다가 자동 백업이 같이 날아가서 낭패를 보는 경우가 있다. 삭제 전에 수동 스냅샷을 찍어두는 습관이 필요한 이유다.

### 수동 스냅샷

언제든지 콘솔이나 CLI로 찍는 전체 스냅샷이다. 보존 기간 제한이 없다. 인스턴스를 삭제해도 수동 스냅샷은 남는다.

수동 스냅샷은 전체 스토리지를 S3에 저장하는 구조다. 첫 스냅샷은 전체 데이터를 복사하고, 이후 스냅샷은 변경된 블록만 저장하는 증분 방식으로 동작한다. 따라서 첫 스냅샷은 시간이 오래 걸리고, 이후 스냅샷은 빠르다.

| 항목 | 자동 백업 | 수동 스냅샷 |
|---|---|---|
| 보존 기간 | 1~35일 | 무기한 |
| 인스턴스 삭제 시 | 같이 삭제 | 유지 |
| PITR 지원 | 가능 | 불가 (스냅샷 시점으로만 복원) |
| 생성 방법 | 자동 (백업 창) | 수동 또는 CLI/API |
| 트랜잭션 로그 포함 | 포함 | 미포함 |

스냅샷 스토리지 요금은 별도로 발생한다. 같은 리전의 프로비저닝된 스토리지 크기까지는 무료고, 초과분은 유료다. Multi-AZ 구성이면 Standby 스냅샷이 Primary 대신 찍혀서 Primary 성능 영향이 줄어든다.

## PITR 동작 원리와 복원 시간 예측

PITR은 자동 백업(일별 스냅샷 + 트랜잭션 로그)을 조합해서 특정 시점의 DB 상태로 복원하는 기능이다. "보존 기간 내 임의의 초 단위까지 복원 가능"이라고 AWS 문서에 나오지만, 실제로는 복원 가능한 최초 시점이 보존 기간 시작점이 아닌 경우가 있다. `DescribeDBInstances` API 응답의 `RestoreWindow.EarliestRestorableTime` 값을 직접 확인해야 한다.

### 복원 내부 동작

복원 요청이 들어오면 RDS가 다음 순서로 진행한다.

1. 목표 시점 직전에 생성된 스냅샷을 찾아서 새 인스턴스로 복원
2. 해당 스냅샷 이후부터 목표 시점까지의 트랜잭션 로그를 순서대로 적용

목표 시점이 스냅샷 생성 시점과 가까울수록 로그 재생 시간이 짧아진다. 반대로 스냅샷 생성 직후부터 목표 시점이 23시간 후라면, 그 23시간 치 트랜잭션 로그를 전부 재생해야 한다.

### 복원 시간 예측

DB 크기와 트랜잭션 볼륨에 따라 편차가 크다.

```
복원 소요 시간 ≈ 스냅샷 복원 시간 + 트랜잭션 로그 재생 시간

스냅샷 복원 시간 = 스냅샷 크기 / 스토리지 복원 처리량
트랜잭션 로그 재생 시간 = (목표 시점 - 스냅샷 생성 시점) 동안의 트랜잭션 볼륨
```

실제 경험상 300GB DB에서 최근 스냅샷 기준 PITR 복원은 30~60분 정도 걸린다. 스냅샷 생성 후 12시간 치 로그를 재생해야 하는 상황이면 추가로 1~2시간이 더 붙는다. 대용량 배치 작업이 집중된 시간대라면 로그 재생 시간이 배로 늘어난다.

PITR 복원은 기존 인스턴스를 덮어쓰지 않는다. 항상 새 인스턴스로 복원된다. 따라서 복원 후 애플리케이션 연결 변경이 필요하고, 이 시간까지 RTO에 포함해야 한다.

```bash
# PITR 복원 명령 예시
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier prod-db \
  --target-db-instance-identifier prod-db-restored \
  --restore-time 2026-07-23T14:30:00Z \
  --db-instance-class db.r6g.xlarge \
  --availability-zone ap-northeast-2a

# 복원 가능한 최초 시점 확인
aws rds describe-db-instances \
  --db-instance-identifier prod-db \
  --query 'DBInstances[0].RestoreWindow'
```

복원된 인스턴스는 파라미터 그룹, 보안 그룹, 서브넷 그룹이 기본값으로 설정된다. 복원 후 원본과 동일하게 맞춰줘야 한다. Multi-AZ도 기본적으로 꺼진 상태로 복원된다.

## 리전 간 DR 구성 (스냅샷 복사)

단일 리전 내 백업은 리전 전체가 장애 날 때 쓸모가 없다. 실제로 단일 리전 장애 가능성은 낮지만, 금융이나 공공 분야에서는 멀티 리전 DR을 요구하는 경우가 있다. 스냅샷 복사가 가장 직접적인 방법이다.

### 수동 스냅샷 복사

```bash
# ap-northeast-2에서 us-east-1로 스냅샷 복사
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:ap-northeast-2:123456789:snapshot:prod-db-2026-07-24 \
  --target-db-snapshot-identifier prod-db-2026-07-24-dr \
  --region us-east-1
```

스냅샷 복사는 전체 데이터를 리전 간 전송하기 때문에 시간이 걸린다. 100GB 스냅샷을 복사하면 네트워크 대역폭에 따라 30분~1시간 이상 걸린다. 복사 중에는 `DescribeDBSnapshots`로 진행 상태를 확인한다.

### 자동화 방법

DR 용도로 쓰려면 수동 복사보다 자동화가 필요하다. 두 가지 방법이 있다.

**RDS 자동 백업 복제(Automated Backup Replication)**

콘솔에서 "Automated backups" 탭에서 "Replicate automatic backups"를 켜면 자동 백업이 지정한 대상 리전으로 자동 복제된다. 수동으로 스냅샷을 복사하는 작업이 필요 없다. 대신 원본 리전과 대상 리전 모두에서 스토리지 비용이 발생한다.

```bash
# 자동 백업 복제 활성화
aws rds enable-cross-region-automated-backups \
  --db-instance-identifier prod-db \
  --replication-source-identifier arn:aws:rds:ap-northeast-2:123456789:db:prod-db \
  --region us-east-1
```

**Lambda + EventBridge로 주기적 복사**

스냅샷 생성 이벤트를 EventBridge로 받아서 Lambda로 복사를 트리거하는 방법이다. 복사 완료 알림, 오래된 DR 스냅샷 정리 같은 추가 로직을 붙일 수 있다.

```python
import boto3

def lambda_handler(event, context):
    source_snapshot_arn = event['detail']['SourceArn']
    
    rds = boto3.client('rds', region_name='us-east-1')
    response = rds.copy_db_snapshot(
        SourceDBSnapshotIdentifier=source_snapshot_arn,
        TargetDBSnapshotIdentifier=f"dr-{event['detail']['SnapshotId']}",
        SourceRegion='ap-northeast-2',
        CopyTags=True
    )
    return response['DBSnapshot']['DBSnapshotIdentifier']
```

DR 리전에서 복원 테스트를 실제로 해봐야 한다. 스냅샷이 정상 복사되었더라도 복원 자체를 테스트하지 않으면 실제 장애 시 예상치 못한 문제가 생길 수 있다. 분기에 한 번이라도 DR 복원 절차를 실행해보는 게 좋다.

## 스냅샷 공유와 암호화된 스냅샷 공유 주의사항

### 일반 스냅샷 공유

암호화되지 않은 스냅샷은 다른 AWS 계정과 공유하거나 퍼블릭으로 공개할 수 있다.

```bash
# 특정 계정에 스냅샷 공유
aws rds modify-db-snapshot-attribute \
  --db-snapshot-identifier prod-db-snapshot \
  --attribute-name restore \
  --values-to-add 987654321098  # 공유할 대상 계정 ID

# 퍼블릭 공개 (주의: 모든 계정에서 접근 가능)
aws rds modify-db-snapshot-attribute \
  --db-snapshot-identifier prod-db-snapshot \
  --attribute-name restore \
  --values-to-add all
```

퍼블릭 공개는 거의 쓸 일이 없다. 실수로 퍼블릭으로 설정했다가 내부 데이터가 노출되는 사고가 가끔 발생하는데, AWS Config 규칙 `rds-snapshots-public-prohibited`로 퍼블릭 스냅샷을 자동 감지하도록 설정해두는 게 안전하다.

### 암호화된 스냅샷 공유

암호화된 스냅샷을 다른 계정과 공유할 때 제약이 있다. 기본 키(AWS managed key, `aws/rds`)로 암호화된 스냅샷은 다른 계정과 직접 공유할 수 없다. CMK(Customer Managed Key)로 암호화한 스냅샷만 공유가 가능하다.

공유 절차가 두 단계다.

**1단계: KMS 키 정책에 대상 계정 추가**

```json
{
  "Sid": "Allow use of the key by another account",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::987654321098:root"
  },
  "Action": [
    "kms:Decrypt",
    "kms:CreateGrant",
    "kms:DescribeKey"
  ],
  "Resource": "*"
}
```

**2단계: 스냅샷 공유**

```bash
aws rds modify-db-snapshot-attribute \
  --db-snapshot-identifier encrypted-snapshot \
  --attribute-name restore \
  --values-to-add 987654321098
```

대상 계정에서 이 스냅샷을 복원할 때 주의할 점이 있다. 대상 계정에서 스냅샷을 복원하면, 복원된 인스턴스는 원본 계정의 CMK로 암호화된 상태다. 이 상태에서 스냅샷을 다시 찍으면 원본 계정 CMK를 계속 참조한다. 대상 계정 소유 CMK로 재암호화하려면 스냅샷을 복사하면서 `--kms-key-id`로 대상 계정의 키를 지정해야 한다.

```bash
# 대상 계정에서 실행: 원본 공유 스냅샷을 자체 키로 재암호화
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:ap-northeast-2:123456789:snapshot:encrypted-snapshot \
  --target-db-snapshot-identifier my-reencrypted-snapshot \
  --kms-key-id arn:aws:kms:ap-northeast-2:987654321098:key/my-cmk \
  --source-region ap-northeast-2
```

재암호화된 스냅샷으로 복원하면 이후 원본 계정 CMK에 의존하지 않는다. 원본 계정이 CMK를 비활성화하거나 삭제하면 재암호화하지 않은 스냅샷은 복원 자체가 불가능해진다.

## 백업 창 설정이 성능에 미치는 영향

### 백업 창이란

자동 백업이 수행되는 시간대다. 기본값은 AWS가 리전별로 자동 지정하며, 원하는 시간으로 변경할 수 있다.

```bash
# 백업 창을 매일 오전 3시~4시(UTC)로 설정
aws rds modify-db-instance \
  --db-instance-identifier prod-db \
  --backup-window "03:00-04:00" \
  --apply-immediately
```

### 성능 영향

스냅샷 생성 자체가 I/O를 유발한다. 특히 Multi-AZ가 꺼진 단일 인스턴스에서는 스냅샷 동안 스토리지 I/O 성능이 저하된다. "briefly suspended"라는 표현이 AWS 문서에 나오는데, 실제로는 수 초에서 길게는 수십 초 I/O가 멈추는 경우가 있다.

Multi-AZ가 켜진 경우, 스냅샷은 Standby(또는 Multi-AZ 클러스터의 Reader)에서 수행된다. Primary의 I/O 영향이 거의 없다. 그래서 운영 환경 RDS는 Multi-AZ를 켜두는 게 백업 영향 측면에서도 유리하다.

스토리지 타입별로 영향이 다르다.

| 스토리지 타입 | 백업 시 I/O 영향 |
|---|---|
| gp2 | I/O 크레딧 소모로 성능 일시 저하 |
| gp3 | gp2보다 안정적, 기저 IOPS 유지 |
| io1/io2 | 프로비저닝된 IOPS 유지, 영향 최소 |

### 백업 창 선택 기준

트래픽이 가장 낮은 시간대를 선택해야 한다. 백업 창과 유지보수 창(maintenance window)이 겹치지 않도록 해야 한다. 두 작업이 겹치면 유지보수가 지연되거나 백업이 늦게 시작된다.

```
백업 창: 03:00-04:00 (UTC)
유지보수 창: 04:30-05:30 (UTC)  # 최소 30분 이상 간격 권장
```

백업 창 시간이 지나도 스냅샷 생성이 완료되지 않으면 계속 진행된다. 즉, "창" 안에 시작해야 하는 거지 창 안에 끝내야 하는 게 아니다. DB가 수백 GB를 넘어가면 백업 창 이후로도 스냅샷이 진행되는 경우가 있다.

### 백업으로 인한 I/O 스파이크 확인

CloudWatch에서 `ReadIOPS`, `WriteIOPS`, `ReadLatency`, `WriteLatency`를 백업 창 전후로 비교해서 실제 영향을 측정해볼 수 있다.

```bash
# 백업 시작/종료 이벤트 확인
aws rds describe-events \
  --db-instance-identifier prod-db \
  --duration 1440 \
  --event-categories backup
```

백업 창 동안 슬로우 쿼리가 급증하거나 응답 시간이 느려진다면, Multi-AZ 활성화나 io1/io2 스토리지로 전환을 검토해야 한다. gp2를 쓰는 단일 인스턴스에서 야간 배치와 백업이 겹칠 때 가장 자주 발생하는 패턴이다.
