---
title: AWS 리전과 글로벌 서비스의 차이
tags: [aws, cloud, network, cdn, iam]
updated: 2026-09-10
---

# AWS 리전과 글로벌 서비스의 차이

AWS를 처음 쓸 때 가장 헷갈리는 게 서비스마다 콘솔에서 리전 선택이 먹히는 것도 있고 아닌 것도 있다는 점이다. IAM은 리전 드롭다운이 회색이고, CloudFront는 리전 없이 쭉 나오는데, EC2는 리전 바꾸면 목록이 완전히 달라진다. 이 차이의 근거는 AWS 물리 인프라의 계층 구조에 있다.

## AWS 인프라의 세 계층

**리전(Region)**은 지리적으로 분리된 AWS 데이터센터 클러스터다. 서울(ap-northeast-2), 버지니아(us-east-1), 도쿄(ap-northeast-1) 같은 단위다. 리전끼리는 전용 광케이블로 연결되어 있지만 기본적으로 격리된 단위로 동작한다. 리전 간 데이터 복제는 자동으로 일어나지 않는다. S3 Cross-Region Replication이나 RDS Read Replica across regions처럼 명시적으로 설정해야 복제된다.

**가용 영역(AZ)**은 리전 안의 물리적 데이터센터 단위다. 서울 리전(ap-northeast-2)은 현재 4개의 AZ(2a, 2b, 2c, 2d)가 있다. 같은 리전 안의 AZ는 저지연 전용선으로 연결되어 있다. 하나의 AZ가 통째로 내려가도 다른 AZ는 영향받지 않도록 물리적으로 분리되어 있다. EC2 인스턴스, EBS 볼륨, 서브넷이 AZ에 묶인다.

**엣지 로케이션**은 컴퓨트나 스토리지를 제공하지 않는다. CloudFront CDN, Route 53 DNS, WAF, Shield, Global Accelerator의 엔드포인트 역할만 한다. 전 세계 400개 이상에 있고, 사용자와 가장 가까운 엣지에서 트래픽을 처리한 뒤 필요한 경우에만 리전으로 전달한다.

## 서비스 분류

어느 계층에서 동작하는지 모르면 배포 계획을 세울 때마다 계속 찾아봐야 한다. 한 번 정리해 두면 편하다.

| 분류 | 서비스 | 특징 |
|---|---|---|
| 글로벌 | IAM, CloudFront, Route 53, WAF (Global), Shield, Global Accelerator, ACM (CloudFront용) | 리전 선택 없음. AWS 전체에서 단일 인스턴스로 동작 |
| 리전 | EC2, VPC, RDS, ECS, EKS, Lambda, S3 버킷, ELB, SQS, SNS, ACM (리전용) | 리전 안에 생성. 다른 리전에서 직접 참조 불가 |
| AZ 종속 | 서브넷, EBS 볼륨, EC2 인스턴스, ElastiCache 노드, RDS 인스턴스 | 특정 AZ에 고정. AZ 장애 시 직접 영향 |

글로벌 서비스는 ARN에 리전이 빠진다.

```
arn:aws:iam::123456789012:role/MyLambdaRole
arn:aws:cloudfront::123456789012:distribution/ABCDEF123456
```

리전 서비스는 ARN 중간에 리전이 들어간다.

```
arn:aws:lambda:ap-northeast-2:123456789012:function:MyFunction
arn:aws:rds:ap-northeast-2:123456789012:db:my-database
```

S3는 조금 특수하다. 서비스 자체는 글로벌하게 보이지만 버킷은 리전 종속이다. `ap-northeast-2`에 만든 버킷의 데이터는 물리적으로 서울에 있다. 다른 리전에서 접근하면 AWS 내부 WAN을 경유한다. 글로벌 서비스처럼 보이지만 데이터 위치는 리전에 묶여 있다.

## 리전 선택에서 따져봐야 할 것들

레이턴시만 보고 리전을 고르는 경우가 많은데, 실제로는 네 가지를 같이 봐야 한다.

**레이턴시**는 사용자가 주로 어디 있느냐의 문제다. 한국 사용자만 쓴다면 서울(ap-northeast-2)이 맞다. 전 세계 사용자가 있다면 CloudFront나 Global Accelerator를 앞에 두고 오리진은 주요 사용자 위치 기준 리전에 두는 구조가 된다.

**데이터 주권**은 금융, 헬스케어, 공공 서비스에서 법적 요구사항이다. 한국 금융 데이터는 한국에 있어야 한다는 규정이 있으면 서울 리전 외에 선택지가 없다. AWS는 Cross-Region Replication을 명시적으로 설정하지 않는 한 데이터가 리전 밖으로 나가지 않는다고 보장한다.

**서비스 가용성 차이**는 생각보다 자주 걸린다. 새 서비스나 인스턴스 타입이 us-east-1에는 있고 ap-northeast-2에는 몇 달 뒤에 들어오는 경우가 있다. 특정 Graviton 기반 인스턴스나 RDS 엔진 버전이 서울에 아직 없는 경우가 실제로 있었다. 아키텍처 설계 전에 필요한 서비스가 해당 리전에 있는지 확인해야 한다.

