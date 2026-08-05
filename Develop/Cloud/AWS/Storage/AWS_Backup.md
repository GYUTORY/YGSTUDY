---
title: AWS Backup
tags: [aws, backup, disaster-recovery, rds, ebs, efs, dynamodb, restore]
updated: 2026-01-18
---

# AWS Backup

## 개요

AWS Backup은 중앙 집중식 백업 서비스다. 여러 AWS 서비스의 백업을 한 곳에서 관리한다. 백업 정책을 자동화한다. 복구를 간편하게 한다. 규정 준수 리포트를 제공한다.

### 지원 서비스

**컴퓨팅:**
- EC2
- EBS

**스토리지:**
- EFS
- FSx (Windows File Server, Lustre, NetApp ONTAP, OpenZFS)
- S3

**데이터베이스:**
- RDS (모든 엔진)
- Aurora
- DynamoDB
- DocumentDB
- Neptune

**기타:**
- ECS (AWS Backup for Amazon ECS)
- Storage Gateway
- VMware on AWS

### 왜 필요한가

각 서비스마다 백업 방법이 다르다.

**문제 상황:**

**개별 백업 관리:**
- EBS: 스냅샷 생성 스크립트
- RDS: 자동 백업 설정
- DynamoDB: On-Demand 백업
- EFS: AWS Backup 또는 스크립트

각각 다른 방식으로 관리한다. 복잡하다.

**백업 정책:**
- 일일 백업
- 7일 보관
- 월간 백업
- 1년 보관

각 서비스마다 설정해야 한다. 누락하기 쉽다.

**복구:**
- EBS: 스냅샷 → 볼륨 생성 → 연결
- RDS: Point-in-Time 복구
- DynamoDB: 테이블 복원

서비스마다 복구 방법이 다르다. 재해 시 혼란스럽다.

**AWS Backup의 해결:**
- 하나의 콘솔에서 모든 백업 관리
- 통합 백업 정책
- 중앙 집중식 복구
- 규정 준수 리포트

## 핵심 개념

### Backup Plan (백업 계획)

백업 일정과 보존 기간을 정의한다.

**구성 요소:**
- **Backup Rule**: 백업 시간, 빈도
- **Lifecycle**: 스토리지 클래스 전환
- **Retention**: 보관 기간

**예시:**
- 매일 오전 2시 백업
- 7일 보관
- 7일 후 Cold Storage로 이동
- 90일 후 삭제

### Backup Vault (백업 저장소)

백업을 저장하는 컨테이너다. 암호화와 접근 제어를 설정한다.

**기본 Vault:**
자동으로 생성된다. 커스텀 Vault를 만들 수도 있다.

**Vault Lock:**
백업을 수정/삭제하지 못하도록 잠근다. 규정 준수에 필요하다.

### Resource Assignment (리소스 할당)

어떤 리소스를 백업할지 지정한다.

**방법:**
- **태그 기반**: 특정 태그를 가진 리소스 자동 백업
- **리소스 ID**: 개별 리소스 지정
- **리소스 타입**: 모든 EBS 볼륨, 모든 RDS 인스턴스 등

## 백업 계획 생성

### 콘솔에서 생성

**단계:**
1. AWS Backup 콘솔
2. "Backup plans" → "Create Backup plan"
3. "Build a new plan" 선택
4. 이름 입력: daily-backup
5. Backup rule 추가
   - Rule name: Daily
   - Schedule: Daily at 2:00 AM
   - Backup window: 1 hour
   - Retention: 7 days
   - Lifecycle: Move to Cold Storage after 7 days
   - Delete after 90 days
6. 생성

**리소스 할당:**
1. "Assign resources" 클릭
2. Resource assignment name: production-resources
3. IAM role: Default role
4. Resource selection: Tags
   - Key: Environment
   - Value: Production
5. 할당

이제 `Environment=Production` 태그를 가진 모든 리소스가 자동으로 백업된다.

### CLI로 생성

**Backup Plan:**
```bash
aws backup create-backup-plan \
  --backup-plan file://backup-plan.json
```

**backup-plan.json:**
```json
{
  "BackupPlanName": "DailyBackup",
  "Rules": [
    {
      "RuleName": "Daily",
      "TargetBackupVaultName": "Default",
      "ScheduleExpression": "cron(0 2 * * ? *)",
      "StartWindowMinutes": 60,
      "CompletionWindowMinutes": 120,
      "Lifecycle": {
        "MoveToColdStorageAfterDays": 7,
        "DeleteAfterDays": 90
      }
    }
  ]
}
```

**리소스 할당:**
```bash
aws backup create-backup-selection \
  --backup-plan-id <plan-id> \
  --backup-selection file://selection.json
```

**selection.json:**
```json
{
  "SelectionName": "ProductionResources",
  "IamRoleArn": "arn:aws:iam::123456789012:role/AWSBackupDefaultServiceRole",
  "Resources": ["*"],
  "ListOfTags": [
    {
      "ConditionType": "STRINGEQUALS",
      "ConditionKey": "Environment",
      "ConditionValue": "Production"
    }
  ]
}
```

