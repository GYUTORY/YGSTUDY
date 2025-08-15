---
title: AWS RDS (Relational Database Service)
tags: [aws, database, rds, mysql, postgresql, aurora]
updated: 2024-12-19
---

# AWS RDS (Relational Database Service)

## 배경

AWS RDS(Relational Database Service)는 AWS에서 제공하는 완전 관리형 관계형 데이터베이스 서비스입니다. 서버를 직접 관리하지 않고도 MySQL, PostgreSQL, MariaDB, SQL Server, Oracle, Amazon Aurora 등의 데이터베이스를 손쉽게 운영할 수 있도록 지원합니다. 데이터베이스 관리의 복잡성을 줄이고 개발에 집중할 수 있게 해줍니다.

## 핵심

### RDS의 기본 개념

#### 완전 관리형 데이터베이스
- 서버 유지보수, 백업, 패치, 모니터링 등의 관리 작업을 자동으로 수행
- 관리 부담을 줄여 개발에 집중할 수 있음
- AWS가 인프라 관리를 담당

#### 다양한 데이터베이스 엔진 지원
- **MySQL**: 가장 널리 사용되는 오픈소스 관계형 데이터베이스
- **PostgreSQL**: 고급 기능을 제공하는 오픈소스 데이터베이스
- **MariaDB**: MySQL의 포크로 완전한 호환성 제공
- **Oracle**: 엔터프라이즈급 데이터베이스
- **SQL Server**: Microsoft의 관계형 데이터베이스
- **Amazon Aurora**: AWS에서 개발한 클라우드 네이티브 데이터베이스

### RDS의 주요 특징

| 특징 | 설명 | 장점 |
|------|------|------|
| **완전 관리형** | 서버 관리, 백업, 패치 자동화 | 관리 부담 최소화 |
| **고가용성** | Multi-AZ 배포로 자동 장애 복구 | 서비스 중단 최소화 |
| **자동 백업** | 자동 백업 및 스냅샷 생성 | 데이터 보호 |
| **보안** | VPC, IAM, KMS 암호화 지원 | 강력한 보안 |
| **확장성** | 수직/수평 확장 지원 | 성능 요구사항 대응 |

### RDS 구성 요소

#### DB 인스턴스
- RDS에서 실행되는 개별 데이터베이스 서버
- CPU, 메모리, 스토리지 등 리소스 할당
- 인스턴스 클래스에 따른 성능 결정

#### 스토리지
- RDS 인스턴스에 연결된 영구적인 저장 공간
- 자동 확장 가능한 스토리지 지원
- IOPS 설정으로 성능 조정

#### 백업 및 스냅샷
- 자동 백업: 설정된 보관 기간 동안 자동 백업
- 수동 스냅샷: 사용자가 직접 생성하는 백업
- 크로스 리전 복사 지원

#### Multi-AZ 배포
- 고가용성을 위한 이중화 구성
- 자동 장애 복구 지원
- 읽기 전용 복제본 지원

## 예시

### 기본 RDS 인스턴스 생성

```python
import boto3

# AWS RDS 클라이언트 생성
rds = boto3.client('rds', region_name='ap-northeast-2')

# MySQL RDS 인스턴스 생성
response = rds.create_db_instance(
    DBInstanceIdentifier='my-mysql-db',
    DBInstanceClass='db.t3.micro',
    Engine='mysql',
    EngineVersion='8.0.28',
    MasterUsername='admin',
    MasterUserPassword='MySecurePassword123!',
    AllocatedStorage=20,
    StorageType='gp2',
    MultiAZ=False,
    PubliclyAccessible=False,
    VpcSecurityGroupIds=['sg-12345678'],
    DBSubnetGroupName='default',
    BackupRetentionPeriod=7,
    PreferredBackupWindow='03:00-04:00',
    PreferredMaintenanceWindow='sun:04:00-sun:05:00',
    AutoMinorVersionUpgrade=True,
    DeletionProtection=False
)

print(f"RDS 인스턴스 생성 중: {response['DBInstance']['DBInstanceIdentifier']}")
```

### PostgreSQL 인스턴스 생성

