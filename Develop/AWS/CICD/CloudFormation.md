---
title: AWS CloudFormation
tags: [aws, cloudformation, iac, infrastructure-as-code, cdk, sam, stack, template, drift, stackset]
updated: 2026-05-06
---

# AWS CloudFormation

## 한 문장 정의

CloudFormation은 AWS 리소스를 YAML/JSON 템플릿으로 선언하면 그 상태로 만들어주는 IaC 서비스다. 직접 콘솔에서 누르거나 CLI로 만들던 리소스를 코드 한 덩어리로 묶어서 만들고 지운다.

처음 접했을 때 가장 헷갈리는 부분이 "스택"이라는 단위다. 스택은 한 템플릿이 만든 리소스들의 묶음이다. 스택을 지우면 그 안의 리소스가 같이 사라진다. 이 단순한 규칙이 운영하면서 가장 자주 사고를 낸다. 잘못 지웠다가 RDS가 같이 날아가는 사례가 흔하다. DeletionPolicy 이야기가 뒤에 나오는 이유다.

```
template.yaml ──▶  CloudFormation  ──▶  Stack
                   (control plane)       └ VPC, EC2, RDS, S3, ...
                                          (실제 리소스)
```

## 템플릿 구조

### 섹션 7개

| 섹션 | 용도 | 필수 |
|------|------|------|
| `AWSTemplateFormatVersion` | 템플릿 버전. 사실상 `2010-09-09` 고정 | 권장 |
| `Description` | 템플릿 설명 (1024자 이내) | 선택 |
| `Metadata` | UI 그룹화, 추가 정보 | 선택 |
| `Parameters` | 배포 시 입력값 | 선택 |
| `Mappings` | 정적 룩업 테이블 (리전별 AMI ID 등) | 선택 |
| `Conditions` | 분기 조건 | 선택 |
| `Transform` | SAM, 매크로 등 변환기 | 선택 |
| `Resources` | 실제 리소스 선언 | 필수 |
| `Outputs` | 출력값, 다른 스택에서 import 가능 | 선택 |

`Resources` 외에는 전부 선택이다. 작은 템플릿은 `Resources` 한 블록만 있어도 된다. 운영 들어가면 점점 다른 섹션이 붙는다.

### Resources

가장 많이 만지는 부분. 형식은 단순하다.

```yaml
Resources:
  논리이름:
    Type: AWS::서비스::리소스타입
    Properties:
      속성: 값
    DependsOn: 다른논리이름   # 선택
    DeletionPolicy: Retain   # 선택
    UpdateReplacePolicy: Snapshot  # 선택
    Metadata: {...}          # 선택
    Condition: 조건이름      # 선택
```

논리 이름(Logical ID)은 템플릿 안에서만 쓰는 식별자다. AWS에 만들어지는 실제 이름은 보통 `스택명-논리이름-랜덤` 형태로 자동 생성된다. 이름을 직접 지정하는 `Name` 같은 속성을 쓸 수도 있는데, 이름 충돌이나 업데이트 시 교체 문제 때문에 가급적 자동 생성을 두는 편이 낫다.

### Parameters

실행 시 받을 입력값이다. 같은 템플릿으로 dev/staging/prod를 만들 때 환경 이름을 파라미터로 받아서 분기한다.

```yaml
Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]
    Description: 배포 환경

  InstanceType:
    Type: String
    Default: t3.micro
    AllowedPattern: '^t[23]\.(nano|micro|small|medium)$'
    ConstraintDescription: t2/t3 micro~medium 만 허용

  KeyName:
    Type: AWS::EC2::KeyPair::KeyName  # AWS 전용 타입
    Description: SSH 키 페어 이름

  DBPassword:
    Type: String
    NoEcho: true                       # 콘솔/이벤트에 가려서 표시
    MinLength: 8
    MaxLength: 41
```

`AWS::EC2::KeyPair::KeyName` 같은 AWS 전용 타입을 쓰면 콘솔에서 드롭다운이 자동으로 뜬다. 손으로 입력하다 오타 내는 일을 줄일 수 있다.

`NoEcho: true`는 비밀번호를 가리지만 완전한 보안 수단은 아니다. CloudFormation 이벤트나 변경 세트 미리보기에서는 가려지지만, 그 비밀번호로 만든 리소스의 메타데이터에는 평문으로 남는 경우가 있다. 운영에선 SSM Parameter Store나 Secrets Manager를 참조하는 형태가 정석이다.

