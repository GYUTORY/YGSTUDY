---
title: AWS Config
tags: [aws, config, compliance, configuration, audit, governance, security]
updated: 2026-01-22
---

# AWS Config

## 개요

AWS Config는 리소스 구성을 추적하는 서비스다. 모든 변경사항을 기록한다. 규정 준수를 자동으로 확인한다. 보안 모범 사례를 검증한다. 감사 리포트를 생성한다. 변경 이력을 시각화한다.

### 왜 필요한가

AWS 리소스가 많아지면 관리가 어렵다.

**문제 상황 1: 보안 그룹 변경**

**상황:**
누군가 프로덕션 DB의 보안 그룹을 수정했다. 3306 포트가 0.0.0.0/0에 열렸다. 전 세계에서 DB에 접근 가능하다. 심각한 보안 문제다.

**질문:**
- 누가 변경했나?
- 언제 변경했나?
- 이전 설정은 무엇이었나?
- 다른 DB도 같은 문제가 있나?

**일반적인 대응:**
- CloudTrail 로그 확인 (복잡)
- 수동으로 모든 보안 그룹 확인
- 시간이 오래 걸림

**AWS Config의 해결:**
- 자동으로 변경 감지
- 즉시 알림 (SNS)
- 누가, 언제, 무엇을 바꿨는지 명확히 표시
- 이전 설정으로 복원 가능
- 모든 리소스를 자동 검사

**문제 상황 2: 규정 준수**

**요구사항:**
금융 규제로 모든 S3 버킷은 암호화되어야 한다.

**질문:**
- 모든 버킷이 암호화되어 있나?
- 새로 만든 버킷은 자동으로 암호화되나?
- 비준수 버킷이 있으면 즉시 알림받나?

**AWS Config:**
- 자동으로 모든 버킷 검사
- 암호화되지 않은 버킷 탐지
- 비준수 리포트 생성
- 새 버킷도 자동 검사

## 핵심 개념

### Configuration Item (CI)

리소스의 구성 스냅샷이다. 특정 시점의 리소스 상태를 기록한다.

**포함 정보:**
- 리소스 ID
- 리소스 타입
- 구성 (태그, 속성 등)
- 관계 (연결된 다른 리소스)
- 변경 시간
- 변경한 사용자 (CloudTrail 연동)

**예시 (Security Group CI):**
```json
{
  "resourceType": "AWS::EC2::SecurityGroup",
  "resourceId": "sg-12345678",
  "configuration": {
    "groupName": "production-db",
    "ipPermissions": [
      {
        "fromPort": 3306,
        "toPort": 3306,
        "ipProtocol": "tcp",
        "ipRanges": ["10.0.0.0/16"]
      }
    ]
  },
  "configurationItemCaptureTime": "2026-01-18T10:30:00Z",
  "configurationItemStatus": "ResourceDiscovered",
  "relationships": [
    {
      "resourceType": "AWS::RDS::DBInstance",
      "resourceId": "prod-db"
    }
  ]
}
```

### Configuration History

리소스의 변경 이력이다. 타임라인으로 확인한다.

**예시:**
```
2026-01-18 10:00:00 - 보안 그룹 생성
2026-01-18 10:30:00 - 포트 3306 추가 (10.0.0.0/16)
2026-01-18 11:00:00 - 포트 3306 변경 (0.0.0.0/0) ← 문제!
```

### Config Rules

리소스가 규정을 준수하는지 자동으로 확인한다.

**AWS Managed Rules:**
AWS가 미리 만든 규칙. 바로 사용한다.

**예시:**
- `s3-bucket-public-read-prohibited`: S3 버킷이 public read 금지
- `rds-storage-encrypted`: RDS가 암호화되어 있는지
- `ec2-instance-no-public-ip`: EC2에 Public IP 없는지

**Custom Rules:**
Lambda 함수로 직접 만든다.

### Compliance

규정 준수 상태다.

**상태:**
- **Compliant**: 준수
- **Non-Compliant**: 비준수
- **Not Applicable**: 해당 없음
- **Insufficient Data**: 데이터 부족

## 설정

### Config 활성화