```python
# PostgreSQL RDS 인스턴스 생성
response = rds.create_db_instance(
    DBInstanceIdentifier='my-postgres-db',
    DBInstanceClass='db.t3.micro',
    Engine='postgres',
    EngineVersion='13.7',
    MasterUsername='admin',
    MasterUserPassword='MySecurePassword123!',
    AllocatedStorage=20,
    StorageType='gp2',
    MultiAZ=True,  # 고가용성을 위해 Multi-AZ 활성화
    PubliclyAccessible=False,
    VpcSecurityGroupIds=['sg-12345678'],
    DBSubnetGroupName='default',
    BackupRetentionPeriod=7,
    PreferredBackupWindow='03:00-04:00',
    PreferredMaintenanceWindow='sun:04:00-sun:05:00',
    AutoMinorVersionUpgrade=True,
    DeletionProtection=True  # 실수로 삭제되는 것을 방지
)

print(f"PostgreSQL 인스턴스 생성 중: {response['DBInstance']['DBInstanceIdentifier']}")
```

### 읽기 전용 복제본 생성

```python
# 읽기 전용 복제본 생성
response = rds.create_db_instance_read_replica(
    DBInstanceIdentifier='my-mysql-db-replica',
    SourceDBInstanceIdentifier='my-mysql-db',
    DBInstanceClass='db.t3.micro',
    AvailabilityZone='ap-northeast-2a',
    PubliclyAccessible=False,
    VpcSecurityGroupIds=['sg-12345678']
)

print(f"읽기 전용 복제본 생성 중: {response['DBInstance']['DBInstanceIdentifier']}")
```

### RDS 인스턴스 관리

```python
class RDSManager:
    def __init__(self, region='ap-northeast-2'):
        self.rds_client = boto3.client('rds', region_name=region)
    
    def list_instances(self):
        """RDS 인스턴스 목록 조회"""
        try:
            response = self.rds_client.describe_db_instances()
            instances = []
            for instance in response['DBInstances']:
                instances.append({
                    'identifier': instance['DBInstanceIdentifier'],
                    'engine': instance['Engine'],
                    'status': instance['DBInstanceStatus'],
                    'endpoint': instance.get('Endpoint', {}).get('Address', 'N/A'),
                    'port': instance.get('Endpoint', {}).get('Port', 'N/A')
                })
            return instances
        except Exception as e:
            print(f"인스턴스 목록 조회 실패: {e}")
            return []
    
    def get_instance_status(self, instance_id):
        """특정 인스턴스 상태 조회"""
        try:
            response = self.rds_client.describe_db_instances(
                DBInstanceIdentifier=instance_id
            )
            return response['DBInstances'][0]['DBInstanceStatus']
        except Exception as e:
            print(f"인스턴스 상태 조회 실패: {e}")
            return None
    
    def modify_instance(self, instance_id, new_class=None, new_storage=None):
        """인스턴스 수정"""
        try:
            params = {'DBInstanceIdentifier': instance_id}
            if new_class:
                params['DBInstanceClass'] = new_class
            if new_storage:
                params['AllocatedStorage'] = new_storage
                params['ApplyImmediately'] = True
            
            response = self.rds_client.modify_db_instance(**params)
            return response['DBInstance']['DBInstanceIdentifier']
        except Exception as e:
            print(f"인스턴스 수정 실패: {e}")
            return None
    
    def create_snapshot(self, instance_id, snapshot_id):
        """스냅샷 생성"""
        try:
            response = self.rds_client.create_db_snapshot(
                DBSnapshotIdentifier=snapshot_id,
                DBInstanceIdentifier=instance_id
            )
            return response['DBSnapshot']['DBSnapshotIdentifier']
        except Exception as e:
            print(f"스냅샷 생성 실패: {e}")
            return None

# 사용 예시
rds_manager = RDSManager()

# 인스턴스 목록 조회
instances = rds_manager.list_instances()
for instance in instances:
    print(f"인스턴스: {instance['identifier']}, 상태: {instance['status']}")

# 인스턴스 수정
rds_manager.modify_instance('my-mysql-db', new_class='db.t3.small')

# 스냅샷 생성
rds_manager.create_snapshot('my-mysql-db', 'my-mysql-snapshot-2024-12-19')
```

### CloudFormation 템플릿

