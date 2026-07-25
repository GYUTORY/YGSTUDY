---
title: AWS Savings Plans
tags: [aws, cost, savings-plans, reserved-instances, ec2, fargate, lambda, organizations]
updated: 2026-07-25
---

# AWS Savings Plans

1년 또는 3년 약정으로 시간당 최소 사용량을 달러 단위로 약정하면 On-Demand 대비 최대 72% 할인을 받는 방식이다. Reserved Instances(RI)와 달리 특정 인스턴스 유형을 고정하지 않아도 된다.

## Reserved Instances와 구조적 차이

RI는 인스턴스 단위 예약이다. `m5.large`를 예약했으면 그 타입으로 써야만 할인이 붙는다. 타입을 바꾸거나 리전을 이동하면 예약분은 그냥 낭비된다.

Savings Plans는 "시간당 $X 이상 쓰겠다"는 금액 단위 약정이다. 인스턴스 타입을 바꿔도, 크기를 조정해도 약정 금액 내라면 할인이 자동으로 붙는다. 운영 중에 인스턴스 유형을 자주 바꾸는 팀이라면 RI보다 Savings Plans 쪽이 관리가 훨씬 단순하다.

둘의 결정적인 차이는 적용 대상 서비스다. RI는 EC2, RDS, ElastiCache, OpenSearch, Redshift 각각을 서비스별로 별도 예약해야 한다. Compute Savings Plans 하나로 EC2, Fargate, Lambda까지 한 번에 커버된다.

결제 방식은 둘 다 동일하다. All Upfront(전액 선납), Partial Upfront(일부 선납), No Upfront(선납 없음) 중 선택한다. 선납 비율이 높을수록 할인율이 올라간다.

"Savings Plans 하나로 전부 해결된다"고 오해하는 경우가 있는데, RDS나 ElastiCache처럼 Savings Plans가 적용되지 않는 서비스는 여전히 RI를 써야 한다.

| 구분 | Savings Plans | Reserved Instances |
|---|---|---|
| 약정 단위 | 시간당 금액 ($) | 인스턴스 수량 |
| 적용 서비스 | EC2, Fargate, Lambda, SageMaker | EC2, RDS, ElastiCache, OpenSearch, Redshift 등 |
| 인스턴스 유형 변경 | 자유 (플랜 종류에 따라 다름) | 패밀리·리전 고정 |
| 최대 할인율 | 72% (EC2 Instance SP) | 75% (EC2 Convertible RI 제외) |

## 플랜 유형별 차이

### Compute Savings Plans

EC2, Fargate, Lambda 전부 적용된다. 인스턴스 패밀리, 리전, OS, 테넌시를 고정하지 않아도 된다.

할인율은 최대 66%로 세 종류 중 가장 낮지만, 유연성이 가장 높다. 아키텍처를 자주 바꾸거나 멀티 리전 운영을 하는 경우에 선택한다.

Fargate와 Lambda 적용 범위는 조금 다르다. Fargate는 vCPU 시간과 메모리 GB-시간 단위로 할인이 들어간다. Lambda는 GB-초(메모리 × 실행 시간) 단위로 적용되는데, 요청당 과금(월 100만 건 이후 $0.20/백만 건)은 할인 대상이 아니다. Lambda 비용이 대부분 실행 시간에서 나오는지, 요청 수에서 나오는지 먼저 구분해야 계산이 맞는다.

### EC2 Instance Savings Plans

인스턴스 패밀리와 리전을 지정해야 한다. `us-east-1`의 M 패밀리로 약정하면 `m5.large`, `m5.xlarge`, `m6i.large` 등 M 계열이면 크기와 세대가 달라도 할인이 적용된다. OS나 테넌시는 바꿀 수 있다.

할인율은 최대 72%로 세 종류 중 가장 높다. 특정 리전에서 특정 인스턴스 패밀리를 장기적으로 운영하는 게 확실한 서비스라면 절감 효과가 크다.