**콘솔:**
1. AWS Config 콘솔
2. "Get started" 클릭
3. 기록할 리소스 선택
   - All resources (권장)
   - Specific resource types
4. S3 버킷 선택 (구성 저장)
5. SNS topic 선택 (알림)
6. IAM role 생성 또는 선택
7. 시작

**CLI:**
```bash
# S3 버킷 생성
aws s3 mb s3://my-config-bucket

# Delivery Channel 생성
aws configservice put-delivery-channel \
  --delivery-channel name=default,s3BucketName=my-config-bucket

# Configuration Recorder 생성
aws configservice put-configuration-recorder \
  --configuration-recorder name=default,roleARN=arn:aws:iam::123456789012:role/config-role

# Recording 시작
aws configservice start-configuration-recorder \
  --configuration-recorder-name default
```

**비용:**
매월 활성화한 리소스당 비용 발생.

## Config Rules 설정

### Managed Rule 추가

**S3 암호화 규칙:**
```bash
aws configservice put-config-rule \
  --config-rule \
    '{
      "ConfigRuleName": "s3-bucket-encryption",
      "Source": {
        "Owner": "AWS",
        "SourceIdentifier": "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"
      }
    }'
```

**RDS 암호화 규칙:**
```bash
aws configservice put-config-rule \
  --config-rule \
    '{
      "ConfigRuleName": "rds-storage-encrypted",
      "Source": {
        "Owner": "AWS",
        "SourceIdentifier": "RDS_STORAGE_ENCRYPTED"
      }
    }'
```

**EBS 암호화 규칙:**
```bash
aws configservice put-config-rule \
  --config-rule \
    '{
      "ConfigRuleName": "ec2-ebs-encryption-by-default",
      "Source": {
        "Owner": "AWS",
        "SourceIdentifier": "EC2_EBS_ENCRYPTION_BY_DEFAULT"
      }
    }'
```

### Custom Rule (Lambda)

**요구사항:**
모든 EC2 인스턴스는 특정 태그를 가져야 한다.

**Lambda 함수:**
```python
import boto3
import json

def lambda_handler(event, context):
    config = boto3.client('config')
    
    # 구성 항목 파싱
    config_item = json.loads(event['configurationItem'])
    resource_type = config_item['resourceType']
    resource_id = config_item['resourceId']
    
    # EC2만 검사
    if resource_type != 'AWS::EC2::Instance':
        return {
            'compliance_type': 'NOT_APPLICABLE',
            'annotation': 'Not an EC2 instance'
        }
    
    # 태그 확인
    tags = config_item['configuration'].get('tags', [])
    required_tags = ['Environment', 'Owner', 'Project']
    
    missing_tags = []
    for tag_key in required_tags:
        if not any(t['key'] == tag_key for t in tags):
            missing_tags.append(tag_key)
    
    if missing_tags:
        return {
            'compliance_type': 'NON_COMPLIANT',
            'annotation': f'Missing required tags: {", ".join(missing_tags)}'
        }
    
    return {
        'compliance_type': 'COMPLIANT',
        'annotation': 'All required tags present'
    }
```

**Config Rule 생성:**
```bash
aws configservice put-config-rule \
  --config-rule \
    '{
      "ConfigRuleName": "required-tags",
      "Source": {
        "Owner": "CUSTOM_LAMBDA",
        "SourceIdentifier": "arn:aws:lambda:us-west-2:123456789012:function:check-required-tags",
        "SourceDetails": [
          {
            "EventSource": "aws.config",
            "MessageType": "ConfigurationItemChangeNotification"
          }
        ]
      },
      "Scope": {
        "ComplianceResourceTypes": ["AWS::EC2::Instance"]
      }
    }'
```

## 실무 규칙

### 보안 규칙

