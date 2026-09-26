---
title: AWS Multi-AZ 고가용성 설계
tags: [aws, cloud, network, backend, architecture]
updated: 2026-09-26
---

## AZ 분산이 필요한 시점

AWS는 리전 내에 물리적으로 분리된 AZ(Availability Zone)를 여러 개 운영한다. 각 AZ는 전력·냉각·네트워크가 독립적이라 한 AZ가 멈춰도 다른 AZ는 영향을 받지 않는다.

ap-northeast-2(서울)는 AZ가 4개다: `ap-northeast-2a`, `ap-northeast-2b`, `ap-northeast-2c`, `ap-northeast-2d`. 실무에서는 a, b, c 세 곳을 주로 쓴다. d는 일부 인스턴스 타입이 제공되지 않아서 나중에 오토스케일링이나 스팟 조달에서 막히는 경우가 있다.

단일 AZ로 운영하다 그 AZ가 죽으면 서비스 전체가 중단된다. 이건 장비 결함, 전력 이상, 네트워크 분리 등 예측 불가능한 원인으로 실제 발생한다. 대응 방법은 하나다 — 컴퓨팅, 데이터베이스, 로드밸런서를 전부 AZ에 나눠 두는 것이다.

## RDS Multi-AZ와 Read Replica

이 둘의 목적은 다르다. 혼동해서 설계하면 돈만 쓰고 가용성도 안 나온다.

**Multi-AZ**는 장애 대응용이다. 프라이머리 인스턴스와 스탠바이 인스턴스가 동기 복제로 항상 같은 상태를 유지한다. 프라이머리가 있는 AZ가 죽으면 AWS가 스탠바이를 프라이머리로 자동 승격시킨다. 이때 DNS 레코드가 스탠바이의 IP로 업데이트되고, 이 과정이 약 60초 걸린다. 애플리케이션은 엔드포인트를 바꿀 필요가 없다.

**Read Replica**는 읽기 분산용이다. 비동기 복제라 약간의 복제 지연이 있다. AZ 장애 시 자동 승격은 없다. 수동으로 `promote`를 실행해야 프라이머리가 되고, 엔드포인트도 직접 바꿔줘야 한다.

| | Multi-AZ | Read Replica |
|---|---|---|
| 복제 방식 | 동기 | 비동기 |
| 장애 자동 전환 | 있음 (~60초) | 없음 (수동) |
| 읽기 트래픽 처리 | 불가 (스탠바이) | 가능 |
| 주목적 | 고가용성 | 읽기 분산 |

Multi-AZ 스탠바이는 읽기 요청을 처리하지 못한다. "어차피 있는 거 읽기도 시키자"는 생각에 스탠바이로 트래픽을 보내려 하면 연결이 거부된다. 읽기 분산이 필요하면 Read Replica를 별도로 만든다.

RDS의 60초 failover는 보장 수치가 아닌 일반적인 경험치다. JDBC URL에 DNS 캐싱이 걸려 있으면 그보다 길어진다. `connectTimeout`, `socketTimeout`을 짧게 잡고 재시도 로직을 넣어야 failover가 끝난 뒤 앱이 구 엔드포인트를 계속 바라보는 상황을 막는다.

## ALB와 AZ 배치

ALB는 생성 시 서브넷을 2개 이상 지정해야 하고, 각 서브넷은 서로 다른 AZ에 있어야 한다. 지정된 AZ 중 하나가 죽으면 ALB는 나머지 AZ로만 트래픽을 흘린다.

서브넷을 2개 AZ에만 두면 한 AZ가 죽었을 때 부하가 살아 있는 AZ 하나에 전부 몰린다. 3개 AZ로 두면 한 곳이 죽어도 남은 두 곳이 나눠서 받는다.

ALB의 cross-zone load balancing은 기본으로 켜져 있다. 타겟이 특정 AZ에 몰려 있어도 ALB가 다른 AZ의 타겟으로 트래픽을 보낸다. 이게 AZ 간 데이터 전송 비용이 쌓이는 주요 원인 중 하나다.

## ECS/Fargate Task AZ 분산

ECS 태스크 배치 전략은 비용 우선이냐 가용성 우선이냐에 따라 선택이 갈린다.

**binpack**: 태스크를 최대한 같은 인스턴스나 AZ에 몰아 넣는다. 인스턴스 수를 줄여 비용을 아끼는 게 목적이다. 해당 AZ가 죽으면 태스크 대부분이 한꺼번에 사라진다.

**spread**: 지정 기준으로 태스크를 분산한다. AZ 기준으로 spread하면 각 AZ에 태스크가 고르게 배치된다.