## 백업 실행

### 자동 백업

Backup Plan의 스케줄에 따라 자동으로 실행된다.

**확인:**
AWS Backup 콘솔 → "Jobs" → "Backup jobs"

실행 중인 백업과 완료된 백업을 확인한다.

### 수동 백업

즉시 백업을 만든다.

**콘솔:**
1. "Protected resources"
2. 리소스 선택
3. "Create on-demand backup" 클릭
4. Backup vault 선택
5. IAM role 선택
6. 생성

**CLI:**
```bash
aws backup start-backup-job \
  --backup-vault-name Default \
  --resource-arn arn:aws:rds:us-west-2:123456789012:db:mydb \
  --iam-role-arn arn:aws:iam::123456789012:role/AWSBackupDefaultServiceRole
```

즉시 백업이 시작된다.

## 복구

### EC2/EBS 복구

**백업 선택:**
1. "Backup vaults" → Vault 선택
2. Recovery point 선택
3. "Restore" 클릭

**EBS 복구:**
- 새 볼륨 생성
- 가용 영역 선택
- 암호화 설정
- 복구

**EC2 복구:**
- 새 인스턴스 생성
- 인스턴스 타입 선택
- VPC, 서브넷 선택
- 복구

**CLI:**
```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-west-2:123456789012:recovery-point:... \
  --metadata \
    VolumeType=gp3,\
    AvailabilityZone=us-west-2a,\
    Encrypted=true \
  --iam-role-arn arn:aws:iam::123456789012:role/AWSBackupDefaultServiceRole
```

### RDS 복구

**Point-in-Time Restore:**
특정 시점으로 복구한다.

**콘솔:**
1. Recovery point 선택
2. "Restore" 클릭
3. DB instance identifier 입력
4. 시점 선택 (특정 시간)
5. VPC, 서브넷 선택
6. 복구

**CLI:**
```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-west-2:123456789012:recovery-point:... \
  --metadata \
    DBInstanceIdentifier=restored-db,\
    DBInstanceClass=db.t3.medium,\
    VpcId=vpc-12345678 \
  --iam-role-arn arn:aws:iam::123456789012:role/AWSBackupDefaultServiceRole
```

새 RDS 인스턴스가 생성된다.

### DynamoDB 복구

**테이블 복원:**
```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-west-2:123456789012:recovery-point:... \
  --metadata \
    targetTableName=restored-table \
  --iam-role-arn arn:aws:iam::123456789012:role/AWSBackupDefaultServiceRole
```

새 테이블이 생성된다.

### Cross-Region 복구

다른 리전으로 백업을 복사하고 복구한다.

**Copy Rule 추가:**
```json
{
  "Rules": [
    {
      "RuleName": "Daily",
      "CopyActions": [
        {
          "DestinationBackupVaultArn": "arn:aws:backup:us-east-1:123456789012:backup-vault:Default",
          "Lifecycle": {
            "DeleteAfterDays": 90
          }
        }
      ]
    }
  ]
}
```

백업이 자동으로 us-east-1로 복사된다.

**재해 복구:**
- 주 리전 (us-west-2) 장애
- us-east-1에서 백업 복구
- 서비스 재개

## 백업 정책 예시

### 3-2-1 백업 전략

**규칙:**
- 3개 복사본
- 2개 다른 미디어
- 1개 오프사이트

**AWS Backup 구현:**

**Plan 1: 일일 백업 (로컬)**
```json
{
  "BackupPlanName": "Daily",
  "Rules": [
    {
      "RuleName": "Daily",
      "ScheduleExpression": "cron(0 2 * * ? *)",
      "Lifecycle": {
        "DeleteAfterDays": 7
      }
    }
  ]
}
```

**Plan 2: 주간 백업 (로컬 + Cold Storage)**
```json
{
  "BackupPlanName": "Weekly",
  "Rules": [
    {
      "RuleName": "Weekly",
      "ScheduleExpression": "cron(0 2 ? * 1 *)",
      "Lifecycle": {
        "MoveToColdStorageAfterDays": 7,
        "DeleteAfterDays": 90
      }
    }
  ]
}
```

**Plan 3: 월간 백업 (Cross-Region)**
```json
{
  "BackupPlanName": "Monthly",
  "Rules": [
    {
      "RuleName": "Monthly",
      "ScheduleExpression": "cron(0 2 1 * ? *)",
      "CopyActions": [
        {
          "DestinationBackupVaultArn": "arn:aws:backup:us-east-1:123456789012:backup-vault:Default",
          "Lifecycle": {
            "DeleteAfterDays": 365
          }
        }
      ]
    }
  ]
}
```

**결과:**
- 일일: 7일 보관 (빠른 복구)
- 주간: 90일 보관 (Cold Storage, 비용 절감)
- 월간: 1년 보관 (다른 리전, 재해 복구)

### 규정 준수 (금융)

**요구사항:**
- 일일 백업
- 7년 보관
- 변경/삭제 불가

**Backup Vault with Lock:**
```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name ComplianceVault \
  --min-retention-days 2555 \
  --max-retention-days 2555
```