```yaml
# rds-instance.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'RDS MySQL Instance'

Parameters:
  DBInstanceClass:
    Type: String
    Default: db.t3.micro
    Description: RDS instance class
  
  DBName:
    Type: String
    Default: mydatabase
    Description: Database name
  
  DBUsername:
    Type: String
    Default: admin
    Description: Database admin username
  
  DBPassword:
    Type: String
    NoEcho: true
    Description: Database admin password

Resources:
  DBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for RDS instance
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 3306
          ToPort: 3306
          SourceSecurityGroupId: !Ref WebServerSecurityGroup

  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Subnet group for RDS instance
      SubnetIds:
        - subnet-12345678
        - subnet-87654321

  DBInstance:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: my-mysql-instance
      DBInstanceClass: !Ref DBInstanceClass
      Engine: mysql
      EngineVersion: '8.0.28'
      MasterUsername: !Ref DBUsername
      MasterUserPassword: !Ref DBPassword
      AllocatedStorage: 20
      StorageType: gp2
      DBName: !Ref DBName
      VPCSecurityGroups:
        - !Ref DBSecurityGroup
      DBSubnetGroupName: !Ref DBSubnetGroup
      BackupRetentionPeriod: 7
      PreferredBackupWindow: '03:00-04:00'
      PreferredMaintenanceWindow: 'sun:04:00-sun:05:00'
      MultiAZ: false
      PubliclyAccessible: false
      DeletionProtection: false

Outputs:
  DBEndpoint:
    Description: Database endpoint
    Value: !GetAtt DBInstance.Endpoint.Address
  
  DBPort:
    Description: Database port
    Value: !GetAtt DBInstance.Endpoint.Port
```

## 운영 팁

### 1. 인스턴스 클래스 선택

#### 개발/테스트 환경
```bash
# 개발용 인스턴스 클래스
db.t3.micro    # 2 vCPU, 1GB RAM
db.t3.small    # 2 vCPU, 2GB RAM
db.t3.medium   # 2 vCPU, 4GB RAM
```

#### 프로덕션 환경
```bash
# 프로덕션용 인스턴스 클래스
db.r5.large    # 2 vCPU, 16GB RAM (메모리 최적화)
db.m5.large    # 2 vCPU, 8GB RAM (범용)
db.c5.large    # 2 vCPU, 4GB RAM (컴퓨팅 최적화)
```

### 2. 백업 및 복구 전략

#### 자동 백업 설정
```python
# 자동 백업 설정
response = rds.modify_db_instance(
    DBInstanceIdentifier='my-mysql-db',
    BackupRetentionPeriod=30,  # 30일간 백업 보관
    PreferredBackupWindow='02:00-03:00',  # 백업 시간
    PreferredMaintenanceWindow='sun:03:00-sun:04:00'  # 유지보수 시간
)
```

#### 스냅샷 관리
```python
# 스냅샷 생성 및 복원
def create_and_restore_snapshot():
    # 스냅샷 생성
    rds.create_db_snapshot(
        DBSnapshotIdentifier='my-snapshot-2024-12-19',
        DBInstanceIdentifier='my-mysql-db'
    )
    
    # 스냅샷에서 복원
    rds.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier='my-mysql-db-restored',
        DBSnapshotIdentifier='my-snapshot-2024-12-19',
        DBInstanceClass='db.t3.micro'
    )
```

### 3. 성능 최적화

#### 읽기 전용 복제본 활용
```python
# 읽기 전용 복제본 생성
response = rds.create_db_instance_read_replica(
    DBInstanceIdentifier='my-mysql-read-replica',
    SourceDBInstanceIdentifier='my-mysql-db',
    DBInstanceClass='db.t3.micro',
    AvailabilityZone='ap-northeast-2b'
)
```

#### 파라미터 그룹 설정
```python
# 커스텀 파라미터 그룹 생성
response = rds.create_db_parameter_group(
    DBParameterGroupName='my-custom-params',
    DBParameterGroupFamily='mysql8.0',
    Description='Custom parameter group for MySQL 8.0'
)

# 파라미터 수정
rds.modify_db_parameter_group(
    DBParameterGroupName='my-custom-params',
    Parameters=[
        {
            'ParameterName': 'max_connections',
            'ParameterValue': '200',
            'ApplyMethod': 'immediate'
        },
        {
            'ParameterName': 'innodb_buffer_pool_size',
            'ParameterValue': '{DBInstanceClassMemory*3/4}',
            'ApplyMethod': 'pending-reboot'
        }
    ]
)
```

### 4. 보안 설정