```yaml
Parameters:
  DBPassword:
    Type: AWS::SSM::Parameter::Value<String>
    Default: /myapp/dev/db/password
    NoEcho: true
```

이렇게 쓰면 SSM에 저장된 값을 배포 시점에 가져와서 쓴다. 템플릿에는 SSM 파라미터 이름만 남는다.

### Mappings

정적 룩업 테이블이다. 가장 흔한 용도는 리전별 AMI ID.

```yaml
Mappings:
  RegionMap:
    ap-northeast-2:
      AMI: ami-0c6e5afdd23291f73
    us-east-1:
      AMI: ami-0c55b159cbfafe1f0
    us-west-2:
      AMI: ami-098e42ae54c764c35

Resources:
  WebServer:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: !FindInMap [RegionMap, !Ref 'AWS::Region', AMI]
```

요즘은 SSM Public Parameter로 최신 AMI를 자동으로 가져오는 패턴이 더 흔하다. AMI는 자주 갱신되고 Mappings는 손으로 관리해야 해서 금세 낡는다.

```yaml
Parameters:
  LatestAmiId:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64
```

### Conditions

조건부 리소스 생성에 쓴다. prod에서만 NAT Gateway를 만든다거나, MultiAZ를 켠다거나.

```yaml
Conditions:
  IsProd: !Equals [!Ref Environment, prod]
  IsNotProd: !Not [!Equals [!Ref Environment, prod]]
  IsLargeRegion: !Or
    - !Equals [!Ref 'AWS::Region', us-east-1]
    - !Equals [!Ref 'AWS::Region', us-west-2]

Resources:
  NatGateway:
    Type: AWS::EC2::NatGateway
    Condition: IsProd            # IsProd가 true일 때만 생성
    Properties:
      AllocationId: !GetAtt NatEip.AllocationId
      SubnetId: !Ref PublicSubnet1

  Database:
    Type: AWS::RDS::DBInstance
    Properties:
      MultiAZ: !If [IsProd, true, false]
      DBInstanceClass: !If [IsProd, db.r5.large, db.t3.micro]
```

### Outputs

스택의 결과물을 내보낸다. 콘솔이나 CLI로 확인할 수도 있고, 다른 스택에서 import 할 수도 있다.

```yaml
Outputs:
  VpcId:
    Description: VPC ID
    Value: !Ref VPC
    Export:
      Name: !Sub ${AWS::StackName}-VpcId

  DatabaseEndpoint:
    Value: !GetAtt Database.Endpoint.Address
```

`Export`로 이름을 붙이면 다른 스택에서 `!ImportValue`로 가져온다. 단점은 export된 값을 누가 import 중이면 그 export를 바꾸거나 지울 수 없다. 의존성이 거꾸로 묶이는 셈이다. 작은 환경에서 편하지만 스택이 늘어나면 SSM Parameter Store에 값을 쓰고 다른 스택에서 읽는 패턴이 더 풀기 쉽다.

## YAML vs JSON

CloudFormation 템플릿은 YAML과 JSON 둘 다 받는다. 같은 내용을 두 형식으로 비교해본다.

```yaml
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub my-bucket-${AWS::AccountId}
```

```json
{
  "Resources": {
    "MyBucket": {
      "Type": "AWS::S3::Bucket",
      "Properties": {
        "BucketName": { "Fn::Sub": "my-bucket-${AWS::AccountId}" }
      }
    }
  }
}
```

YAML이 짧고 주석을 쓸 수 있어서 사람이 읽고 쓸 때 유리하다. JSON은 다른 도구에서 생성하거나 파이프로 흘릴 때 다루기 쉽다. CDK가 합성하는 결과물은 JSON이다.

YAML을 쓸 때 자주 막히는 부분 두 가지다.

첫째, 짧은 형식 함수와 태그가 충돌한다.

```yaml
# 안 됨
Bucket: !If !Ref ProdCondition mybucket-prod mybucket-dev

# 됨
Bucket: !If [ProdCondition, mybucket-prod, mybucket-dev]

# 짧은 형식을 중첩하면 긴 형식으로 풀어야 함
SubnetId: !If
  - IsProd
  - !Ref ProdSubnet
  - !Ref DevSubnet
```

`!Ref`, `!Sub` 같은 짧은 함수 안에 다른 짧은 함수를 또 넣으면 파서가 헷갈린다. 한 단계라도 풀어 쓰면 해결된다.

