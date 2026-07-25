---
title: AWS Savings Plans
tags: [aws, cost, savings-plans, reserved-instances, ec2, fargate, lambda]
updated: 2026-07-25
---

# AWS Savings Plans

1년 또는 3년 약정으로 시간당 최소 사용량을 달러 단위로 약정하면 On-Demand 대비 최대 72% 할인을 받는 방식이다. Reserved Instances(RI)와 달리 특정 인스턴스 유형을 고정하지 않아도 된다.

## Reserved Instances와 구조적 차이

RI는 인스턴스 단위 예약이다. `m5.large`를 예약했으면 그 타입으로 써야만 할인이 붙는다. 타입을 바꾸거나 리전을 이동하면 예약분은 그냥 낭비된다.

Savings Plans는 "시간당 $X 이상 쓰겠다"는 금액 단위 약정이다. 인스턴스 타입을 바꿔도, 크기를 조정해도 약정 금액 내라면 할인이 자동으로 붙는다. 운영 중에 인스턴스 유형을 자주 바꾸는 팀이라면 RI보다 Savings Plans 쪽이 관리가 훨씬 단순하다.

결제 방식은 둘 다 동일하다. All Upfront(전액 선납), Partial Upfront(일부 선납), No Upfront(선납 없음) 중 선택한다. 선납 비율이 높을수록 할인율이 올라간다.

## 종류별 차이

### Compute Savings Plans

EC2, Fargate, Lambda 전부 적용된다. 인스턴스 패밀리, 리전, OS, 테넌시를 고정하지 않아도 된다.

할인율은 최대 66%로 세 종류 중 가장 낮지만, 유연성이 가장 높다. 아키텍처를 자주 바꾸거나 멀티 리전 운영을 하는 경우에 적합하다.

### EC2 Instance Savings Plans

인스턴스 패밀리와 리전을 지정해야 한다. 예를 들어 `us-east-1`의 M 패밀리로 약정하면 `m5.large`, `m5.xlarge`, `m6i.large` 등 M 계열이면 크기와 세대가 달라도 할인이 적용된다. OS나 테넌시는 바꿀 수 있다.

할인율은 최대 72%로 가장 높다. 특정 리전에서 특정 인스턴스 패밀리를 장기적으로 운영하는 게 확실한 서비스라면 이 방식이 절감 효과가 크다.

### SageMaker Savings Plans

SageMaker 워크로드 전용이다. 인스턴스 패밀리, 크기, 리전, SageMaker 컴포넌트(Training, Inference, Processing 등) 구분 없이 적용된다. 할인율은 최대 64%.

ML 파이프라인을 상시 운영하는 팀만 해당되는 플랜이다. 간헐적으로 쓰는 경우에는 약정 금액을 채우지 못해 오히려 손해가 난다.

## RI와 혼용 시 적용 우선순위

RI와 Savings Plans를 동시에 보유하는 경우가 있다. 이때 적용 순서는 다음과 같다.

1. Reserved Instances가 먼저 적용된다.
2. RI로 커버되지 않는 사용량에 Savings Plans가 적용된다.
3. 두 할인 모두 소진되면 나머지는 On-Demand로 과금된다.

이 순서를 모르고 RI와 Savings Plans를 중복 구매하면 약정을 다 소화하지 못하는 상황이 생긴다. 예를 들어 `m5.large 10대`를 RI로 예약해두고 Compute Savings Plans도 구매했는데 실제로 `m5.large`만 10대 쓴다면 RI가 전부 커버하므로 Savings Plans 약정 금액이 남아도는 상태가 된다. Savings Plans 잔여 약정은 버려지지 않고 다른 인스턴스 사용량에 자동 적용되지만, RI와 Savings Plans의 커버 범위가 겹치면 실질 절감률이 기대보다 낮아진다.

RI 만료 시점에 맞춰 Savings Plans로 전환하거나, 새 워크로드에는 Savings Plans만 쓰고 기존 RI는 만료까지 유지하는 식으로 분리하는 게 낫다.

## 약정 전 Calculator 사용

AWS 콘솔 → Cost Management → Savings Plans → Recommendations에서 확인한다. 최소 14일간의 사용 이력 데이터가 쌓여야 의미 있는 추천이 나온다.

Recommendations 화면에서 세 가지를 확인한다.

약정 금액 대비 예상 절감액은 권장 약정 금액과 함께 제시되는데, 이 금액을 그대로 따를 필요는 없다. 현재 On-Demand 지출의 70~80% 수준에서 시작하는 게 안전하다. 나머지는 On-Demand로 두면 트래픽 급증 시에도 비용이 폭발하지 않는다.

커버리지(Coverage)는 현재 사용량 중 약정으로 커버되는 비율이다. 90%를 넘기면 과도한 약정일 수 있다. 사용량이 줄어드는 시기에 약정을 다 소화 못 하면 그만큼 손해다.

약정 기간과 결제 방식 조합도 살펴본다. 1년 No Upfront와 3년 All Upfront는 할인율 차이가 크다. 서비스가 3년 이상 유지된다는 확신이 있을 때만 3년을 선택한다.

```bash
# AWS CLI로 Savings Plans 추천 조회
aws savingsplans list-savings-plans-offerings \
  --product-type EC2 \
  --plan-type ComputeSavingsPlans \
  --durations 31536000

# 현재 Savings Plans 사용률 조회
aws ce get-savings-plans-utilization \
  --time-period Start=2026-07-01,End=2026-07-25
```

## 실제 운영 시 주의사항

약정은 취소가 안 된다. 구매 후 비즈니스 상황이 바뀌어 사용량이 줄어도 약정 금액은 그대로 청구된다. AWS Marketplace에서 재판매가 가능하긴 한데 절차가 번거롭고 원금 회수도 어렵다.

No Upfront 방식은 약정 기간 동안 매달 청구되는 구조라 현금 흐름 부담이 덜하지만, All Upfront 대비 할인율이 낮다. 초기 비용이 부담스러운 스타트업 환경에서는 No Upfront로 시작해서 서비스 안정화 후 다음 약정 시 All Upfront로 전환하는 경우가 많다.

Lambda에 Compute Savings Plans가 적용된다는 점을 모르는 경우가 꽤 있다. Lambda 비용이 크다면 Compute Savings Plans 약정 금액에 Lambda 사용량도 포함해서 계산하면 된다. 단, Lambda는 요청량 예측이 어려운 경우가 많으니 안정적으로 사용량이 나오는 함수 위주로 계산하는 게 현실적이다.