**Public 접근 차단:**
```bash
# S3 Public Read 금지
aws configservice put-config-rule --config-rule \
  '{"ConfigRuleName":"s3-bucket-public-read-prohibited","Source":{"Owner":"AWS","SourceIdentifier":"S3_BUCKET_PUBLIC_READ_PROHIBITED"}}'

# S3 Public Write 금지
aws configservice put-config-rule --config-rule \
  '{"ConfigRuleName":"s3-bucket-public-write-prohibited","Source":{"Owner":"AWS","SourceIdentifier":"S3_BUCKET_PUBLIC_WRITE_PROHIBITED"}}'

# EC2 Public IP 금지
aws configservice put-config-rule --config-rule \
  '{"ConfigRuleName":"ec2-instance-no-public-ip","Source":{"Owner":"AWS","SourceIdentifier":"EC2_INSTANCE_NO_PUBLIC_IP"}}'
```

**암호화 규칙:**
```bash
# EBS 암호화
# RDS 암호화
# S3 암호화
# DynamoDB 암호화
```

**보안 그룹 규칙:**
```bash
# SSH 0.0.0.0/0 금지
aws configservice put-config-rule --config-rule \
  '{"ConfigRuleName":"restricted-ssh","Source":{"Owner":"AWS","SourceIdentifier":"INCOMING_SSH_DISABLED"}}'

# RDP 0.0.0.0/0 금지
aws configservice put-config-rule --config-rule \
  '{"ConfigRuleName":"restricted-rdp","Source":{"Owner":"AWS","SourceIdentifier":"RESTRICTED_INCOMING_TRAFFIC"},"InputParameters":"{\"blockedPort1\":\"3389\"}"}'
```

### 비용 최적화 규칙

**미사용 리소스:**
```bash
# Unattached EBS 볼륨
aws configservice put-config-rule --config-rule \
  '{"ConfigRuleName":"ec2-volume-inuse-check","Source":{"Owner":"AWS","SourceIdentifier":"EC2_VOLUME_INUSE_CHECK"}}'

# Elastic IP 미사용
aws configservice put-config-rule --config-rule \
  '{"ConfigRuleName":"eip-attached","Source":{"Owner":"AWS","SourceIdentifier":"EIP_ATTACHED"}}'
```

### 백업 규칙

**RDS 백업:**
```bash
aws configservice put-config-rule --config-rule \
  '{"ConfigRuleName":"db-backup-enabled","Source":{"Owner":"AWS","SourceIdentifier":"DB_BACKUP_ENABLED"},"InputParameters":"{\"backupRetentionPeriod\":\"7\"}"}'
```

7일 이상 백업 보관.

## Remediation (자동 수정)

비준수 리소스를 자동으로 수정한다.

### SSM Automation

**S3 버킷 암호화 활성화:**
```bash
aws configservice put-remediation-configuration \
  --config-rule-name s3-bucket-encryption \
  --remediation-configuration \
    '{
      "TargetType": "SSM_DOCUMENT",
      "TargetIdentifier": "AWS-EnableS3BucketEncryption",
      "TargetVersion": "1",
      "Parameters": {
        "BucketName": {
          "ResourceValue": {
            "Value": "RESOURCE_ID"
          }
        },
        "SSEAlgorithm": {
          "StaticValue": {
            "Values": ["AES256"]
          }
        }
      },
      "Automatic": true,
      "MaximumAutomaticAttempts": 5,
      "RetryAttemptSeconds": 60
    }'
```

**동작:**
1. Config가 암호화되지 않은 버킷 탐지
2. SSM Automation 실행
3. 버킷 암호화 활성화
4. 재검사
5. 준수 상태로 변경

### Lambda Remediation

**보안 그룹 수정:**
비준수 보안 그룹의 위험한 규칙을 삭제한다.

**Lambda 함수:**
```python
import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    
    # Config에서 전달된 보안 그룹 ID
    sg_id = event['configRuleInvokingEvent']['configurationItem']['resourceId']
    
    # 위험한 규칙 삭제 (0.0.0.0/0에서 SSH)
    try:
        ec2.revoke_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
        return {'status': 'SUCCESS'}
    except Exception as e:
        return {'status': 'FAILED', 'error': str(e)}
```

## 변경 추적

### Timeline

리소스의 변경 이력을 타임라인으로 확인한다.

**콘솔:**
1. Config 콘솔 → Resources
2. 리소스 선택 (예: Security Group)
3. "Resource Timeline" 탭