Fargate에는 적용되지 않는다. Fargate를 주요 워크로드로 운영하는 팀이 EC2 Instance SP를 구매하면 Fargate 비용은 그대로 On-Demand로 나간다. 이 차이를 모르고 구매하는 사례가 꽤 있다.

### SageMaker Savings Plans

SageMaker 워크로드 전용이다. 인스턴스 패밀리, 크기, 리전, SageMaker 컴포넌트(Training, Inference, Processing 등) 구분 없이 적용된다. 할인율은 최대 64%.

ML 파이프라인을 상시 운영하는 팀만 해당된다. 간헐적으로 쓰는 경우에는 약정 금액을 채우지 못해 오히려 손해가 난다.

## RI와 혼용 시 적용 우선순위

RI와 Savings Plans를 동시에 보유하는 경우가 있다. 적용 순서는 RI가 먼저 들어간다. RI로 커버되지 않는 사용량에 Savings Plans가 적용된다. 두 할인 모두 소진되면 나머지는 On-Demand로 과금된다.

이 순서를 모르고 중복 구매하면 약정을 다 소화하지 못하는 상황이 생긴다. `m5.large 10대`를 RI로 예약해두고 Compute Savings Plans도 구매했는데 실제로 `m5.large`만 10대 쓴다면 RI가 전부 커버하므로 Savings Plans 약정 금액이 남아도는 상태가 된다. Savings Plans 잔여 약정은 버려지지 않고 다른 인스턴스 사용량에 자동 적용되지만, 커버 범위가 겹치면 실질 절감률이 기대보다 낮아진다.

RI 만료 시점에 맞춰 Savings Plans로 전환하거나, 새 워크로드에는 Savings Plans만 쓰고 기존 RI는 만료까지 유지하는 식으로 분리하는 게 낫다.

## 약정 금액 계산 방법

약정 금액 계산의 핵심은 현재 On-Demand 지출에서 안정적인 기저 사용량(baseline)만 잡아내는 것이다. 최댓값 기준으로 잡으면 트래픽이 줄어드는 시기에 약정을 소화하지 못한다.

**1단계: 최근 3개월 일별 On-Demand 비용 확인**

Cost Explorer에서 Savings Plans가 적용되지 않은 On-Demand 사용량만 따로 뽑는다. 일별로 보면 주중/주말 차이, 배포 주기, 이벤트성 스파이크가 보인다. 이 중 가장 낮은 날의 값이 안정적인 기저 사용량이다.

**2단계: 기저 사용량에서 시간당 비용 산출**

일별 On-Demand 기저 비용이 $240이면 시간당으로 나누면 $10/hr이다. 이 값이 약정 후보의 상한이다.

**3단계: 약정 비율 조정**

일별 최저값의 70~80% 수준에서 시작한다. 기저가 $10/hr이면 처음 약정은 $7~$8/hr로 잡는다. 나머지 $2~$3/hr은 On-Demand로 두면 트래픽 급증 시에도 비용이 폭발하지 않는다. 운영 이력이 쌓이면 Coverage 리포트를 보면서 조금씩 올린다.

커버리지(Coverage)가 90%를 넘기면 과도한 약정일 수 있다. 사용량이 줄어드는 시기에 약정을 다 소화 못 하면 그만큼 손해다.

```bash
# 최근 30일 On-Demand 일별 비용 조회
aws ce get-cost-and-usage \
  --time-period Start=2026-06-25,End=2026-07-25 \
  --granularity DAILY \
  --metrics AmortizedCost \
  --filter '{"Dimensions":{"Key":"PURCHASE_TYPE","Values":["On Demand"]}}' \
  --query 'ResultsByTime[*].[TimePeriod.Start,Total.AmortizedCost.Amount]' \
  --output table

# Savings Plans 추천 조회 (60일 이력 기반)
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days SIXTY_DAYS

# 현재 Savings Plans 사용률 조회
aws ce get-savings-plans-utilization \
  --time-period Start=2026-07-01,End=2026-07-25

# Savings Plans 커버리지 조회
aws ce get-savings-plans-coverage \
  --time-period Start=2026-07-01,End=2026-07-25 \
  --granularity MONTHLY
```