```json
{
  "placementStrategy": [
    {
      "type": "spread",
      "field": "attribute:ecs.availability-zone"
    }
  ]
}
```

Fargate는 EC2 인스턴스를 직접 관리하지 않으므로 `instanceId` 기준 spread는 의미가 없다. AZ 기준으로만 걸어야 한다.

AZ가 죽으면 그 AZ의 태스크가 종료되고, ECS가 남은 AZ에 즉시 새 태스크를 스케줄한다. 단 태스크가 `RUNNING`으로 올라오는 데 걸리는 시간(이미지 풀, 헬스체크 통과)은 별도로 더해진다. ECR 이미지를 미리 캐시해두면 이 시간을 줄일 수 있다.

## AZ 간 데이터 전송 비용이 쌓이는 패턴

같은 리전 안이라도 AZ를 넘으면 $0.01/GB씩 나온다. 송신 측과 수신 측 각각 과금이라 왕복이면 $0.02/GB다. 트래픽이 많은 서비스에서 이게 청구서에서 예상보다 크게 잡히는 패턴이 세 가지 있다.

**RDS Read Replica와 앱 AZ 불일치**: 앱이 `ap-northeast-2a`에 있고 Read Replica가 `ap-northeast-2c`에 있으면 모든 읽기 쿼리가 AZ를 넘는다. 동일 AZ에 Replica를 하나 더 두거나, 앱을 Replica와 같은 AZ에 배치하면 된다.

**ElastiCache 노드와 앱 AZ 불일치**: Redis 클러스터 노드가 `2b`에 있는데 앱이 `2a`에서 캐시를 읽으면 매 요청이 AZ를 넘는다. 클러스터 모드에서는 각 AZ에 샤드를 배치하고, 클라이언트가 로컬 AZ 노드를 우선 읽도록 설정한다.

**마이크로서비스 간 AZ 혼합 호출**: 서비스 A(`2a`)가 서비스 B(`2b`, `2c`)를 호출하면 절반 요청이 AZ를 넘는다. ALB의 cross-zone 비용을 Cost Explorer에서 모니터링하면 어느 서비스가 주범인지 파악할 수 있다.

## Terraform으로 ap-northeast-2 서브넷 3개 AZ 분산

```hcl
locals {
  azs = ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]

  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
}

resource "aws_subnet" "public" {
  count             = length(local.azs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.public_subnet_cidrs[count.index]
  availability_zone = local.azs[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name = "public-${local.azs[count.index]}"
  }
}

resource "aws_subnet" "private" {
  count             = length(local.azs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnet_cidrs[count.index]
  availability_zone = local.azs[count.index]

  tags = {
    Name = "private-${local.azs[count.index]}"
  }
}

resource "aws_lb" "main" {
  name               = "main-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
}

resource "aws_db_subnet_group" "main" {
  name       = "main-db-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier           = "main-rds"
  engine               = "postgres"
  instance_class       = "db.t3.medium"
  multi_az             = true
  db_subnet_group_name = aws_db_subnet_group.main.name
  # ...
}
```

`count.index`로 azs 리스트를 순회하면 서브넷이 a, b, c에 하나씩 들어간다. `aws_db_instance`의 `multi_az = true`는 AWS가 스탠바이를 다른 AZ에 자동 배치한다. RDS 서브넷 그룹에 3개 AZ 서브넷을 전부 넣어도 되고, AWS가 프라이머리와 스탠바이를 서로 다른 AZ에서 자동으로 고른다.

## AZ 장애 시 서비스별 복구 시간

| 서비스 | Failover 방식 | 소요 시간 |
|---|---|---|
| RDS Multi-AZ | 스탠바이 승격 + DNS TTL 반영 | ~60초 |
| ECS/Fargate 태스크 | 새 태스크 스케줄 후 기동 | 태스크 기동 시간 의존 (보통 30~90초) |
| ALB 타겟 | 헬스체크 제거 후 정상 타겟으로만 라우팅 | 헬스체크 설정에 따라 다름 |
| ElastiCache Multi-AZ | 레플리카 승격 | ~30초 |

ECS 태스크는 즉시 재스케줄이 시작되지만 `RUNNING` 상태까지 올라오는 시간이 붙는다. 이미지 크기가 크거나 헬스체크 시작 주기가 길면 30초가 훌쩍 넘는다. 서비스 desired count를 실 부하보다 여유 있게 잡아두면 AZ 하나가 빠져도 남은 태스크가 트래픽을 감당하는 시간을 벌 수 있다.