#### 암호화 설정
```python
# 암호화된 RDS 인스턴스 생성
response = rds.create_db_instance(
    DBInstanceIdentifier='my-encrypted-db',
    DBInstanceClass='db.t3.micro',
    Engine='mysql',
    MasterUsername='admin',
    MasterUserPassword='MySecurePassword123!',
    AllocatedStorage=20,
    StorageEncrypted=True,  # 스토리지 암호화
    KmsKeyId='arn:aws:kms:ap-northeast-2:123456789012:key/abcd1234-5678-90ef-ghij-klmnopqrstuv'
)
```

#### VPC 보안 그룹 설정
```python
import boto3

ec2 = boto3.client('ec2')

# RDS용 보안 그룹 생성
response = ec2.create_security_group(
    GroupName='rds-security-group',
    Description='Security group for RDS instance'
)

security_group_id = response['GroupId']

# 인바운드 규칙 추가 (특정 IP에서만 접근)
ec2.authorize_security_group_ingress(
    GroupId=security_group_id,
    IpPermissions=[
        {
            'IpProtocol': 'tcp',
            'FromPort': 3306,
            'ToPort': 3306,
            'IpRanges': [
                {
                    'CidrIp': '10.0.0.0/16',  # VPC 내부에서만 접근
                    'Description': 'VPC internal access'
                }
            ]
        }
    ]
)
```

### 5. 모니터링 및 알림

#### CloudWatch 메트릭 모니터링
```python
import boto3
from datetime import datetime, timedelta

cloudwatch = boto3.client('cloudwatch')

def get_rds_metrics(instance_id):
    """RDS 인스턴스 메트릭 조회"""
    
    # CPU 사용률
    cpu_response = cloudwatch.get_metric_statistics(
        Namespace='AWS/RDS',
        MetricName='CPUUtilization',
        Dimensions=[
            {
                'Name': 'DBInstanceIdentifier',
                'Value': instance_id
            }
        ],
        StartTime=datetime.utcnow() - timedelta(hours=1),
        EndTime=datetime.utcnow(),
        Period=300,
        Statistics=['Average']
    )
    
    # 연결 수
    connections_response = cloudwatch.get_metric_statistics(
        Namespace='AWS/RDS',
        MetricName='DatabaseConnections',
        Dimensions=[
            {
                'Name': 'DBInstanceIdentifier',
                'Value': instance_id
            }
        ],
        StartTime=datetime.utcnow() - timedelta(hours=1),
        EndTime=datetime.utcnow(),
        Period=300,
        Statistics=['Average']
    )
    
    return {
        'cpu_utilization': cpu_response['Datapoints'],
        'database_connections': connections_response['Datapoints']
    }

# 메트릭 조회
metrics = get_rds_metrics('my-mysql-db')
print(f"CPU 사용률: {metrics['cpu_utilization']}")
print(f"데이터베이스 연결 수: {metrics['database_connections']}")
```

## 참고

### RDS vs 다른 데이터베이스 서비스 비교

| 기능 | RDS | Aurora | DynamoDB | DocumentDB |
|------|-----|--------|----------|------------|
| **데이터 모델** | 관계형 | 관계형 | NoSQL | 문서형 |
| **확장성** | 수직 확장 | 자동 확장 | 무제한 | 자동 확장 |
| **성능** | 좋음 | 매우 좋음 | 매우 좋음 | 좋음 |
| **비용** | 중간 | 높음 | 낮음 | 중간 |
| **관리 복잡성** | 낮음 | 낮음 | 매우 낮음 | 낮음 |

### RDS 엔진별 특징

| 엔진 | 장점 | 단점 | 적합한 용도 |
|------|------|------|-------------|
| **MySQL** | 널리 사용됨, 커뮤니티 활발 | 확장성 제한 | 웹 애플리케이션 |
| **PostgreSQL** | 고급 기능, 확장성 | 복잡성 | 복잡한 데이터 모델 |
| **Aurora** | 자동 확장, 고성능 | 비용 | 대용량 트래픽 |
| **SQL Server** | Windows 생태계 | 라이선스 비용 | 엔터프라이즈 |
| **Oracle** | 엔터프라이즈 기능 | 높은 비용 | 대기업 |

### 관련 링크

- [AWS RDS 공식 문서](https://docs.aws.amazon.com/rds/)
- [AWS RDS 가격](https://aws.amazon.com/rds/pricing/)
- [RDS Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [AWS Well-Architected Framework - 데이터베이스](https://aws.amazon.com/architecture/well-architected/)