둘째, 들여쓰기. 탭은 안 된다. 스페이스 2칸이 보통이다. 에디터에서 자동 들여쓰기 설정이 탭으로 돼 있으면 syntax error가 나는데 메시지가 모호해서 시간을 잡아먹는다.

## 내장 함수

자주 쓰는 것 위주로.

```yaml
# Ref: 파라미터 값 또는 리소스의 기본 식별자
VpcId: !Ref MyVPC                         # VPC ID 반환

# Sub: 변수 치환
BucketName: !Sub ${Environment}-${AWS::AccountId}-bucket
UserData: !Sub |
  #!/bin/bash
  echo "Region: ${AWS::Region}" > /tmp/info
  echo "Stack: ${AWS::StackName}" >> /tmp/info

# GetAtt: 리소스의 속성값
DbHost: !GetAtt Database.Endpoint.Address
DbPort: !GetAtt Database.Endpoint.Port

# Join: 문자열 결합
ConnectionString: !Join
  - ''
  - - 'postgres://'
    - !GetAtt Database.Endpoint.Address
    - ':5432/mydb'

# Select: 배열에서 인덱스로 선택
AvailabilityZone: !Select [0, !GetAZs '']

# If: 조건 분기
InstanceType: !If [IsProd, t3.large, t3.micro]

# ImportValue: 다른 스택의 Export 값 가져오기
SubnetId: !ImportValue !Sub ${NetworkStack}-PublicSubnet1

# Cidr: CIDR 블록을 자동 분할
SubnetCidrs: !Cidr [!Ref VpcCidr, 6, 8]   # /16을 6개 /24로
```

`!Sub`는 `!Join`보다 가독성이 좋다. 단, `${}` 안에 `Resource.Attribute` 형태로 쓰면 GetAtt까지 한 번에 처리한다.

```yaml
Url: !Sub https://${ApiGateway.DomainName}/v1
# 동등: !Join ['', ['https://', !GetAtt ApiGateway.DomainName, '/v1']]
```

의사 파라미터(Pseudo Parameter)는 별도 선언 없이 쓸 수 있는 시스템 변수다.

| 변수 | 값 |
|------|------|
| `AWS::Region` | 현재 리전 (`ap-northeast-2`) |
| `AWS::AccountId` | 계정 ID |
| `AWS::StackName` | 스택 이름 |
| `AWS::StackId` | 스택 ARN |
| `AWS::Partition` | `aws`, `aws-cn`, `aws-us-gov` |
| `AWS::URLSuffix` | `amazonaws.com`, `amazonaws.com.cn` |
| `AWS::NoValue` | 속성을 생략하는 값 (조건부) |

`AWS::NoValue`가 미묘하다. 조건에 따라 어떤 속성 자체를 빼고 싶을 때 쓴다.

```yaml
Database:
  Type: AWS::RDS::DBInstance
  Properties:
    KmsKeyId: !If [HasKms, !Ref KmsKey, !Ref 'AWS::NoValue']
```

`HasKms`가 false면 `KmsKeyId` 속성 자체가 템플릿에서 빠진다. 빈 문자열을 넣으면 API가 거부하는 경우에 쓰는 패턴이다.

## 스택 라이프사이클

### 생성

```bash
aws cloudformation create-stack \
  --stack-name myapp-dev \
  --template-body file://template.yaml \
  --parameters ParameterKey=Environment,ParameterValue=dev \
               ParameterKey=DBPassword,ParameterValue=Secret123! \
  --capabilities CAPABILITY_NAMED_IAM \
  --tags Key=Project,Value=myapp Key=Owner,Value=team
```

`--capabilities` 플래그는 IAM 리소스를 만들거나 이름 있는 IAM 리소스를 만들 때 명시적으로 동의하라는 안전장치다. 처음에 빠뜨려서 `InsufficientCapabilitiesException` 에러를 받는 일이 잦다.

| 플래그 | 의미 |
|--------|------|
| `CAPABILITY_IAM` | IAM 역할/정책을 만드는 템플릿 |
| `CAPABILITY_NAMED_IAM` | 이름을 직접 지정한 IAM 리소스 |
| `CAPABILITY_AUTO_EXPAND` | SAM/매크로로 템플릿이 확장되는 경우 |

상태 흐름은 이렇다.

```
CREATE_IN_PROGRESS ──▶ CREATE_COMPLETE        (성공)
                  └─▶ CREATE_FAILED ──▶ ROLLBACK_IN_PROGRESS ──▶ ROLLBACK_COMPLETE
                                                              └▶ ROLLBACK_FAILED  (수동 개입 필요)
```