2555일 (7년) 동안 백업을 삭제할 수 없다.

**Backup Plan:**
```json
{
  "BackupPlanName": "Compliance",
  "Rules": [
    {
      "RuleName": "Daily",
      "TargetBackupVaultName": "ComplianceVault",
      "ScheduleExpression": "cron(0 2 * * ? *)",
      "Lifecycle": {
        "MoveToColdStorageAfterDays": 30,
        "DeleteAfterDays": 2555
      }
    }
  ]
}
```

## 모니터링

### Backup Jobs

**상태:**
- **Running**: 진행 중
- **Completed**: 완료
- **Failed**: 실패
- **Aborted**: 중단

**실패 알림:**
SNS로 알림을 보낸다.

**EventBridge 규칙:**
```bash
aws events put-rule \
  --name backup-failure \
  --event-pattern file://pattern.json \
  --state ENABLED
```

**pattern.json:**
```json
{
  "source": ["aws.backup"],
  "detail-type": ["Backup Job State Change"],
  "detail": {
    "state": ["FAILED", "ABORTED"]
  }
}
```

**SNS 연결:**
```bash
aws events put-targets \
  --rule backup-failure \
  --targets Id=1,Arn=arn:aws:sns:us-west-2:123456789012:backup-alerts
```

백업 실패 시 즉시 알림을 받는다.

### CloudWatch 메트릭

**주요 메트릭:**
- **NumberOfBackupJobsCreated**: 생성된 백업 작업 수
- **NumberOfBackupJobsCompleted**: 완료된 백업 작업 수
- **NumberOfBackupJobsFailed**: 실패한 백업 작업 수

**대시보드 생성:**
백업 성공률, 복구 시간 등을 시각화한다.

### 규정 준수 리포트

**AWS Backup Audit Manager:**
백업 정책 준수 여부를 자동으로 확인한다.

**프레임워크:**
- CIS (Center for Internet Security)
- PCI DSS
- HIPAA
- GDPR
- 커스텀 프레임워크

**리포트 생성:**
1. "Audit Manager" 메뉴
2. "Create audit" 클릭
3. 프레임워크 선택 (PCI DSS)
4. 리소스 선택
5. 실행

**리포트 내용:**
- 백업 정책 존재 여부
- 백업 빈도
- 보관 기간
- 암호화 여부
- Cross-Region 복사 여부

규정을 위반하는 리소스를 자동으로 찾는다.

## 비용

### 백업 스토리지

**Warm Storage:**
$0.05/GB-월

**Cold Storage:**
$0.01/GB-월 (90일 이상 보관 시)

**예시 (1 TB):**
- Warm: 1,024 × $0.05 = $51.20/월
- Cold: 1,024 × $0.01 = $10.24/월

**80% 절감**

### 복구 비용

**Warm Storage:**
무료

**Cold Storage:**
$0.02/GB

**예시 (100 GB 복구):**
100 × $0.02 = $2.00

### Cross-Region 복사

**데이터 전송:**
리전 간 데이터 전송 비용 발생 ($0.02/GB).

**스토리지:**
대상 리전의 스토리지 비용.

**예시 (1 TB 복사):**
- 전송: 1,024 × $0.02 = $20.48
- 스토리지 (목적지): $51.20/월

### 최적화

**Lifecycle 정책:**
- 7일: Warm Storage
- 90일: Cold Storage
- 재해 복구용만 Cross-Region

불필요한 백업을 조기 삭제한다.

**태그 기반 백업:**
중요한 리소스만 백업한다. 개발/테스트 환경은 제외한다.

## 실무 사용

### 자동화된 재해 복구

**시나리오:**
주 리전 (us-west-2)이 장애. 백업 리전 (us-east-1)으로 복구.

**사전 준비:**
1. Cross-Region 백업 활성화
2. 복구 절차 문서화
3. 정기 복구 테스트 (분기 1회)

**복구 절차:**
1. AWS Backup 콘솔 (us-east-1)
2. 최신 백업 선택
3. RDS 복구
4. EC2 복구
5. Route 53 DNS 변경
6. 서비스 재개

**자동화:**
Lambda 함수로 복구를 자동화한다. EventBridge에서 장애를 감지하면 자동으로 복구를 시작한다.

### Multi-Account 백업

**AWS Organizations 사용:**
중앙 백업 계정에서 모든 계정의 백업을 관리한다.

**설정:**
1. Backup 계정 생성
2. Organizations 활성화
3. Cross-Account 백업 활성화
4. 멤버 계정의 리소스 백업

**장점:**
- 중앙 집중식 관리
- 권한 분리 (멤버 계정은 백업 삭제 불가)
- 규정 준수 간편

## 참고

- AWS Backup 개발자 가이드: https://docs.aws.amazon.com/aws-backup/
- AWS Backup 요금: https://aws.amazon.com/backup/pricing/
- Backup Audit Manager: https://docs.aws.amazon.com/aws-backup/latest/devguide/aws-backup-audit-manager.html
- 재해 복구 아키텍처: https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/

