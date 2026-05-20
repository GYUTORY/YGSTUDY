---
title: ECS Task Placement
tags: [aws, ecs, ec2, placement-strategy, placement-constraint, fargate]
updated: 2026-05-20
---

# ECS Task Placement

## 개요

ECS EC2 launch type을 쓰는 순간 따라오는 질문이 있다. "지금 띄우려는 task가 클러스터 안의 어느 EC2 인스턴스에 들어갈 것인가." 이 결정을 내리는 메커니즘이 Task Placement다. Placement는 두 축으로 동작한다. 후보 인스턴스를 걸러내는 **constraint**, 그리고 걸러진 인스턴스 중에서 우선순위를 매기는 **strategy**. ECS 스케줄러는 두 가지를 순서대로 적용해서 최종 배치 인스턴스를 고른다.

배치 순서를 정리하면 이렇다.

1. CPU·메모리·포트·ENI 같은 리소스 요구사항으로 1차 필터링
2. 사용자가 지정한 placement constraint로 2차 필터링
3. placement strategy 우선순위에 따라 남은 인스턴스를 정렬
4. 가장 앞에 오는 인스턴스에 task 배치

이 흐름을 이해하지 못하면 "왜 분명 자리가 있는데 task가 PROVISIONING에서 안 넘어가지?" 라는 의문이 풀리지 않는다. 대부분의 경우는 1번이나 2번 단계에서 후보가 0개로 떨어지는 상황이다.

Fargate는 이 페이지의 거의 모든 내용이 해당되지 않는다. Fargate는 인스턴스라는 개념 자체가 없어서 placement strategy 입력이 들어와도 무시한다. 단, AZ 간 spread는 ECS가 기본으로 적용한다. 이 부분은 마지막 절에서 따로 다룬다.

## Placement Strategy 세 종류

### binpack

남는 자원이 적은 인스턴스부터 채워 넣는 방식이다. 옵션으로 `cpu` 또는 `memory`를 지정한다.

```json
{
  "placementStrategy": [
    { "type": "binpack", "field": "memory" }
  ]
}
```

`field: memory`라면 "메모리 여유가 가장 적게 남는 인스턴스부터 우선 채운다"는 의미다. 결과적으로 인스턴스 한 대를 거의 꽉 채우고 나서야 다음 인스턴스가 동원된다. ECS Capacity Provider의 managed scaling과 같이 쓰면 비어 있는 인스턴스가 빨리 만들어지고, scale-in 단계에서 비어 있는 인스턴스를 빠르게 정리할 수 있다. 그래서 비용 최적화 맥락에서 가장 자주 보이는 선택지다.

함정은 가용성이다. 메모리 집약 워크로드 30개를 binpack:memory로 3개 인스턴스에 몰아 넣었다고 하자. 인스턴스 한 대가 죽으면 task 10개가 한꺼번에 사라진다. 게다가 사라진 10개를 다시 띄우려면 남은 두 대에 여유가 있어야 하는데, 이미 binpack 결과로 다 채워져 있으니 자리가 없다. ASG가 새 인스턴스를 띄울 때까지 desiredCount를 못 맞춘다. 비용은 줄였지만 단일 인스턴스 장애가 곧 전체 장애로 번지는 구조다. 실제 운영에서 binpack을 단독으로 쓰는 경우는 드물고, spread와 조합해 가용성 하한을 만들어 둔다.

### spread

지정한 필드 기준으로 가능한 한 고르게 분산시킨다. field에는 다음이 들어간다.

- `attribute:ecs.availability-zone` — AZ 단위 분산. 가용성 확보의 표준
- `instanceId` — 인스턴스 한 대당 task 1개씩 우선 배치
- `host` — `instanceId`와 동일
- 사용자 정의 attribute — 인스턴스에 붙여둔 임의 태그 기준 분산

```json
{
  "placementStrategy": [
    { "type": "spread", "field": "attribute:ecs.availability-zone" },
    { "type": "spread", "field": "instanceId" }
  ]
}
```

이 조합이 EC2 launch type의 사실상 기본 설정이다. ECS는 명시하지 않아도 서비스 스케줄러 단에서 AZ spread를 우선 시도하는데, 그래도 명시적으로 적어두는 편이 안전하다. ECS 콘솔에서 service replica 타입을 고르면 위 두 줄이 자동으로 들어간다.