`ROLLBACK_COMPLETE` 상태가 된 스택은 더 이상 업데이트할 수 없다. 지우고 다시 만들어야 한다. 처음 보면 당황스럽지만 규칙이다. 실패한 스택은 빈 껍데기로 남아 있어서 콘솔에 보이는데, `delete-stack`으로 지우면 깔끔하다.

### 업데이트

```bash
aws cloudformation update-stack \
  --stack-name myapp-dev \
  --template-body file://template.yaml \
  --parameters ParameterKey=Environment,UsePreviousValue=true \
               ParameterKey=DBPassword,UsePreviousValue=true \
  --capabilities CAPABILITY_NAMED_IAM
```

업데이트 시 리소스가 어떻게 바뀌는지가 중요하다. 세 가지 동작이 있다.

| 변경 종류 | 동작 |
|-----------|------|
| **수정 가능 속성 변경** | 그 자리에서 수정 (No interruption / Some interruption) |
| **수정 불가 속성 변경** | 새 리소스 만들고 옛 리소스 삭제 (Replacement) |
| **무관한 변경** | 무시 |

EC2의 `InstanceType`은 stop/start로 처리되니 간단하다. 그런데 `AvailabilityZone`을 바꾸면 인스턴스가 통째로 교체된다. RDS의 `DBInstanceIdentifier`를 바꾸면 새 DB를 만들고 옛 DB를 삭제한다. 데이터가 그대로 사라진다. 변경 세트 없이 update를 그냥 돌리면 사고가 난다.

리소스 타입별로 어떤 속성이 교체를 유발하는지는 공식 문서의 각 리소스 페이지에 명시돼 있다. "Update requires: Replacement"가 표시되면 위험 신호다.

### 변경 세트 (Change Set)

업데이트 전에 무슨 일이 벌어질지 미리 본다. 운영 환경에서는 이 단계를 건너뛰면 안 된다.

```bash
# 변경 세트 생성
aws cloudformation create-change-set \
  --stack-name myapp-prod \
  --change-set-name update-2026-05 \
  --template-body file://template.yaml \
  --parameters ParameterKey=Environment,UsePreviousValue=true \
  --capabilities CAPABILITY_NAMED_IAM

# 결과 확인
aws cloudformation describe-change-set \
  --stack-name myapp-prod \
  --change-set-name update-2026-05

# 적용
aws cloudformation execute-change-set \
  --stack-name myapp-prod \
  --change-set-name update-2026-05

# 폐기
aws cloudformation delete-change-set \
  --stack-name myapp-prod \
  --change-set-name update-2026-05
```

`describe-change-set`의 출력 중 `Action: Replace`나 `Replacement: True`가 보이면 한 번 멈춰서 의도한 변화인지 확인한다. 데이터가 들어 있는 리소스(RDS, EBS, DynamoDB)에서 Replace가 잡히면 거의 사고다.

CDK도 내부적으로는 변경 세트를 만들고 실행한다. `cdk diff`가 그 결과를 보여준다.

### 삭제

```bash
aws cloudformation delete-stack --stack-name myapp-dev

# 특정 리소스만 빼고 삭제 (실패한 리소스를 강제로 보존)
aws cloudformation delete-stack \
  --stack-name myapp-dev \
  --retain-resources Database BucketLogs
```

`DeletionPolicy`로 리소스마다 삭제 동작을 제어한다.

```yaml
Database:
  Type: AWS::RDS::DBInstance
  DeletionPolicy: Snapshot          # 삭제 시 스냅샷 자동 생성
  UpdateReplacePolicy: Snapshot     # 교체될 때도 스냅샷
  Properties: {...}

LogsBucket:
  Type: AWS::S3::Bucket
  DeletionPolicy: Retain            # 스택 삭제해도 버킷은 남김
  Properties: {...}
```

| 정책 | 동작 |
|------|------|
| `Delete` (기본) | 리소스 같이 삭제 |
| `Retain` | 스택에서 분리만 하고 리소스는 보존 |
| `Snapshot` | 스냅샷 생성 후 삭제 (RDS, EBS, ElastiCache 등 지원 리소스만) |
| `RetainExceptOnCreate` | 생성 실패 시에는 삭제, 정상 운영 후 삭제 시는 보존 |

