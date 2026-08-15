---
title: AWS 실무 입문 15선
tags: [aws, cloud, vpc, network, iam, security, devops, monitoring, backend, messaging, event-driven, load-balancer]
updated: 2026-08-15
---

# AWS 실무 입문 15선

신입이 AWS 프로젝트에 투입되면 처음 받는 것이 IAM 계정이고, 처음 당황하는 것이 VPC다. 서비스 15개를 실제 투입 순서대로 정리했다. 각 서비스가 어떤 상황에서 처음 등장하는지, 어디서 막히는지, 무엇을 잘못 설정하는지 위주로 썼다.

---

## 1. IAM — 계정 받은 날부터 시작

팀에 합류하면 가장 먼저 받는 것이 IAM 계정이다. 처음엔 "AdministratorAccess 주면 다 되는 거 아닌가"라고 생각하지만, 실제로 팀에서 가장 많이 손이 가는 서비스 중 하나가 IAM이다.

### 정책 구조

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-app-bucket/*"
    }
  ]
}
```

S3 권한에서 자주 틀리는 부분이 있다. `s3:ListBucket`은 버킷 레벨 ARN(`arn:aws:s3:::bucket`)에 붙고, `s3:GetObject`는 객체 레벨 ARN(`arn:aws:s3:::bucket/*`)에 붙는다. 이걸 반대로 설정하면 `AccessDenied`가 아니라 `NoSuchKey`가 나와서 권한 문제인지 키 문제인지 구분이 안 된다.

`"Resource": "*"`로 시작하는 정책은 나중에 정책 감사할 때 찾아내기 어렵다. 처음부터 리소스 ARN을 명시하는 습관을 들인다.

### 역할 신뢰 정책

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

`Principal`을 `"*"`로 설정하면 어떤 AWS 주체든 이 역할을 assume할 수 있어 심각한 보안 구멍이 된다. CI/CD에서 cross-account 역할을 설정할 때 실수로 생기는 경우가 있다.

IAM User보다 IAM Role을 쓴다. EC2나 Lambda에 역할을 붙이면 액세스 키를 코드나 환경 변수에 박아 넣지 않아도 된다. 액세스 키를 GitHub에 올리는 사고가 지금도 매일 발생한다.

---

## 2. VPC — 처음에 CIDR을 잘못 잡으면 나중에 고치기 힘들다

VPC는 처음에 제대로 설계하지 않으면 나중에 피곤해진다. 서브넷을 너무 작게 잡아서 IP가 부족해지거나, 퍼블릭/프라이빗 구분을 안 해서 RDS가 인터넷에 노출되는 경우가 실제로 있다.

### 실용적인 CIDR 예시

```
VPC: 10.0.0.0/16  (최대 65,536 IP)

퍼블릭 서브넷 (ALB, NAT Gateway 배치):
  ap-northeast-2a: 10.0.1.0/24  (사용 가능 254 IP)
  ap-northeast-2c: 10.0.2.0/24

프라이빗 서브넷 (앱 서버):
  ap-northeast-2a: 10.0.10.0/24
  ap-northeast-2c: 10.0.11.0/24

프라이빗 서브넷 (DB):
  ap-northeast-2a: 10.0.20.0/24
  ap-northeast-2c: 10.0.21.0/24
```

`/16`은 처음엔 너무 크다고 느낀다. 그런데 나중에 VPC Peering이나 Transit Gateway로 다른 VPC와 연결할 때 CIDR이 겹치면 안 돼서 여유 있게 잡는 게 낫다. 이미 `/24`로 VPC를 만들었다면 CIDR을 수정할 수 없다. 새로 만들어야 한다.

### 흔히 틀리는 설정

**라우팅 테이블**: 퍼블릭 서브넷은 인터넷 게이트웨이(IGW)로 `0.0.0.0/0` 라우팅이 있어야 한다. 프라이빗 서브넷은 NAT Gateway로 연결한다. 라우팅 테이블을 서브넷에 직접 연결(associate)하지 않으면 기본 라우팅 테이블이 쓰이는데, 기본 테이블엔 IGW 라우팅이 없다. "퍼블릭 서브넷인데 왜 인터넷이 안 되지?" 라고 한참 찾게 된다.

```bash
# 현재 라우팅 테이블과 서브넷 연결 확인
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=vpc-xxxxxxxx" \
  --query 'RouteTables[*].{ID:RouteTableId,Routes:Routes[*].{Dest:DestinationCidrBlock,GW:GatewayId},Assoc:Associations[*].SubnetId}' \
  --output json
```

**NAT Gateway 비용**: NAT Gateway는 시간당 요금 외에 데이터 처리 비용이 GB당 붙는다. 개발 환경에서 NAT Gateway를 켜두고 잊어버리면 달에 생각보다 많이 나온다. 개발 환경에는 NAT Instance(t3.nano EC2)를 쓰거나 필요할 때만 켜는 팀이 있다.

고가용성을 위해 NAT Gateway를 AZ당 하나씩 만들어야 한다. NAT Gateway 하나만 두면 그 AZ가 죽을 때 다른 AZ의 프라이빗 서브넷도 인터넷이 끊긴다.

---

## 3. EC2 — 인스턴스 유형과 구매 방식

EC2는 가장 먼저 쓰는 서비스지만 제대로 쓰는 팀이 드물다.

### 인스턴스 유형 선택

| 유형 | 특성 | 용도 |
|------|------|------|
| t3.micro / t3.small | CPU 버스트 가능 | 개발, 테스트 |
| t3a.medium (AMD) | t3 대비 약 10% 저렴 | 소규모 앱 서버 |
| c6i.xlarge | CPU 집약 | 연산 집약적 서비스 |
| r6i.large | 메모리 집약 | 인메모리 처리, 캐시 |
| m6i.large | CPU/메모리 균형 | 범용 웹 서버 |

t3 계열의 CPU 크레딧 모델을 모르면 당황한다. 평소엔 잘 돌다가 갑자기 응답이 느려지는데, `unlimited` 옵션이 켜져 있으면 크레딧 부족 시 추가 요금이 붙는다. 기본값이 `unlimited`라서 의도치 않게 요금이 나올 수 있다.

### 구매 옵션

| 옵션 | 특성 | 언제 쓰나 |
|------|------|-----------|
| On-Demand | 기준 가격 | 예측 불가한 워크로드 |
| Savings Plans | 최대 66% 절감 | 1~3년 약정, 가장 범용적 |
| Reserved Instance | 최대 72% 절감 | 특정 인스턴스 타입 고정 |
| Spot | 최대 90% 절감 | 중단 가능한 배치 작업 |

Spot 인스턴스는 2분 전 알림 후 강제 종료된다. Stateless 배치 작업(데이터 처리, 렌더링 등)에만 써야 한다. 상태가 있는 웹 서버에 Spot을 쓰다가 서비스가 중단되는 사례가 있다.

### EBS 볼륨

EC2를 종료해도 기본값에 따라 EBS 볼륨은 남는다. 루트 볼륨은 인스턴스 종료 시 함께 삭제되는 게 기본이지만, 추가 볼륨은 남는다. 인스턴스를 많이 만들고 지우다 보면 EBS 볼륨이 쌓여서 비용이 나온다.

```bash
# 연결되지 않은 EBS 볼륨 찾기
aws ec2 describe-volumes \
  --filters "Name=status,Values=available" \
  --query 'Volumes[*].{ID:VolumeId,Size:Size,Created:CreateTime}' \
  --output table
```

---

## 4. ALB — HTTP 라우팅과 HTTPS 설정

ALB는 설정 자체보다 타겟 그룹 헬스체크에서 막히는 경우가 많다.

### 헬스체크 함정

기본 헬스체크 경로가 `/`인데, Spring Boot는 기본적으로 `/` 경로가 없다. `/actuator/health`나 앱이 200을 반환하는 경로로 설정해야 한다. 헬스체크 실패 → 타겟 `unhealthy` 상태 → 트래픽 없음 순서로 이어지는데, 처음엔 "배포는 됐는데 왜 접근이 안 되지?"로 나타난다.

```bash
# 타겟 그룹 헬스 상태 확인
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:ap-northeast-2:123456789:targetgroup/my-tg/abc123
```

헬스체크 임계값도 확인한다. 기본 Healthy threshold가 5인데, 이는 5번 연속 성공해야 healthy로 바뀐다는 뜻이다. 배포 후 트래픽이 들어오기까지 헬스체크 간격 × 임계값만큼 기다려야 한다.

### HTTPS 설정

ACM에서 인증서를 발급하고 ALB 리스너에 붙인다. 도메인 검증을 DNS 방식으로 하면 Route 53에 CNAME 레코드가 자동으로 추가돼서 편하다. 이메일 방식은 도메인 소유자 메일로 확인 요청이 가는데 받지 못하는 경우가 많다.

리스너 설정:
```
HTTPS:443 → 타겟 그룹 (기본 액션)
HTTP:80   → HTTPS:443으로 리다이렉트 (301)
```

리다이렉트를 안 해놓으면 HTTP로 접근하는 요청이 연결 거부나 타임아웃이 된다. 브라우저는 보통 HTTPS를 먼저 시도하지만, API 클라이언트는 HTTP로 그냥 보내는 경우가 있다.

### 보안 그룹 설정

```
ALB 보안 그룹:
  인바운드: 80, 443 ← 0.0.0.0/0

EC2/ECS 보안 그룹:
  인바운드: 8080 ← ALB 보안 그룹 ID (CIDR이 아닌 SG ID 참조)
```

EC2 보안 그룹에 `0.0.0.0/0:8080`을 여는 실수를 자주 본다. ALB를 쓴다면 EC2 포트는 ALB 보안 그룹에서만 접근하도록 제한해야 한다. 보안 그룹 ID를 소스로 지정하면 ALB IP가 바뀌어도 자동으로 따라간다.

---

## 5. RDS — 관리형 DB의 함정

RDS는 편하지만 비용이 많이 나오고, Multi-AZ와 Read Replica를 혼동하는 경우가 많다.

### Multi-AZ vs Read Replica

**Multi-AZ**: 장애 복구 목적. 스탠바이 인스턴스는 읽기 요청을 받지 않는다. 장애 발생 시 자동 페일오버가 60~120초 걸린다. 엔드포인트는 하나고, 페일오버 후 자동으로 스탠바이를 가리킨다.

**Read Replica**: 읽기 분산 목적. 별도 엔드포인트. 복제 지연(replication lag)이 있어서 쓰기 직후 Read Replica에서 읽으면 데이터가 안 보이는 경우가 있다. "방금 저장했는데 조회가 안 된다"는 버그 리포트가 이 경우다.

Multi-AZ 없이 Read Replica만 있으면, Primary가 죽었을 때 Read Replica를 수동으로 승격해야 한다. 자동 페일오버가 아니다.

### 파라미터 그룹

RDS를 만들 때 기본 파라미터 그룹이 붙는다. 기본 파라미터 그룹은 수정 불가다. slow query log나 `max_connections` 같은 설정을 건드리려면 커스텀 파라미터 그룹을 미리 만들어 연결해야 한다. 나중에 파라미터 그룹을 교체하면 재시작이 필요할 수 있다.

```bash
# 커스텀 파라미터 그룹 생성
aws rds create-db-parameter-group \
  --db-parameter-group-name my-mysql8-params \
  --db-parameter-group-family mysql8.0 \
  --description "Custom params for my app"

# slow query 설정
aws rds modify-db-parameter-group \
  --db-parameter-group-name my-mysql8-params \
  --parameters "ParameterName=slow_query_log,ParameterValue=1,ApplyMethod=immediate" \
               "ParameterName=long_query_time,ParameterValue=1,ApplyMethod=immediate"
```

### 연결 수 관리

RDS의 `max_connections`는 인스턴스 메모리에 비례해서 결정된다. `db.t3.micro`(1GB RAM)는 MySQL 기준 수십~80 개 수준이다. 앱 서버가 여러 대고 각 서버에서 연결 풀을 열면 순식간에 가득 찬다. 이 경우 RDS Proxy를 앞에 두면 실제 DB 연결 수를 줄일 수 있다.

---

## 6. ECS — 컨테이너 오케스트레이션

ECS는 처음에 개념이 헷갈린다. Cluster > Service > Task Definition > Container 계층을 이해하는 게 먼저다.

### Task Definition 핵심 설정

```json
{
  "family": "my-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::123456789:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789:role/myAppTaskRole",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "123456789.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest",
      "portMappings": [{"containerPort": 8080}],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/my-app",
          "awslogs-region": "ap-northeast-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

`executionRoleArn`과 `taskRoleArn`을 혼동한다.

- `executionRole`: ECS 에이전트가 ECR에서 이미지를 받고, CloudWatch에 로그를 쓰는 권한. 이게 없으면 이미지 pull 자체가 실패한다.
- `taskRole`: 컨테이너 안의 앱이 AWS 서비스를 호출하는 권한. 앱에서 S3나 DynamoDB를 쓰려면 이 역할에 권한을 붙여야 한다.

`logConfiguration`을 설정하지 않으면 컨테이너 로그가 어디에도 남지 않는다. 태스크가 죽는 이유를 알 수 없게 된다.

### 서비스 배포

ECS Service를 통해 원하는 태스크 수를 유지한다. 롤링 업데이트 시 기본적으로 최소 100% 유지, 최대 200%로 새 버전을 올리고 구 버전을 내린다.

```bash
# 서비스 강제 새 배포
aws ecs update-service \
  --cluster my-cluster \
  --service my-service \
  --force-new-deployment
```

배포 중 태스크가 `STOPPED` 상태로 자꾸 죽으면 `stopped-task` 이유를 확인한다. 보통 OOM(메모리 초과), 헬스체크 실패, 이미지 pull 실패 중 하나다.

---

## 7. Fargate — 서버리스 컨테이너

Fargate는 ECS의 런치 타입 중 하나다. EC2를 직접 관리하지 않아도 된다는 게 핵심이다.

### EC2 런치 타입과의 차이

| 항목 | EC2 런치 타입 | Fargate |
|------|--------------|---------|
| 서버 관리 | 직접 패치, 업데이트 | AWS가 관리 |
| 과금 단위 | EC2 인스턴스 시간 | vCPU + 메모리 사용 시간 |
| 최소 단위 | EC2 인스턴스 크기 | 0.25 vCPU / 0.5 GB |
| 네트워크 | 브리지, host 등 선택 가능 | awsvpc만 가능 |

Fargate는 EC2보다 vCPU당 단가가 높다. 태스크가 24시간 돌아가는 워크로드라면 EC2 런치 타입이 싸다. 트래픽이 불규칙하고 0으로 스케일 다운하는 경우엔 Fargate가 유리하다.

### 프라이빗 서브넷에서 이미지 pull 문제

Fargate 태스크를 프라이빗 서브넷에 배포하면 ECR에서 이미지를 받을 수 없다. 두 가지 방법이 있다.

방법 1 — NAT Gateway 경유:
```
Fargate Task (Private Subnet)
  → NAT Gateway (Public Subnet)
  → Internet
  → ECR
```

방법 2 — VPC 엔드포인트:
```bash
# ECR 접근용 VPC 엔드포인트 생성
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxxxxx \
  --service-name com.amazonaws.ap-northeast-2.ecr.dkr \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxxxxx

aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxxxxx \
  --service-name com.amazonaws.ap-northeast-2.ecr.api \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxxxxx

# S3 게이트웨이 엔드포인트 (ECR 이미지 레이어가 S3에 저장됨)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxxxxx \
  --service-name com.amazonaws.ap-northeast-2.s3 \
  --vpc-endpoint-type Gateway \
  --route-table-ids rtb-xxxxxxxx
```

VPC 엔드포인트 방법이 장기적으로 NAT Gateway보다 저렴하고 트래픽이 AWS 내부에서만 돈다.

---

## 8. Lambda — 이벤트 드리븐 함수

Lambda는 단순해 보이지만 VPC 연동이나 동시 실행 제한에서 예상치 못한 문제가 생긴다.

### 기본 함정

기본 타임아웃이 3초다. 외부 API 호출이나 DB 쿼리가 포함된 함수는 충분하지 않다. 최대 15분까지 설정할 수 있지만, 길게 잡으면 실패 시 재시도에도 동일한 시간이 걸린다.

메모리와 CPU는 연동된다. 메모리 1,769 MB = vCPU 1개 기준이다. CPU 집약적 작업에서 메모리를 늘리면 실행 시간이 짧아져서 비용이 오히려 줄어드는 경우가 있다.

```bash
# 함수 설정 확인
aws lambda get-function-configuration \
  --function-name my-function \
  --query '{Timeout:Timeout,MemorySize:MemorySize,VpcConfig:VpcConfig}'
```

### VPC 연동 시 주의사항

Lambda를 VPC 안에 넣으면 RDS 같은 프라이빗 리소스에 접근할 수 있다. 대신 인터넷 접근이 필요하면 NAT Gateway가 있어야 한다. VPC 밖에 있는 Lambda는 외부 API를 직접 호출할 수 있지만, VPC 안에 있으면 NAT 없이는 못 한다.

Lambda에서 RDS를 직접 연결하면 함수 호출마다 DB 연결이 새로 생긴다. 동시 실행이 많으면 DB 연결이 금방 가득 찬다. 이 경우 RDS Proxy를 사이에 두거나 연결 풀을 전역 변수로 관리해서 재사용한다.

### 동시 실행 제한

계정 기본 동시 실행 한도가 있다. 특정 함수가 폭발적으로 호출되면 같은 계정의 다른 함수가 쓰로틀링된다. 중요한 함수에는 Provisioned Concurrency나 예약된 동시 실행을 설정한다.

---

## 9. ECR — 컨테이너 이미지 저장소

ECR은 단순해 보이지만 라이프사이클 정책을 설정하지 않으면 이미지가 무제한으로 쌓인다.

### 이미지 푸시

```bash
# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin \
  123456789.dkr.ecr.ap-northeast-2.amazonaws.com

# 이미지 태그 후 푸시
docker tag my-app:latest \
  123456789.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest

docker push \
  123456789.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest
```

로그인 토큰은 12시간 유효하다. CI/CD 파이프라인에서 이 명령을 캐싱하면 반나절 지나서 푸시가 실패한다.

### 라이프사이클 정책

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "최근 10개만 유지",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {"type": "expire"}
    }
  ]
}
```

이미지 하나가 수백 MB인데 저장 비용이 GB당 부과된다. CI/CD를 자주 돌리는 팀에서 라이프사이클 정책 없이 수백 개 이미지가 쌓이는 경우가 있다.

---

## 10. S3 — 객체 스토리지

S3는 단순해 보이지만 퍼블릭 액세스 설정이 여러 단계로 나뉘어 혼란스럽다.

### 퍼블릭 액세스 차단

퍼블릭 액세스 차단 설정이 버킷 레벨과 계정 레벨 두 곳에 있다. 계정 레벨에서 막혀 있으면 버킷 정책으로 퍼블릭을 허용해도 안 된다.

```bash
# 버킷 퍼블릭 액세스 차단 상태 확인
aws s3api get-public-access-block --bucket my-bucket

# 계정 레벨 확인
aws s3control get-public-access-block --account-id 123456789
```

버킷 ACL과 버킷 정책이 별개로 작동한다는 점도 혼란의 원인이다. 두 곳 모두 허용해야 퍼블릭 접근이 된다. 요즘엔 ACL을 비활성화하고 버킷 정책만 쓰는 게 권장된다.

### Presigned URL

파일 업로드를 서버를 거치지 않고 클라이언트가 S3에 직접 올리게 할 때 쓴다. 업로드 파일이 크면 서버 메모리와 대역폭을 아낄 수 있다.

```python
import boto3

s3 = boto3.client('s3', region_name='ap-northeast-2')

# 업로드용 Presigned URL (5분 유효)
url = s3.generate_presigned_url(
    'put_object',
    Params={
        'Bucket': 'my-bucket',
        'Key': 'uploads/file.jpg',
        'ContentType': 'image/jpeg'
    },
    ExpiresIn=300
)
```

`ContentType`을 Params에 지정하면 클라이언트 요청 헤더에도 동일한 Content-Type을 보내야 한다. 안 맞으면 서명 불일치로 `403`이 난다.

### 정적 웹사이트와 HTTPS

S3 정적 웹사이트 호스팅은 HTTP만 지원한다. HTTPS를 쓰려면 CloudFront를 앞에 두고 S3를 오리진으로 연결해야 한다. 이 경우 S3 버킷을 퍼블릭으로 열지 않고 OAC(Origin Access Control)를 써서 CloudFront에서만 접근하도록 제한할 수 있다.

---

## 11. SQS — 큐 기반 비동기 처리

SQS는 Visibility Timeout 설정 하나를 잘못하면 중복 처리 문제가 생긴다.

### Visibility Timeout

메시지를 받으면 다른 컨슈머에게 보이지 않는 시간이다. 처리 시간보다 짧으면 같은 메시지를 여러 컨슈머가 동시에 처리하는 상황이 생긴다. 처리가 30초 걸린다면 Visibility Timeout을 60~90초로 설정한다.

처리 시간이 가변적이면 처리 중에 `ChangeMessageVisibility`를 호출해서 타임아웃을 연장한다.

```bash
# 큐 설정 확인
aws sqs get-queue-attributes \
  --queue-url https://sqs.ap-northeast-2.amazonaws.com/123456789/my-queue \
  --attribute-names VisibilityTimeout,MessageRetentionPeriod,RedrivePolicy
```

### DLQ 설정

처리 실패한 메시지를 별도 큐로 이동하는 설정이다. `maxReceiveCount`를 3으로 설정하면 3번 실패 후 DLQ로 이동한다. DLQ를 설정하지 않으면 실패 메시지가 `MessageRetentionPeriod`(기본 4일)까지 큐에 남아서 정상 메시지 처리를 방해한다.

Standard Queue는 메시지 순서를 보장하지 않는다. 순서가 중요하면 FIFO Queue를 써야 하는데, FIFO는 초당 처리량 제한이 있다.

---

## 12. SNS — 토픽 기반 팬아웃

SNS는 단독보다 SQS나 Lambda와 조합해서 쓴다.

### SNS → SQS 팬아웃

```
이벤트 발행 → SNS Topic
              ├── SQS Queue A (이메일 발송 워커)
              ├── SQS Queue B (푸시 알림 워커)
              └── Lambda (실시간 집계)
```

SQS를 SNS 구독으로 연결하면 SQS 큐에 메시지가 이 형태로 들어온다:

```json
{
  "Type": "Notification",
  "MessageId": "...",
  "TopicArn": "arn:aws:sns:...",
  "Message": "{\"userId\": 123, \"event\": \"order_created\"}"
}
```

`Message` 필드 안에 실제 데이터가 JSON 문자열로 이중 직렬화되어 있다. 컨슈머에서 `body`를 파싱한 후 `Message` 필드를 다시 파싱해야 한다. 이걸 모르고 직접 파싱하려다 실패한다.

구독 필터 정책을 설정하면 특정 조건의 메시지만 각 SQS 큐에 전달할 수 있다. 모든 이벤트를 한 토픽에 발행하고 수신 측에서 필터링하는 패턴이다.

---

## 13. CloudWatch — 로그와 알람

CloudWatch는 로그 보존 기간을 설정하지 않으면 비용 폭탄이 된다.

### 로그 보존 기간

기본값이 "만료 없음"이다. 설정하지 않으면 로그가 영원히 쌓이고 비용이 계속 나온다. 로그 그룹을 만들 때 보존 기간을 같이 설정한다.

```bash
# 보존 기간 없는 로그 그룹 찾기
aws logs describe-log-groups \
  --query 'logGroups[?!retentionInDays].logGroupName' \
  --output text

# 보존 기간 설정 (30일)
aws logs put-retention-policy \
  --log-group-name /ecs/my-app \
  --retention-in-days 30
```

ECS 태스크 정의에서 `awslogs-group`으로 로그 그룹을 지정하는데, 이 로그 그룹이 미리 만들어져 있지 않으면 태스크 시작 시 자동 생성된다. 자동 생성된 로그 그룹은 보존 기간이 없다.

### 알람 설정

```bash
# ALB 5xx 에러율 알람
aws cloudwatch put-metric-alarm \
  --alarm-name "alb-5xx-high" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --dimensions Name=LoadBalancer,Value=app/my-alb/xxxxxxxx \
  --statistic Sum \
  --period 60 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789:alert-topic \
  --treat-missing-data notBreaching
```

`EvaluationPeriods`를 1로 설정하면 순간 스파이크에도 알람이 울린다. 2~3으로 설정해서 연속으로 초과할 때만 알람이 오게 한다. `treat-missing-data`도 신경 써야 한다. 기본값이 `missing`이면 메트릭 데이터가 없을 때 알람 상태로 들어가는 경우가 있다.

---

## 14. Secrets Manager — 비밀값 관리

`.env` 파일을 코드 저장소에 올리거나 EC2 SSH로 들어가 직접 수정하는 방식을 대체한다.

### 애플리케이션에서 사용

```python
import boto3
import json
from functools import lru_cache

@lru_cache(maxsize=1)
def get_db_config():
    client = boto3.client('secretsmanager', region_name='ap-northeast-2')
    response = client.get_secret_value(SecretId='prod/myapp/db')
    return json.loads(response['SecretString'])

# 사용
config = get_db_config()
password = config['password']
```

매 요청마다 Secrets Manager를 호출하면 API 쿼리 비용이 쌓이고 레이턴시도 생긴다. 캐싱해서 재사용한다. AWS SDK에서 제공하는 캐싱 기능을 쓰거나 위처럼 직접 캐싱한다.

### ECS에서 환경 변수로 주입

```json
"secrets": [
  {
    "name": "DB_PASSWORD",
    "valueFrom": "arn:aws:secretsmanager:ap-northeast-2:123456789:secret:prod/myapp/db:password::"
  }
]
```

태스크 시작 시 ECS가 Secrets Manager에서 값을 읽어 환경 변수로 주입한다. 앱 코드에서 AWS SDK를 쓰지 않아도 되고, 비밀값이 태스크 정의에 평문으로 안 들어간다.

### Parameter Store와의 선택

비밀값 하나당 월 비용이 발생한다. 환경이 많아지면 비용이 쌓인다. 자동 교체(Rotation)가 필요한 DB 비밀번호나 API 키는 Secrets Manager, 단순 설정값이나 교체가 필요 없는 값은 Parameter Store 무료 티어를 쓰는 팀이 많다.

---

## 15. WAF — L7 방화벽

WAF는 ALB나 CloudFront 앞에 붙인다. SQL 인젝션, XSS 같은 L7 공격을 차단한다.

### 관리형 규칙

AWS가 제공하는 관리형 규칙 그룹을 쓰면 직접 규칙을 짜지 않아도 된다. `AWSManagedRulesCommonRuleSet`가 가장 기본이다.

처음 WAF를 붙일 때 바로 `BLOCK` 모드로 시작하면 안 된다. `COUNT` 모드로 먼저 달아서 일주일 정도 로그를 확인한다. 정상 요청이 차단 대상으로 잡히는 오탐(false positive)을 파악한 후 규칙을 조정하고 `BLOCK`으로 전환한다.

```bash
# WAF 로그에서 COUNT된 요청 확인
aws logs filter-log-events \
  --log-group-name aws-waf-logs-my-app \
  --filter-pattern '{ $.action = "COUNT" }' \
  --start-time $(date -d '24 hours ago' +%s000) \
  --query 'events[*].message' \
  --output text | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        print(d.get('terminatingRuleId'), d.get('httpRequest', {}).get('uri'))
    except: pass
"
```

### 레이트 리미팅

IP 기반 레이트 리미팅은 모바일 통신사 공유 IP 상황에서 정상 사용자를 막을 수 있다. 전체 IP 레이트 제한보다는 로그인 실패 횟수나 특정 엔드포인트 호출 빈도로 제한하는 게 오탐이 적다.

WAF 요금은 웹 ACL당, 규칙당, 요청 100만 건당 각각 부과된다. 관리형 규칙 그룹을 여러 개 붙이면 비용이 예상보다 많이 나올 수 있다.

---

## 서비스 의존 관계

실제로 서비스를 연결할 때 어떤 순서로 설정해야 하는지 흐름이다.

```
IAM
 └─ 모든 서비스의 접근 제어 (가장 먼저 설계)

VPC
 ├─ EC2, RDS, ECS/Fargate, Lambda (배치 공간)
 └─ 보안 그룹 (서비스 간 통신 제어)

ECR ─── 이미지 저장 ──→ ECS/Fargate (이미지 pull)

ALB ──→ ECS 서비스 (타겟 그룹 연결)
     └→ EC2 (직접 연결 시)

RDS ← ECS/EC2/Lambda (DB 연결)
    ← RDS Proxy (연결 수 관리 필요 시)

Secrets Manager ← ECS 태스크 정의 (비밀값 주입)
                ← Lambda (SDK 호출)

SQS/SNS ← Lambda 트리거
        ← ECS 워커

S3 ← EC2/ECS/Lambda (파일 접근)
   ← CloudFront (정적 자산 배포 시)

CloudWatch ← 모든 서비스 (로그, 메트릭 수집)
           → SNS → 알람 수신

WAF ─→ ALB 앞단
     └→ CloudFront 앞단
```

새 서비스를 추가할 때 연결이 안 되면 순서대로 확인한다.
1. IAM 권한(`AccessDenied` → 역할이나 정책 문제)
2. VPC/보안 그룹(`Connection timeout` → 보안 그룹이나 라우팅 문제)
3. 서비스 설정(각 서비스별 엔드포인트, 리전 확인)

---

## 다음 단계

- **고가용성**: [Multi-AZ](../Cloud/AWS/Database/RDS_Multi_AZ.md), [Auto Scaling](../Cloud/AWS/Compute/Auto_Scaling.md)
- **비용 최적화**: [Savings Plans](../Cloud/AWS/Cost/Savings_Plans.md), [Compute Optimizer](../Cloud/AWS/Cost/Compute_Optimizer.md)
- **심화 네트워킹**: [Transit Gateway](../Cloud/AWS/Network/Transit_Gateway.md), [PrivateLink](../Cloud/AWS/Network/PrivateLink.md)
