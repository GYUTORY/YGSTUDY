---
title: AWS CloudFormation IaC 가이드
tags: [aws, cloudformation, iac, infrastructure-as-code, cdk, sam, stack, template]
updated: 2026-03-01
---

# AWS CloudFormation

## 개요

CloudFormation은 AWS 인프라를 **YAML/JSON 템플릿으로 정의하고 자동 배포**하는 IaC(Infrastructure as Code) 서비스이다. 인프라를 코드로 관리하므로 버전 관리, 반복 배포, 롤백이 가능하다.

```
템플릿 (YAML)
    │
    ▼
CloudFormation (서비스)
    │
    ▼
스택 (Stack) = 실제 AWS 리소스 집합
    ├── VPC
    ├── Subnet
    ├── EC2
    ├── RDS
    └── S3
```

### CloudFormation vs Terraform

| 항목 | CloudFormation | Terraform |
|------|---------------|-----------|
| **제공자** | AWS 네이티브 | HashiCorp (멀티 클라우드) |
| **언어** | YAML/JSON | HCL |
| **상태 관리** | AWS가 관리 (자동) | 별도 Backend 필요 (S3 등) |
| **멀티 클라우드** | AWS 전용 | AWS, GCP, Azure 등 |
| **드리프트 탐지** | 내장 | `terraform plan` |
| **비용** | 무료 | 무료 (Enterprise 유료) |
| **CDK 지원** | ✅ (AWS CDK) | ✅ (CDKTF) |
| **적합한 경우** | AWS 전용 환경 | 멀티 클라우드 |

## 핵심

### 1. 템플릿 구조

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: My Application Infrastructure

# 파라미터: 배포 시 입력값
Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]
  InstanceType:
    Type: String
    Default: t3.micro

# 조건: 환경별 분기
Conditions:
  IsProd: !Equals [!Ref Environment, prod]

# 매핑: 환경별 값 테이블
Mappings:
  RegionMap:
    ap-northeast-2:
      AMI: ami-0c6e5afdd23291f73

# 리소스: 실제 AWS 리소스 정의
Resources:
  MyVPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-vpc

# 출력: 스택 생성 후 내보내는 값
Outputs:
  VpcId:
    Value: !Ref MyVPC
    Export:
      Name: !Sub ${Environment}-VpcId
```

#### 주요 섹션

| 섹션 | 용도 | 필수 |
|------|------|------|
| `Parameters` | 배포 시 입력값 | 선택 |
| `Mappings` | 환경별 고정 값 테이블 | 선택 |
| `Conditions` | 조건부 리소스 생성 | 선택 |
| `Resources` | AWS 리소스 정의 | **필수** |
| `Outputs` | 출력값, 스택 간 참조 | 선택 |

### 2. 내장 함수

```yaml
Resources:
  # !Ref: 파라미터나 리소스의 값 참조
  SecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      VpcId: !Ref MyVPC

  # !Sub: 문자열 치환
  Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub ${Environment}-app-bucket-${AWS::AccountId}

  # !GetAtt: 리소스의 속성값 참조
  Output:
    Value: !GetAtt MyInstance.PublicIp

  # !If: 조건부 값
  Instance:
    Type: AWS::EC2::Instance
    Properties:
      InstanceType: !If [IsProd, t3.large, t3.micro]

  # !Join: 문자열 결합
  SecurityGroupIngress:
    CidrIp: !Join ['', ['10.0.', '0.0/16']]

  # !Select + !GetAZs: 가용영역 선택
  Subnet:
    Type: AWS::EC2::Subnet
    Properties:
      AvailabilityZone: !Select [0, !GetAZs '']
```

### 3. 실전 예시: VPC + EC2 + RDS

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Web Application Infrastructure

Parameters:
  Environment:
    Type: String
    Default: dev
  DBPassword:
    Type: String
    NoEcho: true    # 콘솔에 표시 안 함

Resources:
  # ─── VPC ───
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-vpc

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.10.0/24
      AvailabilityZone: !Select [0, !GetAZs '']

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.11.0/24
      AvailabilityZone: !Select [1, !GetAZs '']

  InternetGateway:
    Type: AWS::EC2::InternetGateway

  AttachGateway:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  # ─── 보안 그룹 ───
  WebSG:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Web Server SG
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0

  DbSG:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Database SG
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !Ref WebSG

  # ─── RDS ───
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Private subnets for DB
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2

  Database:
    Type: AWS::RDS::DBInstance
    Properties:
      Engine: postgres
      EngineVersion: '15'
      DBInstanceClass: db.t3.micro
      AllocatedStorage: 20
      MasterUsername: admin
      MasterUserPassword: !Ref DBPassword
      DBSubnetGroupName: !Ref DBSubnetGroup
      VPCSecurityGroups:
        - !Ref DbSG
      MultiAZ: false
      DeletionPolicy: Snapshot

Outputs:
  VpcId:
    Value: !Ref VPC
  DatabaseEndpoint:
    Value: !GetAtt Database.Endpoint.Address
```