S3 버킷은 비어 있지 않으면 삭제가 거부된다. 스택을 지울 때 버킷에 객체가 남아 있어서 `DELETE_FAILED`로 끝나는 일이 흔하다. 사전에 비우거나, 객체가 들어가는 버킷은 처음부터 `DeletionPolicy: Retain`을 걸어두는 편이 안전하다.

## 실전 예제: VPC + EC2 + RDS

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Web stack with VPC, EC2 (ASG), RDS PostgreSQL

Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]

  DBPassword:
    Type: AWS::SSM::Parameter::Value<String>
    Default: /myapp/dev/db/password
    NoEcho: true

  LatestAmiId:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64

Conditions:
  IsProd: !Equals [!Ref Environment, prod]

Resources:
  # ── 네트워크 ──
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-vpc

  InternetGateway:
    Type: AWS::EC2::InternetGateway

  AttachIgw:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
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

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: AttachIgw
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PublicSubnet1Assoc:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet1
      RouteTableId: !Ref PublicRouteTable

  PublicSubnet2Assoc:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet2
      RouteTableId: !Ref PublicRouteTable

  # ── 보안 그룹 ──
  WebSG:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Web tier
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0

  DbSG:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: DB tier
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !Ref WebSG

  # ── EC2 Auto Scaling ──
  WebLaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: !Sub ${Environment}-web-lt
      LaunchTemplateData:
        ImageId: !Ref LatestAmiId
        InstanceType: !If [IsProd, t3.medium, t3.micro]
        SecurityGroupIds:
          - !Ref WebSG
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            dnf install -y nginx
            systemctl enable --now nginx
            echo "Hello from ${Environment}" > /usr/share/nginx/html/index.html

  WebAsg:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      VPCZoneIdentifier:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      LaunchTemplate:
        LaunchTemplateId: !Ref WebLaunchTemplate
        Version: !GetAtt WebLaunchTemplate.LatestVersionNumber
      MinSize: !If [IsProd, 2, 1]
      MaxSize: !If [IsProd, 10, 2]
      DesiredCapacity: !If [IsProd, 2, 1]
      HealthCheckType: EC2
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-web
          PropagateAtLaunch: true

  # ── RDS ──
  DbSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Private subnets
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2

  Database:
    Type: AWS::RDS::DBInstance
    DeletionPolicy: Snapshot
    UpdateReplacePolicy: Snapshot
    Properties:
      Engine: postgres
      EngineVersion: '15.5'
      DBInstanceClass: !If [IsProd, db.r5.large, db.t3.micro]
      AllocatedStorage: !If [IsProd, 100, 20]
      StorageType: gp3
      MasterUsername: appuser
      MasterUserPassword: !Ref DBPassword
      DBSubnetGroupName: !Ref DbSubnetGroup
      VPCSecurityGroups:
        - !Ref DbSG
      MultiAZ: !If [IsProd, true, false]
      BackupRetentionPeriod: !If [IsProd, 7, 1]
      DeletionProtection: !If [IsProd, true, false]

Outputs:
  VpcId:
    Value: !Ref VPC
    Export:
      Name: !Sub ${AWS::StackName}-VpcId

  DbEndpoint:
    Value: !GetAtt Database.Endpoint.Address

  AsgName:
    Value: !Ref WebAsg
```

이 한 템플릿이 dev에선 t3.micro/SingleAZ로, prod에선 t3.medium/MultiAZ + DeletionProtection으로 동작한다. 템플릿이 길어 보여도 비슷한 구조의 코드가 반복되는 셈이다. 이 정도 규모를 넘으면 중첩 스택이나 CDK로 모듈화를 고려한다.

## 중첩 스택 (Nested Stacks)

큰 템플릿을 여러 개로 쪼개고, 부모 스택이 자식 스택들을 묶는다.

```yaml
Resources:
  Network:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/iac-bucket/network.yaml
      Parameters:
        Environment: !Ref Environment
      TimeoutInMinutes: 10

  Database:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/iac-bucket/database.yaml
      Parameters:
        VpcId: !GetAtt Network.Outputs.VpcId
        SubnetIds: !GetAtt Network.Outputs.PrivateSubnetIds

  App:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/iac-bucket/app.yaml
      Parameters:
        VpcId: !GetAtt Network.Outputs.VpcId
        DbEndpoint: !GetAtt Database.Outputs.Endpoint