Cost Explorer의 Savings Plans → Recommendations 화면에서 추천 금액을 확인할 수도 있다. 최소 14일간의 사용 이력 데이터가 쌓여야 의미 있는 추천이 나온다. 추천 금액을 그대로 따를 필요는 없다. 현재 On-Demand 지출의 70~80% 수준에서 시작하는 게 안전하다.

## Organizations 멀티 계정 적용

AWS Organizations 환경에서 payer(결제 마스터) 계정에서 Savings Plans를 구매하면 linked account 전체에 할인이 공유된다. 반대로 linked account에서 개별 구매하면 그 계정에만 적용된다.

공유 방식이 중요한 이유는 약정 활용률 때문이다. 계정별로 따로 구매하면 A 계정은 사용량이 초과하고 B 계정은 약정이 남는 상황이 생긴다. payer 계정에서 하나로 구매하면 AWS가 모든 linked account의 사용량을 합산해서 할인을 배분한다.

적용 방식은 두 가지다.

**sharing on (기본값):** payer 계정의 Savings Plans가 모든 linked account의 사용량에 자동 적용된다. 비용 배분 리포트는 각 계정별로 절감액이 표시된다.

**sharing off:** 각 계정이 자신의 약정만 사용한다. 팀별 비용 책임을 엄격히 구분하는 경우에 쓴다. 공유를 끄면 payer 계정의 약정이 놀아도 linked account에 넘어가지 않는다. 절감 효율은 sharing on보다 낮아질 수 있다.

멀티 계정에서 약정 구매 시점을 조율하지 않으면 linked account 담당자가 각자 구매해서 중복이 발생하는 사례가 있다. payer 계정 담당자만 구매권을 갖고, linked account는 Cost Explorer에서 추천만 보는 방식으로 운영하는 게 낫다.

```bash
# payer 계정에서 전체 Savings Plans 상태 확인
aws savingsplans describe-savings-plans \
  --states active \
  --query 'savingsPlans[*].{ARN:savingsPlanArn,Type:savingsPlanType,Region:region,Commitment:committedAmount,Currency:currency,End:end}'

# Organizations 내 계정별 Savings Plans 커버리지 확인
aws ce get-savings-plans-coverage \
  --time-period Start=2026-07-01,End=2026-07-25 \
  --granularity MONTHLY \
  --group-by '[{"Type":"DIMENSION","Key":"LINKED_ACCOUNT"}]'
```

## 구매 실수 사례와 트러블슈팅

**실수 1: 피크 기준으로 약정 금액을 잡는 경우**

스케일다운 계획이 있거나 이벤트성 트래픽이 몰리는 서비스에서 자주 발생한다. $15/hr 피크 기준으로 구매했다가 평소 $8/hr 수준으로 내려오면 매달 $7 × 720시간 = $5,040을 그냥 날린다. 약정은 사용 여부와 무관하게 청구된다.

**실수 2: EC2 Instance SP와 Compute SP를 동시 구매해서 커버 범위가 겹치는 경우**

패밀리가 겹치는 인스턴스를 운영하면 EC2 Instance SP가 먼저 적용되고 남은 사용량에 Compute SP가 붙는다. 의도적인 조합이 아니라면 Compute SP 약정이 남는 상황이 생긴다. EC2 Instance SP는 할인율이 높아서 해당 패밀리에 집중하고, 나머지 유연한 사용량에만 Compute SP를 소량 잡는 조합이 현실적이다.

**실수 3: Fargate 사용량이 EC2 Instance Savings Plans에 포함된다고 착각**