**요금 차이**도 무시하기 어렵다. 같은 EC2 인스턴스 타입이라도 리전에 따라 10~25% 차이가 난다. us-east-1이 대체로 가장 싸고, 서울, 도쿄, 유럽 순으로 비싸지는 경향이 있다. 데이터 전송 요금도 리전마다 다르다.

## 실제로 빠진 함정들

### CloudFront용 ACM 인증서는 us-east-1

CloudFront에 HTTPS를 붙이려면 ACM 인증서가 필요한데, **반드시 us-east-1 리전에서 발급해야 한다.** CloudFront가 글로벌 서비스고, ACM 인증서를 us-east-1에서만 참조한다는 제약이 있다.

ap-northeast-2에서 인증서를 발급하면 CloudFront 콘솔에서 인증서 선택 드롭다운에 아무것도 나오지 않는다. 처음 겪으면 인증서 발급 자체가 잘못된 줄 알고 다시 발급한다. DNS 검증을 다 마친 인증서인데 CloudFront에서 보이지 않으면 리전 확인부터 한다.

```bash
# ap-northeast-2에서 발급한 경우 — CloudFront에서 선택 불가
aws acm request-certificate \
  --domain-name "example.com" \
  --validation-method DNS \
  --region ap-northeast-2

# us-east-1에서 발급해야 CloudFront와 연결된다
aws acm request-certificate \
  --domain-name "example.com" \
  --validation-method DNS \
  --region us-east-1
```

Terraform에서 CloudFront를 프로비저닝할 때는 provider alias로 us-east-1을 명시해야 한다.

```hcl
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

resource "aws_acm_certificate" "cloudfront_cert" {
  provider          = aws.us_east_1
  domain_name       = "example.com"
  validation_method = "DNS"
}

resource "aws_cloudfront_distribution" "main" {
  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate.cloudfront_cert.arn
    ssl_support_method  = "sni-only"
  }
  # ...
}
```

WAF도 같은 제약이 있다. CloudFront에 붙이는 WAF WebACL은 us-east-1에 만들어야 한다. ALB에 붙이는 WAF는 ALB와 같은 리전에 만든다.

### IAM이 리전별로 나뉘지 않는 이유

IAM 사용자, 역할, 정책은 글로벌이다. 서울 리전의 EC2가 S3에 접근하든, 도쿄 리전의 Lambda가 DynamoDB에 접근하든 같은 IAM 역할을 쓸 수 있다. 리전마다 역할을 따로 만들 필요가 없다.

IAM 정책 ARN에 리전 표시가 없는 것도 이 때문이다.

```
arn:aws:iam::123456789012:role/MyLambdaRole
# 서비스 다음 자리(리전 부분)가 비어 있다
# arn:aws:서비스:리전:계정:리소스
```

IAM 정책으로 특정 리전 리소스만 허용하려면 Resource ARN에 리전을 명시하거나, Condition 블록에 `aws:RequestedRegion`을 쓴다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ["ap-northeast-2"]
        }
      }
    }
  ]
}
```

단, `aws:RequestedRegion` 조건은 글로벌 서비스(IAM, CloudFront, Route 53)에는 적용되지 않는다. IAM 자체는 리전 개념이 없으니 리전 조건으로 IAM 작업을 막을 수 없다.

### S3 버킷이 리전에 묶이는 문제

S3 버킷 URL은 글로벌하게 보인다. `https://my-bucket.s3.amazonaws.com` 같은 형태라 리전 개념이 없어 보이지만, 버킷 자체는 특정 리전에 존재한다.

서울에 있는 EC2에서 us-east-1의 S3 버킷을 읽으면 리전 간 데이터 전송이 발생한다. 레이턴시가 200~300ms씩 나오는 경우가 있다. 같은 리전이면 10ms 안이다. 리전 간 데이터 전송 요금도 추가로 붙는다. 버킷 위치와 접근 위치가 다를 때 비용이 어떻게 나올지 미리 계산해 두지 않으면 요금 고지서에서 놀라게 된다.

멀티리전에서 같은 데이터를 빠르게 읽어야 하면 선택지가 있다.

- **S3 Multi-Region Access Point**: AWS가 자동으로 가장 가까운 리전 버킷으로 라우팅. 복제 설정을 함께 해야 한다.
- **CloudFront + S3**: 엣지 캐싱으로 반복 요청 레이턴시를 줄인다. 자주 안 바뀌는 정적 콘텐츠에 맞다.
- **S3 Cross-Region Replication**: 각 리전에 버킷을 두고 변경사항을 비동기로 복제한다. 읽기 레이턴시는 줄지만 쓰기 일관성 문제를 직접 처리해야 한다.

어느 방법을 쓰든 버킷이 리전에 묶여 있다는 사실 자체는 변하지 않는다. 글로벌하게 보이는 API 뒤에서 데이터가 어디에 있는지를 신경 써야 하는 서비스다.