```

자식 템플릿은 S3에 올려둬야 한다. CDK는 합성 시 자동으로 올린다. 직접 쓸 땐 `aws cloudformation package` 명령이 로컬 경로를 S3로 자동 업로드한다.

```bash
aws cloudformation package \
  --template-file root.yaml \
  --s3-bucket iac-bucket \
  --output-template-file packaged.yaml

aws cloudformation deploy \
  --template-file packaged.yaml \
  --stack-name myapp-prod \
  --capabilities CAPABILITY_NAMED_IAM
```

중첩 스택의 단점은 자식 스택 하나가 실패하면 부모도 같이 롤백 단계로 들어간다는 점이다. 디버깅할 때 이벤트가 부모/자식 양쪽에 흩어져서 헷갈린다. 콘솔에서 자식 스택을 따로 열어 이벤트를 봐야 원인이 명확하다.

## StackSets

여러 계정·여러 리전에 같은 스택을 한 번에 배포한다. 조직 전체에 보안 베이스라인(IAM 역할, GuardDuty, Config 등)을 까는 용도가 가장 흔하다.

```bash
# StackSet 생성 (관리 계정에서)
aws cloudformation create-stack-set \
  --stack-set-name baseline \
  --template-body file://baseline.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false

# 인스턴스 생성 (각 계정·리전에 실제 배포)
aws cloudformation create-stack-instances \
  --stack-set-name baseline \
  --deployment-targets OrganizationalUnitIds=ou-xxxx-xxxxxxx \
  --regions ap-northeast-2 us-east-1 \
  --operation-preferences MaxConcurrentPercentage=25,FailureTolerancePercentage=10
```

권한 모델이 두 가지다.

| 모델 | 사용 |
|------|------|
| `SELF_MANAGED` | 각 계정에 IAM 역할(`AWSCloudFormationStackSetExecutionRole` 등)을 직접 만들고 신뢰 관계를 맺음 |
| `SERVICE_MANAGED` | AWS Organizations와 연동해 자동 처리. 권장 |

운영 시 자주 만나는 문제가 일부 계정에서만 실패하는 상황이다. `FailureTolerancePercentage`를 0으로 두면 한 계정만 실패해도 전체가 멈춘다. 10~25% 정도 여유를 두고 실패한 계정은 별도로 추적하는 패턴이 일반적이다.

## Drift Detection

스택 외부에서 누군가 콘솔로 리소스를 직접 바꾸면 템플릿과 실제 상태가 어긋난다. 이걸 드리프트라 부른다. CloudFormation은 이를 탐지하는 기능을 제공한다.

```bash
# 스택 단위 드리프트 탐지 시작
aws cloudformation detect-stack-drift --stack-name myapp-prod

# 결과 조회
aws cloudformation describe-stack-resource-drifts \
  --stack-name myapp-prod \
  --stack-resource-drift-status-filters MODIFIED DELETED
```

탐지 결과는 네 가지 상태로 나온다.

- `IN_SYNC`: 일치
- `MODIFIED`: 속성이 변경됨
- `DELETED`: 리소스가 외부에서 삭제됨
- `NOT_CHECKED`: 드리프트 검사를 지원하지 않는 리소스

탐지가 됐다고 자동으로 고쳐주지는 않는다. 두 가지 선택지뿐이다. 템플릿을 실제 상태에 맞게 수정하거나, 콘솔에서 바꾼 내용을 되돌리고 다시 배포해서 강제로 맞추거나. 후자를 시도할 때 IAM 역할이 외부에서 인라인 정책이 추가됐다거나 하는 경우, CloudFormation이 그 변화를 모르고 덮어쓰기 때문에 의도와 다른 결과가 나올 수 있다.

운영 팁: 정기적으로(예: 주 1회) Drift Detection을 돌리고 결과를 Slack으로 알린다. EventBridge + Lambda로 짤 수 있다. 콘솔로 급하게 손댄 변경이 누적되면 다음 배포에서 사고가 난다.

## Terraform과 비교

| 항목 | CloudFormation | Terraform |
|------|----------------|-----------|
| 제공자 | AWS 네이티브 | HashiCorp, 멀티 클라우드 |
| 작성 언어 | YAML/JSON | HCL |
| 상태 관리 | AWS가 보관 | 별도 backend (S3+DynamoDB 등) 직접 운영 |
| 신규 AWS 서비스 지원 | 출시 직후 보통 즉시 | 며칠~수주 지연 |
| 드리프트 탐지 | 내장 | `terraform plan` |
| 모듈화 | 중첩 스택, 매크로 | 모듈, workspace |
| 가져오기 | `import` (리소스마다 지원 여부 다름) | `terraform import`, `import` 블록 |
| 멀티 계정/리전 | StackSets | provider alias, workspace |
| 조건부 생성 | `Conditions` | `count`, `for_each` |
| 비용 | 무료 (리소스 비용만) | 오픈소스 무료, Cloud/Enterprise 유료 |
| 락(lock) | 자동 | DynamoDB 등 직접 구성 |

내 경험상 선택 기준은 단순하다.

- AWS만 쓰고, CDK로 갈 가능성도 있다 → CloudFormation
- AWS + GCP, AWS + Cloudflare처럼 멀티 프로바이더 → Terraform
- 신규 AWS 서비스를 출시 직후부터 IaC로 다뤄야 한다 → CloudFormation
- 팀에 HCL 경험이 충분하고 모듈 생태계를 활용하고 싶다 → Terraform

CloudFormation의 결정적 약점은 진단성이다. 무엇이 잘못됐는지 메시지가 모호한 경우가 자주 있다. Terraform은 plan에서 정확한 diff를 보여주지만, 상태 파일을 잘못 다루면 복구가 까다롭다. 둘 다 트레이드오프가 있다.

## CDK

CloudFormation 템플릿을 손으로 쓰지 않고, TypeScript/Python/Java로 정의해서 합성한다. 합성 결과는 결국 CloudFormation 템플릿이다.

```typescript
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';