### 4. 스택 관리

```bash
# 스택 생성
aws cloudformation create-stack \
  --stack-name my-app-dev \
  --template-body file://template.yaml \
  --parameters ParameterKey=Environment,ParameterValue=dev \
               ParameterKey=DBPassword,ParameterValue=MySecretPw123! \
  --capabilities CAPABILITY_IAM

# 스택 업데이트
aws cloudformation update-stack \
  --stack-name my-app-dev \
  --template-body file://template.yaml

# 변경 세트 (Change Set) — 업데이트 전 미리보기
aws cloudformation create-change-set \
  --stack-name my-app-dev \
  --change-set-name my-changes \
  --template-body file://template.yaml

aws cloudformation describe-change-set \
  --stack-name my-app-dev \
  --change-set-name my-changes

# 스택 삭제
aws cloudformation delete-stack --stack-name my-app-dev

# 스택 이벤트 확인
aws cloudformation describe-stack-events --stack-name my-app-dev
```

### 5. AWS CDK (Cloud Development Kit)

프로그래밍 언어(TypeScript, Python, Java)로 인프라를 정의하면 CloudFormation 템플릿으로 변환된다.

```typescript
// CDK (TypeScript) — CloudFormation YAML 대신 코드로 작성
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';

export class AppStack extends cdk.Stack {
    constructor(scope: cdk.App, id: string) {
        super(scope, id);

        // VPC
        const vpc = new ec2.Vpc(this, 'AppVpc', {
            maxAzs: 2,
            natGateways: 1,
        });

        // RDS
        const database = new rds.DatabaseInstance(this, 'Database', {
            engine: rds.DatabaseInstanceEngine.postgres({
                version: rds.PostgresEngineVersion.VER_15,
            }),
            instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            vpc,
            vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
            multiAz: false,
            removalPolicy: cdk.RemovalPolicy.SNAPSHOT,
        });

        // 출력
        new cdk.CfnOutput(this, 'DbEndpoint', {
            value: database.dbInstanceEndpointAddress,
        });
    }
}
```

```bash
# CDK 명령어
cdk init app --language typescript
cdk synth          # CloudFormation 템플릿 생성
cdk diff           # 변경사항 미리보기
cdk deploy         # 배포
cdk destroy        # 삭제
```

| YAML vs CDK | CloudFormation (YAML) | CDK (TypeScript) |
|------------|----------------------|-----------------|
| **작성** | 선언적 YAML | 프로그래밍 언어 |
| **재사용** | 중첩 스택, 모듈 | 클래스, 함수, 루프 |
| **타입 안전** | 없음 | IDE 자동완성 |
| **학습 곡선** | 낮음 | 중간 |
| **적합한 경우** | 간단한 인프라 | 복잡한 인프라, 반복 패턴 |

### 6. 고급 기능

#### 중첩 스택 (Nested Stacks)

큰 템플릿을 **모듈화**하여 재사용한다.

```yaml
Resources:
  NetworkStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/my-bucket/network.yaml
      Parameters:
        Environment: !Ref Environment

  DatabaseStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/my-bucket/database.yaml
      Parameters:
        VpcId: !GetAtt NetworkStack.Outputs.VpcId
```

#### 스택 간 참조 (Cross-Stack Reference)

```yaml
# 네트워크 스택 (Export)
Outputs:
  VpcId:
    Value: !Ref VPC
    Export:
      Name: !Sub ${Environment}-VpcId

# 앱 스택 (Import)
Resources:
  Instance:
    Type: AWS::EC2::Instance
    Properties:
      SubnetId: !ImportValue !Sub ${Environment}-SubnetId
```

#### 롤백 동작

```
스택 생성 실패 시:
  기본: 자동 롤백 (생성된 리소스 삭제)
  옵션: --disable-rollback (디버깅용)

스택 업데이트 실패 시:
  자동으로 이전 상태로 롤백
```

## 운영 팁

### 체크리스트

| 항목 | 설명 | 필수 |
|------|------|------|
| Change Set 사용 | 업데이트 전 미리보기 | ✅ |
| DeletionPolicy 설정 | DB는 Snapshot, 중요 리소스 Retain | ✅ |
| 파라미터로 환경 분리 | dev/staging/prod 하나의 템플릿 | ✅ |
| 시크릿은 SSM/SecretsManager | 템플릿에 비밀번호 하드코딩 금지 | ✅ |
| 태깅 일관성 | 모든 리소스에 Environment, Team 태그 | ⭐ |
| 스택 정책 | 프로덕션 리소스 삭제 방지 | ⭐ |

## 참고

- [AWS CloudFormation 공식 문서](https://docs.aws.amazon.com/cloudformation/)
- [AWS CDK 공식 문서](https://docs.aws.amazon.com/cdk/)
- [Terraform 기초](../../DevOps/Infrastructure_as_Code/Terraform_기초.md) — 멀티 클라우드 IaC
- [CodePipeline](CodePipeline.md) — CI/CD 파이프라인