주의할 점은 spread가 "엄격한 균등 배치"가 아니라는 것이다. 후보 인스턴스 중 가장 task 수가 적은 쪽을 고를 뿐이다. AZ-a에 task 4개, AZ-b에 3개, AZ-c에 3개인 상태에서 새 task가 들어오면 AZ-b 또는 AZ-c로 간다. 그런데 AZ-c 인스턴스에 자리가 없으면 그냥 AZ-b로 흘러간다. 결과적으로 AZ-c가 비어버리는 경우가 종종 보인다. AZ별 인스턴스 수가 처음부터 비대칭이면 spread도 비대칭이 된다.

### random

말 그대로 무작위다. 후보 인스턴스 중에서 임의로 하나를 고른다. 테스트 환경이나, 배치 결과가 비결정적이어도 되는 단기 job에 쓴다. 운영 서비스에 단독으로 쓸 일은 거의 없다.

## Placement Strategy 조합과 우선순위

strategy는 배열로 여러 개를 넣을 수 있고, 앞에 적힌 항목부터 우선순위가 높다. ECS는 첫 번째 strategy로 후보를 정렬해서 동률을 만들어낸 뒤, 동률이 풀리지 않는 경우에만 두 번째 strategy로 타이브레이커를 적용한다.

운영에서 가장 자주 쓰는 조합은 이런 모양이다.

```json
{
  "placementStrategy": [
    { "type": "spread",  "field": "attribute:ecs.availability-zone" },
    { "type": "binpack", "field": "memory" }
  ]
}
```

먼저 AZ별로 균등 분산해서 가용성을 확보하고, 같은 AZ 내에서는 binpack으로 인스턴스를 채워 비용을 줄이는 의도다. "AZ 분산은 양보 못 하지만, 그 안에서는 최대한 빽빽하게" 가 한 줄 요약이다.

순서를 바꾸면 의미가 완전히 달라진다. binpack을 먼저 두면 ECS는 메모리가 가장 적게 남은 인스턴스부터 채우는 정렬을 적용하고, 그 안에서 AZ가 같은 인스턴스가 여러 개 동률로 나오는 경우에만 AZ spread를 본다. 인스턴스 자원 점유가 불균등한 상태에서는 동률 자체가 거의 안 생기므로 사실상 AZ spread가 무시된다. AZ-a에 task가 몰리는 결과가 나온다.

strategy를 5개까지 쌓을 수 있지만, 실제로 3개를 넘기면 결과를 머릿속에서 추적하기 어렵다. AZ spread + binpack 두 줄로 충분한 경우가 대부분이다.

## Placement Constraint

constraint는 후보 인스턴스를 아예 걸러내는 필터다. strategy는 "정렬"이지만 constraint는 "탈락"이다. 두 가지 타입이 있다.

### distinctInstance

같은 service의 task가 한 인스턴스에 두 개 이상 안 들어가게 강제한다.

```json
{
  "placementConstraints": [
    { "type": "distinctInstance" }
  ]
}
```

ENI 모드를 trunking 없이 쓰는 환경에서, EC2 한 대당 ENI 슬롯이 빠르게 고갈되는 걸 피하려고 강제로 한 대당 task 1개로 묶는 식의 활용이 있다. 또 다른 패턴은 stateful 워크로드 — 같은 호스트에 같은 service의 task가 둘 들어가면 EBS 마운트나 로컬 포트가 충돌하는 경우다.

함정은 분명하다. desiredCount가 10인데 클러스터에 인스턴스가 7대뿐이면 task 3개는 영원히 못 뜬다. ASG에 capacity provider managed scaling을 붙여뒀어도, managed scaling은 "리소스 부족"을 트리거로 스케일 아웃하지 "constraint 불만족"은 트리거로 잡지 않는다. 결국 task가 PROVISIONING에 박혀 있고 인스턴스는 안 늘어나는 상태가 발생한다. distinctInstance를 쓸 거면 ASG의 minimum size를 desiredCount 이상으로 미리 올려두거나, 별도 알람으로 인스턴스를 증설해야 한다.

### memberOf

쿼리 언어 표현식을 만족하는 인스턴스만 후보로 남긴다. ECS의 cluster query language를 쓴다.

```json
{
  "placementConstraints": [
    {
      "type": "memberOf",
      "expression": "attribute:ecs.instance-type == c5.xlarge"
    }
  ]
}
```

기본 attribute로 자주 쓰는 것들이다.

- `ecs.instance-type` — `c5.xlarge`, `m5.2xlarge` 같은 인스턴스 타입
- `ecs.availability-zone` — `ap-northeast-2a` 같은 AZ
- `ecs.os-type` — `linux`, `windows`
- `ecs.ami-id` — AMI ID
- `ecs.cpu-architecture` — `x86_64`, `arm64`

