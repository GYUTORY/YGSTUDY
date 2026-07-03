---
title: ECS 비용 산정과 절감
tags:
  - AWS
  - ECS
  - Fargate
  - Cost
  - FinOps
updated: 2026-06-17
---

# ECS 비용 산정과 절감

ECS 클러스터 비용이 슬금슬금 오르는데 원인을 못 짚는 경우가 많다. 인스턴스를 줄이자니 트래픽 스파이크가 무섭고, 그대로 두자니 청구서가 부담이다. 이 문서는 Fargate와 EC2 모드의 실비용을 어떻게 계산하는지, 어디서 돈이 새는지, Savings Plans와 Spot을 비용 관점에서 어떻게 섞는지를 다룬다.

base/weight 파라미터의 동작 원리는 [ECS Capacity Providers](ECS_Capacity_Providers.md)에, Spot 회수 대응과 체크포인팅은 [Fargate Spot 운영 심화](Fargate_Spot.md)에, 지표의 Reserved/Utilized 구분은 [ECS Container Insights](ECS_Container_Insights.md)에 정리돼 있다. 여기서는 그 메커니즘을 다시 설명하지 않고 비용 숫자를 잡는 데만 집중한다.

## Fargate 요금이 어떻게 매겨지는가

Fargate는 인스턴스 단위가 아니라 태스크가 점유한 vCPU와 메모리를 **초 단위**로 과금한다. 최소 1분은 보장된다. 서울 리전(ap-northeast-2) 기준 온디맨드 단가는 대략 이렇다(요금은 수시로 바뀌므로 항상 [공식 요금표](https://aws.amazon.com/fargate/pricing/)로 재확인해야 한다).

- vCPU: 시간당 약 $0.04656
- 메모리: GB당 시간당 약 $0.00511

태스크 하나의 시간당 비용은 단순하다.

```
태스크 시간당 비용 = (vCPU 수 × 0.04656) + (메모리 GB × 0.00511)
```

0.5 vCPU / 1GB 태스크를 한 달(730시간) 돌리면:

```
(0.5 × 0.04656 + 1 × 0.00511) × 730
= (0.02328 + 0.00511) × 730
= 0.02839 × 730
≈ $20.7/월
```

이 태스크를 desiredCount 4로 상시 띄우면 약 $83/월이다. 여기에 ALB, NAT Gateway, CloudWatch Logs 수집 비용이 별도로 붙는다. 컴퓨팅만 보면 작아 보여도 NAT Gateway 데이터 처리 요금이 컴퓨팅보다 큰 경우도 흔하다. 비용을 볼 때 Fargate 라인만 보지 말고 같은 서비스가 끌고 오는 부수 비용까지 한 줄에 묶어서 봐야 한다.

태스크 크기는 vCPU와 메모리를 아무 조합으로나 못 정한다. 0.25 vCPU는 0.5~2GB, 1 vCPU는 2~8GB 식으로 조합이 정해져 있다. right-sizing할 때 이 제약 때문에 "메모리만 줄이고 싶은데 CPU 단계가 강제로 같이 내려가는" 상황이 생긴다.

## Fargate vs EC2, 어느 쪽이 싼지 계산해 보기

"Fargate가 비싸다"는 말은 절반만 맞다. 비교는 **인스턴스 점유율(packing)**에 달려 있다.

EC2 모드는 인스턴스 요금을 통째로 낸다. m5.large(2 vCPU, 8GB)가 서울 온디맨드 시간당 약 $0.118이다. 한 달이면 약 $86이다. 이 인스턴스 한 대에 태스크를 얼마나 빽빽하게 채우느냐가 관건이다.

같은 0.5 vCPU / 1GB 태스크를 EC2에 올린다고 하자. m5.large 한 대에 vCPU 기준으로는 4개(2 / 0.5), 메모리 기준으로는 8개(8 / 1)가 들어간다. 둘 중 작은 쪽인 4개가 한 대 한계다. 실제로는 ECS 에이전트와 시스템이 약간 먹으므로 3개 정도로 잡는 게 안전하다.

```
EC2 모드: m5.large 1대에 태스크 3개
대당 $86 → 태스크당 약 $28.7/월

Fargate 모드: 태스크당 약 $20.7/월
```

이 조합에서는 오히려 Fargate가 싸다. 태스크를 빽빽하게 못 채우면 EC2의 "통째 과금"이 손해로 돌아온다. 반대로 인스턴스를 거의 100% 채울 수 있는 워크로드(예: vCPU를 꽉 쓰는 배치 작업, 큰 태스크 여러 개)라면 EC2가 유리해진다.

판단 기준을 이렇게 잡는다.

- 태스크 크기가 작고 수가 들쭉날쭉하다 → Fargate. 인스턴스 관리 비용(패치, AMI, ASG 튜닝)까지 빼면 차이가 더 좁혀진다.
- 큰 태스크를 인스턴스에 꽉 채워 상시 돌린다 → EC2 + Savings Plans 또는 Reserved.
- GPU, 특수 인스턴스 타입, 커스텀 커널 파라미터가 필요하다 → EC2(Fargate는 선택지가 없다).

EC2를 고를 때 잊기 쉬운 비용이 **빈 공간**이다. 인스턴스 점유율이 60%면 나머지 40%는 아무도 안 쓰는데 돈은 나간다. Fargate는 이 빈 공간이 구조적으로 없다(태스크 단위 과금이라). EC2의 절감 효과를 누리려면 bin-packing 배치 전략과 [Container Insights](ECS_Container_Insights.md)로 점유율을 꾸준히 80% 이상 유지해야 한다. 점유율 관리를 안 할 거면 EC2의 단가 우위는 환상이다.

## Fargate Spot으로 컴퓨팅 단가 낮추기

Fargate Spot은 온디맨드 대비 보통 60~70% 싸다. 위의 $20.7/월 태스크가 Spot이면 $6~8/월 수준이다. 회수만 감당할 수 있으면 절감폭이 가장 크다.

Capacity Provider Strategy의 weight를 조정해서 온디맨드와 Spot 비율을 정한다. weight 동작 원리는 [Capacity Providers 문서](ECS_Capacity_Providers.md)에 있고, 여기서는 비용이 어떻게 갈리는지만 본다.

desiredCount 10인 서비스를 예로 든다.

```json
[
  {"capacityProvider": "FARGATE",      "base": 2, "weight": 1},
  {"capacityProvider": "FARGATE_SPOT", "base": 0, "weight": 4}
]
```

base 2는 온디맨드로 고정되고, 나머지 8개를 1:4로 나눠서 대략 온디맨드 4 / Spot 6이 된다. 비용을 계산하면:

```
온디맨드 4개: 4 × 20.7 = $82.8
Spot 6개:     6 × 7   = $42.0
합계: 약 $124.8/월
```

전부 온디맨드(10개)로 돌리면 $207/월이니, 이 구성으로 약 40% 절감이다. base를 0으로 낮추고 weight를 더 Spot 쪽으로 밀면 더 싸지지만, Spot 풀이 동시에 회수되면 살아남는 태스크가 줄어든다. base는 "Spot이 전부 회수돼도 서비스가 죽지 않을 최소 개수"로 잡는다. 절감액과 가용성을 맞바꾸는 다이얼이라고 보면 된다.

가중치를 바꿀 때는 회수율을 같이 봐야 한다. Spot 비율을 70%로 올려놨는데 그 리전·태스크 크기의 회수가 잦으면, 재시작과 ALB 헬스체크 흔들림으로 생기는 운영 비용이 절감액을 갉아먹는다. 회수 빈도를 숫자로 보는 방법은 [Fargate Spot 문서](Fargate_Spot.md)에 있다.

## Compute Savings Plans가 어디까지 덮는가

Compute Savings Plans는 시간당 일정 금액을 1년 또는 3년 약정하고, 그 금액만큼의 온디맨드 사용에 할인을 적용한다. 1년 약정이면 Fargate에 대략 15%, 3년이면 더 큰 할인이 붙는다(할인율은 구간·리전마다 다르므로 Cost Explorer의 추천값으로 확인한다).

커버리지 범위를 정확히 알아야 약정 금액을 잘못 잡지 않는다.

- 덮는다: Fargate 온디맨드, EC2 온디맨드(인스턴스 패밀리·리전 무관), Lambda.
- 안 덮는다: **Fargate Spot, EC2 Spot**. Spot은 이미 할인 가격이라 Savings Plans 대상이 아니다.

여기서 가장 흔한 실수가 Spot 사용량까지 약정에 넣는 것이다. Spot은 Savings Plans와 겹치지 않으니, Spot으로 돌릴 부분을 빼고 **상시 떠 있는 온디맨드 양에만 맞춰** 약정해야 한다. 약정이 실제 온디맨드보다 크면 못 쓴 약정액이 그대로 손실이다. 이 계산을 거꾸로 잡았을 때 생기는 두 방향의 함정은 [Fargate Spot 문서의 "Savings Plans와 Spot을 같이 쓸 때" 절](Fargate_Spot.md)에 자세히 있으니 참고한다.

약정 금액을 잡는 순서는 이렇다.

1. base로 항상 떠 있는 온디맨드 태스크의 시간당 컴퓨팅 비용을 계산한다.
2. 그 금액의 70~80% 정도만 약정한다. 100%를 약정하면 트래픽이 줄어 태스크가 스케일 인할 때 약정이 비게 된다.
3. Cost Explorer의 Savings Plans utilization을 매달 본다. 100% 미만이면 약정이 남는 것이고, 다음 갱신 때 약정을 줄인다.

위의 온디맨드 4개 상시 구성($82.8/월)에 15% Savings Plans를 적용하면 약 $70/월이 된다. Spot 6개는 약정과 무관하게 그대로 $42다. 약정을 살 때 이 $82.8 기준선을 넘기지 않는 게 핵심이다.

## Container Insights 지표로 태스크 right-sizing

비용이 새는 가장 큰 구멍은 태스크에 메모리·CPU를 과하게 잡아둔 것이다. Task Definition에 메모리 2048(2GB)을 박아놨는데 실제로는 700MB만 쓰고 있으면, 나머지 1.3GB는 매시간 돈을 내면서 노는 셈이다.

[Container Insights](ECS_Container_Insights.md)를 켜면 태스크·서비스 단위로 실제 사용량이 나온다. right-sizing은 이 지표에서 시작한다. CloudWatch에서 봐야 할 지표는 다음이다.

- `CpuUtilized` / `CpuReserved`: 실제 쓴 vCPU 대 예약한 vCPU
- `MemoryUtilized` / `MemoryReserved`: 실제 쓴 메모리 대 예약한 메모리

CloudWatch Logs Insights로 최근 2주 사용량의 분포를 뽑는다. 평균만 보면 안 되고 p95, p99를 같이 봐야 한다. 평균이 700MB여도 p99가 1.4GB면 2GB 예약이 과한 게 아니라 적정에 가깝다.

```
fields @timestamp, MemoryUtilized, CpuUtilized
| filter Type = "Task"
| stats avg(MemoryUtilized) as avg_mem,
        pct(MemoryUtilized, 95) as p95_mem,
        pct(MemoryUtilized, 99) as p99_mem,
        avg(CpuUtilized) as avg_cpu,
        pct(CpuUtilized, 99) as p99_cpu
  by bin(1d)
```

right-sizing 기준은 보수적으로 잡는다. p99에 20~30% 헤드룸을 더한 값을 새 예약량으로 정한다. 예를 들어 p99 메모리가 1.1GB면 1.1 × 1.3 ≈ 1.4GB, Fargate 조합 제약에 맞춰 1.5GB나 2GB 중 가까운 쪽으로 내린다. 2GB에서 1GB로 줄이면 메모리 비용이 절반이 되는데, 한 태스크에서는 작아도 desiredCount × 태스크 수로 곱하면 무시 못 할 금액이다.

조심할 점이 몇 가지 있다.

- **OOM 여유는 남겨야 한다.** 메모리를 너무 빡빡하게 줄이면 트래픽 스파이크나 GC 순간에 OOM Killed로 태스크가 죽는다. 죽은 태스크 재시작 비용과 사용자 영향이 절감액보다 크다. 메모리는 p99 + 헤드룸을 지키고, 애매하면 한 단계 위로 둔다.
- **CPU는 burst 특성을 본다.** 평소 0.2 vCPU를 쓰다가 배포·캐시 워밍 순간에 1 vCPU를 치는 워크로드가 있다. 평균만 보고 CPU를 깎으면 그 순간 응답이 느려진다. 이런 워크로드는 max를 기준으로 잡는다.
- **JVM은 힙 외 메모리를 본다.** 컨테이너 메모리는 힙뿐 아니라 메타스페이스, 스레드 스택, 네이티브 메모리를 합한 값이다. `-Xmx`만 보고 예약을 잡으면 모자란다. `MemoryUtilized`(실측)를 기준으로 잡아야 정확하다.

right-sizing은 한 번 하고 끝나는 게 아니라 분기에 한 번씩 다시 본다. 코드가 바뀌면 메모리 프로파일도 바뀐다.

## 과다 프로비저닝된 desiredCount와 min capacity 찾기

태스크 크기를 줄여도, 안 쓰는 태스크를 여러 개 띄워두면 소용없다. 낭비가 가장 잘 숨는 곳이 Service Auto Scaling의 `MinCapacity`와 고정 `desiredCount`다.

흔한 패턴은 이렇다. 처음 서비스를 만들 때 불안해서 desiredCount를 6으로 잡았다. 그 뒤로 트래픽은 평소 2개면 충분한데, 아무도 desiredCount를 다시 안 내렸다. 6개가 1년 내내 떠 있으면서 4개는 거의 노는 중이다.

찾는 방법은 [Container Insights](ECS_Container_Insights.md)의 서비스 단위 지표에서 시작한다.

- `RunningTaskCount`가 항상 `DesiredTaskCount`와 같고 변동이 없다 → Auto Scaling이 안 걸려 있거나 MinCapacity가 너무 높다.
- 서비스 전체 `CpuUtilized` 합이 예약 대비 20% 미만으로 며칠째 깔려 있다 → 태스크 수가 과하다.

Service Auto Scaling 설정에서 봐야 할 값:

```bash
aws application-autoscaling describe-scalable-targets \
  --service-namespace ecs \
  --resource-ids service/my-cluster/my-service
```

`MinCapacity`가 실제 새벽 최저 트래픽보다 높게 잡혀 있으면, 그 차이만큼 매일 밤 낭비다. 새벽에 0건 트래픽인 내부 서비스를 MinCapacity 4로 두는 식의 설정이 자주 보인다. MinCapacity를 트래픽 바닥에 맞춰 1~2로 내리고, 타겟 트래킹 정책(예: CPU 50% 타겟)으로 낮에만 늘어나게 두면 야간 비용이 빠진다.

과다 프로비저닝을 줄일 때 순서는 이렇다.

1. 2주치 `RunningTaskCount`와 서비스 CPU/메모리 사용률을 시간대별로 본다.
2. 트래픽 바닥 시간대의 실제 필요량을 확인하고 MinCapacity를 거기에 맞춘다.
3. 타겟 트래킹으로 스케일 아웃을 맡기되, 스케일 인 쿨다운을 너무 짧게 잡지 않는다(스파이크마다 태스크가 떴다 사라지면 콜드 스타트 비용이 든다).
4. 고정 desiredCount로 운영 중이면 Auto Scaling으로 전환을 검토한다. 변동이 없는 워크로드라면 desiredCount를 실측 필요량으로 낮추는 것만으로 끝난다.

스케줄 기반 스케일링도 같이 본다. 업무 시간에만 트래픽이 있는 사내 서비스라면 [Scheduled Scaling](ECS_Service_Auto_Scaling.md)으로 밤·주말에 태스크를 1개로 줄였다가 아침에 올리는 게 가장 단순하면서 큰 절감이다. 24시간 × 7일을 다 띄울 이유가 없는 서비스가 생각보다 많다.

## 비용을 어디서 확인하나

절감 작업을 했으면 결과를 숫자로 확인해야 한다. 추측으로 "줄었겠지" 하면 안 된다.

- **Cost Explorer**: 서비스별·태그별 일/월 비용 추이. ECS 태스크에 `team`, `service`, `env` 태그를 달아두면 누가 얼마 쓰는지 분해된다. 태그 없이 운영하면 어느 서비스가 비용을 끄는지 영영 모른다.
- **Savings Plans utilization/coverage 리포트**: 약정이 남는지(utilization < 100%) 모자라는지(coverage < 목표) 본다.
- **Container Insights**: 태스크 단위 실사용량. right-sizing 전후 비교의 근거.
- **AWS Cost Anomaly Detection**: 비용이 갑자기 튀면 알림을 준다. 잘못된 배포로 desiredCount가 폭증하거나 로그가 폭주할 때 며칠 안에 잡힌다.

태그 기반 비용 배분(cost allocation tag)을 켜는 데 하루 정도 걸리지만, 이걸 안 해두면 위의 모든 절감 작업이 "체감상 줄었다" 수준에 머문다. 가장 먼저 해둬야 할 작업이다.

## 참고

- [ECS Capacity Providers](ECS_Capacity_Providers.md) — base/weight 동작 원리
- [Fargate Spot 운영 심화](Fargate_Spot.md) — Spot 회수 대응, Savings Plans+Spot 함정
- [ECS Container Insights](ECS_Container_Insights.md) — 실사용량 지표
- [ECS Service Auto Scaling](ECS_Service_Auto_Scaling.md) — 스케일링 정책
- [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [Compute Savings Plans](https://aws.amazon.com/savingsplans/compute-pricing/)