EC2 Instance SP는 Fargate에 적용되지 않는다. Fargate를 주요 워크로드로 운영하는 팀에서 EC2 Instance SP를 구매하면 Fargate 비용은 그대로 On-Demand로 나간다. Fargate가 있으면 반드시 Compute SP를 써야 한다.

**실수 4: Lambda 요청 수 비용까지 포함해서 약정 금액 계산**

Lambda 비용은 실행 시간(GB-초)과 요청 수로 나뉜다. Savings Plans는 실행 시간 비용에만 붙는다. 요청 수에서 비용이 대부분 나오는 함수라면 Savings Plans 약정을 잡아도 절감액이 거의 없다. Lambda 함수별 비용 구성을 먼저 확인한다.

**실수 5: 만료일 관리 실패**

여러 시점에 나눠서 구매하면 만료일이 분산된다. 만료 후 재약정을 놓치면 그 기간은 On-Demand로 과금된다. 만료 30일 전에 알림이 오도록 Cost Explorer에서 설정해두는 게 낫다.

**트러블슈팅: 약정을 샀는데 할인이 안 들어오는 경우**

Cost Explorer → Savings Plans → Utilization 화면을 먼저 본다. Utilization이 낮으면 약정이 사용량에 붙지 않고 있다는 뜻이다.

원인 후보는 순서대로 확인한다.

- EC2 Instance SP인데 운영 중 다른 패밀리로 인스턴스를 바꿨다.
- EC2 Instance SP인데 다른 리전을 쓰고 있다.
- RI가 먼저 적용돼서 Savings Plans가 커버할 사용량 자체가 없다.
- Organizations에서 sharing이 off 상태인데 linked account에서 적용되기를 기대하고 있다.
- 구매 직후라 반영까지 최대 24시간이 걸릴 수 있다.

```bash
# 활성 Savings Plans 목록과 약정 내용 확인
aws savingsplans describe-savings-plans \
  --states active \
  --query 'savingsPlans[*].{Type:savingsPlanType,Region:region,Commitment:committedAmount,End:end}'

# 기간별 미사용 약정 금액 조회
aws ce get-savings-plans-utilization-details \
  --time-period Start=2026-07-01,End=2026-07-25 \
  --query 'SavingsPlansUtilizationDetails[*].{ARN:SavingsPlanArn,Used:Utilization.UsedCommitment,Unused:Utilization.UnusedCommitment,Pct:Utilization.UtilizationPercentage}'
```

## 운영 시 주의사항

약정은 취소가 안 된다. 구매 후 비즈니스 상황이 바뀌어 사용량이 줄어도 약정 금액은 그대로 청구된다. AWS Marketplace에서 재판매가 가능하긴 한데 절차가 번거롭고 원금 회수도 어렵다.

No Upfront 방식은 약정 기간 동안 매달 청구되는 구조라 현금 흐름 부담이 덜하지만, All Upfront 대비 할인율이 낮다. 초기 비용이 부담스러운 스타트업 환경에서는 No Upfront로 시작해서 서비스 안정화 후 다음 약정 시 All Upfront로 전환하는 경우가 많다.

3년 약정은 할인율이 확실히 높지만 서비스가 3년 이상 같은 구성으로 유지된다는 확신이 있을 때만 선택한다. 스타트업이나 빠르게 변화하는 워크로드라면 1년으로 시작하는 게 낫다.

Savings Plans 도입 후에는 매주 두 가지 지표를 챙긴다.

- **Utilization**: 산 약정이 얼마나 쓰이는가. 90% 아래로 내려가면 약정이 남는다는 신호.
- **Coverage**: 전체 사용량 중 약정이 덮은 비율. 낮아지면 새 약정 검토 신호.

두 지표를 분리해서 보는 게 중요하다. Utilization이 낮으면 산 약정이 놀고 있는 것이고, Coverage가 낮으면 약정이 부족한 것이다.