연산자는 `==`, `!=`, `>`, `<`, `in`, `not_in`, `=~`, `and`, `or`를 지원한다. 정규식까지 들어가서 표현력은 충분히 넓다. GPU 워크로드를 `g5.xlarge`에만 띄우는 케이스, ARM 빌드를 `arm64` 인스턴스로 격리하는 케이스, AZ 한쪽으로 만 임시 격리하는 케이스가 대표적이다.

```json
{
  "expression": "attribute:ecs.cpu-architecture == arm64 and attribute:ecs.instance-type =~ c7g.*"
}
```

사용자 정의 attribute도 거의 같은 방식으로 동작한다. ECS Container Agent의 `ECS_INSTANCE_ATTRIBUTES` 환경변수, 또는 `put-attributes` API로 인스턴스에 `workload=gpu-inference` 같은 키-값을 붙여두면 expression에서 `attribute:workload == gpu-inference`로 참조한다. 인스턴스 타입에 묶지 않고 워크로드 의도를 직접 표현할 수 있어서, 인스턴스 타입을 바꿔도 service 정의를 안 건드려도 된다.

### Task Definition 레벨 constraint vs Service 레벨 constraint

constraint는 두 군데에 넣을 수 있다. Task Definition에 적으면 그 task가 어디서 실행되든 따라다닌다. Service에 적으면 그 service의 task에만 적용된다. 같은 task definition을 여러 service가 공유하는데 service별로 배치 위치를 다르게 하고 싶다면 service 레벨에 넣는다. 두 레벨이 동시에 지정되면 AND로 결합된다 — 하나라도 만족 안 하는 인스턴스는 탈락한다.

## Fargate의 동작

Fargate는 EC2 인스턴스가 사용자 시야 밖에 있다. 그래서 placement strategy를 정의해도 API가 받아주는 척만 하고 실제 배치 로직에 들어가지 않는다. AWS 문서에 "Fargate는 placement strategy와 constraint를 지원하지 않는다"고 적혀 있는데, 정확히는 "사용자 입력이 무시된다" 쪽이 현실에 가깝다.

다만 가용성 측면에서 한 가지 보장은 있다. Fargate 서비스의 task는 ECS 스케줄러가 자동으로 AZ 간 spread를 시도한다. desiredCount가 3이고 service가 3개 AZ에 걸친 subnet을 가지고 있다면 AZ별로 1개씩 배치된다. 이건 사용자 설정이 아니라 ECS 내부 동작이라 끌 수도 없고 강화할 수도 없다.

`distinctInstance` 같은 constraint는 Fargate에서 아예 의미가 없다. Fargate task는 각자 독립된 micro-VM 위에서 도니까 "다른 인스턴스" 조건이 사실상 항상 만족된다. memberOf 표현식 중 `ecs.os-type`이나 `ecs.cpu-architecture` 정도는 task definition의 `runtimePlatform` 필드로 동등한 통제가 가능하니, Fargate에서는 그쪽을 본다.

## 실무에서 자주 만나는 함정

### binpack으로 묶다가 동시 장애

앞서 잠깐 언급한 케이스. 메모리 8GB짜리 task 12개를 `m5.4xlarge`(메모리 64GB) 인스턴스 2대에 binpack으로 꽉 채워 넣었다. 인스턴스 비용이 거의 절반으로 줄어서 한동안 좋아 보였는데, 한 대가 NodeNotReady로 빠지자 task 6개가 한꺼번에 사라졌다. ECS 서비스가 desiredCount 12를 맞추려고 재배치를 시도했지만, 남은 한 대에 자리가 없어서 ASG 스케일 아웃을 기다려야 했다. ASG가 새 인스턴스를 띄우고 ECS 에이전트가 등록되기까지 4분 정도 걸렸고, 그동안 서비스 처리량이 절반으로 떨어졌다.

여기서 얻은 교훈은 두 가지였다. 첫째, binpack 앞에 AZ spread를 반드시 둔다. 둘째, capacity provider의 `targetCapacity`를 100으로 두지 말고 80~90 정도로 낮춘다. ECS가 인스턴스 점유율 80%를 유지하도록 동작하니, 한 대가 빠져도 다른 인스턴스에 즉시 재배치할 여유가 생긴다.

### distinctInstance와 ASG 사이즈 불일치