export class AppStack extends cdk.Stack {
    constructor(scope: cdk.App, id: string, props: cdk.StackProps) {
        super(scope, id, props);

        const vpc = new ec2.Vpc(this, 'Vpc', {
            maxAzs: 2,
            natGateways: this.node.tryGetContext('env') === 'prod' ? 2 : 1,
        });

        const db = new rds.DatabaseInstance(this, 'Db', {
            engine: rds.DatabaseInstanceEngine.postgres({
                version: rds.PostgresEngineVersion.VER_15_5,
            }),
            instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            vpc,
            vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
            removalPolicy: cdk.RemovalPolicy.SNAPSHOT,
        });

        new cdk.CfnOutput(this, 'DbEndpoint', { value: db.dbInstanceEndpointAddress });
    }
}
```

```bash
cdk synth      # CloudFormation 템플릿 생성
cdk diff       # 현재 스택과 차이 표시
cdk deploy     # 변경 세트 만들고 실행
cdk destroy
```

CDK의 장점은 반복 패턴을 함수/클래스로 묶을 수 있다는 점, 그리고 IDE 자동완성이다. 단점은 합성된 템플릿을 직접 봐야 디버깅이 가능한 경우가 많다는 것. CDK 추상화 한 줄이 백 줄짜리 CloudFormation을 만들어내기 때문에, 무엇이 만들어졌는지 모르면 비용 산정도 어렵다. `cdk synth`로 결과 템플릿을 한 번씩 들여다보는 습관이 필요하다.

## 운영하면서 자주 깨지는 지점

### 1. 롤백 실패

`UPDATE_ROLLBACK_FAILED` 상태는 가장 까다롭다. 업데이트가 실패해서 이전 상태로 되돌리려는데, 그 되돌림 자체도 실패한 상황이다. 흔한 원인은 이렇다.

- 스택 외부에서 손으로 리소스를 바꿔서 CloudFormation이 원래 상태를 못 찾음
- 보안 그룹 같은 리소스가 다른 리소스에 참조되어 삭제 실패
- 시간 초과(Default 60분 등)
- IAM 권한이 중간에 빠짐

처리 방법.

```bash
# 문제 리소스를 건너뛰고 강제로 롤백 완료 처리
aws cloudformation continue-update-rollback \
  --stack-name myapp-prod \
  --resources-to-skip ProblemResource1 ProblemResource2
```

`resources-to-skip`은 해당 리소스를 "이미 정상"이라고 가정하고 진행한다. 이후 그 리소스를 직접 정리하거나 템플릿과 동기화하는 작업이 추가로 필요하다. 권장은 사전에 변경 세트로 검증하는 것. 사후 수습은 손이 많이 간다.

### 2. 의존성 순환

리소스가 서로를 참조해서 누가 먼저 만들어져야 하는지 결정 못 하는 상황이다. 보안 그룹 두 개가 서로의 그룹 ID를 ingress 규칙에서 참조하면 발생한다.

```yaml
# 안 됨: WebSG → DbSG → WebSG (순환)
WebSG:
  Type: AWS::EC2::SecurityGroup
  Properties:
    SecurityGroupIngress:
      - SourceSecurityGroupId: !Ref DbSG  # DB SG를 참조