**표시:**
```
2026-01-18 11:00 - 구성 변경 (IpPermissions 수정)
2026-01-18 10:30 - 구성 변경 (IpPermissions 추가)
2026-01-18 10:00 - 리소스 생성
```

각 시점을 클릭하면 상세 구성을 볼 수 있다.

**변경 사항 비교:**
두 시점의 구성을 비교한다. 무엇이 바뀌었는지 명확히 보인다.

### CloudTrail 통합

누가 변경했는지 확인한다.

**Config의 변경 이력:**
- 무엇이 바뀌었나
- 언제 바뀌었나

**CloudTrail:**
- 누가 바꿨나
- 어떤 API를 호출했나

Config가 자동으로 CloudTrail 이벤트를 연결한다.

**예시:**
```
변경 시간: 2026-01-18 11:00:00
변경 내용: IpPermissions 수정 (0.0.0.0/0 추가)
사용자: john@example.com
API: AuthorizeSecurityGroupIngress
소스 IP: 203.0.113.5
```

## 규정 준수 리포트

### Compliance Dashboard

모든 규칙의 준수 상태를 한눈에 확인한다.

**표시:**
- Compliant 리소스 수
- Non-Compliant 리소스 수
- 규칙별 준수율

**필터링:**
- 비준수만 표시
- 특정 규칙만 표시
- 특정 리소스 타입만 표시

### 리포트 다운로드

감사용 리포트를 생성한다.

**Config Aggregator:**
여러 계정과 리전의 데이터를 집계한다.

```bash
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name my-aggregator \
  --account-aggregation-sources \
    '[{
      "AccountIds": ["123456789012", "210987654321"],
      "AllAwsRegions": true
    }]'
```

**리포트:**
- 계정별 준수율
- 리전별 준수율
- 규칙별 비준수 리소스 목록

## 비용

### Configuration Items

**가격:**
$0.003 per configuration item recorded

**예시:**
- 리소스 1,000개
- 매월 평균 3회 변경
- 월 CI: 1,000 × 3 = 3,000
- 비용: 3,000 × $0.003 = $9

### Config Rules

**가격:**
- Active Rules: $2.00 per rule per month (처음 10개)
- 11개 이상: $1.00 per rule per month

**예시:**
- 규칙 20개
- 비용: (10 × $2) + (10 × $1) = $30/월

### 최적화

**리소스 선택:**
모든 리소스를 기록하지 않는다. 중요한 리소스만 선택한다.

**예시:**
- EC2, RDS, S3: 기록
- CloudWatch Logs, Lambda 실행: 제외

**규칙 최적화:**
중복된 규칙을 제거한다.

## 실무 사용

### 보안 감사

**요구사항:**
모든 프로덕션 리소스가 암호화되어 있는지 감사.

**규칙 설정:**
- RDS 암호화
- EBS 암호화
- S3 암호화
- DynamoDB 암호화

**비준수 발견:**
```
Non-Compliant Resources:
- RDS: prod-db-2 (암호화 안 됨)
- S3: legacy-bucket (암호화 안 됨)
```

**조치:**
1. 비준수 리소스 확인
2. 암호화 활성화 또는 마이그레이션
3. 재검사

### 변경 추적

**문제:**
프로덕션 서비스가 다운됐다. 최근 변경사항을 확인한다.

**Config:**
1. 관련 리소스 선택 (ALB, EC2, Security Group)
2. Timeline 확인
3. 최근 1시간 내 변경 찾기

**발견:**
```
2026-01-18 10:45 - Security Group 변경
  변경 전: Port 80 허용
  변경 후: Port 80 삭제
  사용자: admin@example.com
```

보안 그룹에서 포트 80을 삭제했다. 웹 서버 접근 불가.

**복구:**
이전 구성을 확인하고 포트 80을 다시 추가한다.

## 참고

- AWS Config 개발자 가이드: https://docs.aws.amazon.com/config/
- Config 요금: https://aws.amazon.com/config/pricing/
- Managed Rules: https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html
- Remediation: https://docs.aws.amazon.com/config/latest/developerguide/remediation.html