ALB 뒤에 붙은 service의 desiredCount를 평소 6에서 트래픽 증가 대비 12로 올렸다. 그런데 task 6개가 PROVISIONING에서 30분 넘게 멈춰 있었다. service에 `distinctInstance` 제약이 걸려 있었고, 클러스터의 EC2 인스턴스는 6대뿐이었다. capacity provider managed scaling이 동작하려면 "리소스 부족으로 task가 PROVISIONING에 쌓임" 신호가 필요한데, 이 신호는 CPU·메모리 부족에 반응할 뿐 constraint 위반에는 반응하지 않는다. 결국 ASG는 수동으로 사이즈를 12로 올린 뒤에야 task가 정상 배치됐다.

distinctInstance는 그 자체로 잘못된 선택이 아니다. 다만 desiredCount와 ASG의 desired/min capacity가 늘 함께 움직여야 한다는 부가 조건이 따라온다. service auto scaling이 desiredCount를 동적으로 바꾼다면, ASG의 min capacity도 같은 알람으로 함께 올라가도록 묶어둬야 한다.

### memberOf로 인스턴스 타입을 박아두고 잊어버림

ML 추론 service의 task definition에 `ecs.instance-type == g4dn.xlarge` 제약을 걸어뒀다. 한참 뒤 g4dn 재고가 부족한 시점에 service가 scale-out을 시도했는데 task가 안 떴다. ASG의 instance type 후보에는 g5도 들어 있어서 인스턴스 자체는 잘 늘어났는데, ECS는 g5 인스턴스를 후보에서 떨어뜨렸다. expression이 instance-type을 직접 박아뒀기 때문이다.

이 경험 이후로는 인스턴스 타입을 직접 박는 대신 사용자 정의 attribute(`workload=gpu`)를 써서 의도를 표현하고, 어떤 instance type을 GPU 노드로 쓸지는 ASG의 launch template과 instance attribute 자동 부여 스크립트에서 결정하도록 분리했다. expression이 인프라 구현과 결합되지 않게 한 단계 떨어뜨리는 셈이다.

### spread가 비대칭이 되는 경우

AZ-a, AZ-b, AZ-c 각각에 EC2 5대씩 두고 spread:availability-zone으로 task 30개를 배치했다. 처음에는 AZ별 10개씩 잘 나뉘었다. 그런데 운영 중 AZ-c 인스턴스 두 대가 spot interruption으로 빠졌고, 남은 AZ-c 용량이 부족해지자 신규 task가 AZ-a와 AZ-b로만 몰렸다. ECS는 "spread를 위해 task를 거부"하지 않고 "spread를 위해 우선순위만 매긴다". 후보가 한쪽에만 있으면 spread 의도와 무관하게 한쪽으로 간다.

해결은 두 가지였다. 하나는 capacity provider의 managed scaling이 AZ 별 균형을 맞추도록 ASG에 `availability-zone-distribution: balanced-best-effort`를 설정한 것. 다른 하나는 spread 비대칭을 CloudWatch metric으로 노출해서, 일정 임계치를 넘으면 알람으로 사람이 개입하게 한 것. spread는 강제 보장이 아니라 우선순위라는 점을 metric으로 항상 확인하는 셈이다.

## 디버깅 흐름

task가 안 뜨거나 이상한 인스턴스에 배치된다면 다음 순서로 본다.

`describe-tasks`로 stoppedReason 확인이 먼저다. "no container instances were found in your cluster" 메시지는 1차 필터링 — 즉 CPU·메모리·ENI 같은 리소스 요건을 만족하는 인스턴스가 0개라는 뜻이다. 이때 placement constraint·strategy는 무관하다. 인스턴스 자원이나 ENI 슬롯을 본다.

같은 메시지가 떠도 리소스에는 여유가 있어 보인다면 constraint를 의심한다. `aws ecs list-container-instances`로 후보 인스턴스를 보고, 각 인스턴스의 attribute를 `describe-container-instances`로 확인한다. expression에 적은 attribute가 실제 인스턴스에 붙어 있지 않은 경우가 흔하다. user data 스크립트에서 attribute를 설정하는데 EC2 부팅 타이밍에 실패한 경우, 또는 콘솔에서 ASG를 새로 만들면서 attribute 설정을 빼먹은 경우다.

배치는 됐는데 의도와 다른 분포라면 strategy 순서를 본다. binpack과 spread 순서가 뒤집혀 있지 않은지, AZ spread 다음에 instanceId spread가 빠져 있지 않은지 확인한다. ECS는 strategy 평가 과정을 외부로 노출하지 않으므로, 실제 배치 결과를 ECS Cluster의 task 분포로 직접 확인하는 방법밖에 없다. CloudWatch Container Insights에 task의 AZ·instance ID 차원을 추가해두면 평소 분포를 모니터링하기 편하다.