DbSG:
  Type: AWS::EC2::SecurityGroup
  Properties:
    SecurityGroupIngress:
      - SourceSecurityGroupId: !Ref WebSG  # Web SG를 참조
```

해결책은 SG 자체와 ingress 규칙을 분리하는 것.

```yaml
WebSG:
  Type: AWS::EC2::SecurityGroup
  Properties:
    GroupDescription: Web
    VpcId: !Ref VPC

DbSG:
  Type: AWS::EC2::SecurityGroup
  Properties:
    GroupDescription: DB
    VpcId: !Ref VPC

# Ingress 규칙은 별도 리소스로 분리
WebFromDb:
  Type: AWS::EC2::SecurityGroupIngress
  Properties:
    GroupId: !Ref WebSG
    SourceSecurityGroupId: !Ref DbSG
    IpProtocol: tcp
    FromPort: 8080
    ToPort: 8080

DbFromWeb:
  Type: AWS::EC2::SecurityGroupIngress
  Properties:
    GroupId: !Ref DbSG
    SourceSecurityGroupId: !Ref WebSG
    IpProtocol: tcp
    FromPort: 5432
    ToPort: 5432
```

이 패턴은 SG 외에도 비슷한 구조에서 자주 쓴다. "리소스 본체"와 "관계"를 분리한다는 발상.

### 3. IAM 권한 부족

`User: arn:aws:iam::xxxx:user/yyy is not authorized to perform: iam:CreateRole` 같은 메시지를 만난다. CloudFormation을 실행하는 주체(사용자/CI 역할/Service Role)가 그 안의 모든 리소스를 만들/지울 권한을 가져야 한다.

두 가지 권한 모델.

- 직접 권한 위임: 실행자에게 모든 리소스 권한을 직접 부여
- Service Role: CloudFormation에 별도 역할을 넘겨주고, 그 역할이 실제 작업 수행

```bash
aws cloudformation create-stack \
  --stack-name myapp \
  --template-body file://t.yaml \
  --role-arn arn:aws:iam::123:role/CloudFormationServiceRole \
  --capabilities CAPABILITY_NAMED_IAM
```

Service Role 패턴이 운영에선 더 안전하다. 사람의 권한과 배포의 권한을 분리할 수 있다. 사람은 `cloudformation:*`과 `iam:PassRole`(특정 역할에 한해서)만 가지고, 실제 리소스는 Service Role이 만든다.

권한 부족이 배포 중간에 터지면 부분적으로 만들어진 상태에서 롤백이 시작되는데, 롤백에도 같은 권한이 필요하다. 그래서 권한 점검은 사전에 끝내야 한다. CloudFormation 콘솔에는 "스택 정책 시뮬레이션" 같은 기능이 없어서 작은 테스트 스택으로 미리 돌려보는 방법이 가장 확실하다.

### 4. 그 외 잔주의 사항

- **이름 충돌**: `BucketName`, `RoleName` 같은 명시적 이름은 글로벌·계정 단위 유니크 제약이 있다. 같은 이름으로 두 번 만들면 두 번째가 실패한다. CloudFormation이 자동 이름을 만들도록 두면 이 문제를 피한다. 단, Replace가 발생할 때 자동 이름은 새 이름으로 바뀐다.
- **타임아웃**: RDS는 생성에 10~20분, NAT Gateway 5분 등 시간이 오래 걸리는 리소스가 있다. `--timeout-in-minutes`를 너무 짧게 잡으면 자동 롤백된다. 60분 이상으로 두는 편이 안전하다.
- **Limits**: 한 템플릿에 리소스 500개, 파라미터 200개, 매핑 200개 등 한도가 있다. 큰 환경에선 중첩 스택으로 쪼갠다.
- **CFN-Init / cfn-signal**: EC2 부팅 후 설정 스크립트가 끝났다는 신호를 CloudFormation에 보내는 기능. ASG 같은 리소스에 `CreationPolicy`로 신호를 기다리게 하면 부팅 실패도 스택 실패로 잡힌다.

## 참고

- [AWS CloudFormation 공식 문서](https://docs.aws.amazon.com/cloudformation/)
- [AWS CDK 공식 문서](https://docs.aws.amazon.com/cdk/)
- [CodePipeline](CodePipeline.md)
